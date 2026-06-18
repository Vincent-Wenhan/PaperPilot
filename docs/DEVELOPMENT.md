# PaperPilot：多智能体论文复现助手 — 项目开发文档

> 仓库地址：https://github.com/Vincent-Wenhan/PaperPilot

---

## 1. 提交规范

所有 commit 遵循 **Conventional Commits** 格式：

```
<type>(<scope>): <subject>
```

### type

| type | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | 修复 bug |
| `docs` | 文档变更（README、开发文档、prompt 等） |
| `refactor` | 重构（不改变外部行为） |
| `chore` | 构建、依赖、配置等杂项 |
| `style` | 代码格式调整（不影响逻辑） |
| `test` | 增加或修改测试 |
| `perf` | 性能优化 |

### scope

| scope | 说明 |
|-------|------|
| `agent` | Agent 相关（base_agent、具体 Agent） |
| `tool` | 工具模块（pdf_parser、command_runner 等） |
| `ui` | 前端（app.py） |
| `pipeline` | 主流程编排（main.py） |
| `prompt` | 提示词文件 |
| `doc` | 文档（README、开发文档、实现文档） |
| `doc` | 文档 |
| `config` | 配置相关 |
| `security` | 安全策略 |
| `productize` | 产品机会、模板、scaffold、检查与产品管线 |
| `reproduce` | 复现管线相关 |

### subject

- 英文，祈使语气
- 首字母小写
- 不超过 72 字符

示例：
```
feat(agent): add debug agent for log diagnosis
fix(runner): handle timeout edge case when output is empty
docs(readme): add install and usage instructions
refactor(tool): extract URL validation into github_tool
```

---

## 2. Git User 配置

多人协作时，提交前确认 `git config user.name` 和 `user.email` 是当前开发者的身份：

```bash
git config user.name "Your Name"
git config user.email "your@email.com"
```

---

## 3. 分支策略

| 分支 | 用途 |
|------|------|
| `master` | 主分支，保持可发布状态 |
| `feat/<name>` | 功能开发分支 |
| `fix/<name>` | 修复分支 |

功能分支开发完成后，squash merge 到 master，merge message 中描述改动摘要。

---

## 4. 开发顺序

开发新功能时：

1. **先写/更新文档**，描述清楚要解决的问题、设计方案、涉及的文件
2. **文档确认后**再开始写代码
3. **提交时**按 Conventional Commits 规范

---

## 5. 架构概览

### 核心流程

```
User Input（单篇或多篇论文）→ LangGraph 编排 + 确定性 Tool
  → Reproduce Graph（Parse → Research/Repo 并行 → Join → Plan → Command Risk → Implementation → Diagnosis）
  → ImplementationBlueprint（确定性复现代码协议 + 覆盖率检查）
  → Outputs（三份复现文件）
  → Productize Graph（按论文 Send fan-out → Synthesis → Product Plan → 有界 Revision → Scaffold）
  → ProductUISpec（确定性 UI 协议 + scaffold 覆盖率检查）
  → generated_product/（mock-first Streamlit 原型）
```

### 设计原则

- **确定性操作不走 LLM**：clone、scan、run 直接调 subprocess / 文件读写
- **兼容包装迁移**：公开函数签名和结果键稳定，内部默认由 LangGraph 编排
- **有界循环**：Productize 默认最多修订一次，达到上限后带 warning 结束
- **命令只规划不自动执行**：Reproduce Graph 只记录 safe/review/blocked 路由
- **错误不阻断流程**：每个步骤单独 try/except，失败后保留已有结果继续
- **Mock mode 显式启用**：无需 API key 可演示，但真实 LLM 分析是默认模式
- **严格安全策略**：命令执行用精确 allowlist + blocklist，禁止 `shell=True`
- **严格九个高层 Agent**：Reproduce 五个、Productize 四个活动推理 Agent
- **Legacy 隔离**：旧碎片 Agent 仅位于 `agents/legacy/`，活动代码禁止导入
- **Guidelines 注入**：产品理论、组合、UI 和安全规则从 `guidelines/` 加载
- **结构化产物**：关键中间结果使用 Pydantic schema，不只依赖 Markdown
- **生成协议先行**：复现代码先生成 `ImplementationBlueprint`，产品原型先生成 `ProductUISpec`
- **确定性协议 Builder**：`tools/implementation_blueprint.py` 与 `productize/ui_spec.py` 将 LLM 计划转换为可测试、可覆盖率检查的生成契约

### 项目结构

```
PaperPilot/
├── app.py              # Streamlit 前端
├── main.py             # 主流程编排入口
├── config.py           # 环境变量配置
├── agents/             # 九个活动高层 Agent
│   └── legacy/         # 不参与活动流程的旧 Agent
├── graphs/             # LangGraph 工作流与子图
├── runtime/            # 图状态、路由、checkpoint、tool registry/executor
├── guidelines/         # 产品理论、多论文组合、UI 与安全规则
├── schemas/            # 论文、组合、产品、评估与 Runner schema
├── productize/         # 产品模板、scaffold、检查和编排
├── tools/              # 确定性工具和 guideline loader
├── prompts/            # Agent 提示词文件
├── workspace/          # clone 的仓库和 sandbox 运行目录
├── uploads/            # 上传的 PDF
├── outputs/            # 生成的输出文件
├── generated_product/  # 运行时生成的产品原型（gitignored）
├── requirements.txt
└── README.md
```

---

## 6. 安全策略

Runner 只执行 allowlist 中的命令：`python --version`、`pip --version`、已识别入口文件的 `--help`。

禁止操作：
- `sudo`、`rm -rf`、`mkfs`、`shutdown`、`reboot`
- curl、wget、管道、重定向、shell 控制符
- `shell=True`
- `cwd` 只允许项目目录或 `workspace/` 内
- 无 repo 时只做 paper-only 规划，不自动生成或执行替代仓库
- Productize 只向 `generated_product/` 写入原型，不修改被分析仓库
- 多论文组合计划只描述能力关系，不自动连接或执行多个真实仓库
- 已有产品目录先备份为 `generated_product_backup_<timestamp>/`
- 生成的 `ModelAdapter` 默认 `mock_mode=True`，不自动导入或执行原仓库
- Product Tester Tool 只做文件、文本标记和 Python 语法检查，不启动 Streamlit
- 静态 Tool 必须限制 `allowed_roots`，拒绝 secret 文件与路径越界
- `safe` Tool 可直接运行；`review`/`sandbox` 必须显式授权；`blocked` 永不运行
- `pytest_collect` 仅使用 `--collect-only`，禁用 cache 和字节码写入

---

## 7. 开发注意事项

- 函数要有类型标注，关键函数有 docstring
- 所有路径用 `pathlib.Path`，不写硬编码绝对路径
- API key 从环境变量或 `config.py` 读取，不写入代码
- 不要把逻辑写在 `app.py`
- 永远不要使用 `shell=True`
- 不要默认下载大型数据集或模型权重

---

## 8. 文档同步规则

每次新增功能后，必须同步更新以下文档：

| 文档 | 更新内容 |
|---|---|
| `README.md` | 英文版使用说明，包括新的配置、操作步骤 |
| `README_ZH.md` | 中文版使用说明，与英文版同步 |
| `docs/DEVELOPMENT.md` | 开发规范（如新增 scope） |
| `docs/implementation-plan/` | 新增功能的设计与实现文档 |

> 规则：**先写实现文档，再改代码，最后更新 README 和开发规范。**
