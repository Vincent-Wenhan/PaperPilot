"use client";

import type { ApiFileNode } from "@/lib/api";

type CodePanelProps = {
  fileTabs: Array<{ id: string; label: string }>;
  activeFileId: string;
  activeFile:
    | { id: string; path: string; language: string; content: string }
    | undefined;
  apiFiles: ApiFileNode[];
  onSelectFile: (id: string) => void;
};

export function CodePanel({
  fileTabs,
  activeFileId,
  activeFile,
  apiFiles,
  onSelectFile,
}: CodePanelProps) {
  if (!activeFile) {
    return <div className="empty-state">No code files available.</div>;
  }
  return (
    <div className="code-tab">
      {/* File tabs */}
      <div className="file-tabs">
        {fileTabs.map((file) => (
          <button
            key={file.id}
            className={activeFileId === file.id ? "file-tab active" : "file-tab"}
            onClick={() => onSelectFile(file.id)}
            type="button"
          >
            {file.label}
          </button>
        ))}
      </div>
      <div className="code-meta">
        <span>{activeFile.path}</span>
        <span>{activeFile.language}</span>
      </div>
      <pre className="code-block">
        <code>{activeFile.content}</code>
      </pre>
    </div>
  );
}
