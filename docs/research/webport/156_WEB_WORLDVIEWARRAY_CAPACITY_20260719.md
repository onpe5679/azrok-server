# 156 — 웹 이식 FFP 셰이더 `worldViewArray` 용량 확장 (64 → 256)

**날짜**: 2026-07-19
**관련**: 154 (world matrix slot 256..317 실측, 최소 62개), 150 (웹 이식 백엔드 설계)
**상태**: VERIFIED (실제 WebGL2 드라이버로 컴파일/링크/드로우 재확인 + 라운드트립 5/5 통과)

## 배경

154에서 캐릭터 선택 화면의 `SetTransform` 인자 히스토그램을 실측한 결과, 64개
고유 슬롯 테이블이 가득 찼고 실제 값은 fixed 2/3 + **world matrix 256..317**
(D3DTS_WORLDMATRIX 0..61, 즉 최소 62개)였다. 반면 웹 이식 셰이더
(`tools/web_backend/shaders/d3d9_ffp.vert`)는 vertex blending/skinning용
`worldViewArray`를 `MAX_BLEND_MATRICES = 64`로 임시 제한해뒀다
(`PORTING_NOTES.md`에 "64 is a placeholder, not a measured requirement"로
명시). 여유가 단 2칸뿐이라 실사용 콘텐츠에서 오버플로우할 위험이 있었다.

## 실측한 제약 (하네스로 실제 WebGL2 컨텍스트 측정)

`tools/web_backend/harness/index.html`에 `MAX_VERTEX_UNIFORM_COMPONENTS` /
`MAX_COMBINED_VERTEX_UNIFORM_COMPONENTS` 로깅을 추가하고
`node tools/web_backend/harness/run-headless.js`(실제 시스템 Chrome, ANGLE)로
측정:

```
MAX_VERTEX_UNIFORM_BLOCKS: 14
MAX_UNIFORM_BLOCK_SIZE: 65536
MAX_VERTEX_UNIFORM_COMPONENTS: 16384
MAX_COMBINED_VERTEX_UNIFORM_COMPONENTS: 245760
```

`MAX_VERTEX_UNIFORM_COMPONENTS`는 UBO가 아닌 default-block 유니폼에만 적용되므로
`worldViewArray`(uniform block 내부)의 진짜 제약은 아니다 — 실제 governing
값은 블록당 상한 `MAX_UNIFORM_BLOCK_SIZE`와, 전체 vertex 유니폼(블록+
default-block 합산) 상한 `MAX_COMBINED_VERTEX_UNIFORM_COMPONENTS`다.

std140에서 `mat4` = 64바이트(16바이트 정렬 vec4 컬럼 4개). D3D9의
`D3DTS_WORLDMATRIX(i)`는 `i`가 0..255에서만 정의되는 하드 상한이므로,
256개면 D3D9가 만들 수 있는 어떤 인덱스도 놓치지 않는다.

- 256 × 64B = **정확히 16384바이트**. 이는 WebGL2 스펙이 보장하는
  `MAX_UNIFORM_BLOCK_SIZE` 최소값과 정확히 같다 — 즉 스펙을 준수하는 **모든**
  WebGL2 구현에서 이 배열 하나가 단일 유니폼 블록에 들어간다는 뜻이며, 이
  환경에서 실측한 65536바이트의 약 1/4만 사용한다.
- vertex 쪽 3개 블록 합계(`FFVertexData` 2096B + `FFClipPlanes` 96B +
  `FFBlendMatrices` 16384B ≈ 18576B ≈ 4644 word)는 실측 combined 예산
  (245760 word)은 물론 스펙 최소 combined 예산(약 50176 word)에도 충분히
  못 미친다.

## 결정: 256

D3D9 API 자체의 `D3DTS_WORLDMATRIX` 인덱스 상한(0..255)과 정확히 일치하며,
위 실측/계산으로 단일 블록·combined 예산 모두에서 여유가 크다는 것을 확인했다.
"충분히 크게"가 아니라 "D3D9가 낼 수 있는 값을 전부 커버"하는 숫자를 골랐다.

## 변경 파일

- `tools/web_backend/shaders/d3d9_ffp.vert`: `MAX_BLEND_MATRICES` 64u→256u,
  `worldViewArray[64]`→`[256]`, 근거 주석 갱신.
- `tools/web_backend/host/ffp-constants.js`: `MAX_BLEND_MATRICES = 256` export
  추가 (JS 쪽 단일 진실원).
- `tools/web_backend/host/ffp-state.js`: `blendMatrices` 배열 길이를
  하드코딩 64 대신 `MAX_BLEND_MATRICES`로.
- `tools/web_backend/host/pack-ffp.js`: `packFFBlendMatrices`의 루프 상한을
  하드코딩 64 대신 `MAX_BLEND_MATRICES`로. std140 오프셋 자체는 여전히
  런타임 질의(`queryBaseElementLayout`/`elementOffset`), 하드코딩 없음.
- `tools/web_backend/harness/index.html`: 위 측정을 위한 로깅 2줄 추가.
- `tools/web_backend/host/roundtrip/index.html`: **Test D** 추가 — 배열의
  새 마지막 원소 `worldViewArray[255]`가 std140 오프셋 질의로 정상
  접근되는지, 실제 드로우콜(정점 블렌딩 인덱스 255, 방향광 lighting 색상
  비교)로 검증. Negative-control(z-flip 제거 시 4/5로 FAIL)로 이 테스트가
  실제로 구분 능력이 있음을 확인.
- `tools/web_backend/shaders/UNIFORMS.md`, `PORTING_NOTES.md`,
  `tools/web_backend/harness/README.md`, `tools/web_backend/host/README.md`:
  새 용량·근거·측정치 반영.

## 검증 (실행 결과 원문)

`node tools/web_backend/harness/run-headless.js`:
```
--- d3d9_ffp.vert compile status: SUCCESS ---
--- d3d9_ffp.frag compile status: SUCCESS ---
--- Program link status: SUCCESS ---
Active uniform blocks (5):
  [2] FFBlendMatrices dataSize=16384 bytes
Draw attempt (dummy zeroed UBOs + 1x1 textures, gl.POINTS x1): NO GL ERROR
OVERALL: PASS (both shaders compiled and linked)
```

`node tools/web_backend/host/roundtrip/run-headless.js`:
```
[PASS] A: stage0 SELECTARG1(TFACTOR) reproduces packed D3DCOLOR
[PASS] B: directional light Diffuse reproduces packed Light/Material state
[PASS] C1: alphaRef=100 < alpha=128 survives with correct color
[PASS] C2: alphaRef=200 > alpha=128 is discarded (background preserved)
[PASS] D: vertex-blend index 255 resolves to worldViewArray[MAX_BLEND_MATRICES-1] (the last element)
=== 5/5 round-trip tests passed ===
OVERALL: PASS
```

Negative control (테스트 D의 z-flip을 identity로 되돌린 임시 변경 후 재실행):
`=== 4/5 round-trip tests passed === / OVERALL: FAIL` → 원복 후 5/5 재확인.

## 남은 위험 / NOT VERIFIED

- 동시(비인덱스, `vertexBlendCount>0`) 다중 블렌딩 실사용 빈도는 이번 조사
  범위 밖(154는 인덱스 범위만 측정했지 프레임당 동시 블렌드 수는 아님).
- 256을 넘는 인덱스는 D3D9 자체가 낼 수 없으므로 이론상 문제 없음(클램프
  코드는 방어적으로 유지).
- 게임 실제 컨텐츠(텍스처/버텍스 버퍼 포함)로 렌더링 결과의 시각적 정확성은
  여전히 미검증 — 이번 작업은 셰이더 컴파일/링크/패킹 계약만 검증한다
  (harness/roundtrip의 원래 범위와 동일).
