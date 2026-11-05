# 481 Gate 6 embedded MediaElement BGM output repair (2026-07-28)

## 결론

- **VERIFIED:** 현재 내장 브라우저의 원래 BGM fallback `<audio>` 엘리먼트는 `paused=false`, `readyState=4`, 재생 시간이 진행 중이어도 `volume` 속성과 프로토타입 API가 모두 `undefined`였습니다. 즉 기존의 "재생 중" DOM 상태는 실제 PCM 출력의 근거가 될 수 없었습니다.
- **VERIFIED:** `index_d3d9web_pathouse.html`의 fallback을 Web Audio (`AudioContext` → `GainNode` → `destination`) 우선 경로로 교체했습니다. 원본 `PetHouse.mp3`를 same-origin에서 fetch/decode한 후 launch 클릭 안에서 resume된 context로 loop 재생하며, HTML media element는 호환성 fallback으로만 남겼습니다.
- **VERIFIED:** 새로 고친 private HTTPS 탭을 reload한 뒤 실제 `오디오 활성화 후 Azrok 실행`을 클릭하여 상태 `playing`, transport `webaudio`, track `PetHouse.mp3`, error 없음 및 원래 media element `paused=true`를 확인했습니다.
- **NOT VERIFIED:** 이 자동화 표면은 스피커에서 나온 공기 진동을 계측하지 못하므로, 사용자의 실제 청취 확인은 별도로 필요합니다. 다만 효과음과 동일한 Web Audio destination을 사용하도록 출력 경로 자체는 바뀌었습니다.

## 구현 경계

- 파일: `tools/boxedwine_local/index_d3d9web_pathouse.html`
- `beginWebAudio()`는 사용자 launch/rearm 제스처 안에서 `AudioContext.resume()`을 수행하고, MP3 decode 완료 후 `AudioBufferSourceNode`를 loop로 시작합니다.
- 트랙 전환과 `BGM 다시 재생`은 활성 source를 stop/disconnect한 뒤 같은 경로에서 새 source를 만듭니다.
- `AudioContext` 또는 decode가 없는 일반 브라우저만 기존 HTML `<audio>` fallback을 사용합니다.

## 재현/검증

1. private HTTPS 페이지를 새로고침합니다.
2. `오디오 활성화 후 Azrok 실행`을 한 번 클릭합니다.
3. 페이지의 `runtime-status` dataset에서 `webBgmFallback=playing`, `webBgmFallbackTransport=webaudio`, `webBgmFallbackTrack=PetHouse.mp3`인지 확인합니다.
4. 들리지 않으면 `BGM 다시 재생`을 클릭합니다. 이 동작은 기존 source를 제거하고 클릭 제스처에 새 Web Audio source를 연결합니다.

