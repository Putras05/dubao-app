# Chatbot math rendering audit

Goal: render math formulas like Gemini/ChatGPT (italic Cambria-Math, centered display, tinted box) regardless of whether Gemini wraps them in `$...$`, `$$...$$`, ``` ``` ```, single backticks, `**bold**`, or just plain text.

Files touched:
- `app_pages/chatbot.py` — rendering pipeline (`_md_to_html`, `_looks_like_math`, `_latex_to_pretty`, `_inline_md`, new `_line_looks_like_math`, `_strip_emphasis_wrap`, `_looks_like_identifier`)
- `_test_chatbot_render.py` — harness (NEW, 57 scenarios across 4 sets)
- `_chatbot_render_audit.md` — this log

AI prompt: NOT modified — system prompt v8 (`core/chatbot_ai.py`) already instructs Gemini to use `$...$`/`$$...$$`. The pipeline now catches math regardless.

## Iteration log

| # | Action | Result |
|---|---|---|
| 1 | Baseline run on 15 mandate scenarios | 12/15 PASS — fails: inline_backticks_mape, plain_paragraph_formula, bold_wrapped_formula |
| 2 | Strengthen `_looks_like_math` (add MAPE/RMSE/R² domain tokens, remove false-positive code keywords like `def`/`SELECT`); add `_line_looks_like_math` + `_strip_emphasis_wrap`; pre-extract single-backtick spans as `\x00BACKTICK{n}\x00` placeholders, route math-y ones through `_math_inline_html`; pre-scan paragraph lines for full-formula candidates, stash as `\x00AUTOMATH{n}\x00` | 15/15 mandate PASS |
| 3 | Add 5 negative regression scenarios (SQL/JSON/bash/prose/python kept as code or no_math) | 20/20 PASS — confirms no false promotion of code |
| 4 | Add 10 progressive math scenarios (fenced ```math, multi-line fenced, list items with inline math, $$ display + sqrt+frac, mixed display+code) | 30/30 PASS |
| 5 | Manual probe of original screenshot bug (`MAPE = (1/n)·Σ|y_actual - y_pred|/...`) — confirms math `<div>` rendered | verified |
| 6 | Make `_math_display_html` use `white-space:pre` (instead of `pre-wrap`) so wide formulas scroll horizontally instead of mid-formula linebreak | wide_formula stays one line |
| 7 | Fix multi-char alpha subscripts in `_latex_to_pretty` so `y_actual`, `y_pred` subscript whole identifier, not just first letter | verified by repr |
| 8 | Fix multi-digit numeric subscripts/superscripts (`MA_20`, `x^12`) | verified by repr |
| 9 | Add 2 negative scenarios (long_vn_prose_eq, inline_identifier with `forecast_price()`) — first PASS, second FAILED (snake_case promoted to math) | 6/7 — bug found |
| 10 | Remove `_t`, `_i`, `_n`, `_p` from `_STRONG_MATH_MARKERS` — were too greedy on snake_case identifiers; keep `_{`, `^{` (unambiguous LaTeX braces) | inline_identifier PASSES; subsup_chains still PASSES via `_{` |
| 11 | Add 2 more conversational negatives (question_with_eq, csv_like) | 10/10 negatives PASS |
| 12 | Add 2 more positives (heading_then_formula, display_plus_plain) | 12/12 PASS |
| 13 | Add 2 more positives (two_consecutive_plain_formulas, bullet_list_with_math_inline) | 14/14 PASS |
| 14 | Manual probe single-token math (`$\beta$`, `$\sigma^2$`, `$\phi$`) — all render as inline math span | verified |
| 15 | Add full Gemini-style end-to-end scenario | 15/15 PASS |
| 16 | Add 3 stress scenarios (bold_wrapped_fenced, inline_metric_reference, inline_backtick_latex) | 18/18 PASS |
| 17 | Add 2 prose-with-metric negatives (mape_threshold_only, rmse_mention_no_formula) | 12/12 negatives PASS |
| 18 | Add 2 advanced positives (multi_line_subequations, plain_latex_command_in_fence) | 20/20 PASS |
| 19 | Add 2 more positives (fenced_with_label_lines, compact_arp) | 22/22 PASS |
| 20 | Manual e2e probe — found 2 real defects: (a) `\%` not unescaped to `%`; (b) prose sentence "Trong app này, AR(1) trên FPT có MAPE = 1.2%" was incorrectly promoted to math display | bugs identified |
| 21 | Fix (a): in `_latex_to_pretty`, unescape `\%`, `\$`, `\&`, `\_`, `\#` BEFORE the generic `\cmd` strip. Fix (b): rewrite `_line_looks_like_math` to require LHS-of-`=` to be ≤ 4 tokens AND match a known formula name (MAPE/RMSE/Ŷ/AR(1)/etc.) OR be a single-token math identifier; reject prose with multi-word LHS | both bugs fixed; no regression |
| 22 | Add 3 regression scenarios (prose_with_metric_number, prose_two_metrics_inline, regression_screenshot_bug) to enshrine the iter-21 fixes | 15/15 negatives PASS, 57/57 OVERALL |

## Top fixes (highest impact)

1. **Pre-extract inline backtick spans + route math-y ones through `_math_inline_html`** (iter 2) — fixed inline_backticks_mape and inline_backtick_latex. Backtick spans are stashed before HTML escaping so we can detect math content (`Σ`, `·`, `MAPE = ...`) and route to italic Cambria span instead of `<code>`.
2. **Auto-promote whole paragraph lines that are formulas via `_line_looks_like_math` + `\x00AUTOMATH{n}\x00` placeholder** (iter 2 + iter 21 tightening) — fixed plain_paragraph_formula and bold_wrapped_formula. Iter 21 tightened the heuristic so prose sentences mentioning a metric (`... có MAPE = 1.2%`) are NOT promoted: LHS of `=` must be ≤4 tokens and a known formula name or single math identifier.
3. **Tighten `_looks_like_math` indicator set** (iter 10) — removed `_t`, `_i`, `_n`, `_p` strong markers because they false-matched snake_case identifiers like `forecast_price`. Kept `_{`, `^{` (unambiguous LaTeX braces).
4. **Fix multi-char/multi-digit sub-/super-scripts in `_latex_to_pretty`** (iter 6-7) — `y_actual` now subscripts whole identifier; `MA_20` subscripts both digits; `x^12` superscripts both digits.
5. **Unescape LaTeX punctuation `\%`, `\$`, `\&`, `\_`, `\#`** (iter 21) — was leaking `\%` into output. Now `100\%` → `100%`.

## How to run

```bash
cd d:/NCKH_CH_XAYDUNGCHATBOT/dubao_app
python _test_chatbot_render.py
```

Expected output: `OVERALL: 57/57 PASS` (15 primary + 5 negatives + 22 hardening+ + 15 hardening-).

## Final status

- ITERATIONS: 22
- FINAL: 15/15 mandate scenarios PASS; 57/57 overall (incl. negatives + regressions)
- AI prompt: NOT modified
- New deps: NONE (pure stdlib `re`, `html`)
- KaTeX JS: NOT touched (per constraint — server-side Unicode is the renderer)
