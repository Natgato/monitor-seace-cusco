import unittest

from seace_monitor.monitor import changed


class MonitorLogicTests(unittest.TestCase):
    def test_unchanged_listing_does_not_request_detail(self):
        listing = {"nomEstadoContrato": "Vigente", "fecFinCotizacion": "05/08/2026 16:00:00", "fecPublica": "04/08/2026 12:38:09"}
        stored = {"estado": "Vigente", "fecha_vencimiento_raw": "05/08/2026 16:00:00", "fecha_publicacion": "2026-08-04T12:38:09-05:00"}
        self.assertFalse(changed(listing, stored))
