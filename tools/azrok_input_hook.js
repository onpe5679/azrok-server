"use strict";

const fakeState = {
    active: false,
    hwnd: 0,
    captureHwnd: 0,
    x: 0,
    y: 0,
    targetX: 0,
    targetY: 0,
    clientX: 0,
    clientY: 0,
    startClientX: 0,
    startClientY: 0,
    dx: 0,
    dy: 0,
    movePending: false,
    leftDown: false,
    hoverPollsRemaining: 0,
    downPollsRemaining: 0,
    settlePollsRemaining: 0,
    asyncEdgePending: false,
    motionQueue: [],
    cursorQueue: [],
    messageQueue: [],
    lastMessagePos: 0,
    lastMessageTime: 0,
    lastMessageHwnd: 0,
    armedAt: 0,
    hoverEndAt: 0,
    releaseAt: 0,
    deactivateAt: 0,
    lastDeviceStateTick: 0,
    observe: false,
    observeCounts: {
        getCursorPos: 0,
        getAsyncKeyState: 0,
        getKeyState: 0,
        getMessagePos: 0,
        getMessageTime: 0,
        getCapture: 0,
        setCapture: 0,
        releaseCapture: 0,
        setCursorPos: 0,
        clipCursor: 0,
        directInput8Create: 0,
        createDevice: 0,
        setDataFormat: 0,
        setCooperativeLevel: 0,
        acquire: 0,
        getDeviceState: 0,
        getDeviceData: 0,
        peekMessage: 0,
        showWindow: 0,
        enableWindow: 0,
        setFocus: 0,
        setWindowPos: 0,
        abstractMouseLeft: 0,
        abstractPointer: 0,
        azrokMousePoll: 0,
        worldInputFrame: 0,
        worldHitTest: 0,
        popupBuild: 0,
        popupButton: 0,
        buttonPush: 0,
        buttonRead: 0,
        myBagSetBmpById: 0,
        myBagButtonSetBmp: 0,
        careAction: 0,
        evolutionCheck: 0,
        evolutionCommit: 0,
        evolutionGateRead: 0,
        protocolField130Write: 0,
        nexusBottomFail: 0,
        nexusTopFail: 0,
        e1201Report: 0,
    },
    evolutionGateOwner: "0x0",
    evolutionGateValue: null,
    worldInputOwner: "0x0",
    worldHitOwner: "0x0",
};

const hookedVtables = {};
const hookedDevices = {};

const DI8_CREATE_DEVICE_INDEX = 3;
const DID8_ACQUIRE_INDEX = 7;
const DID8_GET_DEVICE_STATE_INDEX = 9;
const DID8_GET_DEVICE_DATA_INDEX = 10;
const DID8_SET_DATA_FORMAT_INDEX = 11;
const DID8_SET_COOPERATIVE_LEVEL_INDEX = 13;
const WM_KEYDOWN = 0x0100;
const WM_KEYUP = 0x0101;
const WM_CHAR = 0x0102;
const WM_MOUSEMOVE = 0x0200;
const WM_LBUTTONDOWN = 0x0201;
const WM_LBUTTONUP = 0x0202;
const MK_LBUTTON = 0x0001;
const AZROK_GM_PTR_ADDR = ptr("0x006e8430");
const AZROK_NAME_EDIT_OFFSET = 0x0b93;
const AZROK_NAME_EDIT_TEXT_OFFSET = 0x003a;
const AZROK_SELECTED_EGG_OFFSET = 0x0d7b;
const AZROK_NAME_DIALOG_FLAG_PTR = ptr("0x005e7ae0");
const AZROK_NAME_DIALOG_SHOW_PTR = ptr("0x005e80b0");
const AZROK_NAME_EDIT_FOCUS_PTR = ptr("0x00507a30");
const AZROK_NAME_COMMIT_PTR = ptr("0x0050acb0");
const AZROK_ABSTRACT_INPUT_INT_PTR = ptr("0x005328c0");
const AZROK_ABSTRACT_INPUT_VEC3_PTR = ptr("0x00532930");
const AZROK_RAW_MOUSE_POLL_PTR = ptr("0x00508fa0");
const AZROK_WORLD_INPUT_FRAME_PTR = ptr("0x00532980");
const AZROK_WORLD_HIT_TEST_PTR = ptr("0x0055ae90");
const AZROK_VEC_TO_SCREEN_PTR = ptr("0x004e04c5");
const AZROK_CAMERA_DRAG_PTR = ptr("0x004db8df");
const AZROK_ENT_FOR_NAME_PTR = ptr("0x004d8eaa");
const AZROK_POPUP_BUILD_PTR = ptr("0x005e6960");
const AZROK_POPUP_BUTTON_POS_PTR = ptr("0x005196e0");
const AZROK_BUTTON_EVENT_PUSH_PTR = ptr("0x0050fe80");
const AZROK_MYBAG_SET_BMP_BY_ID_PTR = ptr("0x005197a0");
const AZROK_BUTTON_SET_BMP_PTR = ptr("0x0051b5c0");
const AZROK_CARE_ACTION_PTR = ptr("0x00596690");
const AZROK_EVOLUTION_CHECK_PTR = ptr("0x005a6910");
const AZROK_EVOLUTION_COMMIT_PTR = ptr("0x005a7e40");
const AZROK_EVOLUTION_GATE_READ_PTR = ptr("0x005465c0");
const AZROK_PROTOCOL_FIELD130_WRITE_PTR = ptr("0x00599150");
// Plaza portal commit boundary recovered from the original client.  The
// click resolver stores a local-room selector here; the next main game tick
// performs the real level load and emits C2S 0x0065.  Only the fixed Gym
// selector is exposed through RPC so callers cannot invoke arbitrary code.
const AZROK_PLAZA_OWNER_OFFSET = 0x348f9;
const AZROK_PLAZA_PORTAL_OFFSET = 0x0db0;
const AZROK_PLAZA_PHASE_OFFSET = 0x31792;
const AZROK_PLAZA_PENDING_OFFSET = 0x0314;
const AZROK_GYM_SELECTOR = 2;
const AZROK_PLAZA_ROOM_SELECTORS = Object.freeze({
    pathouse: 0,
    playroom: 1,
    gym: 2,
    magic: 3,
    cook: 4,
    shop: 5,
    library: 6,
    ground: 10,
});
const AZROK_PLAZA_PORTAL_COMMIT_PTR = ptr("0x004dbd99");
const queuePlazaPortalNative = new NativeFunction(
    AZROK_PLAZA_PORTAL_COMMIT_PTR,
    "void",
    ["pointer", "int"],
    "thiscall"
);
const ACKNEX_MODULE = Process.getModuleByName("acknex.dll");
const ACKNEX_NEXUS_BOTTOM_FAIL_PTR = ACKNEX_MODULE.base.add(0x003f25c);
const ACKNEX_NEXUS_TOP_FAIL_PTR = ACKNEX_MODULE.base.add(0x003f3d2);
const ACKNEX_ERROR_REPORT_PTR = ACKNEX_MODULE.base.add(0x0034700);
const ACKNEX_NEXUS_BOTTOM_PTR = ACKNEX_MODULE.base.add(0x02fe9b0);
const ACKNEX_NEXUS_TOTAL_PTR = ACKNEX_MODULE.base.add(0x02fe9bc);
const ACKNEX_NEXUS_TOP_PTR = ACKNEX_MODULE.base.add(0x02fe9c0);
const ACKNEX_NEXUS_BASE_PTR = ACKNEX_MODULE.base.add(0x02fe9c8);

const setNameDialogFlagNative = new NativeFunction(AZROK_NAME_DIALOG_FLAG_PTR, "void", ["pointer", "uint"], "thiscall");
const showNameDialogNative = new NativeFunction(AZROK_NAME_DIALOG_SHOW_PTR, "void", ["pointer"], "thiscall");
const focusNameEditNative = new NativeFunction(AZROK_NAME_EDIT_FOCUS_PTR, "void", ["pointer"], "thiscall");
const commitNameNative = new NativeFunction(AZROK_NAME_COMMIT_PTR, "void", ["pointer"], "thiscall");
const abstractInputIntNative = new NativeFunction(AZROK_ABSTRACT_INPUT_INT_PTR, "int", ["pointer"], "stdcall");
const abstractInputVec3Native = new NativeFunction(AZROK_ABSTRACT_INPUT_VEC3_PTR, "pointer", ["pointer", "pointer"], "stdcall");

const AZROK_BUTTON_EVENT_READ_PTR = ptr("0x0050ffd0");
const pendingButtonInjection = { id: -1, param2: 0xFFFFFFFF, param3: 0xFFFFFFFF, remaining: 0, targetCaller: 0 };
const pendingShopPrepare = { armed: false, balance: 0 };

// Test-only Shop preparation boundary.  A discontinued-server client starts
// with model+0x1F0 == 0, so the verified cart validation cannot reach its
// 45-byte purchase send.  Seed only this live scalar at the exact validation
// entry, report the original value, and rely on process restart to discard it.
Interceptor.attach(ptr("0x005A95B0"), {
    onEnter: function (_args) {
        if (!pendingShopPrepare.armed) {
            return;
        }
        const model = this.context.ecx;
        let original = null;
        let vtable = null;
        try {
            original = model.add(0x1F0).readU32();
            vtable = model.readPointer().toString();
            model.add(0x1F0).writeU32(pendingShopPrepare.balance >>> 0);
            notify("shop-money-seeded", {
                model: model.toString(),
                vtable: vtable,
                original: original,
                seeded: pendingShopPrepare.balance >>> 0,
                lock: model.add(0x808).readU32(),
            });
        } catch (err) {
            notify("shop-money-seed-error", { error: String(err) });
        }
        pendingShopPrepare.armed = false;
    },
});

Interceptor.attach(AZROK_BUTTON_EVENT_READ_PTR, {
    onLeave: function (retval) {
        if (fakeState.observe) {
            let buttonId = -1;
            let param2 = 0;
            let param3 = 0;
            try {
                buttonId = retval.readS32();
                param2 = retval.add(4).readS32();
                param3 = retval.add(8).readS32();
            } catch (_err) {
                buttonId = -2;
            }
            maybeSample("buttonRead", {
                caller: this.returnAddress.toString(),
                buttonId: buttonId,
                param2: param2,
                param3: param3,
            });
        }
        if (pendingButtonInjection.remaining > 0) {
            const caller = this.returnAddress.toUInt32();
            if (pendingButtonInjection.targetCaller !== 0 && caller !== pendingButtonInjection.targetCaller) {
                return;
            }
            const buf = retval;
            buf.writeU32(pendingButtonInjection.id);
            buf.add(4).writeU32(pendingButtonInjection.param2);
            buf.add(8).writeU32(pendingButtonInjection.param3);
            pendingButtonInjection.remaining--;
            notify("button-injected", {
                buttonId: pendingButtonInjection.id,
                remaining: pendingButtonInjection.remaining,
                caller: this.returnAddress.toString(),
            });
            if (pendingButtonInjection.remaining <= 0) {
                pendingButtonInjection.id = -1;
            }
        }
    },
});

// Late Frida attachment cannot observe the DirectInput8Create/CreateDevice
// calls that already created Acknex's mouse device.  The live client instead
// polls that existing device in FUN_00508FA0 and writes the left-button state
// to the caller-owned four-dword result at +4.  Patch only that one dword while
// a synthetic click is active; preserve the other raw-input fields.
Interceptor.attach(AZROK_RAW_MOUSE_POLL_PTR, {
    onEnter: function (_args) {
        this.output = null;
        try {
            this.output = this.context.esp.add(4).readPointer();
        } catch (_err) {
            this.output = null;
        }
        maybeSample("azrokMousePoll", {
            output: this.output === null ? "0x0" : this.output.toString(),
        });
    },
    onLeave: function (_retval) {
        if (!fakeState.active || this.output === null || this.output.isNull()) {
            return;
        }
        syncUiOnlyState();
        try {
            const current = this.output.add(4).readU32();
            const patched = fakeState.leftDown
                ? (current | 0x80)
                : (current & 0xffffff7f);
            this.output.add(4).writeU32(patched >>> 0);
            if (fakeState.observe && ((current ^ patched) & 0x80) !== 0) {
                notify("raw-left-patched", {
                    down: fakeState.leftDown,
                    before: current >>> 0,
                    after: patched >>> 0,
                });
            }
        } catch (err) {
            if (fakeState.observe) {
                notify("info", {
                    message: "FUN_00508FA0 output patch failed",
                    error: String(err),
                });
            }
        }
    },
});

Interceptor.attach(AZROK_WORLD_INPUT_FRAME_PTR, {
    onEnter: function (_args) {
        const owner = this.context.ecx;
        fakeState.worldInputOwner = owner.toString();
        let scene = null;
        let inputMode = null;
        try {
            scene = owner.add(0x3084a).readU32();
            inputMode = owner.add(0x30805).readU8();
        } catch (_err) {
            scene = null;
            inputMode = null;
        }
        maybeSample("worldInputFrame", {
            owner: owner.toString(),
            scene: scene,
            inputMode: inputMode,
        });
    },
});

Interceptor.attach(AZROK_WORLD_HIT_TEST_PTR, {
    onEnter: function (args) {
        fakeState.worldHitOwner = this.context.ecx.toString();
        this.screenX = args[0].toInt32();
        this.screenY = args[1].toInt32();
    },
    onLeave: function (retval) {
        maybeSample("worldHitTest", {
            screenX: this.screenX,
            screenY: this.screenY,
            action: retval.toInt32(),
        });
    },
});

// Instrument the live PatHouse interaction path.  These hooks are read-only:
// they expose the actual radial-menu button IDs and prove that a natural care
// action reaches the client-owned evolution state machine.
Interceptor.attach(AZROK_POPUP_BUILD_PTR, {
    onEnter: function (args) {
        maybeSample("popupBuild", {
            owner: this.context.ecx.toString(),
            key: args[0].toInt32(),
            screenX: args[1].toInt32(),
            screenY: args[2].toInt32(),
        });
    },
});

Interceptor.attach(AZROK_POPUP_BUTTON_POS_PTR, {
    onEnter: function (args) {
        maybeSample("popupButton", {
            owner: this.context.ecx.toString(),
            buttonId: args[0].toInt32(),
            screenX: args[1].toInt32(),
            screenY: args[2].toInt32(),
        });
    },
});

Interceptor.attach(AZROK_BUTTON_EVENT_PUSH_PTR, {
    onEnter: function (args) {
        maybeSample("buttonPush", {
            owner: this.context.ecx.toString(),
            buttonId: args[0].toInt32(),
            param2: args[1].toInt32(),
            param3: args[2].toInt32(),
        });
    },
});

// Read-only MyBag bitmap diagnostics.  The first hook records the manager
// lookup contract (button id + requested BMAP); the second records the exact
// CGameButton selected by that lookup and verifies the three state bitmaps
// written by SetBmp.  This distinguishes a bad inventory/Refri mapping from a
// later draw/occlusion failure without patching client state.
Interceptor.attach(AZROK_MYBAG_SET_BMP_BY_ID_PTR, {
    onEnter: function (args) {
        const payload = {
            manager: this.context.ecx.toString(),
            buttonId: args[0].toInt32(),
            bitmap: args[1].toString(),
        };
        maybeSample("myBagSetBmpById", payload);
        if (fakeState.observe && payload.buttonId === 0x189) {
            notify("mybag-slot0-bitmap", payload);
        }
    },
});

Interceptor.attach(AZROK_BUTTON_SET_BMP_PTR, {
    onEnter: function (args) {
        this.button = this.context.ecx;
        this.bitmap = args[0];
        let before = null;
        try {
            before = {
                normal: this.button.add(0x41).readPointer().toString(),
                hover: this.button.add(0x45).readPointer().toString(),
                down: this.button.add(0x49).readPointer().toString(),
            };
        } catch (_err) {
            before = null;
        }
        maybeSample("myBagButtonSetBmp", {
            phase: "enter",
            button: this.button.toString(),
            bitmap: this.bitmap.toString(),
            before: before,
        });
    },
    onLeave: function (_retval) {
        let after = null;
        try {
            after = {
                normal: this.button.add(0x41).readPointer().toString(),
                hover: this.button.add(0x45).readPointer().toString(),
                down: this.button.add(0x49).readPointer().toString(),
            };
        } catch (_err) {
            after = null;
        }
        maybeSample("myBagButtonSetBmp", {
            phase: "leave",
            button: this.button.toString(),
            bitmap: this.bitmap.toString(),
            after: after,
        });
    },
});

Interceptor.attach(AZROK_CARE_ACTION_PTR, {
    onEnter: function (args) {
        maybeSample("careAction", {
            owner: this.context.ecx.toString(),
            arg0: args[0].toInt32(),
            arg1: args[1].toInt32(),
            arg2: args[2].toInt32(),
        });
    },
});

Interceptor.attach(AZROK_EVOLUTION_CHECK_PTR, {
    onEnter: function (args) {
        maybeSample("evolutionCheck", {
            owner: this.context.ecx.toString(),
            kind: args[0].toInt32(),
            arg1: args[1].toInt32(),
            arg2: args[2].toInt32(),
        });
    },
});

Interceptor.attach(AZROK_EVOLUTION_COMMIT_PTR, {
    onEnter: function (args) {
        maybeSample("evolutionCommit", {
            owner: this.context.ecx.toString(),
            target: args[0].toInt32(),
        });
    },
});

Interceptor.attach(AZROK_PROTOCOL_FIELD130_WRITE_PTR, {
    onEnter: function (args) {
        this.owner = this.context.ecx;
        this.value = args[0].toInt32();
        this.before = null;
        try {
            this.before = this.owner.add(0x130).readU32();
        } catch (_err) {
            this.before = null;
        }
    },
    onLeave: function (_retval) {
        let after = null;
        try {
            after = this.owner.add(0x130).readU32();
        } catch (_err) {
            after = null;
        }
        maybeSample("protocolField130Write", {
            owner: this.owner.toString(),
            value: this.value,
            before: this.before,
            after: after,
        });
        if (fakeState.observe) {
            notify("evolution-field-write", {
                owner: this.owner.toString(),
                value: this.value,
                before: this.before,
                after: after,
            });
        }
    },
});

Interceptor.attach(AZROK_EVOLUTION_GATE_READ_PTR, {
    onEnter: function (_args) {
        this.owner = this.context.ecx;
    },
    onLeave: function (retval) {
        const value = retval.toInt32();
        const ownerText = this.owner.toString();
        const changed = fakeState.evolutionGateValue !== value ||
            fakeState.evolutionGateOwner !== ownerText;
        fakeState.evolutionGateOwner = ownerText;
        fakeState.evolutionGateValue = value;
        maybeSample("evolutionGateRead", {
            owner: ownerText,
            value: value,
        });
        if (fakeState.observe && changed) {
            notify("evolution-gate", {
                owner: ownerText,
                value: value,
            });
        }
    },
});

function readNexusArena() {
    try {
        const bottom = ACKNEX_NEXUS_BOTTOM_PTR.readU32();
        const total = ACKNEX_NEXUS_TOTAL_PTR.readU32();
        const top = ACKNEX_NEXUS_TOP_PTR.readU32();
        const base = ACKNEX_NEXUS_BASE_PTR.readPointer();
        return {
            base: base.toString(),
            totalBytes: total,
            bottomUsedBytes: bottom,
            topUsedBytes: top,
            freeBytes: Math.max(0, total - bottom - top),
        };
    } catch (err) {
        return { error: String(err) };
    }
}

function nexusFailurePayload(kind, context) {
    let requestBytes = null;
    let caller = "0x0";
    try {
        caller = context.esp.add(4).readPointer().toString();
        requestBytes = context.esp.add(8).readU32();
    } catch (_err) {
    }
    let backtrace = [];
    try {
        backtrace = Thread.backtrace(context, Backtracer.ACCURATE)
            .slice(0, 20)
            .map(function (address) {
                return DebugSymbol.fromAddress(address).toString();
            });
    } catch (_err) {
    }
    const alignedBytes = kind === "bottom-up"
        ? context.edx.toUInt32()
        : context.esi.toUInt32();
    const availableBytes = kind === "bottom-up"
        ? context.esi.toUInt32()
        : context.ecx.toUInt32();
    const payload = {
        kind: kind,
        caller: caller,
        requestBytes: requestBytes,
        alignedBytes: alignedBytes,
        availableBytes: availableBytes,
        detailValue: kind === "bottom-up"
            ? ((alignedBytes + 1023) >>> 10)
            : alignedBytes,
        arena: readNexusArena(),
        eax: context.eax.toString(),
        ecx: context.ecx.toString(),
        edx: context.edx.toString(),
        esi: context.esi.toString(),
        backtrace: backtrace,
    };
    return payload;
}

// Attach only at the two proven failure branches.  Successful allocations are
// deliberately left untraced so the game timing and logs remain undisturbed.
Interceptor.attach(ACKNEX_NEXUS_BOTTOM_FAIL_PTR, {
    onEnter: function (_args) {
        fakeState.observeCounts.nexusBottomFail += 1;
        notify("nexus-allocation-failure", nexusFailurePayload("bottom-up", this.context));
    },
});

Interceptor.attach(ACKNEX_NEXUS_TOP_FAIL_PTR, {
    onEnter: function (_args) {
        fakeState.observeCounts.nexusTopFail += 1;
        notify("nexus-allocation-failure", nexusFailurePayload("top-down", this.context));
    },
});

Interceptor.attach(ACKNEX_ERROR_REPORT_PTR, {
    onEnter: function (args) {
        if (args[0].toUInt32() !== 0x4b1) {
            return;
        }
        fakeState.observeCounts.e1201Report += 1;
        let backtrace = [];
        try {
            backtrace = Thread.backtrace(this.context, Backtracer.ACCURATE)
                .slice(0, 20)
                .map(function (address) {
                    return DebugSymbol.fromAddress(address).toString();
                });
        } catch (_err) {
        }
        notify("e1201-report", {
            detail: args[2].toUInt32(),
            caller: this.returnAddress.toString(),
            arena: readNexusArena(),
            backtrace: backtrace,
        });
    },
});
const setWindowTextANative = new NativeFunction(getExport("user32.dll", "SetWindowTextA"), "bool", ["pointer", "pointer"], "stdcall");

function notify(type, payload) {
    send({ type: type, payload: payload || {} });
}

function getGameManagerPtr() {
    try {
        const gm = Memory.readPointer(AZROK_GM_PTR_ADDR);
        if (gm.isNull()) {
            return null;
        }
        return gm;
    } catch (_err) {
        return null;
    }
}

function getNameEditObjectPtr() {
    const gm = getGameManagerPtr();
    if (gm === null) {
        return null;
    }
    return gm.add(AZROK_NAME_EDIT_OFFSET);
}

function getNameEditHwnd() {
    const edit = getNameEditObjectPtr();
    if (edit === null) {
        return null;
    }
    try {
        const hwnd = Memory.readPointer(edit.add(0x0c));
        if (hwnd.isNull()) {
            return null;
        }
        return hwnd;
    } catch (_err) {
        return null;
    }
}

function setSelectedEggIndex(index) {
    const gm = getGameManagerPtr();
    if (gm === null) {
        return false;
    }
    try {
        Memory.writeU8(gm.add(AZROK_SELECTED_EGG_OFFSET), index & 0xff);
        return true;
    } catch (_err) {
        return false;
    }
}

function writeAnsiBytesToEdit(edit, hwnd, values) {
    const bytes = [];
    const maxBytes = 12;
    for (let i = 0; i < values.length && bytes.length < maxBytes; i++) {
        bytes.push(values[i] & 0xff);
    }
    const raw = bytes.concat([0]);
    const buf = Memory.alloc(raw.length);
    Memory.writeByteArray(buf, raw);
    Memory.writeByteArray(edit.add(AZROK_NAME_EDIT_TEXT_OFFSET), new Array(13).fill(0));
    Memory.writeByteArray(edit.add(AZROK_NAME_EDIT_TEXT_OFFSET), raw);
    if (hwnd !== null) {
        setWindowTextANative(hwnd, buf);
    }
    return bytes.length;
}

function showNameDialogInternal(index) {
    const gm = getGameManagerPtr();
    if (gm === null) {
        return false;
    }
    if (typeof index === "number" && index >= 0) {
        setSelectedEggIndex(index);
    }
    try {
        setNameDialogFlagNative(gm, 1);
    } catch (_err) {
    }
    showNameDialogNative(gm);
    const edit = getNameEditObjectPtr();
    if (edit !== null) {
        try {
            focusNameEditNative(edit);
        } catch (_err) {
        }
    }
    notify("name-dialog-show", {
        gm: gm.toString(),
        edit: edit ? edit.toString() : null,
        hwnd: (getNameEditHwnd() || ptr(0)).toString(),
        eggIndex: (typeof index === "number") ? (index | 0) : null,
    });
    return true;
}

function setNameTextBytes(values) {
    const edit = getNameEditObjectPtr();
    if (edit === null) {
        return 0;
    }
    const hwnd = getNameEditHwnd();
    const written = writeAnsiBytesToEdit(edit, hwnd, values);
    notify("name-text-set", {
        edit: edit.toString(),
        hwnd: hwnd ? hwnd.toString() : null,
        written: written,
    });
    return written;
}

function submitNameBytes(values, eggIndex) {
    const gm = getGameManagerPtr();
    if (gm === null) {
        return false;
    }
    const edit = getNameEditObjectPtr();
    if (edit === null) {
        return false;
    }
    if (typeof eggIndex === "number" && eggIndex >= 0) {
        setSelectedEggIndex(eggIndex);
    }
    const hwnd = getNameEditHwnd();
    writeAnsiBytesToEdit(edit, hwnd, values);
    try {
        focusNameEditNative(edit);
    } catch (_err) {
    }
    commitNameNative(gm);
    notify("name-submit", {
        gm: gm.toString(),
        edit: edit.toString(),
        hwnd: hwnd ? hwnd.toString() : null,
        eggIndex: (typeof eggIndex === "number") ? (eggIndex | 0) : null,
    });
    return true;
}

function maybeSample(name, payload) {
    fakeState.observeCounts[name] += 1;
    if (!fakeState.observe) {
        return;
    }
    const count = fakeState.observeCounts[name];
    if (count <= 10 || (count % 50) === 0) {
        notify("observe", Object.assign({ api: name, count: count }, payload || {}));
    }
}

function tryReadCString(ptrValue) {
    try {
        if (ptrValue === null || ptrValue.isNull()) {
            return null;
        }
        return Memory.readCString(ptrValue);
    } catch (_err) {
        return null;
    }
}

function tryReadUtf16(ptrValue) {
    try {
        if (ptrValue === null || ptrValue.isNull()) {
            return null;
        }
        return Memory.readUtf16String(ptrValue);
    } catch (_err) {
        return null;
    }
}

function getExport(moduleName, exportName) {
    const mod = Process.findModuleByName(moduleName);
    if (mod !== null) {
        return mod.getExportByName(exportName);
    }
    return Module.getGlobalExportByName(exportName);
}

function tryGetWindowClass(hwnd) {
    try {
        if (!hwnd || ptr(hwnd).isNull()) {
            return null;
        }
        const buf = Memory.alloc(256);
        Memory.writeByteArray(buf, new Array(256).fill(0));
        const len = GetClassNameWOrig(ptr(hwnd), buf, 128);
        if (!len) {
            return null;
        }
        return tryReadUtf16(buf);
    } catch (_err) {
        return null;
    }
}

function shouldTraceUiHwnd(hwnd) {
    const cls = tryGetWindowClass(hwnd);
    if (!cls) {
        return false;
    }
    return cls === "Edit" || cls === "Static" || cls === "Button";
}

function tryGetExport(moduleName, exportName) {
    try {
        return getExport(moduleName, exportName);
    } catch (_err) {
        return null;
    }
}

function hresultSucceeded(retval) {
    return retval.toInt32() >= 0;
}

function ptrKey(ptr) {
    return ptr.toString();
}

function clamp(value, minValue, maxValue) {
    return Math.max(minValue, Math.min(maxValue, value));
}

function easeInOutCubic(t) {
    if (t <= 0) {
        return 0;
    }
    if (t >= 1) {
        return 1;
    }
    if (t < 0.5) {
        return 4 * t * t * t;
    }
    return 1 - Math.pow(-2 * t + 2, 3) / 2;
}

function buildAxisSteps(total, steps) {
    const values = [];
    let previous = 0;
    for (let i = 1; i <= steps; i++) {
        const eased = easeInOutCubic(i / steps);
        const current = Math.round(total * eased);
        values.push(current - previous);
        previous = current;
    }
    return values;
}

function buildMotionQueue(totalDx, totalDy, steps) {
    const dxSteps = buildAxisSteps(totalDx, steps);
    const dySteps = buildAxisSteps(totalDy, steps);
    const queue = [];
    for (let i = 0; i < steps; i++) {
        queue.push({
            dx: dxSteps[i],
            dy: dySteps[i],
        });
    }
    return queue;
}

function buildCursorQueue(startX, startY, targetX, targetY, steps) {
    const queue = [];
    for (let i = 1; i <= steps; i++) {
        const eased = easeInOutCubic(i / steps);
        queue.push({
            x: Math.round(startX + (targetX - startX) * eased),
            y: Math.round(startY + (targetY - startY) * eased),
        });
    }
    return queue;
}

function chooseMotionSteps(totalDx, totalDy, hoverMs) {
    const distance = Math.max(Math.abs(totalDx), Math.abs(totalDy));
    const distanceSteps = Math.ceil(distance / 18);
    const timeSteps = Math.ceil(hoverMs / 8);
    return clamp(Math.max(distanceSteps, timeSteps, 10), 10, 48);
}

function choosePollCount(ms, minimum, maximum) {
    const minValue = (typeof minimum === "number") ? minimum : 1;
    const maxValue = (typeof maximum === "number") ? maximum : 60;
    return clamp(Math.ceil(ms / 16), minValue, maxValue);
}

function makeMouseLParam(clientX, clientY) {
    return ((clientY & 0xffff) << 16) | (clientX & 0xffff);
}

function makeGenericMessageEntry(hwnd, message, wParam, lParam, screenX, screenY) {
    return {
        hwnd: hwnd,
        message: message,
        wParam: wParam,
        lParam: lParam,
        screenX: screenX,
        screenY: screenY,
        time: 0,
    };
}

function makeMouseMessageEntry(hwnd, message, wParam, clientX, clientY, screenX, screenY) {
    return makeGenericMessageEntry(hwnd, message, wParam, makeMouseLParam(clientX, clientY), screenX, screenY);
}

function buildUiMoveQueue(hwnd, cursorPath, clientPath) {
    const queue = [];
    for (let i = 0; i < cursorPath.length; i++) {
        const screen = cursorPath[i];
        const client = clientPath[i];
        queue.push(makeMouseMessageEntry(hwnd, WM_MOUSEMOVE, 0, client.x, client.y, screen.x, screen.y));
    }
    return queue;
}

function virtualKeyForChar(code) {
    if (code === 0x09) {
        return 0x09;
    }
    if (code === 0x0d) {
        return 0x0d;
    }
    if (code >= 0x30 && code <= 0x39) {
        return code;
    }
    if (code >= 0x41 && code <= 0x5a) {
        return code;
    }
    if (code >= 0x61 && code <= 0x7a) {
        return code - 0x20;
    }
    if (code === 0x20) {
        return 0x20;
    }
    if (code === 0x08) {
        return 0x08;
    }
    return 0;
}

function makeKeyDownLParam() {
    return 0x00000001;
}

function makeKeyUpLParam() {
    return 0xc0000001;
}

function makeCharLParam() {
    return 0x00000001;
}

function buildTextMessageQueue(hwnd, text, screenX, screenY) {
    const queue = [];
    if (!text || !hwnd) {
        return queue;
    }
    for (let i = 0; i < text.length; i++) {
        const code = text.charCodeAt(i) & 0xffff;
        const vk = virtualKeyForChar(code);
        if (vk !== 0) {
            queue.push(makeGenericMessageEntry(hwnd, WM_KEYDOWN, vk, makeKeyDownLParam(), screenX, screenY));
        }
        queue.push(makeGenericMessageEntry(hwnd, WM_CHAR, code, makeCharLParam(), screenX, screenY));
        if (vk !== 0) {
            queue.push(makeGenericMessageEntry(hwnd, WM_KEYUP, vk, makeKeyUpLParam(), screenX, screenY));
        }
    }
    return queue;
}

function writeMsg(lpMsg, entry) {
    lpMsg.writePointer(ptr(entry.hwnd));
    lpMsg.add(4).writeU32(entry.message >>> 0);
    lpMsg.add(8).writeU32(entry.wParam >>> 0);
    lpMsg.add(12).writeU32(entry.lParam >>> 0);
    lpMsg.add(16).writeU32(entry.time >>> 0);
    lpMsg.add(20).writeS32(entry.screenX | 0);
    lpMsg.add(24).writeS32(entry.screenY | 0);
}

function hookMethodOnce(target, key, callbacks) {
    if (target === null || target.isNull()) {
        return false;
    }
    const finalKey = key + "@" + ptrKey(target);
    if (hookedVtables[finalKey]) {
        return false;
    }
    hookedVtables[finalKey] = true;
    Interceptor.attach(target, callbacks);
    return true;
}

function patchMouseStateBuffer(buffer, cbData) {
    if (buffer === null || buffer.isNull()) {
        return;
    }
    if (cbData !== 16 && cbData !== 20) {
        return;
    }

    let originalDx = buffer.readS32();
    let originalDy = buffer.add(4).readS32();
    const originalDz = buffer.add(8).readS32();
    const buttonCount = cbData - 12;
    const originalButtons = [];
    for (let i = 0; i < buttonCount; i++) {
        originalButtons.push(buffer.add(12 + i).readU8());
    }

    let syntheticDx = 0;
    let syntheticDy = 0;
    if (fakeState.motionQueue.length > 0) {
        const motion = fakeState.motionQueue.shift();
        syntheticDx = motion.dx;
        syntheticDy = motion.dy;
        fakeState.dx = syntheticDx;
        fakeState.dy = syntheticDy;
        fakeState.movePending = fakeState.motionQueue.length > 0;
        if (fakeState.cursorQueue.length > 0) {
            const cursor = fakeState.cursorQueue.shift();
            fakeState.x = cursor.x;
            fakeState.y = cursor.y;
        } else {
            fakeState.x = fakeState.targetX;
            fakeState.y = fakeState.targetY;
        }
    } else {
        fakeState.dx = 0;
        fakeState.dy = 0;
        fakeState.movePending = false;
    }

    if (fakeState.hoverPollsRemaining > 0) {
        fakeState.hoverPollsRemaining -= 1;
    } else if (fakeState.downPollsRemaining > 0) {
        if (!fakeState.leftDown) {
            fakeState.leftDown = true;
            fakeState.asyncEdgePending = true;
            notify("click-press", { x: fakeState.targetX, y: fakeState.targetY });
        }
        fakeState.downPollsRemaining -= 1;
    } else if (fakeState.settlePollsRemaining > 0) {
        fakeState.settlePollsRemaining -= 1;
    }

    buffer.writeS32(originalDx + syntheticDx);
    buffer.add(4).writeS32(originalDy + syntheticDy);
    buffer.add(8).writeS32(originalDz);

    for (let i = 0; i < buttonCount; i++) {
        let value = originalButtons[i];
        if (i === 0) {
            value = fakeState.leftDown ? (value | 0x80) : (value & 0x7f);
        }
        buffer.add(12 + i).writeU8(value);
    }

    if (fakeState.leftDown && fakeState.downPollsRemaining === 0) {
        fakeState.leftDown = false;
        notify("click-release", { x: fakeState.targetX, y: fakeState.targetY });
    }

    if (
        fakeState.active &&
        fakeState.motionQueue.length === 0 &&
        fakeState.hoverPollsRemaining === 0 &&
        fakeState.downPollsRemaining === 0 &&
        fakeState.settlePollsRemaining === 0
    ) {
        completeActiveClick();
    }
}

function readMouseStateBuffer(buffer, cbData) {
    if (buffer === null || buffer.isNull()) {
        return null;
    }
    if (cbData !== 16 && cbData !== 20) {
        return null;
    }
    const buttonCount = cbData - 12;
    const buttons = [];
    for (let i = 0; i < buttonCount; i++) {
        buttons.push(buffer.add(12 + i).readU8());
    }
    return {
        dx: buffer.readS32(),
        dy: buffer.add(4).readS32(),
        dz: buffer.add(8).readS32(),
        buttons: buttons,
    };
}

function hookDirectInputDevice(devicePtr) {
    if (devicePtr === null || devicePtr.isNull()) {
        return false;
    }
    const deviceKey = ptrKey(devicePtr);
    if (hookedDevices[deviceKey]) {
        return false;
    }
    hookedDevices[deviceKey] = true;

    const vtable = devicePtr.readPointer();
    const pAcquire = vtable.add(DID8_ACQUIRE_INDEX * Process.pointerSize).readPointer();
    const pGetDeviceState = vtable.add(DID8_GET_DEVICE_STATE_INDEX * Process.pointerSize).readPointer();
    const pGetDeviceData = vtable.add(DID8_GET_DEVICE_DATA_INDEX * Process.pointerSize).readPointer();
    const pSetDataFormat = vtable.add(DID8_SET_DATA_FORMAT_INDEX * Process.pointerSize).readPointer();
    const pSetCooperativeLevel = vtable.add(DID8_SET_COOPERATIVE_LEVEL_INDEX * Process.pointerSize).readPointer();

    hookMethodOnce(pSetDataFormat, "SetDataFormat", {
        onEnter(args) {
            maybeSample("setDataFormat", {
                device: deviceKey,
                dataFormat: args[1].toString(),
            });
        },
    });

    hookMethodOnce(pSetCooperativeLevel, "SetCooperativeLevel", {
        onEnter(args) {
            maybeSample("setCooperativeLevel", {
                device: deviceKey,
                hwnd: args[1].toString(),
                flags: args[2].toUInt32(),
            });
        },
    });

    hookMethodOnce(pAcquire, "Acquire", {
        onEnter(_args) {
            maybeSample("acquire", { device: deviceKey });
        },
    });

    hookMethodOnce(pGetDeviceState, "GetDeviceState", {
        onEnter(args) {
            this.cbData = args[1].toUInt32();
            this.stateBuffer = args[2];
            fakeState.lastDeviceStateTick = getTickCountNow();
            maybeSample("getDeviceState", {
                device: deviceKey,
                cbData: this.cbData,
            });
        },
        onLeave(retval) {
            if (!hresultSucceeded(retval)) {
                return;
            }
            if (fakeState.active) {
                patchMouseStateBuffer(this.stateBuffer, this.cbData);
            }
            if (fakeState.observe) {
                const state = readMouseStateBuffer(this.stateBuffer, this.cbData);
                if (state !== null) {
                    const anyButtons = state.buttons.some(value => value !== 0);
                    if (state.dx !== 0 || state.dy !== 0 || state.dz !== 0 || anyButtons) {
                        notify("mouse-state", {
                            device: deviceKey,
                            cbData: this.cbData,
                            dx: state.dx,
                            dy: state.dy,
                            dz: state.dz,
                            buttons: state.buttons,
                        });
                    }
                }
            }
        },
    });

    hookMethodOnce(pGetDeviceData, "GetDeviceData", {
        onEnter(args) {
            const inout = args[3];
            let requested = 0;
            try {
                requested = inout.readU32();
            } catch (_err) {
                requested = 0;
            }
            maybeSample("getDeviceData", {
                device: deviceKey,
                cbObjectData: args[1].toUInt32(),
                requested: requested,
                flags: args[4].toUInt32(),
            });
        },
    });

    notify("dinput-device-hooked", { device: deviceKey });
    return true;
}

function hookDirectInputInterface(interfacePtr) {
    if (interfacePtr === null || interfacePtr.isNull()) {
        return false;
    }
    const vtable = interfacePtr.readPointer();
    const pCreateDevice = vtable.add(DI8_CREATE_DEVICE_INDEX * Process.pointerSize).readPointer();
    return hookMethodOnce(pCreateDevice, "CreateDevice", {
        onEnter(args) {
            this.outDevicePtr = args[2];
            maybeSample("createDevice", {
                iface: ptrKey(interfacePtr),
                guid: args[1].toString(),
            });
        },
        onLeave(retval) {
            if (!hresultSucceeded(retval)) {
                return;
            }
            try {
                const devicePtr = this.outDevicePtr.readPointer();
                hookDirectInputDevice(devicePtr);
            } catch (err) {
                notify("info", {
                    message: "CreateDevice succeeded but device hook failed",
                    error: String(err),
                });
            }
        },
    });
}

const pGetCursorPos = getExport("user32.dll", "GetCursorPos");
const pGetAsyncKeyState = getExport("user32.dll", "GetAsyncKeyState");
const pGetKeyState = getExport("user32.dll", "GetKeyState");
const pGetMessagePos = getExport("user32.dll", "GetMessagePos");
const pGetMessageTime = getExport("user32.dll", "GetMessageTime");
const pGetCapture = getExport("user32.dll", "GetCapture");
const pSetCapture = getExport("user32.dll", "SetCapture");
const pReleaseCapture = getExport("user32.dll", "ReleaseCapture");
const pSetCursorPos = getExport("user32.dll", "SetCursorPos");
const pClipCursor = getExport("user32.dll", "ClipCursor");
const pShowWindow = getExport("user32.dll", "ShowWindow");
const pEnableWindow = getExport("user32.dll", "EnableWindow");
const pSetFocus = getExport("user32.dll", "SetFocus");
const pSetWindowPos = getExport("user32.dll", "SetWindowPos");
const pGetClassNameW = getExport("user32.dll", "GetClassNameW");
const pPeekMessageA = getExport("user32.dll", "PeekMessageA");
const pGetMessageA = getExport("user32.dll", "GetMessageA");
const pPeekMessageW = getExport("user32.dll", "PeekMessageW");
const pGetMessageW = getExport("user32.dll", "GetMessageW");
const pPostMessageW = getExport("user32.dll", "PostMessageW");
const pGetTickCount = getExport("kernel32.dll", "GetTickCount");

const GetCursorPosOrig = new NativeFunction(pGetCursorPos, "bool", ["pointer"], "stdcall");
const GetAsyncKeyStateOrig = new NativeFunction(pGetAsyncKeyState, "int16", ["int"], "stdcall");
const GetKeyStateOrig = new NativeFunction(pGetKeyState, "int16", ["int"], "stdcall");
const GetMessagePosOrig = new NativeFunction(pGetMessagePos, "uint", [], "stdcall");
const GetMessageTimeOrig = new NativeFunction(pGetMessageTime, "int", [], "stdcall");
const GetCaptureOrig = new NativeFunction(pGetCapture, "pointer", [], "stdcall");
const SetCaptureOrig = new NativeFunction(pSetCapture, "pointer", ["pointer"], "stdcall");
const ReleaseCaptureOrig = new NativeFunction(pReleaseCapture, "bool", [], "stdcall");
const SetCursorPosOrig = new NativeFunction(pSetCursorPos, "bool", ["int", "int"], "stdcall");
const ClipCursorOrig = new NativeFunction(pClipCursor, "bool", ["pointer"], "stdcall");
const ShowWindowOrig = new NativeFunction(pShowWindow, "bool", ["pointer", "int"], "stdcall");
const EnableWindowOrig = new NativeFunction(pEnableWindow, "bool", ["pointer", "bool"], "stdcall");
const SetFocusOrig = new NativeFunction(pSetFocus, "pointer", ["pointer"], "stdcall");
const SetWindowPosOrig = new NativeFunction(pSetWindowPos, "bool", ["pointer", "pointer", "int", "int", "int", "int", "uint"], "stdcall");
const GetClassNameWOrig = new NativeFunction(pGetClassNameW, "int", ["pointer", "pointer", "int"], "stdcall");
const PeekMessageAOrig = new NativeFunction(pPeekMessageA, "bool", ["pointer", "pointer", "uint", "uint", "uint"], "stdcall");
const GetMessageAOrig = new NativeFunction(pGetMessageA, "bool", ["pointer", "pointer", "uint", "uint"], "stdcall");
const PeekMessageWOrig = new NativeFunction(pPeekMessageW, "bool", ["pointer", "pointer", "uint", "uint", "uint"], "stdcall");
const GetMessageWOrig = new NativeFunction(pGetMessageW, "bool", ["pointer", "pointer", "uint", "uint"], "stdcall");
const PostMessageWOrig = new NativeFunction(pPostMessageW, "bool", ["pointer", "uint", "uint", "uint"], "stdcall");
const GetTickCountOrig = new NativeFunction(pGetTickCount, "uint", [], "stdcall");

function getTickCountNow() {
    return GetTickCountOrig() >>> 0;
}

function syntheticMessageIsFresh() {
    if ((fakeState.lastMessageTime >>> 0) === 0) {
        return false;
    }
    return (((getTickCountNow() - (fakeState.lastMessageTime >>> 0)) >>> 0) <= 2000);
}

function hasFreshDevicePoll() {
    if ((fakeState.lastDeviceStateTick >>> 0) === 0) {
        return false;
    }
    return (((getTickCountNow() - (fakeState.lastDeviceStateTick >>> 0)) >>> 0) <= 100);
}

function completeActiveClick() {
    fakeState.active = false;
    fakeState.x = fakeState.targetX;
    fakeState.y = fakeState.targetY;
    fakeState.dx = 0;
    fakeState.dy = 0;
    fakeState.movePending = false;
    fakeState.leftDown = false;
    fakeState.hoverPollsRemaining = 0;
    fakeState.downPollsRemaining = 0;
    fakeState.settlePollsRemaining = 0;
    fakeState.motionQueue = [];
    fakeState.cursorQueue = [];
    fakeState.messageQueue = [];
    fakeState.captureHwnd = 0;
    fakeState.armedAt = 0;
    fakeState.hoverEndAt = 0;
    fakeState.releaseAt = 0;
    fakeState.deactivateAt = 0;
    fakeState.lastDeviceStateTick = 0;
    notify("click-complete", { x: fakeState.targetX, y: fakeState.targetY });
}

function syncUiOnlyState() {
    if (!fakeState.active || hasFreshDevicePoll()) {
        return;
    }
    const now = getTickCountNow();
    if ((fakeState.hoverEndAt >>> 0) > (fakeState.armedAt >>> 0) && now < (fakeState.hoverEndAt >>> 0)) {
        const progress = clamp(
            (now - (fakeState.armedAt >>> 0)) / ((fakeState.hoverEndAt >>> 0) - (fakeState.armedAt >>> 0)),
            0,
            1
        );
        const eased = easeInOutCubic(progress);
        fakeState.x = Math.round(fakeState.x + (fakeState.targetX - fakeState.x) * eased);
        fakeState.y = Math.round(fakeState.y + (fakeState.targetY - fakeState.y) * eased);
    } else {
        fakeState.x = fakeState.targetX;
        fakeState.y = fakeState.targetY;
    }
    if ((fakeState.hoverEndAt >>> 0) !== 0 && now >= (fakeState.hoverEndAt >>> 0) && now < (fakeState.releaseAt >>> 0)) {
        if (!fakeState.leftDown) {
            fakeState.leftDown = true;
            fakeState.asyncEdgePending = true;
            notify("click-press", { x: fakeState.targetX, y: fakeState.targetY, source: "ui-only" });
        }
    } else if ((fakeState.releaseAt >>> 0) !== 0 && now >= (fakeState.releaseAt >>> 0)) {
        if (fakeState.leftDown) {
            fakeState.leftDown = false;
            notify("click-release", { x: fakeState.targetX, y: fakeState.targetY, source: "ui-only" });
        }
    }
    if ((fakeState.deactivateAt >>> 0) !== 0 && now >= (fakeState.deactivateAt >>> 0) && fakeState.messageQueue.length === 0) {
        completeActiveClick();
    }
}

function postSyntheticMouseMessage(hwnd, message, wParam, clientX, clientY) {
    if (!hwnd) {
        return false;
    }
    const ok = !!PostMessageWOrig(ptr(hwnd), message >>> 0, wParam >>> 0, makeMouseLParam(clientX, clientY) >>> 0);
    if (fakeState.observe) {
        notify("pm-post", {
            hwnd: hwnd,
            message: message,
            wParam: wParam,
            clientX: clientX,
            clientY: clientY,
            ok: ok,
        });
    }
    return ok;
}

function tryInjectQueuedMessage(lpMsg, hWnd, wMsgFilterMin, wMsgFilterMax, consume, sourceName) {
    if (fakeState.messageQueue.length <= 0 || !lpMsg || lpMsg.isNull()) {
        return false;
    }
    const entry = fakeState.messageQueue[0];
    const message = entry.message >>> 0;
    const filterMin = wMsgFilterMin >>> 0;
    const filterMax = wMsgFilterMax >>> 0;
    const filterActive = !(filterMin === 0 && filterMax === 0);
    const filterMatches = !filterActive || (message >= filterMin && message <= filterMax);
    const hwndMatches = hWnd.isNull() || hWnd.toUInt32() === (entry.hwnd >>> 0);
    if (!filterMatches || !hwndMatches) {
        return false;
    }
    if (consume) {
        fakeState.messageQueue.shift();
    }
    if (!entry.time) {
        entry.time = getTickCountNow();
    }
    fakeState.lastMessagePos = makeMouseLParam(entry.screenX, entry.screenY) >>> 0;
    fakeState.lastMessageTime = entry.time >>> 0;
    fakeState.lastMessageHwnd = entry.hwnd >>> 0;
    if (entry.message === WM_LBUTTONDOWN) {
        fakeState.captureHwnd = entry.hwnd >>> 0;
    } else if (entry.message === WM_LBUTTONUP) {
        fakeState.captureHwnd = 0;
    }
    writeMsg(lpMsg, entry);
    if (fakeState.observe) {
        notify("message-inject", {
            source: sourceName,
            consume: !!consume,
            hwnd: entry.hwnd,
            message: entry.message,
            wParam: entry.wParam,
            lParam: entry.lParam,
            screenX: entry.screenX,
            screenY: entry.screenY,
            remaining: fakeState.messageQueue.length,
        });
    }
    return true;
}

Interceptor.replace(
    pGetCursorPos,
    new NativeCallback(function (lpPoint) {
        maybeSample("getCursorPos");
        if (fakeState.active) {
            syncUiOnlyState();
            lpPoint.writeS32(fakeState.x);
            lpPoint.add(4).writeS32(fakeState.y);
            return 1;
        }
        return GetCursorPosOrig(lpPoint);
    }, "bool", ["pointer"], "stdcall")
);

Interceptor.replace(
    pGetAsyncKeyState,
    new NativeCallback(function (vKey) {
        maybeSample("getAsyncKeyState", { vKey: vKey });
        if (fakeState.active && vKey === 0x01) {
            if (fakeState.leftDown) {
                if (fakeState.asyncEdgePending) {
                    fakeState.asyncEdgePending = false;
                    return 0x8001;
                }
                return 0x8000;
            }
            return 0;
        }
        return GetAsyncKeyStateOrig(vKey);
    }, "int16", ["int"], "stdcall")
);

Interceptor.replace(
    pGetKeyState,
    new NativeCallback(function (vKey) {
        maybeSample("getKeyState", { vKey: vKey });
        if (fakeState.active && vKey === 0x01) {
            return fakeState.leftDown ? 0x8000 : 0;
        }
        return GetKeyStateOrig(vKey);
    }, "int16", ["int"], "stdcall")
);

Interceptor.replace(
    AZROK_ABSTRACT_INPUT_INT_PTR,
    new NativeCallback(function (namePtr) {
        const name = tryReadCString(namePtr);
        if (name === "mouse_left") {
            syncUiOnlyState();
            maybeSample("abstractMouseLeft", {
                active: fakeState.active,
                leftDown: fakeState.leftDown,
            });
            if (fakeState.active) {
                return fakeState.leftDown ? 1 : 0;
            }
        }
        return abstractInputIntNative(namePtr);
    }, "int", ["pointer"], "stdcall")
);

Interceptor.replace(
    AZROK_ABSTRACT_INPUT_VEC3_PTR,
    new NativeCallback(function (outPtr, namePtr) {
        const name = tryReadCString(namePtr);
        if (name === "POINTER") {
            syncUiOnlyState();
            maybeSample("abstractPointer", {
                active: fakeState.active,
                clientX: fakeState.clientX,
                clientY: fakeState.clientY,
            });
            if (fakeState.active && outPtr !== null && !outPtr.isNull()) {
                outPtr.writeS32(fakeState.clientX | 0);
                outPtr.add(4).writeS32(fakeState.clientY | 0);
                outPtr.add(8).writeS32(0);
                return outPtr;
            }
        }
        return abstractInputVec3Native(outPtr, namePtr);
    }, "pointer", ["pointer", "pointer"], "stdcall")
);

Interceptor.replace(
    pGetMessagePos,
    new NativeCallback(function () {
        maybeSample("getMessagePos");
        syncUiOnlyState();
        if (syntheticMessageIsFresh()) {
            return fakeState.lastMessagePos >>> 0;
        }
        return GetMessagePosOrig() >>> 0;
    }, "uint", [], "stdcall")
);

Interceptor.replace(
    pGetMessageTime,
    new NativeCallback(function () {
        maybeSample("getMessageTime");
        syncUiOnlyState();
        if (syntheticMessageIsFresh()) {
            return fakeState.lastMessageTime | 0;
        }
        return GetMessageTimeOrig() | 0;
    }, "int", [], "stdcall")
);

Interceptor.replace(
    pGetCapture,
    new NativeCallback(function () {
        maybeSample("getCapture");
        if (fakeState.captureHwnd) {
            return ptr(fakeState.captureHwnd);
        }
        return GetCaptureOrig();
    }, "pointer", [], "stdcall")
);

Interceptor.replace(
    pSetCapture,
    new NativeCallback(function (hwnd) {
        maybeSample("setCapture", { hwnd: hwnd.isNull() ? 0 : hwnd.toUInt32() });
        if (!hwnd.isNull()) {
            fakeState.captureHwnd = hwnd.toUInt32();
        }
        return SetCaptureOrig(hwnd);
    }, "pointer", ["pointer"], "stdcall")
);

Interceptor.replace(
    pReleaseCapture,
    new NativeCallback(function () {
        maybeSample("releaseCapture");
        fakeState.captureHwnd = 0;
        return ReleaseCaptureOrig();
    }, "bool", [], "stdcall")
);

Interceptor.replace(
    pSetCursorPos,
    new NativeCallback(function (x, y) {
        maybeSample("setCursorPos", { x: x, y: y });
        if (fakeState.active) {
            return 1;
        }
        return SetCursorPosOrig(x, y);
    }, "bool", ["int", "int"], "stdcall")
);

Interceptor.replace(
    pClipCursor,
    new NativeCallback(function (lpRect) {
        maybeSample("clipCursor");
        if (fakeState.active) {
            return 1;
        }
        return ClipCursorOrig(lpRect);
    }, "bool", ["pointer"], "stdcall")
);

Interceptor.replace(
    pShowWindow,
    new NativeCallback(function (hWnd, nCmdShow) {
        maybeSample("showWindow", { hwnd: hWnd.isNull() ? 0 : hWnd.toUInt32(), cmdShow: nCmdShow | 0 });
        if (fakeState.observe && shouldTraceUiHwnd(hWnd)) {
            notify("ui-call", {
                api: "ShowWindow",
                hwnd: hWnd.toUInt32(),
                className: tryGetWindowClass(hWnd),
                cmdShow: nCmdShow | 0,
            });
        }
        return ShowWindowOrig(hWnd, nCmdShow);
    }, "bool", ["pointer", "int"], "stdcall")
);

Interceptor.replace(
    pEnableWindow,
    new NativeCallback(function (hWnd, enabled) {
        maybeSample("enableWindow", { hwnd: hWnd.isNull() ? 0 : hWnd.toUInt32(), enabled: !!enabled });
        if (fakeState.observe && shouldTraceUiHwnd(hWnd)) {
            notify("ui-call", {
                api: "EnableWindow",
                hwnd: hWnd.toUInt32(),
                className: tryGetWindowClass(hWnd),
                enabled: !!enabled,
            });
        }
        return EnableWindowOrig(hWnd, enabled);
    }, "bool", ["pointer", "bool"], "stdcall")
);

Interceptor.replace(
    pSetFocus,
    new NativeCallback(function (hWnd) {
        maybeSample("setFocus", { hwnd: hWnd.isNull() ? 0 : hWnd.toUInt32() });
        if (fakeState.observe && shouldTraceUiHwnd(hWnd)) {
            notify("ui-call", {
                api: "SetFocus",
                hwnd: hWnd.toUInt32(),
                className: tryGetWindowClass(hWnd),
            });
        }
        return SetFocusOrig(hWnd);
    }, "pointer", ["pointer"], "stdcall")
);

Interceptor.replace(
    pSetWindowPos,
    new NativeCallback(function (hWnd, hWndInsertAfter, X, Y, cx, cy, uFlags) {
        maybeSample("setWindowPos", {
            hwnd: hWnd.isNull() ? 0 : hWnd.toUInt32(),
            x: X | 0,
            y: Y | 0,
            cx: cx | 0,
            cy: cy | 0,
            flags: uFlags >>> 0,
        });
        if (fakeState.observe && shouldTraceUiHwnd(hWnd)) {
            notify("ui-call", {
                api: "SetWindowPos",
                hwnd: hWnd.toUInt32(),
                className: tryGetWindowClass(hWnd),
                x: X | 0,
                y: Y | 0,
                cx: cx | 0,
                cy: cy | 0,
                flags: uFlags >>> 0,
            });
        }
        return SetWindowPosOrig(hWnd, hWndInsertAfter, X, Y, cx, cy, uFlags);
    }, "bool", ["pointer", "pointer", "int", "int", "int", "int", "uint"], "stdcall")
);

Interceptor.replace(
    pPeekMessageA,
    new NativeCallback(function (lpMsg, hWnd, wMsgFilterMin, wMsgFilterMax, wRemoveMsg) {
        maybeSample("peekMessage", {
            hwnd: hWnd.isNull() ? 0 : hWnd.toUInt32(),
            filterMin: wMsgFilterMin >>> 0,
            filterMax: wMsgFilterMax >>> 0,
            remove: wRemoveMsg >>> 0,
        });
        if (tryInjectQueuedMessage(lpMsg, hWnd, wMsgFilterMin, wMsgFilterMax, (wRemoveMsg & 0x0001) !== 0, "PeekMessageA")) {
            return 1;
        }
        return PeekMessageAOrig(lpMsg, hWnd, wMsgFilterMin, wMsgFilterMax, wRemoveMsg);
    }, "bool", ["pointer", "pointer", "uint", "uint", "uint"], "stdcall")
);

Interceptor.replace(
    pGetMessageA,
    new NativeCallback(function (lpMsg, hWnd, wMsgFilterMin, wMsgFilterMax) {
        if (tryInjectQueuedMessage(lpMsg, hWnd, wMsgFilterMin, wMsgFilterMax, true, "GetMessageA")) {
            return 1;
        }
        return GetMessageAOrig(lpMsg, hWnd, wMsgFilterMin, wMsgFilterMax);
    }, "bool", ["pointer", "pointer", "uint", "uint"], "stdcall")
);

Interceptor.replace(
    pPeekMessageW,
    new NativeCallback(function (lpMsg, hWnd, wMsgFilterMin, wMsgFilterMax, wRemoveMsg) {
        maybeSample("peekMessage", {
            hwnd: hWnd.isNull() ? 0 : hWnd.toUInt32(),
            filterMin: wMsgFilterMin >>> 0,
            filterMax: wMsgFilterMax >>> 0,
            remove: wRemoveMsg >>> 0,
            wide: true,
        });
        if (tryInjectQueuedMessage(lpMsg, hWnd, wMsgFilterMin, wMsgFilterMax, (wRemoveMsg & 0x0001) !== 0, "PeekMessageW")) {
            return 1;
        }
        return PeekMessageWOrig(lpMsg, hWnd, wMsgFilterMin, wMsgFilterMax, wRemoveMsg);
    }, "bool", ["pointer", "pointer", "uint", "uint", "uint"], "stdcall")
);

Interceptor.replace(
    pGetMessageW,
    new NativeCallback(function (lpMsg, hWnd, wMsgFilterMin, wMsgFilterMax) {
        if (tryInjectQueuedMessage(lpMsg, hWnd, wMsgFilterMin, wMsgFilterMax, true, "GetMessageW")) {
            return 1;
        }
        return GetMessageWOrig(lpMsg, hWnd, wMsgFilterMin, wMsgFilterMax);
    }, "bool", ["pointer", "pointer", "uint", "uint"], "stdcall")
);

try {
    const pDirectInput8Create = tryGetExport("dinput8.dll", "DirectInput8Create");
    if (pDirectInput8Create === null) {
        throw new Error("DirectInput8Create export not available yet");
    }
    Interceptor.attach(pDirectInput8Create, {
        onEnter(args) {
            this.outInterfacePtr = args[3];
            maybeSample("directInput8Create", {
                hinst: args[0].toString(),
                version: args[1].toUInt32(),
            });
        },
        onLeave(retval) {
            if (!hresultSucceeded(retval)) {
                return;
            }
            try {
                const ifacePtr = this.outInterfacePtr.readPointer();
                hookDirectInputInterface(ifacePtr);
            } catch (err) {
                notify("info", {
                    message: "DirectInput8Create succeeded but interface hook failed",
                    error: String(err),
                });
            }
        },
    });
} catch (err) {
    notify("info", { message: "DirectInput8Create export not available yet", error: String(err) });
}

function activateClick(x, y, hoverMs, holdMs, settleMs, dx, dy, startX, startY, hwnd, clientX, clientY, startClientX, startClientY) {
    const motionSteps = chooseMotionSteps(dx, dy, hoverMs);
    const hoverPolls = Math.max(choosePollCount(hoverMs, 2, 60), motionSteps);
    const downPolls = choosePollCount(holdMs, 2, 30);
    const settlePolls = choosePollCount(settleMs, 1, 30);
    const cursorPath = buildCursorQueue(startX, startY, x, y, motionSteps);
    const clientPath = buildCursorQueue(startClientX, startClientY, clientX, clientY, motionSteps);
    fakeState.active = true;
    fakeState.hwnd = hwnd | 0;
    fakeState.x = startX;
    fakeState.y = startY;
    fakeState.targetX = x;
    fakeState.targetY = y;
    fakeState.clientX = clientX | 0;
    fakeState.clientY = clientY | 0;
    fakeState.startClientX = startClientX | 0;
    fakeState.startClientY = startClientY | 0;
    fakeState.dx = dx | 0;
    fakeState.dy = dy | 0;
    fakeState.motionQueue = buildMotionQueue(fakeState.dx, fakeState.dy, motionSteps);
    fakeState.cursorQueue = cursorPath.slice();
    fakeState.messageQueue = buildUiMoveQueue(fakeState.hwnd, cursorPath, clientPath);
    fakeState.captureHwnd = 0;
    fakeState.lastMessagePos = 0;
    fakeState.lastMessageTime = 0;
    fakeState.lastMessageHwnd = 0;
    fakeState.armedAt = getTickCountNow();
    fakeState.hoverEndAt = (fakeState.armedAt + (hoverMs >>> 0)) >>> 0;
    fakeState.releaseAt = (fakeState.hoverEndAt + (holdMs >>> 0)) >>> 0;
    fakeState.deactivateAt = (fakeState.releaseAt + (settleMs >>> 0) + 120) >>> 0;
    fakeState.lastDeviceStateTick = 0;
    fakeState.movePending = fakeState.motionQueue.length > 0;
    fakeState.leftDown = false;
    fakeState.hoverPollsRemaining = hoverPolls;
    fakeState.downPollsRemaining = downPolls;
    fakeState.settlePollsRemaining = settlePolls;
    fakeState.asyncEdgePending = false;
    notify("click-armed", {
        hwnd: fakeState.hwnd,
        x: x,
        y: y,
        startX: startX,
        startY: startY,
        clientX: fakeState.clientX,
        clientY: fakeState.clientY,
        dx: fakeState.dx,
        dy: fakeState.dy,
        motionSteps: motionSteps,
        hoverMs: hoverMs,
        holdMs: holdMs,
        settleMs: settleMs,
        hoverPolls: hoverPolls,
        downPolls: downPolls,
        settlePolls: settlePolls,
    });
    if (fakeState.hwnd && clientPath.length > 0) {
        setTimeout(function () {
            if (!fakeState.active) {
                return;
            }
            fakeState.messageQueue.push(
                makeMouseMessageEntry(fakeState.hwnd, WM_LBUTTONDOWN, MK_LBUTTON, fakeState.clientX, fakeState.clientY, x, y)
            );
            fakeState.messageQueue.push(
                makeMouseMessageEntry(fakeState.hwnd, WM_MOUSEMOVE, MK_LBUTTON, fakeState.clientX, fakeState.clientY, x, y)
            );
        }, hoverMs);
        setTimeout(function () {
            if (!fakeState.active) {
                return;
            }
            fakeState.messageQueue.push(
                makeMouseMessageEntry(fakeState.hwnd, WM_LBUTTONUP, 0, fakeState.clientX, fakeState.clientY, x, y)
            );
        }, hoverMs + holdMs);
    }
}

rpc.exports = {
    cancelinput: function () {
        completeActiveClick();
        return true;
    },
    queuegym: function (gameManagerAddress) {
        // 0x006E8430 is the Acknex engine root, not this GameManager.  The
        // caller supplies the already observed per-process GameManager so we
        // do not confuse those two live objects.
        const gm = ptr(gameManagerAddress >>> 0);
        if (gm.isNull()) {
            throw new Error("game manager is null");
        }
        const phase = gm.add(AZROK_PLAZA_PHASE_OFFSET).readS32();
        if (phase !== 4) {
            throw new Error("Gym portal can only be queued from healthy Plaza phase 4; phase=" + phase);
        }
        const plazaOwner = gm.add(AZROK_PLAZA_OWNER_OFFSET);
        const portal = plazaOwner.add(AZROK_PLAZA_PORTAL_OFFSET);
        const vtable = portal.readPointer();
        if (vtable.isNull()) {
            throw new Error("Plaza portal subsystem is not initialized");
        }
        const pendingBefore = portal.add(AZROK_PLAZA_PENDING_OFFSET).readS32();
        if (pendingBefore !== -1) {
            throw new Error("Plaza portal already has a pending selector: " + pendingBefore);
        }
        queuePlazaPortalNative(portal, AZROK_GYM_SELECTOR);
        const pendingAfter = portal.add(AZROK_PLAZA_PENDING_OFFSET).readS32();
        if (pendingAfter !== AZROK_GYM_SELECTOR) {
            throw new Error("Gym selector was not committed; pending=" + pendingAfter);
        }
        const result = {
            gameManager: gm.toString(),
            phase: phase,
            plazaOwner: plazaOwner.toString(),
            portal: portal.toString(),
            portalVtable: vtable.toString(),
            pendingBefore: pendingBefore,
            pendingAfter: pendingAfter,
            selector: AZROK_GYM_SELECTOR,
        };
        notify("gym-portal-queued", result);
        return result;
    },
    queueplazaroom: function (gameManagerAddress, roomName) {
        const normalizedRoom = String(roomName || "").toLowerCase();
        if (!Object.prototype.hasOwnProperty.call(AZROK_PLAZA_ROOM_SELECTORS, normalizedRoom)) {
            throw new Error("Unsupported Plaza room: " + normalizedRoom);
        }
        const selector = AZROK_PLAZA_ROOM_SELECTORS[normalizedRoom];
        const gm = ptr(gameManagerAddress >>> 0);
        if (gm.isNull()) {
            throw new Error("game manager is null");
        }
        const phase = gm.add(AZROK_PLAZA_PHASE_OFFSET).readS32();
        if (phase !== 4) {
            throw new Error("Plaza room can only be queued from healthy Plaza phase 4; phase=" + phase);
        }
        const plazaOwner = gm.add(AZROK_PLAZA_OWNER_OFFSET);
        const portal = plazaOwner.add(AZROK_PLAZA_PORTAL_OFFSET);
        const vtable = portal.readPointer();
        if (vtable.isNull()) {
            throw new Error("Plaza portal subsystem is not initialized");
        }
        const pendingBefore = portal.add(AZROK_PLAZA_PENDING_OFFSET).readS32();
        if (pendingBefore !== -1) {
            throw new Error("Plaza portal already has a pending selector: " + pendingBefore);
        }
        queuePlazaPortalNative(portal, selector);
        const pendingAfter = portal.add(AZROK_PLAZA_PENDING_OFFSET).readS32();
        if (pendingAfter !== selector) {
            throw new Error("Plaza room selector was not committed; pending=" + pendingAfter);
        }
        const result = {
            gameManager: gm.toString(),
            phase: phase,
            plazaOwner: plazaOwner.toString(),
            portal: portal.toString(),
            portalVtable: vtable.toString(),
            pendingBefore: pendingBefore,
            pendingAfter: pendingAfter,
            selector: selector,
            room: normalizedRoom,
        };
        notify("plaza-room-portal-queued", result);
        return result;
    },
    mapstate: function (gameManagerAddress) {
        const engineRoot = AZROK_GM_PTR_ADDR.readPointer();
        const gameManager = ptr(gameManagerAddress >>> 0);
        if (engineRoot.isNull() || gameManager.isNull()) {
            throw new Error("engine root or game manager is null");
        }
        const owner = gameManager.add(0xe4a);
        const player = owner.add(0x12817).readPointer();
        const view = engineRoot.add(0x918).readPointer();
        const controller = owner.add(0x176b9);
        const entForName = new NativeFunction(
            AZROK_ENT_FOR_NAME_PTR,
            "pointer",
            ["pointer"]
        );
        const findEntity = function (name) {
            const entity = entForName(Memory.allocUtf8String(name));
            if (entity.isNull()) return null;
            return {
                pointer: entity.toString(),
                x: entity.add(0x10).readS32() / 1024.0,
                y: entity.add(0x14).readS32() / 1024.0,
                z: entity.add(0x18).readS32() / 1024.0,
            };
        };
        const readPosition = function (base, offset) {
            if (base.isNull()) return null;
            return {
                x: base.add(offset).readS32() / 1024.0,
                y: base.add(offset + 4).readS32() / 1024.0,
                z: base.add(offset + 8).readS32() / 1024.0,
            };
        };
        return {
            engineRoot: engineRoot.toString(),
            gameManager: gameManager.toString(),
            owner: owner.toString(),
            player: player.isNull() ? null : {
                pointer: player.toString(),
                position: readPosition(player, 0x10),
            },
            camera: {
                controller: controller.toString(),
                radius: controller.add(0x24).readS32() / 1024.0,
                yaw: controller.add(0x28).readS32() / 1024.0,
                pitch: controller.add(0x2c).readS32() / 1024.0,
                view: view.toString(),
                position: readPosition(view, 0x28),
                pan: view.add(0x34).readS32() / 1024.0,
                tilt: view.add(0x38).readS32() / 1024.0,
                roll: view.add(0x3c).readS32() / 1024.0,
            },
            entities: {
                outsideDoor: findEntity("dm_door_0003_057"),
                internalDoor: findEntity("doorframe_01"),
                outsideFootprint: findEntity("foot3_057"),
            },
        };
    },
    rotateandproject: function (worldX, worldY, worldZ, delta, repeats) {
        const ownerText = fakeState.worldInputOwner;
        if (ownerText === "0x0") {
            throw new Error("world input owner is not available yet");
        }
        const owner = ptr(ownerText);
        const cameraDrag = new NativeFunction(
            AZROK_CAMERA_DRAG_PTR,
            "void",
            ["pointer", "float"],
            "thiscall"
        );
        const manager = AZROK_GM_PTR_ADDR.readPointer();
        const view = manager.add(0x918).readPointer();
        const vecToScreen = new NativeFunction(
            AZROK_VEC_TO_SCREEN_PTR,
            "int",
            ["pointer", "pointer"]
        );
        const hitTest = new NativeFunction(
            AZROK_WORLD_HIT_TEST_PTR,
            "int",
            ["pointer", "int", "int"],
            "thiscall"
        );
        const results = [];
        const count = Math.max(1, Math.min(4, repeats | 0));
        for (let i = 0; i < count; i++) {
            cameraDrag(owner.add(0x176b9), Number(delta));
            const vector = Memory.alloc(12);
            vector.writeS32(Math.round(Number(worldX) * 1024));
            vector.add(4).writeS32(Math.round(Number(worldY) * 1024));
            vector.add(8).writeS32(Math.round(Number(worldZ) * 1024));
            const visible = vecToScreen(vector, view) | 0;
            const xFixed = vector.readS32();
            const yFixed = vector.add(4).readS32();
            const action = visible !== 0
                ? (hitTest(owner.add(0x23), xFixed, yFixed) | 0)
                : null;
            results.push({
                turn: i + 1,
                visible: visible,
                x: xFixed / 1024.0,
                y: yFixed / 1024.0,
                z: vector.add(8).readS32() / 1024.0,
                action: action,
            });
        }
        return { owner: ownerText, delta: Number(delta), results: results };
    },
    worldtoscreen: function (worldX, worldY, worldZ) {
        const manager = AZROK_GM_PTR_ADDR.readPointer();
        if (manager.isNull()) {
            throw new Error("game manager is null");
        }
        const view = manager.add(0x918).readPointer();
        if (view.isNull()) {
            throw new Error("current view is null");
        }
        const vector = Memory.alloc(12);
        vector.writeS32(Math.round(Number(worldX) * 1024));
        vector.add(4).writeS32(Math.round(Number(worldY) * 1024));
        vector.add(8).writeS32(Math.round(Number(worldZ) * 1024));
        const vecToScreen = new NativeFunction(
            AZROK_VEC_TO_SCREEN_PTR,
            "int",
            ["pointer", "pointer"]
        );
        const visible = vecToScreen(vector, view) | 0;
        return {
            visible: visible,
            view: view.toString(),
            xFixed: vector.readS32(),
            yFixed: vector.add(4).readS32(),
            zFixed: vector.add(8).readS32(),
            x: vector.readS32() / 1024.0,
            y: vector.add(4).readS32() / 1024.0,
            z: vector.add(8).readS32() / 1024.0,
        };
    },
    hittestgrid: function (x0, y0, x1, y1, step) {
        const inputOwnerText = fakeState.worldInputOwner;
        const hitOwnerText = fakeState.worldHitOwner;
        if (inputOwnerText === "0x0" && hitOwnerText === "0x0") {
            throw new Error("world input owner is not available yet");
        }
        const hitOwner = inputOwnerText !== "0x0"
            ? ptr(inputOwnerText).add(0x23)
            : ptr(hitOwnerText);
        const hitTest = new NativeFunction(
            AZROK_WORLD_HIT_TEST_PTR,
            "int",
            ["pointer", "int", "int"],
            "thiscall"
        );
        const stride = Math.max(4, step | 0);
        const hits = [];
        const counts = {};
        for (let y = y0 | 0; y <= (y1 | 0); y += stride) {
            for (let x = x0 | 0; x <= (x1 | 0); x += stride) {
                const action = hitTest(hitOwner, (x * 1024) | 0, (y * 1024) | 0) | 0;
                const key = String(action);
                counts[key] = (counts[key] || 0) + 1;
                if (action === 0x6f) {
                    hits.push({ x: x, y: y, action: action });
                }
            }
        }
        return { owner: hitOwner.toString(), step: stride, counts: counts, hits: hits };
    },
    activate: function (x, y, hoverMs, holdMs, settleMs) {
        let hover = 120;
        let hold = 100;
        let settle = 100;
        if (typeof settleMs === "undefined") {
            hold = hoverMs | 0;
            settle = holdMs | 0;
        } else {
            hover = hoverMs | 0;
            hold = holdMs | 0;
            settle = settleMs | 0;
        }
        activateClick(x | 0, y | 0, hover, hold, settle, 0, 0, x | 0, y | 0, 0, 0, 0, 0, 0);
        return true;
    },
    activatewithdelta: function (x, y, hoverMs, holdMs, settleMs, dx, dy, startX, startY, hwnd, clientX, clientY, startClientX, startClientY) {
        const sx = (typeof startX === "undefined") ? (x | 0) : (startX | 0);
        const sy = (typeof startY === "undefined") ? (y | 0) : (startY | 0);
        activateClick(
            x | 0,
            y | 0,
            hoverMs | 0,
            holdMs | 0,
            settleMs | 0,
            dx | 0,
            dy | 0,
            sx,
            sy,
            (typeof hwnd === "undefined") ? 0 : (hwnd | 0),
            (typeof clientX === "undefined") ? 0 : (clientX | 0),
            (typeof clientY === "undefined") ? 0 : (clientY | 0),
            (typeof startClientX === "undefined") ? 0 : (startClientX | 0),
            (typeof startClientY === "undefined") ? 0 : (startClientY | 0)
        );
        return true;
    },
    queuetext: function (hwnd, text, screenX, screenY) {
        const targetHwnd = (typeof hwnd === "undefined" || !hwnd)
            ? ((fakeState.hwnd >>> 0) || (fakeState.lastMessageHwnd >>> 0))
            : (hwnd | 0);
        const sx = (typeof screenX === "undefined") ? (fakeState.x | 0) : (screenX | 0);
        const sy = (typeof screenY === "undefined") ? (fakeState.y | 0) : (screenY | 0);
        const queue = buildTextMessageQueue(targetHwnd, String(text || ""), sx, sy);
        for (let i = 0; i < queue.length; i++) {
            fakeState.messageQueue.push(queue[i]);
        }
        if (fakeState.observe) {
            notify("text-queue", {
                hwnd: targetHwnd,
                text: String(text || ""),
                count: queue.length,
                screenX: sx,
                screenY: sy,
            });
        }
        return queue.length;
    },
    namewidgetinfo: function () {
        const gm = getGameManagerPtr();
        const edit = getNameEditObjectPtr();
        const hwnd = getNameEditHwnd();
        return {
            gm: gm ? gm.toString() : null,
            edit: edit ? edit.toString() : null,
            hwnd: hwnd ? hwnd.toString() : null,
            eggIndex: gm ? Memory.readU8(gm.add(AZROK_SELECTED_EGG_OFFSET)) : null,
        };
    },
    shownamedialog: function (eggIndex) {
        return showNameDialogInternal((typeof eggIndex === "undefined") ? -1 : (eggIndex | 0));
    },
    setnametextbytes: function (values) {
        return setNameTextBytes(values || []);
    },
    focusnameedit: function () {
        const edit = getNameEditObjectPtr();
        if (edit === null) {
            return false;
        }
        focusNameEditNative(edit);
        notify("name-edit-focus", {
            edit: edit.toString(),
            hwnd: (getNameEditHwnd() || ptr(0)).toString(),
        });
        return true;
    },
    commitnamehandler: function () {
        const gm = getGameManagerPtr();
        if (gm === null) {
            return false;
        }
        commitNameNative(gm);
        notify("name-commit-handler", {
            gm: gm.toString(),
        });
        return true;
    },
    submitnamebytes: function (values, eggIndex) {
        return submitNameBytes(values || [], (typeof eggIndex === "undefined") ? -1 : (eggIndex | 0));
    },
    pushbutton: function (buttonId, param2, param3, repeat, targetCaller) {
        const id = buttonId | 0;
        const p2 = (typeof param2 === "undefined") ? 0xFFFFFFFF : (param2 >>> 0);
        const p3 = (typeof param3 === "undefined") ? 0xFFFFFFFF : (param3 >>> 0);
        const reps = (typeof repeat === "undefined" || repeat < 1) ? 5 : (repeat | 0);
        const target = (typeof targetCaller === "undefined") ? 0 : (targetCaller >>> 0);
        pendingButtonInjection.id = id;
        pendingButtonInjection.param2 = p2;
        pendingButtonInjection.param3 = p3;
        pendingButtonInjection.remaining = reps;
        pendingButtonInjection.targetCaller = target;
        notify("button-armed", { buttonId: id, param2: p2, param3: p3, repeat: reps, targetCaller: target });
        return true;
    },
    prepareshop: function (buttonId, balance, targetCaller) {
        const id = buttonId | 0;
        const seededBalance = balance >>> 0;
        const target = targetCaller >>> 0;
        if (id < 0x14D || id > 0x179 || seededBalance < 1 || target !== 0x005C3F81) {
            throw new Error("invalid verified Shop preparation arguments");
        }
        pendingShopPrepare.armed = true;
        pendingShopPrepare.balance = seededBalance;
        pendingButtonInjection.id = id;
        pendingButtonInjection.param2 = 2;
        pendingButtonInjection.param3 = 0;
        pendingButtonInjection.remaining = 1;
        pendingButtonInjection.targetCaller = target;
        notify("shop-prepare-armed", { buttonId: id, balance: seededBalance, targetCaller: target });
        return true;
    },
    setobserve: function (enabled) {
        fakeState.observe = !!enabled;
        return fakeState.observe;
    },
    status: function () {
        return {
            active: fakeState.active,
            x: fakeState.x,
            y: fakeState.y,
            targetX: fakeState.targetX,
            targetY: fakeState.targetY,
            clientX: fakeState.clientX,
            clientY: fakeState.clientY,
            dx: fakeState.dx,
            dy: fakeState.dy,
            movePending: fakeState.movePending,
            leftDown: fakeState.leftDown,
            hoverPollsRemaining: fakeState.hoverPollsRemaining,
            downPollsRemaining: fakeState.downPollsRemaining,
            settlePollsRemaining: fakeState.settlePollsRemaining,
            motionQueueLength: fakeState.motionQueue.length,
            cursorQueueLength: fakeState.cursorQueue.length,
            messageQueueLength: fakeState.messageQueue.length,
            observe: fakeState.observe,
            observeCounts: fakeState.observeCounts,
             evolutionGateOwner: fakeState.evolutionGateOwner,
             evolutionGateValue: fakeState.evolutionGateValue,
             worldInputOwner: fakeState.worldInputOwner,
             worldHitOwner: fakeState.worldHitOwner,
            nexusArena: readNexusArena(),
        };
    },
};

notify("loaded", { pointerSize: Process.pointerSize, arch: Process.arch });
