import json
from types import SimpleNamespace
import pytest
from app.config import LLMSettings
from app.llm_client import LLMClient
from app.schemas import ContractFacts

class SequencedCompletions:
    def __init__(self):
        self.calls = 0
        self.contents = [
            json.dumps({"language": {"equal_effectiveness": True}, "parties": {"seller": "甲方"}}),
            json.dumps({"title": "采购合同", "language": "bilingual", "parties": []}),
        ]

    async def create(self, **kwargs):
        content = self.contents[self.calls]
        self.calls += 1
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

@pytest.mark.asyncio
async def test_structured_retries_invalid_model_json():
    llm = LLMClient(LLMSettings(api_key="mock"))
    completions = SequencedCompletions()
    llm.client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    facts = await llm.structured("提取合同信息", ContractFacts)
    assert facts.language == "bilingual"
    assert completions.calls == 2
