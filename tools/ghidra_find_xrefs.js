var targets = getScriptArgs().split(";");
for (var i = 0; i < targets.length; i++) {
    var text = targets[i].trim();
    if (text.length === 0) continue;
    var target = toAddr(text);
    println("TARGET " + target);
    var refs = getReferencesTo(target);
    for (var j = 0; j < refs.length; j++) {
        var ref = refs[j];
        var fn = getFunctionContaining(ref.getFromAddress());
        println("  " + ref.getFromAddress() + " " + ref.getReferenceType()
            + " function=" + (fn === null ? "<none>" : fn.getEntryPoint() + " " + fn.getName()));
    }
}
