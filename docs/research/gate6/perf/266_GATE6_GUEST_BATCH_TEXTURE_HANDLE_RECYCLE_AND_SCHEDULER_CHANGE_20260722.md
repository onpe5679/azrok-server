# 266 — Gate 6 guest batching, transient texture handle recycle, scheduler change (2026-07-22)

## Scope

PatHouse 1024x768의 남은 CPU 비용을 줄이기 위해 두 개의 guest proxy 실험을 분리해 검증했다.

1. 여러 일반 D3D 명령을 guest에서 한 INT `+5` envelope로 묶는 command batching
2. 매 프레임 생성되는 256x256, 1-level, `D3DFMT_R5G6B5` transient texture의 COM 객체가 아니라 host handle만 재사용

측정 중 Windows scheduler 환경이 바뀌었으므로 변경 전/후 FPS 표본을 섞지 않는다.

## 1. Guest command batching

### VERIFIED — static/ABI

- `D3D9WEB_GUEST_BATCH`는 기본값 0인 실험 기능이다.
- 새 `+5` envelope는 magic/version/count/recordBytes와 허용 opcode를 host에서 검증한다.
- terminal/direct upload/direct DrawUP 전에 pending 명령을 flush하여 D3D 명령 순서를 보존한다.
- 새 host의 reject와 old host의 unsupported 반환을 구분하고 old host fallback replay를 유지한다.

### VERIFIED — clock-free census

기준 120 Presents:

- `i2=64200` = 535/f
- `i3=1440` = 12/f
- `i4=17280` = 144/f
- 총 guest private INT = 691/f

단순 batching의 이론치는 약 307 INT/f였고, 실제 새 경로에서도 INT 감소와 기준 PatHouse 렌더 보존을 확인했다. 그러나 logical workload가 세션별로 달라 census 자체를 FPS 비교에 사용하지 않았다.

### VERIFIED — performance REJECTED

같은 no-profile host에서 guest proxy만 OFF/ON으로 바꾼 장시간 쌍:

- A2 control: `1080 Presents / 33.201 s = 32.529 FPS`
- B2 batch: `1080 / 33.506 s = 32.233 FPS` (`-0.91%`)
- A3 control: `1560 / 47.921 s = 32.554 FPS`
- B3 batch: `1560 / 48.434 s = 32.209 FPS` (`-1.06%`)

첫 A1/B1은 A1 세션이 27.531 FPS로 비정상적으로 낮아 이후 쌍과 일치하지 않았다. 재현 가능한 두 쌍은 모두 회귀였으므로 guest `+5` batching은 성능 경로에서 **REJECTED**다. 코드는 기본 OFF인 실험 자산으로만 남긴다.

## 2. Handle-only transient texture recycle

### VERIFIED — static safety

구현: `tools/d3d9_web_backend/d3d9_web.cpp`

- feature gate `D3D9WEB_TRANSIENT_TEXTURE_RECYCLE` 기본값 0
- target은 실측된 `256x256 / 1 level / RGB565 / pitch 512 / total 131072`이며 usage/pool을 포함한 exact descriptor가 같을 때만 hit
- old `TextureObject`와 embedded surface는 refs=0/destroy_sent=1 tombstone으로 남기고 backing은 기존처럼 free
- 새 Create는 새 COM object/surface/zeroed backing을 할당하고 host handle만 가져온다
- final Release의 handle은 quarantine에 넣고 성공한 다음 Present 뒤에만 available로 승격
- recycled texture는 Unlock/UpdateSurface의 전체 upload 성공 또는 첫 host bind 전 강제 전체 upload가 완료되어야 사용 가능
- bridge failure/Reset/new device는 slot을 abandon/drain하고 recycle epoch를 증가시킨다. old generation texture는 재입장할 수 없다.

이 설계는 old COM pointer를 되살릴 때 발생하는 surface/stateblock late-Release ABA와 이전 프레임 GL 내용 노출을 피한다. Azrok의 single render thread가 실측 범위이며, 범용 `D3DCREATE_MULTITHREADED` serialization은 별도 미구현이다.

### VERIFIED — diagnostic PatHouse

`boxedwine.upstreamjit38guestbatchcensus2` + `Azrok_D3D9Web_pathouse_guesttexrecycle4`:

- 기준 PatHouse 화면 유지: 카펫 UV, 벽/가구, 캐릭터 얼굴/그림자, 한글, UI alpha/cull 정상
- steady `op12(CreateTexture)=0`, `op15(DestroyResource)=0`
- recurrent RGB565 handle의 full upload는 `120 final / 15,728,640 bytes` 유지
- `missing=0`, `bound_blocked=0`, fatal/exception/OOM/bad Upload/GL error 0
- 장기 구간에도 recurrent handle은 유지됐다. 전체 live count 131→134 증가는 별도 영구 UI texture의 드문 `op12=1` 창과 함께 발생했으며 recurrent texture create/destroy 재발은 아니었다.

산출물:

- DLL SHA256 `2C5CEE49D2C06831C33581EBF16DE21B3EC1CB3F23B4BC2CEE5F42878D38E2A0`
- package `Azrok_D3D9Web_pathouse_guesttexrecycle4.zip`
- package SHA256 `BB9B2284D78D749D9F8F45EEC027AFC2779438D9B643E06AE6D59957C83CAD25`
- package 내부 `d3d9.dll` SHA가 DLL과 동일함을 직접 확인

### PARTIAL — old scheduler clean release screen

환경 변경 전에 완료된 strict foreground 쌍:

| pair | control | recycle | delta |
|---|---:|---:|---:|
| 1 | 34.175 FPS | 35.409 FPS | +3.61% |
| 2 | 33.964 FPS | 37.222 FPS | +9.59% |

세 번째 control은 36.404 FPS였지만 B3 중 foreground 이탈 6회/restore failure 2회가 발생했고, 동시에 아래 scheduler 설정 변경 통지가 들어왔다. B3는 폐기한다. 두 쌍만으로 채택하지 않는다.

## 3. Scheduler environment change

사용자 통지로 다음 설정이 적용됐다.

- `Win32PrioritySeparation 0x2 -> 0x18`: foreground CPU quantum bonus 제거
- renderer process EcoQoS 해제 + High priority, 30분마다 재적용

현재 레지스트리를 직접 읽어 `Win32PrioritySeparation=0x18`을 확인했다. ChatGPT 프로세스군에서도 main PID 15032와 renderer 후보 PID 36544/39644/83812가 `High`로 관측됐다. EcoQoS bit 자체와 30분 재적용 작업은 이 문서에서 별도 검증하지 않았다.

따라서 기존 strict-foreground 결과와 새 결과는 같은 population이 아니다.

### VERIFIED — new-environment natural background sample

동일 recycle B3 세션에서 포그라운드를 강제로 바꾸지 않고 측정했다.

- OS foreground start: HWiNFO64, end: Comet
- page start/end: `visibilityState=visible`, `hidden=false`
- `840 Presents / 28.785 s = 29.182 FPS`
- fatal/exception/OOM/GL error 0

이 값은 **background baseline 한 개**일 뿐 foreground delta 결론이 아니다. 다음에 사용자가 자연스럽게 Codex 창으로 돌아온 구간에서 같은 세션/visible 상태로 foreground 표본을 얻어 비교한다.

판정 규칙:

- foreground/background delta가 사실상 0이면 이후 HWND 고정을 폐지하고 visible-background 측정을 허용
- delta가 크면 사용자 작업 중에는 foreground를 빼앗지 않고 FPS A/B를 연기
- `visibilityState != visible`, `hidden=true`, Present marker 정지/급감 표본은 Chromium occlusion/스로틀 후보로 제외

## Current verdict

- guest command batching: **REJECTED**
- transient texture handle recycle correctness: **VERIFIED**
- transient texture handle recycle performance: **PARTIAL**, scheduler 변경 후 foreground/background calibration 대기
- production/default proxy: 기존 `statecache_release1` 유지. recycle은 아직 기본 OFF
