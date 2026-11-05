"""Durable OX match results and an explicitly local information policy.

The original server's score awards and tier promotion rules have not been
recovered.  ``ox_info_projection`` therefore uses a preservation policy:
one displayed point per completed win and wins/matches as the gauge.  Tier
promotion at the original client's display thresholds is also a local policy.
The raw result ledger is independent of that policy and can be reprojected.
"""

import json
import os
import re


_KEY = re.compile(r'^[A-Za-z0-9_]+$')
_OUTCOMES = frozenset(('won', 'eliminated', 'abandoned', 'aborted'))
# Original Azrok.exe FUN_005FDF80 display literals for tiers 1..11.
# These are display thresholds, not evidence for original promotion rules.
CLIENT_DISPLAY_THRESHOLDS = (150, 300, 600, 1000, 3000, 5000, 7000,
                             9000, 10000, 10000, 10000)


def selected_ox_character_key(proto_state):
    """Validate the selected-character lease binding without changing context."""
    if not isinstance(proto_state, dict) or not proto_state.get('client_0005_seen'):
        return None
    selected = proto_state.get('selected_character_key')
    if not isinstance(selected, str):
        return None
    name = proto_state.get('char_name_raw') or b'Player'
    account = proto_state.get('account_raw') or b''
    if isinstance(name, str):
        name = name.encode('cp949', errors='ignore')
    if isinstance(account, str):
        account = account.encode('cp949', errors='ignore')
    name = bytes(name).split(b'\x00', 1)[0][:32] or b'Player'
    account = bytes(account).split(b'\x00', 1)[0][:13]
    if account:
        slot = int(proto_state.get('character_slot', 0)) & 3
        expected = f'a{account.hex()}_s{slot}_c{name.hex()}'
    else:
        expected = name.hex()
    return selected if selected == expected else None


def _path(state_store_dir, character_key):
    if not isinstance(character_key, str) or not _KEY.fullmatch(character_key):
        raise ValueError('invalid selected character key')
    if not state_store_dir:
        raise ValueError('state store unavailable')
    return os.path.join(state_store_dir, character_key + '_ox_v1.json')


def load_ox_progression(state_store_dir, character_key):
    """Read one selected character's ledger without creating a profile."""
    path = _path(state_store_dir, character_key)
    try:
        with open(path, 'r', encoding='utf-8') as stream:
            document = json.load(stream)
    except FileNotFoundError:
        return {'schema_version': 1, 'results': {}}
    if (not isinstance(document, dict) or document.get('schema_version') != 1
            or not isinstance(document.get('results'), dict)):
        raise ValueError('invalid OX result document')
    for match_id, result in document['results'].items():
        if (not isinstance(match_id, str) or not isinstance(result, dict)
                or result.get('outcome') not in _OUTCOMES
                or not isinstance(result.get('rounds_survived'), int)
                or result['rounds_survived'] < 0):
            raise ValueError('invalid OX result row')
    return document


def record_ox_result(state_store_dir, character_key, match_id, outcome,
                     rounds_survived):
    """Atomically commit one result; duplicate match IDs do not award twice."""
    if not isinstance(match_id, str) or not re.fullmatch(r'[0-9a-f]{32}', match_id):
        raise ValueError('invalid OX match id')
    if outcome not in _OUTCOMES:
        raise ValueError('invalid OX outcome')
    if (isinstance(rounds_survived, bool) or not isinstance(rounds_survived, int)
            or rounds_survived < 0):
        raise ValueError('invalid OX survived-round count')
    document = load_ox_progression(state_store_dir, character_key)
    if match_id in document['results']:
        return False
    document['results'][match_id] = {
        'outcome': outcome, 'rounds_survived': rounds_survived,
    }
    path = _path(state_store_dir, character_key)
    os.makedirs(state_store_dir, exist_ok=True)
    tmp_path = path + '.tmp'
    try:
        with open(tmp_path, 'w', encoding='utf-8', newline='\n') as stream:
            json.dump(document, stream, ensure_ascii=False, sort_keys=True)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    return True


def ox_info_projection(state_store_dir, character_key):
    """Return 0070 tier/points/denominator/numerator under local policy."""
    results = load_ox_progression(state_store_dir, character_key)['results'].values()
    outcomes = [row['outcome'] for row in results]
    wins = outcomes.count('won')
    matches = len(outcomes)
    tier = 1
    for threshold in CLIENT_DISPLAY_THRESHOLDS[:-1]:
        if wins < threshold:
            break
        tier += 1
    return {
        'tier': tier,
        'points': min(wins, 0xFFFF),
        'gauge_denominator': min(matches, 0xFFFFFFFF),
        'gauge_numerator': min(wins, 0xFFFFFFFF),
        'matches': matches,
        'wins': wins,
        'eliminations': outcomes.count('eliminated'),
        'abandonments': outcomes.count('abandoned'),
        'aborts': outcomes.count('aborted'),
        'policy': 'preservation_win_count_v1',
    }


def ox_preservation_ranking(state_store_dir):
    """Rank persisted characters by local wins, then matches, without writes."""
    if not state_store_dir or not os.path.isdir(state_store_dir):
        return []
    rows = []
    suffix = '_ox_v1.json'
    for filename in os.listdir(state_store_dir):
        if not filename.endswith(suffix):
            continue
        key = filename[:-len(suffix)]
        try:
            score = ox_info_projection(state_store_dir, key)
        except (OSError, TypeError, ValueError):
            continue
        rows.append({
            'character_key': key,
            'wins': score['wins'],
            'matches': score['matches'],
            'points': score['points'],
        })
    rows.sort(key=lambda row: (-row['wins'], row['matches'], row['character_key']))
    for index, row in enumerate(rows, 1):
        row['rank'] = index
    return rows
