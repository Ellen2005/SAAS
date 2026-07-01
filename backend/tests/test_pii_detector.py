from api.services.pii_detector import PIIDetector


class TestPIIDetector:
    def setup_method(self):
        self.detector = PIIDetector()

    def test_detect_email(self):
        findings = self.detector.detect("Contact me at john@example.com for details")
        email_findings = [f for f in findings if f["type"] == "email"]
        assert len(email_findings) >= 1
        assert email_findings[0]["value"] == "john@example.com"

    def test_detect_phone(self):
        findings = self.detector.detect("Call me at +237 612 345 678")
        phone_findings = [f for f in findings if f["type"] == "phone"]
        assert len(phone_findings) >= 1

    def test_redact_for_llm(self):
        redacted, mapping = self.detector.redact_for_llm(
            "Email john@example.com and call +237 612 345 678"
        )
        assert "john@example.com" not in redacted
        assert "__PII_" in redacted
        assert len(mapping) > 0

    def test_restore(self):
        original = "Email john@example.com"
        redacted, mapping = self.detector.redact_for_llm(original)
        restored = self.detector.restore(redacted, mapping)
        assert restored == original

    def test_no_pii(self):
        findings = self.detector.detect("The weather is nice today")
        assert len(findings) == 0
