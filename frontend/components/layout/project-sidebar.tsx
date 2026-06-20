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
  { label: "Projects", id: "run", icon: FolderKanban },
  { label: "Papers", id: "paper", icon: FileText },
  { label: "Repos", id: "repo", icon: GitFork },
  { label: "Runs", id: "run", icon: CirclePlay },
  { label: "Agents", id: "product", icon: Bot },
] as const;

export function ProjectSidebar({ currentTask, selectedNavId, onNavSelect }: ProjectSidebarProps) {
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
          {NAV_ITEMS.map(({ label, id, icon: Icon }, index) => (
            <button
              aria-label={label}
              className={index === 0 ? "global-nav-item active" : "global-nav-item"}
              key={label}
              type="button"
              onClick={() => onNavSelect(id)}
            >
              <Icon size={18} />
              <span>{label}</span>
            </button>
          ))}
        </div>
        <button className="global-nav-item settings-nav" aria-label="Settings" type="button">
          <Settings size={18} />
          <span>Settings</span>
        </button>
      </nav>

      <div className="sidebar-footer">
        <section className="plan-usage" aria-label="Plan usage">
          <strong>Pro Plan</strong>
          <span><b>12k</b> / 50k credits used</span>
          <div className="usage-track"><span /></div>
        </section>
        <button className="user-profile" type="button" aria-label="Jane Miller profile">
          <span className="avatar avatar-small">JM</span>
          <span className="user-copy">
            <strong>Jane Miller</strong>
            <small>jane@acme.ai</small>
          </span>
          <ChevronDown size={15} />
        </button>
      </div>
    </aside>
  );
}
