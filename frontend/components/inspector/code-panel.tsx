"use client";

import type { CodeFile } from "@/lib/workbench-types";
import type { ApiFileNode } from "@/lib/api";
import { CodeEditor } from "@/components/code/code-editor";
import { FileTree, type FileTreeNode } from "@/components/code/file-tree";

type CodePanelProps = {
  fileTabs: Array<{ id: string; label: string }>;
  activeFileId: string;
  activeFile:
    | { id: string; path: string; language: string; content: string }
    | undefined;
  apiFiles: ApiFileNode[];
  onSelectFile: (id: string) => void;
  onSyntaxCheck?: (path: string) => void;
  onExplain?: (path: string) => void;
  onAskPatch?: (path: string) => void;
};

export function CodePanel({
  fileTabs,
  activeFileId,
  activeFile,
  apiFiles,
  onSelectFile,
  onSyntaxCheck,
  onExplain,
  onAskPatch,
}: CodePanelProps) {
  if (!activeFile) {
    return <div className="empty-state">No code files available.</div>;
  }

  const treeNodes: FileTreeNode[] = apiFiles.length > 0
    ? apiFiles.map((f) => ({
        path: f.path,
        name: f.name,
        kind: f.kind,
        size_bytes: f.size_bytes,
      }))
    : fileTabs.map((ft) => ({
        path: ft.id,
        name: ft.label,
        kind: "file" as const,
        size_bytes: 0,
      }));

  const editorFile: CodeFile = {
    id: activeFile.id,
    path: activeFile.path,
    language: activeFile.language,
    content: activeFile.content,
  };

  return (
    <div className="code-panel">
      <div className="code-panel-layout">
        <div className="code-panel-sidebar">
          <p className="eyebrow">Files</p>
          <FileTree
            files={treeNodes}
            activePath={activeFileId}
            onSelect={onSelectFile}
          />
        </div>
        <div className="code-panel-main">
          <CodeEditor
            file={editorFile}
            readOnly
            onSyntaxCheck={onSyntaxCheck}
            onExplain={onExplain}
            onAskPatch={onAskPatch}
          />
        </div>
      </div>
    </div>
  );
}
