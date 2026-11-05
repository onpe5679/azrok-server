import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER = (ROOT / "azrok_server.py").read_text(encoding="utf-8")


class LinuxServerImportContractTests(unittest.TestCase):
    def test_windows_native_handles_are_platform_guarded(self) -> None:
        self.assertIn("if os.name == 'nt':", SERVER)
        self.assertIn("kernel32 = ctypes.windll.kernel32", SERVER)
        self.assertIn("kernel32 = None", SERVER)
        self.assertIn("user32 = None", SERVER)


if __name__ == "__main__":
    unittest.main()
