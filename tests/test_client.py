import unittest

from seace_monitor.client import SeaceClient, SeaceError, belongs_to_year
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
