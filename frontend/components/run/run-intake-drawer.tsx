"use client";

import type { ChangeEvent, FormEvent } from "react";
import { useRef } from "react";
import { Play, Save, Upload, X } from "lucide-react";

import type { RunFormState } from "@/components/layout/project-sidebar";
import type { RunMode } from "@/lib/workbench-types";

type RunIntakeDrawerProps = {
  open: boolean;
  runForm: RunFormState;
  creatingRun: boolean;
  testingConnection: boolean;
  savingConfig: boolean;
  uploadingPdf: boolean;
  uploadedFileName: string;
  onClose: () => void;
  onFormUpdate: <K extends keyof RunFormState>(key: K, value: RunFormState[K]) => void;
  onFileUpload: (event: ChangeEvent<HTMLInputElement>) => void;
  onSaveConfig: () => void;
  onTestConnection: () => void;
  onSubmitRun: (event: FormEvent<HTMLFormElement>) => void;
};

export function RunIntakeDrawer({
  open,
  runForm,
  creatingRun,
  testingConnection,
  savingConfig,
  uploadingPdf,
  uploadedFileName,
  onClose,
  onFormUpdate,
  onFileUpload,
  onSaveConfig,
  onTestConnection,
  onSubmitRun,
}: RunIntakeDrawerProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!open) return null;

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header">
          <h2>New Run</h2>
          <button className="icon-button" type="button" onClick={onClose} title="Close">
            <X size={17} />
          </button>
        </div>

        <form className="run-form" onSubmit={onSubmitRun}>
          <div className="form-row">
            <label>
              <span>Mode</span>
              <select
                value={runForm.mode}
                onChange={(event) =>
                  onFormUpdate("mode", event.target.value as RunMode)
                }
              >
                <option value="reproduce">Reproduce</option>
                <option value="productize">Productize</option>
              </select>
            </label>
            <label>
              <span>Project</span>
              <input
                value={runForm.project_id}
                onChange={(event) => onFormUpdate("project_id", event.target.value)}
                placeholder="project_id"
              />
            </label>
          </div>

          <label>
            <span>Paper PDF</span>
            <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                onChange={onFileUpload}
                style={{ display: "none" }}
              />
              <button
                className="command-button"
                type="button"
                disabled={uploadingPdf}
                onClick={() => fileInputRef.current?.click()}
                style={{ flex: 1, justifyContent: "flex-start" }}
              >
                <Upload size={14} />
                {uploadingPdf ? "Uploading..." : uploadedFileName || "Choose PDF..."}
              </button>
            </div>
          </label>

          <label>
            <span>Repository</span>
            <input
              value={runForm.github_url}
              onChange={(event) => onFormUpdate("github_url", event.target.value)}
              placeholder="GitHub URL or local repo path"
            />
          </label>

          <div className="form-row">
            <label>
              <span>Hardware</span>
              <select
                value={runForm.hardware}
                onChange={(event) => onFormUpdate("hardware", event.target.value)}
              >
                <option value="CPU only">CPU only</option>
                <option value="Single GPU">Single GPU</option>
                <option value="Multi GPU">Multi GPU</option>
              </select>
            </label>
            <label>
              <span>GPU</span>
              <input
                value={runForm.gpu_info}
                onChange={(event) => onFormUpdate("gpu_info", event.target.value)}
                placeholder="e.g. RTX 4090"
              />
            </label>
          </div>

          {runForm.mode === "reproduce" && (
            <label>
              <span>Goal</span>
              <select
                value={runForm.goal}
                onChange={(event) => onFormUpdate("goal", event.target.value)}
              >
                <option value="understand paper">understand paper</option>
                <option value="run official demo">run official demo</option>
                <option value="minimal training experiment">
                  minimal training experiment
                </option>
                <option value="reproduce main experiments">
                  reproduce main experiments
                </option>
                <option value="debug errors">debug errors</option>
              </select>
            </label>
          )}

          <label>
            <span>Task</span>
            <textarea
              value={runForm.task}
              onChange={(event) => onFormUpdate("task", event.target.value)}
              placeholder="What should PaperPilot do?"
              rows={3}
            />
          </label>

          {runForm.mode === "productize" && (
            <>
              <label>
                <span>Preferred Type</span>
                <select
                  value={runForm.preferred_type}
                  onChange={(event) =>
                    onFormUpdate("preferred_type", event.target.value)
                  }
                >
                  <option value="auto">Auto</option>
                  <option value="image">Image</option>
                  <option value="text">Text</option>
                  <option value="video">Video</option>
                  <option value="file">File</option>
                </select>
              </label>
              <label>
                <span>Target User</span>
                <input
                  value={runForm.target_user}
                  onChange={(event) =>
                    onFormUpdate("target_user", event.target.value)
                  }
                  placeholder="e.g. lab teams, students, clinicians"
                />
              </label>
              <label>
                <span>Product Goal</span>
                <textarea
                  value={runForm.product_goal}
                  onChange={(event) =>
                    onFormUpdate("product_goal", event.target.value)
                  }
                  placeholder="Mock-first product outcome"
                  rows={2}
                />
              </label>
            </>
          )}

          <div className="form-divider">
            <span>Agent Runtime</span>
          </div>

          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={runForm.mock_mode}
              onChange={(event) => onFormUpdate("mock_mode", event.target.checked)}
            />
            <span>Mock Mode (runs pipeline without LLM calls)</span>
          </label>

          <label>
            <span>API Key (session only — never saved)</span>
            <input
              type="password"
              value={runForm.api_key}
              onChange={(event) => onFormUpdate("api_key", event.target.value)}
              placeholder={runForm.mock_mode ? "not needed in Mock Mode" : "sk-..."}
            />
          </label>

          <label>
            <span>Base URL</span>
            <input
              value={runForm.base_url}
              onChange={(event) => onFormUpdate("base_url", event.target.value)}
              placeholder="https://api.openai.com/v1"
            />
          </label>

          <div className="form-row">
            <label>
              <span>Model</span>
              <input
                value={runForm.model}
                onChange={(event) => onFormUpdate("model", event.target.value)}
                placeholder="gpt-4o-mini"
              />
            </label>
            <label>
              <span>Code Model</span>
              <input
                value={runForm.implementation_model}
                onChange={(event) =>
                  onFormUpdate("implementation_model", event.target.value)
                }
                placeholder="optional"
              />
            </label>
          </div>

          <button
            className="command-button"
            disabled={testingConnection}
            type="button"
            onClick={onTestConnection}
          >
            {testingConnection ? "Testing..." : "Test LLM"}
          </button>

          <button
            className="command-button"
            disabled={savingConfig}
            type="button"
            onClick={onSaveConfig}
          >
            <Save size={14} />
            {savingConfig ? "Saving..." : "Save Config"}
          </button>

          <button className="command-button primary" disabled={creatingRun} type="submit">
            <Play size={15} />
            {creatingRun ? "Starting..." : "Run Agents"}
          </button>
        </form>
      </div>
    </div>
  );
}
