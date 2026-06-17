# Streamlit UI Rules

Use Streamlit to build a compact working tool, not a landing page. The first
screen should make the user's task, inputs, primary action, result area, and
safety boundary immediately clear.

## Generated Product UI

- Use a product-specific title from the PRD or selected proposal.
- Put runtime controls in the sidebar: mock mode, threshold or mode selector,
  and output detail when applicable.
- Use domain-specific inputs. Avoid generic labels such as "Input" when a more
  precise label is available.
- Treat `PrototypePlan.user_inputs`, `system_outputs`, `page_structure`, and
  `mock_result` as implementation-facing fields. They should be short, concrete,
  and suitable for direct display in the generated Streamlit app.
- Show the primary action once and keep it close to the main input.
- Present results in tabs or clear sections: summary, evidence/limits, and
  export.
- Include status metrics when they clarify the output, such as mode, threshold,
  confidence, file count, or selected workflow.
- Provide downloadable JSON for structured outputs.
- Show limitations as product constraints, not apologetic filler.
- Keep custom CSS restrained: readable spacing, 8px-or-less radii, neutral
  panels, no decorative gradient blobs.
- Never make raw JSON the only visible result.

## PaperPilot Host UI

- Prefer concise summaries before detailed JSON.
- Show generated output directories and exact run commands.
- Keep capability cards, composition, PRD/MVP, prototype plan, generated files,
  and evaluation separate.
- Surface deterministic inspection status and generated-code quality checks.
- Never launch generated products or execute analyzed repositories
  automatically.
