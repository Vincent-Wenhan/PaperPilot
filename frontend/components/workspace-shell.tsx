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
  type ApiRun,
} from "@/lib/api";
import {
  activeProject,
  agentEvents,
  planSteps,
  projectNavItems,
} from "@/lib/mock-data";

export function WorkspaceShell() {
  const [apiRun, setApiRun] = useState<ApiRun | null>(null);
  const [timelineEvents, setTimelineEvents] = useState(agentEvents);

  useEffect(() => {
    let cancelled = false;
    fetchWorkbenchSnapshot()
      .then((snapshot) => {
        if (cancelled) {
          return;
        }
        setApiRun(snapshot.active_run);
        setTimelineEvents(snapshot.events.map(eventFromApi));
      })
      .catch(() => {
        // Keep the mock-first shell usable when the FastAPI server is not running.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const planItems =
    apiRun?.plan.map((label, index) => ({
      id: `api-plan-${index}`,
      label,
      enabled: true,
      status:
        index < 3
          ? ("success" as const)
          : index === 4
            ? ("waiting_review" as const)
            : ("pending" as const),
    })) ?? planSteps;

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
            <input aria-label="Search workspace" placeholder="Search runs, files, agents" />
          </div>

          <nav className="nav-section" aria-label="Project navigation">
            <NavGroup
              title="Inputs"
              icon={<FileText size={16} />}
              items={projectNavItems.slice(0, 2)}
            />
            <NavGroup
              title="Runs"
              icon={<Activity size={16} />}
              items={projectNavItems.slice(2, 3)}
            />
            <NavGroup
              title="Artifacts"
              icon={<Boxes size={16} />}
              items={projectNavItems.slice(3)}
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
              <button className="command-button" type="button">
                <MessageSquareText size={15} />
                Ask Agent
              </button>
              <button className="command-button primary" type="button">
                <Play size={15} />
                Continue
              </button>
            </div>
          </div>

          <section className="workspace-band two-columns">
            <div className="tool-panel plan-panel">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Co-planning</p>
                  <h2>Editable plan</h2>
                </div>
                <button className="icon-button" title="Approve plan" type="button">
                  <CheckSquare size={17} />
                </button>
              </div>
              <div className="plan-list">
                {planItems.map((step) => (
                  <label className="plan-step" key={step.id}>
                    <input type="checkbox" defaultChecked={step.enabled} />
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
                <ChatBubble
                  role="agent"
                  text="@repo scan found train.py, eval.py, and config/default.yaml."
                />
                <ChatBubble
                  role="user"
                  text="@run.sh keep the first check CPU-only and skip dataset download."
                />
                <ChatBubble
                  role="agent"
                  text="Updated plan: smoke test first, full training remains blocked."
                />
              </div>
              <div className="composer">
                <span>@</span>
                <input aria-label="Agent message" placeholder="paper, repo, prd, code, terminal" />
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
                <p>Medium-risk generated-code check. It is bounded to synthetic input and requires explicit approval.</p>
              </div>
              <div className="action-row">
                <button className="command-button primary" type="button">
                  Approve
                </button>
                <button className="command-button" type="button">
                  Edit
                </button>
                <button className="command-button" type="button">
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
}: {
  title: string;
  icon: ReactNode;
  items: typeof projectNavItems;
}) {
  return (
    <section className="nav-group">
      <div className="nav-group-title">
        {icon}
        <span>{title}</span>
      </div>
      {items.map((item) => (
        <button className="nav-item" key={item.id} type="button">
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
