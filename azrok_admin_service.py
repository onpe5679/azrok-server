"""Private operator transactions; no public route or credential projection."""
import copy
import json
import os
import shutil
import time
import uuid
from pathlib import Path

from azrok_admin import (parse_character_key, character_admin_view, list_accounts,
                         validate_patch, ITEM_ID_BASE, INVENTORY_SIZES)


def players(server):
    with server.ctl_lock:
        result = []
        for conn, meta in server.client_meta.items():
            if conn not in server.connections:
                continue
            proto = meta.get('proto_state') or {}
            raw = proto.get('account_raw') or b''
            account = raw if isinstance(raw, str) else bytes(raw).split(b'\0', 1)[0].decode('ascii', 'replace')
            result.append({'account': account, 'entity_id': meta.get('entity_id'),
                           'connected_at': meta.get('connected_at')})
        return result


def accounts(server, registry=None):
    from azrok_admin_history import latest_login_by_account
    active = players(server)
    rows = list_accounts(server.state_store_dir,
                         registry.admin_snapshot() if registry else {}, active)
    logins = latest_login_by_account(server)['latest']
    for row in rows:
        row['last_login'] = logins.get(row['account'])
        row['activity_basis'] = 'login' if row['last_login'] else 'state_file_mtime_not_login'
    rows.sort(key=lambda row: row['last_login'] or row.get('latest_state_saved_utc') or '', reverse=True)
    return {'accounts': rows}


def detail(server, key):
    result = character_admin_view(server.state_store_dir, key)
    result['online'] = any(p['account'] == result['account'] for p in players(server))
    result['edit_notice'] = '접속 중에는 저장 충돌 방지를 위해 편집할 수 없습니다. 게임 종료 후 저장하세요.'
    return result


def mutate(server, body):
    identity = parse_character_key(body.get('key'))
    key = identity['key']
    action = body.get('action')
    if action not in ('update', 'archive'):
        raise ValueError('지원하지 않는 작업입니다.')
    server._ensure_ox_runtime()
    with server.proto_lock, server.ox_action_lock:
        if any(p['account'] == identity['account'] for p in players(server)):
            return False, {'error': '현재 접속 중인 계정입니다. 게임 종료 후 다시 저장하세요.'}
        path = Path(server.state_store_dir) / (key + '_state_v1.json')
        document = json.loads(path.read_text(encoding='utf-8'))
        revision = body.get('expected_revision')
        if type(revision) is not int or revision != document.get('revision'):
            return False, {'error': '다른 작업으로 저장이 변경됐습니다. 최신 정보를 다시 불러오세요.'}
        changes = body.get('changes') or {}
        normalized = None
        if action == 'archive':
            if body.get('confirmation') != identity['name']:
                raise ValueError('삭제할 캐릭터 이름이 일치하지 않습니다.')
        else:
            if not isinstance(changes, dict) or set(changes) - {'fields', 'inventory'}:
                raise ValueError('잘못된 수정 항목입니다.')
            fields = changes.get('fields') or {}
            if not isinstance(fields, dict) or set(fields) - {'currency'}:
                raise ValueError('현재 지원하는 기본정보 편집은 펀콘입니다.')
            patch = {'expected_revision': revision, **fields}
            if 'inventory' in changes:
                inventory = changes['inventory']
                if not isinstance(inventory, dict):
                    raise ValueError('인벤토리 형식이 올바르지 않습니다.')
                edits = []
                for item, quantity in inventory.items():
                    item = int(item)
                    matches = [(name, item-base) for name, base in ITEM_ID_BASE.items()
                               if 0 <= item-base < INVENTORY_SIZES[name]]
                    if len(matches) != 1:
                        raise ValueError('알 수 없는 아이템입니다.')
                    name, slot = matches[0]
                    edits.append({'name': name, 'slot': slot, 'quantity': quantity})
                patch['inventory'] = edits
            normalized = validate_patch(document, patch)
        backup = Path(server.state_store_dir) / 'admin_backups' / (time.strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:10])
        backup.mkdir(parents=True)
        files = [Path(server.state_store_dir) / (key + suffix)
                 for suffix in ('_state_v1.json', '_c2s0007.bin', '_ox_v1.json')]
        legacy = Path(server.state_store_dir) / (document['character']['name_hex'] + '_c2s0007.bin')
        if legacy.exists():
            files.append(legacy)
        for source in files:
            if source.exists():
                shutil.copy2(source, backup / source.name)
        receipt = {'key': key, 'action': action, 'revision_before': revision,
                   'changes': normalized, 'status': 'prepared'}
        (backup / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False), encoding='utf-8')
        if action == 'archive':
            moved = []
            try:
                for source in files:
                    if source.exists():
                        # Backup is already durable and remains recoverable.
                        target = backup / (source.name + '.removed')
                        os.replace(source, target)
                        moved.append((source, target))
            except OSError:
                for source, target in reversed(moved):
                    os.replace(target, source)
                raise
        else:
            working = copy.deepcopy(document)
            if 'currency' in normalized:
                working['currency'] = normalized['currency']
            for edit in normalized.get('inventory', ()):
                working['inventory'][edit['name']][edit['slot']] = edit['quantity']
            old_proto = server.proto_state
            try:
                server.proto_state = {'account_raw': identity['account'].encode('ascii'),
                                      'char_name_raw': bytes.fromhex(document['character']['name_hex']),
                                      'character_slot': identity['slot'],
                                      'char_type': document['character']['species']}
                if not server._save_canonical_character_state(working, key=key,
                        mutation={'kind': 'admin_update', 'changed_fields': list(normalized)}):
                    return False, {'error': '저장에 실패했습니다. 원본 백업은 보관됐습니다.'}
            finally:
                server.proto_state = old_proto
        for name in ('saved_server_states', 'saved_character_states'):
            getattr(server, name, {}).pop(key, None)
        if action == 'archive' and hasattr(server, 'ox_pending_results'):
            server.ox_pending_results = [row for row in server.ox_pending_results if row[0] != key]
        receipt['status'] = 'committed'
        (backup / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False), encoding='utf-8')
        from azrok_admin_history import record_event
        try:
            record_event(server, 'audit', '캐릭터 백업 삭제' if action == 'archive' else '캐릭터 정보 수정',
                         details={'key': key, 'action': action, 'backup_path': backup.name})
        except OSError:
            # The transaction receipt remains with the durable backup.
            server.admin_history_failures = getattr(server, 'admin_history_failures', 0) + 1
        return True, {'ok': True, 'message': '백업 후 삭제했습니다.' if action == 'archive' else '저장했습니다. 다음 접속부터 적용됩니다.',
                      'backup_id': backup.name, 'revision': revision + (action == 'update')}
