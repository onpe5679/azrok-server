# S2C 0x0007 domain-bank sentinel static correction (2026-07-18)

## 결론

- **VERIFIED:** `S2C 0x0007 +0x1AC..+0x1D3`은 10바이트씩 4개인 총 40개 domain-bank entry입니다.
- **VERIFIED:** `HandleS2C_0007_LoadSetupBlob @ 0x0059E330`은 16개 entry를 상수로 덮은 뒤 네 그룹 모두 `count=10`으로 `DomainBank_ImportByteBank10 @ 0x005AB010`에 전달합니다.
- **VERIFIED:** downstream `FUN_005AB1B0`은 네 그룹의 40개 entry를 전부 순회하며 `value != 0xFF`를 live로 세고 `(group + 1) * 10000 + value`로 내보냅니다. 따라서 `0`은 empty가 아니라 live selector이고 empty sentinel은 `0xFF`입니다.
- **SUPERSEDES:** content/09의 “only 13 server bytes matter / zero-fill is safe”와 content/57의 “zero is structurally accepted” 결론은 폐기합니다. 16개 강제 상수를 제외한 24바이트는 서버 제어 범위입니다.
- **IMPLEMENTED:** fresh S2C 0007은 domain-bank 40바이트 전체를 `0xFF`로 만들고, 수신 클라이언트가 자기 16개 fixed entry만 설치하게 했습니다. `+0x1D4..+0x1D7` 액세서리 selector vector는 별도 필드이며 그대로 유지합니다.

## 직접 근거

`ghidra_temp/bootstrap_0059e330.txt:48-68`:

1. 아래 16개 offset을 상수로 덮어씁니다.
2. 이어서 `+0x1AC`, `+0x1B6`, `+0x1C0`, `+0x1CA`를 각각 정확히 10개씩 import합니다.

| 분류 | wire offsets | 개수 |
|---|---|---:|
| client fixed | `+0x1B0..+0x1B5`, `+0x1BB..+0x1BC`, `+0x1C3`, `+0x1CB..+0x1D1` | 16 |
| server-controlled | `+0x1AC..+0x1AF`, `+0x1B6..+0x1BA`, `+0x1BD..+0x1BF`, `+0x1C0..+0x1C2`, `+0x1C4..+0x1C9`, `+0x1CA`, `+0x1D2..+0x1D3` | 24 |

`ghidra_temp/net_005ab1b0.txt:16-23`:

```c
for (group = 0; group < 4; group++) {
    for (index = 0; index < 10; index++) {
        if (bank[group][index] != 0xff) live_count++;
        output[...] = (group + 1) * 10000 + bank[group][index];
    }
}
```

그러므로 기존 zero-filled payload는 클라이언트 강제 상수 외의 24칸에도 `10000/20000/30000/40000` 계열 live ID를 중복 생성할 수 있었습니다. `0xFF * 40` wire default를 받은 뒤 클라이언트 overwrite가 끝난 effective table에는 fixed 16개만 live로 남습니다.

## 서버 수정과 회귀

- `azrok_server.py::_build_zone_0007_draft()`가 `payload[0x1AC:0x1D4] = b'\xFF' * 40`으로 초기화합니다.
- `tools/test_content_builders.py`는 raw 40바이트가 모두 FF인지, 16개 client overwrite를 적용한 effective table이 정확히 16개만 live인지, 네 그룹의 exact 값과 액세서리 `+0x1D4`가 보존되는지를 검사합니다.
- **VERIFIED (test):** `python -m py_compile azrok_server.py tools/test_content_builders.py` 통과.
- **VERIFIED (test):** `python -m unittest discover -s tools -p "test_*.py"` — **131 tests OK**.
- **NOT VERIFIED (live):** 수정된 FF domain-bank bootstrap의 원본 클라이언트 clean restart 및 화면/패킷 live 회귀는 아직 수행하지 않았습니다.

## 0x0007 잔여 UNKNOWN 감사

### P1 — mode-pair group 0..4

- **VERIFIED layout:** C2S `+0x9C..+0xA0` modes와 `+0xA4..+0xB7` values가 S2C `+0x184..+0x188` / `+0x18C..+0x19F`로 복원됩니다.
- **VERIFIED implementation:** 현재 sanitizer는 질병으로 확정된 group 5..7만 상태/날짜를 검증하며 group 0..4는 opaque하게 저장·복원합니다.
- **NOT VERIFIED:** group 0..4의 실제 콘텐츠 의미, 유효 mode 범위, value 형식. 같은 클라이언트의 왕복 보존은 되지만 서버가 malformed state를 판별할 수 없습니다.

### P1/P2 — C2S `+0x9A..+0x9B`

- **VERIFIED observation:** 저장된 196바이트 snapshot들에서 이 `u16`은 `0`, `10`, `30`으로 변합니다.
- **VERIFIED implementation:** 서버는 raw snapshot 안에는 보존하지만 별도 검증이나 S2C directional restore mapping을 적용하지 않습니다.
- **NOT VERIFIED:** 필드 의미와 대응 S2C 필드. 추측 복사는 금지합니다.

### P2 — C2S header `+0x00..+0x09` 중 evolution 이외

- **VERIFIED:** `+0x05`만 evolution stage이며 S2C `+0x02`로 복원합니다.
- **OBSERVED / INFERRED:** 현재 저장 샘플에서 `+0x01..+0x04 == +0x06..+0x09`이고 packed `YYMMDDHH`처럼 보입니다.
- **NOT VERIFIED:** `+0x00`, 두 dword의 각각의 정확한 역할과 서버 검증 규칙.

### P2 — S2C `+0x00` status

- **VERIFIED:** `FUN_0059E2D0`이 manager `+0x134`에 저장하며 0007 handler 자체는 이 값으로 분기하지 않습니다.
- **INFERRED, NOT VERIFIED:** `0 = new character`. 기존 코드 주석과 content/09의 표현은 직접 증명이 아닙니다.

### P3 — handler structural holes

- **VERIFIED (complete handler direct-read audit):** `+0xDB..+0xE9`, `+0x130`, `+0x132..+0x133`은 복구된 `HandleS2C_0007_LoadSetupBlob` 호출/읽기 목록에 직접 소비가 없습니다.
- **NOT VERIFIED:** 전역적인 역사적/예약 의미. 현행 zero 유지가 맞으며 다른 필드로 추측 매핑하지 않습니다.

### P3 — imported capacity tail

- **VERIFIED:** drug `+0xBE..+0xC6`, energy `+0xCA..+0xDA`, food `+0x10B..+0x10F`는 각 container capacity 안에 import됩니다.
- **VERIFIED:** 현재 클라이언트 resource/live item은 drug 6개, energy 3개, food 33개뿐입니다.
- **NOT VERIFIED:** 남는 9/17/5칸의 출시 서버 의미. zero quantity를 유지합니다.

