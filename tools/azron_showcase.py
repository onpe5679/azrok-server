"""
Azron Showcase - Cycle through species/evolution combos and screenshot each.
Usage: python tools/azron_showcase.py [mode]
  mode=finals  -> 4 species at stage 4 (default)
  mode=all     -> 4 species × 5 stages = 20 combos
  mode=one N   -> species N at all 5 stages
"""
import subprocess, sys, os, time, ctypes, ctypes.wintypes as wt, struct

SPECIES_NAMES = ['Ark', 'Abo', 'Paz', 'Tero']
STAGE_NAMES = ['Baby', 'Child', 'Teen', 'Adult', 'Final']
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_PY = os.path.join(BASE_DIR, 'azrok_server.py')
SCREENSHOT_DIR = os.path.join(BASE_DIR, 'screenshots')

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

def find_azrok_window():
    result = [0]
    def cb(hwnd, _):
        l = user32.GetWindowTextLengthW(hwnd)
        if l > 0:
            b = ctypes.create_unicode_buffer(l + 1)
            user32.GetWindowTextW(hwnd, b, l + 1)
            if b.value == 'AZROK':
                result[0] = hwnd
        return True
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, ctypes.POINTER(ctypes.c_long))
    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return result[0]

def screenshot(path):
    hwnd = find_azrok_window()
    if not hwnd:
        print(f"  [!] AZROK window not found")
        return False
    rect = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w, h = rect.right - rect.left, rect.bottom - rect.top
    hdc = user32.GetDC(hwnd)
    mem = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mem, bmp)
    user32.PrintWindow(hwnd, mem, 2)
    class BMI(ctypes.Structure):
        _fields_ = [('biSize',ctypes.c_uint32),('biWidth',ctypes.c_int32),('biHeight',ctypes.c_int32),
                     ('biPlanes',ctypes.c_uint16),('biBitCount',ctypes.c_uint16),('biCompression',ctypes.c_uint32),
                     ('biSizeImage',ctypes.c_uint32),('biXPelsPerMeter',ctypes.c_int32),('biYPelsPerMeter',ctypes.c_int32),
                     ('biClrUsed',ctypes.c_uint32),('biClrImportant',ctypes.c_uint32)]
    bi = BMI(); bi.biSize = ctypes.sizeof(BMI); bi.biWidth = w; bi.biHeight = -h; bi.biPlanes = 1; bi.biBitCount = 24
    sz = ((w * 3 + 3) & ~3) * h
    buf = ctypes.create_string_buffer(sz)
    gdi32.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(bi), 0)
    bmp_path = path.replace('.png', '.bmp')
    with open(bmp_path, 'wb') as f:
        fs = 14 + ctypes.sizeof(BMI) + sz
        f.write(b'BM' + struct.pack('<I', fs) + struct.pack('<HH', 0, 0) + struct.pack('<I', 14 + ctypes.sizeof(BMI)))
        bi.biHeight = -h
        f.write(bytes(bi))
        f.write(buf.raw)
    gdi32.DeleteObject(bmp); gdi32.DeleteDC(mem); user32.ReleaseDC(hwnd, hdc)
    try:
        from PIL import Image
        Image.open(bmp_path).save(path)
        os.remove(bmp_path)
    except ImportError:
        os.rename(bmp_path, path)
    return True

def kill_azrok():
    os.system('taskkill /F /IM Azrok.exe >nul 2>&1')
    time.sleep(2)

def run_combo(species, stage):
    name = f"{SPECIES_NAMES[species]}_stage{stage}_{STAGE_NAMES[stage]}"
    print(f"\n{'='*60}")
    print(f"  {name} (species={species}, evolution={stage})")
    print(f"{'='*60}")

    kill_azrok()

    env = os.environ.copy()
    env['AZROK_SPECIES'] = str(species)
    env['AZROK_EVOLUTION'] = str(stage)

    proc = subprocess.Popen(
        [sys.executable, SERVER_PY],
        env=env, cwd=BASE_DIR,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )

    # Wait for game to load
    print(f"  Waiting for game to load...")
    for i in range(90):
        time.sleep(1)
        ret = proc.poll()
        if ret is not None:
            print(f"  [!] Server exited with code {ret}")
            return False
        if find_azrok_window() and i > 60:
            break

    # Extra wait for rendering
    time.sleep(5)

    out_path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    ok = screenshot(out_path)
    if ok:
        print(f"  -> Saved: {out_path}")

    proc.terminate()
    kill_azrok()
    return ok

def main():
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    mode = sys.argv[1] if len(sys.argv) > 1 else 'finals'

    if mode == 'finals':
        combos = [(s, 4) for s in range(4)]
    elif mode == 'all':
        combos = [(s, e) for s in range(4) for e in range(5)]
    elif mode == 'one':
        sp = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        combos = [(sp, e) for e in range(5)]
    elif mode == 'stages':
        combos = [(0, e) for e in range(5)]
    else:
        combos = [(s, 4) for s in range(4)]

    print(f"Azron Showcase - {len(combos)} combinations")
    print(f"Output: {SCREENSHOT_DIR}")

    for species, stage in combos:
        run_combo(species, stage)

    print(f"\nDone! {len(combos)} screenshots saved to {SCREENSHOT_DIR}")

if __name__ == '__main__':
    main()
