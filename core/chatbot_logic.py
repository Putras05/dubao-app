"""Chatbot pure-logic module — extracted from app_pages/chatbot.py.

Contains business-logic helpers for the chatbot (ticker detection, context
building, query classification, AI retry chain, fallback answers). UI rendering
helpers stay in app_pages/chatbot.py.
"""
import streamlit as st
import time
import re
from core.i18n import t
from core.chatbot_ai import (
    ask_gemini, build_context_string, RateLimitError, QuotaExhaustedError,
)
from core.chatbot_groq import ask_groq, is_groq_available


def _log(msg: str):
    """Safe logging — tránh UnicodeEncodeError trên Windows CMD."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode('ascii'))


# ═══════════════════════════════════════════════════════════════
# TICKER DETECTION — bot tự nhận diện mã trong câu hỏi user
# ═══════════════════════════════════════════════════════════════
def _detect_ticker_in_query(query: str, current_ticker: str) -> str | None:
    """Trả ticker user mention trong query nếu KHÁC ticker hiện tại, else None.

    Match standalone token (word boundary) để tránh match nhầm. Hỗ trợ
    nguyên ticker name + 1 vài cách viết phổ biến.
    """
    if not query:
        return None
    import re
    q_upper = query.upper()
    for tk in ('FPT', 'HPG', 'VNM'):
        if tk == (current_ticker or '').upper():
            continue
        if re.search(rf'\b{tk}\b', q_upper):
            return tk
    return None


# ═══════════════════════════════════════════════════════════════
# CONTEXT BUILDER  (FIXED — đơn vị giá đúng, nhãn vol rõ ràng)
# ═══════════════════════════════════════════════════════════════
def _build_context(ticker, r1, r2, r3, m1, m2, m3, df, ar_order):
    """Xây dict context đầy đủ với ĐƠN VỊ chính xác.

    Raw 'Close' trong df được lưu dưới dạng NGHÌN ĐỒNG (ví dụ 74.6 = 74,600đ).
    Tất cả số tiền xuất cho AI phải nhân 1000 để tránh nhầm lẫn.
    """
    ctx = {'ticker': ticker, 'p': ar_order}

    # ── MAPE (đơn vị: %) ────────────────────────────────────────
    try:
        ctx['mape'] = {
            'ar':   m1.get('MAPE', 0),
            'mlr':  m2.get('MAPE', 0),
            'cart': m3.get('MAPE', 0),
        }
    except Exception:
        pass

    # ── RMSE, MAE, R² (giúp bot trả lời chi tiết hơn) ──────────
    try:
        ctx['rmse'] = {
            'ar':   m1.get('RMSE', 0),
            'mlr':  m2.get('RMSE', 0),
            'cart': m3.get('RMSE', 0),
        }
        ctx['mae'] = {
            'ar':   m1.get('MAE', 0),
            'mlr':  m2.get('MAE', 0),
            'cart': m3.get('MAE', 0),
        }
        ctx['r2adj'] = {
            'ar':   m1.get('R2adj', 0),
            'mlr':  m2.get('R2adj', 0),
            'cart': m3.get('R2adj', 0),
        }
    except Exception:
        pass

    # ── Dự báo phiên tới (đã ở đơn vị nghìn đồng, nhân 1000 khi in) ──
    try:
        ctx['next_preds_vnd'] = {
            'ar':   float(r1.get('next_pred', 0)) * 1000,
            'mlr':  float(r2.get('next_pred', 0)) * 1000,
            'cart': float(r3.get('next_pred', 0)) * 1000,
        }
    except Exception:
        pass

    # ── Giá đóng cửa hiện tại (FIX: nhân 1000) ──────────────────
    try:
        ctx['close_vnd']     = float(df['Close'].iloc[-1]) * 1000  # VNĐ thật
        ctx['return_pct']    = float(df['Return'].iloc[-1]) if 'Return' in df.columns else 0.0
        ctx['date_last']     = str(df['Ngay'].iloc[-1])[:10]
    except Exception:
        pass

    # ── Annualized volatility 30 ngày (FIX: đổi tên cho rõ) ─────
    try:
        import numpy as np
        _ret = df['Return'].tail(30).dropna() if 'Return' in df.columns else []
        if len(_ret) > 0:
            # Return đã ở đơn vị %, nên std cũng %, annualize = ×√252
            ctx['annualized_vol_pct'] = float(_ret.std() * np.sqrt(252))
            ctx['daily_vol_pct']      = float(_ret.std())
    except Exception:
        pass

    # ── Ichimoku signal — ưu tiên session_state, fallback tự compute ──
    _ichi = st.session_state.get('ichimoku_summary')
    if not _ichi:
        # User chưa vào Dashboard/Signals → tự tính ngay từ df
        try:
            from data.ichimoku import (
                add_ichimoku, classify_primary_trend, detect_tk_cross,
                classify_trading_signal, classify_chikou_confirmation,
                classify_future_kumo, aggregate_signals, _donchian_mid, SENKOU_N,
            )
            import numpy as _np
            _df_i = add_ichimoku(df)
            _last = _df_i.iloc[-1]
            _close_now = float(_last['Close'])
            _kt = float(_last['Kumo_top']) if not _np.isnan(_last['Kumo_top']) else float('nan')
            _kb = float(_last['Kumo_bot']) if not _np.isnan(_last['Kumo_bot']) else float('nan')
            _prim, _ = classify_primary_trend(_close_now, _kt, _kb)
            _tk, _, _ = detect_tk_cross(_df_i['Tenkan'], _df_i['Kijun'])
            _trd, _ = classify_trading_signal(_tk, _prim)
            _c26 = float(_df_i['Close'].iloc[-27]) if len(_df_i) >= 27 else float('nan')
            _chk, _ = classify_chikou_confirmation(_close_now, _c26)
            _ten = float(_last['Tenkan']); _kij = float(_last['Kijun'])
            _fa = (_ten + _kij) / 2.0
            _fb = float(_donchian_mid(df['High'], df['Low'], SENKOU_N).iloc[-1])
            _fut, _ = classify_future_kumo(_fa, _fb)
            _ov_code, _ov_label, _score = aggregate_signals(_prim, _trd, _chk, _fut)
            _ichi = {
                'label':       _ov_label,
                'code':        _ov_code,
                'score':       int(_score),
                'primary':     _prim,
                'trading':     _trd,
                'chikou':      _chk,
                'future_kumo': _fut,
            }
            # Cache cho lần sau
            st.session_state['ichimoku_summary'] = _ichi
        except Exception:
            _ichi = None
    if _ichi:
        ctx['ichimoku'] = _ichi

    return ctx


# ═══════════════════════════════════════════════════════════════
# NAVIGATION HINTS
# ═══════════════════════════════════════════════════════════════
def _detect_navigation_intent(query: str) -> str:
    q = query.lower()
    nav_map = {
        'Dashboard Tổng quan': ['dashboard', 'tổng quan', 'overview',
                                 'biểu đồ giá', 'chart giá', 'giá đóng cửa', 'price chart',
                                 'kpi', 'tín hiệu tổng'],
        'Phân tích Chi tiết':  ['phân tích chi tiết', 'analysis detail',
                                 'phương trình', 'equation', 'hệ số', 'coefficient',
                                 'cây cart', 'decision tree visualization', 'scatter'],
        'Lịch sử & Dữ liệu':   ['lịch sử', 'history', 'dữ liệu thô', 'raw data',
                                 'bảng dữ liệu', 'data table', 'csv',
                                 'dữ liệu lấy từ', 'nguồn dữ liệu', 'data source'],
        'Tín hiệu & Cảnh báo': ['tín hiệu chi tiết', 'alert', 'cảnh báo',
                                 'ichimoku đầy đủ', 'kumo chi tiết'],
        'Danh mục Đầu tư':     ['danh mục', 'portfolio', 'so sánh ticker',
                                 'fpt hpg vnm', 'cả 3 mã', 'correlation'],
    }
    for page, kws in nav_map.items():
        if any(kw in q for kw in kws):
            return page
    return None


# ═══════════════════════════════════════════════════════════════
# CONTEXT FALLBACK — khi AI fail, build câu trả lời từ số liệu thật
# ═══════════════════════════════════════════════════════════════
def _strip_diacritics_simple(s: str) -> str:
    """Strip dấu tiếng Việt đơn giản (cho keyword match)."""
    import unicodedata
    s = s.replace('đ', 'd').replace('Đ', 'D')
    return ''.join(c for c in unicodedata.normalize('NFKD', s)
                   if not unicodedata.combining(c))


def _context_based_answer(query: str, context: dict, lang: str) -> str | None:
    """Sinh câu trả lời từ context khi AI không khả dụng.
    Trả về None nếu không match intent nào → caller fallback tiếp.

    FIX v6: Diacritic-insensitive keyword match — user gõ "phan tich FPT" cũng match.
    Bổ sung Ichimoku + RMSE/MAE/R²adj khi context có sẵn.
    """
    if not context:
        return None
    # Strip diacritics → 'phân tích' và 'phan tich' đều match
    q = _strip_diacritics_simple(query.lower())
    ticker = context.get('ticker', '')

    _forecast_kw = ['du bao', 'du doan', 'forecast', 'predict', 'phien toi',
                    'phien ke tiep', 'next session', 'next day', 'gia ngay mai',
                    'tomorrow', 'phien sau']
    _price_kw = ['gia', 'price', 'closing', 'dong cua', 'hien tai', 'current',
                 'bao nhieu']
    _mape_kw = ['mape', 'rmse', 'mae', 'r2adj', 'do chinh xac', 'accuracy',
                'sai so', 'error', 'hieu nang', 'performance']
    _analyze_kw = ['phan tich', 'analyze', 'analysis', 'tinh hinh', 'situation',
                   'danh gia', 'assess', 'tong quan', 'overview', 'review',
                   'tom tat', 'summary']
    _signal_kw = ['ichimoku', 'tin hieu', 'signal', 'kumo', 'tenkan', 'kijun',
                  'mua hay ban', 'should i buy', 'should i sell',
                  'nen mua', 'nen ban', 'co nen mua', 'co nen ban',
                  'buy or sell', 'hold or sell']

    is_forecast = any(k in q for k in _forecast_kw)
    is_price    = any(k in q for k in _price_kw)
    is_mape     = any(k in q for k in _mape_kw)
    is_analyze  = any(k in q for k in _analyze_kw)
    is_signal   = any(k in q for k in _signal_kw)

    if not (is_forecast or is_price or is_mape or is_analyze or is_signal):
        return None

    lines = []
    if lang == 'EN':
        lines.append(f'### {ticker} — Quick snapshot from current data')
    else:
        lines.append(f'### {ticker} — Tóm tắt nhanh từ dữ liệu hiện tại')

    if 'close_vnd' in context:
        price = context['close_vnd']
        if lang == 'EN':
            lines.append(f'- **Latest close:** `{price:,.0f} VND`')
        else:
            lines.append(f'- **Giá đóng cửa gần nhất:** `{price:,.0f} đ`')

    if 'return_pct' in context:
        r = context['return_pct']
        arrow = '▲' if r >= 0 else '▼'
        if lang == 'EN':
            lines.append(f'- **Session change:** {arrow} {r:+.2f}%')
        else:
            lines.append(f'- **Biến động phiên:** {arrow} {r:+.2f}%')

    if 'next_preds_vnd' in context:
        np_ = context['next_preds_vnd']
        if lang == 'EN':
            lines.append('- **Next-session forecast** (3 models):')
        else:
            lines.append('- **Dự báo phiên kế tiếp** (3 mô hình):')
        for k, label in [('ar', 'AR'), ('mlr', 'MLR'), ('cart', 'CART')]:
            if k in np_:
                lines.append(f'  - {label}: `{np_[k]:,.0f} ' +
                             ('VND`' if lang == 'EN' else 'đ`'))

    if 'mape' in context:
        m = context['mape']
        if lang == 'EN':
            lines.append('- **Test MAPE** (lower is better):')
        else:
            lines.append('- **MAPE trên Test** (thấp hơn tốt hơn):')
        for k, label in [('ar', 'AR'), ('mlr', 'MLR'), ('cart', 'CART')]:
            if k in m:
                lines.append(f'  - {label}: `{m[k]:.2f}%`')

    # Ichimoku signal — quan trọng cho buy/sell queries
    if is_signal and 'ichimoku' in context:
        ichi = context['ichimoku']
        if lang == 'EN':
            lines.append(f'- **Ichimoku signal:** {ichi.get("label","?")} '
                         f'(score {ichi.get("score",0)}/5)')
        else:
            lines.append(f'- **Tín hiệu Ichimoku:** {ichi.get("label","?")} '
                         f'(score {ichi.get("score",0)}/5)')

    # Buy/sell guard
    if any(k in q for k in ['mua', 'ban', 'buy', 'sell', 'hold', 'nen']):
        if lang == 'EN':
            lines.append('\n> ⚠️ **Note:** This is research output, academic reference only — '
                         'not investment advice.')
        else:
            lines.append('\n> ⚠️ **Lưu ý:** đây là kết quả NCKH, chỉ tham khảo học thuật, '
                         'không phải tư vấn đầu tư.')

    if lang == 'EN':
        lines.append('\n*AI is temporarily unavailable — showing raw numbers from the app. '
                     'Try again in a few seconds for a natural-language analysis.*')
    else:
        lines.append('\n*AI tạm thời không khả dụng — đang hiển thị số liệu thô từ app. '
                     'Thử lại sau vài giây để nhận phân tích đầy đủ.*')

    return '\n'.join(lines) if len(lines) > 1 else None


# ═══════════════════════════════════════════════════════════════
# AI-DOWN MESSAGE — 1 dòng honest thay vì template dài
# ═══════════════════════════════════════════════════════════════
def _ai_down_msg(lang: str, wait_sec: int = 0) -> str:
    """Message thân thiện khi AI không reply — KHÔNG show error code cho user."""
    err_low = st.session_state.get('_last_gemini_error', '').lower()
    if wait_sec <= 0:
        wait_sec = int(st.session_state.get('_last_gemini_retry_s', 0))

    is_daily = any(k in err_low for k in ['per day', 'daily', 'generate_requests_per_day'])
    is_long_wait = wait_sec > 120 or is_daily

    if lang == 'EN':
        if is_long_wait:
            return ("I've reached today's chat quota. "
                    "Please come back tomorrow — I'll be ready to chat again then.")
        if wait_sec:
            return (f"I'm a bit overloaded — give me about **{wait_sec}s** "
                    f"then send your question again.")
        return "Having a small hiccup — please try again in a few seconds."
    else:
        if is_long_wait:
            return ("Mình đã dùng hết lượt trò chuyện cho hôm nay rồi. "
                    "Bạn quay lại ngày mai giúp mình nhé — lúc đó sẽ trả lời lại đầy đủ.")
        if wait_sec:
            return (f"Mình đang hơi quá tải, bạn cho mình khoảng **{wait_sec}s** "
                    f"rồi gửi lại câu hỏi nhé.")
        return "Mình đang trục trặc chút — bạn thử gửi lại sau vài giây nhé."


# ═══════════════════════════════════════════════════════════════
# QUERY CLASSIFIER — câu hỏi phụ thuộc dữ liệu số → KHÔNG cache
# ═══════════════════════════════════════════════════════════════
def _is_data_dependent(query: str) -> bool:
    """Các query chứa dữ liệu số động (giá, volatility, prediction) không nên cache
    vì giá thay đổi hàng ngày → tránh trả lời lỗi thời cho hội đồng.

    v6: Strip diacritics → 'phan tich' và 'phân tích' đều match.
    Loại trừ theory question (vd "MAPE là gì") — không phải data-dep.
    """
    q = _strip_diacritics_simple((query or '').lower())
    # Nếu là theory query (có "la gi", "la sao", "explain"...) → KHÔNG data-dep
    # ngay cả khi mention metric name, vì user đang hỏi định nghĩa.
    theory_indicators = ['la gi', 'la sao', 'nghia la', 'cong thuc', 'phuong trinh',
                         'giai thich', 'dinh nghia', 'y nghia', 'thang danh gia',
                         'what is', 'what are', 'how does', 'how do', 'explain',
                         'meaning', 'formula', 'equation', 'definition']
    if any(t in q for t in theory_indicators):
        return False

    data_kws = [
        'gia', 'price', 'dong cua', 'closing',
        'du bao', 'forecast', 'predict',
        'bien dong', 'volatility',
        'mape', 'rmse', 'mae',
        'phan tich', 'analyze', 'analysis',
        'phien toi', 'next session', 'next day',
        'hom nay', 'today', 'current',
        'tinh hinh', 'situation',
        'tom tat', 'summary', 'review', 'tong quan', 'overview',
        'nen mua', 'nen ban', 'should i', 'buy', 'sell',
    ]
    return any(kw in q for kw in data_kws)


# ═══════════════════════════════════════════════════════════════
# QUERY PROCESSING — logic rõ ràng, tách riêng khỏi UI
# ═══════════════════════════════════════════════════════════════
def _process_query(query: str, context: dict, ar_order: int,
                   ticker: str, df, lang: str, ai_ok: bool) -> tuple:
    """
    Process 1 query, return (response_text, diagram_html).

    Logic priority:
      1. Citation request → references + AI intro (AI viết intro tự nhiên)
      2. Data-dependent query → SKIP cache, gọi AI trực tiếp
      3. Mọi câu hỏi khác → cache → AI (Gemini) → rule fallback nếu AI fail

    Không còn shortcut template cho greeting/intro — mọi câu đều qua AI để có
    câu trả lời tự nhiên theo ngữ cảnh (ticker, giá, MAPE hiện tại).
    """
    from core.references import detect_citation_request, get_references_by_topic, get_all_references
    from core import chatbot_cache as cache

    response = None
    diagram_html = None

    is_citation, citation_topic = detect_citation_request(query)

    # ── 1. CITATION REQUEST ─────────────────────────────────────
    if is_citation:
        refs = (get_references_by_topic(citation_topic, lang=lang)
                if citation_topic else get_all_references(lang=lang))
        response = refs
        if ai_ok:
            try:
                with st.spinner('● ● ● ' + t('chatbot.thinking')):
                    intro = ask_gemini(
                        f'Viết đoạn giới thiệu ngắn 2-3 câu về chủ đề '
                        f'"{citation_topic or "tổng quan"}" trước khi liệt kê tài liệu tham khảo.',
                        context=context, lang=lang,
                    )
                response = f'{intro}\n\n---\n\n{refs}'
            except Exception:
                pass
        return response, diagram_html

    # ── 2. DATA-DEPENDENT QUERIES — BỎ QUA CACHE ───────────────
    _is_data_q = _is_data_dependent(query)

    # ── 3. CACHE CHECK (chỉ cho câu lý thuyết) ─────────────────
    if not _is_data_q:
        cached = cache.get(query, context, lang)
        if cached:
            return cached, diagram_html

    # ── 4. GỌI AI (với self-review gated) — luôn cho AI trả lời thật ─
    if ai_ok:
        ai_resp = _ai_answer_with_review(query, context, lang)
        if ai_resp:
            if not _is_data_q:
                cache.set(query, context, ai_resp, lang)
            return ai_resp, diagram_html

        # AI đã thử hết cách vẫn fail → thử data-context (numbers từ app)
        data_ans = _context_based_answer(query, context, lang)
        if data_ans:
            return data_ans, diagram_html
        return _ai_down_msg(lang), diagram_html

    # ── 5. AI không khả dụng (thiếu API key) ──────────────────
    data_ans = _context_based_answer(query, context, lang)
    if data_ans:
        return data_ans, diagram_html
    return _ai_down_msg(lang), diagram_html


def _is_theory_query(query: str) -> bool:
    """Câu hỏi lý thuyết thuần — KHÔNG cần context (giá, MAPE, etc).
    Trả lời có thể share cache giữa các ticker → tiết kiệm quota tối đa.

    v6: Strip diacritics → 'la gi' / 'là gì' đều match.
    """
    q = _strip_diacritics_simple((query or '').lower())
    theory_kws = [
        'la gi', 'la sao', 'nghia la', 'hoat dong', 'cong thuc', 'phuong trinh',
        'giai thich', 'dinh nghia', 'khac nhau', 'khac gi', 'so sanh',
        'nen chon', 'khi nao', 'tai sao', 'y nghia', 'thang danh gia',
        'what is', 'what are', 'how does', 'how do', 'explain', 'meaning',
        'difference', 'compare', 'formula', 'equation', 'when to use',
        'why', 'definition',
    ]
    # Exclude nếu có data-specific keywords (giá, dự báo, ticker name)
    data_kws = ['gia', 'price', 'du bao', 'forecast', 'phan tich',
                'analyze', 'analysis', 'hien tai', 'current',
                'phien toi', 'next session', 'fpt', 'hpg', 'vnm',
                'tom tat', 'review', 'tong quan']
    has_theory = any(k in q for k in theory_kws)
    has_data   = any(k in q for k in data_kws)
    return has_theory and not has_data


def _get_recent_history(max_turns: int = 2) -> list:
    """Lấy max_turns gần nhất từ active conversation, bỏ tin user cuối (current).

    Returns: list of {'role': 'user'|'assistant', 'content': str}.
    Empty nếu không có active conv hoặc lỗi.
    """
    try:
        from core import chat_history as ch
        active_id = st.session_state.get('active_conv_id')
        if not active_id:
            return []
        conv = ch.get_conversation(active_id) or {}
        msgs = conv.get('messages') or []
        # Tin cuối cùng là user message vừa add (current query) → bỏ
        if msgs and msgs[-1].get('role') == 'user':
            msgs = msgs[:-1]
        # Lấy max_turns × 2 messages gần nhất
        return msgs[-(max_turns * 2):]
    except Exception:
        return []


def _format_history_prefix(history: list, lang: str) -> str:
    """Format history thành text prefix gắn vào prompt (portable Gemini/Groq)."""
    if not history:
        return ''
    lines = []
    for h in history:
        role = h.get('role', 'user')
        content = (h.get('content') or '').strip()
        if not content:
            continue
        # Truncate per-message để tránh prompt quá dài
        if len(content) > 600:
            content = content[:600] + '...'
        if role == 'assistant':
            label = 'Bot' if lang == 'VI' else 'Bot'
        else:
            label = 'User' if lang == 'VI' else 'User'
        lines.append(f'[{label}]: {content}')
    if not lines:
        return ''
    if lang == 'EN':
        header = '## RECENT CONVERSATION (most recent at bottom):'
    else:
        header = '## HỘI THOẠI GẦN ĐÂY (gần nhất ở dưới):'
    return header + '\n' + '\n'.join(lines) + '\n\n'


# ═══════════════════════════════════════════════════════════════
# Phase-3 simplification (2026-05-06):
#   - Self-review pattern (_ai_answer_with_review / _build_critique_prompt /
#     _build_refine_prompt / _should_self_review) → REMOVED.
#   - Slim Gemini retry, Groq 8B retry, countdown retry → REMOVED.
#   - Retry chain is now: Gemini full → Groq 70B → polite-error message.
# Backwards-compat shims kept for: _ai_answer_with_review (= retry now),
# _try_groq, _countdown_and_retry — chatbot.py imports those names.
# ═══════════════════════════════════════════════════════════════

ENABLE_SELF_REVIEW = False  # Phase-3 disabled


def _ai_answer_with_review(query: str, context: dict, lang: str):
    """Backwards-compat shim. Phase-3 dropped self-review; this just calls
    the simplified retry chain so the chatbot.py import path stays valid."""
    return _ai_answer_with_retry(query, context, lang)


def _ai_answer_with_retry(query: str, context: dict, lang: str):
    """Simple two-step retry chain.

      1. Gemini (full system prompt, real model)
      2. Groq llama-3.3-70b-versatile (only if GROQ_API_KEY configured)
      3. Otherwise return None — caller surfaces a polite error.

    Conversation history (last 2 turns) is prefixed to the prompt so the
    bot remembers context across turns (memory unchanged from Phase-2)."""
    _groq_ready = is_groq_available()

    # Theory queries → drop ticker context (saves tokens, lets cache share
    # across tickers). Only applies to data-independent questions.
    _ctx_to_send = None if _is_theory_query(query) else context

    _history = _get_recent_history(max_turns=2)
    _history_prefix = _format_history_prefix(_history, lang)
    _query_with_history = (_history_prefix + query) if _history_prefix else query

    # ── Attempt 1: Gemini ──
    try:
        with st.spinner('● ● ● ' + t('chatbot.thinking')):
            resp = ask_gemini(_query_with_history, context=_ctx_to_send, lang=lang)
        if resp and resp.strip():
            return resp
        _log('[Chatbot] Gemini empty response')
    except QuotaExhaustedError:
        _log('[Chatbot] Gemini daily quota exhausted')
        if _groq_ready:
            r = _try_groq(_query_with_history, _ctx_to_send, lang)
            if r:
                return r
        return None
    except RateLimitError as e:
        _wait = int(getattr(e, 'wait_seconds', 30) or 30)
        st.session_state['_last_gemini_retry_s'] = max(5, min(_wait, 60))
        st.session_state['_last_gemini_error'] = str(e)
        _log(f'[Chatbot] Gemini rate limited (~{_wait}s)')
        if _groq_ready:
            r = _try_groq(_query_with_history, _ctx_to_send, lang)
            if r:
                return r
        return None
    except Exception as e:
        _log(f'[Chatbot] Gemini error: {str(e)[:150]}')

    # ── Attempt 2: Groq llama-3.3-70b ──
    if _groq_ready:
        r = _try_groq(_query_with_history, _ctx_to_send, lang)
        if r:
            return r
    return None


def _try_groq(query: str, context: dict, lang: str):
    """Single shot: Groq llama-3.3-70b-versatile only.

    8B fallback removed in Phase-3 — quality of 70B is already strong and
    Groq's free-tier rate limit on 70B is generous enough for chat usage.
    """
    try:
        with st.spinner('● ● ● ' + t('chatbot.thinking')):
            resp = ask_groq(query, context=context, lang=lang)
        if resp and resp.strip():
            _log('[Chatbot] Groq 70B OK')
            return resp
    except RateLimitError:
        _log('[Chatbot] Groq rate limited')
    except Exception as e:
        _log(f'[Chatbot] Groq error: {str(e)[:150]}')
    return None


def _countdown_and_retry(query: str, context: dict, lang: str, wait_seconds: int):
    """Backwards-compat shim. Phase-3 removed countdown UX; this just calls
    the simplified retry chain (no sleep)."""
    return _ai_answer_with_retry(query, context, lang)
