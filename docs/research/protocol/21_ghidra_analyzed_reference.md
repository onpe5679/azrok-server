# Ghidra Analyzed Reference

Source: `Azrok_analyzed.exe` via Ghidra MCP (2026-03-31)
Total renamed functions: 101 (+ ~35 thunk wrappers)
Custom struct types: 18

## Dispatch Functions

| Address | Name | Signature |
|---------|------|-----------|
| 0x00594310 | `DispatchInbound_ByClientMode` | `void __thiscall (void*, int opcode, byte* payload, int payload_len)` |
| 0x0050CBC0 | `DispatchState0Common_S2C` | `void __thiscall (void*, int opcode, byte* payload)` |
| 0x0059DD20 | `DispatchState0Specific_S2C` | - |
| 0x00613740 | `DispatchState1_S2C` | - |

## S2C Handlers

| Address | Name | Opcode |
|---------|------|--------|
| 0x0059E070 | `HandleS2C_0000_LoadLobbySparseCache` | 0x0000 |
| 0x0050D0E0 | `HandleS2C_0000_SelectLobbyEntryScene` | 0x0000 |
| 0x0050D360 | `HandleS2C_0001_ResetLatchOrRaiseError` | 0x0001 |
| 0x00615610 | `HandleS2C_0003_ForwardStateValue` | 0x0003 |
| 0x0059DE50 | `HandleS2C_0004_CalibrationSample` | 0x0004 |
| 0x0059E1F0 | `HandleS2C_0006_ResetLocalClockAndSeed` | 0x0006 |
| 0x0059E330 | `HandleS2C_0007_LoadSetupBlob` | 0x0007 |
| 0x0050D290 | `HandleS2C_0007_EmitPostSetupStateRequest` | 0x0007 |
| 0x00615650 | `HandleS2C_0064_ApplyAuthoritativeSelf` | 0x0064 |
| 0x00615B20 | `HandleS2C_0065_FlushRemoteActors` | 0x0065 |
| 0x00615B50 | `HandleS2C_0066_BatchRemoteActorSpawn` | 0x0066 |
| 0x00615D00 | `HandleS2C_0067_RemoveRemoteActor` | 0x0067 |
| 0x00615D50 | `HandleS2C_0068_BatchActorState` | 0x0068 |
| 0x00615E70 | `HandleS2C_0069_ApplyActorActionState` | 0x0069 |
| 0x00615FF0 | `HandleS2C_006A_ApplyActorTextPayload` | 0x006A |
| 0x00615340 | `HandleS2C_006B_UpdateSelfStateField33A` | 0x006B |
| 0x00615410 | `HandleS2C_006C_UpdateActorStateFields336_33A` | 0x006C |
| 0x006154E0 | `HandleS2C_006D_AdvanceActorField332Stage` | 0x006D |
| 0x006165B0 | `HandleS2C_000C_ApplyActorSlotValue` | 0x000C |
| 0x006169D0 | `HandleS2C_006E_CommitReadyMode` | 0x006E |
| 0x00616B20 | `HandleS2C_006F_SetSelectorPair` | 0x006F |
| 0x00616860 | `HandleS2C_0070_HandleLatchedDualForm` | 0x0070 |
| 0x00616510 | `HandleS2C_0071_SynthesizeLocalFE` | 0x0071 |
| 0x006167E0 | `HandleS2C_03E8_ShowState1SystemNotice` | 0x03E8 |

## C2S Handlers

| Address | Name | Opcode |
|---------|------|--------|
| 0x006130B0 | `SendC2S_0064_LocalBootstrapStatus` | 0x0064 |

## Lobby / Bootstrap

| Address | Name |
|---------|------|
| 0x0050D1C0 | `Lobby_CopyBootstrapBlob_0183` |
| 0x005A00A0 | `LobbySparseRecordTable_InsertIfNonzero` |
| 0x005A0020 | `LobbySparseRecordTable_Reset` |

## Stat / Schema System

| Address | Name |
|---------|------|
| 0x005A37A0 | `StatSchema_LoadFallbackAndMapNames` |
| 0x005A3540 | `StatSchema_LookupIdByName` |
| 0x005AA090 | `StatRegistry_WriteGroupedKeyValue` |
| 0x005A3020 | `Stats_ApplyLocalArchetypeSeed` |
| 0x005A4880 | `Stats_StoreClampedValue` |

## Domain / Event System

| Address | Name |
|---------|------|
| 0x0059A460 | `DomainCode_ClassifyBucket` |
| 0x0059A6E0 | `DomainCode_EmitLocalEffect` |
| 0x005AB010 | `DomainBank_ImportByteBank10` |
| 0x005AB080 | `DomainSelector_ImportByteVector4` |

## RuntimeRowTable (tri-table)

| Address | Name |
|---------|------|
| 0x005A5AB0 | `RuntimeRowTable_ImportFrom0007` |
| 0x005A5730 | `RuntimeRowTable_ResetWorkingAndMirror` |
| 0x005A5830 | `RuntimeRowTable_ImportExternalBuffer` |
| 0x005A58D0 | `RuntimeRowTable_MergeActiveRows` |
| 0x005A59E0 | `RuntimeRowTable_ExportCompactActiveRows` |
| 0x005A5BC0 | `RuntimeRowTable_SnapshotTo50Bytes` |

## Actor System

| Address | Name |
|---------|------|
| 0x00524DA0 | `Actor_SetTargetCoordsAndVisualSync` |
| 0x00524EB0 | `Actor_Apply0068StateRecord` |
| 0x005250C0 | `Actor_Apply0069ActionState` |
| 0x00525050 | `Actor_SetField133` |
| 0x00525080 | `Actor_SetFields137_13B` |
| 0x00526DF0 | `Actor_ClearAttachedEntityAndResetTransition` |
| 0x00526EC0 | `Actor_ResetTransitionState` |
| 0x00527720 | `Actor_ResetFields32E_332` |
| 0x00527970 | `Actor_ResetFields336_33A` |
| 0x00527BB0 | `Actor_ResetFields33E_346` |
| 0x0050ECB0 | `Actor_SetSecondaryText` |

## Remote Actor

| Address | Name |
|---------|------|
| 0x0050C960 | `RemoteActorListNodePool_Alloc` |
| 0x0050C700 | `RemoteActorList_Append` |
| 0x0050D690 | `RemoteActorPool_AllocUnusedSlot` |
| 0x0050D730 | `RemoteActorSlot_IsInUse` |
| 0x0050D760 | `RemoteActorSlot_SetInUse` |
| 0x0050D790 | `RemoteActor_EnsureFrom0066Record` |
| 0x00524620 | `RemoteActor_FinalizeSpawnVisualState` |
| 0x005243E0 | `RemoteActor_InitFrom0066Record` |
| 0x0050F0A0 | `RemoteActor_RefreshSceneTint` |
| 0x005245F0 | `RemoteActor_SetSpawnVariantFlag` |
| 0x0050E560 | `State1Runtime_FindRemoteActorByActorId` |

## Scene / Protocol

| Address | Name |
|---------|------|
| 0x00527A40 | `SetPendingSceneCode` |
| 0x005FFBC0 | `SetPendingSceneArg0` |
| 0x005FFBF0 | `SetPendingSceneArg2` |
| 0x005FFC50 | `SetPendingSceneArg3` |
| 0x00600970 | `SetPendingSceneArg1` |
| 0x00619470 | `SceneGate_IsState6FReady` |
| 0x0050C2B0 | `ProtocolRoot_GetState1TextSubsystem` |
| 0x00599150 | `ProtocolState_SetField130Value` |
| 0x0050F010 | `RemoteSync_GetTickBias` |
| 0x0050F070 | `RemoteSync_UseAdditiveTickBias` |

## Scene / Room System

| Address | Name |
|---------|------|
| 0x00509200 | `GameManager_PerFrameUpdate` |
| 0x0050A0F0 | `GameManager_DispatchRoomCode` |
| 0x0050B400 | `GameManager_ExecuteRoomInit` |
| 0x0050A840 | `GameManager_CloseLoadingScreen` |
| 0x0050b090 | `GameManager_EnqueueDefaultRoom` |
| 0x0050a7f0 | `GameManager_EnqueueRoomCode` |
| 0x0050FE80 | `ButtonQueue_Push` |
| 0x0050FFD0 | `ButtonQueue_Pop` |
| 0x0050D200 | `HandleS2C_0003_StoreSpacePath` |

## Hansol / Plaza

| Address | Name |
|---------|------|
| 0x00614370 | `Hansol_SceneStageHandler` |
| 0x00614720 | `Hansol_Stage6Handler` |
| 0x004f3ad0 | `Hansol_GetSubsystemOffset` |
| 0x00568770 | `Plaza_TransitionFromRoom` |
| 0x00528490 | `GameManager_SetHansolFlag` |
| 0x005284c0 | `GameManager_SetOXQuizFlag` |
| 0x005283e0 | `GameManager_ResetTransitionFlags` |
| 0x00531640 | `PatHouse_RoomInit` |
| 0x0050dd10 | `GameManager_ProcessChatInput` |
| 0x00613470 | `Hansol_PerFrameUpdate` |

## Stat / Bootstrap

| Address | Name |
|---------|------|
| 0x0059ECA0 | `HandleS2C_000A_StatRegistry` |
| 0x0059EEE0 | `HandleS2C_000B_XPCurve` |
| 0x0059EBD0 | `HandleS2C_0005_PostLoadState` |
| 0x0059D150 | `HandleS2C_0002_TransitionPrimary` |
| 0x0059E1C0 | `HandleS2C_0001_Primary` |
| 0x0059BC00 | `KeyedByteList_Import` |
| 0x005AA6F0 | `ModePairWriter_Import` |
| 0x005A50F0 | `XPCurve_StoreValues` |
| 0x005A9B50 | `StatCache_ReplayToRegistry` |
| 0x0050CFF0 | `HandleS2C_0005_CommonWrapper` |

## Still-Default Key Functions (candidates for rename)

| Address | Current Name | Known Purpose |
|---------|-------------|---------------|
| 0x00507DF0 | FUN_00507df0 | CGameManager constructor |

---

## S2C Struct Definitions

### S2C_0000_LobbySparseCache (0x183 bytes)

| Offset | Type | Field | Notes |
|--------|------|-------|-------|
| +0x00 | u8 | result_code | 0=success, 2=alt error |
| +0x01 | u8 | lobby_mode | 0→scene 0x6C, nonzero→scene 0x6B |
| +0x56 | u8 | sparse_count | Number of sparse records |
| +0x57 | u8[] | sparse_keys | count entries |
| +0xBB | u8[] | sparse_values | count entries |

### S2C_0007_SetupBlob (0x1D8 bytes)

| Offset | Type | Field | Notes |
|--------|------|-------|-------|
| +0x00 | u8 | header_00 | clock/seed init |
| +0x01 | u8 | header_01 | mode selector (species) |
| +0x02 | u8 | header_02 | field130 value |
| +0x03 | u32 | packed_seed | YYMMDDHH |
| +0x07 | u32 | packed_clock | state dword |
| +0x0B | u16[70] | stat_words | 70 clamped stats |
| +0x97..+0x130 | blocks | opaque blocks | 7 keyed byte-list blocks |
| +0x125 | u8[11] | domain_emit_codes | 0xFF=nop, 0x00=real code! |
| +0x134 | u16[10] | row_kind | runtime row table |
| +0x148 | u16[10] | row_aux | runtime row table |
| +0x15C | u32[10] | row_value | runtime row table |
| +0x184 | u8[8] | tuple_kind | mode bytes |
| +0x18C | u32[8] | tuple_value | mode payload |
| +0x1D4 | u8[4] | bootstrap_selectors | 0xFF=clear, 0=valid |

### S2C_0064_AuthoritativeSelf (0x1B bytes)

| Offset | Type | Field | Notes |
|--------|------|-------|-------|
| +0x00 | u8 | entry_kind | 0x00/0x0A/0x0B/0x14 |
| +0x01 | u8 | selector_0 | |
| +0x02 | u8 | selector_1 | |
| +0x03 | u32 | self_id | actor ID |
| +0x07 | u32 | pos_x_raw | |
| +0x0B | u32 | pos_y_raw | |
| +0x13 | u8 | room_domain | <0x1E triggers reset |

### S2C_0066_RemoteActorRecord (0x1A bytes per record)

| Offset | Type | Field | Notes |
|--------|------|-------|-------|
| +0x00 | u8 | record_kind | 0x0A→scene 0x2E, 0x0B→scene 0x2F |
| +0x01 | u32 | actor_id | |
| +0x18 | u8 | pair_left | 0xFF=skip |
| +0x19 | u8 | pair_right | |

### S2C_006A_ActorTextPayload

| Offset | Type | Field | Notes |
|--------|------|-------|-------|
| +0x00 | u8 | text_kind | 0=white, 1=red, 2=cyan, 3=yellow |
| +0x01 | u8 | text_mode | routing control |
| +0x02 | u32 | actor_id | 0=system when kind==1 |
| +0x06 | char[15] | primary_text | display name |
| +0x15 | char[] | secondary_text | null-terminated |

### S2C_006E_ReadyCommit

| Offset | Type | Field | Notes |
|--------|------|-------|-------|
| +0x00 | u8 | mode_selector | |
| +0x01 | u8 | ready_gate | 0=commit, nonzero=reject |

---

## Game Classes (key ones)

**Core:** CGameManager, CLogicManager, CClientPeer, CGame, CConnection, CNetwork, CPacket
**UI:** CPopupLoading, CPopupSelectEgg, CPopupSelectPet, CPopupMainMenu, CPopupStatus
**Game:** CPlayerInfo, CPlayerAni, CEquipMent, CInventory, CQuest, CSound, CEffect
**JS Bindings:** CJSLogic, CJSCommand, CJSProperty, CJSStatus, CJSInventory, CJSShop
**Networking:** TcpClient, TcpPeer, CClientPeer, Replicator, Monitor
