from __future__ import annotations
import uuid
from datetime import datetime, timezone
from pathlib import Path
from app.contract_templates import get_template, validate_answers
from app.schemas import ContractGenerationRequest, ContractGenerationResponse, GeneratedContract

ROOT = Path(__file__).resolve().parents[1]

class ContractGenerationPipeline:
    def __init__(self, llm): self.llm = llm

    async def run(self, request: ContractGenerationRequest) -> ContractGenerationResponse:
        template = get_template(request.template_id)
        answers = validate_answers(template, request.answers)
        prompt = f"""你是严谨的中日跨境合同起草助手。基于下方经过结构化确认的交易信息起草完整合同草案。
不得编造未提供的商业事实；未提供且无法安全省略的信息，必须在对应条款中使用 [待确认] 占位符，并在 missing_information 中逐项列出。
合同模板：{template.label}。模板说明：{template.description}
参考来源：{template.source_title} {template.source_url or '无外部来源'}；版本：{template.version}。该来源只作为结构参考，不得声称已对具体交易作出法律意见。
模板专属规则：{template.instructions}
默认使用中日双语；每个条款必须先给出中文，再给出内容等效的日文，并保持条款编号、金额、期限、义务主体与例外条件一致。
document_markdown 只能包含完整合同正文，不要加入解释性前言。coverage 逐项说明关键条款已纳入或仍待确认。

已确认模板字段：
{answers}"""
        draft = await self.llm.structured(prompt, GeneratedContract)
        response = ContractGenerationResponse(generation_id=uuid.uuid4().hex, created_at=datetime.now(timezone.utc), request=ContractGenerationRequest(template_id=request.template_id, answers=answers),
            template_label=template.label, template_source_title=template.source_title, template_source_url=template.source_url, template_version=template.version,
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
    template = get_template(request.template_id)
    labels = {field.key: field.label for field in template.fields}
    lines = [f"# {result.title}\n", f"- 生成编号：`{response.generation_id}`", f"- 模板：{response.template_label}", f"- 模板版本：{response.template_version}", f"- 参考来源：{response.template_source_title} {response.template_source_url or ''}\n", "## 已确认交易信息"]
    for key, value in request.answers.items():
        label = labels.get(key, key)
        lines.append(f"- {label}：{value or '未提供'}")
    lines.extend(["\n## 起草假设", *assumptions, "\n## 待确认信息", *missing_information, "\n## 条款覆盖", *coverage])
    lines.extend(["\n## 完整合同草案", result.document_markdown])
    return "\n".join(lines) + "\n"
