import argparse
import json
import os
import sys
import time

import frida

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from auto_azrok_ui import client_ratio_to_client, client_ratio_to_screen, move_window, wait_for_window
from azrok_frida_input import load_script_source, resolve_pid


def on_message(message, data):
    mtype = message.get("type")
    if mtype == "send":
        payload = message.get("payload", {})
        print(json.dumps(payload, ensure_ascii=False), flush=True)
    elif mtype == "error":
        print(json.dumps(message, ensure_ascii=False), file=sys.stderr, flush=True)
    else:
        print(json.dumps(message, ensure_ascii=False), flush=True)


def attach(pid, script_path):
    session = frida.attach(pid)
    script = session.create_script(load_script_source(script_path))
    script.on("message", on_message)
    script.load()
    return session, script


def resolve_screen_geometry(title, timeout, command):
    hwnd, _title = wait_for_window(title, timeout, pid=None)
    if command.get("move_top_left"):
        move_window(hwnd, 0, 0)
        hwnd, _title = wait_for_window(title, timeout, pid=None)

    start_x, start_y = client_ratio_to_screen(hwnd, 0.5, 0.5)
    start_client_x, start_client_y = client_ratio_to_client(hwnd, 0.5, 0.5)

    if "x" in command and "y" in command:
        return int(hwnd), int(command["x"]), int(command["y"]), int(start_x), int(start_y), int(start_client_x), int(start_client_y), int(start_client_x), int(start_client_y)

    if "x_ratio" not in command or "y_ratio" not in command:
        raise RuntimeError("click command requires x/y or x_ratio/y_ratio")

    client_x, client_y = client_ratio_to_client(hwnd, float(command["x_ratio"]), float(command["y_ratio"]))
    x, y = client_ratio_to_screen(hwnd, float(command["x_ratio"]), float(command["y_ratio"]))
    return int(hwnd), int(x), int(y), int(start_x), int(start_y), int(client_x), int(client_y), int(start_client_x), int(start_client_y)


def resolve_logical_delta(command):
    if "dx" in command and "dy" in command:
        return int(command["dx"]), int(command["dy"])
    return None, None


def iter_new_lines(path, state):
    if not os.path.exists(path):
        return []
    size = os.path.getsize(path)
    if size < state["offset"]:
        state["offset"] = 0
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        f.seek(state["offset"])
        for line in f:
            line = line.strip()
            if line:
                lines.append(line)
        state["offset"] = f.tell()
    return lines


def process_command(script, title, timeout, command):
    ctype = command.get("type")
    if ctype == "observe":
        enabled = bool(command.get("enabled", True))
        result = script.exports_sync.setobserve(enabled)
        print(json.dumps({"command": "observe", "enabled": result}, ensure_ascii=False), flush=True)
        return

    if ctype == "click":
        hwnd, x, y, start_x, start_y, client_x, client_y, start_client_x, start_client_y = resolve_screen_geometry(title, timeout, command)
        dx, dy = resolve_logical_delta(command)
        if dx is None or dy is None:
            dx = int(client_x - start_client_x)
            dy = int(client_y - start_client_y)
        hover_ms = int(command.get("hover_ms", 120))
        hold_ms = int(command.get("hold_ms", 100))
        settle_ms = int(command.get("settle_ms", 100))
        script.exports_sync.activatewithdelta(
            x,
            y,
            hover_ms,
            hold_ms,
            settle_ms,
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
        print(
            json.dumps(
                {
                    "command": "click",
                    "hwnd": hwnd,
                    "x": x,
                    "y": y,
                    "start_x": start_x,
                    "start_y": start_y,
                    "client_x": client_x,
                    "client_y": client_y,
                    "dx": dx,
                    "dy": dy,
                    "hover_ms": hover_ms,
                    "hold_ms": hold_ms,
                    "settle_ms": settle_ms,
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        return

    if ctype == "status":
        status = script.exports_sync.status()
        print(json.dumps({"command": "status", "status": status}, ensure_ascii=False), flush=True)
        return

    raise RuntimeError(f"unsupported command type: {ctype}")


def main():
    parser = argparse.ArgumentParser(description="Persistent Frida session for AZROK input hooks")
    parser.add_argument("--pid", type=int, default=0, help="Optional target PID")
    parser.add_argument("--title", default="AZROK", help="Window title")
    parser.add_argument("--timeout", type=float, default=10.0, help="Window wait timeout")
    parser.add_argument(
        "--script",
        default=os.path.join(SCRIPT_DIR, "azrok_input_hook.js"),
        help="Path to the Frida JS hook",
    )
    parser.add_argument("--commands", required=True, help="JSONL command file to poll")
    parser.add_argument("--observe", action="store_true", help="Enable observe mode on startup")
    parser.add_argument("--poll-ms", type=int, default=100, help="Command poll interval in ms")
    args = parser.parse_args()

    pid = resolve_pid(args.pid, args.title, args.timeout)
    session, script = attach(pid, args.script)
    state = {"offset": 0}

    try:
        if args.observe:
            script.exports_sync.setobserve(True)
        print(json.dumps({"attached_pid": pid, "commands": args.commands}, ensure_ascii=False), flush=True)
        while True:
            for line in iter_new_lines(args.commands, state):
                try:
                    command = json.loads(line)
                    process_command(script, args.title, args.timeout, command)
                except Exception as exc:
                    print(
                        json.dumps({"command_error": str(exc), "line": line}, ensure_ascii=False),
                        file=sys.stderr,
                        flush=True,
                    )
            time.sleep(args.poll_ms / 1000.0)
    finally:
        session.detach()


if __name__ == "__main__":
    main()
