# 233 — `0x8E05E` material-scan 브라우저 릴리스 기각

## 결론

- **VERIFIED:** release 1은 1024×768 D3D viewport의 PatHouse 기준 화면을 보존했습니다. 카펫 밉맵, 벽, 식탁·의자, 캐릭터가 기준과 동일하며 콘솔 error/warn은 없었습니다.
- **VERIFIED:** 같은 세션의 8개 측정 창은 합계 1,785 Present / 55.055초 = **32.422 FPS**였습니다.
- **VERIFIED:** 문서 212의 counter-free 기준 33.842 FPS보다 **4.196% 낮으므로 기각**합니다. 기본 자산은 계속 `boxedwine.hotaotrelease2`입니다.
- **VERIFIED:** 네이티브 한 반복 3.538배 개선은 브라우저 전체 프레임 시간으로 전이되지 않았습니다.
- **INFERRED:** 동일한 주소 비교 기반으로 더 작은 exact block을 추가하는 방식은 50 FPS 목표의 유효한 레버가 아닙니다. 다음 측정은 실제 guest interpreter의 시간 기반 함수/블록 비중과 dispatcher·decode·memory 비용을 분리해야 합니다.

## 릴리스 식별

- selector: `?materialscan=1`
- build directory: `Build/RunMaterialScanRelease1`
- JS SHA-256: `4948EBA222BA8F8772A7CFAB3E66853034D25A4ACF929E69E2079B1C45F292F8`
- WASM SHA-256: `B472489429F8AFABAF8925E50C78138F99D0BAD88D51FF12EEE0AD64818A8508`
- **VERIFIED:** build 원본과 배포본 해시가 일치했고 기존 `boxedwine.hotaotrelease2.js/.wasm`은 덮어쓰지 않았습니다.

## 브라우저 측정

| 창 | frames | ms | FPS |
|---:|---:|---:|---:|
| 5초 1 | 166 | 5000 | 33.200 |
| 5초 2 | 158 | 5014 | 31.512 |
| 5초 3 | 159 | 5001 | 31.794 |
| 5초 4 | 167 | 5016 | 33.293 |
| 5초 5 | 156 | 5007 | 31.156 |
| 10초 1 | 327 | 10007 | 32.677 |
| 10초 2 | 329 | 10006 | 32.880 |
| 10초 3 | 323 | 10004 | 32.287 |

- **VERIFIED:** 가중 합계 1,785 / 55.055초 = **32.422123 FPS**.
- **VERIFIED:** 기준 33.842 FPS 대비 **-4.1956%**.

## 실행 무결성

- **VERIFIED:** heartbeat 지연 자동 선택 경로만 사용해 PatHouse에 진입했고 사용자 클릭은 없었습니다.
- **VERIFIED:** 최종 `dpupCount=210938`, loop marker `4928512:13070:10:180`까지 렌더가 지속됐습니다.
- **VERIFIED:** bridge는 종료 직전까지 heartbeat를 양방향 전달했고 탭 종료 시 `WS_CLOSED`를 기록했습니다.
- **VERIFIED:** 테스트 탭을 닫았으며 9200/9201 established 연결은 남지 않았습니다.

## 다음 게이트

단일 래치 기각(224)보다 큰 fused trace에서도 같은 패턴이 재현됐습니다. 새 helper 구현 전에 하나의 공통 wall-time 프로파일로 guest NormalCPU, 전역 dispatcher, decode/getNextOp, soft-MMU, x87/SSE, D3D command 생성, guest→host 복사를 분리합니다. 한 프레임 내 top 함수/trace의 exclusive wall-time과 호출 수도 같은 시간축으로 측정합니다. 이 측정 없이 더 많은 exact-entry helper를 추가하지 않습니다.
