# 641 — PatHouse 40% 개선 이후 r10까지: 통합 시도·측정 기록

Date: 2026-09-01 KST  
Scope: #618에서 확인한 약 40% 개선 뒤의 후속 실험·계측인 **#621–#640**만 통합한다. #618 자체의 측정은 출발점으로만 인용하며, 각 원문과 원시 artifact를 대체하지 않는다.

## 판정 요약

- **VERIFIED 출발점 (#618):** expanded AOT + multi-direct-loop 배포 쌍은 actual PatHouse A-B-A-B에서 조건 평균 **+40.1128% FPS** (강건 중앙값 +39.4043%)였다. 이는 두 변경을 합친 효과이며, 둘 중 어느 하나의 단독 기여라고 해석하지 않는다.
- **VERIFIED 후속 결론:** #621–#638의 최적화 후보 대부분은 현재 production-B/r10의 실제 owner window에서 독립 frame-time 10% 가능성을 보이지 못했거나 실제 A/B에서 악화됐다. 특히 Acknex per-element host HLE, batch64 host HLE, Wasm fusion, ZIP mutex bypass는 모두 기각됐다.
- **VERIFIED r10 효과 (#636/#639):** fresh equal-phase A1/B1/A2/B2에서 r10은 600-Present superwindow frame time 중앙값 **18.5468% 감소**, 평균 **19.8282% 감소**, paired legs **22.4239% / 17.2796% 감소**를 보였다. 이는 #618의 40%와 같은 실험/후보가 아니므로 두 비율을 합산하거나 직접 비교하지 않는다.
- **VERIFIED 정책 경계:** #639 시점 admission-v1은 control drift 6.6488% (>5%) 때문에 false였다. 그러나 #640은 사용자의 별도 승격 결정으로 r10을 production default로 변경했다. 이 배포 결정은 #639의 통계적 admission 판정을 바꾸지 않는다.
- **NOT VERIFIED:** #640 배포 확인에서는 private-session 식별자를 전송하지 않았으므로, 원격 r10 PatHouse 재진입 및 live HLE counter 재측정은 하지 않았다. 실제 성능 근거는 #639의 로컬 equal-phase 측정이다.

## 측정 계약과 해석 규칙

1. 성능 판정은 FPS가 아니라 actual PatHouse **frame time**의 fresh-process 인접/교차 A/B로 한다.
2. 실제 장면·전후 PNG·정확한 C2S `0x0005` 수락·Present window·data loss zero를 함께 확인한다. character selector나 전환 frame은 성능 leg에 포함하지 않는다.
3. residency, sample count, entry count, 또는 renderer leaf share는 제거 가능 시간과 같지 않다. causal join 또는 실제 A/B가 없는 surface는 구현 승격하지 않는다.
4. 후보가 첫 유효 인접 A/B에서 10% gate에 미달하면 사용자 immediate-reject 규칙에 따라 다음 A/B를 진행하지 않을 수 있다.

## 시간순 통합 기록

| # | 시도 또는 측정 | 직접 측정·결과 | 판정 |
|---:|---|---|---|
| 621 | `uboDirtySplit`, generic Binaryen post-link, current exit histogram | `uboDirtySplit`은 36.6560→36.0527 FPS, frame time **+1.6734%**로 악화. Binaryen 후보는 33,912 marker/patch 중 제거 0. actual 20.006765 s에서 generated entries 245,541,925, transform loop 3,148,652/1,604. | VERIFIED / 후보 기각, exact edge 기반 확보 |
| 622 | Acknex transform island 재발견 | 구 zero 측정은 ASLR load-base `+0x40000` 오해였다. 보정 뒤 5개 RVA 각 2,533,560 hits, transform loop **99.949084%**; 10 regions/91 blocks/1,398 ops. | VERIFIED / speedup은 아직 UNKNOWN |
| 623 | Acknex whole-function HLE | matcher 결함을 고쳐 helper 성공 15,802,344/15,804,108=99.9888%였지만 24.5176→91.2001 ms, **+271.98%** 악화. | VERIFIED / 즉시 기각 |
| 624 | Acknex `+49650` batch64 host HLE | 24,265,220 elements를 평균 63.3548개 chunk로 처리했어도 21.6707→75.3932 ms, **+247.9041%** 악화. | VERIFIED / 즉시 기각 |
| 625 | Acknex direct generated-Wasm fusion | fast elements 41,892,525를 확인했으나 19.0640→19.7131 ms, **+3.4049%** 악화. fusion3의 +12.31% 표시는 fast0/control drift였다. | VERIFIED / 즉시 기각 |
| 626 | direct-Wasm guard cache / mapping-epoch cache | active fusion5가 이미 +3.405% 악화. 10%에 도달하려면 추가 2.5555 ms/frame(전체 wall 12.9635%) 제거가 필요하나 신뢰 가능한 bound가 없다. | VERIFIED / 미구현·기각 |
| 627 | current-B owner CPU window | transform 2.4376%, dispatcher pair 2.5132% wall로 10% 축 기각. libc `__read` blocked interval은 6.385636 s=**21.2657%**였지만 causal removability는 미확정. | VERIFIED / read 원인 계측으로 이동 |
| 628 | blocked read의 fd/Wine request 귀속 | 720 Presents/15.014 s에서 >=1 ms read 2.847 s=18.9623%; fd4 len64 pipe 1.460 s=9.7243%, WIS 1.387 s=9.2380%. 단일 request/가족은 10% 미달. | VERIFIED / 후보 기각, WIS join 후속 |
| 629 | cached ZIP global-read-mutex bypass | 20.7724→19.6567 ms, **-5.3707%**. | VERIFIED / 10% 미달 즉시 기각 |
| 630 | WIS lifecycle causal join | 매 frame 6 reads/130,580 B와 Wine file/fd/handle 수명을 720회 직접 결합. 보수 하한 10.205337%, full join HLE 10.619149%로 admission 후보가 됨. | VERIFIED/INFERRED / 실제 A/B 대기 |
| 631 | FACE-WIS HLE r5 | exact HLE hit 1,621/1,622, fallback/tail-change 0. 20.86806→19.26026 ms, **-7.7045949%**. | VERIFIED / 10% 미달이나 보조 최적화로 배포 |
| 632 | FACE-on owner/tier 및 causal surface | dispatcher 1.5864%, HQEMU plan 4.5728%, V8 compile 0.1131%; renderer pack은 owner compute와 98.955% 동시여서 causal lower 0. `__read` residency 18.9104%는 원인 미결. | VERIFIED / 새 standalone-10 후보 없음 |
| 633 | FACE-on WIS join + disabled-state retry race | full WIS+join lower 1.451810 s=**8.360071%**, 10%에 284.790 ms 부족. r5의 최초 identity 실패가 `enabled=false`를 영구 설치하는 retry bug를 확인. | VERIFIED / HLE2 단독 기각, r6 retry 진행 |
| 634 | r10 CWD-safe republish fresh A/B run 1–2 | Run1 median 16.7534%, Run2 12.4651%, pooled48 median 14.7294%; CI 하한/양방향 drift가 strict gate를 통과하지 못함. | VERIFIED / strict reject, canary-only |
| 635 | r10 static-only remote canary | r10 asset exact SHA 및 remote character-select를 확인. 강제 `0x0005`/UI 우회 없이 remote PatHouse activation은 수행하지 않음. | VERIFIED / canary 배포, remote HLE NOT VERIFIED |
| 636 | r10 phase variance attribution | #634는 A/B start skew 11.3445 s라 순효과를 식별 못함을 확정. 새 동등-phase 계약에서는 superwindow median **18.5468%** 감소, paired **22.4239% / 17.2796%**; control drift 6.6488%로 strict admission false. | VERIFIED / prospective effect, strict reject |
| 637 | r10 actual owner profile | 35.030745 s/2,688 Presents에서 libc read 8.2684%, dispatcher 3.7620%, generic helper union 9.3094%, largest grouped Wasm 4.3318%; 완전 제거 가정도 각 standalone 10% 미만. | VERIFIED / no new standalone-10 |
| 638 | r10 renderer/D3D9Web source audit | FFP pack leaf 13.8582%이나 3.45x perfect saving upper **9.8413%**; independent critical lower 0. JS/Wasm marshalling/bufferData/draw도 standalone 10% 불가. | VERIFIED / renderer 후보 기각 |
| 639 | r10 prospective equal-phase proof | 4개 fresh leg, 각 30개 120-Present window, phase skew median 0.0045 s. superwindow median **18.5468%**, mean 19.8282%, flat CI95 [15.5776,24.0639]%, hierarchical CI95 [14.8564,24.7683]%. | VERIFIED / objective >10% 달성, admission-v1 false |
| 640 | r10 production default promotion | default PatHouse page/server-list가 r10 JS/Wasm/cache 및 10 identity flag를 사용하도록 변경. HTTPS identity exact; service restart 없음. | VERIFIED / 사용자 승인 production promotion; remote re-entry NOT VERIFIED |

## 재현 가능한 최종 성능 수치

### #618 출발점 (후속 범위의 기준선)

| 조건 | FPS | 결과 |
|---|---:|---|
| control A | 20.8840 / 21.7682 | expanded AOT + multi-direct-loop 이전 조건 |
| candidate B | 30.3458 / 29.4154 | 동일 장면의 배포 쌍 |
| 인접 candidate effects | +45.3065% / +39.4043% / +35.1301% | robust median +39.4043%, condition mean **+40.1128%** |

### r10 동등-phase 계약 (#636/#639)

| 지표 | 결과 |
|---|---:|
| superwindow frame-time median reduction | **18.5468%** |
| superwindow frame-time mean reduction | **19.8282%** |
| flat bootstrap 95% CI | **[15.5776%, 24.0639%]** |
| hierarchical bootstrap 95% CI | **[14.8564%, 24.7683%]** |
| independent paired legs | **22.4239% / 17.2796%** reduction |
| candidate drift | 0.1135% (superwindow), 2.4131% (base window) |
| control drift | 6.6488% (superwindow), 5.6112% (base window) |
| policy result at #639 | `acceptedFrameTime10=false` (control drift >5%) |

## 원문 및 artifact 경로

이 문서는 압축 요약이다. 구현 세부, trace, verifier, 원시 A/B leg는 아래 원문을 권위 근거로 사용한다.

- 출발점: [#618](618_CURRENT_PATHOUSE_EXPANDED_AOT_MULTI_DIRECT_LOOPS_GAIN_20260830.md)
- 후보 탐색: [#621](621_CURRENT_FRAME_TIME_10PCT_GATE_AND_EDGE_HISTOGRAM_20260831.md), [#622](622_CURRENT_ACKNEX_TRANSFORM_ISLAND_ASLR_REDISCOVERY_20260831.md), [#623](623_ACKNEX_HLE_TERMINAL_RELOCATION_MATCHER_FIX_20260831.md), [#624](624_ACKNEX_OUTER_BATCH64_REJECT_20260831.md), [#625](625_ACKNEX_DIRECT_WASM_FUSION_REJECT_20260831.md), [#626](626_DIRECT_WASM_GUARD_CACHE_AMDAHL_REJECT_20260831.md)
- read/WIS/FACE 계측 및 구현: [#627](627_CURRENT_B_EXACT_OWNER_TIME_WINDOW_20260831.md), [#628](628_CURRENT_PATHOUSE_READ_SOURCE_AND_WINE_REQUEST_ATTRIBUTION_20260831.md), [#629](629_CACHED_ZIP_UNLOCKED_READ_EARLY_REJECT_20260901.md), [#630](630_CURRENT_PATHOUSE_WIS_LIFECYCLE_CAUSAL_JOIN_20260901.md), [#631](631_FACE_WIS_HLE_R5_ACTUAL_AND_REMOTE_PROMOTION_20260901.md), [#632](632_FACE_OWNER_TIER_AND_CAUSAL_SURFACE_AUDIT_20260901.md), [#633](633_FACE_ON_READWAIT_CAUSAL_JOIN_AND_HLE_RETRY_RACE_20260901.md)
- r10 A/B, audit, canary, default promotion: [#634](634_FACE_CWD_SAFE_REPUBLISH_FRESH_AB_RUN1_20260901.md), [#635](635_R10_SAFE_STATIC_ONLY_REMOTE_CANARY_DEPLOY_20260901.md), [#636](636_R10_AB_PHASE_VARIANCE_AND_PROSPECTIVE_GATE_20260901.md), [#637](637_R10_ACTUAL_OWNER_PROFILE_AND_REMAINING_AMDAHL_SURFACES_20260901.md), [#638](638_R10_RENDERER_D3D9WEB_NEXT10_SOURCE_AUDIT_20260901.md), [#639](639_R10_PROSPECTIVE_EQUAL_PHASE_OBJECTIVE_PROOF_20260901.md), [#640](640_R10_PRODUCTION_DEFAULT_PROMOTION_20260901.md)

The canonical r10 experiment is `artifacts/performance/face_r8_vs_r10_phasegated30_attempt4_fresh_ab_20260901.json`, with its validated legs and fixed-superwindow analysis named in #639. Rejected runs are retained as `face_r8_vs_r10_phasegated30_attempt{1,2,3}_NOT_ACCEPTED_20260901.json` and must not be mixed into the accepted estimate.
