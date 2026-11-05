# 아즈록 플라자 (Azrok Plaza) - Windows 11 실행 패치 기록

**게임:** 아즈록 플라자 (한솔교육, 2006~2008)
**엔진:** Acknex 7 (3D GameStudio) + MFC 8.0 + .NET
**원본 파일:** Azrok_original.exe (MD5: eac34b226ff54bcd2621a2c2178af577)

---

## 증상

Windows 11에서 실행 시 한솔교육 로고가 잠깐 나타난 후 즉시 크래시. 원인은 온라인 서버 폐쇄로 인한 초기화 실패 + MSVC 2005 CRT 보안 기능의 연쇄 반응.

---

## 적용된 패치 (총 5개)

### Patch 1: IsInitialized() 우회
- **위치:** VA 0x4D7B90 (file offset 0x1B90)
- **원본:** `E9 6B 85 0D 00` (jmp 0x5B0100)
- **패치:** `B0 01 C3 90 90` (mov al, 1; ret)
- **설명:** 서버 연결 상태를 확인하는 IsInitialized() 함수가 28곳에서 호출됨. 서버가 폐쇄되어 항상 false를 리턴하므로, 항상 true를 리턴하도록 패치.

### Patch 2+3: strcpy NULL 포인터 안전 처리
- **위치 (리다이렉트):** VA 0x654425 (file offset 0x17E425)
- **원본:** `8B 4C 24 0C F7 C1 03 00 00 00`
- **패치:** `E9 7E 00 00 00 90 90 90 90 90` (jmp trampoline)
- **위치 (트램폴린):** VA 0x6544A8 (file offset 0x17E4A8), INT3 패딩 영역 활용
- **패치 내용:** `8B 4C 24 0C 85 C9 74 0B F7 C1 03 00 00 00 E9 74 FF FF FF C6 07 00 8B 44 24 08 5F C3`
- **설명:** CRT strcpy에 NULL 소스 포인터가 전달될 때 Access Violation 대신 빈 문자열을 반환하도록 NULL 체크 트램폴린 삽입.

### Patch 4: _invoke_watson 강제 종료 제거
- **위치:** VA 0x650D6E (file offset 0x17AD6E)
- **원본:** `68 0D 00 00 C0 FF 15 38 02 6F 00 50 FF 15 20 03 6F 00` (push STATUS_INVALID_PARAMETER; call GetCurrentProcess; push eax; call TerminateProcess)
- **패치:** 18바이트 NOP (0x90)
- **설명:** MSVC 2005 CRT의 invalid parameter handler가 TerminateProcess를 호출하여 프로세스를 즉시 종료시키던 것을 제거. 함수가 정상 리턴하도록 변경.

### Patch 5: [eax+0x74] NULL 객체 포인터 체크
- **위치 (리다이렉트):** VA 0x5F06A6 (file offset 0x11A6A6)
- **원본:** `8B 48 74 C7 41 1C 00 40 00 00`
- **패치:** `E9 1C 02 00 00 90 90 90 90 90` (jmp trampoline)
- **위치 (트램폴린):** VA 0x5F08C7 (file offset 0x11A8C7)
- **패치 내용:** `8B 48 74 85 C9 74 07 C7 41 1C 00 40 00 00 E9 D6 FD FF FF`
- **설명:** 초기화되지 않은 객체 멤버(offset 0x74)가 NULL일 때 [ecx+0x1C] 쓰기를 건너뜀.

### Patch 6: [ebp-4] this 포인터 NULL 체크
- **위치 (리다이렉트):** VA 0x59D3A9 (file offset 0xC73A9)
- **원본:** `8B 4D FC 8B 91 F4 05 00 00`
- **패치:** `E9 D1 00 00 00 90 90 90 90` (jmp trampoline)
- **위치 (트램폴린):** VA 0x59D47F (file offset 0xC747F)
- **패치 내용:** `8B 4D FC 85 C9 74 0B 8B 91 F4 05 00 00 E9 21 FF FF FF E9 32 FF FF FF`
- **설명:** this 포인터([ebp-4])가 NULL일 때 [ecx+0x5F4] 읽기를 건너뛰고 return 0 경로로 이동.

---

## 결과

- EXIT CODE: 0 (정상 종료)
- 크래시 없음 (Azrok.txt 미생성 확인)
- 게임이 서버 접속 단계까지 정상 도달
- 현재 "서버와의 연결이 종료되었습니다" 메시지 출력 (서버 폐쇄로 인한 정상 동작)

---

## 패치 기법 요약

모든 패치는 **트램폴린 기법**을 사용: 원본 코드를 JMP로 대체 → INT3(0xCC) 패딩 영역에 NULL 체크 코드 삽입 → 원본 로직 수행 또는 안전 경로로 분기 → JMP로 원래 위치 복귀. 원본 코드의 기능을 최대한 보존하면서 NULL 포인터 역참조만 방지.
