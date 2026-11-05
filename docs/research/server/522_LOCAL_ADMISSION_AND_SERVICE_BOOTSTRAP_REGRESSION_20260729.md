# 522 로컬 접속 차단과 서비스 기동 회귀 (2026-07-29)

날짜: 2026-07-29
범위: `tools/run_browser_runtime_services.ps1`, `tools/ws_tcp_bridge.py`, 브라우저 런타임 선택 경로.
원본 실행파일·게임 자산·바이너리는 건드리지 않았다.

## 1. 서비스 기동이 조용히 반쪽만 되는 결함 (VERIFIED)

- `run_browser_runtime_services.ps1` 는 브리지 인자에 `'--instance-token', $InstanceToken` 을
  무조건 넣는다. 토큰 없이 실행하면 그 원소가 **빈 문자열**이 되고,
  `Start-Process -ArgumentList` 의 `ValidateNotNullOrEmpty` 가 배열 원소 검증에서 이를 거부한다.
- 결과: 예외가 `try/finally` 블록보다 앞에서 발생하므로 **코어(9200/9300)만 살아남고
  브리지(9201)와 자산 서버(8765)는 아예 시작되지 않으며, finally 정리도 돌지 않는다.**
  로그 파일은 0바이트라 실패가 눈에 띄지 않는다.
- 실측: 2026-07-29 02:2x 기동에서 9200/9300 만 LISTEN, 8765/9201 down.
  오류 원문 `'ArgumentList' 매개 변수에 대한 인수의 유효성을 검사할 수 없습니다`.
- `ws_tcp_bridge.py` 의 `--instance-token` 은 `default=""` 인 선택 인자이므로,
  비어 있을 때는 인자를 넘기지 않는 것이 맞다. 그렇게 수정했고 4포트 모두 LISTEN 을 확인했다.

## 2. 로컬 루프백 접속이 전부 거부되고 있었다 (VERIFIED)

`tools/ws_tcp_bridge.py::request_has_admission` 은 다음과 같다.

```python
if expected_token and hmac.compare_digest(supplied, expected_token):
    return True
return access_secret is not None and validate_browser_ticket(access_secret, supplied)
```

- `--instance-token` 도 `--access-secret-file` 도 주지 않으면 **두 분기 모두 거짓**이 되어
  루프백 연결까지 예외 없이 거부된다. 시작 로그가 `admission=loopback-only` 라고 찍히지만
  실제 판정은 토큰을 요구한다.
- 실측 거부 3건 (KST): `02:57:59`, `03:06:06`, `03:20:23`,
  모두 `WS_REJECT peer=('127.0.0.1', …) reason=bad_private_admission`.
- **게임 쪽 증상은 클라이언트 자체 팝업 `연결이 종료되었…`** 이다. 브라우저 오류 화면이 아니라
  원본 UI가 그리는 대화상자이므로, 화면만 보면 브라우저 문제로 오인하기 쉽다.
- `-InstanceToken` 을 주고 페이지 URL 에 `&instance=<토큰>` 을 붙이면
  브리지가 `admission=legacy-token` 으로 올라오고 페이지가 ws 주소에 토큰을 덧붙인다
  (`index_d3d9web_pathouse.html` 398~400행의 `Module.websocket.url`).

### 판단

게이트7의 사설 티켓 도입(#519·#521) 이후 **토큰 없는 로컬 실행 경로가 사라졌다.**
LAN/Tailscale 을 잠그는 것은 의도된 설계지만, 루프백 개발 실행까지 같은 게이트를 통과해야 하는 것은
문서에 남아 있지 않았다. 최소 수정 두 가지 중 하나가 필요하다.

1. (무위험) 로컬 실행 시 항상 `-InstanceToken` 과 URL `&instance=` 를 쌍으로 쓴다. 지금 채택.
2. (코드 수정) 피어가 루프백이고 토큰·시크릿이 모두 미설정일 때만 허용하도록 되돌린다.
   사설 대역 정책은 `is_private_client` 가 이미 별도로 강제하므로 공개 노출 위험은 늘지 않는다.
   **아직 적용하지 않았다.**

## 3. 07-22 오디오 검증 런타임은 아직 살아 있다 (VERIFIED)

- `assets_d3d9web/boxedwine.upstreamjit14audiobest.wasm` (2.7MB, 07-22 10:39) 가 남아 있고,
  현재 페이지에서 **정상 로드·초기화·렌더**한다. `D3D9WEB_PHASE6_FFP_INIT webgl2=1` 와
  연속 `D3D9WEB_FPS_SAMPLE` 를 확인했다.
- 다만 두 가지 함정이 있다.
  - 페이지는 `jitCacheUrl` 을 **현재 ABI 전용 그룹 캐시로 기본 설정**한다(223행).
    옛 런타임에 그 캐시를 물리면 `JIT 그룹 캐시 준비 중` 에서 멈춘다. `jitCacheUrl=off` 필요.
  - `audioGesture` 가 있으면 자동 시작이 걸리지 않고 실행 버튼 클릭이 필요하다(1140행).
- 이는 "오디오 회귀가 런타임 교체와 함께 왔는가"를 A/B 로 물을 수 있는 조건이 갖춰졌다는 뜻이다.

## 4. BGM 회귀 A/B — 두 가설 기각 (VERIFIED)

측정 방법: `webBgmFallback=0` 으로 브라우저 대행 재생을 끄고, 매 leg 마다 **새 Edge 프로필**
(IndexedDB 비어 있음)로 부팅한 뒤 펫하우스 도달 상태에서 30초를 잰다. 두 축을 동시에 본다.

- **guestTap**: `Module.SDL2.audio.scriptProcessorNode.onaudioprocess` 를 감싸 게스트가 실제로
  써 넣는 출력 버퍼를 직접 센다. 시스템 믹서와 무관하다.
- **loopback**: `tools/capture_loopback.py` 30초 + `Data/Sound/*.mp3` 15곡 포락선 상관.

| leg | 런타임 | root | 앱 | guestTap | 상관 |
|---|---|---|---|---|---|
| A | `upstreamjit14audiobest` (07-22 오디오 검증본) | `…-bgmloop3-dsound80ms1` | stateblock1 | 콜백 140회, nz 0, max 0 | 0.000 |
| B | 같음 | **`…-bgmloop3`** (dsound80ms 이전) | stateblock1 | 콜백 **713회, nz 0, max 0** | 0.000 |
| C | `upstreamjit64fn6inlineabi2` (현재) | `…-dsound80ms1` | guesttexrecycle4 | 콜백 713회, nz 0, max 0 | 0.000 |

- 세 leg 모두 `Module.SDL2.audioContext` 가 `state=running`, 48 kHz, currentTime 260~345초였다.
  **오디오 컨텍스트는 정지 상태가 아니며, 흘려보낼 PCM 이 없는 것이다.**
- 측정 경로 대조군: 같은 탭에서 440 Hz OscillatorNode 를 울리자 루프백이 RMS `0.069579`,
  peak `0.0984`, 비영 383,884/384,000 으로 잡았다. 무음 판정은 도구 결함이 아니다.
- 첫 측정에서 RMS 0.116 이 나왔던 것은 같은 기계에서 재생 중이던 다른 영상 소리였고 폐기했다.
  `capture_loopback.py` 는 시스템 기본 출력 전체를 뜬다는 점을 항상 같이 기록할 것.

### 기각된 가설

1. **"성능용 JIT 런타임 교체가 오디오를 깨뜨렸다"** — leg A 로 기각. 07-22 오디오 검증 런타임을
   그대로 되돌려도 BGM 이 없다.
2. **"258 의 DirectSound 80 ms 수위 변경(root)이 범인이다"** — leg B 로 기각. 그 변경 이전 root
   에서도 BGM 이 없다.

### leg D — 게스트는 MP3 를 실제로 연다 (VERIFIED, 결정적)

같은 프로덕션 조합에서 `webBgmFallback=1` 로 되돌려 게스트 FS 관찰자를 켜고 측정한 라이브 상태:

```text
webBgmFallbackObserver     = installed
webBgmFallbackGuestRequest = intro.mp3      at 69302.905 ms
webBgmFallback             = playing        at 69328.875 ms   (게스트 open 25.97 ms 뒤)
webBgmFallbackTransport    = media-element
audio element              = paused:false, currentTime 21.2 s, volume 1, src intro.mp3
```

- **원본 실행파일이 `intro.mp3` 를 여는 것까지는 정상**이다. 따라서 실패는 게임의 사운드 초기화나
  설정이 아니라 그 이후 게스트 내부 디코딩 경로에 있다.
- leg A·B·C 가 완전 무음이었던 것과 모순되지 않는다. 그 leg 들은 대행을 껐으므로
  "게스트가 열지만 디코딩에서 죽는다" 상태에서 소리가 하나도 남지 않는 것이 정상이다.
- 사용자가 실제로 들은 소리는 이 대행 재생이며, 게스트가 낸 소리가 아니다.

### 측정 절차상의 정정 (중요)

leg D(03:56:26 시작)와 leg E(03:59:27 시작)를 **같은 탭에 겹쳐 실행했다.** leg E 의 `Page.navigate`
가 leg D 의 페이지를 파괴했으므로, leg D 스크립트가 04:01:30 에 잰 20초 창은 실제로는 leg E 의
페이지를 잰 것이다(그 시점 `bgmDataset` 에 `webBgm*` 키가 하나도 없는 것이 증거).

- **무효**: leg D 의 루프백 20초 수치.
- **유효**: leg D 페이지가 살아 있는 동안 라이브로 읽은 `guestReq=intro.mp3` / `fallback=playing`
  / `currentTime 21.2 s` 상태. 사용자의 청취 보고와도 일치한다.
- **유효**: leg A·B·C·E·F 의 guestTap 결과(각각 단독 실행).
- 규칙: leg 는 절대 겹쳐 돌리지 않는다. 한 탭에 한 leg.

### leg E·F — 진단 root 는 아직 쓸 수 없다 (VERIFIED)

| leg | 조건 | 결과 |
|---|---|---|
| E | root `…-dsound80ms1-winegstrace3`, 현재 런타임 | guestTap 콜백 360회 nz 0. 캔버스 클릭 3회 뒤에도 149회 nz 0 |
| F | 같은 root + `&lean=0` | `#output` 길이 **0**. `dumpAudioLog()` → `AUDIO_LOG_ERROR` (`/d_drive/audio_graph.log` 없음) |

- `lean=0` 으로도 게스트 로그 싱크가 채워지지 않았다. `#output` 은 `dumpAcklog()`/`dumpAudioLog()`
  가 게스트 FS 에서 파일을 읽어 채우는 용도이며, 그 파일 자체가 생성되지 않는다.
- **`winegstrace1/2/3` root 는 어떤 문서에도 등장하지 않는다.** 2026-07-28 09:06~09:22 에 만들어졌지만
  무엇을 켜는지, 어디에 쓰는지 기록이 없다. 사용 전에 zip 내부(런처 bat, `system.reg`, `WINEDEBUG`
  설정)를 직접 열어 확인해야 한다.
- 캔버스 정중앙 클릭으로는 어떤 leg 에서도 효과음 PCM 이 나오지 않았다. 빈 바닥을 눌렀을 가능성이
  높아 **효과음 재현은 아직 실패**이며, 사용자 청취 보고와 별개로 계측으로는 미확인이다.

### 다음 단계 (순서)

1. `…winegstrace3.zip` 내부를 열어 트레이스 활성 방식과 출력 경로를 확인한다. 없으면 `WINEDEBUG`
   를 명시적으로 주는 실행 경로를 만든다.
2. 대행을 켠 상태에서 **같은 순간**에 오디오 엘리먼트 상태와 루프백을 함께 읽어, 루프백 축이
   브라우저 재생을 제대로 잡는지 한 번 검증한다.
3. 그 뒤에 `0xc0000005` 발생 지점을 실측한다.

### 남은 유력 지점

`#461`·`#462`·`#463` 이 이미 잡아 둔 게스트 내부 실패가 그대로 유효하다: Quartz 스플리터 생성이
전 클래스 `0x8007000e`, 그 아래 winegstreamer 32비트 Unix-call 콜백에서 `0xc0000005`.
`fs/` 에 07-28 09:0x~09:22 에 만들어진 `…-dsound80ms1-winegstrace1/2/3.zip` 진단 root 가 있으므로,
빌드 계보를 더 뒤지는 대신 그 root 로 실패 순간의 Wine 로그를 직접 받는 것이 다음 단계다.

## 5. 아직 확정되지 않은 것 (NOT VERIFIED)

- 옛 런타임에서 원본 BGM 이 실제로 나는가. `webBgmFallback=0` 으로 브라우저 대행을 끈 채
  25초 WASAPI 루프백을 떴을 때 **비영 샘플 0개, RMS 0.0** 이었으나,
  그 시점의 게스트는 아직 씬에 도달하지 못했고 직후 브리지 거부로 연결이 끊겼다.
  씬 도달 후 재측정해야 한다.
- 측정 방법 주의: `tools/capture_loopback.py` 는 **시스템 기본 출력 전체**를 뜬다.
  같은 기계에서 다른 소리(브라우저 영상 등)가 나면 그대로 섞인다.
  실제로 첫 측정에서 RMS 0.116 이 나왔으나 이는 게임이 아닌 다른 재생물이었고 폐기했다.
  판별은 `Data/Sound/*.mp3` 15곡과의 포락선 정규화 상관으로 한다(#250·#257 방식).
