from __future__ import annotations
import hashlib
import re
import uuid
from pathlib import Path
from typing import Literal
import yaml
from fastembed import TextEmbedding
from qdrant_client import QdrantClient, models
from app.schemas import KnowledgeChunk, KnowledgeSource, KnowledgeSourceUpdate

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "knowledge_sources" / "manifest.yaml"
QDRANT_PATH = ROOT / "data" / "qdrant"
COLLECTION = "contract_knowledge"

class KnowledgeBase:
    def __init__(self, manifest: Path = MANIFEST, path: Path = QDRANT_PATH):
        self.manifest, self.path = manifest, path
        self.local_sources_dir = self.path.parent / "knowledge_sources"
        self.local_manifest = self.local_sources_dir / "manifest.yaml"
        self._embedding: TextEmbedding | None = None

    @property
    def embedding(self) -> TextEmbedding:
        # E5 is multilingual and keeps Chinese/Japanese queries in one vector space.
        if self._embedding is None: self._embedding = TextEmbedding("intfloat/multilingual-e5-large")
        return self._embedding

    def _client(self) -> QdrantClient:
        self.path.mkdir(parents=True, exist_ok=True)
        return QdrantClient(path=str(self.path))

    @staticmethod
    def _load_manifest(path: Path) -> dict:
        return yaml.safe_load(path.read_text("utf-8")) if path.exists() else {"sources": []}

    def _manifest(self) -> dict:
        return self._load_manifest(self.manifest) or {"sources": []}

    def _sources(self) -> list[dict]:
        sources = []
        for manifest_path, uploaded in ((self.manifest, False), (self.local_manifest, True)):
            for source in self._load_manifest(manifest_path).get("sources", []):
                sources.append({**source, "_root": manifest_path.parent, "_uploaded": uploaded})
        return sources

    @staticmethod
    def _source_path(source: dict) -> Path:
        return Path(source["_root"]) / source["path"]

    @staticmethod
    def _preview(text: str) -> str:
        sentences = [part.strip() for part in re.split(r"(?<=[。！？.!?])\s*", text) if part.strip()]
        return " ".join(sentences[:2]) or text[:500]

    def _find_source(self, source_id: str) -> tuple[Path, dict, dict]:
        for manifest_path in (self.manifest, self.local_manifest):
            manifest = self._load_manifest(manifest_path)
            source = next((item for item in manifest.get("sources", []) if item["source_id"] == source_id), None)
            if source is not None: return manifest_path, manifest, source
        raise KeyError(source_id)

    def list_sources(self) -> list[KnowledgeSource]:
        sources = []
        for source in self._sources():
            content = self._source_path(source).read_text("utf-8")
            sources.append(KnowledgeSource.model_validate({**source, "enabled": source.get("enabled", True), "preview": self._preview(content), "content_length": len(content), "uploaded": source["_uploaded"], "can_delete": source["_uploaded"]}))
        return sources

    def update_source(self, source_id: str, update: KnowledgeSourceUpdate) -> None:
        manifest_path, manifest, source = self._find_source(source_id)
        source.update(update.model_dump(exclude_unset=True, exclude_none=True))
        manifest_path.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), "utf-8")

    def add_source(self, title: str, jurisdiction: str, source_url: str, effective_date: str, document_type: str, filename: str, text: str) -> KnowledgeSource:
        source_id = f"uploaded-{uuid.uuid4().hex[:12]}"
        files = self.local_sources_dir / "files"; files.mkdir(parents=True, exist_ok=True)
        path = files / f"{source_id}.txt"; path.write_text(text, "utf-8")
        manifest = self._load_manifest(self.local_manifest)
        manifest.setdefault("sources", []).append({"source_id": source_id, "title": title, "jurisdiction": jurisdiction, "source_url": source_url or f"local://{filename}", "effective_date": effective_date or "未提供", "document_type": document_type or "uploaded", "path": f"files/{path.name}", "enabled": True})
        self.local_sources_dir.mkdir(parents=True, exist_ok=True)
        self.local_manifest.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), "utf-8")
        return next(source for source in self.list_sources() if source.source_id == source_id)

    def delete_source(self, source_id: str) -> None:
        manifest_path, manifest, source = self._find_source(source_id)
        if manifest_path != self.local_manifest: raise PermissionError(source_id)
        source_path = manifest_path.parent / source["path"]
        manifest["sources"] = [item for item in manifest["sources"] if item["source_id"] != source_id]
        manifest_path.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), "utf-8")
        if source_path.exists(): source_path.unlink()

    def source_file(self, source_id: str) -> tuple[Path, str]:
        manifest_path, _, source = self._find_source(source_id)
        return manifest_path.parent / source["path"], source["title"]

    def _chunks(self) -> list[KnowledgeChunk]:
        chunks: list[KnowledgeChunk] = []
        for source in self._sources():
            if not source.get("enabled", True): continue
            text = self._source_path(source).read_text("utf-8")
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            current = ""
            for paragraph in paragraphs:
                if len(paragraph) > 1000:
                    if current:
                        chunks.append(self._make_chunk(source, len(chunks) + 1, current)); current = ""
                    for start in range(0, len(paragraph), 800):
                        part = paragraph[start:start + 900]
                        if part: chunks.append(self._make_chunk(source, len(chunks) + 1, part))
                    continue
                candidate = f"{current}\n\n{paragraph}".strip()
                if current and len(candidate) > 1000:
                    chunks.append(self._make_chunk(source, len(chunks) + 1, current))
                    current = f"{current[-100:]}\n\n{paragraph}"
                else:
                    current = candidate
            if current: chunks.append(self._make_chunk(source, len(chunks) + 1, current))
        return chunks

    def _make_chunk(self, source: dict, number: int, text: str) -> KnowledgeChunk:
        digest = hashlib.sha1(f"{source['source_id']}:{number}:{text}".encode()).hexdigest()[:12]
        return KnowledgeChunk(chunk_id=f"{source['source_id']}-{digest}", source_id=source["source_id"], title=source["title"], jurisdiction=source["jurisdiction"], section=text.splitlines()[0][:100], source_url=source["source_url"], text=text)

    def rebuild(self) -> dict:
        chunks = self._chunks(); client = self._client()
        if client.collection_exists(COLLECTION): client.delete_collection(COLLECTION)
        if not chunks:
            sources = self._sources()
            return {"sources": sum(source.get("enabled", True) for source in sources), "available_sources": len(sources), "chunks": 0, "ready": False}
        vectors = list(self.embedding.embed([c.text for c in chunks]))
        client.create_collection(COLLECTION, vectors_config=models.VectorParams(size=len(vectors[0]), distance=models.Distance.COSINE))
        client.upsert(COLLECTION, models.Batch(ids=list(range(len(chunks))), vectors=vectors, payloads=[c.model_dump() for c in chunks]))
        sources = self._sources()
        return {"sources": sum(source.get("enabled", True) for source in sources), "available_sources": len(sources), "chunks": len(chunks), "ready": True}

    def status(self) -> dict:
        sources = self._sources(); enabled = sum(source.get("enabled", True) for source in sources)
        if not self.path.exists(): return {"sources": enabled, "available_sources": len(sources), "chunks": 0, "ready": False}
        client = self._client()
        count = client.count(COLLECTION, exact=True).count if client.collection_exists(COLLECTION) else 0
        return {"sources": enabled, "available_sources": len(sources), "chunks": count, "ready": bool(count)}

    def search_knowledge(self, query: str, jurisdiction: Literal["CN", "JP", "CN-JP"], top_k: int = 5) -> list[KnowledgeChunk]:
        status = self.status()
        if not status["ready"]: self.rebuild()
        if not self.status()["ready"]: return []
        client = self._client(); vector = list(self.embedding.embed([query]))[0]
        # Retrieve the complete small collection before jurisdiction filtering, so a
        # high-scoring chunk from another jurisdiction does not hide valid evidence.
        points = client.query_points(COLLECTION, query=vector, limit=max(10, min(top_k * 4, 50))).points
        chunks = [KnowledgeChunk.model_validate(point.payload) for point in points]
        return [c for c in chunks if jurisdiction == "CN-JP" or c.jurisdiction in (jurisdiction, "CN-JP")][:top_k]
