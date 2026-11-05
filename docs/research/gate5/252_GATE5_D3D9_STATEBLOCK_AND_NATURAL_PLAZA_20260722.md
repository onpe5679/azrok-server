# Gate 5 — D3D9 StateBlock 표면 보강과 자연 PatHouse → Plaza 전환

날짜: 2026-07-22 KST

## 결론

- **VERIFIED (dynamic):** 종전 Plaza 진입 직후 `EIP=0` 예외는 BoxedWine 깨우기나 WinSock 전달 문제가 아니었습니다. 실제 null indirect-call operand는 `0x7BDD61C8`, device vtable base는 `0x7BDD6058`였고 차이 `0x170 / 4 = slot 92`, 즉 `IDirect3DDevice9::SetVertexShader(NULL)`였습니다.
- **VERIFIED (static + trace):** 원본 Wine D3D9 trace는 Plaza 전환에서 StateBlock 생성/기록/적용과 `SetVertexShader(NULL)`, `SetPixelShader(NULL)`, `GetCreationParameters`, `GetRenderTarget`, `SetNPatchMode(0)`, `GetIndices`를 실제 사용합니다.
- **VERIFIED (implementation/build):** 프록시에 위 표준 device 슬롯과 6-slot StateBlock COM 객체를 구현했습니다. 최종 DLL SHA-256은 `22A36B83893DBFC477C352544D8F8AA407C49D18DBB12D796BD5FBECAE51CEC0`, 패키지는 `Azrok_D3D9Web_pathouse_stateblock1.zip`입니다.
- **VERIFIED (browser + wire):** 한 탭에서 원본 선택 화면 → PatHouse → 자연 문 입력 → Plaza가 화면으로 확인됐습니다. `C2S 0x0019`, `S2C 0x000D`, `C2S/S2C 0x0064` 뒤 heartbeat가 109.770초 이상 지속됐고 WebSocket과 TCP 양쪽이 Established였습니다. 브라우저 런타임 로그 41,224바이트에서 null-call/page-fault/signal-11은 모두 0건입니다.

## 직접 원인 실측

진단 BoxedWine 런타임은 null indirect call 직전에 caller, operand, 레지스터, vtable 주변 슬롯을 기록했습니다.

```text
D3D9WEB_NULL_CALL caller=7F42A913 operand=7BDD61C8
eax=7BDD6380 ecx=7BDD6058 edx=00000000 esi=082F3068 esp=7F1C2EDC
ret0=7F42A919 slot17=7BDD2740 slot30=7BDD3350 slot86=7BDD2170
```

`operand - ecx = 0x170`이며 32-bit COM vtable slot은 4바이트이므로 slot 92입니다. D3D9 표준에서 slot 92는 `SetVertexShader`입니다. caller가 NULL shader를 설정했는데 프록시 슬롯이 NULL이어서 직접 `EIP=0`으로 분기했습니다.

이 실측은 다음 가설을 폐기합니다.

- **REJECTED:** `Present` 뒤 vtable 자체가 훼손됐다.
- **REJECTED:** 서버 `S2C 0x0064`가 게스트를 깨우지 못했다.
- **REJECTED:** WinSock `FD_READ` 전달이 Plaza 진입을 막았다.

## Wine trace에서 확인한 실제 표면

`azrok_wine11_d3d_scene_0431_stdout.log` 기준 Plaza 경로에서 프록시에 없던 표준 호출은 다음과 같습니다.

| slot | 메서드 | 관측 |
|---:|---|---:|
| 9 | `GetCreationParameters` | 18 |
| 38 | `GetRenderTarget` | 18 |
| 61 | `EndStateBlock` | 108 |
| 79 | `SetNPatchMode(0)` | 36 |
| 92 | `SetVertexShader(NULL)` | 36 |
| 105 | `GetIndices` | 18 |
| 107 | `SetPixelShader(NULL)` | 36 |

StateBlock 객체의 `Capture`, `Apply`, `Release`도 실제 호출됩니다. `SetNPatchMode`는 StateBlock 기록 상태가 아니라 live state에 즉시 적용되는 Wine 동작을 따랐습니다.

## 프록시 구현

`tools/d3d9_web_backend/d3d9_web.cpp`에 다음을 추가했습니다.

- device 슬롯 9/38/61/79/92/105/107
- `IUnknown` 3개 + `GetDevice`/`Capture`/`Apply`의 6-slot StateBlock 객체
- `BeginStateBlock` 중 transform, viewport, scissor, material, light, render/texture-stage/sampler state, vertex declaration/FVF, stream/index/texture를 독립 기록
- `Capture`는 기록된 키만 현재 live state로 갱신하고 `Apply`는 기록 순서의 의미를 보존해 재적용
- declaration과 FVF를 상호 배타적인 vertex-input tag로 보관하며 COM 자원 참조 수명 보존
- `GetRenderTarget(0)`은 현재 구현 범위에서 backbuffer를 반환

빌드 뒤 패키지 내부 `d3d9.dll`을 다시 추출해 위 SHA-256과 일치하는 것도 확인했습니다.

## 자연 전환 동적 증거

2026-07-22 KST 최신 세션의 정확한 순서는 다음과 같습니다.

```text
08:27:03.781  C2S 0019[00]
08:27:03.789  S2C 000D[00]
08:27:04.173~08:27:04.512  calibration heartbeat
08:27:15.241  C2S 0064[01]
08:27:15.248  S2C 0064, entry kind 0A, entity 1
08:27:34.805~08:29:05.018  C2S/S2C 0016 heartbeat 10회 연속
```

서버 상태는 `room_kind=27`, `room_name=plaza (0064-only)`, `door_0019_seen=true`, `full_0064_sent=true`, `plaza_clients=1`이었습니다. 화면에서는 Plaza 지형, 바나나 오브젝트, 캐릭터와 UI가 정상 렌더됐습니다.

## 남은 경계

- **NOT VERIFIED:** 두 브라우저 세션의 reciprocal actor 표시, 이동 `0x0068`, targeted leave `0x0067`.
- **NOT VERIFIED:** 비NULL vertex/pixel shader 객체. 현재 관측 전환은 NULL bind만 사용하지만 `Data/sun.fx`의 실제 shader object 생성/실행은 별도 구현 게이트입니다.
- **NOT VERIFIED:** Pointer Lock은 문서 251의 표준 브라우저 root-document 검증이 남아 있습니다.

