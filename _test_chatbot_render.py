# -*- coding: utf-8 -*-
"""Test harness for chatbot math rendering pipeline.

Exercises _md_to_html() against 15 scenarios.
A scenario PASSES when the formula portion is rendered as math typography
(italic Cambria-ish serif via the math span/div helpers) rather than as
a <pre><code> code block. Scenario #9 is the inverse — code MUST stay code.

Run:  python _test_chatbot_render.py
"""
from __future__ import annotations

import sys
import os
import io
import importlib

# Force UTF-8 stdout/stderr so we can print Σ, β, ŷ, etc. without crashing on Win cp1252.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Make sure we import from this directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Stub streamlit BEFORE importing chatbot (chatbot.py imports streamlit at top).
# We do not need real streamlit for testing the rendering helpers.
class _StubStreamlit:
    session_state = {}
    secrets = {}

    def __getattr__(self, name):
        # Some Streamlit symbols are decorators: cache_data, cache_resource.
        # Return a callable that, when called either as decorator (with kwargs)
        # OR with a function arg, returns the function unchanged.
        if name in ('cache_data', 'cache_resource', 'experimental_memo',
                    'experimental_singleton', 'memo', 'singleton'):
            def _dec(*a, **kw):
                # @st.cache_data → called as @cache_data(...) or @cache_data
                if len(a) == 1 and callable(a[0]) and not kw:
                    return a[0]
                def _wrap(fn):
                    return fn
                return _wrap
            return _dec
        # Any other attribute access returns a no-op callable that returns None
        return lambda *a, **kw: None

if 'streamlit' not in sys.modules:
    sys.modules['streamlit'] = _StubStreamlit()
# components.v1 sub-module
class _StubComponents:
    def html(self, *a, **kw): return None
sys.modules['streamlit.components'] = type(sys)('streamlit.components')
sys.modules['streamlit.components.v1'] = _StubComponents()

# Stub heavy modules that chatbot.py pulls
for mod in [
    'core.chatbot_rules', 'core.chatbot_ai', 'core.chatbot_groq',
    'core.chatbot_logic', 'core.references', 'core.chat_history',
    'core.chatbot_cache', 'core.i18n',
]:
    if mod not in sys.modules:
        m = type(sys)(mod)
        # Generic stubs
        m.get_rule_answer = lambda *a, **kw: None
        m.ask_gemini = lambda *a, **kw: None
        m.is_ai_available = lambda *a, **kw: False
        m.RateLimitError = type('RateLimitError', (Exception,), {})
        m.QuotaExhaustedError = type('QuotaExhaustedError', (Exception,), {})
        m.ask_groq = lambda *a, **kw: None
        m.is_groq_available = lambda *a, **kw: False
        m._log = lambda *a, **kw: None
        m._detect_ticker_in_query = lambda *a, **kw: None
        m._build_context = lambda *a, **kw: None
        m._detect_navigation_intent = lambda *a, **kw: None
        m._context_based_answer = lambda *a, **kw: None
        m._ai_down_msg = lambda *a, **kw: ''
        m._is_data_dependent = lambda *a, **kw: False
        m._process_query = lambda *a, **kw: None
        m._is_theory_query = lambda *a, **kw: False
        m._ai_answer_with_retry = lambda *a, **kw: None
        m._try_groq = lambda *a, **kw: None
        m._countdown_and_retry = lambda *a, **kw: None
        m.detect_citation_request = lambda *a, **kw: None
        m.get_references_by_topic = lambda *a, **kw: []
        m.get_all_references = lambda *a, **kw: []
        m.format_timestamp = lambda *a, **kw: ''
        m.t = lambda key, default='': default or key
        sys.modules[mod] = m


# --- import chatbot pipeline ---
from app_pages import chatbot as cb  # noqa: E402

# Force reload to pick up edits between iterations during dev.
importlib.reload(cb)
_md_to_html = cb._md_to_html
_looks_like_math = cb._looks_like_math


# ─────────────────────────────────────────────────────────────────
# Scenarios
# ─────────────────────────────────────────────────────────────────

SCENARIOS = [
    # 1. Plain MAPE formula in fenced code block
    ("plain_fenced_mape",
     "MAPE bao nhiêu là tốt?\n\n"
     "```\nMAPE = (1/n)·Σ|y_actual - y_pred|/|y_actual|·100%\n```\n\n"
     "Theo Hyndman 2021, <10% là rất tốt.",
     "math"),

    # 2. Same formula in single backticks (inline code)
    ("inline_backticks_mape",
     "Công thức là `MAPE = (1/n)·Σ|y_actual - y_pred|/|y_actual|·100%` đúng không?",
     "math"),

    # 3. Plain text scattered Greek/operators
    ("plain_greek_ops",
     "Mô hình dùng Σ, β, φ, σ. Dự báo Ŷ ≈ ŷ. Điều kiện: x ≤ 5, y ≥ 0, √x · 100%.",
     "any"),

    # 4. LaTeX inline $...$
    ("latex_inline",
     r"Phương trình AR(1): $\hat{Y}_{t+1} = c + \phi_1 Y_t$ trong đó c là hệ số chặn.",
     "math"),

    # 5. LaTeX display $$...$$
    ("latex_display",
     r"Công thức MAPE:" "\n\n"
     r"$$\text{MAPE} = \frac{1}{n}\sum_{i=1}^{n}\left|\frac{y_i-\hat{y}_i}{y_i}\right| \cdot 100\%$$"
     "\n\nNgưỡng <10% rất tốt.",
     "math"),

    # 6. AR(1) plain text
    ("ar1_plain_text",
     "AR(1) có dạng:\n\n```\nŶ_{t+1} = c + φ₁·Y_t\n```",
     "math"),

    # 7. R²adj plain
    ("r2adj_plain",
     "Công thức R² hiệu chỉnh:\n```\nR²adj = 1 - (1-R²)·(n-1)/(n-k-1)\n```",
     "math"),

    # 8. RMSE
    ("rmse_plain",
     "RMSE đo:\n```\nRMSE = sqrt((1/n)·Σ(y - ŷ)²)\n```",
     "math"),

    # 9. Mixed: inline math + REAL code (must stay code)
    ("mixed_real_code",
     r"Hệ số $\beta_1 = 0.99$ và đoạn code Python:" "\n\n"
     "```python\n"
     "def forecast(prices, phi=0.98):\n"
     "    return prices.shift(1) * phi\n"
     "```\n",
     "code"),

    # 10. Subscript / superscript chains plain
    ("subsup_chains",
     "Các trễ:\n```\nY_{t-1}, x², MA_5, MA_{20}\n```",
     "math"),

    # 11. Greek-only line
    ("greek_only",
     "```\nβ · Σ φ\n```",
     "math"),

    # 12. Vietnamese narrative + formula
    ("vietnamese_narrative",
     "Công thức MAPE:\n\n"
     "```\nMAPE = (1/n)·Σ|y - ŷ|/|y|·100%\n```\n\n"
     "Hyndman 2021: ngưỡng <10% rất tốt.",
     "math"),

    # 13. AI emits formula without backticks at all (just plain paragraph)
    ("plain_paragraph_formula",
     "Công thức: MAPE = (1/n)·Σ|y - ŷ|/|y|·100% — Hyndman 2021.",
     "math"),

    # 14. Bold-wrapped formula
    ("bold_wrapped_formula",
     "Đáp án: **MAPE = (1/n)·Σ|y - ŷ|/|y|·100%**",
     "math"),

    # 15. Wide formula — must NOT linewrap (overflow-x: auto + nowrap-friendly)
    ("wide_formula",
     "```\n"
     "Score = w1·Primary + w2·TKCross + w3·Chikou + w4·FutureKumo where Σwi = 1 and wi ≥ 0\n"
     "```",
     "math"),
]


# Additional hardening scenarios used in later iterations to make sure we don't
# break common non-math content.
NEGATIVE_SCENARIOS = [
    # SQL block must stay code
    ("sql_stays_code",
     "```sql\nSELECT ticker FROM prices WHERE close > 100;\n```",
     "code"),

    # Plain prose with one '=' must not be promoted
    ("prose_with_equals",
     "Giá = 100 đồng (giá đóng cửa hôm nay không bao gồm phí).",
     "no_math"),

    # JSON must stay code
    ("json_stays_code",
     '```json\n{"ticker":"FPT","close":75200}\n```',
     "code"),

    # bash command must stay code
    ("bash_stays_code",
     '```bash\nexport DEBUG=true && python app.py\n```',
     "code"),

    # Inline code containing python must stay code, not math
    ("inline_python_pdf",
     "Dùng `pd.DataFrame({\"x\": prices})` trước.",
     "no_math"),
]


# Progressive hardening — these test edge-cases discovered during iteration.
HARDENING_SCENARIOS = [
    # 16. AI emits MAPE formula in fenced code with language tag (e.g. ```math)
    ("fenced_math_lang_tag",
     "```math\nMAPE = (1/n)·Σ|y - ŷ|/|y|·100%\n```",
     "math"),

    # 17. Multi-line fenced math (display-style, line breaks within)
    ("fenced_multiline_math",
     "```\nRMSE = sqrt((1/n)·Σ(y - ŷ)²)\nMAE  = (1/n)·Σ|y - ŷ|\n```",
     "math"),

    # 18. Inline LaTeX with \\frac and subscript/superscript
    ("inline_latex_frac",
     r"Hiệu chỉnh: $R^2_{adj} = 1 - (1-R^2)\frac{n-1}{n-k-1}$ giúp phạt tham số dư.",
     "math"),

    # 19. AI emits plain-text MAPE without backticks at the START of a line
    ("formula_at_line_start",
     "MAPE = (1/n)·Σ|y_actual - y_pred|/|y_actual|·100%",
     "math"),

    # 20. Prose paragraph with embedded inline `$\\beta$` should not blow away
    ("prose_with_inline_dollar",
     r"Hệ số $\beta_1 = 0.99$ cho thấy giá gần random walk.",
     "math"),

    # 21. AR(1) formula in a list item (must still render math, not stay flat)
    ("formula_in_list_item",
     "- Mô hình AR(1): $\\hat{Y}_{t+1} = c + \\phi_1 Y_t$\n- MAPE: <10% rất tốt.",
     "math"),

    # 22. Greek + operators with wide character spacing
    ("greek_with_spacing",
     "```\nβ̂ ≈ 0.985 và φ ≈ 1, σ² nhỏ\n```",
     "math"),

    # 23. Real-world Gemini-ish output: paragraph with nested `MAPE = ...` then prose
    ("realworld_gemini_style",
     "MAPE đo sai số trung bình theo phần trăm:\n\n"
     "MAPE = (1/n)·Σ|y - ŷ|/|y|·100%\n\n"
     "Ngưỡng <10% rất tốt theo Hyndman 2021.",
     "math"),

    # 24. Display $$ with sqrt and frac
    ("display_sqrt_frac",
     r"$$\text{RMSE} = \sqrt{\frac{1}{n}\sum_{i=1}^{n}(y_i-\hat{y}_i)^2}$$",
     "math"),

    # 25. Mixed: $$display$$ followed by ``` real Python ```
    ("mixed_display_then_code",
     r"$$\hat{Y}_{t+1} = c + \phi_1 Y_t$$" "\n\n"
     "```python\nimport pandas as pd\ndf = pd.read_csv('prices.csv')\n```",
     "any"),

    # 26. Two formulas on consecutive plain lines — both should be promoted
    ("two_consecutive_plain_formulas",
     "MAPE = (1/n)·Σ|y - ŷ|/|y|·100%\nRMSE = sqrt((1/n)·Σ(y - ŷ)²)",
     "math"),

    # 27. Bullet list with a math inline
    ("bullet_list_with_math_inline",
     "- Mô hình: $\\hat{Y}_{t+1} = c + \\phi_1 Y_t$\n- Sai số: MAPE < 10% là tốt",
     "math"),

    # 28. Heading then formula
    ("heading_then_formula",
     "## Công thức MAPE\n\nMAPE = (1/n)·Σ|y - ŷ|/|y|·100%",
     "math"),

    # 29. Mixed formulas: display $$ then plain promoted
    ("display_plus_plain",
     r"$$\hat{Y}_{t+1} = c + \phi_1 Y_t$$" "\n\n"
     "Sai số ngưỡng: MAPE = (1/n)·Σ|y - ŷ|/|y|·100%",
     "math"),

    # 30. Real Gemini reply: prose + display + prose
    ("end_to_end_gemini_reply",
     "MAPE — Mean Absolute Percentage Error.\n\n"
     "$$\\text{MAPE} = \\frac{1}{n}\\sum_{i=1}^{n}\\left|\\frac{y_i-\\hat{y}_i}{y_i}\\right|\\cdot 100\\%$$\n\n"
     "Hyndman 2021: <10% rất tốt.",
     "math"),

    # 31. Bold-wrapped multi-line formula in fenced block
    ("bold_wrapped_fenced",
     "**Lý thuyết:**\n```\nRMSE = sqrt((1/n)·Σ(y - ŷ)²)\n```",
     "math"),

    # 32. Inline `MAPE` reference in prose (no '=', no operators)
    ("inline_metric_reference",
     "Chỉ số MAPE đo độ lệch %.",
     "no_math"),

    # 33. Inline backtick wrapped LaTeX command
    ("inline_backtick_latex",
     r"Dùng `\\hat{Y}_{t+1}` cho dự báo.",
     "math"),

    # 34. AI emits MAPE formula with sub-equations on multiple fenced lines
    ("multi_line_subequations",
     "```\nMAPE = (1/n)·Σ|y - ŷ|/|y|·100%\nWhere y = actual, ŷ = predicted\n```",
     "math"),

    # 35. Single LaTeX command on its own (no $)
    ("plain_latex_command_in_fence",
     "```\n\\hat{Y}_{t+1} = c + \\phi_1 Y_t\n```",
     "math"),

    # 36. Fenced with leading and trailing prose around the formula
    ("fenced_with_label_lines",
     "```\nMAPE formula:\nMAPE = (1/n)·Σ|y - ŷ|/|y|·100%\n```",
     "math"),

    # 37. AR(p) compact form — formula at line start, no formatting
    ("compact_arp",
     "Ŷ_{t+1} = c + φ_1·Y_t + φ_2·Y_{t-1} + ... + φ_p·Y_{t-p+1}",
     "math"),
]


# Negative hardening — non-math content that must NOT be promoted.
NEGATIVE_HARDENING = [
    # Conversational prose with '=' as natural language
    ("conversational_eq_no_math",
     "Bạn nói = OK rồi đó!",
     "no_math"),

    # Markdown link with '=' in URL
    ("markdown_link_with_eq",
     "Xem tại https://example.com/?q=test để biết thêm.",
     "no_math"),

    # Filename with '='
    ("filename_with_eq",
     "Lưu vào `output_v=2.csv` nhé.",
     "no_math"),

    # Plain numeric text (no math indicators)
    ("plain_numeric_prose",
     "Doanh thu năm 2024 đạt 1500 tỷ đồng, tăng 12% so với năm trước.",
     "no_math"),

    # Bash with conditional
    ("bash_with_eq_no_math",
     "```bash\nif [ $x -eq 0 ]; then echo zero; fi\n```",
     "code"),

    # Long Vietnamese prose with `=` should not promote
    ("long_vn_prose_eq",
     "Mục tiêu nghiên cứu = xây dựng mô hình dự báo giá cổ phiếu HOSE đạt độ chính xác cao.",
     "no_math"),

    # Inline backtick with normal identifier (not math)
    ("inline_identifier",
     "Hàm `forecast_price()` được gọi sau khi load model.",
     "no_math"),

    # Conversational chat: "Lương = bao nhiêu?" → not math
    ("question_with_eq",
     "Lương cơ bản = bao nhiêu vậy bạn?",
     "no_math"),

    # YAML config block must stay code
    ("yaml_stays_code",
     "```yaml\nticker: FPT\nclose: 75200\nmape: 1.2\n```",
     "code"),

    # Comma-separated values, no math
    ("csv_like",
     "Danh sách: FPT, HPG, VNM, MWG, VCB.",
     "no_math"),

    # MAPE comparison without an actual formula equation (just numbers)
    ("mape_threshold_only",
     "MAPE < 10% rất tốt theo Hyndman 2021.",
     "no_math"),

    # Plain prose mentioning RMSE and MSE without formula
    ("rmse_mention_no_formula",
     "Chúng ta dùng RMSE và MSE để đánh giá.",
     "no_math"),

    # Prose mentioning a metric with a number (e.g. MAPE = 1.2%) — must NOT
    # be promoted to math. Iteration 21 fix.
    ("prose_with_metric_number",
     "Trong app này, AR(1) trên FPT có MAPE = 1.2% — đạt mức rất tốt.",
     "no_math"),

    # Prose with two metrics inline (sentence about results)
    ("prose_two_metrics_inline",
     "Kết quả cho thấy MAPE = 1.5% và RMSE = 0.9k đồng trên test set.",
     "no_math"),

    # The original screenshot bug — fenced MAPE formula MUST render as math
    ("regression_screenshot_bug",
     "```\nMAPE = (1/n)·Σ|y_actual - y_pred|/|y_actual|·100%\n```",
     "math"),
]


# ─────────────────────────────────────────────────────────────────
# Detection helpers
# ─────────────────────────────────────────────────────────────────

MATH_DIV_MARK = "font-style:italic"          # appears in display & inline math html
MATH_FAMILY_MARK = "Cambria Math"            # math font family
CODE_PRE_MARK = "<pre"                        # real code block

def _has_math(html: str) -> bool:
    return MATH_DIV_MARK in html and MATH_FAMILY_MARK in html

def _has_code(html: str) -> bool:
    return CODE_PRE_MARK in html


def _run_one_set(label: str, scenarios):
    print("-" * 70)
    print(f"  Set: {label}")
    print("-" * 70)
    passed = 0
    failed = []
    for name, src, expect in scenarios:
        try:
            html = _md_to_html(src)
        except Exception as e:
            failed.append((name, expect, f"EXCEPTION: {e}"))
            print(f"  [FAIL] {name:30s}  EXCEPTION: {e}")
            continue
        ok = False
        reason = ""
        if expect == "math":
            ok = _has_math(html) and not _has_code(html)
            if not ok:
                if _has_code(html):
                    reason = "rendered as <pre><code> (math leaked into code path)"
                else:
                    reason = "no math div/span markers found"
        elif expect == "code":
            # Must contain a <pre><code> for the python block
            ok = _has_code(html)
            if not ok:
                reason = "code block was upgraded to math (false positive)"
        elif expect == "any":
            # Just must not crash
            ok = True
        elif expect == "no_math":
            ok = not _has_math(html)
            if not ok:
                reason = "non-math content was promoted to math"
        else:
            ok = False
            reason = f"unknown expectation {expect}"

        if ok:
            passed += 1
            print(f"  [PASS] {name:30s}  ({expect})")
        else:
            failed.append((name, expect, reason))
            snippet = html[:300].replace("\n", " ")
            print(f"  [FAIL] {name:30s}  {reason}")
            print(f"         html[:300]: {snippet}")

    total = len(scenarios)
    print(f"  Subtotal: {passed}/{total} PASS, {len(failed)} FAIL")
    return passed, total, failed


def run() -> None:
    print("=" * 70)
    print("CHATBOT MATH RENDERING — TEST HARNESS")
    print("ITERATIONS: 22 (test → identify → fix → re-test cycles)")
    print("=" * 70)
    p1, t1, f1 = _run_one_set("Primary scenarios (15 mandate)", SCENARIOS)
    p2, t2, f2 = _run_one_set("Negative regression scenarios", NEGATIVE_SCENARIOS)
    p3, t3, f3 = _run_one_set("Progressive hardening (math)", HARDENING_SCENARIOS)
    p4, t4, f4 = _run_one_set("Progressive hardening (negative)", NEGATIVE_HARDENING)
    print("=" * 70)
    print(f"FINAL: primary {p1}/{t1}  |  negatives {p2}/{t2}"
          f"  |  hardening+ {p3}/{t3}  |  hardening- {p4}/{t4}")
    total_p = p1 + p2 + p3 + p4
    total_t = t1 + t2 + t3 + t4
    print(f"OVERALL: {total_p}/{total_t} PASS")
    if f1 or f2 or f3 or f4:
        print("\nFailures:")
        for name, expect, reason in f1 + f2 + f3 + f4:
            print(f"  - {name} (expected={expect}): {reason}")
    print("=" * 70)
    return (p1, t1, f1), (p2, t2, f2), (p3, t3, f3), (p4, t4, f4)


def _smoke_pages():
    """Import all app_pages — they must not crash even with stubbed streamlit."""
    print("-" * 70)
    print("  Set: All app_pages module-import smoke tests")
    print("-" * 70)
    failed = 0
    # Stub heavy externals
    if 'streamlit_option_menu' not in sys.modules:
        m = type(sys)('streamlit_option_menu')
        m.option_menu = lambda *a, **kw: None
        sys.modules['streamlit_option_menu'] = m
    if 'vnstock' not in sys.modules:
        m = type(sys)('vnstock')
        class _Vnstock:
            def stock(self, **kw):
                class S:
                    class quote:
                        @staticmethod
                        def history(**kw): return None
                return S()
        m.Vnstock = _Vnstock
        sys.modules['vnstock'] = m
    page_modules = ['dashboard', 'analysis', 'history', 'signals',
                    'portfolio', 'guide', 'splash', 'chatbot']
    for pname in page_modules:
        try:
            mod_name = f'app_pages.{pname}'
            if mod_name in sys.modules:
                # Force fresh import to pick up edits
                importlib.reload(sys.modules[mod_name])
            else:
                __import__(mod_name)
            print(f"  [PASS] app_pages.{pname}")
        except Exception as e:
            failed += 1
            print(f"  [FAIL] app_pages.{pname}: {type(e).__name__}: {e}")
    print(f"  Page-import subtotal: {len(page_modules) - failed}/{len(page_modules)} PASS, {failed} FAIL")
    return failed == 0


def _smoke_imports():
    """Smoke-test that the new modules import + tool registry is well-formed.
    Runs in addition to the math-render harness; failures raise.
    """
    print("-" * 70)
    print("  Set: Module-import smoke tests (new chatbot v2 modules)")
    print("-" * 70)
    failed = 0

    try:
        from core import chatbot_tools as ct
        assert hasattr(ct, 'AVAILABLE_TOOLS') and isinstance(ct.AVAILABLE_TOOLS, list)
        assert len(ct.AVAILABLE_TOOLS) >= 6, f"only {len(ct.AVAILABLE_TOOLS)} tools registered"
        names = [f.__name__ for f in ct.AVAILABLE_TOOLS]
        assert 'get_current_ticker_data' in names
        assert 'get_forecast_results' in names
        assert 'get_technical_signals' in names
        assert 'plot_price_chart' in names
        # has_state should be False before set_app_state
        assert ct.has_state() is False
        # Each tool must be callable + return dict-ish on empty state
        for fn in ct.AVAILABLE_TOOLS:
            try:
                # Pass dummy positional safe defaults where needed
                if fn.__name__ == 'compute_metric':
                    res = fn('MAPE', 'ar')
                elif fn.__name__ == 'switch_ticker':
                    res = fn('FPT')
                elif fn.__name__ == 'plot_price_chart':
                    res = fn(30, True)
                elif fn.__name__ == 'get_price_history':
                    res = fn(30)
                else:
                    res = fn()
                assert isinstance(res, dict), f"{fn.__name__} did not return dict"
            except Exception as e:
                failed += 1
                print(f"  [FAIL] tool {fn.__name__} raised: {e}")
                continue
        print(f"  [PASS] core.chatbot_tools imports + {len(ct.AVAILABLE_TOOLS)} tools callable")
    except Exception as e:
        failed += 1
        print(f"  [FAIL] core.chatbot_tools import: {e}")

    try:
        from core import chatbot_stream as cs
        assert hasattr(cs, 'stream_answer')
        assert hasattr(cs, 'is_streaming_available')
        # is_streaming_available may return False (no API key in test env) — that's fine
        ok = cs.is_streaming_available()
        print(f"  [PASS] core.chatbot_stream imports (is_streaming_available={ok})")
    except Exception as e:
        failed += 1
        print(f"  [FAIL] core.chatbot_stream import: {e}")

    print(f"  Smoke subtotal: {2 - failed}/2 PASS, {failed} FAIL")
    return failed == 0


if __name__ == "__main__":
    run()
    ok1 = _smoke_imports()
    ok2 = _smoke_pages()
    if not (ok1 and ok2):
        import sys as _s
        _s.exit(1)
