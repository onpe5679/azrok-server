from ghidra.app.script import GhidraScript


class FindRefsScript(GhidraScript):
    def run(self):
        args = self.getScriptArgs()
        if len(args) < 1:
            print("usage: <address>")
            return

        target = self.toAddr(args[0])
        print("TARGET", target)
        refs = self.getReferencesTo(target)
        count = 0
        for ref in refs:
            frm = ref.getFromAddress()
            func = self.getFunctionContaining(frm)
            name = func.getName() if func else "<no_func>"
            print("FROM", frm, "FUNC", name, "TYPE", ref.getReferenceType())
            count += 1
        print("TOTAL", count)


if __name__ == "__main__":
    FindRefsScript().run()
