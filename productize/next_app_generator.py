"""Generate a real Next.js application bundle from a ProductPlan.

Replaces the static mock-first bundle (``productize.product_scaffold``) with
a strict contract: ``GeneratedFile`` + ``AppContract`` + ``GeneratedAppBundle``
written through ``productize.next_app_writer.write_bundle``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from schemas.generated_app import (
    AppContract,
    GeneratedAppBundle,
    GeneratedFile,
)
from schemas.product_schema import ProductPlan

DEFAULT_INTEGRATION_NOTES = [
    "Adapter is mock-first by default; replace lib/adapter.ts with the real inference call when ready.",
    "All API routes live under app/api/*; the browser never sees the adapter directly.",
    "Run `npm run dev` for HMR; `npm run build && npm start` for production.",
]


def build_contract(plan: ProductPlan) -> AppContract:
    product_name = plan.prd.product_name or "PaperPilot Product"
    return AppContract(
        required_scripts={
            "dev": "next dev",
            "build": "next build",
            "start": "next start",
            "test": "vitest run",
            "test:e2e": "playwright test",
            "lint": "next lint",
        },
        required_routes=[
            "/",
            f"/{product_name.lower().replace(' ', '-')}/result",
        ],
        required_components=[
            "components/UploadCard.tsx",
            "components/ResultPanel.tsx",
            "components/ErrorBoundary.tsx",
        ],
        required_api_routes=[
            "app/api/health/route.ts",
            "app/api/predict/route.ts",
        ],
        acceptance_tests=[
            "tests/e2e/product.spec.ts covers the primary workflow",
            "npm run build succeeds without type errors",
            "app/api/predict/route.ts returns 200 with mock adapter",
        ],
        real_adapter_required=True,
        mock_fallback_allowed=True,
    )


def build_files(plan: ProductPlan, repo_path: str | None = None) -> list[GeneratedFile]:
    return [
        _package_json(),
        _tsconfig(),
        _next_config(),
        _tailwind_config(),
        _postcss_config(),
        _vitest_config(),
        _playwright_config(),
        _gitignore(),
        _env_example(),
        _app_layout(plan),
        _app_page(plan),
        _app_globals(),
        _api_health_route(),
        _api_predict_route(),
        _lib_adapter(plan, repo_path),
        _lib_types(),
        _components_upload_card(),
        _components_result_panel(),
        _components_error_boundary(),
        _tests_e2e_product_spec(),
        _tests_unit_predict_spec(),
        _readme(plan, repo_path),
    ]


def build_bundle(plan: ProductPlan, repo_path: str | None = None) -> GeneratedAppBundle:
    return GeneratedAppBundle(
        contract=build_contract(plan),
        files=build_files(plan, repo_path=repo_path),
        integration_notes=list(DEFAULT_INTEGRATION_NOTES),
    )


def _package_json() -> GeneratedFile:
    return GeneratedFile(
        path="package.json",
        content="""{
  "name": "paperpilot-generated-app",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "test": "vitest run",
    "test:e2e": "playwright test",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "14.2.5",
    "react": "18.3.1",
    "react-dom": "18.3.1"
  },
  "devDependencies": {
    "@playwright/test": "1.45.0",
    "@types/node": "20.14.10",
    "@types/react": "18.3.3",
    "@types/react-dom": "18.3.0",
    "autoprefixer": "10.4.19",
    "postcss": "8.4.39",
    "tailwindcss": "3.4.6",
    "typescript": "5.5.3",
    "vitest": "2.0.3"
  }
}
""",
        purpose="Dependency manifest and npm scripts.",
    )


def _tsconfig() -> GeneratedFile:
    return GeneratedFile(
        path="tsconfig.json",
        content="""{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
""",
        purpose="TypeScript compiler configuration.",
    )


def _next_config() -> GeneratedFile:
    return GeneratedFile(
        path="next.config.mjs",
        content="""/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    typedRoutes: true,
  },
};

export default nextConfig;
""",
        purpose="Next.js configuration.",
    )


def _tailwind_config() -> GeneratedFile:
    return GeneratedFile(
        path="tailwind.config.ts",
        content="""import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};

export default config;
""",
        purpose="Tailwind CSS configuration.",
    )


def _postcss_config() -> GeneratedFile:
    return GeneratedFile(
        path="postcss.config.mjs",
        content="""export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
""",
        purpose="PostCSS pipeline for Tailwind + autoprefixer.",
    )


def _vitest_config() -> GeneratedFile:
    return GeneratedFile(
        path="vitest.config.ts",
        content="""import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["tests/unit/**/*.spec.ts"],
  },
});
""",
        purpose="Vitest configuration for unit tests.",
    )


def _playwright_config() -> GeneratedFile:
    return GeneratedFile(
        path="playwright.config.ts",
        content="""import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  retries: 1,
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: {
    command: "npm run dev",
    url: "http://127.0.0.1:3000",
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
""",
        purpose="Playwright configuration for E2E tests.",
    )


def _gitignore() -> GeneratedFile:
    return GeneratedFile(
        path=".gitignore",
        content="""# dependencies
/node_modules
/.pnp
.pnp.js

# next.js
/.next/
/out/

# production
/build

# misc
.DS_Store
*.pem

# debug
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# local env files
.env*.local

# typescript
*.tsbuildinfo
next-env.d.ts
""",
        purpose="Files Git should ignore.",
    )


def _env_example() -> GeneratedFile:
    return GeneratedFile(
        path=".env.example",
        content="""# Mock adapter by default — no real model integration.
PAPERPILOT_MOCK_MODE=true

# When ready to integrate the real model, set:
# PAPERPILOT_MODEL_ENDPOINT=https://...
# PAPERPILOT_MODEL_API_KEY=...
""",
        purpose="Environment variable template.",
    )


def _app_layout(plan: ProductPlan) -> GeneratedFile:
    product_name = plan.prd.product_name or "PaperPilot Product"
    content = (
        "import type { Metadata } from \"next\";\n"
        "import \"./globals.css\";\n\n"
        f"export const metadata: Metadata = {{\n"
        f"  title: \"{product_name}\",\n"
        "  description: \"Generated by PaperPilot Productize Mode.\",\n"
        "};\n\n"
        "export default function RootLayout({\n"
        "  children,\n"
        "}: {\n"
        "  children: React.ReactNode;\n"
        "}) {\n"
        "  return (\n"
        "    <html lang=\"en\">\n"
        "      <body className=\"min-h-dvh bg-background text-foreground antialiased\">\n"
        "        {children}\n"
        "      </body>\n"
        "    </html>\n"
        "  );\n"
        "}\n"
    )
    return GeneratedFile(
        path="app/layout.tsx",
        content=content,
        purpose="Root layout with global stylesheet.",
    )


def _app_page(plan: ProductPlan) -> GeneratedFile:
    product_name = plan.prd.product_name or "PaperPilot Product"
    problem = plan.prd.problem_statement or "No problem statement was generated."
    goals = plan.prd.goals or ["Demonstrate the paper's core capability interactively."]
    features = plan.prd.core_features or ["Upload input, run mock prediction, view result."]
    flow = plan.prd.user_flow or ["Upload", "Predict", "Review"]

    goals_items = "\n".join(f"      <li>{g}</li>" for g in goals)
    features_items = "\n".join(f"      <li>{f}</li>" for f in features)
    flow_items = "\n".join(
        "      <li>"
        f"<span className=\"text-xs text-muted-foreground\">Step {i + 1}</span>"
        f"<span className=\"ml-2 text-sm font-medium\">{step}</span>"
        "</li>"
        for i, step in enumerate(flow)
    )

    content = f"""import {{ UploadCard }} from "@/components/UploadCard";
import {{ ResultPanel }} from "@/components/ResultPanel";
import {{ ErrorBoundary }} from "@/components/ErrorBoundary";

const goals = [
{goals_items}
];

const features = [
{features_items}
];

const flow = [
{flow_items}
];

export default function Page() {{
  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <header className="mb-10">
        <h1 className="text-3xl font-bold tracking-tight">{product_name}</h1>
        <p className="mt-3 text-sm text-muted-foreground">{problem}</p>
      </header>

      <section className="grid gap-6 md:grid-cols-2">
        <article className="rounded-xl border bg-card p-5 shadow-sm">
          <h2 className="text-sm font-semibold">Goals</h2>
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm">
            {{goals.map((g) => (
              <li key={{g}}>{{g}}</li>
            ))}}
          </ul>
        </article>
        <article className="rounded-xl border bg-card p-5 shadow-sm">
          <h2 className="text-sm font-semibold">Features</h2>
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm">
            {{features.map((f) => (
              <li key={{f}}>{{f}}</li>
            ))}}
          </ul>
        </article>
      </section>

      <section className="mt-10">
        <h2 className="text-sm font-semibold">User flow</h2>
        <ol className="mt-3 space-y-2">
          {{flow.map((item, i) => (
            <li key={{i}}>
              <span className="text-xs text-muted-foreground">Step {{i + 1}}</span>
              <span className="ml-2 text-sm font-medium">{{item}}</span>
            </li>
          ))}}
        </ol>
      </section>

      <ErrorBoundary>
        <UploadCard />
        <ResultPanel />
      </ErrorBoundary>
    </main>
  );
}}
"""
    return GeneratedFile(
        path="app/page.tsx",
        content=content,
        purpose="Top-level page rendered at route `/`.",
    )


def _app_globals() -> GeneratedFile:
    return GeneratedFile(
        path="app/globals.css",
        content="""@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --background: #ffffff;
  --foreground: #0a0a0a;
}

@media (prefers-color-scheme: dark) {
  :root {
    --background: #0a0a0a;
    --foreground: #fafafa;
  }
}

body {
  background: var(--background);
  color: var(--foreground);
}
""",
        purpose="Global CSS with Tailwind directives.",
    )


def _api_health_route() -> GeneratedFile:
    return GeneratedFile(
        path="app/api/health/route.ts",
        content="""import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json({ status: "ok" });
}
""",
        purpose="Health endpoint used by Playwright webServer readiness checks.",
    )


def _api_predict_route() -> GeneratedFile:
    content = """import { NextResponse } from "next/server";

import { runPrediction, type PredictionInput } from "@/lib/adapter";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  let body: PredictionInput;
  try {
    body = (await request.json()) as PredictionInput;
  } catch {
    return NextResponse.json(
      { error: "Invalid JSON body" },
      { status: 400 },
    );
  }

  try {
    const result = await runPrediction(body);
    return NextResponse.json(result);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Prediction failed";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
"""
    return GeneratedFile(
        path="app/api/predict/route.ts",
        content=content,
        purpose="Prediction endpoint delegating to the adapter.",
    )


def _lib_adapter(plan: ProductPlan, repo_path: str | None) -> GeneratedFile:
    product_name = plan.prd.product_name or "PaperPilot Product"
    repo_hint = repo_path or "the original repository"
    content = f"""import {{ PredictionInput, PredictionResult }} from "./types";

/**
 * Mock-first adapter — PaperPilot generates a working mock of the paper's
 * core capability by default. Replace this file with the real inference
 * code when integrating with {repo_hint}.
 *
 * The contract requires `real_adapter_required: true` and
 * `mock_fallback_allowed: true`. While the mock is active, the UI must
 * clearly mark outputs as mock results; do not present them as real model
 * output.
 */

const MOCK_MODE = process.env.PAPERPILOT_MOCK_MODE !== "false";

export async function runPrediction(input: PredictionInput): Promise<PredictionResult> {{
  if (MOCK_MODE) {{
    // Deterministic mock: hash the input to fake a confidence score.
    const text = JSON.stringify(input);
    let hash = 0;
    for (let i = 0; i < text.length; i++) {{
      hash = ((hash << 5) - hash + text.charCodeAt(i)) | 0;
    }}
    const confidence = Math.abs(hash % 100) / 100;
    return {{
      ok: true,
      mode: "mock",
      productName: "{product_name}",
      summary: "Mock prediction generated by PaperPilot.",
      confidence,
      data: {{ input }},
    }};
  }}

  // Real adapter path — wire up the actual model here.
  throw new Error("Real adapter not yet implemented. Set PAPERPILOT_MOCK_MODE=true.");
}}
"""
    return GeneratedFile(
        path="lib/adapter.ts",
        content=content,
        purpose="Adapter contract with mock-first default and real-adapter extension point.",
    )


def _lib_types() -> GeneratedFile:
    return GeneratedFile(
        path="lib/types.ts",
        content="""export type PredictionInput = {
  // Adjust based on the paper's input modality (image | text | video | file).
  payload: unknown;
  metadata?: Record<string, string>;
};

export type PredictionResult = {
  ok: boolean;
  mode: "mock" | "real";
  productName: string;
  summary: string;
  confidence?: number;
  data?: unknown;
};
""",
        purpose="Shared TypeScript types for the prediction contract.",
    )


def _components_upload_card() -> GeneratedFile:
    return GeneratedFile(
        path="components/UploadCard.tsx",
        content="""\"use client\";

import { useState } from "react";

import { runPrediction } from "@/lib/adapter";

export function UploadCard() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onPredict() {
    setBusy(true);
    setError(null);
    try {
      await runPrediction({ payload: { demo: true } });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Prediction failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mt-10 rounded-xl border bg-card p-5 shadow-sm">
      <h2 className="text-sm font-semibold">Input</h2>
      <p className="mt-2 text-xs text-muted-foreground">
        Upload or select input for the mock prediction.
      </p>
      <button
        type="button"
        onClick={onPredict}
        disabled={busy}
        className="mt-4 rounded-md bg-foreground px-4 py-2 text-sm font-medium text-background disabled:opacity-50"
      >
        {busy ? "Running…" : "Run prediction"}
      </button>
      {error ? (
        <p className="mt-3 text-xs text-red-500" role="alert">
          {error}
        </p>
      ) : null}
    </section>
  );
}
""",
        purpose="Client component collecting input and invoking the adapter.",
    )


def _components_result_panel() -> GeneratedFile:
    return GeneratedFile(
        path="components/ResultPanel.tsx",
        content="""\"use client\";

export function ResultPanel() {
  return (
    <section
      data-testid="result-panel"
      className="mt-6 rounded-xl border bg-card p-5 text-sm text-muted-foreground shadow-sm"
    >
      Waiting for prediction results.
    </section>
  );
}
""",
        purpose="Client component displaying prediction results.",
    )


def _components_error_boundary() -> GeneratedFile:
    return GeneratedFile(
        path="components/ErrorBoundary.tsx",
        content="""\"use client\";

import { Component, type ReactNode } from "react";

type Props = { children: ReactNode };
type State = { hasError: boolean; message: string | null };

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div role="alert" className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {this.state.message ?? "Something went wrong."}
        </div>
      );
    }
    return this.props.children;
  }
}
""",
        purpose="Catches render-time errors in the prediction flow.",
    )


def _tests_e2e_product_spec() -> GeneratedFile:
    return GeneratedFile(
        path="tests/e2e/product.spec.ts",
        content="""import { expect, test } from "@playwright/test";

test("primary workflow can complete", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: /paper|research|demo/i }),
  ).toBeVisible();

  const primaryAction = page.getByRole("button", {
    name: /run|analyze|generate|predict/i,
  });
  await expect(primaryAction).toBeEnabled();
  await primaryAction.click();

  await expect(
    page.getByTestId("result-panel"),
  ).toBeVisible({ timeout: 30_000 });

  await expect(page.locator("body")).not.toContainText(
    /uncaught|internal server error|cannot read properties/i,
  );
});
""",
        purpose="Playwright E2E test for the primary workflow.",
    )


def _tests_unit_predict_spec() -> GeneratedFile:
    return GeneratedFile(
        path="tests/unit/predict.spec.ts",
        content="""import { describe, expect, it } from "vitest";

import { runPrediction } from "@/lib/adapter";

describe("runPrediction (mock)", () => {
  it("returns a mock result when PAPERPILOT_MOCK_MODE is true", async () => {
    process.env.PAPERPILOT_MOCK_MODE = "true";
    const result = await runPrediction({ payload: { demo: true } });
    expect(result.ok).toBe(true);
    expect(result.mode).toBe("mock");
  });
});
""",
        purpose="Vitest unit test for the mock adapter path.",
    )


def _readme(plan: ProductPlan, repo_path: str | None) -> GeneratedFile:
    product_name = plan.prd.product_name or "PaperPilot Product"
    repo_hint = repo_path or "the original repository"
    content = f"""# {product_name}

Generated by **PaperPilot Productize Mode**. This is a real Next.js 14
application following the App Router convention. It is **mock-first by
default**: the adapter at `lib/adapter.ts` returns a deterministic mock
prediction, and the UI marks outputs as mock results.

## Quick start

```bash
npm install
npm run dev
# open http://127.0.0.1:3000
```

## Scripts

- `npm run dev` — start Next.js in development mode (HMR)
- `npm run build` — production build
- `npm start` — start the production server
- `npm test` — run unit tests (Vitest)
- `npm run test:e2e` — run E2E tests (Playwright)
- `npm run lint` — run ESLint via Next.js

## Architecture

- `app/` — Next.js App Router pages, layouts, and API routes
- `app/api/health/route.ts` — health endpoint for Playwright readiness
- `app/api/predict/route.ts` — prediction endpoint delegating to the adapter
- `components/` — React components for the upload card, result panel, etc.
- `lib/adapter.ts` — **mock-first adapter**; replace with real inference
- `lib/types.ts` — shared TypeScript types for the prediction contract
- `tests/e2e/product.spec.ts` — Playwright E2E test for the primary workflow
- `tests/unit/predict.spec.ts` — Vitest unit test for the mock adapter

## Real model integration

To connect the real model from {repo_hint}:

1. Set `PAPERPILOT_MOCK_MODE=false` in `.env.local`.
2. Update `lib/adapter.ts` to call the real inference code.
3. Review dependencies, inputs, checkpoints, and outputs manually.
4. Run `npm test && npm run test:e2e` before merging.

## Limitations

This generated product is a prototype. It does not guarantee full
reproduction of the original paper results, and it never downloads
weights, trains models, or executes repository scripts automatically.

## Contract

The bundle is governed by `AppContract`:

- `runtime`: `nextjs`
- `package_manager`: `npm`
- `required_scripts`: dev, build, start, test, test:e2e, lint
- `required_routes`: `/`, `/result`
- `required_api_routes`: `/api/health`, `/api/predict`
- `real_adapter_required`: `true`
- `mock_fallback_allowed`: `true`
"""
    return GeneratedFile(
        path="README.md",
        content=content,
        purpose="Top-level README documenting the generated app.",
    )


def generate_nextjs_app(
    plan: ProductPlan,
    destination: Any | str,
    repo_path: str | None = None,
) -> dict:
    """Build the contract bundle and write it to ``destination``.

    Returns the manifest produced by ``write_bundle``.
    """
    from productize.next_app_writer import write_bundle as _write

    bundle = build_bundle(plan, repo_path=repo_path)
    return _write(bundle, Path(destination))
