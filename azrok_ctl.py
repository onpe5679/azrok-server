# -*- coding: utf-8 -*-
"""
Azrok Plaza - Server control CLI

A thin client over the control API that azrok_launcher.py serves (azrok_control.py).
Same endpoints the web page uses, so agents and humans drive the same surface.

The launcher must already be running.

    python azrok_ctl.py state                       # full snapshot
    python azrok_ctl.py state --watches             # just the client watches
    python azrok_ctl.py packets -n 20               # recent packets
    python azrok_ctl.py send 0x0016                 # send S->C, no payload
    python azrok_ctl.py send 0x0004 01a5804c25      # ... with hex payload
    python azrok_ctl.py macros                      # list recipes
    python azrok_ctl.py macro hansol                # run one
    python azrok_ctl.py pause / resume / step / drop
    python azrok_ctl.py set calib_0004_count 0      # edit proto_state

Exit code is 0 on success, 1 on failure, so scripts can branch on it.
"""
import argparse
import json
import sys
import urllib.error
import urllib.request

DEFAULT_PORT = 9300


def _call(port, path, body=None):
    url = f"http://127.0.0.1:{port}{path}"
    data = json.dumps(body).encode('utf-8') if body is not None else None
    req = urllib.request.Request(
        url, data=data, method='POST' if body is not None else 'GET',
        headers={'Content-Type': 'application/json'} if data else {})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode('utf-8')), r.status
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode('utf-8')), e.code
        except Exception:
            return {'error': str(e)}, e.code
    except urllib.error.URLError as e:
        print(f"cannot reach control panel at {url}", file=sys.stderr)
        print(f"  ({e.reason}) - is azrok_launcher.py running?", file=sys.stderr)
        sys.exit(1)


def _parse_opcode(s):
    return int(s, 16) if s.lower().startswith('0x') else int(s, 10)


def _pp(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def _result(j, code):
    """Print a mutation result and exit accordingly."""
    ok = code < 400 and j.get('ok', True)
    print(j.get('message') or j.get('error') or ('ok' if ok else 'failed'))
    sys.exit(0 if ok else 1)


def main():
    p = argparse.ArgumentParser(description="Azrok server control CLI")
    p.add_argument('--port', type=int, default=DEFAULT_PORT, help="control panel port")
    sub = p.add_subparsers(dest='cmd', required=True)

    st = sub.add_parser('state', help="server + protocol + client state")
    st.add_argument('--watches', action='store_true', help="only the client memory watches")
    st.add_argument('--proto', action='store_true', help="only proto_state")

    pk = sub.add_parser('packets', help="recent packets")
    pk.add_argument('-n', type=int, default=30, help="how many (default 30)")
    pk.add_argument('--dir', choices=['C->S', 'S->C'], help="filter by direction")
    pk.add_argument('--opcode', help="filter by opcode, e.g. 0x000C")

    sd = sub.add_parser('send', help="inject an S->C packet")
    sd.add_argument('opcode', help="e.g. 0x0016")
    sd.add_argument('payload', nargs='?', default='', help="hex, optional")

    sub.add_parser('macros', help="list available recipes")
    mc = sub.add_parser('macro', help="run a recipe")
    mc.add_argument('name')

    sub.add_parser('pause', help="hold outbound auto packets at the gate")
    sub.add_parser('resume', help="release the gate")
    sub.add_parser('step', help="let one held packet through")
    sub.add_parser('drop', help="discard one held packet")

    ss = sub.add_parser('set', help="edit a proto_state key")
    ss.add_argument('key')
    ss.add_argument('value')

    ox = sub.add_parser('ox', help='control deterministic OX mode-2 rounds')
    ox.add_argument('action', choices=['prepare', 'open', 'tick', 'finish', 'counter', 'configure'])
    ox.add_argument('--room-id', default='default')
    ox.add_argument('--question-index', type=int)
    ox.add_argument('--duration-ms', type=int, default=16000)
    ox.add_argument('--exit-mode', choices=['cd', 'd2', 'd4'], default='cd')
    ox.add_argument('--first', type=int)
    ox.add_argument('--second', type=int)
    ox.add_argument('--side0-cells', help='comma-separated grid cells')
    ox.add_argument('--side1-cells', help='comma-separated grid cells')
    ox.add_argument('--questions-json', help='JSON array of custom question objects')

    a = p.parse_args()

    if a.cmd == 'state':
        j, _ = _call(a.port, '/api/state')
        if a.watches:
            _pp(j.get('watches', {}))
        elif a.proto:
            _pp(j.get('proto_state', {}))
        else:
            j.pop('packets', None)  # use `packets` for those
            _pp(j)
        return

    if a.cmd == 'packets':
        j, _ = _call(a.port, '/api/state')
        pkts = j.get('packets', [])
        if a.dir:
            pkts = [x for x in pkts if x['dir'] == a.dir]
        if a.opcode:
            want = f"0x{_parse_opcode(a.opcode):04X}"
            pkts = [x for x in pkts if x['opcode'] == want]
        for x in pkts[-a.n:]:
            tag = '' if x['origin'] == 'auto' else f" [{x['origin']}]"
            print(f"{x['t']}  {x['dir']}  {x['opcode']}  {x['len']:>4}B{tag}  {x['hex'][:64]}")
        if not pkts:
            print("(no matching packets)")
        return

    if a.cmd == 'send':
        try:
            opcode = _parse_opcode(a.opcode)
        except ValueError:
            print(f"bad opcode: {a.opcode}", file=sys.stderr)
            sys.exit(1)
        _result(*_call(a.port, '/api/send',
                       {'opcode': opcode, 'payload': a.payload.replace(' ', '')}))

    if a.cmd == 'macros':
        j, _ = _call(a.port, '/api/macros')
        for name, desc in j.items():
            print(f"\n{name}\n  {desc}")
        return

    if a.cmd == 'macro':
        _result(*_call(a.port, '/api/macro', {'name': a.name}))

    if a.cmd in ('pause', 'resume'):
        j, code = _call(a.port, '/api/pause', {'enabled': a.cmd == 'pause'})
        print(f"paused={j.get('paused')}")
        sys.exit(0 if code < 400 else 1)

    if a.cmd in ('step', 'drop'):
        # Pass {} so _call issues a POST: these mutate, and the API only routes them on POST.
        _result(*_call(a.port, f'/api/{a.cmd}', {}))

    if a.cmd == 'set':
        v = a.value
        if v == 'true':
            v = True
        elif v == 'false':
            v = False
        else:
            try:
                v = int(v, 0)
            except ValueError:
                pass
        j, code = _call(a.port, '/api/protostate', {'key': a.key, 'value': v})
        print(f"{a.key}: {j.get('old')} -> {v!r}" if code < 400 else j.get('error'))
        sys.exit(0 if code < 400 else 1)

    if a.cmd == 'ox':
        body = {
            'action': a.action,
            'room_id': a.room_id,
            'question_index': a.question_index,
            'duration_ms': a.duration_ms,
            'exit_mode': a.exit_mode,
            'first': a.first,
            'second': a.second,
        }
        for key, raw in (
            ('side0_cells', a.side0_cells), ('side1_cells', a.side1_cells)
        ):
            if raw is not None:
                try:
                    body[key] = [int(value, 0) for value in raw.split(',') if value.strip()]
                except ValueError:
                    print(f'bad {key}: {raw}', file=sys.stderr)
                    sys.exit(1)
        if a.questions_json is not None:
            try:
                body['questions'] = json.loads(a.questions_json)
            except json.JSONDecodeError as exc:
                print(f'bad questions JSON: {exc}', file=sys.stderr)
                sys.exit(1)
        _result(*_call(a.port, '/api/ox', body))


if __name__ == '__main__':
    main()
