import os
import unittest
from pathlib import Path
from unittest import mock

import x32dbg_path


class X32DbgPathTests(unittest.TestCase):
    def test_configured_non_d_path_is_selected(self):
        configured = r"B:\Debuggers\x64dbg\x32\x32dbg.exe"
        with mock.patch.dict(os.environ, {"AZROK_X32DBG_PATH": configured}):
            with mock.patch.object(
                Path, "is_file", autospec=True,
                side_effect=lambda path: str(path) == configured,
            ):
                self.assertEqual(x32dbg_path.resolve_x32dbg(), configured)

    def test_d_drive_configuration_is_never_probed(self):
        probed = []

        def fake_is_file(path):
            probed.append(str(path))
            return False

        with mock.patch.dict(
            os.environ, {"AZROK_X32DBG_PATH": r"D:\x64dbg\x32\x32dbg.exe"}
        ):
            with mock.patch.object(Path, "is_file", autospec=True, side_effect=fake_is_file):
                with self.assertRaises(FileNotFoundError):
                    x32dbg_path.resolve_x32dbg()
        self.assertTrue(probed)
        self.assertTrue(all(Path(path).drive.upper() != "D:" for path in probed))


if __name__ == "__main__":
    unittest.main()
