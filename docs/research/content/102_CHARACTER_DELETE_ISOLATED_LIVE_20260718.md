# 102 — 캐릭터 삭제 격리 라이브 검증 (2026-07-18)

## 범위와 안전 경계

- **VERIFIED**: 실제 주 플레이 데이터는 `server_state/profile_playable_v2`이며, 이 트랙은 slot 0 `Azrok1`을 삭제 대상으로 사용하지 않습니다.
- **VERIFIED**: 라이브 조작 전 주 프로필 3개 파일의 SHA-256 기준선을 확보했습니다. canonical `a706c61796572_s0_c417a726f6b31_state_v1.json`은 `D190456272D19D182FB9AA69F405373C31C13393F24A706FF190E71B35B0E31F`/3279B입니다.
- **VERIFIED (live/API/filesystem)**: clean restart API가 `content_profile=minimal`, `state_namespace=profile_minimal`, `state_store_dir=.../server_state/profile_minimal`, roster count 0을 동시에 보고했습니다. 주 프로필 SHA 3개는 전·중·후 모두 불변이었습니다.

## 서버 계약 직접 검증

- **VERIFIED (code)**: C2S `0x0006 [logical_slot:u8]`은 dense 로비의 마지막 슬롯만 허용합니다. logical slot은 로비 record의 `storage_slot`으로 변환한 뒤 account+storage-slot+character-name canonical/raw/legacy 파일을 `deleted/`로 archive합니다.
- **VERIFIED (code)**: S2C `0x0008 [slot,result]`에서 `result=0`은 archive 성공, `result=1`은 malformed/non-tail/missing-state/archive-failure 거부입니다.
- **VERIFIED (test)**: archive 두 번째 `os.replace` 실패를 주입하면 이미 옮긴 첫 파일을 원위치하고 `0008 00 01`을 반환합니다. 원본 두 파일이 모두 남습니다.
- **VERIFIED (new regression)**: 임시 디렉터리에서 `DeleteMe` 생성 → 새 서버 로비 count 1/name 복원 → 삭제 `0008 00 00` → canonical이 `deleted/`로 이동 → 또 새 서버 로비 count 0/slot sentinel `FF FF FF FF`를 직접 확인했습니다.
- **VERIFIED**: `python -m unittest discover -s tools -p 'test_*.py' -q` 결과 전체 **91 tests OK**입니다.

## 격리 live wire/UI 결과

- **VERIFIED (live TCP)**: 빈 격리 서버에 실제 framing으로 login→heartbeat 뒤 C2S `0004` payload `00 44656c313032 00... 00`을 보냈습니다. 서버는 S2C `0003/0007/0005/000A/000B`를 반환했고 `a706c61796572_s0_c44656c313032_state_v1.json` 3013B, SHA `6040C62D4654A4E56C5CA85B6C2C72B8FC4F04004A8CBE916F5F7464DC8E01E8`을 만들었습니다.
- **VERIFIED (original client UI)**: `profile_minimal` clean reconnect 뒤 실제 캐릭터 선택 화면에 slot0 `Del102 / 레벨 0 / 블루론`이 렌더되었습니다. API roster는 logical slot0→storage slot0→위 canonical 경로를 가리켰습니다.
- **VERIFIED (live wire)**: 같은 격리 계정의 새 TCP 세션에서 lobby count1/name `Del102`를 받은 다음 C2S `0006 00`을 보냈습니다. capture seq17은 C2S `0006` 1B `00`, seq18은 S2C `0008` 2B `00 00`입니다.
- **VERIFIED (archive)**: active `profile_minimal` 루트에는 파일이 0개가 되었고, `deleted/a706c61796572_s0_c44656c313032_state_v1.json.20260718_115014`가 3013B/동일 SHA로 존재합니다.
- **VERIFIED (original client reconnect)**: 삭제 후 clean reconnect API는 `account_has_characters=false`, roster 0을 보고했고 원본 클라이언트 화면은 빈 `캐릭터 생성` 화면으로 돌아갔습니다.
- **VERIFIED (main restore)**: 마지막에 `playable/profile_playable_v2`로 clean restore했습니다. API roster는 slot0/storage0 `Azrok1`, species2, level26, evolution1이고 실제 로비 UI도 `Azrok1 / 레벨 26 / 레드론`을 렌더했습니다. 검증된 elevated slot0 선택 뒤 PatHouse를 거쳐 S2C000D 한 번으로 최종 PID `109432` Plaza `room27/scene110/phase4/mode1/self1`, heartbeat recent, saved-state loaded, currency950, unknown0까지 복구했습니다.
- **VERIFIED (main integrity)**: 주 프로필 최종 SHA는 각각 `875390...817E`, `821D08...2940`, canonical `D1904562...E31F`로 기준선과 모두 같습니다.
- **VERIFIED (cleanup)**: `REQUEST_*` marker는 최종 0개입니다. elevated 복구 클릭 로그는 `artifacts/dynamic-analysis/deletion_recovery_slot0_elevated_click_20260718.txt`입니다.
- **VERIFIED (evidence)**: 통합 증거는 `artifacts/dynamic-analysis/character_delete_isolated_live_evidence_20260718.json`에 고정했습니다.

## 결론

캐릭터 생성→로비 복원→삭제 ack→보존 archive→빈 로비 재접속의 서버 계약은 정적·회귀·live wire·원본 클라이언트 UI가 모두 수렴했습니다. 주 `Azrok1`은 삭제 대상으로 사용되지 않았고 파일 단위 무결성이 유지됐으며, 마지막 런타임도 Plaza healthy로 복구했습니다.
