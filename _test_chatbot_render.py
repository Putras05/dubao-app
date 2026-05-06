# -*- coding: utf-8 -*-
"""Phase-1+ smoke harness for the chatbot rewrite (2026-05-06).

Checks:
  - Module imports (chatbot.py + every other app_pages/* page) succeed.
  - _md_to_html preserves $...$ and $$...$$ literally (no fake-math).
  - Old fake-math helpers (_latex_to_pretty / _math_display_html /
    _math_inline_html) are gone.
  - 7 chatbot tools registered, no `plot_price_chart`.
  - System prompts dropped the "LUÔN trả lời tiếng Việt" / "BẮT BUỘC ...
    KaTeX" rules — replaced with the friendlier general-purpose prompt.
  - Retry chain has no _build_critique_prompt / _build_refine_prompt /
    _should_self_review / countdown UI.
  - Cache only fires on pure-theory queries.

Run:  python _test_chatbot_render.py
"""
from __future__ import annotations

import sys
import os
import io
import importlib

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ─────────────────────────────────────────────────────────────────
# Streamlit stub so importing chatbot.py doesn't need a real runtime
# ─────────────────────────────────────────────────────────────────
class _StubStreamlit:
    session_state = {}
    secrets = {}

    def __getattr__(self, name):
        if name in ('cache_data', 'cache_resource', 'experimental_memo',
                    'experimental_singleton', 'memo', 'singleton'):
            def _dec(*a, **kw):
                if len(a) == 1 and callable(a[0]) and not kw:
                    return a[0]
                def _wrap(fn):
                    return fn
                return _wrap
            return _dec
        return lambda *a, **kw: None


if 'streamlit' not in sys.modules:
    sys.modules['streamlit'] = _StubStreamlit()


class _StubComponents:
    def html(self, *a, **kw):
        return None


sys.modules['streamlit.components'] = type(sys)('streamlit.components')
sys.modules['streamlit.components.v1'] = _StubComponents()


# ─────────────────────────────────────────────────────────────────
# Test runner
# ─────────────────────────────────────────────────────────────────
RESULTS = []


def test(name):
    def decorator(fn):
        try:
            fn()
            RESULTS.append((name, 'PASS', ''))
        except AssertionError as e:
            RESULTS.append((name, 'FAIL', str(e) or 'assertion'))
        except Exception as e:
            RESULTS.append((name, 'ERROR', f'{type(e).__name__}: {e}'))
        return fn
    return decorator


# ─────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────
@test('01: import core.chatbot_ai')
def _():
    import core.chatbot_ai as m
    importlib.reload(m)


@test('02: import core.chatbot_logic')
def _():
    import core.chatbot_logic as m
    importlib.reload(m)


@test('03: import core.chatbot_stream')
def _():
    import core.chatbot_stream as m
    importlib.reload(m)


@test('04: import core.chatbot_cache')
def _():
    import core.chatbot_cache as m
    importlib.reload(m)


@test('05: import core.chatbot_groq')
def _():
    import core.chatbot_groq as m
    importlib.reload(m)


@test('06: import core.chatbot_tools')
def _():
    import core.chatbot_tools as m
    importlib.reload(m)


@test('07: import app_pages.chatbot')
def _():
    import app_pages.chatbot as m
    importlib.reload(m)


@test('08: import app_pages.dashboard')
def _():
    import app_pages.dashboard as m
    importlib.reload(m)


@test('09: import app_pages.analysis')
def _():
    import app_pages.analysis as m
    importlib.reload(m)


@test('10: import app_pages.history / signals / portfolio / guide / splash')
def _():
    for sub in ('history', 'signals', 'portfolio', 'guide', 'splash'):
        importlib.reload(importlib.import_module(f'app_pages.{sub}'))


@test('11: $x = 1$ inline math markers survive _md_to_html')
def _():
    from app_pages import chatbot as cb
    out = cb._md_to_html('Test $x = 1$ inline')
    assert '$x = 1$' in out, f'Inline math not preserved: {out!r}'


@test('12: $$ Y = c + phi Y_t $$ display math markers survive _md_to_html')
def _():
    from app_pages import chatbot as cb
    body = r'$$\hat{Y}_{t+1} = c + \phi_1 Y_t$$'
    out = cb._md_to_html(f'See:\n\n{body}\n\ndone.')
    assert body in out, f'Display math not preserved: {out!r}'


@test('13: \\frac{a}{b} preserved literally')
def _():
    from app_pages import chatbot as cb
    out = cb._md_to_html(r'$\frac{a}{b}$')
    assert r'\frac{a}{b}' in out, f'Frac not preserved: {out!r}'


@test('14: \\sum_{i=1}^{n} preserved literally')
def _():
    from app_pages import chatbot as cb
    out = cb._md_to_html(r'$\sum_{i=1}^{n} x_i$')
    assert r'\sum_{i=1}^{n}' in out, f'Sum not preserved: {out!r}'


@test('15: fake-math helpers gone (_latex_to_pretty / _math_display_html / _math_inline_html)')
def _():
    from app_pages import chatbot as cb
    assert not hasattr(cb, '_latex_to_pretty'), 'fake-math helper still present'
    assert not hasattr(cb, '_math_display_html'), 'fake-math helper still present'
    assert not hasattr(cb, '_math_inline_html'), 'fake-math helper still present'


@test('16: source has 0 hits for the deleted fake-math definitions')
def _():
    here = os.path.dirname(os.path.abspath(__file__))
    src = open(os.path.join(here, 'app_pages', 'chatbot.py'), encoding='utf-8').read()
    forbidden_def_lines = (
        'def _latex_to_pretty',
        'def _math_display_html',
        'def _math_inline_html',
    )
    for tok in forbidden_def_lines:
        assert tok not in src, f'Forbidden definition still in source: {tok}'


@test('17: code block has language-* class for Prism.js')
def _():
    from app_pages import chatbot as cb
    out = cb._md_to_html('```python\nprint("hi")\n```')
    assert 'language-python' in out, f'Prism class missing: {out!r}'


@test('18: chatbot_tools registers exactly 7 tools, no plot_price_chart')
def _():
    from core import chatbot_tools as ct
    names = [getattr(fn, '__name__', '?') for fn in ct.AVAILABLE_TOOLS]
    assert len(names) == 7, f'Expected 7 tools, got {len(names)}: {names}'
    assert 'plot_price_chart' not in names, 'plot_price_chart should be deleted'


@test('19: system prompts updated (no "LUÔN trả lời tiếng Việt", no "BẮT BUỘC")')
def _():
    from core.chatbot_ai import _SYSTEM_PROMPT_VI, _SYSTEM_PROMPT_EN
    assert 'LUÔN trả lời bằng tiếng Việt' not in _SYSTEM_PROMPT_VI, \
        'Vietnamese-only mandate should be removed'
    assert 'BẮT BUỘC' not in _SYSTEM_PROMPT_VI, \
        'Mandatory-formula rule should be removed'
    assert 'ALWAYS respond in English' not in _SYSTEM_PROMPT_EN, \
        'English-only mandate should be removed'
    # New prompt should mention general-purpose / friendly / personality
    assert 'tổng quát' in _SYSTEM_PROMPT_VI or 'general-purpose' in _SYSTEM_PROMPT_EN


@test('20: PROMPT_VERSION bumped past v11')
def _():
    from core.chatbot_ai import PROMPT_VERSION
    assert PROMPT_VERSION.startswith('v12') or int(PROMPT_VERSION.split('-')[0][1:]) >= 12, \
        f'Expected v12+, got {PROMPT_VERSION}'


@test('21: retry chain has no _build_critique_prompt / _build_refine_prompt / _should_self_review')
def _():
    from core import chatbot_logic as cl
    assert not hasattr(cl, '_build_critique_prompt'), 'critique helper still present'
    assert not hasattr(cl, '_build_refine_prompt'), 'refine helper still present'
    assert not hasattr(cl, '_should_self_review'), 'gating helper still present'


@test('22: ENABLE_SELF_REVIEW is False')
def _():
    from core.chatbot_logic import ENABLE_SELF_REVIEW
    assert ENABLE_SELF_REVIEW is False, 'self-review should be disabled'


@test('23: Groq candidate list trimmed to 70B only')
def _():
    from core.chatbot_groq import _MODEL_CANDIDATES
    assert _MODEL_CANDIDATES == ['llama-3.3-70b-versatile'], \
        f'Expected 70B-only, got {_MODEL_CANDIDATES}'


@test('24: cache.get returns None for non-theory queries (e.g. "phân tích FPT")')
def _():
    from core import chatbot_cache as cc
    # Make sure fuzzy theory matcher returns False for a clearly non-theory query
    assert cc._is_pure_theory_query('phân tích FPT giúp mình') is False
    assert cc._is_pure_theory_query('giá HPG hôm nay') is False


@test('25: cache.get accepts pure-theory queries (e.g. "MAPE là gì?")')
def _():
    from core import chatbot_cache as cc
    assert cc._is_pure_theory_query('MAPE là gì?') is True
    assert cc._is_pure_theory_query('AR(1) hoạt động thế nào?') is True
    assert cc._is_pure_theory_query('what is Ichimoku?') is True


# ─────────────────────────────────────────────────────────────────
# Phase-1 (v13) — model coefficients in context + tighter theory gate
# ─────────────────────────────────────────────────────────────────
@test('26: _is_theory_query("công thức của FPT là gì?") returns False (data signal)')
def _():
    from core.chatbot_logic import _is_theory_query
    assert _is_theory_query('công thức của FPT là gì?') is False, (
        'FPT mention should disqualify as pure-theory'
    )


@test('27: _is_theory_query("AR(1) là gì?") returns True')
def _():
    from core.chatbot_logic import _is_theory_query
    assert _is_theory_query('AR(1) là gì?') is True


@test('28: _is_theory_query("Python list comprehension là gì?") returns True')
def _():
    from core.chatbot_logic import _is_theory_query
    assert _is_theory_query('Python list comprehension là gì?') is True, (
        'general-purpose theory question should pass (no data signal)'
    )


@test('29: build_context_string with ar_coefs renders c=1.5000 + φ_1 = 0.9800')
def _():
    from core.chatbot_ai import build_context_string
    out = build_context_string({'ar_coefs': {'intercept': 1.5, 'phi': [0.98]}})
    assert 'c = 1.5000' in out, f'intercept missing: {out!r}'
    assert 'φ_1 = 0.9800' in out, f'phi_1 missing: {out!r}'


@test('30: PROMPT_VERSION starts with v13')
def _():
    from core.chatbot_ai import PROMPT_VERSION
    assert PROMPT_VERSION.startswith('v13'), (
        f'Expected v13.. for Phase-1, got {PROMPT_VERSION}'
    )


# ─────────────────────────────────────────────────────────────────
# Rule-based safety net — runs only when both AI providers fail
# ─────────────────────────────────────────────────────────────────
@test('31: _rule_fallback exists and returns string for known intent')
def _():
    from core.chatbot_logic import _rule_fallback
    out = _rule_fallback('AR là gì?', 'VI')
    assert isinstance(out, str) and len(out) > 30, (
        f'Expected canned answer for AR theory, got {out!r}'
    )


@test('32: _rule_fallback returns None for unknown intent (no false-positive)')
def _():
    from core.chatbot_logic import _rule_fallback
    out = _rule_fallback('viết hàm sắp xếp Python theo Kruskal', 'VI')
    assert out is None, f'Should NOT match for unrelated query, got {out!r}'


@test('33: _ai_answer_with_retry calls _rule_fallback when both AI fail')
def _():
    """When Gemini AND Groq are unavailable, retry chain must still produce
    a rule-based answer for theory queries instead of returning None."""
    import core.chatbot_logic as cl
    # Patch ask_gemini & is_groq_available so both AI paths fail.
    orig_ask_gemini = cl.ask_gemini
    orig_groq_avail = cl.is_groq_available
    orig_st = cl.st

    class _StubSpinner:
        def __enter__(self): return self
        def __exit__(self, *a): return False

    class _StubSt:
        session_state = {}
        def spinner(self, *a, **kw): return _StubSpinner()

    def _fail_gemini(*a, **kw):
        raise cl.QuotaExhaustedError('test: forced quota')

    cl.ask_gemini = _fail_gemini
    cl.is_groq_available = lambda: False
    cl.st = _StubSt()
    try:
        resp = cl._ai_answer_with_retry('AR là gì?', context={}, lang='VI')
        assert isinstance(resp, str) and len(resp) > 30, (
            f'Expected rule-based fallback, got {resp!r}'
        )
    finally:
        cl.ask_gemini = orig_ask_gemini
        cl.is_groq_available = orig_groq_avail
        cl.st = orig_st


# ─────────────────────────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────────────────────────
def main():
    pass_n = sum(1 for _, st, _ in RESULTS if st == 'PASS')
    fail_n = sum(1 for _, st, _ in RESULTS if st in ('FAIL', 'ERROR'))
    total = len(RESULTS)
    width = max((len(n) for n, _, _ in RESULTS), default=20)

    for name, status, detail in RESULTS:
        marker = '✓' if status == 'PASS' else '✗'
        line = f'{marker} {name.ljust(width)}  [{status}]'
        if detail:
            line += f'  {detail[:200]}'
        print(line)

    print()
    print(f'{pass_n}/{total} PASS  ·  {fail_n} FAIL')
    sys.exit(0 if fail_n == 0 else 1)


main()
