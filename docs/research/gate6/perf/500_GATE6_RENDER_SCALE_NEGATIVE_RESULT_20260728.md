# 500 Gate 6 render-scale negative result (2026-07-28)

## VERIFIED

- PatHouse의 실제 in-app browser 장면에서 `renderScale=0.75`는 화면 비율과
  BGM 재생을 유지했지만, GPU profile은 `avg_us=6561`, host JS profile은
  `avg_us=7571`, HUD는 약 39.5 FPS였다. 기존 정상 장면의 약 40 FPS 경계와
  비교해 유의한 개선이 없다.
- 이 구현은 축소 FBO를 원래 1024x768 WebGL 기본 프레임버퍼로 Present
  blit한다. 따라서 실제 병목인 Present/합성 비용을 피하지 못한다.
- WebGL 기본 프레임버퍼도 축소하고 CSS만 논리 해상도로 확대하는 후속
  실험은 초기화 뒤 640x480 검은 출력 및 Present HUD 미갱신을 만들었다.
  해당 변경은 즉시 되돌렸고, 정상 모듈 cache key를 갱신한 뒤 선택 화면,
  1024x768 D3D overlay, BGM 재생을 다시 직접 확인했다.

## NOT VERIFIED

- render-scale을 채택 가능한 성능 수단으로 판단할 근거는 없다. 축소 출력
  버퍼의 초기화/리소스 수명 불변식을 별도로 증명하기 전에는 재시도하지
  않는다.

## Next

`DRAW_PRIMITIVE_UP` 다수 호출을 줄이는 host `upBatch`를 기존 `upRing`
조건과 분리한 시각/Present A-B-A 실측으로 검증한다.
