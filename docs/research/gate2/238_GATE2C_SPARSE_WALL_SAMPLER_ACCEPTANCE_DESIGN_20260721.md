# 238 — Sparse wall sampler 1/4096 dynamic acceptance design

Date: 2026-07-21

## Scope and status

- **VERIFIED arithmetic:** document 237의 두 invalid 창에서 얻은 기존 `cpu->run()` 횟수 근사와 새로 관측된 browser timer cost 270 ns를 사용해 1/4096 sparse sampler의 표본 수와 clock-read 비용을 계산했습니다.
- **INFERRED design:** 최소 sample count, window-level CV/CI 및 필요한 120-frame window 수를 정했습니다.
- **NOT VERIFIED browser:** 새 sampler의 실제 표본 수, category 분산, selector/aggregation 비용 및 OFF/ON FPS 영향은 아직 브라우저에서 검증하지 않았습니다.
- 브라우저와 production source는 이 조사에서 변경하거나 실행하지 않았습니다.

## Run-count basis

첫 intrusive profiler는 active deep frame마다 약 945,381/945,343 timer reads를 냈습니다. 당시 guest block 하나가 push/pop 두 reads를 유발했고 다른 scope reads도 포함됐으므로 다음 값은 정확한 block count가 아니라 기존에 채택한 steady-scene 근사입니다.

```text
window 1 approximation = 6,617,666 / (2 * 7) = 472,690.429 runs/frame
window 2 approximation = 7,562,744 / (2 * 8) = 472,671.500 runs/frame
mean approximation                              472,680.965 runs/frame
```

120 frames와 1/4096 sampling을 적용하면:

```text
estimated runs / 120 frames    = 56,721,715.74
estimated samples / frame      = 115.4006
estimated samples / 120 frames = 13,848.075
```

다른 scope reads가 old 총계에 포함됐으므로 실제 run/sample 수는 이 근사보다 낮을 수 있습니다. 따라서 acceptance는 예상치 13,848 자체가 아니라 보수적인 실측 하한을 사용합니다.

## Expected timer overhead at 270 ns

샘플 하나의 `cpu->run()` 앞뒤에서 clock을 두 번 읽는다고 가정합니다.

```text
timer reads / 120 frames = 2 * 13,848.075 = 27,696.150
timer cost               = 27,696.150 * 270 ns
                         = 7,477,961 ns = 7.478 ms / 120 frames
```

| denominator basis | 120-frame wall | timer-only overhead |
|---|---:|---:|
| invalid-profile control 9.980 ms/frame | 1,197.637 ms | 0.624% |
| 33.842 FPS release reference | 3,545.890 ms | 0.211% |
| 32.422 FPS material-scan run | 3,701.191 ms | 0.202% |
| 26.78 FPS FVF-cache release | 4,480.956 ms | 0.167% |

이는 `emscripten_get_now()` 두 번만의 추정치입니다. 모든 run에서 실행되는 selector, selected sample의 module lookup/aggregation, cache behavior 및 logging은 포함하지 않습니다. 따라서 timer-only 계산으로 profiler overhead를 확정하지 않습니다.

## Statistical power of one window

독립 Bernoulli sampling이고 duration weighting이 없다는 단순 모델에서 13,848 samples/window의 worst-case count-share 95% margin은 `p=0.5`에서 ±0.833 percentage point입니다.

| true count share | expected hits/window | one-window 95% half-width | 10-window aggregate hits | ideal aggregate half-width |
|---:|---:|---:|---:|---:|
| 50% | 6,924 | 0.833 pp | 69,240 | 0.263 pp |
| 10% | 1,385 | 0.500 pp | 13,848 | 0.158 pp |
| 5% | 692 | 0.363 pp | 6,924 | 0.115 pp |
| 1% | 138 | 0.166 pp | 1,385 | 0.052 pp |

이 표는 설계 sanity check일 뿐 실제 time-share CI가 아닙니다. `cpu->run()` duration은 heavy-tailed일 수 있고 연속 samples는 자기상관될 수 있습니다. 따라서 최종 CI는 개별 sample을 iid로 간주하지 않고 **120-frame window를 독립 분석 단위**로 계산합니다.

고정 주기 every-4096 방식은 게임 루프 주기와 alias할 수 있습니다. selector는 xorshift/Bernoulli 또는 window마다 무작위 phase를 사용해야 합니다. 고정 phase라면 위 binomial CI를 주장하지 않고 window 간 재현성만 사용합니다.

## Required collection

PatHouse 기준 장면에 도달하고 transition이 끝난 뒤:

1. 첫 완전한 120-frame 창 1개는 warm-up으로 버립니다.
2. 이후 **최소 10개의 accepted 120-frame windows**를 수집합니다.
3. transition/로딩/signature 불일치로 최대 2개가 기각될 수 있도록 최대 12개 candidate windows를 허용합니다.
4. 즉 정상일 때는 warm-up 포함 11 windows, 기각이 있으면 최대 13 windows입니다. 같은 장면에서 UI 조작은 하지 않습니다.

10 windows를 택한 이유는 `t(9, 0.975)=2.262`이기 때문입니다. window CV가 5%/10%/20%일 때 평균의 95% relative CI half-width는 각각 약 3.58%/7.15%/14.31%입니다. 3개 창은 outlier 하나에 지나치게 민감하고 time-weighted hotspot의 분산을 판단하기 부족합니다.

## Per-window acceptance

각 120-frame window는 다음을 모두 만족해야 합니다.

1. `samples >= 10,000`. 예상 13,848보다 27.8% 낮은 보수적 하한입니다.
2. timer calibration이 유효하고 `timer_est_pct <= 1.0%`. 예상 최악 denominator가 0.624%이므로 1%는 검출 가능한 headroom입니다.
3. sampler의 dropped/overflow/mismatch가 모두 0입니다.
4. 정확히 120 Presents이며 scene, upload/direct-call workload signature, WebSocket 연결이 정상입니다.
5. PatHouse 진입, UI 전환, Plaza 이동, asset 생성 burst가 섞인 창은 제외합니다.
6. category time 합과 sampled total의 residual/error가 1% 이하입니다.

10개 accepted windows 전체에서는:

- aggregate samples `>= 100,000`.
- samples/window CV `<= 5%`.
- wall time 또는 FPS CV `<= 5%`.
- timer cost/read count CV `<= 10%`; timer calibration 자체가 흔들리면 category CI를 기각합니다.

## Category and candidate acceptance

Window별 category percentage를 먼저 계산하고, 10개 window의 평균, sample SD, CV 및 Student-t 95% CI를 보고합니다.

```text
mean = sum(window_share) / n
CV = sample_SD / mean
95% CI half-width = t(0.975, n-1) * sample_SD / sqrt(n)
```

분석 등급:

1. **Major category (`mean >= 10%`)**: CV `<=10%`이고 95% CI half-width `<=1.0 pp`일 때만 절대 비중으로 채택합니다.
2. **Optimization candidate (`1% <= mean < 10%`)**: aggregate hit count `>=1,000`, CV `<=20%`, 95% relative half-width `<=20%`일 때만 순위 후보로 채택합니다.
3. **Below 1% 또는 hits <1,000**: 존재 관측으로만 남기고 AOT/JIT 구현 우선순위로 사용하지 않습니다.
4. 두 후보의 95% CI가 겹치면 숫자 순서만으로 우선순위를 확정하지 않습니다.

Time weighting 때문에 hit count 1,000은 충분조건이 아닙니다. 위 window-level CV/CI도 동시에 통과해야 합니다.

## Profiler overhead gate

내부 timer estimate와 통계 안정성만으로 실제 perturbation을 증명할 수 없습니다. 동일 PatHouse scene에서 profiler OFF/ON을 교차 비교해야 합니다.

- 최소 OFF 5 windows + ON 5 windows.
- 각 측의 workload signature와 FPS CV가 5% 이하.
- paired/alternating 순서 또는 세션 순서를 반대로 한 재실행으로 thermal/order drift를 상쇄합니다.
- ON 평균 wall/frame 증가가 5% 미만이어야 합니다.
- 가능하면 paired difference의 95% CI 상한도 5% 미만이어야 합니다. 상한이 5%를 넘으면 `NOT VERIFIED`로 남깁니다.

## Final gate

Sparse 결과를 50-FPS 최적화 우선순위에 사용하는 최소 조건은 다음의 교집합입니다.

```text
10 accepted windows
AND >=100,000 aggregate samples
AND per-window >=10,000 samples
AND timer estimate <=1%
AND OFF/ON observed slowdown <5%
AND zero drops/overflow/mismatch
AND <=1% accounting residual
AND category-specific CV/CI/hit gates
```

이 조건을 통과하기 전에는 1/4096 출력의 category 백분율을 절대 CPU budget으로 변환하지 않습니다.
