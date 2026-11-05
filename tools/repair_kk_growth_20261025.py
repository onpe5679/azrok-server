"""Evidence-bound one-character repair. Run only while azrok-core is stopped."""
import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

KEY = 'a6153536a79344a324341653457_s0_cb3a9b1f8'
EXPECTED = '59d61d2c689003db09135d5308a6d4619d5f3368c6bf9d233a3082f632442f3a'
EXPECTED_REVISION = 33

def repair(root, apply=False):
    path = root / 'server_state' / (KEY + '_state_v1.json')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED:
        raise RuntimeError('Character changed since evidence collection; refusing repair')
    state = json.loads(raw)
    assert state['revision'] == EXPECTED_REVISION
    current = bytearray.fromhex(state['snapshot_hex'])
    assert len(current) == 196 and current[5] == 0
    evidence = json.loads((root/'artifacts/private/20261025_growth_stage1_recovery_evidence.json').read_text(encoding='utf-8'))
    captured = bytes.fromhex(evidence['evidence']['client_rejected_stage1_snapshot_hex'])
    assert len(captured) == 196 and captured[5] == 1
    assert hashlib.sha256(captured).hexdigest() == evidence['evidence']['client_payload_sha256']
    assert all(f'g1:r0:k5:a{aux}:c100' in state['completed_runtime_rows'] for aux in (212,202,203,227,201))
    assert all(row['kind'] == 255 for row in state['runtime_rows'])
    updated = copy.deepcopy(state)
    current[5] = 1
    updated['snapshot_hex'] = current.hex()
    updated['revision'] = EXPECTED_REVISION + 1
    updated['completed_runtime_rows'].append('g1:r0:k3:a0:e1')
    updated['runtime_row_meta'][0] = {'generation': 1, 'issued_evolution': 1}
    assert updated['inventory'] == state['inventory'] and updated['currency'] == state['currency']
    assert sum(a != b for a,b in zip(bytes.fromhex(state['snapshot_hex']), current)) == 1
    report = {'key': KEY, 'revision_before':EXPECTED_REVISION, 'revision_after':EXPECTED_REVISION + 1,
              'snapshot_changed_offsets':[5], 'currency_preserved':state['currency'],
              'inventory_preserved':True, 'evidence_capture_seq':1713, 'applied':False}
    if not apply:
        return report
    active = subprocess.run(['systemctl','--user','is-active','azrok-core'], capture_output=True, text=True)
    if active.stdout.strip() not in ('inactive','failed'):
        raise RuntimeError('azrok-core must be stopped before repair')
    backup = root/'server_state/admin_backups/20261025_kk_growth_repair'
    backup.mkdir(parents=True, exist_ok=False)
    for suffix in ('_state_v1.json','_c2s0007.bin','_ox_v1.json'):
        source = root/'server_state'/(KEY+suffix)
        if source.exists(): shutil.copy2(source, backup/source.name)
    # Canonical commit first; raw mirror is compatibility data only.
    temp = path.with_suffix('.repair.tmp')
    with temp.open('w',encoding='utf-8') as stream:
        json.dump(updated,stream,ensure_ascii=False,sort_keys=True,indent=2)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    os.replace(temp,path)
    mirror = root/'server_state'/(KEY+'_c2s0007.bin')
    temp = mirror.with_suffix('.repair.tmp')
    with temp.open('wb') as stream:
        stream.write(current); stream.flush(); os.fsync(stream.fileno())
    os.replace(temp,mirror)
    report['applied'] = True
    (backup/'receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--root',type=Path,required=True); parser.add_argument('--apply',action='store_true')
    args=parser.parse_args(); print(json.dumps(repair(args.root,args.apply),ensure_ascii=False))
