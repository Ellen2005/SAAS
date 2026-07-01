import pytest
import asyncio
from unittest.mock import MagicMock
from api.services.prompt_manager import PromptManager, DEFAULT_PROMPTS


class TestPromptManager:
    def setup_method(self):
        self.mock_db = MagicMock()
        self.pm = PromptManager(self.mock_db)

    def test_list_prompts(self):
        mock_result = MagicMock()
        mock_result.data = [
            {"name": "test", "category": "nlq", "template": "Test template"},
        ]
        order2 = MagicMock()
        order2.execute.return_value = mock_result
        order1 = MagicMock()
        order1.order.return_value = order2
        eq_mock = MagicMock()
        eq_mock.order.return_value = order1
        select_mock = MagicMock()
        select_mock.eq.return_value = eq_mock
        table_mock = MagicMock()
        table_mock.select.return_value = select_mock
        self.mock_db.table.return_value = table_mock

        prompts = asyncio.run(self.pm.list_prompts(category="nlq"))
        assert isinstance(prompts, list)
        assert len(prompts) >= 1

    def test_get_prompt(self):
        mock_result = MagicMock()
        mock_result.data = [
            {
                "name": "test_prompt",
                "category": "nlq",
                "template": "Hello {name}, your question is: {question}",
                "variables": ["name", "question"],
            },
        ]
        limit_mock = MagicMock()
        limit_mock.execute.return_value = mock_result
        eq3 = MagicMock()
        eq3.limit.return_value = limit_mock
        eq2 = MagicMock()
        eq2.eq.return_value = eq3
        eq1 = MagicMock()
        eq1.eq.return_value = eq2
        select_mock = MagicMock()
        select_mock.eq.return_value = eq1
        table_mock = MagicMock()
        table_mock.select.return_value = select_mock
        self.mock_db.table.return_value = table_mock

        result = asyncio.run(self.pm.get_prompt(
            category="nlq",
            name="test_prompt",
            variables={"name": "User", "question": "What is sales?"},
        ))
        assert "Hello User" in result
        assert "What is sales?" in result

    def test_variable_substitution(self):
        template = "SELECT * FROM {table} WHERE {column} = {value}"
        self.pm._cache["test:sub"] = {"template": template}
        self.mock_db.table.return_value.select.return_value = MagicMock(data=[])

        result = asyncio.run(self.pm.get_prompt(
            category="test",
            name="sub",
            variables={"table": "users", "column": "id", "value": "1"},
        ))
        assert "users" in result
        assert "id" in result
        assert "1" in result
