# Workbench Functional Core Design

## Goal

Turn the reference-aligned Workbench into a real end-to-end operating surface
for the existing PaperPilot backend. A user must be able to create a run,
observe actual pipeline progress, review a concrete action, execute or reject
it safely, and inspect the resulting output without encountering controls that
only simulate success.

## Scope

This phase implements the core flow:

1. Upload a PDF and save or test the LLM configuration.
2. Create a real reproduce or productize run.
3. Poll real run state, events, graph data, actions, artifacts, and files.
4. Review, edit, approve, or reject a concrete command or patch action.
5. Execute an approved action through the existing safety services.
6. Display real command, patch, run, and artifact results.

State remains in the current in-memory backend stores. Persistence across
backend restarts is explicitly deferred.

## Approaches Considered

### Frontend-Orchestrated Execution

The frontend could approve an action and then call command or patch endpoints
itself. This is quick, but approval and execution can diverge if one request
succeeds and the next fails. It also duplicates action-routing policy in the
browser.

### Backend-Orchestrated Execution

The selected approach adds one backend execution boundary for reviewed
actions. The backend owns action validation, safety review, dispatch, result
recording, and event emission. The frontend makes one intent-level request and
then refreshes authoritative state.

### Persistent Workflow Engine

A database-backed job and approval state machine would provide durable
recovery and stronger concurrency guarantees. It is valuable, but too broad
for this phase and unnecessary to establish the first functional core loop.

## Backend Design

### Real Action Creation

New real runs must not be seeded with `build_mock_actions()`. Mock actions
remain available only from the explicit `/api/workbench/mock` preview route.

When a pipeline finishes with an executable `run.sh`, generated command, or
patch proposal, the run service creates a pending `ActionRequest` from that
actual output. The action records its concrete command or patch identifier,
working directory, risk classification, and reason. Runs without an actionable
output expose no pending approval.

`ActionRequest` gains structured execution metadata instead of requiring the
frontend to parse a display command. Command actions carry `command`, `cwd`,
and execution mode. Patch actions carry `patch_id` and path.

### Approval And Execution

The backend exposes an intent-level execution endpoint for an action. It
accepts only actions in `pending` or `edited` state.

- A command action is reviewed and executed through `CommandService` and the
  existing command-runner policy.
- A patch action is applied through `PatchService`, which enforces generated
  code roots.
- A blocked safety review returns a recorded, non-executed result.
- A rejected action cannot execute.
- An edited action stores the new command and remains reviewable; editing never
  executes anything. The user must approve it again.
- Repeated execution requests return the recorded outcome and do not execute
  the same action twice.

Execution updates the action state and emits run-scoped events for approval,
start, success, failure, or policy blocking. Command and patch results remain
available from their existing result services.

### Error Semantics

Validation and policy blocks return explicit 4xx responses. Runtime failures
are recorded as execution results and events with stderr or a bounded error
message. Approval status is never presented as execution success.

## Frontend Design

### Core Run Flow

`WorkspaceShell` remains the coordinator. After run creation it polls the real
run, event, graph, action, result, file, and artifact APIs. Once a run exists,
mock workflow nodes, events, actions, and output are not mixed into that run.

The approval overlay renders only an actual backend action. Approve calls the
new action execution API, Reject calls the existing rejection API, and Edit
opens an editable command form and saves without execution. All actions show a
busy state and disable duplicate submissions.

After approval or rejection, the shell refreshes actions, events, command or
patch results, files, artifacts, and run status. Terminal and Results display
real stdout, stderr, exit code, blocked reason, patch status, and pipeline
summary.

### Honest Interface

Controls without a backend capability are removed from the active workbench:

- Hide Chat until an agent-chat API exists.
- Hide message and split-run menu buttons that have no behavior.
- Remove fake evaluation mutation commands; evaluation remains read-only.
- Keep console tab switching and clearing because those are complete local UI
  behaviors, but do not label local pause as pausing backend execution.
- Keep project navigation only where it changes a real view or opens a real
  workflow.

The offline state may show a clearly labeled preview, but it must not claim a
run, action, or execution succeeded. Starting a real operation while the API is
unavailable produces an actionable connection error.

## Data Flow

1. The run drawer uploads the PDF and submits `POST /api/runs`.
2. The shell stores the returned run ID and polls authoritative run resources.
3. The pipeline stores outputs and creates an action only from actionable real
   output.
4. The inspector and approval overlay present the same run-scoped backend data.
5. The user edits, rejects, or approves the action.
6. The backend validates and dispatches the approved action exactly once.
7. The frontend refreshes results and presents the recorded outcome.

## Safety

No browser code executes commands or writes files. Command working directories
and patch paths continue through existing allow-list resolution. Editing a
command cannot bypass a second safety review. Duplicate clicks, stale action
state, and rejected actions cannot trigger execution.

## Testing

Backend tests cover:

- Real runs are not seeded with mock actions.
- Actual pipeline output creates the correct action metadata.
- Command approval executes through the policy service and records output.
- Patch approval applies only a known proposal in an allowed root.
- Reject never executes.
- Edit requires a later approval.
- Duplicate execution is idempotent.
- Blocked and failed execution remain distinguishable from success.

Frontend tests cover:

- A real pending action is rendered without preview substitution.
- Approve invokes execution and refreshes authoritative resources.
- Edit changes the command but does not execute it.
- Reject removes the pending approval and displays the rejected state.
- Terminal and Results render actual execution fields.
- Unimplemented controls are absent.
- API failure is reported without simulated success.

Final verification includes the full Python suite, frontend unit tests,
TypeScript, lint, production build, and a browser walkthrough of the complete
run-to-result flow.

## Non-Goals

- Persistence across backend restarts.
- Multi-user authentication or authorization.
- A general-purpose remote shell.
- Live agent chat.
- Background job recovery after process termination.
- Replacing the existing command and patch safety policies.
