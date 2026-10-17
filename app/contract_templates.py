from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class TemplateField:
    key: str
    label: str
    placeholder: str
    required: bool = True
    field_type: str = "textarea"
    options: tuple[tuple[str, str], ...] = ()

    def public(self) -> dict:
        return {"key": self.key, "label": self.label, "placeholder": self.placeholder, "required": self.required, "field_type": self.field_type,
            "options": [{"value": value, "label": label} for value, label in self.options]}

@dataclass(frozen=True)
class ContractTemplate:
    template_id: str
    label: str
    description: str
    source_title: str
    source_url: str
    version: str
    instructions: str
    fields: tuple[TemplateField, ...]

    def public(self) -> dict:
        return {"template_id": self.template_id, "label": self.label, "description": self.description, "source_title": self.source_title,
            "source_url": self.source_url, "version": self.version, "fields": [field.public() for field in self.fields]}

MLIT_HOUSING = "国土交通省 住宅・不動産関連資料"
MLIT_HOUSING_URL = "https://www.mlit.go.jp/jutakukentiku/house/"
MLIT_REAL_ESTATE = "国土交通省 不動産業関連資料"
MLIT_REAL_ESTATE_URL = "https://www.mlit.go.jp/totikensangyo/const/"

TEMPLATES = (
    ContractTemplate("jp-housing-lease", "日本房屋租赁合同", "参考日本住宅租赁标准契约结构的中日双语草案。", MLIT_HOUSING, MLIT_HOUSING_URL, "2026-10",
        "按日本住宅租赁的常见结构起草，明确租赁标的、用途、费用、修缮、解除、返还和保证安排。不得将参考来源表述为对具体交易的法律意见。",
        (TemplateField("property", "房屋与用途", "地址、房号、面积、用途、允许居住人数"), TemplateField("term", "租期与续约", "起租日、期限、续约、解约通知期限"), TemplateField("rent", "租金与初始费用", "月租、管理费、押金、礼金、付款日"), TemplateField("parties", "出租方、承租方与担保", "双方名称、担保公司或保证人、管理公司"), TemplateField("special", "特别约定", "宠物、转租、修缮、家具设备等"))),
    ContractTemplate("jp-real-estate-sale", "日本不动产买卖合同", "参考日本不动产交易常见结构的中日双语草案。", MLIT_REAL_ESTATE, MLIT_REAL_ESTATE_URL, "2026-10",
        "按日本不动产交易常见结构起草，明确标的、权属、价款、融资、交付、设备状况、瑕疵及税费。提示用户另行完成重要事项说明和专业审阅。",
        (TemplateField("property", "不动产与权属", "土地/建筑物地址、登记信息、共有/抵押/租赁负担"), TemplateField("price", "价格与付款", "总价、定金、余款、付款日期与账户"), TemplateField("handover", "交付与设备状况", "交付日、钥匙、设备清单、现状、修缮"), TemplateField("parties", "交易双方与融资", "买卖方信息、中介、融资条件、贷款解除条件"), TemplateField("special", "税费与特别约定", "税费负担、违约、解除、其他约定"))),
    ContractTemplate("digital-asset-settlement", "公司间 USDT/CNY 兑换与结算协议", "用于公司主体间数字资产兑换和结算安排的草案。", "企业内部合规与商业条款结构", "", "2026-10",
        "仅起草公司间商业安排；必须加入主体授权、资产与资金来源声明、KYC/AML、制裁筛查、合法结算前提、暂停和解除条款。不得提供规避监管、规避外汇限制或隐匿交易的设计。",
        (TemplateField("parties", "双方主体与授权", "公司名称、注册地、签署人及授权文件"), TemplateField("asset", "兑换资产与价格", "USDT 数量、CNY 金额、汇率/定价时间、网络"), TemplateField("settlement", "结算安排", "付款与交割顺序、钱包地址、到账确认、时间"), TemplateField("compliance", "来源与合规确认", "资金/资产来源、KYC 资料、内部审批、限制条件"), TemplateField("special", "风险与特别约定", "波动、链上风险、违约、争议解决"))),
    ContractTemplate("it-company-cooperation", "赴日 IT 公司合作合同", "人材介绍或劳务派遣模式下与日本 IT 公司的合作草案。", "日本厚生劳动省 外国人雇用与人材服务相关资料", "https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/koyou_roudou/koyou/gaikokujin/", "2026-10",
        "根据合作模式分别起草人材介绍或劳务派遣条款；不得混用两种模式的费用、指挥命令和雇主责任。必须明确签证协助边界、费用、候选人信息和替换安排。",
        (TemplateField("mode", "合作模式", "", field_type="select", options=(("recruitment", "人材介绍"), ("dispatch", "劳务派遣"))), TemplateField("parties", "双方与目标人员", "双方公司、目标岗位、人数、技能要求"), TemplateField("services", "服务与签证协助", "招聘/派遣范围、签证材料协助、双方责任边界"), TemplateField("fees", "费用与支付", "介绍费或派遣费、发票、替换、取消费用"), TemplateField("work", "工作条件与特别约定", "工作地点、开始日、工时、保密、争议解决"))),
    ContractTemplate("it-worker-contract", "赴日 IT 员工合同", "直接雇佣或派遣雇佣模式下与员工的中日双语草案。", "日本厚生劳动省 外国人雇用与劳动条件相关资料", "https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/koyou_roudou/koyou/gaikokujin/", "2026-10",
        "根据雇佣模式分别起草直接雇佣或派遣雇佣条款，明确雇主、工作条件、签证协助边界、工资、社会保险和解除条件。不得将签证批准作出绝对保证。",
        (TemplateField("mode", "雇佣模式", "", field_type="select", options=(("direct", "直接雇佣"), ("dispatch-employment", "派遣雇佣"))), TemplateField("employee", "员工与职位", "姓名、国籍、职位、技能、预定工作地点"), TemplateField("employment", "劳动条件", "工资、工时、休假、试用期、合同期限"), TemplateField("visa", "签证与赴日支持", "在留资格类别、材料协助、搬迁/住宿支持、费用承担"), TemplateField("special", "社会保险与特别约定", "社保、保密、知识产权、解除、其他约定"))),
    ContractTemplate("personal-information-inquiry", "个人信息查询与处理合同", "用于有明确授权和合法目的的个人信息查询及处理安排。", "日本个人信息保护委员会（PPC）", "https://www.ppc.go.jp/", "2026-10",
        "仅限具有合法目的和授权基础的查询及处理。必须明确数据主体授权、查询范围、最小必要、保存期限、安全措施、删除、事故通知和审计。不得生成绕过同意或非法获取个人信息的条款。",
        (TemplateField("parties", "委托方、受托方与授权基础", "双方主体、数据主体、同意书或其他授权依据"), TemplateField("purpose", "查询目的与范围", "业务目的、查询项目、使用限制"), TemplateField("data", "数据类别与交付", "信息类型、来源、交付方式、准确性说明"), TemplateField("security", "保存与安全", "保存期限、访问控制、删除、泄露通知"), TemplateField("special", "审计与特别约定", "审计、责任、争议解决、其他约定"))),
    ContractTemplate("free-draft", "自由起草", "根据一段完整需求生成合同草案。", "用户提供的起草需求", "", "2026-10",
        "将用户需求整理为合同。缺失的重要商业事实必须标记 [待确认]，并列入待确认信息；除非需求明确，否则默认中日双语并保持两种语言内容等效。",
        (TemplateField("instructions", "起草需求", "说明合同类型、双方、交易事实、希望包含的条款和语言要求", field_type="textarea"),)),
)

def list_templates() -> list[dict]: return [template.public() for template in TEMPLATES]

def get_template(template_id: str) -> ContractTemplate:
    for template in TEMPLATES:
        if template.template_id == template_id: return template
    raise KeyError(template_id)

def validate_answers(template: ContractTemplate, answers: dict[str, str]) -> dict[str, str]:
    fields = {field.key: field for field in template.fields}
    if set(answers) - set(fields): raise ValueError("包含不属于所选模板的字段")
    normalized = {key: value.strip() for key, value in answers.items()}
    missing = [field.label for field in template.fields if field.required and not normalized.get(field.key)]
    if missing: raise ValueError(f"请填写：{'、'.join(missing)}")
    for field in template.fields:
        if field.field_type == "select" and normalized.get(field.key) and normalized[field.key] not in {value for value, _ in field.options}:
            raise ValueError(f"{field.label}选项无效")
    return normalized
