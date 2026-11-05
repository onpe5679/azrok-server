> **SUPERSEDED by 551.** #550은 currentabi1 manifest를 `12968152`로 잘못 읽었다. 실제 archive manifest는 `12968408/262144`이며 korean4는 호환되지 않는다.

# 550. Korean4 currentabi1 map identity and locale-literal A/B (2026-08-07)

## Scope

사용자 라이브 부팅에서 korean3 runtime이 generic-indirect relocation map `12968408`을 보고했지만 currentabi1 manifest는 `12968152`를 요구해 Wine 시작 전에 중단됐다. manifest를 새 runtime에 맞춰 완화하지 않고, `XLocaleOfIM`의 정적 문자열이 256-byte 이동을 만들었는지 A/B하고 정확한 ABI를 가진 새 immutable stem을 배포했다. 실제 게임은 실행하지 않았다.

## VERIFIED — live failure and disk baseline

- 사용자 라이브 로그: runtime map `12968408`, manifest map `12968152`, 차이 `256`; replay admission이 의도대로 중단됐다.
- 현재 디스크 korean3 WASM SHA-256 `A3E0160AF4AD1AF7A32CF5045CF0497A8AC501C3406DA4A8A6330AD316CE4520`을 Node `WebAssembly.Instance`로 직접 인스턴스화했다.
- korean3 export 결과는 map `12968152`, capacity `262144`였다. 즉 현재 디스크 korean3 바이트는 currentabi1 계약과 이미 일치한다.
- 따라서 라이브 `12968408`은 현재 디스크 korean3와 동일한 WASM에서 나온 값일 수 없다. 어느 캐시/응답이 선택됐는지는 별도 브라우저 요청 추적 전까지 **INFERRED**이며, 단순 manifest patch 근거로 쓰지 않는다.

## VERIFIED — locale literal hypothesis falsified

- `XLocaleOfIM`의 `static constexpr "ko_KR.UTF-8"`를 제거하고 12-byte guest allocation에 다음 little-endian dword를 직접 썼다: `0x4b5f6f6b`, `0x54552e52`, `0x00382d46`.
- 변형 WASM에는 ASCII `ko_KR.UTF-8` static literal이 존재하지 않는다.
- 변형 WASM export도 map `12968152`, capacity `262144`였다.
- baseline과 변형이 같은 map base를 반환하므로, locale literal이 map을 `+256` 이동시켰다는 가설은 **반증됐다**.

## VERIFIED — immutable korean4 deployment

- 새 stem: `boxedwine.upstreamjit64fn6inlineabi2korean4`.
- build id: `ime-xim-abi-current1-v1-20260807`.
- korean3과 그 자산은 rollback용으로 보존했고, 기본 경로에서만 korean4로 전환했다.
- korean3은 이미 재사용된 URL에서 모순된 라이브 값을 냈으므로 명시적으로 cache-off를 유지한다.
- korean4는 export가 정확히 맞으므로 기본 currentabi1 cache `/profiles/azrok-jit-grouped-commonfast64-depthlocal-inlinefetch2-currentabi1.zip`을 사용한다.
- korean4 JS: 328,459 bytes, SHA-256 `857BADA4C966F5691989557559A4BC5144F7E337C802CE8765983E39135482DE`.
- korean4 WASM: 3,053,628 bytes, SHA-256 `5FE1B3ED1D6E0D8E7B9D80E1F1EB32255593CF860892C146C4A12FDB885AF3DC`.
- LAN HTTPS `<lan-ip>:8765`가 위 JS/WASM과 정확히 같은 길이·해시를 반환했고 HTML에서 korean4/build id/currentabi1을 모두 확인했다.
- Tailscale HTTPS `<tailscale-ip>:8765`도 같은 WASM 길이·해시와 korean4 HTML을 반환했다.

## Verification

- `python -m unittest tools.test_boxedwine_xim_contract tools.test_d3d9web_page_contract`: **19 passed**.
- korean4 generated JS `node --check`: pass.
- Node direct WASM exports: `12968152,262144`.
- LAN/Tailscale served WASM hash equals disk korean4 hash.

## NOT VERIFIED

- Wine이 fake XIM/XIC를 만들고 Azrok Edit에 완성 한글을 수락하는지.
- 실제 Plaza에서 `vvvv`와 라틴 조합 원문 누출이 사라졌는지.
- currentabi1 replay가 실제 게임 부팅과 플레이에서 끝까지 통과하는지.
- BGM, 렌더링, 성능 회귀가 없는지.

이 항목들은 사용자의 다음 플레이 테스트 전에는 성공으로 승격하지 않는다.
