# PaperPilot 功能修复实现文档

> 基于 2026-06-10 代码审查结果，修复三项高优先级功能问题。

---

## 1. Goal 路由

### 问题

UI 提供了 5 种 goal（只理解论文/跑通官方 demo/最小训练实验/复现主实验/Debug 报错），但 pipeline 始终跑完所有 Agent，goal 没有实际影响。

### 方案

在 `main.py` 中定义 goal → Agent 列表的映射，根据 goal 跳过不必要的 Agent。

### Goal-Agent 映射

| goal | 运行的 Agent | 说明 |
|------|-------------|------|
| `只理解论文` | PaperReader → MethodExtractor → Report | 跳过 clone、scan、env、experiment |
| `跑通官方 demo` | PaperReader → MethodExtractor → RepoClone → RepoAnalyzer → Env → Report | 跳过 experiment planner |
| `最小训练实验` | 全部 Agent | 完整 pipeline |
| `复现主实验` | 全部 Agent | 完整 pipeline |
| `Debug 报错` | 仅显示 Debug 区 | 跳过整个 pipeline |

### 改动文件

**`main.py`**
- 新增 `_get_pipeline_steps(goal)` 返回需要执行的 Agent 列表
- `run_paperpilot()` 按 goal 选择执行哪些 Agent
- 新增 `run_minimal_pipeline()` 和 `run_full_pipeline()` 两个内部路径，或通过条件分支控制

**`app.py`**
- `run_paperpilot()` 调用时传入 goal
- 如果 goal 是 "Debug 报错"，不调 `run_paperpilot()`，直接展开 Debug 区

---

## 2. 扫描版 PDF 处理

### 问题

扫描版 PDF 提取不到文本（空字符串），传给 PaperReader Agent 导致其报错，下游所有 Agent 拿不到论文上下文，整条 pipeline 产出「未生成」。

### 方案

`main.py` 中在调 PaperReader Agent 之前加守卫判断：如果 `paper_text` 为空或空白，跳过 Agent，设置 fallback 信息。

同时处理连带影响：
- MethodExtractor 依赖 `paper_info`，如果 paper_info 是 fallback 信息，MethodExtractor 也可以跳过
- `_run_agent` 里对空字符串输入增加前置校验

### 改动文件

**`main.py`**
- `run_paperpilot()` 中增加：
  ```python
  if not paper_text.strip():
      result["paper_info"] = "PDF 未提取到文本，文件可能是扫描版，请提供 OCR 版本。"
      # 跳过 PaperReader 和 MethodExtractor
  ```
- `_run_agent` 函数：输入为空时直接返回 fallback，不调 Agent

---

## 3. 进度反馈

### 问题

运行中一股脑把所有 Agent 状态列出来，用户不知道当前跑到哪一步了。

### 方案

`run_paperpilot()` 增加回调函数参数，每启动一个 Agent 时回调通知当前步骤名称。

`app.py` 里逐行追加当前 Agent 名称。

### 改动文件

**`main.py`**
- `run_paperpilot()` 新增 `progress_callback: Callable[[str], None] | None = None` 参数
- 每个 Agent 启动前调用 `progress_callback(agent_name)`

**`app.py`**
- 创建进度占位符 `progress_placeholder = st.empty()`
- 每次回调时追加一行：`progress_placeholder.markdown(...)`
- 移除原来的 `AGENT_STATUS_MESSAGES` 静态列表方式

---

## 4. Prompt 更新

### 改动文件

**`prompts/experiment_prompt.txt`**
- 开头增加 goal 说明，让 LLM 按用户目标调整输出
- 例如在 `repo_analyzer_prompt.txt` 中追加：`用户选择的复现目标是：{goal}`

**`prompts/report_prompt.txt`**
- 同上，引用 goal

---

## 需要修改的文件清单

| 文件 | 改动类型 |
|------|---------|
| `docs/PaperPilot_Codex_Prompt_Revised.md` — `docs/PaperPilot_Codex_Prompt_Revised.md` | 移动（已移） |
| `docs/DEVELOPMENT.md` | 移动（已移） |
| `docs/implementation-plan.md` | 新建（本文档） |
| `main.py` | goal 路由 + PDF 空文本守卫 + progress callback |
| `app.py` | 进度显示 + goal 路由入口调整 |
| `prompts/experiment_prompt.txt` | 引用 goal |
| `prompts/report_prompt.txt` | 引用 goal |

## 验证方式

1. **Goal 路由**：选「只理解论文」，确认 clone/scan/env 等 Agent 不执行
2. **扫描版 PDF**：用空白 PDF 或非 PDF 文件测试，确认不崩溃，提示「扫描版」
3. **进度反馈**：运行时确认每步名称逐一出现
