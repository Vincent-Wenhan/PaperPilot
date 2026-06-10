"""Structured mock outputs for Productize Mode course demonstrations."""

PRODUCT_OPPORTUNITY_MOCK = """# Product Opportunities

## Technical Capability
The analyzed research method can be wrapped as a bounded file-analysis
workflow. Real inputs and outputs require repository-specific verification.

## Suitable Scenarios
- Guided research demo
- Educational analysis assistant
- Small-scale result exploration

## Unsuitable Scenarios
- Safety-critical automated decisions
- Unreviewed production inference
- Claims of reproducing paper metrics

## Product Ideas

| Product idea | User value | Feasibility | Demo effect | Paper fit | Difficulty | Safety risk | Score |
|---|---:|---:|---:|---:|---:|---:|---:|
| Interactive research analyzer | 8 | 9 | 8 | 9 | 4 | 2 | 8.5 |
| Method comparison assistant | 7 | 8 | 7 | 8 | 5 | 2 | 7.5 |
| Experiment report explainer | 7 | 9 | 7 | 7 | 3 | 2 | 7.8 |

## Recommended MVP
Interactive research analyzer.

## Recommendation Reason
It has a clear input-to-result flow, fits a Streamlit course demo, and can be
shown safely with a mock adapter until the real inference API is verified.
"""

PRODUCT_DESIGNER_MOCK = """# Product Specification

## Product Name
Interactive Research Analyzer

## One-line Description
Upload or enter one research input and receive a structured demonstration of
the paper technology through a unified adapter.

## Target User
Machine learning learners and course reviewers.

## User Problem
Research repositories are difficult to present as a simple application.

## Core Features
- Accept one template-specific input
- Run a mock-first ModelAdapter
- Display and download structured results

## User Flow
Provide input, click Analyze, review the result, and download JSON.

## Input and Output
The selected template defines the input. Output is structured JSON plus a
human-readable result panel.

## Page Design
A single-page Streamlit interface with instructions, input, action, and result.

## MVP Boundary
No training, weight download, arbitrary script execution, or guaranteed real
model integration.

## Future Extensions
Add a manually reviewed repository-specific inference bridge.

## Risks and Limitations
Mock results are demonstrations and are not predictions from the paper model.
"""

TECH_ADAPTER_MOCK = """# ModelAdapter Plan

## Candidate Integration Evidence
Repository entry points, checkpoint locations, and exact call signatures are
not assumed until a human verifies them.

## Unified Interface
Use `setup()`, `load_model()`, and `predict(input_data)`.

## Real Integration Status
Uncertain. Do not invent repository functions or execute scripts automatically.

## Mock Fallback
Keep `mock_mode=True` by default and return a deterministic result matching the
selected image, text, video, or file template.

## Manual Information Required
Confirm dependencies, preprocessing, checkpoint path, inference entry point,
device behavior, and output conversion.
"""

FRONTEND_BUILDER_MOCK = """# Streamlit Frontend Plan

## Page Title
Generated Product Prototype

## Layout
Instructions, input panel, primary action, result panel, and download control.

## Input Components
Use the selected template's image uploader, text area, video uploader, or
generic file uploader.

## Action
One explicit Run Model or Analyze button.

## Result and Download
Display structured JSON and provide a JSON download button.

## Errors and Guidance
Catch adapter errors with `st.error` and explain that mock mode is enabled.
"""

PRODUCT_TEST_MOCK = """# Product Prototype Test Report

## File Completeness
Review `app.py`, `adapter.py`, `README.md`, `product_spec.md`,
`requirements.txt`, and `outputs/` using the deterministic inspection result.

## Mock Mode
The generated adapter defaults to mock mode and is sufficient to demonstrate
the product interaction.

## Run Instructions
Install requirements and run `streamlit run app.py` inside the generated
product directory.

## Safety Review
The prototype does not train, download weights, or execute source-repository
scripts automatically.

## Next Step
Resolve any deterministic inspection notes before manually implementing real
model integration.
"""
