from __future__ import annotations
import json
import re
from typing import Any, TypeVar
from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError
from app.config import LLMSettings

T = TypeVar("T", bound=BaseModel)

SYSTEM = "你是严谨的中日跨境合同审查助手。无法确认时必须明确说明，不得编造事实或法律依据。"

def _json(text: str) -> Any:
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    return json.loads(match.group(1) if match else text)

class LLMClient:
    def __init__(self, settings: LLMSettings):
        self.settings = settings
        self.client = AsyncOpenAI(api_key=settings.api_key, base_url=settings.base_url)

    async def chat(self, prompt: str) -> str:
        response = await self.client.chat.completions.create(model=self.settings.model, temperature=self.settings.temperature,
            messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}])
        return response.choices[0].message.content or ""

    async def structured(self, prompt: str, schema: type[T], temperature: float | None = None) -> T:
        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        messages = [
            {"role": "system", "content": SYSTEM + " 仅输出合法 JSON，不要输出 Markdown、解释或 Schema 中未定义的结构。"},
            {"role": "user", "content": f"{prompt}\n\n必须严格符合以下 JSON Schema。字段类型不确定时使用 null、空字符串或空数组，不得改为嵌套对象：\n{schema_json}"},
        ]
        for attempt in range(2):
            response = await self.client.chat.completions.create(model=self.settings.model, temperature=self.settings.temperature if temperature is None else temperature,
                response_format={"type": "json_object"}, messages=messages)
            content = response.choices[0].message.content or "{}"
            try:
                return schema.model_validate(_json(content))
            except (ValidationError, ValueError) as exc:
                if attempt:
                    raise ValueError(f"LLM 返回内容不符合 {schema.__name__} 结构，已自动重试一次：{exc}") from exc
                messages.append({"role": "assistant", "content": content})
                messages.append({"role": "user", "content": f"上一个 JSON 未通过 {schema.__name__} 校验：{exc}。请仅输出已修正的完整 JSON，严格使用给定 Schema；不要保留不符合类型的嵌套对象。"})

    async def tool_completion(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]], temperature: float | None = None) -> Any:
        return await self.client.chat.completions.create(model=self.settings.model, temperature=self.settings.temperature if temperature is None else temperature, messages=messages, tools=tools, tool_choice="auto")

    async def test(self) -> str:
        return await self.chat("仅回复 OK")
