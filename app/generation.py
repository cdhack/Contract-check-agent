from __future__ import annotations
import uuid
from datetime import datetime, timezone
from pathlib import Path
from app.schemas import ContractGenerationRequest, ContractGenerationResponse, GeneratedContract

ROOT = Path(__file__).resolve().parents[1]

class ContractGenerationPipeline:
    def __init__(self, llm): self.llm = llm

    async def run(self, request: ContractGenerationRequest) -> ContractGenerationResponse:
        prompt = f"""你是严谨的中日跨境合同起草助手。基于下方经过结构化确认的交易信息起草完整合同草案。
不得编造未提供的商业事实；未提供且无法安全省略的信息，必须在对应条款中使用 [待确认] 占位符，并在 missing_information 中逐项列出。
合同应至少覆盖：定义与主体、标的与范围、价格与付款、交付或履行、验收、期限与解除、保密、知识产权、陈述保证、违约与赔偿、责任限制、不可抗力、通知、适用法律与争议解决。
起草立场为 {request.drafting_position}；仅在不改变已确认事实的范围内调整保护强度。
语言为 {request.language}。若为 bilingual，每个条款必须先给出中文，再给出内容等效的日文，并保持条款编号、金额、期限、义务主体与例外条件一致。
document_markdown 只能包含完整合同正文，不要加入解释性前言。coverage 逐项说明关键条款已纳入或仍待确认。

结构化交易信息：
{request.model_dump_json(indent=2)}"""
        draft = await self.llm.structured(prompt, GeneratedContract)
        response = ContractGenerationResponse(generation_id=uuid.uuid4().hex, created_at=datetime.now(timezone.utc), request=request,
            result=draft, model=self.llm.settings.model, report_markdown="")
        response.report_markdown = render_generation_report(response)
        self.save(response)
        return response

    def save(self, response: ContractGenerationResponse) -> None:
        directory = ROOT / "data" / "generations"; directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{response.generation_id}.json").write_text(response.model_dump_json(indent=2), "utf-8")
        (directory / f"{response.generation_id}.md").write_text(response.report_markdown, "utf-8")

def render_generation_report(response: ContractGenerationResponse) -> str:
    request, result = response.request, response.result
    assumptions = [f"- {item}" for item in result.assumptions] or ["- 无"]
    missing_information = [f"- {item}" for item in result.missing_information] or ["- 无"]
    coverage = [f"- {'已纳入' if item.status == 'included' else '待确认'}：{item.clause} - {item.note}" for item in result.coverage] or ["- 未提供"]
    lines = [f"# {result.title}\n", f"- 生成编号：`{response.generation_id}`", f"- 合同类型：{request.contract_type}", f"- 法域：{request.jurisdiction}", f"- 语言：{request.language}", f"- 起草立场：{request.drafting_position}\n", "## 已确认交易信息"]
    for label, value in [("甲方", f"{request.party_a_name}（{request.party_a_role}）"), ("乙方", f"{request.party_b_name}（{request.party_b_role}）"), ("标的与范围", request.scope), ("价格", request.price), ("付款", request.payment_terms), ("交付或履行", request.delivery_terms), ("验收", request.acceptance_terms), ("期限", request.term), ("争议解决", request.dispute_resolution)]:
        lines.append(f"- {label}：{value or '未提供'}")
    lines.extend(["\n## 起草假设", *assumptions, "\n## 待确认信息", *missing_information, "\n## 条款覆盖", *coverage])
    lines.extend(["\n## 完整合同草案", result.document_markdown])
    return "\n".join(lines) + "\n"
