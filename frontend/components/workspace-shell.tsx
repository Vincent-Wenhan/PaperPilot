"use client";

import {
  Activity,
  Boxes,
  CheckSquare,
  Clock3,
  FileText,
  Layers,
  MessageSquareText,
  Play,
  Plus,
  Save,
  Search,
  Settings,
  ShieldCheck,
  Upload,
} from "lucide-react";
import type { ChangeEvent, FormEvent, ReactNode } from "react";
import { useEffect, useRef, useState } from "react";

import { InspectorPanel } from "@/components/inspector-panel";
import { StatusPill } from "@/components/status-pill";
import { WorkflowGraph } from "@/components/workflow-graph";
import { TopBar } from "@/components/layout/top-bar";
import {
  approveAction,
  createRun,
  editAction,
  eventFromApi,
  fetchLlmConfig,
  fetchRun,
  fetchRunEvents,
  rejectAction,
  saveLlmConfig,
  testLlmConnection,
  uploadPdf,
  type ApiRun,
  type ApiLlmConfig,
} from "@/lib/api";
import {
  planSteps,
  type AgentEvent,
  type PlanStep,
  type ProjectNavItem,
  type RunMode,
  type WorkflowStatus,
} from "@/lib/mock-data";

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

const defaultRunForm: RunFormState = {
  project_id: "paperpilot_workspace",
  mode: "reproduce",
  task: "",
  pdf_path: "",
  github_url: "",
  hardware: "CPU only",
  gpu_info: "",
  goal: "minimal training experiment",
  target_user: "",
  product_goal: "",
  preferred_type: "auto",
  api_key: "",
  base_url: "https://api.openai.com/v1",
  model: "gpt-4o-mini",
  implementation_model: "",
  mock_mode: false,
};

export function WorkspaceShell() {
  const [apiRun, setApiRun] = useState<ApiRun | null>(null);
  const [timelineEvents, setTimelineEvents] = useState<AgentEvent[]>([]);
  const [runForm, setRunForm] = useState<RunFormState>(defaultRunForm);
  const [creatingRun, setCreatingRun] = useState(false);
  const [testingConnection, setTestingConnection] = useState(false);
  const [savingConfig, setSavingConfig] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedNavId, setSelectedNavId] = useState("run");
  const [planState, setPlanState] = useState(planSteps);
  const [chatMessages, setChatMessages] = useState<
    Array<{ role: "agent" | "user"; text: string }>
  >([]);
  const [chatInput, setChatInput] = useState("");
  const [approvalStatus, setApprovalStatus] = useState<
    "pending" | "approved" | "edited" | "rejected"
  >("pending");
  const [notice, setNotice] = useState(
    "Upload a PDF and configure agent settings, then create a backend run.",
  );
  const [uploadedFileName, setUploadedFileName] = useState("");
  const [uploadingPdf, setUploadingPdf] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const currentProject = apiRun?.project_id ?? runForm.project_id;
  const currentMode = apiRun?.mode ?? runForm.mode;
  const currentTask =
    apiRun?.task || runForm.task || "New PaperPilot research run";
  const paperInput = apiRun?.inputs?.pdf_path ?? runForm.pdf_path;
  const repoInput = apiRun?.inputs?.github_url ?? runForm.github_url;
  const productGoal = apiRun?.inputs?.product_goal ?? runForm.product_goal;
  const targetUser = apiRun?.inputs?.target_user ?? runForm.target_user;
  const currentModel = apiRun?.inputs?.llm_model ?? runForm.model;
  const projectNavItems = buildNavItems({
    run: apiRun,
    form: runForm,
    paperInput,
    repoInput,
    productGoal,
    targetUser,
  });
  const visibleNavItems = projectNavItems.filter((item) => {
    const haystack = `${item.label} ${item.meta}`.toLowerCase();
    return haystack.includes(query.toLowerCase());
  });
  const displayedChatMessages = buildChatMessages(timelineEvents, chatMessages);

  // Load persisted LLM config on mount
  useEffect(() => {
    fetchLlmConfig()
      .then((config) => {
        setRunForm((current) => ({
          ...current,
          api_key: config.api_key || current.api_key,
          base_url: config.base_url || current.base_url,
          model: config.model || current.model,
          implementation_model: config.implementation_model || current.implementation_model,
        }));
      })
      .catch(() => {
        // Backend not available yet — keep defaults
      });
  }, []);

  useEffect(() => {
    if (!apiRun || apiRun.status !== "running") {
      return;
    }
    let cancelled = false;
    async function refreshRun() {
      try {
        const [nextRun, nextEvents] = await Promise.all([
          fetchRun(apiRun!.run_id),
          fetchRunEvents(apiRun!.run_id),
        ]);
        if (cancelled) {
          return;
        }
        setApiRun(nextRun);
        setTimelineEvents(nextEvents.map(eventFromApi));
        setPlanState(planForRunStatus(nextRun));
        if (nextRun.status !== "running") {
          setNotice(nextRun.summary);
        }
      } catch (error) {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : "poll failed";
          setNotice(`Could not refresh run status: ${message}`);
        }
      }
    }
    const timer = window.setInterval(refreshRun, 1800);
    void refreshRun();
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [apiRun?.run_id, apiRun?.status]);

  function addTimelineEvent(message: string, status: WorkflowStatus = "running") {
    setTimelineEvents((events) => [
      {
        id: `local-${Date.now()}`,
        time: new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }),
        agent: "Workbench",
        eventType: "ui_action",
        message,
        status,
      },
      ...events,
    ]);
  }

  function updateRunForm<K extends keyof RunFormState>(
    key: K,
    value: RunFormState[K],
  ) {
    setRunForm((current) => ({ ...current, [key]: value }));
  }

  function resetWorkspace() {
    setApiRun(null);
    setRunForm((current) => ({ ...current, pdf_path: "" }));
    setPlanState(planSteps);
    setTimelineEvents([]);
    setSelectedNavId("paper");
    setApprovalStatus("pending");
    setUploadedFileName("");
    setNotice("New workspace ready. Upload a PDF and create a backend run.");
  }

  async function handleFileUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setNotice("Only PDF files are supported.");
      return;
    }
    setUploadingPdf(true);
    setNotice(`Uploading ${file.name}...`);
    try {
      const result = await uploadPdf(file);
      updateRunForm("pdf_path", result.pdf_path);
      setUploadedFileName(file.name);
      setNotice(`Uploaded: ${file.name}`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Upload failed";
      setNotice(`PDF upload failed: ${message}`);
    } finally {
      setUploadingPdf(false);
    }
  }

  async function handleSaveConfig() {
    setSavingConfig(true);
    setNotice("Saving LLM configuration...");
    try {
      await saveLlmConfig({
        api_key: runForm.api_key,
        base_url: runForm.base_url,
        model: runForm.model,
        implementation_model: runForm.implementation_model,
      });
      setNotice("LLM configuration saved.");
      addTimelineEvent("LLM configuration saved.", "success");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Save failed";
      setNotice(`Could not save LLM config: ${message}`);
    } finally {
      setSavingConfig(false);
    }
  }

  async function submitRun(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!runForm.pdf_path.trim()) {
      setNotice("Upload a PDF file first. The backend agent pipeline needs a readable PDF.");
      return;
    }
    setCreatingRun(true);
    setNotice("Starting PaperPilot agents through FastAPI...");
    try {
      const run = await createRun({
        ...runForm,
        project_id: runForm.project_id.trim() || "paperpilot_workspace",
        task:
          runForm.task.trim() ||
          (runForm.mode === "reproduce"
            ? "Reproduce the submitted paper and repository."
            : "Productize the submitted research into a mock-first MVP."),
        run_pipeline: true,
      });
      const runEvents = await fetchRunEvents(run.run_id).catch(() => []);
      setApiRun(run);
      setPlanState(planForRunStatus(run));
      setTimelineEvents(
        runEvents.length ? runEvents.map(eventFromApi) : eventsFromRun(run),
      );
      setSelectedNavId("run");
      setApprovalStatus("pending");
      setNotice(`Started backend run ${run.run_id}. Agent progress will update here.`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown API error";
      setNotice(`Could not create backend run: ${message}`);
      addTimelineEvent(`Run creation failed: ${message}`, "failed");
    } finally {
      setCreatingRun(false);
    }
  }

  async function testConnection() {
    setTestingConnection(true);
    setNotice("Testing LLM connection through FastAPI...");
    try {
      const result = await testLlmConnection({
        api_key: runForm.api_key,
        base_url: runForm.base_url,
        model: runForm.model,
        mock_mode: runForm.mock_mode,
      });
      setNotice(
        result.ok
          ? `LLM connection ok: ${result.message}`
          : `LLM connection failed: ${result.message}`,
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown API error";
      setNotice(`Could not test LLM connection: ${message}`);
    } finally {
      setTestingConnection(false);
    }
  }

  function continueRun() {
    if (!apiRun) {
      setNotice("Create a backend run before refreshing agent state.");
      return;
    }
    void refreshCurrentRun(apiRun.run_id);
  }

  function approvePlan() {
    setNotice(
      apiRun
        ? "Plan review acknowledged. Backend agent execution continues from server events."
        : "Plan review acknowledged locally.",
    );
    addTimelineEvent("Editable plan review acknowledged.", "success");
  }

  function togglePlanStep(stepId: string) {
    setPlanState((steps) =>
      steps.map((step) =>
        step.id === stepId ? { ...step, enabled: !step.enabled } : step,
      ),
    );
    setNotice("Plan step toggled.");
  }

  function askAgent() {
    const text =
      chatInput.trim() || "@terminal explain why the run is waiting for approval";
    setChatMessages((messages) => [
      ...messages,
      { role: "user", text },
      {
        role: "agent",
        text: apiRun
          ? "I am showing backend run events for this workspace. Use Event Stream and Logs for live agent progress."
          : "Create a backend run first so the chat can reference real PaperPilot events.",
      },
    ]);
    setChatInput("");
    setNotice("Agent response added to the chat panel.");
  }

  async function updateApproval(nextStatus: "approved" | "edited" | "rejected") {
    try {
      if (nextStatus === "approved") {
        await approveAction("act_smoke_test");
      } else if (nextStatus === "edited") {
        await editAction("act_smoke_test", "python main.py --help");
      } else {
        await rejectAction("act_smoke_test");
      }
    } catch {
      // Keep local preview responsive even when the API server is offline.
    }
    setApprovalStatus(nextStatus);
    setNotice(`Action ${nextStatus} recorded for this workbench session.`);
    addTimelineEvent(`Action ${nextStatus}: python main.py --smoke-test`, "success");
  }

  async function refreshCurrentRun(runId: string) {
    setNotice("Refreshing backend run state...");
    try {
      const [nextRun, nextEvents] = await Promise.all([
        fetchRun(runId),
        fetchRunEvents(runId),
      ]);
      setApiRun(nextRun);
      setTimelineEvents(nextEvents.map(eventFromApi));
      setPlanState(planForRunStatus(nextRun));
      setNotice(nextRun.summary);
    } catch (error) {
      const message = error instanceof Error ? error.message : "refresh failed";
      setNotice(`Could not refresh backend run state: ${message}`);
    }
  }

  return (
    <main className="workbench-shell">
      <TopBar
        project={currentProject}
        mode={currentMode}
        model={currentModel}
        summary={apiRun?.summary ?? ""}
        runStatus={apiRun?.status ?? "pending"}
      />

      <section className="workspace-grid">
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
              onClick={resetWorkspace}
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
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>

          <form className="run-form" onSubmit={submitRun}>
            <div className="form-row">
              <label>
                <span>Mode</span>
                <select
                  value={runForm.mode}
                  onChange={(event) =>
                    updateRunForm("mode", event.target.value as RunMode)
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
                  onChange={(event) => updateRunForm("project_id", event.target.value)}
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
                  onChange={handleFileUpload}
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
                onChange={(event) => updateRunForm("github_url", event.target.value)}
                placeholder="GitHub URL or local repo path"
              />
            </label>
            <div className="form-row">
              <label>
                <span>Hardware</span>
                <select
                  value={runForm.hardware}
                  onChange={(event) => updateRunForm("hardware", event.target.value)}
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
                  onChange={(event) => updateRunForm("gpu_info", event.target.value)}
                  placeholder="e.g. RTX 4090"
                />
              </label>
            </div>
            {runForm.mode === "reproduce" && (
              <label>
                <span>Goal</span>
                <select
                  value={runForm.goal}
                  onChange={(event) => updateRunForm("goal", event.target.value)}
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
                onChange={(event) => updateRunForm("task", event.target.value)}
                placeholder="What should PaperPilot do?"
                rows={3}
              />
            </label>
            {runForm.mode === "productize" && (
              <>
                <label>
                  <span>Preferred Type</span>
                  <select
                    value={runForm.preferred_type}
                    onChange={(event) =>
                      updateRunForm("preferred_type", event.target.value)
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
                      updateRunForm("target_user", event.target.value)
                    }
                    placeholder="e.g. lab teams, students, clinicians"
                  />
                </label>
                <label>
                  <span>Product Goal</span>
                  <textarea
                    value={runForm.product_goal}
                    onChange={(event) =>
                      updateRunForm("product_goal", event.target.value)
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
                onChange={(event) => updateRunForm("mock_mode", event.target.checked)}
              />
              <span>Mock Mode (runs pipeline without LLM calls)</span>
            </label>
            <label>
              <span>API Key</span>
              <input
                type="password"
                value={runForm.api_key}
                onChange={(event) => updateRunForm("api_key", event.target.value)}
                placeholder={runForm.mock_mode ? "not needed in Mock Mode" : "sk-..."}
              />
            </label>
            <label>
              <span>Base URL</span>
              <input
                value={runForm.base_url}
                onChange={(event) => updateRunForm("base_url", event.target.value)}
                placeholder="https://api.openai.com/v1"
              />
            </label>
            <div className="form-row">
              <label>
                <span>Model</span>
                <input
                  value={runForm.model}
                  onChange={(event) => updateRunForm("model", event.target.value)}
                  placeholder="gpt-4o-mini"
                />
              </label>
              <label>
                <span>Code Model</span>
                <input
                  value={runForm.implementation_model}
                  onChange={(event) =>
                    updateRunForm("implementation_model", event.target.value)
                  }
                  placeholder="optional"
                />
              </label>
            </div>
            <button
              className="command-button"
              disabled={testingConnection}
              type="button"
              onClick={testConnection}
            >
              {testingConnection ? "Testing..." : "Test LLM"}
            </button>
            <button
              className="command-button"
              disabled={savingConfig}
              type="button"
              onClick={handleSaveConfig}
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
              onSelect={setSelectedNavId}
            />
            <NavGroup
              title="Runs"
              icon={<Activity size={16} />}
              items={visibleNavItems.filter((item) => item.id === "run")}
              selectedId={selectedNavId}
              onSelect={setSelectedNavId}
            />
            <NavGroup
              title="Artifacts"
              icon={<Boxes size={16} />}
              items={visibleNavItems.filter((item) => item.id === "product")}
              selectedId={selectedNavId}
              onSelect={setSelectedNavId}
            />
          </nav>

          <div className="settings-strip">
            <Settings size={15} />
            <span>Runner: review-required</span>
          </div>
        </aside>

        <section className="center-workspace">
          <div className="workspace-toolbar">
            <div>
              <p className="eyebrow">Run</p>
              <h2>{currentMode === "reproduce" ? "Reproduce workflow" : "Productize workflow"}</h2>
            </div>
            <div className="toolbar-actions">
              <button className="command-button" type="button" onClick={askAgent}>
                <MessageSquareText size={15} />
                Ask Agent
              </button>
              <button className="command-button primary" type="button" onClick={continueRun}>
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
                <button className="icon-button" title="Approve plan" type="button" onClick={approvePlan}>
                  <CheckSquare size={17} />
                </button>
              </div>
              <div className="plan-list">
                {planState.map((step) => (
                  <label className="plan-step" key={step.id}>
                    <input
                      type="checkbox"
                      checked={step.enabled}
                      onChange={() => togglePlanStep(step.id)}
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
                {displayedChatMessages.map((message, index) => (
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
                  onChange={(event) => setChatInput(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      askAgent();
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
                <button className="command-button primary" type="button" onClick={() => updateApproval("approved")}>
                  Approve
                </button>
                <button className="command-button" type="button" onClick={() => updateApproval("edited")}>
                  Edit
                </button>
                <button className="command-button" type="button" onClick={() => updateApproval("rejected")}>
                  Reject
                </button>
              </div>
            </div>
          </section>
        </section>

        <InspectorPanel
          events={timelineEvents}
          refreshToken={apiRun?.updated_at ?? ""}
          runId={apiRun?.run_id ?? "run_mock_reproduce"}
          runStatus={apiRun?.status ?? "pending"}
        />
      </section>
    </main>
  );
}

function buildNavItems({
  run,
  form,
  paperInput,
  repoInput,
  productGoal,
  targetUser,
}: {
  run: ApiRun | null;
  form: RunFormState;
  paperInput: string;
  repoInput: string;
  productGoal: string;
  targetUser: string;
}): ProjectNavItem[] {
  const hasPaper = Boolean(paperInput.trim());
  const hasRepo = Boolean(repoInput.trim());
  const productMeta = [targetUser, productGoal].filter(Boolean).join(" / ");
  return [
    {
      id: "paper",
      label: hasPaper ? compactLabel(paperInput) : "No paper selected",
      meta: hasPaper ? "paper input ready" : "upload a PDF",
      status: hasPaper ? "success" : "pending",
    },
    {
      id: "repo",
      label: hasRepo ? compactLabel(repoInput) : "No repository selected",
      meta: hasRepo ? "repository input ready" : "add GitHub URL or local repo path",
      status: hasRepo ? "success" : "pending",
    },
    {
      id: "run",
      label: run?.run_id ?? "No backend run yet",
      meta: run ? `${run.mode} workflow` : `${form.mode} draft`,
      status: run?.status ?? "pending",
    },
    {
      id: "product",
      label: productGoal ? compactLabel(productGoal) : "Product goal",
      meta: productMeta || "optional for productize mode",
      status: productGoal ? "revised" : "pending",
    },
  ];
}

function compactLabel(value: string) {
  const trimmed = value.trim();
  if (trimmed.length <= 36) {
    return trimmed;
  }
  return `${trimmed.slice(0, 33)}...`;
}

function planFromRun(run: ApiRun): PlanStep[] {
  return run.plan.map((label, index) => ({
    id: `${run.run_id}-plan-${index}`,
    label,
    enabled: true,
    status:
      index === 0
        ? ("running" as const)
        : label.toLowerCase().includes("review")
          ? ("waiting_review" as const)
          : ("pending" as const),
  }));
}

function planForRunStatus(run: ApiRun): PlanStep[] {
  if (run.status === "success") {
    return run.plan.map((label, index) => ({
      id: `${run.run_id}-plan-${index}`,
      label,
      enabled: true,
      status: "success" as const,
    }));
  }
  if (run.status === "failed") {
    return run.plan.map((label, index) => ({
      id: `${run.run_id}-plan-${index}`,
      label,
      enabled: true,
      status: "failed" as const,
    }));
  }
  return planFromRun(run);
}

function buildChatMessages(
  events: AgentEvent[],
  manualMessages: Array<{ role: "agent" | "user"; text: string }>,
) {
  const eventMessages = events.slice(-5).map((event) => ({
    role: "agent" as const,
    text: `${event.agent}: ${event.message}`,
  }));
  if (!eventMessages.length && !manualMessages.length) {
    return [
      {
        role: "agent" as const,
        text: "Start a backend run to see artifact-aware agent context here.",
      },
    ];
  }
  return [...eventMessages, ...manualMessages];
}

function eventsFromRun(run: ApiRun) {
  const timestamp = new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
  const paper = run.inputs?.pdf_path || "paper input";
  const repo = run.inputs?.github_url || "repository input";
  return [
    {
      id: `${run.run_id}-created`,
      time: timestamp,
      agent: "Workbench",
      eventType: "run_created",
      message: `Created ${run.mode} run from current inputs.`,
      status: "success" as const,
    },
    {
      id: `${run.run_id}-inputs`,
      time: timestamp,
      agent: "Input Router",
      eventType: "input_received",
      message: `Paper: ${paper}; repository: ${repo}.`,
      status: "running" as const,
    },
    {
      id: `${run.run_id}-plan`,
      time: timestamp,
      agent: "Planning Agent",
      eventType: "plan_generated",
      message: `Editable plan generated for: ${run.task}`,
      status: "waiting_review" as const,
    },
  ];
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

function ChatBubble({ role, text }: { role: "agent" | "user"; text: string }) {
  return <div className={`chat-bubble ${role}`}>{text}</div>;
}
