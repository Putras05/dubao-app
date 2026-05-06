# PLAN — Trợ lý AI v2 Upgrade (ChatGPT/Gemini-tier)

## Goal

Bring the "Trợ lý AI" page to ChatGPT/Gemini-grade UX while keeping the navy-blue theme, the existing math rendering pipeline (`_md_to_html` → 57/57 tests), and the existing per-session chat history. Add streaming, native Gemini function calling against app data, transparent tool-call display, stop / copy / regenerate, and auto-rendered Plotly charts inline.

## Architecture (additive — minimal disruption)

```
app_pages/chatbot.py              ── UI (rewires pipeline, keeps math/render code intact)
core/chatbot_ai.py                ── EXISTING: legacy Gemini wrapper (kept as fallback path)
core/chatbot_groq.py              ── EXISTING: Groq fallback (untouched)
core/chatbot_logic.py             ── EXISTING: legacy retry chain (still wired for Groq)
core/chatbot_cache.py             ── EXISTING: cache (untouched)
core/chatbot_rules.py             ── EXISTING: rule answers (untouched)
core/chat_history.py              ── EXISTING: persistence (untouched)

NEW:
core/chatbot_tools.py             ── Gemini-callable Python tools (data + chart)
core/chatbot_stream.py            ── new google-genai client w/ function calling + streaming
                                     uses generate_content_stream + automatic function calling
                                     gracefully falls back to non-streaming `ask_gemini` then Groq
```

## Tool functions (`core/chatbot_tools.py`)

The following functions are exposed to Gemini. The SDK introspects each function's docstring + type hints and builds the schema automatically.

1. `get_current_ticker_data()` → dict
   The ticker, last close (VND), session % return, last trading date, daily/annualized vol, train ratio, AR order, date range from sidebar.
2. `get_forecast_results()` → dict
   AR / MLR / CART next-session forecast in VND + MAPE/RMSE/MAE/R²adj on the test set.
3. `get_technical_signals()` → dict
   Ichimoku 4-tier signal label, score [-5..+5], primary trend, TK cross, Chikou, future Kumo. Plus RSI14, MA5/20/50.
4. `get_price_history(days)` → list of {date, open, high, low, close, volume} for the latest N sessions (capped 60).
5. `get_portfolio()` → dict — placeholder, returns empty if user hasn't configured a portfolio yet.
6. `compute_metric(metric_name, model)` → number — fetch a single MAPE/RMSE/MAE/R²adj for ar|mlr|cart on the test set.
7. `plot_price_chart(days, with_ma)` → registered chart key — stores a Plotly figure in session state, returns a placeholder so the UI can render it inline next to the assistant message.
8. `switch_ticker(ticker)` → dict — switches the in-memory data context for this turn (bot can answer for FPT/HPG/VNM regardless of current sidebar selection).

The active app state (df, r1..r3, m1..m3, sidebar args) is set once at the top of `render()` via `chatbot_tools.set_app_state(...)`. Tools read from a thread-local-style module global so the SDK can call them without us having to thread arguments through.

## Streaming + function calling client (`core/chatbot_stream.py`)

Public API:

```python
def stream_answer(query: str, history: list, lang: str) -> Iterator[Event]
```

Yields events:

* `{'type': 'text', 'delta': '...'}` — token chunk
* `{'type': 'tool_call', 'name': 'get_forecast_results', 'args': {...}}`
* `{'type': 'tool_result', 'name': '...', 'value': {...}}`
* `{'type': 'done'}`
* `{'type': 'error', 'message': '...'}`

Implementation:

1. Build `tools=[fn1, fn2, ...]` from `chatbot_tools.AVAILABLE_TOOLS`.
2. Configure `GenerateContentConfig` with: `system_instruction=<v8 prompt>`, `tools=…`, `automatic_function_calling=AutomaticFunctionCallingConfig(disable=False)`.
3. Call `client.models.generate_content_stream(model='gemini-2.0-flash', contents=…, config=…)`.
4. Iterate response chunks. For each chunk's `parts`:
   * `text` parts → yield `text` event
   * `function_call` parts → yield `tool_call` event (the SDK auto-executes Python tool, but we still surface the name to the UI for transparency)
   * `function_response` parts (after auto-exec) → yield `tool_result`
5. On any failure (rate-limit, quota, network) → yield `error`. Caller decides how to fall back.

History conversion: list of `{'role':'user'|'assistant','content':'...'}` → list of `types.Content(role='user'|'model', parts=[types.Part.from_text(text=…)])`.

If the new SDK call raises (e.g. wrong package version), the page falls through to the existing `_process_query` legacy path → user still gets an answer.

## UI changes (`app_pages/chatbot.py`)

What stays:

* Sidebar history list / search / new conversation
* Bubble layout, math rendering pipeline (`_md_to_html`, `_looks_like_math`, KaTeX injection)
* Welcome card + 4 suggested chips (auto-hide after 1st user msg — already does)
* Search-in-conversation, copy & regenerate buttons, sticky sidebar, navy theme

What changes:

* When the user submits, instead of calling `_process_query` synchronously and rerunning, we use `st.write_stream` over `stream_answer(...)` *inside* a freshly-rendered bot bubble:
  * A `st.empty()` placeholder is created for the bot bubble.
  * As text events arrive, the placeholder updates with `_md_to_html(buffered_text)`.
  * Tool-call events are collected; on `tool_result` we render a small expander labelled `🔧 Đã sử dụng dữ liệu: <fn>(args)`.
  * After `done`, the final text is committed to history.
* If any chart key was registered by `plot_price_chart`, render that figure right above the message text via `st.plotly_chart`.
* Stop button: a `st.button('⏹')` next to the input. Sets `st.session_state['_chat_stop'] = True`; the streaming generator polls this flag every chunk and breaks early.
* On error event → fallback to legacy `_process_query` for that turn (keeps Gemini-down resilience).
* `chat_history.add_message` is called once at the end with the FINAL text (not per-token).

## Memory / context truncation

`stream_answer` accepts `history`. We pass the last 12 messages (≈6 turns) of the active conversation. Each message > 1500 chars truncated. The `system_instruction` already covers persona + math rules.

## Error handling

* Missing `GEMINI_API_KEY` AND missing `GROQ_API_KEY` → friendly banner with secrets.toml setup instructions.
* Streaming exception → caught in the stream wrapper → emits `error` event → UI falls back to the legacy synchronous chain (`_process_query`) for the current message.
* Empty / whitespace input → blocked at `chat_input` callback with no API call.
* Rate-limit during stream → graceful "đợi vài giây" message, then UI lets user retry.

## Files added / modified

| Status | Path |
|---|---|
| ADD | `core/chatbot_tools.py` |
| ADD | `core/chatbot_stream.py` |
| ADD | `PLAN.md` |
| ADD | `CHANGELOG.md` |
| MODIFY | `app_pages/chatbot.py` (small: replace synchronous answer block with streaming block; add plot rendering) |
| TOUCH | `requirements.txt` (add nothing; google-genai already present) |

No other page is modified. The math rendering pipeline is untouched. The existing `chatbot_logic._process_query` keeps working as the universal fallback.

## DOD self-test plan

1. `python _test_chatbot_render.py` → 57/57 PASS.
2. `python -c "import app_pages.chatbot, app_pages.dashboard, app_pages.analysis, app_pages.history, app_pages.signals, app_pages.portfolio, app_pages.guide"` → no import error.
3. `python -c "from core import chatbot_tools, chatbot_stream"` → no import error.
4. Manual sanity: with stub `set_app_state` populated, tools return JSON-serializable dicts.

## Risks & mitigations

* **SDK schema mismatch** — `google-genai` is fast-moving. Mitigation: stream wrapper catches any `AttributeError` / `TypeError` at construction and falls back to `chatbot_ai.ask_gemini`, which is known-good. Streaming becomes "fake stream" (post-hoc word-by-word) when this happens.
* **Auto function calling looping** — cap at 6 hops via SDK config; if exceeded we abort and emit final text.
* **Plotly figure size in chat** — we render with `use_container_width=True` and `height=320` for compact display; default plotly toolbar disabled.
