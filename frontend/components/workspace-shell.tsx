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
  Search,
  Settings,
  ShieldCheck,
} from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";

import { InspectorPanel } from "@/components/inspector-panel";
import { StatusPill } from "@/components/status-pill";
import { WorkflowGraph } from "@/components/workflow-graph";
import {
  eventFromApi,
  fetchWorkbenchSnapshot,
  approveAction,
  editAction,
  rejectAction,
  type ApiRun,
} from "@/lib/api";
import {
  activeProject,
  agentEvents,
  planSteps,
  projectNavItems,
  type WorkflowStatus,
} from "@/lib/mock-data";

export function WorkspaceShell() {
  const [apiRun, setApiRun] = useState<ApiRun | null>(null);
  const [timelineEvents, setTimelineEvents] = useState(agentEvents);
  const [query, setQuery] = useState("");
  const [selectedNavId, setSelectedNavId] = useState("run");
  const [planState, setPlanState] = useState(planSteps);
  const [chatMessages, setChatMessages] = useState([
    {
      role: "agent" as const,
      text: "@repo scan found train.py, eval.py, and config/default.yaml.",
    },
    {
      role: "user" as const,
      text: "@run.sh keep the first check CPU-only and skip dataset download.",
    },
    {
      role: "agent" as const,
      text: "Updated plan: smoke test first, full training remains blocked.",
    },
  ]);
  const [chatInput, setChatInput] = useState("");
  const [approvalStatus, setApprovalStatus] = useState<
    "pending" | "approved" | "edited" | "rejected"
  >("pending");
  const [notice, setNotice] = useState("Workbench ready. Actions are preview-safe.");

  useEffect(() => {
    let cancelled = false;
    fetchWorkbenchSnapshot()
      .then((snapshot) => {
        if (cancelled) {
          return;
        }
        setApiRun(snapshot.active_run);
        setTimelineEvents(snapshot.events.map(eventFromApi));
        setPlanState(
          snapshot.active_run.plan.map((label, index) => ({
            id: `api-plan-${index}`,
            label,
            enabled: true,
            status:
              index < 3
                ? ("success" as const)
                : index === 4
                  ? ("waiting_review" as const)
                  : ("pending" as const),
          })),
        );
      })
      .catch(() => {
        // Keep the mock-first shell usable when the FastAPI server is not running.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const visibleNavItems = projectNavItems.filter((item) => {
    const haystack = `${item.label} ${item.meta}`.toLowerCase();
    return haystack.includes(query.toLowerCase());
  });

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

  function continueRun() {
    setPlanState((steps) =>
      steps.map((step) =>
        step.status === "pending" ? { ...step, status: "running" } : step,
      ),
    );
    setNotice("Continue queued. Runner remains gated by approval.");
    addTimelineEvent("Continue requested; waiting on reviewed command approval.");
  }

  function approvePlan() {
    setPlanState((steps) =>
      steps.map((step) =>
        step.enabled && step.status === "pending"
          ? { ...step, status: "success" }
          : step,
      ),
    );
    setNotice("Plan approved for the current preview run.");
    addTimelineEvent("Editable plan approved by user.", "success");
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
        text: "This preview keeps commands behind human approval. Open Runner and choose Approve, Edit, or Reject.",
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
    setNotice(`Action ${nextStatus}.`);
    addTimelineEvent(`Action ${nextStatus}: python main.py --smoke-test`, "success");
  }

  return (
    <main className="workbench-shell">
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
          <span>Project: {apiRun?.project_id ?? activeProject.name}</span>
          <span>Mode: {apiRun?.mode ?? activeProject.mode}</span>
          <span>Model: {activeProject.model}</span>
        </div>

        <div className="run-state">
          <span>{apiRun?.summary ?? activeProject.runStatus}</span>
          <StatusPill status={apiRun?.status ?? "waiting_review"} />
        </div>
      </header>

      <section className="workspace-grid">
        <aside className="navigator">
          <div className="navigator-header">
            <div>
              <p className="eyebrow">Workspace</p>
              <h1>{activeProject.name}</h1>
            </div>
            <button className="icon-button" title="New project" type="button">
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
              <h2>Reproduce workflow</h2>
            </div>
            <div className="toolbar-actions">
              <button className="command-button" type="button" onClick={askAgent}>
                <MessageSquareText size={15} />
                Ask Agent
              </button>
              <button className="command-button primary" type="button" onClick={continueRun}>
                <Play size={15} />
                Continue
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

        <InspectorPanel runId={apiRun?.run_id ?? "run_mock_reproduce"} />
      </section>
    </main>
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
  items: typeof projectNavItems;
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
