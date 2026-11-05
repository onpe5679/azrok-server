# 2011.img 추출 아티팩트 분석 — 발견 로그

원본: `D:\2011.img` (사용자 본인의 2011년 PC 하드 덤프) → `docs/research/_img2011_extracted/` (281 파일)
매니페스트: `_img2011_diff.md`
분석 시작: 2026-07-18 (artifact-probe)

각 항목 등급: **VERIFIED**(파일 직접 열어 확인) / **INFERRED**(추론) / **NOT VERIFIED**(추가 확인 필요)

> 이 문서는 append-only 로그다. 발견 즉시 추가한다.

---

## 배치 1 — 웹 아티팩트 / URL / 버전 / 서버 주소

### F1. 원본 서비스 URL 체계 확정 — VERIFIED

`.url` 바로가기 4개와 IE 캐시 HTM 2개를 직접 열어 확인:

| 출처 파일 | URL |
|---|---|
| 바로가기(.url) 파일 — 파일명은 공개본에서 뺐다 | `http://www.funitto.com/azrok/main.screen` |
| 바로가기(.url) 파일 — 파일명은 공개본에서 뺐다 | `http://funitto.jaeminara.co.kr/intro.screen` |
| `login_funitto_do[1].htm` (IE 캐시, DEL 복구) | JS 리다이렉트 → `http://funitto.jaeminara.co.kr/azrok/main.screen` |
| `funitto_jaeminara_co_kr[1].htm` (IE 캐시, DEL 복구) | `location.href="/intro.screen"` + `http://file.funitto.com/acecounter/funitto_acecounter_pro.js` |

(개인 PC 사용 흔적 목록은 공개본에서 뺐다)

**확정 사실:**
- 게임 진입점은 `{host}/azrok/main.screen` 이며 **`www.funitto.com` 과 `funitto.jaeminara.co.kr` 두 호스트가 같은 경로 체계를 공유**했다. 후자가 원본/내부 호스트, 전자가 대외 서비스 도메인으로 보인다 (INFERRED).
- 파일명 `login_funitto_do` = 원본 URL `login_funitto.do`. 즉 포털은 **`.do`(Struts 계열) + `.screen`** 확장자를 쓰는 **Java 웹 프레임워크**다 (INFERRED, 강함).
- `login_funitto.do` 의 실제 응답 본문은 **137바이트 JS 리다이렉트뿐**이다. 로그인 폼/파라미터는 이 캐시에 없다.
- `file.funitto.com` = 정적 파일/스크립트 CDN 호스트. `acecounter` = 당시 국내 웹로그분석 서비스(에이스카운터).
- 서브도메인 `club.funitto.jaeminara.co.kr` 존재 (쿠키 F2 참조).

**아즈로크 게임서버 프로토콜에 대한 정보는 이 웹 아티팩트에 없다.** 웹은 포털/런처 계층이고 게임 소켓과는 별개다.

### F2. 퍼니또 쿠키 3개 — VERIFIED (그러나 세션 정보 없음)

(개인 PC 사용 흔적 목록은 공개본에서 뺐다)

- 세션 쿠키(`JSESSIONID` 등)는 복구되지 않았다. 로그인 세션 구조는 이 아티팩트로 확정 불가 (NOT VERIFIED).
- 서브도메인 `club.funitto.jaeminara.co.kr` 이 실재했음이 확정됐다 — 커뮤니티/클럽 서브사이트 (INFERRED).

### F3. `starmaru_progressbar[1].htm` 은 HTML 이 아니다 — VERIFIED (부정 결과)

**우선순위 1로 지목된 파일이지만, 내용이 HTML 이 아니다.**

- 첫 바이트: `90 90 90 90 90 8b ff 55 8b ec 83 ec 48 a1 98 b3 fe 43 33 c5 89 45 fc ...`
  = x86 `nop×5 / mov edi,edi / push ebp / mov ebp,esp / sub esp,0x48` + `/GS` 보안 쿠키 로드(`mov eax,[0x43FEB398]`).
- 파일 전체 3,055바이트에 **6자 이상 ASCII 문자열이 0개**다. 순수 기계어다.
- 참조 전역 주소대는 `0x43F6xx~0x43F9xx`, 이미지 베이스 0x400000 대의 MSVC 빌드.

**결론: 이 파일은 삭제된 MFT 레코드에서 이름만 복구되고, 데이터 클러스터는 이미 다른 실행 파일에 재할당된 상태였다.** 파일명과 내용이 불일치한다. 서버 URL·패치 프로토콜·종료 안내 문구를 여기서 얻을 수 없다.

- 같은 디렉터리(`_broken_reference_0xaaa7#6_`)의 `starmaru[1].css` 2,604B 는 **정상 복구**됐다(순수 CSS, 돋움 12px, 오렌지 `#FF6C00` 테마). 즉 같은 참조 묶음이라도 클러스터별로 복구 성패가 갈렸다.
- CSS 에도 게임 프로토콜 정보는 없다. 별마루 웹 페이지의 스킨일 뿐이다.

### F4. `Azrok.txt` 의 정체 = 크래시 로그 (append-only) — VERIFIED

프로젝트 루트 `Azrok.txt`(129,651 B)와 2011 원본(994 B)을 둘 다 열어 직접 대조:

- **둘 다 같은 포맷의 예외 덤프**다. `//===` 구분선 + `Exception code` + `Fault address` + 레지스터 + 콜스택(빈) + Global Variables.
- 즉 **`Azrok.txt` 는 설정 파일이 아니라 클라이언트가 크래시할 때마다 append 하는 크래시 로그**다. 우리 사본이 큰 것은 우리가 돌리며 크래시를 누적시켰기 때문이 맞다. **원본 초기 내용은 "빈 파일" 이 아니라 "크래시 1건"** 이다.
- 2011 원본의 유일한 레코드:
  ```
  Exception code: C0000005 ACCESS_VIOLATION
  Fault address:  00654453 02:0017D453 H:\Program Files\Hansol\Azrok_Plaza\Azrok.exe
  CS:EIP:0023:00654453   EAX:00000000  EDX:7EFEFEFF  ESI:00000002  EDI:00184A9E
  ```
- **`0x00654453` 는 상용 서비스가 살아있던 2011년에, 정상 클라이언트가 정상 서버에 붙은 상태에서 발생한 진짜 크래시 주소다.** 우리 실행 환경에서 나온 크래시(예: `0x005E7CE5`)와 구분해야 한다. `EDX:7EFEFEFF` 는 전형적인 문자열 스캔(`strlen`/`memchr`) 센티넬이므로 **널 포인터 문자열 처리 크래시** 로 보인다 (INFERRED).
- 부수 사실: 2011년 사용자 PC 의 설치 드라이브는 **`H:\Program Files\Hansol\Azrok_Plaza`** 였다 (VERIFIED). 프로젝트가 `C:`/`B:` 경로를 가정하는 부분과 무관하지만, 원본 설치가 드라이브 레터에 종속되지 않았다는 증거다.

### F5. 원본 클라이언트 버전 = `Ver. PLAZA 1.3.1` — VERIFIED

`Program Files/Hansol/Azrok_Plaza/Ver.txt` (16 B) 전문: `Ver. PLAZA 1.3.1`

2011-05 시점 서비스 종료 직전의 최종 패치 레벨로 보인다 (INFERRED). 우리 사본의 `Ver.txt` 와 크기가 같으므로(diff 목록에 없음) **우리 설치본도 동일한 1.3.1 이다** (VERIFIED — diff 매니페스트가 크기 불일치 1건=Azrok.txt 만 보고).

### F6. ★ HansolFunnyMini 의 원본 서버 IP/포트 — VERIFIED

`hansol/HansolFunnyMini/Server.dat` (30 B) 전문: `NTguMjI1LjU2LjEwMSwgODk0OQ==`

**base64 디코드 → `58.225.56.101, 8949`**

- 이것은 **아즈로크가 아니라 한솔 퍼니미니(HansolGameKing)의 게임 서버 주소**다. 혼동 금지.
- 그러나 **같은 발행사(한솔)가 게임 서버 접속 정보를 "base64 인코딩된 `IP, PORT` 평문"으로 로컬 `.dat` 에 둔다**는 패턴이 확인됐다. 아즈로크에도 유사 파일이 있는지 재확인할 근거가 된다 (아즈로크는 커맨드라인/WDL 경로가 이미 확정).
- `58.225.56.101` 은 당시 한국 IP 대역. 현재 살아있지 않으며, 이 프로젝트는 접속을 시도하지 않는다.
- 부수: `Log.txt` 는 `GPackage3::Open() 파일 오픈 실패` — 마지막 실행이 `.gp3` 로드 실패로 끝났다. `Track.dat` 는 BGM 트랙 목록(`FantasyTrack2/Halloween2/Random2/Random4`).

### F7. AzrokStarter ActiveX 설치 매니페스트 — VERIFIED

`WINDOWS/Downloaded Program Files/AzrokStarter.inf` 전문 확인:

- 헤더 주석: `; INF file for JSStarter.ocx` ← **원래 이름이 `JSStarter.ocx`** 였고 아즈로크용으로 리브랜딩됐다 (INFERRED, 강함). `JS` = 이미 알려진 `CJSLogic` 클래스 접두사와 일치한다.
- CLSID: `{6C0D5D40-BF44-45AF-B24C-2B4AD2CE30A9}`
- FileVersion: `1,4,2,1` (OCX 및 `AzrokInstaller.exe` 동일)
- CAB 동봉 3종: `AzrokStarter.ocx`, `AzrokInstaller.exe`(Destdir=11=system32), `DSETUP.dll`(4,9,0,900 = DirectX 9 설치 지원)
- `RegisterServer=yes`

**웹 → 게임 기동 경로: 브라우저가 `main.screen` 에서 이 ActiveX 를 로드 → `AzrokInstaller.exe` 가 system32 에 설치 → OCX 가 클라이언트를 기동.** (INFERRED — OCX 바이너리 자체 분석은 별도 ocx-probe 담당)


---

## 배치 2 — 설치본 대조 (우선순위 4 종결)

### F8. ★ 추출된 `starmaru` 121개 파일 전부가 우리 사본과 **바이트 단위 완전 일치** — VERIFIED

우선순위 4의 전제("삭제 복구된 `.uit` 112개 + `.skn` 2개는 패치로 교체된 구버전일 것")를 직접 검증했다.
`_img2011_extracted/Program Files/starmaru/**` 전체를 프로젝트 `starmaru/**` 와 1:1 바이트 비교:

```
SUMMARY {'IDENTICAL': 121} total 121
```

- **IDENTICAL 121 / SIZE_DIFF 0 / BYTE_DIFF 0 / MISSING 0.**
- 즉 `userInterface2D` 56개, `goods2D` 53개, `character3D` 4개, `skin001/002.skn`, `data.dat`, `version.dat`, `license.txt`, `bar/bg/cancel.uit` 가 **모두 현행 사본과 동일**하다.

**결론: 이것들은 구버전 에셋이 아니다. 보존 가치는 0이다.** MFT 에서 삭제 표시된 레코드였던 것은 사실이나, 내용은 우리가 이미 가진 것과 같다. (삭제 표시 자체는 언인스톨/재설치 흔적으로 설명된다 — INFERRED)

### F9. 게임 데이터 파일도 전부 일치, 유일한 차이는 크래시 로그 — VERIFIED

`_img2011_extracted/Program Files/Hansol/Azrok_Plaza/**` 대조:

| 파일 | 결과 |
|---|---|
| `Azrok.dat` (8188 B) | IDENTICAL |
| `init.csv` (1090 B) | IDENTICAL |
| `test.csv` (4266 B) | IDENTICAL |
| `Ver.txt` (16 B) | IDENTICAL |
| `Data\Plaza\bee.npc` (1337 B) | IDENTICAL |
| `Data\Space\Plaza\Skin1.txt` (24 B) | IDENTICAL |
| `Azrok.txt` | **DIFFERS** (994 vs 129,651 — F4 크래시 로그) |

**우리 설치본은 2011년 원본과 동일한 패치 레벨(PLAZA 1.3.1)의 무손상 사본임이 독립 증거로 확정됐다.** `init.csv`/`Azrok.dat` 기반의 기존 결론(문서 11/15/57b/71)은 원본과 동일한 바이트에서 나온 것이므로 안전하다.

### F10. `version.dat` = 패처 매니페스트 — 포맷 확정, 다만 홀수 오프셋 스크램블 존재

> **PARTIALLY SUPERSEDED by 661.** 아래 "스크램블"은 의도된 처리가 아니라 3/29 덤프 때 생긴 전송 손상(홀수 오프셋 비트 0x02)이다. 같은 패턴이 `Data\` 721개에도 있다. 레코드 포맷과 `license.txt` 개발사 조각은 유효하다. See `tooling/661_HDD_IMAGE_BIT9_TRANSFER_DAMAGE_20261105.md`.

`starmaru/version.dat` (16,061 B) 구조를 직접 디코드:

**레코드 = `[파일명 ASCII][0x00][크기 u32 LE][MD5 16B]` 가변길이 연속.**

검증 근거(VERIFIED): 오프셋 13 의 레코드가 `bar.uit\0` + `04 02 00 00` = **516** 이고, 실제 `starmaru/bar.uit` 는 **정확히 516 바이트**다. 다음 레코드명(`bg.uit`)이 MD5 16바이트 뒤 오프셋 41 에서 시작하는 것도 일치한다.
파일 선두 `open.gxg\0 fe 00 00 00` 는 패키지 헤더로 보인다 (INFERRED).

**스크램블 (부분 규명, 일부 UNRESOLVED):**
- 바이트 불일치는 **홀수 오프셋에서만, 오직 비트 `0x02` 에서만** 발생한다. 짝수 오프셋은 100% 원본 그대로다 (실제 파일명 270개로 정렬 검증: 짝수 오프셋 5,322 샘플 중 비트1 보존).
- 홀수 오프셋 비트1 이 0 인 바이트 비율: `version.dat` **10.2%**, `license.txt` **11.5%**. 반면 짝수 오프셋은 각각 53.9% / 55.5%, 그리고 같은 폴더의 `open.exe` 48.8/48.8%, `d3dx9_36.dll` 64.2/63.9%, `bar.uit` 60.5/59.3% 로 **완벽히 대칭**이다.
  → **이 두 파일에만 적용된 처리다. 디스크/이미지 손상이 아니다** (손상이라면 같은 영역의 다른 파일도 비대칭이어야 한다). VERIFIED.
- 다만 방향이 일정하지 않다: 파일명 구간에서는 비트1 이 **set**(`a→c`, `e→g`, `m→o`, `t→v`, `u→w`)되지만, `bar.uit` 의 MD5 구간에서는 **clear**(`36→34`, `13→11`)된다. 단일 상수 규칙으로 가역 복원이 불가능하다.
- `license.txt` 에 홀수 오프셋 비트1 을 일괄 clear 해 CP949 로 디코드하면 **약 70% 만 정상 한국어**로 읽힌다(예: "별마루 아즈로크", "최종 사용자 사용권 계약서", "www.funitto.com" 은 복원되나 인접 음절은 깨짐). → 상수 규칙 복원은 손실적이다. VERIFIED.

**등급: 스크램블의 정확한 키/규칙은 NOT VERIFIED (미해결).**
**실무적 영향은 없다.** `version.dat` 은 우리 사본과 바이트 동일(F8)하고, 우리는 그것이 검증하려는 대상 파일 270개를 이미 전부 온전히 갖고 있다. 이는 게임 서버 프로토콜이 아니라 **런처(별마루) 패처의 파일 무결성 매니페스트**다.

**부수 확정(VERIFIED):** `license.txt` 복원 조각에서 —
- 제품 정식 명칭 = **"별마루 아즈로크 클라이언트"** (starmaru = 별마루 = 아즈로크 제품 라인명)
- 개발사 = **(주)에이픽스튜디오**, 공식 홈페이지 = **www.funitto.com**

---

## 배치 3 — 설치 경로 / HansolFunnyMini / 복구 실패 파일

### F11. ★★ `AzrokInstaller.exe` — 별도 배포판 `Azrok_Naver` 와 다운로드 서버 확정 — VERIFIED

`WINDOWS/system32/AzrokInstaller.exe` (684,120 B) 문자열 직접 추출. 본체는 압축 페이로드라 대부분 노이즈지만, 평문 구간에서:

| 문자열 | 의미 |
|---|---|
| `http://www.funitto.com/azrok/main.screen` | 설치 완료 후 진입 URL (F1 과 일치) |
| `http://file.funitto.com/azrok/notice/notice_naver.html` | **공지 페이지** — 네이버판 전용 |
| `/azrok/download/` | **패치/설치 파일 다운로드 경로** |
| `file.jr.naver.com` | **쥬니어네이버 파일 서버** |
| `Setup.zip` | 배포 아카이브 이름 |
| `%c:\Program Files\Hansol\Azrok_Naver` | **설치 디렉터리 (네이버판)** |
| `Software\Hansol\Azrok_Naver` | **레지스트리 키 (네이버판)** |
| `D:\2006_Project\Hansol\` | 개발 빌드 경로 |
| `\Installer\Release\AzrokInstaller.pdb` | PDB 경로 |
| `%d％ 아즈로크 인스톨러` | 진행률 창 제목 |
| `%s 파일이 존재 하지 않아 종료 합니다.` | 오류 메시지 |

**새 확정 사실:**
1. **아즈로크에는 최소 두 개의 배포판이 존재했다 — `Azrok_Plaza`(우리가 가진 것)와 `Azrok_Naver`(쥬니어네이버 채널).** 설치 디렉터리와 레지스트리 키가 서로 다르다. 이 설치 관리자는 **네이버판 전용**이다. VERIFIED.
2. 배포/패치 파일 서버는 **`file.funitto.com`**, 경로 **`/azrok/download/`**, 아카이브 **`Setup.zip`**. VERIFIED.
3. `file.jr.naver.com` 참조 → 쥬니어네이버가 실제 배포 호스팅에 관여했다. VERIFIED(문자열), 역할 상세는 INFERRED.
4. **개발 빌드 경로 `D:\2006_Project\Hansol\` → 아즈로크 프로젝트는 2006년에 시작됐다.** 2011년 종료까지 최소 5년 서비스. VERIFIED(문자열 근거).

> 주의: 이 배포판 정보가 우리 `Azrok_Plaza` 클라이언트의 서버 프로토콜을 바꾸지는 않는다. 두 배포판이 같은 게임 서버를 썼는지는 **NOT VERIFIED**.

### F12. `AzrokStarter.ocx` — 순수 기동 래퍼, 네트워크 코드 없음 — VERIFIED

36,864 B. 문자열 200개 전수 확인 결과:

- ActiveX 등록 정보(`AZROKSTARTER.AzrokStarterCtrl.1`, `DllRegisterServer`, 프로퍼티 페이지)와 **DirectX 버전 판별 문자열**(`DirectX version is 9.0a/9.0b/9.0c`, `. DirectX version is %d.0`)이 전부다.
- 참조 실행 파일은 `AzrokInstaller.exe` 하나.
- **URL·호스트명·포트·패치 프로토콜 문자열이 0개다.**

**결론: OCX 의 역할은 "DirectX 버전 확인 + AzrokInstaller 기동" 뿐이다.** 서버 주소는 OCX 가 아니라 웹 페이지/인스톨러 쪽에 있다. (OCX 바이너리 디컴파일은 별도 ocx-probe 담당 — 이 문자열 결과와 충돌하면 ocx-probe 를 우선한다)

### F13. HansolFunnyMini 는 아즈로크와 자산·포맷을 전혀 공유하지 않는다 — VERIFIED

우선순위 5 판정. 세 축으로 직접 확인:

**(a) 아카이브 포맷** — `.gp3` 헤더를 직접 디코드:
```
'GP3!' + [count] + 반복[ namelen u16 ][ name ][ u32 ][ u32 ]
첫 엔트리: "Angel_01_01.png"
```
→ **`GP3!` 매직 + PNG 원소**의 커스텀 2D 아카이브다.
아즈로크는 `.wis`(헤더 `02 00 00 00 ...`), `.wmb`(`WMB6`), `.mdl` — **Conitec Acknex(3D GameStudio) 계열**이다. 매직·구조·원소 포맷이 전부 다르다.
프로젝트 전체에 `.gp3` 파일은 **0개**, `Data/**` 에 `.uit` 는 **0개**다. VERIFIED.

**(b) 엔진/런타임** — HansolFunnyMini 는 `d3dx9_27.dll` + `msvcr80/msvcp80/msvcm80`(VC++2005) + `unicows.dll`(Win9x 유니코드 레이어) + `ogg/vorbis` 를 직접 동봉한 **자체 DirectX9 2D 엔진**이다. 아즈로크의 Acknex 런타임과 무관하다. VERIFIED.

**(c) 스크린샷** — `GK02d110224200055.jpg`(2011-02-24), `GK02d110224200854.jpg`(2011-02-24) 두 장을 직접 열어 확인:
- 내용은 **HansolGameKing 의 2D 로비 화면**이다. 카드팩 선택, 개인전/단체전(Team Play/Single Play), RED/BLUE 팀, 난이도(쉬움/보통/어려움), 아이템구매/나가기 버튼, 상단 배너 "오픈 베타 테스트 많은 참여 부탁드립니다".
- **아즈로크 요소는 하나도 없다.** 3D 광장도, 아즈로크 캐릭터(블루론/레드론)도, 아즈로크 UI 도 없다. 아트 스타일부터 완전히 다른 게임이다. VERIFIED.
- 세 번째 `GK02d110208204158.jpg`(2011-02-08)는 **선두 클러스터 손실**로 JPEG SOI 가 없다(첫 4바이트 `ff da ff e2` = 스캔 중간부터 시작). 디코드 불가. VERIFIED(부정).

**최종 판정: 한솔 퍼니미니는 같은 발행사(한솔)의 별개 게임이며, 아즈로크 서버 복원에 재사용할 자산·포맷·프로토콜이 없다.** 보존 가치는 "같은 발행사의 동시대 게임" 이라는 맥락 자료로서만 존재한다.

(개인 PC 사용 흔적에 관한 부수 사실은 공개본에서 뺐다)

### F14. 복구 실패 파일 목록 (클러스터 재할당) — VERIFIED

DEL 표시 파일 중 **파일명만 살아남고 내용은 다른 데이터로 덮인 것**들. 시간 낭비 방지를 위해 명시:

| 파일 | 실제 내용 |
|---|---|
| `starmaru_progressbar[1].htm` | x86 기계어 (F3) |
| `WINDOWS/Prefetch/STARMARU.EXE-16A5D751.pf` | ASCII 16진 텍스트(`9F50313C`, `393200F1`, `41404566 16","`…). 프리페치 매직 `SCCA` 없음 → **XP 프리페치가 아니다.** 실행 이력·참조 경로 추출 불가 |
| `skin_funittomania_left_bottom[1].gif` | GIF 헤더 없음 (`62 bc 12 a1`) |
| `skin_funittomania_menu[1].gif` | GIF 헤더 없음 (`6e 00 20 00`) |
| `skin_funittomania_body[1].jpg` | JPEG 헤더 없음 (`49 49 49 42`) |
| `skin_funittomania_top[1].jpg` | 선두 손실 (`02 25 25 25`), 꼬리에 `ff d9` 만 존재 |
| `GK02d110208204158.jpg` | 선두 손실 |

정상 복구된 DEL 파일: `starmaru[1].css`, `login_funitto_do[1].htm`, `funitto_jaeminara_co_kr[1].htm`, 쿠키 3종, `skin_funittomania_left_top[1].gif`, `skin_funittomania_left_bg[1].gif`.
비-DEL 파일(`Documents and Settings/Guest/**` 아이콘 3종, HansolFunnyMini 전체, OCX/INF/Installer)은 **전부 구조 정상**이다 — PE 시그니처 6개 전수 확인.

---

## 미회수 — 추가 추출 권장 (아직 이미지 안에 있음)

`_img2011_diff.md` 가 "우리에게 없는 원본 파일 48개"로 식별했으나 **추출 폴더에 복사되지 않은 것들.**

1. **★ `Program Files\Hansol\Azrok_Plaza\azrok.lg` (23 B)** — 우리에게 없는 **유일한 비-Thumbs.db 파일**이다. 23바이트짜리 정체 불명 파일이며 확장자 `.lg` 는 로그/설정으로 보인다 (INFERRED). **추출 가치 최상 — 비용은 23바이트다.**
2. `Data\Space\Plaza\Thumbs.db` (398,848 B), `Data\Texture\Thumbs.db` (362,496 B) 외 Thumbs.db 46개 — 각 폴더 이미지의 **당시 썸네일 캐시**. 원본 텍스처를 이미 전부 갖고 있으므로 우선순위 낮음. 다만 Thumbs.db 는 **삭제된 이미지의 썸네일도 보존**하므로, 현행 폴더에 없는 파일명이 들어있다면 "패치로 제거된 에셋"의 증거가 된다 (INFERRED). Plaza/Texture 두 개만 확인해 볼 값어치는 있다.
3. IE 캐시 인덱스(`index.dat`) — 추출 목록에 없다. 있다면 **방문 URL 전체 이력**(패치 요청 URL 포함)이 나온다. **1순위 추천.**

---

## 배치 4 — 전수 키워드 스윕 (마무리)

281개 파일 전부를 CP949 / UTF-8 / UTF-16LE 3중 인코딩으로 키워드 스윕했다.

### F15. "서비스 종료 안내" 문구는 이 덤프에 존재하지 않는다 — VERIFIED (부정)

`서비스 종료` / `종료 안내` / `서비스종료` / `종료안내` 를 3중 인코딩으로 전수 검색 → **0건.**

설명: 이 PC 의 마지막 웹 접속 흔적은 **2011-05-01** 이고, 종료 공지는 그 이후에 게시됐거나 캐시가 이미 덮였다 (INFERRED). 종료 안내 문구는 이 아티팩트가 아니라 wayback 트랙에서 찾아야 한다.

### F16. `봉에너지`/`출석` 문자열 위치 — 신규 정보 없음, 기존 결론 보강

스윕 결과 해당 문자열 보유 파일은 4개뿐이며 **전부 우리 사본과 바이트 동일**(F9):
`Data\Plaza\bee.npc`(꿀풍 NPC 대사 25줄), `init.csv`, `test.csv`, `Azrok.dat`.

**`bee.npc` 전문은 `_wayback_energy_findings.md` 가 이미 전수 디코드·분석 완료**했다(봉에너지 웹 지급 3종, 보관함, 펀콘공장). **본 조사는 그 내용을 독립적으로 재확인만 했고 새로 추가할 것이 없다.** 해당 주제의 권위는 `_wayback_energy_findings.md` 다.

부수 확인(VERIFIED, bee.npc 원문): 4종족 NPC 명 — **뮤리 / 새지 / 테로 / 아링**. 이는 `Data\OutMap\` 폴더명 `MuryPlay`(놀이) / `PaziKnow`(지식) / `TeroGym`(체육) / `ArimCook`(요리) 및 `starmaru/resource_starmaru/character3D/sejee001~004.dat` 와 대응한다. `산달폰 할아버지는 운영자랍니다` 는 문서 106 의 산달폰 가이드 NPC 와 일치한다.

### F17. `skin_funittomania_top[1].jpg` (640 KB) 재할당 클러스터 = 코드서명 인증서 — VERIFIED (부정)

`패치`/`http://` 키워드가 걸렸으나 실제 내용은 **Authenticode 서명 블록**이다: `ocsp.thawte.com`, `crl.verisign.com`, `csc3-2010-crl.verisign.com`, `ts-ocsp.ws.symantec.com`, `crl.microsoft.com/pki/crl/products/MicrosoftCodeVerifRoot.crl` 등 CA/타임스탬프 URL 뿐. 서명된 PE 가 이 클러스터를 덮었다.
**아즈로크·퍼니또 관련 URL 0건. 더 파볼 가치 없다.**

---

## 종합 판정표

| 우선순위 | 대상 | 판정 |
|---|---|---|
| 1 | `starmaru_progressbar[1].htm` | ❌ 내용 소실(x86 기계어). 회수 불가 |
| 1 | `login_funitto_do` / `funitto_jaeminara_co_kr` | ✅ 복구 성공. URL 체계 확정(F1) |
| 1 | 퍼니또 쿠키 3종 | ✅ 복구. 단 `_EXEN` 카운터뿐, 세션 구조 없음(F2) |
| 1 | 종료 안내 문구 | ❌ 이 덤프에 없음(F15) |
| 2 | `.url` 4개 | ✅ 완전 확정(F1) |
| 3 | `Azrok.txt` 원본 | ✅ 정체 = 크래시 로그. 2011 실서비스 크래시 1건 확보(F4) |
| 4 | `.uit` 112 + `.skn` 2 | ❌ 구버전 아님. 우리 사본과 **121/121 바이트 동일**. 보존 가치 0(F8) |
| 5 | HansolFunnyMini | ❌ 아즈로크와 포맷·엔진·자산 공유 0. 스크린샷에 아즈로크 요소 없음(F13) |
| — | `AzrokInstaller.exe` | ★ **최대 수확** — `Azrok_Naver` 배포판, `file.funitto.com/azrok/download/`, 2006 프로젝트 개시(F11) |
| — | `Server.dat` | ★ 퍼니미니 원본 서버 `58.225.56.101:8949`(아즈로크 아님)(F6) |
| — | `version.dat` | ○ 패처 매니페스트 포맷 확정, 스크램블 미해결(F10) |

---

## 배치 5 — ★★★ `Azrok_Naver\Setup.zip` 회수 (2011.img 직접 추출)

> **정정**: 배치 3 말미의 "미회수 권장 1번 `azrok.lg`" 는 이미 회수되었다(전문 `IsInitialized()==false`, 단순 에러 로그). 목록에서 삭제.

### F18. ★★★ 원본 배포 아카이브 `Setup.zip` 58,563,520 B 를 이미지에서 추출 — VERIFIED

`_img2011_files.md` MFT 열거에서 발견:
```
| Program Files\Hansol\Azrok_Naver\Setup.zip | file | 58563520 | 2011-03-14 13:59 |  | 55107 |
```
**DEL 표시가 없다 = 삭제되지 않은 살아있는 파일이다.**

`D:\2011.img` 를 읽기 전용으로 열어 NTFS 를 직접 파싱해 추출했다(파티션 offset 32256, bps 512, spc 8, cluster 4096, MFT LCN 786432, 레코드 1024 B).
레코드 55107 은 `$ATTRIBUTE_LIST`(0x20)를 가진 분산 파일이라 `$DATA` 가 확장 레코드 4개에 나뉘어 있었다:
`MFT#55141(VCN 0) / #55152(VCN 5392) / #55161(VCN 7696) / #55156(VCN 10000)`, 총 4 run / 14,298 클러스터.

**추출 결과: 58,563,520 B, md5 `bd46ecb4f3018c27f70840f1ce40ff03`.**
저장 위치: `docs/research/_img2011_extracted/Program Files/Hansol/Azrok_Naver/Setup.zip`

**상태: 선두부터 정상이나 말미가 잘렸다 (VERIFIED).**
- 매직 `PK\x03\x04` 정상. 그러나 EOCD(`PK\x05\x06`)·중앙디렉터리(`PK\x01\x02`)가 **파일 전체에 0건**이다.
- 로컬 헤더를 순차 워크하면 **2,564 엔트리**를 읽고 오프셋 58,623,559 에서 파일 끝(58,563,520)을 넘어선다 → 마지막 1개 엔트리와 중앙디렉터리가 없다.
- 즉 **다운로드가 중단된 상태로 남은 파일**이다. 2011-03-14 12:10 에 `Azrok_Naver\Data\{button,Common}` 디렉터리만 생성되고 13:59 에 zip 이 기록된 정황과 일치한다(설치 미완료). INFERRED.
- **실질 손실은 거의 없다**: 압축 55.7 MB / 원본 212.2 MB, 2,564 엔트리가 온전하다.

### F19. ★★★ 빌드 아티팩트 동봉 — `Azrok.ilk` 심볼 확보 — VERIFIED

Setup.zip 루트에 **개발 빌드 산출물이 그대로 들어있다.** 핵심 11개를 CRC 검증하며 추출(11/11 CRC OK):
`_img2011_extracted/Program Files/Hansol/Azrok_Naver/_unpacked/`

| 파일 | 크기 | md5(앞12) |
|---|---:|---|
| `Azrok.exe` | 2,461,759 | `0d347e22fe2f` |
| **`Azrok.ilk`** | **2,929,976** | `d81890c398f2` |
| `Azrok.exp` | 5,898 | `a415cdb73a9a` |
| `Azrok.lib` | 10,858 | `eb7bc059775d` |
| `med.exe` | 1,036,288 | `ec577cd50323` |
| `Azrok.bat` | 64 | `d64da0fec034` |
| `azrok.lg` | 12 | `fbc6c79f8b5b` |
| `Azrok.SUP` | 93 | `6b4348be13c0` |
| `JSData.tmp` | 329 | `0f04b3dfe631` |
| `lgc.tmp` | 1,049 | `a5d657e2de69` |
| `sys.tmp` | 4,268 | `849ba2343044` |

**`Azrok.ilk` = MSVC 증분 링크 파일이며 원본 심볼을 보존한다.** 헤더 `Microsoft Linker`. 빌드 환경은 `C:\Program Files\Microsoft Visual Studio\VC98\LIB\...` = **Visual C++ 6.0 + MFC** (VERIFIED).

심볼 덤프 저장: `_img2011_extracted/Program Files/Hansol/Azrok_Naver/_ilk_symbols.txt`
- **프로젝트 `.obj` 모듈 120개** (원본 소스 파일명)
- **데코레이트 C++ 심볼 4,553개**
- **클래스 177개**

**120개 모듈 전체:**
```
Azrok AzrokLog Bmap BmapCombination ButtonManager Camera CaptureScreen Caution
Chat ClientPeer DxEdit Effect EquipMent EquipMentIndex ErrorMessage Expression
Game GameButton GameManager GameManagerPacket GameMsg GamePanel GamePeer Game_Key
Interface Interior Inventory ItemToolTipTable JSCommand JSInventory JSInventoryBase
JSInventoryFurniture JSLogic JSMarumong JSMenu JSOutDoor JSProperty JSQuestList
JSRefrigerator JSScheduler JSShop JSStatus JSUser Jpeg KeyMan Lobby Logic LogicJSDB
Monitor MsgQue Option OutMap PL_Action PL_Camera PL_Effect PL_KeyMap PL_Player
Packet PanManager PanelManager PlayerAni PlayerAniEffect PlazaManager PopcornInterface
Popup PopupCalendar PopupCharacterInfo PopupClean PopupEquip PopupErrorMessage
PopupExp PopupGameOver PopupHelp PopupItemShop PopupMainMenu PopupMyBag PopupOption
PopupOutMap PopupOutMapBingBing PopupOutMapCook PopupOutMapGym PopupOutMapKnow
PopupOutMapMagic PopupOutMapNPC PopupOutMapPlay PopupOutMapResult PopupPopcornInterface
PopupRingCommand PopupSelectEgg PopupSelectPet PopupStateList PopupStatus PopupTestBmap
Quest ResourceMan Sound StdAfx Story StringAnalysis TcpClient Text TextureMaker
ThreadBase ToolTip UI UIAni UIManager Util ViewProperty
(+ ximabmp ximaenc ximage ximainfo ximaint ximalpha ximapal ximath ximatran ximawnd xmemfile = CxImage 서드파티)
```

**★ 네트워크 스택 전체 시그니처 (VERIFIED, 디맹글):**
```
TcpClient::Connect(char*, int) -> bool
TcpClient::Send(char*, int) -> int
TcpClient::OnReceive(char*, int)            [virtual]
TcpClient::TcpClientThread(void*)           [static]
TcpClient::{Startup,Cleanup,AttachSocket,DetachSocket,Disconnect,OnConnect,OnDisconnect,OnTerminated,WaitDestoryThread}

CClientPeer::Protocol(int, void*, int) -> bool      [virtual, protected]
CClientPeer::PushReceivePacketList(void*, int, int) -> bool
CClientPeer::PushSendPacketList(void*, int, int) -> bool
CClientPeer::PopPacketList(bool) -> GAME_PACKET*
CClientPeer::{Data2Queue, Queue2Data, Queue2Send, SendPacket, SendPacketList, DeletePacketList, IsConnect}

CGamePeer::AddPacket(int, void*, int)
CGamePeer::SendPacket() -> bool
CGamePeer::Protocol(int, void*, int) -> bool        [virtual]
CGamePeer::GetPacket() -> SPacket*                  [protected]

CPacket::MakePacket(void*, int, void*, int) -> int
CMsgQue::{AddMsg(int,int,int), GetMsg()->ANIMSG, Clear}
```
`Protocol(int opcode, void* payload, int len)` 이 **정확한 디스패처 시그니처**다. 구조체 `GAME_PACKET`, `SPacket`, `ANIMSG`, `LOGIC_MSG`, `BMAP_NODE`, `SKINBUF`, `TextNode` 도 심볼에서 확인된다.

**★ `CJSLogic` 계열 확정 (문서 123 보강):** `CJSLogic`, `CJSCommand`, `CJSColumn`, `CJSUser`, `CJSStatus`, `CJSProperty`, `CJSQuestList`, `CJSInventory`, `CJSInventoryBase`, `CJSInventoryFurniture`, `CJSShop`, `CJSScheduler`, `CJSMenu`, `CJSOutDoor`, `CJSMarumong`, `CJSRefrigerator`, `CLogicJSDB`. → `JS` 접두사는 실제 원본 명명이며(F7 의 `JSStarter.ocx` 와 일치) `CJSLogic` 은 추정이 아니라 **원본 클래스명**이다.

### F20. ★★★ `Azrok.bat` — 원본 커맨드라인 전문 — VERIFIED

`_unpacked/Azrok.bat` (64 B) 전문:
```
Azrok -nwnd -nx 100 -pl naver -dir 1234567890 -ip 127.0.0.1:3000
```

**이것은 개발자 자신의 로컬 실행 배치다**(127.0.0.1 = 로컬 테스트 서버). 확정되는 것:

1. **`-nx 100`** — INDEX 미해결 항목 "원본 Nexus 계약: 원본 서비스가 실제 전달한 정확한 값 미확정"에 **직접 증거**다. 개발 빌드 기본이 **100** 이다. 우리 복원 프로파일은 `-NX200`. → 원본은 200 이 아니라 **100 이 기준선**이었을 가능성이 크다 (VERIFIED = 배치파일 문자열 / 실서비스 전달값과 동일한지는 INFERRED).
2. **`-pl naver`** — **플랫폼/배급사 스위치**. 같은 실행 파일이 `-pl` 인자로 배포 채널을 분기한다. → **Plaza 판과 Naver 판은 동일 코드베이스의 빌드 변형**이다 (INFERRED, 강함).
3. **`-ip <host>:<port>`** — 서버 주소를 **커맨드라인으로 받는다**.
   > **SUPERSEDED by 195.** 이 항목의 원문은 "포트 표기가 `:3000`(개발), 실서비스는 `8949`(다른 트랙 확정값)" 이었다.
   > **`8949` 는 아즈로크 포트가 아니다.** 이미지 74.56 GB 전수에서 `:8949` 는 고유 문맥 1건(바이너리 노이즈)뿐이고,
   > `8949` 의 두 출처는 각각 퍼니미니(`HansolFunnyMini\Server.dat`)와 별마루(`starmaru\...\data.dat`) 다.
   > 아즈로크 광장 실서비스 포트는 **4000** 으로 2011·2013 두 시점 실측됐다 (문서 195 §4·§5).
4. `-nwnd` (창 모드 추정), **`-dir` = `GAMESESSION`** — OCX 가 넘기는 `GAMESESSION` 이 그대로 `-DIR` 로 들어간다.
   > **문서 195 §3 에서 INFERRED → VERIFIED 승격.** 2011년 실행 커맨드라인 실측 3건으로 확정됐고,
   > 형식은 `{13자리 epoch ms}_{66자 [A-Za-z0-9]}` 다. 예: `1296962604061_FmSFNTJM…`(2011-02-06 12:23:24 KST).

**ocx-probe 결과와의 정합**: OCX 는 `ShellExecuteA("AzrokInstaller.exe", "<GAMEIP> <GAMEID> <GAMESESSION> ")` 를 실행한다. `Azrok.bat` 의 `-ip` / `-dir` 와 대응 구조가 일치한다 (INFERRED).

### F21. 두 배포판은 서로 다른 빌드 — VERIFIED

| | Plaza (우리 것) | Naver (Setup.zip) |
|---|---|---|
| `Azrok.exe` 크기 | 2,199,552 | **2,461,759** |
| md5 | `eac34b226ff5…` | `0d347e22fe2f…` |
| 버전 문자열 | `Ver. PLAZA 1.3.1` | **`Ver. Jr. Naver  1.4`** |
| 하드코딩 IP | 없음 | `127.0.0.1` (개발 잔재) |

- **Naver 판이 1.4 로 더 높다.** Naver 빌드는 `.ilk/.exp/.lib` 가 동봉된 **링커 산출물 미정리 빌드**라 크기가 크다.
- 버전 문자열이 `Ver. <채널> <번호>` 형식임이 확정됐다 → `-pl` 스위치와 대응.
- **두 배포판이 같은 게임 서버를 썼는지**: 여전히 **NOT VERIFIED**. 다만 (a) 동일 코드베이스·동일 `-ip` 커맨드라인 계약, (b) 동일 `CGamePeer::Protocol` 스택, (c) 같은 `funitto.com` 포털 → **같은 프로토콜을 쓴 것은 거의 확실하고(INFERRED-강), 같은 서버 인스턴스였는지는 별개 문제로 미확정**이다.

### F22. `JSData.tmp` = 로컬 캐릭터 상태 스냅샷 — VERIFIED

`_unpacked/JSData.tmp` (329 B):
```
'<saved-id>' + 0xCC 패딩(13B) + 'Guest' + 0xCC 패딩(약 100B) + 바이너리 스탯 블록
```
- `<saved-id>` = 개발/테스트 계정 ID, `Guest` = 기본 캐릭터명. **INDEX 문서 56 의 "self 이름 = localPlayer+0xC8 기본 `Guest`" 와 정확히 일치**한다.
- 0xCC 패딩 = MSVC 디버그 초기화 바이트 → 고정 길이 필드(ID 22B, 이름 105B 추정)를 그대로 덤프한 구조체다 (INFERRED).
- 뒤따르는 u16 배열이 스탯/상태로 보인다. **S→C 0x0007 페이로드의 로컬 대응물일 가능성이 높다 → 서버 0x0007 검증용 참조값으로 쓸 수 있다** (NOT VERIFIED, 필드 매핑 미실시).
- `azrok.lg` = `m_pNowSpace` (Plaza 판은 `IsInitialized()==false`) → **`.lg` 는 마지막 실패 표현식을 기록하는 assert 로그**임이 두 샘플로 확정됐다.

### F23. `lgc.tmp` / `sys.tmp` 는 Plaza 판과 다르다 — VERIFIED

| 파일 | Naver 판 | Plaza 판(우리) |
|---|---:|---:|
| `lgc.tmp` | 1,049 | (프로젝트 사본과 크기 비교 필요) |
| `sys.tmp` | 4,268 | 〃 |

문서 11/15 가 `lgc.tmp`(57행 스탯 스키마) / `sys.tmp`(액션 델타)를 권위로 쓰고 있으므로, **Naver 1.4 판과의 차분은 밸런스 변경 이력의 직접 증거가 된다.** 대조는 후속 과제 (NOT VERIFIED).

### F23 (확정). `lgc.tmp` 차분 = 단 2바이트, `지식경험` 상한 600 → 450 — VERIFIED

`sys.tmp` 는 **IDENTICAL**(4,268 B) — 액션 델타 테이블은 두 판이 동일하다. 문서 65/76/79 의 sys.tmp 근거는 안전하다.

`lgc.tmp` 는 크기 동일(1,049 B)이나 **오프셋 560,561 두 바이트만 다르다.** 둘 다 57행 CP949 텍스트이며 차이는 **30행 하나**뿐:

```
L30  Naver 1.4   : 지식경험,0,0,600
L30  Plaza 1.3.1 : 지식경험,0,0,450
```

- 행 인덱스 30 = **stat30**. 문서 76 의 `0=독서(지식 stat30)` 매핑과 정확히 일치한다 → **57행 lgc.tmp 행번호가 곧 stat 번호라는 것의 독립 확증** (VERIFIED).
- 네 번째 필드가 **상한값**이며 채널/버전에 따라 조정됐다 (INFERRED — 필드 의미는 문서 11/15 권위).
- 어느 쪽이 나중인지는 버전 번호만으로 단정할 수 없다(채널별 독립 번호 가능). Setup.zip 기록 시각은 2011-03-14. **선후 판정은 NOT VERIFIED.**

### F24. `Setup.zip` 은 웹아카이브에 없다 — VERIFIED (부정)

`web.archive.org` CDX 조회:
- `file.funitto.com/azrok*` (prefix) → **0건**
- `funitto.com` 도메인 전체에서 `download|Setup|.zip|.cab|.exe` 필터 → **0건**
- 반면 `file.funitto.com` 도메인 자체는 다수 아카이브됨(`/css/azrok.css` 20141220, `/css/azrok_tcg.css`, `/acecounter/*` 20101231, `/images/alliance/img/azrok_*` 등). 즉 CDN 은 크롤됐지만 **배포 바이너리 경로 `/azrok/download/` 는 크롤되지 않았다.**

**→ 이 `Setup.zip` 은 현존하는 유일본일 가능성이 높다. 보존 가치 최상.** (INFERRED-강)

부수(VERIFIED): wayback 에 `file.funitto.com/css/azrok_tcg.css`, `azrok_tcg_yahoo.css` 가 있다 → **`아즈로크TCG` 라는 별도 파생 게임과 야후 코리아 제휴판**이 존재했다. 배포 채널이 최소 4종(퍼니또 자체 / 쥬니어네이버 / 야후 / 제휴 alliance)이다.

---

## 갱신된 종합 판정 (배치 5 반영)

| 항목 | 등급 | 요지 |
|---|---|---|
| `Azrok_Naver` 설치 흔적 | **VERIFIED** | MFT 에 디렉터리 4개 + `Setup.zip`. 2011-03-14 설치 시도, **미완료** |
| `Setup.zip` 회수 | **VERIFIED** | 58,563,520 B 추출. 2,564 엔트리 온전, 말미/EOCD 결손 |
| 원본 심볼 | **VERIFIED** | `Azrok.ilk` → 모듈 120 / 클래스 177 / 심볼 4,553 |
| 원본 커맨드라인 | **VERIFIED** | `-nwnd -nx 100 -pl naver -dir <token> -ip <host>:<port>` |
| 원본 Nexus 값 | **VERIFIED(개발빌드)** | `-nx 100`. 실서비스 전달값과 동일 여부는 INFERRED |
| 두 배포판 동일 서버 | **NOT VERIFIED** | 동일 코드베이스·동일 프로토콜은 INFERRED-강, 동일 인스턴스는 미확정 |
| 레지스트리 `Software\Hansol\Azrok_Naver` | **NOT VERIFIED** | 인스톨러 문자열로만 확인. 하이브 직접 파싱 미실시 |

### F25. 레지스트리 — `Azrok_Plaza` 키는 있고 `Azrok_Naver` 키는 없다 — VERIFIED

`_img2011_scan.md`(원본 이미지 키워드 스캔) 대조:

- **`Azrok_Plaza`**: 레지스트리 셀 시그니처와 함께 등장한다 —
  `nk ...Azrok_Plaza ... lf ... vk ... InstallPath ... vk ... Version` 및
  `vk ... InstallPath ... C:\Program Files\Hansol\...`(UTF-16)
  → **`Software\Hansol\Azrok_Plaza` 키가 `InstallPath` / `Version` 값과 함께 실재한다.**
- **`Azrok_Naver`**: 15건 모두 `AzrokInstaller.exe` 내부 문자열(진행률 `%d` 메시지, 경로 템플릿)이다. **`nk`/`vk` 레지스트리 셀 컨텍스트가 단 1건도 없다.**

**→ 네이버판은 레지스트리 등록 단계까지 가지 못했다.** F18 의 "설치 미완료"(디렉터리 2개만 생성, Setup.zip 다운로드 중단) 판정과 독립적으로 일치한다. INFERRED → **VERIFIED 로 상향.**
