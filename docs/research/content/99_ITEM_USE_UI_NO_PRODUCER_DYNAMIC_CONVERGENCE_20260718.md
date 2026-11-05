# 아이템 사용 UI 무생성 경로 동적 수렴 (2026-07-18)

관련 문서: 90, 91, 98. 원본 서비스나 외부 서버에는 접속하지 않았으며, `profile_playable_v2` 로컬 서버와 정당하게 보유한 클라이언트만 사용했습니다.

표기: **VERIFIED**=패킷·API·저장 파일·화면 직접 확인, **INFERRED**=확정 현상에 대한 최소 해석, **NOT VERIFIED**=후속 격리 실행이 필요한 항목.

## 1. 결론

- **VERIFIED (dynamic)** Plaza의 일반 인벤토리 UI 관찰 구간에서 C→S `000D/000E/000F`와 S→C `0009`는 한 건도 발생하지 않았습니다.
- **VERIFIED (static, 98)** toy/gym 인벤토리 탭에는 C→S `000D/000E` producer가 없습니다. sender body는 존재하지만 shipped 클라이언트의 direct caller 전수에서 full-width toy/gym ID를 넣을 수 있는 producer가 없어 dormant/future-compatible 경로입니다.
- **VERIFIED (static, 98)** 실제 UI producer는 furniture commit과 energy 선택 경로뿐입니다. energy는 소유 수량과 추가 gate를 통과해야 하며, 이번 canonical energy 수량은 전부 0이므로 UI 소비를 시도하지 않았습니다.
- 따라서 91에서 장난감 슬롯 클릭 뒤 패킷이 없었던 현상은 실패가 아니라 원본 호출 그래프와 일치하는 정상 결과입니다. toy/gym UI를 더 클릭해도 `000D/000E`를 얻을 수 있다는 가설은 폐기합니다.

## 2. 시작 체크포인트

**VERIFIED** 실행 기준선은 다음과 같습니다.

| 항목 | 값 |
|---|---|
| client | PID `65612`, entity `2`, `Azrok1` |
| server/control | TCP `9207` / HTTP `9300` |
| room | kind 27, `plaza (0064-only)` |
| health | scene110 / phase4 / mode1 / self1 / heartbeat recent |
| unknown C2S | 0 |
| canonical | `server_state/profile_playable_v2/a706c61796572_s0_c417a726f6b31_state_v1.json` |
| canonical SHA-256 | `D190456272D19D182FB9AA69F405373C31C13393F24A706FF190E71B35B0E31F` |
| canonical length | 3279B |
| slot / species / currency | 0 / 2 / 950 |
| energy quantities | 20칸 모두 0 |
| content save count | 0 |

OX는 재진입하지 않았고 S→C `0007` synthetic setup도 주 캐릭터에 주입하지 않았습니다.

## 3. 제한된 UI 관찰과 즉시 중단

docs91의 기존 실측 화면과 좌표를 먼저 확인했습니다. 당시 실제 경로는 `메뉴 → 내가방 → 장난감`이었고, 기본 소유로 보이는 슬롯 하나를 선택했지만 `000D/000E/000F`는 0건이었습니다.

이번 실행에서는 Plaza 화면에서 하단 toolbar와 메뉴 위치만 비파괴적으로 확인했습니다. 정적 담당이 direct xref를 thunk까지 완주해 아래를 정정한 즉시 추가 입력을 중단했습니다.

1. `FUN_005BBC00`은 toy/gym commit이 아니라 furniture 전용입니다.
2. `FUN_005BC970`은 energy `5000..5002` 선택 경로이며 보유 수량·pending·시간비율 등의 gate가 있습니다.
3. `HandleS2C_0007_LoadSetupBlob@0059E330`의 `+0x125..12F`는 11×u8 absolute item-ID command입니다. `0..255`만 표현하므로 furniture 또는 nop만 가능하고 toy `2000+`/gym `2500+`/energy `5000+`는 이 경로에서도 도달하지 않습니다.

**VERIFIED** 이 정정 뒤 추가 클릭은 0회입니다. energy 0 상태에서 소비를 강제하지 않았고, 임의 파일 rollback이나 main 저장 재주입도 하지 않았습니다.

## 4. 패킷 구간

`captures/packets_20260718_110829.txt`의 seq254..323, 총 70프레임을 직접 분류했습니다.

| 방향/opcode | 건수 |
|---|---:|
| C→S `0016` | 35 |
| S→C `0016` | 35 |
| C→S `000D` | 0 |
| C→S `000E` | 0 |
| C→S `000F` | 0 |
| S→C `0009` | 0 |
| heartbeat 외 프레임 | 0 |

**VERIFIED** item-use 또는 다른 상태 변경 프레임은 없었습니다. `unknown_c2s_count`도 0을 유지했습니다.

## 5. 종료 체크포인트

- canonical SHA-256/길이: 시작과 동일
- slot0 `Azrok1`, species2, currency950: 동일
- energy 20칸: 모두 0 유지
- content save count: 0 유지
- 최종 상태: room27, scene110, phase4, mode1, self1, heartbeat 정상

즉, bounded UI 관찰은 저장·통화·인벤토리·Plaza 상태를 손상시키지 않았습니다.

## 6. 동적 검증 계약 (§7에서 완료)

- 권장 비파괴 절차는 fresh reconnect에서 정상 S→C `0007`을 한 번 받고 `+0x125..12F=FF×11`, toy/gym quantity array 정상, setup 직후 C→S `000D/E` 0건, canonical/Plaza 불변을 확인하는 음성 대조이며 §7에서 완료했습니다.
- **NOT VERIFIED** dormant toy/gym sender body의 ABI 양성 대조가 정말 필요하면 disposable client/profile에서 ownership을 갖춘 뒤 `DomainCode_EmitLocalEffect`에 full-width `2001` 또는 `2500`을 직접 한 번 호출해야 합니다. 이는 자연 UI 경로가 아니므로 메인 사용자 저장에서는 수행하지 않습니다.
- 이때 검증 항목은 C→S exact length/payload, 서버 active loadout 반영, canonical 무소비와 격리 상태 복원입니다.
- energy `000F→0009[00 0F]`는 정당한 구매/보상으로 energy를 1개 이상 보유한 격리 프로필에서만 수행합니다.

## 7. 최신 코드 clean reconnect 음성 대조

98의 정정과 effect-byte truncate 방지 회귀가 들어간 최신 서버를 실제 런타임에 올리기 위해 clean restart했습니다.

- **VERIFIED** one-shot `REQUEST_CONTENT_PROFILE=playable`이 소비됐고 새 runtime은 PID `77524`, TCP/control `9207/9300`, namespace `profile_playable_v2`였습니다.
- **VERIFIED** 실제 로비 slot0 `Azrok1`을 선택해 C→S `0005[00]`과 정상 zone bundle을 받았습니다.
- **VERIFIED** S→C `0007` seq52는 exact 472B였고 `+0x125..12F`가 `FF FF FF FF FF FF FF FF FF FF FF`였습니다.
- **VERIFIED** 같은 raw에서 toy `+0x113..11C = 00 01 00 00 01 00 00 01 00 00`, gym `+0x11D..124 = 01 00 00 01 00 00 01 00`, energy `+0xC7..DA = 20×00`, evolution1, currency950을 직접 디코드했습니다.
- **VERIFIED** zone load seq52부터 Plaza healthy seq98까지 C→S `000D/000E/000F`와 S→C `0009`는 모두 0건이었습니다.
- **VERIFIED** single S→C `000D[00]` transition 뒤 room27, scene110, phase4, mode1, self1, heartbeat 정상, unknown0으로 Plaza healthy를 완주했습니다.
- **VERIFIED** canonical SHA `D1904562...B0E31F`, 3279B, slot0, species2, currency950, energy all-zero, content-save0은 restart 전후 불변입니다.

ABI direct call, item UI click, OX 재진입, synthetic S→C `0007`은 수행하지 않았습니다. 이 음성 대조로 shipped fresh load에서 `FF×11 → natural 000D/E 무발생`이 정적 callgraph와 실제 wire 양쪽에서 확정됐습니다.

## 8. 증거

- `artifacts/dynamic-analysis/item_use_ui_no_producer_checkpoint_evidence_20260718.json`
- `artifacts/dynamic-analysis/item_use_ui_stopped_plaza_20260718.bmp`
- `artifacts/dynamic-analysis/item_reconnect_ff11_negative_evidence_20260718.json`
- `artifacts/dynamic-analysis/item_reconnect_ff11_plaza_healthy_20260718.bmp`
- `artifacts/dynamic-analysis/item_reconnect_slot0_elevated_click_20260718.txt`
- 기존 실제 인벤토리 화면: `artifacts/dynamic-analysis/latest_item_ui_myroom_20260718.bmp`
- 기존 실제 toy 탭: `artifacts/dynamic-analysis/latest_item_ui_toy_tab_20260718.bmp`
- wire 원문: `captures/packets_20260718_110829.txt`

최종 판정: **VERIFIED dynamic/static convergence**. Plaza 일반 toy/gym UI에서 item-use 패킷이 발생하지 않는 것은 원본 producer reachability와 일치합니다. 후속은 UI 반복 클릭이 아니라 격리된 S→C `0007` setup-response 실측으로 전환합니다.
