# contract-check-agent

面向中日跨境贸易和商业服务的双语合同初步审查系统。它读取文本型 PDF、DOCX、TXT，使用可配置的 OpenAI-compatible LLM 提取合同事实、比较中日条款，并通过一个只读 RAG 工具取得本地可信资料依据。系统不替代律师。

## 架构

`FastAPI 页面/API -> parsers -> LLM structured output -> ReviewAgent(search_knowledge) -> Qdrant Local + FastEmbed -> Pydantic 校验 -> Markdown/JSON 报告`。

- `app/`: Web、解析、统一 LLM 客户端、Prompt Builder、Agent、流水线。
- `knowledge_sources/`: 由 manifest 管理的中国、日本资料和企业审查清单。
- `data/`: 被 Git 忽略的设置、Qdrant 索引和报告。
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

所有完整审查、报告生成与一键核实共享 `app.llm_client.LLMClient` 和同一配置。上传时可选择标准审查或深度审查：标准审查最多 2 轮 RAG，深度审查最多 4 轮 RAG，并扩展覆盖主题与建议条款。Agent 会剔除不在工具真实返回结果中的引用 ID。

## 测试

```powershell
pytest
```

测试会解析示例中日双语 TXT、读取知识资料、执行真实 `KnowledgeBase.search_knowledge` 的本地向量检索，并借由 Mock LLM 跑完整流水线，不请求外部 LLM API。

## 快速使用

1. 启动服务，点击“重建知识库”。
2. 在设置中配置并测试 DeepSeek 或其他兼容 API。
3. 上传 `tests/fixtures/bilingual_contract.txt`，选择法域、审查立场和审查深度后点击“开始审查”。
4. 查看结构化字段、付款期限差异、Agent 的 `search_knowledge` 参数与来源片段、风险报告。
5. 查看结构化信息、立场与深度评价、RAG 检索依据和最终报告；按需下载 Markdown 或 JSON。

## 限制

- 不支持扫描件 OCR、登录、异步队列、在线编辑或自动联网抓取。
- 内置资料是基础摘录；上线前应由法务更新 `manifest.yaml` 和资料正文。
- 使用真实 API 需要自行承担模型、资料时效与人工法律复核责任。
