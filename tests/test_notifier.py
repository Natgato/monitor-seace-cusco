import unittest

from seace_monitor.notifier import build_messages


class NotifierTests(unittest.TestCase):
    def test_notification_escapes_html_and_keeps_contract_together(self):
        messages = build_messages([{"codigo_contratacion": "CM <1>", "entidad": "A&B", "descripcion": "x", "fecha_vencimiento": None, "cantidad_items": 0, "enlace_publico": "https://example.test"}], "2026-08-04T10:00:00-05:00")
        self.assertEqual(len(messages), 1)
        self.assertIn("CM &lt;1&gt;", messages[0])
        self.assertIn("A&amp;B", messages[0])
