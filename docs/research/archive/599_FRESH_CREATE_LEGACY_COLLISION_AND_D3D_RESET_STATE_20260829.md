> **PARTIALLY SUPERSEDED by 600.** 신규 create의 name-only legacy 차단은 유지된다.
> fastboot5/D3D Reset 배포와 그 검증 주장은 E1242/INT99 운영 회귀로 기각되어
> fastboot4로 롤백됐다.

# 599 — 신규 캐릭터 legacy 충돌과 D3D Reset 상태 복구 (2026-08-29)

## 증상

신규 사용자가 첫 캐릭터를 만든 뒤 PatHouse의 3D가 정상 표시되지 않는다는 재발
제보를 받았다. 모바일/데스크톱 귀속은 제보만으로 확정하지 않았다.

## VERIFIED — 운영 일반 신규 경로

- 2026-08-29 15:38 운영 신규 캐릭터 `testncc`는 S2C `0003 PatHouse`와
  `0007/0005/000A/000B`를 받았다.
- 그 `0007 +0x03` packed date는 0이고 stage도 0이었다. 약 0.4초 뒤 원본
  클라이언트가 C2S `0011 kind=5/aux=212`를 보냈다.
- 따라서 모든 신규 캐릭터에서 date=0이 사라진 단순 회귀는 아니었다.

## VERIFIED — 이름 전역 legacy snapshot의 계정 경계 침범

- 신규 생성은 account+slot+name canonical을 먼저 저장하지만 그 문서의
  `snapshot_hex`는 아직 `None`이다.
- 같은 응답의 첫 `0007` 빌더가 저장 snapshot을 찾을 때 account-scoped raw가
  없으면 과거 name-only `<namehex>_c2s0007.bin`을 fallback으로 읽었다.
- 운영 state에는 `Azrok1`과 `Player`의 name-only stage-1 snapshot이 실제 남아
  있었다. 새 account가 `Azrok1`을 만들면 다른 계정의 stage 1/stat을 이식하고
  `0007 +0x03`을 현재 날짜로 바꾸는 것을 로컬 full create flow로 재현했다.
- 신규 C2S `0004` 트랜잭션의 첫 `0007`에서는 모든 persisted snapshot import를
  금지했다. 기존 캐릭터의 의도된 1회 legacy migration은 유지한다.
- `Azrok1` 충돌 회귀 테스트는 수정 후 date=0, stage=0,
  `legacy_state_import_suppressed=True`를 확인한다.

## VERIFIED — D3D Reset의 stale COLORWRITE 방어

- guest `Device_Reset`은 host cache set flag만 무효화하고 render-state 숫자를
  보존했으며, host `COMMAND.INIT`도 이전 장면의 `renderStates` Map을 지우지
  않았다. 이는 #536에서 이미 확정된 수명 불일치다.
- guest Reset에서 `SeedDefaultRenderStates()`를 다시 적용하고, host INIT에서
  Map을 clear한 뒤 `gl.colorMask(true,true,true,true)`를 복구한다.
- 새 immutable app `fastboot5`에 재빌드된 `d3d9.dll`을 넣었다. app SHA-256은
  `22705cfadf7ce25f0bde4a3426e1ee5d1bf3fbe36b51e03057e836f51b5eeb76`이다.
- host module URL을 `bootsplash2&initreset1`로 승격해 모바일/데스크톱의 기존
  immutable cache가 새 host 코드를 받도록 했다.

## VERIFIED — 재진입 route와 운영 배포

- 로그아웃 뒤 캐릭터 선택 재진입 함수가 운영에 없는 base `startersplash1`을
  가리키던 404 경로를 fastboot5/root/runtime/JIT 현재 조합으로 고쳤다.
- 전체 `tools/test_*.py` 297개가 통과했다.
- 접속자 0명에서 u32ws를 동기화하고 `azrok-core`/`azrok-web`만 재기동했다.
  core/web/bridge/cloudflared 네 서비스는 모두 active이고 재기동 뒤 warning 0건이다.
- 공개 홈페이지 200, 상태 API `ok=true`, fastboot5 Range 206, 공개 HTML의
  fastboot5/initreset1, 공개 host runtime의 Map/colorMask reset 본문을 확인했다.
- 로컬과 운영의 server/runtime/page/launcher/app SHA-256이 모두 일치한다.

## NOT VERIFIED

- 제보가 나온 정확한 모바일 또는 데스크톱 브라우저에서 캐시 갱신 뒤 첫 캐릭터
  PatHouse 3D 픽셀의 최종 사용자 수용.
- 그 제보 세션의 실제 캐릭터 이름이 `Azrok1`/`Player` 계열 legacy 충돌이었는지,
  또는 D3D Reset stale state였는지의 단일 원인 귀속. 두 결함은 각각 직접 재현
  또는 코드 경로로 확정되어 함께 수정했다.
