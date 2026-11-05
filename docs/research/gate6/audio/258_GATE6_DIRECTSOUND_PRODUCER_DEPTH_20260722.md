# Gate 6 — DirectSound 80 ms 생산 수위로 브라우저 BGM 페이싱 복구 (2026-07-22)

## 결론

- **VERIFIED (static):** 이 BGM 경로는 `K_POLLOUT`이나 `BoxedWineCondition`으로 깨어나지 않는다. Wine 11 `wineoss`의 `audio_client_timer`가 10 ms마다 `NtDelayExecution`에서 돌아와 비차단 `GETOSPACE + write`를 수행한다.
- **VERIFIED (static):** 8192-byte OSS fragment 실험은 wineoss의 쓰기 허용량만 약 69.66 ms로 늘렸다. DirectSound는 `dlls/dsound/primary.c`에서 `aclen_frames = min(acbuf_frames, 3 * frag_frames)`로 실제 생산 PCM을 약 31.97 ms에 제한했으므로 효과가 거의 없었다.
- **VERIFIED (implementation):** `aclen_frames = acbuf_frames`로 바꿔 게임이 이미 요청한 약 80 ms 버퍼 전체를 생산하도록 했다. 가짜 지연 보고, 합성 무음, BoxedWine 큐 팽창은 사용하지 않았다.
- **VERIFIED (30 s WASAPI + source comparison):** exact-zero는 `2.304722% -> 0.251528%`로 89.1% 감소했고, 10 ms 이상 공백은 `6회 -> 0회`, 최장 공백은 `31.063 ms -> 9.000 ms`로 줄었다.
- **VERIFIED (30 s source comparison):** 원본 진행률 기울기는 `0.9975669 source-sec/capture-sec`, `R²=0.999999815`, 최대 위치 잔차 `7.584 ms`다. 63-band spectral-temporal fingerprint 평균 cosine은 `0.98998`이고, 의도적으로 10초 어긋난 비교는 `0.64710`이다. 음악 내용·피치·속도가 원본과 직접 일치한다.

## 30초 A/B

| 빌드 | exact-zero | >=5 ms | >=10 ms | >=20 ms | 최장 |
|---|---:|---:|---:|---:|---:|
| 이전 최선 `jit9`, DirectSound 약 32 ms | 2.304722% | 40 / 0.510750 s | 17 / 0.339292 s | 6 / 0.161542 s | 31.063 ms |
| **`upstreamjit16 + dsound80ms1`** | **0.251528%** | **5 / 0.037667 s** | **0** | **0** | **9.000 ms** |

## 원인 판정

브라우저의 timed wait가 간헐적으로 25~62 ms 늦게 복귀하는 현상 자체는 존재한다. 그러나 이 경로는 별도 신호 발신자가 없는 Wine의 10 ms 폴링 타이머이므로, `POLLOUT` 깨우기 수정은 실행 경로에 닿지 않는다. 실제 고장 조건은 DirectSound 생산 수위 약 32 ms가 그 스케줄링 지터보다 얕았다는 것이다. 게임이 요청한 80 ms까지 실제 PCM을 미리 생산하자 guest 입력의 `zeroframes`는 관측 창마다 0이었고 SDL 큐가 대부분 0 위를 유지했으며 긴 host underflow가 사라졌다.

따라서 이는 **BoxedWine condition missed-wake 버그가 아니라, 브라우저 스케줄링 지터와 Wine DirectSound의 보수적인 3-fragment 생산 제한이 결합된 문제**로 판정한다.

## 산출물

- 수정 소스: `artifacts/wine11_source/wine-11.0/dlls/dsound/primary.c`
- 32-bit Unix Wine DLL: `artifacts/runtime/dsound80ms1/dsound.dll.so`
  - SHA-256: `5D427860505CEFD5C089D45BA1164367899A4EB2AEE24C5C3B7DC6B37A6E7F62`
- 게스트 root: `tools/boxedwine_local/fs/TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1.zip`
  - SHA-256: `329BEA48852C33C7937B9848EE37500060C31ADFA751F75CA256A8532EED4228`
- 계측 runtime: `tools/boxedwine_local/assets_d3d9web/boxedwine.upstreamjit16audiozero.{js,wasm}`
- 30초 증거: `docs/research/evidence/upstreamjit16_dsound80ms_30s_20260722.wav`
- 100초 자연 루프 증거: `docs/research/evidence/upstreamjit16_dsound80ms_100s_20260722.wav`

## 남은 검증

- **VERIFIED:** 100초 캡처는 `capture 22 s -> source 82.34725 s`, `27 s -> source 1.69550 s`, `97 s -> source 71.29650 s`로 tail-to-head 자연 루프와 두 번째 cycle PCM을 직접 확인했다. 두 번째 cycle spectral fingerprint 평균은 `0.98335`다.
- **PARTIAL / 새 결함:** 루프 경계 `25.023229~25.323438 s`에 실제 `300.208 ms` 무음이 남았다. 안정적인 두 번째 cycle `32~97 s` 진행률은 `0.995854`지만, 전체 exact-zero는 `1.563646%`이고 >=10 ms 공백이 25회다. Soundcard의 DATA_DISCONTINUITY 경고는 0을 삽입하지 않으며 source-time 손실과 exact-zero가 거의 1:1이므로 캡처 도구가 합성한 공백이 아니다.
- **VERIFIED release visual:** 계측 제거 `boxedwine.upstreamjit17release`가 같은 한 탭에서 선택 화면을 거쳐 intact PatHouse를 렌더했다. 오디오 루프 경계 수정 후 최종 회귀가 다시 필요하다.
