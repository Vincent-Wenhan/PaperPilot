import { create } from "zustand";

type WorkbenchState = {
  selectedRunId: string;
  selectedArtifactId: string;
  setSelectedRunId: (runId: string) => void;
  setSelectedArtifactId: (artifactId: string) => void;
};

export const useWorkbenchStore = create<WorkbenchState>((set) => ({
  selectedRunId: "run_2026_0618_a",
  selectedArtifactId: "reproduction_plan",
  setSelectedRunId: (selectedRunId) => set({ selectedRunId }),
  setSelectedArtifactId: (selectedArtifactId) => set({ selectedArtifactId }),
}));
