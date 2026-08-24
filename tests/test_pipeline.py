from pathlib import Path
import pytest
from app.knowledge import KnowledgeBase
from app.parsers import parse_contract
from app.pipeline import ReviewPipeline
from tests.mock_llm import MockLLM

@pytest.mark.asyncio
async def test_mock_end_to_end_writes_valid_report(tmp_path, monkeypatch):
    import app.pipeline as pipeline_module
    monkeypatch.setattr(pipeline_module, "ROOT", tmp_path)
    content = (Path(__file__).parent / "fixtures" / "bilingual_contract.txt").read_bytes()
    result = await ReviewPipeline(MockLLM(), KnowledgeBase(path=tmp_path / "qdrant")).run(parse_contract("sample.txt", content), "CN-JP", "buyer", "deep")
    assert result.comparison and result.tool_calls
    assert result.created_at is not None
    assert result.stance == "buyer"
    assert result.depth == "deep"
    assert "审查立场：买方" in result.report_markdown
    assert "审查深度：深度审查" in result.report_markdown
    assert "合同审查报告" in result.report_markdown
    assert (tmp_path / "data" / "reports" / f"{result.review_id}.json").exists()
