from app.schemas import ReviewStance

LABELS = {"Auto": "自动判断", "buyer": "买方", "seller": "卖方", "neutral": "中立"}

def stance_label(stance: ReviewStance) -> str:
    return LABELS[stance]

def stance_guidance(stance: ReviewStance) -> str:
    if stance == "buyer":
        return "审查立场：我方为买方。优先识别付款、验收、质量、交付、知识产权、赔偿、解除和争议条款中对买方不利的安排；建议应保护买方。"
    if stance == "seller":
        return "审查立场：我方为卖方。优先识别付款保障、验收期限、责任上限、知识产权、交付、赔偿、解除和争议条款中对卖方不利的安排；建议应保护卖方。"
    if stance == "neutral":
        return "审查立场：中立。客观说明条款对双方的影响，不将任何一方视为我方。"
    return "审查立场：自动判断。根据合同角色与义务分配说明哪一方受益或承担风险；未能确认我方时不得假设任何一方为我方。"
