# 551. Korean5 currentabi1 explicit relocation reserve (2026-08-07)

## Scope

#550이 currentabi1 archive manifest의 relocation map base를 `12968152`로 잘못 판독해 korean4를 호환 runtime으로 승격한 오류를 정정한다. archive/manifest를 직접 읽고 runtime export를 동일한 Node harness로 비교한 뒤, manifest를 수정하지 않고 runtime 자체에 명시적인 256-byte ABI reserve를 추가했다. 실제 게임은 실행하지 않았다.

## VERIFIED — authoritative archive contract

- 기본 archive `azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2-currentabi1.zip`은 4,804,035 bytes, SHA-256 `B007FA84AC483360389D136FA45682EF774B8A7B19F8CBF214CEF1D4A389035A`다.
- archive 내부 `boxedwine-jit-grouped-manifest.json`은 12,963,687 bytes, SHA-256 `E0E63B45A20BF533332E8FAF13B7660391E830BE1235518A12E1383683B62696`다.
- manifest의 `source.runtimeGenericIndirect`는 `relocMapBase=12968408`, `relocMapCapacity=262144`다. #550의 `12968152` 주장은 틀렸다.
- Node direct WASM export 비교:
  - korean1: `12968408/262144`
  - korean2: `12968408/262144`
  - korean3: `12968152/262144`
  - korean4: `12968152/262144`
- 따라서 korean3/4가 currentabi1과 맞지 않아 admission에서 중단된 것이 정상이며, manifest를 `12968152`로 바꾸는 것은 기존 archive 계약을 깨뜨린다.

## VERIFIED — explicit ABI reserve

- `jitWasmCodeGen.cpp`의 backing을 `CAPACITY + 64` U32로 확장했다.
- usable pointer는 `storage + 64`로 정의했다. 64 U32는 정확히 256 bytes다.
- 기존 publish의 `base[tableIndex]`, capacity bounds, atomic store, worker table/ready-bitmap capacity는 전부 usable pointer와 기존 capacity를 그대로 사용한다. 인덱스 의미와 worker semantics는 바뀌지 않는다.
- unrelated static data나 linker alignment가 우연히 256 bytes를 공급하기를 기대하지 않으며 reserve 자체가 소스 계약으로 드러난다.
- 새 korean5 Node direct export는 정확히 `12968408/262144`다.

## VERIFIED — immutable korean5 deployment

- runtime stem: `boxedwine.upstreamjit64fn6inlineabi2korean5`.
- build id: `ime-xim-currentabi1-reserve64-v1-20260807`.
- korean5 JS: 328,459 bytes, SHA-256 `857BADA4C966F5691989557559A4BC5144F7E337C802CE8765983E39135482DE`.
- korean5 WASM: 3,053,628 bytes, SHA-256 `F98A79681C9E0E78C506F608BD539B234936B9252FD1F027F82837ED13C5B5AE`.
- 기본 page는 korean5 + currentabi1을 선택한다. korean3/4는 cache-off rollback으로 보존한다.
- LAN `<lan-ip>:8765`와 Tailscale `<tailscale-ip>:8765`가 모두 위 korean5 WASM 해시와 currentabi1 archive 해시를 정확히 반환했다.
- 양쪽 live HTML에서 korean5 stem, 새 build id, korean3/4 cache-off rollback guard를 확인했다.

## Verification

- `python -m unittest tools.test_boxedwine_xim_contract tools.test_d3d9web_page_contract`: **22 passed**.
- korean5 generated JS `node --check`: pass.
- Node direct export: `12968408,262144`.
- 테스트가 korean5 WASM, currentabi1 archive, 내부 manifest의 세 SHA-256과 manifest map/capacity를 고정한다.

## NOT VERIFIED

- currentabi1 replay가 실제 브라우저 게임 부팅에서 끝까지 admission·instantiate되는지.
- Wine fake XIM/XIC가 생성되고 Azrok Edit가 완성 한글을 수락하는지.
- Plaza에서 `vvvv`와 라틴 조합 원문 누출이 사라졌는지.
- BGM, 렌더링, 성능 회귀가 없는지.

이 항목들은 사용자의 다음 플레이 테스트 전에는 성공으로 승격하지 않는다.
