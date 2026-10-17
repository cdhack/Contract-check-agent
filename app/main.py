from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from app.config import LLMSettings, get_settings, save_settings
from app.knowledge import KnowledgeBase
from app.llm_client import LLMClient
from app.parsers import ParseError, parse_contract
from app.contract_templates import list_templates
from app.generation import ContractGenerationPipeline
from app.pipeline import ReviewPipeline
from app.prompt_builder import selection_prompt
from app.schemas import AskSelectionRequest, AskSelectionResponse, ContractGenerationRequest, ContractGenerationResponse, GenerationHistoryItem, KnowledgeSourceUpdate, ParsedContract, ReviewDepth, ReviewHistoryItem, ReviewResponse, ReviewStance, VerificationResult, VerifyRequest, VerifyResponse

ROOT = Path(__file__).resolve().parents[1]; REPORTS = ROOT / "data" / "reports"; GENERATIONS = ROOT / "data" / "generations"
app = FastAPI(title="contract-check-agent")
app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")
templates = Jinja2Templates(directory=ROOT / "app" / "templates")

def load_review(review_id: str) -> ReviewResponse:
    path = REPORTS / f"{review_id}.json"
    if not path.exists(): raise HTTPException(404, "审查报告不存在")
    return ReviewResponse.model_validate_json(path.read_text("utf-8"))

def review_history() -> list[ReviewHistoryItem]:
    if not REPORTS.exists(): return []
    items = []
    for path in REPORTS.glob("*.json"):
        try:
            stored = ReviewResponse.model_validate_json(path.read_text("utf-8"))
            created_at = stored.created_at or datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
            items.append(ReviewHistoryItem(review_id=stored.review_id, created_at=created_at, filename=stored.contract.filename,
                title=stored.facts.title, language=stored.facts.language, stance=stored.stance, depth=stored.depth, issue_count=len(stored.review.issues),
                high_risk_count=sum(issue.severity == "high" for issue in stored.review.issues)))
        except (OSError, ValueError):
            continue
    return sorted(items, key=lambda item: item.created_at, reverse=True)

def delete_review(review_id: str) -> None:
    paths = [REPORTS / f"{review_id}.json", REPORTS / f"{review_id}.md"]
    if not any(path.exists() for path in paths): raise FileNotFoundError(review_id)
    for path in paths:
        if path.exists(): path.unlink()

def load_generation(generation_id: str) -> ContractGenerationResponse:
    path = GENERATIONS / f"{generation_id}.json"
    if not path.exists(): raise HTTPException(404, "合同草案不存在")
    return ContractGenerationResponse.model_validate_json(path.read_text("utf-8"))

def generation_history() -> list[GenerationHistoryItem]:
    if not GENERATIONS.exists(): return []
    items = []
    for path in GENERATIONS.glob("*.json"):
        try:
            stored = ContractGenerationResponse.model_validate_json(path.read_text("utf-8"))
            items.append(GenerationHistoryItem(generation_id=stored.generation_id, created_at=stored.created_at, title=stored.result.title,
                template_label=stored.template_label, missing_information_count=len(stored.result.missing_information)))
        except (OSError, ValueError):
            continue
    return sorted(items, key=lambda item: item.created_at, reverse=True)

def delete_generation(generation_id: str) -> None:
    paths = [GENERATIONS / f"{generation_id}.json", GENERATIONS / f"{generation_id}.md"]
    if not any(path.exists() for path in paths): raise FileNotFoundError(generation_id)
    for path in paths:
        if path.exists(): path.unlink()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request): return templates.TemplateResponse(request, "index.html")

@app.get("/knowledge", response_class=HTMLResponse)
async def knowledge_page(request: Request): return templates.TemplateResponse(request, "knowledge.html")

@app.get("/api/settings")
async def settings():
    current = get_settings().model_dump(); current["api_key"] = "" if not current["api_key"] else "********"
    return current

@app.put("/api/settings")
async def update_settings(settings: LLMSettings):
    old = get_settings()
    if settings.api_key == "********": settings.api_key = old.api_key
    save_settings(settings); return {**settings.model_dump(), "api_key": "" if not settings.api_key else "********"}

@app.post("/api/settings/test")
async def test_settings(settings: LLMSettings):
    if not settings.api_key or settings.api_key == "********": raise HTTPException(400, "请提供 API Key")
    try: return {"ok": True, "message": await LLMClient(settings).test()}
    except Exception as exc: raise HTTPException(502, f"连接失败：{exc}") from exc

@app.get("/api/knowledge/status")
async def knowledge_status(): return KnowledgeBase().status()

@app.get("/api/knowledge/sources")
async def knowledge_sources(): return KnowledgeBase().list_sources()

@app.post("/api/knowledge/sources")
async def upload_knowledge_source(file: UploadFile = File(...), title: str = Form(...), jurisdiction: str = Form(...), source_url: str = Form(""), effective_date: str = Form(""), document_type: str = Form("uploaded")):
    if jurisdiction not in {"CN", "JP", "CN-JP"}: raise HTTPException(400, "法域必须为 CN、JP 或 CN-JP")
    if not file.filename: raise HTTPException(400, "请选择知识库资料")
    try:
        parsed = parse_contract(file.filename, await file.read())
        return KnowledgeBase().add_source(title=title, jurisdiction=jurisdiction, source_url=source_url, effective_date=effective_date, document_type=document_type, filename=file.filename, text=parsed.text)
    except ParseError as exc: raise HTTPException(400, str(exc)) from exc

@app.get("/api/knowledge/sources/{source_id}/download")
async def download_knowledge_source(source_id: str):
    try:
        path, title = KnowledgeBase().source_file(source_id)
        if not path.exists(): raise HTTPException(404, "知识资料文件不存在")
        return FileResponse(path, filename=f"{title}.txt")
    except KeyError as exc: raise HTTPException(404, "知识资料不存在") from exc

@app.put("/api/knowledge/sources/{source_id}")
async def update_knowledge_source(source_id: str, update: KnowledgeSourceUpdate):
    try:
        KnowledgeBase().update_source(source_id, update)
        return {"ok": True, "message": "资料配置已保存，请重建知识库使其生效。"}
    except KeyError as exc: raise HTTPException(404, "知识资料不存在") from exc

@app.delete("/api/knowledge/sources/{source_id}")
async def delete_knowledge_source(source_id: str):
    try:
        KnowledgeBase().delete_source(source_id)
        return {"ok": True, "message": "已删除上传的知识资料，请重建知识库使其生效。"}
    except KeyError as exc: raise HTTPException(404, "知识资料不存在") from exc
    except PermissionError as exc: raise HTTPException(400, "内置资料不能删除，可将其停用") from exc

@app.post("/api/knowledge/rebuild")
async def rebuild_knowledge():
    try: return KnowledgeBase().rebuild()
    except Exception as exc: raise HTTPException(500, f"知识库重建失败：{exc}") from exc

@app.post("/api/review")
async def review(file: UploadFile = File(...), jurisdiction: str = Form("Auto"), stance: ReviewStance = Form("Auto"), depth: ReviewDepth = Form("standard")):
    if not file.filename: raise HTTPException(400, "请选择合同文件")
    try: contract = parse_contract(file.filename, await file.read()); result = await ReviewPipeline(LLMClient(get_settings()), KnowledgeBase()).run(contract, jurisdiction, stance, depth); return result
    except ParseError as exc: raise HTTPException(400, str(exc)) from exc
    except Exception as exc: raise HTTPException(500, f"审查失败：{exc}") from exc

@app.get("/api/reviews", response_model=list[ReviewHistoryItem])
async def list_reviews(): return review_history()

@app.get("/api/reviews/{review_id}", response_model=ReviewResponse)
async def get_review(review_id: str): return load_review(review_id)

@app.delete("/api/reviews/{review_id}")
async def remove_review(review_id: str):
    try:
        delete_review(review_id)
        return {"ok": True, "message": "审查记录已删除。"}
    except FileNotFoundError as exc: raise HTTPException(404, "审查记录不存在") from exc

@app.post("/api/generations", response_model=ContractGenerationResponse)
async def generate_contract(body: ContractGenerationRequest):
    try: return await ContractGenerationPipeline(LLMClient(get_settings())).run(body)
    except (KeyError, ValueError) as exc: raise HTTPException(422, str(exc)) from exc
    except Exception as exc: raise HTTPException(500, f"合同生成失败：{exc}") from exc

@app.get("/api/generation-templates")
async def generation_templates(): return list_templates()

@app.get("/api/generations", response_model=list[GenerationHistoryItem])
async def list_generations(): return generation_history()

@app.get("/api/generations/{generation_id}", response_model=ContractGenerationResponse)
async def get_generation(generation_id: str): return load_generation(generation_id)

@app.delete("/api/generations/{generation_id}")
async def remove_generation(generation_id: str):
    try:
        delete_generation(generation_id)
        return {"ok": True, "message": "生成记录已删除。"}
    except FileNotFoundError as exc: raise HTTPException(404, "生成记录不存在") from exc

@app.post("/api/generations/{generation_id}/review", response_model=ReviewResponse)
async def review_generated_contract(generation_id: str):
    generated = load_generation(generation_id)
    contract = ParsedContract(filename=f"{generated.result.title}.md", text=generated.result.document_markdown)
    try: return await ReviewPipeline(LLMClient(get_settings()), KnowledgeBase()).run(contract, "CN-JP", "neutral", "standard")
    except Exception as exc: raise HTTPException(500, f"草案审查失败：{exc}") from exc

@app.post("/api/verify", response_model=VerifyResponse)
async def verify(body: VerifyRequest):
    prompt = f"""你是中日跨境合同与商业文本核实助手。直接核实用户输入；事实或法律依据不足时明确说明。
conclusion 用一至两句话直接回答；basis 和 recommendations 各不超过三项；suggested_text 仅在用户要求改写或条款时填写，否则为 null。除非用户明确要求完整条款，全文控制在 700 个汉字以内。

用户输入：
{body.prompt}"""
    client = LLMClient(get_settings())
    return VerifyResponse(prompt=body.prompt, result=await client.structured(prompt, VerificationResult))

@app.post("/api/ask-selection", response_model=AskSelectionResponse)
async def ask_selection(body: AskSelectionRequest):
    stored = load_review(body.review_id); prompt = selection_prompt(body, stored.facts)
    answer = await LLMClient(get_settings()).chat(prompt)
    return AskSelectionResponse(selected_text=body.selected_text, task=body.task, answer=answer, model=get_settings().model, prompt=prompt)

@app.get("/api/reports/{review_id}.{format}")
async def download(review_id: str, format: str):
    if format not in {"md", "json"}: raise HTTPException(404)
    path = REPORTS / f"{review_id}.{format}"
    if not path.exists(): raise HTTPException(404, "报告不存在")
    return FileResponse(path, filename=path.name)

@app.get("/api/generations/{generation_id}/download/{format}")
async def download_generation(generation_id: str, format: str):
    if format not in {"md", "json"}: raise HTTPException(404)
    path = GENERATIONS / f"{generation_id}.{format}"
    if not path.exists(): raise HTTPException(404, "合同草案不存在")
    return FileResponse(path, filename=path.name)
