# canonical revision·exact SHA·transaction receipt GUI (2026-07-18)

> **DURABLE JOURNAL GAP SUPERSEDED by 118.** P1a revision/SHA/receipt 결론은 유효하며, RAM-only 한계와 P1b 저널 상태는 118을 따릅니다.

표기: **VERIFIED test**=회귀/실패 주입, **VERIFIED runtime**=격리 control API, **VERIFIED browser**=실제 관제 페이지 렌더, **NOT VERIFIED durable**=재시작 후 audit 보존은 아직 미구현.

## 결론

105/114의 대개편 P1 중 가장 작은 안전 단위인 **P1a canonical commit receipt**를 구현했습니다.

- 모든 canonical 성공 저장은 중앙 `_save_canonical_character_state`에서 revision을 1 증가시킵니다.
- 실제 교체 전 파일 raw bytes SHA256과 실제 기록할 deterministic UTF-8 JSON bytes SHA256을 transaction에 기록합니다.
- `os.replace` 성공 뒤에만 cache/revision/commit receipt가 갱신됩니다.
- transaction은 `tx-########`, mutation kind/result, opaque `chr_*`, selected-key validity, opcode/packet seq, revision before/after, SHA before/after, changed field path, reason을 가집니다.
- 계정/캐릭터 hex가 포함된 raw canonical key는 transaction/event GUI에 넣지 않습니다.
- canonical JSON에는 자기참조 digest를 넣지 않고 `revision`만 저장합니다.
- GUI의 영속성 카드에 schema/revision/SHA256을, 최근 commit/reject 카드에 `tx · kind · result · rN→rN+1`을 표시합니다.

## 1. 적용 mutation

**VERIFIED test** 중앙 save caller에 다음 kind와 최소 changed field를 연결했습니다.

- `character_create` / C2S0004
- `state_snapshot` / C2S0007
- `purchase` / C2S0013
- `energy_consume` / C2S000F
- `active_loadout` / C2S000D/E
- `accessory` / C2S0018
- `legacy_snapshot_migration`
- 테스트/관리용 기본 `canonical_save`

구매·item-use·state save·accessory의 load 이전 fail-closed reject도 revision/SHA를 읽거나 변경하지 않는 reject receipt를 남깁니다. canonical save 자체의 validation/hash/write/replace 실패도 rejected transaction으로 남고 revision은 증가하지 않습니다.

## 2. 정확 파일 digest와 revision 계약

**VERIFIED test**:

1. fresh canonical revision0 → 첫 저장 revision1 → 둘째 저장 revision2.
2. transaction `sha256_after`가 실제 파일 raw bytes SHA256과 일치.
3. 둘째 transaction `sha256_before`가 첫 파일 SHA와 일치.
4. 주입한 `os.replace` 실패 뒤 파일 bytes/revision/cache는 불변이고 commit receipt는 생기지 않으며 reject receipt만 생김.
5. invalid/negative/non-integer stored revision은 `_revision_valid=False`로 로드돼 다음 mutation을 fail-closed 처리.

## 3. API와 GUI

- `AzrokServer.snapshot().transactions`: bounded RAM ring 500.
- 기존 event ring에도 `kind=transaction`을 넣어 `/api/events` cursor가 receipt를 운반합니다.
- `/api/state`와 `/api/overview`의 operator에 최근 transaction 12건을 노출합니다.
- canonical read-only summary는 raw bytes를 한 번만 읽어 `schema_version`, `revision`, exact SHA256을 계산하며 파일을 수정하지 않습니다.
- 기존 `schema` 오독을 `schema_version`으로 교정했습니다.

**VERIFIED runtime** 격리 B: profile/control probe:

- canonical revision `1`, currency `321`
- `tx-00000001`, kind `runtime_probe`, committed, revision `0→1`
- transaction after SHA == API canonical SHA
- raw key exposed `false`
- `/api/overview`도 revision1/transaction1 일치

**VERIFIED browser** 실제 `http://127.0.0.1:9304/` 렌더에서 다음을 확인했습니다.

- 영속성 카드: `REVISION 1`, `SHA256 fc0a31366726…`, `SCHEMA 1`
- 최근 commit/reject: `tx-00000001 · runtime_probe · committed · r0→r1`
- timeline transaction 세부 envelope
- 브라우저 console error `0`

## 4. 회귀

- `python -m py_compile azrok_server.py azrok_control.py azrok_control_page.py ...` PASS.
- C: 여유 공간 복구 뒤 기본 TEMP에서 `python -m unittest discover -s tools -p 'test_*.py' -q` **133 tests PASS**.

## 남은 P1b/P1c

- **NOT VERIFIED durable** transaction ring은 RAM bounded receipt이며 재시작 후 보존되는 append-only journal이 아닙니다.
- 캐릭터 삭제 archive는 다중 move/rollback이므로 별도 P1b transaction으로 분리합니다.
- admin expected-revision CAS preview/commit은 writer가 생기는 단계에서 별도 구현합니다.
- 단일 protocol registry source는 별도 P1c로 진행합니다.

Related: 84, 90, 104, 105, 108, 109, 114, 115, INDEX.
