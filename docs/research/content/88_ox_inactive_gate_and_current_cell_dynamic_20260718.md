# OX 비활성 게이트 + 0066 current-cell 동적 확정 (2026-07-18)

> **PARTIALLY SUPERSEDED by 92.** 0066 current-cell 실측은 유지됩니다. 다만 최종 cutoff/tie-break는 클라이언트 정적으로 복구할 수 없고, mode-2 CE가 정답 side를 전달하며 CB가 서버 판정 패자목록을 적용한다는 경계가 확정됐습니다.

87의 OX 이동 제출 정적 계약을 실제 OX 비활성 화면과 기존 Plaza wire 캡처로 좁힌 기록입니다.
VERIFIED=화면/wire/x32dbg 직접 실측, INFERRED=OX 활성 문제에서 재실측 전 정책,
NOT VERIFIED=추가 동적 A/B가 필요한 항목입니다.

## 1. 안전 범위와 세션

- 주 클라이언트 PID `33132`는 Plaza `scene=110/phase=4`, dispatch mode 1, heartbeat 정상으로 보존했습니다.
- 보조 PID `75680`만 OX 관찰 대상으로 사용했습니다. 관찰 전 화면은 이미 `OX지존` 맵이었으므로
  새 `S→C 006E`는 보내지 않았습니다.
- Frida는 사용하지 않았고 x32dbg만 부착했습니다.
- 입력은 보조 창의 바닥 한 점 `rel=(0.25,0.55)`, screen `(262,451)` 한 번뿐입니다.

## 2. OX 비활성 화면의 이동 게이트 (VERIFIED live)

관찰 로그 `artifacts/dynamic-analysis/x32dbg_ox_pid75680_20260718_0854.jsonl`:

- `00613C60`은 클릭 전에도 실행되는 약 5 Hz 프레임 경계였습니다. 180초 동안 `301`회 hit했습니다.
- 클릭 뒤에도 `0061B510`, `005AB7B0`, C→S `0066`, C→S `0067`은 **0회**였습니다.
- 서버 entity3의 `0066/0067` 카운트와 좌표 `(3963,195)`도 변하지 않았습니다.

따라서 현재 질문/판정이 없는 OX 화면에서는 world input frame이 실행되어도 route/answer movement까지
통과하지 않습니다. 실패는 입력 누락이 아니라 **phase gate가 `0061B510` 이전에 닫힌 직접 증거**입니다.

`00613C60` 일반 breakpoint는 저온 관찰점이 아닙니다. 브레이크/재개 반복이 프레임 타이밍을 교란해
observer timeout/detach 뒤 보조 heartbeat가 회복되지 않았습니다. 보조만 PID+start-time 고정 요청으로 닫고
빈 x32dbg를 종료했으며, 주 클라이언트/서버는 `1 client`, `plaza_healthy`, heartbeat 정상으로 유지했습니다.
후속 `ox` 프로필에서는 `00613C60`을 제외했습니다.

증거:

- `artifacts/dynamic-analysis/ox_inactive_click_pid75680_20260718_0856.txt`
- `artifacts/dynamic-analysis/x32dbg_ox_pid75680_20260718_0854.jsonl`
- `artifacts/dynamic-analysis/close_stalled_ox_secondary_pid75680_20260718.txt`

## 3. C→S 0066 첫 바이트는 current cell (VERIFIED wire)

87의 레이아웃을 기존 실제 Plaza 이동 캡처 두 개에서 전수 대조했습니다.

| 캡처 | 0066 수 | byte0 == cell(curX,curY) | byte0 == cell(dstX,dstY) | cur/dst cell 다름 |
|---|---:|---:|---:|---:|
| `packets_20260717_080648.txt` | 6 | **6/6** | 3/6 | 3 |
| `packets_20260717_081659.txt` | 108 | **108/108** | 83/108 | 25 |
| 합계 | 114 | **114/114** | 86/114 | 28 |

셀 공식은 정적 계약과 같은
`cell=((y+9000)/3000)+((x+9000)/3000)*6`입니다.

직접 불일치 예:

```text
0066 1b 7b0f0000 c3000000 390c0000 13ffffff ... 00
byte0=27, cur=(3963,195)→cell27, dst=(3129,-237)→cell26
```

```text
0066 1a e30d0000 efffffff e8090000 73000000 ... 00
byte0=26, cur=(3555,-17)→cell26, dst=(2536,115)→cell21
```

그러므로 `0066`의 첫 바이트는 destination/answer cell이 아니라 **송신 당시 current cell**입니다.
목적지는 별도 `dstX/dstY`이며 이동 중에는 다른 셀일 수 있습니다. `0067`은 도착/current-position commit입니다.

## 4. 서버 판정 계약

- VERIFIED: `0066.byte0`과 `curX/curY`는 같은 current-cell snapshot입니다.
- VERIFIED: 클릭 목적지 셀을 즉시 답으로 확정하면 이동 중 28/114 표본에서 실제 위치와 어긋납니다.
- INFERRED: OX 마감 판정은 서버가 마지막으로 수신한 current cell을 사용하고, `0067` 도착이 오면 그 좌표를
  최신 권위 위치로 승격해야 합니다. 활성 문제에서 같은 좌표 A/B 전까지 원본 마감 timestamp는 미확정입니다.
- NOT VERIFIED: O side/X side의 정확한 cell 집합. 성공 `006E` OX 진입 캡처들은 비활성 대기만 포함해
  C→S `0066/0067`이 0건이었습니다.

따라서 구현은 목적지 선확정이 아니라 current/arrival 기반으로 유지하고, O/X cell mapping은 fail-closed 또는
설정 가능 테이블로 남겨야 합니다.

Related: 75, 84, 86, 87, world/29, world/30.
