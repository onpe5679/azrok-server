# 284. Gate 6 runtime parity inline and Wasm CFOF preservation

## 결론

- **VERIFIED static:** P/NP 조건은 컴파일 시점의 `currentLazyFlags`가 아니라
  런타임 `CPU.lazyFlagType`을 읽어 판정하도록 바뀌었습니다. 따라서 서로 다른
  선행 블록이 합류하는 지점에서도 선형 컴파일 상태를 잘못 재사용하지 않습니다.
- **VERIFIED static:** `NONE`은 `flags & PF`, 실제 lazy producer enum 1..49는
  `popcnt(result.u8) & 1`로 판정합니다. `P`는 짝수 패리티, `NP`는 그 반대입니다.
- **VERIFIED static:** `CFOF`이면 `lazyFlagTypePrev`를 사용합니다.
  `storeLazyFlagType(CFOF)`도 기존 Wasm backend의 누락을 고쳐, 최초 CFOF 전환에서만
  현재 producer를 `lazyFlagTypePrev`로 보존하고 중첩 CFOF는 원 producer를 유지합니다.
- **VERIFIED tests/build:** JP/JNP 4개와 shift/rotate 계열 36개가 통과했습니다.
  전체 fast suite는 637개 중 628개가 통과했으며, 실패 9개는 기존과 같은
  MT broker Node harness `callHandler` 실패입니다. 새 CPU/JIT 실패는 없습니다.
- **VERIFIED static cache baseline:** 현재 채택 캐시 134개 그룹에는
  `fn_22=P` 호출 지점 301개, `fn_23=NP` 호출 지점 106개, 합계 407개가 있습니다.
  새 parity 캐시의 합격 조건은 두 호출 수가 모두 0인 것입니다.
- **NOT VERIFIED browser:** 새 런타임의 cache-OFF PatHouse 렌더, 새 기록 캐시,
  helper 0개, A-B-A FPS는 아직 완료 전입니다.
- **NOT VERIFIED dedicated regression:** 아래 exact join 형태를 한 번에 고정하는
  전용 회귀 테스트는 아직 없습니다.

```text
rol eax, 1
jz L
test ebx, ebx
L:
setp cl
```

## 측정에서 후보를 고른 근거

이전 저장 프로필의 18.487초 구간에서 condition helper는 18,534,400회 호출됐고,
프로필 내부 누적 timer는 4,539,285 us였습니다. 그중 P/NP는 54.50%, 약
10.10M 호출입니다.

이 절대 시간은 이전 계측 런타임의 값이므로 현재 release FPS의 24.55%라고
환산하지 않습니다. 다만 호출 밀도는 다음 후보의 우선순위를 정하는 직접 근거입니다.
컴파일 시점에 producer가 알려진 경우만 최적화하면 block entry와 merge에서 뜨거운
runtime-lazy 경로를 놓치므로, 이번 구현은 모든 P/NP를 런타임 exact path로 처리합니다.

## 구현 계약

매 P/NP 판정은 다음 순서를 따릅니다.

1. `CPU.lazyFlagType`을 읽습니다.
2. 값이 CFOF이면 한 번만 `CPU.lazyFlagTypePrev`로 치환합니다.
3. NONE이면 architectural flags의 PF를 읽습니다.
4. 그 밖의 실제 producer enum 1..49이면 lazy result의 하위 8비트 popcount를 씁니다.
5. helper 호출, GP register sync, GP cache invalidate는 수행하지 않습니다.

`FLAGS_NULL`은 컴파일 상태 sentinel일 뿐 런타임 `lazyFlagType`에 기록되지 않음을
소스 전체 write-site로 확인했습니다.

## 산출물

- runtime stem: `boxedwine.upstreamjit67parity1`
- JavaScript SHA-256:
  `39FD867C77003040AA9B71CC4363237B32D86DE75A8CB6407D0B9F0AF50DDECD`
- Wasm SHA-256:
  `2D4D20C0DF068E4E842A742AF9F75CC9779BD401EA22B3096D70517ABE1E62CE`

기존 `inlinefetch2` 캐시는 생성된 block 안에 옛 CFOF store와 옛 P/NP helper 호출을
내장합니다. 따라서 새 런타임에 그 캐시를 붙이는 것은 후보 검증이 아닙니다.
새 런타임으로 fresh record를 만들고 동일 inline-fetch pipeline을 다시 거쳐야 합니다.

## 캐시 생성 게이트

채택 캐시 manifest에서 복원한 authoritative 옵션은 다음과 같습니다.

- `--mt-generic-indirect-limit 64`
- `--mt-generic-depth-local`
- `--mt-generic-inline-fetch`
- relocation map load는 `atomic`
- table bounds는 `dispatcher-checked`
- slot visibility는 `table-ref-v1`

따라서 plain-load, bitmap, pregrow, call-ref, last-slot 후보를 섞지 않습니다.
각 raw 업로드 직후 `azrok-jit-record-raw.zip`을 고유명으로 보존하고
manifest entry 수, 실제 v5 Wasm 수, SHA-256을 확인해야 합니다.

baseline과 candidate의 raw corpus가 다르면 공통 key 교집합만으로도 Binaryen 이후의
크기 기반 group packing이 달라질 수 있습니다. 그룹별 ordered membership이 완전히
같지 않으면 “동일 레이아웃 A/B”로 주장하지 않고, 자연 A-B-A의 corpus/layout
공변량을 명시합니다.

## 재부팅 후 런타임 상태

- **VERIFIED:** TCP 9200, control 9300, WebSocket bridge 9201, HTTP 8765가
  모두 LISTEN 상태로 복구됐습니다.
- **VERIFIED:** 서버는 `playable` + 기존 캐릭터 자동 선택 경로로 시작했습니다.
- **NOT VERIFIED:** 첫 HTTP 시도 전에 서비스가 종료되어 Chromium 오류 페이지가
  만들어졌고, Browser URL 정책상 그 오류 문서에서의 재내비게이션은 차단됐습니다.
  사용자가 같은 단일 탭의 Reload를 누르면 원래 후보 URL이 다시 열리도록 유지했습니다.
