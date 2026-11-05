# Playroom 직접 진입·3종 완주와 C2S 0065 방 매핑 교정 (2026-07-18)

상태 표기: **VERIFIED** = 디컴파일 또는 실제 클라이언트/패킷 실측,
**INFERRED** = 직접 증거 조합, **NOT VERIFIED** = 후속 동적 확인 필요.

## 결론

- **VERIFIED:** Plaza portal selector `1`의 원본 commit을 직접 queue하면
  `playroom.wmb`, 클라이언트 `scene=0x65 / phase=2 / mode=0`이 로드된다.
- **VERIFIED:** 자연 C→S `0x0065`는
  `06 07 4E F1 FF FF B0 F0 FF FF`이며 `<BBii>`로
  `kind=6, direction=7, x=-3762, y=-3920`이다. descriptor entry와 정확히 같다.
- **VERIFIED:** 서버의 기존 `kind6=library` 및 `<BBII>` 해석은 모두 틀렸다.
  정확한 값은 `kind6=playroom`과 signed 좌표다.
- **VERIFIED:** 원본 Playroom 선택 링의 저글링·재주넘기·요요를 모두 완료했고
  각각 196바이트 C→S `0x0007`이 발생했다. 최종 stat34/35/36은 `5/4/5`다.
- **VERIFIED:** Playroom 나가기 `0x1A9`는 scene request `0x6E`를 만들고,
  S→C `0x000D[00]` calibration 뒤 건강한 Plaza로 복귀한다.

## 1. 직접 portal 전환과 signed wire

generic 도구는 이름 `playroom`을 hard-coded selector `1`로만 변환한다. 호출은
`FUN_006142C0(PortalMgr,1)`에서 pending selector만 기록하고 즉시 detach한다.
다음 native tick이 원본 `FUN_00611CD0→FUN_006122C0` 경로를 실행했다.

```text
client scene/phase/mode = 0x65 / 2 / 0
C→S 0x0065 payload      = 06074ef1ffffb0f0ffff
decoded                 = kind 6, dir 7, x -3762, y -3920
process                 = PID 80208, Responding=True, helper residue 없음
```

화면에는 공·책·광대·부메랑 오브젝트와 “여기는 놀이를 배우는 곳이지” 원본
안내가 렌더됐다. 진입만으로 C→S `0x0007` 저장은 발생하지 않았다.

## 2. 서버 room kind/좌표 오류와 수정

`FUN_006122C0`의 selector→wire kind는 동일 숫자가 아니다. 현행 일반 portal
계약은 다음과 같다.

| wire kind | room | portal selector |
|---:|---|---:|
| 1 | pathouse | 0 |
| 6 | playroom | 1 |
| 8 | gym | 2 |
| 9 | magic | 3 |
| 7 | cook | 4 |
| 11 | shop | 5 |
| 10 | library | 6 |
| 12 | ground | 10 |

수정 전 실행 서버는 Playroom frame을 `room_kind=6 / library`로 표시하고 음수
좌표를 `4294963534,4294963376`으로 표시했다. 코드는 다음과 같이 교정했다.

- C→S `0x0065`: `<BBii>` 전용 decoder 및 위 8종 exact map.
- C→S `0x0066`: `<Biiii>`로 두 좌표쌍 signed 처리.
- C→S `0x0067`: `<BiiIH>`로 x/y만 signed, action/angle은 unsigned 유지.
- PatHouse 집계: bootstrap sentinel `-1`과 실제 wire kind `1`을 모두 인정.
- `azrok_control.py`의 중복 packet glossary도 같은 map으로 교정.

`tools/test_server_room_mapping.py`를 추가했고 전체 관련 suite는 23 tests OK다.
이 실행 중 서버 프로세스는 수정 전 코드이므로 새 map의 **재시작 live 활성화는
NOT VERIFIED**다.

## 3. Playroom 원본 UI와 3종 결과

정적 원본 이벤트와 정확한 소비 caller는 다음과 같다.

```text
ButtonQueue_Pop return = 0x005DD8B4
0x65 = 저글링
0x66 = 재주넘기
0x67 = 요요
0x1A9 = 나가기
```

입장 안내 feather는 Frida 가상 클릭으로 닫히지 않았지만 elevated real UI click
한 번으로 닫혀 고정 선택 링이 열렸다. 그 뒤 이벤트를 위 caller에만 한정해
직접 전달했다.

| 순서 | 활동 | target stat | 결과 | 봉에너지 | C→S 0007/save |
|---:|---|---:|---:|---:|---:|
| 1 | 저글링 | 34 | `0→5` | `25→20` | count `3→4`, sum 38 |
| 2 | 재주넘기 | 36 | `0→5` | `20→15` | count `4→5`, sum 43 |
| 3 | 요요 | 35 | `0→4` | `15→10` | count `5→6`, sum 47 |

최종 공통 값은 `(stat3,4,5,6,7,9)=(0,9,30,100,0,10)`, Gym은
`(7,21,5)`, Playroom은 `(5,4,5)`다. 요요 `+4`는 실행 직전 stat3/stat5
tier를 넣은 정적 보상 공식과 일치한다. 세 저장 모두 checksum 일치다.

## 증거

- `captures/packets_20260718_052925.txt` — Playroom C→S `0x0065` 및 세 C→S `0x0007`
- `artifacts/dynamic-analysis/playroom_direct_portal_queue_20260718.bmp`
- `artifacts/dynamic-analysis/playroom_after_real_feather_click_20260718.bmp`
- `artifacts/dynamic-analysis/playroom_juggling_direct_event_20260718.bmp`
- `artifacts/dynamic-analysis/playroom_tumbling_result_20260718.bmp`
- `artifacts/dynamic-analysis/playroom_yoyo_result_20260718.bmp`
- `artifacts/dynamic-analysis/playroom_exit_1a9_waiting_000d_20260718.bmp`
- `tools/test_server_room_mapping.py`

