# contract-check-agent

面向中日跨境贸易和商业服务的双语合同工作台。它可以读取文本型 PDF、DOCX、TXT 进行初步审查，也可以根据结构化交易信息生成可追溯的合同草案；审查通过一个只读 RAG 工具取得本地可信资料依据。系统不替代律师。

## 架构

`FastAPI 页面/API -> 结构化交易信息或合同解析 -> LLM structured output -> 生成草案或 ReviewAgent(search_knowledge) -> Qdrant Local + FastEmbed -> Pydantic 校验 -> Markdown/JSON 文件`。

- `app/`: Web、解析、统一 LLM 客户端、Prompt Builder、Agent、流水线。
- `knowledge_sources/`: 由 manifest 管理的中国、日本资料和企业审查清单。
- `data/`: 被 Git 忽略的设置、Qdrant 索引、审查报告和生成草案。
- `tests/`: 不使用真实 API 的 Mock LLM 端到端测试，示例合同在 `tests/fixtures/`。

## 安装与运行（Windows）

需要 Python 3.12。创建虚拟环境后安装：

```powershell
C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

双击 `start_contract_check_agent.bat` 启动服务并自动打开 `http://127.0.0.1:22215`。双击 `stop_contract_check_agent.bat` 关闭服务。首次点击“重建知识库”会下载 FastEmbed 模型并建立本地 Qdrant 索引。也可执行 `.\.venv\Scripts\python.exe scripts\rebuild_knowledge.py`。

## 配置真实 LLM

在 `.env` 填写 `LLM_API_KEY`，或在页面设置区输入并保存。环境变量优先于 `data/settings.json`。默认值为 DeepSeek；页面也可改为 OpenRouter 或任意 OpenAI-compatible Base URL 和模型。点击“测试连接”确认后再上传合同。

所有完整审查、合同生成、报告生成与一键核实共享 `app.llm_client.LLMClient` 和同一配置。上传时可选择标准审查或深度审查：标准审查最多 2 次实际 RAG 检索，深度审查最多 4 次，并扩展覆盖主题与建议条款。Agent 会剔除不在工具真实返回结果中的引用 ID。

## 测试

```powershell
pytest
```

测试会解析示例中日双语 TXT、读取知识资料、执行真实 `KnowledgeBase.search_knowledge` 的本地向量检索，并借由 Mock LLM 跑完整流水线，不请求外部 LLM API。

## 快速使用

1. 启动服务，点击“重建知识库”。
2. 在设置中配置并测试 DeepSeek 或其他兼容 API。
3. 在“合同审查”上传 `tests/fixtures/bilingual_contract.txt`，选择法域、审查立场和审查深度后点击“开始审查”。
4. 在“合同生成”选择预设模板，仅填写该模板要求的 3 至 5 项关键信息；自由起草仅填写一段完整需求。
5. 在生成结果中确认待确认事项，按需下载 Markdown 或 JSON，或点击“一键审查草案”执行标准审查。
6. 查看审查结构化信息、立场与深度评价、RAG 检索依据和最终报告。

## 限制

- 不支持扫描件 OCR、登录、异步队列、在线编辑或自动联网抓取。
- 生成模块会将未确认的商业信息标为待确认占位符；草案必须经过业务及法务复核后使用。
- 日本不动产模板仅参考国土交通省公开资料和行业常见结构，仍需完成重要事项说明并接受专业审阅。数字资产与个人信息模板会保留必要的授权、来源和合规前提，不用于规避监管或取得未获授权的信息。
- 内置资料是基础摘录；上线前应由法务更新 `manifest.yaml` 和资料正文。
- 使用真实 API 需要自行承担模型、资料时效与人工法律复核责任。
