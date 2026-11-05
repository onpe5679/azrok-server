import argparse
import ctypes
import ctypes.wintypes as wt
import os
import struct
import sys
import time


user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32


INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_ABSOLUTE = 0x8000
SRCCOPY = 0x00CC0020
BI_RGB = 0
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
WM_CHAR = 0x0102
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SETTEXT = 0x000C
WM_GETTEXT = 0x000D
WM_GETTEXTLENGTH = 0x000E
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
MK_LBUTTON = 0x0001
EM_SETSEL = 0x00B1


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wt.LONG),
        ("dy", wt.LONG),
        ("mouseData", wt.DWORD),
        ("dwFlags", wt.DWORD),
        ("time", wt.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wt.WORD),
        ("wScan", wt.WORD),
        ("dwFlags", wt.DWORD),
        ("time", wt.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wt.DWORD),
        ("wParamL", wt.WORD),
        ("wParamH", wt.WORD),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wt.DWORD),
        ("union", _INPUTUNION),
    ]


class RECT(ctypes.Structure):
    _fields_ = [("left", wt.LONG), ("top", wt.LONG), ("right", wt.LONG), ("bottom", wt.LONG)]


class POINT(ctypes.Structure):
    _fields_ = [("x", wt.LONG), ("y", wt.LONG)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wt.DWORD),
        ("biWidth", wt.LONG),
        ("biHeight", wt.LONG),
        ("biPlanes", wt.WORD),
        ("biBitCount", wt.WORD),
        ("biCompression", wt.DWORD),
        ("biSizeImage", wt.DWORD),
        ("biXPelsPerMeter", wt.LONG),
        ("biYPelsPerMeter", wt.LONG),
        ("biClrUsed", wt.DWORD),
        ("biClrImportant", wt.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", wt.DWORD * 3),
    ]


VK_CODES = {
    "ENTER": 0x0D,
    "TAB": 0x09,
    "ESC": 0x1B,
    "SPACE": 0x20,
    "LEFT": 0x25,
    "UP": 0x26,
    "RIGHT": 0x27,
    "DOWN": 0x28,
}


def real_input_allowed():
    return os.environ.get("AZROK_ALLOW_REAL_INPUT", "").strip() == "1"


# Character select commit points calibrated from no-real-input Frida clicks on
# the March 31, 2026 character creation screen.
SLOT_POSITIONS = [
    (0.18, 0.66),
    (0.35, 0.63),
    (0.60, 0.63),
    (0.88, 0.60),
]

# Lower-left edge "Create" button candidates. The exact hitbox seems narrow and
# click handling improves when the window is first moved to the top-left corner.
CREATE_BUTTON_CANDIDATES = [
    (0.040, 0.915),
    (0.048, 0.930),
    (0.055, 0.945),
    (0.062, 0.955),
    (0.070, 0.965),
]

# Name-entry confirm button. Real click is more reliable here than Enter.
CONFIRM_BUTTON_DEFAULT = (0.42, 0.56)
NAME_INPUT_DEFAULT = (0.43, 0.46)
CHAR_SCREEN_BG_SAMPLE_1 = (0.14, 0.20)
CHAR_SCREEN_BG_SAMPLE_2 = (0.82, 0.20)
CHAR_SCREEN_TITLE_SAMPLE = (0.09, 0.03)
CHAR_SCREEN_SLOT2_SAMPLE = (0.40, 0.66)
NAME_POPUP_PANEL_SAMPLE = (0.52, 0.54)
NAME_POPUP_CONFIRM_SAMPLE = (0.42, 0.56)
INGAME_POPUP_PANEL_SAMPLE = (0.53, 0.67)
INGAME_POPUP_CONFIRM_SAMPLE = (0.61, 0.80)
INGAME_POPUP_CONFIRM_DEFAULT = (0.61, 0.80)


def _enum_windows():
    hwnds = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def callback(hwnd, lparam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, len(buf))
            title = buf.value
            if title:
                hwnds.append((hwnd, title))
        return True

    user32.EnumWindows(callback, 0)
    return hwnds


def get_window_pid(hwnd):
    pid = wt.DWORD(0)
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def get_window_area(hwnd):
    try:
        left, top, right, bottom = get_window_rect(hwnd)
    except Exception:
        return 0
    return max(0, right - left) * max(0, bottom - top)


def _pick_best_window(candidates):
    if not candidates:
        return None, None
    hwnd, title = max(candidates, key=lambda item: get_window_area(item[0]))
    return hwnd, title


def find_window(title_contains="AZROK", pid=None):
    title_contains = (title_contains or "").lower()
    windows = _enum_windows()
    if pid is not None:
        pid_windows = [(hwnd, title) for hwnd, title in windows if get_window_pid(hwnd) == pid]
        if not pid_windows:
            return None, None
        if title_contains:
            exact = [(hwnd, title) for hwnd, title in pid_windows if title.lower() == title_contains]
            if exact:
                return _pick_best_window(exact)
            contains = [(hwnd, title) for hwnd, title in pid_windows if title_contains in title.lower()]
            if contains:
                return _pick_best_window(contains)
        return _pick_best_window(pid_windows)
    for hwnd, title in windows:
        if title.lower() == title_contains:
            return hwnd, title
    if title_contains == "azrok":
        return None, None
    for hwnd, title in windows:
        if title_contains in title.lower():
            return hwnd, title
    return None, None


def get_client_rect_screen(hwnd):
    rect = RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        raise RuntimeError("GetClientRect failed")
    tl = POINT(rect.left, rect.top)
    br = POINT(rect.right, rect.bottom)
    if not user32.ClientToScreen(hwnd, ctypes.byref(tl)):
        raise RuntimeError("ClientToScreen failed (top-left)")
    if not user32.ClientToScreen(hwnd, ctypes.byref(br)):
        raise RuntimeError("ClientToScreen failed (bottom-right)")
    return (tl.x, tl.y, br.x, br.y)


def get_client_size(hwnd):
    left, top, right, bottom = get_client_rect_screen(hwnd)
    return (right - left, bottom - top)


def get_window_rect(hwnd):
    rect = RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        raise RuntimeError("GetWindowRect failed")
    return (rect.left, rect.top, rect.right, rect.bottom)


def move_window(hwnd, x, y):
    left, top, right, bottom = get_window_rect(hwnd)
    width = right - left
    height = bottom - top
    if not user32.MoveWindow(hwnd, x, y, width, height, True):
        raise RuntimeError("MoveWindow failed")
    time.sleep(0.2)


def show_window(hwnd):
    user32.ShowWindow(hwnd, 5)
    time.sleep(0.05)


def focus_window(hwnd):
    show_window(hwnd)
    fg = user32.GetForegroundWindow()
    current_tid = kernel32.GetCurrentThreadId()
    target_tid = user32.GetWindowThreadProcessId(hwnd, None)
    fg_tid = user32.GetWindowThreadProcessId(fg, None) if fg else 0
    attached_fg = False
    attached_target = False
    try:
        if fg_tid and fg_tid != current_tid:
            attached_fg = bool(user32.AttachThreadInput(current_tid, fg_tid, True))
        if target_tid and target_tid != current_tid:
            attached_target = bool(user32.AttachThreadInput(current_tid, target_tid, True))
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.SetActiveWindow(hwnd)
        user32.SetFocus(hwnd)
    finally:
        if attached_target:
            user32.AttachThreadInput(current_tid, target_tid, False)
        if attached_fg:
            user32.AttachThreadInput(current_tid, fg_tid, False)
    time.sleep(0.2)


def capture_rect_to_bmp(rect, out_path):
    left, top, right, bottom = rect
    width = right - left
    height = bottom - top
    if width <= 0 or height <= 0:
        raise RuntimeError(f"invalid capture rect: {rect}")

    hdc_screen = user32.GetDC(0)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
    hbitmap = gdi32.CreateCompatibleBitmap(hdc_screen, width, height)
    old_obj = gdi32.SelectObject(hdc_mem, hbitmap)
    try:
        if not gdi32.BitBlt(hdc_mem, 0, 0, width, height, hdc_screen, left, top, SRCCOPY):
            raise RuntimeError("BitBlt failed")

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = width
        bmi.bmiHeader.biHeight = -height  # top-down
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = BI_RGB
        buf_size = width * height * 4
        pixel_buf = ctypes.create_string_buffer(buf_size)
        lines = gdi32.GetDIBits(
            hdc_mem,
            hbitmap,
            0,
            height,
            pixel_buf,
            ctypes.byref(bmi),
            0,
        )
        if lines != height:
            raise RuntimeError(f"GetDIBits failed: {lines}/{height}")

        file_header_size = 14
        info_header_size = 40
        file_size = file_header_size + info_header_size + buf_size
        with open(out_path, "wb") as f:
            f.write(b"BM")
            f.write(struct.pack("<IHHI", file_size, 0, 0, file_header_size + info_header_size))
            f.write(struct.pack(
                "<IiiHHIIiiII",
                info_header_size,
                width,
                -height,
                1,
                32,
                BI_RGB,
                buf_size,
                0,
                0,
                0,
                0,
            ))
            f.write(pixel_buf.raw)
    finally:
        gdi32.SelectObject(hdc_mem, old_obj)
        gdi32.DeleteObject(hbitmap)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(0, hdc_screen)


def capture_window(hwnd, out_path, client_only=False):
    rect = get_client_rect_screen(hwnd) if client_only else get_window_rect(hwnd)
    capture_rect_to_bmp(rect, out_path)
    return rect


def get_screen_pixel(x, y):
    hdc = user32.GetDC(0)
    if not hdc:
        raise RuntimeError("GetDC failed")
    try:
        color = gdi32.GetPixel(hdc, x, y)
        if color == 0xFFFFFFFF:
            raise RuntimeError("GetPixel failed")
        r = color & 0xFF
        g = (color >> 8) & 0xFF
        b = (color >> 16) & 0xFF
        return (r, g, b)
    finally:
        user32.ReleaseDC(0, hdc)


def _send_input(inp):
    arr = (INPUT * 1)(inp)
    if user32.SendInput(1, ctypes.byref(arr), ctypes.sizeof(INPUT)) != 1:
        raise RuntimeError("SendInput failed")


def get_cursor_pos():
    pt = POINT()
    if not user32.GetCursorPos(ctypes.byref(pt)):
        raise RuntimeError("GetCursorPos failed")
    return pt.x, pt.y


def move_mouse_abs(x, y):
    if not real_input_allowed():
        raise RuntimeError("Real OS mouse input is disabled; set AZROK_ALLOW_REAL_INPUT=1 to allow it")
    sw = user32.GetSystemMetrics(0) - 1
    sh = user32.GetSystemMetrics(1) - 1
    nx = int(x * 65535 / sw)
    ny = int(y * 65535 / sh)
    inp = INPUT(type=INPUT_MOUSE)
    inp.union.mi = MOUSEINPUT(nx, ny, 0, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, 0, None)
    _send_input(inp)


def left_click(x, y, pre_delay=0.03, hold_delay=0.08, after_delay=0.12, restore_cursor=True):
    if not real_input_allowed():
        raise RuntimeError("Real OS mouse input is disabled; set AZROK_ALLOW_REAL_INPUT=1 to allow it")
    original_pos = None
    if restore_cursor:
        original_pos = get_cursor_pos()
    if not user32.SetCursorPos(x, y):
        raise RuntimeError("SetCursorPos failed")
    time.sleep(pre_delay)
    down = INPUT(type=INPUT_MOUSE)
    down.union.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, None)
    _send_input(down)
    time.sleep(hold_delay)
    up = INPUT(type=INPUT_MOUSE)
    up.union.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, None)
    _send_input(up)
    time.sleep(after_delay)
    if original_pos is not None:
        user32.SetCursorPos(*original_pos)


def right_click(x, y, pre_delay=0.03, hold_delay=0.08, after_delay=0.12, restore_cursor=True):
    if not real_input_allowed():
        raise RuntimeError("Real OS mouse input is disabled; set AZROK_ALLOW_REAL_INPUT=1 to allow it")
    original_pos = get_cursor_pos() if restore_cursor else None
    if not user32.SetCursorPos(x, y):
        raise RuntimeError("SetCursorPos failed")
    time.sleep(pre_delay)
    down = INPUT(type=INPUT_MOUSE)
    down.union.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_RIGHTDOWN, 0, None)
    _send_input(down)
    time.sleep(hold_delay)
    up = INPUT(type=INPUT_MOUSE)
    up.union.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_RIGHTUP, 0, None)
    _send_input(up)
    time.sleep(after_delay)
    if original_pos is not None:
        user32.SetCursorPos(*original_pos)


def _pack_client_lparam(x, y):
    return (y << 16) | (x & 0xFFFF)


def post_client_click(hwnd, client_x, client_y):
    lparam = _pack_client_lparam(client_x, client_y)
    if not user32.PostMessageW(hwnd, WM_MOUSEMOVE, 0, lparam):
        raise RuntimeError("PostMessageW(WM_MOUSEMOVE) failed")
    time.sleep(0.02)
    if not user32.PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lparam):
        raise RuntimeError("PostMessageW(WM_LBUTTONDOWN) failed")
    time.sleep(0.03)
    if not user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, lparam):
        raise RuntimeError("PostMessageW(WM_LBUTTONUP) failed")


def send_client_click(hwnd, client_x, client_y):
    lparam = _pack_client_lparam(client_x, client_y)
    user32.SendMessageW(hwnd, WM_MOUSEMOVE, 0, lparam)
    time.sleep(0.02)
    user32.SendMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lparam)
    time.sleep(0.03)
    user32.SendMessageW(hwnd, WM_LBUTTONUP, 0, lparam)


def send_vk(vk):
    if not real_input_allowed():
        raise RuntimeError("Real OS keyboard input is disabled; set AZROK_ALLOW_REAL_INPUT=1 to allow it")
    down = INPUT(type=INPUT_KEYBOARD)
    down.union.ki = KEYBDINPUT(vk, 0, 0, 0, None)
    _send_input(down)
    up = INPUT(type=INPUT_KEYBOARD)
    up.union.ki = KEYBDINPUT(vk, 0, KEYEVENTF_KEYUP, 0, None)
    _send_input(up)


def send_vk_hold(vk, hold_ms):
    if not real_input_allowed():
        raise RuntimeError("Real OS keyboard input is disabled; set AZROK_ALLOW_REAL_INPUT=1 to allow it")
    down = INPUT(type=INPUT_KEYBOARD)
    down.union.ki = KEYBDINPUT(vk, 0, 0, 0, None)
    _send_input(down)
    time.sleep(max(0.0, hold_ms / 1000.0))
    up = INPUT(type=INPUT_KEYBOARD)
    up.union.ki = KEYBDINPUT(vk, 0, KEYEVENTF_KEYUP, 0, None)
    _send_input(up)


def send_text(text):
    if not real_input_allowed():
        raise RuntimeError("Real OS keyboard input is disabled; set AZROK_ALLOW_REAL_INPUT=1 to allow it")
    for ch in text:
        down = INPUT(type=INPUT_KEYBOARD)
        down.union.ki = KEYBDINPUT(0, ord(ch), KEYEVENTF_UNICODE, 0, None)
        _send_input(down)
        up = INPUT(type=INPUT_KEYBOARD)
        up.union.ki = KEYBDINPUT(0, ord(ch), KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, None)
        _send_input(up)
        time.sleep(0.02)


def post_text(hwnd, text):
    for ch in text:
        if not user32.PostMessageW(hwnd, WM_CHAR, ord(ch), 0):
            raise RuntimeError("PostMessageW(WM_CHAR) failed")
        time.sleep(0.02)


def post_vk(hwnd, vk):
    if not user32.PostMessageW(hwnd, WM_KEYDOWN, vk, 0):
        raise RuntimeError("PostMessageW(WM_KEYDOWN) failed")
    time.sleep(0.02)
    if not user32.PostMessageW(hwnd, WM_KEYUP, vk, 0):
        raise RuntimeError("PostMessageW(WM_KEYUP) failed")


def get_window_text_a(hwnd):
    length = user32.SendMessageA(hwnd, WM_GETTEXTLENGTH, 0, 0)
    if length < 0:
        length = 0
    buf = ctypes.create_string_buffer(length + 1)
    user32.SendMessageA(hwnd, WM_GETTEXT, length + 1, ctypes.cast(buf, ctypes.c_void_p))
    try:
        return buf.value.decode("cp949")
    except UnicodeDecodeError:
        return buf.value.decode("mbcs", errors="replace")


def set_window_text_a(hwnd, text):
    try:
        encoded = text.encode("cp949")
    except UnicodeEncodeError:
        encoded = text.encode("mbcs", errors="replace")
    if not user32.SetWindowTextA(hwnd, encoded):
        raise RuntimeError(f"SetWindowTextA failed for hwnd={hwnd}")


def _enum_child_windows(hwnd):
    children = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def callback(child_hwnd, lparam):
        children.append(child_hwnd)
        return True

    user32.EnumChildWindows(hwnd, callback, 0)
    return children


def get_class_name(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, len(buf))
    return buf.value


def get_window_style(hwnd):
    return user32.GetWindowLongW(hwnd, -16)


def get_window_exstyle(hwnd):
    return user32.GetWindowLongW(hwnd, -20)


def get_dlg_ctrl_id(hwnd):
    return user32.GetDlgCtrlID(hwnd)


def list_child_edits(hwnd):
    edits = []
    for child in _enum_child_windows(hwnd):
        if get_class_name(child) != "Edit":
            continue
        edits.append(
            {
                "hwnd": child,
                "visible": bool(user32.IsWindowVisible(child)),
                "enabled": bool(user32.IsWindowEnabled(child)),
                "ctrl_id": get_dlg_ctrl_id(child),
                "style": get_window_style(child),
                "exstyle": get_window_exstyle(child),
                "text": get_window_text_a(child),
            }
        )
    return edits


def choose_name_edit_candidates(hwnd):
    edits = list_child_edits(hwnd)
    if not edits:
        raise RuntimeError("No child Edit controls found")
    blank = [item for item in edits if not item["text"]]
    enabled = [item for item in blank if item["enabled"]]
    if enabled:
        return enabled
    if blank:
        return blank
    return edits


def commit_name_via_child_edit(hwnd, text, enter_count=1, all_candidates=True, pre_enter_delay=0.35):
    candidates = choose_name_edit_candidates(hwnd)
    if not all_candidates:
        candidates = candidates[:1]
    results = []
    for item in candidates:
        child = item["hwnd"]
        set_window_text_a(child, text)
        text_len = len(get_window_text_a(child))
        user32.SendMessageA(child, EM_SETSEL, text_len, text_len)
        time.sleep(max(0.0, pre_enter_delay))
        user32.SendMessageA(child, WM_KEYDOWN, VK_CODES["ENTER"], 0)
        user32.SendMessageA(child, WM_KEYUP, VK_CODES["ENTER"], 0)
        for _ in range(max(0, enter_count - 1)):
            time.sleep(0.05)
            user32.SendMessageA(child, WM_KEYDOWN, VK_CODES["ENTER"], 0)
            user32.SendMessageA(child, WM_KEYUP, VK_CODES["ENTER"], 0)
        results.append((child, get_window_text_a(child)))
        time.sleep(0.10)
    return results


def wait_for_window(title_contains="AZROK", timeout=30.0, pid=None):
    deadline = time.time() + timeout
    while time.time() < deadline:
        hwnd, title = find_window(title_contains, pid=pid)
        if hwnd:
            return hwnd, title
        time.sleep(0.25)
    if pid is not None:
        raise RuntimeError(f"Window not found for pid={pid} title={title_contains}")
    raise RuntimeError(f"Window not found: {title_contains}")


def client_ratio_to_screen(hwnd, x_ratio, y_ratio):
    left, top, right, bottom = get_client_rect_screen(hwnd)
    width = right - left
    height = bottom - top
    x = left + round(width * x_ratio)
    y = top + round(height * y_ratio)
    return x, y


def client_ratio_to_client(hwnd, x_ratio, y_ratio):
    width, height = get_client_size(hwnd)
    x = round(width * x_ratio)
    y = round(height * y_ratio)
    return x, y


def sample_client_pixel(hwnd, x_ratio, y_ratio):
    x, y = client_ratio_to_screen(hwnd, x_ratio, y_ratio)
    return get_screen_pixel(x, y)


def looks_like_character_creation_screen(hwnd):
    bg1_r, bg1_g, bg1_b = sample_client_pixel(hwnd, *CHAR_SCREEN_BG_SAMPLE_1)
    bg2_r, bg2_g, bg2_b = sample_client_pixel(hwnd, *CHAR_SCREEN_BG_SAMPLE_2)
    title_r, title_g, title_b = sample_client_pixel(hwnd, *CHAR_SCREEN_TITLE_SAMPLE)
    slot_r, slot_g, slot_b = sample_client_pixel(hwnd, *CHAR_SCREEN_SLOT2_SAMPLE)
    bg1_ok = bg1_r <= 180 and bg1_g <= 150 and bg1_b >= 170
    bg2_ok = bg2_r <= 190 and bg2_g <= 170 and bg2_b >= 180
    title_ok = title_r <= 120 and title_g <= 90 and title_b >= 80
    slot_ok = slot_r >= 140 and slot_g <= 100 and slot_b >= 90
    return bg1_ok and bg2_ok and title_ok and slot_ok


def wait_for_character_creation_screen(hwnd, timeout=15.0, poll_interval=0.25):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if looks_like_character_creation_screen(hwnd):
            return True
        time.sleep(poll_interval)
    return False


def looks_like_name_popup(hwnd):
    panel_r, panel_g, panel_b = sample_client_pixel(hwnd, *NAME_POPUP_PANEL_SAMPLE)
    confirm_r, confirm_g, confirm_b = sample_client_pixel(hwnd, *NAME_POPUP_CONFIRM_SAMPLE)
    panel_ok = panel_b >= 120 and panel_g >= 80 and panel_r <= 120
    confirm_ok = confirm_g >= 180 and confirm_b >= 120 and confirm_r <= 180
    return panel_ok and confirm_ok


def wait_for_name_popup(hwnd, timeout=4.0, poll_interval=0.20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if looks_like_name_popup(hwnd):
            return True
        time.sleep(poll_interval)
    return False


def wait_for_name_popup_clear(hwnd, timeout=4.0, poll_interval=0.20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not looks_like_name_popup(hwnd):
            return True
        time.sleep(poll_interval)
    return False


def looks_like_ingame_popup(hwnd):
    panel_r, panel_g, panel_b = sample_client_pixel(hwnd, *INGAME_POPUP_PANEL_SAMPLE)
    confirm_r, confirm_g, confirm_b = sample_client_pixel(hwnd, *INGAME_POPUP_CONFIRM_SAMPLE)
    panel_ok = panel_b >= 120 and panel_g >= 90 and panel_r <= 160
    confirm_ok = confirm_g >= 160 and confirm_b >= 120 and confirm_r <= 190
    return panel_ok and confirm_ok


def wait_for_ingame_popup(hwnd, timeout=8.0, poll_interval=0.25):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if looks_like_ingame_popup(hwnd):
            return True
        time.sleep(poll_interval)
    return False


def click_ingame_popup_confirm(hwnd, x_ratio=None, y_ratio=None, message=False, wait_seconds=0.0):
    if wait_seconds > 0:
        wait_for_ingame_popup(hwnd, timeout=wait_seconds)
    rx = INGAME_POPUP_CONFIRM_DEFAULT[0] if x_ratio is None else x_ratio
    ry = INGAME_POPUP_CONFIRM_DEFAULT[1] if y_ratio is None else y_ratio
    if message:
        return click_relative_message(hwnd, rx, ry)
    return click_relative(hwnd, rx, ry)


def click_slot(hwnd, slot_index):
    if slot_index < 0 or slot_index >= len(SLOT_POSITIONS):
        raise ValueError("slot_index must be 0..3")
    rx, ry = SLOT_POSITIONS[slot_index]
    x, y = client_ratio_to_screen(hwnd, rx, ry)
    left_click(x, y)
    return x, y


def click_slot_message(hwnd, slot_index):
    if slot_index < 0 or slot_index >= len(SLOT_POSITIONS):
        raise ValueError("slot_index must be 0..3")
    rx, ry = SLOT_POSITIONS[slot_index]
    client_x, client_y = client_ratio_to_client(hwnd, rx, ry)
    post_client_click(hwnd, client_x, client_y)
    return client_x, client_y


def click_relative(hwnd, x_ratio, y_ratio):
    x, y = client_ratio_to_screen(hwnd, x_ratio, y_ratio)
    left_click(x, y)
    return x, y


def move_relative(hwnd, x_ratio, y_ratio):
    """Move over one client-relative point without pressing a button."""
    x, y = client_ratio_to_screen(hwnd, x_ratio, y_ratio)
    move_mouse_abs(x, y)
    return x, y


def right_click_relative(hwnd, x_ratio, y_ratio):
    left, top, right, bottom = get_client_rect_screen(hwnd)
    x = left + int((right - left) * x_ratio)
    y = top + int((bottom - top) * y_ratio)
    right_click(x, y)
    return x, y


def click_create_candidate(hwnd, candidate_index):
    if candidate_index < 0 or candidate_index >= len(CREATE_BUTTON_CANDIDATES):
        raise ValueError(f"candidate_index must be 0..{len(CREATE_BUTTON_CANDIDATES) - 1}")
    return click_relative(hwnd, *CREATE_BUTTON_CANDIDATES[candidate_index])


def click_create_candidate_message(hwnd, candidate_index):
    if candidate_index < 0 or candidate_index >= len(CREATE_BUTTON_CANDIDATES):
        raise ValueError(f"candidate_index must be 0..{len(CREATE_BUTTON_CANDIDATES) - 1}")
    return click_relative_message(hwnd, *CREATE_BUTTON_CANDIDATES[candidate_index])


def click_create_candidate_sync(hwnd, candidate_index):
    if candidate_index < 0 or candidate_index >= len(CREATE_BUTTON_CANDIDATES):
        raise ValueError(f"candidate_index must be 0..{len(CREATE_BUTTON_CANDIDATES) - 1}")
    rx, ry = CREATE_BUTTON_CANDIDATES[candidate_index]
    client_x, client_y = client_ratio_to_client(hwnd, rx, ry)
    send_client_click(hwnd, client_x, client_y)
    return client_x, client_y


def click_relative_message(hwnd, x_ratio, y_ratio):
    client_x, client_y = client_ratio_to_client(hwnd, x_ratio, y_ratio)
    post_client_click(hwnd, client_x, client_y)
    return client_x, client_y


def run_create_flow(
    hwnd,
    slot,
    candidate_index=2,
    name="",
    move_top_left=False,
    message=False,
    confirm_ratio=None,
    confirm_enter=False,
    input_ratio=None,
    settle_seconds=1.0,
    wait_char_screen_seconds=15.0,
    slot_repeat=2,
    slot_interval=0.20,
    post_slot_seconds=0.60,
    post_create_seconds=0.80,
    create_retry_count=3,
    direct_edit_commit=False,
):
    if move_top_left:
        move_window(hwnd, 0, 0)
    if settle_seconds > 0:
        time.sleep(settle_seconds)
    if wait_char_screen_seconds > 0:
        if not wait_for_character_creation_screen(hwnd, timeout=wait_char_screen_seconds):
            raise RuntimeError("Character creation screen was not detected before create-flow started")

    if message:
        slot_pos = None
        for _ in range(max(1, slot_repeat)):
            slot_pos = click_slot_message(hwnd, slot)
            time.sleep(slot_interval)
        create_pos = click_create_candidate_message(hwnd, candidate_index)
    else:
        focus_window(hwnd)
        slot_pos = None
        for _ in range(max(1, slot_repeat)):
            slot_pos = click_slot(hwnd, slot)
            time.sleep(slot_interval)
        time.sleep(post_slot_seconds)
        create_pos = click_create_candidate(hwnd, candidate_index)

    time.sleep(post_create_seconds)
    confirm_pos = None
    input_pos = None
    if name:
        popup_visible = wait_for_name_popup(hwnd, timeout=1.2)
        retry_count = max(1, create_retry_count)
        while (not popup_visible) and retry_count > 1:
            time.sleep(0.20)
            if message:
                create_pos = click_create_candidate_sync(hwnd, candidate_index)
            else:
                create_pos = click_create_candidate(hwnd, candidate_index)
            time.sleep(post_create_seconds)
            popup_visible = wait_for_name_popup(hwnd, timeout=1.2)
            retry_count -= 1
        if message and not popup_visible:
            retry_count = max(1, create_retry_count)
            while (not popup_visible) and retry_count > 0:
                time.sleep(0.20)
                create_pos = click_create_candidate_sync(hwnd, candidate_index)
                time.sleep(post_create_seconds)
                popup_visible = wait_for_name_popup(hwnd, timeout=1.2)
                retry_count -= 1
        if not popup_visible:
            raise RuntimeError("Name popup was not detected after the Create clicks")
        ix, iy = input_ratio or NAME_INPUT_DEFAULT
        if message:
            input_pos = click_relative_message(hwnd, ix, iy)
        else:
            input_pos = click_relative(hwnd, ix, iy)
        time.sleep(0.15)
        if direct_edit_commit:
            commit_name_via_child_edit(hwnd, name)
            time.sleep(0.35)
            return slot_pos, create_pos, input_pos, confirm_pos
        if message:
            post_text(hwnd, name)
        else:
            send_text(name)
        time.sleep(0.20)
        if confirm_enter:
            if message:
                post_vk(hwnd, VK_CODES["ENTER"])
            else:
                send_vk(VK_CODES["ENTER"])
        else:
            cx, cy = confirm_ratio or CONFIRM_BUTTON_DEFAULT
            if message:
                confirm_pos = click_relative_message(hwnd, cx, cy)
            else:
                confirm_pos = click_relative(hwnd, cx, cy)
            if not wait_for_name_popup_clear(hwnd, timeout=1.0):
                time.sleep(0.15)
                if message:
                    confirm_pos = click_relative_message(hwnd, cx, cy)
                else:
                    confirm_pos = click_relative(hwnd, cx, cy)
                if not wait_for_name_popup_clear(hwnd, timeout=0.8):
                    raise RuntimeError("Name popup did not close after the confirm click")
    return slot_pos, create_pos, input_pos, confirm_pos


def sweep_create(hwnd, x0, x1, y0, y1, cols, rows, capture_dir=None, message=False):
    if cols <= 0 or rows <= 0:
        raise ValueError("cols and rows must be positive")
    capture_dir_abs = os.path.abspath(capture_dir) if capture_dir else None
    if capture_dir_abs:
        os.makedirs(capture_dir_abs, exist_ok=True)

    results = []
    for row in range(rows):
        ry = y0 if rows == 1 else y0 + (y1 - y0) * row / (rows - 1)
        for col in range(cols):
            rx = x0 if cols == 1 else x0 + (x1 - x0) * col / (cols - 1)
            if message:
                px, py = click_relative_message(hwnd, rx, ry)
                kind = "client"
            else:
                px, py = click_relative(hwnd, rx, ry)
                kind = "screen"
            results.append((row, col, rx, ry, kind, px, py))
            if capture_dir_abs:
                out_name = os.path.join(capture_dir_abs, f"sweep_r{row:02d}_c{col:02d}.bmp")
                capture_window(hwnd, out_name, client_only=True)
            time.sleep(0.35)
    return results


def main():
    parser = argparse.ArgumentParser(description="Best-effort AZROK window automation helper")
    parser.add_argument("--title", default="AZROK", help="Window title substring")
    parser.add_argument("--pid", type=int, default=0, help="Optional process id to bind window selection to")
    parser.add_argument("--timeout", type=float, default=30.0, help="Window wait timeout in seconds")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("info", help="Print window and client rects")

    slot_p = sub.add_parser("click-slot", help="Click one of the four character slots")
    slot_p.add_argument("slot", type=int, help="0-based slot index")

    slot_msg_p = sub.add_parser("click-slot-msg", help="Send a click message to one of the four character slots")
    slot_msg_p.add_argument("slot", type=int, help="0-based slot index")

    rel_p = sub.add_parser("click-rel", help="Click a client-relative position")
    rel_p.add_argument("x", type=float, help="0..1")
    rel_p.add_argument("y", type=float, help="0..1")

    move_rel_p = sub.add_parser("move-rel", help="Move over a client-relative position without clicking")
    move_rel_p.add_argument("x", type=float, help="0..1")
    move_rel_p.add_argument("y", type=float, help="0..1")

    right_rel_p = sub.add_parser("right-click-rel", help="Right-click a client-relative position")
    right_rel_p.add_argument("x", type=float, help="0..1")
    right_rel_p.add_argument("y", type=float, help="0..1")

    create_p = sub.add_parser("click-create", help="Click a lower-left Create button candidate")
    create_p.add_argument("candidate", type=int, nargs="?", default=2, help="0-based candidate index")
    create_p.add_argument("--message", action="store_true", help="Use window messages instead of moving the OS cursor")

    popup_p = sub.add_parser("click-popup-confirm", help="Click the in-game popup confirm button")
    popup_p.add_argument("--x", type=float, default=INGAME_POPUP_CONFIRM_DEFAULT[0], help="0..1 x ratio")
    popup_p.add_argument("--y", type=float, default=INGAME_POPUP_CONFIRM_DEFAULT[1], help="0..1 y ratio")
    popup_p.add_argument("--message", action="store_true", help="Use window messages instead of moving the OS cursor")
    popup_p.add_argument("--wait-seconds", type=float, default=0.0, help="Wait for the popup to become visible before clicking")

    rel_msg_p = sub.add_parser("click-rel-msg", help="Send a click message to a client-relative position")
    rel_msg_p.add_argument("x", type=float, help="0..1")
    rel_msg_p.add_argument("y", type=float, help="0..1")

    flow_p = sub.add_parser("create-flow", help="Select a slot, click Create, and optionally type a name")
    flow_p.add_argument("--slot", type=int, default=1, help="0-based slot index")
    flow_p.add_argument("--candidate", type=int, default=2, help="0-based Create button candidate index")
    flow_p.add_argument("--name", default="", help="Optional name to type after clicking Create")
    flow_p.add_argument("--move-top-left", action="store_true", help="Move the game window to (0,0) first")
    flow_p.add_argument("--message", action="store_true", help="Use window messages for the full flow (slot/create/name/confirm) without moving the OS cursor")
    flow_p.add_argument("--confirm-x", type=float, default=CONFIRM_BUTTON_DEFAULT[0], help="Name-confirm button x ratio")
    flow_p.add_argument("--confirm-y", type=float, default=CONFIRM_BUTTON_DEFAULT[1], help="Name-confirm button y ratio")
    flow_p.add_argument("--confirm-enter", action="store_true", help="Press Enter instead of clicking the name-confirm button")
    flow_p.add_argument("--input-x", type=float, default=NAME_INPUT_DEFAULT[0], help="Name-input box x ratio")
    flow_p.add_argument("--input-y", type=float, default=NAME_INPUT_DEFAULT[1], help="Name-input box y ratio")
    flow_p.add_argument("--settle-seconds", type=float, default=1.0, help="Wait before the first slot click")
    flow_p.add_argument("--wait-char-screen-seconds", type=float, default=15.0, help="Wait until the character-creation screen is visibly ready")
    flow_p.add_argument("--slot-repeat", type=int, default=2, help="How many times to click the selected slot")
    flow_p.add_argument("--slot-interval", type=float, default=0.20, help="Delay between repeated slot clicks")
    flow_p.add_argument("--post-slot-seconds", type=float, default=0.60, help="Delay after the slot clicks before Create")
    flow_p.add_argument("--post-create-seconds", type=float, default=0.80, help="Delay after clicking Create before typing")
    flow_p.add_argument("--create-retry-count", type=int, default=3, help="How many times to retry the Create click until the name popup appears")
    flow_p.add_argument("--direct-edit-commit", action="store_true", help="When the name popup appears, write directly into hidden child Edit controls and send Enter")

    edits_p = sub.add_parser("list-edits", help="List hidden child Edit controls under the game window")

    edit_commit_p = sub.add_parser("edit-commit", help="Write text into likely hidden child Edit controls and send Enter")
    edit_commit_p.add_argument("text", help="Text to commit")
    edit_commit_p.add_argument("--first-only", action="store_true", help="Only target the first likely Edit instead of all candidates")
    edit_commit_p.add_argument("--enter-count", type=int, default=1, help="How many Enter presses to send per target Edit")
    edit_commit_p.add_argument("--pre-enter-delay", type=float, default=0.35, help="Seconds to wait after writing text before sending Enter")

    sweep_p = sub.add_parser("sweep-create", help="Click a grid of candidate Create-button positions")
    sweep_p.add_argument("--x0", type=float, required=True)
    sweep_p.add_argument("--x1", type=float, required=True)
    sweep_p.add_argument("--y0", type=float, required=True)
    sweep_p.add_argument("--y1", type=float, required=True)
    sweep_p.add_argument("--cols", type=int, required=True)
    sweep_p.add_argument("--rows", type=int, required=True)
    sweep_p.add_argument("--capture-dir", default="", help="Optional folder for client-only captures after each click")
    sweep_p.add_argument("--message", action="store_true", help="Use window messages instead of moving the OS cursor")

    move_p = sub.add_parser("move-window", help="Move the window to a screen position")
    move_p.add_argument("x", type=int)
    move_p.add_argument("y", type=int)

    cap_p = sub.add_parser("capture", help="Capture the game window or client area to BMP")
    cap_p.add_argument("path", help="Output .bmp path")
    cap_p.add_argument("--client", action="store_true", help="Capture client area only")

    key_p = sub.add_parser("key", help="Send a virtual key")
    key_p.add_argument("key_name", help="ENTER/TAB/ESC/SPACE/LEFT/UP/RIGHT/DOWN")

    key_hold_p = sub.add_parser("key-hold", help="Hold a virtual key for a bounded duration")
    key_hold_p.add_argument("key_name", help="ENTER/TAB/ESC/SPACE/LEFT/UP/RIGHT/DOWN")
    key_hold_p.add_argument("hold_ms", type=int, help="Hold duration in milliseconds")

    text_p = sub.add_parser("text", help="Send unicode text")
    text_p.add_argument("text", help="Text to type")

    args = parser.parse_args()
    hwnd, title = wait_for_window(args.title, args.timeout, pid=(args.pid or None))
    if not (
        args.cmd in {"click-slot-msg", "click-rel-msg"}
        or (args.cmd == "click-create" and args.message)
        or (args.cmd == "click-popup-confirm" and args.message)
        or (args.cmd == "create-flow" and args.message)
        or (args.cmd == "sweep-create" and args.message)
    ):
        focus_window(hwnd)
    else:
        show_window(hwnd)

    if args.cmd == "info":
        print(f"title={title}")
        print(f"window_rect={get_window_rect(hwnd)}")
        print(f"client_rect={get_client_rect_screen(hwnd)}")
        fg = user32.GetForegroundWindow()
        fg_pid = get_window_pid(fg) if fg else 0
        fg_len = user32.GetWindowTextLengthW(fg) if fg else 0
        fg_buf = ctypes.create_unicode_buffer(fg_len + 1) if fg else None
        if fg:
            user32.GetWindowTextW(fg, fg_buf, fg_len + 1)
        print(f"foreground_hwnd={int(fg or 0)} foreground_pid={fg_pid} foreground_title={fg_buf.value if fg_buf else ''!r}")
        try:
            print(f"cursor_pos={get_cursor_pos()}")
        except Exception as exc:
            print(f"cursor_pos_error={exc}")
        return

    if args.cmd == "click-slot":
        x, y = click_slot(hwnd, args.slot)
        print(f"title={title}")
        print(f"clicked_slot={args.slot}")
        print(f"screen_pos=({x},{y})")
        return

    if args.cmd == "click-slot-msg":
        x, y = click_slot_message(hwnd, args.slot)
        print(f"title={title}")
        print(f"clicked_slot_msg={args.slot}")
        print(f"client_pos=({x},{y})")
        return

    if args.cmd == "click-rel":
        x, y = click_relative(hwnd, args.x, args.y)
        print(f"title={title}")
        print(f"clicked_rel=({args.x},{args.y})")
        print(f"screen_pos=({x},{y})")
        return

    if args.cmd == "move-rel":
        x, y = move_relative(hwnd, args.x, args.y)
        print(f"title={title}")
        print(f"moved_rel=({args.x},{args.y})")
        print(f"screen_pos=({x},{y})")
        return

    if args.cmd == "right-click-rel":
        x, y = right_click_relative(hwnd, args.x, args.y)
        print(f"title={title}")
        print(f"right_clicked_rel=({args.x},{args.y})")
        print(f"screen_pos=({x},{y})")
        return

    if args.cmd == "click-create":
        rx, ry = CREATE_BUTTON_CANDIDATES[args.candidate]
        if args.message:
            x, y = click_create_candidate_message(hwnd, args.candidate)
            pos_kind = "client_pos"
            action = "clicked_create_candidate_msg"
        else:
            x, y = click_create_candidate(hwnd, args.candidate)
            pos_kind = "screen_pos"
            action = "clicked_create_candidate"
        print(f"title={title}")
        print(f"{action}={args.candidate}")
        print(f"clicked_rel=({rx},{ry})")
        print(f"{pos_kind}=({x},{y})")
        return

    if args.cmd == "click-popup-confirm":
        if args.message:
            x, y = click_ingame_popup_confirm(
                hwnd,
                x_ratio=args.x,
                y_ratio=args.y,
                message=True,
                wait_seconds=args.wait_seconds,
            )
            pos_kind = "client_pos"
            action = "clicked_popup_confirm_msg"
        else:
            x, y = click_ingame_popup_confirm(
                hwnd,
                x_ratio=args.x,
                y_ratio=args.y,
                message=False,
                wait_seconds=args.wait_seconds,
            )
            pos_kind = "screen_pos"
            action = "clicked_popup_confirm"
        print(f"title={title}")
        print(f"{action}=({args.x},{args.y})")
        print(f"{pos_kind}=({x},{y})")
        return

    if args.cmd == "click-rel-msg":
        x, y = click_relative_message(hwnd, args.x, args.y)
        print(f"title={title}")
        print(f"clicked_rel_msg=({args.x},{args.y})")
        print(f"client_pos=({x},{y})")
        return

    if args.cmd == "create-flow":
        slot_pos, create_pos, input_pos, confirm_pos = run_create_flow(
            hwnd,
            slot=args.slot,
            candidate_index=args.candidate,
            name=args.name,
            move_top_left=args.move_top_left,
            message=args.message,
            confirm_ratio=(args.confirm_x, args.confirm_y),
            confirm_enter=args.confirm_enter,
            input_ratio=(args.input_x, args.input_y),
            settle_seconds=args.settle_seconds,
            wait_char_screen_seconds=args.wait_char_screen_seconds,
            slot_repeat=args.slot_repeat,
            slot_interval=args.slot_interval,
            post_slot_seconds=args.post_slot_seconds,
            post_create_seconds=args.post_create_seconds,
            create_retry_count=args.create_retry_count,
            direct_edit_commit=args.direct_edit_commit,
        )
        print(f"title={title}")
        print(f"slot={args.slot}")
        print(f"slot_pos={slot_pos}")
        print(f"create_candidate={args.candidate}")
        print(f"create_rel={CREATE_BUTTON_CANDIDATES[args.candidate]}")
        print(f"create_pos={create_pos}")
        if args.name:
            print(f"submitted_name={args.name}")
            print(f"input_rel=({args.input_x},{args.input_y})")
            print(f"input_pos={input_pos}")
            if args.confirm_enter:
                print("confirm_method=enter")
            else:
                print(f"confirm_rel=({args.confirm_x},{args.confirm_y})")
                print(f"confirm_pos={confirm_pos}")
        return

    if args.cmd == "list-edits":
        edits = list_child_edits(hwnd)
        print(f"title={title}")
        for item in edits:
            print(
                "edit hwnd={hwnd} visible={visible} enabled={enabled} ctrl_id={ctrl_id} "
                "style=0x{style:08X} exstyle=0x{exstyle:08X} text={text!r}".format(**item)
            )
        return

    if args.cmd == "edit-commit":
        results = commit_name_via_child_edit(
            hwnd,
            args.text,
            enter_count=max(1, args.enter_count),
            all_candidates=not args.first_only,
            pre_enter_delay=max(0.0, args.pre_enter_delay),
        )
        print(f"title={title}")
        for child, child_text in results:
            print(f"committed_edit={child} text={child_text!r}")
        return

    if args.cmd == "sweep-create":
        results = sweep_create(
            hwnd,
            x0=args.x0,
            x1=args.x1,
            y0=args.y0,
            y1=args.y1,
            cols=args.cols,
            rows=args.rows,
            capture_dir=args.capture_dir or None,
            message=args.message,
        )
        print(f"title={title}")
        print(f"sweep_points={len(results)}")
        for row, col, rx, ry, kind, px, py in results:
            print(
                f"row={row} col={col} ratio=({rx:.4f},{ry:.4f}) "
                f"{kind}_pos=({px},{py})"
            )
        return

    if args.cmd == "move-window":
        move_window(hwnd, args.x, args.y)
        print(f"title={title}")
        print(f"window_rect={get_window_rect(hwnd)}")
        print(f"client_rect={get_client_rect_screen(hwnd)}")
        return

    if args.cmd == "capture":
        out_path = os.path.abspath(args.path)
        rect = capture_window(hwnd, out_path, client_only=args.client)
        print(f"title={title}")
        print(f"capture_rect={rect}")
        print(f"saved={out_path}")
        return

    if args.cmd == "key":
        key_name = args.key_name.upper()
        if key_name not in VK_CODES:
            raise SystemExit(f"unsupported key: {args.key_name}")
        send_vk(VK_CODES[key_name])
        print(f"title={title}")
        print(f"sent_key={key_name}")
        return

    if args.cmd == "key-hold":
        key_name = args.key_name.upper()
        if key_name not in VK_CODES:
            raise SystemExit(f"unsupported key: {args.key_name}")
        if args.hold_ms < 20 or args.hold_ms > 2000:
            raise SystemExit("hold_ms must be in 20..2000")
        send_vk_hold(VK_CODES[key_name], args.hold_ms)
        print(f"title={title}")
        print(f"held_key={key_name}")
        print(f"hold_ms={args.hold_ms}")
        return

    if args.cmd == "text":
        send_text(args.text)
        print(f"title={title}")
        print(f"sent_text={args.text}")
        return


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[auto_azrok_ui] {exc}", file=sys.stderr)
        raise
