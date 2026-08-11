import unittest

from seace_monitor.client import FILES_BASE, SeaceClient, SeaceError, belongs_to_year
from seace_monitor.config import Config


class ClientTests(unittest.TestCase):
    def test_filters_year_using_real_publication_date(self):
        self.assertTrue(belongs_to_year({"idContrato": 1, "fecPublica": "04/08/2026 12:00:00"}, 2026))
        self.assertFalse(belongs_to_year({"idContrato": 2, "fecPublica": "31/12/2025 12:00:00"}, 2026))

    def test_invalid_publication_date_aborts_instead_of_losing_data(self):
        with self.assertRaises(SeaceError):
            belongs_to_year({"idContrato": 3, "fecPublica": "fecha-inválida"}, 2026)

    def test_fetches_each_department_and_deduplicates(self):
        client = SeaceClient(Config(page_delay_seconds=0, departments=((8, "CUSCO"), (3, "APURIMAC"))))
        calls = []

        def fake_search(page, department_code):
            calls.append((page, department_code))
            return {
                "data": [{"idContrato": 1, "fecPublica": "04/08/2026 12:00:00"}],
                "pageable": {"totalElements": 1},
            }

        client.search_page = fake_search
        records = client.fetch_all()
        self.assertEqual(calls, [(1, 8), (1, 3)])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["_requested_department"], "CUSCO")

    def test_builds_direct_requirement_download_url(self):
        client = SeaceClient(Config())
        calls = []

        def fake_get_json(base, path, params):
            calls.append((base, path, params))
            return [{"idContratoArchivo": 339689, "nombre": "TDR.pdf"}]

        client._get_json = fake_get_json
        url = client.requirement_url("85929")

        self.assertEqual(
            url,
            f"{FILES_BASE}/archivos-publico/descargar-archivo-contrato/339689",
        )
        self.assertEqual(
            calls,
            [(FILES_BASE, "archivos-publico/listar-archivos-contrato/85929/1", {})],
        )
        self.assertEqual(client.file_requests, 1)

    def test_requirement_url_is_optional_when_seace_has_no_file(self):
        client = SeaceClient(Config())
        client._get_json = lambda base, path, params: []

        self.assertIsNone(client.requirement_url("1"))
