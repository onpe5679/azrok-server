# u32ws / playazrok.com deployment

- Runtime root: `/home/u32ws/32dev/azroksrv`
- Web/API: `127.0.0.1:8765`
- WebSocket bridge: `127.0.0.1:9201`
- Preservation core: `127.0.0.1:9200`
- Control API: `127.0.0.1:9300`
- Operator account management: `https://<tailnet-host>:9300/admin`
  (Tailscale only; Serve HTTPS 9300 proxies loopback 9300).
- Public route: `https://playazrok.com`, with `/azrok-ws` routed to the bridge.

Run `sync_to_u32ws.ps1 -InitializeState` once from the Windows checkout. Later
syncs omit `-InitializeState`, so live account credentials and server state are
never overwritten. Static HTML/CSS/JS updates are visible after sync; bump their
query-string version when the origin marks them immutable. Restart only the
service whose Python code changed.

Core startup pulls in the web and WebSocket bridge through `Wants=`; both
children use `PartOf=azrok-core.service` so an explicit core restart includes
them. After unit changes run `systemctl --user daemon-reload`. After deploying,
check **all three** services and the real public game handshake, not just HTML:

```sh
systemctl --user is-active azrok-core azrok-web azrok-bridge
PYTHONPATH=tools/bridge_pydeps python3 deploy/u32ws/probe_public_wss.py
```

Expected probe: `PUBLIC_WSS_OK` with heartbeat/calibration/lobby responses.
HTTP 200 or `/api/private-server-status` alone cannot detect an inactive bridge.

