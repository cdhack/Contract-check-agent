from __future__ import annotations
import json
from json import JSONDecodeError
from pydantic import ValidationError
from app.schemas import ContractFacts, ComparisonItem, ReviewResult, ToolCallRecord
from app.knowledge import KnowledgeBase

TOOL = [{"type": "function", "function": {"name": "search_knowledge", "description": "检索本地可信合同法律资料。", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "jurisdiction": {"type": "string", "enum": ["CN", "JP", "CN-JP"]}, "top_k": {"type": "integer", "default": 5}}, "required": ["query", "jurisdiction"]}}}]

class ReviewAgent:
    def __init__(self, llm, knowledge: KnowledgeBase): self.llm, self.knowledge = llm, knowledge

    async def review(self, text: str, facts: ContractFacts, comparison: list[ComparisonItem], jurisdiction: str) -> tuple[ReviewResult, list[ToolCallRecord]]:
        prompt = f"""审查下列合同。你必须先至少调用一次 search_knowledge 获取依据，最多三轮；只引用工具真实返回的 chunk_id。完成后返回 JSON，格式为 {{\"issues\":[],\"missing_clauses\":[],\"overall_summary\":\"\"}}。\n合同事实：{facts.model_dump_json()}\n双语差异：{[x.model_dump() for x in comparison]}\n正文：{text[:30000]}"""
        messages = [{"role": "system", "content": "你是合同审查 Agent。仅基于工具返回的依据引用 chunk_id。"}, {"role": "user", "content": prompt}]
        records: list[ToolCallRecord] = []
        for _ in range(self.llm.settings.max_tool_rounds):
            response = await self.llm.tool_completion(messages, TOOL); message = response.choices[0].message
            calls = message.tool_calls or []
            if not calls:
                if not records and _ < self.llm.settings.max_tool_rounds - 1:
                    messages.extend([{"role": "assistant", "content": message.content or ""}, {"role": "user", "content": "在输出审查结论前必须调用一次 search_knowledge，并根据返回片段填写真实 chunk_id。"}])
                    continue
                if not records:
                    fallback_jurisdiction = jurisdiction if jurisdiction in {"CN", "JP", "CN-JP"} else "CN-JP"
                    fallback_query = "合同审查 " + "；".join(filter(None, [facts.contract_type, facts.governing_law, *facts.focus_topics]))
                    chunks = self.knowledge.search_knowledge(fallback_query or "合同审查关键条款", fallback_jurisdiction, 5)
                    records.append(ToolCallRecord(query=fallback_query or "合同审查关键条款", jurisdiction=fallback_jurisdiction, results=chunks))
                try:
                    result = ReviewResult.model_validate(json.loads(message.content or "{}"))
                except (JSONDecodeError, ValidationError):
                    result = await self.llm.structured(
                        "将以下 Agent 最终输出修正为 ReviewResult JSON。只保留已有检索记录中真实存在的 chunk_id；若依据不足则 basis_chunk_ids 为空。\n"
                        f"检索记录：{json.dumps([record.model_dump() for record in records], ensure_ascii=False)}\n"
                        f"原输出：{message.content or '（空）'}",
                        ReviewResult,
                    )
                self._validate_references(result, records); return result, records
            messages.append(message.model_dump(exclude_none=True))
            for call in calls:
                args = json.loads(call.function.arguments); jurisdiction_arg = args.get("jurisdiction", jurisdiction if jurisdiction in {"CN", "JP", "CN-JP"} else "CN-JP")
                chunks = self.knowledge.search_knowledge(args["query"], jurisdiction_arg, args.get("top_k", 5)); records.append(ToolCallRecord(query=args["query"], jurisdiction=jurisdiction_arg, results=chunks))
                messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps([x.model_dump() for x in chunks], ensure_ascii=False)})
        messages.append({"role": "user", "content": "工具轮次已达上限。现在仅输出最终 JSON。"})
        result = await self.llm.structured("基于以下 Agent 对话输出最终审查 JSON：\n" + json.dumps(messages, ensure_ascii=False, default=str), ReviewResult)
        self._validate_references(result, records); return result, records

    @staticmethod
    def _validate_references(result: ReviewResult, records: list[ToolCallRecord]) -> None:
        valid = {chunk.chunk_id for record in records for chunk in record.results}
        for issue in result.issues: issue.basis_chunk_ids = [item for item in issue.basis_chunk_ids if item in valid]
