"use client";

import type { ChangeEvent, FormEvent } from "react";
import { useEffect, useRef, useState } from "react";

import { InspectorPanel } from "@/components/inspector-panel";
import { TopBar, type TopBarRunState } from "@/components/layout/top-bar";
import { ProjectSidebar } from "@/components/layout/project-sidebar";
import type { RunFormState } from "@/components/layout/project-sidebar";
import {
  CenterWorkspace,
  type WorkspaceSectionContext,
} from "@/components/layout/center-workspace";
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
  ApiRequestError,
  createRun,
  editAction,
  eventFromApi,
  executeAction,
  executeProductizeProposal,
  fetchCommandResults,
  fetchLlmConfig,
  fetchRun,
  fetchRunActions,
  fetchRunEvents,
  fetchRunGraph,
  fetchRunResult,
  rejectAction,
  requestRevision,
  saveLlmConfig,
  testLlmConnection,
  uploadPdf,
  type ApiAction,
  type ApiCommandRunResult,
  type ApiEvent,
  type ApiGraphNode,
  type ApiRevisionAction,
  type ApiRun,
  type ApiRunResult,
} from "@/lib/api";
import { planSteps } from "@/lib/mock-data";
import type {
  AgentEvent,
  PlanStep,
  ProjectNavItem,
  RunMode,
  WorkflowStatus,
} from "@/lib/workbench-types";

const defaultRunForm: RunFormState = {
  project_id: "paperpilot_workspace",
  mode: "reproduce",
  task: "",
  pdf_path: "",
  pdf_paths: [],
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

function readActiveRunId(): string {
  window.localStorage.removeItem(ACTIVE_RUN_STORAGE_KEY);
  return window.sessionStorage.getItem(ACTIVE_RUN_STORAGE_KEY) ?? "";
}

function writeActiveRunId(runId: string) {
  window.sessionStorage.setItem(ACTIVE_RUN_STORAGE_KEY, runId);
  window.localStorage.removeItem(ACTIVE_RUN_STORAGE_KEY);
}

function rememberActiveRun(run: ApiRun) {
  if (run.status === "running") {
    writeActiveRunId(run.run_id);
    return;
  }
  clearActiveRunId();
}

function clearActiveRunId() {
  window.sessionStorage.removeItem(ACTIVE_RUN_STORAGE_KEY);
  window.localStorage.removeItem(ACTIVE_RUN_STORAGE_KEY);
}

function isNotFoundError(error: unknown): boolean {
  return error instanceof ApiRequestError && error.status === 404;
}

export function WorkspaceShell() {
  const [apiRun, setApiRun] = useState<ApiRun | null>(null);
  const [timelineEvents, setTimelineEvents] = useState<AgentEvent[]>([]);
  const [graphNodes, setGraphNodes] = useState<ApiGraphNode[]>([]);
  const [runForm, setRunForm] = useState<RunFormState>(defaultRunForm);
  const [creatingRun, setCreatingRun] = useState(false);
  const [testingConnection, setTestingConnection] = useState(false);
  const [savingConfig, setSavingConfig] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedNavId, setSelectedNavId] = useState("run");
  const [planState, setPlanState] = useState(planSteps);
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
  const [commandResults, setCommandResults] = useState<ApiCommandRunResult[]>([]);
  const [approvalBusyId, setApprovalBusyId] = useState("");

  const activeRunId = apiRun?.run_id;
  const activeRunStatus = apiRun?.status;
  const currentProject = apiRun?.project_id ?? runForm.project_id;
  const currentMode = apiRun?.mode ?? runForm.mode;
  const currentTask =
    apiRun?.task || runForm.task || "New PaperPilot research run";
  const paperInput =
    apiRun?.inputs?.pdf_paths ||
    apiRun?.inputs?.pdf_path ||
    runForm.pdf_paths.join("\n") ||
    runForm.pdf_path;
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
    .filter((action) => action.status === "pending" || action.status === "edited")
    .map((action) => ({
      id: action.action_id,
      runId: action.run_id,
      agent: action.agent,
      type: action.tool === "apply_patch" ? "apply_patch" : "run_command",
      risk:
        action.risk === "blocked"
          ? "blocked"
          : action.execution_mode === "sandbox"
            ? "sandbox"
            : action.risk === "low"
              ? "safe"
              : "review",
      reason: action.reason,
      payload: {
        command: action.edited_command || action.command,
        cwd: action.cwd,
        path: action.path,
        patchId: action.patch_id,
      },
      status: action.status,
      executionStatus: action.execution_status,
    }));
  const displayedApprovalActions: PendingAction[] = pendingApprovalActions;
  const sectionContext: WorkspaceSectionContext = {
    projectId: currentProject,
    task: currentTask,
    paperInput,
    repoInput,
    mode: currentMode,
    model: currentModel,
    baseUrl: apiRun?.inputs?.llm_base_url ?? runForm.base_url,
    goal: apiRun?.inputs?.goal ?? runForm.goal,
    hardware: apiRun?.inputs?.hardware ?? runForm.hardware,
    gpuInfo: apiRun?.inputs?.gpu_info ?? runForm.gpu_info,
    mockMode: (apiRun?.inputs?.mock_mode ?? String(runForm.mock_mode)).toLowerCase() === "true",
    runId: apiRun?.run_id,
    runStatus: apiRun?.status ?? "pending",
    pendingActions: pendingApprovalActions.length,
    eventCount: timelineEvents.length,
    generatedFiles: Number(runResult?.generated_files ?? 0),
    pipelineStatus: String(runResult?.pipeline_status ?? apiRun?.result_summary?.pipeline_status ?? ""),
    productGoal,
    targetUser,
  };

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
    if (pendingApprovalActions.length > 0) {
      setApprovalOpen(true);
    }
  }, [pendingApprovalActions.length]);

  // Restore only actively running backend work. Review/completed runs should not
  // make a fresh page load look stuck on an old session.
  useEffect(() => {
    const storedRunId = readActiveRunId();
    if (!storedRunId) {
      return;
    }
    const restoreRunId = storedRunId;
    let cancelled = false;
    async function restoreRun() {
      try {
        const [
          restoredRun,
          restoredEvents,
          restoredGraph,
          restoredActions,
          restoredCommands,
          restoredResult,
        ] = await Promise.all([
          fetchRun(restoreRunId),
          fetchRunEvents(restoreRunId),
          fetchRunGraph(restoreRunId).catch(() => []),
          fetchRunActions(restoreRunId).catch(() => []),
          fetchCommandResults(restoreRunId).catch(() => []),
          fetchRunResult(restoreRunId).catch(() => null),
        ]);
        if (cancelled) {
          return;
        }
        if (restoredRun.status !== "running") {
          clearStaleRun(
            restoreRunId,
            `Previous run ${restoreRunId} is not running anymore. Start a new run when you want to submit fresh inputs.`,
          );
          return;
        }
        setApiRun(restoredRun);
        setTimelineEvents(restoredEvents.map(eventFromApi));
        setGraphNodes(enrichGraphFromEvents(restoredGraph, restoredEvents, restoredRun.mode));
        setPlanState(planForRunStatus(restoredRun));
        setNotice(restoredRun.summary);
        setApiActions(restoredActions);
        setCommandResults(restoredCommands);
        setRunResult(restoredResult);
        setEvaluationIssues(restoredResult ? issuesFromRunResult(restoredResult) : []);
      } catch (error) {
        if (cancelled) {
          return;
        }
        if (isNotFoundError(error)) {
          clearStaleRun(
            restoreRunId,
            `Run ${restoreRunId} is no longer available in the backend process. The backend may have restarted; start a new run or inspect saved outputs on disk.`,
          );
          return;
        }
        const message = error instanceof Error ? error.message : "restore failed";
        setNotice(`Could not restore previous run: ${message}`);
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
        const [
          nextRun,
          nextEvents,
          nextGraph,
          nextActions,
          nextCommands,
          nextResult,
        ] = await Promise.all([
          fetchRun(runId),
          fetchRunEvents(runId),
          fetchRunGraph(runId).catch(() => []),
          fetchRunActions(runId).catch(() => []),
          fetchCommandResults(runId).catch(() => []),
          fetchRunResult(runId).catch(() => null),
        ]);
        if (cancelled) {
          return;
        }
        setApiRun(nextRun);
        setTimelineEvents(nextEvents.map(eventFromApi));
        setGraphNodes(enrichGraphFromEvents(nextGraph, nextEvents, nextRun.mode));
        setPlanState(planForRunStatus(nextRun));
        setApiActions(nextActions);
        setCommandResults(nextCommands);
        setRunResult(nextResult);
        setEvaluationIssues(nextResult ? issuesFromRunResult(nextResult) : []);
        if (
          nextRun.mode === "productize" &&
          (nextResult?.productize_stage === "proposal_review" ||
            nextResult?.pipeline_status === "proposal_review")
        ) {
          setActiveWorkbenchTab("product");
        }
        if (nextRun.status !== "running") {
          setNotice(nextRun.summary);
        }
      } catch (error) {
        if (!cancelled) {
          if (isNotFoundError(error)) {
            clearStaleRun(
              runId,
              `Run ${runId} is stale because the backend no longer has its state. The running indicator has been cleared.`,
            );
            return;
          }
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

  // Fetch durable outputs when a run reaches a review or terminal state.
  useEffect(() => {
    if (!activeRunId) return;
    if (activeRunStatus !== "success" && activeRunStatus !== "waiting_review" && activeRunStatus !== "failed") return;
    Promise.all([
      fetchRunResult(activeRunId).catch(() => null),
      fetchCommandResults(activeRunId).catch(() => []),
      fetchRunActions(activeRunId).catch(() => []),
    ])
      .then(([result, commands, actions]) => {
        setRunResult(result);
        setCommandResults(commands);
        setApiActions(actions);
        setEvaluationIssues(result ? issuesFromRunResult(result) : []);
      })
      .catch(() => {});
  }, [activeRunId, activeRunStatus]);

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

  function clearStaleRun(runId: string, message: string) {
    clearActiveRunId();
    setApiRun(null);
    setApiActions([]);
    setCommandResults([]);
    setRunResult(null);
    setEvaluationIssues([]);
    setPlanState(planSteps);
    setNotice(message);
    setTimelineEvents((events) => [
      {
        id: `stale-${Date.now()}`,
        time: new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }),
        agent: "Workbench",
        eventType: "run_stale",
        message,
        status: "failed",
      },
      ...events,
    ]);
    setGraphNodes((nodes) =>
      nodes.map((node) =>
        node.status === "running"
          ? {
              ...node,
              status: "failed",
              issues: [
                ...node.issues,
                {
                  eventId: `stale-${runId}`,
                  message,
                  payload: { runId },
                },
              ],
            }
          : node,
      ),
    );
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
    clearActiveRunId();
    setRunForm((current) => ({ ...current, pdf_path: "", pdf_paths: [] }));
    setPlanState(planSteps);
    setGraphNodes([]);
    setTimelineEvents([]);
    setSelectedNavId("paper");
    setUploadedFileName("");
    setNotice("New workspace ready. Upload a PDF and create a backend run.");
    setRunResult(null);
    setEvaluationIssues([]);
    setCommandResults([]);
    setApprovalBusyId("");
  }

  function openNewRun() {
    resetWorkspace();
    setNewRunDrawerOpen(true);
  }

  function handleSidebarNavSelect(id: string) {
    setSelectedNavId(id);
    if (id === "project" || id === "run") {
      setActiveWorkbenchTab("workflow");
      setNotice(
        id === "run"
          ? apiRun
            ? `Showing workflow for ${apiRun.run_id}.`
            : "No backend run yet. Use New Run to submit a paper and repository."
          : `Showing project overview for ${currentProject}.`,
      );
      return;
    }
    if (id === "agents") {
      setActiveWorkbenchTab("product");
      setNotice(
        currentMode === "productize"
          ? "Showing product-design agent outputs for the active run."
          : "Agent outputs appear in the workflow and inspector after a run starts.",
      );
      return;
    }
    if (id === "paper") {
      setNotice("Showing paper input for the active workspace.");
      return;
    }
    if (id === "repo") {
      setNotice("Showing repository input for the active workspace.");
      return;
    }
    if (id === "settings") {
      setNotice("Showing local runtime settings.");
    }
  }

  function showWorkflow() {
    setSelectedNavId("run");
    setActiveWorkbenchTab("workflow");
  }

  async function handleFileUpload(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    if (!files.length) return;
    const invalidFile = files.find((file) => !file.name.toLowerCase().endsWith(".pdf"));
    if (invalidFile) {
      setNotice("Only PDF files are supported.");
      return;
    }
    setUploadingPdf(true);
    const multiProductize = runForm.mode === "productize" && files.length > 1;
    setNotice(
      multiProductize
        ? `Uploading ${files.length} PDFs...`
        : `Uploading ${files[0].name}...`,
    );
    try {
      const uploaded = await Promise.all(files.map((file) => uploadPdf(file)));
      const pdfPaths = uploaded.map((item) => item.pdf_path).filter(Boolean);
      const displayedPdfPaths =
        runForm.mode === "productize"
          ? appendUniquePaths(runForm.pdf_paths, pdfPaths)
          : pdfPaths;
      setRunForm((current) => {
        if (current.mode !== "productize") {
          return {
            ...current,
            pdf_path: pdfPaths[0] ?? "",
            pdf_paths: [],
          };
        }
        const nextPdfPaths = appendUniquePaths(current.pdf_paths, pdfPaths);
        return {
          ...current,
          pdf_path: nextPdfPaths[0] ?? "",
          pdf_paths: nextPdfPaths,
        };
      });
      setUploadedFileName(
        runForm.mode === "productize" && displayedPdfPaths.length > 1
          ? `${displayedPdfPaths.length} PDFs selected`
          : files[0].name,
      );
      setNotice(
        files.length > 1
          ? `Uploaded ${files.length} PDFs.`
          : `Uploaded: ${files[0].name}`,
      );
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

    const hasProductizePapers =
      runForm.mode === "productize" && runForm.pdf_paths.length > 0;
    if (!runForm.pdf_path.trim() && !hasProductizePapers) {
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
      const [runEvents, runGraph, runActions, runCommands, initialResult] = await Promise.all([
        fetchRunEvents(run.run_id).catch(() => []),
        fetchRunGraph(run.run_id).catch(() => []),
        fetchRunActions(run.run_id).catch(() => []),
        fetchCommandResults(run.run_id).catch(() => []),
        fetchRunResult(run.run_id).catch(() => null),
      ]);
      setApiRun(run);
      rememberActiveRun(run);
      setPlanState(planForRunStatus(run));
      setGraphNodes(enrichGraphFromEvents(runGraph, runEvents, run.mode));
      setTimelineEvents(
        runEvents.length ? runEvents.map(eventFromApi) : eventsFromRun(run),
      );
      setApiActions(runActions ?? []);
      setCommandResults(runCommands);
      setSelectedNavId("run");
      setNotice(`Started backend run ${run.run_id}. Agent progress will update here.`);
      setNewRunDrawerOpen(false);
      setRunResult(initialResult);
      setEvaluationIssues(initialResult ? issuesFromRunResult(initialResult) : []);
      if (initialResult?.productize_stage === "proposal_review" || initialResult?.pipeline_status === "proposal_review") {
        setActiveWorkbenchTab("product");
      } else {
        setActiveWorkbenchTab("workflow");
      }
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

  async function handleApproveAction(actionId: string) {
    const target = apiActions.find((a) => a.action_id === actionId);
    if (!target) {
      setNotice("Action is no longer available.");
      return;
    }
    setApprovalBusyId(actionId);
    try {
      const result = await executeAction(actionId);
      setNotice(result.message);
    } catch (error) {
      setNotice(`Action execution did not complete: ${describeActionError(error)}`);
    } finally {
      await refreshCurrentRun(target.run_id, { quiet: true });
      setApprovalBusyId("");
    }
  }

  async function handleEditAction(actionId: string, command: string) {
    const target = apiActions.find((a) => a.action_id === actionId);
    if (!target) {
      setNotice("Action is no longer available.");
      return;
    }
    setApprovalBusyId(actionId);
    try {
      await editAction(actionId, command);
      setNotice("Command edit saved. Review and approve it again before execution.");
    } catch (error) {
      setNotice(`Action edit failed: ${describeActionError(error)}`);
    } finally {
      await refreshCurrentRun(target.run_id, { quiet: true });
      setApprovalBusyId("");
    }
  }

  async function handleRejectAction(actionId: string) {
    const target = apiActions.find((a) => a.action_id === actionId);
    if (!target) {
      setNotice("Action is no longer available.");
      return;
    }
    setApprovalBusyId(actionId);
    try {
      await rejectAction(actionId);
      setNotice("Action rejected. No command or patch was executed.");
    } catch (error) {
      setNotice(`Action rejection failed: ${describeActionError(error)}`);
    } finally {
      await refreshCurrentRun(target.run_id, { quiet: true });
      setApprovalBusyId("");
    }
  }

  async function handleRequestRevision(issueId: string, action: ApiRevisionAction) {
    if (!apiRun) {
      setNotice("Create or restore a productize run before requesting a revision.");
      return;
    }
    try {
      const result = await requestRevision(apiRun.run_id, {
        issue_id: issueId,
        action,
      });
      setNotice(result.message);
      await refreshCurrentRun(apiRun.run_id, { quiet: true });
    } catch (error) {
      setNotice(`Revision request failed: ${describeActionError(error)}`);
    }
  }

  async function handleExecuteProductizeProposal(proposalIndex: number) {
    if (!apiRun) {
      setNotice("Create or restore a productize run before executing a proposal.");
      return;
    }
    setNotice(`Executing product proposal ${proposalIndex + 1}...`);
    try {
      const result = await executeProductizeProposal(apiRun.run_id, proposalIndex);
      setRunResult(result);
      setEvaluationIssues(issuesFromRunResult(result));
      addTimelineEvent(`Executed product proposal ${proposalIndex + 1}.`, "success");
      await refreshCurrentRun(apiRun.run_id, { quiet: true });
      setNotice("Selected product proposal executed.");
    } catch (error) {
      setNotice(`Proposal execution failed: ${describeActionError(error)}`);
    }
  }

  async function refreshCurrentRun(runId: string, options: { quiet?: boolean } = {}) {
    if (!options.quiet) {
      setNotice("Refreshing backend run state...");
    }
    try {
      const [
        nextRun,
        nextEvents,
        nextGraph,
        nextActions,
        nextCommands,
        nextResult,
      ] = await Promise.all([
        fetchRun(runId),
        fetchRunEvents(runId),
        fetchRunGraph(runId).catch(() => []),
        fetchRunActions(runId).catch(() => []),
        fetchCommandResults(runId).catch(() => []),
        fetchRunResult(runId).catch(() => null),
      ]);
      setApiRun(nextRun);
      rememberActiveRun(nextRun);
      setTimelineEvents(nextEvents.map(eventFromApi));
      setGraphNodes(enrichGraphFromEvents(nextGraph, nextEvents, nextRun.mode));
      setPlanState(planForRunStatus(nextRun));
      setApiActions(nextActions);
      setCommandResults(nextCommands);
      setRunResult(nextResult);
      setEvaluationIssues(nextResult ? issuesFromRunResult(nextResult) : []);
      if (
        nextRun.mode === "productize" &&
        (nextResult?.productize_stage === "proposal_review" ||
          nextResult?.pipeline_status === "proposal_review")
      ) {
        setActiveWorkbenchTab("product");
      }
      if (!options.quiet) {
        setNotice(nextRun.summary);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "refresh failed";
      setNotice(`Could not refresh backend run state: ${message}`);
    }
  }

  return (
    <main className="workbench-shell">
      <TopBar
        run={topBarRun}
        onNewRun={openNewRun}
        onModeChange={handleModeChange}
      />

      <section className="workspace-grid">
        <ProjectSidebar
          currentTask={currentTask}
          query={query}
          selectedNavId={selectedNavId}
          visibleNavItems={visibleNavItems}
          onQueryChange={setQuery}
          onNavSelect={handleSidebarNavSelect}
          onNewRun={openNewRun}
        />

        <CenterWorkspace
          mode={currentMode}
          notice={notice}
          planState={planState}
          timelineEvents={timelineEvents}
          runStatus={apiRun?.status ?? "pending"}
          hasRun={Boolean(apiRun)}
          graphNodes={graphNodes}
          activeTab={activeWorkbenchTab}
          activeNavId={selectedNavId}
          sectionContext={sectionContext}
          onTabChange={setActiveWorkbenchTab}
          onTogglePlanStep={togglePlanStep}
          onApprovePlan={approvePlan}
          onContinueRun={continueRun}
          onOpenRunDrawer={() => setNewRunDrawerOpen(true)}
          onShowWorkflow={showWorkflow}
          onRequestRevision={(issueId, action) => void handleRequestRevision(issueId, action)}
          runResult={runResult}
          onExecuteProductizeProposal={(index) => void handleExecuteProductizeProposal(index)}
          evaluationIssues={evaluationIssues}
        />

        <InspectorPanel
          events={timelineEvents}
          refreshToken={apiRun?.updated_at ?? ""}
          runId={apiRun?.run_id ?? ""}
          runStatus={apiRun?.status ?? "pending"}
          preview={false}
        />
      </section>

      <BottomDock
        events={timelineEvents}
        commandResults={formatCommandResults(commandResults)}
        resultSummary={buildResultSummary(runResult, apiActions, commandResults)}
        runId={apiRun?.run_id}
      />

      <ActionApprovalDrawer
        open={approvalOpen && displayedApprovalActions.length > 0}
        actions={displayedApprovalActions}
        busyActionId={approvalBusyId}
        onClose={() => setApprovalOpen(false)}
        onApprove={(id) => void handleApproveAction(id)}
        onEdit={(id, command) => void handleEditAction(id, command)}
        onReject={(id) => void handleRejectAction(id)}
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

function appendUniquePaths(existing: string[], additions: string[]): string[] {
  return Array.from(new Set([...existing, ...additions].filter(Boolean)));
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

function describeActionError(error: unknown): string {
  if (error instanceof ApiRequestError) {
    if (typeof error.detail === "object" && error.detail !== null) {
      const detail = error.detail as Record<string, unknown>;
      if (typeof detail.message === "string") {
        return detail.message;
      }
      if (typeof detail.blocked_reason === "string") {
        return detail.blocked_reason;
      }
    }
    return error.message || `API returned ${error.status}`;
  }
  return error instanceof Error ? error.message : "action failed";
}

function formatCommandResults(results: ApiCommandRunResult[]): string {
  if (!results.length) {
    return "";
  }
  return results
    .map((result, index) => {
      const lines = [
        `$ ${result.command}`,
        `cwd: ${result.cwd}`,
        `mode: ${result.mode}`,
        `risk: ${result.risk_level}`,
        `executed: ${String(result.executed)}`,
        `exit_code: ${result.exit_code ?? "not available"}`,
      ];
      if (result.blocked_reason) {
        lines.push(`blocked_reason: ${result.blocked_reason}`);
      }
      if (result.stdout) {
        lines.push("", "stdout:", result.stdout.trimEnd());
      }
      if (result.stderr) {
        lines.push("", "stderr:", result.stderr.trimEnd());
      }
      return [`# Command result ${index + 1}`, ...lines].join("\n");
    })
    .join("\n\n");
}

function buildResultSummary(
  runResult: ApiRunResult | null,
  actions: ApiAction[],
  commands: ApiCommandRunResult[],
): Record<string, unknown> | null {
  if (!runResult && !actions.length && !commands.length) {
    return null;
  }
  return {
    run: runResult,
    actions: actions.map((action) => ({
      action_id: action.action_id,
      tool: action.tool,
      status: action.status,
      execution_status: action.execution_status,
      command: action.edited_command || action.command || undefined,
      cwd: action.cwd || undefined,
      patch_id: action.patch_id || undefined,
      path: action.path || undefined,
      result: Object.keys(action.execution_result ?? {}).length
        ? action.execution_result
        : undefined,
    })),
    commands,
  };
}

const TERMINAL_EVENT_TYPES = new Set([
  "pipeline_finished",
  "pipeline_failed",
  "review_actions_resolved",
]);

export function enrichGraphFromEvents(
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
  let latestMappedNode = "";

  for (const event of events) {
    const nodeId = graphNodeFromEvent(event, mode, indexById, latestMappedNode);
    const index = nodeId ? indexById.get(nodeId) : undefined;
    if (index === undefined) {
      continue;
    }
    touched.push(index);
    if (event.event_type !== "pipeline_failed") {
      latestMappedNode = nodeId;
    }
    if (TERMINAL_EVENT_TYPES.has(event.event_type)) {
      terminal = event.status;
      next[index].status = event.status;
    } else if (event.status === "running" || event.status === "waiting_review") {
      next[index].status = mergeWorkflowStatus(next[index].status, event.status);
    } else if (event.status === "success" || event.status === "failed" || event.status === "revised") {
      next[index].status = mergeWorkflowStatus(next[index].status, event.status);
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

function mergeWorkflowStatus(current: WorkflowStatus, incoming: WorkflowStatus): WorkflowStatus {
  if (incoming === "failed" || incoming === "success" || incoming === "revised") {
    return incoming;
  }
  if (incoming === "waiting_review") {
    return current === "failed" || current === "success" || current === "revised"
      ? current
      : incoming;
  }
  if (incoming === "running") {
    return current === "pending" ? incoming : current;
  }
  return current;
}

function graphNodeFromEvent(
  event: ApiEvent,
  mode: RunMode,
  knownNodeIds?: Map<string, number>,
  latestMappedNode = "",
): string {
  if (event.node === "run_intake" || event.node === "input_review") {
    return "parse";
  }
  if (event.node === "planner") {
    return mode === "reproduce" ? "planning" : "prd";
  }
  if (event.node === "runner_execution" || event.node === "runner_review") {
    return mode === "reproduce" ? "command_routing" : "scaffold";
  }
  if (mode === "productize" && event.event_type === "pipeline_failed") {
    return latestMappedNode || "parse";
  }
  if (
    mode === "productize" &&
    event.event_type === "pipeline_finished" &&
    event.payload?.pipeline_status === "proposal_review"
  ) {
    return "mvp";
  }
  if (mode === "productize" && event.event_type === "proposal_executed") {
    return "scaffold";
  }
  if (TERMINAL_EVENT_TYPES.has(event.event_type)) {
    return mode === "reproduce" ? "outputs" : "scaffold";
  }

  const message = event.message.toLowerCase();
  if (mode === "productize") {
    if (message.includes("extracting capability")) return "capability_cards";
    if (message.includes("composing paper capabilities")) return "capability_map";
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

  if (knownNodeIds?.has(event.node)) {
    return event.node;
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
