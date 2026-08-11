import unittest

from seace_monitor.client import SeaceError
from seace_monitor.monitor import changed, contract_row, hydrate_requirement_links


class MonitorLogicTests(unittest.TestCase):
    def test_unchanged_listing_does_not_request_detail(self):
        listing = {"nomEstadoContrato": "Vigente", "fecFinCotizacion": "05/08/2026 16:00:00", "fecPublica": "04/08/2026 12:38:09"}
        stored = {"estado": "Vigente", "fecha_vencimiento_raw": "05/08/2026 16:00:00", "fecha_publicacion": "2026-08-04T12:38:09-05:00"}
        self.assertFalse(changed(listing, stored))

    def test_contract_row_persists_requirement_download_url(self):
        listing = {
            "idContrato": 1,
            "desContratacion": "CM-1-2026",
            "fecPublica": "04/08/2026 12:38:09",
            "fecFinCotizacion": "05/08/2026 16:00:00",
        }
        url = "https://prod6.seace.gob.pe/requirement/1"

        row = contract_row(listing, None, "2026-08-04T13:00:00-05:00", url, True)

        self.assertEqual(row["enlace_requerimiento"], url)
        self.assertEqual(row["requerimiento_consultado"], "1")

    def test_requirement_lookup_is_optional_and_retryable(self):
        class FakeClient:
            def requirement_url(self, contract_id):
                if contract_id == "2":
                    raise SeaceError("servicio temporalmente no disponible")
                return "https://example.com/requirement/1"

        rows = {"1": {}, "2": {}}
        completed = hydrate_requirement_links(FakeClient(), rows, ["1", "2"])

        self.assertEqual(completed, 1)
        self.assertEqual(rows["1"]["requerimiento_consultado"], "1")
        self.assertNotIn("requerimiento_consultado", rows["2"])
