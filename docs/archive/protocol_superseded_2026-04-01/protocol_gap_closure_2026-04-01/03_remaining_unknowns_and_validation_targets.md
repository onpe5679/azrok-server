# Remaining Unknowns And Validation Targets

## What is now closed

- `C->S 0x0017` sender and wire layout are recovered.
- `C->S 0x0064` sender and 1-byte wire layout are recovered.
- `C->S 0x000C` sender, payload length, dirty-check gate, and two higher-level callsites are recovered.

## What is still not fully closed

### Exact byte meaning inside `C->S 0x000C`

- The payload builder is known.
- The exact semantic map from each emitted delta byte to server-authoritative slot/domain/equipment meaning is still not fully named.
- This is the main remaining blocker before a byte-perfect server reply contract can be declared.

### Exact high-level naming of the two recovered `0x000C` caller paths

- `FUN_005ba900` looks like a reset/finalize path that sends the latest snapshot before clearing several local states.
- `FUN_005bc970` looks like a UI selection/confirm path with menu-like codes `0x104..0x107`, scroll handling, gating, local effect emission, and local apply/finalize work.
- Strong inference: both belong to the same domain/equipment/selection subsystem, but their final user-facing labels are still unnamed.
- This is the remaining distinction between "wire sender recovered" and "single fully named producer subsystem recovered".

## Best next validation pass

1. Instrument real play to capture exactly what user action causes each `0x000C`.
2. Correlate each user action with the three observed payload families in:
   - [packets_log.txt](<home>/Documents/<project-dir>/Azrok_Plaza/packets_log.txt#L382)
   - [packets_log.txt](<home>/Documents/<project-dir>/Azrok_Plaza/packets_log.txt#L410)
   - [packets_log.txt](<home>/Documents/<project-dir>/Azrok_Plaza/packets_log.txt#L438)
3. Build the translation table from outbound delta byte position/value to authoritative server-side slot update.
4. Only then finalize the server response as one of:
   - one `S->C 0x000C` per changed slot
   - or `S->C 0x000C` plus adjacent `0x0068/0x0069` actor-state refreshes

## Current confidence summary

- High confidence:
  - `0x0017` sender/layout
  - `0x0064` sender/layout
  - `0x000C` send length, dirty-check gate, and non-symmetry with inbound `S->C 0x000C`
- Medium confidence:
  - `0x000C` is a selection/domain/equipment snapshot packet
  - the server should translate it into authoritative slot updates rather than echo it
- Low confidence:
  - the exact slot-by-slot byte map for all 11 outbound `0x000C` bytes
