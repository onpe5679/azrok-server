# 액세서리 2클라이언트 원격 set/clear relay live 종결 (2026-07-18)

표기: **VERIFIED**=원본 클라이언트 화면·실제 wire·canonical 또는 디컴파일로 직접 확인, **INFERRED**=호환 정책, **NOT VERIFIED**=후속 실측 필요.

## 결론

109의 액세서리 appearance 계층을 같은 Plaza 방의 원본 클라이언트 2개로 실측 종결했습니다. 송신자 `entity 2/player`가 slot0/value0을 장착하면 상대 `entity 3/peer111`에게 recipient-local actor id 2의 `S2C 0x000C`가 중계되고, 상대 화면의 원격 아바타 머리 위에 태양 효과가 나타났습니다. 해제도 동일한 actor id 2 delta로 중계됐고 상대 화면에서 효과가 사라졌습니다.

| 단계 | C→S sender | S→C sender | S→C peer relay | canonical |
|---|---|---|---|---|
| 장착 | capture seq143 `0018 000000` | `000C 01000000000000` | `000C 02000000000000` | `[00,FF,FF,FF]` |
| 해제 | capture seq290 `0018 010000` | `000C 01000000010000` | `000C 02000000010000` | `[FF,FF,FF,FF]` |

- **VERIFIED live** sender에게는 self actor id 1, peer에게는 보이는 원격 actor id 2가 사용됩니다.
- **VERIFIED live** set/clear 양쪽 모두 같은 방 peer에게 exact 7B `0x000C`로 중계됩니다.
- **VERIFIED live** 해제 뒤 서버 player snapshot과 canonical 4B는 모두 FF×4입니다.
- **VERIFIED live** 두 클라이언트 입장 시 양방향 `0x0066` baseline의 액세서리 4B도 FF×4였고 두 원격 아바타가 화면에 생성됐습니다.

## 원본 UI의 정확한 해제 선택 규칙

동적 실패를 정적 분석과 다시 대조해 해제 전제조건도 확정했습니다.

- catalogue 버튼 `0x1C5..0x1CC`는 장착 후보를 선택하면서 `CPopupAccessory+0x7AC`의 현재 장착 슬롯 선택을 `-1`로 지웁니다.
- 장착 버튼 `0x1D3`은 `FUN_005B2970(0)`으로 set을 보냅니다.
- self `0x000C` ACK 뒤 현재 장착 슬롯 버튼 `0x1CD..0x1D0` 중 해당 슬롯을 선택해야 합니다. slot0은 `0x1CD`입니다.
- 해제 버튼 `0x1D4`은 `FUN_005B2970(1)`이며, `+0x7AC==-1`이면 로컬 안내 code `0x1A`만 띄우고 wire를 보내지 않습니다.
- 정확한 slot0 순서는 `catalogue 0x1C5 → set 0x1D3 → self ACK → equipped slot 0x1CD → clear 0x1D4`입니다.

모든 버튼은 `FUN_005AFF90`, `ButtonQueue_Pop` return `0x005AFFC1`에서 소비되며 `param2/param3`는 사용하지 않습니다. 이 규칙은 첫 카탈로그 항목을 다시 선택한 뒤 바로 해제를 눌렀을 때 wire가 0건이었던 현상과, 장착 슬롯 선택 뒤 seq290 clear가 발생한 현상을 모두 설명합니다.

## 관제·도구 후속

- launcher에 격리 계정용 `--username`과 재사용 서버의 두 번째 원본 클라이언트 경로를 추가했습니다.
- elevated Frida allowlist는 exact accessory consumer에서 catalogue `0x1C5..0x1CC`, equipped slot `0x1CD..0x1D0`, set/clear `0x1D3/0x1D4`, modal confirm `0x02@0x005BE851`만 허용합니다.
- 관제 appearance projection은 active entity 패킷만 집계하도록 분리했고, `S2C 0x0065` reset 및 `0x0067` remove를 반영해 다중 클라이언트 self/remote 혼합과 퇴장 잔상을 막았습니다.
- inspector 최신 보고서는 13행, unknown 0, malformed 0이며 set/clear의 sender ACK와 peer relay를 모두 포함합니다.

## 증거

- `captures/packets_20260718_142936.txt` line 1280/1284/1288: 2클라이언트 set/ACK/relay
- `captures/packets_20260718_142936.txt` line 3050/3054/3058: 2클라이언트 clear/ACK/relay
- `artifacts/dynamic-analysis/accessory_peer_remote_set_20260718.bmp` SHA-256 `76179DDD7C7505928E43879C70A4869035DBF7ED96D784718B0E748149FB41B3`
- `artifacts/dynamic-analysis/accessory_peer_remote_clear_20260718.bmp` SHA-256 `C4DDF1E2458DB9FC1A1001F42EDB2419706F1BE79E8215C9A571973105E548AB`
- `tools/artifacts/packet_capture_accessory_two_client_live_20260718.json`
- `tools/artifacts/packet_capture_accessory_two_client_live_20260718.html`

주 `profile_playable_v2` PID104264 및 서버 PID106840은 이 격리 실측에서 변경하지 않았습니다. 주 profile SHA 3개도 111의 값과 동일합니다.

## 남은 경계

- **NOT VERIFIED live** set 상태로 재접속한 원본 클라이언트의 `S2C 0x0007 +0x1D4` 화면 복원과, 이미 set된 peer가 새로 입장할 때 `S2C 0x0066 +0x14` 화면 생성은 builder/contract test로는 검증됐으나 이번 화면 비교에는 포함하지 않았습니다.
- 액세서리 해금 권위의 exact 9행은 109에 고정됐지만, 서버의 forged locked-value 거부는 별도 구현·동적 음성 테스트가 필요합니다.

Related: 84, 105, 109, 110, 111, INDEX.
