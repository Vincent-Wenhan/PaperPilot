# UI API Configuration — Design Document

> 2026-06-10

## Problem

Users currently configure LLM API credentials via environment variables (`LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_MOCK_MODE`). This requires manual `export` before launching the app, which is inconvenient, especially for non-technical users and classroom demos. The goal is to move this configuration into the Streamlit UI so users can type or paste values directly in the browser.

## Design

Add a collapsible configuration section in the Streamlit **sidebar** where users can set:

| Field | Component | Default | Notes |
|---|---|---|---|
| API Key | `text_input` (password mode) | empty | Hidden while typing |
| Base URL | `text_input` | `https://api.openai.com/v1` | Common OpenAI-compatible endpoint |
| Model | `text_input` | `gpt-4o-mini` | Any model name |
| Mock Mode | `toggle` | `True` | When on, LLM calls return fixed text |

Values are stored in `st.session_state` and passed to `LLMClient` at construction time.

## Data Flow

```
Sidebar Input → st.session_state["llm_api_key"]
                                   ["llm_base_url"]
                                   ["llm_model"]
                                   ["llm_mock_mode"]
                                        ↓
                           LLMClient.__init__(session_state)
                                        ↓
                           OpenAI-compatible Chat Completions API
```

- `LLMClient` receives config at instantiation, not from global env vars
- If a field is empty in session state, `LLMClient` falls back to environment variable (then to hardcoded default)
- Mock mode toggle is checked first — when on, no API call is made regardless of other fields

## Files to Change

### `app.py`
- Add `st.sidebar` section at the top
- Initialize session state defaults from `config.py` constants
- Render input fields and store back to session state on change

### `tools/llm_client.py`
- `__init__()` now accepts optional kwargs: `api_key`, `base_url`, `model`, `mock_mode`
- Constructor reads from kwargs first, then from env vars (`os.getenv`), then from hardcoded defaults
- Remove `from config import ...` — config is injected, not imported

### `main.py`
- `run_paperpilot()` no longer creates `LLMClient()` internally — instead, caller passes it in
- Callers in `app.py` build `LLMClient` from session state and pass to `run_paperpilot()`

### `agents/__init__.py` (or wherever agents are instantiated)
- Debug Agent in `app.py` is created with `LLMClient()` — this also needs to pass config

No changes to `config.py` — it remains as the env var fallback source and module-level default reference.

## Caller Changes in Detail

The key structural change: `LLMClient` construction moves from inside `main.py` (where it exists in `run_paperpilot`) to `app.py`, so session state is accessible.

In `app.py`, helper function:
```python
def _get_llm_client() -> LLMClient:
    return LLMClient(
        api_key=st.session_state.get("llm_api_key"),
        base_url=st.session_state.get("llm_base_url"),
        model=st.session_state.get("llm_model"),
        mock_mode=st.session_state.get("llm_mock_mode", True),
    )
```

Then:
- `run_paperpilot(llm_client=..., ...)` — passes the client through
- `DebugAgent(_get_llm_client())` — debug section also uses it

## Non-Goals

- No persistence of API keys (no file write, no remembering across sessions)
- No validation of API key format or connectivity test on input
- No per-user or per-session isolation beyond Streamlit's built-in session state
- The config remains read-once at agent creation time; changing sidebar values mid-pipeline has no effect until next Analyze click

## Verification

1. Launch with `streamlit run app.py` (no env vars set), confirm sidebar shows defaults
2. Fill in a real API key, toggle Mock Mode off, run a pipeline — confirm LLM call goes through
3. Leave API key empty, toggle Mock Mode on — confirm pipeline runs without error
4. Toggle Mock Mode off with empty key — confirm clear error message in agent output
