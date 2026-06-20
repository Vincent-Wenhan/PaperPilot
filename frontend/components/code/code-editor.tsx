"use client";

import Editor, { type Monaco } from "@monaco-editor/react";
import type { editor } from "monaco-editor";
import { useEffect, useRef, useState } from "react";

import type { CodeFile } from "@/lib/mock-data";

const LANGUAGE_MAP: Record<string, string> = {
  py: "python",
  ts: "typescript",
  tsx: "typescript",
  js: "javascript",
  jsx: "javascript",
  json: "json",
  yaml: "yaml",
  yml: "yaml",
  md: "markdown",
  txt: "plaintext",
  sh: "shell",
  toml: "toml",
  cfg: "ini",
  ini: "ini",
};

function detectLanguage(path: string): string {
  const ext = path.split(".").pop() ?? "";
  return LANGUAGE_MAP[ext] ?? "plaintext";
}

type CodeEditorProps = {
  file: CodeFile;
  readOnly?: boolean;
  onSyntaxCheck?: (path: string) => void;
  onExplain?: (path: string) => void;
  onAskPatch?: (path: string) => void;
};

export function CodeEditor({
  file,
  readOnly = true,
  onSyntaxCheck,
  onExplain,
  onAskPatch,
}: CodeEditorProps) {
  const [editorMounted, setEditorMounted] = useState(false);
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);

  function handleMount(editor: editor.IStandaloneCodeEditor, _monaco: Monaco) {
    editorRef.current = editor;
    setEditorMounted(true);
  }

  useEffect(() => {
    setEditorMounted(false);
  }, [file.path]);

  return (
    <div className="code-editor">
      <div className="code-editor-meta">
        <span className="code-path">{file.path}</span>
        <span className="code-lang">{detectLanguage(file.path)}</span>
        {readOnly && <span className="code-readonly">read-only</span>}
        <div className="code-actions">
          {onSyntaxCheck && (
            <button
              className="command-button"
              type="button"
              onClick={() => onSyntaxCheck(file.path)}
            >
              Syntax Check
            </button>
          )}
          {onExplain && (
            <button
              className="command-button"
              type="button"
              onClick={() => onExplain(file.path)}
            >
              Explain
            </button>
          )}
          {onAskPatch && (
            <button
              className="command-button"
              type="button"
              onClick={() => onAskPatch(file.path)}
            >
              Ask Agent to Patch
            </button>
          )}
        </div>
      </div>
      <div className="monaco-container">
        <Editor
          height="100%"
          language={detectLanguage(file.path)}
          value={file.content}
          theme="vs-dark"
          onMount={handleMount}
          options={{
            readOnly,
            minimap: { enabled: false },
            fontSize: 13,
            lineNumbers: "on",
            scrollBeyondLastLine: false,
            wordWrap: "on",
            automaticLayout: true,
            tabSize: 4,
          }}
        />
      </div>
      {!editorMounted && file.content && (
        <pre className="code-fallback">
          <code>{file.content}</code>
        </pre>
      )}
    </div>
  );
}
