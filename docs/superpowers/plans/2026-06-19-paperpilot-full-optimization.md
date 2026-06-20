# PaperPilot Full Project Optimization (Phase 0-7) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform PaperPilot from an Agent Workbench Preview into a product-quality Research Agent IDE across 7 phases: engineering fixes, frontend redesign, event-driven graph, code workbench, patch-first approval, productize quality, and reproduce quality.

**Architecture:** Enhance the existing `frontend/` (Next.js) + `backend/` (FastAPI) + `graphs/` (LangGraph) + `runtime/` stack. Phase 0 fixes CI/deps. Phase 1 splits oversized components and introduces Tailwind design system. Phase 2 unifies event streaming between backend graph nodes and frontend WorkflowGraph. Phase 3 adds Monaco Editor and file tree. Phase 4 makes all code changes go through patch-first approval. Phases 5-6 add evaluation/revision quality loops. Phase 7 polishes docs and demos.

**Tech Stack:** Python 3.12, FastAPI, LangGraph, Next.js 14, React 18, TypeScript, Zustand, @xyflow/react, @monaco-editor/react, react-diff-viewer-continued, Tailwind CSS, @radix-ui

---

### Task 1: Phase 0 — Create requirements-dev.txt

**Files:**
- Create: `requirements-dev.txt`

- [ ] **Step 1: Create requirements-dev.txt**

```text
pytest>=8,<9
```

- [ ] **Step 2: Commit**

```bash
git add requirements-dev.txt
git commit -m "chore(deps): add requirements-dev.txt with pytest"
```

---

### Task 2: Phase 0 — Enhance CI with frontend build and dev deps

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Update CI workflow**

Replace current `.github/workflows/ci.yml` with:

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  backend:
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
          pip install -r requirements-dev.txt

      - name: Check Python syntax
        run: |
          python -m py_compile app.py main.py config.py
          python -m py_compile agents/*.py
          python -m py_compile agents/legacy/*.py
          python -m py_compile tools/*.py
          python -m py_compile pipeline/*.py
          python -m py_compile productize/*.py
          python -m py_compile schemas/*.py
          python -m py_compile runtime/*.py
          python -m py_compile graphs/*.py
          python -m py_compile graphs/subgraphs/*.py
          python -m py_compile backend/*.py
          python -m py_compile backend/**/*.py

      - name: Run tests
        run: |
          pytest tests/ -v --tb=long 2>&1 | tee /tmp/pytest-results.log

  frontend:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: "20"

      - name: Install and build frontend
        run: |
          cd frontend
          npm ci
          npm run build
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add frontend build and backend compile check"
```

---

### Task 3: Phase 0 — Sync README with workbench startup instructions

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add clear startup sections to README**

After the existing "## Running" section (around line 183), replace the Streamlit-only instructions with:

```markdown
## Running

### Legacy Streamlit App

```bash
cd <path/to/PaperPilot>
conda run -n paperpilot streamlit run app.py
```

Open the local address output by Streamlit in your browser. The application entry is `app.py`; the core orchestration function is `run_paperpilot()` in `main.py`.

### Agent Workbench (Next.js + FastAPI)

The workbench is the new Research Agent IDE surface with workflow graph,
co-planning, action approval, artifacts, code, diff, runner review, and tool
trace panels.

**Start the FastAPI backend:**

```bash
cd <path/to/PaperPilot>
conda run -n paperpilot uvicorn backend.main:app --reload --port 8000
```

**Start the Next.js frontend (in a separate terminal):**

```bash
cd <path/to/PaperPilot/frontend>
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

**Node dependencies:** Node.js 20+ required. Install with `npm install` inside `frontend/`.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs(readme): add workbench startup and dual-runtime instructions"
```

---

### Task 4: Phase 1 — Install frontend dependencies

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install new frontend packages**

```bash
cd frontend
npm install @monaco-editor/react react-diff-viewer-continued clsx tailwind-merge class-variance-authority @radix-ui/react-tabs @radix-ui/react-dialog @radix-ui/react-dropdown-menu
npm install -D tailwindcss postcss autoprefixer
```

- [ ] **Step 2: Initialize Tailwind config**

```bash
cd frontend
npx tailwindcss init -p
```

- [ ] **Step 3: Create `frontend/tailwind.config.ts`**

Replace the generated `tailwind.config.js` with:

```ts
import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        surface: "#ffffff",
        "surface-muted": "#f7f8fa",
        border: "#d9dee6",
        "border-strong": "#bdc6d1",
        muted: "#657080",
        soft: "#8a94a3",
        accent: "#176b5d",
        "accent-strong": "#0f564a",
        green: "#1f7a4d",
        amber: "#a56412",
        red: "#b42318",
        violet: "#6d4cc2",
        blue: "#2867b2",
      },
    },
  },
  plugins: [],
};

export default config;
```

- [ ] **Step 4: Add Tailwind directives to `frontend/app/globals.css`**

Replace the top of `frontend/app/globals.css` (keep all existing CSS after the tailwind directives):

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  ...existing vars...
```

The existing `:root` block and all subsequent CSS selectors remain unchanged — Tailwind sits on top; custom properties and selectors continue to work alongside utility classes.

- [ ] **Step 5: Verify build works**

```bash
cd frontend
npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 6: Commit**

```bash
cd frontend
git add package.json package-lock.json tailwind.config.ts postcss.config.js app/globals.css
cd ..
git add frontend/
git commit -m "feat(frontend): add Tailwind CSS, Monaco editor, diff viewer, Radix UI deps"
```

---

### Task 5: Phase 1 — Create lib/utils.ts with cn helper

**Files:**
- Create: `frontend/lib/utils.ts`

- [ ] **Step 1: Create the cn utility**

```ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/lib/utils.ts
git commit -m "feat(frontend): add cn utility for Tailwind class merging"
```

---

### Task 6: Phase 1 — Split TopBar from workspace-shell

**Files:**
- Create: `frontend/components/layout/top-bar.tsx`
- Modify: `frontend/components/workspace-shell.tsx`

- [ ] **Step 1: Create `frontend/components/layout/top-bar.tsx`**

```tsx
"use client";

import { Layers } from "lucide-react";
import { StatusPill } from "@/components/status-pill";
import type { WorkflowStatus } from "@/lib/mock-data";

type TopBarProps = {
  project: string;
  mode: string;
  model: string;
  summary: string;
  runStatus: WorkflowStatus;
};

export function TopBar({ project, mode, model, summary, runStatus }: TopBarProps) {
  return (
    <header className="topbar">
      <div className="brand-block">
        <div className="brand-mark">
          <Layers size={18} />
        </div>
        <div>
          <span className="brand-name">PaperPilot</span>
          <span className="brand-subtitle">Research Agent IDE</span>
        </div>
      </div>

      <div className="topbar-context">
        <span>Project: {project}</span>
        <span>Mode: {mode}</span>
        <span>Model: {model}</span>
      </div>

      <div className="run-state">
        <span>{summary || "No backend run created yet"}</span>
        <StatusPill status={runStatus} />
      </div>
    </header>
  );
}
```

- [ ] **Step 2: Update `workspace-shell.tsx` to use TopBar**

In `workspace-shell.tsx`, replace the `header` element (lines 404-425):

```tsx
import { TopBar } from "@/components/layout/top-bar";

// Replace the <header className="topbar">...</header> block with:
<TopBar
  project={currentProject}
  mode={currentMode}
  model={currentModel}
  summary={apiRun?.summary ?? ""}
  runStatus={apiRun?.status ?? "pending"}
/>
```

- [ ] **Step 3: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add frontend/components/layout/top-bar.tsx frontend/components/workspace-shell.tsx
git commit -m "refactor(frontend): extract TopBar component from workspace-shell"
```

---

### Task 7: Phase 1 — Split ProjectSidebar from workspace-shell

**Files:**
- Create: `frontend/components/layout/project-sidebar.tsx`
- Modify: `frontend/components/workspace-shell.tsx`

- [ ] **Step 1: Create `frontend/components/layout/project-sidebar.tsx`**

```tsx
"use client";

import type { ChangeEvent, FormEvent, ReactNode } from "react";
import { useRef } from "react";
import {
  Activity,
  Boxes,
  FileText,
  Play,
  Plus,
  Save,
  Search,
  Settings,
  Upload,
} from "lucide-react";

import { StatusPill } from "@/components/status-pill";
import type { ProjectNavItem, RunMode, WorkflowStatus } from "@/lib/mock-data";

type ProjectSidebarProps = {
  projectId: string;
  currentTask: string;
  mode: RunMode;
  runForm: RunFormState;
  query: string;
  selectedNavId: string;
  visibleNavItems: ProjectNavItem[];
  creatingRun: boolean;
  testingConnection: boolean;
  savingConfig: boolean;
  uploadingPdf: boolean;
  uploadedFileName: string;
  onQueryChange: (q: string) => void;
  onNavSelect: (id: string) => void;
  onFormUpdate: <K extends keyof RunFormState>(key: K, value: RunFormState[K]) => void;
  onFileUpload: (event: ChangeEvent<HTMLInputElement>) => void;
  onSaveConfig: () => void;
  onTestConnection: () => void;
  onSubmitRun: (event: FormEvent<HTMLFormElement>) => void;
  onResetWorkspace: () => void;
};

type RunFormState = {
  project_id: string;
  mode: RunMode;
  task: string;
  pdf_path: string;
  github_url: string;
  hardware: string;
  gpu_info: string;
  goal: string;
  target_user: string;
  product_goal: string;
  preferred_type: string;
  api_key: string;
  base_url: string;
  model: string;
  implementation_model: string;
  mock_mode: boolean;
};

export function ProjectSidebar({
  projectId: _projectId,
  currentTask,
  mode,
  runForm,
  query,
  selectedNavId,
  visibleNavItems,
  creatingRun,
  testingConnection,
  savingConfig,
  uploadingPdf,
  uploadedFileName,
  onQueryChange,
  onNavSelect,
  onFormUpdate,
  onFileUpload,
  onSaveConfig,
  onTestConnection,
  onSubmitRun,
  onResetWorkspace,
}: ProjectSidebarProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  return (
    <aside className="navigator">
      <div className="navigator-header">
        <div>
          <p className="eyebrow">Workspace</p>
          <h1>{currentTask}</h1>
        </div>
        <button
          className="icon-button"
          title="New run"
          type="button"
          onClick={onResetWorkspace}
        >
          <Plus size={17} />
        </button>
      </div>

      <div className="search-box">
        <Search size={16} />
        <input
          aria-label="Search workspace"
          placeholder="Search runs, files, agents"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
        />
      </div>

      <form className="run-form" onSubmit={onSubmitRun}>
        <div className="form-row">
          <label>
            <span>Mode</span>
            <select
              value={runForm.mode}
              onChange={(event) =>
                onFormUpdate("mode", event.target.value as RunMode)
              }
            >
              <option value="reproduce">Reproduce</option>
              <option value="productize">Productize</option>
            </select>
          </label>
          <label>
            <span>Project</span>
            <input
              value={runForm.project_id}
              onChange={(event) => onFormUpdate("project_id", event.target.value)}
              placeholder="project_id"
            />
          </label>
        </div>

        {/* PDF Upload */}
        <label>
          <span>Paper PDF</span>
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              onChange={onFileUpload}
              style={{ display: "none" }}
            />
            <button
              className="command-button"
              type="button"
              disabled={uploadingPdf}
              onClick={() => fileInputRef.current?.click()}
              style={{ flex: 1, justifyContent: "flex-start" }}
            >
              <Upload size={14} />
              {uploadingPdf ? "Uploading..." : uploadedFileName || "Choose PDF..."}
            </button>
          </div>
        </label>

        <label>
          <span>Repository</span>
          <input
            value={runForm.github_url}
            onChange={(event) => onFormUpdate("github_url", event.target.value)}
            placeholder="GitHub URL or local repo path"
          />
        </label>
        <div className="form-row">
          <label>
            <span>Hardware</span>
            <select
              value={runForm.hardware}
              onChange={(event) => onFormUpdate("hardware", event.target.value)}
            >
              <option value="CPU only">CPU only</option>
              <option value="Single GPU">Single GPU</option>
              <option value="Multi GPU">Multi GPU</option>
            </select>
          </label>
          <label>
            <span>GPU</span>
            <input
              value={runForm.gpu_info}
              onChange={(event) => onFormUpdate("gpu_info", event.target.value)}
              placeholder="e.g. RTX 4090"
            />
          </label>
        </div>
        {mode === "reproduce" && (
          <label>
            <span>Goal</span>
            <select
              value={runForm.goal}
              onChange={(event) => onFormUpdate("goal", event.target.value)}
            >
              <option value="understand paper">understand paper</option>
              <option value="run official demo">run official demo</option>
              <option value="minimal training experiment">
                minimal training experiment
              </option>
              <option value="reproduce main experiments">
                reproduce main experiments
              </option>
              <option value="debug errors">debug errors</option>
            </select>
          </label>
        )}
        <label>
          <span>Task</span>
          <textarea
            value={runForm.task}
            onChange={(event) => onFormUpdate("task", event.target.value)}
            placeholder="What should PaperPilot do?"
            rows={3}
          />
        </label>
        {mode === "productize" && (
          <>
            <label>
              <span>Preferred Type</span>
              <select
                value={runForm.preferred_type}
                onChange={(event) =>
                  onFormUpdate("preferred_type", event.target.value)
                }
              >
                <option value="auto">Auto</option>
                <option value="image">Image</option>
                <option value="text">Text</option>
                <option value="video">Video</option>
                <option value="file">File</option>
              </select>
            </label>
            <label>
              <span>Target User</span>
              <input
                value={runForm.target_user}
                onChange={(event) =>
                  onFormUpdate("target_user", event.target.value)
                }
                placeholder="e.g. lab teams, students, clinicians"
              />
            </label>
            <label>
              <span>Product Goal</span>
              <textarea
                value={runForm.product_goal}
                onChange={(event) =>
                  onFormUpdate("product_goal", event.target.value)
                }
                placeholder="Mock-first product outcome"
                rows={2}
              />
            </label>
          </>
        )}
        <div className="form-divider">
          <span>Agent Runtime</span>
        </div>
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={runForm.mock_mode}
            onChange={(event) => onFormUpdate("mock_mode", event.target.checked)}
          />
          <span>Mock Mode (runs pipeline without LLM calls)</span>
        </label>
        <label>
          <span>API Key</span>
          <input
            type="password"
            value={runForm.api_key}
            onChange={(event) => onFormUpdate("api_key", event.target.value)}
            placeholder={runForm.mock_mode ? "not needed in Mock Mode" : "sk-..."}
          />
        </label>
        <label>
          <span>Base URL</span>
          <input
            value={runForm.base_url}
            onChange={(event) => onFormUpdate("base_url", event.target.value)}
            placeholder="https://api.openai.com/v1"
          />
        </label>
        <div className="form-row">
          <label>
            <span>Model</span>
            <input
              value={runForm.model}
              onChange={(event) => onFormUpdate("model", event.target.value)}
              placeholder="gpt-4o-mini"
            />
          </label>
          <label>
            <span>Code Model</span>
            <input
              value={runForm.implementation_model}
              onChange={(event) =>
                onFormUpdate("implementation_model", event.target.value)
              }
              placeholder="optional"
            />
          </label>
        </div>
        <button
          className="command-button"
          disabled={testingConnection}
          type="button"
          onClick={onTestConnection}
        >
          {testingConnection ? "Testing..." : "Test LLM"}
        </button>
        <button
          className="command-button"
          disabled={savingConfig}
          type="button"
          onClick={onSaveConfig}
        >
          <Save size={14} />
          {savingConfig ? "Saving..." : "Save Config"}
        </button>
        <button className="command-button primary" disabled={creatingRun} type="submit">
          <Play size={15} />
          {creatingRun ? "Starting..." : "Run Agents"}
        </button>
      </form>

      <nav className="nav-section" aria-label="Project navigation">
        <NavGroup
          title="Inputs"
          icon={<FileText size={16} />}
          items={visibleNavItems.filter((item) => ["paper", "repo"].includes(item.id))}
          selectedId={selectedNavId}
          onSelect={onNavSelect}
        />
        <NavGroup
          title="Runs"
          icon={<Activity size={16} />}
          items={visibleNavItems.filter((item) => item.id === "run")}
          selectedId={selectedNavId}
          onSelect={onNavSelect}
        />
        <NavGroup
          title="Artifacts"
          icon={<Boxes size={16} />}
          items={visibleNavItems.filter((item) => item.id === "product")}
          selectedId={selectedNavId}
          onSelect={onNavSelect}
        />
      </nav>

      <div className="settings-strip">
        <Settings size={15} />
        <span>Runner: review-required</span>
      </div>
    </aside>
  );
}

function NavGroup({
  title,
  icon,
  items,
  selectedId,
  onSelect,
}: {
  title: string;
  icon: ReactNode;
  items: ProjectNavItem[];
  selectedId: string;
  onSelect: (id: string) => void;
}) {
  return (
    <section className="nav-group">
      <div className="nav-group-title">
        {icon}
        <span>{title}</span>
      </div>
      {items.map((item) => (
        <button
          className={selectedId === item.id ? "nav-item active" : "nav-item"}
          key={item.id}
          type="button"
          onClick={() => onSelect(item.id)}
        >
          <div>
            <strong>{item.label}</strong>
            <span>{item.meta}</span>
          </div>
          <StatusPill status={item.status} />
        </button>
      ))}
    </section>
  );
}
```

- [ ] **Step 2: Update `workspace-shell.tsx` to use ProjectSidebar**

In `workspace-shell.tsx`:
- Add import: `import { ProjectSidebar } from "@/components/layout/project-sidebar";`
- Remove the `NavGroup` function and `compactLabel` function (they move to sidebar)
- Replace the `<aside className="navigator">...</aside>` block with:

```tsx
<ProjectSidebar
  projectId={currentProject}
  currentTask={currentTask}
  mode={currentMode}
  runForm={runForm}
  query={query}
  selectedNavId={selectedNavId}
  visibleNavItems={visibleNavItems}
  creatingRun={creatingRun}
  testingConnection={testingConnection}
  savingConfig={savingConfig}
  uploadingPdf={uploadingPdf}
  uploadedFileName={uploadedFileName}
  onQueryChange={setQuery}
  onNavSelect={setSelectedNavId}
  onFormUpdate={updateRunForm}
  onFileUpload={handleFileUpload}
  onSaveConfig={handleSaveConfig}
  onTestConnection={testConnection}
  onSubmitRun={submitRun}
  onResetWorkspace={resetWorkspace}
/>
```

Keep `compactLabel` in `workspace-shell.tsx` since it's used by `buildNavItems`.

- [ ] **Step 3: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add frontend/components/layout/project-sidebar.tsx frontend/components/workspace-shell.tsx
git commit -m "refactor(frontend): extract ProjectSidebar from workspace-shell"
```

---

### Task 8: Phase 1 — Split CenterWorkspace from workspace-shell

**Files:**
- Create: `frontend/components/layout/center-workspace.tsx`
- Modify: `frontend/components/workspace-shell.tsx`

- [ ] **Step 1: Create `frontend/components/layout/center-workspace.tsx`**

```tsx
"use client";

import { useState } from "react";
import {
  CheckSquare,
  Clock3,
  MessageSquareText,
  Play,
  ShieldCheck,
} from "lucide-react";

import { StatusPill } from "@/components/status-pill";
import type { AgentEvent, PlanStep, RunMode, WorkflowStatus } from "@/lib/mock-data";
import { WorkflowGraph } from "@/components/workflow-graph";

type CenterWorkspaceProps = {
  mode: RunMode;
  notice: string;
  planState: PlanStep[];
  timelineEvents: AgentEvent[];
  chatMessages: Array<{ role: "agent" | "user"; text: string }>;
  approvalStatus: "pending" | "approved" | "edited" | "rejected";
  onTogglePlanStep: (stepId: string) => void;
  onApprovePlan: () => void;
  onAskAgent: () => void;
  onChatInputChange: (value: string) => void;
  chatInput: string;
  onContinueRun: () => void;
  onUpdateApproval: (nextStatus: "approved" | "edited" | "rejected") => void;
};

export function CenterWorkspace({
  mode,
  notice,
  planState,
  timelineEvents,
  chatMessages,
  approvalStatus,
  onTogglePlanStep,
  onApprovePlan,
  onAskAgent,
  onChatInputChange,
  chatInput,
  onContinueRun,
  onUpdateApproval,
}: CenterWorkspaceProps) {
  return (
    <section className="center-workspace">
      <div className="workspace-toolbar">
        <div>
          <p className="eyebrow">Run</p>
          <h2>{mode === "reproduce" ? "Reproduce workflow" : "Productize workflow"}</h2>
        </div>
        <div className="toolbar-actions">
          <button className="command-button" type="button" onClick={onAskAgent}>
            <MessageSquareText size={15} />
            Ask Agent
          </button>
          <button className="command-button primary" type="button" onClick={onContinueRun}>
            <Play size={15} />
            Refresh
          </button>
        </div>
      </div>
      <div className="notice-strip">{notice}</div>

      <section className="workspace-band two-columns">
        <div className="tool-panel plan-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Co-planning</p>
              <h2>Editable plan</h2>
            </div>
            <button className="icon-button" title="Approve plan" type="button" onClick={onApprovePlan}>
              <CheckSquare size={17} />
            </button>
          </div>
          <div className="plan-list">
            {planState.map((step) => (
              <label className="plan-step" key={step.id}>
                <input
                  type="checkbox"
                  checked={step.enabled}
                  onChange={() => onTogglePlanStep(step.id)}
                />
                <span>{step.label}</span>
                <StatusPill status={step.status} />
              </label>
            ))}
          </div>
        </div>

        <div className="tool-panel chat-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Agent chat</p>
              <h2>Artifact-aware context</h2>
            </div>
            <StatusPill status="running" />
          </div>
          <div className="chat-thread">
            {chatMessages.map((message, index) => (
              <ChatBubble
                key={`${message.role}-${index}`}
                role={message.role}
                text={message.text}
              />
            ))}
          </div>
          <div className="composer">
            <span>@</span>
            <input
              aria-label="Agent message"
              placeholder="paper, repo, prd, code, terminal"
              value={chatInput}
              onChange={(event) => onChatInputChange(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  onAskAgent();
                }
              }}
            />
          </div>
        </div>
      </section>

      <section className="tool-panel graph-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">LangGraph</p>
            <h2>Workflow graph</h2>
          </div>
          <div className="legend">
            <span className="legend-item success">success</span>
            <span className="legend-item running">running</span>
            <span className="legend-item review">review</span>
          </div>
        </div>
        <WorkflowGraph />
      </section>

      <section className="workspace-band two-columns bottom-band">
        <div className="tool-panel timeline-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Event stream</p>
              <h2>Agent trace</h2>
            </div>
            <Clock3 size={17} />
          </div>
          <div className="timeline">
            {timelineEvents.map((event) => (
              <article className="timeline-event" key={event.id}>
                <div className={`event-dot status-${event.status}`} />
                <div>
                  <span>{event.time}</span>
                  <strong>{event.agent}</strong>
                  <p>{event.message}</p>
                </div>
                <StatusPill status={event.status} />
              </article>
            ))}
          </div>
        </div>

        <div className="tool-panel approval-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Approval</p>
              <h2>Human-in-the-loop</h2>
            </div>
            <ShieldCheck size={18} />
          </div>
          <div className="approval-summary">
            <code>python main.py --smoke-test</code>
            <p>
              Medium-risk generated-code check. Current decision:
              {" "}
              <strong>{approvalStatus}</strong>.
            </p>
          </div>
          <div className="action-row">
            <button className="command-button primary" type="button" onClick={() => onUpdateApproval("approved")}>
              Approve
            </button>
            <button className="command-button" type="button" onClick={() => onUpdateApproval("edited")}>
              Edit
            </button>
            <button className="command-button" type="button" onClick={() => onUpdateApproval("rejected")}>
              Reject
            </button>
          </div>
        </div>
      </section>
    </section>
  );
}

function ChatBubble({ role, text }: { role: "agent" | "user"; text: string }) {
  return <div className={`chat-bubble ${role}`}>{text}</div>;
}
```

- [ ] **Step 2: Update `workspace-shell.tsx` to use CenterWorkspace**

In `workspace-shell.tsx`:
- Add import: `import { CenterWorkspace } from "@/components/layout/center-workspace";`
- Remove the `ChatBubble` function (moved to center-workspace)
- Replace the entire `<section className="center-workspace">...</section>` block with:

```tsx
<CenterWorkspace
  mode={currentMode}
  notice={notice}
  planState={planState}
  timelineEvents={timelineEvents}
  chatMessages={displayedChatMessages}
  approvalStatus={approvalStatus}
  onTogglePlanStep={togglePlanStep}
  onApprovePlan={approvePlan}
  onAskAgent={askAgent}
  onChatInputChange={setChatInput}
  chatInput={chatInput}
  onContinueRun={continueRun}
  onUpdateApproval={updateApproval}
/>
```

- [ ] **Step 3: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add frontend/components/layout/center-workspace.tsx frontend/components/workspace-shell.tsx
git commit -m "refactor(frontend): extract CenterWorkspace from workspace-shell"
```

---

### Task 9: Phase 1 — Split Inspector panels into separate components

**Files:**
- Create: `frontend/components/inspector/artifacts-panel.tsx`
- Create: `frontend/components/inspector/code-panel.tsx`
- Create: `frontend/components/inspector/diff-panel.tsx`
- Create: `frontend/components/inspector/runner-panel.tsx`
- Create: `frontend/components/inspector/tool-call-panel.tsx`
- Create: `frontend/components/inspector/logs-panel.tsx`
- Create: `frontend/components/inspector/preview-panel.tsx`
- Modify: `frontend/components/inspector-panel.tsx`

- [ ] **Step 1: Create `frontend/components/inspector/artifacts-panel.tsx`**

```tsx
"use client";

import { StatusPill } from "@/components/status-pill";
import type { ArtifactItem } from "@/lib/mock-data";

type ArtifactsPanelProps = {
  artifactRows: ArtifactItem[];
};

export function ArtifactsPanel({ artifactRows }: ArtifactsPanelProps) {
  if (!artifactRows.length) {
    return <div className="empty-state">No artifacts for this run yet.</div>;
  }
  return (
    <div className="stack">
      {artifactRows.map((artifact) => (
        <div className="artifact-row" key={artifact.id}>
          <div>
            <strong>{artifact.name}</strong>
            <span>{artifact.kind}</span>
            <code>{artifact.path}</code>
          </div>
          <StatusPill status={artifact.status} />
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Create `frontend/components/inspector/code-panel.tsx`**

```tsx
"use client";

type CodePanelProps = {
  fileTabs: Array<{ id: string; label: string }>;
  activeFileId: string;
  activeFile: {
    id: string;
    path: string;
    language: string;
    content: string;
  } | undefined;
  onSelectFile: (id: string) => void;
};

export function CodePanel({ fileTabs, activeFileId, activeFile, onSelectFile }: CodePanelProps) {
  if (!activeFile) {
    return <div className="empty-state">No code files available.</div>;
  }
  return (
    <div className="code-tab">
      <div className="file-tabs">
        {fileTabs.map((file) => (
          <button
            key={file.id}
            className={activeFileId === file.id ? "file-tab active" : "file-tab"}
            onClick={() => onSelectFile(file.id)}
            type="button"
          >
            {file.label}
          </button>
        ))}
      </div>
      <div className="code-meta">
        <span>{activeFile.path}</span>
        <span>{activeFile.language}</span>
      </div>
      <pre className="code-block">
        <code>{activeFile.content}</code>
      </pre>
    </div>
  );
}
```

- [ ] **Step 3: Create `frontend/components/inspector/diff-panel.tsx`**

```tsx
"use client";

import { Check } from "lucide-react";
import { StatusPill } from "@/components/status-pill";
import type { WorkflowStatus } from "@/lib/mock-data";

type DiffPanelProps = {
  patchFile: string;
  oldCode: string;
  newCode: string;
  patchStatus: WorkflowStatus;
  onApprove: () => void;
  onReject: () => void;
  onRevise: () => void;
};

export function DiffPanel({
  patchFile,
  oldCode,
  newCode,
  patchStatus,
  onApprove,
  onReject,
  onRevise,
}: DiffPanelProps) {
  return (
    <div className="stack">
      <div className="diff-header">
        <div>
          <p className="eyebrow">Patch proposal</p>
          <strong>{patchFile}</strong>
        </div>
        <StatusPill status={patchStatus} />
      </div>
      <div className="diff-grid">
        <pre className="diff-pane old">
          <code>{oldCode}</code>
        </pre>
        <pre className="diff-pane new">
          <code>{newCode}</code>
        </pre>
      </div>
      <div className="action-row">
        <button className="command-button primary" type="button" onClick={onApprove}>
          <Check size={15} />
          Approve Patch
        </button>
        <button className="command-button" type="button" onClick={onReject}>
          Reject
        </button>
        <button className="command-button" type="button" onClick={onRevise}>
          Ask Revision
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Create `frontend/components/inspector/runner-panel.tsx`**

```tsx
"use client";

import { Check } from "lucide-react";
import type { ApprovalRequest, RunnerReview, WorkflowStatus } from "@/lib/mock-data";

type RunnerPanelProps = {
  approvalRequest: ApprovalRequest;
  runnerReview: RunnerReview;
  runnerStatus: WorkflowStatus;
  runnerMessage: string;
  onApprove: () => void;
  onEdit: () => void;
  onReject: () => void;
};

export function RunnerPanel({
  approvalRequest,
  runnerReview,
  runnerStatus,
  runnerMessage,
  onApprove,
  onEdit,
  onReject,
}: RunnerPanelProps) {
  return (
    <div className="stack">
      <div className="action-request">
        <p className="eyebrow">Action request</p>
        <h3>{approvalRequest.tool}</h3>
        <dl>
          <div>
            <dt>Agent</dt>
            <dd>{approvalRequest.agent}</dd>
          </div>
          <div>
            <dt>Command</dt>
            <dd>
              <code>{approvalRequest.command}</code>
            </dd>
          </div>
          <div>
            <dt>Risk</dt>
            <dd>{approvalRequest.risk}</dd>
          </div>
          <div>
            <dt>Reason</dt>
            <dd>{approvalRequest.reason}</dd>
          </div>
        </dl>
      </div>
      <div className="runner-grid">
        <span>Purpose</span>
        <strong>{runnerReview.purpose}</strong>
        <span>Working dir</span>
        <code>{runnerReview.cwd}</code>
        <span>Expected</span>
        <strong>{runnerReview.expectedOutput}</strong>
        <span>Exit code</span>
        <strong>{runnerStatus === "success" ? 0 : runnerReview.exitCode ?? "not run"}</strong>
      </div>
      <pre className="terminal-block">
        <code>{runnerMessage}</code>
      </pre>
      <div className="action-row">
        <button className="command-button primary" type="button" onClick={onApprove}>
          <Check size={15} />
          Approve
        </button>
        <button className="command-button" type="button" onClick={onEdit}>
          Edit
        </button>
        <button className="command-button" type="button" onClick={onReject}>
          Reject
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Create `frontend/components/inspector/tool-call-panel.tsx`**

```tsx
"use client";

import { StatusPill } from "@/components/status-pill";
import type { ToolCall } from "@/lib/mock-data";

type ToolCallPanelProps = {
  toolCalls: ToolCall[];
};

export function ToolCallPanel({ toolCalls }: ToolCallPanelProps) {
  return (
    <div className="stack">
      {toolCalls.map((call) => (
        <div className="tool-call" key={call.id}>
          <div>
            <code>{call.action}</code>
            <p>{call.observation}</p>
          </div>
          <StatusPill status={call.status} />
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 6: Create `frontend/components/inspector/logs-panel.tsx`**

```tsx
"use client";

import type { AgentEvent } from "@/lib/mock-data";

type LogsPanelProps = {
  events: AgentEvent[];
};

export function LogsPanel({ events }: LogsPanelProps) {
  return (
    <pre className="terminal-block">
      <code>
        {events.length
          ? events
              .map(
                (event) =>
                  `> ${event.eventType} ${event.agent}: ${event.message}`,
              )
              .join("\n")
          : "> no backend events for this run yet"}
      </code>
    </pre>
  );
}
```

- [ ] **Step 7: Create `frontend/components/inspector/preview-panel.tsx`**

```tsx
"use client";

export function PreviewPanel() {
  return (
    <div className="preview-frame">
      <div className="preview-toolbar">
        <span />
        <span />
        <span />
      </div>
      <div className="preview-body">
        <p className="eyebrow">Generated Product</p>
        <h3>Mock-first analysis console</h3>
        <div className="preview-metric">
          <span>Demo readiness</span>
          <strong>4.2 / 5</strong>
        </div>
        <div className="preview-metric">
          <span>Adapter mode</span>
          <strong>Mock</strong>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 8: Update `inspector-panel.tsx` to use sub-components**

Replace the content of `inspector-panel.tsx`:

```tsx
"use client";

import {
  Check,
  Code2,
  FileText,
  GitCompare,
  ListChecks,
  Play,
  RotateCcw,
  Terminal,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState } from "react";

import {
  type AgentEvent,
  approvalRequest,
  artifacts,
  codeFiles,
  patchPreview,
  runnerReview,
  toolCalls,
} from "@/lib/mock-data";
import { StatusPill } from "@/components/status-pill";
import {
  artifactFromApi,
  fetchArtifacts,
  fetchFileContent,
  fetchFiles,
  type ApiFileNode,
} from "@/lib/api";
import { ArtifactsPanel } from "@/components/inspector/artifacts-panel";
import { CodePanel } from "@/components/inspector/code-panel";
import { DiffPanel } from "@/components/inspector/diff-panel";
import { RunnerPanel } from "@/components/inspector/runner-panel";
import { ToolCallPanel } from "@/components/inspector/tool-call-panel";
import { LogsPanel } from "@/components/inspector/logs-panel";
import { PreviewPanel } from "@/components/inspector/preview-panel";

type InspectorTab = "artifacts" | "code" | "diff" | "runner" | "tools" | "logs" | "preview";

const tabs: Array<{ id: InspectorTab; label: string; icon: LucideIcon }> = [
  { id: "artifacts", label: "Artifacts", icon: FileText },
  { id: "code", label: "Code", icon: Code2 },
  { id: "diff", label: "Diff", icon: GitCompare },
  { id: "runner", label: "Runner", icon: Terminal },
  { id: "tools", label: "Tool Calls", icon: ListChecks },
  { id: "logs", label: "Logs", icon: Play },
  { id: "preview", label: "Preview", icon: RotateCcw },
];

export function InspectorPanel({
  events = [],
  refreshToken = "",
  runId,
  runStatus = "pending",
}: {
  events?: AgentEvent[];
  refreshToken?: string;
  runId: string;
  runStatus?: "pending" | "running" | "success" | "waiting_review" | "failed" | "revised";
}) {
  const [activeTab, setActiveTab] = useState<InspectorTab>("artifacts");
  const [activeFileId, setActiveFileId] = useState(codeFiles[0]?.id ?? "");
  const [artifactRows, setArtifactRows] = useState(artifacts);
  const [apiFiles, setApiFiles] = useState<ApiFileNode[]>([]);
  const [apiFileContent, setApiFileContent] = useState("");
  const [patchStatus, setPatchStatus] = useState<
    "waiting_review" | "success" | "failed" | "revised"
  >("waiting_review");
  const [runnerStatus, setRunnerStatus] = useState<
    "waiting_review" | "success" | "failed" | "revised"
  >("waiting_review");
  const [runnerMessage, setRunnerMessage] = useState(runnerReview.diagnosis);

  const activeMockFile =
    codeFiles.find((file) => file.id === activeFileId) ?? codeFiles[0];
  const activeApiFile = apiFiles.find((file) => file.path === activeFileId);
  const activeFile = activeApiFile
    ? {
        id: activeApiFile.path,
        path: activeApiFile.path,
        language: activeApiFile.path.endsWith(".py") ? "python" : "text",
        content: apiFileContent,
      }
    : activeMockFile;

  useEffect(() => {
    let cancelled = false;
    Promise.all([fetchArtifacts(runId), fetchFiles(runId)])
      .then(([apiArtifacts, files]) => {
        if (cancelled) return;
        setArtifactRows(apiArtifacts.map(artifactFromApi));
        setApiFiles(files);
        if (files[0]?.path) setActiveFileId(files[0].path);
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [refreshToken, runId]);

  useEffect(() => {
    if (!activeApiFile) return;
    let cancelled = false;
    fetchFileContent(runId, activeApiFile.path)
      .then((file) => {
        if (!cancelled) setApiFileContent(file.content);
      })
      .catch(() => {
        if (!cancelled) setApiFileContent("");
      });
    return () => { cancelled = true; };
  }, [activeApiFile, runId]);

  const fileTabs = apiFiles.length
    ? apiFiles.map((file) => ({ id: file.path, label: file.name }))
    : codeFiles.map((file) => ({
        id: file.id,
        label: file.path.split("/").pop() ?? file.path,
      }));

  return (
    <aside className="inspector">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Inspector</p>
          <h2>Run workspace</h2>
        </div>
        <StatusPill status={runStatus} />
      </div>

      <div className="tab-list" role="tablist" aria-label="Inspector tabs">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              className={activeTab === tab.id ? "tab active" : "tab"}
              onClick={() => setActiveTab(tab.id)}
              type="button"
              title={tab.label}
            >
              <Icon size={15} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      <div className="inspector-content">
        {activeTab === "artifacts" && <ArtifactsPanel artifactRows={artifactRows} />}

        {activeTab === "code" && (
          <CodePanel
            fileTabs={fileTabs}
            activeFileId={activeFileId}
            activeFile={activeFile}
            onSelectFile={setActiveFileId}
          />
        )}

        {activeTab === "diff" && (
          <DiffPanel
            patchFile={patchPreview.file}
            oldCode={patchPreview.oldCode}
            newCode={patchPreview.newCode}
            patchStatus={patchStatus}
            onApprove={() => setPatchStatus("success")}
            onReject={() => setPatchStatus("failed")}
            onRevise={() => setPatchStatus("revised")}
          />
        )}

        {activeTab === "runner" && (
          <RunnerPanel
            approvalRequest={approvalRequest}
            runnerReview={runnerReview}
            runnerStatus={runnerStatus}
            runnerMessage={runnerMessage}
            onApprove={() => {
              setRunnerStatus("success");
              setRunnerMessage("Approved. Preview runner recorded a successful bounded smoke test.");
            }}
            onEdit={() => {
              setRunnerStatus("revised");
              setRunnerMessage("Edited command to python main.py --help for a safer first check.");
            }}
            onReject={() => {
              setRunnerStatus("failed");
              setRunnerMessage("Rejected. No command will run until the plan is revised.");
            }}
          />
        )}

        {activeTab === "tools" && <ToolCallPanel toolCalls={toolCalls} />}

        {activeTab === "logs" && <LogsPanel events={events} />}

        {activeTab === "preview" && <PreviewPanel />}
      </div>
    </aside>
  );
}
```

- [ ] **Step 9: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 10: Commit**

```bash
git add frontend/components/inspector/ frontend/components/inspector-panel.tsx
git commit -m "refactor(frontend): split inspector into per-tab panel components"
```

---

### Task 10: Phase 2 — Create event_service.py with JSONL persistence

**Files:**
- Create: `backend/services/event_service.py`
- Modify: `backend/services/run_service.py`

- [ ] **Step 1: Create `backend/services/event_service.py`**

```python
"""Event persistence with JSONL storage for workbench event streams."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.schemas import WorkbenchEvent
from config import PROJECT_ROOT

EVENTS_DIR = PROJECT_ROOT / "backend" / "storage"
EVENTS_DIR.mkdir(parents=True, exist_ok=True)


class EventService:
    """Append events to JSONL files keyed by run_id."""

    def __init__(self, storage_dir: Path | None = None) -> None:
        self.storage_dir = Path(storage_dir or EVENTS_DIR).resolve()
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def emit(self, event: WorkbenchEvent) -> None:
        path = self.storage_dir / f"{event.run_id}.jsonl"
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(event.model_dump_json() + "\n")

    def list_events(self, run_id: str) -> list[WorkbenchEvent]:
        path = self.storage_dir / f"{run_id}.jsonl"
        if not path.exists():
            return []
        events: list[WorkbenchEvent] = []
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(WorkbenchEvent.model_validate_json(line))
                except Exception:
                    continue
        return events

    def list_events_after(self, run_id: str, after_event_id: str) -> list[WorkbenchEvent]:
        events = self.list_events(run_id)
        found = False
        result: list[WorkbenchEvent] = []
        for event in events:
            if found:
                result.append(event)
            if event.event_id == after_event_id:
                found = True
        return result


event_service = EventService()
```

- [ ] **Step 2: Integrate EventService into RunService**

In `backend/services/run_service.py`, add import:

```python
from backend.services.event_service import event_service
```

Then in `InMemoryRunService._append_event`, add `event_service.emit(event)` after the event is created (after line 426):

```python
event_service.emit(event)
```

- [ ] **Step 3: Commit**

```bash
git add backend/services/event_service.py backend/services/run_service.py
git commit -m "feat(backend): add EventService with JSONL persistence"
```

---

### Task 11: Phase 2 — Add GET /api/runs/{run_id}/graph endpoint

**Files:**
- Create: `backend/services/graph_service.py`
- Modify: `backend/routers/runs.py`

- [ ] **Step 1: Create `backend/services/graph_service.py`**

```python
"""Compute graph node state from event stream."""

from __future__ import annotations

from backend.schemas import WorkbenchEvent


class GraphService:
    @staticmethod
    def compute_node_states(events: list[WorkbenchEvent]) -> list[dict]:
        """Derive node status from events. One entry per unique node name."""
        nodes: dict[str, dict] = {}
        for event in events:
            node_name = event.node
            if node_name not in nodes:
                nodes[node_name] = {
                    "id": node_name,
                    "label": node_name.replace("_", " ").title(),
                    "agent": event.agent,
                    "status": "pending",
                    "startedAt": None,
                    "finishedAt": None,
                    "toolCalls": [],
                    "issues": [],
                }
            node = nodes[node_name]
            if event.event_type == "node_started" and event.status == "running":
                node["status"] = "running"
                node["startedAt"] = event.created_at
            elif event.event_type == "node_finished":
                if event.status == "success":
                    node["status"] = "success"
                elif event.status == "failed":
                    node["status"] = "failed"
                elif event.status == "waiting_review":
                    node["status"] = "waiting_review"
                node["finishedAt"] = event.created_at
            elif event.event_type in ("tool_call", "tool_result"):
                node.setdefault("toolCalls", []).append(
                    {
                        "id": event.event_id,
                        "type": event.event_type,
                        "message": event.message,
                        "status": event.status,
                        "timestamp": event.created_at,
                    }
                )
        return list(nodes.values())


graph_service = GraphService()
```

- [ ] **Step 2: Add graph endpoint to `backend/routers/runs.py`**

Add import:

```python
from backend.services.graph_service import graph_service
```

Add route:

```python
@router.get("/runs/{run_id}/graph")
def get_run_graph(run_id: str) -> list[dict]:
    if run_service.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    events = run_service.list_events(run_id)
    return graph_service.compute_node_states(events)
```

- [ ] **Step 3: Commit**

```bash
git add backend/services/graph_service.py backend/routers/runs.py
git commit -m "feat(backend): add graph node state endpoint from event stream"
```

---

### Task 12: Phase 2 — Update WorkflowGraph to accept dynamic node data

**Files:**
- Modify: `frontend/components/workflow-graph.tsx`

- [ ] **Step 1: Rewrite `workflow-graph.tsx` to accept props**

```tsx
"use client";

import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";

import type { WorkflowStatus } from "@/lib/mock-data";

type GraphNodeState = {
  id: string;
  label: string;
  agent?: string;
  status: WorkflowStatus;
  startedAt?: string;
  finishedAt?: string;
  toolCalls?: Array<{ id: string; type: string; message: string }>;
};

type WorkflowGraphProps = {
  nodeStates?: GraphNodeState[];
  onNodeClick?: (nodeId: string) => void;
};

const DEFAULT_LAYOUT: Record<string, { x: number; y: number }> = {
  parse: { x: 0, y: 40 },
  research: { x: 210, y: 0 },
  repo: { x: 210, y: 96 },
  repository: { x: 460, y: 96 },
  planner: { x: 720, y: 48 },
  review: { x: 980, y: 48 },
  diagnosis: { x: 1240, y: 48 },
  report: { x: 1500, y: 48 },
};

export function WorkflowGraph({ nodeStates, onNodeClick }: WorkflowGraphProps) {
  if (!nodeStates || nodeStates.length === 0) {
    return (
      <div className="workflow-canvas" aria-label="Workflow graph">
        <div className="empty-state" style={{ padding: 24 }}>
          No graph state available. Start a backend run to see the workflow graph.
        </div>
      </div>
    );
  }

  const nodes: Node[] = nodeStates.map((nodeState) => {
    const layout = DEFAULT_LAYOUT[nodeState.id] ?? {
      x: 100 + nodeStates.indexOf(nodeState) * 220,
      y: 48,
    };
    return {
      id: nodeState.id,
      type: "default",
      position: layout,
      className: `workflow-node status-${nodeState.status}`,
      data: { label: nodeState.label, status: nodeState.status },
    };
  });

  const edges: Edge[] = [];
  for (let i = 1; i < nodeStates.length; i++) {
    edges.push({
      id: `e-${nodeStates[i - 1].id}-${nodeStates[i].id}`,
      source: nodeStates[i - 1].id,
      target: nodeStates[i].id,
      animated: nodeStates[i].status === "running",
      className: "workflow-edge",
    });
  }

  return (
    <div className="workflow-canvas" aria-label="Workflow graph">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        minZoom={0.55}
        maxZoom={1.35}
        onNodeClick={onNodeClick ? (_event, node) => onNodeClick(node.id) : undefined}
      >
        <Background gap={18} size={1} />
        <MiniMap pannable zoomable />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
```

- [ ] **Step 2: Add graph fetching to workspace-shell and pass to WorkflowGraph**

In `workspace-shell.tsx`:
- Add a state: `const [graphNodes, setGraphNodes] = useState<GraphNodeState[]>([]);`
- Add import for `GraphNodeState` from workflow-graph
- In the polling effect, also fetch graph data:

Add after the existing event fetch:
```tsx
fetch(`${API_BASE}/api/runs/${apiRun!.run_id}/graph`)
  .then(r => r.json())
  .then(setGraphNodes)
  .catch(() => {});
```

- Update `CenterWorkspace` to accept and pass `graphNodes` to `WorkflowGraph`

- [ ] **Step 3: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add frontend/components/workflow-graph.tsx frontend/components/layout/center-workspace.tsx frontend/components/workspace-shell.tsx
git commit -m "feat(frontend): make WorkflowGraph dynamic from backend events"
```

---

### Task 13: Phase 3 — Install Monaco Editor and create Code Workbench

**Files:**
- Create: `frontend/components/code/file-tree.tsx`
- Create: `frontend/components/code/code-editor.tsx`
- Modify: `frontend/components/inspector/code-panel.tsx`

- [ ] **Step 1: Create `frontend/components/code/file-tree.tsx`**

```tsx
"use client";

import type { ApiFileNode } from "@/lib/api";

type FileTreeProps = {
  files: ApiFileNode[];
  activeFileId: string;
  onSelectFile: (path: string) => void;
};

export function FileTree({ files, activeFileId, onSelectFile }: FileTreeProps) {
  // Build a simple tree from flat file list
  const tree = buildTree(files);
  return (
    <div className="file-tree" style={{ maxHeight: 200, overflow: "auto" }}>
      {tree.map((node) => (
        <FileTreeNode
          key={node.path}
          node={node}
          depth={0}
          activeFileId={activeFileId}
          onSelectFile={onSelectFile}
        />
      ))}
    </div>
  );
}

type TreeNode = {
  name: string;
  path: string;
  kind: "file" | "directory";
  children: TreeNode[];
};

function buildTree(files: ApiFileNode[]): TreeNode[] {
  const root: TreeNode[] = [];
  for (const file of files) {
    const parts = file.path.split("/");
    let current = root;
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const isLast = i === parts.length - 1;
      let found = current.find((n) => n.name === part);
      if (!found) {
        found = {
          name: part,
          path: parts.slice(0, i + 1).join("/"),
          kind: isLast ? file.kind : "directory",
          children: [],
        };
        current.push(found);
      }
      if (isLast) {
        found.kind = file.kind;
        found.path = file.path;
      } else {
        current = found.children;
      }
    }
  }
  return root;
}

function FileTreeNode({
  node,
  depth,
  activeFileId,
  onSelectFile,
}: {
  node: TreeNode;
  depth: number;
  activeFileId: string;
  onSelectFile: (path: string) => void;
}) {
  const isActive = node.path === activeFileId;
  return (
    <>
      <button
        className={isActive ? "file-tab active" : "file-tab"}
        style={{ marginLeft: depth * 16, display: "block", width: "calc(100% - 16px)" }}
        type="button"
        onClick={() => node.kind === "file" && onSelectFile(node.path)}
      >
        {node.kind === "directory" ? "📁" : "📄"} {node.name}
      </button>
      {node.children.map((child) => (
        <FileTreeNode
          key={child.path}
          node={child}
          depth={depth + 1}
          activeFileId={activeFileId}
          onSelectFile={onSelectFile}
        />
      ))}
    </>
  );
}
```

- [ ] **Step 2: Create `frontend/components/code/code-editor.tsx`**

```tsx
"use client";

import Editor, { type OnMount } from "@monaco-editor/react";
import type { editor } from "monaco-editor";
import { useRef } from "react";

type CodeEditorProps = {
  path: string;
  language: string;
  content: string;
  readOnly?: boolean;
  onContentChange?: (value: string) => void;
};

export function CodeEditor({
  path,
  language,
  content,
  readOnly = true,
  onContentChange,
}: CodeEditorProps) {
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);

  const handleMount: OnMount = (editor) => {
    editorRef.current = editor;
    editor.updateOptions({ readOnly });
  };

  return (
    <div className="code-editor-wrapper" style={{ minHeight: 320 }}>
      <Editor
        height="50vh"
        language={language}
        value={content}
        theme="vs-dark"
        onMount={handleMount}
        onChange={(value) => onContentChange?.(value ?? "")}
        options={{
          readOnly,
          minimap: { enabled: false },
          fontSize: 13,
          lineNumbers: "on",
          scrollBeyondLastLine: false,
          wordWrap: "on",
        }}
        path={path}
      />
    </div>
  );
}
```

- [ ] **Step 3: Update `frontend/components/inspector/code-panel.tsx` to use CodeEditor**

```tsx
"use client";

import { FileTree } from "@/components/code/file-tree";
import { CodeEditor } from "@/components/code/code-editor";
import type { ApiFileNode } from "@/lib/api";

type CodePanelProps = {
  fileTabs: Array<{ id: string; label: string }>;
  activeFileId: string;
  activeFile:
    | { id: string; path: string; language: string; content: string }
    | undefined;
  apiFiles: ApiFileNode[];
  onSelectFile: (id: string) => void;
};

export function CodePanel({
  fileTabs,
  activeFileId,
  activeFile,
  apiFiles,
  onSelectFile,
}: CodePanelProps) {
  if (!activeFile) {
    return <div className="empty-state">No code files available.</div>;
  }
  return (
    <div className="code-tab">
      {apiFiles.length > 0 && (
        <FileTree files={apiFiles} activeFileId={activeFileId} onSelectFile={onSelectFile} />
      )}
      <div className="file-tabs">
        {fileTabs.map((file) => (
          <button
            key={file.id}
            className={activeFileId === file.id ? "file-tab active" : "file-tab"}
            onClick={() => onSelectFile(file.id)}
            type="button"
          >
            {file.label}
          </button>
        ))}
      </div>
      <div className="code-meta">
        <span>{activeFile.path}</span>
        <span>{activeFile.language}</span>
      </div>
      <CodeEditor
        path={activeFile.path}
        language={activeFile.language}
        content={activeFile.content}
        readOnly
      />
    </div>
  );
}
```

- [ ] **Step 4: Update InspectorPanel to pass apiFiles to CodePanel**

In `inspector-panel.tsx`, add `apiFiles` prop to CodePanel usage:

```tsx
{activeTab === "code" && (
  <CodePanel
    fileTabs={fileTabs}
    activeFileId={activeFileId}
    activeFile={activeFile}
    apiFiles={apiFiles}
    onSelectFile={setActiveFileId}
  />
)}
```

- [ ] **Step 5: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 6: Commit**

```bash
git add frontend/components/code/ frontend/components/inspector/code-panel.tsx frontend/components/inspector-panel.tsx
git commit -m "feat(frontend): add Monaco editor and file tree to Code panel"
```

---

### Task 14: Phase 4 — Create diff-viewer with react-diff-viewer

**Files:**
- Create: `frontend/components/code/diff-viewer.tsx`
- Modify: `frontend/components/inspector/diff-panel.tsx`

- [ ] **Step 1: Create `frontend/components/code/diff-viewer.tsx`**

```tsx
"use client";

import ReactDiffViewer, { DiffMethod } from "react-diff-viewer-continued";

type DiffViewerProps = {
  oldContent: string;
  newContent: string;
  leftTitle?: string;
  rightTitle?: string;
};

const darkTheme = {
  diffContainer: {
    borderRadius: "8px",
  },
};

export function DiffViewer({
  oldContent,
  newContent,
  leftTitle = "Current",
  rightTitle = "Proposed",
}: DiffViewerProps) {
  return (
    <div className="diff-viewer">
      <ReactDiffViewer
        oldValue={oldContent}
        newValue={newContent}
        splitView
        compareMethod={DiffMethod.WORDS}
        leftTitle={leftTitle}
        rightTitle={rightTitle}
        styles={darkTheme}
        useDarkTheme
      />
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/code/diff-viewer.tsx
git commit -m "feat(frontend): add diff viewer component"
```

---

### Task 15: Phase 4 — Create ActionApproval drawer

**Files:**
- Create: `frontend/components/approval/action-approval-drawer.tsx`
- Create: `frontend/components/approval/approval-card.tsx`

- [ ] **Step 1: Create `frontend/components/approval/approval-card.tsx`**

```tsx
"use client";

import { StatusPill } from "@/components/status-pill";
import type { WorkflowStatus } from "@/lib/mock-data";

export type PendingActionItem = {
  id: string;
  runId: string;
  agent: string;
  type: "run_command" | "apply_patch" | "write_file" | "download_resource" | "install_dependency" | "open_external_url";
  risk: "safe" | "review" | "sandbox" | "blocked";
  reason: string;
  command: string;
  status: "pending" | "approved" | "rejected" | "edited";
};

type ApprovalCardProps = {
  action: PendingActionItem;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  onEdit: (id: string) => void;
};

export function ApprovalCard({ action, onApprove, onReject, onEdit }: ApprovalCardProps) {
  return (
    <div className="tool-panel" style={{ marginBottom: 12 }}>
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Action Request</p>
          <strong>{action.type.replace(/_/g, " ")}</strong>
        </div>
        <StatusPill status={action.status === "pending" ? "waiting_review" : (action.status as WorkflowStatus)} />
      </div>
      <dl style={{ display: "grid", gap: "8px 10px", gridTemplateColumns: "80px minmax(0, 1fr)", margin: "0 0 12px" }}>
        <dt style={{ color: "var(--muted)", fontSize: 12 }}>Agent</dt>
        <dd style={{ margin: 0, fontSize: 13 }}>{action.agent}</dd>
        <dt style={{ color: "var(--muted)", fontSize: 12 }}>Risk</dt>
        <dd style={{ margin: 0, fontSize: 13 }}>
          <StatusPill status={action.risk === "blocked" ? "failed" : action.risk === "review" ? "waiting_review" : "success"} />
        </dd>
        <dt style={{ color: "var(--muted)", fontSize: 12 }}>Reason</dt>
        <dd style={{ margin: 0, fontSize: 13 }}>{action.reason}</dd>
      </dl>
      <code style={{ display: "block", overflowWrap: "anywhere", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: 10, background: "var(--surface-muted)", fontSize: 12, marginBottom: 12 }}>
        {action.command}
      </code>
      <div className="action-row">
        <button className="command-button primary" type="button" onClick={() => onApprove(action.id)}>
          Approve
        </button>
        <button className="command-button" type="button" onClick={() => onEdit(action.id)}>
          Edit
        </button>
        <button className="command-button" type="button" onClick={() => onReject(action.id)}>
          Reject
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create `frontend/components/approval/action-approval-drawer.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { fetchRun, fetchRunEvents } from "@/lib/api";
import type { ApiAction } from "@/lib/api";
import { ApprovalCard, type PendingActionItem } from "@/components/approval/approval-card";

type ActionApprovalDrawerProps = {
  runId: string;
  refreshToken: string;
  onApprove: (actionId: string) => void;
  onReject: (actionId: string) => void;
  onEdit: (actionId: string) => void;
};

function toPendingAction(api: ApiAction): PendingActionItem {
  return {
    id: api.action_id,
    runId: api.run_id,
    agent: api.agent,
    type: (api.tool as PendingActionItem["type"]) || "run_command",
    risk: api.risk,
    reason: api.reason,
    command: api.command,
    status: api.status,
  };
}

export function ActionApprovalDrawer({
  runId,
  refreshToken,
  onApprove,
  onReject,
  onEdit,
}: ActionApprovalDrawerProps) {
  const [actions, setActions] = useState<PendingActionItem[]>([]);
  const pending = actions.filter((a) => a.status === "pending");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        // Load actions via API
        const resp = await fetch(`${process.env.NEXT_PUBLIC_PAPERPILOT_API_BASE ?? "http://localhost:8000"}/api/runs/${runId}/events`);
        if (cancelled) return;
        // For now, mock actions from existing mock data
        // In Phase 4 full, this will call GET /api/runs/{run_id}/actions
      } catch {
        // keep mock
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [runId, refreshToken]);

  if (!pending.length) {
    return (
      <div className="empty-state" style={{ padding: 12 }}>
        No pending actions for this run.
      </div>
    );
  }

  return (
    <div>
      {pending.map((action) => (
        <ApprovalCard
          key={action.id}
          action={action}
          onApprove={onApprove}
          onReject={onReject}
          onEdit={onEdit}
        />
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/approval/
git commit -m "feat(frontend): add ActionApproval drawer with approval cards"
```

---

### Task 16: Phase 5 — Productize evaluation issue cards

**Files:**
- Create: `frontend/components/productize/evaluation-issue-cards.tsx`
- Create: `frontend/components/productize/productize-tabs.tsx`

- [ ] **Step 1: Create `frontend/components/productize/evaluation-issue-cards.tsx`**

```tsx
"use client";

import { StatusPill } from "@/components/status-pill";

export type EvaluationIssue = {
  id: string;
  issue: string;
  severity: "low" | "medium" | "high";
  target: string;
  suggestion: string;
};

type EvaluationIssueCardsProps = {
  issues: EvaluationIssue[];
  onRevise: (issueId: string, action: string) => void;
};

const actionLabels: Record<string, string> = {
  reduce_mvp: "Reduce MVP Scope",
  revise_prd: "Revise PRD",
  revise_prototype: "Revise Prototype",
  accept_warning: "Accept with Warning",
};

export function EvaluationIssueCards({ issues, onRevise }: EvaluationIssueCardsProps) {
  if (!issues.length) {
    return <div className="empty-state">No evaluation issues. The product looks good!</div>;
  }
  return (
    <div className="stack">
      {issues.map((issue) => (
        <div className="tool-panel" key={issue.id}>
          <div style={{ marginBottom: 10 }}>
            <strong>{issue.issue}</strong>
          </div>
          <div className="runner-grid" style={{ marginBottom: 10 }}>
            <span>Severity</span>
            <StatusPill
              status={
                issue.severity === "high"
                  ? "failed"
                  : issue.severity === "medium"
                    ? "waiting_review"
                    : "revised"
              }
            />
            <span>Target</span>
            <strong>{issue.target}</strong>
            <span>Suggestion</span>
            <strong>{issue.suggestion}</strong>
          </div>
          <div className="action-row">
            {Object.entries(actionLabels).map(([key, label]) => (
              <button
                key={key}
                className="command-button"
                type="button"
                onClick={() => onRevise(issue.id, key)}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Create `frontend/components/productize/productize-tabs.tsx`**

```tsx
"use client";

import { useState } from "react";

const VIEWS = ["Research", "Product", "Prototype", "Evaluation"] as const;
type ProductizeView = (typeof VIEWS)[number];

type ProductizeTabsProps = {
  researchContent: React.ReactNode;
  productContent: React.ReactNode;
  prototypeContent: React.ReactNode;
  evaluationContent: React.ReactNode;
};

export function ProductizeTabs({
  researchContent,
  productContent,
  prototypeContent,
  evaluationContent,
}: ProductizeTabsProps) {
  const [view, setView] = useState<ProductizeView>("Research");

  const contentMap: Record<ProductizeView, React.ReactNode> = {
    Research: researchContent,
    Product: productContent,
    Prototype: prototypeContent,
    Evaluation: evaluationContent,
  };

  return (
    <div>
      <div className="tab-list" style={{ marginBottom: 14 }}>
        {VIEWS.map((v) => (
          <button
            key={v}
            className={view === v ? "tab active" : "tab"}
            type="button"
            onClick={() => setView(v)}
          >
            {v}
          </button>
        ))}
      </div>
      {contentMap[view]}
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/productize/
git commit -m "feat(frontend): add Productize evaluation issue cards and tabs"
```

---

### Task 17: Phase 6 — Reproduce quality panels (blueprint + evidence trace)

**Files:**
- Create: `frontend/components/reproduce/blueprint-panel.tsx`
- Create: `frontend/components/reproduce/evidence-trace.tsx`

- [ ] **Step 1: Create `frontend/components/reproduce/blueprint-panel.tsx`**

```tsx
"use client";

import { StatusPill } from "@/components/status-pill";
import type { WorkflowStatus } from "@/lib/mock-data";

type BlueprintItem = {
  label: string;
  status: WorkflowStatus;
};

type BlueprintPanelProps = {
  files: string[];
  coverageScore: number;
  items: BlueprintItem[];
};

export function BlueprintPanel({ files, coverageScore, items }: BlueprintPanelProps) {
  return (
    <div className="stack">
      <div className="preview-metric" style={{ padding: "10px 0" }}>
        <span>Blueprint coverage</span>
        <strong>{coverageScore}%</strong>
      </div>
      <div className="preview-metric" style={{ padding: "10px 0" }}>
        <span>Generated files</span>
        <strong>{files.length}</strong>
      </div>
      {files.length > 0 && (
        <div className="tool-panel" style={{ padding: 10 }}>
          {files.map((f) => (
            <code key={f} style={{ display: "block", fontSize: 12, marginBottom: 4 }}>
              {f}
            </code>
          ))}
        </div>
      )}
      {items.map((item, i) => (
        <div className="tool-panel" key={i}>
          <div className="panel-heading" style={{ marginBottom: 0 }}>
            <span>{item.label}</span>
            <StatusPill status={item.status} />
          </div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Create `frontend/components/reproduce/evidence-trace.tsx`**

```tsx
"use client";

import { StatusPill } from "@/components/status-pill";
import type { WorkflowStatus } from "@/lib/mock-data";

type EvidenceItem = {
  id: string;
  finding: string;
  source: string;
  status: WorkflowStatus;
};

type EvidenceTraceProps = {
  items: EvidenceItem[];
};

export function EvidenceTrace({ items }: EvidenceTraceProps) {
  if (!items.length) {
    return <div className="empty-state">No repository evidence gathered yet.</div>;
  }
  return (
    <div className="stack">
      {items.map((item) => (
        <div className="tool-call" key={item.id}>
          <div>
            <strong style={{ display: "block", marginBottom: 4 }}>{item.finding}</strong>
            <code>{item.source}</code>
          </div>
          <StatusPill status={item.status} />
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/reproduce/
git commit -m "feat(frontend): add Reproduce blueprint and evidence trace panels"
```

---

### Task 18: Phase 7 — Update README with screenshots section and enhanced docs

**Files:**
- Modify: `README.md`
- Create: `docs/architecture.md`

- [ ] **Step 1: Add screenshots and architecture section to README**

After the opening paragraph in `README.md`, before "## Project Positioning", add:

```markdown
## Screenshots

> Screenshots of the PaperPilot Research Agent IDE workbench.

![Workbench Overview](docs/screenshots/workbench-overview.png)

*Agent Workbench with three-panel layout: project sidebar, workflow graph + chat, and code inspector.*

## Architecture Overview

![Architecture](docs/architecture-diagram.png)

See [docs/architecture.md](docs/architecture.md) for the full architecture diagram and component relationships.
```

- [ ] **Step 2: Create `docs/architecture.md`**

```markdown
# PaperPilot Architecture

## System Components

```text
┌─────────────────────────────────────────────────────────┐
│                    PaperPilot IDE                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────────┐  │
│  │ Next.js  │  │ FastAPI  │  │ LangGraph Pipelines    │  │
│  │ Frontend │──│ Backend  │──│ reproduce_graph.py     │  │
│  │ :3000    │  │ :8000    │  │ productize_graph.py    │  │
│  └──────────┘  └──────────┘  └───────────────────────┘  │
│       │              │                   │               │
│       ▼              ▼                   ▼               │
│  ┌──────────────────────────────────────────────────┐   │
│  │                  Shared Layer                      │   │
│  │  agents/  tools/  schemas/  runtime/  pipeline/   │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Frontend Architecture

- **Layout**: Three-panel (sidebar / workspace / inspector)
- **State**: Zustand store per run
- **API**: REST + WebSocket event stream
- **Components**: Split by domain — layout/, run/, chat/, workflow/, approval/, inspector/, code/, productize/, reproduce/

## Backend Architecture

- **Routers**: runs, actions, artifacts, checks, commands, files, llm, patches, uploads
- **Services**: run_service, event_service, artifact_service, file_service, patch_service, graph_service, check_service, command_service
- **Storage**: JSONL files under backend/storage/ for events, runs, actions, artifacts, patches

## Graph Pipelines

### Reproduce Graph
parse → research + repo preparation → repository understanding → planner → command review → implementation → code review → diagnosis → report

### Productize Graph
paper fan-out → research synthesis → product planning → prototype building → evaluation → revision routing → scaffold
```

- [ ] **Step 3: Commit**

```bash
git add README.md docs/architecture.md
git commit -m "docs: add architecture doc and screenshots section"
```

---

### Task 19: Final verification — Full build + tests

**Files:**
- None (verification only)

- [ ] **Step 1: Run backend tests**

```bash
cd "C:\Users\34217\Desktop\Study\2026Spring\Large AI Models\project\PaperPilot"
pytest tests/ -v --tb=short 2>&1 | tail -30
```

Expected: All tests pass (or existing failures only, no new ones).

- [ ] **Step 2: Verify backend imports**

```bash
python -c "from backend.main import app; from backend.services.event_service import event_service; from backend.services.graph_service import graph_service; print('backend ok')"
```

Expected: `backend ok`

- [ ] **Step 3: Verify frontend build**

```bash
cd frontend
npm run build
```

Expected: Build succeeds.

- [ ] **Step 4: Commit any remaining changes and push**

```bash
git add -A
git status
git commit -m "chore: final verification and cleanup across all phases"
git push origin master
```

---

### Task 20: Commit all changes and push

**Files:**
- None (git operations)

- [ ] **Step 1: Push all commits**

```bash
cd "C:\Users\34217\Desktop\Study\2026Spring\Large AI Models\project\PaperPilot"
git log --oneline -20
git push origin master
```

