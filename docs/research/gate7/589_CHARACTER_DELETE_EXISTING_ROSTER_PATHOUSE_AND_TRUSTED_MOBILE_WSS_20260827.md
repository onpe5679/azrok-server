# 589 — 중간 캐릭터 삭제, 기존 계정 신규 캐릭터 PatHouse, 신뢰 가능한 모바일 WSS

날짜: 2026-08-27

## 결론

- **VERIFIED:** 삭제 실패는 원본 클라이언트 요청 누락이 아니라 서버가 `slot == len(slots) - 1`인 마지막 논리 슬롯만 허용하던 정책 때문이었다. 운영 캡처에서 C2S `0006[01]` 네 건이 모두 archive 전 precondition에서 거부됐다.
- **VERIFIED:** 임의의 점유 논리 슬롯을 보존 archive로 이동한 뒤, 생존 레코드의 `storage_slot`과 파일명은 유지하고 wire용 논리 키만 `0..N-1`로 재밀집하도록 수정했다.
- **VERIFIED:** 운영 프로세스의 폐기 계정에서 슬롯 0/1/2 생성 후 가운데 슬롯 1 삭제가 S2C `0008[01,00]`으로 성공했고, 곧바로 새 논리 슬롯 2 생성도 731-byte 진입 응답으로 성공했다.
- **VERIFIED:** 기존 계정의 빈 슬롯에 새 캐릭터를 생성할 때 서버는 최초 `0003/0007/0005/000A/000B`를 보냈고 클라이언트가 tutorial `0011`까지 보냈지만 `0017/0008`로 진행하지 않았다. 같은 캐릭터를 다시 선택하면 정상 진행한 라이브 차이를 근거로, 기존 roster가 있던 생성에만 다음 heartbeat에서 C2S `0005` 선택 경로를 한 번 재생한다.
- **VERIFIED:** 운영 폐기 계정의 두 번째 캐릭터 생성에서 직접 응답 `0003/0007/0005/000A/000B` 뒤 다음 heartbeat가 `0016/0003/0007/0005/000A/000B`를 반환했다. 첫 계정 캐릭터에는 이 재생을 예약하지 않는다.
- **VERIFIED:** 모바일의 `연결이 종료되었습니다`는 코어 거부가 아니라 MagicDNS가 Tailscale IPv4의 자체서명 9201 리스너와 충돌해 TLS hostname 검증에 실패하던 경로였다. 충돌 리스너를 제거하고 동일한 신뢰 TLS 443의 `/azrok-ws`를 loopback bridge로 proxy했다.
- **VERIFIED:** `wss://<tailnet-host>/azrok-ws`의 인증서 SAN은 MagicDNS 이름과 일치하며, private ticket 로그인과 heartbeat에서 코어의 `0016 + 0004 + 0000` 405-byte 응답을 받았다. 실행기와 캐릭터 전환 재실행은 이 `ws` 값을 유지한다.
- **NOT VERIFIED:** 실제 물리 모바일 브라우저에서 원본 D3D 클라이언트가 PatHouse까지 렌더링하고 장시간 heartbeat를 유지하는 최종 사용자 수용 확인은 아직 필요하다.

## 변경

- `azrok_server.py`: 중간 슬롯 삭제 허용·논리 roster 재밀집, 기존 roster 신규 생성에 한한 one-shot post-create select replay.
- `tools/boxedwine_local/azrok_launch.js`: Tailscale IP/MagicDNS 접속 시 동일 TLS의 `/azrok-ws` 지정.
- `tools/boxedwine_local/index_d3d9web_pathouse.html`: 캐릭터 전환 재실행 시 `ws` 보존, `/azrok-ws` 연결 종료 추적.
- Tailscale Serve: `/ -> 127.0.0.1:8765`, `/azrok-ws -> 127.0.0.1:9201`; 이름 불일치 직접 `<tailscale-ip>:9201` 리스너 제거.

## 검증

- `python -m unittest discover -s tools -p 'test_*.py'` — **283/283 PASS**
- 운영 코어 재기동: `127.0.0.1:9200`, control `9300`, `playable`, `--auto-select-existing`.
- trusted WSS live: `[(0x0016,1), (0x0004,5), (0x0000,387)]`, 총 405 bytes.
- 기존 roster 두 번째 생성 live heartbeat replay: `0016,0003,0007,0005,000A,000B`.
- 가운데 슬롯 삭제 live ACK: `0008 payload=0100`; 이후 같은 논리 끝 슬롯 재생성 성공.
- 시험 계정 상태는 검증 후 full reset API로 복구 가능 archive 처리했다.

