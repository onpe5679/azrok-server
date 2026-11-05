# Wayback: 퍼니또(funitto.com) 봉에너지 지급 규칙 발굴

조사 개시: 2026-07-18
목표: Azrok Plaza "봉에너지" 웹 지급 규칙 (출석도장 / 학습만화 / 유료학습만화) 원문 확보

---

## www.funitto.com/game/azroktcg.*.screen (guide / help / item / main / story / notice)
- 상태: **전부 302** (14개 URL, CDX 전수 확인)
- CDX 확인: `url=funitto.com/game/*` 전 스냅샷 409건 중 statuscode 200 은 단 4건이며 모두 2021년 이후 도메인 스쿼팅 페이지(middle2/3/6.main.screen). azroktcg 계열은 200 스냅샷이 **하나도 없음**.
- 원인 추정: 로그인 게이트(`/mbr/mbr.login.screen?p_return_url=...`)로 리다이렉트. 크롤러가 비로그인이라 본문 미보존.
- 판정: **미아카이브 (본문 영구 소실)** — azroktcg.guide.screen / azroktcg.help.screen 이 봉에너지 규칙의 1순위 후보였으나 회수 불가.

## www.funitto.com/eventmgr/* (출석발도장 팝업)
- 상태: **302만**
- CDX 전수(`url=funitto.com/eventmgr` matchType=prefix): 스냅샷 총 3건
  - `20100315175115 .../eventmgr/071205/popup_stamp.jsp?bbsId=funny_study 302`
  - `20100529070846 .../eventmgr/071205/popup_stamp.jsp?bbsId=funny_study 302`
  - `20230615001355 .../eventmgr/newterm/newsc_event_01.jsp 307` (스쿼팅 시기)
- 판정: **미아카이브** — 출석도장 팝업 본문 없음. (리다이렉트 대상 추적 진행 중)

## www.funitto.com/funnytoon/learning.detail.screen?p_learning_id=LC000001 (2012-06-10)
- 상태: **본문확보** (131,758 byte, CP949)
- 발견 1: 출석도장 팝업을 여는 JS 함수가 **공용 include 에 남아 있음** (원문 그대로):
  ```js
  function goEvt071205() {
    var _pop071205 = window.open("/eventmgr/071205/popup_stamp.jsp?bbsId=funny_study", "MY_STAMP_071205", "top=10,left=50,toolbar=no,width=478,height=205,directories=no,status=no,menubar=no,scrollbars=no,resizable=no");
    _pop071205.focus();
  }
  ```
  - 창 크기 **478x205**, scrollbars=no → 도장판이 아니라 **단발 결과 알림 팝업** 규격. 이벤트 코드 `071205` = 2007-12-05 개시.
  - `bbsId=funny_study` → 학습(study) 게시판에 종속된 출석 이벤트.
  - 이 페이지 안에서 `goEvt071205()` 를 **호출하는 곳은 없음** (호출부 0건) → 배너/다른 페이지에서 호출.
- 발견 2: 페이지 내 봉에너지 언급 **없음**. "에너지" 문자열은 학습만화 제목 "과학대모험-에너지 편" 뿐. `아즈로크` 는 GNB 메뉴 링크 `아즈로크TCG` → `/game/azroktcg.main.screen` 하나뿐.
- 판정: **VERIFIED(원문 인용)** — 단, 봉에너지 수치 규칙은 없음. 팝업 규격만 확보.

## file.funitto.com/images/re_azrok/ (아즈로크 홈페이지 자산)
- 상태: 자산 목록 확보 (CDX, 60여 건 200)
- 발견: 이 디렉터리는 **오픈 전(pre-open) 티저 사이트**임. 근거 자산명:
  - `main_bn_preop.swf` (preop = pre-open 배너)
  - `start_goTester.swf` (테스터 모집)
  - `left_login_*`, `left_poll_*`(설문), `body_main_rak_*`(랭킹), `body_main_not_*`(공지), `body_bn_02stemp.gif`(출석도장 배너)
  - HTML 은 `html/azrok_screenshot.html` 단 1건만 아카이브됨 (200)
- 판정: INFERRED — 티저 사이트라 봉에너지 규칙 본문 가능성 낮음. 단 `body_bn_02stemp.gif` 는 아즈로크 홈페이지에도 출석도장 배너가 있었다는 **직접 증거**.

### ★ 정정 (위 re_azrok 항목)
- `file.funitto.com/images/re_azrok/**` 의 statuscode 200 은 **전부 가짜다.** CDX 에 mimetype 을 추가해 재조회한 결과 re_azrok 하위 스냅샷 **123건 전부 `text/html`** — .gif/.swf 인데 HTML.
- 직접 확인: `curl` 로 `20190412000540/.../body_bn_02stemp.gif` 를 받으니 `<!DOCTYPE html><html data-adblockkey=...` (도메인 파킹 페이지). `file` 판정도 `HTML document`.
- `html/azrok_screenshot.html` 도 스냅샷 3건(2014/2019/2019) 전부 파킹 페이지(parkingcrew.net, "funitto.com Buy this domain"). **실제 본문 아카이브 0건.**
- file.funitto.com 연도 분포: 2005:1, 2010:2, 2013:134, 2014:12, 2019:62, 2022:94 ... → 서비스 종료(2013-07-05) 이전 캡처는 2013년분 뿐.
- 판정: **미아카이브** — 단, URL 파일명 자체는 크롤러가 살아있던 시절 링크에서 수집한 것이므로 **아즈로크 홈페이지 구조의 간접 증거로는 유효**. 랭킹(`body_main_rak_*`), 공지(`body_main_not_*`), 설문(`left_poll_*`), 출석도장 배너(`body_bn_02stemp.gif`), 오픈전 배너(`main_bn_preop.swf`), 테스터 모집(`start_goTester.swf`) 메뉴가 있었다.

## azrok.co.kr / azrok.kr / azrok.com (별도 도메인 가설)
- azrok.co.kr, azrok.kr: **아카이브 0건**
- azrok.com: 아카이브 있으나 **미국 웹호스팅 업체**(All_hosting_plans.htm, whyazrok.htm, 2004년) — 무관
- 판정: 무관. "아즈로크 홈페이지"는 별도 도메인이 아니라 funitto.com 내부 경로였다.

## file.funitto.com/main/event.html (2013-07-03, 서비스종료 2일 전)
- 상태: **본문확보** (417 byte)
- 발견 (원문 그대로): `document.writeln("이벤트가 없습니다.");`
- 판정: VERIFIED — 종료 직전 진행 중 이벤트 0건. 출석도장 이벤트는 이 시점에 이미 종료됨.

## teaser.funitto.com / club.funitto.com / starmaru.funitto.com / azrok.hansol.com / funitto.co.kr / hansoledu.co.kr
- 상태: teaser/club/starmaru = **302만**(robots.txt 제외 전부). 나머지 3개 도메인은 **아카이브 0건**.
- 판정: 무관 / 미아카이브

## ★ 클라이언트 원본 데이터 교차검증 (wayback 아님, 수치 앵커용)
- `Data/Plaza/bee.npc` (CP949) 전문 디코드 — 봉에너지 관련 3줄 확인 (원문 그대로):
  - `봉에너지를 얻으려면 아즈로크 홈페이지에서 출석발도장 쾅쾅쾅!`
  - `봉에너지를 얻으려면 퍼니또 학습만화를 꼼꼼히 읽어보기!`
  - `퍼니또 유료학습만화에는 숨겨진 봉에너지가 있대~~ 소근소근~`
  - `웹에서 얻은 아이템은 장착 창의 “보관함” 에 있답니다.`
  - (관련) `아즈로크에 대한 자세한 내용은 게임가이드를 참고해보세요~` → 게임가이드 = `/game/azroktcg.guide.screen` (아카이브 소실)
  - (관련) `돈이 없다구요? 어서 아르바이트를 하러 펀콘공장으로 출발!!` → 펀콘(funcorn)은 **게임 내** 화폐. wayback 에 `file.funitto.com/images/alliance/img/game_funcorn_guide_btn.gif` 존재 = 제휴사이트에도 펀콘 가이드 버튼이 있었음.
- **수치 앵커 (VERIFIED, 원본 데이터파일)**:
  - `init.csv`: `봉에너지,50,0,300` → **초기값 50 / 최소 0 / 최대 300**
  - `lgc.tmp`: `봉에너지,0,0,300` → 신규 캐릭터 **0에서 시작**, 최대 300
  - `sys.tmp` 활동 델타: 놀이/마술/체육/독서/요리 **모든 활동이 봉에너지 -5** (예: `저글링,-5,-5,-5,5,-5,10,5,...,-5` 마지막 필드가 봉에너지)
  - → **최대치 300 = 활동 60회분.** 웹 지급량은 이 스케일(1회 수십 단위) 안에 있어야 함.
- 판정: VERIFIED(원본 데이터). 단 **지급량 자체는 서버/웹 측 값이라 클라이언트에 없음.**

## ★★ 핵심 종합: "지급 방식"은 확정됐다 — 에너지팩 아이템 지급이다
웹 아카이브가 아니라 **원본 클라이언트 데이터 교차검증**으로 지급 메커니즘이 닫혔다.

근거 체인 (전부 기존 VERIFIED 문서):
1. `Azrok.dat` 아이템 카탈로그 (content/71): **에너지 domain7 = 아이템 5000/5001/5002 "에너지팩 A/B/C" = 봉에너지 +300/+400/+500**, **가격 0 = 상점 판매 아님**.
2. `init.csv` / `lgc.tmp`: 봉에너지 최대 300 (기본 봉), 봉가구 B/C 장착 시 최대 500/600/700.
3. NPC 꿀풍(`Data/Plaza/bee.npc`): "웹에서 얻은 아이템은 장착 창의 **보관함**에 있답니다."
4. 봉에너지를 얻는 **게임 내 경로가 존재하지 않음** — 모든 활동은 봉에너지 -5 소비뿐(sys.tmp, content/76). 회복 수단은 에너지팩이 유일.
5. C→S `0x000F` = 에너지 아이템 사용, S→C `0x0009` ACK (content/108, live 실측).

→ **결론(INFERRED-강, 반증 없음): 웹(출석도장/학습만화)은 봉에너지 수치를 직접 주지 않았다. "에너지팩" 아이템을 캐릭터 보관함에 지급했고, 플레이어가 게임에서 그 아이템을 사용해 봉에너지를 회복했다.** ~~상점 가격 0(비매품)인 것이 이 해석의 결정적 근거.~~

> **★ 부분 정정 (2026-07-20). "가격 0 = 비매품" 이라는 근거는 철회한다 — 봉에너지는 웹 아이템샵에서 팔던 유료 상품이었다.**
>
> `file.funitto.com/js/menuLink.js`(아카이브 `20130406123349`, 30,867 B, 로컬 보존
> `artifacts/_funitto_js/menuLink.js`) 에 아이템샵 메뉴 라우팅이 **원문 그대로** 남아 있다:
> ```js
> //아이템샵-아즈로크아이템
> function menu06_09(){    location.href = ".../itemshop/marumong.screen"; }
> //아이템샵-아즈로크아이템-봉에너지          ← ★
> function menu06_09_01(){ ...marumong.screen?depth2_code=0401000&depth3_code=0402001 }
> //아이템샵-아즈로크아이템-봉아이템
> function menu06_09_02(){ ...depth3_code=0401001 }
> //아이템샵-아즈로크아이템-고급가구
> function menu06_09_03(){ ...depth3_code=0403001 }
> ```
> **`봉에너지` 는 아즈로크아이템 아래 독립 상품 카테고리다.** — VERIFIED (원문 인용)
>
> 즉 `Azrok.dat` 의 **가격 0 은 "비매품"이 아니라 "게임 내 상점에서 취급하지 않음"** 을 뜻한다.
> 판매처는 **웹 아이템샵**이었다. 아즈로크 메인의 `goMyItem()` 이
> `/itemshop/mypage.itemshop.**marumong**.buy.screen` 으로 가는 것과 같은 계열이며,
> **구매 → 마이페이지 → 게임 보관함** 파이프라인으로 읽힌다.
>
> **결론에 미치는 영향**: "에너지팩 아이템을 보관함으로 지급" 이라는 메커니즘 자체는 그대로 유효하다
> (근거 2·3·4·5 는 건재). 다만 **획득 경로가 3종이 아니라 최소 4종**이다 —
> 출석도장 / 무료학습만화 / 유료학습만화 / **유료 구매**.
> 따라서 아래 "출처 3종 ↔ 티어 3종(A/B/C) 대응" 추론은 **근거가 약해진다.**
> 티어 하나가 유료 구매 전용일 수도 있다. NOT VERIFIED 유지.
>
> **상품 목록·가격은 회수 불가.** `www.funitto.com/itemshop/marumong.screen*` 아카이브 **0건**,
> `itemshop/*` 는 6건 전부 **302**(로그인 필수). CDX 조회 완료.

→ **지급 단위(INFERRED): 1회 지급 = 에너지팩 1개 = 봉에너지 +300 / +400 / +500.**
   웹 지급 출처가 정확히 3종(출석도장 · 무료학습만화 · 유료학습만화)이고 에너지팩도 정확히 3티어(A/B/C)라는 대응이 가장 단순한 설명:
   - 출석발도장 → 에너지팩 A (+300)
   - 퍼니또 학습만화 정독 → 에너지팩 B (+400)
   - 퍼니또 **유료**학습만화 숨은 보상 → 에너지팩 C (+500)  ← "유료"가 최상위 티어인 것과 정합
   ⚠ 이 A/B/C↔출처 대응은 **NOT VERIFIED**. 티어 수와 출처 수가 일치한다는 정황일 뿐, 직접 증거 없음.

→ **하루 지급 횟수(INFERRED)**: 출석도장은 정의상 **1일 1회**. 에너지팩 A = +300 = 기본 봉 최대치 전량 = 활동 60회분. 즉 "하루 한 번 출석 → 하루치 활동 60회분 충전"이라는 설계로 앞뒤가 맞는다.

## 서버 재구현 권고 (이 조사의 실질 산출물)
웹 지급 규칙 원문은 회수 불가하므로, 서버는 다음을 구현하면 원본과 동등한 플레이 경험이 된다:
1. 로그인 시 **하루 1회** 캐릭터 보관함에 **에너지팩 A(item 5000) 1개** 지급 (출석도장 대체).
2. 에너지팩 B/C(5001/5002)는 별도 트리거(운영자 지급/퀘스트)로 열어둘 것.
3. 지급 위치 = 보관함(장착 창). 사용 시 C→S `0x000F`, ACK S→C `0x0009`, 봉에너지 +300/+400/+500.

## cdn.funitto.com — 아즈로크 사이트 이미지 자산 (실물 확보)
- 상태: **본문(이미지) 확보** — `images/gameplay/azroktcg/**` 중 image/gif·jpeg 200 인 21개 다운로드 성공 (나머지는 레이트리밋으로 실패, 재시도 가치 낮음)
- 발견 (이미지 내 한글 텍스트 판독):
  - `azrok_main_gamestart04.gif` = "게임시작 Game Start"
  - `azrok_sub01_title.gif` = "**공지사항/이벤트**", `azrok_sub01_index02.gif` = "공지"
  - `azrok_sub03_title.gif` = "**스크린샷**"
  - `azrok_sub05_title.gif` = "**카드소개**"
  - `azrok_sub06_index.gif` = "**순위 / 별명 / 점수**" (랭킹 테이블 헤더)
  - `login_join.gif` = "회원가입"
- 판정: VERIFIED(이미지 실물) — 단 이것은 **아즈로크 TCG(플래시 카드게임) 사이트**(2013년 캡처)이지 3D 아즈로크 광장 사이트가 아니다. 메뉴에 **출석/에너지 항목 없음.**
- ⚠ 혼동 주의: `azroktcg` ≠ 우리가 복원 중인 3D 아즈로크 광장. 두 게임은 사이트가 다르다.

## file.funitto.com/main/notice.html (2013-07-03)
- 상태: **본문확보** (1,400 byte). 종료 직전 공지 3건 제목만 (원문 그대로):
  - `알림] 퍼니또 캐쉬 환불 접..` → `/notice.view.screen?bbsId=1&messageId=270552`
  - `알림] 퍼니또 서비스 종료..` → `messageId=270456`
  - `안내] 학습 만화 서비스점..` → `messageId=254160`
- `notice.view.screen` 은 CDX 상 스냅샷 1건·302 → **공지 본문 전부 소실.**
- `adboard.html` = 빈 marquee, `sky_banner.html` = 빈 응답.
- 판정: VERIFIED(제목만) / 본문 미아카이브

## 웹 검색 병행 결과 (wayback 외)
- namu.wiki 「퍼니또」 전문 회수(429KB) — **"봉에너지" 문자열 0건.** 아즈로크 항목은 세계관·아즈론 설명 위주.
  - 다만 원문 인용: `다른 퍼니또의 게임들은 보존이 되어 영상이 남아있거나 실제 플레이가 가능하지만, 유독 이 게임만은 극소수의 스크린샷 몇 장을 제외하고 게임에 대한 정보가 거의 남아있지 않다.`
  - → **웹에 자료가 없다는 것 자체가 문서화된 사실.** 우리 조사의 음성 결과와 일치.
- 경향게임스 아즈로크 리뷰 2건(idxno=5965, 12420) 본문 확인 — 에너지/출석/학습만화 보상 언급 **0건**.
- 검색어 `"봉에너지" 아즈로크`, `아즈로크 봉에너지 채우는 방법` 등 6회 — **유효 결과 0건.**
- ⚠ 검색엔진 요약이 "학습만화로 얻은 아이템을 사용"이라 답한 건 **엔진의 합성 문장이고 원문 확인 불가** → 증거로 채택하지 않음.

---

# 최종 결론

1. **봉에너지 지급 수치(하루 몇, 행동당 몇)의 원문은 Internet Archive 에 존재하지 않는다.** 확정 근거:
   - 출석도장 팝업 `popup_stamp.jsp` 스냅샷 2건 전부 302
   - 아즈로크 게임가이드/도움말 `/game/azroktcg.{guide,help,item,main}.screen` 전 스냅샷 302 (로그인 게이트)
   - 아즈로크 홈페이지 자산 `re_azrok/**` 는 file/cdn 양쪽 모두 도메인 파킹 HTML (mimetype 검증)
   - 공지 본문 `notice.view.screen` 미아카이브
   - funitto.com 도메인 전체 pre-2014 고유 URL 1,221건 전수 확인 완료
2. **지급 "방식"은 확정에 근접했다** — 웹은 봉에너지 수치가 아니라 **에너지팩 아이템(5000/5001/5002)** 을 보관함에 지급했고, 게임 내 사용 시 +300/+400/+500 회복. 근거는 위 "핵심 종합" 절.
3. 서버 재구현은 "1일 1회 로그인 시 에너지팩 A 지급"으로 원본과 동등한 경험을 만들 수 있다.

---
# ★★★ 돌파구: 아즈로크 홈페이지 실물 확보 (2026-07-18 2차)

## 전제 정정
2011년 PC 덤프에서 바로가기 파일(.url)을 발굴 → 실제 접속 URL = `http://www.funitto.com/azrok/main.screen`.
**내가 1순위로 잡았던 `/game/azroktcg.*` 는 별개 게임(TCG)이었다.** 위쪽 "azroktcg 미아카이브" 판정은 유효하나 **애초에 잘못된 표적**이었음.

## www.funitto.com/azrok/** — 여전히 미아카이브
- CDX prefix 전수(www 유/무 모두): 스냅샷 **5건뿐, 전부 2019년 이후**
  - `/azrok/main.screen` (2019-04-12, 2019-04-22, 2023 307)
  - `/azrok/bbs.view.screen?bbsId=20&messageId=48578&...` (2019 ×2)
- 직접 확인: 2019 `/azrok/main.screen` 본문 = `<!DOCTYPE html><html data-adblockkey=...` + `Este dominio podría estar en venta!` → **도메인 파킹**. 본문 아님.
- 판정: www.funitto.com 쪽 아즈로크 홈페이지는 **미아카이브**.

## ★ funitto.jaeminara.co.kr/azrok/main.screen — 살아있는 시절 본문 확보!!
- `20120129125400 http://funitto.jaeminara.co.kr:80/azrok/main.screen text/html 200` — **112,996 byte 실제 본문** (파킹 아님, CP949 정상 디코드)
- 즉 **재미나라(한솔교육 자매 사이트) 미러가 funitto 본편보다 아카이브가 잘 되어 있다.** 앞으로 이 호스트를 1순위로 뒤질 것.
- 이 페이지 자체에는 봉에너지/출석/도장 문자열 **없음** (아즈로크 10회, 학습만화 1회).
- **메인 메뉴가 Flash 임**: `http://cdn.funitto.com/images/re_azrok/img/main_menu.swf` — 그래서 가이드/도움말 링크가 HTML 에 안 나온다. SWF 안에 URL 이 있을 것.
- ★ HTML 에서 회수한 **실제 아즈로크 홈페이지 경로들** (원문 그대로, 전부 신규 발견):
  - `/azrok/apply2.confirm.screen`
  - `/azrok/bbs.list.screen?bbsId=18&topIndex=02`
  - `/azrok/bbs.ranking.list.screen?topIndex=05`
  - `/azrok/bbs.shot.list.screen?bbsId=121&topIndex=06`
  - `/azrok/bbs.toon.list.screen?bbsId=23&topIndex=06`
  - `/azrok/azrokpoll.azrokpoll_result.screen?categoryId=2&pollId=2072`
  - `/azrok/policy.screen`
  - `/azrok/bbs.view.screen?bbsId=20&messageId=48578` (2019 CDX 에서)
  - 기타: `cdn.funitto.com/images/azrok/wmv/azrok_wmv9.wmv` (홍보 영상)
  - → `topIndex` 가 02/05/06 이므로 **01/03/04 가 미발견 메뉴**(게임소개/가이드/다운로드 추정). 여기에 봉에너지 규칙이 있을 가능성.
- 판정: **VERIFIED(본문 확보)**. 후속 조사 진행 중.

## /azrok/main.screen 본문 해부 (2012-01-29 + 2012-05-03, 두 스냅샷 내용 동일)

### ★ 출석도장 시스템 — 아즈로크 전용 엔드포인트 확인 (VERIFIED, 원문 인용)
아즈로크 홈페이지 메인에 출석도장 팝업 함수가 **`bbsId=azrok`** 로 존재한다:
```js
function goEvt071205() {
  var _pop071205 = window.open("/eventmgr/071205/popup_stamp.jsp?bbsId=azrok", "MY_STAMP_071205",
    "top=10,left=50,toolbar=no,width=478,height=205,directories=no,status=no,menubar=no,scrollbars=no,resizable=no");
  _pop071205.focus();
}
```
- 앞서 학습만화 페이지에서 찾은 것은 `bbsId=funny_study` 였다. → **동일한 출석도장 엔진(이벤트코드 071205)을 `bbsId` 파라미터로 사이트별 분기.** 아즈로크용 도장판이 별도로 있었다는 직접 증거.
- 창 규격 478x205 · scrollbars=no 동일.
- ⚠ `bbsId=azrok` 스냅샷은 **아카이브 0건**(prefix 전수: `bbsId=funny_study` 2건 302가 전부). 본문 소실.

```js
function goAttendance()
{
    alert("로그인이 필요한 서비스입니다.");
    location.href="/mbr/mbr.login.screen?p_return_url=/azrok/main.screen";
}
function goMyItem()
{
    alert("로그인이 필요한 서비스입니다.");
    location.href="/mbr/mbr.login.screen?p_return_url=/itemshop/mypage.itemshop.marumong.buy.screen";
}
```
- **`goAttendance()` 의 존재 자체가 "아즈로크 홈페이지에 출석 기능이 있었다"의 직접 증거** (NPC 대사와 일치).
- 크롤러가 **비로그인** 상태라 두 함수 모두 로그인 유도 분기만 렌더됐다. 로그인 분기(실제 출석 URL·지급량 표시)는 서버가 렌더하는 부분이라 **영구 소실**.
- 출석도장 배너 `body_bn_02stemp.gif`(289x95)는 페이지에 있으나 앵커가 **주석 처리**됨: `<!-- <a href="javascript:goMyItem();"> -->`.

### 배너/가이드 라우팅 (VERIFIED, 원문 인용)
```js
function goBanner( kind )
{
    if(kind == "check" ) {
        location.href = "/azrok/server.list.screen";
    } else if( kind == "guide") {
        //location.href = "/event.view.screen?bbsId=3&messageId=83623";
        //location.href = "/event.view.screen?bbsId=3&messageId=115431";
        location.href = "http://starmaru.funitto.com/star/starmaru.azrok.intro.screen";
    }
}
```
- 가이드 배너 최종 목적지 = `starmaru.funitto.com/star/starmaru.azrok.intro.screen` → CDX 전수: **아카이브 0건**(starmaru.funitto.com 은 robots.txt 80여건과 `star/starmaru.intro.screen` 302 7건이 전부).
- 주석 처리된 구(舊) 가이드 = `/event.view.screen?bbsId=3&messageId=83623`, `=115431` → event.view.screen 은 2021/2023 스쿼팅 캡처뿐, **live-era 본문 0건.**
- `openMsgBoxEvent()` → `http://file.funitto.com/azrok/popup/pop_op.html` (쿠키 `POPUP070417`) → `file.funitto.com/azrok` prefix CDX **0건**.
- 테스터 신청 배너 `fd_tester_banner.gif` → `/azrok/apply2.confirm.screen` (미아카이브)
- 공지 목록 `/azrok/bbs.list.screen?bbsId=18&topIndex=02`, 공지 본문은 `readNoticeMessage(id)` → POST-ish form submit to `/azrok/bbs.view.screen`. 회수된 공지 id: **136934, 142270, 152971, 181181, 183974** (전부 미아카이브)
- 아즈로크 메인 공지 제목(원문): `아즈로크 운영단 합격자 명단` / `[수정]아즈로크 유저운영단 모집` / `[수정] 게임시작 버튼을 눌러도 ..` / `광장서버 접속오류 수정 안내` / `<수정>광장서버 오류수정 안내`
- 랭킹 등급 명칭(원문): **골드론 / 실버론** (아즈론 랭킹 티어)

## ★ funitto.jaeminara.co.kr = 최고의 미러 (신규 확립)
- live-era `text/html 200` 페이지 **104건** 보존 (funitto.com 본편은 대부분 302).
- 회수 성공: `/azrok/main.screen`, `/notice.list.screen`, `/event.list.screen`, `/customer/main.screen`, `/intro.screen`, `/itemshop/main.screen`, 각 게임 `*.help.screen`/`*.itemshop.screen` 등.
- **후속 조사자는 funitto.com 이 아니라 이 호스트를 1순위로 쳐라.**

## 공지 목록에서 확정된 날짜 (VERIFIED)
`/notice.list.screen` (2012-06-10 캡처) 원문:
- `[안내] 아즈로크 서비스 종료 안내` — **messageId 254071, 2011.03.29, 조회 2903**
- `[안내] 학습 만화 서비스점검안내` — messageId 254160, 2011.04.01
- `[이벤트]추석맞이 경험치 2배! 아이템 2배!!` — messageId 244614, 2010.09.17
- → **아즈로크(3D)는 2011년 3~4월에 종료됐다. 퍼니또 전체 종료(2013-07-05)보다 2년 이상 빠르다.** 봉에너지 지급 웹 기능도 그때 함께 사라졌다.
- 공지 본문(`notice.view.screen?bbsId=1&messageId=254071`)은 두 호스트 모두 미아카이브.

## FAQ — 아즈로크 전용 분류 존재, 본문 미아카이브
`/customer/main.screen` 의 `mainCategory` select 원문 값:
`100 회원정보 · 108 캐쉬/퍼니/쿠폰 · 109 퍼니학습 · 110 별마루 · 111 퍼니짱 · 112 겜플레이 · 113 커뮤니티 · 114 아이템샵 · 115 검색 · 116 마이페이지 · 118 퀘스트/보상 · 120 접속/설치문의 · **148 아즈로크**`
- 봉에너지 규칙이 있었을 가장 유력한 자리 = FAQ 148(아즈로크) / 118(퀘스트·보상).
- FAQ 는 `faq.search.list.screen` **POST 폼** → 크롤러가 못 들어감. `/customer/` prefix CDX 결과 `main.screen` 2건이 전부. **본문 영구 소실.**

## 2차 최종 판정
아즈로크 홈페이지 본체는 회수했으나, **출석도장·가이드·FAQ·공지 본문은 전부 비로그인 게이트 또는 POST 폼 뒤에 있어 크롤러가 도달하지 못했다.** 봉에너지 지급 수치의 원문은 Internet Archive 에 존재하지 않는다 — 이번엔 올바른 표적(`/azrok/`)으로 확인한 결론이다.
지급 **방식**에 대한 결론(에너지팩 아이템 지급)은 위 "핵심 종합" 절 그대로 유효하며, 이번에 `goAttendance()` 실물 확인으로 "웹 출석 기능 실재" 부분이 VERIFIED 로 승격됐다.

---

# 3차 — `funitto.kids.yahoo.co.kr` (야후 꾸러기 제휴 호스트) 전수 조사 · 2026-07-18 artifact-probe

새로 지목된 광맥. `funitto.com` 게임 섹션이 302 로그인 게이트라 크롤러가 못 들어간 반면, 야후 제휴판은 **status 200 에 실제 본문**이 있다.

## 회수한 파일 (전부 `docs/research/_salvage/` 안에 저장됨)

**`_salvage/web_pages/`** — 신규 10개. 매니페스트: `web_pages/manifest_yahookids.txt` (`파일명|타임스탬프|URL|크기`)

| 파일 | 스냅샷 | 크기 | 내용 |
|---|---|---:|---|
| `yk_notice_198647.html` | 20090424085126 | 30,862 | 공지 `[까끌래뽀끌래2] 3,6,9 레벨업 이벤트` 2009.04.16 |
| `yk_notice_198649.html` | 20090424085132 | 30,862 | 공지 `[피쉬피버] 마의 점수를 돌파하라` 2009.04.16 |
| `yk_notice_list.html` | 20100317155757 | 38,974 | **공지목록 21건 전체 (제목·날짜·조회수)** |
| `yk_funcorn_guide.html` | 20060514090225 | 45,565 | **펀콘공장 게임 가이드 — 스토리·아즈론 종류·주문량** |
| `yk_gameplay_main.html` | 20060503224923 | 17,356 | 펀콘공장 게임 소개 |
| `yk_minigame_main.html` | 20060503224945 | 19,819 | **미니게임 6종 목록 (테로·뮤리 등장)** |
| `yk_introduction.html` | 20060503225031 | 19,157 | 퍼니툰 소개 |
| `yk_introduction_new.html` | 20060514074709 | 27,032 | 퍼니툰 소개(개정) |
| `yk_alliance_main2009.html` | 20090422153718 | 32,661 | 제휴 메인 2009 |
| `yk_billing.html` | 20100317155801 | 10,544 | 퍼니또 캐쉬 충전 페이지 |

**`_salvage/cdx/`** — 신규 3개: `cdx_funitto_yahookids.txt`(369행 전수), `cdx_alliance_azimg_full.txt`(0행), `cdx_cdn_yahoo_event.txt`(0행)

**`_salvage/web_images/`** — **신규 이미지 0개.** 사유는 아래 참조.

## 판정

### Y1. 야후 제휴 호스트 전수 — 200 인 고유 URL 120개 — VERIFIED
`matchType=domain` 전수 369행: **200=292 / 404=65 / 500=9 / 403=3.**
구성은 `azroktcg.*`(아즈로크TCG), `fishfever.*`, `kabo2.*`(까끌래뽀끌래2), `middle6.*`, `learning.*`, `sso/*`.
**아즈로크 광장(3D) 관련은 `azrok.main.screen` 단 1페이지뿐이며 이미 확보되어 있다.** 이 호스트는 야후에 얹은 **플래시 게임 라인업**이 본체다.

### Y2. 봉에너지·출석도장은 이 호스트에 없다 — VERIFIED (부정)
공지목록 21건 전체 제목을 확보했다(2009.05~2010.01 + 무날짜 1건). 전부 정기점검·이벤트·당첨자발표이며 **아즈로크 광장 관련 0건, 봉에너지/출석도장 0건.**
```
21 새해 복 많이 받으세요. 01.21 | 20 [공지] 퍼니또 8월 정기점검 안내 2009.08.18
19 [공지] 퍼니또 정기점검 안내 2009.07.15 | 18 [공지]아즈로크TCG 오픈 안내!! 2009.06.22
17 [이벤트]아즈로크TCG 오픈!! 2009.06.22 | 16 [공지]퍼니또 정기점검 안내 2009.06.16
15 [공지]서비스 임시 점검 안내 2009.05.29 | 14 [공지]정기점검 2009.05.20
13 [당첨자발표]피쉬피버 고고씽 챔피언 대회 2009.05.19 | 12 [이벤트]캐쉬파뤼~2탄! 2009.05.14 …
```
**부수 확정: 아즈로크TCG 오픈일 = 2009-06-22** (VERIFIED).

### Y3. 공지 본문은 이미지이며 미아카이브 — VERIFIED (부정)
`notice.view.screen` 본문 영역은 텍스트가 아니라 `<IMG src="http://cdn.funitto.com/images/alliance/yahoo/event/2009/0416/yahoo_funitto_event_cut22.jpg">` + 이미지맵이다.
`cdn.funitto.com/images/alliance/yahoo/event*` prefix CDX → **0건**. **공지 본문은 영구 소실**이다. 이 호스트에서 종료일을 얻을 수 없다.
(참고: `cdn.funitto.com/images/alliance/yahoo/common|gameplay/*` 은 2013 캡처가 200 으로 존재 — 이벤트 폴더만 안 잡혔다.)

### Y4. `az_wall_*` 등 제휴 이미지도 회수 불가 — VERIFIED (부정)
지목된 이미지 전체를 재확인했다. **원인은 기존 CDX 가 `collapse=urlkey` 라 URL 당 1개만 남긴 것이 아니었다** — collapse 를 빼고 개별 조회해도 스냅샷 자체가 1건뿐이다:
```
azrok_tit.gif : 20220514121356  unk  307  544 B   ← 유일 스냅샷
az_wall_img01/02, az_wall_btn_1024/1280/1600, az_wall_bg, azrok_txt_01/03,
azrok_link_img, azrok_line_01, azrok_shot_bg, upload/.../azrok_shot_01~03 : 전부 2022 캡처 307
azrok_txt_02.gif : 200 이지만 mimetype text/html = 파킹 페이지 (이미지 아님)
```
**전부 2022년(서비스 종료 후, 도메인 파킹 시점) 캡처다.** 서비스 당시 크롤이 없어 실물 이미지가 존재하지 않는다. 다운로드를 시도하지 않았고 `web_images/` 에 추가한 파일도 없다.

### Y5. ★ 신규 세계관 확정 — 벨라토리오 / 아즈론 / 퍼니 / 펀콘 — VERIFIED
`gameplay.main.screen`, `gameplay.funcornguide.screen` 원문:
> 환상의 섬, **벨라토리오** 섬에 사는 **아즈론**들은 “**퍼니**”를 먹고 사는데, 이 퍼니는 **펀콘 공장**에서 만들어진다. 아즈론 세계로 온 **제이풍**은 펀콘 공장을 맡아서 운영을 하게 되는데…
> 정해진 하루 운영 시간 내에 최대 양의 맛 좋은 퍼니를 만들어서 아즈론에게 주고 **게임 머니인 퍼니를 획득**하는 것이 게임의 성공 포인트!
> (가이드) 지상의 벌새가 우주를 향해 백 만년을 날아올라야 닿을 수 있는 환상의 섬 벨라토리오. **펀콘을 수확하여 먹을 수 있게 튀겨 아즈론에게 주는** 과정… 주문하러 들어오는 아즈론은 3종류, 펀콘을 tray 로 가져오는 아즈론 1종.

- **`펀콘`(원료 옥수수) → 튀김 → `퍼니`(완제품·게임머니)** 의 2단 구조가 확정됐다. 기존 문서가 `펀콘=funcorn=게임 내 화폐`로 본 것을 **정정**한다: 화폐는 `퍼니`이고 `펀콘`은 원료다 (VERIFIED, 단 이는 **야후판 펀콘공장 플래시게임 기준**이며 아즈로크 광장 본편의 `콘`(model+0x1F0)과 동일한지는 NOT VERIFIED).
- `bee.npc` 의 `돈이 없다구요? 어서 아르바이트를 하러 펀콘공장으로 출발!!` 이 가리키는 대상이 **이 펀콘공장 게임**임이 확정됐다.
- 무대 이름 **벨라토리오**, 주인공 **제이풍**은 이 프로젝트에서 처음 나온 설정이다.

### Y6. 야후 미니게임 6종은 아즈로크 캐릭터를 쓴다 — VERIFIED
`minigame.main.screen` 원문 6종: `도르레 구조대 / 빵빵 타자왕 / 도시락 특공대 / 우체부 허니비 / **청소맨 테로**(“테로의 아르바이트는 창문 가득 낀 거미줄을 없애는 것!”) / **버블다이브**(“**뮤리**가 발판들을 잘 이용해서…”)`
→ `테로`·`뮤리`는 `bee.npc` 의 4종족과 같은 이름이다. 아즈로크 세계관이 야후 플래시 미니게임으로 확장돼 있었다 (VERIFIED).

## 3차 최종 판정
**야후 제휴 호스트는 "200 본문"이라는 점에서는 새 광맥이 맞으나, 담긴 내용은 야후용 플래시 게임(TCG·피쉬피버·까끌래뽀끌래2·펀콘공장)이다.**
**서비스 종료일과 봉에너지/출석도장 규칙은 이 호스트에 없다** — 공지 본문이 전부 미아카이브 이미지이기 때문이며, 2차 판정("원문은 Internet Archive 에 존재하지 않는다")을 **뒤집지 못하고 재확인**한다.
수확은 **세계관·용어(Y5)와 캐릭터 확장(Y6), 아즈로크TCG 오픈일(Y2)** 이다.
