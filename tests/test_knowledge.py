from pathlib import Path
from app.knowledge import KnowledgeBase
from app.schemas import KnowledgeSourceUpdate

def test_chunking_reads_all_manifest_sources(tmp_path):
    kb = KnowledgeBase(path=tmp_path / "qdrant")
    chunks = kb._chunks()
    assert len(chunks) >= 30
    assert {x.jurisdiction for x in chunks} >= {"CN", "JP", "CN-JP"}

def test_source_configuration_can_disable_a_document(tmp_path):
    document = tmp_path / "source.txt"
    manifest = tmp_path / "manifest.yaml"
    document.write_text("# 资料\n\n合同条款内容。", "utf-8")
    manifest.write_text("""sources:
  - source_id: source
    title: 测试资料
    jurisdiction: CN
    source_url: https://example.com/source
    effective_date: '2026-01-01'
    document_type: law
    path: source.txt
    enabled: true
""", "utf-8")
    kb = KnowledgeBase(manifest=manifest, path=tmp_path / "qdrant")
    assert kb.list_sources()[0].enabled
    kb.update_source("source", KnowledgeSourceUpdate(enabled=False))
    assert not kb.list_sources()[0].enabled
    assert kb._chunks() == []

def test_uploaded_source_can_be_added_downloaded_and_deleted(tmp_path):
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text("sources: []\n", "utf-8")
    kb = KnowledgeBase(manifest=manifest, path=tmp_path / "qdrant")
    source = kb.add_source("自定义资料", "CN-JP", "", "2026-01-01", "reference", "source.txt", "第一句。第二句。第三句。")
    assert source.uploaded and source.can_delete
    assert source.preview == "第一句。 第二句。"
    path, _ = kb.source_file(source.source_id)
    assert path.exists()
    assert kb._chunks()
    kb.delete_source(source.source_id)
    assert not path.exists()
    assert not kb.list_sources()
