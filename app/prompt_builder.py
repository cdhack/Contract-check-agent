from app.schemas import AskSelectionRequest, ContractFacts

TASKS = {"explain": "解释这段条款", "risk": "分析对我方可能存在的风险", "rewrite": "改写得更清晰或更有利", "compare": "对比中日文含义", "negotiate": "生成谈判意见或替代条款", "custom": "回答用户问题"}

def selection_prompt(request: AskSelectionRequest, facts: ContractFacts) -> str:
    goal = request.question if request.task == "custom" else TASKS.get(request.task, request.task)
    return f"""你是中日跨境合同审查助手。仅提供初步商业和法律风险提示，不替代律师。
合同背景：名称={facts.title or '未确认'}；类型={facts.contract_type or '未确认'}；适用法={facts.governing_law or '未确认'}；审查法域={request.jurisdiction}。
选中的合同文字：
---
{request.selected_text}
---
用户目标：{goal or '解释选中内容'}
请使用与选中文字相同的主要语言回答；说明不确定之处，给出清晰、可执行的建议。"""
