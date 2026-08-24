import json
from types import SimpleNamespace
import pytest
from app.agent import ReviewAgent
from app.depth import depth_guidance, depth_label, max_searches, review_temperature
from app.schemas import ContractFacts, ReviewResult

def test_depth_policy_has_expected_rounds_and_temperature():
    assert depth_label("standard") == "标准审查"
    assert depth_label("deep") == "深度审查"
    assert max_searches("standard") == 2
    assert max_searches("deep") == 4
    assert review_temperature("standard", 0.1) == 0.1
    assert review_temperature("deep", 0.1) == 0.2
    assert review_temperature("deep", 0.8) == 0.3
    assert "逐项覆盖" in depth_guidance("deep")

class MultiCallLLM:
    def __init__(self): self.settings = SimpleNamespace(max_tool_rounds=3); self.calls = 0
    async def tool_completion(self, messages, tools, **kwargs):
        self.calls += 1
        if self.calls == 1:
            tool_calls = [SimpleNamespace(id=f"tool-{index}", function=SimpleNamespace(arguments=json.dumps({"query": str(index), "jurisdiction": "CN"}))) for index in range(4)]
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=tool_calls, content=None, model_dump=lambda **kwargs: {"role": "assistant", "tool_calls": []}))])
        content = ReviewResult().model_dump_json()
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[], content=content, model_dump=lambda **kwargs: {"role": "assistant", "content": content}))])

class StubKnowledge:
    def search_knowledge(self, query, jurisdiction, top_k): return []

@pytest.mark.asyncio
async def test_standard_review_limits_actual_searches_when_model_requests_many():
    _, records = await ReviewAgent(MultiCallLLM(), StubKnowledge()).review("合同正文", ContractFacts(), [], "CN", max_searches=2)
    assert len(records) == 2
