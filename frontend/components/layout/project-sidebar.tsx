"use client";

import type { ReactNode } from "react";
import {
  Activity,
  Boxes,
  FileText,
  Plus,
  Search,
  Settings,
} from "lucide-react";

import { StatusPill } from "@/components/status-pill";
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

export function ProjectSidebar({
  currentTask,
  query,
  selectedNavId,
  visibleNavItems,
  onQueryChange,
  onNavSelect,
  onNewRun,
}: ProjectSidebarProps) {
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
          onClick={onNewRun}
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
