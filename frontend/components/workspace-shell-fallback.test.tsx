import React from "react";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { WorkspaceShell } from "@/components/workspace-shell";

vi.mock("@/components/workflow-graph", () => ({
  WorkflowGraph: () => <div aria-label="Workflow graph" />,
}));

vi.mock("@/components/inspector-panel", () => ({
  InspectorPanel: () => <aside aria-label="Run inspector" />,
}));

describe("workspace demo fallback", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
  });

  it("shows representative activity when the backend is unavailable", async () => {
    render(<WorkspaceShell />);

    expect((await screen.findAllByText(/Extracted method modules/)).length).toBeGreaterThan(0);
  });
});
