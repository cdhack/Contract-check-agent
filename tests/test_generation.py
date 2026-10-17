from types import SimpleNamespace
from fastapi.testclient import TestClient
from app.contract_templates import TEMPLATES
from app.schemas import ContractGenerationRequest, GeneratedContract, KnowledgeChunk

REQUEST = {
    "template_id": "jp-housing-lease",
    "answers": {
        "property_parties": "东京都千代田区1-1-1；甲株式会社为出租方，乙为承租方",
        "term_rent": "2026年1月1日起两年；月租 JPY 100,000，押金两个月",
        "conditions": "禁止转租",
        "supplement": "允许饲养一只猫",
    },
}

class FakeGenerationLLM:
    def __init__(self, settings): self.settings = SimpleNamespace(model="mock-generation")
    async def structured(self, prompt, schema, **kwargs):
        assert schema is GeneratedContract
        return GeneratedContract(title="中日软件开发服务合同", document_markdown="# 中日软件开发服务合同\n\n第一条 服务范围\n\n第1条 サービス範囲",
            assumptions=["维护响应级别待确认"], missing_information=["请确认验收标准"], drafting_notes=["中日条款按相同编号起草"],
            coverage=[{"clause": "保密", "status": "included", "note": "已纳入"}, {"clause": "数据保护", "status": "needs_confirmation", "note": "待确认适用要求"}])

class FakeKnowledge:
    def search_knowledge(self, query, jurisdiction, top_k):
        return [KnowledgeChunk(chunk_id="jp-law-1", source_id="jp-law", title="日本法规资料", jurisdiction="JP", section="第1条", source_url="https://example.com/jp-law", text="日本合同法规依据")]

def test_generation_api_persists_lists_downloads_and_deletes(tmp_path, monkeypatch):
    import app.generation as generation_module
    import app.main as main_module
    monkeypatch.setattr(generation_module, "ROOT", tmp_path)
    monkeypatch.setattr(main_module, "GENERATIONS", tmp_path / "data" / "generations")
    monkeypatch.setattr(main_module, "LLMClient", FakeGenerationLLM)
    monkeypatch.setattr(main_module, "KnowledgeBase", FakeKnowledge)
    with TestClient(main_module.app) as client:
        assert client.post("/api/access/login", json={"employee_id": "1"}).status_code == 200
        created = client.post("/api/generations", json={**REQUEST, "language": "ja"})
        generation_id = created.json()["generation_id"]
        templates = client.get("/api/generation-templates")
        history = client.get("/api/generations")
        detail = client.get(f"/api/generations/{generation_id}")
        markdown = client.get(f"/api/generations/{generation_id}/download/md")
        word = client.get(f"/api/generations/{generation_id}/download/docx")
        deleted = client.delete(f"/api/generations/{generation_id}")
    assert created.status_code == 200
    assert created.json()["result"]["missing_information"] == ["请确认验收标准"]
    assert created.json()["request"]["language"] == "ja"
    assert "补充说明" in created.json()["result"]["document_markdown"]
    assert "语言：日文" in created.json()["report_markdown"]
    assert created.json()["template_label"] == "日本房屋租赁合同"
    assert created.json()["knowledge_chunks"][0]["chunk_id"] == "jp-law-1"
    assert templates.status_code == 200
    assert len(templates.json()) == 8
    assert history.json()[0]["generation_id"] == generation_id
    assert history.json()[0]["template_label"] == "日本房屋租赁合同"
    assert detail.json()["model"] == "mock-generation"
    assert markdown.status_code == 200
    assert "完整合同草案" in markdown.text
    assert word.status_code == 200
    assert word.content[:2] == b"PK"
    assert deleted.status_code == 200

def test_contract_templates_limit_input_fields_and_have_unique_ids():
    assert len({template.template_id for template in TEMPLATES}) == len(TEMPLATES)
    assert all(1 <= len(template.fields) <= 6 for template in TEMPLATES)
    lease = next(template for template in TEMPLATES if template.template_id == "jp-housing-lease")
    goods = next(template for template in TEMPLATES if template.template_id == "goods-sale")
    assert "乙方（承租方）：日全テック株式会社" in lease.fields[0].default
    assert "宠物：可 / 不可" in lease.fields[2].default
    assert "乙方（买方）：日全テック株式会社" in goods.fields[0].default
    assert len(next(template for template in TEMPLATES if template.template_id == "free-draft").fields) == 1

def test_generation_request_defaults_to_bilingual():
    assert ContractGenerationRequest(template_id="free-draft", answers={"instructions": "合同需求"}).language == "bilingual"
