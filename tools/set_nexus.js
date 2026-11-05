"use strict";

try {
    var varForName = Module.getExportByName("acknex.dll", "var_for_name");
    send({type: "info", msg: "var_for_name: " + varForName});

    var fn = new NativeFunction(varForName, "pointer", ["pointer"]);
    var nameStr = Memory.allocUtf8String("nexus");
    var ptr = fn(nameStr);
    send({type: "info", msg: "nexus ptr: " + ptr});

    if (!ptr.isNull()) {
        var cur = ptr.readS32();
        send({type: "current", value: cur});
        ptr.writeS32(10000);
        send({type: "set", value: ptr.readS32()});
    } else {
        send({type: "error", msg: "nexus is null"});
    }
} catch (e) {
    send({type: "error", msg: e.message, stack: e.stack});
}
