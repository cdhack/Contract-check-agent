from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class TemplateField:
    key: str
    label: str
    required: bool = True
    field_type: str = "text"
    options: tuple[tuple[str, str], ...] = ()

    def public(self) -> dict:
        return {"key": self.key, "label": self.label, "required": self.required, "field_type": self.field_type,
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

MLIT_HOUSING = "国土交通省 住宅・不动产相关资料"
MLIT_HOUSING_URL = "https://www.mlit.go.jp/jutakukentiku/house/"
MLIT_REAL_ESTATE = "国土交通省 不动产业相关资料"
MLIT_REAL_ESTATE_URL = "https://www.mlit.go.jp/totikensangyo/const/"
SUPPLEMENT = TemplateField("supplement", "补充说明", required=False)

TEMPLATES = (
    ContractTemplate("jp-housing-lease", "日本房屋租赁合同", "参考日本住宅租赁标准契约结构的中日双语草案。", MLIT_HOUSING, MLIT_HOUSING_URL, "2026-10",
        "按日本住宅租赁的常见结构起草，明确租赁标的、用途、费用、修缮、解除、返还和保证安排。不得将参考来源表述为对具体交易的法律意见。",
        (TemplateField("property_parties", "房屋与双方主体"), TemplateField("term_rent", "租期、租金与费用"), TemplateField("conditions", "担保与特别约定"), SUPPLEMENT)),
    ContractTemplate("jp-real-estate-sale", "日本不动产买卖合同", "参考日本不动产交易常见结构的中日双语草案。", MLIT_REAL_ESTATE, MLIT_REAL_ESTATE_URL, "2026-10",
        "按日本不动产交易常见结构起草，明确标的、权属、价款、融资、交付、设备状况、瑕疵及税费。提示用户另行完成重要事项说明和专业审阅。",
        (TemplateField("property_parties", "不动产与交易双方"), TemplateField("price_payment", "价格、付款与融资"), TemplateField("handover_conditions", "交付、税费与特别约定"), SUPPLEMENT)),
    ContractTemplate("currency-exchange", "换汇合同", "用于公司主体间货币兑换和结算安排的草案。", "企业内部商业条款结构", "", "2026-10",
        "仅起草公司间商业安排；必须加入主体授权、资金来源声明、KYC/AML、合法结算前提、暂停和解除条款。不得提供规避监管、规避外汇限制或隐匿交易的设计。",
        (TemplateField("time_location", "交易时间或地点"), TemplateField("transaction_method", "交易方式"), TemplateField("amount_currency", "金额与币种"), TemplateField("exchange_rate", "汇率", field_type="select", options=(("realtime", "按实时汇率"), ("fixed", "固定汇率"))), TemplateField("fee", "手续费"), SUPPLEMENT)),
    ContractTemplate("it-company-cooperation", "赴日 IT 公司合作合同", "人材介绍或劳务派遣模式下与日本 IT 公司的合作草案。", "日本厚生劳动省 外国人雇用与人材服务相关资料", "https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/koyou_roudou/koyou/gaikokujin/", "2026-10",
        "根据合作模式分别起草人材介绍或劳务派遣条款；不得混用两种模式的费用、指挥命令和雇主责任。必须明确签证协助边界、费用、候选人信息和替换安排。",
        (TemplateField("mode", "合作模式", field_type="select", options=(("recruitment", "人材介绍"), ("dispatch", "劳务派遣"))), TemplateField("parties_people", "双方与人员信息"), TemplateField("services_fees", "服务、签证协助与费用"), TemplateField("work_conditions", "工作条件与约定"), SUPPLEMENT)),
    ContractTemplate("it-worker-contract", "赴日 IT 员工合同", "直接雇佣或派遣雇佣模式下与员工的中日双语草案。", "日本厚生劳动省 外国人雇用与劳动条件相关资料", "https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/koyou_roudou/koyou/gaikokujin/", "2026-10",
        "根据雇佣模式分别起草直接雇佣或派遣雇佣条款，明确雇主、工作条件、签证协助边界、工资、社会保险和解除条件。不得将签证批准作出绝对保证。",
        (TemplateField("mode", "雇佣模式", field_type="select", options=(("direct", "直接雇佣"), ("dispatch-employment", "派遣雇佣"))), TemplateField("employee_position", "员工、职位与工作地点"), TemplateField("employment_terms", "工资、工时与合同期限"), TemplateField("visa_support", "签证支持与其他约定"), SUPPLEMENT)),
    ContractTemplate("personal-information-inquiry", "个人信息查询与处理合同", "用于有明确授权和合法目的的个人信息查询及处理安排。", "日本个人信息保护委员会（PPC）", "https://www.ppc.go.jp/", "2026-10",
        "仅限具有合法目的和授权基础的查询及处理。必须明确数据主体授权、查询范围、最小必要、保存期限、安全措施、删除、事故通知和审计。不得生成绕过同意或非法获取个人信息的条款。",
        (TemplateField("parties_authority", "双方与授权基础"), TemplateField("purpose_scope", "查询目的与范围"), TemplateField("data_security", "数据、保存与安全"), SUPPLEMENT)),
    ContractTemplate("free-draft", "自由起草", "根据一段完整需求生成合同草案。", "用户提供的起草需求", "", "2026-10",
        "将用户需求整理为合同。缺失的重要商业事实必须标记 [待确认]，并列入待确认信息；除非需求明确，否则默认中日双语并保持两种语言内容等效；合同末尾必须增加“补充说明”条款。",
        (TemplateField("instructions", "起草需求", field_type="textarea"),)),
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
