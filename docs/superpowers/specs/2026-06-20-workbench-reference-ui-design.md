# Workbench Reference UI Design

## Goal

Upgrade the existing Next.js PaperPilot Workbench to match the supplied
reference interface while preserving the current FastAPI contracts, mock-data
fallback, and legacy Streamlit application.

## Scope

This change is a focused frontend redesign under `frontend/`. It reorganizes
the existing workbench into a dense research-agent IDE with global navigation,
workflow monitoring, code inspection, logs, and human approval. It does not
change backend endpoints, pipeline behavior, safety policy, or the Streamlit
entry point.

## Chosen Approach

Use a structural layout rewrite while reusing existing capabilities. Existing
API adapters, mock data, status semantics, React Flow graph behavior, and
approval content remain the data foundation. Components and CSS are reshaped
around the reference layout instead of attempting to force the current card
grid into place with CSS alone.

## Information Architecture

The viewport is divided into five coordinated regions:

1. A fixed left rail contains PaperPilot branding, primary navigation,
   settings, usage, and user identity.
2. A top context bar contains project breadcrumbs, mode selection, run status,
   messages, and the primary New Run command.
3. A main tab strip exposes Workflow, Chat, Evaluation, and Product Design.
4. The default Workflow surface contains the graph, activity stream, and a
   bottom console with Logs, Terminal, Results, and Metrics.
5. A right inspector contains Artifacts, Code, Diff, Runner, and Tool Calls.
   Human approval appears as a floating panel anchored over the lower-right
   workspace so it remains visible without consuming a permanent column.

## Components

### Workspace Shell

`WorkspaceShell` remains responsible for loading the active run snapshot and
events. It composes navigation, context header, workspace tabs, workflow area,
console, inspector, and approval overlay. UI-only state such as active tabs is
local and does not alter API state.

### Navigation

The left rail uses familiar Lucide icons and compact text labels for Projects,
Papers, Repos, Runs, Agents, and Settings. Projects is selected by default.
Usage and user controls are anchored to the bottom on desktop. On narrow
screens the rail becomes a compact horizontal/navigation region rather than
forcing a desktop-width sidebar.

### Workflow Surface

The existing React Flow implementation remains interactive. Nodes are rendered
as compact status cards with explicit success, running, review, and pending
states. The workflow occupies the upper central area, followed by a concise
activity table sourced from the existing event stream.

### Inspector

The inspector switches to a horizontal tab bar. The Code tab is the default to
match the reference and uses a file navigator beside a code viewer. Existing
artifact, diff, runner, and tool-call content remains reachable through tabs.
The file navigator may present a flat API file list with visual hierarchy
derived from paths; no backend tree contract is introduced.

### Console

The bottom console provides Logs, Terminal, Results, and Metrics tabs. Logs are
shown by default and use compact timestamp, level, and message rows. Console
controls expose live status, pause, and clear as local demo interactions.

### Approval Overlay

The approval panel summarizes the pending command, modification scope, and
reason. Approve, Edit, and Reject remain explicit commands. In this frontend
pass they retain the current mock/read-only behavior; no command is executed
and no patch is applied implicitly.

## Data Flow

On mount, the shell requests the workbench snapshot. The inspector separately
requests artifacts and files, then requests content for the selected file. Any
request failure keeps the local mock content visible. This preserves the
documented offline demo behavior and avoids adding a new loading dependency.

## Visual System

The interface uses white and neutral gray surfaces with blue as the primary
action and selection color. Green, amber, and red are reserved for semantic
status. Borders are subtle, shadows are limited to the floating approval
panel, card radii remain at or below 8px, and dense workspace typography stays
within compact panel proportions. Controls use Lucide icons with titles or
accessible labels where their meaning is not obvious.

## Responsive Behavior

Desktop uses the full left rail, central workspace, and right inspector. At
medium widths the inspector moves below the workflow while retaining its tab
structure. At mobile widths all regions become a single column, navigation and
top actions wrap deliberately, graph and code areas keep stable minimum
heights, and no button or label may overlap neighboring content.

## Testing And Verification

Frontend tests will cover the presence of the five main regions, default active
tabs, API fallback behavior where practical, and tab switching. Implementation
will follow test-first red/green cycles. Final verification requires the full
frontend test command, lint/type checks supported by the repository, a
production Next.js build, and browser inspection at desktop and mobile
viewports with the development server running.

## Non-Goals

- Changing FastAPI schemas or endpoint behavior.
- Connecting the Workbench to live pipeline execution.
- Executing approvals, commands, or patches from the redesigned controls.
- Replacing or removing the Streamlit application.
- Introducing a new design system or state-management dependency.
