# Azrok Plaza - Windows 11 실행 가이드

Azrok Plaza는 2006~2008년경 제작된 **Acknex 7 엔진 (3D GameStudio)** 기반의 32비트 게임입니다.
현재 `ACCESS_VIOLATION (0xC0000005)` 오류로 크래시가 발생하고 있습니다.

아래 방법들을 **순서대로** 시도해 주세요.

---

## 방법 1: 호환성 모드 + 관리자 권한 (가장 먼저 시도)

1. `Azrok.exe`를 **마우스 오른쪽 버튼**으로 클릭 → **속성**
2. **호환성** 탭으로 이동
3. 다음 항목들을 체크:
   - **호환 모드에서 이 프로그램 실행**: `Windows XP (서비스 팩 3)` 선택
   - **축소된 색 모드**: `16비트 (65536) 색` 체크
   - **640 x 480 해상도로 실행** 체크
   - **관리자 권한으로 이 프로그램 실행** 체크
4. **적용** → **확인** 클릭 후 게임 실행

---

## 방법 2: DEP(데이터 실행 방지) 예외 추가

ACCESS_VIOLATION 오류의 주요 원인 중 하나가 DEP입니다.

1. **Windows 키 + R** → `sysdm.cpl` 입력 → 확인
2. **고급** 탭 → 성능 영역의 **설정** 클릭
3. **데이터 실행 방지** 탭 클릭
4. **다음 선택한 프로그램을 제외한 모든 프로그램에 대해 DEP 사용** 선택
5. **추가** 클릭 → `Azrok.exe` 파일 선택
6. **적용** → **확인** → **컴퓨터 재시작**

---

## 방법 3: DirectX 9.0c 런타임 설치

Acknex 7 엔진은 DirectX 9를 사용합니다. Windows 11에는 기본 포함되어 있지 않을 수 있습니다.

1. Microsoft 공식 사이트에서 **DirectX 9.0c End-User Runtime** 다운로드
   - 검색: `DirectX End-User Runtime Web Installer site:microsoft.com`
2. 다운로드 후 설치
3. 컴퓨터 재시작

---

## 방법 4: Visual C++ 런타임 설치

오래된 게임은 구버전 Visual C++ 런타임이 필요할 수 있습니다.

다음을 모두 설치해 주세요:
- **Visual C++ 2005 Redistributable (x86)**
- **Visual C++ 2008 Redistributable (x86)**

Microsoft 공식 다운로드 센터에서 검색하여 설치할 수 있습니다.

---

## 방법 5: dgVoodoo2 래퍼 사용 (그래픽 호환성)

오래된 DirectX 게임의 그래픽 호환성을 해결하는 도구입니다.

1. `dgVoodoo2` 검색 후 최신 버전 다운로드 (dege.freeweb.hu)
2. 압축 해제 후:
   - `dgVoodoo.conf` 파일을 Azrok_Plaza 폴더에 복사
   - `MS/x86` 폴더 안의 DLL 파일들을 Azrok_Plaza 폴더에 복사:
     - `D3D8.dll`
     - `D3D9.dll`
     - `D3DImm.dll`
     - `DDraw.dll`
3. `dgVoodooCpl.exe`를 실행하여 설정 조정
4. 게임 실행

---

## 방법 6: 전체화면 최적화 비활성화

1. `Azrok.exe` → 마우스 오른쪽 버튼 → **속성**
2. **호환성** 탭
3. **전체 화면 최적화 사용 안 함** 체크
4. 적용 후 게임 실행

---

## 추가 팁

- 게임 폴더를 **C:\Games\Azrok_Plaza** 같은 단순한 경로에 놓으세요 (한글/공백 없는 경로 권장)
- **바이러스 백신 실시간 보호**에서 게임 폴더를 예외로 추가하세요
- 위 방법이 모두 안 될 경우, **VirtualBox**나 **VMware**에 Windows XP를 설치하여 실행하는 것도 방법입니다
