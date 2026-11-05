from ghidra.program.model.listing import Function

# Usage:
#   script args: <hex_address> [hex_address ...]
#
# Prints direct references to each address and the containing function name.

args = getScriptArgs()
if not args:
    print("usage: show_xrefs.py <hex_address> [hex_address ...]")
    exit()

listing = currentProgram.getListing()

for raw in args:
    raw = raw.strip()
    if raw.lower().startswith("0x"):
        raw = raw[2:]
    addr = toAddr(raw)
    if addr is None:
        print("invalid address:", raw)
        continue

    print("== xrefs to %s ==" % addr)
    refs = getReferencesTo(addr)
    count = 0
    for ref in refs:
        from_addr = ref.getFromAddress()
        func = getFunctionContaining(from_addr)
        if func is None:
            func_name = "<no function>"
        else:
            func_name = func.getName()
        print("%s  %-18s  %s" % (from_addr, ref.getReferenceType(), func_name))
        count += 1
    if count == 0:
        print("<none>")
