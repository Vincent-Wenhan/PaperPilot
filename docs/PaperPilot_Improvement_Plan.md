# PaperPilot 改进计划

## 0. 项目定位

PaperPilot 当前已经具备比较完整的 multi-agent workflow：

```text
Paper PDF + optional GitHub repo
        ↓
Paper understanding
        ↓
Repository analysis
        ↓
Reproduction planning
        ↓
Safe command / report generation
        ↓
Productize mode: mock-first Streamlit prototype
```

这个项目不是简单的 PDF Chatbot，而是一个面向论文复现规划和产品原型生成的 Agent 系统。

后续改进的目标不是重写项目，而是提高以下几个方面：

1. 工程可信度；
2. Agent 输出稳定性；
3. Productize Mode 的差异化；
4. Runner 的实用性和安全边界；
5. 项目展示效果；
6. 简历和课程项目完成度。

---

## 1. P0：加入 CI，保证项目可验证

### 1.1 目标

每次 push 到 GitHub 后，自动检查：

- 依赖能否安装；
- Python 文件是否有语法错误；
- 测试是否能通过。

这样可以让别人看到这个 repo 是可运行、可维护的，而不是只写了 README 的 demo。

### 1.2 新增文件

新建：

```text
.github/workflows/ci.yml
```

内容：

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Check Python syntax
        run: |
          python -m py_compile app.py main.py config.py
          python -m py_compile agents/*.py
          python -m py_compile tools/*.py
          python -m py_compile productize/*.py

      - name: Run tests
        run: |
          pytest -q
```

### 1.3 注意事项

如果目前 `tests/` 里的测试还不完整，可以先临时改成：

```yaml
      - name: Run tests
        run: |
          pytest -q || true
```

但不建议长期保留 `|| true`。最终还是应该让测试真实通过。

---

## 2. P0：补充最小测试

### 2.1 目标

先不追求覆盖所有 Agent，只需要保证核心工具函数和基础 pipeline 不会轻易坏掉。

建议优先测试：

```text
tools/pdf_parser.py
tools/repo_scanner.py
tools/command_runner.py
config.py
```

### 2.2 推荐测试文件结构

```text
tests/
  test_config.py
  test_repo_scanner.py
  test_command_runner.py
  test_pdf_parser.py
```

### 2.3 示例：测试安全命令 Runner

```python
from tools.command_runner import is_command_allowed

def test_allow_python_version():
    assert is_command_allowed("python --version") is True

def test_block_dangerous_command():
    assert is_command_allowed("rm -rf /") is False

def test_block_pip_install():
    assert is_command_allowed("pip install torch") is False
```

如果当前函数名不是 `is_command_allowed`，按实际代码调整。

---

## 3. P1：Agent 输出结构化

### 3.1 当前问题

目前大多数 Agent 输出应该还是自然语言或 Markdown。  
这种方式适合 demo，但在多 Agent pipeline 中容易出现：

- 格式不稳定；
- 下游 Agent 难以复用；
- 前端展示困难；
- 自动测试困难；
- LLM 输出漂移。

### 3.2 改进目标

把关键 Agent 的输出改成 JSON schema 或 Pydantic model。

推荐流程：

```text
LLM raw output
    ↓
JSON parser
    ↓
Pydantic validation
    ↓
如果失败，自动 retry
    ↓
返回结构化对象
```

### 3.3 新增目录

建议新增：

```text
schemas/
  paper_schema.py
  repo_schema.py
  product_schema.py
  pipeline_schema.py
```

### 3.4 示例：Paper Summary Schema

```python
from pydantic import BaseModel, Field
from typing import List, Optional


class PaperSummary(BaseModel):
    title: Optional[str] = None
    task: str = Field(default="")
    problem: str = Field(default="")
    contributions: List[str] = Field(default_factory=list)
    method_summary: str = Field(default="")
    datasets: List[str] = Field(default_factory=list)
    metrics: List[str] = Field(default_factory=list)
    training_details: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
```

### 3.5 示例：Repo Analysis Schema

```python
from pydantic import BaseModel, Field
from typing import List


class RepoAnalysis(BaseModel):
    framework: str = "unknown"
    task_type: str = "unknown"
    training_entrypoints: List[str] = Field(default_factory=list)
    inference_entrypoints: List[str] = Field(default_factory=list)
    config_files: List[str] = Field(default_factory=list)
    dependency_files: List[str] = Field(default_factory=list)
    dataset_requirements: List[str] = Field(default_factory=list)
    checkpoint_requirements: List[str] = Field(default_factory=list)
    risk_level: str = "medium"
    notes: List[str] = Field(default_factory=list)
```

### 3.6 BaseAgent 可加入的方法

可以在 `BaseAgent` 中增加类似函数：

```python
import json
from pydantic import BaseModel, ValidationError


def parse_json_response(raw_text: str, schema: type[BaseModel]):
    try:
        data = json.loads(raw_text)
        return schema.model_validate(data), None
    except (json.JSONDecodeError, ValidationError) as e:
        return None, str(e)
```

后面可以做自动 retry。示例中不要直接把复杂修复 prompt 写死在主逻辑里，建议单独封装成 `repair_json_output()`。

---

## 4. P1：拆分 main.py 的 orchestration

### 4.1 当前问题

`main.py` 是核心调度文件，功能比较集中。  
它可以工作，但长期维护会变得困难。

### 4.2 推荐拆分结构

新增：

```text
pipeline/
  __init__.py
  reproduce_pipeline.py
  productize_pipeline.py
  repository_stage.py
  output_builder.py
  result_schema.py
```

### 4.3 拆分原则

#### reproduce_pipeline.py

负责论文复现链路：

```text
parse paper
run paper reader
run method extractor
analyze repo
generate env plan
generate experiment plan
generate report
```

#### productize_pipeline.py

负责产品化链路：

```text
find product opportunities
select MVP idea
generate adapter plan
generate frontend plan
create mock Streamlit app
generate test report
```

#### repository_stage.py

负责 GitHub repo 相关逻辑：

```text
clone repo
scan repo
summarize structure
detect entrypoints
detect requirements
```

#### output_builder.py

负责保存输出：

```text
write markdown report
write JSON artifacts
write run scripts
write generated app
```

### 4.4 目标效果

最后 `main.py` 只保留高层入口：

```python
from pipeline.reproduce_pipeline import run_reproduce_pipeline
from pipeline.productize_pipeline import run_productize_pipeline


def run_paperpilot(args):
    if args.goal == "reproduce":
        return run_reproduce_pipeline(args)
    elif args.goal == "productize":
        return run_productize_pipeline(args)
    else:
        raise ValueError(f"Unknown goal: {args.goal}")
```

这样代码结构会更清楚，也更像正式工程项目。

---

## 5. P1：强化 Runner 安全策略

### 5.1 当前情况

现在 Runner 采用严格 allowlist 策略，只允许非常有限的命令，例如：

```text
python --version
pip --version
python xxx.py --help
```

这个设计的优点是非常安全，适合默认模式。  
但是实际做论文复现时会有点死，因为很多 repo 至少需要：

- 查看 help；
- 检查依赖；
- 运行轻量 demo；
- 执行 dry-run；
- 创建临时环境；
- 用户确认后执行特定命令。

因此建议保留默认安全模式，同时增加更灵活的执行模式。

### 5.2 推荐三种 Runner 模式

```text
Safe Mode
  默认模式，只跑 allowlist 命令，适合无人工确认的自动流程。

Review Mode
  LLM 可以生成候选命令，但必须展示给用户确认。
  用户确认后才执行。

Sandbox Mode
  在 Docker 或 conda 临时环境中执行命令。
  适合真实复现实验，但需要隔离文件系统、限制网络和资源。
```

### 5.3 推荐配置项

可以在 `config.py` 或 `.env` 中加入：

```python
RUNNER_MODE = "safe"  # safe / review / sandbox
RUNNER_TIMEOUT_SECONDS = 60
RUNNER_REQUIRE_CONFIRMATION = True
RUNNER_WORKDIR_ISOLATION = True
```

如果用环境变量：

```text
PAPERPILOT_RUNNER_MODE=safe
PAPERPILOT_RUNNER_TIMEOUT_SECONDS=60
PAPERPILOT_REQUIRE_CONFIRMATION=true
```

### 5.4 Safe Mode

Safe Mode 是默认模式。

特点：

- 只允许 allowlist；
- 不允许安装包；
- 不允许删除文件；
- 不允许访问危险路径；
- 不允许执行任意 shell；
- 适合网页 demo 和课程展示。

示例 allowlist：

```python
SAFE_COMMANDS = [
    ["python", "--version"],
    ["pip", "--version"],
]

SAFE_PATTERNS = [
    r"^python\s+[\w./-]+\.py\s+--help$",
    r"^python\s+-m\s+[\w.]+\s+--help$",
]
```

### 5.5 Review Mode

Review Mode 适合提升实用性。

流程：

```text
Agent 生成候选命令
        ↓
Runner 做危险命令检测
        ↓
前端展示命令、风险、说明
        ↓
用户点击 Confirm
        ↓
Runner 执行命令
        ↓
保存 stdout / stderr / exit code
```

命令展示建议包括：

```json
{
  "command": "python train.py --help",
  "purpose": "Inspect training arguments",
  "risk_level": "low",
  "requires_confirmation": true,
  "blocked_reason": null
}
```

对于中高风险命令，即使用户确认，也可以继续阻止。

例如：

```text
rm -rf
sudo
curl | bash
wget ... | sh
chmod -R 777
pip install from unknown URL
access ~/.ssh
access system directories
```

### 5.6 Sandbox Mode

Sandbox Mode 适合真实复现实验。

建议第一版不要做太重，可以先支持 conda sandbox：

```text
创建临时工作目录
复制 repo 到 sandbox dir
限制 timeout
执行命令
保存日志
退出后不自动删除，方便 debug
```

后续再支持 Docker：

```text
docker run --rm
  -v sandbox_dir:/workspace
  -w /workspace
  --network none 或 restricted
  --memory 8g
  --cpus 4
  image_name
  command
```

### 5.7 Runner 执行结果结构

建议统一保存：

```python
from pydantic import BaseModel
from typing import Optional


class CommandResult(BaseModel):
    command: str
    mode: str
    executed: bool
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    timeout: bool = False
    risk_level: str = "unknown"
    blocked_reason: Optional[str] = None
```

这样 Report Agent 可以引用真实执行结果，而不是只生成文字建议。

### 5.8 Runner 风险分级

建议加入风险分级：

```text
low
  python --version
  pip --version
  python xxx.py --help
  ls / dir
  cat README.md / type README.md

medium
  python demo.py
  python eval.py --dry-run
  pip install -r requirements.txt
  conda env create -f environment.yml

high
  python train.py
  downloading external weights
  running unknown shell scripts
  commands requiring GPU
  commands writing many files

blocked
  rm -rf
  sudo
  chmod/chown system paths
  curl | bash
  wget | sh
  accessing ~/.ssh or credentials
```

### 5.9 前端展示建议

在 Streamlit 里可以新增一个 Runner panel：

```text
Generated command
Purpose
Risk level
Mode
Confirm / Reject button
Execution output
stdout
stderr
exit code
```

这样项目会更像真正的人机协作 Agent，而不是 LLM 自己偷偷执行命令。

### 5.10 推荐实现顺序

```text
Step 1：保留现有 Safe Mode
Step 2：加入 runner_mode 参数
Step 3：加入 CommandPlan / CommandResult schema
Step 4：实现 Review Mode 的 confirm gate
Step 5：保存所有命令日志
Step 6：后续再做 Sandbox Mode
```

### 5.11 价值

这个改进可以让 PaperPilot 的定位更清楚：

```text
不是完全禁止执行命令；
也不是危险地自动执行任意命令；

而是：

默认安全，
需要时人工确认，
更复杂时进入隔离环境。
```

这对 Agent 项目非常加分，因为它体现了：

- safety-aware agent design；
- human-in-the-loop；
- tool execution governance；
- reproducibility engineering；
- real-world LLM application design。

---

## 6. P1：强化 Productize Mode 的评分逻辑

### 6.1 当前优点

Productize Mode 是 PaperPilot 的亮点。  
它不只是总结论文，而是尝试把论文方法转化成一个可展示的产品原型。

这个方向比普通论文助手更有辨识度。

### 6.2 当前可改进点

Product opportunity 如果只是 LLM brainstorming，容易显得泛。  
建议加入明确的评分体系，让 Product Agent 更像一个真正的产品决策模块。

### 6.3 推荐评分维度

每个产品机会输出时，增加以下字段：

```json
{
  "idea_name": "",
  "target_user": "",
  "core_value": "",
  "technical_feasibility": 0,
  "demo_feasibility": 0,
  "model_availability": 0,
  "data_requirement": 0,
  "integration_risk": 0,
  "user_value": 0,
  "course_presentation_value": 0,
  "overall_score": 0,
  "reason": ""
}
```

评分范围建议为 1 到 5。

### 6.4 Product Opportunity Schema

```python
from pydantic import BaseModel, Field
from typing import List


class ProductOpportunity(BaseModel):
    idea_name: str
    target_user: str
    core_value: str
    technical_feasibility: int = Field(ge=1, le=5)
    demo_feasibility: int = Field(ge=1, le=5)
    model_availability: int = Field(ge=1, le=5)
    data_requirement: int = Field(ge=1, le=5)
    integration_risk: int = Field(ge=1, le=5)
    user_value: int = Field(ge=1, le=5)
    course_presentation_value: int = Field(ge=1, le=5)
    overall_score: float
    reason: str


class ProductOpportunityList(BaseModel):
    opportunities: List[ProductOpportunity]
```

### 6.5 推荐排序公式

```python
overall_score = (
    technical_feasibility * 0.20
    + demo_feasibility * 0.20
    + model_availability * 0.15
    + user_value * 0.20
    + course_presentation_value * 0.15
    - integration_risk * 0.10
)
```

其中 `data_requirement` 可以反向处理：数据要求越低，分数越高。

---

## 7. P1：突出 Mock-first 设计

### 7.1 为什么重要

PaperPilot 的一个重要优点是边界清楚：

- 不宣称自动完整复现论文；
- 不宣称自动集成任意模型；
- 先生成 mock-first 原型；
- 真实模型接入需要人工 review。

这比夸大式 Agent 项目更可信。

### 7.2 README 顶部建议增加一句

```text
PaperPilot is a mock-first, safety-bounded multi-agent system for turning research papers into reproduction plans and demonstrable product prototypes.
```

中文理解：

```text
PaperPilot 是一个 mock-first、安全边界明确的多智能体系统，用于将研究论文转化为复现计划和可演示的产品原型。
```

### 7.3 README 里建议新增小节

```markdown
## Why Mock-first?

Many research repositories are difficult to run directly because of missing checkpoints,
large datasets, environment conflicts, or undocumented preprocessing steps.

PaperPilot therefore uses a mock-first productization strategy:

1. Understand the paper and optional repository.
2. Identify a feasible product scenario.
3. Generate a clean interface and adapter boundary.
4. Use mock outputs by default.
5. Leave real model integration as a reviewed engineering step.

This makes the generated prototype safe, fast to run, and suitable for course demos or early product validation.
```

---

## 8. P2：加强 Repo Analyzer

### 8.1 当前功能

当前 Repo Analyzer 已经可以扫描：

- README；
- requirements；
- environment；
- setup；
- entrypoints；
- configs。

这是一个合理的静态分析起点。

### 8.2 建议增强

增加更结构化的 repo evidence：

```json
{
  "repo_name": "",
  "detected_framework": "",
  "main_language": "",
  "has_training_code": true,
  "has_inference_code": true,
  "has_pretrained_weights": false,
  "has_dataset_script": false,
  "entrypoints": [],
  "config_files": [],
  "dependency_files": [],
  "important_modules": [],
  "reproduction_risks": []
}
```

### 8.3 可以检测的模式

#### Framework

```text
torch
pytorch_lightning
tensorflow
keras
jax
sklearn
```

#### Config system

```text
hydra
argparse
yaml
json
toml
```

#### Common entrypoints

```text
train.py
main.py
run.py
test.py
eval.py
inference.py
demo.py
app.py
```

#### Risk signals

```text
missing requirements
no README
no checkpoint link
hard-coded paths
large dataset required
CUDA-specific extension
custom C++ / CUDA ops
```

---

## 9. P2：增加 OCR / 表格 / 公式解析能力

### 9.1 当前问题

很多论文 PDF 的关键信息不只在正文里，还在：

- 表格；
- 公式；
- 图注；
- 伪代码；
- scanned PDF 图片层。

如果只靠普通文本提取，可能会漏掉训练设置、指标、消融实验和方法细节。

### 9.2 推荐改进路线

分阶段做，不要一次做太复杂。

#### Stage 1：检测 PDF 文本质量

在 `pdf_parser.py` 里加入：

```text
如果提取文本长度太短
或者平均每页字符数太少
则标记为 scanned_or_low_text_pdf
```

#### Stage 2：图注抽取

优先找：

```text
Figure
Fig.
Table
Algorithm
```

把相关段落单独保存给 Method Agent。

#### Stage 3：OCR fallback

可以后续接入：

```text
pytesseract
PaddleOCR
docling
marker
nougat
```

早期不建议直接做太重，先把接口留出来即可。

### 9.3 推荐输出结构

```json
{
  "main_text": "",
  "figures": [],
  "tables": [],
  "algorithms": [],
  "equations": [],
  "warnings": []
}
```

---

## 10. P2：增加 Demo Case 和截图

### 10.1 当前问题

README 很完整，但如果没有具体 example，别人需要自己上传 PDF 才能理解项目效果。

### 10.2 建议新增目录

```text
examples/
  README.md
  sample_input.md
  sample_reproduction_plan.md
  sample_product_spec.md
  sample_generated_app/
  screenshots/
    upload_page.png
    agent_progress.png
    report_page.png
    generated_app.png
```

### 10.3 推荐 example 选择

选择一个小型、容易理解、不需要复杂环境的论文或 repo。  
不要选太大的 medical image / diffusion 项目，否则别人很难验证。

推荐标准：

```text
repo 小
README 清楚
有 requirements
有 train / eval / demo 入口
不依赖大型私有数据
不需要复杂 CUDA extension
```

### 10.4 README 中加入

```markdown
## Example Output

We provide a sample run in `examples/`, including:

- parsed paper summary
- reproduction plan
- environment checklist
- generated run script
- product opportunity report
- mock-first Streamlit prototype
```

---

## 11. P2：GitHub 项目展示优化

### 11.1 GitHub About

当前仓库可以补充 description 和 topics。

#### Description

```text
Multi-agent assistant for paper reproduction planning and mock-first research-to-product prototyping.
```

#### Topics

```text
llm-agent
multi-agent
paper-reproduction
research-assistant
streamlit
openai-compatible
product-prototype
paper-to-product
```

### 11.2 README badge

等 CI 加好之后，在 README 顶部加入：

```markdown
![CI](https://github.com/Vincent-Wenhan/PaperPilot/actions/workflows/ci.yml/badge.svg)
```

### 11.3 README 推荐开头结构

```markdown
# PaperPilot

Mock-first, safety-bounded multi-agent system for turning research papers into reproduction plans and demonstrable product prototypes.

![CI](...)

## Features

- Paper understanding from PDF
- Optional GitHub repository analysis
- Reproduction planning
- Safe command generation
- Productize mode
- Mock-first Streamlit prototype generation
```

---

## 12. 推荐开发顺序

### Phase 1：工程可信度

优先完成：

```text
1. 加 CI
2. 补最小 tests
3. README 加 badge
4. GitHub About + topics
```

预计改动小，但展示效果明显。

### Phase 2：Runner 实用性增强

继续做：

```text
1. 保留现有 Safe Mode
2. 加 runner_mode 配置
3. 加 CommandPlan / CommandResult schema
4. 实现 Review Mode 的用户确认机制
5. 保存命令执行日志
6. 后续再实现 Sandbox Mode
```

这一步非常适合作为 Agent 工程亮点。

### Phase 3：Agent 稳定性

继续做：

```text
1. 新增 schemas/
2. 给关键 Agent 加 JSON output
3. 加 validation + retry
4. 保存 structured JSON artifacts
```

这一步能让项目从“LLM demo”变成“Agent workflow”。

### Phase 4：代码结构整理

继续做：

```text
1. 拆分 main.py
2. 新增 pipeline/
3. 分离 reproduce pipeline 和 productize pipeline
4. 分离 output builder
```

这一步提升可维护性。

### Phase 5：产品化亮点强化

最后做：

```text
1. Product opportunity scoring
2. Mock-first adapter boundary
3. Example case
4. Demo screenshots
```

这一步主要提升展示和简历价值。

---

## 13. 最终目标

改完之后，PaperPilot 应该能体现以下特点：

```text
不是 PDF chatbot
不是简单 prompt demo
不是夸大的自动复现工具

而是：

一个 mock-first、安全边界明确、工程化的 multi-agent research assistant，
可以把论文和可选代码仓库转化成：
1. 复现计划；
2. 环境检查；
3. 实验建议；
4. 安全运行脚本；
5. human-in-the-loop 命令执行；
6. 产品机会分析；
7. 可演示的 Streamlit 原型。
```

这个定位适合：

- 人工智能大模型导论课程项目；
- 简历上的 Agent 开发项目；
- 面试时讲 multi-agent workflow；
- 展示 LLM application engineering 能力；
- 展示 safety-aware tool execution 设计能力。

---

## 14. 简历表述建议

英文版本：

```text
PaperPilot: Multi-Agent Research Paper Reproduction and Productization Assistant

Built a mock-first, safety-bounded multi-agent system that parses research papers,
analyzes optional GitHub repositories, generates structured reproduction plans,
and creates Streamlit-based product prototypes.

Designed a human-in-the-loop command runner with Safe Mode, Review Mode,
and planned Sandbox Mode to balance reproducibility and execution safety.

Improved agent reliability through structured outputs, schema validation,
and modular pipeline orchestration.
```

中文版本：

```text
PaperPilot：多智能体论文复现与产品化助手

构建了一个 mock-first、安全边界明确的多智能体系统，可解析论文 PDF，
分析可选 GitHub 仓库，生成结构化复现计划，并自动创建 Streamlit 产品原型。

设计了 human-in-the-loop 命令执行机制，包括 Safe Mode、Review Mode
和规划中的 Sandbox Mode，在复现实用性和执行安全之间取得平衡。

通过结构化输出、schema 校验和模块化 pipeline 提升 Agent workflow 的稳定性和工程可维护性。
```
