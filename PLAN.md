# PLAN — Chatbot rewrite (Phase 1-5, 2026-05-06)

## Goal

Two missions:

1. **Real KaTeX math rendering.** Strip out the Unicode pretty-print
   "fake math" pipeline (`_latex_to_pretty`, `_math_display_html`,
   `_math_inline_html` and friends). Math now flows through Streamlit's
   native `st.markdown(text)` path, which already pipes `$...$` and
   `$$...$$` through KaTeX.
2. **General-purpose ChatGPT-class assistant.** Replace the rigid
   "must-use-formula / Vietnamese-only / app-only" prompt with a
   friendly general-purpose persona that ALSO knows the HOSE
   forecasting tools when the user asks about the app data.

## Phase order (executed in this order)

1. **Phase 1 — Math rendering pivot.** Delete fake-math helpers, rewrite
   `_md_to_html` to preserve `$...$`/`$$...$$` literally, change
   `_render_bot_message` to send content through `st.markdown(text)`
   so KaTeX renders natively. Streaming live bubble switched to plain
   `st.markdown(text)` per chunk too (throttled at ~5 fps). Welcome
   subtitle still uses the HTML wrapper because it has no math.
2. **Phase 2 — System prompts.** Replace `_SYSTEM_PROMPT_VI` and
   `_SYSTEM_PROMPT_EN` with a friendly, language-agnostic general-purpose
   prompt. Add a brief "use these tools when the user asks about FPT/
   HPG/VNM" section. Drop the rigid mandates ("LUÔN trả lời tiếng
   Việt", "BẮT BUỘC kèm công thức KaTeX", "ALWAYS respond in English").
3. **Phase 3 — Retry chain simplification.** Two attempts only:
   - Gemini (full system prompt)
   - Groq llama-3.3-70b-versatile
   - Otherwise polite "AI temporarily down" message.
   Removed: `_ai_answer_with_review`, `_build_critique_prompt`,
   `_build_refine_prompt`, `_should_self_review`, slim Gemini retry,
   Groq 8B fallback, Gemma2 fallback, countdown UI.
4. **Phase 4 — Cache scope tightening.** Cache fires ONLY for clear
   theory questions (must contain a marker like "là gì" / "what is" AND
   a theory token like AR / MAPE / Ichimoku) AND no ticker token
   AND no data-dependent words. Fuzzy MD5 cross-ticker key removed.
5. **Phase 5 — Code block syntax highlighting.** Prism.js is injected
   alongside the (now legacy) KaTeX shim so that fenced code blocks
   inside HTML-mode bubbles (live streaming bubble) get coloured.
   Plain markdown bubbles use Streamlit's built-in highlighter.

## Architecture (after rewrite)

```
app_pages/chatbot.py
  - _md_to_html  (live streaming bubble only; preserves $…$ literally)
  - _render_bot_message  (history bubble: chrome via HTML, content via
    st.markdown(text) → native KaTeX)
  - _render_user_message  (unchanged)
  - _inject_katex_once  (now Prism.js injector + MutationObserver)
  - _katex_rerender_only  (no-op for backwards-compat)

core/chatbot_ai.py
  - PROMPT_VERSION → 'v12-2026-05-06-general-purpose'
  - _SYSTEM_PROMPT_VI / _SYSTEM_PROMPT_EN  (rewritten — friendly,
    general-purpose, language-agnostic, single-line math instruction)

core/chatbot_logic.py
  - _ai_answer_with_retry  (Gemini → Groq 70B; no slim, no countdown)
  - _ai_answer_with_review  = alias to _ai_answer_with_retry (compat)
  - _try_groq  (Groq 70B only)
  - _countdown_and_retry  = alias to _ai_answer_with_retry (compat)
  - REMOVED: _build_critique_prompt, _build_refine_prompt,
    _should_self_review, ENABLE_SELF_REVIEW now False

core/chatbot_groq.py
  - _MODEL_CANDIDATES = ['llama-3.3-70b-versatile']

core/chatbot_cache.py
  - _is_pure_theory_query  gates BOTH get() and set()
  - _make_key(query, lang)  — exact normalized query, no ticker context

core/chatbot_stream.py  (unchanged — picks up new system prompt automatically)
core/chatbot_tools.py   (unchanged — 7 tools, no plot_price_chart)
core/chat_history.py    (unchanged)

_test_chatbot_render.py  (replaced — 25 new assertions, see DOD below)
```

## Definition of Done — current run

Math
  - [x] grep `_latex_to_pretty` / `_math_display_html` / `_math_inline_html`
        in `app_pages/chatbot.py` finds zero `def …` definitions
  - [x] `_md_to_html('Test $x = 1$ inline')` contains literal `$x = 1$`
  - [x] `$$\hat{Y}_{t+1} = c + \phi_1 Y_t$$` survives `_md_to_html`
  - [x] `\frac{a}{b}` and `\sum_{i=1}^{n}` survive
  - [x] Streaming render path uses `st.markdown(text)` so KaTeX picks up
        math each chunk
  - [x] History bubbles use `st.markdown(text)` for content

Generality
  - [x] System prompt rewritten — no Vietnamese-only mandate, no must-use-formula
  - [x] LaTeX instruction reduced to one line ("Use $...$ for inline,
        $$...$$ for display")
  - [x] "When asked about FPT/HPG/VNM, call these tools" section kept

Code quality
  - [x] Retry chain: Gemini → Groq 70B
  - [x] Self-review removed (`ENABLE_SELF_REVIEW = False`, helpers gone)
  - [x] Cache fires only on pure-theory queries (exact normalized key)
  - [x] PROMPT_VERSION bumped to `v12-…` so old fuzzy cache invalidates
  - [x] PLAN.md + CHANGELOG.md updated

Robustness
  - [x] App imports cleanly (smoke harness covers all 8 pages)
  - [x] Quota exhausted → polite Vietnamese / English message
        (delegated to _ai_down_msg)
