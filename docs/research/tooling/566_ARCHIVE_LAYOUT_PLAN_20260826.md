# 566. 아카이브 계층 설계 — 실측 현황과 정리 계획 (2026-08-26)

## Scope

프로젝트 트리 전체(58 GB)를 콜드 스토리지 보존용으로 재편하기 위한 계획서.
**이 문서 단계에서는 파일을 옮기거나 지우지 않는다.** 실측·판정·계획까지만이며,
실행은 별도 승인 후 §5 순서대로 진행한다.

목적은 "전량 보존 + 중복 제거"다. 공개 배포용 슬림화가 아니므로 원본 클라이언트·
별마루·복구본은 전부 남긴다.

---

## §1 VERIFIED — 실측 현황 (2026-08-26)

측정: `Get-ChildItem -Recurse -File -Force | Measure-Object Length -Sum`. 재현 명령은 §7.

### 디렉터리별 (상위)

| 경로 | 크기 | 파일 수 |
|---|---:|---:|
| `tools/` | 32.43 GB | 71,587 |
| `dmdes/` | 12.20 GB | 5,359 |
| `artifacts/` | 11.77 GB | 63,813 |
| `Data/` | 0.49 GB | 4,171 |
| `docs/` | 0.30 GB | 1,284 |
| `_ghidra_backup_20260717/` | 0.27 GB | 47 |
| `azrok..rep/` | 0.27 GB | 52 |
| `ghidra_temp/` | 0.18 GB | 173 |
| `bwujit_threaded_abi/` | 0.14 GB | 3,644 |
| `.runtime/` | 0.12 GB | 1,228 |
| `starmaru/` | 0.09 GB | 270 |
| `.tmp_depthlocal1_verify_20260723_1050/` | 0.06 GB | 135 |
| `.tmp_combinedabi1_verify_20260723_1018/` | 0.06 GB | 135 |
| 루트 낱개 파일 | 0.10 GB | 137 |

### `tools/` 내역

| 경로 | 크기 | 파일 수 |
|---|---:|---:|
| `tools/boxedwine_local/` | 29.10 GB | 34,548 |
| `tools/emsdk/` | 1.95 GB | 20,519 |
| `tools/d3d9_web_backend/` | 1.15 GB | 8,446 |
| `tools/ghidra-mcp-beth/` | 0.10 GB | 2,860 |
| `tools/GhydraMCP/` | 0.09 GB | 1,352 |

### `tools/boxedwine_local/` 내역

| 경로 | 크기 | 파일 수 |
|---|---:|---:|
| `apps/` | 14.58 GB | 123 |
| `fs/` | 10.73 GB | 73 |
| `bwujit_threaded_abi/` | 1.40 GB | 28,939 |
| `profiles/` | 1.17 GB | 259 |
| `assets_d3d9web/` | 0.59 GB | 414 |
| `_guesttexrecycle_pack_20260722/` | 0.50 GB | 4,187 |

### `artifacts/` 내역

| 경로 | 크기 | 파일 수 |
|---|---:|---:|
| `boxedwine/` | 6.34 GB | 39,814 |
| `dynamic-analysis/` | 1.63 GB | 1,373 |
| `runtime/` | 1.29 GB | 891 |
| `ui-probes/` | 0.99 GB | 869 |
| `wine11_source/` | 0.33 GB | 11,076 |
| `audio/` | 0.22 GB | 212 |
| `wine11_build_dbg3/` | 0.17 GB | 4,076 |

### 최대 단일 파일 (상위 6)

| 크기 | 경로 |
|---:|---|
| 853.6 MB | `artifacts/dynamic-analysis/procdump_20260717_0530/Azrok.dmp` |
| 663.7 MB | `artifacts/boxedwine/20260719_gate2b_native/azrok_wine11_vulkan_ox_reset_trace_retry_stdout.log` |
| 569.0 MB | `artifacts/boxedwine/20260719_gate2b_native/dumps/gstreamer_mpg123_20260721/BoxedWine.exe_260721_221816.dmp` |
| 446.3 MB | `dmdes/Documents/chm/f60633543.chm` |
| 416.2 MB | `dmdes/cab/f57063090.cab` |
| 310.4 MB | `dmdes/cab/f7350593.cab` |

**총계 약 58 GB.**

---

## §2 VERIFIED — 중복·재생성 가능 판정

### 2.1 원본 실행파일 3벌은 동일 파일

SHA-256 실측:

| 파일 | 크기 | mtime | SHA-256 (앞 24) |
|---|---:|---|---|
| `Azrok.exe` | 2,199,552 | 2008-01-31 | `39680DA744DF27CF13EAE03F` |
| `Azrok_original.exe` | 2,199,552 | 2008-01-31 | `39680DA744DF27CF13EAE03F` |
| `real_orig/Azrok.exe` | 2,199,552 | 2008-01-31 | `39680DA744DF27CF13EAE03F` |
| `Azrok_patched.exe` | 2,199,552 | 2026-03-29 | `83142D86A7F8F5319F3120CF` |
| `Azrok.exe.patched_backup` | 2,199,552 | 2026-03-29 | `B7637944F112FBF2B7112F5D` |
| `acknex.dll` | 2,682,880 | 2006-12-12 | `876F6870F6858C3829C08304` |

- 앞 3개는 **바이트 동일**. 원본 1벌 + 사본 2벌이다.
- `Azrok_patched.exe` 와 `Azrok.exe.patched_backup` 은 **서로도 다르다.** 서로 다른
  패치 세대이며, 둘 다 원본이 아니라 파생물이다. Tier 0 에 넣지 않는다.
- `[[project_ghidra_baseline]]` 의 Ghidra 베이스라인이 `Azrok_original.exe` 임을 고려해
  Tier 0 의 정본 파일명은 **`Azrok_original.exe`** 로 삼는다.

### 2.2 `apps/*.zip` 116개는 게임 데이터 전체 사본

`tools/boxedwine_local/apps/Azrok_D3D9Web_pathouse_diag5.zip` 을 직접 열어 확인:

- 엔트리 **4,187개**, 전부 `Data\...` 접두. (`Data\button\`, `Data\Space\Plaza\` 등)
- 디스크의 `Data/` 는 4,171 파일 / 0.49 GB — 사실상 같은 집합.
- zip 개당 약 161.6 MB, **116개 = 14.58 GB.**

즉 원본 `Data/` 한 벌 + 빌드 레시피만 있으면 전량 재생성된다.
**VERIFIED — 추론이 아니라 zip 엔트리 목록을 직접 읽어 확인했다.**

### 2.3 `fs/*.zip` 70개는 TinyCore 루트 변종

파일명이 공통 접두 `TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1-pcrestd1-`
뒤에 변종 접미사만 다르다: `-acp949-xim11focusedit1`, `-xim12childedit1`,
`-xim14descendedit1`, `-xim15v6edit1`, `-noprefixupd1-acp949` 등.

개당 약 160 MB, **70개 = 10.73 GB.** 대부분은 이미 폐기된 실험이며
`FAILED_EXPERIMENTS.md` 가 xim30/xim31, korean7/korean8 계열의 재도입을 금지하고 있다.

### 2.4 소계

`apps/` + `fs/` = **25.3 GB**, 전체의 44%가 근사 중복 zip 186개다.

---

## §3 VERIFIED — 버전 관리가 존재하지 않는다

`.git/` 의 전체 내용:

```
.git/info
.git/info/exclude
```

**파일 1개.** `HEAD` 없음, `objects/` 없음, `refs/` 없음.
`git ls-files` 는 `fatal: not a git repository` 를 반환한다.
세션 시작 배너가 "clean / no recent commits" 로 보이는 것은 이 빈 껍데기 때문이다.

**커밋 이력이 0건이다.** 531 KB 의 `azrok_server.py` 를 포함한 5개월치 작업 전체가
버전 관리 밖에 있다. 정리 작업은 되돌릴 수 없는 이동·삭제를 수반하므로,
**§5 의 어떤 단계보다 git 복구가 먼저다.**

---

## §4 제안 구조 — 4계층

```
Azrok_Archive/
├── 00_ORIGINAL/          원본. 불변. 체크섬 필수.
│   ├── client/           Azrok_original.exe acknex.dll ackutl.dll med.exe
│   │                     Azrok.dat azrok.ico init.csv lgc.tmp sys.tmp test.csv
│   │                     Ver.txt Title.bmp logo.bmp BL.tga BL.wis
│   ├── data/             Data/                       (4,171 files, 0.49 GB)
│   ├── launcher/         starmaru/                   (별마루, 2007-2011)
│   ├── MANIFEST.sha256
│   └── PROVENANCE.md     출처·타임스탬프·무결성 근거
│
├── 10_SALVAGE/           발굴·복구본. 재취득 불가.
│   ├── dmdes/            DMDE 복구 산출물 (cab/ Text/ Other/ Documents/ $MetaData/)
│   ├── img2011/          docs/research/_img2011_extracted + _img2011_webcache
│   ├── web/              docs/research/_salvage (wayback cdx·html·screenshots·symbols)
│   └── SALVAGE_LOG.md    ★ 무엇을 어디서 어떻게 건졌는가
│
├── 20_RESEARCH/          연구 문서. git 대상.
│   ├── research/         docs/research 전체 (INDEX·REGISTRY·FAILED_EXPERIMENTS·gate*)
│   └── handoffs/         루트에 흩어진 HANDOFF_*.md 6건, AZROK_ANALYSIS,
│                         STATUS_REPORT, PATCH_NOTES, RE_REQUEST,
│                         NOTE_server_control_panel, NEW_SESSION_GOAL,
│                         Windows11_실행가이드
│
├── 30_SERVER/            재구현 코드. git 대상.
│   ├── azrok_server.py azrok_control.py azrok_control_page.py
│   │   azrok_protocol_registry.py azrok_private_access.py
│   │   azrok_launcher.py azrok_network.py azrok_capture.py azrok_ctl.py
│   └── tools/            손으로 쓴 스크립트만 (빌드 산출물·SDK 제외)
│
├── 40_BOXEDWINE/         우리 포크. git 대상.
│   ├── src/              bwujit_threaded_abi 소스 (빌드 산출물 제외)
│   ├── PATCHES.md        원본 BoxedWine 대비 수정점 + 업스트림 커밋 기준점
│   └── runtime/          현재 배포 중인 wasm/js 1벌
│
└── 90_REGENERABLE/       재생성 가능. 콜드 스토리지에서 제외하거나 별도 보관.
```

### 계층별 성격

| 계층 | 크기(예상) | 소실 시 |
|---|---:|---|
| `00_ORIGINAL` | ~0.6 GB | **치명적.** 다만 외부에 사본이 존재할 여지는 있음 |
| `10_SALVAGE` | ~12.4 GB | **치명적·복구 불가.** 직접 건진 것이라 외부 사본이 없다 |
| `20`+`30`+`40` | ~0.4 GB | **치명적.** 프로젝트의 실질적 산출물 전부 |
| `90_REGENERABLE` | ~44 GB | 시간만 들면 재생성 |

**대체 불가능한 것의 총합이 1 GB 미만이고, 나머지 57 GB 는 중복이거나 재생성 가능하다.**

### `90_REGENERABLE` 로 분류하는 것

| 대상 | 크기 | 근거 |
|---|---:|---|
| `apps/*.zip` 116개 → 최신 1개만 | 14.4 GB 절감 | §2.2 — `Data/` 전체 사본 |
| `fs/*.zip` 70개 → 현용 + FAILED_EXPERIMENTS 참조분만 | ~9 GB 절감 | §2.3 |
| `artifacts/` 덤프·대용량 로그 | ~2.1 GB | 결론이 문서에 남아 있으면 원본 불필요 |
| `tools/emsdk` | 1.95 GB | 외부 SDK. 버전 문자열만 기록 |
| `profiles/` (Edge 프로필) | 1.17 GB | 브라우저 캐시 |
| `_Converted_{WIS,PCX,TGA,MDL_Textures}` | ~0.04 GB | `Data/` 에서 변환 재생성 |
| Ghidra: `azrok..rep` `_ghidra_backup_*` `ghidra_temp` `headless_project.rep` | ~0.72 GB | `azrok._2026_04_09.gar` (72 MB) 1벌로 대체 |
| `.tmp_*` 3개, `__pycache__`, `logs/`, `captures/`, `server_state/`, `.runtime/` | ~0.24 GB | 런타임 산출물 |
| 루트: `tmp_audio_cap*`, `mrg_fixture*.log`, `*.obj` 3개, `screenshot*.{bmp,png}`, `Azrok2026*.jpg` | ~0.09 GB | 임시·중간 산출물 |

**58 GB → 약 14 GB (그중 12.4 GB 가 `10_SALVAGE`).**

---

## §5 실행 순서

되돌릴 수 없는 단계에 (!) 표시. 각 단계는 앞 단계 완료 후에만 진행한다.

1. **git 복구.** `git init` → `.gitignore` 작성(90_REGENERABLE 대상 전부 제외)
   → Tier 2/3/4 커밋. **이것이 끝나기 전에는 아무것도 옮기지 않는다.**
2. **체크섬 대장 생성.** `00_ORIGINAL` 후보 + `10_SALVAGE` 전체의 SHA-256 을 뜬다.
   원본이 정말 원본인지, 그동안 오염되지 않았는지의 유일한 근거가 된다.
3. **`PROVENANCE.md` / `SALVAGE_LOG.md` 작성.** 기억이 남아 있는 지금 쓴다.
   특히 `dmdes/` 12 GB 는 이 문서가 없으면 정체불명 파일 더미가 된다.
4. **복사(이동 아님)로 계층 구성.** 원본은 제자리에 둔 채 새 트리에 복사한다.
5. **새 트리 검증.** 체크섬 재대조, `Data/` 파일 수 4,171 일치 확인.
6. (!) **원 위치 정리.** 5번이 통과한 뒤에만. 중복 zip → 덤프/로그 → 임시파일 순으로,
   각 묶음마다 개별 확인.

---

## §6 NOT VERIFIED — 열린 질문

- `dmdes/` 의 출처와 복구 경위. `cab/` 5 GB 와 `Text/` 3.8 GB 가 각각 무엇인지,
  어느 디스크·어느 시점에서 건진 것인지 기록이 없다. §5-3 에서 채워야 한다.
- `docs/research/_img2011_extracted/` 의 `hansol`, `Program Files`, `WINDOWS`,
  `_broken_reference_0x*` 항목들의 의미와 원본 이미지 출처.
- `artifacts/` 의 덤프·대용량 로그 각각에 대해, 거기서 얻은 결론이 실제로
  문서화되어 있는지. 확인 전에는 삭제 후보로만 두고 지우지 않는다.
- `fs/*.zip` 70개 중 현재 운영에 쓰이는 것과 `FAILED_EXPERIMENTS.md` 가 참조하는 것의
  정확한 목록. 파일명 접미사로 추정은 되지만 대조 확인이 필요하다.
- `tools/` 71,587 파일 중 손으로 쓴 스크립트와 빌드 산출물의 경계.

---

## §7 측정 재현

```powershell
$root = '<home>\Documents\<project-dir>\Azrok_Plaza'

# 디렉터리별 크기
Get-ChildItem -Directory -Force $root | ForEach-Object {
  $s = Get-ChildItem -Recurse -File -Force -EA SilentlyContinue $_.FullName |
       Measure-Object Length -Sum
  [PSCustomObject]@{ Name=$_.Name; GB=[math]::Round($s.Sum/1GB,2); Files=$s.Count }
} | Sort-Object GB -Descending

# 최대 단일 파일
Get-ChildItem -Recurse -File -Force -EA SilentlyContinue $root |
  Sort-Object Length -Descending | Select-Object -First 20 Length, FullName

# app zip 내용물 확인
Add-Type -A System.IO.Compression.FileSystem
$z = [IO.Compression.ZipFile]::OpenRead("$root\tools\boxedwine_local\apps\Azrok_D3D9Web_pathouse_diag5.zip")
$z.Entries.Count; $z.Entries | Select-Object -First 12 FullName; $z.Dispose()
```

`du -sh` 는 이 트리에서 120초를 넘겨 완주하지 못한다. PowerShell 경로를 쓸 것.

---

## 관련

- `[[project_ghidra_baseline]]` — Tier 0 정본 파일명 근거
- `docs/research/FAILED_EXPERIMENTS.md` — `fs/*.zip` 보존 대상 판정에 필요
- `docs/research/REGISTRY.md` — 문서 전량 목록
