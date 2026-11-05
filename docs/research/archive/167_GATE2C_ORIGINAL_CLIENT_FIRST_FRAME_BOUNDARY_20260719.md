> **SUPERSEDED by 168.** The no-draw/no-server boundary was overturned by direct original UI pixels and a live login/heartbeat.

# 167 Gate 2c original-client first-frame boundary (2026-07-19)

## Scope

웹 이식 우선 원칙에 따라 원본 `Azrok.exe`의 기동부터 첫 렌더 프레임 경계까지만 측정했다.
PatHouse/Plaza/미니게임 콘텐츠 QA는 실행하지 않았다.

## Result summary

| Gate 2c item | Result | Evidence |
|---|---|---|
| (a) 기동 | **VERIFIED** | Wine 11 guest가 원본 EXE와 `acknex.dll`을 적재하고 Acknex main loop 진입 |
| (b) D3D device | **VERIFIED** | `Direct3DCreate9(31)`, capability queries, `CreateDevice(640x480)` 및 FFP WebGL2 init 성공 |
| (c) 화면 출력 | **PARTIAL** | WebGL2 overlay와 Present는 동작하나 game draw는 아직 0, 검은 화면 |
| (d) 프레임 | **NOT VERIFIED** | 세 번의 초기 Present 이후 실제 draw가 없어 game FPS 판정 불가 |
| (e) 서버 접속 | **NOT VERIFIED** | TCP bridge 9201에 연결 0건; Winsock TRACE도 0건 |

## 1. Wine 11 loader and startup prerequisites

### `med.exe` prerequisite

**VERIFIED (dynamic + prior native evidence).** 패키지에 `med.exe`가 없을 때 Acknex는
`CreateFileA("med.exe")` 실패 후 설치 손상 경로로 정상 종료했다. 원본 `med.exe`
(1,036,288 bytes, SHA-256
`2F4E73BBB7DEB5903E47568827935B7B7C7DE39B02366088BDBC5ED0F66ACFEF`)를 추가한 뒤
그 경계를 통과했다.

### SDK version compatibility

**VERIFIED (browser dynamic).** 원본 엔진은 `Direct3DCreate9(0x1f)`를 호출한다. 초기 백엔드는
32만 허용해 NULL을 반환했고 엔진은 `Can't initialize: need DirectX 9.0c`를 표시했다.
`Direct3DCreate9`가 31과 32를 모두 허용하게 한 뒤 capability/CreateDevice 경로가 열렸다.

이는 구현된 입력을 실제 D3D9보다 엄격하게 거절한 첫 사례다. 이후 감사에서 실측으로 확정된
동종 결함은 sampler 범위 한 곳뿐이었다.

## 2. WebGL2 canvas ownership

**VERIFIED (browser dynamic).** Wine 11의 SDL software 화면이 원래 canvas의 2D context를 먼저
소유하므로 같은 canvas에서 WebGL2 context를 얻을 수 없었다. 런타임이 형제 overlay canvas
`#d3d9web-canvas`를 생성하게 하자 다음을 직접 관측했다.

```text
D3D9WEB_PHASE6_FFP_INIT webgl2=1 shader=driver-linked blocks=5 canvas=overlay
```

원본 클라이언트는 이어서 초기 Present 3회와 첫 텍스처를 전달했다.

```text
D3D9WEB_PHASE7_CREATE kind=texture handle=1 format=23 size=8x8 levels=1 bytes=128
D3D9WEB_PHASE7_UPLOAD kind=1 handle=1 bytes=128 levels=1 final=1
```

## 3. Official Acknex `-DIAG` path

### Static contract

**VERIFIED (Ghidra MCP, `acknex.dll`).**

- `FUN_10017EE0` at `0x10017EE0` parses `-DIAG` and sets `DAT_102FC550=1`.
- `engine_open` parses options before `FUN_10018DD0` opens the log.
- `FUN_10018DD0` selects `acklog.txt` / `acklog_cl.txt` / `acklog_sv.txt` and opens it through
  `__fsopen(path, "wt", 0x40)`.
- `FUN_10017B20` flushes after each write.
- `FUN_10022930` uses the parsed `-DIR` value when constructing the log directory.

따라서 현재 CLI의 `-DIR localauth`에서는 로그가 CWD의 `localauth\\acklog.txt`에 생긴다.
기존 브라우저 수집기가 CWD의 `acklog.txt`만 찾아서 놓친 것이었다.

### Dynamic log

**VERIFIED (guest helper + Browser FS).** `C:\\files\\localauth\\acklog.txt`를 실행 중 읽었고
각 쓰기가 이미 flush되어 있었다.

```text
Options -diag -NX 200 -NWND -PL player -DIR localauth -IP 127.0.0.1:9201
App C:\files\Azrok.exe in C:\files\
...
D3D9Web Browser Adapter slow device 180 detected
D3D device D3D9Web Browser Adapter 180 selected.. 2 objects
D3D_Init Window: 640x480x32 -> Window: 1x640x480x32
Video memory found: 256 MB
Build video tables
Main loop.........ok
```

엔진은 첫 `wait()` 이전이나 D3D 초기화에서 실패하지 않았다. 명시적 Acknex error도 없다.

## 4. Permissiveness audit

**VERIFIED (Gate 1 argument probe + source audit).** `Device_SetSamplerState`는 처음에 sampler
`<8`만 허용했지만 Gate 1에서 sampler `8..15`, `257..260`이 468회 직접 관측됐다.

- type 값은 모두 `1..13`으로 기존 범위 안이었다.
- WebGL FFP가 실제 소비하는 `0..7`만 host로 전달한다.
- D3D9의 유효하지만 이 게임에서 draw에 쓰지 않는 `8..15`, `256..260`은 `D3D_OK`로 수용한다.
- 그 밖의 값만 `D3DERR_INVALIDCALL`로 유지한다.

Gate 1에서 관측한 texture format, transform slot, render state, texture-stage state 및 primitive는
현재 구현 범위를 모두 통과했다. stub과 미실측 입력은 관대화 근거가 없으므로 변경하지 않았다.

## 5. First-frame call sequence

> **CORRECTION (VERIFIED):** `VIEWPORT_BEGIN/END`만으로는 guest 복귀가 증명되지 않았다.
> 후속 INT-return, EAX 전달, actual-to-static PC 재배치 측정이 guest 복귀를 직접 증명했다.

**VERIFIED (browser dynamic, first 256 calls only).** one-shot/sequence INT 0x9A 표식으로 초기
device 호출 순서를 측정했다.

1. `Clear -> Present` 3회
2. 초기 `SetRenderState`
3. sampler 1 및 texture-stage 1 상태 초기화
4. `CreateTexture(format=23, 8x8) -> Lock/Unlock -> upload`
5. `BeginScene`
6. `SetViewport(width=640)`

처음에는 마지막 device 표식이 `SetViewport` 진입이어서 host call 또는 guest 복귀가 막힌
것으로 보였다. `VIEWPORT_BEGIN/END`는 같은 millisecond 안에 JavaScript dispatcher가
완료됐음을 보였지만, 이 두 표식만으로 guest `INT 0x9A` 이후의 COM 복귀까지 증명할 수는
없었다.

```text
D3D9WEB_PHASE8_VIEWPORT_BEGIN 640x480
D3D9WEB_PHASE8_VIEWPORT_END
```

후속 측정이 그 빈틈을 직접 닫았다. **VERIFIED:** `d3d9webDispatchPhase6`의 EM_JS 반환값이
BoxedWine `callD3D9Web`에서 guest EAX로 전달됐고, `INT 0x9A` 다음 guest 코드가 재개됐다.
동적 actual PC를 `acknex.dll` static address로 재배치한 결과 SetViewport tail-JMP caller의
복귀 이후 주소에 도달했으며, 그 뒤 guest 실행도 계속됐다. 따라서 SetViewport의 return
address/ESP 손실 또는 nonvolatile-register 훼손 가설은 배제된다.

정적 ABI도 이 결과와 일치한다. `FUN_10040000`은 `[esp+4]`/`[esp+8]`을 `(device, viewport)`로
치환한 뒤 slot 47(`vtable+0xBC`)로 tail-JMP하고, D3D9Web `Device_SetViewport`는 x86
`__stdcall ret 8`로 두 인자를 정확히 정리한다.

첫 512개 후속 명령의 마지막 주소들은 `FUN_10010ad0 -> FUN_100101e0 -> pixel_for_vec`의
UI 텍스트 색상 패킹·글리프 순회 경로였다. **VERIFIED (Ghidra MCP):** 이 함수들에는 Winsock,
OS wait, script VM 호출이 없다. 정상 구조에서는 유한하며, 이 bounded trace 자체는 지속
대기점을 가리키지 않는다.

현재 직접 확정할 수 있는 경계는 **SetViewport 반환 이후에도 guest 실행이 지속됐지만,
bounded capture 안에서 다음 D3D 호출과 서버 연결은 나타나지 않았다**는 것까지다. 정확한
후속 대기/루프/비-D3D 호출 지점은 **NOT VERIFIED**다.

## 6. Network boundary

**VERIFIED (host TCP state).** 서버 `127.0.0.1:9200`과 WebSocket-TCP bridge
`127.0.0.1:9201`은 LISTEN 상태였지만 브라우저 원본 클라이언트 세션 동안 ESTABLISHED 연결이
없었다.

**NOT VERIFIED.** `WINEDEBUG=+winsock` 단발 실행은 위 first-frame 경계까지 재현했으나
`socket`/`connect` TRACE를 한 줄도 내지 않았다. 가능한 결론은 아직 둘이다.

1. 게임이 Winsock 호출에 아직 도달하지 않았다.
2. 이 Wine 11/BoxedWine 빌드에 해당 TRACE 채널이 빠져 있다.

간접 증거로 둘 중 하나를 고르지 않는다. SetViewport caller 복귀는 이미 VERIFIED이므로,
다음 정적/동적 목표는 재배치한 post-return PC부터 최초의 지속 대기/루프 또는 네트워크
선행조건까지 control flow를 좁히는 것이다.

## 7. Files and retained state

- `tools/d3d9_web_backend/d3d9_web.cpp`: SDK31 수용, valid sampler 수용, bounded call trace
- `tools/web_backend/host/d3d9web-runtime.js`: overlay canvas, no-op resize 방지, viewport markers
- `tools/boxedwine_local/web_backend/host/d3d9web-runtime.js`: served byte-equivalent source
- `tools/d3d9_web_backend/acklog_tail.cpp`: attach/inject 없는 진단 수집 helper
- `tools/boxedwine_local/index_d3d9web_pathouse.html`: local bounded gate page
- latest measured package: `Azrok_D3D9Web_pathouse_diag5.zip`

진단 후 source batch에서는 `WINEDEBUG=+winsock`과 helper 자동 실행을 제거했다. 서버 9200,
HTTP 8765, bridge 9201은 다음 측정을 위해 유지한다. 브라우저 실험 탭은 종료했다.
