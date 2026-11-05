# Gate 5 — 두 브라우저 세션 Plaza 멀티플레이

날짜: 2026-07-22 KST

## 결론

- **VERIFIED (browser):** 동일한 StateBlock 수정 패키지를 `127.0.0.1`과 `localhost`의 분리된 브라우저 저장소에서 각각 실행해 두 원본 Azrok 세션을 동시에 Plaza에 진입시켰습니다.
- **VERIFIED (server):** `connected_clients=2`, `plaza_clients=2`였고 양쪽 모두 `peer_count=1`, `visible_remote_actor_count=1`이었습니다.
- **VERIFIED (browser + wire):** 양쪽 화면에 self와 remote 캐릭터 두 개가 실제로 렌더됐습니다. 두 번째 세션을 이동시키자 첫 번째 화면의 원격 캐릭터도 이동했고 서버는 첫 번째 세션으로 새 `S2C 0x0068`을 중계했습니다.
- **VERIFIED (browser + wire):** 두 번째 탭 종료 뒤 첫 번째 화면에서 원격 캐릭터가 제거됐고 `S2C 0x0067`, payload entity 14가 기록됐습니다. 탭은 다시 한 개만 남았습니다.

## 실행 구성

두 탭 모두 다음 자산을 사용했습니다.

- runtime: `boxedwine.nullcall1`
- app: `Azrok_D3D9Web_pathouse_stateblock1`
- root: `TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3`
- primary program: `run_azrok_seh.bat`, account `player`
- peer program: `run_azrok_peer111.bat`, account `peer111`

primary는 `http://127.0.0.1:8765`, peer는 `http://localhost:8765`로 열어 브라우저 저장소를 분리했습니다. 두 세션 모두 선택 화면 → PatHouse → 자연 `C2S 0x0019` 경로로 Plaza에 들어갔습니다.

## reciprocal roster 및 초기 위치

두 번째 세션 진입 직후 서버 기록은 다음과 같습니다.

```text
seq 1139  S2C 0066 -> entity 13, remote actor 1 record
seq 1140  S2C 0068 -> entity 13, remote position 1 record
seq 1141  S2C 0066 -> entity 14, remote actor 1 record
seq 1142  S2C 0068 -> entity 14, remote position 1 record
```

이 시점 상태:

```text
entity 13 / account player  / peer_count 1 / visible_remote_actor_count 1
entity 14 / account peer111 / peer_count 1 / visible_remote_actor_count 1
```

초기 좌표가 겹쳐 있어 한 캐릭터처럼 보였지만, 두 번째 세션에 Plaza 바닥 이동 입력을 주자 두 화면 모두 self와 remote의 두 캐릭터를 분리해 렌더했습니다.

## 이동 relay

두 번째 세션의 이동 뒤 첫 번째 세션에 다음 relay가 추가됐습니다.

```text
seq 1164  08:36:05.025  S2C 0068 -> entity 13
           payload 24 bytes, position record 1
```

첫 번째 화면에서도 remote 캐릭터가 오른쪽 아래 위치로 이동한 것을 직접 확인했습니다. 서버의 entity 13 `relay_tx_packets`도 2에서 3으로 증가했습니다.

## targeted leave

두 번째 탭만 닫은 뒤:

```text
seq 1178  08:36:29.968  S2C 0067 -> entity 13
           payload 4 bytes, removed entity_id 14
```

첫 번째 화면에서는 원격 캐릭터가 즉시 사라졌습니다. 최종 상태는 `connected_clients=1`, `plaza_clients=1`, primary의 `peer_count=0`, `visible_remote_actor_count=0`이며 브라우저 탭도 한 개입니다.

## 남은 범위

- **VERIFIED:** 별도 브라우저 원점 두 세션의 접속, reciprocal actor upsert, 위치 중계, targeted leave.
- **NOT VERIFIED:** 서로 다른 물리 PC/외부 LAN에서의 동일 시나리오. 서버의 `--bind` 및 방화벽 경계를 포함한 별도 실측이 필요합니다.
- **NOT VERIFIED:** Pointer Lock 카메라 회전과 Escape detach는 문서 251의 표준 브라우저 root-document 검증이 남아 있습니다.

