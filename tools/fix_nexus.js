"use strict";

// Fix Acknex "Nexus too small" by expanding the nexus buffer
// Nexus globals in acknex.dll (loaded at 0x10000000):
//   0x102FE9B0 = nexus current alloc position (pointer)
//   0x102FE9BC = nexus end pointer
//   0x102FE9C0 = nexus start pointer
// Size = end - start. Default ~28KB, need ~2MB+ for room.wmb

try {
    var pStart = ptr("0x102FE9C0");
    var pEnd   = ptr("0x102FE9BC");
    var pPos   = ptr("0x102FE9B0");

    var startAddr = pStart.readPointer();
    var endAddr   = pEnd.readPointer();
    var posAddr   = pPos.readPointer();
    var curSize   = endAddr.sub(startAddr).toUInt32();

    send({type: "current", start: startAddr.toString(), end: endAddr.toString(),
          pos: posAddr.toString(), sizeBytes: curSize, sizeKB: curSize / 1024});

    var targetSize = 4 * 1024 * 1024; // 4MB
    if (curSize < targetSize) {
        // Allocate new larger buffer
        var newBuf = Memory.alloc(targetSize);
        var newEnd = newBuf.add(targetSize);

        // Copy existing data
        var used = posAddr.sub(startAddr).toUInt32();
        if (used > 0 && used < curSize) {
            Memory.copy(newBuf, startAddr, used);
        }

        // Update pointers
        pStart.writePointer(newBuf);
        pEnd.writePointer(newEnd);
        pPos.writePointer(newBuf.add(used));

        send({type: "expanded", newStart: newBuf.toString(), newEnd: newEnd.toString(),
              newSizeKB: targetSize / 1024, copiedBytes: used});
    } else {
        send({type: "ok", msg: "nexus already large enough"});
    }
} catch(e) {
    send({type: "error", msg: e.message, stack: e.stack});
}
