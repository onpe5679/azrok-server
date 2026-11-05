# 237 — First browser wall profile invalid result and persistent-transition gate

Date: 2026-07-21

## Scope

첫 `BOXEDWINE_D3D9WEB_WALL_PROFILE` 브라우저 실행에서 보존된 두 개의 120-Present 출력과 해당 빌드/현재 source를 대조했습니다. 브라우저를 다시 실행하거나 새로고침하지 않았고 production source도 수정하지 않았습니다.

## VERIFIED browser output — 두 창 모두 무효

보존된 첫 출력의 핵심 필드:

```text
valid=0 frames=120 wall_us=2611994 fps_x100=4594
deep_frames=7 deep_wall_us=1484659 deep_fps_x100=471
control_frames=113 control_wall_us=1127334
deep_slowdown_pct_x100=202595
timer_reads=6617666 timer_cost_ns=208 timer_est_us=1376474
timer_pct_x100=9271 stack_overflow=0 sum_error_us=0
```

다음 출력의 핵심 필드:

```text
valid=0 frames=120 wall_us=2794025
deep_frames=8 deep_wall_us=1676230
control_frames=112 control_wall_us=1117795
deep_slowdown_pct_x100=199942
timer_reads=7562744 timer_cost_ns=208 timer_est_us=1573050
timer_pct_x100=9384
```

독립 재계산:

| field | window 1 | window 2 |
|---|---:|---:|
| deep 평균, us/frame | 212,094.143 | 209,528.750 |
| control 평균, us/frame | 9,976.407 | 9,980.312 |
| deep/control | 21.259572x | 20.994207x |
| slowdown delta | +2,025.957% | +1,999.421% |
| `timer_est/deep_wall` | 92.7131% | 93.8445% |
| timer reads/deep frame | 945,380.857 | 945,343.000 |

출력의 `deep_slowdown_pct_x100`과 `timer_pct_x100`은 위 산술과 반올림 범위에서 일치합니다. `sum_error_us=0`은 bucket 합이 닫혔다는 뜻일 뿐, 계측 교란이 작다는 뜻은 아닙니다. 두 창 모두 타이머 비용과 deep/control slowdown gate를 수십 배 초과하므로 category 백분율을 성능 결론에 사용할 수 없습니다.

## VERIFIED source — 실패 원인

첫 브라우저 빌드에서 `D3D9WebWallGuestScope`는 모든 interpreter `cpu->run()` 호출을 감쌌고, active deep frame에서는 constructor의 push와 destructor의 pop이 각각 clock을 읽었습니다. 즉 guest block 하나당 두 번의 `emscripten_get_now()`가 발생했습니다.

전체 `timer_reads`에는 Present와 명시적 bridge/copy/proxy scope도 포함되므로 guest block 수를 정확히 역산할 수는 없습니다. 다만 guest block만으로 설명할 때의 상한은 두 창 모두 약 472,700 blocks/deep-frame입니다.

```text
window 1: 6,617,666 / (2 * 7) = 472,690.429
window 2: 7,562,744 / (2 * 8) = 472,671.500
```

두 독립 창의 `timer reads/deep frame`이 0.004% 이내로 반복된 점은 per-block 두-read 경로가 steady workload와 함께 반복됐다는 강한 동적 증거입니다. 이것은 개별 guest block 수의 정확한 측정치는 아닙니다.

## VERIFIED current source / browser NOT VERIFIED — persistent guest root

현재 source는 guest scope를 push/pop하지 않고 persistent root category를 유지합니다.

- 매 `cpu->run()` 전에 page/category를 확인합니다.
- 같은 guest page이면 즉시 반환합니다.
- 다른 page라도 module category가 같으면 clock을 읽지 않습니다.
- Acknex / d3d9 / other category가 실제로 바뀔 때만 한 번 `transitionNow()`를 호출합니다.
- deep frame 활성화 시 module cache를 비우고 강제 분류를 clock 두 번으로 별도 계상합니다.
- Present와 명시적 decode/bridge/copy/batch/proxy scope의 clock reads는 남습니다.

따라서 현재 source의 deep-frame read 수는 대략 다음 구조입니다.

```text
deep_timer_reads = deep Present boundaries
                 + 2 * deep-frame activations
                 + guest module-category transitions
                 + 2 * entered explicit nested scopes
```

기존 출력에는 guest module-category transition count와 모든 explicit scope entry count가 없으므로 새 read 수를 정확한 숫자로 예측할 수 없습니다. 다만 `2 * every cpu->run()` 항은 제거됐으므로 방향은 맞습니다. PatHouse의 기존 D3D 측정은 120프레임당 uploads 2,160, direct calls 240, cache 전 SetFVF 19,080 같은 호출 규모를 보였으며, 이는 수백만 guest-block read와 다른 규모입니다. 이 비교는 감소 가능성의 근거이지 `<5%` 통과 증명은 아닙니다.

## Required timer-read reduction

`timer_cost_ns=208`이 유지된다고 가정할 때 timer share `<5%`에 필요한 동적 상한은 다음과 같습니다.

```text
deep_timer_reads < floor(deep_wall_us * 1000 * 0.05 / timer_cost_ns)
```

| window basis | `<5%` read cap | old reads 대비 필요한 감소 |
|---|---:|---:|
| window 1 | 356,889 | 94.607% 이상 |
| window 2 | 402,939 | 94.672% 이상 |

즉 persistent 방식은 old per-block timer reads를 약 18.5~18.8배 이상 줄여야 첫 gate를 통과합니다. 현재 구조상 가능성은 높지만 **NOT VERIFIED**입니다.

참고로 old `timer_est_us`만 기계적으로 뺀 잔여 deep 평균은 window 1이 15,455 us/frame, window 2가 12,897.5 us/frame입니다. control 평균 대비 각각 1.5492x와 1.2923x이므로, calibrated timer 비용 제거만으로도 deep/control `<5%`를 보장하지 않습니다. constructor/classification, cache cold start, scheduler 차이 또는 calibration 오차가 남을 수 있어 slowdown gate를 별도로 유지해야 합니다.

## Acceptance gate for the next retained browser run

동일한 1024x768 PatHouse steady scene에서 다음을 모두 만족한 120-Present 창만 category breakdown에 사용할 수 있습니다.

1. `valid=1`.
2. `deep_frames`와 `control_frames`가 합쳐서 120이며 예정된 1/16 배치(경계상 7/113 또는 8/112)입니다.
3. `stack_overflow=0`, `stack_mismatch=0`.
4. `sum_error_pct_x100 <= 100` (1% 이하).
5. `timer_pct_x100 <= 500` (5% 이하), 동치로 위 동적 read cap을 만족합니다.
6. `deep_delta_pct_x100 <= 500` (deep/control 프레임 평균 차이 5% 이하).
7. 동일 창의 scene/workload signature와 연결 상태가 정상입니다. 전환·로딩·Plaza 이동 창은 제외합니다.
8. profiler OFF/ON 동일 장면의 공통-wall FPS 교차 비교에서도 ON slowdown이 5% 미만이어야 합니다. `valid=1` 한 줄만으로 전체 계측 오버헤드를 대신하지 않습니다.
9. 최소 3개의 연속 valid 창에서 timer/read 및 category 비율이 재현되어야 합니다. 한 창만 통과하면 성능 분해를 확정하지 않습니다.

이 gate 이전에는 첫 두 창의 Acknex/D3D/other/category 비율을 최적화 우선순위나 50-FPS 예산으로 사용하지 않습니다.
