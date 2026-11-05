# 195. 웹 런처 계약 · 진입 사슬 · 광장 서버 엔드포인트 확정 (2026-07-20)

2011 디스크 이미지(`D:\2011.img`, 80,060,424,192 B) **전수 스캔** + web.archive.org 교차조회로
포털 로그인부터 `Azrok.exe` 실행까지의 사슬 전체를 복원했다.
**기존 결론 2건을 뒤집는다** (§5, §6).

---

## 1. 웹 런처 계약 전문 — VERIFIED

출처: `http://file.funitto.com/js/objectWrite.js`
아카이브 사본 `20130406123412`, 2013년 스냅샷 5건 전부 동일 다이제스트
(`ZPP45RIP3XGXROIWPE6LS4Q4F22YIQYC`).
로컬 보존: `docs/research/artifacts/objectWrite_funitto_20130406.js` (25,261 B)
이미지 내 사본도 3곳에서 독립 확인 (오프셋 14789876360 / 41161374364 / 51923548808).

| 함수 | 주석 | CAB | 버전 | CLSID | `GAMEIP` |
|---|---|---|---|---|---|
| `writeCabAzrokObject` | 아즈로크 **게임** | `JSStarter.cab` | 1,4,0,1 | `2C7A85FB-CAB3-40B1-B9D8-6E29456BF27B` | `pet.funitto.com:3000` |
| `writeCabAzrokObject2` | **광장용** | `PlazaStarter.cab` | 1,4,1,2 | `1570A176-88D2-4C37-9A5C-E55641DB8A20` | **`222.112.161.115:4000`** |
| `writeCabAzrokObject3` | **광장용** | `PlazaStarter.cab` | 1,4,2,6 | 동일 | 인자로 전달 (**동적**) |

세 함수 모두 `<param>` 이 정확히 **`GAMEIP` / `GAMEID` / `GAMESESSION`** 3개다.
즉 ActiveX 스타터의 역할은 **"호스트:포트 + 계정 + 세션토큰"을 클라이언트에 넘기는 것**이 전부다.

**PlazaStarter CLSID 는 `9A5C` 다** — 이미지 내 HTML 사본에서는 `9A50` 으로 보이지만,
그 위치의 바이트는 `33 37 2D 39 41 35 30 82 36 6D ...` 이고 `30 82` 는 ASCII `0` 이 아니라
PKCS#7 서명을 여는 **DER SEQUENCE 태그**다(뒤에 OID 1.2.840.113549.1.7.2 = signedData).
레지스트리 하이브 조각 3벌과 아카이브 JS 가 독립적으로 `9A5C` 를 준다. — VERIFIED

`writeCabAzrokObject3` 이 `gameIp` 를 인자로 받는다는 것은 그 시점에 **광장 서버가 복수**가
됐다는 뜻이다. — INFERRED (강함)

---

## 2. 진입 사슬 5단계 — VERIFIED (실측값 포함)

```
① http://www.funitto.com/funnytoon/login/login_funitto_do.jsp
     ?p_return_url=http%3A%2F%2Ffunitto.jaeminara.co.kr%2Fazrok%2Fmain.screen
     &p_lgk=<base64 약 340자>
② → 로그인 성공 페이지 (title: "한솔교육 관리자")
     setCookie(cookieStoreID, "peaceful0415", ...)
     window.open(".../member/login/view/login_reward_pop.jsp?return_code=FN0000", 445x198)
     location.replace("/member/login/action/login_chk.jsp?p_return_url=...%2Fazrok%2Fmain.screen")
③ → funitto.jaeminara.co.kr/azrok/main.screen
④ → writeCabAzrokObject2(gameId, gameSession) → PlazaStarter OCX
     → ShellExecute("PlazaInstaller.exe", "<GAMEIP> <GAMEID> <GAMESESSION>")
⑤ → Azrok.exe -NX 100 -NWND -PL peaceful0415
              -DIR 1296962604061_FmSFNTJM... -IP 58.225.56.101:4000
```

②의 로그인 성공 페이지는 **IE 캐시 실물**로 회수됐다:
`docs/research/artifacts/_img2011_pages/p027271863842_da42b6f4_한솔교육 관리자.htm`

**★ 시각 교차검증**: 캐시된 HTTP 응답 헤더가 `Date: Sun, 06 Feb 2011 03:25:05 GMT` 이고,
⑤ 세션 토큰의 epoch `1296962604061` = **2011-02-06 03:23:24 GMT**. **1분 41초 차이.**
독립된 두 증거(웹 캐시 / 프로세스 메모리)가 분 단위로 정합한다.

OCX 는 두 파라미터를 검증한다 — 바이너리 문자열 실측:
`GAMESESSION 파라미터 없음` / `GAMEID 파라미터 없음`, 그리고
`PlazaInstaller.exe`(오프셋 43211067440) 와 `AzrokInstaller.exe`(오프셋 43217469488) 가
각각 별도 빌드로 존재한다.

---

## 3. `gameSession` 실제 형식 — VERIFIED (샘플 3)

`-DIR` 인자가 곧 `GAMESESSION` 이다. 프로세스 환경블록과 함께 페이지파일 영역에 남은 실측:

```
{13자리 epoch ms}_{66자 [A-Za-z0-9]}
```

| epoch | KST | 토큰(66자) | 이미지 오프셋 |
|---|---|---|---|
| 1296962604061 | 2011-02-06 12:23:24 | `FmSFNTJMQyxJdpdnTj9qwBrxwnrSwYhYjmwyPLLmm1GG7lYQMhkZf16Xmp1mhG700h` | 3767760958, 3767785542 |
| 1296119298121 | 2011-01-27 18:08:18 | `QkhvNB2CvLL8hLT89cv2pT80hmndNjV6YLQlLzrV6tpMwcMsL125Wn046nfTb272ZZ` | 3922835518 |
| 1295953847659 | 2011-01-25 20:10:47 | `rfQkN2vXfkR9BHHbJyQqpL012MMvVprTyk8fy4kST2yz5Xy2z8LP3YbV8yQGydn4tn` | 3976064118 |

세 개 모두 정확히 66자, 대문자+소문자+숫자 혼합. 계정은 전부 `peaceful0415`,
`-NX` 는 전부 **100** (현 운영값 200 과 다름 — 문서 138/126 참조).

→ `_img2011_artifact_findings.md:413` 의 `-dir` = "세션/인증 토큰 자리로 **추정**" 을
   **INFERRED → VERIFIED 로 승격**한다.

---

## 4. 광장 서버 엔드포인트 — 시대별

| 시점 | 광장(PlazaStarter) 서버 | 포트 | 근거 |
|---|---|---|---|
| 2011-01~02 | **`58.225.56.101`** | **4000** | 실행 커맨드라인 8회 (VERIFIED) |
| 2013 | `222.112.161.115` | **4000** | 아카이브 `objectWrite.js` (VERIFIED) |
| (그 이후) | 동적 | — | `writeCabAzrokObject3(gameIp)` |

**IP 는 바뀌었지만 포트 4000 은 불변.** 독립된 두 증거가 일치한다.

`58.225.56.101` 은 **퍼니또 공유 호스트**다 — 포트로 제품을 갈랐다:

| 포트 | 제품 | 근거 |
|---|---|---|
| **4000** | **아즈로크 광장** | 실행 커맨드라인 (본 문서) |
| 8949 | 퍼니미니 | `\hansol\HansolFunnyMini\Server.dat` = b64 `58.225.56.101, 8949` |

`pet.funitto.com:3000` 은 `writeCabAzrokObject`(JSStarter, "아즈로크 게임") 전용이며
**실행 커맨드라인에 단 한 번도 나오지 않는다**(이미지 전수 기준 14회 전부 JS 내부).
우리 클라이언트는 `Ver.txt` = **`Ver. PLAZA 1.3.1`** 이므로 광장 트랙이고,
따라서 `azrok_server.py` 가 재현 대상으로 삼아야 할 것은 **4000번 서버**다.

우리 클라이언트 하나에 공간 12개(`PatHouse`, `Plaza/hansol`, `OXquiz`, `ItemShop`,
`ArimCook`, `Magic`, `MuryPlay`, `Pazi`, `PopcornGame`, `SelectPet`, `TeroGym`, `lobby`)가
모두 들어 있고 `-IP` 도 하나뿐이므로, **12개 공간 전부가 단일 서버에 붙었다.** — INFERRED (강함)

---

## 5. ★ 정정 — `8949` 는 아즈로크 포트가 아니다

`_img2011_artifact_findings.md:412` 는 다음과 같이 적고 있다:

> 포트 표기가 `:3000`(개발), 실서비스는 `8949`(다른 트랙 확정값).

**이 서술은 폐기한다.** 근거:

1. 이미지 74.56 GB 전수에서 `:8949` 히트가 **총 2건(고유 문맥 1건)** 이고 그마저 바이너리 노이즈다.
   대조군: `:4000` 은 실행 커맨드라인에만 8회.
2. `8949` 가 나온 두 출처는 모두 **아즈로크가 아니다**:
   - `\hansol\HansolFunnyMini\Server.dat` → 퍼니미니
   - `\Program Files\starmaru\resource_starmaru\data.dat` → 별마루 (§6)
3. 아즈로크의 실서비스 포트는 2011·2013 두 시점 모두 **4000** 으로 실측됐다.

---

## 6. ★ 정정 — `data.dat` 은 별마루(starmaru) 파일이다

`_img2011_ocx_findings.md:783-785` 는 `data.dat` 의 `gameServer 202.89.127.166` /
`gameServerPort 8949` 를 근거로 `GAMEIP = 202.89.127.166:8949` 추론을 승격했다.

**그 `data.dat` 은 아즈로크 것이 아니다.**
`\Program Files\Hansol\Azrok_Plaza\` 의 MFT 전체 목록에 **`data.dat` 이 존재하지 않는다**:

```
acknex.dll, ackutl.dll, Azrok.dat, Azrok.exe, azrok.ico/.lg/.txt,
BL.tga/.wis, Data\, init.csv, JSData.tmp, lgc.tmp, logo.bmp, med.exe,
Screenshot\, sys.tmp, test.csv, Thumbs.db, Title.bmp, Ver.txt
```

해당 파일의 실제 경로는 **`\Program Files\starmaru\resource_starmaru\data.dat`**
(MFT #34039 @ `0x0213DC00`) 이다. MFT 레코드 슬랙에 남은 **구버전** 전문:

```
Server / notifyServer / saveServer / chattingServer  starmaru.funitto.jaeminara.co.kr
login       https://member.funitto.jaeminara.co.kr/member/login/app/app_login_do.jsp
gameServer  58.225.56.105        gameServerPort  8949
```

→ **`GAMEIP = 202.89.127.166:8949` 추론은 형제 타이틀에서 물려받은 오귀속이므로 철회한다.**

부수 확정: 별마루는 아즈로크와 연동돼 있었다 —
`home http://starmaru.funitto.com/star/maru.azrok.screen`,
`notifyPath starmaru/azrok/app`, 문자열 `"아즈로크에서 아즈론을 생성 하세요"`.

**아즈로크에는 서버 설정파일 자체가 없다.** 서버 주소를 오직 커맨드라인으로만 받았고,
이는 현재 우리 런처 구조와 일치한다.

---

## 7. 회수 실패 확정 — 다시 파지 말 것

| 대상 | 판정 | 근거 |
|---|---|---|
| `JSStarter.cab` / `PlazaStarter.cab` | **회수 불가** | `file.funitto.com` 아카이브 398 URL 경로가 `/images`(247) `/upload`(102) `/js`(13) `/css`(10) `/main`(9) `/track.php`(8) `/acecounter`(5) 뿐. **`/cab/` 디렉터리 미색인.** funitto 전 서브도메인 2,485 URL 중 `.cab`/`.ocx`/`.exe`/`.zip` **0건**. 원인: `codebase=` 가 `document.write` 문자열 안이라 크롤러가 링크로 인식 못 함 |
| 봉에너지 안내 이미지 `/images/azrok/popup/070417/img_01.gif` | **영구 소실** | 아카이브: `file.funitto.com` 398 URL 에 `popup` **0건**, 도메인 전체 2,486 URL 에 `070417` **0건**. 디스크: 74.56 GB 에 해당 치수 GIF **0건** |
| `bbsId=azrok` 도장판 본문 | **영구 소실** | 아카이브 0건. `bbsId=funny_study` 2건은 둘 다 302 |
| `gameSession` (메타데이터 경로) | 메타데이터엔 없음 | `$MFT`/`$LogFile`/`$Bitmap` 전부 0건. **단 페이지파일에는 있었다** (§3) — 소스를 갈랐어야 했다는 교훈 |

---

## 8. 방법론 교훈 — 이후 조사에 적용할 것

1. **CDX 의 `statuscode 200` 은 콘텐츠 생존을 뜻하지 않는다.**
   `file.funitto.com/images/re_azrok/*` 61건이 전부 200 이지만 실체는
   `text/html` 4.2~4.5 KB **도메인 파킹 페이지**(`x-archive-orig-x-template: tpl_CleanPeppermintBlack_twoclick`).
   2019-04 이후 캡처는 전부 이것. `cdn.funitto.com/images/re_azrok/*` 도 `image/*` **0건**.
   → **`mimetype` 과 `length` 를 반드시 함께 볼 것.** `text/html` + 4~6 KB = 파킹.
2. **HTML 의 `width`/`height` 는 표시 치수지 실제 이미지 치수가 아니다.**
   GIF 헤더 치수(바이트 6-9, LE16)로 카빙할 때 HTML 속성을 단독 근거로 쓰면 안 된다.
   실제로 `400x208`/`400x77` 시그니처로 74.56 GB 를 훑어 **0건**이었다.
   또한 `60x23`, `?x35` 같은 흔한 치수는 오탐만 낸다(각각 2건·15건 전부 오탐).
3. **이 볼륨의 `$LogFile` 은 2011년 데이터가 아니다.**
   VirtualBox 로 **2014-08-10 / 2020-10-23~24** 부팅된 이력이 있어 64 MB 순환 저널이 덮였다
   (VBox Guest Additions INF, MAC `0800271B6691`, `nSafeGuard_20201024_*`).
   → 아즈로크 가치는 `$MFT` 와 **미할당 영역**에 있고 저널에는 없다. 다시 파지 말 것.
4. **`$Bitmap` 실측**: 19,545,072 클러스터 중 할당 4,452,000(**22.78%**), 여유 61.8 GB.
   그중 약 26 GB 는 한 번도 쓰인 적 없고(regions 3–9, 50–63 = 0.00%),
   **약 35 GB 가 "쓰였다가 해제된" 진짜 카빙 대상**이다.
5. **메타데이터 고갈 ≠ 이미지 고갈.** `gameSession` 은 메타데이터에서 "없음"이었지만
   페이지파일/최대절전 영역에 프로세스 환경블록과 함께 온전히 남아 있었다.
   카빙 분류(Documents/Text/Other)에도 안 잡히는 자리다 — **원시 이미지 직접 스캔만이 답이었다.**

---

## 9. 보존 산출물

| 경로 | 내용 |
|---|---|
| `artifacts/objectWrite_funitto_20130406.js` | 원본 런처 JS (아카이브 회수, 25,261 B) |
| `artifacts/_img2011_pages/` | 이미지에서 추출한 캐시 HTML 실물 **31개** + `MANIFEST.md` (오프셋·MD5·title 기재) |
| `artifacts/_img2011_scan_20260720/` | 전수 스캔 2회분 결과 + 재현용 스크립트 |
| `artifacts/_img2011_popup_gif/` | 치수 카빙 산출 17개 — **전부 오탐**, 음성 근거로만 보존 |

---

## 10. 미해결 / 후속

- `cdn.funitto.com` 에 **진짜 이미지 바이너리가 살아 있다** — `images/gameplay/azroktcg/*`
  172 캡처 중 `image/gif` 41 + `image/jpeg` 3. 실물 확인: `azrok_contentsbg.gif` = GIF89a 669×9.
  아즈로크 **TCG** 자산이라 3D 광장과는 별개지만 회수 가치 있음. — 미착수
- `www.funitto.com/funnytoon/learning.main.screen` 7건 전부 200 / 약 17.9 KB 실본문.
  봉에너지 2번째 지급처(학습만화)라 내용 확인 가치 있음. digest 가 전부 달라 시기별 변화 있음. — 미착수
- 이미지 안에 `main.screen` HTML 이 1,064 벌 있으나 추출기가 `<html`~`</html>` 경계를 둘 다
  요구해 31개만 회수됐다. 경계 완화 또는 `<img ... width= height= src=>` 태그 직접 수확 시
  치수+파일명 대응표가 크게 늘어난다. — 미착수
- 사이트 이미지 대량 회수는 **카빙이 아니라 아카이브 다운로드**가 정답:
  `cdn.funitto.com` 1,228 + `file.funitto.com` 397 URL. 원본 파일명 보존, 오탐 0.
  카빙은 그 차집합(아카이브에 없는 것)에만 쓸 것.
