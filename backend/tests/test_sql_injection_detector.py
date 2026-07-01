from api.services.sql_injection_detector import SQLInjectionDetector


class TestSQLInjectionDetector:
    def setup_method(self):
        self.detector = SQLInjectionDetector()

    def test_detect_union_injection(self):
        result = self.detector.analyze("SELECT * FROM users UNION SELECT * FROM passwords")
        assert result["safe"] is False
        assert result["risk_level"] == "CRITICAL"

    def test_detect_stacked_queries(self):
        result = self.detector.analyze("SELECT 1; DROP TABLE users")
        assert result["safe"] is False
        assert result["risk_level"] == "CRITICAL"

    def test_clean_input(self):
        result = self.detector.analyze("SELECT name FROM users WHERE id = 1")
        assert result["safe"] is True
        assert result["risk_level"] == "NONE"

    def test_detect_drop_table(self):
        result = self.detector.analyze("DROP TABLE users")
        assert result["safe"] is False
        assert result["risk_level"] == "CRITICAL"
