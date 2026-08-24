from app.schemas import ReviewDepth

LABELS = {"standard": "标准审查", "deep": "深度审查"}

def depth_label(depth: ReviewDepth) -> str:
    return LABELS[depth]

def max_searches(depth: ReviewDepth) -> int:
    return 4 if depth == "deep" else 2

def review_temperature(depth: ReviewDepth, configured: float) -> float:
    return min(max(configured, 0.2), 0.3) if depth == "deep" else configured

def depth_guidance(depth: ReviewDepth) -> str:
    if depth == "deep":
        return "审查深度：深度审查。除核心商业条款外，逐项覆盖主体与签署权限、定义与附件、税费、价格调整、交付验收、质量瑕疵、责任上限、赔偿、保险、保密、数据、知识产权、不可抗力、变更、转让、解除、存续、通知送达、争议解决和双语优先；每轮 RAG 应检索不同主题，并列出待人工确认事项。"
    return "审查深度：标准审查。覆盖主体、金额、付款、交付、验收、违约、解约、保密、知识产权、适用法、争议解决和语言优先等核心事项。"
