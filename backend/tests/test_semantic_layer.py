import pytest
from unittest.mock import MagicMock
from api.services.semantic_layer import SemanticLayer


class TestSemanticLayer:
    def setup_method(self):
        self.mock_db = MagicMock()
        self.layer = SemanticLayer(self.mock_db, "test-user-123")
        self.layer._raw_to_business = {
            "claim_amt": "Claim Amount",
            "policy_no": "Policy Number",
        }
        self.layer._business_to_raw = {
            "Claim Amount": "claim_amt",
            "Policy Number": "policy_no",
        }
        self.layer._loaded = True

    def test_to_business(self):
        result = self.layer.to_business("claim_amt")
        assert result == "Claim Amount"

    def test_to_raw(self):
        result = self.layer.to_raw("Claim Amount")
        assert result == "claim_amt"

    def test_has_mappings(self):
        assert self.layer.has_mappings() is True

        empty_layer = SemanticLayer(self.mock_db, "test-user-456")
        empty_layer._raw_to_business = {}
        assert empty_layer.has_mappings() is False
