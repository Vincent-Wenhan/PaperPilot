# Codex Prompt：在 WSL 中构建 PaperPilot 多智能体论文复现助手

你将帮助我在 WSL 环境中从零实现一个课程期末 Project：**PaperPilot：多智能体论文复现助手**。项目根目录必须命名为：`PaperPilot/`。

请严格按照本文档要求分阶段完成。  
**不要一次性把所有代码写完。必须按阶段推进：每完成一个阶段，都要先自检、运行必要测试、输出检查结果。**

**更重要：每完成一个阶段并输出自检结果后，必须停止，等待我明确回复“继续阶段 X”。不要自动进入下一阶段。**

---

## -1. 当前 WSL 环境与强制执行约束

当前开发环境已经确认：

```bash
Python 3.12.12
git version 2.43.0
pip 25.3 from /home/fcc/miniforge3/lib/python3.12/site-packages/pip (python 3.12)
```

请按照以下约束开发：

1. 项目根目录必须创建为：`PaperPilot/`。
2. 建议项目路径为：`~/projects/PaperPilot` 或当前工作目录下的 `PaperPilot/`。不要放在 Windows 挂载盘路径，例如 `/mnt/c/...`。
3. 使用当前 WSL 的 Python 3.12.12 开发。代码必须兼容 Python 3.12。
4. 不要修改 base/miniforge 全局环境。需要安装依赖时，优先在项目内创建虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

5. 如果某个依赖在 Python 3.12 下安装失败，应优先换用轻量兼容依赖或给出清晰说明，不要强行安装大型框架。
6. 每个阶段完成后必须实际运行检查命令，不要只口头声称检查通过。
7. 如果网络、GitHub、API key 或包安装导致某项测试失败，不要伪造通过；必须明确说明失败原因，并提供离线或 mock 替代测试。
8. mock mode 必须优先保证可演示；真实 LLM API 配置放在后面验证。
9. 除非我明确要求，不要自动下载大型数据集、checkpoint 或模型权重。
10. 除非我明确回复继续，不要进入下一阶段。

### Codex 阶段推进规则

你必须遵循如下交互节奏：

```text
完成阶段 N → 运行自检 → 输出指定格式的自检结果 → 停止
等待我回复“继续阶段 N+1” → 再开始下一阶段
```

即使某阶段全部检查通过，也不能主动继续下一阶段。

---

## 0. 项目总目标

构建一个面向科研新手的半自动论文复现助手。

用户输入：

1. 论文 PDF
2. GitHub 仓库链接
3. 硬件条件，例如 CPU / 单 GPU / 多 GPU
4. 复现目标，例如只理解论文、跑通 demo、最小训练实验、debug 报错

系统输出：

1. 论文核心信息摘要
2. 方法模块拆解
3. GitHub 仓库结构分析
4. 环境配置建议
5. 最小复现路线
6. 可执行的 `run.sh`
7. 实验 checklist
8. 报错日志分析与 debug 建议
9. 复现报告模板

项目定位：

> PaperPilot 不是简单的论文总结器，而是从“论文 + GitHub 仓库”到“可执行复现计划”的多智能体应用系统。

---

## 1. 核心功能范围

### 1.1 系统应该支持的功能

必须实现：

- 上传论文 PDF
- 解析 PDF 文本
- 输入 GitHub URL
- 自动 `git clone --depth 1`
- 扫描并分析仓库结构
- 识别关键文件：
  - `README.md`
  - `requirements.txt`
  - `environment.yml`
  - `setup.py`
  - `pyproject.toml`
  - `train.py`
  - `main.py`
  - `eval.py`
  - `test.py`
  - `demo.py`
  - `scripts/`
  - `configs/`
  - `examples/`
  - `notebooks/`
- 调用 LLM 生成：
  - 论文摘要
  - 方法模块拆解
  - 仓库分析报告
  - 环境配置命令
  - 最小复现计划
  - debug 建议
  - 复现报告
- 生成输出文件：
  - `outputs/reproduction_plan.md`
  - `outputs/run.sh`
  - `outputs/report.md`
- 提供 Streamlit Web 页面
- 支持用户粘贴报错日志并进行分析
- 支持轻量安全命令运行，例如：
  - `python --version`
  - `pip --version`
  - `python train.py --help`
  - `python main.py --help`
  - `python eval.py --help`
  - `python test.py --help`
  - `python demo.py --help`
  - `python examples/demo.py --help`

注意：`python demo.py` 和 `python examples/demo.py` 本体不允许默认自动运行。很多 demo 会下载数据、下载模型权重、访问网络或执行较重计算；必须由用户二次确认后才可运行。

### 1.2 系统不应该默认做的事情

不要默认执行：

- 自动下载大型数据集
- 自动训练完整模型
- 自动运行未知 shell 脚本
- 自动执行 `sudo`
- 自动删除文件
- 自动修改用户系统环境
- 自动执行高风险命令

如果检测到大型数据集需求，只生成说明和目录结构，不直接下载。

---

## 2. 技术栈要求

优先使用简单、稳定、容易展示的方案。

建议技术栈：

- Python 3.12.12（当前 WSL 环境；代码保持 Python 3.10+ 风格，但必须在 3.12.12 下通过语法检查）
- Streamlit
- PyMuPDF 或 pypdf
- pathlib / os / subprocess
- requests，可选
- openai / dashscope / deepseek SDK，任选一种或设计统一 LLM Client
- Markdown 输出
- 可选：python-dotenv

不要一开始引入过重框架。  
MVP 阶段不要使用 LangGraph、CrewAI 等复杂框架。  
先用清晰的 Python pipeline 实现多 Agent 流程。

---

## 3. 推荐项目结构

请按照下面结构创建项目：

```text
PaperPilot/
│
├── app.py                         # Streamlit 前端
├── main.py                        # 主流程入口
├── config.py                      # 配置文件
│
├── agents/
│   ├── __init__.py
│   ├── base_agent.py               # Agent 基类
│   ├── paper_reader_agent.py       # 论文阅读
│   ├── method_extractor_agent.py   # 方法拆解
│   ├── repo_clone_agent.py         # GitHub clone
│   ├── repo_analyzer_agent.py      # 仓库分析
│   ├── env_agent.py                # 环境配置
│   ├── experiment_agent.py         # 实验规划
│   ├── runner_agent.py             # 安全运行
│   ├── debug_agent.py              # 报错诊断
│   └── report_agent.py             # 报告生成
│
├── tools/
│   ├── __init__.py
│   ├── pdf_parser.py               # PDF 解析
│   ├── github_tool.py              # GitHub clone 工具
│   ├── repo_scanner.py             # 扫描代码仓库
│   ├── command_runner.py           # 安全运行命令
│   ├── llm_client.py               # LLM 调用封装
│   └── markdown_writer.py          # Markdown 输出工具
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
├── workspace/                      # clone 的仓库放这里
├── outputs/
│   ├── reproduction_plan.md
│   ├── run.sh
│   └── report.md
│
├── requirements.txt
└── README.md
```

---

## 4. 多智能体设计

请实现以下 Agent。  
每个 Agent 应该有明确职责，输入输出尽量结构化。

### 4.1 BaseAgent

文件：`agents/base_agent.py`

职责：

- 封装 Agent 名称
- 封装 system prompt
- 调用 LLM Client
- 返回文本结果
- 便于后续所有 Agent 继承

建议接口：

```python
class BaseAgent:
    def __init__(self, name: str, prompt_path: str, llm_client):
        ...

    def run(self, input_data: dict | str) -> str:
        ...
```

---

### 4.2 Paper Reader Agent

文件：`agents/paper_reader_agent.py`

职责：

从论文 PDF 文本中提取复现相关信息。

输出内容包括：

1. 论文标题
2. 研究任务
3. 输入与输出
4. 核心贡献
5. 方法概览
6. 使用的数据集
7. 评价指标
8. 关键实验设置
9. 复现时必须关注的细节

要求：

- 只基于论文内容回答
- 不要编造论文没有说明的内容
- 如果论文未明确说明，写“论文未明确说明”

---

### 4.3 Method Extractor Agent

文件：`agents/method_extractor_agent.py`

职责：

把论文方法拆解成工程实现模块。

输出内容包括：

1. 模型整体结构
2. 每个模块的输入输出
3. 损失函数
4. 训练流程
5. 推理流程
6. 最小复现必须实现的部分
7. 可暂时跳过的复杂部分
8. 复现难点

重点：

- 不要只做概念总结
- 要从工程实现角度描述
- 要告诉用户先实现什么、后实现什么

---

### 4.4 Repo Clone Agent

文件：`agents/repo_clone_agent.py`

职责：

自动 clone GitHub 仓库。

要求：

- 只接受 `github.com` 或 `www.github.com` 链接
- 使用 `git clone --depth 1`
- 仓库保存在 `workspace/`
- 如果仓库已存在，不重复 clone
- 返回本地仓库路径
- 捕获 clone 错误并返回清晰报错

安全要求：

- 不执行仓库中的任何代码
- 只 clone，不运行

---

### 4.5 Repo Analyzer Agent

文件：`agents/repo_analyzer_agent.py`

职责：

分析已经 clone 的仓库结构。

输入：

- 仓库扫描结果
- README 内容
- requirements / environment 文件内容
- 可能入口文件列表
- config 文件列表

输出：

1. 仓库主要结构
2. 依赖文件在哪里
3. 训练入口在哪里
4. 评估入口在哪里
5. demo 入口在哪里
6. 配置文件在哪里
7. README 推荐运行命令
8. 建议优先尝试的命令
9. 仓库复现风险

---

### 4.6 Environment Agent

文件：`agents/env_agent.py`

职责：

根据仓库依赖文件和用户硬件生成环境配置建议。

输出：

1. Python 版本建议
2. conda 环境创建命令
3. pip 安装命令
4. CUDA / PyTorch 风险提示
5. 可能缺失的 checkpoint 或数据
6. 路径配置注意事项

要求：

- 不要默认假设用户 GPU 无限
- 如果依赖文件缺失，要给出 fallback 安装建议
- 不要编造确定版本，除非文件中明确写出

---

### 4.7 Experiment Planner Agent

文件：`agents/experiment_agent.py`

职责：

生成分层复现路线。

必须包含：

```text
Level 0：运行 --help，确认入口可用
Level 1：运行官方 demo
Level 2：小数据 / 小 epoch smoke test
Level 3：尝试复现主实验
Level 4：尝试复现 ablation 或扩展实验
```

输出内容：

1. 最小复现步骤
2. 完整复现步骤
3. 数据准备说明
4. 训练命令
5. 评估命令
6. 实验 checklist
7. 资源不足时如何缩小实验规模
8. 推荐的 `run.sh`

---

### 4.8 Runner Agent

文件：`agents/runner_agent.py`

职责：

运行轻量、安全命令。

允许默认运行：

- `python --version`
- `pip --version`
- `python train.py --help`
- `python main.py --help`
- `python eval.py --help`
- `python test.py --help`
- `python demo.py --help`
- `python examples/demo.py --help`

不允许默认运行 `python demo.py` 或 `python examples/demo.py` 本体。真正运行 demo 必须由用户二次确认，并仍然需要 timeout 与安全检查。

禁止运行：

- `sudo`
- `rm -rf`
- `mkfs`
- `shutdown`
- `reboot`
- `curl | bash`
- `wget | bash`
- 未经用户确认的 `.sh` 脚本
- 默认完整训练命令

要求：

- 使用 subprocess
- 设置 timeout
- 捕获 stdout / stderr
- 返回 return code
- 不让命令无限运行
- `subprocess.run` 必须使用 list 参数，禁止 `shell=True`
- 使用 `shlex.split` 解析命令
- 以 allowlist 为主、blacklist 为辅
- 禁止命令中出现管道、重定向、分号、`&&`、`||` 等 shell 控制符
- `cwd` 必须限制在项目根目录或 `workspace/` 内

---

### 4.9 Debug Agent

文件：`agents/debug_agent.py`

职责：

根据运行命令、stdout、stderr、用户环境信息分析报错。

输出：

1. 报错直接原因
2. 可能根本原因
3. 如何验证判断
4. 推荐修改方案
5. 修改后的命令或代码片段
6. 下一步建议

要求：

- 优先给最可能原因
- 不要一次性输出大量无关建议
- 如果信息不足，说明还需要哪些信息

---

### 4.10 Report Agent

文件：`agents/report_agent.py`

职责：

生成最终复现报告。

报告结构：

1. 论文信息
2. 方法概述
3. 代码仓库分析
4. 环境配置
5. 数据准备
6. 运行命令
7. 实验 checklist
8. 遇到的问题
9. Debug 建议
10. 与原论文差异
11. 下一步计划

---

## 5. Prompt 文件要求

请在 `prompts/` 目录下创建每个 Agent 的 prompt。

### 5.1 `paper_reader_prompt.txt`

内容要求：

```text
你是论文阅读助手。请从论文文本中提取与复现相关的信息。

你需要输出：
1. 论文标题
2. 研究任务
3. 输入与输出
4. 核心贡献
5. 方法概览
6. 使用的数据集
7. 评价指标
8. 关键实验设置
9. 复现时必须关注的细节

要求：
- 只基于论文内容回答
- 如果论文没有说明，请写“论文未明确说明”
- 不要编造超参数
- 输出结构化 Markdown
```

### 5.2 `method_extractor_prompt.txt`

内容要求：

```text
你是机器学习工程师，负责把论文方法拆解成可实现模块。

请根据论文信息输出：
1. 模型整体结构
2. 每个模块的输入输出
3. 损失函数
4. 训练流程
5. 推理流程
6. 需要实现的核心代码文件
7. 最小复现必须实现的模块
8. 可以暂时跳过的模块
9. 复现难点

要求：
- 用工程实现视角解释
- 不要只做概念总结
- 标出哪些模块是最小复现必须实现的
```

### 5.3 `repo_analyzer_prompt.txt`

内容要求：

```text
你是代码仓库分析助手。请根据仓库结构、README、依赖文件和可能入口文件，分析这个仓库应该如何开始复现。

你需要输出：
1. 仓库功能概览
2. 关键目录和文件
3. 依赖安装方式
4. 训练入口
5. 评估入口
6. demo 入口
7. 配置文件
8. README 中推荐的运行命令
9. 建议优先尝试的最小命令
10. 仓库潜在复现风险

要求：
- 不要猜测不存在的文件
- 如果某类文件不存在，明确说明未找到
- 输出结构化 Markdown
```

### 5.4 `env_prompt.txt`

内容要求：

```text
你是环境配置助手。请根据仓库依赖文件、README 安装说明和用户硬件，生成复现环境配置方案。

你需要输出：
1. 推荐 Python 版本
2. conda 环境创建命令
3. pip 安装命令
4. CUDA / PyTorch 版本注意事项
5. 可能的版本冲突
6. 需要手动下载的模型权重或数据
7. 环境验证命令

要求：
- 不要编造依赖版本
- 如果依赖文件未说明版本，请说明需要用户确认
- 优先生成安全、可回滚的环境配置方案
```

### 5.5 `experiment_prompt.txt`

内容要求：

```text
你是实验规划助手。请根据论文信息、方法模块、代码仓库分析、环境配置和用户硬件，制定复现计划。

你需要输出：
1. Level 0：运行 --help，确认入口可用
2. Level 1：运行官方 demo
3. Level 2：小数据 / 小 epoch smoke test
4. Level 3：尝试复现主实验
5. Level 4：尝试复现 ablation 或扩展实验
6. 数据准备步骤
7. 训练命令
8. 评估命令
9. 实验 checklist
10. 如果资源不足，如何缩小实验规模
11. 推荐 run.sh 内容

要求：
- 命令要尽量具体
- 明确哪些路径需要用户手动修改
- 不要假设用户有无限 GPU
- 不要默认下载大型数据集
```

### 5.6 `debug_prompt.txt`

内容要求：

```text
你是论文复现 Debug 助手。用户会提供报错日志、运行命令和环境信息。

请你分析：
1. 报错的直接原因
2. 可能的根本原因
3. 如何验证你的判断
4. 推荐修改方案
5. 修改后的命令或代码片段
6. 下一步建议

要求：
- 优先给出最可能的原因
- 不要一次性给太多无关建议
- 如果信息不足，说明还需要哪些信息
```

### 5.7 `report_prompt.txt`

内容要求：

```text
你是复现报告生成助手。请根据论文分析、方法拆解、仓库分析、环境配置和实验计划，生成一份结构化复现报告。

报告需要包含：
1. 论文信息
2. 方法概述
3. 代码仓库分析
4. 环境配置
5. 数据准备
6. 推荐运行命令
7. 实验 checklist
8. 可能遇到的问题
9. Debug 建议
10. 与原论文设置的差异
11. 下一步计划

要求：
- 输出结构化 Markdown
- 内容要适合课程 project 展示
- 不要夸大系统能力
```

---

## 6. LLM Client 要求

请实现统一的 `tools/llm_client.py`。

要求：

- 默认实现 OpenAI-compatible Chat Completions 接口，便于后续兼容 OpenAI / DeepSeek / DashScope 等服务
- 支持从环境变量读取 API key
- 支持环境变量：`LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`、`LLM_MOCK_MODE`
- 模型名称可以在 `config.py` 中配置
- 提供统一接口：

```python
class LLMClient:
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        ...
```

如果没有 API key，系统不要崩溃。  
可以返回清晰提示：

```text
未检测到 LLM API key，请在 .env 或环境变量中配置。
```

为了方便本地测试，也可以提供 mock 模式：

```python
LLM_MOCK_MODE=True
```

mock 模式下返回固定示例结果，保证 Streamlit 页面可以运行。

---

## 7. 工具模块要求

### 7.1 PDF Parser

文件：`tools/pdf_parser.py`

功能：

- 接收 PDF 路径
- 提取文本
- 限制最大字符数，避免 prompt 过长
- 如果 PDF 无法解析，返回清晰错误

建议接口：

```python
def parse_pdf(pdf_path: str, max_chars: int = 50000) -> str:
    ...
```

---

### 7.2 GitHub Tool

文件：`tools/github_tool.py`

功能：

- 校验 GitHub URL
- clone 仓库
- 避免重复 clone
- 返回本地 repo path

建议接口：

```python
def is_valid_github_url(url: str) -> bool:
    ...

def clone_github_repo(github_url: str, workspace_dir: str = "workspace") -> Path:
    ...
```

clone 命令：

```bash
git clone --depth 1 <github_url> <repo_path>
```

实现要求：

- 必须使用 `subprocess.run([...], timeout=180)` 形式，禁止 `shell=True`
- 必须捕获 stdout / stderr
- clone 失败时返回清晰错误，不要抛出未捕获异常
- 仓库目录名需要 sanitize，不能直接拼接未经处理的 URL 字符串
- 自检时使用小型公开 GitHub 仓库，不要使用大型深度学习仓库

---

### 7.3 Repo Scanner

文件：`tools/repo_scanner.py`

功能：

扫描仓库并返回结构化信息。

需要识别：

- important files
- directories
- possible entrypoints
- config files
- README content
- requirements content
- environment content
- setup / pyproject content

建议接口：

```python
def scan_repo(repo_path: str | Path, max_file_chars: int = 12000) -> dict:
    ...
```

---

### 7.4 Command Runner

文件：`tools/command_runner.py`

功能：

安全运行命令。

要求：

- 命令 allowlist / blacklist 检查，必须以 allowlist 为主
- 设置 timeout
- 捕获 stdout / stderr
- 返回 dict

默认 allowlist 至少包含：

```python
ALLOWED_COMMANDS = [
    ["python", "--version"],
    ["pip", "--version"],
    ["python", "train.py", "--help"],
    ["python", "main.py", "--help"],
    ["python", "eval.py", "--help"],
    ["python", "test.py", "--help"],
    ["python", "demo.py", "--help"],
    ["python", "examples/demo.py", "--help"],
]
```

额外要求：

- 禁止 `shell=True`
- 使用 `shlex.split` 解析命令
- 禁止 `|`、`;`、`>`、`<`、`&&`、`||`
- 所有命令必须设置 timeout

建议接口：

```python
def is_safe_command(command: str) -> tuple[bool, str]:
    ...

def run_command(command: str, cwd: str | Path, timeout: int = 120) -> dict:
    ...
```

返回格式：

```python
{
    "command": command,
    "cwd": str(cwd),
    "returncode": result.returncode,
    "stdout": result.stdout[-4000:],
    "stderr": result.stderr[-4000:],
    "success": result.returncode == 0
}
```

---

### 7.5 Markdown Writer

文件：`tools/markdown_writer.py`

功能：

- 保存 `reproduction_plan.md`
- 保存 `run.sh`
- 保存 `report.md`

建议接口：

```python
def save_markdown(content: str, path: str | Path) -> None:
    ...

def save_shell_script(content: str, path: str | Path) -> None:
    ...
```

保存 `run.sh` 时注意加入：

```bash
#!/usr/bin/env bash
set -e
```

---

## 8. Streamlit 前端要求

文件：`app.py`

页面标题：

```text
PaperPilot：多智能体论文复现助手
```

页面分区：

### 8.1 输入区

包含：

- PDF 上传
- GitHub URL 输入
- 硬件条件选择：
  - CPU only
  - Single GPU
  - Multi GPU
- GPU 型号输入，例如 RTX 4090
- 复现目标选择：
  - 只理解论文
  - 跑通官方 demo
  - 最小训练实验
  - 复现主实验
  - Debug 报错

### 8.2 Agent 状态区

运行过程中显示：

- Paper Reader Agent 正在分析论文
- Method Extractor Agent 正在拆解方法
- Repo Clone Agent 正在 clone 仓库
- Repo Analyzer Agent 正在分析代码
- Environment Agent 正在生成环境配置
- Experiment Planner Agent 正在生成复现计划
- Report Agent 正在生成报告

### 8.3 输出区

显示：

- 论文摘要
- 方法拆解
- 仓库分析
- 环境配置
- 实验计划
- run.sh
- report.md

### 8.4 Runner 区

按钮：

- 运行 `python --version`
- 运行 `pip --version`
- 运行候选入口文件 `--help`
- demo 本体只显示为“需要二次确认”的可选操作，不作为默认自动运行

显示：

- command
- stdout
- stderr
- return code

### 8.5 Debug 区

文本框：

- 用户粘贴报错日志

按钮：

- 分析报错

输出：

- Debug Agent 诊断结果

---

## 9. 主流程要求

文件：`main.py`

实现核心函数：

```python
def run_paperpilot(
    pdf_path: str,
    github_url: str,
    hardware: str,
    gpu_info: str,
    goal: str
) -> dict:
    ...
```

返回 dict，至少包含：

```python
{
    "paper_info": ...,
    "method_info": ...,
    "repo_path": ...,
    "repo_info": ...,
    "env_plan": ...,
    "experiment_plan": ...,
    "report": ...,
    "run_sh": ...
}
```

每一步都要有错误处理。

如果某一步失败，例如 clone 失败，不要让整个程序直接崩溃。  
应返回清晰错误，并尽量保留前面已经完成的结果。

---

## 10. 分阶段开发要求

请严格按照下面阶段实现。  
**每完成一个阶段，必须先检查、测试并输出检查结果。检查通过后再进入下一阶段。**

---

### 阶段 1：项目骨架与基础配置

任务：

1. 创建项目根目录 `PaperPilot/`，并在该目录内创建项目结构
2. 创建 `requirements.txt`
3. 创建 `config.py`
4. 创建 `README.md`
5. 创建空的 `agents/`、`tools/`、`prompts/`、`outputs/`、`workspace/`

检查要求：

- 项目目录结构正确
- 所有必要文件存在
- `python -m py_compile` 不报错
- README 能说明项目基本用途

完成后请输出：

```text
阶段 1 完成。
自检结果：
- 目录结构：通过 / 不通过
- 必要文件：通过 / 不通过
- Python 语法检查：通过 / 不通过
- 发现的问题：
- 下一步：
```

只有阶段 1 检查通过后，才能进入阶段 2。

---

### 阶段 2：实现工具模块

任务：

1. 实现 `pdf_parser.py`
2. 实现 `github_tool.py`
3. 实现 `repo_scanner.py`
4. 实现 `command_runner.py`
5. 实现 `markdown_writer.py`
6. 实现 `llm_client.py`，包含 mock mode

检查要求：

- 能解析一个本地 PDF，或者在没有 PDF 时返回清晰错误
- 能校验 GitHub URL
- 能 clone 一个小型公开 GitHub 仓库；如果网络失败，应明确标记为网络问题并提供离线 scanner 测试
- 能扫描仓库结构
- 能拒绝危险命令，例如 `rm -rf /`
- 能运行安全命令，例如 `python --version`
- mock mode 下不需要 API key 也能运行

完成后请输出：

```text
阶段 2 完成。
自检结果：
- PDF parser：通过 / 不通过
- GitHub clone：通过 / 不通过
- Repo scanner：通过 / 不通过
- Command safety：通过 / 不通过
- LLM mock mode：通过 / 不通过
- 发现的问题：
- 下一步：
```

只有阶段 2 检查通过后，才能进入阶段 3。

---

### 阶段 3：实现 Agent 层

任务：

1. 实现 `BaseAgent`
2. 实现所有 Agent 文件
3. 创建所有 prompt 文件
4. 每个 Agent 使用统一 LLM Client
5. 每个 Agent 的输入输出可打印、可调试

检查要求：

- 每个 Agent 能在 mock mode 下运行
- Agent prompt 能正确加载
- Agent 出错时返回清晰错误
- 不因为某个 Agent 失败导致整个程序崩溃

完成后请输出：

```text
阶段 3 完成。
自检结果：
- BaseAgent：通过 / 不通过
- Paper Reader Agent：通过 / 不通过
- Method Extractor Agent：通过 / 不通过
- Repo Analyzer Agent：通过 / 不通过
- Environment Agent：通过 / 不通过
- Experiment Planner Agent：通过 / 不通过
- Debug Agent：通过 / 不通过
- Report Agent：通过 / 不通过
- 发现的问题：
- 下一步：
```

只有阶段 3 检查通过后，才能进入阶段 4。

---

### 阶段 4：实现主流程 main.py

任务：

1. 实现 `run_paperpilot`
2. 串联 PDF parser、Repo clone、Repo scanner、各 Agent
3. 生成 `outputs/reproduction_plan.md`
4. 生成 `outputs/run.sh`
5. 生成 `outputs/report.md`
6. 做错误处理和中间结果保存

检查要求：

- 在 mock mode 下可以完整跑通
- 没有 PDF 时能提示用户
- GitHub URL 错误时能提示用户
- clone 失败时能保留已有结果
- 输出文件能成功生成

完成后请输出：

```text
阶段 4 完成。
自检结果：
- 主流程 mock run：通过 / 不通过
- 错误处理：通过 / 不通过
- 输出 reproduction_plan.md：通过 / 不通过
- 输出 run.sh：通过 / 不通过
- 输出 report.md：通过 / 不通过
- 发现的问题：
- 下一步：
```

只有阶段 4 检查通过后，才能进入阶段 5。

---

### 阶段 5：实现 Streamlit 前端

任务：

1. 实现 `app.py`
2. 支持 PDF 上传
3. 支持 GitHub URL 输入
4. 支持硬件条件选择
5. 支持复现目标选择
6. 调用 `run_paperpilot`
7. 显示每个 Agent 的输出
8. 显示生成的 run.sh 和 report
9. 支持 Debug 日志输入

检查要求：

- `streamlit run app.py` 可以启动
- 页面布局清晰
- 上传 PDF 后能保存到临时目录
- 点击 Analyze 后能调用主流程
- mock mode 下完整页面可演示

完成后请输出：

```text
阶段 5 完成。
自检结果：
- Streamlit 启动：通过 / 不通过
- PDF 上传：通过 / 不通过
- 主流程调用：通过 / 不通过
- 输出展示：通过 / 不通过
- Debug 区：通过 / 不通过
- 发现的问题：
- 下一步：
```

只有阶段 5 检查通过后，才能进入阶段 6。

---

### 阶段 6：实现 Runner 与 Debug 闭环

任务：

1. 在前端增加安全命令运行按钮
2. 支持运行 `python --version`
3. 支持对识别出的入口文件运行 `--help`
4. 不默认运行 demo 本体；如果实现 demo 按钮，必须加入二次确认提示
5. 捕获 stdout / stderr
6. 如果命令失败，自动调用 Debug Agent
7. 用户也可以手动粘贴日志调用 Debug Agent

检查要求：

- 危险命令会被拒绝
- 安全命令可以运行
- 命令超时会被终止
- stderr 能传给 Debug Agent
- Debug Agent 能输出建议

完成后请输出：

```text
阶段 6 完成。
自检结果：
- 安全命令运行：通过 / 不通过
- 危险命令拦截：通过 / 不通过
- timeout：通过 / 不通过
- 自动 debug：通过 / 不通过
- 手动 debug：通过 / 不通过
- 发现的问题：
- 下一步：
```

只有阶段 6 检查通过后，才能进入阶段 7。

---

### 阶段 7：最终整理与课程展示材料

任务：

1. 更新 README
2. 加入项目介绍
3. 加入安装方式
4. 加入运行方式
5. 加入 demo 流程
6. 加入安全策略说明
7. 加入系统架构图，文本图即可
8. 准备一个示例输入
9. 确保 mock mode 下可以无 API key 演示
10. 确保真实 API key 模式下可以调用 LLM

检查要求：

- README 完整
- 一键启动说明清楚
- demo 流程清楚
- mock mode 可演示
- 真实 LLM 模式有配置说明
- 输出文件路径清楚

完成后请输出：

```text
阶段 7 完成。
自检结果：
- README：通过 / 不通过
- 安装说明：通过 / 不通过
- 运行说明：通过 / 不通过
- demo 流程：通过 / 不通过
- mock mode：通过 / 不通过
- 真实 API 配置：通过 / 不通过
- 发现的问题：
- 项目最终状态：
```

---

## 11. 安全策略要求

因为本项目会 clone GitHub 仓库并可选运行命令，所以必须实现安全策略。

必须做到：

1. 只接受 GitHub URL
2. clone 使用 `--depth 1`
3. 仓库隔离到 `workspace/`
4. 默认不运行训练脚本
5. 运行命令需要用户点击按钮确认
6. 默认只运行轻量命令，且优先只运行 `--help` / version 命令
7. 禁止危险命令，禁止 `shell=True`
8. 所有命令设置 timeout
9. 命令安全策略必须以 allowlist 为主、blacklist 为辅
10. 捕获输出，不让程序无限运行
11. 不自动下载大型数据集

`command_runner.py` 中必须至少拦截以下关键词：

```text
sudo
rm -rf
mkfs
shutdown
reboot
curl
wget
chmod 777
:(){:|:&};:
```

如果命令被拒绝，要返回原因。

---

## 12. 输出文件内容要求

### 12.1 `outputs/reproduction_plan.md`

必须包含：

```text
# Reproduction Plan

## 1. Paper Summary
## 2. Method Breakdown
## 3. Repository Analysis
## 4. Environment Setup
## 5. Minimal Reproduction Plan
## 6. Commands
## 7. Checklist
## 8. Risks
```

### 12.2 `outputs/run.sh`

必须包含：

```bash
#!/usr/bin/env bash
set -e

# TODO: activate environment
# TODO: install dependencies
# TODO: run minimal demo or help command
```

不要默认写完整训练命令作为直接执行项。  
完整训练命令可以写成注释。

### 12.3 `outputs/report.md`

必须包含：

```text
# PaperPilot Reproduction Report

## Paper Information
## Method Overview
## Code Repository
## Environment
## Data Preparation
## Commands
## Debug Notes
## Difference from Original Paper
## Next Steps
```

---

## 13. 代码质量要求

请保持代码质量：

- 函数要有类型标注
- 关键函数要有 docstring
- 错误处理要清晰
- 不要写硬编码绝对路径
- 所有路径用 `pathlib.Path`
- 不要在代码中写死 API key
- 配置从环境变量或 `config.py` 读取
- 保持模块化
- 不要把所有逻辑写在 `app.py`
- 不要一次性写超长函数

---

## 14. 测试与自检要求

至少实现或手动运行以下检查：

```bash
cd PaperPilot
python -m py_compile app.py main.py config.py
python -m py_compile agents/*.py
python -m py_compile tools/*.py
```

测试 GitHub URL 校验：

```python
assert is_valid_github_url("https://github.com/user/repo") is True
assert is_valid_github_url("https://google.com") is False
```

测试危险命令拦截：

```python
assert is_safe_command("rm -rf /")[0] is False
assert is_safe_command("python --version")[0] is True
```

测试 mock LLM：

```python
client = LLMClient(mock_mode=True)
result = client.generate("system", "user")
assert isinstance(result, str)
assert len(result) > 0
```

---

## 15. 最终交付物

最终需要交付：

```text
1. 完整项目代码
2. README.md
3. requirements.txt
4. Streamlit app.py
5. 多 Agent 代码
6. prompts 文件
7. 工具模块
8. 示例 outputs/
9. 可运行 demo
10. 自检报告
```

---

## 16. 最终项目介绍文本

请把以下介绍放进 README：

```text
PaperPilot 是一个面向科研新手的多智能体论文复现助手。传统论文复现通常需要研究者反复阅读论文、查找代码、配置环境、理解实验设置并解决报错，过程复杂且容易失败。本项目将论文复现流程拆分为论文阅读、方法拆解、代码仓库分析、环境配置、实验规划、运行诊断和报告生成等多个阶段，并设计多个专业 Agent 协作完成这些任务。用户只需要上传论文 PDF 并提供 GitHub 仓库链接，系统即可生成结构化的复现路线、实验 checklist、运行命令和 debug 建议，从而降低论文复现的启动成本。
```

---

## 17. 重要提醒

请始终遵守以下原则：

1. **分阶段完成，不要一次性写完整项目。每个阶段结束后必须停止，等待我回复继续。**
2. **每个阶段完成后必须先自检。**
3. **自检不通过不要进入下一阶段。**
4. **优先保证 MVP 可运行，而不是堆很多复杂功能。**
5. **不要默认运行危险命令。**
6. **不要默认训练完整模型。**
7. **不要默认下载大型数据集。**
8. **所有 API key 必须从环境变量读取。**
9. **mock mode 必须可用，保证没有 API key 也能演示。**
10. **输出要适合课程 project 展示。**

---

## 18. 请现在开始

请从阶段 1 开始实现。

每个阶段结束时，必须按照指定格式输出自检结果。  
如果某个检查不通过，请先修复，不要继续下一阶段。
