import unittest
from datetime import datetime

from seace_monitor.daily_digest import select_open_regional
from seace_monitor.email_templates import build_daily_email, build_new_contracts_email
from seace_monitor.timeutils import LIMA


class EmailTemplateTests(unittest.TestCase):
    def setUp(self):
        self.moment = datetime(2026, 8, 4, 7, 5, tzinfo=LIMA)
        self.row = {
            "idContrato": "1",
            "codigo_contratacion": "C-001",
            "estado": "Vigente",
            "entidad": "Municipalidad <Cusco>",
            "departamento": "CUSCO",
            "descripcion": "Compra de equipos",
            "fecha_publicacion": "2026-08-04T06:00:00-05:00",
            "fecha_vencimiento": "2026-08-05T12:00:00-05:00",
            "enlace_publico": "https://example.com/1",
            "cantidad_items": 2,
        }

    def test_immediate_email_is_professional_and_escapes_content(self):
        html = build_new_contracts_email([self.row], self.moment)
        self.assertIn("Alerta inmediata", html)
        self.assertIn("Municipalidad &lt;Cusco&gt;", html)
        self.assertNotIn("Municipalidad <Cusco>", html)

    def test_daily_email_contains_regional_metrics(self):
        html = build_daily_email([self.row], {"1": 2}, self.moment)
        self.assertIn("Resumen diario", html)
        self.assertIn("Publicadas hoy", html)
        self.assertIn("solicitudes adicionales", html)

    def test_daily_selection_excludes_expired_and_other_regions(self):
        expired = self.row | {"idContrato": "2", "fecha_vencimiento": "2026-08-03T12:00:00-05:00"}
        other = self.row | {"idContrato": "3", "departamento": "LIMA"}
        apurimac = self.row | {"idContrato": "4", "departamento": "APURÍMAC"}
        selected = select_open_regional([self.row, expired, other, apurimac], self.moment)
        self.assertEqual({row["idContrato"] for row in selected}, {"1", "4"})
