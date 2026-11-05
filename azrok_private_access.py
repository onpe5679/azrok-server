"""Private-network device credentials and account-bound admission tickets.

The browser identifier is only a device credential handle. New browsers get
an opaque original-client account automatically. Each account has one stable
recovery code derived with the private server secret; only an explicit rotation
changes it, and the plaintext code is never stored in the registry.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import hmac
import ipaddress
import json
import os
import re
import secrets
import threading
import time
from pathlib import Path


_PRIVATE_CLIENT_NETWORKS = (
    ipaddress.IPv4Network("127.0.0.0/8"),
    ipaddress.IPv4Network("10.0.0.0/8"),
    ipaddress.IPv4Network("172.16.0.0/12"),
    ipaddress.IPv4Network("192.168.0.0/16"),
    ipaddress.IPv4Network("100.64.0.0/10"),
)
_BROWSER_ID = re.compile(r"[A-Za-z0-9_-]{22,128}\Z")
# Conservative original-client account-field limit and cmd.exe-safe alphabet.
_ACCOUNT_ID = re.compile(r"[A-Za-z0-9_]{3,13}\Z")
_RECOVERY_CODE = re.compile(r"azr1-[A-Za-z0-9_-]{43}\Z")
_TICKET_V1 = re.compile(r"v1\.([0-9]{1,12})\.([A-Za-z0-9_-]{22,128})\.([A-Za-z0-9_-]{43})\Z")
_TICKET_V2 = re.compile(
    r"v2\.([0-9]{1,12})\.([A-Za-z0-9_-]{22,128})\.([A-Za-z0-9_]{3,13})\.([A-Za-z0-9_-]{43})\Z"
)
_PROFILE_LAUNCHERS = {
    "player": "run_azrok_seh.bat",
    "peer111": "run_azrok_peer111.bat",
    "player2": "run_azrok_multi2.bat",
    "player3": "run_azrok_player3.bat",
    "player4": "run_azrok_player4.bat",
    "player5": "run_azrok_player5.bat",
    "player6": "run_azrok_player6.bat",
}
GENERIC_ACCOUNT_LAUNCHER = "run_azrok_account.bat"


def is_private_client(address: object) -> bool:
    if not isinstance(address, str):
        return False
    try:
        candidate = ipaddress.IPv4Address(address)
    except ipaddress.AddressValueError:
        return False
    return any(candidate in network for network in _PRIVATE_CLIENT_NETWORKS)


def valid_browser_id(value: object) -> bool:
    return isinstance(value, str) and _BROWSER_ID.fullmatch(value) is not None


def valid_account_id(value: object) -> bool:
    return isinstance(value, str) and _ACCOUNT_ID.fullmatch(value) is not None


def read_access_secret(path: Path) -> bytes:
    secret = path.read_bytes().strip()
    if len(secret) < 16 or len(secret) > 4096:
        raise ValueError("private access secret must contain 16..4096 bytes")
    return secret


def _encoded_hmac(secret: bytes, payload: bytes) -> str:
    digest = hmac.new(secret, payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _ticket_signature(secret: bytes, expires_at: int, browser_id: str, account_id: str) -> str:
    return _encoded_hmac(secret, f"v2|{expires_at}|{browser_id}|{account_id}".encode("ascii"))


def issue_browser_ticket(
    secret: bytes,
    browser_id: str,
    account_id: str,
    *,
    now: float | None = None,
    ttl_seconds: int = 43200,
) -> str:
    """Issue a v2 ticket cryptographically bound to browser and account."""
    if not valid_browser_id(browser_id):
        raise ValueError("invalid browser identifier")
    if not valid_account_id(account_id):
        raise ValueError("invalid account identifier")
    if ttl_seconds < 60 or ttl_seconds > 86400:
        raise ValueError("ticket TTL must be within 60 seconds..24 hours")
    expires_at = int((time.time() if now is None else now) + ttl_seconds)
    signature = _ticket_signature(secret, expires_at, browser_id, account_id)
    return f"v2.{expires_at}.{browser_id}.{account_id}.{signature}"


def browser_ticket_claims(
    secret: bytes,
    ticket: object,
    *,
    now: float | None = None,
    allow_legacy: bool = False,
) -> dict[str, object] | None:
    """Return authenticated claims, or ``None`` for malformed/expired input.

    Legacy v1 tickets may be decoded only when explicitly requested. They
    carry no account claim and therefore must not authorize a game relay.
    """
    if not isinstance(ticket, str):
        return None
    current = int(time.time() if now is None else now)
    match = _TICKET_V2.fullmatch(ticket)
    if match is not None:
        expires_at = int(match.group(1))
        browser_id = match.group(2)
        account_id = match.group(3)
        expected = _ticket_signature(secret, expires_at, browser_id, account_id)
        if expires_at < current or not hmac.compare_digest(match.group(4), expected):
            return None
        return {
            "version": 2,
            "expires_at": expires_at,
            "browser_id": browser_id,
            "account_id": account_id,
        }
    if not allow_legacy:
        return None
    match = _TICKET_V1.fullmatch(ticket)
    if match is None:
        return None
    expires_at = int(match.group(1))
    browser_id = match.group(2)
    expected = _encoded_hmac(secret, f"v1|{expires_at}|{browser_id}".encode("ascii"))
    if expires_at < current or not hmac.compare_digest(match.group(3), expected):
        return None
    return {
        "version": 1,
        "expires_at": expires_at,
        "browser_id": browser_id,
        "account_id": None,
    }


def validate_browser_ticket(
    secret: bytes,
    ticket: object,
    *,
    now: float | None = None,
    expected_account: str | None = None,
    allow_legacy: bool = False,
) -> bool:
    claims = browser_ticket_claims(secret, ticket, now=now, allow_legacy=allow_legacy)
    if claims is None:
        return False
    if expected_account is not None:
        return valid_account_id(expected_account) and hmac.compare_digest(
            str(claims.get("account_id") or ""), expected_account
        )
    return claims.get("account_id") is not None or allow_legacy


class PrivateAccountRegistry:
    """Durable browser/device bindings with password-free account recovery."""

    def __init__(self, path: Path, recovery_secret: bytes | None = None):
        self.path = Path(path)
        if recovery_secret is not None and not 16 <= len(recovery_secret) <= 4096:
            raise ValueError("private recovery secret must contain 16..4096 bytes")
        self.recovery_secret = recovery_secret
        self._lock = threading.RLock()
        # Password-free v3 is an eager migration, not merely an in-memory
        # view. Starting either private service removes obsolete password and
        # one-time-code records before serving account recovery.
        if self.path.exists():
            with self._locked():
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(raw, dict) and raw.get("version") in {1, 2}:
                    migrated = self._migrate_v1(raw) if raw.get("version") == 1 else self._migrate_v2(raw)
                    self._write(migrated)

    @contextlib.contextmanager
    def _locked(self):
        """Serialize transactions across the LAN and Tailscale processes."""
        with self._lock:
            lock_path = self.path.with_suffix(self.path.suffix + ".lock")
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            with lock_path.open("a+b") as handle:
                handle.seek(0, os.SEEK_END)
                if handle.tell() == 0:
                    handle.write(b"\0")
                    handle.flush()
                handle.seek(0)
                try:
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                    unlock = lambda: msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                except ImportError:  # pragma: no cover - production is Windows
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                    unlock = lambda: fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                try:
                    yield
                finally:
                    handle.seek(0)
                    unlock()

    @staticmethod
    def _empty() -> dict:
        return {"version": 3, "bindings": {}, "accounts": {}}

    @staticmethod
    def _validate_v3(data: dict) -> dict:
        bindings = data.get("bindings")
        accounts = data.get("accounts")
        if not isinstance(bindings, dict) or not isinstance(accounts, dict):
            raise ValueError("invalid private account registry fields")
        clean_accounts: dict[str, dict] = {}
        for account_id, metadata in accounts.items():
            if not valid_account_id(account_id) or not isinstance(metadata, dict):
                raise ValueError("invalid private account record")
            recovery_revision = metadata.get("recovery_revision", 0)
            if not isinstance(recovery_revision, int) or recovery_revision < 0:
                raise ValueError("invalid private account recovery revision")
            created_at = metadata.get("created_at", 0)
            if not isinstance(created_at, int) or created_at < 0:
                raise ValueError("invalid private account creation time")
            clean_accounts[account_id] = {
                "created_at": created_at,
                "recovery_revision": recovery_revision,
                "legacy": bool(metadata.get("legacy", False)),
            }
        clean_bindings: dict[str, str] = {}
        for browser_id, account_id in bindings.items():
            if not valid_browser_id(browser_id) or account_id not in clean_accounts:
                raise ValueError("invalid private browser binding")
            clean_bindings[browser_id] = account_id
        return {"version": 3, "bindings": clean_bindings, "accounts": clean_accounts}

    @classmethod
    def _migrate_v1(cls, data: dict) -> dict:
        bindings = data.get("bindings")
        passwords = data.get("passwords")
        if not isinstance(bindings, dict) or not isinstance(passwords, dict):
            raise ValueError("invalid private account registry fields")
        migrated = cls._empty()
        account_ids = set(_PROFILE_LAUNCHERS)
        account_ids.update(bindings.values())
        account_ids.update(passwords)
        if not all(valid_account_id(account_id) for account_id in account_ids):
            raise ValueError("invalid legacy private account identifier")
        for account_id in sorted(account_ids):
            migrated["accounts"][account_id] = {
                "created_at": 0,
                "recovery_revision": 0,
                "legacy": True,
            }
        for browser_id, account_id in bindings.items():
            if not valid_browser_id(browser_id) or account_id not in migrated["accounts"]:
                raise ValueError("invalid legacy private browser binding")
            migrated["bindings"][browser_id] = account_id
        # Password hashes are intentionally discarded in password-free v3.
        return migrated

    @classmethod
    def _migrate_v2(cls, data: dict) -> dict:
        bindings = data.get("bindings")
        accounts = data.get("accounts")
        if not isinstance(bindings, dict) or not isinstance(accounts, dict):
            raise ValueError("invalid private account registry fields")
        migrated = cls._empty()
        for account_id, metadata in accounts.items():
            if not valid_account_id(account_id) or not isinstance(metadata, dict):
                raise ValueError("invalid private account record")
            migrated["accounts"][account_id] = {
                "created_at": int(metadata.get("created_at", 0)),
                "recovery_revision": 0,
                "legacy": bool(metadata.get("legacy", False)),
            }
        for browser_id, account_id in bindings.items():
            if not valid_browser_id(browser_id) or account_id not in migrated["accounts"]:
                raise ValueError("invalid private browser binding")
            migrated["bindings"][browser_id] = account_id
        return migrated

    def _read(self) -> dict:
        if not self.path.exists():
            return self._empty()
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("invalid private account registry")
        if data.get("version") == 1:
            return self._migrate_v1(data)
        if data.get("version") == 2:
            return self._migrate_v2(data)
        if data.get("version") != 3:
            raise ValueError("invalid private account registry")
        return self._validate_v3(data)

    def _write(self, data: dict) -> None:
        data = self._validate_v3(data)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=True, separators=(",", ":")), encoding="utf-8")
        os.replace(temporary, self.path)

    @staticmethod
    def launcher_for(account_id: str) -> str:
        if not valid_account_id(account_id):
            raise ValueError("invalid preserved account")
        return _PROFILE_LAUNCHERS.get(account_id, GENERIC_ACCOUNT_LAUNCHER)

    @staticmethod
    def _browser_preview(browser_id: str) -> str:
        if not isinstance(browser_id, str):
            return "invalid"
        digest = hashlib.sha256(browser_id.encode("utf-8")).hexdigest()[:10]
        return f"browser…{digest}"

    @staticmethod
    def _new_account_id(existing: dict) -> str:
        for _ in range(128):
            candidate = "a" + secrets.token_urlsafe(9)
            if valid_account_id(candidate) and candidate not in existing:
                return candidate
        raise RuntimeError("could not allocate a private account identifier")

    def _recovery_code(self, account_id: str, revision: int) -> str:
        if self.recovery_secret is None:
            raise ValueError("private recovery secret unavailable")
        payload = f"azrok-recovery-v3|{account_id}|{revision}".encode("ascii")
        return "azr1-" + _encoded_hmac(self.recovery_secret, payload)

    @staticmethod
    def _require_account(data: dict, account_id: str) -> None:
        if not valid_account_id(account_id) or account_id not in data["accounts"]:
            raise ValueError("unknown private account")

    def admin_snapshot(self) -> dict:
        with self._locked():
            data = self._read()
            accounts = []
            for account_id, metadata in sorted(data["accounts"].items()):
                previews = sorted(
                    self._browser_preview(browser_id)
                    for browser_id, bound_account in data["bindings"].items()
                    if bound_account == account_id
                )
                accounts.append({
                    "account": account_id,
                    "launcher": self.launcher_for(account_id),
                    "binding_count": len(previews),
                    "browser_refs": previews,
                    "recovery_code_active": self.recovery_secret is not None,
                    "legacy": metadata["legacy"],
                })
            return {
                "schema": "azrok-private-account-admin-v3",
                "accounts": accounts,
                "allocation": {"mode": "dynamic", "limit": None, "count": len(accounts)},
                "privacy": {
                    "browser_ids": "redacted stable references only",
                    "recovery_codes": "HMAC-derived; stable until explicit rotation",
                    "passwords": "removed in schema v3",
                },
            }

    def admin_export_recovery_code(self, account_id: str) -> str:
        """Explicitly rotate and return an account recovery code."""
        with self._locked():
            data = self._read()
            self._require_account(data, account_id)
            data["accounts"][account_id]["recovery_revision"] += 1
            code = self._recovery_code(
                account_id, data["accounts"][account_id]["recovery_revision"]
            )
            self._write(data)
            return code

    def export_recovery_code(self, browser_id: str, *, rotate: bool = False) -> str:
        """Return the stable account code, rotating only when requested."""
        if not valid_browser_id(browser_id):
            raise ValueError("invalid browser identifier")
        with self._locked():
            data = self._read()
            account_id = data["bindings"].get(browser_id)
            if account_id is None:
                raise ValueError("browser has no private account binding")
            metadata = data["accounts"][account_id]
            if rotate:
                metadata["recovery_revision"] += 1
                self._write(data)
            return self._recovery_code(account_id, metadata["recovery_revision"])

    def import_recovery_code(self, browser_id: str, recovery_code: str) -> str:
        """Bind a browser using the account's current stable recovery code."""
        if not valid_browser_id(browser_id) or not isinstance(recovery_code, str):
            raise ValueError("invalid private account recovery")
        if _RECOVERY_CODE.fullmatch(recovery_code) is None:
            raise ValueError("invalid private account recovery")
        with self._locked():
            data = self._read()
            matches = [
                account_id
                for account_id, metadata in data["accounts"].items()
                if hmac.compare_digest(
                    self._recovery_code(account_id, metadata["recovery_revision"]),
                    recovery_code,
                )
            ]
            if len(matches) != 1:
                raise ValueError("private account recovery rejected")
            account_id = matches[0]
            data["bindings"][browser_id] = account_id
            self._write(data)
            return account_id

    def admin_clear_bindings(self, account_id: str) -> int:
        with self._locked():
            data = self._read()
            self._require_account(data, account_id)
            doomed = [
                browser_id for browser_id, bound_account in data["bindings"].items()
                if bound_account == account_id
            ]
            for browser_id in doomed:
                del data["bindings"][browser_id]
            if doomed:
                self._write(data)
            return len(doomed)

    def replace_browser_account(self, browser_id: str, expected_account: str) -> dict:
        """Retire one account and bind the requesting browser to a fresh one.

        This is the registry half of the explicit full-reset transaction.  All
        other browser bindings and the old recovery-code revision disappear
        with the retired account, so a copied recovery code cannot resurrect
        the reset identity.
        """
        if not valid_browser_id(browser_id) or not valid_account_id(expected_account):
            raise ValueError("invalid private account reset")
        with self._locked():
            data = self._read()
            current = data["bindings"].get(browser_id)
            if current != expected_account:
                raise ValueError("browser account changed before reset")
            self._require_account(data, expected_account)
            released = [
                bound_browser
                for bound_browser, account_id in data["bindings"].items()
                if account_id == expected_account
            ]
            replacement = self._new_account_id(data["accounts"])
            for bound_browser in released:
                del data["bindings"][bound_browser]
            del data["accounts"][expected_account]
            data["accounts"][replacement] = {
                "created_at": int(time.time()),
                "recovery_revision": 0,
                "legacy": False,
            }
            data["bindings"][browser_id] = replacement
            self._write(data)
            return {
                "old_account": expected_account,
                "account": replacement,
                "released_bindings": len(released),
            }

    def session_account(self, browser_id: str) -> str:
        if not valid_browser_id(browser_id):
            raise ValueError("invalid browser identifier")
        with self._locked():
            data = self._read()
            current = data["bindings"].get(browser_id)
            if current is not None:
                return current
            assigned = self._new_account_id(data["accounts"])
            data["accounts"][assigned] = {
                "created_at": int(time.time()),
                "recovery_revision": 0,
                "legacy": False,
            }
            data["bindings"][browser_id] = assigned
            self._write(data)
            return assigned

    def bind_existing_browser(self, browser_id: str, account_id: str) -> str:
        """Operator-only compatibility hook for preserved v1 accounts."""
        if not valid_browser_id(browser_id) or not valid_account_id(account_id):
            raise ValueError("invalid account binding")
        with self._locked():
            data = self._read()
            self._require_account(data, account_id)
            data["bindings"][browser_id] = account_id
            self._write(data)
            return account_id
