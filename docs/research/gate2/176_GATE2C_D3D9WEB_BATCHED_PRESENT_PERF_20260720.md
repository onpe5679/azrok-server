# 176 — Gate 2c D3D9Web `Present` 배치 성능 측정 (2026-07-20)

## 범위

브라우저 BoxedWine 멀티스레드 빌드에서 PatHouse 렌더 루프만 측정했다.
콘텐츠 진행·QA는 하지 않았다.

## VERIFIED — 병목 분리

배치 전, 동일한 `pathouseav` 브라우저 세션의 10초 표본은
`119808:852` → `152576:1001`이었다. 즉 `Present` 149회, 약 **14.9 FPS**다.

호스트 WebGL 명령 실행 시간은 64개 명령마다 표본을 수집했다.
해당 실행의 누적 표본은 평균 **0.078 ms**, 최대 **6.505 ms**였다.
따라서 WebGL 함수 본문만으로는 전체 약 67ms 프레임 시간을 설명할 수 없었다.

정적 코드도 일치한다. `d3d9web.cpp`의 멀티스레드 경로는 매 guest D3D 명령마다
`MAIN_THREAD_EM_ASM_INT`를 호출하고 결과를 기다렸다. 프레임당 수백 번의 동기 worker→main
왕복이 있었다.

## VERIFIED — 구현과 실행 결과

`source/opengl/d3d9web.cpp`에 길이 접두 패킷 배치를 추가했다.

- 상태·바인드·드로우·`Present`는 worker 측에 순서대로 누적한다.
- `Present`에서 `dispatchBatch` 한 번으로 main-thread WebGL에 전달한다.
- 텍스처/버퍼/선언의 생성·업로드·해제는 앞선 queued indexed draw를 먼저 flush한 뒤 여전히 동기로
  처리한다. 리소스 쓰기가 과거 draw를 앞지르지 않는다.
- JS `dispatchBatch`는 각 원래 패킷을 기존 `dispatch`에 순서대로 넘긴다. 새 렌더 의미론은 없다.

새 WASM/JS 쌍을 `tools/boxedwine_local/assets_d3d9web/boxedwine.pathouseav.{js,wasm}`에 같이 배포했다.
배치 실행 10초 표본은 `265216:1564` → `317440:1801`: `Present` **237회**, 약 **23.7 FPS**였다.
`D3D9WEB_PHASE6_ERROR`는 0건이었다. 이는 배치 전보다 약 59% 상승이며, PatHouse 렌더가 계속된
직접 실행 증거다.

## VERIFIED — 폐기한 미세 최적화

`preserveDrawingBuffer=false`는 같은 방법으로 약 **22.8 FPS**(`1163` → `1391` Present/10초)였고
개선이 없었다. 유지하지 않고 원래 `true`로 복원했다.

## VERIFIED — draw 검증 및 텍스처 바인드 캐시

매 draw 뒤 `gl.getError()`를 호출하던 검증은 256 draw마다 한 번으로 표본화했다.
PatHouse 10초 표본은 `1303` → `1615` Present, 약 **31.2 FPS**, 오류 0건이었다.
이는 오류 질의가 실제 hot-path 비용이었음을 직접 보인다.

그 다음 모든 draw마다 8개 stage에 반복하던 texture bind/sampler parameter 호출을, 실제
texture handle 또는 sampler state가 바뀐 stage에만 수행하도록 캐시했다. 표본은
`1427` → `1748` Present/10초, 약 **32.1 FPS**, 오류 0건이었다. 작은 이득이지만 렌더 의미론
변경 없이 계속 PatHouse를 그렸다.

마지막으로 매 draw마다 16 attribute를 일괄 disable/enable/pointer 설정하던 호출을, 실제
vertex layout 또는 source buffer가 바뀔 때만 재설정하도록 캐시했다. 표본은
`1698` → `2042` Present/10초, 약 **34.4 FPS**, 오류 0건이었다.

UBO 전체 업로드를 상태 변경 때만 하도록 한 후속 실험은 약 **33.5 FPS**로 이득이 없었다.
상태 캐시 복잡도만 늘리므로 해당 실험은 폐기하고 34.4 FPS 경로로 복원했다.

## 다음

50 FPS는 아직 **NOT VERIFIED**다. 배치 후 남은 비용은 BoxedWine x86 인터프리터 실행과
남은 WebGL draw 호출을 분리해 추가 측정한 뒤 결정한다.
