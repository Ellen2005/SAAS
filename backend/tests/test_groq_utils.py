import os
import pytest
from unittest.mock import patch
from api.services.groq_utils import get_groq_model, create_groq_client


class TestGroqUtils:
    def test_get_groq_model_default(self):
        with patch.dict(os.environ, {}, clear=True):
            model = get_groq_model()
            assert model == "llama-3.3-70b-versatile"

    def test_get_groq_model_env_override(self):
        with patch.dict(os.environ, {"GROQ_MODEL": "custom-model"}):
            model = get_groq_model()
            assert model == "custom-model"

    def test_create_groq_client_no_key(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}, clear=False):
            with pytest.raises(RuntimeError, match="GROQ_API_KEY not configured"):
                create_groq_client()
