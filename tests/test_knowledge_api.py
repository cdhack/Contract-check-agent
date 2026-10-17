from fastapi.testclient import TestClient
from app.knowledge import KnowledgeBase

def test_upload_download_and_delete_knowledge_source(tmp_path, monkeypatch):
    import app.main as main_module
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text("sources: []\n", "utf-8")
    knowledge = KnowledgeBase(manifest=manifest, path=tmp_path / "qdrant")
    monkeypatch.setattr(main_module, "KnowledgeBase", lambda: knowledge)
    with TestClient(main_module.app) as client:
        assert client.post("/api/access/login", json={"employee_id": "1"}).status_code == 200
        created = client.post("/api/knowledge/sources", data={"title": "上传资料", "jurisdiction": "CN", "document_type": "reference"}, files={"file": ("source.txt", "第一句。第二句。第三句。", "text/plain")})
        source_id = created.json()["source_id"]
        downloaded = client.get(f"/api/knowledge/sources/{source_id}/download")
        deleted = client.delete(f"/api/knowledge/sources/{source_id}")
    assert created.status_code == 200
    assert created.json()["preview"] == "第一句。 第二句。"
    assert downloaded.status_code == 200
    assert "第三句" in downloaded.text
    assert deleted.status_code == 200
    assert knowledge.list_sources() == []
