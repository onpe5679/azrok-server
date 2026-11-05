# 619 — 원격 multi-direct-loops 배포와 PatHouse INIT Reset 복구 (2026-08-31)

> **SUPERSEDED by 620.** 원격 runtime/cache 및 INIT reset 배포 사실은 보존하지만, INIT reset을 신규 생성 직행 실패의 해결 원인으로 귀속한 결론은 `S2C 0006` CreateEgg ACK same-process 실측으로 기각됐다.

## 결론

- **VERIFIED:** 로컬 기본 후보의 multi-direct-loops 런타임과 143-group AOT 캐시를 `playazrok.com` 운영 경로에 배포했다.
- **VERIFIED:** 첫 원격 신규 캐릭터는 서버가 PatHouse/date=0 계약을 정확히 보냈는데도 `SelectEgg` 픽셀 위에 HUD와 튜토리얼만 겹치는 혼합 화면을 보였다. 이 화면은 PatHouse 3D가 아니다.
- **VERIFIED:** fastboot4 guest DLL을 그대로 유지하고 host `COMMAND.INIT`에서 이전 `renderStates`를 비우고 COLORWRITE를 전 채널로 복구하자, 같은 브라우저 계정의 새 티켓 실행이 실제 PatHouse 3D 방으로 전환됐다.

## 원격 성능 후보 배포

배포 기본값:

| 구성 | 값 |
|---|---|
| runtime stem | `boxedwine.upstreamjit64fn6inlineabi2korean6chat1touch2multidirectloops1` |
| runtime JS SHA-256 | `b5135db7989b38b6d3e52c3420dd5f8028ea3a941927f7c12735d866d57c7954` |
| runtime Wasm SHA-256 | `e6f9ae4183358ec6145ffdd6e118454b3af9d454a1fed20113a77ec1cbace57f` |
| grouped cache | `azrok-jit-grouped-multidirectloops1-currentabi1-20260830.zip` |
| grouped cache SHA-256 | `03a322841ae2ff221aba793ab832318349deeb8a3d3a1db2bf5c3ce189a7dbb5` |

- **VERIFIED:** 원격 디스크와 공개 HTTPS 다운로드의 세 SHA-256이 각각 일치했다.
- **VERIFIED:** 캐시는 공개 경로에서 `206 Partial Content`, `Content-Range: bytes 0-1023/7146876`, immutable Cloudflare HIT를 반환했다.
- **VERIFIED:** 실제 공개 실행 로그는 `AZROK_JIT_REPLAY_REGISTERED groups=143 entries=44395 patches=33912`를 기록했다.
- **VERIFIED:** `azrok_server_list.html`의 launcher cache key를 `perf-multidirectloops1`로 올렸고, `sync_to_u32ws.ps1`은 새 runtime/cache와 구 Touch2/currentabi1 rollback 파일을 함께 보존한다.

## 첫 실행 혼합 화면의 직접 분리

첫 신규 캐릭터 세션에서 직접 본 화면은 보라색 `캐릭터 생성/선택` 배경 위에 baby BlueRon HUD, 퀘스트, 튜토리얼 말풍선이 겹친 상태였다.

같은 시점의 운영 core wire:

- **VERIFIED:** C2S `0x0004` character creation 수신.
- **VERIFIED:** S2C `0x0003`은 `Data\\Space\\PatHouse`를 보냈다.
- **VERIFIED:** 첫 S2C `0x0007`의 packed date와 stage는 0이었다.
- **VERIFIED:** 클라이언트는 이후 C2S `0x0011` runtime/tutorial rows와 `0x0012` quest reward를 보냈다.

따라서 서버가 잘못된 scene/date를 보낸 단순 회귀는 직접 기각한다. #599에서 확인됐지만 #600의 잘못된 fastboot5 롤백 때 함께 철회된 host D3D Reset 상태 수명 문제가 현재 증상과 일치했다.

## 최소 복구

수정 파일:

- `tools/boxedwine_local/web_backend/host/d3d9web-runtime.js`
- `tools/boxedwine_local/index_d3d9web_pathouse.html`

`COMMAND.INIT`에서 다음만 수행한다.

1. 이전 scene의 `renderStates` Map을 clear한다.
2. 현재 WebGL context에 `colorMask(true, true, true, true)`를 적용한다.
3. `D3D9WEB_INIT_STATE_RESET color_write=15 render_states=0` 마커를 남긴다.

fastboot4의 24,576-byte texture-recycle production `d3d9.dll`은 바꾸지 않았다. #600에서 E1242/INT99를 만든 23,040-byte 일반 build/fastboot5를 재도입하지 않았다. import-map URL은 immutable cache 우회를 위해 `bootsplash2-initreset2`로 승격했다.

공개 배포 SHA-256:

| 파일 | SHA-256 |
|---|---|
| `index_d3d9web_pathouse.html` | `662edc122e8bcf5d7303725bbf40a97d0fc98f381e9057994085030a33391a90` |
| `web_backend/host/d3d9web-runtime.js` | `538ad5d9b4bc4c8685457cc427ee60e05668066bd292d2a1720e3b89b8e3053a` |

## 실제 공개 브라우저 수락

- **VERIFIED:** 같은 브라우저 계정으로 새 account-bound ticket을 받아 fastboot4 + multi-direct-loops를 다시 실행했다.
- **VERIFIED:** 새 host URL에서 INIT reset 마커 3회, first Present, async ring `gaps=0 reorders=0 errors=0`을 확인했다.
- **VERIFIED:** 원본 캐릭터 선택에서 저장 캐릭터의 `접속` 버튼을 누른 뒤 카펫, 문, 화분, baby BlueRon, HUD, 퀘스트 패널이 보이는 실제 PatHouse 3D 방으로 전환됐다. 이전 `SelectEgg` 배경은 사라졌다.
- **VERIFIED:** 최종 host warning/error는 0건이었다.
- **VERIFIED:** 마지막 5개 120-Present 구간은 3435.935/2916.100/3108.570/2843.740/3240.925 ms로 약 34.92/41.15/38.60/42.20/37.03 FPS였다. 이는 수락 화면의 HUD 38.8 FPS와 일치한다. 정식 A-B 성능 재측정은 아니며 #618의 로컬 A-B-A-B 수치를 대체하지 않는다.

## 검증과 롤백

- **VERIFIED:** Node syntax 통과.
- **VERIFIED:** `tools.test_d3d9web_page_contract`, `tools.test_azrok_home_contract`, `tools.test_fastboot_account_app` 합계 44 tests 통과.
- **VERIFIED:** 전체 `tools/test_*.py` **302 tests 통과**.
- **VERIFIED:** 운영 `azrok-core`, `azrok-web`, `azrok-bridge`, `azrok-cloudflared`는 모두 active다.
- **VERIFIED:** 원격 덮어쓰기 전 백업은 `deploy_backups/20260830-234633-multidirectloops1` 및 `deploy_backups/20260830-235652-initreset2`에 보존했다.

## 경계

- **NOT VERIFIED:** 물리 모바일에서 동일 첫 캐릭터 생성부터 PatHouse까지의 픽셀 수락.
- **NOT VERIFIED:** host-only Reset이 모든 D3D9 Reset/scene 전환의 전체 상태 계약을 포괄한다는 일반화. 이번에 직접 확인한 것은 현재 fastboot4 신규/기존 캐릭터 PatHouse 경로다.
