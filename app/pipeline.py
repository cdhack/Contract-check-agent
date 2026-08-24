from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
import markdown
from pydantic import BaseModel
from app.agent import ReviewAgent
from app.depth import depth_guidance, depth_label, review_temperature, tool_rounds
from app.schemas import ComparisonItem, ContractFacts, ParsedContract, ReviewDepth, ReviewResponse, ReviewStance
from app.stance import stance_guidance, stance_label

ROOT = Path(__file__).resolve().parents[1]

class ReviewPipeline:
    def __init__(self, llm, knowledge): self.llm, self.knowledge = llm, knowledge

    async def run(self, contract: ParsedContract, jurisdiction: str, stance: ReviewStance = "Auto", depth: ReviewDepth = "standard") -> ReviewResponse:
        facts = await self.llm.structured(f"从合同中提取结构化事实。未知字段为 null，不能猜测。输出 ContractFacts JSON。\n{contract.text[:30000]}", ContractFacts, temperature=0.1)
        bilingual = facts.language == "bilingual" or (any("\u4e00" <= c <= "\u9fff" for c in contract.text) and any("\u3040" <= c <= "\u30ff" for c in contract.text))
        review_temp = review_temperature(depth, self.llm.settings.temperature)
        envelope = None if not bilingual else await self.llm.structured(f"比较以下中日双语合同，输出 {{\"items\": [ComparisonItem]}} JSON；没有差异可为空。\n{stance_guidance(stance)}\n{depth_guidance(depth)}\n每项必须填写 stance_assessment（对当前立场不利、不利以外的有利/中性/无法判断）和 stance_reason。\n{contract.text[:30000]}", ComparisonEnvelope, temperature=review_temp)
        comparison = [] if envelope is None else envelope.items
        review, calls = await ReviewAgent(self.llm, self.knowledge).review(contract.text, facts, comparison, jurisdiction, stance, depth, tool_rounds(depth), review_temp)
        response = ReviewResponse(review_id=uuid.uuid4().hex, created_at=datetime.now(timezone.utc), stance=stance, depth=depth, contract=contract, facts=facts, comparison=comparison, comparison_skipped=not bilingual, tool_calls=calls, review=review, report_markdown="")
        response.report_markdown = render_report(response)
        self.save(response); return response

    def save(self, response: ReviewResponse) -> None:
        directory = ROOT / "data" / "reports"; directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{response.review_id}.json").write_text(response.model_dump_json(indent=2), "utf-8")
        (directory / f"{response.review_id}.md").write_text(response.report_markdown, "utf-8")

class ComparisonEnvelope(BaseModel):
    items: list[ComparisonItem] = []

def render_report(response: ReviewResponse) -> str:
    facts = response.facts
    lines = [f"# 合同审查报告\n", f"- 审查编号：`{response.review_id}`", f"- 合同：{facts.title or response.contract.filename}", f"- 类型：{facts.contract_type or '未确认'}", f"- 语言：{facts.language}", f"- 审查立场：{stance_label(response.stance)}", f"- 审查深度：{depth_label(response.depth)}\n", "## 关键商业条款"]
    for label, value in [("合同主体", "；".join(filter(None, [f"{p.name or '未确认'}（{p.role or '角色未确认'}）" for p in facts.parties]))), ("金额", facts.amount), ("付款", facts.payment_terms), ("适用法律", facts.governing_law), ("争议解决", facts.dispute_resolution)]: lines.append(f"- {label}：{value or '未确认'}")
    lines.append("\n## 中日双语差异")
    lines.append("单语合同，已跳过双语比较。" if response.comparison_skipped else ("\n".join(f"- **{x.severity}** {x.explanation}：{x.recommendation}（立场评价：{x.stance_assessment} {x.stance_reason}）" for x in response.comparison) or "未发现明确差异。"))
    lines.append("\n## 风险事项")
    for issue in response.review.issues: lines.extend([f"### [{issue.severity.upper()}] {issue.title}", f"- 位置：{issue.contract_location}", f"- 问题：{issue.issue}", f"- 影响：{issue.impact}", f"- 立场评价：{issue.stance_assessment} {issue.stance_reason}", f"- 建议：{issue.recommendation}", f"- 建议条款：{issue.suggested_clause or '无'}", f"- 依据：{', '.join(issue.basis_chunk_ids) or '未检索到充分依据'}"])
    missing = [f"- {item}" for item in response.review.missing_clauses] or ["- 未识别"]
    lines.extend(["\n## 缺失或不完整条款", *missing, "\n## 审查结论", response.review.overall_summary or "未提供结论。", "\n## 引用依据"])
    cited = {identifier for issue in response.review.issues for identifier in issue.basis_chunk_ids}
    for call in response.tool_calls:
        for chunk in call.results:
            if chunk.chunk_id in cited: lines.append(f"- `{chunk.chunk_id}` [{chunk.title}]({chunk.source_url})：{chunk.text[:300]}")
    return "\n".join(lines) + "\n"

def report_html(markdown_text: str) -> str: return markdown.markdown(markdown_text, extensions=["tables"])
