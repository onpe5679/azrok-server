"""Isolated operator UI with representative, disposable characters."""
import json
import os
import struct
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
root = tempfile.mkdtemp(prefix='azrok-operator-preview-')
os.environ['AZROK_CAPTURE_DIR'] = str(Path(root)/'captures_structured')
from azrok_server import AzrokServer
from azrok_control import ControlServer
from azrok_admin import INVENTORY_SIZES
from azrok_admin_history import record_event

server = AzrokServer(port=0, log_dir=root)
for index, name in enumerate(('진달래', '별빛', '구름', '관리테스트', '느티나무')):
    account = f'demo{index+1}'
    key = 'a'+account.encode().hex()+'_s0_c'+name.encode('cp949').hex()
    snapshot = bytearray(196); snapshot[5] = 1
    struct.pack_into('<H',snapshot,12,3+index)
    state = {'schema_version':1, 'revision':1, 'currency':500+index*100,
             'character':{'name_hex':name.encode('cp949').hex(),'slot':0,'species':index%4},
             'snapshot_hex':snapshot.hex(),
             'inventory':{k:[0]*v for k,v in INVENTORY_SIZES.items()},
             'accessory_slots':[8,6,3,2], 'active_loadouts':{},
             'runtime_rows':[], 'runtime_row_meta':[], 'completed_runtime_rows':[]}
    state['inventory']['food'][0]=1
    state['inventory']['toy'][1]=1
    (Path(server.state_store_dir)/(key+'_state_v1.json')).write_text(json.dumps(state),encoding='utf-8')
    record_event(server,'login',f'{name} 접속',details={'key':key})
    record_event(server,'chat',f'{name}: 반갑습니다!',details={'key':key})
    record_event(server,'audit','테스트용 재화 지급',details={'key':key,'action':'update'})
control=ControlServer(server,port=0); assert control.start()
print(json.dumps({'port':control.httpd.server_address[1],'state_dir':server.state_store_dir}),flush=True)
while True: time.sleep(1)
