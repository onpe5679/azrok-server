"""Disposable full-server admin UI fixture. No production account connection."""
import json
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from azrok_server import AzrokServer
from azrok_control import ControlServer
from azrok_admin import INVENTORY_SIZES
from azrok_admin_history import record_event

root = tempfile.mkdtemp(prefix='azrok-admin-preview-')
server = AzrokServer(port=0, log_dir=root)
key = 'a74657374_s0_c' + '관리테스트'.encode('cp949').hex()
state = {'schema_version': 1, 'revision': 1, 'currency': 500,
         'character': {'name_hex': '관리테스트'.encode('cp949').hex(), 'species': 1, 'slot': 0},
         'snapshot_hex': (bytes(5)+bytes([1])+bytes(190)).hex(),
         'inventory': {k: [0]*v for k,v in INVENTORY_SIZES.items()},
         'accessory_slots': [8,6,3,2], 'active_loadouts': {},
         'runtime_rows': [], 'runtime_row_meta': [], 'completed_runtime_rows': []}
(Path(server.state_store_dir)/(key+'_state_v1.json')).write_text(json.dumps(state), encoding='utf-8')
record_event(server,'login','테스트 접속',details={'key':key})
record_event(server,'chat','관리테스트: 확인용 메시지',details={'key':key})
control = ControlServer(server, port=0)
assert control.start()
print('PORT', control.httpd.server_address[1], flush=True)
print(root, flush=True)
while True:
    time.sleep(1)
