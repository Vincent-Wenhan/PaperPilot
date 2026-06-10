# PaperPilot / PaperPilot

[English](README.md)

PaperPilot 是一个面向科研新手的多智能体论文复现助手。传统论文复现通常需要研究者反复阅读论文、查找代码、配置环境、理解实验设置并解决报错，过程复杂且容易失败。本项目将论文复现流程拆分为论文阅读、方法拆解、代码仓库分析、环境配置、实验规划、运行诊断和报告生成等多个阶段，并设计多个专业 Agent 协作完成这些任务。用户只需要上传论文 PDF 并提供 GitHub 仓库链接，系统即可生成结构化的复现路线、实验 checklist、运行命令和 debug 建议，从而降低论文复现的启动成本。

## 项目定位

这是一个 AIGC 课程期末 project，目标是展示如何用轻量、可解释的多 Agent pipeline 辅助论文复现。PaperPilot 不是自动完成全部训练的系统，也不是单纯的论文摘要器；它连接"论文理解、代码分析、环境规划、最小实验、安全运行、报错诊断和报告生成"，优先帮助用户得到可执行的复现起点。

## 系统功能

- 上传并解析论文 PDF
- 校验并浅克隆公开 GitHub 仓库
- 扫描 README、依赖文件、配置和候选入口
- 生成论文摘要与工程化方法拆解
- 根据 CPU、单 GPU 或多 GPU 条件规划环境
- 生成分层实验路线、checklist 和安全 `run.sh`
- 运行 version 与候选入口 `--help` 等轻量命令
- 自动分析 Runner 失败，也支持手动粘贴日志 Debug
- 生成并下载复现计划、脚本和课程展示报告
- 无 API key 时通过 mock mode 完整演示

## 系统架构

```text
User Input
├── Paper PDF
├── GitHub URL
├── Hardware Info
└── Reproduction Goal
↓
PDF Parser + GitHub Clone + Repo Scanner
↓
Multi-Agent Pipeline
├── Paper Reader Agent
├── Method Extractor Agent
├── Repo Analyzer Agent
├── Environment Agent
├── Experiment Planner Agent
├── Runner Agent
├── Debug Agent
└── Report Agent
↓
Outputs
├── reproduction_plan.md
├── run.sh
└── report.md
```

## 多 Agent 说明

| Agent | 职责 |
| --- | --- |
| Paper Reader Agent | 提取论文任务、贡献、数据集、指标和实验设置 |
| Method Extractor Agent | 将论文方法拆成可实现模块、训练与推理流程 |
| Repo Clone Agent | 确定性调用 GitHub clone 工具，不执行仓库代码 |
| Repo Analyzer Agent | 分析仓库结构、依赖、配置和运行入口 |
| Environment Agent | 根据依赖证据与硬件生成环境建议 |
| Experiment Planner Agent | 生成 Level 0 到 Level 4 的分层复现路线 |
| Runner Agent | 确定性调用安全命令运行器 |
| Debug Agent | 分析 command、stdout、stderr 与环境信息 |
| Report Agent | 汇总各阶段结果并生成复现报告 |

所有 LLM Agent 共用 `BaseAgent` 和统一的 OpenAI-compatible `LLMClient`。命令执行与仓库 clone 不由 LLM 决策。

## 项目结构

```text
PaperPilot/
├── app.py
├── main.py
├── config.py
├── agents/
├── tools/
├── prompts/
├── uploads/
├── workspace/
├── outputs/
│   ├── reproduction_plan.md
│   ├── run.sh
│   └── report.md
├── requirements.txt
└── README.md
```

## 安装方式

项目在 WSL 与 Python 3.12 环境下开发。推荐使用独立 Conda 环境：

```bash
cd <path/to/PaperPilot>
conda create -n paperpilot python=3.12 -y
conda run -n paperpilot python -m pip install --upgrade pip
conda run -n paperpilot python -m pip install -r requirements.txt
```

检查依赖：

```bash
conda run -n paperpilot python -m pip check
conda run -n paperpilot python -c "import fitz, streamlit, openai; print('imports ok')"
```

## 运行方式

```bash
cd <path/to/PaperPilot>
conda run -n paperpilot streamlit run app.py
```

浏览器打开 Streamlit 输出的本地地址。程序入口为 `app.py`，核心编排函数为 `main.py` 中的 `run_paperpilot(...)`。

## Mock Mode 演示

项目默认 `LLM_MOCK_MODE=True`，无需 API key：

```bash
export LLM_MOCK_MODE=True
conda run -n paperpilot streamlit run app.py
```

Mock mode 会返回固定文本，但 PDF 解析、URL 校验、仓库 clone、扫描、输出文件生成和安全 Runner 仍走真实本地流程。没有 API key 时页面不会崩溃。

## 真实 LLM API

`LLMClient` 使用 OpenAI-compatible Chat Completions 接口。启动前设置：

```bash
export LLM_MOCK_MODE=False
export LLM_API_KEY="your-api-key"
export LLM_MODEL="your-model-name"
export LLM_BASE_URL="https://your-compatible-endpoint/v1"
conda run -n paperpilot streamlit run app.py
```

使用 OpenAI 默认端点时，可不设置 `LLM_BASE_URL`。不要将 API key 写入代码或提交到版本库。未配置 key 时，客户端会返回清晰提示而不是使系统崩溃。

## Streamlit 使用流程

1. 上传论文 PDF。
2. 输入 `https://github.com/owner/repository` 格式的仓库 URL。
3. 选择 `CPU only`、`Single GPU` 或 `Multi GPU`，可填写 GPU 型号。
4. 选择理解论文、官方 demo、最小训练实验、主实验或 Debug 目标。
5. 点击 `Analyze`，查看 Agent 状态与各阶段结果。
6. 下载 `reproduction_plan.md`、`run.sh` 和 `report.md`。
7. 在 Runner 区手动点击安全命令；命令失败时查看自动 Debug。
8. 也可以在 Debug 区粘贴日志，获得独立诊断。

## 示例输入

- 示例 PDF：用户上传任意可提取文本的论文 PDF
- 示例 GitHub URL：`https://github.com/octocat/Hello-World`
- 示例硬件：`CPU only` 或 `Single GPU`
- 示例目标：`run official demo` 或 `minimal training experiment`

示例仓库仅用于演示浅 clone 与扫描，不代表它包含机器学习训练流程。请避免使用大型深度学习仓库做课堂快速演示。

## Runner 安全策略

Runner 只在用户点击按钮后执行轻量命令：

- `python --version`
- `pip --version`
- 已识别入口文件的 `python <entrypoint> --help`

安全实现包括：

- 精确 allowlist 为主，blacklist 为辅
- 使用 `shlex.split`，并以 list 参数调用 `subprocess.run`
- 禁止 `shell=True`
- 禁止管道、重定向、分号、`&&` 和 `||`
- 拦截 `sudo`、`rm -rf`、`mkfs`、`shutdown`、`reboot`、`curl`、`wget`、`chmod 777` 和 fork bomb
- `cwd` 仅允许项目目录或 `workspace/` 内
- 每条命令都有 timeout
- stdout 与 stderr 截断到最近 4000 字符

Runner 不会默认执行完整训练、demo 本体、未知 shell 脚本，也不会下载大型数据集。

## Debug 功能

Runner 命令失败时，系统将 command、cwd、return code、stdout 和 stderr 自动交给 Debug Agent。用户也可以手动粘贴命令、日志和环境信息。Debug Agent 输出直接原因、可能根因、验证方法、修改建议和下一步。Mock mode 下同样会返回可展示的 mock 诊断。

## 输出文件

- `outputs/reproduction_plan.md`：论文、方法、仓库、环境、实验路线、checklist 与风险
- `outputs/run.sh`：仅包含安全默认命令和注释形式的 TODO
- `outputs/report.md`：适合课程 project 展示的结构化复现报告

仓库内已提供 mock 示例输出。每次运行主流程会覆盖这些文件。

## 项目限制

- PDF 扫描件没有 OCR 时可能无法提取文本。
- LLM 输出质量取决于模型、上下文长度和论文文本质量。
- 仓库分析基于静态文件扫描，不保证自动理解所有自定义入口。
- 系统不验证完整训练能否达到原论文指标。
- Runner 有意采用严格 allowlist，不提供任意终端能力。
- 真实 API、私有仓库、数据集和 checkpoint 可能需要用户自行配置。

## 未来改进

- 增加 OCR 与论文表格、公式解析
- 增加可配置的仓库扫描深度与依赖冲突分析
- 引入人工确认后的受控 demo 执行
- 保存多次复现会话与实验对比
- 增加真实模型的结构化输出校验
- 增加单元测试、CI 和容器化发布
