import unittest

from seace_monitor.client import SeaceError, belongs_to_year


class ClientTests(unittest.TestCase):
    def test_filters_year_using_real_publication_date(self):
        self.assertTrue(belongs_to_year({"idContrato": 1, "fecPublica": "04/08/2026 12:00:00"}, 2026))
        self.assertFalse(belongs_to_year({"idContrato": 2, "fecPublica": "31/12/2025 12:00:00"}, 2026))

    def test_invalid_publication_date_aborts_instead_of_losing_data(self):
        with self.assertRaises(SeaceError):
            belongs_to_year({"idContrato": 3, "fecPublica": "fecha-inválida"}, 2026)
