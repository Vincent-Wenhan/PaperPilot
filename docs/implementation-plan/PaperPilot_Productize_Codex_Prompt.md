# Codex Prompt：在现有 PaperPilot 项目基础上添加 Productize 产品化功能

你将继续开发一个已经完成基础论文复现功能的课程期末项目：**PaperPilot**。

当前项目已经具备以下能力：

- 上传论文 PDF
- 解析论文内容
- 输入 GitHub URL
- clone GitHub 仓库
- 分析 README / requirements / scripts / configs
- 生成论文复现计划
- 生成环境配置建议
- 生成 `run.sh`
- 支持轻量命令运行
- 支持 debug 日志分析
- 支持 Streamlit 页面展示

现在需要在现有项目基础上继续添加一个新的模式：

> **Productize Mode：论文技术产品化模式**

目标是让 PaperPilot 不仅能帮助用户复现论文，还能进一步根据论文方法和开源代码，分析该技术能做什么真实应用，并自动生成一个可交互的产品原型。

请严格按照本文档分阶段完成。  
**不要重写已有复现功能。不要破坏原有功能。每完成一个阶段，都必须先自检，确认无误后再进入下一阶段。**

---

## 0. 总目标

在现有 PaperPilot 项目中添加第二个核心模式：

```text
Mode 1：Reproduce Mode
论文 PDF + GitHub URL → 复现计划 / 环境配置 / run.sh / debug 建议

Mode 2：Productize Mode
论文 PDF + GitHub URL → 产品 idea / MVP 设计 / 产品原型代码 / 可运行 demo
```

Productize Mode 的核心流程：

```text
论文 PDF + GitHub URL
        ↓
复用已有论文分析结果
        ↓
复用已有仓库分析结果
        ↓
分析论文技术能力
        ↓
推荐适合的应用场景
        ↓
设计 MVP 产品
        ↓
判断产品模板类型
        ↓
生成 generated_product/
        ↓
生成 Streamlit 产品 demo
        ↓
生成统一 ModelAdapter
        ↓
支持 mock mode 演示
```

最终新增输出：

```text
generated_product/
│
├── app.py
├── adapter.py
├── README.md
├── product_spec.md
├── requirements.txt
└── outputs/
```

---

## 1. 项目定位

请把项目升级为：

# PaperPilot 2.0：论文复现与产品化助手

项目一句话介绍：

> PaperPilot 2.0 是一个多智能体论文复现与产品化助手。用户上传论文 PDF 并提供 GitHub 代码后，系统首先分析论文方法和开源仓库，生成复现计划；随后进入产品化模式，自动识别论文技术能力，推荐适合的应用场景，设计 MVP 产品，并生成基于 Streamlit 的交互式产品原型。

核心卖点：

```text
从 Paper-to-Reproduce 升级到 Paper-to-Product。
```

不要把系统描述成“万能自动产品生成器”。  
正确定位是：

```text
系统根据论文和开源代码，生成一个有限范围内的产品原型。
如果真实模型接口无法确定，则生成 mock adapter，保证产品流程可以演示。
```

---

## 2. 功能边界

### 2.1 Productize Mode 应该做什么

必须支持：

1. 复用已有论文分析结果
2. 复用已有仓库分析结果
3. 分析论文技术能力
4. 推荐 3 个产品 idea
5. 对产品 idea 进行评分
6. 选择最适合的 MVP 产品
7. 生成 `product_spec.md`
8. 判断产品模板类型：
   - image product
   - text product
   - video product
   - generic file-analysis product
9. 生成 `generated_product/app.py`
10. 生成 `generated_product/adapter.py`
11. 生成 `generated_product/README.md`
12. 生成 `generated_product/requirements.txt`
13. 支持 mock mode
14. 支持在主 Streamlit 页面中触发 Productize Mode
15. 支持展示生成的产品文件内容
16. 支持提示用户如何运行生成的产品 demo

### 2.2 Productize Mode 不应该默认做什么

不要默认：

1. 修改原始 GitHub 仓库代码
2. 直接在原 repo 里写文件
3. 自动下载大型模型权重
4. 自动下载大型数据集
5. 自动训练完整模型
6. 自动执行未知 shell 脚本
7. 自动运行危险命令
8. 保证所有论文都能真实接入模型

正确做法：

```text
原始 repo 保持不动。
产品代码生成到 generated_product/。
adapter.py 通过统一接口尝试调用原 repo。
如果无法确定真实调用方式，则使用 mock adapter。
```

---

## 3. 新增目录结构

请在现有项目基础上新增以下文件和目录。

```text
PaperPilot/
│
├── productize/
│   ├── __init__.py
│   ├── product_pipeline.py
│   ├── product_templates.py
│   ├── product_scaffold.py
│   └── product_tester.py
│
├── agents/
│   ├── product_opportunity_agent.py
│   ├── product_designer_agent.py
│   ├── tech_adapter_agent.py
│   ├── frontend_builder_agent.py
│   └── product_test_agent.py
│
├── prompts/
│   ├── product_opportunity_prompt.txt
│   ├── product_designer_prompt.txt
│   ├── tech_adapter_prompt.txt
│   ├── frontend_builder_prompt.txt
│   └── product_test_prompt.txt
│
├── generated_product/
│   ├── app.py
│   ├── adapter.py
│   ├── README.md
│   ├── product_spec.md
│   ├── requirements.txt
│   └── outputs/
```

注意：

- 如果已有类似目录，请复用，不要重复创建混乱结构。
- 不要删除已有文件。
- 不要改坏现有 Reproduce Mode。
- 新增功能要尽量模块化，不要把所有逻辑塞进 `app.py`。

---

## 4. 新增 Agent 设计

### 4.1 Product Opportunity Agent

文件：

```text
agents/product_opportunity_agent.py
prompts/product_opportunity_prompt.txt
```

职责：

根据论文分析结果、方法拆解结果、仓库分析结果，判断论文技术适合做什么应用。

输入：

```python
{
    "paper_info": "...",
    "method_info": "...",
    "repo_info": "...",
    "target_user": "...",
    "product_goal": "..."
}
```

输出：

```text
1. 技术能力总结
2. 输入输出形式
3. 适合的应用场景
4. 不适合的应用场景
5. 目标用户
6. 3 个产品 idea
7. 每个 idea 的评分
8. 推荐 MVP
```

评分维度：

```text
用户价值
技术可行性
展示效果
论文技术匹配度
实现难度
安全风险
```

输出应包含表格，例如：

```text
| 产品 idea | 用户价值 | 技术可行性 | 展示效果 | 实现难度 | 推荐分 |
|---|---:|---:|---:|---:|---:|
| 智能图片标注工具 | 9 | 8 | 9 | 6 | 8.5 |
```

---

### 4.2 Product Designer Agent

文件：

```text
agents/product_designer_agent.py
prompts/product_designer_prompt.txt
```

职责：

把推荐 MVP 变成具体产品需求文档。

输入：

```python
{
    "opportunities": "...",
    "paper_info": "...",
    "method_info": "...",
    "repo_info": "..."
}
```

输出：

```text
1. 产品名称
2. 产品一句话介绍
3. 目标用户
4. 用户痛点
5. 核心功能
6. 用户使用流程
7. 输入格式
8. 输出格式
9. 页面设计
10. MVP 功能边界
11. 后续扩展功能
12. 风险与限制
```

输出内容将保存到：

```text
generated_product/product_spec.md
```

---

### 4.3 Tech Adapter Agent

文件：

```text
agents/tech_adapter_agent.py
prompts/tech_adapter_prompt.txt
```

职责：

分析如何把原论文代码封装成统一接口。

输入：

```python
{
    "repo_info": "...",
    "repo_path": "...",
    "product_spec": "...",
    "template_type": "image/text/video/file"
}
```

输出：

```text
1. 可能的模型加载文件
2. 可能的推理入口文件
3. 可能的 checkpoint 路径
4. 原代码输入格式
5. 原代码输出格式
6. adapter.py 设计建议
7. 是否可以真实接入
8. 如果不能真实接入，mock mode 如何实现
```

注意：

- 不要直接修改原 repo。
- 只生成适配方案。
- 真实调用方式不确定时，必须 fallback 到 mock mode。

---

### 4.4 Frontend Builder Agent

文件：

```text
agents/frontend_builder_agent.py
prompts/frontend_builder_prompt.txt
```

职责：

根据产品类型和产品需求，生成 Streamlit 前端设计方案。

输入：

```python
{
    "product_spec": "...",
    "template_type": "image/text/video/file",
    "adapter_plan": "..."
}
```

输出：

```text
1. 页面标题
2. 页面布局
3. 用户输入组件
4. 运行按钮
5. 结果展示方式
6. 下载输出方式
7. 错误提示方式
```

真正代码生成可以由 `product_scaffold.py` 根据模板完成，不必完全依赖 LLM 生成代码。

---

### 4.5 Product Test Agent

文件：

```text
agents/product_test_agent.py
prompts/product_test_prompt.txt
```

职责：

检查生成的产品原型是否完整、是否可以启动、是否有说明文档。

输入：

```python
{
    "generated_product_dir": "generated_product",
    "template_type": "...",
    "files": [...]
}
```

输出：

```text
1. 文件完整性检查
2. app.py 是否存在
3. adapter.py 是否存在
4. README 是否存在
5. product_spec 是否存在
6. mock mode 是否可用
7. 运行方式是否清楚
8. 可能的问题
9. 下一步建议
```

---

## 5. Prompt 文件内容要求

请创建以下 prompt。

### 5.1 `product_opportunity_prompt.txt`

```text
你是论文技术产品化顾问。请根据论文分析、方法拆解和代码仓库信息，判断这项论文技术适合做什么真实应用。

你需要输出：
1. 技术能力总结
2. 模型或算法的输入输出形式
3. 适合的应用场景
4. 不适合的应用场景
5. 目标用户
6. 3 个产品 idea
7. 产品 idea 评分表
8. 推荐 MVP 产品
9. 推荐理由

评分维度包括：
- 用户价值
- 技术可行性
- 展示效果
- 论文技术匹配度
- 实现难度
- 安全风险

要求：
- 不要夸大论文技术能力
- 不要假设代码已经可以完美运行
- 如果真实模型难以接入，请说明可以先做 mock demo
- 输出结构化 Markdown
```

### 5.2 `product_designer_prompt.txt`

```text
你是 AI 产品经理。请根据推荐的产品 idea，设计一个适合课程展示的 MVP 产品。

你需要输出：
1. 产品名称
2. 产品一句话介绍
3. 目标用户
4. 用户痛点
5. 核心功能
6. 用户使用流程
7. 输入格式
8. 输出格式
9. 页面设计
10. MVP 功能边界
11. 后续可扩展功能
12. 风险与限制

要求：
- 产品要偏 application，不要偏论文总结
- MVP 要能在 Streamlit 中展示
- 功能边界要现实，不要承诺完整商业系统
- 输出结构化 Markdown
```

### 5.3 `tech_adapter_prompt.txt`

```text
你是机器学习工程适配专家。请根据代码仓库分析和产品需求，设计一个统一的 ModelAdapter 接口，用于把论文代码包装成产品可调用模块。

你需要输出：
1. 可能的模型加载文件
2. 可能的推理入口文件
3. 可能的 checkpoint 路径
4. 原代码可能需要的输入格式
5. 原代码可能输出的结果格式
6. adapter.py 的设计建议
7. 是否可以真实接入原 repo
8. 如果不能确定真实接口，mock mode 应该如何返回结果
9. 用户需要手动补充的信息

要求：
- 不要修改原始 repo
- 不要编造不存在的函数
- 如果不能确定真实调用方式，明确写出“不确定”
- 必须提供 mock fallback 方案
- 输出结构化 Markdown
```

### 5.4 `frontend_builder_prompt.txt`

```text
你是 Streamlit 产品前端设计助手。请根据产品需求和模板类型，设计一个可以展示论文技术的交互式页面。

你需要输出：
1. 页面标题
2. 页面结构
3. 输入组件
4. 操作按钮
5. 结果展示方式
6. 下载功能
7. 错误提示
8. 用户引导文案

要求：
- 页面要适合课程 project 展示
- 交互流程要简单
- 必须支持 mock mode
- 输出结构化 Markdown
```

### 5.5 `product_test_prompt.txt`

```text
你是产品原型测试助手。请检查 generated_product 目录是否完整，以及生成的产品 demo 是否适合展示。

你需要检查：
1. app.py 是否存在
2. adapter.py 是否存在
3. README.md 是否存在
4. product_spec.md 是否存在
5. requirements.txt 是否存在
6. outputs/ 是否存在
7. mock mode 是否可用
8. 运行命令是否清楚
9. 是否有明显安全风险
10. 下一步修复建议

要求：
- 输出结构化 Markdown
- 如果存在缺失文件，明确指出
- 如果无法真实运行模型，说明 mock mode 是否足以展示流程
```

---

## 6. Product Templates 设计

请在 `productize/product_templates.py` 中实现模板类型判断和模板内容。

至少支持四类模板：

```text
image
text
video
file
```

### 6.1 Image Product Template

适用论文：

```text
图像分类
图像检测
图像分割
图像生成
图像增强
OCR
医学图像分析
```

产品形式：

```text
上传图片 → 调用模型 → 显示结果图 / 标签 / mask / 文本说明
```

Streamlit 页面应该包含：

```text
st.file_uploader("Upload an image")
st.image(input_image)
st.button("Run Model")
st.image(result_image) 或 st.json(result)
st.download_button(...)
```

### 6.2 Text Product Template

适用论文：

```text
文本分类
摘要生成
问答系统
RAG
机器翻译
代码生成
信息抽取
```

产品形式：

```text
输入文本 → 调用模型 → 输出摘要 / 回答 / 标签 / 结构化结果
```

Streamlit 页面应该包含：

```text
st.text_area("Input text")
st.button("Run Model")
st.markdown(result)
st.download_button(...)
```

### 6.3 Video Product Template

适用论文：

```text
视频理解
目标跟踪
动作识别
世界模型
object-centric learning
强化学习可视化
```

产品形式：

```text
上传视频或帧序列 → 调用模型 → 显示关键帧 / 轨迹 / 分析报告
```

Streamlit 页面应该包含：

```text
st.file_uploader("Upload a video")
st.video(input_video)
st.button("Analyze")
st.markdown(report)
```

### 6.4 File Analysis Product Template

适用论文：

```text
通用文件分析
表格分析
日志分析
文档解析
代码分析
```

产品形式：

```text
上传文件 → 调用模型或算法 → 输出分析报告
```

Streamlit 页面应该包含：

```text
st.file_uploader("Upload a file")
st.button("Analyze")
st.markdown(report)
st.download_button(...)
```

---

## 7. ModelAdapter 统一接口

`generated_product/adapter.py` 必须生成统一接口。

接口要求：

```python
class ModelAdapter:
    def __init__(self, repo_path: str = "../workspace", device: str = "cpu", mock_mode: bool = True):
        self.repo_path = repo_path
        self.device = device
        self.mock_mode = mock_mode
        self.model = None

    def setup(self):
        """Check paths, dependencies, and runtime mode."""
        pass

    def load_model(self):
        """Load model if real integration is available; otherwise use mock mode."""
        pass

    def predict(self, input_data):
        """Run inference or return mock result."""
        pass
```

### 7.1 Mock mode 要求

mock mode 必须可用。

即使真实模型无法加载，产品 demo 也要能运行。

不同模板的 mock 返回：

#### Image mock

```python
{
    "type": "image",
    "message": "Mock image prediction completed.",
    "result": {
        "label": "demo_object",
        "confidence": 0.95
    }
}
```

#### Text mock

```python
{
    "type": "text",
    "result": "This is a mock response generated by the product prototype."
}
```

#### Video mock

```python
{
    "type": "video",
    "report": "Mock video analysis completed. Key objects and temporal patterns would be shown here."
}
```

#### File mock

```python
{
    "type": "file",
    "report": "Mock file analysis completed. The generated report would be shown here."
}
```

---

## 8. Product Scaffold 设计

请在 `productize/product_scaffold.py` 中实现代码生成。

建议接口：

```python
def scaffold_product(
    template_type: str,
    product_spec: str,
    adapter_plan: str,
    frontend_plan: str,
    repo_path: str,
    output_dir: str = "generated_product"
) -> dict:
    ...
```

该函数需要生成：

```text
generated_product/app.py
generated_product/adapter.py
generated_product/README.md
generated_product/product_spec.md
generated_product/requirements.txt
generated_product/outputs/
```

返回：

```python
{
    "output_dir": "...",
    "files": [...],
    "success": True,
    "message": "..."
}
```

要求：

- 如果 `generated_product/` 已存在，不要静默覆盖。
- 可以先备份旧目录，例如 `generated_product_backup_<timestamp>/`。
- 生成的 `app.py` 必须能在 mock mode 下运行。
- 生成的 `README.md` 必须说明如何运行。
- `adapter.py` 中必须包含 TODO，提示如何接入真实 repo。

---

## 9. Product Pipeline 设计

请在 `productize/product_pipeline.py` 中实现主流程。

建议接口：

```python
def run_productize_pipeline(
    paper_info: str,
    method_info: str,
    repo_info: str,
    repo_path: str,
    target_user: str,
    product_goal: str,
    llm_client,
) -> dict:
    ...
```

流程：

```text
1. Product Opportunity Agent 生成产品机会
2. Product Designer Agent 生成产品需求
3. select_product_template 判断模板
4. Tech Adapter Agent 生成适配方案
5. Frontend Builder Agent 生成前端方案
6. scaffold_product 生成产品代码
7. Product Test Agent 生成测试报告
8. 返回完整结果
```

返回格式：

```python
{
    "opportunities": "...",
    "product_spec": "...",
    "template_type": "...",
    "adapter_plan": "...",
    "frontend_plan": "...",
    "scaffold_result": {...},
    "test_report": "..."
}
```

错误处理要求：

- 某个 Agent 失败时不要直接崩溃
- 返回已经完成的部分
- 明确提示失败阶段
- 保证至少可以生成 mock product

---

## 10. Product Tester 设计

请在 `productize/product_tester.py` 中实现基础检查。

建议接口：

```python
def inspect_generated_product(output_dir: str = "generated_product") -> dict:
    ...
```

检查：

```text
app.py
adapter.py
README.md
product_spec.md
requirements.txt
outputs/
```

返回：

```python
{
    "exists": True,
    "missing_files": [],
    "files": [...],
    "can_run_mock": True,
    "notes": [...]
}
```

可以做轻量语法检查：

```bash
python -m py_compile generated_product/app.py generated_product/adapter.py
```

不要自动启动 Streamlit，除非用户明确点击按钮。

---

## 11. Streamlit 主页面集成

请修改现有 `app.py`，但不要破坏原有功能。

新增一个模式选择：

```python
mode = st.sidebar.radio(
    "Select Mode",
    ["Reproduce Paper", "Productize Paper"]
)
```

### 11.1 Reproduce Paper

保留现有功能，不要破坏。

### 11.2 Productize Paper

新增输入：

```text
Target user
Product goal
Preferred product type:
- Auto
- Image
- Text
- Video
- File
```

新增按钮：

```text
Generate Product Prototype
```

点击后调用：

```python
run_productize_pipeline(...)
```

前提：

- 如果当前会话中已有 `paper_info`、`method_info`、`repo_info`、`repo_path`，直接复用。
- 如果没有，则提示用户先运行 Reproduce Mode，或者自动调用已有论文/仓库分析流程。

页面展示：

```text
1. Product Opportunities
2. Selected MVP Product Spec
3. Template Type
4. Adapter Plan
5. Frontend Plan
6. Generated Files
7. Product Test Report
8. How to Run Generated Product
```

显示运行命令：

```bash
cd generated_product
streamlit run app.py
```

---

## 12. 不要破坏已有功能

在修改前请先检查已有项目结构。

必须做到：

```text
1. 保留原有 Reproduce Mode
2. 保留原有 run_paperpilot
3. 保留原有 Debug Agent
4. 保留原有 Runner Agent
5. 保留原有 outputs/
6. 新功能独立放在 productize/ 和 generated_product/
7. 新增 Agent 不影响旧 Agent
```

如果需要修改已有函数，请尽量新增参数，不要改变原函数返回结构。  
如果必须改变返回结构，要保证向后兼容。

---

## 13. 分阶段开发要求

请严格按照下面阶段完成。  
每完成一个阶段必须先自检，确认无误后再进入下一阶段。

---

### 阶段 0：检查现有项目

任务：

1. 查看当前项目目录结构
2. 确认已有 Reproduce Mode 文件
3. 确认 `main.py`、`app.py`、`agents/`、`tools/` 是否存在
4. 确认现有项目能否运行
5. 找出当前 LLM Client 和 BaseAgent 的实现方式
6. 总结新增功能应该如何接入

检查要求：

- 不修改任何文件
- 只做阅读和分析
- 输出现有项目结构摘要
- 输出接入计划

完成后输出：

```text
阶段 0 完成。
自检结果：
- 已检查项目结构：通过 / 不通过
- 已确认 Reproduce Mode：通过 / 不通过
- 已找到 Agent 基类：通过 / 不通过
- 已找到 LLM Client：通过 / 不通过
- 已找到 Streamlit 入口：通过 / 不通过
- 接入计划：
- 发现的问题：
- 下一步：
```

只有阶段 0 检查通过后，才能进入阶段 1。

---

### 阶段 1：创建 Productize 目录和 Prompt

任务：

1. 创建 `productize/`
2. 创建 `generated_product/`
3. 创建新增 Agent 文件
4. 创建新增 prompt 文件
5. 暂时不实现复杂逻辑，只放骨架

检查要求：

- 所有新增目录存在
- 所有新增文件存在
- 不影响旧功能
- Python 文件语法检查通过

完成后输出：

```text
阶段 1 完成。
自检结果：
- productize/：通过 / 不通过
- generated_product/：通过 / 不通过
- 新增 Agent 文件：通过 / 不通过
- 新增 prompt 文件：通过 / 不通过
- Python 语法检查：通过 / 不通过
- 旧功能未破坏：通过 / 不通过
- 发现的问题：
- 下一步：
```

---

### 阶段 2：实现 Product Templates 和 Product Scaffold

任务：

1. 实现 `productize/product_templates.py`
2. 支持 `image/text/video/file` 四类模板
3. 实现 `select_product_template`
4. 实现 `productize/product_scaffold.py`
5. 能生成 `generated_product/app.py`
6. 能生成 `generated_product/adapter.py`
7. 能生成 `README.md`
8. 能生成 `product_spec.md`
9. 能生成 `requirements.txt`

检查要求：

- 每种模板都能生成 app.py 和 adapter.py
- 生成的 app.py 能语法检查通过
- 生成的 adapter.py 能语法检查通过
- mock mode 可用
- 不覆盖旧产品目录，或者能自动备份

完成后输出：

```text
阶段 2 完成。
自检结果：
- image template：通过 / 不通过
- text template：通过 / 不通过
- video template：通过 / 不通过
- file template：通过 / 不通过
- scaffold_product：通过 / 不通过
- generated app.py 语法：通过 / 不通过
- generated adapter.py 语法：通过 / 不通过
- mock mode：通过 / 不通过
- 发现的问题：
- 下一步：
```

---

### 阶段 3：实现 Productize Agents

任务：

1. 实现 Product Opportunity Agent
2. 实现 Product Designer Agent
3. 实现 Tech Adapter Agent
4. 实现 Frontend Builder Agent
5. 实现 Product Test Agent
6. 所有 Agent 使用现有 BaseAgent 和 LLM Client
7. 所有 Agent 支持 mock mode

检查要求：

- 所有新增 Agent 能在 mock mode 下运行
- prompt 能正确加载
- Agent 失败时有清晰错误
- 不影响已有 Agent

完成后输出：

```text
阶段 3 完成。
自检结果：
- Product Opportunity Agent：通过 / 不通过
- Product Designer Agent：通过 / 不通过
- Tech Adapter Agent：通过 / 不通过
- Frontend Builder Agent：通过 / 不通过
- Product Test Agent：通过 / 不通过
- prompt 加载：通过 / 不通过
- mock mode：通过 / 不通过
- 旧 Agent 未破坏：通过 / 不通过
- 发现的问题：
- 下一步：
```

---

### 阶段 4：实现 Product Pipeline

任务：

1. 实现 `productize/product_pipeline.py`
2. 串联所有 Productize Agent
3. 调用 `select_product_template`
4. 调用 `scaffold_product`
5. 调用 Product Tester
6. 返回结构化结果
7. 错误时保留中间结果

检查要求：

- mock mode 下完整 pipeline 可运行
- 能生成 `generated_product/`
- 能返回 opportunities
- 能返回 product_spec
- 能返回 adapter_plan
- 能返回 frontend_plan
- 能返回 test_report
- 失败时不崩溃

完成后输出：

```text
阶段 4 完成。
自检结果：
- Product pipeline mock run：通过 / 不通过
- opportunities：通过 / 不通过
- product_spec：通过 / 不通过
- template selection：通过 / 不通过
- scaffold：通过 / 不通过
- test_report：通过 / 不通过
- 错误处理：通过 / 不通过
- 发现的问题：
- 下一步：
```

---

### 阶段 5：集成到 Streamlit 主页面

任务：

1. 修改现有 `app.py`
2. 新增模式选择：
   - Reproduce Paper
   - Productize Paper
3. 保留原 Reproduce 功能
4. Productize 页面中添加：
   - target user
   - product goal
   - preferred product type
   - Generate Product Prototype 按钮
5. 调用 `run_productize_pipeline`
6. 展示 Productize 输出结果
7. 展示生成文件路径
8. 展示运行 generated product 的命令

检查要求：

- `streamlit run app.py` 可以启动
- Reproduce Mode 仍然可用
- Productize Mode 可以打开
- mock mode 下可以生成产品原型
- 页面不会因为缺少 paper_info 直接崩溃
- 如果缺少前置分析结果，要给出清晰提示

完成后输出：

```text
阶段 5 完成。
自检结果：
- Streamlit 启动：通过 / 不通过
- Reproduce Mode 未破坏：通过 / 不通过
- Productize Mode 页面：通过 / 不通过
- Productize pipeline 调用：通过 / 不通过
- 输出展示：通过 / 不通过
- 缺少前置结果时提示：通过 / 不通过
- 发现的问题：
- 下一步：
```

---

### 阶段 6：实现 Product Tester 和 mock demo 检查

任务：

1. 完善 `productize/product_tester.py`
2. 检查 generated product 文件完整性
3. 对 generated product 做 py_compile
4. 检查 README 中是否有运行命令
5. 检查 adapter.py 是否有 mock mode
6. 返回测试报告
7. 在 Productize 页面显示测试结果

检查要求：

- 文件完整性检查通过
- app.py py_compile 通过
- adapter.py py_compile 通过
- mock mode 检查通过
- README 检查通过

完成后输出：

```text
阶段 6 完成。
自检结果：
- 文件完整性：通过 / 不通过
- app.py py_compile：通过 / 不通过
- adapter.py py_compile：通过 / 不通过
- mock mode 检查：通过 / 不通过
- README 运行说明：通过 / 不通过
- Product Test Report 展示：通过 / 不通过
- 发现的问题：
- 下一步：
```

---

### 阶段 7：更新 README 和项目展示材料

任务：

1. 更新主项目 README
2. 添加 PaperPilot 2.0 介绍
3. 添加 Reproduce Mode 说明
4. 添加 Productize Mode 说明
5. 添加系统架构
6. 添加运行方式
7. 添加 demo 流程
8. 添加安全策略
9. 添加局限性
10. 添加未来改进方向

README 中必须包含以下项目介绍：

```text
PaperPilot 2.0 是一个多智能体论文复现与产品化助手。用户上传论文 PDF 并提供 GitHub 代码后，系统首先分析论文方法和开源仓库，生成复现计划；随后进入产品化模式，自动识别论文技术能力，推荐适合的应用场景，设计 MVP 产品，并生成基于 Streamlit 的交互式产品原型。系统通过统一的 ModelAdapter 封装论文代码，使原本面向研究的模型能够被包装成面向用户的应用，例如智能图像标注工具、文档问答助手或视频对象分析器。
```

检查要求：

- README 完整
- 安装说明清楚
- Reproduce Mode 说明清楚
- Productize Mode 说明清楚
- demo 流程清楚
- 安全限制说明清楚

完成后输出：

```text
阶段 7 完成。
自检结果：
- README：通过 / 不通过
- Reproduce Mode 说明：通过 / 不通过
- Productize Mode 说明：通过 / 不通过
- 运行说明：通过 / 不通过
- demo 流程：通过 / 不通过
- 安全策略：通过 / 不通过
- 发现的问题：
- 项目最终状态：
```

---

## 14. 安全要求

新增 Productize Mode 也必须遵守安全策略。

必须保证：

```text
1. 不修改原始 GitHub 仓库
2. 不默认执行训练命令
3. 不默认执行未知脚本
4. 不默认下载大型数据集
5. 不默认下载大型权重
6. 所有生成代码放在 generated_product/
7. generated_product/ 已存在时要提示或备份
8. adapter.py 默认 mock_mode=True
9. 用户需要手动关闭 mock_mode 才尝试真实模型
10. README 中要清楚说明真实接入需要人工检查
```

---

## 15. 生成产品 README 要求

`generated_product/README.md` 必须包含：

```text
# Generated Product Prototype

## Product Overview

## What This Demo Does

## Files

## How to Run

pip install -r requirements.txt
streamlit run app.py

## Mock Mode

This product runs in mock mode by default. Mock mode allows the demo workflow to be shown even when the original research model is not fully integrated.

## Real Model Integration

To connect the real model, update `adapter.py` according to the original repository's inference code.

## Limitations

This generated product is a prototype. It does not guarantee full reproduction of the original paper results.
```

---

## 16. generated_product/app.py 要求

生成的 `app.py` 必须：

1. 使用 Streamlit
2. 从 `adapter.py` 导入 `ModelAdapter`
3. 默认使用 `mock_mode=True`
4. 根据模板类型显示不同输入组件
5. 有清晰的标题和说明
6. 有运行按钮
7. 有结果展示
8. 捕获异常并显示错误
9. 不自动调用危险代码
10. 不依赖原 repo 一定可用

---

## 17. generated_product/adapter.py 要求

生成的 `adapter.py` 必须：

1. 包含 `ModelAdapter`
2. 包含 `setup`
3. 包含 `load_model`
4. 包含 `predict`
5. 默认 `mock_mode=True`
6. mock mode 下可以返回演示结果
7. 真实接入部分写 TODO
8. 不自动下载模型
9. 不自动训练
10. 不自动执行 shell 脚本

---

## 18. 主项目 README 新增内容建议

请在主 README 里添加：

```text
## Productize Mode

Productize Mode extends PaperPilot from paper reproduction to product prototyping. After analyzing the paper and its repository, PaperPilot can infer possible application scenarios, select a feasible MVP, and generate a Streamlit-based product prototype.

### Workflow

1. Analyze paper method
2. Analyze repository
3. Identify technical capabilities
4. Generate product ideas
5. Select MVP product
6. Generate product specification
7. Generate ModelAdapter
8. Generate Streamlit app
9. Test generated product files

### Generated Product

Generated product code is saved to:

generated_product/

To run:

cd generated_product
pip install -r requirements.txt
streamlit run app.py
```

---

## 19. 最终验收标准

完成后，项目应满足：

```text
1. 原 Reproduce Mode 可以继续使用
2. Productize Mode 可以在主页面进入
3. Productize Mode 可以生成产品 idea
4. Productize Mode 可以生成 product_spec.md
5. Productize Mode 可以生成 generated_product/app.py
6. Productize Mode 可以生成 generated_product/adapter.py
7. generated_product/app.py 能通过语法检查
8. generated_product/adapter.py 能通过语法检查
9. generated_product 默认 mock mode 可运行
10. README 中有完整说明
```

---

## 20. 最终演示流程

最终课程展示建议：

```text
Step 1：打开 PaperPilot 主页面

Step 2：进入 Reproduce Mode
上传论文 PDF + 输入 GitHub URL
生成论文分析和复现计划

Step 3：切换到 Productize Mode
输入：
- Target user：机器学习初学者
- Product goal：把论文技术变成可交互 demo
- Preferred product type：Auto

Step 4：点击 Generate Product Prototype

Step 5：系统输出：
- 技术能力总结
- 3 个产品 idea
- idea 评分表
- 推荐 MVP
- product_spec.md
- adapter_plan
- frontend_plan
- generated files
- product test report

Step 6：进入 generated_product/
运行：
streamlit run app.py

Step 7：展示生成的产品 demo
例如：
上传图片 → mock 模型分析 → 显示结果
或
输入文本 → mock 模型生成结果
```

---

## 21. 重要原则

请始终遵守：

1. **不要重写现有项目。**
2. **不要破坏已完成的论文复现功能。**
3. **新增功能必须模块化。**
4. **每个阶段完成后必须自检。**
5. **自检不通过不要进入下一阶段。**
6. **Productize Mode 必须支持 mock mode。**
7. **不要默认运行真实模型。**
8. **不要默认下载大型资源。**
9. **不要修改原始 GitHub repo。**
10. **生成的产品原型要适合课程展示。**

---

## 22. 请现在开始

请从阶段 0 开始。

第一步只检查现有项目，不要修改任何文件。  
阶段 0 完成并自检通过后，再进入阶段 1。
