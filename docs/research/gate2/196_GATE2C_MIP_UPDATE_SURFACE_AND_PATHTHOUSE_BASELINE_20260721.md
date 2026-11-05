# 196 Gate 2c mip UpdateSurface fault and corrected PatHouse baseline

## Scope

This investigation started from the carpet's repeated lower-right mip region
after advertising `D3DPTEXTURECAPS_MIPMAP`. It uses the existing one-tab
browser gate and the already-approved saved-character automatic room entry.
No native Windows game instance was launched.

## VERIFIED -- server delivery and the first fault

- The corrected browser socket runtime received the 736-byte PatHouse
  bootstrap and emitted C2S `0x0017` twice plus C2S `0x0008` 51--73 ms later.
  The server signal therefore reached the guest; the fault was after room
  bootstrap, not a network wakeup failure.
- The first exception was an indirect call to address zero. The browser fault
  mapper recorded `ret0=0x7F3FF354`, resolved at runtime as
  `acknex.dll+0x0009F354`.
- Static disassembly at image VA `0x1009F351` is
  `call dword ptr [ecx+0x78]`. For `IDirect3DDevice9`, byte offset `0x78` is
  vtable slot 30, `UpdateSurface`. Its five pushed arguments match the
  standard `UpdateSurface(device, source, sourceRect, destination,
  destinationPoint)` signature.
- The project proxy left `g_device_vtable[30]` null. This is direct evidence
  that this graphics failure was caused by an incomplete standard D3D9 API
  surface, not by a server packet or a null proxy object vtable.

## VERIFIED -- implementation and browser result

- `Device_UpdateSurface` now validates the two texture-backed surfaces,
  format, mip levels, rectangles, destination point, pitch, and bounds. It
  copies rows into the destination texture's retained CPU backing and uploads
  the complete destination resource required by the current host texture
  contract.
- `g_device_vtable[30]` now points at that implementation. The DLL built
  successfully and the DLL hash packaged in
  `Azrok_D3D9Web_pathouse_updatesurface2.zip` is
  `34217B6D4D99B1A1764C56FECA46796BD6E029D244652A64E12C7DD2829994A9`.
- A fresh browser run reached the same PatHouse bootstrap, emitted the normal
  two `0x0017` packets and `0x0008`, and then continued heartbeats. There was
  no `D3D9WEB_PATHOUSE_AV`, `bad UploadResource`, or
  `D3D9WEB_PHASE6_ERROR`.
- The visible 1024x768 scene contains intact walls, furniture, character, and
  HUD. The carpet no longer repeats its lower-right quarter; it matches the
  single large-rug topology of the native reference.
- The three empty-slot lobby labels are intentionally ignored in this
  automatic-entry diagnostic. Document 190 already proves they are local
  selection-layer state, not a PatHouse renderer element.

## INVALIDATED -- performance windows after visual verification

The user reported that a Plaza doorway was clicked while the later profile
windows were being collected. Those FPS, upload, and timing windows mix room
transition state and are discarded. They must not be used as a corrected
PatHouse baseline or as evidence for a buffer-cache decision. The earlier
visual `UpdateSurface` result remains valid because the intact PatHouse and
correct carpet were captured before this invalidated performance sample.

## Next measurement

Re-enter PatHouse in the same browser tab, provide no gameplay input, reject
the transition window, and collect new consecutive steady 120-Present
windows. Only then choose the highest-byte per-frame buffers for bounded exact
content hashing. Suppress an upload only if identical bytes and a previously
successful upload are both directly verified. Do not restore the rejected
host VAO/static-buffer cache.
