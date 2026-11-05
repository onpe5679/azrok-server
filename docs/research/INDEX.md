# INDEX — 확정 사실 지도

> 갱신 **2026-11-05** · 다음 새 문서 번호는 **662**
>
> 이 파일은 **"무엇이 사실인가"** 의 지도다. **"무엇이 어디 있나"** 는 [`REGISTRY.md`](REGISTRY.md) (전 문서 목록).
> 새 조사는 반드시 여기부터 읽고 시작한다. 결론이 뒤집히면 그 즉시 §1·§2 를 고친다.
>
> **실패 실험 재도입 전 필독:** [`FAILED_EXPERIMENTS.md`](FAILED_EXPERIMENTS.md). 특히 한글 active-preedit korean7/korean8/xim30/xim31은 운영 재도입 금지입니다.

**층위**

| 절 | 내용 |
|---|---|
| §1 | 목표별 통과/미통과 판정 — 지금 어디에 서 있는가 |
| §2 | 게이트별 확정 사실과 근거 문서 번호 |
| §3 | 열려 있는 질문 (NOT VERIFIED) |
| §4 | 문서 하자 대장 |
| §5 | 상세 로그 #459–#521 (재구축 전 INDEX 원문, 번호순 정렬해 보존) |

#458 이하 456건의 상세는 이 파일에 없다. [`REGISTRY.md`](REGISTRY.md) 에서 번호·제목·경로로 찾는다.

---

## 2026-11-05 additions

- **661 VERIFIED/INFERRED:** 2011.img 는 3월 그 하드 한 개의 3/29 덤프다(LBA×512 정확히 일치). 이미지 안에 `sun.fx` 온전본 0회·손상본 1회 — 손상은 이미지 자체에 있다. 721 파일의 차이 바이트는 전부 홀수 오프셋·비트 0x02 (워드 비트 9) → 덤프 전송 경로 오류(INFERRED). 같은 날 19:06 하드에서 직접 복사한 프로젝트 `Data\` 가 원본이고, 4/1 이미지에서 꺼낸 `starmaru\` 는 손상을 물려받았다. `_img2011_artifact_findings` F10 "스크램블" 판정을 뒤집는다. See `tooling/661_HDD_IMAGE_BIT9_TRANSFER_DAMAGE_20261105.md`.

## 2026-10-26 additions

- **660 VERIFIED OUTAGE / RECOVERED:** core/web active did not imply game availability: bridge inactive since Oct25 19:38:57. Starting bridge restored public authenticated WSS login/heartbeat/lobby (405B). Added core Wants + child PartOf lifecycle dependencies and mandatory public WSS deployment probe. See `server/660_BRIDGE_LIFECYCLE_OUTAGE_20261026.md`.

- **659 DEPLOYED / GUI VERIFIED:** task-oriented operator UI replaces the default console; old debugger retained at /debug. Search, unified inventory/currency save, dirty-close protection, conflict recovery, backed-up deletion, global history, readable server/OX views and mobile layout verified. Live PAGE hash matched; production character lookup verified without mutations. See `server/659_OPERATOR_UX_REDESIGN_20261026.md`.

## 2026-10-25 additions

- **656 VERIFIED REGRESSION/FIX:** final tutorial directly issues kind3/aux0 without0010; the655 validator rejected it and all later stage1 saves. Same-account reconnect restored stage0. Narrow adjacent final-reward exception passes issuance→growth→restart tests; production recovery completed (stage1/level3/500, revision34) with original backups. See `server/656_FINAL_TUTORIAL_GROWTH_REGRESSION_20261025.md`.
- **657 DEPLOYED / LOCAL EDIT GUI + LIVE API VERIFIED:** private account admin with search, login sorting, inventory/currency edits, backup archive, scoped durable access/chat/audit history. Original tailnet-only HTTPS9300 proxies loopback console. See `server/657_PRIVATE_ACCOUNT_ADMIN_20261025.md`.
- **658 VERIFIED/INFERRED:** 미지의 5단계 아즈론은 클라이언트에 모델이 없다. Temp_Character·HeadPet·Plaza 모델은 종족별 알+1~4번뿐이고, exe의 아즈론 텍스처 형식도 `_B_/_R_/_S_/_G_` 네 가지뿐이다. 2011-05-01 이후 패치 추가 여부는 NOT VERIFIED. See `content/658_NO_FIFTH_GROWTH_STAGE_MODEL_20261025.md`.

## 2026-09-27 additions

- **655 IMPLEMENTED / MIXED LIVE VALIDATION:** restored chair allocation/release, durable OX records (user-approved 1 win=1 point), canonical peer evolution, quest transition validation and registry. Production peer info shows Redron; natural chair requests and corrected release-to-movement were measured. OX admission/question and abandonment persistence measured, completed-match GUI still NOT VERIFIED. Final chair-release update copied; service restart confirmation pending network recovery. See `archive/655_REMAINING_IMPLEMENTATION_RESTORATION_20260927.md`.

- **654 HISTORICAL VERIFIED AUDIT:** audit-time gaps were addressed in655; preserve this pre-fix evidence. See `server/654_REMAINING_IMPLEMENTATION_AUDIT_20260927.md`.

- **653 VERIFIED / DEPLOYED / GUI PASS:** information button C2S006C now receives full12-byte S2C0070 compatible with both original latch branches; level from canonical, OX counters zero pending ranking restoration. 142 combined tests pass; production peer info popup shows nickname/level. Growth-stage label mismatch remains noted. See `gate7/653_PLAZA_USER_INFO_LATCHED_0070_20260927.md`.

- **652 VERIFIED / NO QUEST PATCH:** both reported evolved test states are stage1 level3. Original growth selector requires level10 for the next stage1 growth quest; normal quests have an independent date/RNG gate. Immediate empty rows are consistent with original conditions; perpetual emptiness is not yet verified. See `content/652_REDRON_EMPTY_QUEST_STAGE_LEVEL_GATE_20260927.md`.
- **651 VERIFIED / CHAT ID FIX DEPLOYED:** protocol context truncated 13-character dynamic account IDs to 12, preventing exact-match private chat admission. Full identity preserved; regression fails on prior code and passes on fix, 138 existing contracts pass. Production restarted and live overview reports length13. Production Enter chat overlay verified visually; info and quest findings in653/652. See `gate7/651_PLAZA_CHAT_ACCOUNT_IDENTITY_20260927.md`.
- **650 VERIFIED / DEPLOYED:** removed mandatory server-list archive pre-cache gate; runtime cache failures fall back to download with progress and idle errors. 26 executed JS cases and 44 page/home contracts pass. Fresh isolated-origin character creation screen verified against production files and WSS. See `gate7/650_COLD_LAUNCH_ARCHIVE_CACHE_GATE_20260927.md`.

## 2026-09-09 additions

- **649 VERIFIED / SERVER + FONT FIX DEPLOYED / FRESH GUI PASS:** fresh-origin creation now waits for the real request and enters visible PatHouse3D. Same-character FontSmoothing0 A/B fixes the upper A4 title; questfont1 app applies the setting to retained prefixes and is the production default. Returning-character rescue auto-select also bypassed client initialization and is disabled. Final clean origin18772 shows the baby-food icon and actual double-click feeding completes tutorial212, grants100 and advances to202. Infant food quantity remains1; no general-food0014/0008 is emitted (153 focused tests). See `gate7/649_FRESH_ORIGIN_PATHOUSE_AND_QUEST_TEXTURE_DIAGNOSIS_20260909.md`.

## 2026-09-01 additions

- **125 PARTIALLY SUPERSEDED by649:** slot event type2 is a same-slot double-click within500ms, not an ordinary release. Browse/feed and historical capture facts remain valid; archived original is `archive/125_MYBAG_FOOD_BROWSE_VS_FEED_MODE_20260718.md`.

- **648 PARTIALLY SUPERSEDED by649:** actual input-pulse observations remain valid. The zero-A4-row inference was caused by arming the wrong canvas; #649 directly identifies the title as A4. See `archive/648_QUEST_TITLE_ACTUAL_INPUT_AND_TRACE_BOUNDARY_20260901.md`.

- **647 VERIFIED/NOT VERIFIED:** quest-title opt-in trace now records the decoded DrawUP screen rectangle and UV range alongside A4 handle/raw FNV/state, so the visible upper row can be selected by geometry rather than allocation order. Static syntax/44 contracts and remote SHA match passed; actual ticketed PatHouse classification remains pending. See `gate7/647_QUEST_TITLE_SCREEN_SPACE_TRACE_DEPLOYMENT_20260901.md`.

- **646 VERIFIED/REJECTED:** `FUN_00516160` GDI DIB→A4 pack의 R/G nibble 교차를 host에서 보정하는 actual quest A/B를 수행했다. title은 그대로 깨지고 unrelated UI만 보라/초록으로 변해 원인이 아님을 확정했다. default query에 flag가 없어 production 불변. See `gate7/646_QUEST_TITLE_A4_RG_PACKING_AB_20260901.md`.

- **645 VERIFIED/REJECTED:** title renderer가 `CreateFontA` Hangul face table(굴림체/굴림/돋움/바탕)을 사용하고 current root에는 Batang이 없음을 확인해 Batang TTC+FontSubstitutes immutable root를 A/B했다. actual quest panel에서 upper title은 여전히 깨졌고 lower text는 정상이라 font-root 누락 가설을 기각했다. production root 불변. See `gate7/645_QUEST_TITLE_BATANG_FONT_ROOT_AB_20260901.md`.

- **644 VERIFIED/REJECTED/NOT FIXED:** actual account-bound PatHouse quest panel에서 upper title만 깨지고 lower title/body는 정상인 현상을 재현했다. plain-DLL/recycle-off와 A4 clamp는 같은 결함을 재현했고, A4 raw-order는 first screen에 도달하지 못해 기각했다. 실제 text draw는 A4R4G4B4/NEAREST/SRCALPHA-INVSRCALPHA/MODULATE이고 trace/dump controls는 opt-in만으로 추가했다. production default 불변, title fix 미승격. See `gate7/644_QUEST_TITLE_A4_RENDERER_AB_TRACE_20260901.md`.

- **643 VERIFIED/NOT VERIFIED:** production default를 바꾸지 않은 plain-DLL immutable canary가 server-list 발급 actual ticket/r10/WSS 조건에서 original character-select Korean title/art까지 부팅함을 확인했다. 직접 URL의 ticket/launcher 누락과 custom build-token 실패는 비교에서 제외했다. 그러나 quest panel을 아직 열지 못해 upper title AA 결함의 해결 여부는 NOT VERIFIED이며 canary 승격 금지다. See `gate7/643_QUEST_TITLE_PLAIN_DLL_CANARY_AB_20260901.md`.

- **642 VERIFIED/FIXED + INFERRED/NOT VERIFIED:** 신규 첫 식사 지급이 `food[1]`=햄버거였던 index 오류를 `food[0]`=이유식으로 수정하고 139개 focused contracts를 통과했다. quest title의 상단 glyph edge 깨짐은 문자열/CP949가 아니라 client-local AA renderer path로 좁혔으나, 현재 recycle-off generic DLL은 #600의 E1242/INT99 boot regression이 있어 기본 교체를 금지한다. immutable canary A/B 또는 recycle-on state trace가 다음 gate다. See `gate7/642_STARTER_BABY_FOOD_AND_QUEST_TITLE_RENDERER_BOUNDARY_20260901.md`.

- **641 VERIFIED/CONSOLIDATED:** #618의 약40% 출발점 뒤 #621–#640의 actual-PatHouse 후보 탐색, WIS/FACE 계측, r10 equal-phase 측정, canary/default 승격을 하나의 인덱스형 기록으로 통합했다. #639의 objective >10% 달성과 control drift로 인한 admission-v1 false, 그리고 #640의 별도 사용자 승인 default promotion 및 remote re-entry NOT VERIFIED 경계를 모두 보존했다. See `gate6/perf/641_PATHOUSE_40PCT_TO_R10_CONSOLIDATED_EXPERIMENT_AND_MEASUREMENT_RECORD_20260901.md`.

- **640 VERIFIED/DEPLOYED (r10 production default promotion):** 사용자 승격 결정에 따라 default PatHouse page와 server-list launch path를 FACE r10 safe-republish runtime/cache 및 10개 identity flag로 변경했다. HTTPS page/launcher/server-list와 r10 JS/Wasm/cache exact SHA를 확인했고 services 3개는 restart 없이 active다. 기존 URL에 명시된 r5는 유지되므로 새 server-list 진입부터 r10이다. remote actual PatHouse/HLE re-entry는 이번 deploy validation에서 user ticket을 보내지 않아 NOT VERIFIED. See `gate6/perf/640_R10_PRODUCTION_DEFAULT_PROMOTION_20260901.md`.

- **639 VERIFIED/OBJECTIVE >10% ACHIEVED/PRODUCTION POLICY STILL FALSE (r10 prospective equal-phase proof):** effect-blind 동결 계약(`sceneAge>=25s`, Present delta>=600, slack<=3s, warmup<=10k, pending<=100, nojit0)에서 fresh A1/B1/A2/B2 각30개 120-Present 창을 손실0으로 수집하고 사전 고정 5창=600-Present superwindow6개/leg로 평가했다. A/B phase median skew0.0045s, B FACE hit3686/3689·3708/3711, candidate superwindow drift0.1135%(base2.4131%). Frame time은 median **18.5468%**, mean **19.8282%**, flat bootstrap95 **[15.5776,24.0639]%**, hierarchical95 **[14.8564,24.7683]%**, 두 paired leg **22.4239% / 17.2796%** 개선돼 objective-level 10% 조건을 전부 VERIFIED했다. 기존 admission-v1은 control drift6.6488%(base5.6112%) 때문에 false지만 이는 candidate effect/stability 실패가 아니라 production promotion policy 실패다. r10은 canary-only, production/default 불변. See `gate6/perf/639_R10_PROSPECTIVE_EQUAL_PHASE_OBJECTIVE_PROOF_20260901.md`.
- **638 VERIFIED/REJECTED (r10 renderer/D3D9Web next-10 source audit):** actual r10 PatHouse 35.030745s에서 FFP pack leaf는4.854630s=13.8582%지만3.45x saving upper가9.8413%라 numerical 10%부터 실패하고 최소3.5919x가 필요하다. pack inclusive5.124516s의98.9431%가 owner compute와 겹치며 independent critical lower0, accepted artifact에는 ring-full/sync-drain witness가 없다. generous JS/Wasm command-marshalling leaf envelope3.1366%, bufferData2.7768%, named GL draw0.0650%라 단순 전달/배칭/셰이더·material cache도 standalone10 불가다. persistent incremental FFP packer는 complete-family >=3.5919x exact-byte replay와 same-sequence renderer backpressure >=10% lower를 먼저 증명할 때만 재개한다. completion 회귀는 historical r9 artifact/current r10 superset scope로 verifier를 분리하고 dedicated r10 JS/Wasm/cache/manifest/base/ABI/safe-republish verifier를 추가해 양쪽 PASS로 복구했으며 production/remote 불변. See `gate6/perf/638_R10_RENDERER_D3D9WEB_NEXT10_SOURCE_AUDIT_20260901.md`.
- **637 VERIFIED/REJECTED/NO NEW STANDALONE10 (r10 actual owner profile):** fresh local `player/Azrok1` exact C2S0005 actual PatHouse가 r10 JS/Wasm/cache exact SHA, FACE active/fallback0, warmup/CWD-safe gate를 통과하고 35.030745s/+2688 Presents/data-loss0에서 owner `0x22e7a130`/Profile`0x10`/57,796 samples/36.268034s를 결합했다. 남은 libc read8.2684%, dispatcher3.7620%, HQEMU plan4.7595%, entire Azrok.exe7.7844%, generic runtime helper union9.3094%, largest grouped Wasm4.3318%, largest Acknex function2.5765%, x87 helper upper1.1548%는 완전 제거해도10 미만이다. top100 direct17.4269%/Acknex top10 functions11.9213%는 unrelated union·causal lower0이고 renderer pack도3.45x saving upper9.8413%라 기각했다. old wait697→r10 wait705는 exact canonical Wasm body SHA와 guest read stack으로 remap했고 host analyzer를 evidence-driven으로 교정했다. production/remote 불변. See `gate6/perf/637_R10_ACTUAL_OWNER_PROFILE_AND_REMAINING_AMDAHL_SURFACES_20260901.md`.
- **636 VERIFIED/QUALIFIES 634/PROSPECTIVE EFFECT/STRICT REJECT (r10 equal-phase A/B):** #634 legacy는 r8 median start0.3135s 대 r10 11.658s로 phase skew11.3445s가 있어 순효과 식별 불가였다. 이를 고친 effect-blind 동결 계약(`sceneAge>=25s`, Presents>=600, slack<=3s, warmup<=10k, pending<=100, nojit0)에서 A1/B1/A2/B2 각30개 120-Present 창과 고정5창=600-Present superwindow6개/leg를 수집했다. phase A/B median skew0.0045s, loss/errors0, B FACE hit3686/3689·3708/3711. Superwindow median **18.5468%**, mean19.8282%, bootstrap95 `[15.5776,24.0639]%`, adjacent22.4239/17.2796%로 10%+ 신호는 강하게 재현됐다. 그러나 control drift6.6488%>5%(candidate0.1135%)라 strict admission=false; base-window도 median19.7703%/CI `[17.7701,21.7534]%`이나 control drift5.6112%로 같은 실패다. 문턱은 유지하고 r10은 canary-only, production/default 불변. See `gate6/perf/636_R10_AB_PHASE_VARIANCE_AND_PROSPECTIVE_GATE_20260901.md`.
- **635 VERIFIED/DEPLOYED CANARY/NOT ADMITTED:** r10 safe-republish JS/Wasm/cache/page identity를 `faceCwdSafe=1` explicit opt-in으로만 u32ws/playazrok에 static canary 배포했다. HTTPS r10 assets는 exact SHA, production FACE r5 JS/Wasm/cache/default와 server-list r10 부재는 불변이다. 배포 중 금지 지침 수신 전에 불필요한 `azrok-core` restart 1회가 발생했고 4 services active를 확인했다. server files는 pre SHA로 disk 복원했으며 추가 restart는 하지 않았다. Fresh remote browser는 r10 143/44395/33912 등록과 원본 character-select까지 확인했지만 remote PatHouse/HLE activation은 UI 우회/강제 0x0005 없이 **NOT VERIFIED**다. Rollback은 `/home/u32ws/32dev/azroksrv/rollback/r10-canary-pre-20260901`. See `gate6/perf/635_R10_SAFE_STATIC_ONLY_REMOTE_CANARY_DEPLOY_20260901.md`.
- **634 VERIFIED/STRICT REJECT/CANARY-ONLY (FACE CWD safe republish fresh A/B):** r9 census의 unresolved `confirmFailure=3`, r10 static P1 없음/필수7/7, UI-less exact C2S0005 actual PatHouse hook1/unresolved0·warmup완료·lookup hit를 확정했다. Run1은 median16.7534%/trimmed18.0267%/CI `[14.0900,22.3318]%`였지만 drift를 실패했다. Run2는 median12.4651%/trimmed12.2726%/CI `[7.8834,16.1325]%`, adjacent8.3732/18.1367%, drift3.5216/7.6678%로 역시 실패했다. Pooled48은 median14.7294%/trimmed15.1741%, flatCI `[12.2274,18.1727]%`, hierarchicalCI `[9.5934,21.9685]%`, pooled drift6.0375/13.5097%라 strict admission은 계속 false다. r10은 canary-only, production 배포/default 불변. See `gate6/perf/634_FACE_CWD_SAFE_REPUBLISH_FRESH_AB_RUN1_20260901.md`.
- **633 VERIFIED/REJECTED/IN PROGRESS (FACE-on causal WIS join and disabled-state retry race):** 5-way local diagnostic이 actual PatHouse 720 Presents/17.366s에서 WIS720수명을 same-KThread `create_file→getfd→6 reads/130580B→close→close_handle`로 오류0 결합했다. full WIS+joined clock-tax-corrected lower는1.451810s=8.360071%라 standalone10에284.790ms 부족해 HLE2 단독 구현을 기각했다. 같은 창에서 helper1698/fallbackProcessIdentity1698, lookup/hit/capture delta0(이전 hit47)을 직접 관측했고, r5 `getOrCreateState`가 첫 identity 실패 state를 enabled=false로 영구 설치해 재검증하지 않는 소스 버그를 확정했다. bounded atomic retry r6가 진행 중이며 fresh actual PatHouse frame-time10% 전 production 불변. See `gate6/perf/633_FACE_ON_READWAIT_CAUSAL_JOIN_AND_HLE_RETRY_RACE_20260901.md`.
- **632 VERIFIED/REJECTED/NOT VERIFIED (FACE-on exact owner/tier and causal surfaces):** actual PatHouse의 fresh visual nonce 전후 PNG, 35.036411s marker, 2,683 Presents, data-loss0에서 owner CPU `0x1edd7340`/Profile`0xc`/58,679 samples를 같은 trace로 결합했다. dispatcher pair는 full owner wall1.5864%, current HQEMU plan4.5728%, V8 compile0.1131%, x87 causal helper upper1.0728%, named GL draw0.0925%라 standalone10을 기각했다. renderer pack leaf14.1347%는 owner compute와98.955% 동시라 critical lower0이고 3.45x perfect upper도10.0377%뿐이다. 남은 libc `__read` residency는18.9104%; FACE hit47을 제외한 conditional WIS upper1.8998%, non-WIS lower17.0106%지만 current fd/path/request identity와 removability lower가0이라 구현은 보류했다. 다음 gate는 FACE+owner+readwait same-window join이며 production FACE r5는 불변. See `gate6/perf/632_FACE_OWNER_TIER_AND_CAUSAL_SURFACE_AUDIT_20260901.md`.
- **631 VERIFIED/ACCEPTED-SUPPLEMENTAL/DEPLOYED (FACE-WIS HLE r5):** exact `0x00551198->0x005511b1` HLE가 actual PatHouse에서 `1621/1622` hit, fallback/tail-change 0, active entry3개 Admitted를 달성했다. A1 `20.86806ms` 대비 B1 `19.26026ms`로 frame time **-7.7045949%**라 standalone 10% gate에는 미달했지만 사용자 결정으로 유효한 보조 최적화로 보존·기본/원격 승격했다. descriptor255/256, exec UAF, RX `KMemory::memcmp` kpanic, DOS separator VFS miss, stem-specific stale Wasm cache를 직접 잡아 r5 JS `b6cf...1220`/Wasm `68d7...22d4`/base12984728/cache `b66e...5582`로 고정했다. playazrok.com fresh server-list launch가 143/44395/33912, actual PatHouse, remote1413/1420 hits, admitted3, fallback0을 통과했고 구 multi-direct pair는 rollback 보존. #621 조건 C와 partial tier 측정은 이미 존재하며 다음 독립10% 탐색은 stable-B CPU-time/tier attribution이다. See `gate6/perf/631_FACE_WIS_HLE_R5_ACTUAL_AND_REMOTE_PROMOTION_20260901.md`.
- **630 VERIFIED/INFERRED/NOT VERIFIED (current PatHouse exact WIS lifecycle join):** actual PatHouse `720 Presents/14.335s`에서 매 프레임 WIS 1회 수명이 정확히 `6 reads/130580B`, 전부 cache hit로 반복됐고, 같은 thread/handle/fd/object/path의 Wine11 `create_file(44)->get_handle_fd(48)->close_handle(21)` 각720회가 실패0으로 직접 결합됐다. 세 요청 union891.330ms와 WIS outer wait를 후보별 clock tax로 보수 보정한 하한은1.462935s=10.205337%, full WIS syscall+join HLE 하한은1.522255s=10.619149%(10%선 여유88.755ms)라 exact lookup/capture HLE 구현만 admission한다. causalstage1 Wine1.738475s는 제거가능량이 아닌 residency upper이고 #629 mutex-only 5.3707% 기각은 유지한다. tail512 의미와 실제 >=10% A/B는 NOT VERIFIED, production/remote 불변. See `gate6/perf/630_CURRENT_PATHOUSE_WIS_LIFECYCLE_CAUSAL_JOIN_20260901.md`.
- **629 VERIFIED/REJECTED (cached ZIP global-mutex bypass):** promoted immutable ZIP cache hits만 `FsZip::readMutex`를 건너뛰고 `KFile::filePosMutex`와 모든 uncached/STORE/direct 경로를 보존하는 compile-gated sibling을 구현했다. production ABI exact, 244 objects 중 semantic diff `fszipopennode.cpp.o` 1개를 검증했다. actual PatHouse A1 production `48.1408 FPS/20.7724ms` 대비 B1 `50.8731 FPS/19.6567ms`로 frame time **-5.3707%**에 그쳐 첫 인접 10% 조건을 확정 실패했다. 사용자 immediate-reject 규칙에 따라 A2 없이 기각했고 public candidate assets/cache alias를 제거했으며 source/build/verifier만 실패 근거로 보존, production/remote 불변. See `gate6/perf/629_CACHED_ZIP_UNLOCKED_READ_EARLY_REJECT_20260901.md`.

## 2026-08-31 additions

- **628 VERIFIED/REJECTED/NOT VERIFIED (current PatHouse blocked-read attribution):** lazy shared-seqlock readwait3가 actual PatHouse 전후 화면과 `1 discarded + 6 accepted` 120-Present windows를 통과했다. 720 Presents/15.014s에서 >=1ms read는 2.847s=18.9623%였고, Wine fd4 len64 pipe는 1.460s=9.7243% wall, 반복 `HP_AK_B_base_{0,2}.wis`는 1.387s=9.2380% wall로 갈렸다. fd4는 Wine11 `create_file(44)`560ms, `select(29)`257ms, `set_queue_mask(116)`185ms, `event_op(31)`175ms, `get_handle_fd(48)`162ms, `close_handle(21)`121ms로 100% 귀속됐으며 어느 단일 request/가족도 actual 10% gate를 넘지 못한다. owner-scaled WIS upper bound만 10.3602%라 cached-vector archive-lock bypass를 A/B admission하되 실제 cache-hit 증명과 양쪽 인접 frame time -10%가 필수다. static-buffer readwait2 OOB는 same-account readwait1 control로 진단 회귀가 확정되어 보존/기각, production 불변. See `gate6/perf/628_CURRENT_PATHOUSE_READ_SOURCE_AND_WINE_REQUEST_ATTRIBUTION_20260831.md`.
- **627 VERIFIED/REJECTED/NOT VERIFIED (current-B exact owner time window):** production-shaped owner 진단이 reserve word60 CPU와 re-armable word61 CAS timestamp를 같은 trace에 실어 `0x23e94750`, pid/tid `74668/44904`의 유일 Profile `0x7` 및 delivery-tid가 다른 812 chunks를 explicit id로 결합했다(data loss 0, actual PatHouse 전후 PNG). 30.027896s wall에서 complete Acknex transform 14-block surface는 731,970us=2.4376%(완전 제거 +2.4985%, ideal 4/8-worker +1.8623/+2.1794%)라 병렬/HLE/fusion 10% 축을 기각했다. live A619 Wasm body/source로 확정한 `wasmStartJITOp[6420]+NormalCPU::run[6493]`도 754,673us=2.5132% wall뿐이라 #618의 구 28.4968%를 current B로 전이할 수 없다. 반면 libc `__read` blocked interval은 6,385,636us=21.2657%(완전 제거 +27.0094%)로 유일한 10%+ 실측 표면이지만, fd/object/Wine request 및 47.0241% 이상 causal removability는 별도 계측 전 NOT VERIFIED. mapped generated 52.1082%는 TLB 시간으로 부를 수 없어 mapping-epoch/span cache도 미승격. `--emit-symbol-map` 재링크 SHA12ca는 live A619와 달라 기각했고 production은 불변. See `gate6/perf/627_CURRENT_B_EXACT_OWNER_TIME_WINDOW_20260831.md`.
- **626 VERIFIED/REJECTED (fusion guard-cache Amdahl bound):** active fusion5는 production A2 대비 frame time `+3.405%`였고, 10% 개선선까지 candidate에서 `2.5555ms/frame`, 즉 wall의 `12.9635%`를 더 제거해야 한다. first-element reorder는 initial-fallback 56.255%에만 code guard를 건너뛰므로 guard가 전체 wall의 23.044%여야 하며, 완벽한 mapping-epoch cache도 12.9635%가 필요하다. 실측 entry rate와 604-byte/157-compare guard를 결합하면 각각 34.53us/19.43us per validation이 필요하지만 프레임당 실제 구조는 79.46KB/20,654 comparisons뿐이고 독립 wall timer가 없다. 새 epoch runtime ABI까지 정당화할 credible bound가 없어 둘 다 미구현/기각, production 유지. See `gate6/perf/626_DIRECT_WASM_GUARD_CACHE_AMDAHL_REJECT_20260831.md`.
- **625 VERIFIED/REJECTED (Acknex direct generated-Wasm fusion):** host helper 없이 production-B의 exact `+49650` export만 pure-Wasm SIMD macro로 rebind하고 142/143 group byte identity, 504 exports, 120 reloc patches와 원본문 fallback을 보존했다. reserve-before-reloc-map 주소 오류와 transform-wrapper relocation offset 20→source-proved 19를 fixture/actual 진단으로 바로잡은 뒤 actual PatHouse에서 fast elements 41,892,525를 직접 확인했다. 그러나 인접 A2 production `52.4548 FPS/19.0640ms` 대비 active fusion5 B2 `50.7276 FPS/19.7131ms`, frame time **+3.4049%**로 악화되어 즉시 기각/미배포. fusion3의 겉보기 +12.31%는 fast0 및 직후 A2와 -0.0494%라 control drift로 확정. 다음은 exact current-B owner-thread CPU profile로 transform/TLB 시간 share를 먼저 확정하고 10% Amdahl 상한을 넘는 구조 후보만 admission. See `gate6/perf/625_ACKNEX_DIRECT_WASM_FUSION_REJECT_20260831.md`.
- **624 VERIFIED/REJECTED (Acknex +49650 batch64 host HLE):** exact 3-op/9-byte prefix hash `4FA89EE0`, full 33-byte/live DLL guard, 64-element partial-resume helper와 mapping/mprotect/code epoch를 별도 ABI3 runtime으로 구현하고 Edge differential을 통과했다. actual PatHouse는 24,265,220 elements를 383,005 chunks(평균63.3548)로 처리해 import/guard 경계를 98.4216% 줄였지만, production B A1 `46.1453 FPS/21.6707ms` 대비 AOL64 B1 `13.2638 FPS/75.3932ms`, frame time **+247.9041%**로 붕괴했다. code/stale/yield/bailout/termination/epoch 오류는 모두0이므로 host C++/SIMDe 수학 자체가 generated Wasm SSE보다 느린 것이 확정되어 즉시 기각/미배포. 다음은 host helper 없이 원 generated-Wasm transform body를 caller group에 직접 co-location/inlining하는 region이다. See `gate6/perf/624_ACKNEX_OUTER_BATCH64_REJECT_20260831.md`.
- **623 VERIFIED/REJECTED (Acknex whole-function HLE):** 첫 actual PatHouse B1의 helper 23,391,040회 전부 `FallbackCodeBytes`였던 원인은 6-byte thunk terminal relocation 뒤 zero-length suffix를 invalid range로 처리한 matcher 버그였다. 최소 수정/ABI2/negative cache와 fresh cache-off actual PatHouse helper success 7,304,116을 검증했다. 그러나 exact ABI2 map으로 145 groups/44,458-key superset cache를 재그룹한 valid actual-PatHouse A1/B1은 `40.7870→10.9649 FPS`, frame time `24.5176→91.2001ms(+271.98%)`; B1 helper는 15,802,344/15,804,108=99.9888% 성공하고 code mismatch 0이었다. 즉 per-element host import/guard/math 자체가 grouped JIT SSE보다 압도적으로 느려 whole-function HLE는 즉시 기각/미배포, 다음은 검증된 수학을 재사용해 +49650을 64개씩 처리하는 outer-loop amortization이다. See `gate6/perf/623_ACKNEX_HLE_TERMINAL_RELOCATION_MATCHER_FIX_20260831.md`.
- **622 VERIFIED/SUPERSEDES 605/IN PROGRESS (Acknex transform island ASLR rediscovery):** #605의 11 zero는 scene 변화가 아니라 `acknex.dll` load base가 `7F360000→7F3A0000(+0x40000)`로 이동했는데 historical absolute EIP를 그대로 계측한 오류였다. 동일 RVA를 current base로 재해석하자 owner census가 `+49650/+49659/+46760/+46798/+467A6` 각 2,533,560 hits와 99.94908% loop를 복구했다. 이어 actual PatHouse exact-exit 20.006765초 창이 3,150,256 decisions 중 back edge 3,148,652 / fallthrough 1,604 = **99.949084%**를 양쪽 생존 counter로 직접 재확인했다. current B exact plan은 10 regions/91 blocks/1,398 ops, 31.0330% owner-entry surface이며 transform island를 포함한다. speedup은 아직 UNKNOWN; exact SHA+RVA+blockHash+live-target HLE와 실제 10% frame-time A/B가 다음 gate. See `gate6/perf/622_CURRENT_ACKNEX_TRANSFORM_ISLAND_ASLR_REDISCOVERY_20260831.md`.
- **621 VERIFIED/REJECTED/IN PROGRESS (frame-time 10% gate + exact exit histogram):** fresh-process A/C/B가 current 큰 이득의 주성분을 expanded AOT로 좁혔고, 실제 PatHouse B owner 창에서 245,541,925 generated entries/20.006s 및 331,813 entries/Present를 실측했다. `uboDirtySplit`은 36.6560→36.0527 FPS, frame time +1.6734% 악화로 구현 직후 제거했고, generic Binaryen post-link 후보도 33,912 marker/patch 중 제거 0이라 browser A/B 없이 기각했다. 별도 marker→owner-filtered 91-block/234-exit 파이프라인이 production-B byte-identical alias에서 20.006765초 실제 PatHouse window를 완주해 171 surviving/63 DCE-zero, observed taken 78,823,883, transform entry 3,150,256, loop 3,148,652/1,604를 실측했고 전후 화면과 cleanup zero를 검증했다. 계측 FPS는 비교값이 아니며, HLE/mega-function 구현과 실제 10% frame-time A/B가 진행 중이다. See `gate6/perf/621_CURRENT_FRAME_TIME_10PCT_GATE_AND_EDGE_HISTOGRAM_20260831.md`.
- **620 VERIFIED/ACCEPTED PRODUCTION (CreateEgg ACK same-process PatHouse):** Ghidra에서 S2C `0006[00,00]`이 `CJSLogic::AckCreateEgg`의 자연 C2S `0007` 방출과 `CGameManager::OnCreatEggAck -> CPopupSelectEgg::CreatEggResult`의 SelectEgg purge/remove를 함께 수행하는 진짜 생성 성공 ACK임을 확정했다. 운영 계정에서 `C2S0004 -> 5.541ms -> S2C0006 only -> 99.472ms -> natural C2S0007 -> S2C0003/0007/0005/000A/000B -> C2S0011`을 실측했고, 재부팅·별도 접속·C2S0005·바이너리 패치 없이 같은 URL/프로세스의 실제 카펫/가구/캐릭터/HUD/퀘스트 PatHouse 3D를 사용자와 함께 확인했다. 전체 307 tests pass. See `gate7/620_CREATEEGG_ACK_SAME_PROCESS_PATHOUSE_20260831.md`.
- **619 SUPERSEDED by 620:** 원격 multi-direct-loops와 host INIT reset 배포 사실은 역사 기록으로 유지하되, INIT reset을 첫 생성 직행 문제의 해결 원인으로 귀속한 결론은 기각했다. 저장 캐릭터 재선택 성공은 누락된 CreateEgg ACK를 우회했을 뿐이다. See `archive/619_REMOTE_MULTIDIRECTLOOPS_DEPLOY_AND_PATHOUSE_INIT_RESET_20260831.md`.

---

## 2026-08-30 additions

- **618 VERIFIED/ACCEPTED LOCAL DEFAULT (current PatHouse expanded AOT + multi-direct loops):** browser-wide owner selection을 libc `__read`/mailbox 대기에서 분리해 runtime `wasmStartJITOp` 15.1692% + `NormalCPU::run` 13.3277% = exclusive leaf 28.4968%(conditional ideal +39.8540%)를 직접 확정했다. opt-in multi-laminar loop runtime으로 actual PatHouse 44,395-block raw를 새로 기록하고 bounded-16 export, 143-group/33,912-patch currentabi1 cache로 변환했다. 실제 방 내부 A-B-A-B는 control 20.8840/21.7682, candidate 30.3458/29.4154 FPS, adjacent +45.3065/+39.4043/+35.1301%, median +39.4043%, condition mean +40.1128%. 배포쌍의 expanded-AOT와 multi-loop 기여는 분리되지 않았음을 명시. archive/manifest/corpus pin 뒤 로컬 기본 및 character-select reentry로 승격했고 구 Touch2/currentabi1은 rollback 보존. 파라미터 없는 fresh default가 143/44395/33912 등록, saved Azrok1, 실제 PatHouse를 통과. See `gate6/perf/618_CURRENT_PATHOUSE_EXPANDED_AOT_MULTI_DIRECT_LOOPS_GAIN_20260830.md`.
- **617 VERIFIED/INFERRED/NOT VERIFIED (HQEMU tier-2 directed hot-region plan):** runtime/production을 건드리지 않고 current raw graph + #607 owner census + #608 module resolver를 결합하는 deterministic planner/spec/verifier를 구현했다. single-block을 coverage에서 전부 제외하고 `count==1` unique exact forward edge만 admission한 13/13 directed multi-block regions(103 unique blocks, 849 ops, per-region 8–152<=256)이 owner generated-entry 6,124,880/20,242,521=30.2575%를 덮는다. 197 side exits 중 raw count>1인 21곳은 firstTarget 단정 없이 multi-site ambiguous dispatcher fallback이다. direct resolver 23.9790% + verified archive-span INFERRED 6.2785%이며 ntdll/libc/Azrok exact file SHA와 block hash 재검증을 publication 계약에 넣었다. 단 entry surface는 CPU-time/예상 가속률/실제 removed dispatch가 아니고 dynamic internal-edge taken counts가 없어 셋 모두 UNKNOWN; 아직 compiler/background publication/A-B는 없다. See `gate6/perf/617_CURRENT_HQEMU_TIER2_DIRECTED_HOT_REGION_PLAN_20260830.md`.
- **616 VERIFIED/INFERRED (current browser threading and regional-AOT direction):** JIT 뼈대는 upstream GitHub BoxedWine `BOXEDWINE_WASM_JIT`이 맞지만 현재 것은 Wasm-JIT 약 +4294/-501줄과 grouped cache/publication/broker/D3D9Web/IME를 더한 로컬 포크다. Wine KThread별 CPU*가 이미 pthread/Web Worker에서 병렬이고 Touch2는 pool32+PROXY_TO_PTHREAD, renderer-main도 3-slot async ring으로 겹친다. 따라서 Worker 증설은 단일 Acknex CPU stream을 쪼개지 못하며 임의 분할은 TLS/rollback 엔진급이라 기각. spare Worker는 compile/optimization에 쓰고 실행은 큰 guard-free structured region/AOT로 유지하는 축이 범용성과 잠재력을 함께 잡는다. 첫 multi-laminar hash-loop 표면은 846,384/20s=1796.99/Present, owner entry 4.1812%; 큰 후속은 content fingerprint 후 directory/name cache. See `gate6/perf/616_CURRENT_BROWSER_THREADING_AND_REGIONAL_AOT_DIRECTION_20260830.md`.
- **615 VERIFIED/NOT ADOPTED (current PatHouse frame-plan/multi-draw density):** 동작을 바꾸지 않는 `framePlanProbe=1`을 추가하고 실제 방 내부 전후 PNG에서 120 Presents를 측정. 20,400 draws=170/frame(UP159+indexed11), 정확히 blend-off/depth-on+write/stencil-off/full-mask인 DrawUP 89/frame가 complete-state+barrier 기준 13 groups/frame로 모여 이론상 170→94 calls, 76/frame=44.7059% 감소 표면과 실제 `WEBGL_multi_draw` 지원을 확인. 감사 후 bit-exact 숫자 직렬화·viewport/hostmip 경계를 보강한 fresh PatHouse 재실측도 동일했고 Present 8358→8653 재독에서 유지. alpha-test/depth-func 분포는 미기록이고 비인접 재정렬 의미보존 증명이 아니므로 실제 multiDraw 호출은 0, 미채택. 다음 안전 축은 structured-loop JIT이며 renderer는 order-independence classifier가 다음 gate. See `gate6/perf/615_CURRENT_PATHOUSE_FRAME_PLAN_MULTIDRAW_DENSITY_20260830.md`.
- **614 VERIFIED/REJECTED/NOT ADOPTED (current PatHouse NtCurrentTeb selective original-region):** broad 39-site 중 static-normal 9와 dynamic-normal source 8만 router로 보내고 side exit 22는 원 dispatcher에 남긴 17-site selective를 구현·독립검증했다(94/30550, router/patch 9/9, nonhost 93 groups byte-identical, host diff exact17 ULEB, fail-closed pins). 실제 방 내부 전후 PNG A-B-A-B-A는 A 30.5080/29.0847/28.1727, B 28.0624/27.5712 FPS; condition mean -4.9165%, adjacent median -4.3593%, local interpolated mean -4.7566%. A drift -7.6547%라 보편적 감속 크기는 단정하지 않지만 모든 B가 양옆 A보다 낮아 개선 후보로 기각. 서버 종료로 난 ERR_CONNECTION_REFUSED 두 시도는 행 없이 폐기했고 exact-URL CDP 안정화 gate를 보강. See `gate6/perf/614_CURRENT_PATHOUSE_NTCURRENTTEB_SELECTIVE_REGION_REJECT_20260830.md`.
- **613 VERIFIED/NEUTRAL/NOT ADOPTED (current PatHouse NtCurrentTeb broad original-region):** zero-reloc 원본 2965개에 exact publication U32 token을 제공하는 Touch2 sibling(추가 11,860B/process)과 10 original export co-location/9 router/9 patch의 pinned layout을 구현했다. raw/archive/manifest/runtime/URL ABI fail-closed, fixture 및 독립감사, 94/30550 validate 통과. broad candidate는 source dispatcher 39곳(static normal9+dynamic normal4+residual26)을 router로 보내지만 실제 PatHouse A-B-A-B-A가 A 26.3700/26.9263/27.1728, B 26.4181/27.2369 FPS; mean +0.0167%, 인접 median +0.2092%로 완전 중립이라 미채택. count 12.5854%는 CPU-time 증명이 아니었음. 다음은 residual 22곳을 원 dispatcher에 남기는 17-site selective. See `gate6/perf/613_CURRENT_PATHOUSE_NTCURRENTTEB_BROAD_REGION_NEUTRAL_20260830.md`.
- **612 VERIFIED/ACCEPTED-EXPERIMENTAL/NOT PRODUCTION (current PatHouse i386 PIC thunk clone):** exact 4-byte BX/DX/AX/DI/SI/CX thunk 11개를 caller group의 비export/비registration internal function으로 clone해 150 local return_call을 추가하고 94 groups/30550 registered entries/28944 patches를 보존했다. 94/94 validate, feature-off/on byte-repro, fixture/독립감사 통과. 실제 PatHouse 전후 PNG A-B-A-B-A는 A 29.8330/29.7472/30.4994, B 30.7270/31.2837 FPS; condition mean +3.2598%, 인접 효과 +2.9967/+3.2938/+5.1652/+2.5715%, median +3.1452%, A/B drift 2.2338/1.8118%. 고정 Wine11 root에서 소폭 재현 이득으로 experimental 수락하나 runtime text re-hash가 없어 public default는 유지. Edge starter PID handoff resolver를 추가했고 audit `RM` alias 오삭제 두 ZIP은 exact SHA copies로 완전 복구. See `gate6/perf/612_CURRENT_PATHOUSE_PIC_THUNK_CLONE_MODEST_GAIN_20260830.md`.
- **611 VERIFIED/REJECTED/NOT ADOPTED (current PatHouse INT9A fn8 same-corpus):** 과거 fn36/154-group cache를 재사용하지 않고 current `helpers.fn_8`의 decoded `Int9A`만 `normal_int9A` direct call로 바꾼 Touch2 sibling을 구현했다. 전용 fixture가 direct/generic/GP+segment+lazy successor/SMC/peek32 3-fault에서 0 fail, runtime/cache ABI는 exact 94/30550/28944 및 map12968408/262144. 실제 PatHouse 전후 PNG를 모두 육안 확인한 B1-A2-B2-A3-B3는 B 32.0600/32.6770/32.7308, A 30.8793/34.8541 FPS. A drift +12.8721% 속 인접 효과 +3.8236/+5.8217/-6.2463/-6.0920%, median -1.1342%; condition mean B/A -1.1484%. 재현 이득이 없어 운영 미채택. 병렬 build 오염 A1 23.8622는 visual-only로 제외. See `gate6/perf/611_CURRENT_PATHOUSE_INT9A_FN8_SAME_CORPUS_REJECT_20260830.md`.
- **610 VERIFIED/REJECTED/INFERRED/NOT VERIFIED (current PatHouse NtCurrentTeb boundary):** Unix Wine `NtCurrentTeb→pthread_getspecific`가 283,067=600.99/Present인 exact hot chain이지만 FS base 무조건 반환은 기각했다. main/child 모두 pthread key를 먼저 set하고 FS TEB descriptor를 나중에 설치하는 실제 초기화 창이 있으며 signal handler도 stack-mask TEB 탐색 후 FS/GS를 복구한다. GS 직접 해석은 glibc TCB/key-generation ABI 재구현이라 기각. 실제 TLS load를 유지한 cross-module fused region이 우선이고, per-KThread learned cache는 first-call original/nonzero, clone empty, reset/exec invalidation, reentry guard, FS/self-pointer match를 모두 갖춘 Wine 전용 후순위 후보다. FPS 효과는 A-B 전 미확정. See `gate6/perf/610_CURRENT_PATHOUSE_NTCURRENTTEB_FASTPATH_BOUNDARY_20260830.md`.
- **609 VERIFIED/INFERRED/NOT VERIFIED (current PatHouse Wine filesystem/PIC hot families):** rank1/3 ntdll `0x15F1F/0x15FAA`를 Wine 11 `unix/file.c::hash_short_file_name`의 case-folded 8.3 hash loop/last-dot scan으로 exact 대조했다(함수 entry 32,126, loops 439,255/407,129). `is_legal_8dot3_name` entry 43,199, `lookup_unix_name` entry 887와 hot invalid-char inner loop 221,680/193,970도 FDE/source/callsite로 확정. `NtCurrentTeb→pthread_getspecific` equal-count chain은 283,067=600.99/Present. libc `readdir64` 64,756(성공 63,296), mutex lock/unlock 각 61,070, scalar `strlen`도 확인. 현재 corpus exact 4-byte BX/DX/AX/DI/SI/CX thunk hash 174개 중 nonzero 13개가 1,209,674 generated entries=5.9759%=2,568.31/Present라 clone-only direct-tail 후보가 범용적이나 count는 CPU time이 아니므로 PatHouse A-B-A 전 미채택. Directory cache는 invalidation 미확정이라 보류. See `gate6/perf/609_CURRENT_PATHOUSE_WINE_FILESYSTEM_AND_PIC_THUNK_HOT_FAMILIES_20260830.md`.
- **608 VERIFIED/NOT VERIFIED (current PatHouse owner/module resolver):** 실제 PatHouse 전후 PNG가 유지된 owner `0x2733CBE0`/PID 71에서 상위 100 EIP를 전부 module/file-offset/원본 64 guest bytes로 해석했다. 분포는 `Azrok.exe` 40, Wine `ntdll.so` 35, `/lib/libc.so.6` 24, unmapped 1이며 rank 1–3은 ntdll `0x15F1F/0x7B70/0x15FAA`, rank 4는 `CD 9A`가 직접 보이는 354,543-hit Unix-call thunk다. Resolver 문자열로 map base가 64 bytes 밀린 첫 빌드는 실행 전 기각하고 resolver reserve를 48 words로 줄여 절대 ABI `owner 12968392 / ptr 12968400 / count 12968404 / map 12968408`를 복구했다. 94/30550/28944, 로컬/HTTP 해시, byte-repro, cleanup 모두 확인. ELF 정확한 함수명과 현재 corpus 격리 후보 성능은 다음 gate다. See `gate6/perf/608_CURRENT_PATHOUSE_OWNER_PROCESS_AND_MODULE_RESOLUTION_20260830.md`.
- **607 VERIFIED/NOT VERIFIED (current PatHouse game-CPU anchored census):** Ghidra-confirmed `Azrok.exe` 300-record scan key `v5-0059207c-3c3f909d`가 처음 실행한 CPU `0x27A6F1A0`을 reserve word60에 CAS로 고정하고, 30,550 entry를 그 CPU parameter와 일치할 때만 계수했다. 실제 PatHouse 전후 PNG가 붙은 20.0089초 창에서 20,242,521 hits, nonzero 2,471, top1/10/100 share 2.1700/16.4418/58.7325%를 얻었다. aggregate top `10635F1F/10627B70/10635FAA`와 equal-count chain이 main game CPU에서도 그대로 상위라 background-only 가설을 기각했다. Anchor/latch 141,298/141,297은 471 Presents에 거의 정확히 300회/Present라 static loop bound를 동적으로 재확인했다. 다음은 owner process mapping/guest bytes resolver로 `10635xxx`의 실제 module/semantics를 직접 확정한다. See `gate6/perf/607_CURRENT_PATHOUSE_GAME_CPU_ANCHORED_ENTRY_CENSUS_20260830.md`.
- **606 VERIFIED/NOT VERIFIED (current PatHouse full generated-entry census):** reserve 62/63의 caller-owned 30,550-U32 buffer로 94개 merged group의 모든 함수 본문 진입을 계측하고, 기존 local index 보존, +975,890 Wasm bytes, relocation patch 28,944, artifact SHA `8671...a840`, 94/94 validation을 확인했다. 실제 PatHouse 전후 PNG가 붙은 20.0169초 창에서 33,370,115 entry hits, nonzero key 3,612, top1/10/100 share 1.7593/12.2547/44.8893%를 얻어 단일 magic entry 가설을 기각했다. `Azrok.exe` exact static match에는 300-record `0059207C/AF` scan과 `_LocaleUpdate/__isleadbyte_l` chain이 포함된다. 다만 global cache는 여러 Wine CPU를 합치므로 EIP 숫자만으로 aggregate top의 process를 단정하지 않고, `0059207C` 실행 CPU로 필터한 전수 census가 다음 gate다. See `gate6/perf/606_CURRENT_PATHOUSE_FULL_GENERATED_ENTRY_CENSUS_20260830.md`.
- **605 SUPERSEDED by 622:** targeted-entry cache/counter mechanics and zero observations are valid, but the instrumented absolute EIPs no longer named the historical Acknex RVAs after a `+0x40000` load-base move. The “current scene does not execute the transform island” conclusion is false. See `archive/605_CURRENT_PATHOUSE_OLD_TRANSFORM_LOOP_ZERO_20260830.md`.
- **604 VERIFIED/INFERRED/NOT VERIFIED (current PatHouse guest-worker census):** currentabi1의 relocation map `12968408/262144`를 그대로 둔 별도 3-stripe clock-free runtime을 빌드하고 94 groups/30,550 entries/28,944 patches 및 HTTP 해시를 검증했다. 전후 PNG가 모두 실제 PatHouse인 30.0068초 창에서 outer JIT entry 276,306,321, valid C++->Wasm 276,306,322, slot miss 0, helper 115,981,547을 실측했다. helper 호출 구성은 fetchNext 72.04%, condition 21.54%, emulate 5.57%였으나 이는 횟수이지 CPU 시간 비율이 아니다. bookkeeping이 현행 핵심 표면이라는 추론은 강화됐지만 internal Wasm tail을 포함한 current hot EIP는 아직 미확정이므로 `+49650` transform loop exact-entry 계측이 다음 gate다. See `gate6/perf/604_CURRENT_PATHOUSE_GUEST_WORKER_CENSUS_20260830.md`.
- **603 VERIFIED/NOT VERIFIED (current PatHouse visual witness and fingerprint rejection):** current fastboot4/currentabi1의 `1:120:21480:14158560:2109626789:0:0` fingerprint가 PatHouse가 아니라 마우스 시점변환 전환 화면에서도 성립함을 직접 PNG로 확인했다. 이 tuple만으로 채택했던 Default/NoLiftoff 69.1551/72.2915/70.2774/69.9113 FPS 네 행은 PatHouse 성능에서 전부 기각했다. 같은 유지 탭을 30초 더 관찰해 방·가구·캐릭터·HUD가 보이는 실제 PatHouse를 시각 확인했고 direct 30초는 877/30.008s=29.2257 FPS였다. PatHouse 페이지 CPU profile은 main realm의 `packFFVertexData`가 전체 4.3816%였으나 guest pthread를 포함하지 않는다. 44 worker 동시 CDP profile은 active worker 응답 지연으로 중단했고 게임 liveness는 유지됐다. See `gate6/perf/603_CURRENT_PATHOUSE_VISUAL_WITNESS_AND_FINGERPRINT_REJECTION_20260830.md`.

---

## 2026-08-29 additions

- **602 VERIFIED/NOT VERIFIED (all quest kind audit):** kind0/1/2/3/5의 원본 완료 조건·보상표·wire 순서를 전수 대조했다. FunCorn 표는 전 항목 exact이고 합성 정상 순서에서 보상형 kind0/1/2 58/58, kind5 5/5, 전체 299 tests를 통과했다. 자연 표본은 kind0 food1001, kind3 aux0, kind5 aux212/202/203뿐이라 나머지 UI 수용은 NOT VERIFIED다. 정상 클라이언트 추가 보상 오류는 없었으나 임의 row 삽입, kind5 체인 반복, 비인접 후 무보상 retire, 복합행 제거, kind3 wrong-aux pending의 fail-closed 공백을 격리 재현했으며 추가 자연 캡처 전 운영 동작은 바꾸지 않았다. See `content/602_ALL_QUEST_KIND_REWARD_AND_CONTRACT_AUDIT_20260829.md`.
- **601 VERIFIED/NOT VERIFIED (tutorial play toy2000 + FunCorn order):** 원본 stage0 아즈론 메뉴는 toy2000 딸랑이 보유량이 있을 때만 `BtnPlay(0x36) -> 0x71 -> BabyToy(0x34)/0xE3`를 노출한다. 서버 S2C0007이 toy2000을 0으로 덮어 놀기 버튼을 숨긴 것을 확정해 starter toy를 복구했다. 운영 튜토리얼 3회가 `0011 retire -> 0012/100 -> 0011 next` 순서라 기존 반대순서 서버에서 모두 거부된 것도 확인하고, kind5 선행 retire buffer+atomic FunCorn ACK를 구현했다. 누락 300 FunCorn과 toy2000을 exact precondition recovery로 revision13→14에 복구했으며 전체 297 tests, 4서비스 active, 공개 HTTPS/WSS를 확인했다. 실제 재접속 UI 수용은 NOT VERIFIED다. See `content/601_TUTORIAL_PLAY_TOY2000_AND_FUNCORN_ORDER_20260829.md`.
- **600 VERIFIED/NOT VERIFIED (fastboot5 E1242/INT99 rollback):** 모바일 INT99 2897과 데스크톱 E1242가 모두 WS/TCP 전 fastboot5에서 재현됐다. fastboot5가 production guest-texture-recycle DLL 대신 일반 build DLL을 넣은 계보 회귀임을 확인하고, D3D Reset/host INIT 변경을 철회해 fastboot4로 롤백했다. `restore10`으로 launcher cache를 우회하고 fastboot5를 quarantine했으며 공개 200/206, 4서비스 active, warning 0, 전체 295 tests를 확인했다. 정확한 제보 기기 재수용은 NOT VERIFIED다. See `gate7/600_FASTBOOT5_E1242_ROLLBACK_20260829.md`.
- **599 PARTIALLY SUPERSEDED by 600 (fresh create legacy collision):** 신규 account가 `Azrok1`/`Player` 같은 이름을 만들 때 account 구분 없는 과거 name-only snapshot이 첫 `0007`에 이식되어 date=0 튜토리얼을 깨는 경로를 직접 재현하고 신규 create의 persisted import를 차단한 결론은 유지된다. fastboot5/D3D Reset 배포 결론은 #600에서 기각·롤백했다. See `archive/599_FRESH_CREATE_LEGACY_COLLISION_AND_D3D_RESET_STATE_20260829.md`.

## 2026-08-28 additions

- **598 VERIFIED/NOT VERIFIED (fresh-prefix D3D9 registry fastboot4):** 다른 컴퓨터 로그의 app/root/JIT는 정상 완료됐지만 `Unknown int 99 index 2897` 뒤 worker `alert is not defined`로 첫 네트워크 전에 중단됐고 u32ws에는 해당 계정 WS accept가 없었다. #596 A/B는 baseline `reg add`가 같은 IndexedDB prefix에 남아 후보를 가린 오염 실험이었다. `fastboot4`는 fresh prefix 필수 D3D9 registry 등록만 복구하고 acklog/`-diag`/`+seh` 제거는 유지한다. 공개 Chrome fresh origin에서 first drawn Present/FPS 16.2, console 오류 0, 구 fastboot3 URL 자동 승격, 공개 157,274,465-byte app 200과 전체 293 tests를 확인했다. 제보 물리 PC의 최종 PatHouse 수용은 NOT VERIFIED다. See `gate7/598_FRESH_PREFIX_D3D9_REGISTRY_FASTBOOT4_20260828.md`.

## 2026-08-27 additions

- **597 VERIFIED/NOT VERIFIED (u32ws + playazrok.com Cloudflare Tunnel):** Ubuntu `u32ws`의 `/home/u32ws/32dev/azroksrv`에 immutable 웹 런타임·계정/상태 분리 동기화와 user-systemd 4서비스를 배치했다. Windows 네이티브 helper의 import-time `ctypes.windll`만 OS 가드해 Linux 코어 9200/9300, 웹 8765, bridge 9201을 모두 loopback에서 실측했다. `playazrok` tunnel과 apex proxied CNAME을 연결하고 HTTPS 200, 157,274,401-byte 앱 Range 206, 공개 WSS 서명 ticket→원본 로그인/heartbeat→코어 405-byte `0016/0004/0000`, 전체 292 tests를 확인했다. 로컬 NXDOMAIN cache 만료 뒤 픽셀 수용과 Cloudflare Access 공개 정책은 NOT VERIFIED다. See `gate7/597_U32WS_PLAYAZROK_CLOUDFLARE_TUNNEL_20260827.md`.
- **596 SUPERSEDED by 598 (contaminated browser cold-boot A/B):** app/root/JIT가 약 1.3초였고 acklog/`-diag`/`+seh` 제거가 유효한 점은 유지된다. 그러나 같은 origin baseline의 D3D9 registry가 fastboot 후보에 남아 `reg add` 제거를 잘못 수용했다. fresh prefix 실패로 기각했으며 #598의 fastboot4가 registry 등록을 복구했다. See `archive/596_BROWSER_COLD_BOOT_PRODUCTION_DIAGNOSTIC_REMOVAL_20260827.md`.
- **595 VERIFIED/NOT VERIFIED (mobile touch double-scale removal):** #593은 브라우저 CSS 좌표를 현재 1024×768 논리 좌표로 올바르게 환산했지만, 이를 SDL-window 좌표용 `mouseMove/mouseButton`에 넘겨 내부 `xFromScreen/yFromScreen` 축소를 한 번 더 적용했다. 새 불변 `korean6chat1touch2`는 logical 전용 공통 함수로 XServer에 좌표를 그대로 보내고 recorder/audio/button mapping을 공유한다. pointer exports와 currentabi1 map base `12968408`/capacity `262144`, 이전 touch1 불변 해시, 새 빌드, 전체 289 tests, 8765 실제 전달 해시와 현재 route의 touch2 선택을 검증했다. 물리 모바일 네 모서리 수용 시험은 NOT VERIFIED다. See `webport/595_BOXEDWINE_TOUCH_DOUBLE_SCALE_FIX_20260827.md`.
- **594 VERIFIED/NOT VERIFIED (cold-boot duplicate root prewarm):** 현재 서버 선택 스크립트가 실행 페이지의 `xim25koreanlocale2` 167,825,891 B root가 아니라 사용하지 않는 구 root 167,172,869 B를 먼저 캐시해, 빈 origin의 최대 archive 경로가 474.05 MiB로 늘어난 회귀를 확정했다. 앱/root/JIT를 같은 불변 상수와 병렬 `Promise.all`로 묶고 실행 URL에 정확한 root와 `korean6chat1touch1` stem을 명시했다. 실제 로그에서 세 올바른 archive 요청이 같은 초에 시작되고 구 root가 사라진 것을 확인했으며, 필수 경로는 314.62 MiB로 159.43 MiB 감소했다. HEAD 캐시 계약, Node 문법, 전체 288 tests 통과. 완전히 새 물리 브라우저의 최종 첫 D3D 시간은 NOT VERIFIED다. See `gate7/594_COLD_BOOT_DUPLICATE_ROOT_PREWARM_FIX_20260827.md`.
- **593 SUPERSEDED by 595 (BoxedWine logical touch pointer):** 브라우저의 논리 화면 환산과 전용 export 도입은 유효하지만, 환산된 좌표를 SDL-window 좌표용 `mouseMove/mouseButton`에 넘겨 내부 축소가 다시 적용되었다. 물리 모바일 우하단 오차가 남는 직접 증상으로 기각했으며 #595가 logical 전용 전달로 교체했다. See `archive/593_BOXEDWINE_LOGICAL_TOUCH_POINTER_20260827.md`.
- **592 VERIFIED/NOT VERIFIED (all local facility returns to Plaza):** 현재 마법학원 퇴장에서 누락된 C2S `0016[01]` 후 S2C `000D[00]`을 직접 확인했다. 수동 전송 뒤 5회 `0004[01]` calibration과 C2S/S2C `0064`가 이어져 Plaza 복귀를 실측했다. 서버는 이제 로컬 시설 kind 06–0C 전부에서 첫 `0016[01]`에 `000D[00]`을 한 번 보내고 기존 Plaza calibration을 재사용하며, PatHouse/Plaza 오발은 막는다. 새 코어 실제 TCP에서도 magic 퇴장이 `0016+000D`, 이어 5회 `0016+0004`를 반환했고 전체 288 tests를 통과했다. 실제 UI 7개 시설 전수 수용 시험은 NOT VERIFIED다. See `server/592_LOCAL_FACILITY_PLAZA_RETURN_0016_20260827.md`.
- **591 PARTIALLY SUPERSEDED by 593 (native SDL touch and mobile landscape fullscreen):** #590의 잘못된 touch→MouseEvent 합성을 제거한 결론과 모바일 4:3 fullscreen contain 실측은 유효하다. native SDL touch만으로 물리 모바일 우하단 오차는 해결되지 않아 593의 BoxedWine 논리 화면 직접 주입이 교체했다. See `archive/591_NATIVE_SDL_TOUCH_AND_MOBILE_LANDSCAPE_FULLSCREEN_20260827.md`.
- **590 PARTIALLY SUPERSEDED by 591 (mobile touch coordinates and context menu):** PC 게임 영역 context menu 차단은 유효하다. 커스텀 touch capture/MouseEvent 환산은 물리 모바일에서 기각되어 591이 제거했다. See `archive/590_MOBILE_TOUCH_COORDINATE_AND_GAME_CONTEXT_MENU_20260827.md`.
- **589 VERIFIED/NOT VERIFIED (delete, existing-roster PatHouse, trusted mobile WSS):** 마지막 슬롯만 허용하던 서버 삭제 조건을 제거하고 생존 캐릭터의 durable storage slot은 유지한 채 논리 roster만 재밀집했다. 운영 폐기 계정에서 가운데 슬롯 삭제 `0008[01,00]`과 후속 재생성을 확인했다. 기존 roster의 신규 캐릭터는 다음 heartbeat에 검증된 `0005` 선택 진입을 한 번 재생해 `0016/0003/0007/0005/000A/000B`를 반환한다. 모바일 WSS는 이름 불일치 직접 9201을 제거하고 MagicDNS 동일 TLS 443 `/azrok-ws`로 통합해 인증서 SAN, ticket 로그인, 405-byte 코어 응답을 확인했다. 물리 모바일의 최종 PatHouse 장시간 접속은 NOT VERIFIED다. 전체 283 tests 통과. See `gate7/589_CHARACTER_DELETE_EXISTING_ROSTER_PATHOUSE_AND_TRUSTED_MOBILE_WSS_20260827.md`.
- **588 VERIFIED (recoverable full account reset):** 홈페이지 하단에 2단계 확인식 `계정 완전 초기화`를 추가했다. 실행 중 계정은 거부하고, 저장된 캐릭터·인벤토리·퀘스트 상태를 `reset_accounts`로 복구 가능하게 보관한 뒤 모든 기존 브라우저 결합과 복구코드를 폐기하고 요청 브라우저에 새 동적 계정을 발급한다. 폐기용 임시 브라우저의 라이브 API에서 계정 교체와 구 복구코드 403을 확인했고, 실제 홈페이지 하단 UI를 시각 확인했으며 전체 282 tests가 통과했다. See `gate7/588_FULL_ACCOUNT_RESET_20260827.md`.
- **587 VERIFIED (LAN and Tailscale HTTPS/WSS access):** LAN `<lan-ip>`와 Tailscale IP `<tailscale-ip>`의 8765/9201 전용 리스너를 확인하고, HTTP 200 및 WSS 101 admission 응답을 실측했다. 관리자 권한 없이 Tailscale Serve를 443→8765, 9201→9201로 구성해 `https://<tailnet-host>/`의 홈페이지 200과 `wss://<tailnet-host>:9201`의 101을 확인했다. 활성 게임 세션은 중단하지 않았다. See `gate7/587_LAN_TAILSCALE_SERVE_ACCESS_20260827.md`.
- **585 VERIFIED/NOT VERIFIED (fresh PatHouse and logout completion):** 신규 `playable` date=0 원본 부트스트랩을 기본 복구해 수정하지 않은 클라이언트의 PatHouse 3D, baby Azron, HUD/퀘스트 UI와 `pathouse_stable`을 라이브 확인했다. 로그아웃의 빈 0002 ACK와 후속 0000 roster 재전송은 같은 프로세스의 4슬롯 UI를 되살리지 못하고 무한 로딩을 남겼다. 마지막 C2S 0001에는 동적 확인된 S2C `0001[00]` 종료를 응답하고, 웹 실행기는 clean exit에서 서버 선택 화면으로 복귀한다. 공식 웹의 정확한 로그아웃 URL은 NOT VERIFIED다. See `gate7/585_FRESH_BROWSER_PATHOUSE_AND_LOGOUT_COMPLETION_20260827.md`.
- **584 VERIFIED/NOT VERIFIED (current private frontends and cold boot):** 현재 코어/앱이 최신 `dynamicaccounts2_startersplash1` 세대임을 파일 시각·불변 ZIP SHA-256으로 확인하고, 인증 모듈보다 오래 떠 있던 loopback WSS 브리지만 최신 코드로 재시작했다. loopback, LAN `<lan-ip>`, Tailscale `<tailscale-ip>`의 8765/9201 전용 프런트엔드가 모두 브라우저 티켓·원본 로그인·heartbeat 뒤 코어 405-byte 응답을 반환했다. 실제 LAN 홈페이지 버튼 경로는 314.62 MiB 콜드 캐시에서 약 43초 뒤 첫 D3D 렌더에 도달하고 49초 이상 heartbeat를 유지했다. Tailscale 원격 물리 기기 브라우저와 사용자가 본 종료의 정확한 client-side 원인은 NOT VERIFIED다. See `gate7/584_CURRENT_LAN_TAILSCALE_FRONTENDS_AND_COLD_BOOT_20260827.md`.
- **583 VERIFIED (recovery visibility, canvas fit/fullscreen, favicon):** 실행 화면의 복구 코드 버튼을 `표시 및 복사`로 명확히 하고 값 제거까지 수행하는 숨김 기능을 추가했다. 핸들러가 전혀 없던 화면 맞춤과 정의되지 않은 함수 호출로 예외가 나던 전체 화면을 실제 구현으로 교체했다. 라이브 실행에서 1024×768→510×382 맞춤, 게임 렌더 source/overlay delta 0, 3840×2160 전체 화면 진입과 예외 없음, 숨김 후 코드 길이 0을 확인했다. 루트 `azrok.ico`를 네 주요 페이지에 연결했으며 전체 273 tests가 통과했다. See `webport/583_RUNTIME_RECOVERY_VISIBILITY_CANVAS_FULLSCREEN_AND_FAVICON_20260827.md`.
- **582 VERIFIED (server NPC right edge and live online count):** 서버 선택 헤더의 꿀벌 NPC를 auto margin으로 헤더 우측 끝에 배치했다. 8765의 private status API가 9300 overview에서 `connected is True`인 플레이어만 세어 반환하며, 서버 목록은 즉시 및 10초마다 `현재 N명 접속`을 갱신한다. 라이브 API와 브라우저에서 현재 0명 표시를 확인했고 전체 271 tests가 통과했다. See `webport/582_SERVER_NPC_RIGHT_AND_LIVE_ONLINE_COUNT_20260827.md`.
- **581 VERIFIED (server header title/NPC swap):** 서버 선택 헤더를 아즈로크 로고 → 제목/안내문 → 꿀벌 NPC 순서로 재배치하고 NPC 여백을 왼쪽으로 옮겼다. 실제 브라우저 DOM 순서와 화면 배치를 확인했다. See `webport/581_SERVER_HEADER_TITLE_NPC_ORDER_20260827.md`.
- **580 VERIFIED (stable recovery, gold title, exact frame):** 복구 코드는 서버 비밀키 HMAC과 계정별 revision으로 계산되어 표시만으로는 바뀌지 않고 명시적 `복구 코드 재생성`에서만 회전한다. 평문은 registry에 저장하지 않으며 현재 코드는 여러 브라우저를 같은 계정에 묶을 때 재사용된다. 메인 제목은 금색 채움·검정 외곽선·주황 입체 그림자로 교체했다. 게임 화면 어긋남은 1px가 아니라 `#dropzone` border-box가 테두리만큼 줄어든 7px 문제였고, content-box로 수정한 뒤 source/overlay delta 0 및 네 변 inset 7px를 라이브 측정했다. See `webport/580_STABLE_RECOVERY_GOLD_TITLE_AND_EXACT_GAME_FRAME_20260827.md`.
- **579 PARTIALLY SUPERSEDED by 580 (player surface recovery and boot overlay):** 서버 선택 헤더 로고/NPC 순서와 NPC 73px, 진단 버튼 숨김, 복구 코드 표시 UI, 안내문, 게임 프레임 상단 중앙 부팅 오버레이는 유효하다. 추정 1px 오버레이 보정과 매 표시 회전 정책은 580이 교체했다. See `webport/579_PLAYER_SURFACE_RECOVERY_BOOT_OVERLAY_AND_ALIGNMENT_20260827.md`.
- **578 VERIFIED (server NPC, sky attendance, title/video readability):** 250×234 투명 `NPC_010.png`를 해시 보존해 서버 선택 헤더의 기존 로고 왼쪽에 추가했다. 출석도장은 기존 NPC/지팡이를 유지하고 하늘색 그라데이션으로 변경했다. 메인 제목은 36px 굵은 맑은 고딕, 밝은 노랑 글자, 1px 진청 외곽선과 반투명 청록 명판으로 보정했다. 92px 영상 미리보기는 화면을 덮던 기본 컨트롤을 제거하고 음소거 자동재생/반복으로 바꿨다. See `webport/578_SERVER_NPC_ATTENDANCE_SKY_AND_TITLE_READABILITY_20260827.md`.
- **577 VERIFIED/NOT VERIFIED (title, dead-link guard, recovered promo video):** 배너 제목을 상하 50%·가로 53%로 옮기고 34px 굵은 연노랑 글자/청록 외곽선으로 가독성을 높였다. 제공된 170.958초 320×240 `azrok_wmv9.wmv`를 해시 보존하고 H.264/AAC 미리보기와 원본 다운로드를 우측 영역에 연결했다. 원본 다운로드 URL과 파일명은 일치하지만 별도 `right_banner_movie.swf`와 동일 영상인지는 NOT VERIFIED다. 게임시작/영상 다운로드 외 홈페이지 링크는 종료 안내로 통일했다. See `webport/577_HOMEPAGE_TITLE_LINK_GUARD_AND_PROMO_VIDEO_20260827.md`.
- **576 VERIFIED/INFERRED (compact titles and unofficial notice):** 공지/만화/랭킹/베스트 스크린샷 제목 바를 45px에서 37px로 약 17.8% 축소하고, 미회수 `main_menu.swf` 대체 배너 중앙에 `아즈로크 복원 프로젝트` 및 `한솔교육 공식 복원 프로젝트가 아닙니다.` 안내를 추가했다. 원본 53-table DOM과 실행 경로는 유지했으며 중앙 글자 장식은 퍼니또 공통 디자인 문법 기반 복원 해석이다. See `webport/576_HOMEPAGE_COMPACT_HEADERS_AND_UNOFFICIAL_PROJECT_NOTICE_20260827.md`.
- **575 VERIFIED/INFERRED (Funitto retro panel chrome):** 2011-10-02 `fj_intro.html`과 2012-06-10 `evlist/noticelist/cust` 웨이백 캡처 및 사용자 제공 화면에서 반복되는 작은 Dotum, 주황 탭/버튼, 하늘색 로그인 상자, 연두 보조 상자, 흰색/연크림 내용판을 원본 아즈로크 53-table DOM 위에 적용했다. 공지/만화/랭킹/스크린샷 제목은 원본 338/289x45 영역을 유지하고, 로그인은 233px 원본 셀 안에 퍼니또식 제목띠를 추가했다. 개별 미회수 `body_main_*_tit.gif`의 픽셀 복제는 아니며 공통 디자인 문법 기반 복원 해석이다. See `webport/575_FUNITTO_RETRO_PANEL_AND_LOGIN_CHROME_20260827.md`.
- **574 VERIFIED (preserved-art banners):** 1024x768 `MainLoading.png` 중앙부를 915x305 메인 배너에 상하 크롭 적용하고, 게임시작 GIF의 불투명 영역을 위 약 16px/아래 약 22px로 균형 보정했다. `azrok_dc_2.jpg` 숲 장면에는 당시식 가이드 제목을 오버레이했으며, 289x95 출석도장에는 `NPC_02.png` 고양이와 `Mouse2_0.png` 지팡이를 크림·주황 배너로 함께 배치했다. 빌더 해시, 브라우저 이미지 실패 0개, 전체 페이지 실측을 확인했다. See `webport/574_AZROK_PRESERVED_ART_BANNERS_20260827.md`.
- **573 VERIFIED (body centering and uncropped art):** “가운데 정렬”을 상단바 아래 1019px 본체에만 적용하고 메인 로고는 축소 크기를 유지한 채 원래 좌측 42px 위치로 복귀했다. 게임시작 슬롯을 233x154로 높여 191x152 GIF의 상하 크롭을 제거했으며, `azrok_bg03.jpg`에는 좌측 페이드와 상단 56px 하늘색 페이드를 함께 적용해 사각 절단선을 없앴다. 실제 1101px viewport에서 본체 좌우 중앙 정렬, 로고 위치, 이미지 로드 실패 0개를 확인했다. See `webport/573_AZROK_BODY_CENTERING_AND_UNCROPPED_START_ART_20260827.md`.
- **572 VERIFIED (archive layout and Funitto runtime shell; alignment details superseded by 573):** 원본 53-table 홈페이지 DOM을 유지하면서 미회수 만화 제목 GIF가 `height=100%` table을 289px로 늘린 공백과 1.8px로 축소된 343x95 가이드 배너를 선택적으로 보정했다. `azrok_bg03.jpg` 배경 및 퍼니또 계열 실행 외곽 통일은 유효하며, 로고 위치·게임시작 슬롯·배경 상단 경계의 최신값은 #573을 따른다. canvas/runtime/launcher/app은 변경하지 않았다. See `webport/572_AZROK_ARCHIVE_LAYOUT_AND_FUNITTO_RUNTIME_SHELL_20260827.md`.
- **571 VERIFIED (requested branding substitutions):** 312x246 `Loading1.png`를 미회수 `main_menu.swf` 영역의 로고와 서버 선택 헤더 로고에 적용하고, 261x208 16-frame `azrok_main_gamestart04.gif`를 원본 233x79 게임시작 슬롯과 기존 서버 선택 링크를 유지한 채 적용했다. 빌더가 두 원본의 SHA-256을 보존해 패키징하며 실제 브라우저에서 메인·게임시작·서버 헤더 표시를 확인했다. D3D9Web/runtime/launcher는 수정하지 않았다. See `webport/571_AZROK_LOADING_LOGO_AND_GAME_START_ASSET_SUBSTITUTION_20260827.md`.
- **570 VERIFIED (Wayback all-range asset audit):** 공통 누락 후보 65개에 2005-2020 연도별 Availability와 exact CDX를 세 차례 수행하고 공통 실패를 재시도해 만화 썸네일 GIF 1개 회수, 유효 캡처 없음 64개, 미확정 0개로 닫았다. `re_azrok` 64개 표적의 전 기간 캡처 154건(2014-12-20~2024-08-12)은 raw 재생 세 차례와 마지막 6 digest 개별 확인으로 전부 파킹 HTML임을 확정했다. 정상 3D 이미지/SWF는 0개다. 원본 `common.css`와 공용 JS 5개는 정상 회수해 CSS를 페이지에 적용하고 JS는 보존 패키징했다. See `webport/570_WAYBACK_FULL_RANGE_AZROK_ASSET_RECOVERY_20260827.md`.
- **569 VERIFIED (archive-derived homepage/browser launch):** 첫 현대식 재작성은 폐기했다. 2012-01-29 `azrok_main.utf8`의 53-table DOM, 로그인/설문/공지/랭킹/hidden launch iframe과 픽셀 구획을 정본으로 사용하고 Wayback/tracker만 제거했다. 공통 퍼니또/만화 GIF 69개를 signature/Content-Type/SHA-256 검증 회수해 연결했으며 TCG GIF 2개는 격리했다. 로컬 CDX가 누락한 만화 썸네일도 live Wayback Timegate 직접 확인으로 복구했다. 원본 게임시작 자리에서 서버 선택과 `startersplash1` BoxedWine으로 전환하며, 사용자가 Acknex starter 표시와 이후 정상 전환을 확인했다. See `webport/569_AZROK_HOMEPAGE_AND_BOXEDWINE_LAUNCH_RESTORE_20260827.md`.
- **568 VERIFIED (static/package/browser/user visual):** BoxedWine 뒤의 별도 `acknex_mainwin` starter는 GDI/source-canvas 경로이며 기존 11개 launcher의 `-NWND`가 이를 숨겼다. `-NWND` 제거 후보와 hold/release 수정 뒤 사용자가 홈페이지의 실제 버튼 경로에서 Acknex 로딩 화면이 알아볼 수 있게 표시되고 이후 한솔 화면으로 정상 전환됨을 확인했다. clear-only Present 세 번은 D3D overlay를 표시하지 않고 첫 draw 포함 Present `4`에서만 전환한다. See `webport/568_ACKNEX_STARTER_WINDOW_HOLD_AND_DRAWN_PRESENT_HANDOFF_20260827.md`.

---

## 2026-08-08 additions

- **555 VERIFIED (boot UI, XIM boundary, production routing); human Plaza chat acceptance pending**: the silent 45–50 second black boot now shows dependency/Wine stages and elapsed time until the first real Present. Live XIM probes proved UTF-8 6-byte Korean commits reach Wine `XLookupChars`; the old unavailable `ko_KR.EUC-KR` Unix locale was the remaining lossy conversion boundary. New and old private-session URLs now use the immutable `C.UTF-8` launcher app while preserving original binaries and Windows ACP949. Full tools suite 234/234 passes; visible Plaza Korean text and natural C2S `0x006A` remain the user keyboard gate. See `gate5/555_BOOT_PROGRESS_AND_KOREAN_IME_PRODUCTION_ROUTE_20260808.md`.

## 2026-08-07 additions

- **549 VERIFIED (source/build/package/live delivery), Plaza acceptance pending**: BoxedWine now supplies the minimal Wine 11 XIM/XIC ABI and returns committed browser UTF-8 as `XmbLookupString` `XLookupChars`, bypassing the physical-key path that produced `vvvv`. Immutable korean3/xim1 assets, guest libX11/package hashes, 221 tests, and LAN HTTPS delivery are verified; actual Azrok Edit acceptance remains the user's play-test gate. See `gate5/549_BOXEDWINE_FAKE_XIM_KOREAN3_STATIC_CONTRACT_20260807.md`.
- **548 VERIFIED (audit/launcher contracts), OX completion pending**: the remembered “continue after exception” case belonged to the WineGStreamer BGM loader failure, not OX. Current player2~6 already have native D3D9 and `+seh`; the OX fault is an unhandled invalid-BMAP dereference, so blanket exception skip was rejected pending an exact last-writer capture. See `gate5/548_WEB_OX_SEH_LAUNCHER_AUDIT_20260807.md`.
- **547 VERIFIED (static/server contracts), visual/end-to-end pending**: `playable` no longer starts a fresh account at the shipped level-25 demo state. Ghidra confirms that a zero packed date lets the unmodified client seed the original kind-5/212 tutorial, and the server now accepts the observed `0010 -> 0011 -> 0007 -> 0010 -> 0011` growth order without inventing the next aux. New-character PatHouse 3D visibility and the complete tutorial-to-late-game run remain user-test gates. See `content/547_ORIGINAL_FRESH_BOOTSTRAP_AND_GROWTH_ORDER_20260807.md`.
- **546 VERIFIED (BGM/audio/context/live delivery); IME portion superseded by 549**: browser BGM is diagnostic opt-in, guest output forwards 44.1 kHz, obsolete BGM controls are removed, and the whole visible game surface suppresses the browser context menu. See `gate5/546_GUEST_BGM_44100_RUNTIME_IDENTITY_AND_CONTEXT_MENU_20260807.md`.
- **545 SUPERSEDED by 549 for IME; GUI evidence retained**: the clipboard/forced-Ctrl route produced literal `vvvv` and is now only a rollback fallback. The loopback GUI/account API restart evidence remains valid. See `archive/545_KOREAN_IME_CLIPBOARD_CTRL_AND_LIVE_GUI_RESTART_20260807.md`.
- **543 VERIFIED**: an observed remote `409` was exhausted automatic guest capacity, not a LAN route failure. The private browser pool is now `player2` through `player6`, existing bindings are preserved, and only the 192/Tailscale asset listeners were restarted. New guest launchers retain the native-D3D9/SEH path; that does not claim the separate OX Acknex fault is fixed. See `gate7/543_PRIVATE_ADMISSION_CAPACITY_SEH_AND_GAME_CONTEXT_MENU_20260807.md`.
- **544 SUPERSEDED by 565**: the fixed five-profile/password management design is archived. See `archive/544_PRIVATE_ACCOUNT_GUI_MANAGEMENT_20260807.md`.

---

## §1 목표 판정 (2026-07-29 기준)

| 목표 | 판정 | 최신 실측 | 근거 |
|---|---|---|---|
| 데스크톱 50fps — 격리 Edge 탭 | **통과** | BGM 켠 채 30초×3창 = 71.97 / 71.91 / 67.91 fps | 520 |
| 데스크톱 50fps — in-app 브라우저(실사용 경로) | **미통과** | 40.35 fps (HUD 38.6~41.0, `slow`) | 495 · 508 · 509 |
| 음악 재생 | **우회 통과** | 원본 MP3 를 브라우저가 대신 재생, 엔드포인트 상관 0.9786 | 516 · 494 · 505 |
| 게임 내부(Wine) 음악 디코딩 | **지속 재생 확인, 잔여 끊김 있음** | ① `libpcre2-8.so.0` 미탐색 → `winegstreamer.so` dlopen 실패 → unixlib 핸들 0 → 널 디스패치. pcre2 를 `/lib`·`/usr/lib` 에도 두자 크래시 0건(524). ② 그 뒤 남은 심한 끊김은 **진단 앱(`audiodbg2`)의 `+quartz`·GST LOG 추적이 만든 것**. 추적을 끄니 부팅 325초→40초, 게스트 오디오 비영 95.5%, 루프백 97.45%(525) | **525** · 524 · 523 · 461 · 462 · 463 |
| 부팅 300초 + 주기적 정지 | **해결 — 프리픽스 업데이트가 매 세션 반복** | `run_wineboot()` 은 부모 없는 프로세스에서 무조건 돌고 타임아웃이 소스에 `5*60*1000`(=300초)로 박혀 있다. `SetEvent` 는 wineboot main 의 **맨 마지막 줄**이라 `update_wineprefix()` 에서 막히면 300초를 다 채운다. 그 블록은 `.update-timestamp` 가 `wine.inf` mtime 과 같거나 `disable` 이면 통째로 건너뛴다 — 실제 값이 약 8시간 어긋나 있었다. **`disable`(8바이트) 로 바꾸니 프로덕션에서 부팅 330초→40초, 정지 17~24회/분→0회, 무음 0.00%, fps 40.6** | **528** |
| 게스트 BGM 품질 | **드롭아웃 0** | `noprefixupd1` root · 프로덕션 설정 60초 창에서 콜백 1,406회 중 **무음 0회**. #257 의 바닥값 2.30% 와 #525 의 0.21% 를 모두 밑돈다 | **528** · 524 |
| 게스트 MP3 디코딩의 fps 비용 | **사실상 0 — 목표 충돌 없음** | 통제 A/B: 게스트 디코딩 39.16 vs 브라우저 대행 40.83 fps(차이 1.67, 편차 이내). "음악을 게스트가 낸다" 와 "50fps" 는 상충하지 않는다 | **528** |
| 브라우저 50fps | **미달 — #520 재현 불가** | 오늘 통제 측정은 36.8~40.8 fps 에 모인다. #520 의 67.9~72.0 은 재현되지 않았고 원인 미상. **#520 은 root/app/stem/씬을 기록하지 않아 문서만으로 재현 불가** | **528** · 520 |
| ⚠ JIT 캐시 4배 주장 | **폐기** | 근거였던 135.64fps 는 이상치. 게스트 자체 카운터 `D3D9WEB_FPS_SAMPLE` 이 34~40fps 로 외부 측정과 일치한다. 앞으로 fps 는 이 카운터를 우선할 것 | **528** · 527 |
| 오디오 버퍼 축 | **미결 — 526 의 A/B 는 무효** | 526 의 T1/T2 는 한 Edge 인스턴스를 재사용해 측정했고 렌더러 워킹셋이 4.2→**14.5GB** 로 불어난 상태였다. 수정 없는 채택 스템도 fps 3.35/무음 75.65% 로 같이 무너져 **파라미터 귀속이 성립하지 않는다**. 버퍼 축을 닫는 근거는 #257 의 통제된 A/B 뿐. 소스는 전부 원복 | **526** · 257 |
| **브라우저 인스턴스 수명** | **측정 지배 변수 (신규)** | leg 를 연달아 돌리면 `msedge` 렌더러 워킹셋이 누적돼(root 160MB + 1GB 힙 × leg 수) 게임이 유휴 0.5fps 까지 붕괴한다. **leg 마다 새 브라우저**로 시작하고 워킹셋을 함께 기록할 것 | **526** |
| 로컬 루프백 접속 | **토큰 필수** | 브리지가 토큰·시크릿 없으면 루프백까지 전부 `bad_private_admission` 거부. 증상은 게임 내 "연결이 종료되었…" 팝업 | **522** |
| 2인 동시 접속 + 서버 GUI 동시 동작 | **통과** | `clients=2`, 하트비트 정상, 양쪽 PatHouse 렌더 | 507 · 491 · 480 |
| 브라우저에서 광장 멀티플레이 | **통과** | 두 브라우저 세션이 같은 광장에서 **서로를 렌더링**한다(`Azrok1` ↔ `Player`, 사용자 육안 양방향 확인). C2S `0x0019`·`0x0066`·`0x0067` 전부 관측, 서버 `SEND/relay` `0x0068`×20 `0x0066`×6 | **529** · 507 · 476 |
| 광장 릴레이 품질 | **결함 — 원인 확정** | 상대 캐릭터의 **각도가 0으로 고정**되고 **순간이동**한다. 클라이언트는 필요한 값을 다 보내는데(`0x0066`=시작·끝·duration, `0x0067`=action·angle) 서버가 끝점 x,y만 쓰고 나머지를 버린다 | **529** |
| 광장 Enter 뒤 남색 화면 | **해결 (VERIFIED)** | 프록시 device 상태 캐시가 `ByteZero` 로 0 인데 `D3DRS_COLORWRITEENABLE` 기본값은 `0x0F`. `StateBlock_Capture` 가 device 의 set 플래그를 무시하고 복사해 **0 이 캡처**되고 `StateBlock_Apply` 가 그 0 을 호스트에 전달 → 컬러 쓰기 전면 차단, navy clear 만 잔상. 호출 지점을 `_ReturnAddress()` 로 특정해 **게임이 아니라 프록시**임을 확인. `SeedDefaultRenderStates()` 로 D3D9 기본값 47개를 심어 수정. 실측: `values {0:199,15:199}` → `{15:2}`, 픽셀 `0,0,128` → 정상 장면, **채팅창 정상 표시** | **535** · 532 · 530 |
| 스마트폰 — 뷰포트 에뮬레이션 | **통과** | 390x844 에서 120.29 fps, 캔버스 347x260.25 (4:3) | 493 |
| 스마트폰 — 실기기 | **미검증** | 실행 기록 없음 | 493 · 521 |
| 사설망 한정 접속(게이트7) | **통과** | 리스너 4개 전부 RFC1918/Tailscale, 무토큰 WSS `1008` 차단, 공인·와일드카드 0건 | 519 · 486 |
| 사설망 자동 프로필 배정 | **통과 (확장)** | `player2~6` 자동 슬롯 5개, 새 package/route 및 안전한 SEH launcher 검증. 실행 중 8765 리스너 반영은 재시작 대기 | 544 · 521 |

---

## §2 게이트별 확정 사실

### §2.1 게이트5 — 멀티 세션 멀티플레이

**VERIFIED**
- 네이티브 클라이언트 2개는 **이미 광장에서 서로를 렌더·릴레이했다** (2026-07-17). 서버의 광장 로직 자체는 증명된 것이다 — `multiplayer/67`.
- 브라우저 탭 2개가 하나의 루프백 코어에 동시 접속하고, GUI(9300)가 `clients=2 / connected_clients=2` 와 entity 96 `player/Azrok1`, entity 97 `peer111/Player` 를 보고하며 둘 다 `0x0016` 하트비트 정상 — 507.
- 두 탭 동시 부팅은 공유 IDBFS 콜드 부트스트랩 충돌 때문에 **직렬화가 필요**하다 — 469.
- 리스너 검사상 코어/GUI 는 루프백 전용, 브라우저 프론트엔드만 사설 대역 — 507.

**BLOCKER (NOT VERIFIED)**
- 같은 실측에서 `plaza_clients=0`, `peer_count=0`, `visible_remote_actor_count=0`. 두 클라이언트가 **한 코어를 공유하며 각자 PatHouse 를 렌더할 뿐**, 광장 진입·`0x0066` 액터 upsert·`0x0068` 이동 릴레이·`0x0067` 퇴장은 하나도 관측되지 않았다 — 507.
- 브라우저 입력은 로컬 UI/카메라만 움직이고 C2S `0x0066`/`0x0067`/`0x0019` 를 전혀 만들지 않는다. 바닥 클릭·포인터락·키보드·드래그 모두 실패했고, 계속되는 C2S 는 하트비트뿐 — 476.
- INFERRED: 남은 병목은 DOM 이벤트 변환이 아니라 **좌측 출구의 원본 이동/히트테스트 조건** — 476.
- 512 에서 진단 헬퍼의 좌표 매핑 버그(캔버스 백킹 `640x480` 을 `1024x768` 로 가정)를 고치고 `inputProbe=1` 관찰자를 넣었으나, **그 뒤 광장 진입을 다시 시도한 기록이 없다.**

### §2.2 게이트6 — 성능(50fps)

**VERIFIED**
- 격리 데스크톱 Edge 탭, BGM 켠 채, 표시 `1024x768`(백킹 `640x480`): 네이티브 `COMMAND.PRESENT` 30초 창 3개 = **71.967 / 71.912 / 67.907 fps** — 520.
- 컨트롤 페이지(305초 정착 + 15초 워밍업): **183.83 ~ 185.76 fps**, 3창 편차 1.05% — 490.
- in-app 브라우저의 실사용 PatHouse 경로는 **40.3548 fps** 로 게이트 실패. 이는 별개의 실행 병목이며 위의 빠른 값으로 대체할 수 없다 — 495.
- 렌더러 기본을 low-observation(`lean`)으로 바꿔 36.00 → 40.00 fps — 509. 그래도 50 미달 — 508.

**측정 계보 주의 (지표 자체가 바뀐 지점)**
- 36 → 184 의 급등은 최적화가 아니라 **워커→페이지 Present 카운터 브리지 수리**(488)의 결과다. 수리 전 HUD 는 0 을 읽는데 외부 창은 이미 183.97 fps 를 읽고 있었다.
- 따라서 현재의 fps 는 **네이티브 Present 호출률**이지 스캔아웃 프레임률이 아니다(60Hz 화면에서 184가 나오는 이유). 체감 부드러움은 별도 축이다.
- `sync_drains` 는 워커가 JS 디스패치 완료를 기다린 횟수이지 GPU/컴포지터 완료가 아니다 — 454.

**기각된 최적화 (전부 negative result, 되돌림)**
| 시도 | 결과 | 문서 |
|---|---|---|
| 오프스크린 FBO 75% 렌더 스케일 | 40fps 근방 유지, 출력 버퍼 축소 시 검은 화면 | 500 |
| `upBatch=1` | 39.8 fps | 502 · 501(보관) |
| `hotwisstored` 패키지 | HUD 35.8 fps | 504 |
| DrawUP 인접 병합 | 실제 인접쌍 5개뿐 → 최대 3.1%, 불충분 | 506 |
| `D3DTOP_DISABLE` 이후 셰이더 stage-stop | 40.00 → 35.99 역행 | 510 |
| 동일값 상태 스킵 캐시 | 즉시 동일값 커맨드 0개로 전제 자체가 기각 | 514 · 518 |

### §2.3 게이트6 — 사운드

**VERIFIED (고장 지점)**
- Wine winegstreamer 의 32비트 Unix-call 콜백 지점에서 `0xc0000005` 액세스 위반. `0x8007000e` 는 그 래퍼 결과일 뿐 — 463.
- 현재 루트에서 PetHouse.mp3 는 열리지만 Quartz/GStreamer 스플리터 생성이 모든 클래스에서 실패하고 BGM PCM 이 0 — 461 · 462.

**VERIFIED (현재 동작 방식)**
- 원본 MP3 15개를 사설 서버가 제공하고 **브라우저가 대신 재생**한다 — 465.
- 재생 시점은 **게스트 FS 관찰자가 원본 실행파일의 MP3 open 을 본 뒤**로 게이트됐다. 첫 제스처는 무음 컨텍스트만 재개한다. 실측: `intro.mp3` open `82,486.960ms` → 미디어 싱크 시작 `82,506.820ms` (19.86ms 차) — 516.
- Windows 출력 엔드포인트 도달은 WASAPI 루프백 상관 0.921266 / 0.978613 / 0.9689998 로 증명 — 483 · 494 · 505.
- 511 의 "음량 회귀"는 실제로는 사용자가 낮춰 둔 브라우저 볼륨이었고, 임시 8배 게인은 제거·유니티 게인 복구됨.

**경계**: 이것은 원본 실행파일의 소리가 아니라 **원본 자산을 브라우저가 재생**하는 것이다. 바이너리 패치는 없지만 게임 내부 오디오 복원과 동일하지 않다.

**2026-07-29 A/B (522)** — 브라우저 대행을 끄고 새 프로필로 3개 leg 를 재서 두 가설을 기각했다.
게스트가 오디오 노드에 써 넣는 PCM 을 직접 탭한 결과 세 조합 모두 `nz=0 / max=0` 이었고,
`SDL2.audioContext` 는 셋 다 `running` 이었다 — 컨텍스트가 죽은 게 아니라 보낼 음악이 없다.

| 되돌린 변수 | 결과 |
|---|---|
| 런타임을 07-22 오디오 검증본(`upstreamjit14audiobest`)으로 | 무음 → **런타임 교체 원인설 기각** |
| root 를 dsound80ms 이전(`…-bgmloop3`)으로 | 무음 → **258 root 원인설 기각** |
| 현재 프로덕션 조합 (기준선) | 무음 |

다음 단계는 빌드 계보 추적이 아니라 `fs/…-dsound80ms1-winegstrace1~3.zip` 진단 root 로
`0xc0000005` 발생 순간의 Wine 로그를 직접 받는 것이다.

### §2.4 게이트6 — 모바일

**VERIFIED**
- Chrome 실제 뷰포트 `390x844`(`innerWidth/innerHeight` 확인), 실제 `run_azrok_seh.bat` 실행, 30초 창 3600 Presents / 29,927.385ms = **120.2912 fps**, HUD `fast` — 493.
- BoxedWine 이 캔버스 인라인 스타일을 `1024x768` 로 덮어쓰는 문제는 `?mobileCapture=1` 마킹 + important 규칙으로 억제, 두 캔버스 모두 `347x260.25`(정확히 4:3) 표시 — 493.
- 터치 primary → 경계 검사된 SDL 호환 마우스 이벤트 매핑 — 485.

**기각**: in-app 브라우저는 뷰포트 지정을 무시하고 데스크톱 기하를 유지하므로 그 191 fps 는 모바일 증거가 아니다 — 492 · 473.

**NOT VERIFIED**: 실제 Android/iOS 기기, 지속 발열 주행, 터치 게임플레이, 스피커, 실기 50fps 표본.

### §2.5 게이트7 — 사설 대역 한정 확장

**VERIFIED**
- 리스너는 `<lan-ip>:8765/9201`, `<tailscale-ip>:8765/9201` 넷뿐. 코어 `127.0.0.1:9200` 과 GUI `127.0.0.1:9300` 은 루프백 전용, 공인·와일드카드 바인드 0건 — 519 · 486.
- 브라우저 식별자에 묶인 서명 12시간 티켓을 `/api/private-session` 에서 발급하고 WSS 가 검증. 토큰 없는 WSS 는 정책 코드 `1008` 로 종료 — 519 · 486.
- 계정 연속성은 **브라우저 기기 바인딩 + 1회용 복구 코드**이며 비밀번호 기능은 제거됐다. 티켓은 account claim까지 서명하고 WSS가 첫 로그인 계정 일치를 검사한다 — 565.
- 새 기기에는 `player2` → `player3` → `player4` → `player5` → `player6` 순으로 자동 배정하며 보존 계정 `player`·`peer111` 은 절대 자동 배정하지 않는다. 패키지/라우트/레지스트리 단위 검증은 통과했지만, 실행 중 8765 리스너의 실제 `player5`/`player6` 배정은 리스너 재시작 뒤 재검증이 필요하다 — 544 · 521.
- LAN HTTPS/WSS 실행 파일이 기존 방화벽 규칙과 불일치했고, `<lan-ip>/24` 한정 규칙 설치기를 별도로 두었다(권한 상승 필요) — 513.

**NOT VERIFIED**: 실제 휴대폰의 bare URL 부팅, 복구 코드로 다른 기기 이어하기, 그 위의 광장 멀티플레이 전 과정.

### §2.6 문서 트리

2026-07-29 에 루트에 평평하게 쌓여 있던 425건을 주제 폴더로 옮겼다. 파일별 목록은 [`REGISTRY.md`](REGISTRY.md).

| 폴더 | 건수 | 내용 |
|---|---:|---|
| `gate7/` | 8 | 사설 대역 한정 확장 서버·인증·프로필 |
| `gate6/perf/` | 216 | 50fps 성능 실험 — **대부분 negative result** |
| `gate6/audio/` | 26 | BGM·WASAPI·Quartz/GStreamer |
| `gate6/mobile/` | 5 | 모바일 뷰포트·터치·캡처 |
| `gate5/` | 11 | 멀티 세션 멀티플레이 |
| `gate2/` | 91 | 네이티브 기동·WASM/JIT 계약 (GATE2B·GATE2C) |
| `gate1/` | 4 | 초기 기동 게이트 |
| `webport/` | 17 | D3D9→WebGL2 이식 설계·단계(PHASE0~9) |
| `server/` | 18 | 서버 구현·GUI·프로토콜 레지스트리·저널 |
| `protocol/` | 9 | opcode·프로토콜 계약 |
| `world/` | 21 | 광장·씬·진화·로컬룸·외출 |
| `multiplayer/` | 11 | 로스터·이름·이탈·디스패치 owner — **네이티브 2인 광장 성공은 `multiplayer/67`** |
| `content/` | 46 | 스탯·퀘스트·인벤토리·액세서리·OX·요리 |
| `tooling/` | 11 | frida·x32dbg·런처·캡처 매니페스트 |
| `archive/` | 23 | 대체된 문서 보존 (삭제 금지) |

같은 실험을 다시 하기 전에 REGISTRY 에서 제목을 먼저 검색할 것. `gate6/perf/` 216건의 대부분은 "해봤는데 안 됐다"의 기록이다.

---

## §3 지금 열려 있는 질문

1. **브라우저에서 광장에 못 들어간다.** 512 의 `inputProbe=1` 로 신뢰된 물리 입력 좌표를 찍고, 그 순간의 패킷 캡처에 `C2S 0x0019` 가 있는지/없는지부터 확정해야 한다. 좌표 변환 탓인지 원본 히트테스트 조건 탓인지 아직 갈리지 않았다 — 476 · 512.
2. **in-app 브라우저 40fps 대 격리 탭 70fps 의 차이가 무엇인지** 아직 규명되지 않았다 — 495.
3. **실기기 스마트폰 표본이 0건**이다 — 493 · 521.
4. **50fps 의 정의**가 확정되지 않았다: 지속 정상상태인지, 체감되는 초기 구간인지. 지표가 Present 호출률이라는 점과 함께 정해야 한다 — 488 · 490.
5. 게임 내부(Wine) MP3 디코딩 복구를 계속 시도할지, 브라우저 대행 재생을 최종 형태로 둘지 — 461 · 463 · 516.

---

## §4 문서 하자 대장

- **이 INDEX 는 2026-07-29 에 재구축됐다.** 그 전 INDEX 에는 #459~#521 의 62줄만 있었고 그 이전 456건은 등재되어 있지 않았다. 원문은 [`archive/INDEX_snapshot_20260729.md`](archive/INDEX_snapshot_20260729.md) 에 보존.
- **같은 날 루트 425건을 폴더로 이동**했다(§2.6). 문서 간 마크다운 링크 529개는 전부 새 경로로 재작성했고 깨진 링크 0개를 확인했다. 다만 본문의 백틱 참조(`` `NNN_FOO.md` ``)는 링크가 아니라 텍스트이므로 폴더 접두어가 없다 — 위치는 REGISTRY 에서 찾는다.
- 루트에 남은 `_` 접두 문서(`_img2011_*`, `_wayback_*`, `_web_azrok_lore` 등 10건)는 번호 체계 밖의 자료 노트이며 짝이 되는 데이터 폴더와 함께 두었다. REGISTRY 대상이 아니다.
- **번호 충돌 6건** (물리 리네임은 링크 영향 때문에 보류, 여기서만 구분):
  - `32` — `world/32_all_room_clean_observer_plan` / `world/32_popup_ring_gym_buttons_41_42_43`
  - `45` — `archive/45_dispatch_pointer_semantics_recheck` / `multiplayer/45_two_client_plaza_targeted_roster`
  - `57` — `content/57_content_state_contract_audit` / `content/57_evolution1_e1201_dynamic_ab`
  - `58` — `content/58_quest_money_data_source` / `content/58_shipped_content_profile_dynamic`
  - `70` — `content/70_playable_v2_reconnect_evolution_restore` / `world/70_scene_map_and_plaza_hansol_correction`
  - `458` — 내용 있는 `458_INT9A_B1_WEBGL_ADMISSION_FAIL_20260726.md` 만 유효. **0바이트 중복본은 `archive/458_EMPTY_DUPLICATE_...` 로 이동**했다.
- `00_current_status.md` 는 **2026-07-18 스냅샷**이다. 네이티브 클라이언트 시절 내용이므로 현재 상태로 읽지 말 것 — 현재 상태는 이 파일 §1.
- 저장소에 **git 이력이 없다**(`.git` 에 HEAD·objects 없음). 문서든 코드든 롤백 지점이 존재하지 않으므로 삭제 대신 `archive/` 이동 원칙이 특히 중요하다.

---

## §5 상세 로그 #459–#521

재구축 전 INDEX 의 62줄 원문은 [`archive/INDEX_snapshot_20260729.md`](archive/INDEX_snapshot_20260729.md) 에 바이트 그대로 보존돼 있다.
이 파일에 중복 게재하지 않는다 — 지도는 짧아야 지도다.
---

## §6 상세 로그 #522–

| # | 요지 | 파일 |
|---:|---|---|
| 586 | **캐릭터 전환 로그아웃·신규 이유식·콜드 부팅 캐시** — 원본 옵션 로그아웃의 `0007→0002→0007→0001`과 clean exit를 실측한 뒤, 웹 실행기를 새 account-bound ticket의 `characterSelect=1` 재부팅으로 연결하고 서버가 해당 계정의 다음 auto-select만 1회 억제하도록 구현. 신규 canonical에 `food1001` 1개를 서버 지급하고 실제 `S2C 0007[0x0EB]=1`을 검증. 앱 157 MB + root 168 MB + JIT를 Cache Storage에 보존하고 중복 `end_headers` 덮어쓰기를 수정해 실제 ZIP 응답 `immutable` 적용. 신규 PatHouse 3D/HUD/이유식 퀘스트 UI 라이브 VERIFIED, localhost 반복 부팅 첫 D3D 약 50~55초; 최초 origin 약 130초와 게임 내 로그아웃 후 새 페이지의 최종 4슬롯 GUI는 제한사항 참조. 전체 278 tests 통과 | `gate7/586_CHARACTER_SWITCH_STARTER_FOOD_AND_COLD_CACHE_20260827.md` |
| 567 | **Dynamic launcher boot-stall fix** — `dynamicaccounts1`의 Wine 11 `findstr /X`·문자 클래스 미구현 때문에 모든 정상 계정이 `Azrok.exe` 전에 `exit /b 87`하던 무출력 부팅 고착을 확정. 중복 검증을 페이지의 동일 정규식으로 이동하고 표준 CRLF `dynamicaccounts2`, 사설 landing `autorun=1`을 배포. 새 계정 WSS/TCP 로그인·heartbeat·서버 응답(`rx=3`, `tx=4`)과 기존 사용자 계정의 자동 부팅·원본 첫 화면·76.1 FPS를 라이브 VERIFIED, 254/254 통과 | `gate7/567_DYNAMIC_LAUNCHER_BOOT_STALL_FIX_20260827.md` |
| 566 | **아카이브 계층 설계 — 실측 현황과 정리 계획** — 트리 전체 58 GB 실측. 대체 불가 원본(`Data/` 0.49 GB + 원본 실행파일 + 별마루 0.09 GB + 문서 0.30 GB)은 1 GB 미만이고, `apps/*.zip` 116개(각각 `Data/` 전체 사본, zip 엔트리 직접 확인)와 `fs/*.zip` 70개(TinyCore 루트 변종)가 25.3 GB. `Azrok.exe`/`Azrok_original.exe`/`real_orig/Azrok.exe` 3벌은 SHA-256 동일. **`.git/` 에 파일이 `info/exclude` 하나뿐 — 커밋 이력 0건.** 4계층(원본/발굴본/연구·코드/재생성가능) 구조와 실행 순서 제안. 실측·해시·zip 내용 VERIFIED; `dmdes/` 12.2 GB 의 출처·복구 경위는 NOT VERIFIED | `tooling/566_ARCHIVE_LAYOUT_PLAN_20260826.md` |
| 565 | **PARTIALLY SUPERSEDED by 567** — 동적 계정/복구 코드/account-bound v2 ticket 설계와 GUI·WSS 검증은 유효. 최초 `dynamicaccounts1` launcher의 실제 부팅 수락은 거짓이었고 567의 `dynamicaccounts2` 및 live 원본 handshake가 대체 | `gate7/565_DYNAMIC_ACCOUNT_RECOVERY_AND_BOUND_TICKET_20260826.md` |
| 563 | **16:35 IME production-state rollback** — 사용자 요청에 따라 첫 post-cutoff 산출물 korean7(16:47) 이전 상태로 복구. 페이지에서 이후 `compositionupdate`/Backspace replacement/XIM callback 코드를 전부 제거하고 korean6+xim25+utf8ime2 및 compositionend-only send를 복원. focused 41/full 248 tests, live korean6 JIT 94 groups/30550 blocks, 새 오류 0건 VERIFIED | `gate5/563_IME_PRODUCTION_STATE_ROLLBACK_1635_20260808.md` |
| 564 | **Character logout / roster-return 0x0002 contract + minimal server implementation** — 원본 `C2S 0007 save → 0002[0B]`, ACK `S2C 0002[0B]`, completion `C2S 0007 → 0001[0B]` 계약을 서버에 구현. account/4-slot roster/canonical은 보존하고 selected lease·actor·room만 해제, explicit logout 후 auto-select 억제, registry exact-0B 등록. focused 150 tests VERIFIED; 실제 4슬롯 UI 복귀→다른 캐릭터→PatHouse/Plaza는 NOT VERIFIED | `server/564_CHARACTER_LOGOUT_0002_CONTRACT_20260826.md` |
| 562 | **PARTIALLY SUPERSEDED by 563** — callback 기본 비활성화 결론은 유효하나, 563에서 진단 분기까지 페이지에서 제거하여 16:35 운영 코드로 더 완전히 복구 | `gate5/562_XIM_ACTIVE_PREEDIT_CALLBACK_PRODUCTION_ROLLBACK_20260808.md` |
| 561 | **SUPERSEDED by 562** — depth guard 이후에도 producer 순환으로 FIFO depth 29와 같은 worker stack overflow 재현. 실패 기록은 archive에 보존 | `archive/561_WINE_XIM_PREEDIT_CALLBACK_REENTRY_GUARD_20260808.md` |
| 560 | **SUPERSEDED by 561** — XIM callback bridge에 재진입 가드가 없어 첫 물리 조합 update에서 WASM stack overflow. 실패 기록은 archive에 보존 | `archive/560_WINE_XIM_PREEDIT_CALLBACK_BRIDGE_20260808.md` |
| 559 | **SUPERSEDED by 560** — `compositionupdate`를 확정 문자로 넣고 synthetic Backspace로 교체하는 방식은 사용자 물리 입력 `안녕→ㅇ안` 회귀로 기각. 실패 기록은 archive에 보존 | `archive/559_GAME_WIDE_HANGUL_PREEDIT_LIVE_REPLACEMENT_20260808.md` |
| 558 | **Game-wide Korean input locale environment fix** — BoxedWine argv에 셸용 따옴표를 문자 그대로 넣어 실제 `LANG`/`LC_ALL`이 사라지고 웹 Wine이 ACP 1252로 시작하던 근본 원인을 수정. raw `ko_KR.EUC-KR` 환경에서 웹 `GetACP()=949`, 원본 캐릭터 이름 Edit의 `한글별` 표시와 원본 확인 버튼 다음 화면 진입을 VERIFIED. 일반 URL 기본값을 compiled-locale xim25 + utf8ime2로 승격했으며 `Azrok.exe` 해시는 원본과 동일. 243 tests pass; 모든 ANSI 입력칸 전수 수락은 NOT VERIFIED. #557의 IME 원인 부분을 PARTIALLY SUPERSEDE. | `gate5/558_GAME_WIDE_KOREAN_INPUT_LOCALE_ENV_FIX_20260808.md` |
| 557 | **PARTIALLY SUPERSEDED by 558 (IME root cause); Private browser Hangul chat + OX live acceptance remains valid** - Plaza browser input now owns IME composition and relays an authenticated bound-account message through the preserved S2C 0x006A path. `한글 입력 성공` was VERIFIED in the original client's speech bubble and chat log. The same persisted-character session completed supported OX `006B -> 00C8`, question, loser exit, and rendered Plaza return with no exception-ignore patch and no crash. Full/range 1 MiB asset streaming also removed the reproduced 157 MB ZIP `MemoryError`; 44 focused and 240 full tests pass. #556 is SUPERSEDED. | `gate5/557_PRIVATE_BROWSER_CHAT_AND_OX_LIVE_ACCEPTANCE_20260808.md` |
| 556 | **SUPERSEDED by 557 - Wine XIM Unicode chat input** — locale-only #555는 충분하지 않았음. committed XIM UTF-8을 UTF-16으로 변환한 뒤 Wine `KEYEVENTF_UNICODE`로 재주입하는 `winex11.so`와 immutable xim2 root를 배포. Plaza chat mode에서 물리 US-layout 중복 문자도 차단. 브라우저 부팅·Plaza 렌더 VERIFIED, 실제 물리 한글 glyph와 C2S 0x006A는 수락 대기 | `archive/556_WINE_XIM_UNICODE_CHAT_INPUT_20260808.md` |
| 555 | **PARTIALLY SUPERSEDED by 556** — 부팅 진행 UI 결론은 유효하나 `C.UTF-8`만으로 Plaza Edit가 완성된다는 결론은 사용자 실측으로 기각 | `archive/555_BOOT_PROGRESS_AND_KOREAN_IME_PRODUCTION_ROUTE_20260808.md` |
| 554 | **IME single guest-key debug2** — 브라우저 자동화 Enter 중복을 배제하도록 debug-only SDL press/release 1쌍 export를 추가. immutable debug2 JS/WASM, currentabi1 map `12968408/262144`, LAN/Tailscale hash, 12 tests 검증. Plaza Edit→한글→006A 동적 수락 대기 | `gate5/554_BOXEDWINE_IME_SINGLE_GUEST_KEY_DEBUG2_20260808.md` |
| 553 | **Wine XIM UTF-8 Unix-locale A/B** — #552 live에서 XIC/Xmb/XLookupChars status2·UTF-8 6 bytes까지 완전 통과. Wine은 XLocaleOfIM이 아니라 Unix `unix_cp`로 변환하는데 launcher의 미설치 `ko_KR.EUC-KR`가 C/CP20127로 폴백할 가능성을 소스/root로 좁힘. player2~6 BAT만 `C.UTF-8`로 바꾼 immutable app과 WINEUNIXCP probe, LAN/Tailscale hash, 19 tests 검증; Plaza Edit A/B 대기 | `gate5/553_WINE_XIM_UTF8_UNIX_LOCALE_APP_AB_20260808.md` |
| 552 | **BoxedWine IME XIM runtime probe** — immutable 38-word snapshot live 결과 XIM/XIC 생성, Xmb synthetic 2, XLookupChars 2, UTF-8 6 bytes/status2, FIFO served2/depth0를 직접 확인. fake-XIM 손실 가설을 기각하고 경계를 Wine `xim_set_result_string` 이후로 이동; locale A/B는 #553 | `gate5/552_BOXEDWINE_IME_XIM_RUNTIME_PROBE_20260807.md` |
| 551 | **korean5 explicit currentabi1 relocation reserve** — 실제 archive manifest `12968408/262144`를 재확정하고 #550 오류를 정정. reloc backing을 `CAPACITY+64 U32`, usable pointer를 `storage+64`로 정의해 index/worker semantics를 유지하면서 export를 정확히 복구. immutable korean5/currentabi1 배포 및 LAN/Tailscale runtime/archive 해시 일치 확인; 실게임은 대기 | `gate5/551_KOREAN5_CURRENTABI1_EXPLICIT_RELOC_RESERVE_20260807.md` |
| 550 | **SUPERSEDED by 551** — currentabi1 manifest를 `12968152`로 잘못 읽은 문서. 실제 값은 `12968408/262144`; 오류 원문은 archive에 보존 | `archive/550_KOREAN4_CURRENTABI1_MAP_IDENTITY_20260807.md` |
| 549 | **PARTIALLY SUPERSEDED by 550** — fake-XIM/XIC 계약은 유효. korean3은 라이브 map ABI 모순으로 기본 배포에서 제외하고 cache-off rollback으로 보존 | `gate5/549_BOXEDWINE_FAKE_XIM_KOREAN3_STATIC_CONTRACT_20260807.md` |
| 548 | **웹 OX SEH/런처 감사** — 과거 “계속 실행”은 WineGStreamer BGM null unix-dispatch였고, OX는 별도의 `acknex.dll` invalid-BMAP fault임을 재확인. player2~6에 native D3D9와 `+seh`가 이미 있으나 복구 효과는 없음. 런처 정적 회귀 테스트 추가; 실제 OX 완료는 미검증 | `gate5/548_WEB_OX_SEH_LAUNCHER_AUDIT_20260807.md` |
| 547 | **원본 신규 캐릭터 부트스트랩 복원** — level-25/kind-3 데모 시드를 제거하고 0007 date=0으로 클라이언트 kind-5/212 튜토리얼을 자연 시드. 실측 성장 패킷 순서를 보류/상관 저장하며 다음 aux를 서버가 발명하지 않음. PatHouse 3D 및 전 진행 실플레이는 대기 | `content/547_ORIGINAL_FRESH_BOOTSTRAP_AND_GROWTH_ORDER_20260807.md` |
| 546 | **게스트 단독 BGM + 44.1 kHz + 런타임 식별자 + 우클릭** — 브라우저 BGM은 진단 opt-in, BGM UI 제거, shell 44100 전달, 전체 게임 영역 contextmenu 차단, immutable korean2 배포. XIM/Plaza 한글 수락은 아직 미확정 | `gate5/546_GUEST_BGM_44100_RUNTIME_IDENTITY_AND_CONTEXT_MENU_20260807.md` |
| 541 | **BoxedWine 한글 IME 정적 경로** — SDL text 폐기 확인, composition 완료 text를 synthetic X11 `XLookupString`으로 보내는 최소 훅 적용. Wine ANSI 변환은 브라우저 실측 필요 | `gate5/541_BOXEDWINE_KOREAN_IME_STATIC_PATH_AND_TEXT_HOOK_20260730.md` |
| 529 | **게이트 5 통과** — 브라우저 2세션이 광장에서 상호 렌더링(`plaza_clients=2`, 양쪽 `visible_remote_actor_count=1`) | `gate5/529_GATE5_BROWSER_PLAZA_ENTRY_ACHIEVED_20260730.md` |
| 530 | 파란 화면 GL 파이프라인 실측 — draw/blit 정상 동작 확인, 가설 3개 반증. `canvas 640x480` vs `drawingBuffer 1024x768` 만 남음 | `gate5/530_BLUE_SCREEN_GL_PIPELINE_MEASUREMENT_20260730.md` |
| 531 | OX 팅김 1차 조사 — **§1·§2·§3·§5 는 534 가 뒤집음**. §4·§6 만 유효 | `gate5/531_OX_CRASH_UNADMITTED_C8_REPLY_20260730.md` |
| 532 | 파란 화면 D3D9Web 정적 분석 (Codex) | `gate5/532_D3D9WEB_PLAZA_ENTER_BLUE_SCREEN_STATIC_ANALYSIS_20260730.md` |
| 533 | 광장 액터 릴레이 heading 저장 및 duration 기반 0x0068 보간 수정: Ghidra 디컴파일로 b1 선택, heading/프레임 흐름 인메모리 검증 | `gate5/533_GATE5_PLAZA_RELAY_HEADING_AND_INTERPOLATION_20260730.md` |
| 535 | **파란 화면 근본 원인 확정** — `gl.colorMask(false,false,false,false)` 가 `renderStates[168]==0` 에서 나와 고착. 2초 11,796 draw 전부 차단, navy clear 만 잔상으로 남음. all-false 호출만 막으면 즉시 복구(실측). CDP 키 1회로 결정적 재현. #530 의 크기 단서는 기각 | `gate5/535_BLUE_SCREEN_COLORWRITE_MASK_ROOT_CAUSE_20260730.md` |
| 534 | **OX 크래시 실체** — 서버 프로토콜은 정상(입장→ready→출제 확인), 클라이언트가 `00CE` 뒤 5초 내 사망. 1차 폴트 `eip=7F37DFB8`/`[eax+0x10]`, `eip=0` 은 엔진 크래시 리포터의 2차 산물. **#122 완주는 네이티브였고 OX 는 웹에서 완주한 적 없음** | `gate5/534_NULL_DISPATCH_ON_SCENE_TRANSITION_20260730.md` |
| 536 | **COLORWRITE 프록시 캐시 정적 감사** — `value` 변환 경로와 Reset/Create dedup 영구 삼킴은 확인되지 않음. 단, COMMAND.INIT에서 host `renderStates`를 초기화하지 않아 stale Map 분기와 StateBlock Capture 계측 경계가 확인됨. | `gate5/536_D3D9WEB_COLORWRITE_PROXY_CACHE_AUDIT_20260730.md` |
| 537 | S2C 0x0068 걷기 레코드 필드 [0]~[4] 와 "heading 필드 없음" — **[5] 를 duration 으로 읽은 것은 538 이 뒤집음**(텔포 회귀 유발) | `gate5/537_S2C_0068_WALKING_RECORD_LAYOUT_20260730.md` |
| 545 | **SUPERSEDED by 549** — Clipboard/강제 Ctrl+V는 `vvvv` 실측으로 기본 경로에서 제외하고 rollback fallback으로만 보존. 당시 GUI/계정 API 기록은 유효 | `archive/545_KOREAN_IME_CLIPBOARD_CTRL_AND_LIVE_GUI_RESTART_20260807.md` |
| 542 | **SUPERSEDED by 545** — 브라우저 조합은 해결했으나 XLookupString/FIFO가 Wine Edit에서 유실된 구 경로. 기록 보존을 위해 archive로 이동 | `archive/542_KOREAN_IME_BROWSER_SIDE_SOLVED_GUEST_LOSSY_20260730.md` |
| 541 | BoxedWine 한글 입력 경로 정적 확정 + X11 텍스트 훅 적용(Codex). 기존 빌드엔 조합 텍스트가 Wine까지 갈 경로가 없음을 소스로 확정, `compositionend`→`SDL_TEXTINPUT`→X11 UTF-8 FIFO→`XLookupString` 훅 신설. Wine이 바이너리라 마지막 구간은 정적 증명 불가 | `gate5/541_BOXEDWINE_KOREAN_IME_STATIC_PATH_AND_TEXT_HOOK_20260730.md` |
| 540 | **S2C 0x0066 self-profile 불가 확정(Codex)** — `FUN_0050D790`이 self id를 생성·복사·action 분기보다 **앞에서 조기 반환**한다. 따라서 액터 id 1 로 0x0066 을 보내는 건 해결책이 아니며 539의 그 추론은 뒤집힘. fixed self 는 `FUN_006130B0`→`FUN_00524280` 로 **로컬 프로필**에서 이름을 받는다(공급원 미확정). 0x006C 는 state 가 C2S 0x0069 의자번호 0..5 에서 오고 `DAT_006D9D48` 테이블 실측으로 state 0..5 × toggle 0..1 확정, 그러나 **toggle 정책 근거 없어 중계 보류**. 커뮤니티 상태 0x30 중 이동 거부는 계약임 | `gate5/540_0066_SELF_PROFILE_AND_006C_COMMUNITY_CONTRACT_20260730.md` |
| 539 | Historical Korean IME bridge and target-actor interpretation. Information-button conclusion **SUPERSEDED by 653**: BtnInfo sends C2S006C and requires S2C0070. Nickname/self-record hypothesis separately superseded by540. Original observations retained. | `archive/539_KOREAN_IME_BRIDGE_AND_006C_TARGET_20260730.md` |
| 540 | **0x0066 self-name 가설 기각** — 0x0066은 신규 non-self remote만 생성하며 fixed self id는 필드 복사 전 제외된다. 따라서 self `Guest`는 이 opcode로 고칠 수 없어 전송 구현을 보류하고, self 초기화의 로컬 프로필 경로를 다음 조사 대상으로 분리했다. `0x006C`의 state는 C2S 0x0069 의자 번호(0..5)에서 유래하지만 toggle 서버 정책이 미확정이라 S2C 중계는 계속 보류한다. 커뮤니티 state 0x30에서는 0x0068 이동을 클라이언트가 의도적으로 거부한다. | `gate5/540_0066_SELF_PROFILE_AND_006C_COMMUNITY_CONTRACT_20260730.md` |
| 538 | **걷기 모션·각도 근본 원인 확정** — S2C `record[5]` 는 duration 이 아니라 **서버 동기 시계 기준 절대 도착 시각**. `0x0061A710` 이 `now < record[5]` 로 걷기 분기 전체(=`vec_to_angle` 각도 포함)를 막고 있었다. C2S 0x0066 여섯째 dword 는 상대 duration(실측 217·795) 이므로 **변환은 서버 몫**: `record[5] = now32 + duration`. 라이브 주입 A/B 로 확정(H1 걷기+방향전환, H2 스냅). 0x0004 5샘플 캘리브레이션이 클라 시계를 우리 유닉스 ms 로 맞춤 | `gate5/538_S2C_0068_ARRIVAL_DEADLINE_CLOCK_20260730.md` |
| 537 | **538 이 뒤집음** — S2C 0x0068 `record[5]` 를 duration 으로 읽어 텔레포트 회귀를 일으킴. 필드 [0]~[4] 와 "heading 필드 없음" 결론만 유효 | `gate5/537_S2C_0068_WALKING_RECORD_LAYOUT_20260730.md` |
| 538 | **걷기·각도 근본 원인 확정** — S2C 0x0068 `record[5]` 는 **서버 동기 시계 기준 절대 도착 시각**, C2S 0x0066 6번째 dword 는 **상대 duration**(실측 217/795). 단위가 다르므로 서버가 `now32+duration` 으로 변환해야 한다. 걷기 모션과 각도(`vec_to_angle`)는 `now < record[5]` 분기 안에만 있어 **같은 원인**. 라이브 클라이언트 A/B 주입으로 확정 | `gate5/538_S2C_0068_ARRIVAL_DEADLINE_CLOCK_20260730.md` |
