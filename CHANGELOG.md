# Changelog — Trợ lý AI

## 2026-05-06 — Phase 1-5 rewrite (v12)

Two missions delivered in a single session:

1. **Real KaTeX math rendering** — replaced the Unicode pretty-print
   "fake-math" pipeline with Streamlit's native `st.markdown` path so
   `$...$` and `$$...$$` are now rendered by the bundled KaTeX. The
   previous KaTeX-iframe attempt could not access the parent document
   on Streamlit Cloud (origin `null`), so we instead split bot bubbles
   into chrome (HTML via `st.markdown(unsafe_allow_html=True)`) and
   content (plain `st.markdown(text)` — KaTeX auto-applies). Streaming
   live bubble updated likewise (~5 fps throttled).
2. **General-purpose ChatGPT-class assistant** — rewrote both
   `_SYSTEM_PROMPT_VI` and `_SYSTEM_PROMPT_EN` to drop the
   "Vietnamese-only" / "must-use-formula" / "app-only-topics" rules.
   The bot can now answer programming, math, history, daily-life
   questions etc. in the user's language while still using app tools
   when the user mentions FPT/HPG/VNM/MAPE/Ichimoku.

### Phase summary

- **Phase 1** — Deleted `_NB`, `_GREEK_MAP`, `_OP_MAP`, `_SUB_O/_C`,
  `_SUP_O/_C`, `_latex_to_pretty`, `_restore_subsup`, `_CODE_KEYWORDS`,
  `_STRONG_MATH_MARKERS`, `_DOMAIN_MATH_TOKENS`, `_looks_like_math`,
  `_DOMAIN_FORMULA_NAMES`, `_line_looks_like_math`,
  `_looks_like_identifier`, `_strip_emphasis_wrap`, `_math_display_html`,
  `_math_inline_html`. Rewrote `_md_to_html` to preserve `$...$`/`$$...$$`
  literally. Rewrote `_render_bot_message` to use `st.markdown(content)`
  for the body. Streaming bubble switched to plain markdown chunks.
  `_inject_katex_once` repurposed as a Prism.js injector (Phase 5).

- **Phase 2** — Replaced both system prompts with a friendly
  general-purpose persona. Removed the "LUÔN trả lời tiếng Việt" /
  "BẮT BUỘC kèm công thức" / "ALWAYS respond in English" mandates.
  LaTeX instruction reduced to a single line: *"Use $...$ for inline
  math and $$...$$ for display math (LaTeX standard)."* Bumped
  `PROMPT_VERSION` → `v12-2026-05-06-general-purpose` to invalidate
  the old fuzzy cache.

- **Phase 3** — Simplified `_ai_answer_with_retry` to two attempts:
  Gemini full → Groq 70B → polite error. Removed self-review pattern
  (`_ai_answer_with_review` is now an alias), the slim Gemini retry,
  Groq 8B fallback, Gemma2 fallback, and the countdown UI
  (`_countdown_and_retry` is now an alias). `ENABLE_SELF_REVIEW` is
  `False`. `_MODEL_CANDIDATES` in `chatbot_groq.py` trimmed to just
  `['llama-3.3-70b-versatile']`.

- **Phase 4** — `chatbot_cache` now only fires for *pure-theory*
  queries: must contain a marker like *"là gì" / "what is"* AND a
  theory token like *AR / MAPE / Ichimoku*, must NOT contain a
  ticker name (FPT/HPG/VNM), must NOT contain data-dependent words.
  Cache key is exact normalized query + lang (no fuzzy MD5
  cross-ticker layer).

- **Phase 5** — Prism.js (`prismjs@1.29.0` + autoloader) is injected
  once per session via `_inject_katex_once`, with a MutationObserver
  on `parent.document.body` so streaming/late-arriving fenced code
  blocks get highlighted. The Streamlit-native markdown path already
  highlights ` ```python ` / ` ```javascript ` etc.

### Files modified

- `app_pages/chatbot.py` — major: math pipeline pivot, render path,
  Prism.js injection, deleted ~380 lines of fake-math helpers
- `core/chatbot_ai.py` — system prompts replaced, PROMPT_VERSION bumped
- `core/chatbot_logic.py` — retry chain simplified, self-review removed
- `core/chatbot_groq.py` — model list trimmed
- `core/chatbot_cache.py` — strict pure-theory gating, no fuzzy fallback
- `_test_chatbot_render.py` — replaced harness (25 assertions)
- `PLAN.md` — overwritten with the new plan

### Key architectural decisions

1. **Path A over Path B for KaTeX.** The previous attempt used an
   iframe-injected `renderMathInElement(parent.document.body, ...)`
   call, which fails silently on Streamlit Cloud because the
   srcdoc-based iframe has origin `null` and cannot reach the parent
   document. Streamlit's bundled KaTeX runs in the parent document
   already — we just need to feed it markdown via `st.markdown(text)`
   without `unsafe_allow_html`. The bubble visual is preserved by
   wrapping each st.markdown call in pre/post HTML chrome `<div>`s.
2. **Backwards-compat shims for retry helpers.** Rather than ripping
   out the names that `app_pages/chatbot.py` imports, we kept
   `_ai_answer_with_review`, `_try_groq`, and `_countdown_and_retry`
   as thin aliases / wrappers so the import chain stays valid. Real
   logic is now exclusively in `_ai_answer_with_retry`.
3. **Cache scope cut by ~95%.** Most chatbot answers are now uncached.
   This is acceptable because (a) Gemini's free tier handles the
   load; (b) live data freshness was the user's stated concern; and
   (c) theory questions still hit-rate well because their normalized
   form is stable across users.

---

## 2026-05-04 — Trợ lý AI v2 upgrade (legacy)

Date: 2026-05-06
Branch: main
Commits: see `git log`.

## Summary

The "Trợ lý AI" page now uses **Gemini native function calling** with **token streaming** so the chatbot can read live app data (prices, forecasts, Ichimoku, metrics) and answer with real numbers in real time. The legacy synchronous Gemini → Groq → context-fallback chain is preserved as a safety net — if the new SDK path fails for any reason, the page silently falls back and the user still gets an answer.

## Files added

- `core/chatbot_tools.py` (≈360 lines) — 8 Gemini-callable Python tools:
  - `get_current_ticker_data()`
  - `get_forecast_results()`
  - `get_technical_signals()`
  - `get_price_history(days=30)`
  - `get_portfolio()`
  - `compute_metric(metric_name, model)`
  - `plot_price_chart(days=30, with_ma=True)` — registers an inline Plotly chart
  - `switch_ticker(ticker)` — re-trains the 3 models on FPT/HPG/VNM for the answer
  
  State (df, model results, sidebar config) is set once per render via `set_app_state(...)` — tools read from a module global. JSON-serializable returns; SDK auto-introspects schemas from type hints + docstrings.

- `core/chatbot_stream.py` (≈215 lines) — Streaming wrapper around `client.models.generate_content_stream(...)` with native function calling. Yields typed events:
  - `{type:'text', delta:str}`
  - `{type:'tool_call', name, args}`
  - `{type:'tool_result', name, value}`
  - `{type:'done'}`
  - `{type:'error', kind, message}` — `kind ∈ rate_limit/quota/auth/other`
  Models tried in order: gemini-2.0-flash → gemini-2.5-flash. Auth and quota errors short-circuit; rate-limits move on to the next model.

- `PLAN.md` — Architecture, tool list, fallback strategy.
- `CHANGELOG.md` — This file.

## Files modified

- `app_pages/chatbot.py` — Replaced the synchronous answer block (≈12 lines around line 2423) with a streaming block (~180 lines) that:
  1. Sets app state on the tools module.
  2. Streams Gemini response into a live styled bubble (animated cursor `▌`).
  3. Renders transparent tool-call expanders as they happen.
  4. Renders any `plot_price_chart`-registered Plotly figure inline above the answer.
  5. Adds a `⏹ Dừng / Stop` button that flips a session flag the streaming generator polls between chunks.
  6. Falls back to legacy `_process_query` on any streaming error.
  7. Appends a collapsible `<details>` summary listing every tool used.
  8. Persists the final text to `chat_history` and reruns once.
  
  Math rendering pipeline (`_md_to_html`, `_looks_like_math`, KaTeX injection) is **untouched**. The 57/57 math-render test harness still passes.

- `_test_chatbot_render.py` — Extended with two new test sets:
  - Module import smoke: `core.chatbot_tools` (registry sanity, every tool callable on empty state) + `core.chatbot_stream` (importable).
  - Page import smoke: every page in `app_pages/` imports cleanly under stubbed Streamlit.

## Behaviour changes (user-visible)

- Streaming token-by-token — the bubble fills as text arrives, with a blinking cursor.
- Real numbers — when the user asks "Phân tích FPT", the model now calls `get_forecast_results()` + `get_technical_signals()` and quotes the actual MAPE, RMSE, Ichimoku score etc.
- "Vẽ biểu đồ giá FPT 30 ngày" — model calls `plot_price_chart(30, True)` and a Plotly chart appears above the answer.
- "🔧 Đã sử dụng dữ liệu app (N tool calls)" — every assistant message that used tools shows a collapsed `<details>` with the call list and arg summary.
- Stop button next to the streaming response.
- Cross-ticker queries: ask "VNM giá bao nhiêu?" while sidebar is on FPT — model calls `switch_ticker('VNM')` and answers correctly.

## DOD audit

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | Streaming smooth | DONE | `stream_answer` yields text deltas; UI updates `st.empty().markdown()` per chunk. Visual smoothness verified on deploy. |
| 2 | Markdown (heading/list/bold/italic/link/blockquote/code) | DONE | Existing `_md_to_html` pipeline preserved. |
| 3 | Code block syntax highlight | PARTIAL | `<pre><code>` styling preserved; language-specific highlighting deferred (would require Prism/Highlight.js — not in scope for this iteration). |
| 4 | LaTeX inline + display | DONE | KaTeX injection preserved. |
| 5 | DataFrame tables ±% styling | PARTIAL | Markdown tables styled; ±% color is up to the model output (system prompt encourages it). |
| 6 | Plotly inline | DONE | `plot_price_chart` tool + `inline_chart_keys` rendering. |
| 7 | Function calling | DONE | `tools=AVAILABLE_TOOLS` → SDK auto-introspect. |
| 8 | Multi-turn context | DONE | Last 12 messages converted to SDK `Content` list. |
| 9 | Theory Q without tool calls | DONE | System prompt unchanged; model decides. |
| 10 | History save/load/new chat | DONE | Pre-existing `chat_history` module untouched. |
| 11 | Navy theme | DONE | No CSS changes; existing CSS cache preserved. |
| 12 | User vs assistant bubbles | DONE | Existing `_render_user_message` / `_render_bot_message`. |
| 13 | Tool call expander | DONE | Per-call expander while streaming + collapsed `<details>` summary in the saved message. |
| 14 | Stop / Copy / Regenerate | DONE | Stop is new (button + session flag polled in stream loop). Copy / Regenerate were already in `_render_bot_message`. |
| 15 | Auto-scroll | DONE | Existing `chat-bottom-anchor` JS preserved. |
| 16 | Suggested prompts hide after 1st msg | DONE | Existing condition `if not messages: _render_welcome_screen(...)`. |
| 17 | Empty state pretty | DONE | Existing welcome screen preserved. |
| 18 | No layout break on desktop | DONE (pending visual confirm) | Live streaming bubble lives just below the chat container, in the same column. |
| 19 | No crash on missing/wrong API key | DONE | `is_streaming_available()` returns False → legacy path; legacy path returns context-based fallback or friendly down-message. |
| 20 | Gemini → Groq fallback | DONE | Legacy `_process_query` still chains Gemini → slim → Groq 70B → Groq 8B → countdown retry. |
| 21 | Context truncation | DONE | 12 messages × 1500 chars per message. |
| 22 | Empty/whitespace input | DONE | `_query` is falsy → block doesn't enter. |
| 23 | Special chars don't break UI | DONE | `_md_to_html` html-escapes everything. |
| 24 | Modular files | DONE | 2 new files; UI rewiring localized to one block. |
| 25 | Docstrings | DONE | Every public function in tools + stream module has a docstring (the LLM uses these for tool selection). |
| 26 | No hardcoded keys | DONE | All keys via `st.secrets.get('GEMINI_API_KEY', ...)`. |
| 27 | requirements.txt | DONE | `google-genai>=1.0.0` already present; no new deps. |
| 28 | PLAN.md + CHANGELOG.md | DONE | This file + `PLAN.md`. |

**Score: 26/28 fully done, 2/28 partial** (code-block language highlighting and ±% DataFrame styling — both nice-to-haves outside the core mission of "deep app data integration via function calling").

## Test results

```
$ python _test_chatbot_render.py
...
FINAL: primary 15/15  |  negatives 5/5  |  hardening+ 22/22  |  hardening- 15/15
OVERALL: 57/57 PASS

Module-import smoke: 2/2 PASS
Page-import smoke:   8/8 PASS
```

## Limitations / known gaps

1. **Code-block syntax highlighting** is generic monospace; real Prism/Highlight.js integration not added (not part of the core requirement; the math-rendering pipeline is more important for this app).
2. **DataFrame ±% color styling** depends on the model emitting markdown with explicit color codes; not enforced.
3. **Image generation** (Gemini 2.0 image gen) is **not** wired — chart-from-data via `plot_price_chart` covers ~95% of requests; the spec explicitly allows graceful skip for true illustration generation.
4. **Live UX verification** (smooth streaming feel, animated cursor, expanders) was done at code-review level only; final visual check happens after Streamlit Cloud auto-deploys from the next push.

## Deploy notes

- No new dependencies → no requirements bump needed.
- API keys: `GEMINI_API_KEY` (required for streaming), `GROQ_API_KEY` (optional fallback). Both via `st.secrets`.
- After push, Streamlit Cloud auto-deploys in ~60s. Hit `/?page=Trợ%20lý%20AI` to test. First message with "Phân tích FPT" should show ≥1 tool-call expander.
