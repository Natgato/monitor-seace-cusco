import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from seace_monitor.config import Config
from seace_monitor.storage import load_state, save_state


class StorageTests(unittest.TestCase):
    def test_state_roundtrip_uses_plain_utf8_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "estado.json"
            config = replace(Config(), state_path=path)
            state = load_state(config)
            state["initialized"] = True
            save_state(config, state)
            self.assertFalse(path.read_bytes().startswith(b"\xef\xbb\xbf"))
            self.assertTrue(load_state(config)["initialized"])
            json.loads(path.read_text(encoding="utf-8"))

    def test_migrates_old_initialized_state_as_cusco_only(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "estado.json"
            path.write_text('{"initialized": true, "contratos_conocidos": []}', encoding="utf-8")
            config = replace(Config(), state_path=path)
            self.assertEqual(load_state(config)["departamentos_inicializados"], ["CUSCO"])
