from types import SimpleNamespace
from fastapi.testclient import TestClient
from app.schemas import GeneratedContract

REQUEST = {
    "title": "中日软件开发服务合同",
    "contract_type": "软件开发服务",
    "jurisdiction": "CN-JP",
    "language": "bilingual",
    "drafting_position": "neutral",
    "party_a_name": "甲株式会社",
    "party_a_role": "委托方",
    "party_b_name": "乙科技有限公司",
    "party_b_role": "服务方",
    "scope": "开发并交付企业管理系统",
    "price": "CNY 100,000",
    "payment_terms": "验收合格后30日内付款",
    "delivery_terms": "2026年12月31日前交付",
    "acceptance_terms": "双方书面验收",
    "term": "自签署日起一年",
    "intellectual_property": "成果归委托方所有",
    "confidentiality": "保密义务存续三年",
    "liability": "责任上限为合同总价",
    "dispute_resolution": "北京仲裁委员会仲裁",
    "language_priority": "中文优先",
    "special_requirements": "需要数据保护条款",
}

class FakeGenerationLLM:
    def __init__(self, settings): self.settings = SimpleNamespace(model="mock-generation")
    async def structured(self, prompt, schema, **kwargs):
        assert schema is GeneratedContract
        return GeneratedContract(title="中日软件开发服务合同", document_markdown="# 中日软件开发服务合同\n\n第一条 服务范围\n\n第1条 サービス範囲",
            assumptions=["维护响应级别待确认"], missing_information=["请确认验收标准"], drafting_notes=["中日条款按相同编号起草"],
            coverage=[{"clause": "保密", "status": "included", "note": "已纳入"}, {"clause": "数据保护", "status": "needs_confirmation", "note": "待确认适用要求"}])

def test_generation_api_persists_lists_downloads_and_deletes(tmp_path, monkeypatch):
    import app.generation as generation_module
    import app.main as main_module
    monkeypatch.setattr(generation_module, "ROOT", tmp_path)
    monkeypatch.setattr(main_module, "GENERATIONS", tmp_path / "data" / "generations")
    monkeypatch.setattr(main_module, "LLMClient", FakeGenerationLLM)
    with TestClient(main_module.app) as client:
        created = client.post("/api/generations", json=REQUEST)
        generation_id = created.json()["generation_id"]
        history = client.get("/api/generations")
        detail = client.get(f"/api/generations/{generation_id}")
        markdown = client.get(f"/api/generations/{generation_id}/download/md")
        deleted = client.delete(f"/api/generations/{generation_id}")
    assert created.status_code == 200
    assert created.json()["result"]["missing_information"] == ["请确认验收标准"]
    assert history.json()[0]["generation_id"] == generation_id
    assert detail.json()["model"] == "mock-generation"
    assert markdown.status_code == 200
    assert "完整合同草案" in markdown.text
    assert deleted.status_code == 200
