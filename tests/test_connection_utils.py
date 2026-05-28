import unittest

from backend.api.services.connection_utils import (
    detect_db_type,
    enrich_connection_payload,
    normalize_credentials,
    parse_connection_uri,
)


class ConnectionUtilsTests(unittest.TestCase):
    def test_detect_mongodb_from_uri(self):
        uri = "mongodb+srv://user:pass@cluster.example.net/mydb"
        self.assertEqual(detect_db_type(uri), "mongodb")

    def test_normalize_postgres_uri(self):
        uri = "postgresql://reader:secret@db.example.com:5432/app"
        out = normalize_credentials(uri, "postgresql")
        self.assertTrue(out.startswith("postgresql+psycopg2://"))

    def test_detect_oracle_uri(self):
        uri = "oracle+oracledb://user:secret@oracle.example.com:1521/ORCL"
        self.assertEqual(detect_db_type(uri), "oracle")

    def test_normalize_oracle_uri(self):
        uri = "oracle://user:secret@oracle.example.com:1521/ORCL"
        out = normalize_credentials(uri, "oracle")
        self.assertTrue(out.startswith("oracle+oracledb://"))

    def test_enrich_direct_uri_only_payload(self):
        uri = "postgresql://reader:secret@hh-pgsql-public.ebi.ac.uk:5432/pfmegrnargs"
        enriched = enrich_connection_payload({"credentials": uri, "db_type": "postgresql"})
        self.assertEqual(enriched["host"], "hh-pgsql-public.ebi.ac.uk")
        self.assertEqual(enriched["port"], 5432)
        self.assertEqual(enriched["db_name"], "pfmegrnargs")
        self.assertIn("postgresql", enriched["credentials"])

    def test_parse_sqlite_path(self):
        parsed = parse_connection_uri("sqlite:///C:/data/demo.db")
        self.assertEqual(parsed["host"], "local")
        self.assertIn("demo.db", parsed["db_name"])


if __name__ == "__main__":
    unittest.main()
