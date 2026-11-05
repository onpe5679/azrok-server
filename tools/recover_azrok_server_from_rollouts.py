"""Rebuild a lost azrok_server.py candidate from local history and rollout patches.

This emergency helper never writes azrok_server.py itself.  It copies the last
full Claude file-history snapshot to a separate recovery candidate, extracts
only successful apply_patch blocks targeting azrok_server.py from Codex JSONL,
retargets them to the candidate, and replays them chronologically.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import shutil
import subprocess
import sys


PATCH_ASSIGN_JSON = re.compile(
    r"const\s+patch\s*=\s*(\"(?:\\.|[^\"\\])*\")\s*;",
    re.DOTALL,
)
PATCH_ASSIGN_TEMPLATE = re.compile(
    r"const\s+patch\s*=\s*`([\s\S]*?)`\s*;",
)
BLOCK_HEADER = re.compile(
    r"^\*\*\* (?:Update|Add|Delete) File: (.+azrok_server\.py)\s*$",
    re.IGNORECASE,
)


def parse_time(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def output_text(payload: object) -> str:
    if isinstance(payload, str):
        return payload
    if isinstance(payload, list):
        pieces = []
        for item in payload:
            if isinstance(item, dict):
                pieces.append(str(item.get("text", "")))
            else:
                pieces.append(str(item))
        return "\n".join(pieces)
    return json.dumps(payload, ensure_ascii=False)


def decode_patch(js: str) -> str | None:
    match = PATCH_ASSIGN_JSON.search(js)
    if match:
        return json.loads(match.group(1))
    match = PATCH_ASSIGN_TEMPLATE.search(js)
    if match:
        return match.group(1)
    return None


def server_only_patch(patch: str, candidate: pathlib.Path) -> str | None:
    lines = patch.splitlines()
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in lines:
        if line.startswith("*** Update File:") or line.startswith("*** Add File:") or line.startswith("*** Delete File:"):
            if current is not None:
                blocks.append(current)
            current = [line]
        elif line == "*** End Patch":
            if current is not None:
                blocks.append(current)
                current = None
        elif current is not None:
            current.append(line)
    if current is not None:
        blocks.append(current)

    selected: list[str] = []
    for block in blocks:
        header = block[0]
        if not BLOCK_HEADER.match(header):
            continue
        action = header.split(" File:", 1)[0]
        block[0] = f"{action} File: {candidate}"
        selected.extend(block)
    if not selected:
        return None
    return "*** Begin Patch\n" + "\n".join(selected) + "\n*** End Patch\n"


def collect_calls(session_root: pathlib.Path, start: dt.datetime, end: dt.datetime):
    calls: dict[str, tuple[dt.datetime, str, pathlib.Path, int]] = {}
    outputs: dict[str, str] = {}
    for path in session_root.rglob("*.jsonl"):
        try:
            handle = path.open("r", encoding="utf-8")
        except OSError:
            continue
        with handle:
            for line_number, line in enumerate(handle, 1):
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = item.get("payload") or {}
                call_id = payload.get("call_id")
                if payload.get("type") == "custom_tool_call_output" and call_id:
                    outputs[call_id] = output_text(payload.get("output"))
                    continue
                if payload.get("type") != "custom_tool_call" or not call_id:
                    continue
                timestamp = item.get("timestamp")
                if not timestamp:
                    continue
                when = parse_time(timestamp)
                if not start < when <= end:
                    continue
                js = payload.get("input") or ""
                if "apply_patch" not in js or "azrok_server.py" not in js:
                    continue
                patch = decode_patch(js)
                if patch:
                    calls[call_id] = (when, patch, path, line_number)

    ordered = []
    for call_id, record in calls.items():
        result = outputs.get(call_id, "")
        lowered = result.lower()
        successful = (
            "script completed" in lowered
            and "script failed" not in lowered
            and "verification failed" not in lowered
        )
        if successful:
            ordered.append((record[0], call_id, record[1], record[2], record[3]))
    ordered.sort(key=lambda row: (row[0], str(row[3]), row[4]))
    return ordered


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True, type=pathlib.Path)
    parser.add_argument("--candidate", required=True, type=pathlib.Path)
    parser.add_argument("--sessions", required=True, type=pathlib.Path)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    args = parser.parse_args()

    candidate = args.candidate.resolve()
    if candidate.name != "azrok_server.recovery.py":
        raise SystemExit("candidate must be named azrok_server.recovery.py")
    shutil.copyfile(args.snapshot, candidate)

    calls = collect_calls(args.sessions, parse_time(args.start), parse_time(args.end))
    applied = 0
    for when, call_id, patch, source, line_number in calls:
        narrowed = server_only_patch(patch, candidate)
        if not narrowed:
            continue
        proc = subprocess.run(
            ["cmd.exe", "/d", "/c", "apply_patch"],
            input=narrowed,
            text=True,
            cwd=candidate.parent,
            capture_output=True,
        )
        if proc.returncode != 0:
            print(
                f"FAILED {when.isoformat()} {call_id} {source.name}:{line_number}\n"
                f"stdout={proc.stdout}\nstderr={proc.stderr}",
                file=sys.stderr,
            )
            return 2
        applied += 1
        print(f"APPLIED {applied:02d} {when.isoformat()} {call_id} {source.name}:{line_number}")
    print(f"RECOVERY_APPLIED={applied} CANDIDATE={candidate} SIZE={candidate.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
