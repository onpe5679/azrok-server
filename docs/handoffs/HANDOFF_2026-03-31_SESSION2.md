# Handoff 2026-03-31 Session 2

## 이번 세션에서 달성한 것

### Blocker A (UI 자동화) — 해결
- FUN_0050ffd0 hook으로 범용 버튼 이벤트 주입 시스템 구축
- push-button 0x0e + WM_CHAR + push-button 0x13 → C->S 0x0004 전송 성공
- 성공 패턴: 별도 CLI로 합성 클릭(egg) → Frida 세션에서 0x0e(x60 NO FILTER) + WM_CHAR + 0x13(x1 targetCaller=0x5e7901)

### 프로토콜 수정
- stat opcodes: 0x0010/0x0011 → 0x000A/0x000B (wire opcode 수정)
- S->C 0x0000: 4바이트 → 0x183바이트 (login struct 크기)
- S->C 0x0003: PatHouse 경로 ("Data\Space\PatHouse")
- entry_mode: 0x00 (Plaza 강제 없음)
- 0x0066/0x0068 self follow-up 제거 (self에게 inert)
- 0x006E ready 신호 추가
- C->S 0x0008 핸들러 추가
- 반복 C->S 0x0007에 전체 번들 응답

### 엔진 패치
- nexus 기본값 40→200 (acknex.dll 코드 패치)
- WDL nexus override NOP (2 사이트)
- 런타임 nexus 강제 (apply_runtime_patches)

### 핵심 발견
- FUN_0050CBC0: 공통 secondary handler, param_2=opcode로 분기
- FUN_00594310: main dispatch, this+0x163D8(gate) + this+0x163E4(state)
- FUN_00531640: PatHouse 6-stage handler, 마지막에 FUN_0050A840() 호출 (로딩 닫기)
- FUN_0050B400: FUN_0050a0f0 내에서만 호출 (level_load 직후)
- state1_opcode100_null_guard가 FUN_0050B400(0x6E)를 재진입 호출하여 PatHouse bootstrap을 방해

## 현재 블로커

### 로딩이 완료되지 않음
- level_load("room.wmb") 호출 확인 (Frida hooks)
- FUN_0050B400(100) → FUN_00531640이 호출되어야 하지만 완료 여부 불명
- 모든 게임 상태(dispatch_state, selfEntity, readyLatch)가 0으로 남음
- S->C 0x0064를 보내면 dispatch_state=1이 되지만 null entity 크래시 발생
- null guard를 비활성화하면 재진입 없이 자연 bootstrap이 가능하지만 로딩 여전히 미완료

### 가능한 원인
1. FUN_00531640의 6 stages 중 하나가 실패 (어떤 스테이지인지 모름)
2. gm 오프셋이 실제와 다를 수 있음 (텔레메트리 값이 항상 0)
3. 0x0007 stat bag 값이 잘못되어 stage가 필요한 조건을 못 충족
4. S->C 0x0000 (login response) 내용이 대부분 0이라 초기 상태 부족

## 다음 세션에서 해야 할 것

### 우선순위 1: FUN_00531640 디버깅
- Ghidra로 각 stage 함수 디컴파일 (FUN_00530830, FUN_00557570 등)
- Frida로 FUN_00531640 + 각 stage 함수 + FUN_0050A840 hook → 어디까지 실행되는지 확인
- FUN_00528B30 (에러 체크) 반환값 모니터링

### 우선순위 2: gm 오프셋 검증
- FUN_00594310의 this (0x17b820)와 0x006e8430의 gm가 다른 객체인지 확인
- dispatch object vs game manager의 관계 분석
- 실제 self entity 생성 여부를 올바른 오프셋으로 확인

### 우선순위 3: S->C 0x0000 복원
- 0x183 바이트 중 payload[1] (mode) 등 핵심 필드에 적절한 값 넣기
- FUN_0059E070과 FUN_0050D1C0 분석으로 필요한 필드 확인

### 우선순위 4: 0x0007 stat bag wire order
- init.csv row order ≠ wire order (recovery doc 경고)
- FUN_005a37a0의 71-name table과 wire bag 매핑 정밀 분석

## 서버 현재 설정
- PatHouse 경로
- auto-create: heartbeat 999 (비활성)
- null guard: FULLY DISABLED
- S->C 0x0064: 비활성 (heartbeat/0x0008/0x0017 모두)
- nexus: 200 (3중 패치)
- stat opcodes: 0x000A/0x000B
- minimal stats (bond energy=100)

## 최종 상태 (세션 종료 시)

### 현재 서버 설정
- PatHouse 경로, auto-create heartbeat 8
- null guard: FULLY DISABLED
- S->C 0x0064: 모든 경로에서 비활성
- nexus: 200 (3중 패치)
- opcodes: 0x000A/0x000B
- 0x006E: C->S 0x0064 수신 시 3회 전송

### 게임 상태
- Frida 없이 실행하면 안정적으로 로딩 화면에 멈춤 (371MB, 크래시 없음)
- Frida 훅을 붙이면 간헐적 크래시 (exit code 1 또는 0xC0000005)
- 가장 기능적이었던 설정: safe guard + no 0x0064 → 인벤토리 UI + 안정

### 아직 해결 못한 핵심 의문
1. level_load("room.wmb")가 확실히 호출되는가? (한 테스트에서만 확인, 재현 불일치)
2. FUN_00531640 (PatHouse 6-stage handler)가 실행되고 완료되는가?
3. FUN_0050A840 (loading close)가 호출되는가?
4. gm 오프셋이 실제로 맞는가? (모든 텔레메트리 값이 0)
5. Frida 훅이 왜 게임 실행을 방해하는가?

### 핵심 미해결: gm 포인터 불일치
- 0x006e8430의 값(0x102749E8)은 Acknex 엔진 객체 → 게임 상태 오프셋이 안 맞음
- 0x17b820은 dispatch 객체(CClientPeer) → dispatch_state(+0x163E4)만 정확
- dp+0x35CB9에서 selfEnt가 비-제로로 읽히지만 다른 오프셋(popup 등)은 0
- 실제 게임 매니저(CLogicManager)는 제3의 주소에 있음 → null guard가 캡쳐하던 gm
- Ghidra 재연결 후 FUN_00615650의 this 포인터 출처를 추적해야 함

### 최종 발견: gm+0x31946은 FUN_0050a0f0 호출 게이트
- Ghidra 에이전트가 FUN_00509200 분석: `if (this+0x31946 != 0)` → FUN_0050a0f0 호출
- gm+0x31946=1 강제 설정 → 캐릭터 선택 → 로딩 화면 전환 확인!
- S->C 0x0002가 gm+0x31946을 0으로 리셋 → auto-create 후 재설정 필요
- gm+0x31792 (dispatch_state) = 0 → FUN_0050a0f0 case 0이 실행 안 됨
- FUN_0050a0f0은 gm+0x31AAD에서 room code를 안 읽음 — 별도 큐 메커니즘 사용
- Ghidra 필요: FUN_0050a0f0의 정확한 room code 소스 파악

### 제안
- Ghidra 재연결 필수 — FUN_0050a0f0 디컴파일하여 room code 읽기 소스 확인
- FUN_0050D290 → FUN_0050A7F0 디컴파일하여 room code 큐잉 방식 확인
- FUN_00509200의 this 포인터 출처 확인 (gm=0x102749E8 검증)
- S->C 0x0000 login response 필드 복원
- 0x0007 stat bag wire order 정밀 매핑

## 관련 파일
- azrok_server.py (메인 서버)
- tools/azrok_input_hook.js (Frida hook + push-button)
- tools/azrok_frida_input.py (CLI)
- docs/research/ (프로토콜 분석 문서들)
- docs/debug/ (디버그 노트들)
- docs/protocol_recovery_final_2026-03-31/ (최신 프로토콜 복원 문서)
