# Acknex / 3DGS Notes For Packet-First Scene Loading

This note keeps only manual-backed engine rules that matter for the remaining
problem:

- network handshake progressed
- the client still shows a baked loading image
- local scene/bootstrap then stalls or crashes before real 3D room entry

## Manual-backed facts that constrain reconstruction

### `level_load` is a local engine transition, not a network object spawn

- `level_load` closes the current level, purges the cache holding level entity
  files, removes the old level entities, and invalidates entity pointers that
  referred to them.
- Non-entity functions such as `main()` keep running across the level change.
- `on_level` is the intended hook for displaying a progress bar or animation on
  a panel while loading.
- `last_error` becomes valid one frame after `level_load`.

Implication for us:

- a correct packet stream should make the client enter its own local
  `level_load` path and then finish that path cleanly
- a changed loading bar, changed help text, or progressed popup state does not
  prove room entry; those can still be panel activity during `level_load`
- stale entity pointers and stale UI pointers are plausible if the client
  crosses a level transition with the wrong scene data

### Resource mount success is not the same thing as resource lookup success

- `WRS` resources in the work folder are automatically opened at engine start.
- `acknex.wdf` is the starter-window definition file generated at publish time
  and interpreted by the engine before the script is read.
- If a starter window definition has a syntax/image-format problem, publish
  issues `ERRNO` and does not create a valid `acknex.wdf`.
- If two files with the same name exist externally and inside a resource,
  external files normally have priority. `preload_mode >= 16` is the release
  switch that forces entities and levels to load only from resources.

Implication for us:

- a late `E1515 ... acknex.wdf` popup is weak evidence for literal
  `acknex.wdf` corruption
- the stronger reading is still "the engine hit an invalid argument / null
  object during later scene or UI work"
- `Lobby -> Plaza` or `PatHouse` experiments can fail even if the archive is
  mounted, because later asset lookup may still resolve the wrong external
  override, wrong file name, or a null scene object

### Scene and entity creation still depend on valid local assets and stage

- `ent_create` / `ent_createlocal` return a pointer to the created entity.
- A level must already be loaded before creating level entities.
- `ent_createlocal` changes locality only; it does not relax asset lookup or
  pointer-validity rules.
- The entity file cache used by `ent_create` is cleared by `level_load`.
- `preload_mode` changes when meshes, textures, and environment lighting are
  created, but it does not make missing assets or wrong pointers valid.

Implication for us:

- packet-first reconstruction must supply scene/stage data that lets the client
  naturally reach its own local create path
- if the packet data drives the client into a stage where named assets such as
  sky, water, sound, room, or child widgets are not yet valid, later code can
  still dereference nulls even though the network side looked correct
- `preload_mode` can shift timing, but it is not a root fix for the stuck
  loading-screen problem

### The loading screen is panel/window state, not evidence of gameplay

- `on_level` explicitly exists so a progress bar or animation can run on a
  panel during loading.
- `pan_create` returns `NULL` if panel creation fails.
- `pan_setwindow` returns `0` if the target window element could not be found
  or created.
- `ptr_remove` removes engine objects, makes the removed object invalid, and a
  second removal can crash; removing an object does not null every pointer to
  it.

Implication for us:

- a stuck baked loading screen is consistent with a panel/window lifetime bug:
  created but not finalized, removed but still referenced, or partially updated
- a progressed tutorial/help message on top of the baked art is not evidence of
  playable 3D world entry
- packet-first success must be judged by:
  - real 3D room visible
  - loading panel gone
  - player input attached to the room, not by text or bar motion alone

### `E1515` is generic invalid-argument / null-object territory

- `Error E1515: Invalid arguments` means a function got the wrong argument type
  or number, or a `NULL` pointer where a valid object pointer was expected.
- Nearby error families are:
  - `W1501`: empty pointer
  - `E1514`: invalid pointer or handle
  - `E1516`: invalid or already-freed pointer / overwritten memory

Implication for us:

- once the handshake has progressed and the client is already in scene/UI work,
  `E1515` is more consistent with bad runtime arguments, null resources, or bad
  stage ordering than with startup-only starter-window generation

## Best-fit explanation for the current baked-loading symptom

The strongest manual-consistent explanation is:

1. packets are now sufficient to advance the client into its local load path
2. the client creates or updates loading-panel state during that load
3. one or more scene/bootstrap arguments are still wrong enough that local
   asset lookup or stage-specific object creation remains incomplete
4. later code continues running across the transition and touches a null or
   stale object before the loading panel is properly finalized

That explains why we can see:

- progressed handshake
- changed loading text / changed loading bar
- sometimes progressed popup close flags
- but still no stable 3D room entry

## Packet-first constraints

For packet-first reconstruction, the packets must do more than "keep the socket
alive":

- the scene path and scene-stage values must drive the client into the correct
  local `level_load` target
- the packet set must be coherent enough that local scene/bootstrap code can
  resolve required named resources and child UI objects without rescue patches
- success criteria must stay strict:
  - not "text changed"
  - not "bar moved"
  - not "popup flag flipped"
  - only "real room is visible and controllable"

## Sources

- `aWINSTART.htm`
  - http://manual.conitec.net/aWINSTART.htm
- `wed_publish.htm`
  - http://manual.conitec.net/wed_publish.htm
- `alevel_load.htm`
  - http://manual.conitec.net/alevel_load.htm
- `on_level.htm`
  - http://manual.conitec.net/on_level.htm
- `last_error.htm`
  - http://manual.conitec.net/last_error.htm
- `ent_create.htm`
  - http://manual.conitec.net/ent_create.htm
- `preload_mode.htm`
  - http://manual.conitec.net/preload_mode.htm
- `pan_create.htm`
  - http://manual.conitec.net/pan_create.htm
- `pan_setwindow.htm`
  - http://manual.conitec.net/pan_setwindow.htm
- `ptr_remove.htm`
  - http://manual.conitec.net/ptr_remove.htm
- `engineerrors.htm`
  - http://manual.conitec.net/engineerrors.htm
