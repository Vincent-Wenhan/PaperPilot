"use client";

import type { ChangeEvent, FormEvent } from "react";
import { useEffect, useRef, useState } from "react";

import { InspectorPanel } from "@/components/inspector-panel";
import { TopBar, type TopBarRunState } from "@/components/layout/top-bar";
import { ProjectSidebar } from "@/components/layout/project-sidebar";
import type { RunFormState } from "@/components/layout/project-sidebar";
import { CenterWorkspace } from "@/components/layout/center-workspace";
import { BottomDock } from "@/components/layout/bottom-dock";
import {
  ActionApprovalDrawer,
  type PendingAction,
} from "@/components/approval/action-approval-drawer";
import { RunIntakeDrawer } from "@/components/run/run-intake-drawer";
import type { WorkbenchTabId } from "@/components/workbench/workbench-tabs";
import {
  issuesFromRunResult,
  type EvaluationIssue,
} from "@/components/productize/evaluation-issues";
import {
  approveAction,
  createRun,
  editAction,
  eventFromApi,
  fetchLlmConfig,
  fetchRun,
  fetchRunActions,
  fetchRunEvents,
  fetchRunGraph,
  fetchRunResult,
  rejectAction,
  saveLlmConfig,
  testLlmConnection,
  uploadPdf,
  type ApiAction,
  type ApiEvent,
  type ApiGraphNode,
  type ApiRun,
  type ApiRunResult,
} from "@/lib/api";
import {
  agentEvents,
  planSteps,
  type AgentEvent,
  type PlanStep,
  type ProjectNavItem,
  type RunMode,
  type WorkflowStatus,
} from "@/lib/mock-data";

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

const ACTIVE_RUN_STORAGE_KEY = "paperpilot.activeRunId";

export function WorkspaceShell() {
  const [apiRun, setApiRun] = useState<ApiRun | null>(null);
  const [timelineEvents, setTimelineEvents] = useState<AgentEvent[]>(agentEvents);
  const [graphNodes, setGraphNodes] = useState<ApiGraphNode[]>([]);
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
  const [apiActions, setApiActions] = useState<ApiAction[]>([]);
  const [notice, setNotice] = useState(
    "Upload a PDF and configure agent settings, then create a backend run.",
  );
  const [uploadedFileName, setUploadedFileName] = useState("");
  const [uploadingPdf, setUploadingPdf] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [newRunDrawerOpen, setNewRunDrawerOpen] = useState(false);
  const [approvalOpen, setApprovalOpen] = useState(true);
  const [activeWorkbenchTab, setActiveWorkbenchTab] = useState<WorkbenchTabId>("workflow");
  const [runResult, setRunResult] = useState<ApiRunResult | null>(null);
  const [evaluationIssues, setEvaluationIssues] = useState<EvaluationIssue[]>([]);

  const activeRunId = apiRun?.run_id;
  const activeRunStatus = apiRun?.status;
  const activeRunMode = apiRun?.mode;
  const currentProject = apiRun?.project_id ?? runForm.project_id;
  const currentMode = apiRun?.mode ?? runForm.mode;
  const currentTask =
    apiRun?.task || runForm.task || "New PaperPilot research run";
  const paperInput = apiRun?.inputs?.pdf_path ?? runForm.pdf_path;
  const repoInput = apiRun?.inputs?.github_url ?? runForm.github_url;
  const productGoal = apiRun?.inputs?.product_goal ?? runForm.product_goal;
  const targetUser = apiRun?.inputs?.target_user ?? runForm.target_user;
  const currentModel = apiRun?.inputs?.llm_model ?? runForm.model;

  const topBarRun: TopBarRunState = {
    projectName: currentProject,
    runId: apiRun?.run_id,
    mode: currentMode,
    status: apiRun?.status ?? "pending",
    elapsed: computeElapsed(apiRun?.created_at),
    model: currentModel,
  };

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
  const pendingApprovalActions: PendingAction[] = apiActions
    .filter((action) => action.status === "pending")
    .map((action) => ({
      id: action.action_id,
      runId: action.run_id,
      agent: action.agent,
      type: action.tool === "apply_patch" ? "apply_patch" : "run_command",
      risk: action.risk === "low" ? "safe" : "review",
      reason: action.reason,
      payload: { command: action.command },
      status: action.status,
    }));
  const displayedApprovalActions: PendingAction[] = pendingApprovalActions.length
    ? pendingApprovalActions
    : !apiRun
      ? [{
          id: "preview-approval",
          runId: "preview-run",
          agent: "Prototype Builder",
          type: "apply_patch",
          risk: "review",
          reason: "Implement prototype scaffold and API endpoints.",
          payload: { command: "git apply prototype.patch" },
          status: "pending",
        }]
      : [];
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

  // Restore active run from localStorage
  useEffect(() => {
    const storedRunId = window.localStorage.getItem(ACTIVE_RUN_STORAGE_KEY);
    if (!storedRunId) {
      return;
    }
    let cancelled = false;
    async function restoreRun() {
      try {
        const [restoredRun, restoredEvents, restoredGraph] = await Promise.all([
          fetchRun(storedRunId!),
          fetchRunEvents(storedRunId!),
          fetchRunGraph(storedRunId!).catch(() => []),
        ]);
        if (cancelled) {
          return;
        }
        setApiRun(restoredRun);
        setTimelineEvents(restoredEvents.map(eventFromApi));
        setGraphNodes(enrichGraphFromEvents(restoredGraph, restoredEvents, restoredRun.mode));
        setPlanState(planForRunStatus(restoredRun));
        setNotice(restoredRun.summary);
        fetchRunActions(storedRunId!)
          .then((actions) => { if (!cancelled) setApiActions(actions); })
          .catch(() => {});
      } catch {
        window.localStorage.removeItem(ACTIVE_RUN_STORAGE_KEY);
      }
    }
    void restoreRun();
    return () => {
      cancelled = true;
    };
  }, []);

  // Poll running runs
  useEffect(() => {
    if (!activeRunId || activeRunStatus !== "running") {
      return;
    }
    const runId = activeRunId;
    let cancelled = false;
    async function refreshRun() {
      try {
        const [nextRun, nextEvents, nextGraph] = await Promise.all([
          fetchRun(runId),
          fetchRunEvents(runId),
          fetchRunGraph(runId).catch(() => []),
        ]);
        if (cancelled) {
          return;
        }
        setApiRun(nextRun);
        setTimelineEvents(nextEvents.map(eventFromApi));
        setGraphNodes(enrichGraphFromEvents(nextGraph, nextEvents, nextRun.mode));
        setPlanState(planForRunStatus(nextRun));
        if (nextRun.status !== "running") {
          setNotice(nextRun.summary);
        }
        fetchRunActions(runId)
          .then((actions) => { if (!cancelled) setApiActions(actions); })
          .catch(() => {});
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
  }, [activeRunId, activeRunStatus]);

  // Fetch run result when productize run completes
  useEffect(() => {
    if (!activeRunId || activeRunMode !== "productize") return;
    if (activeRunStatus !== "success" && activeRunStatus !== "waiting_review" && activeRunStatus !== "failed") return;
    fetchRunResult(activeRunId)
      .then((result) => {
        setRunResult(result);
        setEvaluationIssues(issuesFromRunResult(result));
      })
      .catch(() => {});
  }, [activeRunId, activeRunMode, activeRunStatus]);

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

  function handleModeChange(mode: "reproduce" | "productize") {
    updateRunForm("mode", mode);
  }

  function resetWorkspace() {
    setApiRun(null);
    window.localStorage.removeItem(ACTIVE_RUN_STORAGE_KEY);
    setRunForm((current) => ({ ...current, pdf_path: "" }));
    setPlanState(planSteps);
    setGraphNodes([]);
    setTimelineEvents([]);
    setSelectedNavId("paper");
    setUploadedFileName("");
    setNotice("New workspace ready. Upload a PDF and create a backend run.");
    setRunResult(null);
    setEvaluationIssues([]);
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
      const [runEvents, runGraph, runActions] = await Promise.all([
        fetchRunEvents(run.run_id).catch(() => []),
        fetchRunGraph(run.run_id).catch(() => []),
        fetchRunActions(run.run_id).catch(() => []),
      ]);
      setApiRun(run);
      window.localStorage.setItem(ACTIVE_RUN_STORAGE_KEY, run.run_id);
      setPlanState(planForRunStatus(run));
      setGraphNodes(enrichGraphFromEvents(runGraph, runEvents, run.mode));
      setTimelineEvents(
        runEvents.length ? runEvents.map(eventFromApi) : eventsFromRun(run),
      );
      setApiActions(runActions ?? []);
      setSelectedNavId("run");
      setNotice(`Started backend run ${run.run_id}. Agent progress will update here.`);
      setNewRunDrawerOpen(false);
      setActiveWorkbenchTab("workflow");
      setRunResult(null);
      setEvaluationIssues([]);
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
    const pendingActions = apiActions.filter((a) => a.status === "pending");
    const target = pendingActions[0];
    if (!target) {
      setNotice("No pending actions to approve, edit, or reject.");
      return;
    }
    try {
      if (nextStatus === "approved") {
        await approveAction(target.action_id);
        setApiActions((prev) =>
          prev.map((a) =>
            a.action_id === target.action_id ? { ...a, status: "approved" } : a,
          ),
        );
      } else if (nextStatus === "edited") {
        await editAction(target.action_id, target.command);
        setApiActions((prev) =>
          prev.map((a) =>
            a.action_id === target.action_id ? { ...a, status: "edited" } : a,
          ),
        );
      } else {
        await rejectAction(target.action_id);
        setApiActions((prev) =>
          prev.map((a) =>
            a.action_id === target.action_id ? { ...a, status: "rejected" } : a,
          ),
        );
      }
      setNotice(`Action ${nextStatus}: ${target.command}`);
      addTimelineEvent(`Action ${nextStatus}: ${target.command}`, "success");
    } catch (error) {
      const message = error instanceof Error ? error.message : "action failed";
      setNotice(`Action ${nextStatus} failed: ${message}`);
      addTimelineEvent(`Action ${nextStatus} failed: ${message}`, "failed");
    }
  }

  async function refreshCurrentRun(runId: string) {
    setNotice("Refreshing backend run state...");
    try {
      const [nextRun, nextEvents, nextGraph] = await Promise.all([
        fetchRun(runId),
        fetchRunEvents(runId),
        fetchRunGraph(runId).catch(() => []),
      ]);
      setApiRun(nextRun);
      window.localStorage.setItem(ACTIVE_RUN_STORAGE_KEY, nextRun.run_id);
      setTimelineEvents(nextEvents.map(eventFromApi));
      setGraphNodes(enrichGraphFromEvents(nextGraph, nextEvents, nextRun.mode));
      setPlanState(planForRunStatus(nextRun));
      setNotice(nextRun.summary);
      fetchRunActions(runId)
        .then(setApiActions)
        .catch(() => {});
    } catch (error) {
      const message = error instanceof Error ? error.message : "refresh failed";
      setNotice(`Could not refresh backend run state: ${message}`);
    }
  }

  function handleReduceScope(issueId: string) {
    setEvaluationIssues((prev) =>
      prev.map((issue) =>
        issue.id === issueId ? { ...issue, status: "accepted" as const } : issue,
      ),
    );
    setNotice(`Evaluation issue ${issueId}: scope reduction accepted.`);
  }

  function handleRevisePrd(issueId: string) {
    setEvaluationIssues((prev) =>
      prev.map((issue) =>
        issue.id === issueId ? { ...issue, status: "revised" as const } : issue,
      ),
    );
    setNotice(`Evaluation issue ${issueId}: PRD revision requested.`);
  }

  function handleRevisePrototype(issueId: string) {
    setEvaluationIssues((prev) =>
      prev.map((issue) =>
        issue.id === issueId ? { ...issue, status: "revised" as const } : issue,
      ),
    );
    setNotice(`Evaluation issue ${issueId}: prototype revision requested.`);
  }

  function handleAcceptWarning(issueId: string) {
    setEvaluationIssues((prev) =>
      prev.map((issue) =>
        issue.id === issueId ? { ...issue, status: "accepted" as const } : issue,
      ),
    );
    setNotice(`Evaluation issue ${issueId}: warning accepted.`);
  }

  return (
    <main className="workbench-shell">
      <TopBar
        run={topBarRun}
        onNewRun={() => setNewRunDrawerOpen(true)}
        onModeChange={handleModeChange}
      />

      <section className="workspace-grid">
        <ProjectSidebar
          currentTask={currentTask}
          query={query}
          selectedNavId={selectedNavId}
          visibleNavItems={visibleNavItems}
          onQueryChange={setQuery}
          onNavSelect={setSelectedNavId}
          onNewRun={() => setNewRunDrawerOpen(true)}
        />

        <CenterWorkspace
          mode={currentMode}
          notice={notice}
          planState={planState}
          timelineEvents={timelineEvents}
          chatMessages={displayedChatMessages}
          runStatus={apiRun?.status ?? "pending"}
          graphNodes={graphNodes}
          activeTab={activeWorkbenchTab}
          onTabChange={setActiveWorkbenchTab}
          onTogglePlanStep={togglePlanStep}
          onApprovePlan={approvePlan}
          onAskAgent={askAgent}
          onChatInputChange={setChatInput}
          chatInput={chatInput}
          onContinueRun={continueRun}
          evaluationIssues={evaluationIssues}
          onReduceScope={handleReduceScope}
          onRevisePrd={handleRevisePrd}
          onRevisePrototype={handleRevisePrototype}
          onAcceptWarning={handleAcceptWarning}
        />

        <InspectorPanel
          events={timelineEvents}
          refreshToken={apiRun?.updated_at ?? ""}
          runId={apiRun?.run_id ?? "run_mock_reproduce"}
          runStatus={apiRun?.status ?? "pending"}
        />
      </section>

      <BottomDock
        events={timelineEvents}
        resultSummary={runResult as Record<string, unknown> | null}
        runId={apiRun?.run_id}
      />

      <ActionApprovalDrawer
        open={approvalOpen && displayedApprovalActions.length > 0}
        actions={displayedApprovalActions}
        onClose={() => setApprovalOpen(false)}
        onApprove={() => {
          void updateApproval("approved");
          setApprovalOpen(false);
        }}
        onEdit={() => {
          void updateApproval("edited");
          setApprovalOpen(false);
        }}
        onReject={() => {
          void updateApproval("rejected");
          setApprovalOpen(false);
        }}
      />

      <RunIntakeDrawer
        open={newRunDrawerOpen}
        runForm={runForm}
        creatingRun={creatingRun}
        testingConnection={testingConnection}
        savingConfig={savingConfig}
        uploadingPdf={uploadingPdf}
        uploadedFileName={uploadedFileName}
        onClose={() => setNewRunDrawerOpen(false)}
        onFormUpdate={updateRunForm}
        onFileUpload={handleFileUpload}
        onSaveConfig={handleSaveConfig}
        onTestConnection={testConnection}
        onSubmitRun={submitRun}
      />
    </main>
  );
}

function computeElapsed(createdAt?: string): string {
  if (!createdAt) return "00:00:00";
  const start = new Date(createdAt).getTime();
  const diff = Math.max(0, Date.now() - start);
  const h = Math.floor(diff / 3600000);
  const m = Math.floor((diff % 3600000) / 60000);
  const s = Math.floor((diff % 60000) / 1000);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
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

function enrichGraphFromEvents(
  graph: ApiGraphNode[],
  events: ApiEvent[],
  mode: RunMode,
): ApiGraphNode[] {
  if (!graph.length || !events.length) {
    return graph;
  }
  const order = graph.map((node) => node.id);
  const indexById = new Map(order.map((id, index) => [id, index]));
  const next = graph.map((node) => ({ ...node }));
  const touched: number[] = [];
  let terminal: WorkflowStatus | null = null;

  for (const event of events) {
    const nodeId = graphNodeFromEvent(event, mode);
    const index = nodeId ? indexById.get(nodeId) : undefined;
    if (index === undefined) {
      continue;
    }
    touched.push(index);
    if (event.event_type === "pipeline_finished" || event.event_type === "pipeline_failed") {
      terminal = event.status;
      next[index].status = event.status;
    } else if (event.status === "running" || event.status === "waiting_review") {
      next[index].status = event.status;
    } else if (event.status === "success" || event.status === "failed" || event.status === "revised") {
      next[index].status = event.status;
    }
  }

  if (!touched.length) {
    return next;
  }
  const latest = Math.max(...touched);
  if (terminal) {
    next.forEach((node, index) => {
      if (index < latest && ["pending", "running", "waiting_review"].includes(node.status)) {
        node.status = "success";
      }
      if (index === latest) {
        node.status = terminal!;
      }
    });
    return next;
  }
  next.forEach((node, index) => {
    if (index < latest && ["pending", "running", "waiting_review"].includes(node.status)) {
      node.status = "success";
    } else if (index === latest && node.status === "pending") {
      node.status = "running";
    }
  });
  return next;
}

function graphNodeFromEvent(event: ApiEvent, mode: RunMode): string {
  if (event.node === "run_intake" || event.node === "input_review") {
    return "parse";
  }
  if (event.node === "planner") {
    return mode === "reproduce" ? "planning" : "prd";
  }
  if (event.event_type === "pipeline_finished" || event.event_type === "pipeline_failed") {
    return mode === "reproduce" ? "outputs" : "scaffold";
  }

  const message = event.message.toLowerCase();
  if (mode === "productize") {
    if (message.includes("capability card")) return "capability_cards";
    if (message.includes("capability map")) return "capability_map";
    if (message.includes("composition")) return "method_composition";
    if (message.includes("jtbd") || message.includes("job-to-be-done")) return "jtbd";
    if (message.includes("prd")) return "prd";
    if (message.includes("mvp") || message.includes("moscow")) return "mvp";
    if (message.includes("prototype") || message.includes("scaffold")) return "prototype";
    if (message.includes("evaluation") || message.includes("evaluator")) return "evaluation";
    if (message.includes("revision")) return "revision";
  }

  if (message.includes("research understanding")) return "research_evidence";
  if (message.includes("repository cloner") || message.includes("repository understanding")) return "repo_evidence";
  if (message.includes("reproduction planner")) return "planning";
  if (message.includes("implementation agent") || message.includes("generating code") || message.includes("revising code")) return "implementation";
  if (message.includes("sandbox")) return "command_routing";
  if (message.includes("code review") || message.includes("second review") || message.includes("review verdict")) return "review";
  if (message.includes("execution") || message.includes("diagnosis")) return "diagnosis";
  if (message.includes("report") || message.includes("output")) return "outputs";
  return event.node;
}
