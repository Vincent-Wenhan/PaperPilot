# PaperPilot：多智能体论文复现助手 — 项目开发文档

> 本文档替代原 `AIGC_PaperPilot_Codex_Prompt_Revised.md`，是 PaperPilot 项目的开发规范与指南，适用于所有参与者。
>
> 仓库地址：https://github.com/Vincent-Wenhan/PaperPilot

---

## 1. 项目概述

PaperPilot 是一个面向科研新手的多智能体论文复现助手。

用户输入：
- 论文 PDF
- GitHub 仓库链接
- 硬件条件（CPU / 单 GPU / 多 GPU）
- 复现目标（只理解论文 / 跑通 demo / 最小训练实验 / Debug 报错）

系统输出：
- 论文核心信息摘要
- 方法模块拆解
- GitHub 仓库结构分析
- 环境配置建议
- 最小复现路线
- 可执行的 `run.sh`
- 实验 checklist
- 报错日志分析与 debug 建议
- 复现报告模板

---

## 2. 开发流程规范

### 2.1 先写文档，再改代码

任何新功能或重大修改，必须先编写或更新相关文档，描述清楚：
- 要解决的问题
- 设计方案
- 涉及的文件范围

文档通过 review 后再进行代码实现。

### 2.2 提交规范

所有 commit 必须遵循 **Conventional Commits** 格式：

```
<type>(<scope>): <subject>
```

**type**

| type | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | 修复 bug |
| `docs` | 文档变更（README、开发文档、prompt 等） |
| `refactor` | 重构（不改变外部行为的代码改动） |
| `chore` | 构建、依赖、配置等杂项 |
| `style` | 代码格式调整（不影响逻辑） |
| `test` | 增加或修改测试 |
| `perf` | 性能优化 |

**scope**

| scope | 说明 |
|-------|------|
| `agent` | Agent 相关（base_agent、具体 Agent） |
| `tool` | 工具模块（pdf_parser、command_runner 等） |
| `ui` | 前端（app.py） |
| `pipeline` | 主流程编排（main.py） |
| `prompt` | 提示词文件 |
| `doc` | 文档 |
| `config` | 配置相关 |
| `security` | 安全策略 |

**subject**

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

### 2.3 Git User 配置

多人协作时，提交前确认 `git config user.name` 和 `user.email` 是当前开发者的身份：

```bash
git config user.name "Your Name"
git config user.email "your@email.com"
```

### 2.4 分支策略

| 分支 | 用途 |
|------|------|
| `master` | 主分支，保持可发布状态 |
| `feat/<name>` | 功能开发分支 |
| `fix/<name>` | 修复分支 |

功能分支开发完成后，通过 squash merge 合并到 master，并在 merge message 中描述改动摘要。

---

## 3. 项目结构

```
AIGC_PaperPilot/
├── app.py                        # Streamlit 前端
├── main.py                       # 主流程编排入口
├── config.py                     # 环境变量配置
├── CLAUDE.md                     # Claude Code 本地项目指令（不上传 GitHub）
│
├── agents/
│   ├── __init__.py
│   ├── base_agent.py             # Agent 基类（加载 prompt + 调用 LLM）
│   ├── paper_reader_agent.py     # 论文阅读
│   ├── method_extractor_agent.py # 方法拆解
│   ├── repo_clone_agent.py       # GitHub clone（确定性操作）
│   ├── repo_analyzer_agent.py    # 仓库分析
│   ├── env_agent.py              # 环境配置
│   ├── experiment_agent.py       # 实验规划
│   ├── runner_agent.py           # 安全命令运行（确定性操作）
│   ├── debug_agent.py            # 报错诊断
│   └── report_agent.py           # 报告生成
│
├── tools/
│   ├── __init__.py
│   ├── pdf_parser.py             # PDF 文本提取
│   ├── github_tool.py            # URL 校验 + 浅克隆
│   ├── repo_scanner.py           # 仓库结构扫描（只读）
│   ├── command_runner.py         # 安全命令执行器
│   ├── llm_client.py             # LLM 调用封装（OpenAI-compatible）
│   └── markdown_writer.py        # 输出文件写入
│
├── prompts/
│   ├── paper_reader_prompt.txt
│   ├── method_extractor_prompt.txt
│   ├── repo_analyzer_prompt.txt
│   ├── env_prompt.txt
│   ├── experiment_prompt.txt
│   ├── debug_prompt.txt
│   └── report_prompt.txt
│
├── workspace/                    # clone 的仓库存放处（不上传）
├── uploads/                      # 上传的 PDF 存放处（不上传）
├── outputs/                      # 生成的输出文件
│   ├── reproduction_plan.md
│   ├── run.sh
│   └── report.md
│
├── requirements.txt
└── README.md
```

---

## 4. 架构设计

### 4.1 核心流程

```
User Input → PDF Parser + GitHub Clone + Repo Scanner
  → Multi-Agent Pipeline（串行编排，9 个 Agent）
  → Outputs（三份文件）
```

主流程在 `main.py` 的 `run_paperpilot()` 中串行执行，输出存入 dict 并写文件。

### 4.2 设计原则

1. **确定性操作不走 LLM**：clone、scan、run 直接调用 subprocess / 文件读写，不经过 LLM。
2. **错误不阻断流程**：每个步骤单独 try/except，失败后保留已有结果继续下一步。
3. **Mock mode 默认**：`LLM_MOCK_MODE=true`，无需 API key 即可演示。PDF 解析、clone、scan 等本地操作不受 mock mode 影响。
4. **严格安全策略**：命令执行使用精确 allowlist + blocklist，禁止 `shell=True`。

### 4.3 LLM Client

`tools/llm_client.py` 使用 OpenAI-compatible Chat Completions 接口，支持：
- 环境变量配置：`LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`、`LLM_MOCK_MODE`
- Mock mode：返回固定文本
- 无 API key：返回清晰提示，不崩溃

### 4.4 Agent

所有 LLM Agent 继承 `BaseAgent`：
- 从 `prompts/` 加载 system prompt
- 调用 `LLMClient.generate()` 生成结果
- 出错时返回错误字符串，不抛异常

### 4.5 安全策略

Runner 只执行 allowlist 中的命令：
- `python --version` / `pip --version`
- 已识别入口文件的 `python <entrypoint> --help`

禁止操作：
- `sudo`、`rm -rf`、`mkfs`、`shutdown`、`reboot`
- curl、wget、管道、重定向、shell 控制符
- `shell=True`
- `cwd` 只允许项目目录或 `workspace/` 内

---

## 5. 主要开发命令

```bash
# 安装依赖
pip install -r requirements.txt

# 启动前端
streamlit run app.py

# Mock mode（默认）
export LLM_MOCK_MODE=true
streamlit run app.py

# 真实 LLM 模式
export LLM_MOCK_MODE=false
export LLM_API_KEY="sk-xxx"
export LLM_MODEL="gpt-4o"
streamlit run app.py
```

---

## 6. 开发注意事项

### 6.1 代码风格

- 函数要有类型标注
- 关键函数有 docstring
- 所有路径用 `pathlib.Path`，不写硬编码绝对路径
- API key 从环境变量或 `config.py` 读取，不写入代码
- 保持模块化，不要把逻辑写在 `app.py`

### 6.2 常见错误处理模式

参考 `main.py` 中的 `_run_agent()` 和 `_record_error()`：

```python
# 每个 Agent 单独 try/except，失败不影响 pipeline
result["paper_info"] = _run_agent(result, "Paper Reader Agent", agent, input_data)
```

### 6.3 安全红线

- 永远不要使用 `shell=True`
- 永远不要绕过 allowlist
- 勿在代码中硬编码 API key、token 或密码
- 勿默认下载大型数据集或模型权重

---

## 7. 后续可能的改进方向

- OCR 与论文表格、公式解析
- 可配置的仓库扫描深度与依赖冲突分析
- 引入人工确认后的受控 demo 执行
- 保存多次复现会话与实验对比
- 增加真实模型的结构化输出校验
- 增加单元测试、CI 和容器化发布
