import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import fluidsynth_library as F


class PortabilityTests(unittest.TestCase):
    def test_system_library_takes_precedence(self):
        with patch.object(F.ctypes.util, 'find_library', return_value='system-library'), \
                patch.object(F.shutil, 'which') as which:
            self.assertEqual(F.find_library(), 'system-library')
            which.assert_not_called()

    def test_official_windows_dll_next_to_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / 'tools with spaces'
            folder.mkdir()
            cli, dll = folder / 'fluidsynth.exe', folder / 'libfluidsynth-3.dll'
            cli.touch(); dll.touch()
            with patch.object(F.ctypes.util, 'find_library', return_value=None), \
                    patch.object(F.shutil, 'which', return_value=str(cli)):
                self.assertEqual(F.find_library(), str(dll.resolve()))

    def test_missing_library_returns_none(self):
        with patch.object(F.ctypes.util, 'find_library', return_value=None), \
                patch.object(F.shutil, 'which', return_value=None):
            self.assertIsNone(F.find_library())

    def test_isolated_cli_emits_utf8_json_without_utf8_mode_flag(self):
        # -I ignores the parent's PYTHONUTF8; Windows uses its real default locale.
        result = subprocess.run([sys.executable, '-I', '-B', str(SCRIPTS / 'soundfonts.py'),
                                 'search', '钢琴', '--json'], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', 'replace'))
        matches = json.loads(result.stdout.decode('utf-8'))
        self.assertTrue(matches)
        self.assertTrue(any('钢琴' in entry['tags'] for entry in matches))


if __name__ == '__main__':
    unittest.main()
