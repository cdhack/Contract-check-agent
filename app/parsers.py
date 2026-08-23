from __future__ import annotations
from io import BytesIO
from pathlib import Path
import fitz
from docx import Document
from app.schemas import ParsedContract

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
MAX_FILE_SIZE = 10 * 1024 * 1024

class ParseError(ValueError): pass

def parse_contract(filename: str, content: bytes) -> ParsedContract:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS: raise ParseError("仅支持 PDF、DOCX 和 TXT 文件")
    if not content: raise ParseError("上传文件为空")
    if len(content) > MAX_FILE_SIZE: raise ParseError("文件超过 10MB 限制")
    try:
        if suffix == ".txt":
            text = content.decode("utf-8-sig")
            locations = [f"第 {i} 行" for i, _ in enumerate(text.splitlines(), 1)]
        elif suffix == ".docx":
            document = Document(BytesIO(content)); paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
            text = "\n".join(f"[段落 {i}] {p}" for i, p in enumerate(paragraphs, 1)); locations = [f"段落 {i}" for i in range(1, len(paragraphs)+1)]
        else:
            document = fitz.open(stream=content, filetype="pdf"); pages = [p.get_text().strip() for p in document]
            text = "\n".join(f"[第 {i} 页]\n{p}" for i, p in enumerate(pages, 1) if p); locations = [f"第 {i} 页" for i, p in enumerate(pages, 1) if p]
    except Exception as exc: raise ParseError(f"文件解析失败：{exc}") from exc
    if not text.strip(): raise ParseError("未提取到文字；扫描件暂不支持 OCR")
    return ParsedContract(filename=filename, text=text, locations=locations)
