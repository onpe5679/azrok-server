# 523 BGM 실패 지점 확정 — `wg_parser_create` 의 PE→Unix 널 디스패치 (2026-07-29)

날짜: 2026-07-29
선행: #461 #462 #463 (Quartz 스플리터 `0x8007000e`, winegstreamer Unix-call AV), #522 (오늘의 A/B 와 계측 환경)
원본 실행파일·게임 자산은 건드리지 않았다.

## 1. 결정적 시퀀스 (VERIFIED)

`WINEDEBUG=-all,+seh,+loaddll,+quartz,+winegstreamer` 로 돌린 게스트 로그에서 실패 직전 호출이
연속으로 잡혔다. 전문은 `artifacts/audio/guestlog_full_K_20260729.txt`.

```text
0128:trace:quartz:DllGetClassObject ({336475d0-942a-11ce-a870-00aa002feab5},{00000001-...},0798FD78)
0128:trace:quartz:DSCF_CreateInstance (07667AF8)->(00000000,{00000000-0000-0000-c000-000000000046},0798FD7C)
0128:trace:quartz:DllGetClassObject clsid {a8edbf98-2442-42c5-85a1-ab05a580df53}, iid {00000001-...}
0128:trace:quartz:class_factory_QueryInterface iface 1FDFE170, ...
0128:trace:quartz:class_factory_CreateInstance iface 1FDFE170, outer 00000000, ...
0128:trace:quartz:wg_parser_create output_compressed 1.
0128:fixme:dbghelp:elf_search_auxv can't find symbol in module
0128:err:seh:NtRaiseException Unhandled exception code c0000005 flags 0 addr (nil)
```

- `{336475d0-942a-11ce-a870-00aa002feab5}` 는 MPEG-1 스플리터 CLSID 다. 게임이 MP3 재생을 위해
  스플리터를 요청하고, 그것이 winegstreamer 의 클래스 팩토리 `{a8edbf98-...}` 로 라우팅된다.
- PE 쪽 `wg_parser_create` 는 **진입해서 TRACE 를 찍는다.** 그 다음 줄이 곧바로 AV 다.
- **`addr (nil)`** — 널 주소 접근. 유효 주소가 아니라 0이다.

## 2. Unix 쪽은 한 번도 실행되지 않는다 (VERIFIED)

진단 root `…-dsound80ms1-winegstrace3.zip` 은 원본 root 8,656개 항목 중 **딱 두 개**만 다르다.

| 파일 | base | trace |
|---|---:|---:|
| `opt/wine/lib/wine/i386-unix/winegstreamer.so` | 145,872 | 162,232 |
| `opt/wine/lib/wine/i386-unix/winegstreamer.dll.so` | 579,720 | 579,720 (CRC 상이) |

그 계측 빌드가 새로 갖고 있는 문자열은 `wg_parser_create` 의 Unix 쪽 본문을 단계별로 찍는 것들이다.

```text
winegstreamer trace: parser entry args=%p
winegstreamer trace: parser calloc=%p size=%zu   /   parser calloc failed size=%zu
winegstreamer trace: parser mutex initialized
winegstreamer trace: parser init / read / read-done condition initialized
winegstreamer trace: parser params readable output_compressed=%u
```

**이 줄들이 단 한 번도 출력되지 않았다** (leg E·F·G·I·J·K 전부). PE 쪽 TRACE 는 찍히고 Unix 쪽
첫 줄은 안 찍히므로, 크래시는 **PE→Unix 전환 그 자체**에서 일어난다. 즉 `WINE_UNIX_CALL` 이
사용하는 unixlib 디스패치가 NULL 이다. `run_azrok_seh.bat` 주석의 "null-dispatch failure" 가 이것이다.

## 3. `+seh` 런처가 크래시를 삼키고 있었다 (VERIFIED)

| 런처 | WINEDEBUG | 결과 |
|---|---|---|
| `run_azrok_seh.bat` (평소 사용) | `-all,+seh` | 폴트가 `handle_syscall_fault` 로 잡혀 **게임은 계속 실행**. 고정 주소 `0x1065bde6` 에서 무한 반복, 복귀 주소 `1fd987e2`/`1fd97ca8` 교대. 스레드 0138·0148 |
| `run_azrok_web.bat` | (미설정 = Wine 기본) | **프로세스 사망**. `D3D9WEB_PATHOUSE_EXITCODE=-1073741819` (= 0xC0000005) |

지금까지 "BGM 기능이 꺼져 있다"로 보였던 상태의 실체는 **오디오 그래프를 만들 스레드가 널 크래시로
죽고, 그 크래시가 SEH 로 삼켜져 게임만 계속 도는 것**이다.

## 4. 의존성 누락설은 기각 (VERIFIED)

`winegstreamer.so` 의 `DT_NEEDED` 8개를 root 와 대조했다. 정확한 파일명으로는 6개가 없지만,
BoxedWine 은 심볼릭 링크를 `<이름>.link` 파일로 저장하며 실물이 모두 존재한다.

| DT_NEEDED | root 내 실물 |
|---|---|
| `libgstreamer-1.0.so.0` | `usr/local/lib/libgstreamer-1.0.so.0.1602.0` + `.so.0.link` |
| `libgstaudio-1.0.so.0` | `libgstaudio-1.0.so.0.1602.0` + `.link` |
| `libgstvideo-1.0.so.0` | `libgstvideo-1.0.so.0.1602.0` + `.link` |
| `libgsttag-1.0.so.0` | `libgsttag-1.0.so.0.1602.0` + `.link` |
| `libgobject-2.0.so.0` | `libgobject-2.0.so.0.7800.4` + `.link` |
| `libglib-2.0.so.0` | `libglib-2.0.so.0.7800.4` + `.link` |
| `ntdll.so`, `libc.so.6` | 존재 |

`LD_LIBRARY_PATH=/usr/local/lib` 도 실행 인자로 전달된다. 디코더 플러그인
`libgstmpg123.so`·`libgstaudioparsers.so` 도 `usr/local/lib/gstreamer-1.0/` 에 있다.
또한 Wine 기본 디버그(err 전 채널 on)로 돌린 leg 에서 `err:module:` 계열 메시지가 **한 줄도 없었다** —
PE DLL 로드 실패를 알리는 오류는 나오지 않는다.

## 5. 계측 환경에 대한 사실 (VERIFIED)

- 페이지는 `lean` 기본값이 `1` 이고, 셸은 게스트 stdout 을 **`?debugConsole` 이 있을 때만 보관**한다.
  이 둘 때문에 그동안 `#output` 이 계속 0바이트였다.
- 셸의 `getEnvProp()` 은 `split(':')` 후 `kv[0]=kv[1]` 만 쓰므로 **게스트 환경변수를 하나밖에 못 넘긴다.**
  URL 로 `WINEDEBUG` 를 추가하는 방식은 구조상 불가능하다(시도했고 값이 잘려 나갔다. 페이지는 원복함).
- 그래서 진단용 앱 zip `apps/Azrok_D3D9Web_pathouse_guesttexrecycle4_audiodbg1.zip` 을 만들었다.
  프로덕션 zip 을 그대로 복사(4,264개)하고 런처 `run_azrok_audiodbg.bat` 하나만 추가했다
  (`WINEDEBUG=-all,+seh,+loaddll,+quartz,+winegstreamer`). 원본 zip 은 수정하지 않았다.

## 6. 다음 (NOT VERIFIED)

- unixlib 핸들이 왜 NULL 인지. 후보: `NtQueryVirtualMemory(MemoryWineUnixFuncs)` 실패,
  winegstreamer PE 의 `DllMain` 초기화 경로 미실행, BoxedWine 의 unixlib 등록 경로 문제.
  모듈 로드 오류가 안 나오므로 "so 를 못 찾는다"가 아니라 **핸들 획득 단계**를 봐야 한다.
- 확인 방법: Wine 기본 디버그로 전 채널 err/fixme 를 콘솔로 받아 `winegstreamer`·`unix` 관련 줄을
  찾거나, `+loaddll` 로 `winegstreamer.dll` 로드 자체가 일어나는지 본다.
- 이 크래시를 고치면 BGM 은 브라우저 대행 없이 게스트에서 나와야 한다. 그때 #497 기준으로
  성능 영향(대행은 FPS 에 사실상 무비용)을 다시 재는 것이 순서다.
