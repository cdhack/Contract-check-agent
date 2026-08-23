from __future__ import annotations
import json
from types import SimpleNamespace
from app.config import LLMSettings
from app.pipeline import ComparisonEnvelope
from app.schemas import ContractFacts, ReviewResult

class MockLLM:
    def __init__(self): self.settings = LLMSettings(api_key="mock") ; self.round = 0
    async def chat(self, prompt): return "Mock 回答：该条款应结合交付和验收标准进一步明确。"
    async def structured(self, prompt, schema):
        if schema is ContractFacts: return ContractFacts(title="中日双语采购合同", contract_type="采购", language="bilingual", amount="100,000", currency="CNY", payment_terms="交货后付款", governing_law="中华人民共和国法律", dispute_resolution="北京仲裁委员会", language_priority="中文优先", focus_topics=["付款", "语言优先"])
        if schema is ComparisonEnvelope: return ComparisonEnvelope.model_validate({"items":[{"chinese_location":"第2条","chinese_text":"交货后30日内付款","japanese_location":"第2条","japanese_text":"納品後60日以内に支払う","comparison_type":"numeric_conflict","explanation":"付款期限不一致","severity":"high","recommendation":"统一为明确期限"}]})
        if schema is ReviewResult: return ReviewResult(overall_summary="存在付款期限差异，建议人工复核。")
        return schema.model_validate({})
    async def tool_completion(self, messages, tools):
        self.round += 1
        if self.round == 1:
            call = SimpleNamespace(id="tool-1", function=SimpleNamespace(arguments=json.dumps({"query":"跨境采购合同付款期限和语言优先", "jurisdiction":"CN-JP", "top_k":3})))
            message = SimpleNamespace(tool_calls=[call], content=None, model_dump=lambda **kwargs: {"role":"assistant","tool_calls":[]})
        else:
            content = json.dumps({"issues":[{"title":"付款期限文本冲突","severity":"high","category":"payment","contract_location":"第2条","contract_excerpt":"30日 / 60日","issue":"中日文本付款期限不同","impact":"可能导致到期日争议","recommendation":"统一双语版本并明确付款起算日","suggested_clause":"付款期限为验收合格后30日。","basis_chunk_ids":[]}],"missing_clauses":["验收标准"],"overall_summary":"建议先解决高风险双语差异。"})
            message = SimpleNamespace(tool_calls=[], content=content, model_dump=lambda **kwargs: {"role":"assistant","content":content})
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])
