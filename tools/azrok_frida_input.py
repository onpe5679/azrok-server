import argparse
import json
import os
import sys
import time

import frida

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from auto_azrok_ui import client_ratio_to_client, client_ratio_to_screen, find_window, focus_window, move_window, wait_for_window


def load_script_source(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def resolve_pid(pid, title, timeout):
    if pid:
        return pid
    hwnd, _title = wait_for_window(title, timeout, pid=None)
    if not hwnd:
        raise RuntimeError(f"Window not found: {title}")
    import ctypes
    import ctypes.wintypes as wt

    user32 = ctypes.windll.user32
    proc_id = wt.DWORD(0)
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc_id))
    return proc_id.value


def on_message(message, data):
    mtype = message.get("type")
    if mtype == "send":
        payload = message.get("payload", {})
        print(json.dumps(payload, ensure_ascii=False))
    elif mtype == "error":
        print(json.dumps(message, ensure_ascii=False), file=sys.stderr)
    else:
        print(json.dumps(message, ensure_ascii=False))


def encode_ansi_name_bytes(text):
    try:
        encoded = text.encode("cp949")
    except UnicodeEncodeError:
        encoded = text.encode("mbcs", errors="replace")
    return list(encoded)


def attach(pid, script_path):
    session = frida.attach(pid)
    script = session.create_script(load_script_source(script_path))
    script.on("message", on_message)
    script.load()
    return session, script


def wait_for_script_idle(script, timeout_seconds=5.0, poll_seconds=0.05):
    deadline = time.time() + timeout_seconds
    last_status = {}
    while time.time() < deadline:
        status = script.exports_sync.status()
        last_status = status
        if (
            not status.get("active")
            and not status.get("movePending")
            and not status.get("leftDown")
            and status.get("motionQueueLength", 0) == 0
            and status.get("cursorQueueLength", 0) == 0
            and status.get("messageQueueLength", 0) == 0
            and status.get("hoverPollsRemaining", 0) == 0
            and status.get("downPollsRemaining", 0) == 0
            and status.get("settlePollsRemaining", 0) == 0
        ):
            return status
        time.sleep(poll_seconds)
    return last_status


def cmd_observe(args):
    pid = resolve_pid(args.pid, args.title, args.timeout)
    session, script = attach(pid, args.script)
    try:
        script.exports_sync.setobserve(True)
        print(f"attached_pid={pid}")
        print(f"observe_seconds={args.seconds}")
        time.sleep(args.seconds)
        print(json.dumps(script.exports_sync.status(), ensure_ascii=False))
    finally:
        session.detach()


def cmd_hit_test_grid(args):
    pid = resolve_pid(args.pid, args.title, args.timeout)
    hwnd, _title = wait_for_window(args.title, args.timeout, pid=pid)
    if args.move_top_left:
        move_window(hwnd, 0, 0)
        hwnd, _title = wait_for_window(args.title, args.timeout, pid=pid)
    x0, y0 = client_ratio_to_screen(hwnd, args.x0_ratio, args.y0_ratio)
    x1, y1 = client_ratio_to_screen(hwnd, args.x1_ratio, args.y1_ratio)
    prime_x, prime_y = client_ratio_to_screen(hwnd, 0.12, 0.45)
    prime_client_x, prime_client_y = client_ratio_to_client(hwnd, 0.12, 0.45)
    start_x, start_y = client_ratio_to_screen(hwnd, 0.5, 0.5)
    start_client_x, start_client_y = client_ratio_to_client(hwnd, 0.5, 0.5)
    focus_window(hwnd)
    session, script = attach(pid, args.script)
    try:
        # Prime the real PatHouse input frame at the previously verified
        # blocked point so this attachment captures the hit-test owner.
        script.exports_sync.activatewithdelta(
            prime_x, prime_y, 80, 80, 120,
            prime_client_x - start_client_x, prime_client_y - start_client_y,
            start_x, start_y, int(hwnd), prime_client_x, prime_client_y,
            start_client_x, start_client_y,
        )
        time.sleep(0.75)
        result = script.exports_sync.hittestgrid(x0, y0, x1, y1, args.step)
        print(f"attached_pid={pid}")
        print(json.dumps(result, ensure_ascii=False))
    finally:
        session.detach()


def cmd_find_exit_click(args):
    pid = resolve_pid(args.pid, args.title, args.timeout)
    hwnd, _title = wait_for_window(args.title, args.timeout, pid=pid)
    x0, y0 = client_ratio_to_screen(hwnd, 0.0, 0.0)
    x1, y1 = client_ratio_to_screen(hwnd, 1.0, 0.90)
    prime_x, prime_y = client_ratio_to_screen(hwnd, 0.12, 0.45)
    prime_client_x, prime_client_y = client_ratio_to_client(hwnd, 0.12, 0.45)
    start_x, start_y = client_ratio_to_screen(hwnd, 0.5, 0.5)
    start_client_x, start_client_y = client_ratio_to_client(hwnd, 0.5, 0.5)
    client_origin_x, client_origin_y = client_ratio_to_screen(hwnd, 0.0, 0.0)
    focus_window(hwnd)
    session, script = attach(pid, args.script)
    try:
        script.exports_sync.setobserve(True)
        script.exports_sync.activatewithdelta(
            prime_x, prime_y, 5000, 80, 120,
            prime_client_x - start_client_x, prime_client_y - start_client_y,
            start_x, start_y, int(hwnd), prime_client_x, prime_client_y,
            start_client_x, start_client_y,
        )
        time.sleep(0.75)
        # We only need the motion phase to make the game publish its world
        # input owner. Cancel before the delayed button-down so no furniture
        # action ring can open and block the exit click.
        script.exports_sync.cancelinput()
        result = script.exports_sync.hittestgrid(x0, y0, x1, y1, args.step)
        print(f"attached_pid={pid}")
        print("exit_scan=" + json.dumps(result, ensure_ascii=False))
        hits = result.get("hits", [])
        if not hits:
            raise RuntimeError("No live action 0x6f pixel found")
        chosen = hits[len(hits) // 2]
        target_x = int(chosen["x"])
        target_y = int(chosen["y"])
        client_x = target_x - client_origin_x
        client_y = target_y - client_origin_y
        print(f"exit_click_screen=({target_x},{target_y})")
        script.exports_sync.activatewithdelta(
            target_x, target_y, 0, 120, args.settle_ms,
            0, 0, target_x, target_y, int(hwnd),
            client_x, client_y, client_x, client_y,
        )
        time.sleep(max(1.0, (args.settle_ms + 500) / 1000.0))
        print(json.dumps(wait_for_script_idle(script, timeout_seconds=3.0), ensure_ascii=False))
    finally:
        session.detach()


def cmd_world_to_screen(args):
    pid = resolve_pid(args.pid, args.title, args.timeout)
    session, script = attach(pid, args.script)
    try:
        result = script.exports_sync.worldtoscreen(args.world_x, args.world_y, args.world_z)
        print(f"attached_pid={pid}")
        print(json.dumps(result, ensure_ascii=False))
    finally:
        session.detach()


def cmd_map_state(args):
    pid = resolve_pid(args.pid, args.title, args.timeout)
    session, script = attach(pid, args.script)
    try:
        result = script.exports_sync.mapstate(args.gm)
        print(f"attached_pid={pid}")
        print(json.dumps(result, ensure_ascii=False))
    finally:
        session.detach()


def cmd_queue_gym(args):
    pid = resolve_pid(args.pid, args.title, args.timeout)
    session, script = attach(pid, args.script)
    result = None
    try:
        print(f"attached_pid={pid}", flush=True)
        result = script.exports_sync.queuegym(args.gm)
        print("queue_gym=" + json.dumps(result, ensure_ascii=False), flush=True)
    finally:
        # Detach before the next native frame consumes the selector.  Keeping
        # Frida attached across Acknex level_load made the diagnostic helper
        # wait indefinitely even though the Gym transition itself succeeded.
        session.detach()
    time.sleep(args.settle_ms / 1000.0)
    print("queue_gym_settled=true", flush=True)


def cmd_queue_room(args):
    pid = resolve_pid(args.pid, args.title, args.timeout)
    session, script = attach(pid, args.script)
    try:
        print(f"attached_pid={pid}", flush=True)
        result = script.exports_sync.queueplazaroom(args.gm, args.room)
        print("queue_room=" + json.dumps(result, ensure_ascii=False), flush=True)
    finally:
        # The native main tick consumes the selector after detach.  Holding a
        # Frida session across Acknex level_load can strand the helper.
        session.detach()
    time.sleep(args.settle_ms / 1000.0)
    print("queue_room_settled=true", flush=True)


def cmd_rotate_project(args):
    pid = resolve_pid(args.pid, args.title, args.timeout)
    hwnd, _title = wait_for_window(args.title, args.timeout, pid=pid)
    prime_x, prime_y = client_ratio_to_screen(hwnd, args.prime_x_ratio, args.prime_y_ratio)
    prime_client_x, prime_client_y = client_ratio_to_client(hwnd, args.prime_x_ratio, args.prime_y_ratio)
    start_x, start_y = client_ratio_to_screen(hwnd, 0.5, 0.5)
    start_client_x, start_client_y = client_ratio_to_client(hwnd, 0.5, 0.5)
    focus_window(hwnd)
    session, script = attach(pid, args.script)
    try:
        # A freshly loaded hook does not see the PatHouse world-input frame
        # until the abstract mouse path becomes active. Prime it at the
        # previously measured blocked point, keeping the same attachment so
        # the captured owner remains available to rotateandproject().
        script.exports_sync.activatewithdelta(
            prime_x, prime_y, 80, 80, 120,
            prime_client_x - start_client_x, prime_client_y - start_client_y,
            start_x, start_y, int(hwnd),
            prime_client_x, prime_client_y, start_client_x, start_client_y,
        )
        time.sleep(0.75)
        result = script.exports_sync.rotateandproject(
            args.world_x, args.world_y, args.world_z, args.delta, args.repeats
        )
        print(f"attached_pid={pid}")
        print(json.dumps(result, ensure_ascii=False))
    finally:
        session.detach()


def maybe_move_top_left(title, timeout):
    hwnd, _title = wait_for_window(title, timeout, pid=None)
    move_window(hwnd, 0, 0)
    return hwnd


def resolve_screen_geometry(args, pid=None):
    hwnd, _title = wait_for_window(args.title, args.timeout, pid=pid)
    if args.move_top_left:
        move_window(hwnd, 0, 0)
        hwnd, _title = wait_for_window(args.title, args.timeout, pid=pid)
    focus_window(hwnd)
    start_x, start_y = client_ratio_to_screen(hwnd, 0.5, 0.5)
    start_client_x, start_client_y = client_ratio_to_client(hwnd, 0.5, 0.5)
    if args.x is not None and args.y is not None:
        return int(hwnd), int(args.x), int(args.y), int(start_x), int(start_y), int(start_client_x), int(start_client_y), int(start_client_x), int(start_client_y)
    if args.x_ratio is None or args.y_ratio is None:
        raise RuntimeError("Either --x/--y or --x-ratio/--y-ratio is required")
    client_x, client_y = client_ratio_to_client(hwnd, args.x_ratio, args.y_ratio)
    x, y = client_ratio_to_screen(hwnd, args.x_ratio, args.y_ratio)
    return int(hwnd), int(x), int(y), int(start_x), int(start_y), int(client_x), int(client_y), int(start_client_x), int(start_client_y)


def resolve_logical_delta(args, client_x, client_y, start_client_x, start_client_y):
    if args.x_ratio is None or args.y_ratio is None:
        return 0, 0
    return int(client_x - start_client_x), int(client_y - start_client_y)


def cmd_click(args):
    pid = resolve_pid(args.pid, args.title, args.timeout)
    hwnd, x, y, start_x, start_y, client_x, client_y, start_client_x, start_client_y = resolve_screen_geometry(args, pid=pid)
    focus_window(hwnd)
    session, script = attach(pid, args.script)
    try:
        if args.observe:
            script.exports_sync.setobserve(True)
        print(f"attached_pid={pid}")
        print(f"fake_click_hwnd={hwnd}")
        print(f"fake_click_screen=({x},{y})")
        print(f"fake_click_start=({start_x},{start_y})")
        print(f"fake_click_client=({client_x},{client_y})")
        dx, dy = resolve_logical_delta(args, client_x, client_y, start_client_x, start_client_y)
        print(f"fake_click_delta=({dx},{dy})")
        script.exports_sync.activatewithdelta(
            x,
            y,
            args.hover_ms,
            args.hold_ms,
            args.settle_ms,
            dx,
            dy,
            start_x,
            start_y,
            hwnd,
            client_x,
            client_y,
            start_client_x,
            start_client_y,
        )
        base_wait = max(0.25, (args.hover_ms + args.hold_ms + args.settle_ms) / 1000.0)
        time.sleep(base_wait)
        print(json.dumps(wait_for_script_idle(script, timeout_seconds=4.0), ensure_ascii=False))
    finally:
        session.detach()


def cmd_click_sequence(args):
    """Run two world/UI clicks under one Frida attachment.

    Acknex radial menus can close before a second Frida process finishes
    attaching. Keeping both clicks in one session preserves the real engine
    input path while avoiding any direct game-state or button-queue write.
    """
    pid = resolve_pid(args.pid, args.title, args.timeout)
    hwnd, _title = wait_for_window(args.title, args.timeout, pid=pid)
    if args.move_top_left:
        move_window(hwnd, 0, 0)
        hwnd, _title = wait_for_window(args.title, args.timeout, pid=pid)
    focus_window(hwnd)
    start_x, start_y = client_ratio_to_screen(hwnd, 0.5, 0.5)
    start_client_x, start_client_y = client_ratio_to_client(hwnd, 0.5, 0.5)
    x1, y1 = client_ratio_to_screen(hwnd, args.x1_ratio, args.y1_ratio)
    cx1, cy1 = client_ratio_to_client(hwnd, args.x1_ratio, args.y1_ratio)
    x2, y2 = client_ratio_to_screen(hwnd, args.x2_ratio, args.y2_ratio)
    cx2, cy2 = client_ratio_to_client(hwnd, args.x2_ratio, args.y2_ratio)

    session, script = attach(pid, args.script)
    try:
        if args.observe:
            script.exports_sync.setobserve(True)
        print(f"attached_pid={pid}")
        print(f"sequence_click_1_screen=({x1},{y1})")
        print(f"sequence_click_2_screen=({x2},{y2})")
        script.exports_sync.activatewithdelta(
            int(x1), int(y1), args.hover_ms, args.hold_ms, args.inter_click_ms,
            int(cx1 - start_client_x), int(cy1 - start_client_y),
            int(start_x), int(start_y), int(hwnd), int(cx1), int(cy1),
            int(start_client_x), int(start_client_y),
        )
        time.sleep(max(0.25, (args.hover_ms + args.hold_ms + args.inter_click_ms) / 1000.0))
        first = wait_for_script_idle(script, timeout_seconds=3.0)
        print("sequence_click_1_complete=" + json.dumps(first, ensure_ascii=False))

        script.exports_sync.activatewithdelta(
            int(x2), int(y2), args.hover_ms, args.hold_ms, args.settle_ms,
            int(cx2 - cx1), int(cy2 - cy1),
            int(x1), int(y1), int(hwnd), int(cx2), int(cy2), int(cx1), int(cy1),
        )
        time.sleep(max(0.25, (args.hover_ms + args.hold_ms + args.settle_ms) / 1000.0))
        second = wait_for_script_idle(script, timeout_seconds=4.0)
        print("sequence_click_2_complete=" + json.dumps(second, ensure_ascii=False))
    finally:
        session.detach()


def cmd_type(args):
    pid = resolve_pid(args.pid, args.title, args.timeout)
    hwnd, _title = wait_for_window(args.title, args.timeout, pid=None)
    if args.move_top_left:
        move_window(hwnd, 0, 0)
        hwnd, _title = wait_for_window(args.title, args.timeout, pid=None)
    focus_window(hwnd)
    if args.x is not None and args.y is not None:
        x = int(args.x)
        y = int(args.y)
    elif args.x_ratio is not None and args.y_ratio is not None:
        x, y = client_ratio_to_screen(hwnd, args.x_ratio, args.y_ratio)
    else:
        x, y = client_ratio_to_screen(hwnd, 0.5, 0.5)
    session, script = attach(pid, args.script)
    try:
        if args.observe:
            script.exports_sync.setobserve(True)
        print(f"attached_pid={pid}")
        print(f"text_hwnd={int(hwnd)}")
        print(f"text_screen=({int(x)},{int(y)})")
        print(f"text_payload={args.text!r}")
        queued = script.exports_sync.queuetext(int(hwnd), args.text, int(x), int(y))
        print(f"queued_messages={queued}")
        time.sleep(args.settle_ms / 1000.0)
        print(json.dumps(wait_for_script_idle(script, timeout_seconds=2.0), ensure_ascii=False))
    finally:
        session.detach()


def cmd_name_info(args):
    pid = resolve_pid(args.pid, args.title, args.timeout)
    session, script = attach(pid, args.script)
    try:
        print(f"attached_pid={pid}")
        print(json.dumps(script.exports_sync.namewidgetinfo(), ensure_ascii=False))
    finally:
        session.detach()


def cmd_show_name_dialog(args):
    pid = resolve_pid(args.pid, args.title, args.timeout)
    hwnd, _title = wait_for_window(args.title, args.timeout, pid=None)
    if args.move_top_left:
        move_window(hwnd, 0, 0)
        hwnd, _title = wait_for_window(args.title, args.timeout, pid=None)
    focus_window(hwnd)
    session, script = attach(pid, args.script)
    try:
        if args.observe:
            script.exports_sync.setobserve(True)
        print(f"attached_pid={pid}")
        print(json.dumps(script.exports_sync.namewidgetinfo(), ensure_ascii=False))
        print(f"show_result={script.exports_sync.shownamedialog(args.egg_index)}")
        time.sleep(args.settle_ms / 1000.0)
        print(json.dumps(script.exports_sync.namewidgetinfo(), ensure_ascii=False))
        print(json.dumps(wait_for_script_idle(script, timeout_seconds=2.0), ensure_ascii=False))
    finally:
        session.detach()


def cmd_set_name_text(args):
    pid = resolve_pid(args.pid, args.title, args.timeout)
    session, script = attach(pid, args.script)
    try:
        if args.observe:
            script.exports_sync.setobserve(True)
        name_bytes = encode_ansi_name_bytes(args.text)
        print(f"attached_pid={pid}")
        print(json.dumps(script.exports_sync.namewidgetinfo(), ensure_ascii=False))
        print(f"name_bytes={name_bytes}")
        print(f"written={script.exports_sync.setnametextbytes(name_bytes)}")
        time.sleep(args.settle_ms / 1000.0)
        print(json.dumps(script.exports_sync.namewidgetinfo(), ensure_ascii=False))
        print(json.dumps(wait_for_script_idle(script, timeout_seconds=2.0), ensure_ascii=False))
    finally:
        session.detach()


def cmd_focus_name_edit(args):
    pid = resolve_pid(args.pid, args.title, args.timeout)
    hwnd, _title = wait_for_window(args.title, args.timeout, pid=None)
    if args.move_top_left:
        move_window(hwnd, 0, 0)
        hwnd, _title = wait_for_window(args.title, args.timeout, pid=None)
    focus_window(hwnd)
    session, script = attach(pid, args.script)
    try:
        if args.observe:
            script.exports_sync.setobserve(True)
        print(f"attached_pid={pid}")
        print(json.dumps(script.exports_sync.namewidgetinfo(), ensure_ascii=False))
        print(f"focus_result={script.exports_sync.focusnameedit()}")
        time.sleep(args.settle_ms / 1000.0)
        print(json.dumps(wait_for_script_idle(script, timeout_seconds=2.0), ensure_ascii=False))
    finally:
        session.detach()


def cmd_submit_name(args):
    pid = resolve_pid(args.pid, args.title, args.timeout)
    hwnd, _title = wait_for_window(args.title, args.timeout, pid=None)
    if args.move_top_left:
        move_window(hwnd, 0, 0)
        hwnd, _title = wait_for_window(args.title, args.timeout, pid=None)
    focus_window(hwnd)
    session, script = attach(pid, args.script)
    try:
        if args.observe:
            script.exports_sync.setobserve(True)
        name_bytes = encode_ansi_name_bytes(args.text)
        print(f"attached_pid={pid}")
        print(json.dumps(script.exports_sync.namewidgetinfo(), ensure_ascii=False))
        print(f"name_bytes={name_bytes}")
        print(f"submit_result={script.exports_sync.submitnamebytes(name_bytes, args.egg_index)}")
        time.sleep(args.settle_ms / 1000.0)
        print(json.dumps(script.exports_sync.namewidgetinfo(), ensure_ascii=False))
        print(json.dumps(wait_for_script_idle(script, timeout_seconds=2.0), ensure_ascii=False))
    finally:
        session.detach()


def cmd_push_button(args):
    pid = resolve_pid(args.pid, args.title, args.timeout)
    session, script = attach(pid, args.script)
    try:
        if args.observe:
            script.exports_sync.setobserve(True)
        print(f"attached_pid={pid}")
        print(f"button_id=0x{args.button_id:x} ({args.button_id})")
        print(f"param2=0x{args.param2:x}")
        print(f"param3=0x{args.param3:x}")
        result = script.exports_sync.pushbutton(args.button_id, args.param2, args.param3, args.repeat, args.target_caller)
        print(f"push_result={result}")
        time.sleep(args.settle_ms / 1000.0)
        print(json.dumps(script.exports_sync.status(), ensure_ascii=False))
    finally:
        session.detach()


def cmd_prepare_shop(args):
    pid = resolve_pid(args.pid, args.title, args.timeout)
    session, script = attach(pid, args.script)
    try:
        script.exports_sync.setobserve(True)
        print(f"attached_pid={pid}")
        print(f"button_id=0x{args.button_id:x}")
        print(f"synthetic_balance={args.balance}")
        result = script.exports_sync.prepareshop(
            args.button_id, args.balance, args.target_caller
        )
        print(f"prepare_shop_result={result}")
        time.sleep(args.settle_ms / 1000.0)
        print(json.dumps(script.exports_sync.status(), ensure_ascii=False))
    finally:
        session.detach()


def cmd_commit_name_handler(args):
    pid = resolve_pid(args.pid, args.title, args.timeout)
    session, script = attach(pid, args.script)
    try:
        if args.observe:
            script.exports_sync.setobserve(True)
        print(f"attached_pid={pid}")
        print(json.dumps(script.exports_sync.namewidgetinfo(), ensure_ascii=False))
        print(f"commit_result={script.exports_sync.commitnamehandler()}")
        time.sleep(args.settle_ms / 1000.0)
        print(json.dumps(script.exports_sync.status(), ensure_ascii=False))
    finally:
        session.detach()


def main():
    parser = argparse.ArgumentParser(description="Attach a Frida input hook to AZROK / Acknex")
    parser.add_argument("--pid", type=int, default=0, help="Optional target PID")
    parser.add_argument("--title", default="AZROK", help="Window title")
    parser.add_argument("--timeout", type=float, default=10.0, help="Window wait timeout")
    parser.add_argument(
        "--script",
        default=os.path.join(SCRIPT_DIR, "azrok_input_hook.js"),
        help="Path to the Frida JS hook",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    obs = sub.add_parser("observe", help="Observe input API usage for a short period")
    obs.add_argument("--seconds", type=float, default=5.0)

    hit_grid = sub.add_parser("hit-test-grid", help="Read-only scan of world interaction actions")
    hit_grid.add_argument("--x0-ratio", type=float, default=0.0)
    hit_grid.add_argument("--y0-ratio", type=float, default=0.05)
    hit_grid.add_argument("--x1-ratio", type=float, default=1.0)
    hit_grid.add_argument("--y1-ratio", type=float, default=0.75)
    hit_grid.add_argument("--step", type=int, default=16)
    hit_grid.add_argument("--move-top-left", action="store_true")

    find_exit = sub.add_parser("find-exit-click", help="Find live action 0x6f and click it in the same attachment")
    find_exit.add_argument("--step", type=int, default=8)
    find_exit.add_argument("--settle-ms", type=int, default=12000)

    world_screen = sub.add_parser("world-to-screen", help="Project a world position with the live client view")
    world_screen.add_argument("--world-x", type=float, required=True)
    world_screen.add_argument("--world-y", type=float, required=True)
    world_screen.add_argument("--world-z", type=float, required=True)

    map_state = sub.add_parser("map-state", help="Read live player, camera, and named PatHouse entity coordinates")
    map_state.add_argument("--gm", type=lambda x: int(x, 0), required=True)

    queue_gym = sub.add_parser("queue-gym", help="Queue the verified Plaza Gym portal selector for the next native main tick")
    queue_gym.add_argument("--gm", type=lambda x: int(x, 0), required=True)
    queue_gym.add_argument("--settle-ms", type=int, default=8000)

    queue_room = sub.add_parser("queue-room", help="Queue one statically verified Plaza portal selector for the next native main tick")
    queue_room.add_argument("--gm", type=lambda x: int(x, 0), required=True)
    queue_room.add_argument(
        "--room",
        choices=("pathouse", "playroom", "gym", "magic", "cook", "shop", "library", "ground"),
        required=True,
    )
    queue_room.add_argument("--settle-ms", type=int, default=8000)

    rotate_project = sub.add_parser("rotate-project", help="Rotate through the live camera controller and project a world position")
    rotate_project.add_argument("--world-x", type=float, required=True)
    rotate_project.add_argument("--world-y", type=float, required=True)
    rotate_project.add_argument("--world-z", type=float, required=True)
    rotate_project.add_argument("--delta", type=float, required=True)
    rotate_project.add_argument("--repeats", type=int, default=1)
    rotate_project.add_argument("--prime-x-ratio", type=float, default=0.12)
    rotate_project.add_argument("--prime-y-ratio", type=float, default=0.45)

    click = sub.add_parser("click", help="Inject a fake click through the Frida hook")
    click.add_argument("--x", type=int)
    click.add_argument("--y", type=int)
    click.add_argument("--x-ratio", type=float)
    click.add_argument("--y-ratio", type=float)
    click.add_argument("--hover-ms", type=int, default=120)
    click.add_argument("--hold-ms", type=int, default=100)
    click.add_argument("--settle-ms", type=int, default=100)
    click.add_argument("--move-top-left", action="store_true")
    click.add_argument("--observe", action="store_true")

    click_seq = sub.add_parser("click-sequence", help="Inject two fake clicks in one Frida attachment")
    click_seq.add_argument("--x1-ratio", type=float, required=True)
    click_seq.add_argument("--y1-ratio", type=float, required=True)
    click_seq.add_argument("--x2-ratio", type=float, required=True)
    click_seq.add_argument("--y2-ratio", type=float, required=True)
    click_seq.add_argument("--hover-ms", type=int, default=180)
    click_seq.add_argument("--hold-ms", type=int, default=120)
    click_seq.add_argument("--inter-click-ms", type=int, default=1000)
    click_seq.add_argument("--settle-ms", type=int, default=500)
    click_seq.add_argument("--move-top-left", action="store_true")
    click_seq.add_argument("--observe", action="store_true")

    text = sub.add_parser("type", help="Inject fake text messages through the Frida hook")
    text.add_argument("text", help="Text to inject")
    text.add_argument("--x", type=int)
    text.add_argument("--y", type=int)
    text.add_argument("--x-ratio", type=float)
    text.add_argument("--y-ratio", type=float)
    text.add_argument("--settle-ms", type=int, default=350)
    text.add_argument("--move-top-left", action="store_true")
    text.add_argument("--observe", action="store_true")

    sub.add_parser("name-info", help="Dump the inferred game manager / hidden name-edit widget pointers")

    show_name = sub.add_parser("show-name-dialog", help="Call the internal name dialog show helper")
    show_name.add_argument("--egg-index", type=int, default=0)
    show_name.add_argument("--settle-ms", type=int, default=400)
    show_name.add_argument("--move-top-left", action="store_true")
    show_name.add_argument("--observe", action="store_true")

    set_name = sub.add_parser("set-name-text", help="Write ANSI bytes into the hidden name-edit widget")
    set_name.add_argument("text", help="Name text to write")
    set_name.add_argument("--settle-ms", type=int, default=300)
    set_name.add_argument("--observe", action="store_true")

    focus_edit = sub.add_parser("focus-name-edit", help="Call the internal name-edit focus helper")
    focus_edit.add_argument("--settle-ms", type=int, default=300)
    focus_edit.add_argument("--move-top-left", action="store_true")
    focus_edit.add_argument("--observe", action="store_true")

    submit_name = sub.add_parser("submit-name", help="Write the hidden edit buffer and call the internal name-submit handler")
    submit_name.add_argument("text", help="Name text to submit")
    submit_name.add_argument("--egg-index", type=int, default=0)
    submit_name.add_argument("--settle-ms", type=int, default=600)
    submit_name.add_argument("--move-top-left", action="store_true")
    submit_name.add_argument("--observe", action="store_true")

    commit_name = sub.add_parser("commit-name-handler", help="Call the internal name-submit handler directly")
    commit_name.add_argument("--settle-ms", type=int, default=500)
    commit_name.add_argument("--observe", action="store_true")

    push_btn = sub.add_parser("push-button", help="Inject a button event by ID (universal, works for any screen)")
    push_btn.add_argument("button_id", type=lambda x: int(x, 0), help="Button callback ID (e.g. 0x0e for CreatePet)")
    push_btn.add_argument("--param2", type=lambda x: int(x, 0), default=0xFFFFFFFF)
    push_btn.add_argument("--param3", type=lambda x: int(x, 0), default=0xFFFFFFFF)
    push_btn.add_argument("--repeat", type=int, default=120, help="Number of injection repeats (need ~40+ per frame cycle)")
    push_btn.add_argument("--target-caller", type=lambda x: int(x, 0), default=0, help="Only inject for this caller address (0=any)")
    push_btn.add_argument("--settle-ms", type=int, default=500)
    push_btn.add_argument("--observe", action="store_true")

    prepare_shop = sub.add_parser(
        "prepare-shop",
        help="Seed disposable Shop money at validation and add one verified item to cart",
    )
    prepare_shop.add_argument("button_id", type=lambda x: int(x, 0))
    prepare_shop.add_argument("--balance", type=lambda x: int(x, 0), required=True)
    prepare_shop.add_argument("--target-caller", type=lambda x: int(x, 0), default=0x005C3F81)
    prepare_shop.add_argument("--settle-ms", type=int, default=1200)


    args = parser.parse_args()
    if args.cmd == "observe":
        return cmd_observe(args)
    if args.cmd == "hit-test-grid":
        return cmd_hit_test_grid(args)
    if args.cmd == "find-exit-click":
        return cmd_find_exit_click(args)
    if args.cmd == "world-to-screen":
        return cmd_world_to_screen(args)
    if args.cmd == "map-state":
        return cmd_map_state(args)
    if args.cmd == "queue-gym":
        return cmd_queue_gym(args)
    if args.cmd == "queue-room":
        return cmd_queue_room(args)
    if args.cmd == "rotate-project":
        return cmd_rotate_project(args)
    if args.cmd == "click":
        return cmd_click(args)
    if args.cmd == "click-sequence":
        return cmd_click_sequence(args)
    if args.cmd == "type":
        return cmd_type(args)
    if args.cmd == "name-info":
        return cmd_name_info(args)
    if args.cmd == "show-name-dialog":
        return cmd_show_name_dialog(args)
    if args.cmd == "set-name-text":
        return cmd_set_name_text(args)
    if args.cmd == "focus-name-edit":
        return cmd_focus_name_edit(args)
    if args.cmd == "submit-name":
        return cmd_submit_name(args)
    if args.cmd == "commit-name-handler":
        return cmd_commit_name_handler(args)
    if args.cmd == "push-button":
        return cmd_push_button(args)
    if args.cmd == "prepare-shop":
        return cmd_prepare_shop(args)
    raise SystemExit(f"unsupported cmd: {args.cmd}")


if __name__ == "__main__":
    main()
