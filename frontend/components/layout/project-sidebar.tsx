"use client";

import {
  Bot,
  ChevronDown,
  CirclePlay,
  FileText,
  FolderKanban,
  GitFork,
  Grid2X2,
  Settings,
} from "lucide-react";

import type { ProjectNavItem, RunMode } from "@/lib/mock-data";

export type RunFormState = {
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

type ProjectSidebarProps = {
  currentTask: string;
  query: string;
  selectedNavId: string;
  visibleNavItems: ProjectNavItem[];
  onQueryChange: (q: string) => void;
  onNavSelect: (id: string) => void;
  onNewRun: () => void;
};

const NAV_ITEMS = [
  { label: "Projects", id: "project", icon: FolderKanban },
  { label: "Papers", id: "paper", icon: FileText },
  { label: "Repos", id: "repo", icon: GitFork },
  { label: "Runs", id: "run", icon: CirclePlay },
  { label: "Agents", id: "agents", icon: Bot },
] as const;

export function ProjectSidebar({
  currentTask,
  selectedNavId,
  visibleNavItems,
  onNavSelect,
}: ProjectSidebarProps) {
  const runItem = visibleNavItems.find((item) => item.id === "run");
  const paperItem = visibleNavItems.find((item) => item.id === "paper");
  const repoItem = visibleNavItems.find((item) => item.id === "repo");
  const runLabel =
    runItem?.label.toLowerCase().includes("no backend run")
      ? "No active run"
      : (runItem?.label ?? "No active run");
  const sourceSummary = [
    paperItem?.status === "success" ? "PDF ready" : "No PDF",
    repoItem?.status === "success" ? "Repo ready" : "No repo",
  ].join(" / ");

  return (
    <aside className="navigator" title={currentTask}>
      <div className="sidebar-brand">
        <span className="paperpilot-mark" aria-hidden="true">
          <Grid2X2 size={22} />
        </span>
        <strong>PaperPilot</strong>
      </div>

      <nav className="nav-section" aria-label="Project navigation">
        <div className="primary-nav">
          {NAV_ITEMS.map(({ label, id, icon: Icon }) => (
            <button
              aria-label={label}
              aria-current={selectedNavId === id ? "page" : undefined}
              className={selectedNavId === id ? "global-nav-item active" : "global-nav-item"}
              key={label}
              type="button"
              onClick={() => onNavSelect(id)}
            >
              <Icon size={18} />
              <span>{label}</span>
            </button>
          ))}
        </div>
        <button
          className={selectedNavId === "settings" ? "global-nav-item settings-nav active" : "global-nav-item settings-nav"}
          aria-current={selectedNavId === "settings" ? "page" : undefined}
          aria-label="Settings"
          type="button"
          onClick={() => onNavSelect("settings")}
        >
          <Settings size={18} />
          <span>Settings</span>
        </button>
      </nav>

      <div className="sidebar-footer">
        <section className="plan-usage" aria-label="Workspace status">
          <strong>Local Workbench</strong>
          <span>{runLabel}</span>
          <small>{sourceSummary}</small>
        </section>
        <button
          className="user-profile"
          type="button"
          aria-label="Local workspace settings"
          onClick={() => onNavSelect("settings")}
        >
          <span className="avatar avatar-small">PP</span>
          <span className="user-copy">
            <strong>Local Session</strong>
            <small>No cloud billing</small>
          </span>
          <ChevronDown size={15} />
        </button>
      </div>
    </aside>
  );
}
