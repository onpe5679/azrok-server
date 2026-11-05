# Azrok Plaza Server Restoration / 아즈로크 광장 서버 복원

한국어 | [English](#english)

---

## 한국어

### 이 저장소는 무엇인가

**아즈로크(Azrok)** 는 한솔교육이 2008년경 서비스했던 어린이용 온라인 게임으로, 현재는 공식 서비스가 종료되어 원본 서버에 접속할 수 없습니다. 이 저장소는 원본 클라이언트(`Azrok.exe`)가 통신하던 서버 동작을 **클라이언트 바이너리의 정적·동적 분석만으로** 패킷 수준에서 다시 구현한 Python 서버와, 그 과정의 조사 기록 전체를 담고 있습니다.

- 목적은 서비스가 종료된 게임의 **보존(preservation)** 과 **상호운용성 연구**입니다.
- 상업적 이용을 하지 않습니다. 살아있는 상용 서비스를 대상으로 하지 않으며, 공격·침해·무단 접근을 목적으로 하지 않습니다.
- 한솔교육 및 퍼니또와 무관한 **비공식** 프로젝트입니다.

### 저장소 구성

| 위치 | 내용 |
|---|---|
| `azrok_server.py` | 게임 서버 본체 (TCP, 패킷 단위 구현) |
| `azrok_control.py`, `azrok_control_page.py`, `azrok_operator_page.py`, `azrok_admin*.py` | 루프백 제어 API와 운영자 화면 |
| `azrok_protocol_registry.py`, `check_registry.py` | opcode/프로토콜 레지스트리와 검증 |
| `azrok_private_access.py`, `azrok_network.py` | 비공개 접속(티켓, 계정 레지스트리)과 바인드 정책 |
| `azrok_launcher.py` | 원본 클라이언트를 실행해 서버에 연결 (Windows 전용) |
| `tools/` | 서버 실행 스크립트, WebSocket-TCP 브리지(`ws_tcp_bridge.py`), 정적 파일/API 서버(`boxedwine_local/server.py`), 테스트(`test_*.py`), x32dbg/Frida/Ghidra 보조 도구 |
| `ghidra_scripts/` | Ghidra 분석 스크립트 |
| `deploy/u32ws/` | 리눅스 서버 배포 예시 (systemd 유닛, 동기화 스크립트) |
| `web/` | 직접 작성한 서버 선택 페이지(`azrok_server_list.html/.css`)와 실행 연결 스크립트(`azrok_launch.js`). 이미지·미디어 자산은 포함하지 않습니다 |
| `docs/` | 조사 문서 전체 (아래 "문서 지도" 참고) |

### 로컬에서 실행하기

필요한 것:

- Python 3.11 이상. 서버 핵심 모듈(`azrok_*.py`)은 표준 라이브러리만 사용합니다. `websockets`는 WebSocket 브리지 도구에만, `frida`/`psutil`/`numpy`는 일부 연구 도구에만 필요합니다.
- **원본 클라이언트.** 이 저장소는 클라이언트와 게임 데이터를 포함하지 않습니다. 클라이언트 설치본은 archive.org 항목 https://archive.org/details/azrok-hansol-client-2008 에서 받을 수 있습니다.
- **서버가 읽는 클라이언트 설정 파일.** 아래 파일들은 모두 그 archive.org 항목의 `Azrok.zip` 안에, `Azrok.exe` 와 같은 폴더에 들어 있습니다. zip 을 풀어 **이 저장소의 루트 폴더(`azrok_server.py` 가 있는 폴더)** 에 복사하세요. `.gitignore` 에 등록되어 있어 실수로 커밋되지 않습니다.

  | 파일 | 용도 | 없으면 |
  |---|---|---|
  | `init.csv` | 캐릭터 기본 능력치 55행 (CP949). **필수** | `azrok_server.py` 가 import 시점에 읽으므로 서버를 import 할 수 없고, 대부분의 테스트도 실패합니다 |
  | `Azrok.dat` | 아이템 카탈로그(상점 품목·가격) | 서버는 뜨지만 상점 거래가 비활성화됩니다 |
  | `lgc.tmp` | 능력치 열 순서 참고용 | 서버 코드는 읽지 않습니다. `init.csv` 와 함께 두면 문서 대조에 편합니다 |

서버만 실행 (저장소 루트에서):

```text
python tools/run_server_only.py --bind 127.0.0.1 --port 9200 --control-port 9300 --content-profile playable
```

- `--bind` 는 루프백, RFC1918, Tailscale(`100.64.0.0/10`) 주소만 허용합니다. 공개 주소로는 바인드할 수 없습니다.
- 제어 API/운영자 화면은 `127.0.0.1:9300` (루프백 전용)에서 열립니다.
- `--content-profile` 은 `minimal` / `playable` / `shipped` 중 하나입니다.

클라이언트 연결 (Windows, 클라이언트 파일이 저장소 루트에 있어야 함):

```text
python azrok_launcher.py --reuse-server --port 9200
```

런처는 클라이언트 실행 파일을 디스크에서 수정하지 않고, 실행 중인 프로세스 메모리에 값을 써서 접속 정보를 전달합니다.

테스트:

```text
python -m unittest tools.test_server_contract_layers
```

- 위의 `init.csv` 가 루트에 있어야 대부분의 서버 테스트를 import 할 수 있습니다.
- 서버는 `B:` 드라이브가 있으면 `B:\Azrok_Captures` 에 패킷 캡처를 기록합니다. 테스트 전에 `AZROK_CAPTURE_DIR` 환경 변수를 임시 폴더로 지정하세요.
- `tools/test_packet_capture_inspector.py`, `tools/test_x32dbg_path.py` 는 `tools/` 폴더에서 실행해야 합니다.
- `tools/test_web_launch_contract.py` 의 두 항목은 브리지 저장소의 `index_d3d9web_pathouse.html` 이 있어야 실행되고, 없으면 건너뜁니다.
- `tools/test_private_browser_admission.py` 의 일부와 `tools/test_wmb6_minimap.py` 는 이 저장소에 없는 앱 패키지·게임 데이터가 필요합니다.

### 브라우저 포팅

원본 Windows 클라이언트를 브라우저에서 실행하는 BoxedWine 기반 포팅은 별도 저장소에 있습니다: https://github.com/onpe5679/boxedwine-d3d9web. 이 저장소의 `tools/ws_tcp_bridge.py` 와 `deploy/u32ws/` 는 그 포팅이 서버에 접속하는 경로를 설명합니다.

### 문서 지도

**시작점은 [`docs/research/INDEX.md`](docs/research/INDEX.md) 입니다.** 무엇이 확정된 사실인지 정리한 지도이므로, 새로 조사하기 전에 먼저 읽으세요.

| 문서 | 내용 |
|---|---|
| `docs/research/INDEX.md` | 확정 사실 지도 |
| `docs/research/REGISTRY.md` | 전체 조사 문서 등기부 (번호, 제목, 경로) |
| `docs/research/FAILED_EXPERIMENTS.md` | 실패한 시도와 그 이유 |
| `docs/research/<주제>/` | 주제별 상세 조사 (gate*, content, protocol, server, world, multiplayer, tooling, webport 등) |
| `docs/research/archive/`, `docs/archive/` | 뒤집히거나 낡은 문서. 삭제하지 않고 보존합니다 |
| `docs/CHRONICLE.md` | 시간순 연대기 |
| `docs/handoffs/` | 세션 인수인계 문서 |
| `docs/protocol_consolidated_2026-04-01/`, `docs/re/` | 초기 프로토콜 정리와 역분석 메모 |

각 사실에는 근거 등급이 붙어 있습니다.

- **VERIFIED** — 디컴파일 결과나 디버거 실측으로 직접 확인함
- **INFERRED** — 확인된 사실에서 추론함
- **NOT VERIFIED** — 아직 동적 확인이 필요함

기존 결론을 뒤집은 문서에는 맨 위에 `SUPERSEDED by NN` 배너를 남기고 `archive/` 로 옮겼습니다. 낡은 기록도 "왜 그때 틀렸는가"의 증거이므로 지우지 않았습니다.

문서에 나오는 `<tailscale-ip>`, `<lan-ip>`, `<tailnet-host>`, `<home>`, `<player01>` 같은 꺾쇠 표기는 공개 전에 개인·인프라 정보를 지우면서 넣은 치환 표시입니다. "개인 PC 사용 흔적 목록은 공개본에서 뺐다" 라는 줄은 같은 목적으로 목록을 덜어낸 자리입니다. `docs/research/webport/` 등에는 2012년 홈페이지 복원 작업을 다룬 문서가 있지만, 복원본 자체는 이 저장소에 없습니다.

문서는 이 저장소에 포함되지 않은 로컬 경로(`artifacts/`, `captures/`, `tools/boxedwine_local`, `logs/` 등)를 많이 인용합니다. 그 파일들은 공개본에 없습니다.

### 포함하지 않은 것

- 원본 클라이언트, 실행 파일, DLL, 게임 데이터(`.wmb`, `.mdl`, `.pcx`, `.wis`, `.tga`, 음원, 영상 등)와 `init.csv`, `Azrok.dat`, `lgc.tmp` (위 안내대로 클라이언트에서 직접 복사)
- **2012년 한솔교육/퍼니또 홈페이지 복원본(HTML/CSS/JS)과 그 이미지·미디어 자산.** `web/azrok_server_list.html` 이 참조하는 이미지도 포함하지 않았습니다
- 서버 상태, 서버 로그(`logs/`)와 도구가 남긴 `*.log` 파일(문서가 인용한 로그 원본 포함), 패킷 캡처, 계정 데이터, 접속 토큰, 실제 터널 설정
- 5 MB를 넘는 바이너리 증거 파일

### 보존 및 비상업 선언, 삭제 요청

이 저장소는 서비스가 종료된 게임을 보존하고 상호운용성을 연구하기 위한 것이며 상업적 목적이 없습니다. 게임의 저작권과 상표는 각 권리자에게 있습니다. 한솔교육이 삭제를 요청하는 경우 perion5679@naver.com 로 알려 주세요.

### 라이선스

문서 라이선스: CC BY 4.0 (docs/ 아래), 코드: MIT

- 코드: MIT, `Copyright (c) 2026 onpe5679` ([`LICENSE`](LICENSE))
- 문서(`docs/` 아래): CC BY 4.0 ([`docs/LICENSE`](docs/LICENSE)). 문서가 인용한 외부 자료와 게임 자체의 권리는 각 권리자에게 있습니다.

---

## English

### What this is

**Azrok** is a children's online game published by Hansol Education around 2008. The official service has ended and the original servers are unreachable. This repository contains a Python re-implementation of the server behaviour that the original client (`Azrok.exe`) expects, built **packet by packet from static and dynamic analysis of the client binary alone**, together with the full record of that investigation.

- Purpose: **preservation** of a discontinued game and **interoperability research**.
- Non-commercial. It does not target any live commercial service and is not intended for attack, intrusion or unauthorised access.
- This is an **unofficial** project with no affiliation to Hansol Education or Funitto.

### Layout

| Path | Contents |
|---|---|
| `azrok_server.py` | The game server (TCP, packet-level) |
| `azrok_control.py`, `azrok_control_page.py`, `azrok_operator_page.py`, `azrok_admin*.py` | Loopback control API and operator pages |
| `azrok_protocol_registry.py`, `check_registry.py` | Opcode/protocol registry and its checks |
| `azrok_private_access.py`, `azrok_network.py` | Private access (tickets, account registry) and bind policy |
| `azrok_launcher.py` | Starts the original client and connects it to the server (Windows only) |
| `tools/` | Server runner, WebSocket-to-TCP bridge (`ws_tcp_bridge.py`), static file/API server (`boxedwine_local/server.py`), tests (`test_*.py`), x32dbg / Frida / Ghidra helpers |
| `ghidra_scripts/` | Ghidra analysis scripts |
| `deploy/u32ws/` | Example Linux deployment (systemd units, sync script) |
| `web/` | Hand-written server-selection page (`azrok_server_list.html/.css`) and launch script (`azrok_launch.js`). Image and media assets are not included |
| `docs/` | The complete research record (see "Documentation map") |

### Running the server locally

You need:

- Python 3.11 or newer. The core server modules (`azrok_*.py`) use only the standard library. `websockets` is needed only by the WebSocket bridge tools, and `frida` / `psutil` / `numpy` only by some research tools.
- **The original client.** This repository ships neither the client nor any game data. Get the client installation from the archive.org item https://archive.org/details/azrok-hansol-client-2008.
- **Client configuration files that the server reads.** All of them are inside that archive.org item's `Azrok.zip`, in the same folder as `Azrok.exe`. Copy them into the **repository root (the folder that contains `azrok_server.py`)**. They are listed in `.gitignore`, so they will not be committed by accident.

  | File | Purpose | If missing |
  |---|---|---|
  | `init.csv` | 55 rows of default character stats (CP949). **Required** | `azrok_server.py` reads it at import time, so the server cannot be imported and most tests fail |
  | `Azrok.dat` | Item catalog (shop items and prices) | The server starts, but shop transactions are disabled |
  | `lgc.tmp` | Stat column order, for reference | The server code does not read it; keeping it next to `init.csv` helps when cross-checking the docs |

Run the server only (from the repository root):

```text
python tools/run_server_only.py --bind 127.0.0.1 --port 9200 --control-port 9300 --content-profile playable
```

- `--bind` accepts only loopback, RFC1918 and Tailscale (`100.64.0.0/10`) addresses. Public addresses are rejected.
- The control API and operator pages listen on `127.0.0.1:9300` (loopback only).
- `--content-profile` is one of `minimal`, `playable`, `shipped`.

Connect the client (Windows; the client files must be in the repository root):

```text
python azrok_launcher.py --reuse-server --port 9200
```

The launcher does not modify the client executable on disk; it passes the connection values by writing into the running process.

Tests:

```text
python -m unittest tools.test_server_contract_layers
```

- Most server tests can only be imported when `init.csv` is in the repository root, as above.
- If drive `B:` exists, the server writes packet captures to `B:\Azrok_Captures`. Set the `AZROK_CAPTURE_DIR` environment variable to a temporary folder before running tests.
- `tools/test_packet_capture_inspector.py` and `tools/test_x32dbg_path.py` must be run from inside `tools/`.
- Two cases in `tools/test_web_launch_contract.py` need the bridge repository's `index_d3d9web_pathouse.html` and are skipped without it.
- Part of `tools/test_private_browser_admission.py` and `tools/test_wmb6_minimap.py` need app packages or game data that are not in this repository.

### Browser port

The BoxedWine-based port that runs the original Windows client in a browser lives in a separate repository: https://github.com/onpe5679/boxedwine-d3d9web. `tools/ws_tcp_bridge.py` and `deploy/u32ws/` here describe how that port reaches this server.

### Documentation map

**Start at [`docs/research/INDEX.md`](docs/research/INDEX.md).** It is the map of what is established as fact; read it before investigating anything new.

| Document | Contents |
|---|---|
| `docs/research/INDEX.md` | Map of established facts |
| `docs/research/REGISTRY.md` | Registry of all research documents (number, title, path) |
| `docs/research/FAILED_EXPERIMENTS.md` | Failed attempts and why they failed |
| `docs/research/<topic>/` | Detailed investigations by topic (gate*, content, protocol, server, world, multiplayer, tooling, webport, ...) |
| `docs/research/archive/`, `docs/archive/` | Superseded or outdated documents, kept on purpose |
| `docs/CHRONICLE.md` | Chronological narrative |
| `docs/handoffs/` | Session hand-off documents |
| `docs/protocol_consolidated_2026-04-01/`, `docs/re/` | Early consolidated protocol notes and reverse-engineering notes |

Every claim carries an evidence grade:

- **VERIFIED** — confirmed directly, by decompiled code or a debugger measurement
- **INFERRED** — reasoned from verified facts
- **NOT VERIFIED** — still needs dynamic confirmation

When a conclusion was overturned, the old document got a `SUPERSEDED by NN` banner at the top and was moved to `archive/`. Nothing was deleted, because an outdated record is also evidence of why it was wrong.

Angle-bracket tokens such as `<tailscale-ip>`, `<lan-ip>`, `<tailnet-host>`, `<home>` and `<player01>` are placeholders inserted to remove personal and infrastructure details before publication. A line such as "(개인 PC 사용 흔적 목록은 공개본에서 뺐다)" ("the list of personal-PC traces was left out of the public copy") marks a place where a list was removed for the same reason. Some documents (for example under `docs/research/webport/`) describe the work on restoring the 2012 homepage; the restored homepage itself is not in this repository.

Many documents refer to local paths (`artifacts/`, `captures/`, `tools/boxedwine_local`, `logs/`, ...) that are not shipped in this repository.

### Not included

- The original client, executables, DLLs and game data (`.wmb`, `.mdl`, `.pcx`, `.wis`, `.tga`, audio, video, ...), and `init.csv`, `Azrok.dat`, `lgc.tmp` (copy them from the client as described above)
- **The restored 2012 Hansol Education / Funitto homepage (HTML/CSS/JS) and its image and media assets.** The images that `web/azrok_server_list.html` refers to are not included either
- Server state, server logs (`logs/`) and tool-generated `*.log` files (including the original logs that the docs cite), packet captures, account data, access tokens and the real tunnel configuration
- Binary evidence files larger than 5 MB

### Preservation statement and takedown contact

This repository exists to preserve a discontinued game and to study interoperability. It has no commercial purpose. Copyrights and trademarks in the game belong to their respective owners. If Hansol Education asks for removal, please contact perion5679@naver.com.

### License

문서 라이선스: CC BY 4.0 (docs/ 아래), 코드: MIT — Documentation license: CC BY 4.0 (under `docs/`); code: MIT.

- Code: MIT, `Copyright (c) 2026 onpe5679` ([`LICENSE`](LICENSE))
- Documentation (under `docs/`): CC BY 4.0 ([`docs/LICENSE`](docs/LICENSE)). Rights in material quoted by the documents, and in the game itself, remain with their respective owners.
