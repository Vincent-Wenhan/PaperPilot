"use client";

import { Boxes, GitGraph, MessageSquareText, ShieldAlert, type LucideIcon } from "lucide-react";

export type WorkbenchTabId = "workflow" | "chat" | "evaluation" | "product";

type WorkbenchTabsProps = {
  activeTab: WorkbenchTabId;
  onTabChange: (tab: WorkbenchTabId) => void;
};

const TABS: Array<{ id: WorkbenchTabId; label: string; icon: LucideIcon }> = [
  { id: "workflow", label: "Workflow", icon: GitGraph },
  { id: "chat", label: "Chat", icon: MessageSquareText },
  { id: "evaluation", label: "Evaluation", icon: ShieldAlert },
  { id: "product", label: "Product", icon: Boxes },
];

export function WorkbenchTabs({ activeTab, onTabChange }: WorkbenchTabsProps) {
  return (
    <div className="workbench-tab-list" role="tablist" aria-label="Workbench tabs">
      {TABS.map((tab) => {
        const Icon = tab.icon;
        return (
          <button
            key={tab.id}
            className={activeTab === tab.id ? "tab active" : "tab"}
            onClick={() => onTabChange(tab.id)}
            type="button"
          >
            <Icon size={15} />
            <span>{tab.label}</span>
          </button>
        );
      })}
    </div>
  );
}
