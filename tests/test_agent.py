import json
from types import SimpleNamespace
import pytest
from app.agent import ReviewAgent
from app.knowledge import KnowledgeBase
from app.schemas import ContractFacts
from tests.mock_llm import MockLLM

@pytest.mark.asyncio
async def test_agent_calls_search_tool_and_validates_citations(tmp_path):
    agent = ReviewAgent(MockLLM(), KnowledgeBase(path=tmp_path / "qdrant"))
    review, calls = await agent.review("付款条款", ContractFacts(language="bilingual"), [], "CN-JP")
    assert len(calls) == 1
    assert calls[0].results
    assert review.issues[0].basis_chunk_ids == []

@pytest.mark.asyncio
async def test_agent_repairs_non_json_final_tool_response(tmp_path):
    llm = MockLLM()
    original = llm.tool_completion

    async def malformed_final(messages, tools):
        response = await original(messages, tools)
        if llm.round > 1:
            response.choices[0].message.content = "无法生成 JSON"
        return response

    llm.tool_completion = malformed_final
    review, calls = await ReviewAgent(llm, KnowledgeBase(path=tmp_path / "qdrant")).review("付款条款", ContractFacts(language="bilingual"), [], "CN-JP")
    assert calls and review.overall_summary

@pytest.mark.asyncio
async def test_agent_runs_fallback_rag_when_model_skips_tool(tmp_path):
    llm = MockLLM()

    async def no_tool_response(messages, tools):
        content = json.dumps({"issues": [], "missing_clauses": [], "overall_summary": "已完成审查。"})
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[], content=content))])

    llm.tool_completion = no_tool_response
    review, calls = await ReviewAgent(llm, KnowledgeBase(path=tmp_path / "qdrant")).review("付款条款", ContractFacts(contract_type="采购合同", language="bilingual"), [], "CN-JP")
    assert review.overall_summary
    assert len(calls) == 1
    assert calls[0].query.startswith("合同审查")
