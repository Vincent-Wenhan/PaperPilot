"""Deterministic static-web templates for generated PaperPilot prototypes."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from schemas.product_schema import ProductUISpec

SUPPORTED_TEMPLATES = ("image", "text", "video", "file")

_TEMPLATE_KEYWORDS = {
    "image": (
        "image",
        "vision",
        "classification",
        "detection",
        "segmentation",
        "ocr",
        "medical imaging",
        "图像",
        "视觉",
    ),
    "text": (
        "text",
        "language",
        "question answering",
        "rag",
        "translation",
        "summarization",
        "information extraction",
        "文本",
        "问答",
        "翻译",
    ),
    "video": (
        "video",
        "tracking",
        "action recognition",
        "world model",
        "object-centric",
        "temporal",
        "视频",
        "跟踪",
    ),
}

_DEFAULT_MOCK_RESULTS = {
    "image": {
        "type": "image",
        "message": "Mock image analysis completed.",
        "result": {"label": "paper_specific_signal", "confidence": 0.88},
    },
    "text": {
        "type": "text",
        "message": "Mock text analysis completed.",
        "result": "The prototype returned a deterministic paper-aware response.",
    },
    "video": {
        "type": "video",
        "message": "Mock video analysis completed.",
        "report": "Temporal evidence and key events would appear here.",
    },
    "file": {
        "type": "file",
        "message": "Mock file analysis completed.",
        "report": "Structured findings would appear here.",
    },
}


def _normalize_template(template_type: str) -> str:
    normalized = template_type.strip().lower()
    if normalized not in SUPPORTED_TEMPLATES:
        raise ValueError(
            f"Unsupported template_type: {template_type}. "
            f"Expected one of {SUPPORTED_TEMPLATES}."
        )
    return normalized


def select_product_template(
    paper_info: str,
    method_info: str,
    repo_info: str,
    product_spec: str,
    preferred_type: str = "auto",
) -> str:
    """Choose one supported product template from user preference and evidence."""
    preference = preferred_type.strip().lower()
    if preference != "auto":
        if preference not in SUPPORTED_TEMPLATES:
            raise ValueError(
                "preferred_type must be auto, image, text, video, or file."
            )
        return preference

    evidence = " ".join((paper_info, method_info, repo_info, product_spec)).lower()
    scores = {
        template: sum(evidence.count(keyword) for keyword in keywords)
        for template, keywords in _TEMPLATE_KEYWORDS.items()
    }
    best_score = max(scores.values(), default=0)
    if best_score == 0:
        return "file"
    for template in ("image", "text", "video"):
        if scores[template] == best_score:
            return template
    return "file"


def _extract_product_name(product_spec: str) -> str:
    match = re.search(
        r"##\s+Product Name\s*\n+\s*([^\n#]+)",
        product_spec,
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()
    first_heading = re.search(r"^#\s+(.+)$", product_spec, flags=re.MULTILINE)
    if first_heading:
        return first_heading.group(1).strip()
    return "Generated Product Prototype"


def _extract_core_features(product_spec: str) -> list[str]:
    features: list[str] = []
    capture = False
    for line in product_spec.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("### core features"):
            capture = True
            continue
        if capture and stripped.startswith("#"):
            break
        if capture and stripped.startswith("- "):
            features.append(stripped[2:].strip())
    return features[:5]


def _as_list(value: Any, fallback: list[str]) -> list[str]:
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        return items or fallback
    return fallback


def _clean_label(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()[:80] or "Input"


def _safe_control_id(value: str, used: set[str], index: int) -> str:
    base = re.sub(r"[^a-zA-Z0-9_]+", "_", value.strip().lower()).strip("_")
    control_id = base or f"control_{index}"
    suffix = 2
    while control_id in used:
        control_id = f"{base or f'control_{index}'}_{suffix}"
        suffix += 1
    used.add(control_id)
    return control_id


def _template_primary_control(template: str) -> dict[str, Any]:
    if template == "text":
        return {
            "controlId": "primary_text",
            "label": "Input text",
            "type": "textarea",
            "default": "",
            "required": True,
        }
    if template == "image":
        return {
            "controlId": "primary_image",
            "label": "Upload an image",
            "type": "file",
            "accept": "image/*",
            "required": True,
        }
    if template == "video":
        return {
            "controlId": "primary_video",
            "label": "Upload a video",
            "type": "file",
            "accept": "video/*",
            "required": True,
        }
    return {
        "controlId": "primary_file",
        "label": "Upload a file",
        "type": "file",
        "required": True,
    }


def _control_from_label(label: str, used: set[str], index: int) -> dict[str, Any]:
    clean = _clean_label(label)
    lowered = clean.lower()
    control_type = "text"
    if any(word in lowered for word in ("threshold", "confidence", "sensitivity", "score")):
        control_type = "range"
    elif any(word in lowered for word in ("mode", "type", "selector", "category", "module")):
        control_type = "select"
    return {
        "controlId": _safe_control_id(clean, used, index),
        "label": clean,
        "type": control_type,
        "default": 0.65 if control_type == "range" else "",
        "options": ["Default", "Focused", "Broad"] if control_type == "select" else [],
        "required": False,
    }


def _ui_spec_to_payload(
    template: str,
    product_spec: str,
    frontend_plan: str,
    prototype_plan: dict[str, Any] | None,
    ui_spec: dict[str, Any] | None,
) -> dict[str, Any]:
    if ui_spec is not None:
        spec = ProductUISpec.model_validate(ui_spec)
        controls: list[dict[str, Any]] = []
        used: set[str] = set()
        for index, control in enumerate(spec.input_controls[:8], 1):
            control_id = _safe_control_id(
                control.control_id or control.label,
                used,
                index,
            )
            control_type = {
                "text_input": "text",
                "textarea": "textarea",
                "selectbox": "select",
                "slider": "range",
            }.get(control.control_type, "text")
            controls.append(
                {
                    "controlId": control_id,
                    "label": _clean_label(control.label or control_id),
                    "type": control_type,
                    "default": control.default,
                    "options": [str(option) for option in control.options],
                    "helpText": control.help_text,
                    "required": control.required,
                }
            )
        if not controls:
            controls.append(_template_primary_control(template))
        return {
            "templateType": template,
            "productName": spec.product_name or _extract_product_name(product_spec),
            "coreFeatures": _extract_core_features(product_spec)
            or ["Review input", "Run mock analysis", "Export structured findings"],
            "pageStructure": spec.page_sections
            or ["Set up task", "Run analysis", "Review evidence"],
            "controls": controls,
            "resultComponents": [
                component.model_dump(mode="json")
                for component in spec.result_components[:8]
            ],
            "mockResultSchema": spec.mock_result_schema,
            "states": spec.states.model_dump(mode="json"),
            "visualRules": spec.visual_rules,
            "frontendPlan": (frontend_plan or "Mock-first workflow").strip()[:1400],
            "uiSpecMarkers": {
                "structured_controls": True,
                "result_components": True,
                "state_copy": True,
                "mock_schema": True,
            },
        }

    prototype_plan = prototype_plan or {}
    used = {"primary_text", "primary_image", "primary_video", "primary_file"}
    dynamic_controls = [
        _control_from_label(label, used, index)
        for index, label in enumerate(
            _as_list(prototype_plan.get("user_inputs"), [f"{template} input", "Decision context"]),
            1,
        )
    ]
    return {
        "templateType": template,
        "productName": _extract_product_name(product_spec),
        "coreFeatures": _extract_core_features(product_spec)
        or ["Review input", "Run mock analysis", "Export structured findings"],
        "pageStructure": _as_list(
            prototype_plan.get("page_structure"),
            ["Set up task", "Review input", "Run mock analysis", "Export results"],
        ),
        "controls": [_template_primary_control(template), *dynamic_controls[:5]],
        "resultComponents": [
            {
                "component_id": f"output_{index}",
                "label": output,
                "component_type": "summary",
                "source_key": "",
                "description": output,
            }
            for index, output in enumerate(
                _as_list(
                    prototype_plan.get("system_outputs"),
                    ["Summary result", "Structured detail", "Downloadable JSON"],
                ),
                1,
            )
        ],
        "mockResultSchema": prototype_plan.get("mock_result")
        if isinstance(prototype_plan.get("mock_result"), dict)
        else {},
        "states": {
            "empty": "Provide an input to start the mock workflow.",
            "loading": "Running mock analysis.",
            "success": "Mock analysis completed.",
            "error": "The mock workflow could not complete.",
        },
        "visualRules": [],
        "frontendPlan": (frontend_plan or "Mock-first workflow").strip()[:1400],
        "uiSpecMarkers": {
            "structured_controls": False,
            "result_components": True,
            "state_copy": True,
            "mock_schema": bool(prototype_plan.get("mock_result")),
        },
    }


def _json_script(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_index_source(
    template_type: str,
    product_spec: str = "",
    frontend_plan: str = "",
    prototype_plan: dict[str, Any] | None = None,
    ui_spec: dict[str, Any] | None = None,
) -> str:
    """Return the static HTML shell for the generated prototype."""
    template = _normalize_template(template_type)
    payload = _ui_spec_to_payload(
        template,
        product_spec,
        frontend_plan,
        prototype_plan,
        ui_spec,
    )
    product_name = str(payload["productName"])
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{product_name}</title>
    <link rel="stylesheet" href="./styles.css" />
  </head>
  <body>
    <main id="app" class="app-shell" data-template="{template}">
      <noscript>This prototype requires JavaScript enabled in the browser.</noscript>
    </main>
    <script type="module" src="./adapter.js"></script>
    <script type="module" src="./app.js"></script>
  </body>
</html>
"""


def build_client_source(
    template_type: str,
    product_spec: str = "",
    frontend_plan: str = "",
    prototype_plan: dict[str, Any] | None = None,
    ui_spec: dict[str, Any] | None = None,
) -> str:
    """Return browser-side prototype logic with visible controls and results."""
    template = _normalize_template(template_type)
    payload = _ui_spec_to_payload(
        template,
        product_spec,
        frontend_plan,
        prototype_plan,
        ui_spec,
    )
    return f"""import {{ ModelAdapter }} from "./adapter.js";

const PRODUCT_CONFIG = {_json_script(payload)};
const UI_SPEC_MARKERS = PRODUCT_CONFIG.uiSpecMarkers;
const MODEL_ADAPTER = new ModelAdapter({{ mockMode: true }});

const app = document.querySelector("#app");

function el(tag, className = "", text = "") {{
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}}

function renderList(items, className) {{
  const list = el("ol", className);
  items.forEach((item) => {{
    const li = el("li", "", String(item));
    list.appendChild(li);
  }});
  return list;
}}

function createControl(control) {{
  const wrapper = el("label", "control");
  const caption = el("span", "control-label", control.label);
  wrapper.appendChild(caption);

  let input;
  if (control.type === "textarea") {{
    input = document.createElement("textarea");
    input.rows = 6;
    input.value = control.default || "";
  }} else if (control.type === "select") {{
    input = document.createElement("select");
    (control.options?.length ? control.options : ["Default"]).forEach((option) => {{
      const item = document.createElement("option");
      item.value = option;
      item.textContent = option;
      input.appendChild(item);
    }});
  }} else if (control.type === "range") {{
    input = document.createElement("input");
    input.type = "range";
    input.min = "0";
    input.max = "1";
    input.step = "0.05";
    input.value = String(control.default ?? 0.65);
  }} else {{
    input = document.createElement("input");
    input.type = control.type || "text";
    if (control.accept) input.accept = control.accept;
    if (control.default) input.value = control.default;
  }}

  input.id = control.controlId;
  input.name = control.controlId;
  input.required = Boolean(control.required);
  input.dataset.controlId = control.controlId;
  wrapper.appendChild(input);
  if (control.helpText) wrapper.appendChild(el("small", "muted", control.helpText));
  return wrapper;
}}

async function collectInputs(form) {{
  const values = {{}};
  for (const control of PRODUCT_CONFIG.controls) {{
    const input = form.elements.namedItem(control.controlId);
    if (!input) continue;
    if (input.type === "file") {{
      const file = input.files?.[0] || null;
      values[control.controlId] = file
        ? {{
            kind: "file",
            name: file.name,
            size: file.size,
            type: file.type,
            lastModified: file.lastModified,
          }}
        : {{ kind: "empty" }};
    }} else {{
      values[control.controlId] = input.value;
    }}
  }}
  return values;
}}

function renderResult(result) {{
  const panel = document.querySelector("#result-panel");
  panel.innerHTML = "";
  panel.appendChild(el("h2", "", "Result"));
  const metrics = el("div", "metrics");
  metrics.appendChild(el("div", "metric", `Type: ${{result.type || PRODUCT_CONFIG.templateType}}`));
  metrics.appendChild(el("div", "metric", `Signature: ${{result.input_signature || "n/a"}}`));
  metrics.appendChild(el("div", "metric", `Mode: ${{result.mock_mode ? "Mock" : "Integration"}}`));
  panel.appendChild(metrics);

  const tabs = el("div", "tabs");
  ["Summary", "Evidence & Limits", "Export"].forEach((name) => tabs.appendChild(el("span", "tab", name)));
  panel.appendChild(tabs);

  const pre = el("pre", "json-block");
  pre.textContent = JSON.stringify(result, null, 2);
  panel.appendChild(pre);

  const download = el("button", "secondary-button", "Download JSON");
  download.type = "button";
  download.addEventListener("click", () => {{
    const blob = new Blob([JSON.stringify(result, null, 2)], {{ type: "application/json" }});
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "product_result.json";
    link.click();
    URL.revokeObjectURL(url);
  }});
  panel.appendChild(download);
}}

function render() {{
  app.innerHTML = "";
  const header = el("header", "hero");
  header.appendChild(el("p", "eyebrow", `${{PRODUCT_CONFIG.templateType}} prototype`));
  header.appendChild(el("h1", "", PRODUCT_CONFIG.productName));
  header.appendChild(el("p", "subtle", "Mock-first research product prototype with a browser-native UI and manual adapter boundary."));
  app.appendChild(header);

  const grid = el("section", "workspace-grid");
  const setup = el("form", "panel");
  setup.id = "prototype-form";
  setup.appendChild(el("h2", "", "Workflow"));
  setup.appendChild(renderList(PRODUCT_CONFIG.pageStructure, "steps"));
  setup.appendChild(el("h2", "", "Task Setup"));
  PRODUCT_CONFIG.controls.forEach((control) => setup.appendChild(createControl(control)));
  const runButton = el("button", "primary-button", "Run Mock Analysis");
  runButton.type = "submit";
  setup.appendChild(runButton);

  const result = el("section", "panel result-panel");
  result.id = "result-panel";
  result.appendChild(el("h2", "", "Result"));
  result.appendChild(el("p", "muted", PRODUCT_CONFIG.states.empty));

  grid.appendChild(setup);
  grid.appendChild(result);
  app.appendChild(grid);

  const context = el("section", "context-grid");
  const features = el("div", "panel");
  features.appendChild(el("h2", "", "Core Features"));
  PRODUCT_CONFIG.coreFeatures.forEach((feature) => features.appendChild(el("p", "feature", feature)));
  const plan = el("div", "panel");
  plan.appendChild(el("h2", "", "Prototype Plan"));
  plan.appendChild(el("p", "muted", PRODUCT_CONFIG.frontendPlan));
  context.appendChild(features);
  context.appendChild(plan);
  app.appendChild(context);

  setup.addEventListener("submit", async (event) => {{
    event.preventDefault();
    result.innerHTML = `<h2>Result</h2><p class="muted">${{PRODUCT_CONFIG.states.loading}}</p>`;
    try {{
      const inputValues = await collectInputs(setup);
      const output = await MODEL_ADAPTER.predict(inputValues, PRODUCT_CONFIG);
      renderResult({{ ...output, configured_inputs: inputValues, ui_spec_markers: UI_SPEC_MARKERS }});
    }} catch (error) {{
      result.innerHTML = `<h2>Result</h2><p class="error">${{PRODUCT_CONFIG.states.error}}</p>`;
      result.appendChild(el("pre", "json-block", String(error)));
    }}
  }});
}}

render();
"""


def build_styles_source() -> str:
    """Return CSS for the generated static prototype."""
    return """body {
  margin: 0;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: #f6f7f9;
  color: #17202a;
}
.app-shell {
  width: min(1180px, calc(100% - 32px));
  margin: 0 auto;
  padding: 28px 0 40px;
}
.hero {
  padding: 12px 0 24px;
  border-bottom: 1px solid #d9dee7;
}
.eyebrow {
  margin: 0 0 6px;
  color: #59697d;
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
h1, h2 {
  margin: 0 0 12px;
  letter-spacing: 0;
}
h1 {
  font-size: clamp(2rem, 4vw, 3.4rem);
  line-height: 1.05;
}
h2 {
  font-size: 1rem;
}
.subtle, .muted {
  color: #5f6b7a;
}
.workspace-grid, .context-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 0.9fr);
  gap: 16px;
  margin-top: 18px;
}
.panel {
  background: #ffffff;
  border: 1px solid #dfe5ec;
  border-radius: 8px;
  padding: 18px;
  box-shadow: 0 8px 24px rgba(33, 45, 62, 0.06);
}
.steps {
  margin: 0 0 18px;
  padding-left: 20px;
}
.control {
  display: grid;
  gap: 6px;
  margin: 12px 0;
}
.control-label {
  font-size: 0.9rem;
  font-weight: 650;
}
input, textarea, select {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #c9d2df;
  border-radius: 6px;
  padding: 10px 11px;
  font: inherit;
  background: #fff;
}
input[type="range"] {
  padding: 0;
}
.primary-button, .secondary-button {
  border: 0;
  border-radius: 6px;
  cursor: pointer;
  font: inherit;
  font-weight: 650;
}
.primary-button {
  width: 100%;
  margin-top: 10px;
  padding: 12px 14px;
  background: #1769e0;
  color: #fff;
}
.secondary-button {
  padding: 9px 12px;
  background: #edf2f7;
  color: #1d2939;
}
.metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 14px;
}
.metric, .feature, .tab {
  border: 1px solid #dfe5ec;
  border-radius: 6px;
  padding: 10px;
  background: #fbfcfe;
}
.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.json-block {
  overflow: auto;
  max-height: 440px;
  background: #111827;
  color: #eef2ff;
  border-radius: 6px;
  padding: 14px;
}
.error {
  color: #b42318;
}
@media (max-width: 820px) {
  .workspace-grid, .context-grid, .metrics {
    grid-template-columns: 1fr;
  }
}
"""


def build_adapter_source(
    template_type: str,
    repo_path: str | Path,
    prototype_plan: dict[str, Any] | None = None,
) -> str:
    """Return a browser-side mock adapter without executing source code."""
    template = _normalize_template(template_type)
    prototype_plan = prototype_plan or {}
    mock_result = prototype_plan.get("mock_result")
    if isinstance(mock_result, dict) and mock_result:
        base_result = {"type": template, **mock_result}
    else:
        base_result = _DEFAULT_MOCK_RESULTS[template]
    payload = {
        "template": template,
        "repoPath": str(repo_path),
        "baseResult": base_result,
    }
    return f"""const ADAPTER_CONFIG = {_json_script(payload)};

export class ModelAdapter {{
  constructor({{ repoPath = ADAPTER_CONFIG.repoPath, device = "browser", mockMode = true }} = {{}}) {{
    this.repoPath = repoPath;
    this.device = device;
    this.mockMode = mockMode;
  }}

  setup() {{
    return {{
      ready: true,
      mock_mode: this.mockMode,
      repo_path: this.repoPath,
      device: this.device,
    }};
  }}

  async loadModel() {{
    if (this.mockMode) return null;
    throw new Error("Real model integration is not configured. Review repository inference code before disabling mock mode.");
  }}

  summarizeInput(value) {{
    if (value === null || value === undefined) return {{ kind: "empty" }};
    if (Array.isArray(value)) return value.map((item) => this.summarizeInput(item));
    if (typeof value === "object") {{
      const summary = {{}};
      for (const key of Object.keys(value).sort()) summary[key] = this.summarizeInput(value[key]);
      return summary;
    }}
    if (typeof value === "string") {{
      return {{ kind: "text", characters: value.length, preview: value.slice(0, 160) }};
    }}
    return {{ kind: typeof value, value: String(value).slice(0, 160) }};
  }}

  stableSignature(summary) {{
    const payload = JSON.stringify(summary, Object.keys(summary || {{}}).sort());
    let hash = 2166136261;
    for (let index = 0; index < payload.length; index += 1) {{
      hash ^= payload.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }}
    return (hash >>> 0).toString(16).padStart(8, "0");
  }}

  baseMockResult() {{
    return JSON.parse(JSON.stringify(ADAPTER_CONFIG.baseResult));
  }}

  async predict(inputData, productConfig = {{}}) {{
    if (!this.mockMode) {{
      throw new Error("Real prediction is not configured. Enable it only after manual adapter implementation.");
    }}
    const inputSummary = this.summarizeInput(inputData);
    const inputSignature = this.stableSignature(inputSummary);
    const result = this.baseMockResult();
    result.input_summary = inputSummary;
    result.input_signature = inputSignature;
    result.mock_mode = true;
    result.product_name = productConfig.productName || "";
    result.message = result.message || "Mock analysis completed.";
    if (result.result && typeof result.result === "object") {{
      result.result.input_signature = inputSignature;
    }} else if (typeof result.result === "string") {{
      result.result = `${{result.result}} Input signature: ${{inputSignature}}.`;
    }} else {{
      result.result = `Processed ${{ADAPTER_CONFIG.template}} input with signature ${{inputSignature}}.`;
    }}
    return result;
  }}
}}
"""


def build_static_bundle_sources(
    template_type: str,
    product_spec: str = "",
    frontend_plan: str = "",
    prototype_plan: dict[str, Any] | None = None,
    ui_spec: dict[str, Any] | None = None,
    repo_path: str | Path = "../workspace",
) -> dict[str, str]:
    """Return the complete static-web product bundle."""
    return {
        "index.html": build_index_source(
            template_type,
            product_spec,
            frontend_plan,
            prototype_plan=prototype_plan,
            ui_spec=ui_spec,
        ),
        "app.js": build_client_source(
            template_type,
            product_spec,
            frontend_plan,
            prototype_plan=prototype_plan,
            ui_spec=ui_spec,
        ),
        "adapter.js": build_adapter_source(
            template_type,
            repo_path,
            prototype_plan=prototype_plan,
        ),
        "styles.css": build_styles_source(),
    }
