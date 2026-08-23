# contract-check-agent 项目蓝图

## 1. 项目定位

`contract-check-agent` 是一个面向中日跨境贸易与商业服务企业的双语合同智能审查系统。

用户上传中文、日文或中日双语合同后，系统完成文本读取、合同信息结构化、中日条款对比，并由 LLM 自主调用 RAG 检索工具获取可信依据，最终生成带来源引用的审查报告。

项目重点展示六项能力：

1. 文档解析；
2. Structured Output；
3. 中日双语语义对比；
4. Tool Calling 与 RAG；
5. 选中条款智能问答与 Prompt Builder；
6. 可配置 LLM 和结构化报告。

系统用于合同初步审查和人工复核辅助，不追求替代律师，也不在 Python 中编写庞大的法律判断规则。

## 2. 目标使用场景

主要面向：

- 中日贸易、采购、代理和经销企业；
- 日本房地产及跨境商业服务企业；
- 跨境电商、物流、软件和咨询企业；
- 需要快速初筛中日双语合同的业务或法务人员。

第一版重点处理：

- 中文版与日文版的主体、金额、日期和条款是否一致；
- 付款、交付、验收、违约、解约、保密和知识产权等条款；
- 适用法律、争议解决和语言优先条款是否存在或相互冲突；
- 关键条款是否缺失、含糊或明显不利；
- 风险说明、修改建议和建议条款。

## 3. 核心流程

```text
上传合同
   ↓
读取并清洗文本
   ↓
LLM结构化提取合同信息
   ↓
LLM对比中日双语条款
   ↓
合同审查Agent调用RAG检索工具
   ↓
LLM结合合同内容与检索依据进行分析
   ↓
输出网页、Markdown和JSON报告
```

Tool Calling 与 RAG 的关系：LLM 决定需要检索什么，并调用 `search_knowledge`；Python 从本地向量库返回可信片段；LLM 根据片段继续审查。第一版只需要一个 Agent 和一个工具。

## 4. 功能范围

### 4.1 合同读取

- 支持文本型 PDF、DOCX、TXT；
- 支持中文、日文和中日双语合同；
- 保留页码、段落序号等定位信息；
- 扫描件无法提取文字时提示暂不支持 OCR；
- 限制文件类型和合理大小，解析失败时显示明确原因。

### 4.2 结构化提取

LLM 输出经过 Pydantic 校验的 `ContractFacts`：

- 合同名称与合同类型；
- 语言；
- 合同主体及角色；
- 金额、币种、付款条件；
- 生效、交付、验收、续期和终止日期；
- 适用法律；
- 法院或仲裁机构；
- 语言优先级；
- 主要条款摘要；
- 建议重点审查的主题。

无法确认的字段返回 `null`，不得猜测。

### 4.3 中日双语对比

双语合同由 LLM 输出 `ComparisonItem[]`，每项包含：

- 中文位置和原文；
- 日文位置和原文；
- 对比类型：一致、缺失、数值冲突、语义差异、义务强度差异；
- 差异说明；
- 严重程度；
- 建议处理方式。

单语合同跳过此步骤，并在结果中明确标记。

### 4.4 RAG知识库

第一版不自动遍历互联网，也不运行定时任务。可信资料放入 `knowledge_sources/`，通过网页按钮或命令重新建立索引。

资料清单由 `knowledge_sources/manifest.yaml` 管理，至少包含：

- 中国官方合同法律资料；
- 中国涉外合同法律适用资料；
- 日本民法相关资料；
- 日本《法の適用に関する通則法》相关资料；
- 一份企业合同审查清单。

每份资料必须记录：

- `source_id`
- `title`
- `jurisdiction`
- `source_url`
- `effective_date`
- `document_type`
- 本地文件路径

知识片段至少保存：

- `chunk_id`
- `source_id`
- `title`
- `jurisdiction`
- `section`
- `source_url`
- `text`

使用 Qdrant Local Mode 保存向量，FastEmbed 生成多语言向量。按标题、条款和自然段切分，目标长度约 600～1000 字符，重叠约 100 字符。

### 4.5 Agent与工具

Agent 仅提供一个只读工具：

```python
search_knowledge(
    query: str,
    jurisdiction: Literal["CN", "JP", "CN-JP"],
    top_k: int = 5,
) -> list[KnowledgeChunk]
```

工具返回完整片段及来源元数据。Agent 最多执行 3 轮检索，每轮可以根据前一轮结果调整查询。

Agent 需要：

1. 根据合同内容和双语差异决定检索问题；
2. 调用工具获取依据；
3. 只引用工具真实返回的 `chunk_id`；
4. 依据不足时明确写明“未检索到充分依据”；
5. 最终输出经过 Pydantic 校验的结构化结果。

每个 `ReviewIssue` 包含：

- `title`
- `severity`：high、medium、low
- `category`
- `contract_location`
- `contract_excerpt`
- `issue`
- `impact`
- `recommendation`
- `suggested_clause`
- `basis_chunk_ids`

Python 只检查 JSON 格式、字段完整性和引用是否真实，不判断法律风险是否成立。

### 4.6 报告

LLM 根据 `ContractFacts`、双语对比、结构化审查结果及引用片段生成 Markdown 报告，包括：

1. 合同概览；
2. 关键商业条款；
3. 中日双语差异；
4. 高、中、低风险事项；
5. 缺失或不完整条款；
6. 修改建议与建议条款；
7. 引用依据。

网页展示报告，并支持下载 Markdown 和 JSON。报告中的引用可以展开查看原始片段、标题和来源链接。

### 4.7 选中条款智能问答

解析完成后，页面展示带位置标记的合同正文。用户可以选中任意一段文字并点击“问AI”，系统打开智能问答面板。

面板提供快捷任务：

- 解释这段条款；
- 分析对我方可能存在的风险；
- 改写得更清晰或更有利；
- 对比中日文含义；
- 生成谈判意见或替代条款；
- 自定义问题。

前端只提交选中文字、快捷任务、自定义问题、合同 ID 和当前审查法域。后端从已有结构化结果中补充必要合同上下文，通过 `PromptBuilder` 生成标准 Prompt，再调用当前设置中的 LLM。

该功能是一次直接 LLM 调用，不进入 Agent 工具循环，也不强制执行 RAG，避免增加复杂度。回答结果需要显示：

- 选中文字；
- 用户问题或快捷任务；
- LLM回答；
- 使用的模型；
- 可折叠查看的最终 Prompt；
- 复制回答按钮。

Prompt 必须由后端模板生成，至少包含角色、合同背景、选中文字、用户目标、适用语言和输出要求。前端不得直接拼接完整系统 Prompt。

## 5. LLM配置

默认接入 DeepSeek：

```env
LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
LLM_API_KEY=
LLM_TEMPERATURE=0.1
LLM_MAX_TOOL_ROUNDS=3
```

使用 OpenAI Python SDK 的 `AsyncOpenAI` 调用 OpenAI-compatible API。网页设置区允许修改：

- Provider；
- Base URL；
- Model；
- API Key；
- Temperature。

提供 DeepSeek、OpenRouter、Custom 三个预设，并提供测试连接按钮。设置保存在被 `.gitignore` 排除的本地文件中，环境变量优先。

审查流水线、报告生成和“选中条款智能问答”必须共用同一套 LLM Client 与设置，不得分别硬编码 API 地址或模型。

## 6. 技术架构

- Python 3.12
- FastAPI + Uvicorn
- Jinja2 + Vanilla JavaScript + CSS
- Pydantic 2 + pydantic-settings
- PyMuPDF + python-docx
- OpenAI Python SDK
- Qdrant Local Mode
- FastEmbed 多语言向量模型
- PyYAML
- Markdown渲染
- pytest

不使用 React、Node 构建链、MySQL、SQLAlchemy、Redis、Celery、LangChain、LangGraph、Dify或多 Agent 框架。

第一版不需要业务数据库。任务结果直接保存为 `data/reports/{review_id}.json` 和 `.md`，向量数据保存到 `data/qdrant/`，这些运行数据均不提交 Git。

## 7. 页面与接口

### 单页界面

页面包含：

1. 合同上传和审查法域选择：Auto、CN、JP、CN-JP；
2. LLM连接设置与测试；
3. 知识库状态和“重建知识库”按钮；
4. 开始审查按钮和处理状态；
5. 可选中文字并发起智能问答的合同正文；
6. 合同结构化信息；
7. 双语对比结果；
8. Agent工具调用记录与检索依据；
9. 风险列表和最终报告；
10. Markdown、JSON下载按钮。

第一版允许同步处理一次请求，页面显示等待状态即可，不实现任务队列、WebSocket、登录和权限。

### 最少接口

- `GET /`：主页面；
- `POST /api/review`：上传并完成一次审查；
- `POST /api/knowledge/rebuild`：重建知识库；
- `GET /api/knowledge/status`：查看资料和片段数量；
- `GET /api/settings`、`PUT /api/settings`：读取与修改 LLM 配置；
- `POST /api/settings/test`：测试 LLM 连接；
- `POST /api/ask-selection`：根据选中条款生成 Prompt 并调用 LLM；
- `GET /api/reports/{review_id}.md`：下载 Markdown；
- `GET /api/reports/{review_id}.json`：下载 JSON。

## 8. 目录结构

```text
contract-check-agent/
├── AGENTS.md
├── CONTRACT_CHECK_AGENT_BLUEPRINT.md
├── TERRA_BUILD_PROMPT.md
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── run.py
├── app/
│   ├── main.py
│   ├── config.py
│   ├── schemas.py
│   ├── parsers.py
│   ├── llm_client.py
│   ├── prompt_builder.py
│   ├── knowledge.py
│   ├── agent.py
│   ├── pipeline.py
│   ├── prompts/
│   ├── templates/
│   └── static/
├── knowledge_sources/
│   ├── manifest.yaml
│   ├── cn/
│   ├── jp/
│   └── internal/
├── data/
│   └── .gitkeep
├── scripts/
│   └── rebuild_knowledge.py
└── tests/
    ├── fixtures/
    ├── test_parsers.py
    ├── test_knowledge.py
    ├── test_agent.py
    └── test_pipeline.py
```

允许 Terra 在不扩大功能范围的前提下微调模块文件名。

## 9. 验收标准

1. Windows 安装依赖后可通过 `python run.py` 启动；
2. 可以在网页中配置并测试 DeepSeek 或其他 OpenAI-compatible API；
3. 可以从本地可信资料重建 Qdrant 索引，重复重建不会重复累积数据；
4. 可以读取文本型 PDF、DOCX、TXT；
5. 可以生成经过 Pydantic 校验的 `ContractFacts`；
6. 双语合同可以生成结构化对比结果，单语合同可以正确跳过；
7. Agent 真实发起至少一次 `search_knowledge` 工具调用；
8. 页面能显示工具调用参数、返回片段和来源；
9. 每个引用 `chunk_id` 都能在知识库中找到，未知引用不能进入最终报告；
10. 用户可以选择合同文字，通过预设任务或自定义问题调用 LLM，并查看本次生成的 Prompt；
11. 智能问答与完整审查共用页面中配置的 LLM API；
12. 可以生成并下载 Markdown 和 JSON 报告；
13. 提供一份中日双语示例合同和 Mock LLM 测试，测试不消耗真实 API；
14. `pytest` 通过，README 可以让新用户完成安装、运行和三分钟项目讲解。

## 10. 明确不做

- OCR和图像篡改检测；
- 自动发现或定时采集网站；
- 用户、权限、多租户和计费；
- 任务队列、消息队列和微服务；
- 在线合同编辑、批注和协作；
- MySQL及复杂业务数据库；
- 多 Agent 协同；
- 知识图谱、reranker、微调和复杂评测平台；
- Python法律规则引擎；
- 与本蓝图无关的功能扩张。

## 11. 实现顺序

1. 项目骨架、配置、单页页面；
2. PDF、DOCX、TXT解析及测试；
3. 可信资料清单、切片、向量化和检索；
4. 可配置 LLM Client 与连接测试；
5. 合同结构化提取；
6. 中日双语对比；
7. 选中条款智能问答与 Prompt Builder；
8. 单工具 Tool Calling 循环、引用校验；
9. Markdown报告、下载、完整流程测试和README。

每完成一个阶段运行相关测试；修复后再继续下一阶段。
