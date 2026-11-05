> **SUPERSEDED by 591.** 터치를 브라우저 MouseEvent로 우회한 결론은 물리 모바일 재검증에서 기각됐다. PC context menu 차단만 유효하다.

# 590 — 모바일 터치 좌표 일원화와 게임 우클릭 메뉴 차단

날짜: 2026-08-27

## 결론

- **VERIFIED:** 모바일 오입력의 직접 원인은 같은 손가락 입력이 raw SDL touch 경로와 브라우저 호환 mouse 경로로 중복될 수 있고, raw touch 좌표는 CSS 픽셀인 반면 BoxedWine mouse 좌표는 canvas backing-store 비율로 환산된다는 좌표 권한 불일치였다.
- **VERIFIED:** 게임 canvas의 `touchstart/move/end/cancel`을 capture 단계에서 받아 raw touch 전달과 후속 호환 mouse 생성을 막고, 표시 사각형의 CSS 좌표를 `canvas.width/height` 내부 픽셀로 한 번만 환산한 mouse 이벤트로 전달하도록 수정했다.
- **VERIFIED:** pointer→mouse 보완 경로는 실제 mouse pointer에만 제한했다. 터치 입력은 위 전용 경로만 소유하므로 한 번의 손가락 입력이 두 mouse down으로 중복되지 않는다.
- **VERIFIED:** 게임 실행 영역의 `contextmenu`를 window capture 단계에서 취소하고 전파도 중단한다. 별도 실제 실행 탭에서 canvas를 우클릭한 뒤 캡처했을 때 Chromium 기본 메뉴가 나타나지 않았다.
- **VERIFIED:** `touch-action:none`, `-webkit-touch-callout:none`, `user-select:none`을 게임 컨테이너와 canvas에 적용해 모바일 길게 누르기 메뉴·선택 UI를 억제했다.
- **NOT VERIFIED:** 실제 물리 모바일 기기에서 캐릭터 생성부터 PatHouse 조작까지 장시간 플레이하며 모든 버튼의 체감 좌표가 맞는지는 사용자 실기기 재확인이 필요하다.

## 변경

- `tools/boxedwine_local/index_d3d9web_pathouse.html`
  - raw SDL touch를 capture 단계에서 차단.
  - CSS 좌표 → canvas backing-store 좌표 → 픽셀 중심 browser mouse 좌표로 단일 변환.
  - touch start/move/end/cancel을 각각 mouse down/move/up으로 연결.
  - mouse pointer fallback에서 touch/pen을 제외.
  - 실행 중 게임 영역의 context menu를 window capture 단계에서 차단.
  - 모바일 callout과 텍스트 선택 억제.
- `tools/test_d3d9web_page_contract.py`
  - 단일 touch 소유권, backing-store 비율 환산, 픽셀 중심, 종료 좌표, context menu capture 계약 추가.

## 검증

- `python -m unittest tools.test_d3d9web_page_contract` — **24/24 PASS**
- `python -m unittest discover tools` — **283/283 PASS**
- 실제 Chromium 별도 실행 탭에서 `#canvas` 우클릭 후 화면 캡처 — **기본 context menu 없음**.
- URL-gated `runtime-status.dataset.mobileTouchGuest`에 최종 내부 좌표를 남겨 물리 모바일 후속 실측이 가능하다.
