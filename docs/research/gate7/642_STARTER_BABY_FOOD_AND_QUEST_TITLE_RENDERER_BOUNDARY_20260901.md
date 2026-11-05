# 642 — 신규 이유식 지급 수정과 퀘스트 제목 렌더러 경계

Date: 2026-09-01 KST

## 결과

- **VERIFIED / FIXED (신규 캐릭터):** 기본 지급 food slot을 1에서 0으로 바꿨다. `food[0]`은 item ID 1000 이유식이고, 기존 `food[1]`은 item ID 1001 햄버거였다. 첫 튜토리얼 `이유식을 먹여보자`와 이제 일치한다.
- **VERIFIED (회귀):** 기본 canonical state와 S2C `0x0007 + 0x0EA`가 이유식 1개, 다른 food slot은 0인지 계약 테스트로 확인했다. 구매 관련 기존 food[1] 기대값도 햄버거를 별도 구매했을 때의 값으로 교정했다.
- **VERIFIED (문자열 경계):** S2C `0x0007`은 quest row의 kind/aux/value만 전달하며 제목·본문 문자열은 클라이언트 `DAT_006dae98`와 로컬 quest renderer가 만든다. 같은 title 문구가 하단 본문에서 정상인 제보와 첨부 화면은 서버/CP949/quest 데이터 손상을 반증한다.
- **INFERRED / NOT FIXED YET (상단 제목 외곽 깨짐):** 상단 quest-list 전용 bitmapped anti-aliased glyph draw가 가장 유력하다. 현재 기본 앱은 256x256 R5G6B5 transient texture recycle을 켠 24,576-byte D3D9 bridge DLL이다. 다만 일반 23,040-byte recycle-off DLL은 #600에서 E1242/INT99 부팅 회귀를 직접 냈으므로, 그 DLL을 기본 경로에 교체하는 것은 금지한다.

## 이유식 원인과 수정

`SHOP_ITEM_INVENTORY_RANGES`는 음식 ID 1000..1032를 `food[index = item_id - 1000]`로 매핑한다.

| item ID | food slot | Azrok.dat 이름 | 이전/현재 starter 상태 |
|---:|---:|---|---|
| 1000 | 0 | 이유식 | **현재:** 지급 1개 |
| 1001 | 1 | 햄버거 | 이전에 잘못 지급, 현재 기본 지급에서는 0개 |

수정은 `SERVER_GRANTED_STARTER_ITEMS['food']`를 `(1,)`에서 `(0,)`으로 바꾼 한 항목이다. canonical state는 생성 시 이 값을 S2C `0x0007` inventory bytes에 overlay하므로, 새 캐릭터의 첫 식사 메뉴에 이유식이 나타난다.

기존 저장 캐릭터는 inventory를 보존하므로 자동으로 음식 종류를 바꾸지 않는다. 실제로 확인한 기존 `player/Azrok1` 저장은 food 전부 0이고 첫 튜토리얼 상태도 아니어서 소급 교정 대상이 아니다. 이미 가진 1001은 정상 구매품일 수 있으므로 일괄 치환하지 않는다.

## 제목 렌더러 조사

첨부 화면에서 상단 선택 행의 glyph 순서·문구는 유지되고, 하단 본문/동일한 한국어 문구는 정상이다. 따라서 UTF-8/CP949 변환 또는 quest title catalog 손상보다 AA texture와 sampler/blend/state lifetime 쪽이 우선이다.

현재 기본 page와 fastboot4 계열은 `D3D9WEB_TRANSIENT_TEXTURE_RECYCLE=1` guest DLL(SHA-256 `2de7d207...487194d9`)을 사용한다. 이 경로는 정확히 `256x256`, one-level, `R5G6B5`, 131072-byte transient texture handle을 Present 경계에서 재사용한다. upper quest list text가 이 scratch texture를 쓰는지는 아직 직접 trace하지 않았다.

### 안전한 다음 검증

1. 현재 rsdefaults1 app ZIP에서 `d3d9.dll` 하나만 plain DLL로 바꾼 immutable canary를 만든다. 기본 URL, r10 runtime/cache, 원래 ZIP은 변경하지 않는다.
2. fresh browser/character에서 first Present까지 도달하는지 먼저 확인한다. #600의 E1242/INT99가 재현되면 즉시 canary를 폐기하며 renderer 문제의 해결책으로 쓰지 않는다.
3. 부팅하면 같은 quest panel의 upper title을 screenshot A/B로 비교한다. 정상화할 때만 recycle path를 원인 후보로 승격한다.
4. 변화가 없거나 부팅 실패면 recycle-on trace build에서 해당 256x256 texture의 handle, sampler min/mag/mip, alpha blend/test, color-write state와 upper-title draw를 수집한다. 그 결과 없이 전역 anti-alias/sampler 기본값은 바꾸지 않는다.

## 근거와 검증

- `docs/research/content/71_azrok_dat_item_catalog_20260718.md` — ID 1000 이유식, 1001 햄버거의 direct Azrok.dat parse.
- `docs/research/gate7/600_FASTBOOT5_E1242_ROLLBACK_20260829.md` — generic recycle-off DLL의 boot regression 및 rollback.
- `azrok_server.py`, `tools/test_server_contract_layers.py` — starter slot 및 S2C byte contract.
- `py -3 -m unittest tools.test_server_contract_layers tools.test_content_builders` — **139 tests PASS** after the starter correction.
