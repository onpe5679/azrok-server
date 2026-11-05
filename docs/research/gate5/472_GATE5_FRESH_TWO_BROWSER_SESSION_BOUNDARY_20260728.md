# Gate 5 fresh two-browser session boundary (2026-07-28)

## Runtime result

- **VERIFIED (two live browser tabs):** a fresh `player` browser session reached character select, connected with existing `Azrok1`, completed its original tutorial screen, and rendered the PatHouse scene. A separately launched `peer111` browser session passed the earlier cold boot/compile delay and reached the original character-creation screen. Both BGM fallback media elements stayed unmuted and playing.
- **VERIFIED (server GUI):** the shared loopback preservation core reported two simultaneously connected players, with distinct accounts `player` and `peer111`, current heartbeats, and no public listener. TCP inspection showed each browser WSS connection on the private `<lan-ip>:9201` bridge and each bridge TCP leg only to `127.0.0.1:9200`.
- **VERIFIED (non-synthetic input):** the primary session entered its existing character by visible canvas clicks and dismissed its tutorial by Enter. The peer selection and create controls were exercised only with visible canvas input; no protocol packet was fabricated.

## Boundary

- **NOT VERIFIED:** the peer's create click has not produced the original name dialog or `char_created`; the server still records `peer111` as unbound and no client `0x0007` creation packet arrived.
- **NOT VERIFIED:** the primary's natural click at the visible PatHouse doorway did not produce `0x0019`; both clients therefore remain `state-0 local`, with Plaza count zero, no actor roster, no movement relay, and no targeted leave proof.
- **NOT VERIFIED:** 50-fps multiplayer performance. This run contains one fast primary frame readout and a slower peer during cold compilation, not the canonical visible 30-second A-B-A Present samples.
