# 651 Plaza chat account identity

## VERIFIED — source and executed regression

Dynamic accounts are `a` plus 12 URL-safe characters (13 total).
`AzrokServer._client_protocol_context` copied account_name to public metadata
using `[:12]`, confusing the character display-name limit with account identity.
`serve_private_chat_state` and `serve_private_chat_say` match the full signed
ticket account exactly, so they cannot find these connected accounts.

Preserve the full account_name when copying metadata. No ticket or login
validation is weakened. `tools/test_private_chat_account_identity.py` executes
the actual context and chat HTTP handler, including a different account with
the same first 12 characters. Old deployed method fails the test; fixed method
passes. Existing server layers/private admission suites: 138 tests passed.

## VERIFIED — deployment

Applied only this account-line fix to existing production server source; other
concurrent candidate edits are not deployed. Backup:
`rollback/plaza-chat-20260927/azrok_server.py` in production root.
Deployed SHA256: `7d3687fe91618a6bcd630cf9fc6461943f0ac60b2bd67589296992753c3f42c2`.
Core restart reports active. Before fix live overview account length was12;
after restart/reconnect it is13. Account text and admission tickets omitted.

Public WebSocket + HTTP probe `tools/probe_private_chat_identity.py` passes:
13-byte diagnostic login is found before Plaza (ready false), and after a
protocol stage-0 report it is found with ready true, room27, same entity.
No chat is sent and no character data is edited. This proves public admission,
not rendered GUI entry. Cloudflare rejects Python's default User-Agent (1010);
the probe uses a browser User-Agent, with all application admission unchanged.

## VERIFIED — production GUI

Actual Plaza Enter opens the visible chat input overlay with both test characters
rendered. Screenshot: `artifacts/20260927_plaza_enter_chat.png`. No message was
sent. Initial five-minute diagnostic ticket expired during setup (HTTP403);
renewed diagnostic ticket passed. Normal production ticket settings unchanged.
Quest findings are in652; information response deployment and GUI proof in653.
