# Structured packet capture and run manifest (2026-07-18)

## 결론

- **VERIFIED (code/test):** 기존 사람용 `captures/packets_*.txt`와 `packets_log.txt`를 유지하면서 실행별 `packets.jsonl`과 `manifest.json`을 추가했습니다.
- **VERIFIED:** `AZROK_CAPTURE_DIR`가 최우선이고, 미지정 시 B 드라이브가 있으면 `B:\Azrok_Captures`, 아니면 workspace `captures_structured`입니다. D 드라이브는 확인하지 않습니다.
- **VERIFIED:** capture-local sequence는 lock 아래 단조 증가하며 각 append는 `flush + fsync`합니다. payload/raw SHA-256, wall/Unix-ns time, direction/opcode, registry/spec semantics, entity/room metadata를 기록합니다.
- **VERIFIED:** 매 fsynced packet 뒤 manifest counter도 갱신하며 현재 writer PID를 기록합니다. 시작 시 죽은 writer의 열린 manifest는 `unclean_shutdown`으로 reconciliation하고 `recovered_utc`를 남기되 존재하지 않은 정상 `ended_utc`를 꾸며내지 않습니다.
- **VERIFIED:** 로그인, 캐릭터 생성/이름, roster/restore, 채팅처럼 이름·자격정보를 포함할 수 있는 packet은 structured JSONL에서 hash-only이며 decoded 문자열도 저장하지 않습니다.
- **VERIFIED:** 기본 1GiB free-space guard, `paused_low_space`, dropped count, free bytes, last error가 server snapshot과 GUI JSONL CAPTURE/CAPTURE PRIVACY에 노출됩니다.

## 파일 구조

`<root>/runs/<run_id>/manifest.json`과 `packets.jsonl`을 사용합니다. manifest에는 schema, run id, start/end, registry spec id, privacy policy와 health counter가 있습니다. 정상 종료 때 final 상태/통계를 fsync 후 atomic replace합니다.

## 검증

- 병렬 24 append에서 sequence 중복/역전 없음.
- 민감 채팅 payload 및 decoded text 비저장.
- low-space write 차단과 health snapshot.
- server 통합 뒤 legacy text와 structured redaction 동시 동작.
- 전체 **177 tests PASS**, `py_compile` PASS.
- live run `20260718T185312_80364_f3044b17`은 manifest/API/file sequence가 `33→61→141`로 일치했고 강제 stop 뒤 다음 시작에서 `unclean_shutdown`, JSONL lines/seq/written 모두 243, `dropped=0`으로 복구됐습니다.
- OX run `20260718T191339_95676_052fd24d`도 강제 stop 뒤 `unclean_shutdown`, JSONL lines/seq/written 모두 274, `recovered_utc` 존재, `ended_utc=null`, `dropped=0`으로 복구됐습니다.
- 두 run의 recovery `last_error`는 의도적으로 `Previous capture writer exited without close()`이며, 이는 복구 진단값이지 현재 writer 오류가 아닙니다. 현재 run은 healthy/dropped0/last_error null입니다.

## 남은 검증

- **VERIFIED (live process-stop recovery):** 실제 B 캡처 두 실행의 dead-writer manifest reconciliation과 sequence/count 일치를 확인했습니다.
- **NOT VERIFIED:** 실제 B 장시간 실플레이의 low-space 진입→공간 회복 자동 재개와 OS 강제 전원 차단 내구성.
- **KNOWN RISK:** 호환성을 위해 남긴 legacy text 로그에는 민감 원문이 포함될 수 있으므로 배포 artifact에서 별도 보호/제외해야 합니다.
- **NOT VERIFIED:** 아직 의미가 밝혀지지 않은 opcode가 개인정보를 포함하는지 여부. live에서 확인되면 redaction key를 추가합니다.
