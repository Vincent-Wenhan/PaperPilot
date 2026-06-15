# PaperPilot 功能升级与 Agent 架构调整方案

## 0. 本方案目标

这份方案不是单纯做代码重构，而是把 PaperPilot 从当前的：

```text
论文 PDF + 可选 GitHub repo
    ↓
LLM Agent 分析
    ↓
复现规划 / 产品原型
```

升级为：

```text
一篇或多篇论文 + 可选 GitHub repo
    ↓
少量高层 Agent
    ↓
多论文能力理解与组合
    ↓
产品理论约束
    ↓
PRD 驱动产品设计
    ↓
MVP 范围定义
    ↓
Mock-first Streamlit Prototype
    ↓
Rubric 评估与修正
```

核心目标有三个：

1. **减少碎片化 Agent**：避免为了 multi-agent 而拆出太多小 Agent。
2. **支持多篇论文组合**：让 Agent 自己判断多篇论文之间如何互补、冲突、替代或组合。
3. **引入产品设计理论**：让 Productize Mode 不再只靠 LLM 自由发散，而是基于 PRD、JTBD、Value Proposition、MVP、MoSCoW、Rubric 等规范进行设计。

---

## 1. 当前仓库现状

根据当前仓库 README，PaperPilot 2.0 定位为：

```text
multi-agent paper reproduction and product prototyping assistant
```

当前系统包含两条主线：

```text
Reproduce Mode:
  分析论文和代码，生成复现计划、run.sh 和 report.md

Productize Mode:
  识别产品机会，推荐 MVP，并生成 mock-first Streamlit prototype
```

当前 README 中的 Productize Mode 已经包括：

```text
Product Opportunity Agent
Product Designer Agent
Template selection
Tech Adapter Agent
Frontend Builder Agent
Deterministic product scaffold
Product inspection and Product Test Agent
```

当前 Agent Overview 中还列出了：

```text
Paper Reader Agent
Method Extractor Agent
Repo Clone Agent
Code Agent
Repo Analyzer Agent
Environment Agent
Experiment Planner Agent
Runner Agent
Debug Agent
Report Agent
Product Opportunity Agent
Product Designer Agent
Tech Adapter Agent
Frontend Builder Agent
Product Test Agent
```

当前 productize 目录已经包含确定性模块：

```text
productize/
  product_pipeline.py
  product_scaffold.py
  product_templates.py
  product_tester.py
```

这说明项目已经有较完整的工程骨架。下一步不应该继续堆更多 Agent，而应该把功能合并成少量高层 Agent，并加入规范、schema 和评价闭环。

---

## 2. 总体设计原则

## 2.1 少量高层 Agent，而不是大量小 Agent

不要继续新增一堆碎片化 Agent，例如：

```text
JTBD Agent
Value Proposition Agent
PRD Agent
MVP Agent
UIUX Agent
Capability Agent
Relationship Agent
Method Composer Agent
```

这些能力仍然需要，但应该作为高层 Agent 的内部步骤或 guideline 约束。

推荐原则：

```text
Agent 数量少，但每个 Agent 负责一个完整推理阶段。
```

最终建议：

```text
Reproduce Mode：4 个高层 Agent
Productize Mode：4 个高层 Agent
```

---

## 2.2 Agent 负责推理，Tool 负责动作

Agent 负责：

```text
理解
推理
规划
组合
评估
解释
```

确定性工具负责：

```text
PDF parsing
repo cloning
repo scanning
command execution
file writing
product scaffold generation
syntax checking
report building
```

这样可以避免 LLM 直接执行危险动作，也能让系统更稳定。

---

## 2.3 Guidelines 负责规范，不要都做成 Agent

产品理论、复现规范、多论文组合规则、安全规则，都应该放在 `guidelines/` 目录中，然后注入到高层 Agent 的 prompt 里。

推荐新增：

```text
guidelines/
  reproduction_checklist.md
  product_design_principles.md
  prd_template.md
  jtbd_template.md
  value_proposition_canvas.md
  mvp_scope_rules.md
  multi_paper_composition_rules.md
  product_evaluation_rubric.md
  streamlit_ui_rules.md
  safety_rules.md
```

---

## 2.4 Schemas 约束关键输出

关键中间产物不要只输出 Markdown，应该使用 JSON / Pydantic schema 约束。

推荐新增：

```text
schemas/
  paper_schema.py
  repo_schema.py
  reproduction_schema.py
  product_schema.py
  composition_schema.py
  runner_schema.py
  evaluation_schema.py
```

这样能减少 LLM 输出漂移，也方便下游模块使用。

---

## 3. 推荐最终架构

```text
PaperPilot

Shared Inputs:
  - Single paper PDF
  - Multiple paper PDFs
  - Optional GitHub repo(s)
  - Target user / product goal
  - Hardware setting
  - Reproduction goal

Shared deterministic tools:
  - PDF Parser
  - Repo Cloner
  - Repo Scanner
  - Command Runner
  - Product Scaffold
  - Product Tester
  - Report Builder

Reproduce Mode:
  1. Research Understanding Agent
  2. Repository Understanding Agent
  3. Reproduction Planner Agent
  4. Execution & Diagnosis Agent

Productize Mode:
  1. Research Synthesizer Agent
  2. Product Planner Agent
  3. Prototype Builder Agent
  4. Product Evaluator Agent

Shared support:
  - guidelines/
  - schemas/
  - prompts/
  - tests/
```

---

# 4. Reproduce Mode 调整方案

## 4.1 调整目标

当前 Reproduce Mode 中多个 Agent 可以合并：

```text
Paper Reader + Method Extractor
Repo Analyzer + Code/Environment evidence
Environment + Experiment Planner + command planning
Runner + Debug
```

最终流程：

```text
Research Understanding Agent
        ↓
Repository Understanding Agent
        ↓
Reproduction Planner Agent
        ↓
Execution & Diagnosis Agent
        ↓
Report Builder
```

---

## 4.2 Research Understanding Agent

### 合并对象

```text
Paper Reader Agent
Method Extractor Agent
```

### 职责

```text
解析论文内容
提取任务定义
提取方法结构
提取数据集
提取指标
提取训练设置
提取推理流程
提取复现关键线索
标记论文中缺失或不明确的信息
```

### 输出

```text
Paper Summary
Method Card
Experiment Requirement Card
Reproduction Clues
Missing Information
```

### Schema 示例

```python
class PaperUnderstanding(BaseModel):
    title: str
    task: str
    problem: str
    contributions: list[str]
    method_summary: str
    method_modules: list[str]
    datasets: list[str]
    metrics: list[str]
    training_details: list[str]
    inference_details: list[str]
    reproduction_clues: list[str]
    missing_information: list[str]
```

---

## 4.3 Repository Understanding Agent

### 合并对象

```text
Repo Analyzer Agent
Code Agent 的 repo/code understanding 部分
Environment Agent 的依赖识别部分
```

Repo Clone 不建议作为 Agent，应该是 deterministic tool：

```text
tools/repo_cloner.py
```

### 职责

```text
分析 repo 结构
识别 README / requirements / environment / setup 文件
识别 train / eval / demo / inference 入口
识别配置系统
识别数据准备方式
识别 checkpoint 需求
识别硬编码路径
识别 CUDA / custom op 风险
识别最小可运行路径
```

### Schema 示例

```python
class RepositoryUnderstanding(BaseModel):
    repo_url: str | None
    repo_path: str | None
    detected_framework: str
    dependency_files: list[str]
    config_files: list[str]
    training_entrypoints: list[str]
    evaluation_entrypoints: list[str]
    demo_entrypoints: list[str]
    dataset_requirements: list[str]
    checkpoint_requirements: list[str]
    risk_signals: list[str]
    minimal_runnable_candidates: list[str]
```

---

## 4.4 Reproduction Planner Agent

### 合并对象

```text
Environment Agent
Experiment Planner Agent
Runner Agent 的命令规划部分
Debug Agent 的预判部分
```

### 职责

```text
对齐论文和 repo
生成环境配置计划
生成数据准备计划
生成 minimal reproduction path
生成 full reproduction path
生成候选命令
为每条命令标注风险等级
预测可能失败点
生成 fallback plan
```

### Schema 示例

```python
class CommandPlan(BaseModel):
    command: str
    purpose: str
    risk_level: str
    requires_confirmation: bool
    expected_output: str
    fallback_if_failed: str


class ReproductionPlan(BaseModel):
    environment_plan: list[str]
    data_preparation_plan: list[str]
    minimal_reproduction_steps: list[str]
    full_reproduction_steps: list[str]
    command_plans: list[CommandPlan]
    risks: list[str]
    fallback_plan: list[str]
```

---

## 4.5 Execution & Diagnosis Agent

### 合并对象

```text
Runner Agent
Debug Agent
部分 Report Agent
```

真正执行命令仍然由：

```text
tools/command_runner.py
```

完成。Agent 只解释执行结果，不直接执行命令。

### 职责

```text
解释 stdout / stderr
判断失败原因
给出修复建议
决定是否需要换命令
总结实际可执行性
```

### Schema 示例

```python
class ExecutionDiagnosis(BaseModel):
    command: str
    executed: bool
    exit_code: int | None
    direct_cause: str
    possible_root_causes: list[str]
    suggested_fixes: list[str]
    next_actions: list[str]
    feasibility: str
```

---

## 4.6 Report Builder

Report Builder 建议做成确定性模块，而不是主要 Agent。

```text
builders/report_builder.py
```

输入：

```text
PaperUnderstanding
RepositoryUnderstanding
ReproductionPlan
ExecutionDiagnosis
```

输出：

```text
outputs/reproduction_plan.md
outputs/run.sh
outputs/report.md
```

如果需要语言润色，可以加 optional polish step，但不作为核心 Agent。

---

# 5. Productize Mode 调整方案

## 5.1 调整目标

Productize Mode 不只是重构，还要增强两个核心能力：

```text
1. 支持多篇论文输入，让 Agent 自己思考论文如何组合。
2. 引入产品理论，让产品设计不再只靠 LLM 自由发散。
```

最终流程：

```text
Research Synthesizer Agent
        ↓
Product Planner Agent
        ↓
Prototype Builder Agent
        ↓
Product Evaluator Agent
        ↓
Deterministic Product Scaffold / Tester
```

---

## 5.2 Research Synthesizer Agent

### 目标

这个 Agent 是 Productize Mode 的研究理解核心。它需要支持一篇或多篇论文。

### 输入

```text
paper_texts
optional repo_scan_results
target_domain
optional user_goal
multi_paper_composition_rules.md
```

### 职责

```text
为每篇论文生成 Paper Capability Card
构建 Capability Map
分析论文之间的关系
判断哪些论文适合组合
判断哪些论文应该被排除
选择组合策略
输出组合后的产品能力
```

---

## 5.3 Paper Capability Card

多篇论文不能直接丢给 LLM 让它自由发挥。每篇论文应先变成结构化能力卡片。

### 每篇论文提取

```text
paper_id
title
task
input_type
output_type
core_capability
required_data
required_model
metrics
strengths
limitations
possible_product_roles
integration_difficulty
evidence_from_paper
```

### Schema 示例

```python
class PaperCapabilityCard(BaseModel):
    paper_id: str
    title: str
    task: str
    input_type: str
    output_type: str
    core_capability: str
    required_data: list[str]
    required_model: str
    metrics: list[str]
    strengths: list[str]
    limitations: list[str]
    possible_product_roles: list[str]
    integration_difficulty: str
    evidence_from_paper: list[str]
```

---

## 5.4 Capability Map

多篇论文之间要构建能力图谱。

示例：

```text
Paper A → image restoration
Paper B → image quality assessment
Paper C → downstream diagnosis
Paper D → uncertainty estimation
Paper E → report generation
```

系统需要判断每篇论文在产品中的可能角色：

```text
Core engine
Preprocessing module
Postprocessing module
Evaluation module
Safety / uncertainty module
User interaction module
Benchmark reference
Alternative method
Excluded reference
```

---

## 5.5 Paper Relationship Analysis

对多篇论文，两两分析关系：

```text
complementary：互补，可以组合
redundant：功能重复，只选一个或做比较
conflicting：假设冲突，不建议组合
dependency：一篇论文的输出可以作为另一篇输入
alternative：解决同一问题的替代方案
```

### Schema 示例

```python
class PaperRelationship(BaseModel):
    source_paper_id: str
    target_paper_id: str
    relation_type: str
    compatibility_score: int
    reason: str
    integration_note: str
```

---

## 5.6 Method Composition Plan

Agent 不应该简单把所有论文堆在一起，而应该选择组合策略。

### 组合策略

#### 1. Pipeline Composition

一篇论文的输出作为另一篇论文的输入。

```text
Image Quality Assessment
        ↓
Image Restoration
        ↓
Downstream Diagnosis
        ↓
Report Generation
```

#### 2. Modular Composition

每篇论文负责一个独立模块。

```text
System
  ├── preprocessing module
  ├── core model module
  ├── evaluation module
  └── reporting module
```

#### 3. Alternative Selection

多篇论文解决同一问题，选择最适合产品化的一篇。

```text
Paper A：效果强但无代码
Paper B：效果稍弱但有 repo 和权重
Paper C：需要复杂训练

最终选择 Paper B 作为 MVP 核心方法
```

#### 4. Comparison Product

不强行融合，而是设计成多方法比较工具。

```text
Method comparison dashboard
Paper reproduction planning comparator
Model output comparison app
```

#### 5. Agent Workflow Composition

多篇论文分别支持 Agent 系统中的不同能力。

```text
Paper A：planning
Paper B：tool use
Paper C：reflection
Paper D：evaluation
```

### Schema 示例

```python
class MethodCompositionPlan(BaseModel):
    composition_strategy: str
    selected_papers: list[str]
    excluded_papers: list[str]
    paper_roles: dict[str, str]
    system_workflow: list[str]
    integration_risks: list[str]
    product_capability_summary: str
    product_potential_score: float
```

---

# 6. 产品设计理论支撑

Productize Mode 不应该直接从论文生成 app，而应该经过专业产品设计流程。

推荐链路：

```text
Research Synthesis
    ↓
JTBD
    ↓
Value Proposition Canvas
    ↓
Product Opportunity Scoring
    ↓
PRD
    ↓
MVP Scope
    ↓
MoSCoW Priority
    ↓
UI / UX Flow
    ↓
Prototype
    ↓
Product Evaluation Rubric
```

---

## 6.1 PRD：Product Requirements Document

PRD 是产品设计的核心中间产物。

当前 Productize Mode 已经能生成 product specification，但建议升级为更标准的 PRD。

### PRD 作用

```text
把论文能力转化为明确产品需求
约束后续 MVP 和 UI 设计
减少 LLM 随意生成功能
作为 Prototype Builder 的主要输入
```

### PRD 应包含

```text
Product Name
One-sentence Pitch
Background / Opportunity
Target Users
User Pain Points
Jobs To Be Done
Value Proposition
Product Goals
Core Use Cases
Functional Requirements
Non-functional Requirements
User Flow
Input Definition
Output Definition
MVP Scope
Out-of-scope
Success Metrics
Risks
Limitations
Mock-first Implementation Plan
Real Model Integration Plan
```

### PRD Schema 示例

```python
class FeatureRequirement(BaseModel):
    name: str
    description: str
    priority: str
    user_value: str
    implementation_note: str


class PRD(BaseModel):
    product_name: str
    one_sentence_pitch: str
    background: str
    target_users: list[str]
    user_pain_points: list[str]
    jobs_to_be_done: list[str]
    value_proposition: str
    product_goals: list[str]
    core_use_cases: list[str]
    functional_requirements: list[FeatureRequirement]
    non_functional_requirements: list[str]
    user_flow: list[str]
    input_definition: str
    output_definition: str
    mvp_scope: list[str]
    out_of_scope: list[str]
    success_metrics: list[str]
    risks: list[str]
    limitations: list[str]
    mock_first_plan: str
    real_model_integration_plan: str
```

---

## 6.2 JTBD：Jobs To Be Done

JTBD 用于明确用户真正要完成什么任务。

### 模板

```text
When [situation],
I want to [motivation],
so I can [expected outcome].
```

### 在 PaperPilot 中的作用

```text
避免目标用户过泛
明确真实使用场景
让产品目标从用户任务出发
帮助判断论文能力是否有实际产品价值
```

### 示例

```text
When a researcher wants to evaluate whether several paper methods can form a practical workflow,
I want to upload multiple papers and get a method composition plan,
so I can decide which idea is suitable for a demo prototype.
```

---

## 6.3 Value Proposition Canvas

Value Proposition Canvas 用来判断论文能力是否真的能形成产品价值。

### 需要输出

```text
Customer Jobs
Pains
Gains
Pain Relievers
Gain Creators
Product Features
```

### 在 PaperPilot 中的作用

```text
连接论文能力和用户价值
避免只因为方法新颖就生成产品
帮助 Product Planner 选择更合理的产品方向
```

---

## 6.4 Lean Startup / MVP

Lean Startup 的核心是：

```text
Build → Measure → Learn
```

在 PaperPilot 中对应：

```text
先生成 mock-first prototype
先验证产品流程和场景是否成立
不要一开始就追求真实模型集成
真实集成放在 adapter boundary 和 real integration plan 中
```

这也解释了为什么当前 generated_product 应该默认 mock mode。

---

## 6.5 MoSCoW Prioritization

MoSCoW 用于功能优先级排序：

```text
Must have
Should have
Could have
Won't have
```

### 在 PaperPilot 中的作用

```text
控制 MVP 范围
防止生成过大的产品
让 Prototype Builder 只实现核心功能
明确哪些功能暂不实现
```

### 示例

```text
Must have:
  - Upload input
  - Show mock output
  - Show limitation notice
  - Show real integration placeholder

Should have:
  - Parameter controls
  - Result explanation
  - Downloadable report

Could have:
  - Multiple method comparison
  - Example data
  - Visual dashboard

Won't have:
  - Real clinical diagnosis
  - Full model training
  - Arbitrary command execution
```

---

## 6.6 Kano Model

Kano Model 可以作为辅助规则，用来区分：

```text
Basic Needs
Performance Needs
Delighters
```

在第一版中不一定要独立实现，但可以写进 `mvp_scope_rules.md`，辅助 Product Planner 做功能裁剪。

---

## 6.7 Product Evaluation Rubric

Product Evaluator Agent 应根据 rubric 对产品设计打分。

### 评估维度

```text
Paper Faithfulness
Multi-paper Coherence
User Clarity
Problem-solution Fit
PRD Completeness
MVP Simplicity
Demo Feasibility
Mock-first Correctness
Safety Awareness
Integration Feasibility
```

### 示例输出

```json
{
  "paper_faithfulness": 4,
  "multi_paper_coherence": 5,
  "user_clarity": 4,
  "problem_solution_fit": 4,
  "prd_completeness": 5,
  "mvp_simplicity": 4,
  "demo_feasibility": 5,
  "mock_first_correctness": 5,
  "safety_awareness": 5,
  "integration_feasibility": 4,
  "overall_score": 4.5,
  "revision_suggestions": []
}
```

如果分数低于阈值，例如 4.0，可以触发 revision：

```text
generate → evaluate → revise
```

---

# 7. Product Planner Agent 详细逻辑

Product Planner Agent 是 Productize Mode 的核心。

### 输入

```text
Research Synthesis
Paper Capability Cards
Method Composition Plan
Target user
Product goal
product_design_principles.md
prd_template.md
jtbd_template.md
value_proposition_canvas.md
mvp_scope_rules.md
```

### 内部步骤

```text
Step 1：根据 Research Synthesis 识别可产品化能力
Step 2：生成 JTBD
Step 3：生成 Value Proposition Canvas
Step 4：生成多个 Product Opportunities
Step 5：按评分规则选择最适合 MVP 的方向
Step 6：生成 PRD
Step 7：用 MoSCoW 定义 MVP 范围
Step 8：输出 risks / limitations / success metrics
```

### 输出

```text
JTBD
Value Proposition Canvas
Product Opportunities
Opportunity Scoring
Selected Product
PRD
MVP Scope
MoSCoW Priority
Risks
Limitations
Success Metrics
```

---

# 8. Product Opportunity Scoring

每个产品机会都应该评分，防止选择“听起来酷但做不出来”的方向。

### 评分维度

```text
technical_feasibility
demo_feasibility
model_availability
data_requirement
integration_risk
user_value
paper_faithfulness
multi_paper_coherence
mock_first_suitability
```

### 推荐公式

```text
overall_score =
  0.15 * technical_feasibility
+ 0.15 * demo_feasibility
+ 0.10 * model_availability
+ 0.15 * user_value
+ 0.15 * paper_faithfulness
+ 0.10 * multi_paper_coherence
+ 0.10 * mock_first_suitability
- 0.10 * integration_risk
```

说明：

```text
data_requirement 可以反向处理：
数据要求越低，分数越高。
```

---

# 9. Prototype Builder Agent 详细逻辑

Prototype Builder Agent 不直接发散产品 idea，而是基于 Product Planner 输出的 PRD 和 MVP 来设计原型。

### 输入

```text
PRD
MVP Scope
MoSCoW Priority
streamlit_ui_rules.md
Current productize templates
```

### 职责

```text
选择 image / text / video / generic template
设计页面结构
定义用户输入
定义系统输出
定义 mock result
定义 real integration placeholder
定义 adapter boundary
生成 prototype plan
```

### 注意

真正生成代码仍然由：

```text
productize/product_scaffold.py
```

完成。Prototype Builder Agent 只生成结构化 prototype plan，不直接执行任意代码。

---

# 10. Product Evaluator Agent 详细逻辑

Product Evaluator Agent 负责最后检查，而不是只检查文件是否存在。

### 输入

```text
Research Synthesis
Product Plan
PRD
MVP Scope
Prototype Plan
product_tester inspection result
product_evaluation_rubric.md
safety_rules.md
```

### 输出

```text
evaluation_scores
detected_problems
revision_suggestions
safety_warnings
demo_readiness
```

### 检查项

```text
产品能力是否由论文支持？
多论文组合是否合理？
是否有 PRD？
MVP 是否足够小？
是否明确 mock-first？
是否夸大真实模型能力？
是否存在危险执行逻辑？
是否适合 Streamlit demo？
```

---

# 11. Multi-paper UI / Frontend 支持

当前 Productize Mode 输入主要是一篇论文。建议前端支持多论文。

### 输入区

```text
Upload Papers
  - 支持多个 PDF
  - 显示每篇论文解析状态

Optional GitHub Repos
  - 可以为每篇论文绑定一个 repo
  - 也可以只有一个公共 repo
  - 也可以无 repo，仅根据论文分析
```

### 中间结果展示

```text
Paper Capability Cards
  展示每篇论文的任务、输入、输出、核心能力和限制

Capability Map
  展示每篇论文的功能角色

Relationship Analysis
  展示 complementary / redundant / conflicting / dependency / alternative

Method Composition Plan
  展示组合策略和系统 workflow
```

### 产品设计展示

```text
Product Opportunities
  展示多个产品方向和评分

Selected Product
  展示最终选择原因

PRD
  展示完整产品需求文档

MVP Scope
  展示 Must / Should / Could / Won't

Prototype Plan
  展示 UI flow 和 adapter boundary

Evaluation
  展示评分和修改建议
```

---

# 12. Runner 安全策略

当前 Runner 安全策略很严格，这是优点。但可以扩展为三种模式。

```text
Safe Mode:
  默认模式，只允许 allowlist 命令。

Review Mode:
  LLM 生成候选命令，但必须展示给用户确认后执行。

Sandbox Mode:
  在 Docker / conda 临时环境中执行，用于更真实的复现实验。
```

### 推荐流程

```text
Reproduction Planner Agent 生成 Command Plan
        ↓
Command Runner 做风险检测
        ↓
Streamlit 展示 command / purpose / risk level
        ↓
用户 Confirm / Reject
        ↓
执行并保存 stdout / stderr / exit code
        ↓
Execution & Diagnosis Agent 分析结果
```

不要让 Agent 直接执行命令。Agent 只负责计划和解释，执行由 `tools/command_runner.py` 管理。

---

# 13. 推荐目录结构

```text
PaperPilot/
  app.py
  main.py
  config.py

  agents/
    base_agent.py

    # Reproduce Mode
    research_understanding_agent.py
    repository_understanding_agent.py
    reproduction_planner_agent.py
    execution_diagnosis_agent.py

    # Productize Mode
    research_synthesizer_agent.py
    product_planner_agent.py
    prototype_builder_agent.py
    product_evaluator_agent.py

    # Legacy agents can be kept temporarily
    legacy/
      paper_reader_agent.py
      method_extractor_agent.py
      product_opportunity_agent.py
      product_designer_agent.py
      tech_adapter_agent.py
      frontend_builder_agent.py
      product_test_agent.py

  tools/
    pdf_parser.py
    repo_cloner.py
    repo_scanner.py
    command_runner.py
    guideline_loader.py

  productize/
    product_pipeline.py
    product_scaffold.py
    product_templates.py
    product_tester.py

  guidelines/
    reproduction_checklist.md
    product_design_principles.md
    prd_template.md
    jtbd_template.md
    value_proposition_canvas.md
    mvp_scope_rules.md
    multi_paper_composition_rules.md
    product_evaluation_rubric.md
    streamlit_ui_rules.md
    safety_rules.md

  schemas/
    paper_schema.py
    repo_schema.py
    reproduction_schema.py
    product_schema.py
    composition_schema.py
    runner_schema.py
    evaluation_schema.py

  builders/
    report_builder.py
    run_script_builder.py
    artifact_writer.py

  prompts/
  tests/
  docs/
```

说明：

```text
legacy/ 不需要第一版就移动。
可以先保留旧 Agent 文件，只是在新 pipeline 中不再直接调用。
等新 pipeline 稳定后再整理。
```

---

# 14. Productize Pipeline 伪代码

```python
def run_productize_pipeline(inputs):
    paper_texts = [pdf_parser.parse(pdf) for pdf in inputs.pdfs]

    repo_scans = []
    for repo_url in inputs.repo_urls:
        repo_path = repo_cloner.clone(repo_url)
        repo_scans.append(repo_scanner.scan(repo_path))

    research_synthesis = ResearchSynthesizerAgent.run(
        paper_texts=paper_texts,
        repo_scans=repo_scans,
        composition_rules=load_guideline("multi_paper_composition_rules.md"),
    )

    product_plan = ProductPlannerAgent.run(
        research_synthesis=research_synthesis,
        target_user=inputs.target_user,
        product_goal=inputs.product_goal,
        product_guidelines=load_guideline("product_design_principles.md"),
        prd_template=load_guideline("prd_template.md"),
        jtbd_template=load_guideline("jtbd_template.md"),
        value_canvas=load_guideline("value_proposition_canvas.md"),
        mvp_rules=load_guideline("mvp_scope_rules.md"),
    )

    prototype_plan = PrototypeBuilderAgent.run(
        product_plan=product_plan,
        ui_rules=load_guideline("streamlit_ui_rules.md"),
    )

    generated_files = product_scaffold.write_generated_product(
        prototype_plan=prototype_plan,
        product_plan=product_plan,
    )

    inspection = product_tester.inspect_generated_product(generated_files)

    evaluation = ProductEvaluatorAgent.run(
        research_synthesis=research_synthesis,
        product_plan=product_plan,
        prototype_plan=prototype_plan,
        inspection=inspection,
        rubric=load_guideline("product_evaluation_rubric.md"),
        safety_rules=load_guideline("safety_rules.md"),
    )

    if evaluation.overall_score < 4.0:
        product_plan = ProductPlannerAgent.revise(
            product_plan=product_plan,
            evaluation=evaluation,
        )

    return {
        "research_synthesis": research_synthesis,
        "product_plan": product_plan,
        "prototype_plan": prototype_plan,
        "generated_files": generated_files,
        "inspection": inspection,
        "evaluation": evaluation,
    }
```

---

# 15. Reproduce Pipeline 伪代码

```python
def run_reproduce_pipeline(inputs):
    paper_text = pdf_parser.parse(inputs.pdf)

    paper_understanding = ResearchUnderstandingAgent.run(
        paper_text=paper_text,
        guideline=load_guideline("reproduction_checklist.md"),
    )

    repo_scan = None
    if inputs.repo_url:
        repo_path = repo_cloner.clone(inputs.repo_url)
        repo_scan = repo_scanner.scan(repo_path)

    repo_understanding = RepositoryUnderstandingAgent.run(
        paper_understanding=paper_understanding,
        repo_scan=repo_scan,
    )

    reproduction_plan = ReproductionPlannerAgent.run(
        paper_understanding=paper_understanding,
        repo_understanding=repo_understanding,
        hardware=inputs.hardware,
        goal=inputs.goal,
        safety_rules=load_guideline("safety_rules.md"),
    )

    command_results = command_runner.run_allowed_or_confirmed(
        reproduction_plan.command_plans
    )

    diagnosis = ExecutionDiagnosisAgent.run(
        command_results=command_results,
        reproduction_plan=reproduction_plan,
    )

    outputs = report_builder.build(
        paper_understanding=paper_understanding,
        repo_understanding=repo_understanding,
        reproduction_plan=reproduction_plan,
        diagnosis=diagnosis,
    )

    return outputs
```

---

# 16. 分阶段实施计划

## Phase 1：先补产品理论和多论文规范

目标：先建立 Productize Mode 的规范基础，不大改主流程。

任务：

```text
1. 新增 guidelines/
2. 新增 product_design_principles.md
3. 新增 prd_template.md
4. 新增 jtbd_template.md
5. 新增 value_proposition_canvas.md
6. 新增 mvp_scope_rules.md
7. 新增 multi_paper_composition_rules.md
8. 新增 product_evaluation_rubric.md
9. 新增 guideline_loader.py
```

---

## Phase 2：新增结构化 schemas

任务：

```text
1. PaperCapabilityCard
2. PaperRelationship
3. MethodCompositionPlan
4. ProductOpportunity
5. PRD
6. MVP Scope
7. ProductEvaluation
```

---

## Phase 3：改 Productize Mode

目标：先把 Productize Mode 做成新逻辑。

任务：

```text
1. 新增 Research Synthesizer Agent
2. 新增 Product Planner Agent
3. 新增 Prototype Builder Agent
4. 新增 Product Evaluator Agent
5. 保留旧 Productize Agent，不立即删除
6. 支持上传多篇论文
7. 输出 Capability Cards
8. 输出 Method Composition Plan
9. 输出 PRD
10. 输出 MVP / MoSCoW
11. 输出 Product Evaluation
```

---

## Phase 4：合并 Reproduce Mode

任务：

```text
1. Paper Reader + Method Extractor → Research Understanding
2. Repo Analyzer + Environment Evidence → Repository Understanding
3. Environment + Experiment Planner + Command Planning → Reproduction Planner
4. Runner + Debug → Execution & Diagnosis
5. Report Agent → Report Builder
```

---

## Phase 5：Runner Review Mode

任务：

```text
1. 增加 runner_mode 配置
2. 增加 CommandPlan / CommandResult schema
3. Safe Mode 保持默认
4. Review Mode 支持用户确认
5. Streamlit 增加 Confirm / Reject UI
6. 保存 command log
```

---

## Phase 6：工程质量提升

任务：

```text
1. CI
2. pytest
3. README 更新
4. example case
5. screenshots
```

---

# 17. README 推荐描述

## 17.1 新定位

```text
PaperPilot is a theory-guided, safety-bounded multi-agent system for paper reproduction and research-to-product prototyping.

It supports both single-paper and multi-paper productization. For multiple papers, the system extracts paper capability cards, analyzes method complementarity, redundancy, conflicts, and dependencies, and generates a PRD-driven mock-first product prototype.

Instead of relying on raw LLM brainstorming, Productize Mode uses product design frameworks such as Jobs-to-be-Done, Value Proposition Canvas, PRD, MVP scoping, MoSCoW prioritization, and rubric-based evaluation.
```

---

## 17.2 新架构图

```text
Paper PDF(s) + optional GitHub Repo(s)
        ↓
Shared deterministic tools
  - PDF Parser
  - Repo Cloner
  - Repo Scanner
        ↓
Reproduce Mode
  - Research Understanding Agent
  - Repository Understanding Agent
  - Reproduction Planner Agent
  - Execution & Diagnosis Agent
        ↓
Outputs
  - reproduction_plan.md
  - run.sh
  - report.md

Productize Mode
  - Research Synthesizer Agent
      Paper Capability Cards
      Capability Map
      Method Composition Plan
  - Product Planner Agent
      JTBD
      Value Proposition Canvas
      PRD
      MVP Scope
      MoSCoW Priority
  - Prototype Builder Agent
      UI Flow
      Adapter Boundary
      Mock-first Prototype Plan
  - Product Evaluator Agent
      Product Rubric Evaluation
      Revision Suggestions
        ↓
generated_product/
```

---

# 18. 最小可行改造版本

如果时间有限，建议先做最小可行版本：

```text
1. 保留现有 Reproduce Mode，暂时不大改
2. 先升级 Productize Mode
3. 新增 guidelines/
4. 新增 schemas/
5. Productize Mode 收敛成 4 个高层 Agent：
   - Research Synthesizer Agent
   - Product Planner Agent
   - Prototype Builder Agent
   - Product Evaluator Agent
6. 支持多篇论文上传
7. 每篇论文生成 Paper Capability Card
8. 多论文生成 Method Composition Plan
9. Product Planner 生成 PRD + MVP + MoSCoW
10. Product Evaluator 输出评分和修改建议
```

这样可以最快体现这次升级的核心价值：

```text
multi-paper reasoning
theory-guided product design
PRD-driven prototype generation
mock-first productization
```

---

# 19. 最终效果

改完后，PaperPilot 的 Productize Mode 不再是：

```text
论文 → LLM 想产品 → 生成 Streamlit
```

而是：

```text
一篇或多篇论文
    ↓
Paper Capability Cards
    ↓
Capability Map
    ↓
Method Composition Plan
    ↓
JTBD + Value Proposition Canvas
    ↓
Product Opportunity Scoring
    ↓
PRD
    ↓
MVP / MoSCoW
    ↓
UI Flow + Adapter Boundary
    ↓
Mock-first Streamlit Prototype
    ↓
Product Evaluation Rubric
    ↓
Revision Suggestions
```

这会让系统更稳定、更有解释性，也更像一个真正的 Research-to-Product Agent。
