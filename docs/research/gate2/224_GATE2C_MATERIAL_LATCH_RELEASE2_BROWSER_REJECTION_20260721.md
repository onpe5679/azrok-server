# 224 — material-latch release 2 브라우저 기각

## 결론

- **VERIFIED:** `BOXEDWINE_D3D9WEB_MATERIAL_LATCH_AOT`의 두 번째 브라우저 릴리스는 1024×768 PatHouse 화면과 네트워크 진행을 보존했습니다.
- **VERIFIED:** 55.249초, 1,817 Present의 가중 평균은 **32.887 FPS**였고, 문서 212의 counter-free 기준 **33.842 FPS**보다 **2.821% 낮았습니다**.
- **VERIFIED:** 이 단일 `0x1008E0A0` 래치 helper는 기본 릴리스에 채택하지 않습니다. 현재 기본은 계속 `boxedwine.hotaotrelease2`이며 material-latch 매크로가 꺼진 상태입니다.
- **INFERRED:** 모든 디스패치마다 추가되는 주소 비교와 helper/코드·MMU 경계 비용, 그리고 이 계열의 제한된 전체 프레임 비중이 네이티브 국소 이득을 상쇄한 것으로 보입니다.
- **VERIFIED NEXT GATE:** 같은 횟수로 관측된 `0x1008E05E`의 더 큰 쓰기 포함 scan body를 정적·동적 차등 검증한 뒤에만 다음 브라우저 A/B를 허용합니다.

## 산출물 식별

- HTML 선택자: `?materiallatchv2=1`
- JS SHA-256: `27CA8E486FF6A464CEE1489C70FA76A099B8552C45B1A0875E62391F49837714`
- WASM SHA-256: `AC67039B58148AA593D15F025F7F504EE99FAA0AB8ABEEBFE1D689AE0B441BBE`

## 브라우저 실측

| 구간 | FPS |
|---:|---:|
| 5초 1 | 31.187922 |
| 5초 2 | 33.008550 |
| 5초 3 | 33.844316 |
| 5초 4 | 33.412888 |
| 5초 5 | 33.233831 |
| 10초 1 | 32.576210 |
| 10초 2 | 33.273560 |
| 10초 3 | 32.688858 |

- **VERIFIED:** 5초 창 산술 평균 32.937501 FPS.
- **VERIFIED:** 같은 세션 10초 창 산술 평균 32.846210 FPS.
- **VERIFIED:** 전체 가중 평균 1,817 Present / 55.249초 = **32.887473 FPS**.
- **VERIFIED:** 기준 대비 변화율은 **-2.8205%**입니다.
- **VERIFIED:** 카펫 밉맵, 벽, 식탁·의자, 캐릭터를 포함한 기준 PatHouse 화면을 보존했습니다.
- **VERIFIED:** 측정 뒤 탭을 닫았고 bridge는 `WS_CLOSED`를 기록했습니다. 병렬 게임 인스턴스는 남기지 않았습니다.

## 다음 구현 조건

문서 223의 3.5배는 이미 디코드된 네이티브 블록과 helper 호출만 비교한 국소 비용입니다. 이번 결과로 실제 브라우저 프레임 시간 이득은 부정됐습니다. 같은 크기의 단일 블록 추가는 중단합니다.

`0x1008E05E` 후보는 guest write를 포함하므로 exact bytes와 successor를 고정하고, 읽기·쓰기 실패 시 CPU와 memory가 모두 무변경인 transactional side exit을 구현해야 합니다. relocated interpreter와 helper의 전체 상태·메모리 차등 fixture 및 production 경로 microbenchmark가 충분한 이득을 보인 뒤에만 브라우저를 한 번 실행합니다.
