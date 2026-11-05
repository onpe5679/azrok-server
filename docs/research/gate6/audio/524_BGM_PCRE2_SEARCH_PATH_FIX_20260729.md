# 524 BGM 복구 — `libpcre2-8.so.0` 탐색 경로 문제와 수정 (2026-07-29)

날짜: 2026-07-29
선행: #523 (널 디스패치 지점 확정), #522, #461·#462·#463
원본 실행파일·게임 자산·바이너리는 건드리지 않았다. 게스트 root 이미지에 라이브러리 사본만 추가했다.

## 1. 근본 원인 (VERIFIED)

```text
0128:warn:module:get_builtin_unix_funcs failed to load
  "/opt/wine/lib/wine/i386-unix/winegstreamer.so":
  libpcre2-8.so.0: cannot open shared object file: No such file or directory
```

사슬은 이렇다.

1. `libpcre2-8.so.0`(glib 의 전이 의존성)을 로더가 못 연다.
2. `winegstreamer.so` 의 `dlopen` 이 실패한다.
3. `get_builtin_unix_funcs()` (`dlls/ntdll/unix/virtual.c`) 가 실패를 돌려주는데, 그 사유는
   **`WARN_(module)` 레벨로만** 찍힌다. Wine 기본 디버그는 `err+fixme` 이므로 아무 데도 안 보인다.
4. `__wine_init_unix_call()` 이 실패해도 `__wine_unixlib_handle` 은 **0 으로 조용히 남는다**
   (`dlls/winecrt0/unix_lib.c`).
5. 나중에 `wg_parser_create` 가 `WINE_UNIX_CALL(0, ...)` 을 실행 → **`addr (nil)` 널 크래시**.
6. `run_azrok_seh.bat` 의 `WINEDEBUG=-all,+seh` 가 그 크래시를 삼켜서, 게임은 계속 돌고 BGM 만 없다.
   WINEDEBUG 미설정(`run_azrok_web.bat`)으로 돌리면 프로세스가 `EXITCODE=-1073741819` 로 죽는다.

## 2. 왜 파일이 있는데 못 여는가 (VERIFIED)

`libpcre2-8.so.0.7.1`(419,464 바이트)과 `libpcre2-8.so.0.link` 는 **세 root 모두에 존재**하며
ELF 도 정상(32-bit LE i386)이다. 다음을 순서대로 배제했다.

| 가설 | 판정 | 근거 |
|---|---|---|
| 파일 누락 | 기각 | 실물 + `.link` 존재 |
| `.link` 심볼릭 링크 미해결 | 기각 | `.link` 로만 도달하는 SONAME 11개 전부에 평범한 파일명 사본을 넣어도 동일 오류 |
| 32/64비트 불일치 | 기각 | 의존성 폐포 11개 전부 `32-bit LE i386` |
| **`/usr/local/lib` 이 탐색 경로에 없음** | **확인** | `/lib` 과 `/usr/lib` 에 사본을 두자 **오류 문구가 바뀌었다** |

`-env "LD_LIBRARY_PATH=/usr/local/lib"` 를 넘기고 있음에도 이 `dlopen` 에는 적용되지 않는다.
같은 디렉터리의 gstreamer/glib 이 먼저 해결된 것은 로더가 그 시점에 이미 적재했기 때문으로 보이며,
**경로 스코프가 진짜 원인**이라는 결론은 오류 문구 변화로 직접 증명된다.

## 3. 수정과 검증 (VERIFIED)

수정: 게스트 root 에 `libpcre2-8.so.0` 을 **표준 탐색 경로에도** 둔다.

- 새 root: `fs/TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1-pcrestd1.zip`
- 추가 항목 4개(각 419,464 바이트, `usr/local/lib/libpcre2-8.so.0.7.1` 의 사본):
  `lib/libpcre2-8.so.0`, `lib/libpcre2-8.so.0.7.1`,
  `usr/lib/libpcre2-8.so.0`, `usr/lib/libpcre2-8.so.0.7.1`
- 기존 root 는 수정하지 않았다.

검증(`webBgmFallback=0`, 즉 브라우저 대행 재생을 끈 상태):

| 지표 | 수정 전 (leg A~O) | 수정 후 (leg P) |
|---|---|---|
| `warn:module ... failed to load` | 매 실행 | **0건** |
| `c0000005` | 매 실행 반복 | **0건** |
| 게스트가 오디오 노드에 쓴 PCM | 콜백 수백 회 `nz=0 / max=0` | **콜백 595회, `nz=8800`, `max=0.403`** |
| WASAPI 루프백 | 비영 샘플 0 | **peak 0.3030, 비영 13,625** |

GStreamer 파이프라인이 실제로 도는 것도 로그로 확인했다.

```text
wg_parser.c:1230:src_getrange_cb: offset 49613, size 65536
wg_transform.c:907:wg_transform_push_data: Wrapped 417/16384 bytes ...
wg_transform.c:1397:wg_stepper_step: Forwarding buffer ... pts 0:00:03.056326400 ... size 417
wg_transform.c:259:transform_sink_chain_cb: ... size 4608
wg_transform.c:1136:read_transform_output: Copied 4608 bytes
```

417 바이트는 44.1 kHz MP3 프레임, 4608 바이트는 그 한 프레임의 PCM(1152×2ch×2byte)이다.
**원본 실행파일이 MP3 를 디코딩하고 있다.**

## 4. 아직 남은 것 (NOT VERIFIED)

- 출력이 아직 **간헐적**이다. 25초 창에서 비영 샘플이 0.57% 뿐이고 원본 15곡 대비 최고 상관은
  0.189 로 낮다. 디코딩은 되는데 지속 재생까지는 확인되지 않았다.
  씬/타이밍 문제인지, DirectSound 로의 연결이 끊기는지 다음에 가려야 한다.
- SDL 오디오 노드가 실행 중 **교체**된다(`openAudio` 가 두 번 찍힌다). 계측 탭은 노드 인스턴스에
  걸리므로 교체 후 재설치가 필요하다. 측정 시 이 점을 반드시 확인할 것.
- 이 사본 추가가 최종 형태인지, 아니면 `/usr/local/lib` 을 탐색 경로에 넣는 쪽이 옳은지는 미결.
- 성능 영향 재측정(#497 기준: 브라우저 대행은 FPS 에 사실상 무비용이었다).

## 5. 부수 발견 — 진단 root 가 스스로 막고 있었다 (VERIFIED)

`…-winegstrace1/2/3` 계측 root 의 `winegstreamer.so` 는 `g_once_init_enter_pointer` /
`g_once_init_leave_pointer` (GLib 2.80+) 를 참조하는데, root 의 GLib 은 `2.78.4` 다.
그래서 pcre2 를 고친 뒤에도 `undefined symbol: g_once_init_leave_pointer` 로 로드에 실패한다.
**프로덕션 `winegstreamer.so` 는 `g_once_init_enter/leave` 만 참조하므로 이 문제가 없다.**
계측 빌드가 root 보다 새 GLib 환경에서 컴파일된 탓이며, 그 결과 `winegstreamer trace:` 줄은
단 한 번도 출력될 수 없었다. 진단 root 를 다시 쓰려면 GLib 2.78 환경에서 재빌드해야 한다.

## 6. 재현 방법

```text
root  = TinyCore15Wine11.0-wsaeventfix5-korean4-bgmloop3-dsound80ms1-pcrestd1
app   = Azrok_D3D9Web_pathouse_guesttexrecycle4_audiodbg2   (WINEDEBUG=-all,+seh,warn+module,+quartz)
p     = run_azrok_audiodbg2.bat
URL   += &debugConsole=1&lean=0&webBgmFallback=0
```

`debugConsole` 없이는 게스트 로그가 보관되지 않고, `lean=1`(기본) 에서는 저관측 모드가 된다.
`warn+module` 없이는 dlopen 실패 사유가 출력되지 않는다 — 이 세 가지가 그동안 원인을 가리고 있었다.
