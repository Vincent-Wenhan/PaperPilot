# PaperPilot 2.0

[English](README.md)
![CI](https://github.com/Vincent-Wenhan/PaperPilot/actions/workflows/ci.yml/badge.svg)

PaperPilot 2.0 是一个由产品理论指导、受安全边界约束的论文复现与 Research-to-Product 多智能体系统。用户可以上传一篇或多篇论文，并可选提供 GitHub 仓库。复现模式生成可执行的复现计划；产品化模式提取论文能力卡、分析方法关系与组合方式，再基于 JTBD、Value Proposition、PRD、MVP、MoSCoW 和评估 Rubric 生成有限范围的 mock-first Streamlit 原型。

项目从 **Paper-to-Reproduce** 扩展到 **Paper-to-Product**，但不是“万能自动产品生成器”。真实模型接口无法安全确定时，系统会生成 mock-first 原型，保证课程演示流程可运行。

## 项目定位

这是一个 AI 大模型课程期末 project，展示轻量、可解释的多 Agent pipeline 如何连接论文复现与有限范围的应用原型生成。系统不承诺自动完成完整训练、复现论文指标或直接交付生产系统。

## 系统功能

PaperPilot 集论文理解、仓库分析、复现规划和产品原型生成为一体。示例输出见 [`examples/`](examples/sample_outputs/)。

### 复现模式

- 上传并解析论文 PDF
- 校验并浅克隆公开 GitHub 仓库
- 没有仓库 URL 时，明确进入 paper-only 复现规划
- 扫描 README、依赖文件、配置和候选入口
- 生成论文摘要与工程化方法拆解
- 根据 CPU、单 GPU 或多 GPU 条件规划环境
- 生成分层实验路线、checklist 和安全 `run.sh`
- 运行 version 与候选入口 `--help` 等轻量命令
- 命令由确定性 Runner Tool 执行，失败由 Execution & Diagnosis Agent 分析
- 生成并下载复现计划、脚本和课程展示报告

### 产品化模式

- 支持一篇或多篇论文，可选共享 repo 或逐篇绑定 repo
- 生成 Paper Capability Cards、Capability Map 和 Method Composition Plan
- 使用 JTBD、Value Proposition、PRD、MVP 和 MoSCoW 控制产品范围
- 生成结构化原型计划，并使用 Rubric 评估产品
- 支持 image、text、video、file 四类产品模板
- 在独立的 `generated_product/` 中生成 Streamlit 原型
- 检查生成文件、Python 语法、mock mode 和运行说明

### Mock 模式

- 无 API key 时通过 mock mode 完整演示
- 默认 mock-first — 生成的产品原型使用安全 mock 输出

## 系统架构

```text
论文 PDF（单篇或多篇）+ GitHub URL（可选）
↓
Reproduce Mode
├── Research Understanding Agent
├── Repository Understanding Agent
├── Reproduction Planner Agent
├── Execution & Diagnosis Agent
└── 确定性 Report Builder
↓
Productize Mode
├── [阶段1] generate_proposals()
│   ├── Research Synthesizer Agent
│   │   ├── 能力卡、能力图谱与论文关系
│   │   └── 方法组合计划
│   └── Product Planner Agent
│       └── JTBD、Value Proposition、PRD、MVP、MoSCoW
├── [审查] 用户选择并编辑方案
├── [阶段2] execute_proposal()
│   ├── Prototype Builder Agent
│   ├── 模板选择与确定性产品代码生成
│   ├── Product Evaluator Agent
│   └── 静态检查与 Rubric 评估
↓
generated_product/<产品名称>/
```

## 多 Agent 说明

| Agent | 职责 |
| --- | --- |
| Research Understanding Agent | 合并论文阅读与方法拆解，输出结构化研究理解 |
| Repository Understanding Agent | 解释静态仓库扫描与环境证据 |
| Reproduction Planner Agent | 规划环境、数据、实验、安全命令、风险与 fallback |
| Execution & Diagnosis Agent | 解释命令结果与日志，自身不执行命令 |
| Research Synthesizer Agent | 生成能力卡、论文关系与方法组合计划 |
| Product Planner Agent | 使用 JTBD、Value Proposition、PRD、MVP、MoSCoW 规划产品 |
| Prototype Builder Agent | 定义 Streamlit 流程、mock 结果和 adapter 边界 |
| Product Evaluator Agent | 评估论文忠实度、组合合理性、安全性和演示准备度 |

以上八个是系统唯一活动推理 Agent。旧碎片 Agent 仅隔离保存在 `agents/legacy/`，活动流水线不会导入或调用。仓库 clone/scan、命令执行、报告写入、产品 scaffold 和静态检查均由确定性 Tool 或 Builder 完成。

## 项目结构

```text
PaperPilot/
├── app.py
├── main.py
├── config.py
├── agents/                  # 八个活动高层 Agent
│   └── legacy/              # 不参与主流程的迁移参考实现
├── guidelines/              # 产品、组合、UI 与安全规则
├── schemas/                 # 论文、组合、产品与评估结构化模型
├── productize/
├── tools/
├── prompts/
├── uploads/
├── workspace/
├── outputs/
│   ├── reproduction_plan.md
│   ├── run.sh
│   └── report.md
├── generated_product/       # 运行时生成并被 gitignore（按产品名称分子目录）
├── examples/                # 示例输出，展示流程结果
├── requirements.txt
└── README.md
```

## 为什么选择 Mock-first？

许多研究仓库因为缺少 checkpoint、数据集过大、环境冲突或预处理步骤缺失而难以直接运行。

因此 PaperPilot 采用 mock-first 的产品化策略：

1. **理解**论文和可选仓库
2. **识别**可行的产品场景
3. **生成**清晰的接口和适配器边界
4. **默认使用 mock** — 原型无需真实模型即可运行
5. **后续集成** — 真实模型接入作为一个需要审查的工程步骤

这使得生成的原型安全、快速可运行，适合课程演示或早期产品验证。

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

项目默认开启 Mock Mode（无需 API key），通过 Streamlit 侧边栏的 **Mock Mode** 开关控制。

Mock mode 会返回固定文本，但 PDF 解析、URL 校验、仓库 clone、扫描、输出文件生成和安全 Runner 仍走真实本地流程。没有 API key 时页面不会崩溃。

## 真实 LLM API

`LLMClient` 使用 OpenAI-compatible Chat Completions 接口。凭证直接在 Streamlit **侧边栏**中配置：

| 侧边栏字段 | 说明 |
|---|---|
| API Key | OpenAI-compatible API key（密码模式，输入时隐藏） |
| Base URL | API 端点，默认 `https://api.openai.com/v1` |
| Model | 模型名，默认 `gpt-4o-mini` |
| Mock Mode | 开关 — 开启时不调用 LLM |

也可继续使用环境变量（`LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`、`LLM_MOCK_MODE`），侧边栏值优先。不要将 API key 写入代码或提交到版本库。

## Reproduce Mode 使用流程

1. 上传论文 PDF。
2. 可选输入 `https://github.com/owner/repository` 格式的仓库 URL；留空时进入 paper-only 规划。
3. 选择 `CPU only`、`Single GPU` 或 `Multi GPU`，可填写 GPU 型号。
4. 选择理解论文、官方 demo、最小训练实验、主实验或 Debug 目标。
5. 点击 `Analyze`，查看 Agent 状态与各阶段结果。
6. 下载 `reproduction_plan.md`、`run.sh` 和 `report.md`。
7. 在 Runner 区手动点击安全命令；命令失败时查看自动 Debug。
8. 也可以在 Debug 区粘贴日志，获得独立诊断。

## 产品化模式（Productize Mode）

Productize Mode 会优先复用当前会话中的论文分析，也支持同时上传多篇论文。
Repo 可以不提供、为所有论文提供一个共享 URL，或按上传顺序逐行提供一个
URL。分析尚不存在时，系统会为每篇上传论文调用现有 `run_paperpilot()`
分析流程，再继续产品化。

1. 在侧边栏选择 **Productize Paper**。
2. 上传一篇或多篇 PDF。
3. 可选填写一个共享 GitHub URL，或按论文逐行填写 URL。
4. 填写目标用户和产品目标。
5. 选择 `Auto`、`Image`、`Text`、`Video` 或 `File`。
6. 点击 **Generate Proposals** 生成一个或多个产品方案。
7. 在标签页中浏览方案详情（PRD、MVP/MoSCoW、风险、产品机会）。
8. 选择一个方案，可选编辑核心功能和必须包含范围。
9. 点击 **Execute Proposal** 生成 Streamlit 原型。
10. 查看能力卡、组合计划、产品机会、PRD/MVP、原型计划、生成文件和评估结果。

Productize 流水线分为两个阶段：

- **`generate_proposals()`** — 运行 Research Synthesizer + Product Planner，返回 `ProductProposal` 实例列表（每个产品机会一个）。
- **`execute_proposal()`** — 运行 Prototype Builder + 模板选择 + Scaffold + Product Evaluator，执行单个选定方案。

旧的单论文 `run_productize_pipeline()` 调用保持兼容。

生成目录：

```text
generated_product/<产品名称>/
├── app.py
├── adapter.py
├── README.md
├── product_spec.md
├── requirements.txt
└── outputs/
```

运行生成产品：

```bash
cd generated_product/<产品名称>
pip install -r requirements.txt
streamlit run app.py
```

生成的 `adapter.py` 默认 `mock_mode=True`。真实模型接入必须由用户人工
检查原仓库推理接口并修改 adapter；系统不会自动导入或执行原仓库代码。

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

确定性 Runner 命令失败时，系统将 command、cwd、return code、stdout 和 stderr 交给 Execution & Diagnosis Agent。用户也可以手动粘贴日志。该 Agent 输出直接原因、可能根因、有限范围修复建议和下一步，但不会自行执行命令。

## 输出文件

- `outputs/<论文名称>/reproduction_plan.md`：论文、方法、仓库、环境、实验路线、checklist 与风险
- `outputs/<论文名称>/run.sh`：仅包含安全默认命令和注释形式的 TODO
- `outputs/<论文名称>/report.md`：适合课程 project 展示的结构化复现报告

每篇论文的输出保存在以 PDF 文件名命名的独立子目录中。
仓库内已提供 mock 示例输出（`outputs/` 根目录作为无论文名时的回退位置）。

产品原型是 `generated_product/<产品名称>/` 下的运行时产物，不提交到 Git。
主页面会在生成后展示文件内容。

## 项目限制

- PDF 扫描件没有 OCR 时可能无法提取文本。
- LLM 输出质量取决于模型、上下文长度和论文文本质量。
- 仓库分析基于静态文件扫描，不保证自动理解所有自定义入口。
- 系统不验证完整训练能否达到原论文指标。
- Runner 有意采用严格 allowlist，不提供任意终端能力。
- 真实 API、私有仓库、数据集和 checkpoint 可能需要用户自行配置。
- 产品 idea 质量取决于论文内容和静态仓库证据。
- 多论文组合是基于证据的规划，不代表真实模型已经可以正确集成。
- 产品模板仅覆盖 image、text、video 和通用 file-analysis。
- 生成的 adapter 不保证无需人工工程即可接入真实研究模型。
- mock 返回只用于展示交互流程，不代表论文模型预测结果。

## 未来改进

- 增加 OCR 与论文表格、公式解析
- 增加可配置的仓库扫描深度与依赖冲突分析
- 引入人工确认后的受控 demo 执行
- 保存多次复现会话与实验对比
- 增加真实模型的结构化输出校验
- 增加单元测试、CI 和容器化发布
