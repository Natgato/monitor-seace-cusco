import io
import unittest
from datetime import datetime

from pypdf import PdfReader

from seace_monitor.pdf_report import build_daily_pdf
from seace_monitor.timeutils import LIMA


class PdfReportTests(unittest.TestCase):
    def setUp(self):
        self.moment = datetime(2026, 8, 8, 7, 5, tzinfo=LIMA)
        self.row = {
            "idContrato": "1",
            "codigo_contratacion": "CM-001-2026-RA",
            "estado": "Vigente",
            "objeto_contratacion": "Bien",
            "entidad": "Municipalidad Provincial de Abancay",
            "ruc_entidad": "20123456789",
            "departamento": "APURÍMAC",
            "provincia": "Abancay",
            "distrito": "Abancay",
            "descripcion": "Adquisición de útiles, equipos y materiales para atención pública " * 5,
            "fecha_publicacion": "2026-08-08T06:00:00-05:00",
            "fecha_vencimiento": "2026-08-09T12:00:00-05:00",
            "enlace_publico": "https://prod6.seace.gob.pe/buscador-publico/contrataciones/1",
        }

    def test_builds_readable_pdf_with_brand_and_links(self):
        content = build_daily_pdf([self.row], {"1": 3}, self.moment, "Empresa Ñandú")
        self.assertTrue(content.startswith(b"%PDF"))
        reader = PdfReader(io.BytesIO(content))
        self.assertGreaterEqual(len(reader.pages), 5)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        self.assertIn("RADAR", text)
        self.assertIn("Empresa Ñandú", text)
        self.assertIn("APURÍMAC", text)
        annotations = [annotation for page in reader.pages for annotation in (page.get("/Annots") or [])]
        self.assertTrue(annotations)

    def test_builds_empty_report(self):
        content = build_daily_pdf([], {}, self.moment)
        self.assertTrue(content.startswith(b"%PDF"))
        self.assertGreaterEqual(len(PdfReader(io.BytesIO(content)).pages), 4)
