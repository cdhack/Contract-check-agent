from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.knowledge import KnowledgeBase
from app.parsers import parse_contract
from app.pipeline import ReviewPipeline
from tests.mock_llm import MockLLM

@pytest.mark.asyncio
async def test_history_lists_and_loads_saved_reviews(tmp_path, monkeypatch):
    import app.main as main_module
    import app.pipeline as pipeline_module
    monkeypatch.setattr(pipeline_module, "ROOT", tmp_path)
    monkeypatch.setattr(main_module, "REPORTS", tmp_path / "data" / "reports")
    class FakeLLM:
        def __init__(self, settings): self.settings = type("Settings", (), {"model": "mock-model"})()
        async def structured(self, prompt, schema): return schema(conclusion="已核实", basis=["测试依据"], recommendations=["测试建议"])
    monkeypatch.setattr(main_module, "LLMClient", FakeLLM)
    contract = parse_contract("sample.txt", (Path(__file__).parent / "fixtures" / "bilingual_contract.txt").read_bytes())
    saved = await ReviewPipeline(MockLLM(), KnowledgeBase(path=tmp_path / "qdrant")).run(contract, "CN-JP")
    with TestClient(main_module.app) as client:
        assert client.post("/api/access/login", json={"employee_id": "1"}).status_code == 200
        history = client.get("/api/reviews")
        detail = client.get(f"/api/reviews/{saved.review_id}")
        knowledge_page = client.get("/knowledge")
        verify = client.post("/api/verify", json={"prompt": "核实付款条款"})
        deleted = client.delete(f"/api/reviews/{saved.review_id}")
        remaining = client.get("/api/reviews")
    assert history.status_code == 200
    assert history.json()[0]["review_id"] == saved.review_id
    assert history.json()[0]["created_at"]
    assert detail.status_code == 200
    assert detail.json()["report_markdown"] == saved.report_markdown
    assert knowledge_page.status_code == 200
    assert "知识库管理" in knowledge_page.text
    assert verify.status_code == 200
    assert verify.json()["result"]["conclusion"] == "已核实"
    assert deleted.status_code == 200
    assert remaining.json() == []
