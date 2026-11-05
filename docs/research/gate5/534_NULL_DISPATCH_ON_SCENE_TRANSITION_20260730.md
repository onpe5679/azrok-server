# 534 씬 전환 중 널 디스패치 — OX 팅김의 진짜 얼굴 (2026-07-30)

날짜: 2026-07-30
관련: **#531(이 카드가 §2·§3 을 뒤집는다)**, #530(파란 화면), #532(Codex 정적 분석), #122(정상 1회전)
원본 실행파일·게임 자산 무수정. 증거: `artifacts/audio/guestlog_nulldispatch_20260730.txt`

---

## 1. #531 의 §2·§3 은 틀렸다 (VERIFIED)

#531 은 "서버가 입장을 거부해 놓고 전부 0 인 `S→C 00C8` 을 보내서 클라이언트가 죽었다" 고 적었다.
**둘 다 사실이 아니다.** `azrok_server.py` 를 직접 읽어 확인했다.

```python
self.ox_spawn_x = int(os.environ.get('AZROK_OX_SPAWN_X', '0'), 0)   # 기본값 0
self.ox_spawn_y = int(os.environ.get('AZROK_OX_SPAWN_Y', '0'), 0)   # 기본값 0

self._ox_emit(source, 0x00C8, build_s2c_ox_enter_00c8(
    result=0, level_marker=0, ready_ms=0,
    x=self.ox_spawn_x, y=self.ox_spawn_y))       # -> 14B 전부 0
```

`result=0` 은 **유일한 입장 성공 경로**이고(`build_s2c_ox_enter_00c8` docstring: "Ghidra shows that non-zero exits immediately"),
`level_marker`·`ready_ms` 도 안전 기본값 0, 스폰 좌표도 기본 (0,0) 이다.
따라서 **14바이트가 전부 0 인 것은 정상 입장 응답의 모습**이지 거부의 흔적이 아니다.

`participants=[]` 로 보였던 것은 **클라이언트가 죽고 정리된 뒤에 조회했기 때문**이다.
서버는 입장을 시켰다. #122 의 완주 회차도 같은 14B "참가 상태" 를 받았다.

> **결론: "fail-closed 가 송신 쪽에서 지켜지지 않는다" 는 결함은 존재하지 않는다.**
> #531 §5 의 첫 번째 후속 작업(거부 시 C8/CC/CE 를 보내지 않게 한다)은 **취소**한다.

---

## 2. OX 와 무관하게 같은 크래시가 재현됐다 (VERIFIED)

2026-07-30 02:30, 갓 부팅한 클라이언트(게임 화면 도달 직후 ~1초)에 광장 전환 패킷
`0x000D` 하나만 주입했다. **OX 는 전혀 개입하지 않았다.**

```text
D3D9WEB_PHASE8_CREATE kind=declaration handle=8   elements=5
  (GStreamer 플러그인 로드 — BGM 시작)
D3D9WEB_SOCKET_POLL n=3 fd=28 ...
D3D9WEB_PHASE8_CREATE kind=declaration handle=71  elements=5
   ... 4 씩 증가 ...                     handle=163 elements=5
D3D9WEB_PHASE8_CREATE kind=declaration handle=183 elements=5
D3D9WEB_PHASE8_CREATE kind=declaration handle=187 elements=5
00c4:trace:seh:dispatch_exception code=c0000005 addr=00000000
```

`kind=declaration` 30 개 연속 생성 직후 폴트 — **#531 이 기록한 OX 팅김과 같은 서명**이다.
즉 이것은 OX 고유 결함이 아니라 **씬 전환 공통 결함**이다.

---

## 3. 폴트의 실제 정체 — 2 단 폴트 (VERIFIED)

### 1차 — 널 함수 포인터 호출

```text
dispatch_exception code=c0000005 flags=0 addr=00000000
  info[0]=00000000  info[1]=00000000
  eip=00000000 esp=7f1c2c10 ebp=7f1c2c94 eflags=00000246
  eax=7bdd73a0 ebx=00000001 ecx=7bdd7060 edx=00010056
  esi=00000041 edi=00000515
```

**`eip=00000000`** 이 핵심이다. 데이터 널 역참조가 아니라 **주소 0 으로 점프**했다.
`ecx=7bdd7060` 이 살아 있는 포인터인 것으로 보아 thiscall 규약의 `this` 는 유효하고,
**호출하려던 가상 함수 슬롯이 비어 있었다**는 뜻이다.

#531 이 "0 을 액터 인덱스나 포인터로 써서 널 역참조" 라고 추정한 것과 다르다. 그 추정은 폐기한다.

### 2차 — 1차를 처리하는 도중 다시 폴트

```text
call_seh_handlers calling handler at 7F551020 ... returned 1
call_seh_handlers calling handler at 004DE2D8 ... returned 1
call_seh_handlers calling handler at 107706BF ...
dispatch_exception code=c0000005 addr=004FF696
  info[0]=00000000  info[1]=0000003C
  eip=004ff696 eax=00000000 ecx=00000000
call_seh_handlers calling handler at 107598A1 ... returned 2   <- 중첩 예외
...
err:seh:NtRaiseException Unhandled exception code c0000005 addr 0x4ff696
D3D9WEB_PATHOUSE_EXITCODE=-1073741819
```

핸들러 `107706BF` 실행 중 `004FF696` 에서 **`[ecx+0x3C]`, `ecx=0`** 을 읽다 또 터졌고
(`info[1]=0000003C` 가 접근 주소), `107598A1` 이 2(중첩 예외)를 반환해 처리가 무너졌다.

### 주소가 속한 모듈

| 주소 | 모듈 | 근거 |
|---|---|---|
| `004DE2D8`, `004FF696` | **Azrok.exe** (image base 0x400000) | 주소 범위 |
| `107706BF`, `107598A1` | **0x10000000 로드 모듈** | 주소 범위 |
| `7F551020` | Wine 런타임(ntdll 계열) | 주소 범위 |

`WINEDLLOVERRIDES=d3d9=n` 으로 우리 D3D9Web `d3d9.dll` 이 native 로 강제 로드된다.
0x10000000 대역 모듈이 SEH 핸들러를 두 개나 갖고 있다는 사실은 이 모듈이 예외 처리에
깊이 관여한다는 뜻이다.

**INFERRED**: 0x10000000 모듈이 D3D9Web `d3d9.dll` 이고, 1차 널 디스패치는
**우리 구현에서 채워지지 않은 D3D9 vtable 슬롯**을 클라이언트가 호출한 것이다.
광장 씬은 PatHouse 보다 훨씬 많은 정점 선언을 쓰므로(30 개 대 소수), 광장 전용 코드 경로가
미구현 메서드를 건드린다는 그림과 맞는다.

**NOT VERIFIED**: 0x10000000 모듈의 정체를 모듈 목록으로 확인하지 않았다.
`004FF696` 이 어떤 함수인지 Ghidra 로 디컴파일하지 않았다(현재 Ghidra 인스턴스 미기동).
OX 팅김의 호출 지점과 이 호출 지점이 문자 그대로 동일한지도 미확인이다.

---

## 3.5. OX 라운드는 실제로 돌아간다 — 그리고 **문제 출제 직후** 죽는다 (VERIFIED)

주입 **순서**를 바로잡자 OX 회전이 정상 진행됐다. 결정적이다:

```text
02:36:38  0x000D 주입                       -> 광장 (room_kind=27, pos 3963,195)
02:36:53  POST /api/ox/enter                -> 006B marker 세우고 S→C 006E 발신
02:37:10  room_kind=-2 ox_room=default parts=1 surv=1  c8=1 s2c_c8=1  next=prepare   <- 입장 성공
02:37:12  phase=ready      s2c_cc=1                                                  <- 카운트다운
02:37:14  phase=question   q=0  s2c_ce=1                                             <- 문제 출제
02:37:19  conn=0                                                                     <- 사망
```

**서버 쪽 프로토콜은 전부 정상이다.** 입장·카운트다운·출제가 계약대로 났다.
클라이언트는 `S→C 00CE`(문제) 뒤 **약 5 초 안에** 죽는다.

### 순서가 전부였다 (VERIFIED)

앞선 시도가 실패한 이유는 결함이 아니라 내 순서 착오였다.
`/api/send` 로 **날 `0x006E` 를 먼저 주입**하면 클라이언트는 그 자리에서 OX 로 들어가며 `C→S 00C8` 을 쓴다.
그런데 그 시점엔 `ox_portal_006b_at` 이 아직 `None` 이라 `_handle_ox_enter` 의 `require_portal` 게이트(:4813-4830)가
그 C8 을 거부한다. 클라이언트는 로컬로만 OX 안에 있고 서버는 광장으로 아는 **영구 desync** 가 된다.
그 뒤에 `/api/ox/enter` 를 불러도 클라이언트는 이미 C8 을 써버려 다시 보내지 않는다.

> **운용 규칙: OX 는 반드시 `/api/ox/enter` 로 시작한다. 날 `0x006E` 를 `/api/send` 로 주입하지 말 것.**

## 3.6. OX 크래시의 1차 폴트는 `0x000D` 크래시와 다르다 (VERIFIED)

```text
dispatch_exception code=c0000005 addr=7F37DFB8
  info[0]=00000000        <- 읽기 접근
  info[1]=33006D10        <- 폴트난 데이터 주소
  eip=7f37dfb8 esp=7f1c31a0 ebp=fffffff7 eflags=00000206
  eax=33006d00 ebx=05ebd648 ecx=00000000 edx=00002800
  esi=05ebd648 edi=00000000
call_seh_handlers calling handler at 004DE2D8 ... returned 1
call_seh_handlers calling handler at 107706BF
  EnumProcessModulesEx (FFFFFFFF, 0B44C5C0, 1024, 7F1C2408, 0)      <- 엔진 크래시 리포터
dispatch_exception code=c0000005 addr=00000000 eip=00000000          <- 2차
call_seh_handlers calling handler at 107598A1 ... returned 2         <- 중첩 예외
err:seh:NtRaiseException Unhandled exception code c0000005 addr (nil)
```

- 폴트 주소 `0x33006D10` = **`eax + 0x10`**, `eax=0x33006D00`.
- `0x33006D00` 은 힙/스택 포인터로 보이지 않는다. 바이트로 `00 6D 00 33` — **문자 데이터 같은 값**이다.
- `ebp=0xFFFFFFF7`(= -9) 은 정상 프레임 포인터가 아니다.
- `eip=0x7F37DFB8` 은 Azrok.exe(0x400000~0x6F5000) 밖이다.

**중요한 정정**: `107706BF` 핸들러가 `EnumProcessModulesEx` 를 호출한다 — 이것은 **엔진 자체의 크래시 리포터**다.
그 안에서 `eip=00000000` 이 발생한다. 즉 §3 에서 "1차 널 디스패치" 라고 본 `eip=0` 은
**OX 경로에서는 크래시 리포터의 2차 산물**이다. `0x000D` 크래시에서는 `eip=0` 이 1차였으므로
두 크래시의 1차 폴트는 서로 다르다. 하나로 묶지 말 것.

## 3.65. 모듈 맵 확정 — 주소가 전부 귀속됐다 (VERIFIED)

`WINEDEBUG=-all,+seh,+loaddll` 로 실제 로드 베이스를 찍었다
(`Azrok_D3D9Web_pathouse_guesttexrecycle4_modmap1.zip` / `run_azrok_modmap.bat`,
로그 `artifacts/audio/guestlog_modmap_ox_20260730.txt`). **PE 선호 베이스는 하나도 지켜지지 않았다.**

```text
Loaded L"C:\files\Azrok.exe"              at 00400000: native
Loaded L"C:\files\d3d9.dll"               at 7BDD0000: native     <- 우리 D3D9Web d3d9
Loaded L"C:\files\acknex.dll"             at 7F360000: native     <- A6/A7 엔진
Loaded L"C:\files\AckUtl.dll"             at 7F6E0000: native
Loaded L"C:\windows\system32\ntdll.dll"   at 10700000: builtin
```

이제 모든 주소가 확정된다.

| 주소 | 모듈 | RVA | 성격 |
|---|---|---|---|
| **`7F37DFB8`** (OX 1차 폴트) | **acknex.dll** | **`0x1DFB8`** | **실코드 — 실행된 쓰레기가 아니다** |
| `7F551020` (핸들러) | acknex.dll | `0x1F1020` | 엔진 SEH |
| `004DE2D8` (핸들러) | Azrok.exe | `0xDE2D8` | 클라이언트 SEH |
| `004FF696` (0x000D 2차) | Azrok.exe | `0xFF696` | 클라이언트 코드 |
| `107706BF`, `107598A1` | **ntdll.dll** | `0x706BF`, `0x598A1` | **Wine 런타임** |
| `7bdd73a0`(eax), `7bdd7060`(ecx) — 0x000D 1차 | **d3d9.dll** | `0x73A0`, `0x7060` | **우리 D3D9Web 객체** |

### 이것이 뒤집는 것

1. **§3.6 의 "엔진 크래시 리포터" 는 틀렸다.** `107706BF`·`107598A1` 은 **ntdll**,
   즉 **Wine 자신의 미처리 예외 경로**다. 거기서 부르는 `EnumProcessModulesEx` 는
   Wine 이 백트레이스를 만드는 동작이지 게임 엔진의 리포터가 아니다.
2. **`0x000D` 크래시의 널 디스패치는 우리 d3d9.dll 을 향한 것이다.**
   그 폴트의 `ecx=0x7BDD7060` 은 **d3d9.dll+0x7060** — `this` 포인터는 멀쩡한
   D3D9Web 객체를 가리키는데 **호출된 가상 함수 슬롯이 비어 있었다**.
   §3 에서 INFERRED 로 적은 "미구현 vtable 슬롯" 은 이제 **VERIFIED** 다.
3. **OX 1차 폴트는 acknex.dll 안의 진짜 코드다.** `ebp=0xFFFFFFF7` 때문에
   "실행된 쓰레기" 를 의심했지만 아니다. 그 함수가 `[eax+0x10]` 을 읽는데
   `eax` 가 오염된 것이다.

### 결정적 재현 — 레지스터가 런마다 동일 (VERIFIED)

2 회 연속 재현에서 힙 주소(`ebx`/`esi`: `05EBD648` vs `05CA9760`) 만 다르고 나머지는 전부 같다.

```text
eip=7f37dfb8  eax=33006d00  ecx=00000000  edx=00002800  edi=00000000  ebp=fffffff7
info[1]=33006D10   (= eax + 0x10, 읽기)
```

`eax=0x33006D00` 이 **런마다 동일**하다 — 무작위 힙 포인터가 아니라
**데이터에서 계산된 결정적 값**이라는 뜻이다. 바이트로 `00 6D 00 33`.

**다음 한 수: Ghidra 로 `acknex.dll` RVA `0x1DFB8` 을 디컴파일한다.**
`eax` 가 어디서 오는지, `+0x10` 이 무슨 필드인지가 원인 그 자체다.

## 3.7. 모듈 베이스 — PE 선호값 (참고용, VERIFIED)

| 모듈 | 선호 베이스 | SizeOfImage | 끝 |
|---|---|---|---|
| `Azrok.exe` | `0x00400000` | `0x2F5000` | `0x006F5000` |
| `d3d9.dll` | `0x10000000` | `0x217000` | `0x10217000` |
| `acknex.dll` | `0x10000000` | `0x37C000` | `0x1037C000` |
| `ackutl.dll` | `0x10000000` | `0x18000` | `0x10018000` |

`004DE2D8`·`004FF696` 는 **Azrok.exe 안**이다(VERIFIED).

세 DLL 이 모두 `0x10000000` 을 선호하므로 하나만 그 자리를 얻고 나머지는 재배치된다.
그리고 **어느 것도 선호 베이스에서는 `0x107598A1`·`0x107706BF` 를 포함하지 못한다**
(가장 큰 acknex 조차 `0x1037C000` 에서 끝난다). 따라서 그 핸들러들이 있는 모듈은
`0x10000000` 보다 위로 **재배치된 상태**다.

**NOT VERIFIED**: 실제 로드 베이스. `WINEDEBUG=+loaddll` 로 모듈 맵을 찍어 확정해야 한다
(`Azrok_D3D9Web_pathouse_guesttexrecycle4_modmap1.zip` / `run_azrok_modmap.bat` 준비 완료).
확인 전까지 `0x7F37DFB8` 이 코드인지 실행된 쓰레기인지 단정하지 않는다.

## 3.8. #122 의 완주는 웹이 아니었다 (VERIFIED)

#122 는 최종 상태를 `scene=110 / phase=4 / dispatch_mode=1 / self=1` 로 기록했다.
이 값들은 `read_watches()` 로 읽는 **프로세스 메모리 워치**이고, 브라우저 게스트에서는 얻을 수 없다.
따라서 #122 의 완주는 **네이티브 실행**이었다.

> **OX 퀴즈는 웹 포팅에서 한 번도 완주한 적이 없다.** 이것은 회귀가 아니라 웹 포팅 고유 결함이다.
> #531 이 "회귀가 아니다 — 진입 경로가 달랐다" 고 한 것은 결론만 우연히 맞고 이유가 틀렸다.

## 3.9. 폴트 함수를 디컴파일했다 — 자산 조회 실패다 (VERIFIED)

`0x7F37DFB8 - 0x7F360000 = 0x1DFB8` → **acknex.dll RVA 0x1DFB8**.
디스크에서 바이트를 직접 읽어 함수를 복원했다(함수 시작 `0x1001DF90`, 이미지 베이스 0x10000000).

```asm
1001DF90  push ecx / push ebx
1001DF92  mov  ebx, [esp+0x0C]      ; 인자 = 대상 객체
1001DF96  xor  ecx, ecx
1001DF98  cmp  [ebx+0x40], ecx      ; 이미 계산돼 있으면
1001DF9B  je   1001DFAB
1001DF9D  cmp  [ebx+0x3C], ecx
1001DFA0  je   1001DFAB
1001DFA2  mov  [ebx+0x70], ecx      ; 초기화하고 반환
1001DFA5  mov  [ebx+0x74], ecx
1001DFAA  ret
1001DFAB  mov  eax, [ebx+0x24]      ; 비트맵 포인터
1001DFAE  cmp  eax, ecx
1001DFB0  je   1001DFCD             ; <-- 널 검사는 여기뿐
1001DFB2  mov  [ebx+0x70], ecx
1001DFB5  mov  [ebx+0x74], ecx
1001DFB8  mov  ecx, [eax+0x10]      ; <<<< 폴트. info[1] = eax+0x10 과 정확히 일치
1001DFBB  shl  ecx, 10              ; x1024
1001DFBE  mov  [ebx+0x40], ecx
1001DFC1  mov  edx, [eax+0x0C]
1001DFC4  shl  edx, 10
1001DFC7  mov  [ebx+0x3C], edx
```

`ecx=0`(0x1DF96 에서 0 으로 만든 뒤 아직 재적재 전), `info[1]=eax+0x10` — **레지스터가 전부 맞아떨어진다.**
`<<10`(x1024) 로 폭·높이를 스케일하는 A6 의 비트맵 크기 계산이다.

**`[ebx+0x24]` 가 널은 아닌데 유효하지 않은 포인터다.** 널 검사만 있어서 통과한다.

### 그 포인터는 어디서 오는가 (VERIFIED)

호출자 4 곳(`10010952`, `1001E0C6`, `1001E1DD`, `1001F001`) 중 `1001E1DD` 의 문맥이 결정적이다.

```asm
1001E1BA  mov  edx, [0x1029542C]    ; 이름/인자 전역
1001E1C1  call 0x10011F20           ; 자산 조회
1001E1C6  mov  ecx, [0x10290684]    ; 대상 객체(싱글턴)
1001E1CC  mov  [ecx+0x24], eax      ; <-- 반환값을 검증 없이 저장
1001E1D7  cmp  [eax+0x24], ebx
1001E1DD  call 0x1001DF90           ; 폴트 함수
```

`0x10011F20` 의 구조:

```asm
10011F20  push esi / mov esi,[esp+8]
10011F26  call 0x1005BFE0           ; 1차 조회
10011F2E  test eax,eax / jnz 10011F41
10011F32  push 1 / push 0xC / push esi
10011F37  call 0x10012720           ; <-- 폴백. 이 반환값이 그대로 나간다
10011F40  ret
10011F41  ... call 0x10011CBF ... add dword [eax+0x40], 1   ; 성공 경로: refcount++
```

성공 경로는 `add dword [eax+0x40],1` 로 **포인터에 쓰기**를 한다.
`eax=0x33006D00` 이었다면 거기서 먼저 터졌을 텐데 그러지 않았다 —
따라서 **폴백 경로 `0x10012720` 이 반환한 값**이다(VERIFIED).

`0x10012720` 은 이름 문자열로 심볼을 찾는 함수다(`cmp byte [edi],0` 로 빈 문자열을 검사).
성공하면 `mov eax,[eax+0x10]` 로 **심볼의 `+0x10` 필드**를 돌려준다.

**INFERRED**: `0x33006D00` 을 A6 의 16.16 고정소수점 `var` 로 읽으면 13056.42 다.
비트맵 객체가 아니라 **숫자 값**으로 보인다 — 이름은 찾았는데 종류가 다른 심볼일 가능성.

**NOT VERIFIED**: 그 이름이 무엇인지. `[0x1029542C]` 는 `.text` 에서 **215 회** 참조되는
엔진 범용 전역이라 정적으로는 값을 특정할 수 없다. `[0x10290684]` 는 46 회 참조되고
`1001E0DF~1001E5xx` 한 서브시스템에만 몰려 있는 싱글턴이며,
`1001E132` 의 `mov dword [0x10290684], 0` 은 초기화가 아니라 teardown 이다.

### acklog 로는 못 잡는다 (VERIFIED)

`dumpAcklog()` 로 게스트 FS 의 acknex 로그를 수거했다(`artifacts/audio/guestlog_ox_acklog_20260730.txt`).
**크래시 직전 구간이 없다** — 로그는 `Level(pet.wmb)` / `Physics restarted...ok` 에서 끝나고
헤더 시각도 이전 런의 것이다. 프로세스가 죽으면서 버퍼가 플러시되지 않는다.

**다음 한 수는 런타임 프로브다**: `0x10011F20` 진입 시 `[esp+8]` 이 가리키는 문자열을 잡아야 한다.
정적 분석은 여기까지다.

## 4. 재현 조건 (VERIFIED)

`0x000D` 를 **게임 화면 도달 직후**(약 1초 뒤) 보내면 죽는다.
같은 패킷을 클라이언트가 안정된 뒤에 보내면 광장 진입이 정상 동작한다(이 세션에서 이미 여러 번 성공).

직전 로그에 `D3D9WEB_ASYNC_RING_FRAME ... inflight=1 max_inflight=1` 이 있다 —
**프레임이 in-flight 인 상태에서 씬이 갈린다.**

**INFERRED**: 트리거는 "장치 리소스가 아직 다 만들어지지 않은 시점의 씬 전환" 이고,
OX 진입도 같은 종류의 전환이다.

### 두 번째 독립 사례 — 2세션에서 B 가 같은 서명으로 죽었다 (VERIFIED)

2026-07-30 03:30, 게이트5 2세션 검증에서 **세션 B 가 광장 진입 직후 사망**했다.
서명은 `0x000D` 조기 전송 크래시와 동일하다(1차 `eip=00000000`, 2차 `addr 0x4ff696`, exit `-1073741819`).

| | 세션 A | 세션 B |
|---|---|---|
| 부팅 완료 | 03:25:19 | 03:28:29 |
| `0x000D` 전송 | 03:26:49 (**+90s**) | 03:29:59 (**+90s**) |
| 결과 | 생존, 광장 `pos 3963,195` | **사망** |

**같은 90 초인데 결과가 갈렸다.** 차이는 B 가 부팅할 때 **A 의 BoxedWine 이 계속 돌고 있었다**는 것뿐이다.
경합 때문에 B 는 90 초에도 리소스 생성이 끝나지 않았다.

> **고정 대기는 준비 신호가 아니다.** 이것이 §4 의 "리소스 생성 중 전환" 가설을 뒷받침하는
> 두 번째 독립 증거다.

### 준비 게이트 (구현됨)

`room_kind` 는 광장 진입 전까지 `null` 이라 사전 대기를 게이팅할 수 없다.
대신 게스트 자신의 리소스 생성 활동을 본다 — `scratchpad/wait_ready.ps1`:

- `D3D9WebDebug.presents` 가 증가하고 **있고**
- 게스트 콘솔의 `PHASE8_CREATE` 줄 수가 **18 초 연속 그대로**일 때

에만 전환 패킷을 보낸다. 캔버스가 `0x0` 이면 즉시 사망 판정.

이것은 **회피이지 수정이 아니다.** 실제 수정은 전환 시점에 아직 채워지지 않은
D3D9Web vtable 슬롯을 찾아 메우는 것이다(§3.65 참조 — `ecx` 가 d3d9.dll 객체를 가리켰다).

---

## 5. #531 §4 의 분리 주장 수정

증상 수준의 분리(파란 화면은 프로세스 생존, OX 팅김은 사망)는 **여전히 VERIFIED** 다.
그러나 "같은 원인으로 묶지 말 것" 은 근거가 약해졌다 — 셋 다 D3D9Web 계층에서
**씬/모드 전환** 때 일어난다(광장 전환, OX 진입, 엔터 채팅 진입).

**INFERRED**: 같은 계층의 전환 처리 결함일 가능성. 단정하지 않는다.

---

## 6. 다음

1. **0x10000000 모듈 확정** — 게스트에서 모듈 목록을 찍어 d3d9.dll 인지 직접 본다. (간접 증거 금지)
2. **`0x004FF696` 디컴파일** — Ghidra `analyzeHeadless` 로 `/New Traces/Azrok_original.exe` 에서 확인.
3. **널 슬롯 탐색** — D3D9Web d3d9 구현의 vtable 에서 비어 있는 슬롯을 소스에서 찾는다.
4. `0x000D` 크래시는 **결정적 재현이 가능하다**. 이것이 OX 보다 훨씬 싼 실험대다.
