# AzrokStarter.ocx — 역분석 기록 (append-only)

대상: `docs/research/_img2011_extracted/WINDOWS/Downloaded Program Files/AzrokStarter.ocx` (36,864 B)
2011년 하드 덤프 IE `Downloaded Program Files` 캐시에서 복원.

---

## [1] AzrokStarter.inf 전문 — VERIFIED (텍스트 원문)

```inf
; INF file for JSStarter.ocx

[version]
signature="$CHICAGO$"
AdvancedINF=2.0

[Add.Code]
AzrokStarter.ocx=AzrokStarter.ocx
AzrokInstaller.exe=AzrokInstaller.exe
DSETUP.dll=DSETUP.dll

[AzrokStarter.ocx]
file-win32-x86=thiscab
clsid={6C0D5D40-BF44-45AF-B24C-2B4AD2CE30A9}
FileVersion=1,4,2,1
RegisterServer=yes

[AzrokInstaller.exe]
file-win32-x86=thiscab
FileVersion=1,4,2,1
Destdir=11

[DSETUP.dll]
file-win32-x86=thiscab
FileVersion=4,9,0,900
Destdir=11
```

### 확정 사실
- **CLSID `{6C0D5D40-BF44-45AF-B24C-2B4AD2CE30A9}`** — VERIFIED.
  `autoLauncher.dll` 의 `{63875209-13A5-4586-8756-74FB690099CA}` 와 **완전히 다른 컴포넌트**.
  문서 22 의 autoLauncher 와 혼동 금지.
- 버전 `1.4.2.1` (OCX 와 Installer 동일 버전 → 같은 빌드에서 함께 배포).
- **CAB 에 3개 파일이 함께 들어있었다** — VERIFIED:
  1. `AzrokStarter.ocx` — 등록되는 ActiveX (RegisterServer=yes)
  2. `AzrokInstaller.exe` — Destdir=11 (= `%windir%\system32`) 로 설치, 등록 안 함
  3. `DSETUP.dll` v4.9.0.900 — **DirectX Setup DLL** (dsetup.dll 은 DirectX 런타임 설치 API).
     v4.9.0.900 = DirectX 9.0c 계열 재배포 컴포넌트.

### 즉시 따라오는 추론
- `AzrokInstaller.exe` 가 system32 에 깔리고 `DSETUP.dll` 을 함께 쓴다 →
  **OCX 는 "게임 실행기"이자 "게임 설치기"** 다. DirectX 존재 확인/설치 후 클라이언트 설치를 수행하는 구조. — INFERRED
- `; INF file for JSStarter.ocx` 주석 → 원본 템플릿이 `JSStarter.ocx` 였다.
  별마루/funitto 계열의 **범용 스타터 OCX 를 게임별로 리브랜딩**한 것. — INFERRED
- `Destdir=11` 은 system32. OCX 자체는 `Downloaded Program Files` 에 남는다(RegisterServer=yes, Destdir 없음). — VERIFIED (INF 시맨틱)

### 아직 모르는 것 — NOT VERIFIED
- `WEB2INITSTART` 의 실제 시그니처와 4개 인자 처리
- 최종 실행 대상 (`starmaru.exe` / `open.exe` / `Azrok.exe` / `AzrokInstaller.exe`)
- 레지스트리 키

---

## [2] AzrokInstaller.exe 를 덤프에서 발견 — VERIFIED

`_img2011_extracted/WINDOWS/system32/AzrokInstaller.exe` — **684,120 B**.
INF 의 `Destdir=11` 대로 system32 에 설치돼 있었고, 2011 덤프에 그대로 남아있다.
`DSETUP.dll` 은 덤프에 없음(별도 확인 필요).

→ CAB 3개 파일 중 2개를 확보. **후속 분석 대상 1순위.**

---

## [3] OCX 임포트 테이블 — VERIFIED (PE 파싱)

| DLL | 주요 임포트 |
|---|---|
| **DSETUP.dll** | (ordinal/미해결 — DirectX 버전 질의) |
| KERNEL32 | `GetVersionExA`, `GetDiskFreeSpaceExA`, `GetWindowsDirectoryA`, `GlobalMemoryStatus` |
| **SHELL32** | **`ShellExecuteA`** |
| ole32 | `CoCreateInstance` |
| USER32 | `FillRect`, `wsprintfA`, `EnableWindow` |
| GDI32 | `GetStockObject` |
| MFC42 / MSVCRT / OLEAUT32 | 런타임 |

**MFC42 기반 ActiveX 컨트롤**(`COleControl` 파생). 클래스명 `CAzrokStarterCtrl`, `CAzrokStarterPropPage`.
ProgID: `AZROKSTARTER.AzrokStarterCtrl.1`.

임포트 조합이 곧 기능 명세다 — **시스템 요구사항 검사 + 프로세스 실행**. 네트워크 API(WinInet/WinSock)가
**하나도 없다** → OCX 는 직접 다운로드하지 않는다. 다운로드는 `AzrokInstaller.exe` 담당. — VERIFIED (임포트 부재)

---

## [4] 핵심 문자열 (오프셋 포함) — VERIFIED

```
0x521c 'AzrokInstaller.exe'
0x5230 'GAMESESSION '     0x524c 'GAMESESSION'
0x5258 'GAMEID '          0x5270 'GAMEID'
0x5394 'GAMEIP '          0x53ac 'GAMEIP'
0x746b '\AzrokStarter'
0x4120 'DSETUP.dll'
```

시스템 검사 문자열군:
- OS: `Microsoft Windows 3.1 / 95 / 98 / 98SE / ME / NT 4.0 / 2000 / XP / 2003 %s (Build %d)`
- DirectX: `DirectX version is 9.0c / 9.0b / 9.0a / 9.0`, `. DirectX version is 8.%d`, `DirectX 8.1`
- 디스크: `600Mb`, ` (%dMb/%dMb)`
- 메모리: `128Mb`
- ShellExecute 오류 전체: `SE_ERR_SHARE/OOM/NOASSOC/DDETIMEOUT/DDEFAIL/DDEBUSY/ASSOCINCOMPLETE/ACCESSDENIED`,
  `ERROR_BAD_FORMAT`, `ERROR_PATH_NOT_FOUND`, `ERROR_FILE_NOT_FOUND`,
  `The operating system is out of memory or resources`

**최소 사양이 확정됐다 — VERIFIED**: DirectX 8.1+, 여유 디스크 600MB, RAM 128MB.

### `GAMEIP` / `GAMEID` / `GAMESESSION` — 새 파라미터 3종
문서 22 의 `p_target_id`/`p_mbr_id`/`p_mbr_auth_key`(웹 로그인) 및
`Azrok.exe` 커맨드라인 `"IP:PORT user auth"` 와 **자릿수가 정확히 대응**한다:

| OCX 파라미터 | Azrok.exe 인자 | WDL 엔진 변수 |
|---|---|---|
| `GAMEIP` | `IP:PORT` | `engine+0x9a0` |
| `GAMEID` | user | `engine+0x998` |
| `GAMESESSION` | auth | `engine+0x9ac` |

— INFERRED (강한 대응이지만 디컴파일로 확정 필요)

각 이름이 **후행 공백 있는 변형과 없는 변형 2개씩** 존재(`'GAMEIP '` / `'GAMEIP'`).
전형적인 "커맨드라인 조립용 토큰 + 파라미터 이름" 쌍. — INFERRED

---

## [5] 타입라이브러리 전문 — `WEB2INITSTART` 가 **없다** — VERIFIED

타입라이브러리 name table (0x7400–0x752d) 전체:

```
0x7400 'AZROKSTARTERLib'
0x741c '_DAzrokStarter'          (dispinterface)
0x7438 'AboutBox'                ← 유일한 메서드
0x744c '_DAzrokStarterEvents'
0x746b '\AzrokStarter'
0x747a 'AzrokStarter.hlp'
0x748e 'AzrokStarter ActiveX Control module'
0x74b6 'Dispatch interface for AzrokStarter Control'
0x74e6 'Event interface for AzrokStarter Control'
0x7512 'AzrokStarter Control'
```

(끝의 `W`/`D` 문자는 MSFT 타입라이브 name table 의 정렬 패딩이지 이름 일부가 아님.)

**ASCII·UTF-16LE 양쪽 전수 검색에서 `WEB2`, `INITSTART`, `ocxVer`, `homeUrl`, `updateServer`
문자열이 단 하나도 나오지 않는다.** — VERIFIED

### 이것이 뒤집는 것
IE 캐시의 JS `document.initOcx.WEB2INITSTART(gameOcxVer, gameServerAddr, updateServer, homeUrl)`
는 **이 바이너리로 설명되지 않는다.** 두 갈래 중 하나다:

- (A) `initOcx` 는 AzrokStarter.ocx 가 **아닌 다른 OCX** (INF 주석의 원본 `JSStarter.ocx` 계열,
  또는 별마루 공용 스타터). 인자 이름(`updateServer`, `homeUrl`)이 패처 성격이라 정황상 유력.
- (B) `WEB2INITSTART` 를 가진 것은 **다른 버전**의 AzrokStarter (여기 있는 건 1.4.2.1).

→ **`AzrokStarter.ocx == initOcx` 라는 전제는 현 시점 NOT VERIFIED.** 임무 브리핑의 전제를 보류한다.
   대신 이 OCX 는 `<object>` + `<param name="GAMEIP"...>` 로 값을 받는 별개의 실행 경로로 보인다 — INFERRED.

### 이 OCX 의 실제 호출 방식 (INFERRED)
메서드가 `AboutBox` 뿐이므로 JS 메서드 호출로 구동되지 않는다.
MFC `COleControl::DoPropExchange` + `IPersistPropertyBag::Load` 경로로
HTML `<param>` 태그에서 `GAMEIP`/`GAMEID`/`GAMESESSION` 을 읽는 구조가 유력:

```html
<object classid="clsid:6C0D5D40-BF44-45AF-B24C-2B4AD2CE30A9"
        codebase="AzrokStarter.cab#version=1,4,2,1">
  <param name="GAMEIP"      value="202.89.127.166:8949">
  <param name="GAMEID"      value="...">
  <param name="GAMESESSION" value="...">
</object>
```
→ 디컴파일로 확정 필요 (NOT VERIFIED)

---

## [6] 디컴파일 완료 — OCX 의 전 기능은 함수 **하나**다 — VERIFIED

Ghidra MCP 는 `Database is closed` 로 실패. `analyzeHeadless` 로 우회(임시 프로젝트, 기존 azrok 프로젝트 무손상).

전체 함수 목록에서 **의미 있는 코드는 `FUN_100016e0` (0x100016e0, 1684 B) 단 하나**.
나머지는 MFC 보일러플레이트(DllRegisterServer, 팩토리, 언와인드 썽크).

`FUN_100016e0` 의 시그니처와 첫 줄이 정체를 확정한다:

```c
void __thiscall FUN_100016e0(void *this, CPropExchange *param_1)
{
  ...
  COleControl::DoPropExchange(this, param_1);   // 기반 클래스 호출
```

→ **`CAzrokStarterCtrl::DoPropExchange`** 다. — VERIFIED

### 이것이 확정하는 것: 이 OCX 에는 호출 가능한 메서드가 없다
`DoPropExchange` 는 IE 가 `<object>` 태그의 `<param>` 을 읽어줄 때
(`IPersistPropertyBag::Load`) MFC 가 자동으로 부르는 훅이다.
**JS 가 메서드를 부르는 구조가 아니라, 페이지에 컨트롤이 인스턴스화되는 순간
파라미터를 읽고 곧바로 게임을 실행한다.** [5] 의 타입라이브러리 증거(메서드=`AboutBox` 뿐)와 정확히 일치. — VERIFIED

---

## [7] **최종 답: OCX 가 실행하는 것** — VERIFIED (디컴파일 본문)

함수 말미의 실제 코드 흐름:

```c
CString result;                       // 누적 버퍼
CString tmp = "";
PX_String(param_1, "GAMEIP", &tmp);        // <param name="GAMEIP"> 읽기
if (strlen(tmp)==0) → AfxMessageBox("GAMEIP 파라미터 없음"), 중단
result += tmp;  result += " ";

tmp = "";
PX_String(param_1, "GAMEID", &tmp);
if (strlen(tmp)==0) → AfxMessageBox("GAMEID 파라미터 없음"), 중단
result += tmp;  result += " ";

tmp = "";
PX_String(param_1, "GAMESESSION", &tmp);
if (strlen(tmp)==0) → AfxMessageBox("GAMESESSION 파라미터 없음"), 중단
result += tmp;  result += " ";

ShellExecuteA(NULL, "open", "AzrokInstaller.exe", result, NULL, SW_SHOWNORMAL);
```

데이터 상수 실측 (파일 오프셋 = RVA):

| 주소 | 값 |
|---|---|
| `DAT_10005214` (verb) | `"open"` |
| `DAT_10005278` (구분자) | `" "` (공백 1개) |
| `DAT_10005924` (초기값) | `""` |
| `0x10005394` / `0x10005258` / `0x10005230` | `"GAMEIP 파라미터 없음"` / `"GAMEID 파라미터 없음"` / `"GAMESESSION 파라미터 없음"` |

### 확정된 커맨드라인

```
AzrokInstaller.exe "<GAMEIP> <GAMEID> <GAMESESSION> "
```

공백 구분, **끝에도 구분자 하나가 더 붙는다**(마지막 `result += " "`). — VERIFIED

### 이것이 문서 22 와 맞물리는 지점 ★
`Azrok.exe` 가 받는 커맨드라인은 `"IP:PORT user auth"` — **공백 구분 3-튜플, 자릿수·순서 완전 일치.**

```
웹 <param>        →  OCX 조립          →  Azrok.exe          →  WDL 엔진
GAMEIP            →  1번째 토큰        →  "IP:PORT"          →  engine+0x9a0
GAMEID            →  2번째 토큰        →  user               →  engine+0x998
GAMESESSION       →  3번째 토큰        →  auth               →  engine+0x9ac
```

즉 **`GAMEIP` 는 IP 단독이 아니라 `IP:PORT` 형태**여야 한다(문서 22 의 `strtok(param2,":")` 가 요구).
원본 값이라면 `202.89.127.166:8949`. — INFERRED (강함: 토큰 개수·구분자·순서가 모두 일치)

`AzrokInstaller.exe` 가 이 3-튜플을 **그대로 `Azrok.exe` 로 전달(pass-through)** 하는지는
Installer 디컴파일로 확인해야 한다. — NOT VERIFIED

---

## [8] 시스템 요구사항 게이트 전문 — VERIFIED (디컴파일 실측)

`DoPropExchange` 는 파라미터를 읽기 **전에** 4단 게이트를 통과해야 한다.
하나라도 실패하면 `AfxMessageBox` 후 `return` — **ShellExecute 에 도달하지 못한다.**

| # | 검사 | API | 실제 조건 | 실패 메시지 |
|---|---|---|---|---|
| 1 | 물리 메모리 | `GlobalMemoryStatus` | `dwTotalPhys>>20 < 110` → 실패 | `메모리 크기가 작습니다. (%dMb/%dMb)\n이 게임은 128Mb 이상의 메모리가 필요합니다.` |
| 2 | 디스크 여유 | `GetWindowsDirectoryA` → 드라이브 문자 → `GetDiskFreeSpaceExA` | 여유 `< 600 MB` → 실패 | `%c 드라이브에 공간 부족 (%dMb/%dMb)\n 이게임은 600Mb 이상의 여유공간이 필요합니다.` |
| 3 | DirectX | `DSETUP.dll` **Ordinal 11** = `DirectXSetupGetVersion` | `(ver&0xffff) > 7 && != 8` → **DX9 이상만 통과** | `Direct X버전이 낮습니다. DirectX version is 8.%d` / `...%d.0` / `Direct X 가 설치 되지 않았거나 알 수 없는 버전입니다.` |
| 4 | OS | `GetVersionExA` | 아래 표 | `이 게임은 Microsoft Windows 98SE 이상을 필요로 합니다.` |

**메모리 임계값 주의**: 메시지는 "128Mb" 라고 하지만 실제 비교는 `< 0x6e` = **110 MB**. — VERIFIED

**DirectX 임계값 주의**: 메시지는 전부 "DirectX 8.1 이상"이라 하지만 실제 통과 조건은 `ver >= 9`.
DX8 은 case 8 에서 메시지를 찍고, 이어지는 `!= 8` 게이트에서 걸린다. **메시지와 코드가 불일치** —
문구를 믿지 말 것. — VERIFIED

`Ordinal_11` 이 `DirectXSetupGetVersion` 인 근거: DSETUP.dll 임포트, out-DWORD 2개 시그니처,
반환값 LOWORD 를 그대로 DirectX 메이저 버전(7/8/9)으로 switch. — VERIFIED

### OS 판정표 (`dwPlatformId` / `dwMinorVersion` / `szCSDVersion[1]`)

| platformId | 조건 | 결과 |
|---|---|---|
| 0 | — | **차단** (Windows 3.1 또는 그 이하) |
| 1 (Win9x) | minor `0` | **차단** (Windows 95) |
| 1 | minor `10`, `szCSDVersion[1] != 'A'` | **차단** (Windows 98 무印 = 비 SE) |
| 1 | minor `10`, `szCSDVersion[1] == 'A'` | **통과** (Windows 98**SE**) |
| 1 | minor `90` (0x5a) | **통과** (Windows ME) |
| 1 | 그 외 | **차단** |
| 2 (NT) | major `< 5` | **통과** (NT 4.0) |
| 2 | major≥5, minor `0` / `1` / `2` | **통과** (2000 / XP / 2003) |
| 그 외 | — | **차단** (`OS 확인 불가`) |

Windows 98SE 판별에 `szCSDVersion[1] == 'A'` 를 쓰는 건 당대 표준 관용구다. — VERIFIED

---

## [9] 레지스트리를 **전혀 쓰지 않는다** — VERIFIED (부재 증명)

임포트 DLL 전수: `DSETUP.dll`, `KERNEL32.dll`, `MFC42.DLL`, `MSVCRT.dll`,
`USER32.dll`, `GDI32.dll`, `SHELL32.dll`, `ole32.dll`, `OLEAUT32.dll`.

- **`ADVAPI32.dll` 없음** — 바이너리 전체에 `ADVAPI` 문자열 부재.
- `RegOpenKey` / `RegSetValue` / `RegQueryValue` / `RegCreateKey` 문자열 **전부 부재**.

→ **OCX 는 `SOFTWARE\starmaru\` 등 어떤 레지스트리 키도 읽거나 쓰지 않는다.** — VERIFIED

이는 `autoLauncher.dll` 과의 결정적 차이다. autoLauncher 는 `HKLM\SOFTWARE\<key>\autoLauncher`
(REG_BINARY `workdir\0exepath\0`)에서 경로를 읽지만, AzrokStarter 는 **경로를 하드코딩**
(`"AzrokInstaller.exe"`, 상대 경로)하고 값은 전부 웹 `<param>` 에서 받는다.

`ShellExecuteA` 의 파일명이 **상대 경로 `"AzrokInstaller.exe"`** 이고 `lpDirectory=NULL` 이므로,
탐색은 프로세스 CWD → `%windir%\system32`(PATH) 순. INF 의 `Destdir=11`(system32) 배치가
바로 이 해석 경로를 노린 것이다. — VERIFIED (호출 인자) / INFERRED (의도)

`\AzrokStarter` 문자열(0x746b)은 레지스트리 키가 아니라 **타입라이브러리의 헬프 파일 경로**
(`AzrokStarter.hlp` 와 인접). 오독 주의. — VERIFIED

---

## [10] 두 갈래 실행 체인이 **별개로 존재**한다 — INFERRED (강함)

| | **웹 ActiveX 체인** (이번 발견) | **로컬 설치형 체인** (문서 22) |
|---|---|---|
| 컴포넌트 | `AzrokStarter.ocx` | `autoLauncher.dll` |
| CLSID | `{6C0D5D40-BF44-45AF-B24C-2B4AD2CE30A9}` | `{63875209-13A5-4586-8756-74FB690099CA}` |
| 배포 | 웹 CAB 다운로드 (`Downloaded Program Files`) | `starmaru.exe` 가 `regsvr32` |
| 구동 | `<param>` → `DoPropExchange` (JS 호출 없음) | JS `"run"` / `"send"` 명령 |
| 경로 출처 | 하드코딩 `AzrokInstaller.exe` | 레지스트리 REG_BINARY |
| 실행 대상 | `AzrokInstaller.exe` | 레지스트리의 exe (=`Azrok.exe`) |
| 인자 | `"GAMEIP GAMEID GAMESESSION "` | JS 가 준 문자열 그대로 |
| 호스트 | IE (웹페이지) | `open.exe` 내장 WebBrowser |

**용도 분리 해석**: `AzrokStarter.ocx` 는 **최초 방문자용 설치 진입점**
(사양 검사 → 인스톨러 실행), `autoLauncher.dll` 은 **설치 완료 후 재실행 경로**.
DirectX 검사·600MB 디스크 검사·`DSETUP.dll` 동봉이 전부 "설치 전 사양 확인" 문법이다.

### `WEB2INITSTART` 에 대한 결론
[5] 에서 확인한 대로 이 바이너리에 그 이름이 없다.
`WEB2INITSTART(gameOcxVer, gameServerAddr, updateServer, homeUrl)` 의 인자 구성
(`ocxVer`, `updateServer`, `homeUrl`)은 **버전 확인·패치·홈 이동** 성격으로,
`GAMEIP/GAMEID/GAMESESSION`(접속 3-튜플)과 목적이 다르다.
→ `document.initOcx` 는 **또 다른 미확보 OCX** 일 가능성이 높다(INF 주석의 `JSStarter.ocx` 계열). — INFERRED

**세 번째 컴포넌트를 아직 못 찾았다.** IE 캐시/CAB 잔해에서 `JSStarter.ocx` 또는
`WEB2INITSTART` 를 가진 OCX 를 추가 수색할 가치가 있다. — 후속 과제

---

## [11] 우리 런처(`azrok_launcher.py`)와의 차이 — 결론

원본 OCX 가 하는 일 중 **우리가 놓친 단계는 없다.** 근거:

1. OCX 의 검사 4종(RAM/디스크/DirectX/OS)은 **2011년 사양 게이트**일 뿐,
   게임 동작에 어떤 값도 전달하지 않는다. 현대 PC 는 전부 통과하며, 실패해도
   `AfxMessageBox` 후 중단이지 상태를 남기지 않는다. → 재현 불필요. — VERIFIED
2. OCX 는 레지스트리를 읽지도 쓰지도 않는다([9]). → 우리가 세팅할 키가 없다. — VERIFIED
3. OCX 가 넘기는 것은 **공백 구분 3-튜플이 전부**다. 우리 런처는 이미 동일한 3-튜플을
   WDL 엔진 변수(`+0x9a0/+0x998/+0x9ac`)에 직접 주입한다 — 즉 **더 하류에서 같은 값을 넣는다.**

→ 우리 런처는 `OCX → AzrokInstaller.exe → Azrok.exe → engine+0x9xx` 사슬의
**마지막 단계로 직행**하는 것이며, 건너뛴 중간 단계는 값을 변형하지 않는다(단, 3 은
Installer 가 pass-through 라는 가정에 의존 — [7] 참조, 확인 대기).

**실질적 수확은 다른 데 있다**: 웹 페이지가 게임에 넘긴 값의 **이름과 형식이 확정**됐다.
`GAMEIP` 가 `IP:PORT` 합성 문자열이라는 점, 셋 다 비면 실행 자체가 막힌다는 점은
서버측 세션 발급 로직(`GAMESESSION` 이 곧 auth key)을 재구현할 때의 계약서다.

---

# AzrokInstaller.exe — 후속 분석 (같은 CAB 의 2번째 파일)

`_img2011_extracted/WINDOWS/system32/AzrokInstaller.exe` (684,120 B), `analyzeHeadless` 디컴파일.

## [12] Installer 가 argv 를 받는 방식 — VERIFIED

`FUN_00405b30` (= 메인 `CDialog` 생성자, `CDialog::CDialog(this, 0x66, ...)`) 에서:

```c
CString::operator=((CString*)(this+0x70), argv[1]);   // ← GAMEIP
CString::operator=((CString*)(this+0x74), argv[2]);   // ← GAMEID
CString::operator=((CString*)(this+0x78), argv[3]);   // ← GAMESESSION
```

`__p___argv()` 로 CRT argv 를 읽어 오프셋 4/8/0xc = `argv[1]`/`argv[2]`/`argv[3]` 를 멤버에 저장.
**OCX 가 공백으로 이어붙인 3-튜플이 정확히 여기로 들어온다.** [7] 의 체인이 양쪽에서 맞물려 확정됨.

## [13] 하드코딩된 상수 — VERIFIED

같은 생성자에서 설정되는 전역/멤버:

| 값 | 대상 |
|---|---|
| `%c:\Program Files\Hansol\Azrok_Naver` | 설치 디렉터리 (`DAT_0041e814`) |
| `%c:\Program Files\Hansol` | 상위 디렉터리 (`DAT_0041e804`) |
| `Azrok.exe` | 실행 파일명 (`this+0x60`) |
| **`file.jr.naver.com`** | 다운로드 호스트 (`DAT_0041e7fc`) |
| **`/azrok/download/`** | 다운로드 경로 (`DAT_0041e80c`) |
| `Setup.zip` | 패키지 파일명 (`DAT_0041e800`) |
| `UpdateInfo` | 갱신 정보 파일 (`DAT_0041e808`) |
| `40000000` (0x2625A00) | 크기/타임아웃 상수 (`DAT_0041e7dc`) |

다른 함수의 URL:
- `http://file.funitto.com/azrok/notice/notice_naver.html` (공지, `FUN_00405fc0`)
- `http://www.funitto.com/azrok/main.screen` (홈, `FUN_00407810`)
- `\azrok.ico` (바로가기 아이콘)

**새 호스트 `file.jr.naver.com` 확보** — 네이버 주니어(jr.naver.com) 배포판.
문서 22 의 `file.funitto.com` / `starmaru.funitto.com` 와 별개의 배포 채널. — VERIFIED

## [14] 레지스트리 — VERIFIED (디스어셈블 실측)

`FUN_00406c10`, `CreateProcessA` 직전에 호출:

```
RegCreateKeyExA(HKEY_CURRENT_USER, "Software\Hansol\Azrok_Naver", 0,0,0, 0x20006, 0, &hKey, &disp)
RegSetValueExA(hKey, "InstallPath", 0, REG_SZ, <설치디렉터리>, 0xff)
RegSetValueExA(hKey, "Version",     0, REG_SZ, NULL, 0)      ← 빈 값
RegCloseKey(hKey)
```

- 루트는 `0x80000001` = **HKEY_CURRENT_USER** (HKLM 아님). — VERIFIED
- `0x20006` = `KEY_WRITE`.
- **읽기가 아니라 쓰기 전용.** Installer 는 자기 설치 경로를 기록만 한다.

문서 22 의 autoLauncher 는 `HKLM\SOFTWARE\<key>\autoLauncher` 를 **읽는다**.
`Software\Hansol\Azrok_Naver` 는 **다른 키, 다른 방향**이다. 혼동 금지.

## [15] ★ Installer 가 Azrok.exe 를 띄우는 실제 커맨드라인 — VERIFIED

`FUN_00406a60`:

```c
CString::Format(&local_18, "%s\\%s", DAT_0041e814, this+0x60);  // <설치디렉터리>\Azrok.exe
CreateProcessA(
    lpApplicationName = "<설치디렉터리>\\Azrok.exe",
    lpCommandLine     = this+0x6c,
    ...,
    bInheritHandles   = TRUE,
    lpCurrentDirectory= <설치디렉터리>,
    ...);
```

`this+0x6c` 의 정체를 디스어셈블로 추적(0x00405da8, 디컴파일러가 유실한 부분):

```asm
00405da8  PUSH 0x418c30   ; " -NX 100 -NWND -PL naver -DIR 0123456789 -IP 127.0.0.1:3000"
00405dad  MOV EDX, [EBP-0x10]
00405db0  ADD EDX, 0x6c
00405db3  PUSH EDX
00405db4  CALL 0x00415cb8   ; CString::Format
00405db9  ADD ESP, 0x8      ; ← 인자 2개뿐 = 가변인자 없음
```

`ADD ESP,8` 이 결정적이다 — **포맷 지정자도 가변인자도 없는 순수 리터럴 대입**이다.
(비교: `FUN_00406a60` 의 `"%s\%s"` 호출은 `ADD ESP,0x10` 으로 인자 4개.) — VERIFIED

### 따라서 — 이 빌드는 argv 를 **버린다**

`this+0x6c` 는 생성자에서 **한 번 쓰이고**(리터럴), `FUN_00406a60` 에서 **한 번 읽힌다**(lpCommandLine).
그 사이 재조립이 없다. 그리고 `this+0x70/0x74/0x78`(= argv 1/2/3)은
전체 디컴파일 전수 검색 결과 **생성자에서 대입되고 소멸자(`FUN_00405140`)에서 파괴될 뿐,
어디에서도 읽히지 않는다.** — VERIFIED (전수 검색)

→ **덤프에 남은 이 `AzrokInstaller.exe` 는 하드코딩된 테스트 커맨드라인으로 게임을 띄우는
   디버그/테스트 빌드다.** `GAMEIP`/`GAMEID`/`GAMESESSION` 을 받아놓고 쓰지 않는다.

이는 [11] 의 pass-through 가정에 대한 답이다: **pass-through 가 아니다.**
다만 이것이 출시 빌드의 동작인지 테스트 잔재인지는 이 바이너리 하나로 단정 못 한다 — NOT VERIFIED.
(선행 공백은 argv[0] 자리를 비우는 정석 관용구이므로 실수가 아니라 의도된 커맨드라인이다.)

### ★ 엔진 옵션 사전 확보

```
-NX 100        nexus 크기 100
-NWND          (윈도우 관련 플래그로 추정)
-PL naver      플랫폼 = naver
-DIR 0123456789   10자리 ID (네이버 회원번호 자리수와 일치) — INFERRED
-IP 127.0.0.1:3000   접속 대상, IP:PORT 결합형
```

- `-NX <n>` 는 문서 62 에서 이미 native Acknex 옵션으로 확정된 것과 **문법이 정확히 일치**
  (`-NX 200` 허용, `-NX=200` 불가). 원본 런처가 `-NX 100` 을 썼다는 실물 증거. — VERIFIED
- `-IP` 가 `IP:PORT` 를 한 토큰으로 받는다는 점은 문서 22 의 `strtok(param2,":")` 와 정합. — VERIFIED
- 이 문자열은 `_img2011_scan.md` 331/335 행의 원시 스캔에도 이미 잡혀 있었으나 출처 미상이었다.
  **출처가 `AzrokInstaller.exe` 0x418c30 임이 확정됐다.** — VERIFIED

## [16] Plaza 빌드 ≠ Naver 빌드 — VERIFIED

우리 `Azrok.exe` 내부 문자열: `%c:\Program Files\Hansol\Azrok_**Plaza**\Screenshot\`
Installer 내부 문자열: `%c:\Program Files\Hansol\Azrok_**Naver**`

→ **같은 게임의 서로 다른 배포판이다.** 우리가 복원 중인 것은 Hansol 자체 `Azrok_Plaza`,
덤프의 인스톨러는 네이버 주니어 제휴판 `Azrok_Naver`. — VERIFIED

우리 `Azrok.exe` 에는 `-NWND`/`-PL`/`-DIR`/`-IP`/`-NX`/`naver` 리터럴이
대소문자 무관 전수 검색에서 **하나도 없다**(`Hansol` 3회, `ACKNEX` 1회는 존재). — VERIFIED

이 부재를 "우리 빌드는 해당 옵션을 안 받는다"로 읽으면 **안 된다** — 문서 62 가
같은 바이너리에서 `-NX 200` 이 실제로 먹는 것을 실측했다. Acknex 는 옵션명을
평문 문자열 테이블로 두지 않는다. 나머지 옵션(`-PL`/`-DIR`/`-NWND`/`-IP`)이
우리 Plaza 빌드에서 유효한지는 **디버거 실측이 필요**하다 — ~~NOT VERIFIED, 후속 과제.~~

> **⬆ 승격 2026-07-19 — VERIFIED (문서 138).**
> BoxedWine/Wine 11 네이티브 실행에서 이 커맨드라인이 **실제로 먹었다**:
> ```text
> Azrok.exe -NX 200 -NWND -PL player -DIR localauth -IP 127.0.0.1:9200
> ```
> 5단계 전부 PASS — (a) 기동 (b) `Direct3DCreate9`/`wined3d_device_create`
> (c) 화면 출력 (d) 프레임 갱신 (e) **서버가 106바이트 C2S `0x0000` 로그인 수신**.
> 즉 `-PL`=username, `-DIR`=authkey, `-IP`=`host:port` 라는 매핑이 Plaza 빌드에서
> 그대로 성립한다. 위 "리터럴이 하나도 없다"는 관측은 유효하지만, 예상대로
> **옵션 부재의 증거가 아니었다.**
>
> 부수 성과: 이 형태가 `azrok_launcher.py` 의 WDL 메모리 주입 경쟁을 **원인째 제거**한다.
> 주입 방식은 게임이 `FUN_00508b30`(`strtok(param2,":")`)에 도달하는 시점이
> 주입보다 빨라 널 소스로 `0x00654453` 에서 크래시했다(`c0000005`).
> 커맨드라인은 프로세스 시작 시점에 값이 이미 존재하므로 경쟁 자체가 없다.

---

## 미해결 (후속 과제)

1. `WEB2INITSTART` 를 가진 세 번째 컴포넌트(`JSStarter.ocx`?) — IE 캐시/CAB 잔해 추가 수색.
2. `DSETUP.dll` — 덤프에 없음.
3. ~~Plaza 빌드에서 `-PL` / `-DIR` / `-NWND` / `-IP` 실효성 — x32dbg 실측.~~
   **✅ 해결 2026-07-19 (문서 138) — VERIFIED.** x32dbg 가 아니라 BoxedWine 실행으로
   확인됐다. 서버 로그인 수신까지 도달 = 세 플래그 모두 유효.
4. 출시판 `AzrokInstaller.exe` 가 argv 를 실제로 전달하는지 (덤프본은 테스트 빌드).

---

# 2차 조사 (같은 세션 후속)

## [17] pass-through 여부 — **전달하지 않는다** 를 명령어 수준으로 확정 — VERIFIED

[15] 의 근거는 디컴파일 **텍스트** grep 이었다. 두 가지 구멍이 있었다:
(a) 디컴파일러가 `DAT_0041e818->field_0x70` 같은 접근을 다르게 렌더링할 수 있음,
(b) 전역 `DAT_0041e818 = this` 를 통한 우회 접근.

두 구멍을 모두 막았다.

### (a) 전역 다이얼로그 포인터 `DAT_0041e818` 의 전 용례 — VERIFIED

```
FUN_00405b30 :: DAT_0041e818 = local_14;              (대입)
FUN_00406720 :: CDialog::EndDialog(DAT_0041e818, 2)
FUN_00406cc0 :: FUN_00408200(DAT_0041e818, ...)
FUN_00406cc0 :: CWnd::SetWindowTextA((CWnd*)DAT_0041e818, ...)
FUN_00406cc0 :: CDialog::EndDialog(DAT_0041e818, 0)   x2
FUN_00406cc0 :: CWnd::SetWindowTextA((CWnd*)DAT_0041e818, &DAT_00419020)
FUN_00406cc0 :: CDialog::EndDialog(DAT_0041e818, 2)
FUN_004073d0 :: FUN_00408200(DAT_0041e818, ...)
```

전부 `CWnd*`/`CDialog*` 로만 소비된다. 멤버 필드 역참조가 **하나도 없다.**

### (b) 명령어 수준 전수 스캔 — VERIFIED (결정적)

Ghidra 스크립트로 **프로그램 전체 명령어**에서 필드 오프셋 `0x6c/0x70/0x74/0x78` 을
언급하는 것을 전수 추출(207건). `[EBP - 0x..]`(지역변수·음수 오프셋)과 vtable 호출을
걷어내면 **객체 필드 접근은 다음이 전부**다:

| 함수 | 주소 | 명령 | 의미 |
|---|---|---|---|
| `FUN_00405140` (소멸자) | 004051b3/c2/d1/e0 | `ADD ECX,0x78/0x74/0x70/0x6c` | `CString::~CString` ×4 |
| `FUN_00405b30` (생성자) | 00405b7b/8a/99/a8 | `ADD ECX,0x6c/0x70/0x74/0x78` | `CString::CString` ×4 (생성) |
| `FUN_00405b30` | 00405d72/89/a0 | `ADD ECX,0x70/0x74/0x78` | **argv[1]/[2]/[3] 대입** |
| `FUN_00405b30` | 00405db0 | `ADD EDX,0x6c` | `CString::Format(리터럴)` |
| `FUN_00406a60` | 00406a99 | `ADD EAX,0x6c` | **유일한 읽기** → `lpCommandLine` |

(`FUN_004080e0` 의 `CALL dword ptr [EAX + 0x70]` 은 무관한 vtable 디스패치.)

### 결론

**`+0x70` / `+0x74` / `+0x78` (= `GAMEIP` / `GAMEID` / `GAMESESSION`) 는
바이너리 전체에서 생성·대입·파괴만 될 뿐 단 한 번도 읽히지 않는다.** — VERIFIED

**`+0x6c` (커맨드라인) 는 생성자에서 리터럴로 채워지고 `FUN_00406a60` 에서 한 번 읽혀
`CreateProcessA` 로 간다. 그 사이 재조립이 없다.** — VERIFIED

→ **덤프본 `AzrokInstaller.exe` 는 3-튜플을 전달하지 않는다. pass-through 는 거짓이다.**

### 따라서 체인은 아직 닫히지 않았다

`웹 <param> → OCX → Installer → Azrok.exe → WDL 엔진` 을 VERIFIED 로 닫으려던 시도는
**실패했다.** 덤프본 Installer 에서 사슬이 **끊긴다**:

```
웹 <param>  →  OCX  →  Installer  ─╳→  Azrok.exe
[VERIFIED]  [VERIFIED]      ↑
                    여기서 argv 가 버려지고
                    하드코딩 리터럴로 대체됨
```

따라서 **`GAMEIP = 202.89.127.166:8949` 추론은 승격할 수 없다.** — INFERRED 유지.
`data.dat` 의 `gameServer 202.89.127.166` / `gameServerPort 8949` 와
`GAMEIP` 가 `IP:PORT` 결합형이라는 점은 여전히 정합하지만, 이 바이너리는 그 연결의
**증인이 되지 못한다**(자기 argv 를 안 쓰므로). 다른 증인이 필요하다:
출시판 Installer, 또는 `open.exe`/`autoLauncher` 경로.

### 이 빌드의 성격 — INFERRED
`-IP 127.0.0.1:3000`(로컬호스트), `-DIR 0123456789`(자리표시자 성격의 0~9 나열),
`-PL naver` 가 한 리터럴에 묶여 있다. **개발용 테스트 빌드가 system32 에 그대로
설치된 것**으로 보인다. 출시판은 argv 를 조립했을 개연성이 높으나 이 바이너리로는
확인 불가 — NOT VERIFIED.

## [18] MFT 목록의 함정 — 앞선 검색은 무효였다 — VERIFIED

`docs/research/_img2011_files.md` 는 전수 목록이 **아니다.**
생성 스크립트(`scratchpad/ntfs_mft.py`)의 필터:

```python
KEYS = ("azrok", "funitto", "starmaru", "mooondal", "hansol",
        "아즈로크", "퍼니또", "별마루", "마루몽")
```

**경로에 이 키워드가 없으면 목록에 아예 실리지 않는다.**
→ `JSStarter.ocx`, 일반 `*.cab`, `occache` 항목은 **애초에 나타날 수 없다.**

그러므로 이 파일에 대한 `.ocx/.cab/.inf/JSStarter` 검색 결과
(`AzrokStarter.ocx` + `.inf` 2건뿐)는 **아무것도 증명하지 못한다.**
"덤프에 다른 OCX 가 없다"의 근거로 쓰면 안 된다. — VERIFIED (스크립트 원문)

확인된 부수 사실: `AzrokStarter.ocx` 의 MFT 기록 타임스탬프는 **2006-08-30 22:39**,
`.inf` 는 2006-08-30 22:54. 2011년이 아니라 **2006년 파일**이다. — VERIFIED

→ 키워드를 확장한 2차 MFT 스캔과 이미지 전체 원시 바이트 스캔을 별도로 실행 중.

## [19] ★ 2차 MFT 스캔 — **우리 빌드용 컴포넌트 3종을 찾았다** — VERIFIED

확장자(`.ocx/.cab/.inf`)와 경로 키워드로 다시 스캔(MFT 120,573 레코드, 2,013 hit).
`WINDOWS\Downloaded Program Files\` 에서:

| 파일 | 크기 | 수정시각 | MFT# | 상태 |
|---|---|---|---|---|
| `AzrokStarter.ocx` | 36,864 | 2006-08-30 22:39 | 55103 | 정상 |
| `AzrokStarter.inf` | 551 | 2006-08-30 22:54 | 55104 | 정상 |
| **`PlazaStarter.ocx`** | **36,864** | **2006-09-18 16:13** | **32641** | 정상 |
| **`PlazaInstaller.inf`** | **554** | **2006-09-18 16:18** | **32642** | 정상 |
| **`WINDOWS\system32\PlazaInstaller.exe`** | **684,118** | **2006-09-18 16:11** | **32640** | 정상 |

**`Plaza` 는 `_img2011_files.md` 의 KEYS 에 없어서 지금까지 안 보였던 것**이다([18]).
우리가 복원 중인 클라이언트가 바로 `Azrok_Plaza` 이므로 **이쪽이 본체**다.
3개 모두 MFT 추출로 확보했다.

`Downloaded Program Files` 전체에 다른 아즈로크 관련 OCX 는 없다.
`JSStarter.ocx` 는 이미지 어디에도 **존재하지 않는다.** — VERIFIED (전수 MFT)

## [20] PlazaInstaller.inf 전문 — VERIFIED

```inf
; INF file for PlazaStarter.ocx

[version]
signature="$CHICAGO$"
AdvancedINF=2.0

[Add.Code]
PlazaStarter.ocx=PlazaStarter.ocx
PlazaInstaller.exe=PlazaInstaller.exe
DSETUP.dll=DSETUP.dll

[PlazaStarter.ocx]
file-win32-x86=thiscab
clsid={2C7A85FB-CAB3-40B1-B9D8-6E29456BF27B}
FileVersion=1,4,2,6
RegisterServer=yes

[PlazaInstaller.exe]
file-win32-x86=thiscab
FileVersion=1,4,2,6
Destdir=11

[DSETUP.dll]
file-win32-x86=thiscab
FileVersion=4,9,0,900
Destdir=11
```

- **CLSID `{2C7A85FB-CAB3-40B1-B9D8-6E29456BF27B}`** — Azrok판 `{6C0D5D40-...}` 와 다름.
- 버전 **1.4.2.6** (Azrok판은 1.4.2.1 → Plaza 가 더 나중 빌드).
- 세 번째 CLSID 확보. 정리:

| 컴포넌트 | CLSID |
|---|---|
| `autoLauncher.dll` (문서 22) | `{63875209-13A5-4586-8756-74FB690099CA}` |
| `AzrokStarter.ocx` v1.4.2.1 | `{6C0D5D40-BF44-45AF-B24C-2B4AD2CE30A9}` |
| **`PlazaStarter.ocx` v1.4.2.6** | **`{2C7A85FB-CAB3-40B1-B9D8-6E29456BF27B}`** |

## [21] PlazaStarter.ocx — AzrokStarter 의 리브랜딩 쌍둥이 — VERIFIED

크기 동일(36,864), 문자열 오프셋까지 **완전히 동일**. 이름만 치환:

```
0x35a8 'PLAZASTARTER.PlazaStarterCtrl.1'      0x50fc 'CPlazaStarterCtrl'
0x521c 'PlazaInstaller.exe'                    ← AzrokInstaller.exe 자리
0x5230 'GAMESESSION '  0x5258 'GAMEID '  0x5394 'GAMEIP '   ← 오프셋까지 동일
0x5214 'open'          0x5278 ' '                            ← verb/구분자 동일
에러 메시지: 'GAMEIP 파라미터 없음' / 'GAMEID ...' / 'GAMESESSION ...'  동일
```

타입라이브러리 메서드도 **`AboutBox` 하나뿐**. 임포트 DLL 목록 동일(ADVAPI32 없음).

**`WEB2INITSTART` / `INITSTART` / `JSStarter` — ASCII·UTF-16LE 전수 검색 0건.** — VERIFIED

→ [7]~[9] 의 모든 결론이 Plaza 판에도 그대로 적용된다.
   `ShellExecuteA(NULL,"open","PlazaInstaller.exe","<GAMEIP> <GAMEID> <GAMESESSION> ",NULL,1)`

## [22] ★★ PlazaInstaller.exe — **pass-through 를 한다. 체인이 닫혔다** — VERIFIED

Naver 판과 달리 **포맷 지정자가 있다**:

```
Naver판 0x418c30: " -NX 100 -NWND -PL naver -DIR 0123456789 -IP 127.0.0.1:3000"   ← 리터럴
Plaza판 0x418c30: " -NX 100 -NWND -PL %s -DIR %s -IP %s"                          ← 템플릿
```

`FUN_00405b60` (생성자) 디스어셈블, cdecl 은 **오른쪽 인자부터 push**:

```asm
00405da2  ADD ECX,0x70   ;  this+0x70 = argv[1]
00405db9  ADD ECX,0x74   ;  this+0x74 = argv[2]
00405dd0  ADD ECX,0x78   ;  this+0x78 = argv[3]
...
00405ddb  MOV EAX,[EDX + 0x70] ; PUSH  → 마지막 인자  = 3번째 %s = -IP
00405de2  MOV EDX,[ECX + 0x78] ; PUSH  → 2번째 %s              = -DIR
00405de9  MOV ECX,[EAX + 0x74] ; PUSH  → 1번째 %s              = -PL
00405ded  PUSH 0x418c30        ; " -NX 100 -NWND -PL %s -DIR %s -IP %s"
00405df5  ADD EDX,0x6c         ; PUSH  → 대상 CString
00405df9  CALL CString::Format
00405dfe  ADD ESP,0x14         ; ← push 5개 = 가변인자 3개. Naver판의 ADD ESP,8 과 대조
```

`ADD ESP,0x14` 가 결정적 증거다 — **가변인자 3개가 실제로 전달된다.** — VERIFIED

### 확정된 인자 매핑

| 웹 `<param>` | OCX 조립 위치 | Installer argv | 엔진 옵션 |
|---|---|---|---|
| `GAMEIP` | 1번째 토큰 | `argv[1]` → `+0x70` | **`-IP`** |
| `GAMEID` | 2번째 토큰 | `argv[2]` → `+0x74` | **`-PL`** |
| `GAMESESSION` | 3번째 토큰 | `argv[3]` → `+0x78` | **`-DIR`** |

Naver 판의 하드코딩 리터럴과도 정합한다: `-PL naver`(GAMEID="naver"),
`-DIR 0123456789`(GAMESESSION=10자리 자리표시자), `-IP 127.0.0.1:3000`(GAMEIP).

### 그리고 문서 22 의 WDL 엔진 변수와 맞물린다

Acknex 는 `-<name> <value>` 형태의 미지 옵션을 스크립트 가시 변수로 넘긴다.
문서 22 의 3개 변수와 이름·역할이 정확히 대응한다:

| 엔진 옵션 | WDL 엔진 변수 (문서 22) | 내용 |
|---|---|---|
| `-IP` | `engine+0x9a0` | `"IP:PORT"` 결합 문자열 |
| `-PL` | `engine+0x998` | username |
| `-DIR` | `engine+0x9ac` | authkey |

→ 문서 22 의 `"IP:PORT user auth"` 는 **위 3개 명명 옵션의 축약 서술**이었다. — INFERRED (강함)
   (엄밀한 확정은 Acknex 옵션→엔진변수 경로의 디버거 실측 필요 — NOT VERIFIED)

### 전체 체인 (이제 닫힘)

```
웹 <object><param GAMEIP/GAMEID/GAMESESSION>
  → PlazaStarter.ocx  DoPropExchange + PX_String          [VERIFIED]
  → ShellExecuteA "PlazaInstaller.exe" "IP ID SESSION "   [VERIFIED]
  → PlazaInstaller argv[1..3] → CString::Format           [VERIFIED]
  → CreateProcessA "<installdir>\Azrok.exe"
       " -NX 100 -NWND -PL <ID> -DIR <SESSION> -IP <IP>"  [VERIFIED]
  → Acknex 엔진 변수 engine+0x9a0/0x998/0x9ac             [INFERRED]
```

### `GAMEIP = 202.89.127.166:8949` 추론 — 승격 가능해졌다

> **SUPERSEDED by 195. 이 절의 결론은 철회한다.**
> 근거로 삼은 `data.dat` 은 **아즈로크 파일이 아니라 별마루(starmaru) 파일**이다:
> 실제 경로 `\Program Files\starmaru\resource_starmaru\data.dat` (MFT #34039).
> `\Program Files\Hansol\Azrok_Plaza\` 의 MFT 전체 목록에 **`data.dat` 은 존재하지 않는다.**
> 즉 형제 타이틀의 값을 아즈로크 것으로 물려받은 **오귀속**이었다.
> 아즈로크 광장 실서비스 엔드포인트는 **`58.225.56.101:4000`(2011 실측)** /
> **`222.112.161.115:4000`(2013 아카이브)** 이다. 자세한 것은 문서 195 §4·§6.
> 아즈로크에는 서버 설정파일 자체가 없고 **커맨드라인으로만** 서버를 받는다.

`-IP` 가 `GAMEIP` 를 그대로 받고, 문서 22 의 `strtok(param2,":")` 가 `IP:PORT` 를 요구하며,
`data.dat` 에서 `gameServer 202.89.127.166` / `gameServerPort 8949` 가 나왔다.
세 증거가 한 지점에서 만난다. — **INFERRED (매우 강함)**. 최종 확정은 실측 접속으로.

## [23] PlazaInstaller.exe 상수 — VERIFIED

Naver 판과 대조:

| 항목 | Plaza 판 | Naver 판 |
|---|---|---|
| 설치 경로 | `%c:\Program Files\Hansol\Azrok_Plaza` | `...\Azrok_Naver` |
| 다운로드 호스트 | **`file.funitto.com`** | `file.jr.naver.com` |
| 다운로드 경로 | **`/azrok/download_plaza/`** | `/azrok/download/` |
| 공지 | `http://file.funitto.com/azrok/notice/notice_plaza.html` | `.../notice_naver.html` |
| 홈 | `http://www.funitto.com/azrok/main.screen` | 동일 |
| 레지스트리 | `Software\Hansol\Azrok_Plaza` (HKCU) | `Software\Hansol\Azrok_Naver` |
| 실행 대상 | `<installdir>\Azrok.exe` | 동일 |
| 고정 경로 | `C:\Program Files\Hansol` (0x419150) | — |

설치 경로 문자열이 우리 `Azrok.exe` 내부의
`%c:\Program Files\Hansol\Azrok_Plaza\Screenshot\` 와 일치한다 → **같은 배포판 확정.** — VERIFIED

## [24] ★★★ `WEB2INITSTART` 는 **아즈로크와 무관하다** — 다른 게임의 JS 였다 — VERIFIED

80GB 이미지 원시 바이트 스캔(ASCII+UTF-16LE, 대소문자 무관, 4KB 중첩)으로
`WEB2INITSTART` 문자열의 **실물 위치를 찾아** 주변 페이지를 복원했다.

> **스캔 범위 주의**: 이 원시 스캔은 보고 시점에 **약 13%(9.5GB/74.5GB)만 진행**된 상태다.
> 아래 결론은 **찾아낸 것**(positive)에 근거하므로 스캔 완료와 무관하게 유효하다.
> 반면 원시 스캔을 근거로 한 **부재 주장은 아직 성립하지 않는다.**
> (파일 단위 부재는 완료된 MFT 전수 스캔이 따로 뒷받침한다 — 아래 「부수 확인」 참조.)

히트 위치: 오프셋 `0x1b072025a`(7.25GB), `0x1f986325a`(8.48GB) — **동일 내용 캐시 사본 2개**.
두 번째 사본의 출처 URL 도 확보: `http://rc.puppyred.com/inc/js/client.js`.
그 JS 를 포함한 페이지 원문:

```js
function initControl() {
    var bInit = true;
    if( initOcx.object==null ) {
        var agent = window.navigator.userAgent.toLowerCase();
        var spVer = window.navigator.appMinorVersion.toLowerCase();
        if( getCookie("HasInstallConfirm")==null ) {
            if( (agent.indexOf("windows nt 5.1") > 0 && ...) || agent.indexOf("windows nt 6.0") ) {
                if(intiOcxInatallInfoLayerVisibled != null) {
                    intiOcxInatallInfoLayerVisibled(true);
                    initOcxDown(true);
                    return;
                }
            } else {
                document.cookie = "HasInstallConfirm=yes; path=/";
                initOcxDown(true);
                document.location.reload();
            }
        }
    }
    if(bInit) {
        try {
            updateResult = document.initOcx.WEB2INITSTART(gameOcxVer,gameServerAddr, updateServer, homeUrl);
        } catch(e) {}
    }
}
```

같은 페이지의 다른 부분:

```html
<a href="http://id.hangame.com/login.nhn?nxtURL=http%3A%2F%2Fpuppyred.hangame.com%2Fservlet%2Ftrid.api.hg.HGOtpw">
<img src="http://image.puppyred.com/image/layout/bt_loginBottom.gif" alt="로그인" />
...
window.open("/servlet/trid.chat.SearchBeginnerServlet?type=0","searchBeginner",...)
...
<script type="text/javascript">
    writeInitOcx("initOcx");
</script>
</body></html>
```

### 결정적 카운트 — VERIFIED
두 캐시 사본 각각의 `WEB2INITSTART` 호출부를 중심으로 **±1.5MB(3MB) 영역**의 키워드 출현 횟수:

| 키워드 | 사본 1 (7.25GB) | 사본 2 (8.48GB) |
|---|---|---|
| `azrok` | **0** | **0** |
| `funitto` | **0** | **0** |
| `starmaru` | — | **0** |
| `puppyred` | 6 | 6 |
| `hangame` | 2 | 0 |
| `trid.` | — | 4 |

→ **이 JS 는 「퍼피레드(PuppyRed)」/한게임 페이지의 것이다. 아즈로크와 아무 관계가 없다.**

### 임무 전제의 최종 정정
브리핑의 *"IE 캐시에서 호출부 JS 원문을 확보했다 … `AzrokStarter.ocx` 가 바로 이 `initOcx` 다"*
는 **오귀속(misattribution)** 이었다. 디스크 이미지의 캐시 조각에 다른 게임(퍼피레드)의 페이지가
섞여 있었을 뿐이다(`trid.*` 서블릿 = 퍼피레드 운영사).

**따라서 「세 번째 아즈로크 컴포넌트」는 애초에 존재하지 않는다.** — VERIFIED
`document.initOcx` 는 퍼피레드의 ActiveX 이고, `writeInitOcx("initOcx")` 라는
JS 함수가 그 `<object>` 태그를 동적으로 써넣는다. 아즈로크 웹→게임 체인은
[22] 에서 이미 완결됐다. **더 찾을 빈 칸이 없다.**

### 부수 확인
- `JSStarter` 히트는 단 1건, 그마저 `AzrokStarter.inf` 의 주석
  (`; INF file for JSStarter.ocx`)일 뿐 — 리브랜딩 템플릿의 흔적이지 실제 파일이 아니다.
- MFT 전수(120,573 레코드)에 `JSStarter.ocx` 파일은 **없다.** — VERIFIED
- 이미지 내 `AzrokStarter` 히트 5건은 모두 확보한 OCX/INF 및 그 MFT 파일명 레코드.

## [25] 아즈로크 웹→게임 체인 — 최종 정리 (VERIFIED)

```
웹 페이지  <object classid="clsid:2C7A85FB-CAB3-40B1-B9D8-6E29456BF27B"
                  codebase="...PlazaInstaller.cab#version=1,4,2,6">
             <param name="GAMEIP"      value="<IP>:<PORT>">
             <param name="GAMEID"      value="<유저ID>">
             <param name="GAMESESSION" value="<인증키>">
           </object>
   │
   │  PlazaStarter.ocx :: CAzrokStarterCtrl::DoPropExchange  (JS 호출 아님)
   │    게이트: RAM≥110MB, 디스크≥600MB, DirectX≥9, OS≥Win98SE
   │    PX_String ×3 → 공백으로 연결
   ▼
ShellExecuteA(NULL, "open", "PlazaInstaller.exe",
              "<GAMEIP> <GAMEID> <GAMESESSION> ", NULL, SW_SHOWNORMAL)
   │
   │  PlazaInstaller.exe :: argv[1]→+0x70, argv[2]→+0x74, argv[3]→+0x78
   │    HKCU\Software\Hansol\Azrok_Plaza\InstallPath 기록
   │    필요 시 file.funitto.com/azrok/download_plaza/ 에서 Setup.zip 다운로드
   │    CString::Format(" -NX 100 -NWND -PL %s -DIR %s -IP %s", +0x74, +0x78, +0x70)
   ▼
CreateProcessA("<installdir>\Azrok.exe",
               " -NX 100 -NWND -PL <GAMEID> -DIR <GAMESESSION> -IP <GAMEIP>",
               ..., lpCurrentDirectory="<installdir>")
   │
   ▼
Acknex 엔진 → engine+0x9a0 (IP:PORT) / +0x998 (user) / +0x9ac (auth)   [INFERRED]
```

**우리 런처가 놓친 단계는 없다.** 마지막 화살표의 값을 직접 주입하고 있으며,
그 위 단계들은 값을 변형하지 않는다(사양검사는 게이트일 뿐, 레지스트리는 기록 전용).

**새로 확보된 실행 가능한 사실**:
1. 원본 커맨드라인 문법 — `-NX 100 -NWND -PL <user> -DIR <auth> -IP <ip:port>`
2. `-NX 100` 이 원본 기본값(문서 62 의 `-NX 200` 실험과 대조 기준선)
3. `-NWND` 라는 미조사 옵션의 존재
4. `GAMESESSION`(=`-DIR`)이 서버가 발급해야 할 인증키 슬롯

## 미해결 (갱신)

1. ~~`WEB2INITSTART` 세 번째 컴포넌트~~ — **종결.** 퍼피레드/한게임 JS 였다([24]).
2. `DSETUP.dll` — MFT 전수에 없음. DirectX 재배포 표준 파일이라 복원 가치 낮음.
3. ~~Plaza 빌드에서 `-PL` / `-DIR` / `-NWND` / `-IP` 실효성 — **x32dbg 실측 필요.** 최우선.~~
   **✅ 종결 2026-07-19 — VERIFIED (문서 138).** BoxedWine 실행에서 세 플래그 모두 유효,
   서버 로그인 수신까지 도달. 이 형태가 WDL 주입 경쟁도 원인째 제거한다.
4. Acknex 명명 옵션 → `engine+0x9a0/0x998/0x9ac` 매핑 — 여전히 INFERRED.
   플래그가 **먹는다**는 것은 확정됐으나, 그 값이 저 세 오프셋에 실린다는 경로는
   아직 직접 관측되지 않았다(서버 접속 성공은 강한 정황이지만 오프셋 증명은 아니다).

---

## 확보한 원본 파일 (프로젝트에 보존됨)

MFT 추출로 복원해 원래 경로 구조 그대로 저장했다.

| 파일 | 크기 | MFT# | 출처 경로 |
|---|---|---|---|
| `_img2011_extracted/WINDOWS/Downloaded Program Files/PlazaStarter.ocx` | 36,864 | 32641 | 동일 |
| `_img2011_extracted/WINDOWS/Downloaded Program Files/PlazaInstaller.inf` | 554 | 32642 | 동일 |
| `_img2011_extracted/WINDOWS/system32/PlazaInstaller.exe` | 684,118 | 32640 | 동일 |

(기존 `AzrokStarter.ocx` / `AzrokStarter.inf` / `AzrokInstaller.exe` 는 이미 있었음.)

**우리 복원 대상은 `Azrok_Plaza` 이므로 Plaza 3종이 본체이고 Azrok_Naver 3종은 대조군이다.**

---

## [26] ★ `PlazaInstaller.exe` 제어 흐름 — **판정: (c) 위험. 체인에 끼우지 마라** — VERIFIED

대상: `docs/research/_salvage/binaries/PlazaInstaller.exe` (684,118 B, MD5 `924dcc6fb574072d92910f5c93f429c3`)
방법: 정적 분석만. **실행하지 않았다.** `analyzeHeadless` + `DumpAll.java` (임시 프로젝트 `ghinst2`).

### 결론 요약
1. **다운로드는 무조건 탄다.** `UpdateInfo` HTTP GET 이 실패하면 `AfxMessageBox` + `EndDialog(2)` 후
   **`CreateProcessA` 에 도달하지 못한다.** 원본 서버가 죽은 지금 이 바이너리는 게임을 띄울 수 없다.
2. **기존 설치를 감지해 건너뛰는 분기는 없다.**
3. **레지스트리를 읽는 것 자체가 불가능하다** (`RegQueryValueExA`/`RegOpenKeyExA` 미임포트).
4. **실행 경로 위에 재귀 디렉터리 삭제가 있다.**

---

### (1) 임포트 테이블 — 부재가 곧 증거 — VERIFIED

`ADVAPI32.dll` 은 **이름 임포트 3개뿐**이다(ordinal 은닉 불가):
```
RegCreateKeyExA   RegSetValueExA   RegCloseKey
```
→ **`RegQueryValueExA` 도 `RegOpenKeyExA` 도 없다. 레지스트리를 읽는 코드가 존재할 수 없다.**
질문의 *"`HKCU\...\Azrok_Plaza\Version` 을 읽어 비교하는가"* 에 대한 답: **아니오, 불가능.** — VERIFIED

오히려 `Version` 은 **빈 값으로 쓰기만** 한다:
```c
RegSetValueExA(hKey, "Version", 0, REG_SZ, (BYTE*)0, 0);   // 길이 0
```

`KERNEL32` 의 파일계 임포트(전수):
```
CreateFileA WriteFile SetFilePointer GetFileSize CreateFileMappingA MapViewOfFile UnmapViewOfFile
FindFirstFileA FindNextFileA FindClose GetFileAttributesA SetFileAttributesA
CreateDirectoryA RemoveDirectoryA DeleteFileA SetCurrentDirectoryA GetWindowsDirectoryA
CreateThread CreateProcessA
```
**`WININET.DLL` / `URLMON.DLL` 임포트는 없다** — 그러나 지적받은 대로 이것만으로 단정할 수 없었다.

### (2) MFC 네트워크 실호출 — **한다** — VERIFIED

MFC42 는 227개 **전부 ordinal 임포트**이고, `MFC42.DLL`(SysWOW64) 자체가
6,939개 함수 중 이름이 6개뿐(전량 NONAME)이라 **DLL 에서 ordinal 맵을 얻을 수 없었다.**
→ ordinal 이름에 의존하지 않고 **디컴파일 본문**을 근거로 삼았다. Ghidra 가 시그니처로 클래스를 복원했다:

`FUN_00404270` (563 B, 다운로드 함수) 본문:
```c
CInternetSession local_30;
CHttpConnection *local_34;
CHttpFile *local_38;
CInternetSession::CInternetSession(local_30, "JSInstaller", 1, 0, NULL, NULL, 0);
...
local_44 = CreateFileA(param_2, 0x40000000, 3, NULL, 2, 0x80, NULL);   // 로컬 파일 생성
...   WriteFile(local_44, local_448, local_44c, &local_48, NULL);      // 1024B 청크 수신 루프
```
바이너리에 존재하는 MFC 네트워크 심볼 전수:
`CInternetSession`, `~CInternetSession`, `GetHttpConnection`, `GetFtpConnection`,
`OpenRequest`, `SendRequest`, `AddRequestHeaders`, `QueryInfo`, `QueryInfoStatusCode`, `Close`,
`CFtpConnection::CreateDirectoryA`

→ **HTTP(그리고 FTP)를 실제로 쓴다. User-Agent 는 `"JSInstaller"`.** — VERIFIED

### (3) 실제 제어 흐름 — `FUN_00406d10` 이 전부를 가른다 — VERIFIED

`CreateProcessA` 를 가진 함수는 `FUN_00406a90` 하나이고, **그 유일한 호출자가 `FUN_00406d10`**(1,676 B)이다.

```c
FUN_00406d10():
    net.host = DAT_0041e7fc;                       // "file.funitto.com"
    CFileFind ff;
    if (CFileFind::FindFile(&ff, DAT_0041e814) == 0)   // "%c:\Program Files\Hansol\Azrok_Plaza"
        FUN_00406860();                            // ← 없으면 "만든다" (mkdir -p). 건너뛰기 아님
    SetCurrentDirectoryA(installdir);              // 이후 모든 상대경로가 설치폴더 기준
    net.path = DAT_0041e80c;                       // "/azrok/download_plaza/"

    local_30 = FUN_00404270("UpdateInfo", "UpdateInfo");   // ★ HTTP GET — 무조건 실행

    if (local_30 == 0) {                           // 수신 성공
        DeleteFileA("Setup.zip");                  // ← 설치폴더 내 삭제
        local_38 = FUN_00404e30("UpdateInfo", "Setup.zip", DAT_0041e7dc);   // 파싱/비교
        local_3c = FUN_00404eb0(net);              // 받아야 할 개수
        DeleteFileA("UpdateInfo");                 // ← 설치폴더 내 삭제
        if (local_3c == 0) { FUN_00406a90(); ... } // (A) 받을 것 없음 → 실행
        else {
            do { ...다운로드 루프(GetTickCount/Sleep/진행률)...
                 if (local_54 == 1) { AfxMessageBox(...); EndDialog(0); return 0; }  // 실패
                 if (local_54 == 2 && local_38 == 2) {
                     if (FUN_004073d0()) FUN_00406a90();      // (B) 압축해제 후 실행
                     else { AfxMessageBox(...); EndDialog(0); }
                     return;
                 }
            } while (local_3c != 0);
            FUN_00406a90();                        // (C) 루프 완주 후 실행
        }
    } else {                                       // ★ 수신 실패
        CString msg; ...Format(msg, "UpdateInfo"...);
        AfxMessageBox(msg, 0, 0);
        CDialog::EndDialog(DAT_0041e818, 2);
        return 0;                                  // ← CreateProcessA 에 도달하지 않음
    }
```

**`FUN_00406a90()` 호출 지점 (A)(B)(C) 세 곳이 전부 `local_30 == 0` 블록 안에 있다.**
`UpdateInfo` 수신이 실패하면 실행 경로가 **하나도 남지 않는다.** — VERIFIED

`GetFileAttributesA` 는 압축해제 내부(`FUN_0040a240`)에서만 쓰이고 설치 감지 게이트가 아니다.
`CFileFind::FindFile` 로 설치폴더를 보긴 하지만 **없으면 생성**할 뿐, 다운로드를 건너뛰지 않는다. — VERIFIED

### (4) ★ 파괴적 동작 — 실행 경로 위에 **재귀 디렉터리 삭제**가 있다 — VERIFIED

호출 사슬:
```
FUN_00406d10  →  FUN_00406a90 (launcher)
                   ├─ FUN_00406c60()        ← 맨 첫 줄에서 호출됨. CreateProcessA 보다 먼저
                   │    ├─ FUN_00407ab0()   ← ★
                   │    └─ RegCreateKeyExA(HKCU, "Software\Hansol\Azrok_Plaza") + InstallPath/Version 쓰기
                   ├─ FUN_00407810()        ← 바로가기 생성 (\azrok.ico, main.screen)
                   └─ CreateProcessA(installdir\Azrok.exe, " -NX 100 -NWND -PL %s -DIR %s -IP %s", cwd=installdir)
```

`FUN_00407ab0` 전문:
```c
void FUN_00407ab0(void) {
    CHAR target[260]; char windir[260];
    GetWindowsDirectoryA(windir, 0xff);
    if ((windir[0] != 'c') && (windir[0] != 'C')) {
        wsprintfA(target, "C:\\Program Files\\Hansol");
        FUN_00407b50(target);                  // ← 재귀 삭제
    }
    return;
}
```

`FUN_00407b50` (665 B) 은 전형적 재귀 트리 삭제기다 — 자기 자신을 호출하며:
```
FindFirstFileA(dir "\\*.*") → 하위 재귀
SetFileAttributesA(path, 0x80)   // FILE_ATTRIBUTE_NORMAL 로 풀고
DeleteFileA(path)
RemoveDirectoryA(dir)
```

**즉 Windows 가 C: 가 아닌 드라이브에 설치된 시스템에서는,
게임 실행 직전에 `C:\Program Files\Hansol` 트리 전체(= `Azrok_Plaza` 포함)를 지운다.** — VERIFIED

사용자 실기는 Windows 가 C: 이므로 이 분기는 **타지 않는다**. 그러나
**안전 마진이 "시스템 드라이브 문자" 하나뿐**이며, 이 검사는 실행 시점에 매번 수행된다. — VERIFIED

### 그 밖의 파괴적 호출 (전수)
| 위치 | 동작 | 도달 조건 |
|---|---|---|
| `FUN_00406d10` | `DeleteFileA("Setup.zip")`, `DeleteFileA("UpdateInfo")` (설치폴더 내) | UpdateInfo 수신 성공 시 |
| `FUN_00407ab0` → `FUN_00407b50` | **`C:\Program Files\Hansol` 재귀 삭제** | 실행 경로. windir 이 C: 가 아닐 때 |
| `FUN_004073d0` → `FUN_004076a0` | `SetFileAttributesA(...,0x80)` + `DeleteFileA` — **압축 해제 중 기존 파일 덮어쓰기** | 다운로드 완료 후 |
| `FUN_00404aa6` | `SetFileAttributes` + `DeleteFile` + `CreateFile` | 압축 해제 내부 |
| `FUN_0040a850`, `FUN_0040aaf0`, `FUN_0040a0e0` | `CreateDirectoryA`, `SetFileAttributesA` | 압축 해제 내부 |

### (5) 최종 판정 — **(c) 위험**

**세 가지가 동시에 성립하므로 (b) 조건부 안전으로도 낮출 수 없다:**

1. **효용이 0이다.** 원본 다운로드 서버가 죽었으므로 `FUN_00404270` 이 실패 →
   `AfxMessageBox` + `EndDialog(2)` → 실행 안 됨. **체인에 끼워도 게임이 안 뜬다.** — VERIFIED
2. **실행 경로에 재귀 삭제가 있다.** 지금 이 PC 에서는 안 타지만, 방어가 드라이브 문자 하나다. — VERIFIED
3. **가짜 서버를 세워 1번을 우회하면 오히려 더 위험해진다.** `UpdateInfo` 를 받아주는 순간
   `DeleteFileA("Setup.zip")` → 다운로드 → `FUN_004073d0` 압축 해제가 **현재 설치본 위에 덮어쓴다.**
   우리 분석 대상인 `Program Files\Hansol\Azrok_Plaza` 가 훼손된다. — VERIFIED

### 권고 — 인스톨러를 빼고 체인을 재현하라
`PlazaInstaller.exe` 가 **최종적으로 하는 일은 이미 전부 알려져 있다**([22][23]):
```
RegCreateKeyExA(HKCU, "Software\Hansol\Azrok_Plaza")  InstallPath=<설치경로>, Version=""
바로가기 생성
CreateProcessA("<설치경로>\Azrok.exe",
               " -NX 100 -NWND -PL <GAMEID> -DIR <GAMESESSION> -IP <GAMEIP>",
               cwd="<설치경로>")
```
→ **웹 로그인 동선 재현에는 `PlazaStarter.ocx` 까지만 쓰고, 인스톨러 자리에는
   위 `CreateProcessA` 를 그대로 흉내내는 얇은 대역 실행기를 두는 것이 옳다.**
   OCX 가 넘기는 것은 공백 구분 3-튜플이 전부이므로 대역 실행기의 입력 계약은 이미 확정돼 있다.

### 미확인 (정직하게 남긴다)
- `FUN_00404270` 이 HTTP 실패를 **정확히 어떤 반환값**으로 표현하는지(타임아웃 vs DNS 실패 vs 404)는
  세부 추적하지 않았다. 다만 `local_30 != 0` 이면 무조건 `EndDialog` 이므로 **판정에 영향이 없다.** — NOT VERIFIED (무관)
- `FUN_00406750`(261 B, 호출자 없음)도 `FUN_00404270`/`FUN_00406860` 을 부르는 **두 번째 다운로드 경로**로 보이나,
  정적 호출자가 없어(스레드/콜백 가능성) 도달성을 확정하지 못했다. — NOT VERIFIED
  → 이 미확인 경로의 존재도 (c) 판정을 강화하는 쪽이다.
