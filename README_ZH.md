# PaperPilot 2.0

[English](README.md)
![CI](https://github.com/Vincent-Wenhan/PaperPilot/actions/workflows/ci.yml/badge.svg)

PaperPilot 是一个有安全边界的论文复现与 Research-to-Product 多 Agent Workbench。Reproduce Mode 用于分析论文和可选 GitHub 仓库，生成复现计划，并可生成一个小型可运行复现项目。Productize Mode 用于提取论文能力、生成 PRD/MVP、评估产品方案，并生成 mock-first 的静态 Web 产品原型。

系统不承诺自动完整复现实验、不承诺复现论文指标，也不会自动把研究仓库接成生产级模型服务。

## 当前入口

当前主界面是 Next.js Agent Workbench + FastAPI。旧的 Streamlit 主界面已删除。

```text
frontend/        Next.js workbench
backend/         FastAPI API、WebSocket、run/action/file/patch 服务
graphs/          Reproduce / Productize LangGraph 工作流
pipeline/        兼容旧调用方式的 pipeline 入口
productize/      静态产品原型 scaffold 与 inspector
tools/           PDF、仓库、命令、代码质量、文件工具
workspace/runs/  Workbench run 级输出目录
outputs/         兼容旧 pipeline 的本地输出目录
```

## 安装

推荐 Python 3.12。

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pip check
python -c "import fitz, langgraph, openai, yaml; print('imports ok')"
```

前端依赖：

```bash
cd frontend
npm ci
```

## 运行

启动后端：

```bash
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

另开终端启动前端：

```bash
cd frontend
npm run dev -- --hostname 127.0.0.1 --port 3000
```

浏览器打开 `http://localhost:3000`。

## LLM 配置

PaperPilot 使用 OpenAI-compatible Chat Completions 接口。可以通过 Workbench 设置/API 或环境变量配置：

```bash
set LLM_API_KEY=...
set LLM_BASE_URL=https://api.openai.com/v1
set LLM_MODEL=gpt-4o-mini
set LLM_MOCK_MODE=false
```

`LLM_MOCK_MODE=true` 用于本地 mock 演示。API key 不会写入仓库配置文件。

## Reproduce Mode

大致流程：

```text
解析论文 -> 研究理解
       -> 仓库准备 -> 仓库理解
       -> 复现规划 -> 可选代码生成
       -> 代码审查 / 修订 / sandbox 检查
       -> 执行诊断 -> 报告
```

Workbench 创建的新 run 会把输出写到：

```text
workspace/runs/<run_id>/outputs/
workspace/runs/<run_id>/outputs/code/
```

直接调用旧 pipeline 时仍兼容 `outputs/`。

## Productize Mode

流程：

```text
论文 -> 能力卡 -> 综合分析 -> PRD/MVP
    -> 原型计划 -> 评估/修订 -> 静态产品原型
```

生成的产品原型是静态 Web bundle，不需要 Streamlit：

```text
generated_product/<product_name>/
  index.html
  app.js
  adapter.js
  styles.css
  README.md
  product_spec.md
  outputs/
```

运行方式：

```bash
cd generated_product/<product_name>
python -m http.server 8000
```

也可以直接用浏览器打开 `index.html`。

Workbench 创建的新 Productize run 会把产品原型写到：

```text
workspace/runs/<run_id>/generated_product/
```

生成的 `adapter.js` 默认 mock mode。真实模型接入必须先人工审查原仓库的推理入口、依赖、checkpoint、输入输出和错误处理。

## 验证

```bash
python -m compileall main.py config.py
python -m compileall agents tools pipeline productize schemas runtime graphs backend
python -m pytest tests/ -q
cd frontend && npm test && npm run build
```
