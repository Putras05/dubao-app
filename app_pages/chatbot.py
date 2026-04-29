"""Chatbot AI — clean rewrite với logic rõ ràng.

FIX 2026-04-23:
- C3: Sửa đơn vị giá trong context (trước: 74 đ, giờ: 74,600 đ)
- C5: Đổi nhãn 'volatility_30d' → 'annualized_vol_30d' cho rõ ràng
- C1+C2: Giảm reliance vào cache cho câu hỏi chứa dữ liệu số (xem chatbot_cache.py)
- A1: CSS chatbot tại đây dùng !important với cao mức specificity để thắng default
"""
import streamlit as st
import time
from core.i18n import t


def _log(msg: str):
    """Safe logging — tránh UnicodeEncodeError trên Windows CMD."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode('ascii'))
from core.chatbot_rules import get_rule_answer
from core.chatbot_ai import ask_gemini, is_ai_available, RateLimitError, QuotaExhaustedError
from core.chatbot_groq import ask_groq, is_groq_available
from core.references import detect_citation_request, get_references_by_topic, get_all_references
from core import chat_history as ch
from core import chatbot_cache as cache


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


def _render_nav_hint(target_page: str, T: dict) -> str:
    """Trả markdown plain — pipe qua _md_to_html escape an toàn (không HTML raw)."""
    _page_icons = {
        'Dashboard Tổng quan':  '◉',
        'Phân tích Chi tiết':   '◈',
        'Lịch sử & Dữ liệu':    '◎',
        'Tín hiệu & Cảnh báo':  '◬',
        'Danh mục Đầu tư':      '◐',
    }
    _icon_char = _page_icons.get(target_page, '→')
    return (
        f'\n---\n'
        f'**{_icon_char} Gợi ý trang phù hợp:** {target_page}\n\n'
        f'_Chọn ở menu bên trái để xem chi tiết._'
    )


# ═══════════════════════════════════════════════════════════════
# SVG ICONS — tự build, không dùng emoji
# ═══════════════════════════════════════════════════════════════
def _icon_search(color: str = '#93C5FD', size: int = 12) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="2.5" stroke-linecap="round" '
        f'stroke-linejoin="round" style="flex-shrink:0;display:inline-block;vertical-align:middle">'
        f'<circle cx="11" cy="11" r="7"/><path d="m20 20-3-3"/></svg>'
    )


def _icon_pencil(color: str = '#93C5FD', size: int = 12) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="2.5" stroke-linecap="round" '
        f'stroke-linejoin="round" style="flex-shrink:0;display:inline-block;vertical-align:middle">'
        f'<path d="M17 3a2.83 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>'
        f'<path d="m15 5 4 4"/></svg>'
    )


def _icon_trash(color: str = '#93C5FD', size: int = 12) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="2.5" stroke-linecap="round" '
        f'stroke-linejoin="round" style="flex-shrink:0;display:inline-block;vertical-align:middle">'
        f'<path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>'
        f'<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/>'
        f'<line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/>'
        f'</svg>'
    )


def _icon_download(color: str = '#93C5FD', size: int = 12) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="2.5" stroke-linecap="round" '
        f'stroke-linejoin="round" style="flex-shrink:0;display:inline-block;vertical-align:middle">'
        f'<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
        f'<polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>'
        f'</svg>'
    )


def _icon_chevron(direction: str = 'up', color: str = '#93C5FD', size: int = 12) -> str:
    paths = {
        'up':    'polyline points="18 15 12 9 6 15"',
        'down':  'polyline points="6 9 12 15 18 9"',
        'left':  'polyline points="15 18 9 12 15 6"',
        'right': 'polyline points="9 18 15 12 9 6"',
    }
    p = paths.get(direction, paths['up'])
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="2.5" stroke-linecap="round" '
        f'stroke-linejoin="round" style="flex-shrink:0;display:inline-block;vertical-align:middle">'
        f'<{p}/></svg>'
    )


def _highlight_in_html(html_content: str, query: str, accent: str = '#FBBF24',
                       start_offset: int = 0, active_idx: int = -1) -> tuple:
    """Highlight từ khoá trong HTML content — không bẻ HTML tags.

    Mỗi match nhận `id="match-{global_idx}"` (global_idx = start_offset + local_idx).
    Match có global_idx == active_idx sẽ có thêm class `match-active` + màu đậm.

    Returns (html, match_count).
    """
    if not query or not query.strip():
        return html_content, 0

    import re
    q_escaped = re.escape(query.strip())
    tag_pattern = re.compile(r'(<[^>]+>)')
    parts = tag_pattern.split(html_content)

    base_style = (
        f'background:{accent};color:#0F172A;padding:0 3px;'
        f'border-radius:3px;font-weight:700;box-decoration-break:clone;'
        f'-webkit-box-decoration-break:clone'
    )
    active_style = (
        'background:#F97316;color:#FFFFFF;padding:0 3px;'
        'border-radius:3px;font-weight:800;box-decoration-break:clone;'
        '-webkit-box-decoration-break:clone;'
        'box-shadow:0 0 0 2px rgba(249,115,22,0.35)'
    )
    query_pattern = re.compile(f'({q_escaped})', re.IGNORECASE)

    counter = [start_offset]
    def _replace(m):
        idx = counter[0]
        counter[0] += 1
        is_active = (idx == active_idx)
        cls = 'msg-hl match-active' if is_active else 'msg-hl'
        style = active_style if is_active else base_style
        return f'<mark id="match-{idx}" class="{cls}" style="{style}">{m.group(1)}</mark>'

    for i, part in enumerate(parts):
        if part.startswith('<'):
            continue
        if query_pattern.search(part):
            parts[i] = query_pattern.sub(_replace, part)

    total_matches = counter[0] - start_offset
    return ''.join(parts), total_matches


# ═══════════════════════════════════════════════════════════════
# STDLIB MARKDOWN → HTML CONVERTER
# ═══════════════════════════════════════════════════════════════
def _inline_md(text: str) -> str:
    """Convert inline markdown (**bold**, *italic*, `code`) to HTML. Input is already html-escaped."""
    import re
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*([^*\n]+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'`([^`\n]+)`', r'<code>\1</code>', text)
    return text


def _strip_legacy_html(text: str) -> str:
    """Remove legacy raw-HTML blocks (`<div style="...">…</div>`) persisted vào
    chat history TRƯỚC commit 77d484d. Message mới đã là markdown plain → regex
    no-op. Diagram đi theo field `diagram` riêng, KHÔNG nằm trong content.
    """
    import re
    if not text or '<' not in text:
        return text
    text = re.sub(r'<(div|span|a|section|p)\b[^>]*>.*?</\1>',
                  '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+/?>', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _md_to_html(text: str) -> str:
    """Convert markdown text to safe HTML using stdlib only (re + html)."""
    import re
    import html as _hlib

    text = _strip_legacy_html(text)
    lines = text.split('\n')
    out = []
    in_ul = False
    in_ol = False
    ol_counter = 1

    for line in lines:
        raw = line

        # Headings
        if re.match(r'^#{4}\s', raw):
            if in_ul: out.append('</ul>'); in_ul = False
            if in_ol: out.append('</ol>'); in_ol = False; ol_counter = 1
            out.append(f'<h4 style="margin:.4em 0 .2em">{_inline_md(_hlib.escape(raw[5:]))}</h4>')
        elif re.match(r'^#{3}\s', raw):
            if in_ul: out.append('</ul>'); in_ul = False
            if in_ol: out.append('</ol>'); in_ol = False; ol_counter = 1
            out.append(f'<h3 style="margin:.5em 0 .25em">{_inline_md(_hlib.escape(raw[4:]))}</h3>')
        elif re.match(r'^#{2}\s', raw):
            if in_ul: out.append('</ul>'); in_ul = False
            if in_ol: out.append('</ol>'); in_ol = False; ol_counter = 1
            out.append(f'<h2 style="margin:.6em 0 .3em">{_inline_md(_hlib.escape(raw[3:]))}</h2>')
        elif re.match(r'^#{1}\s', raw):
            if in_ul: out.append('</ul>'); in_ul = False
            if in_ol: out.append('</ol>'); in_ol = False; ol_counter = 1
            out.append(f'<h1 style="margin:.6em 0 .3em">{_inline_md(_hlib.escape(raw[2:]))}</h1>')

        # Horizontal rule
        elif re.match(r'^[-*_]{3,}$', raw.strip()):
            if in_ul: out.append('</ul>'); in_ul = False
            if in_ol: out.append('</ol>'); in_ol = False; ol_counter = 1
            out.append('<hr style="border:none;border-top:1px solid rgba(100,116,139,.2);margin:.5em 0">')

        # Unordered list
        elif re.match(r'^[-*+]\s', raw):
            if in_ol: out.append('</ol>'); in_ol = False; ol_counter = 1
            if not in_ul: out.append('<ul style="margin:.3em 0;padding-left:1.4em">'); in_ul = True
            out.append(f'<li>{_inline_md(_hlib.escape(raw[2:]))}</li>')

        # Ordered list
        elif re.match(r'^\d+\.\s', raw):
            if in_ul: out.append('</ul>'); in_ul = False
            m = re.match(r'^\d+\.\s(.*)', raw)
            if not in_ol: out.append('<ol style="margin:.3em 0;padding-left:1.4em">'); in_ol = True
            out.append(f'<li>{_inline_md(_hlib.escape(m.group(1)))}</li>')

        # Blank line
        elif raw.strip() == '':
            if in_ul: out.append('</ul>'); in_ul = False
            if in_ol: out.append('</ol>'); in_ol = False; ol_counter = 1
            out.append('')

        # Normal paragraph line
        else:
            if in_ul: out.append('</ul>'); in_ul = False
            if in_ol: out.append('</ol>'); in_ol = False; ol_counter = 1
            out.append(f'<p style="margin:.25em 0">{_inline_md(_hlib.escape(raw))}</p>')

    if in_ul: out.append('</ul>')
    if in_ol: out.append('</ol>')
    return '\n'.join(out)


# ═══════════════════════════════════════════════════════════════
# WELCOME SCREEN — hiện khi conversation chưa có message nào
# ═══════════════════════════════════════════════════════════════
def _render_welcome_screen(T: dict, lang: str, ticker: str) -> None:
    """Welcome card + 4 suggested question chips. Click chip = auto-gửi câu hỏi."""
    _accent = T.get('accent', '#1565C0')
    _muted  = T.get('text_muted', '#94A3B8')
    _fg     = T.get('text_primary', '#0F172A')
    _bg_el  = T.get('bg_elevated', '#F1F5F9')
    _brd    = T.get('border', '#E2E8F0')

    if lang == 'EN':
        title    = 'Hi — what would you like to explore?'
        # Non-breaking space ( ) giữa "analyze" và ticker → không tách dòng lẻ
        subtitle = f'I can help with forecasting models, metrics, Ichimoku signals, or analyze **{ticker}**.'
        suggestions = [
            ('icon_brain',  'Theory',   f'How does AR(p) work?'),
            ('icon_chart',  'Analysis', f'Analyze {ticker} for me'),
            ('icon_gauge',  'Metrics',  'What is a good MAPE value?'),
            ('icon_signal', 'Signals',  'Explain Ichimoku 4-tier system'),
        ]
    else:
        title    = 'Chào bạn — hôm nay tìm hiểu gì nào?'
        # Non-breaking space ( ) giữa "phân tích" và ticker → không rớt "FPT" xuống dòng
        subtitle = f'Mình hỗ trợ mô hình dự báo, chỉ số đánh giá, tín hiệu Ichimoku, hoặc phân tích **{ticker}**.'
        suggestions = [
            ('icon_brain',  'Lý thuyết',  f'AR(p) hoạt động thế nào?'),
            ('icon_chart',  'Phân tích',  f'Phân tích {ticker} cho mình'),
            ('icon_gauge',  'Chỉ số',     'MAPE bao nhiêu là tốt?'),
            ('icon_signal', 'Tín hiệu',   'Giải thích Ichimoku 4 tầng'),
        ]

    # SVG icons tự build cho từng chip
    _svgs = {
        'icon_brain': ('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" '
                       'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
                       'stroke-linejoin="round">'
                       '<path d="M12 2a3 3 0 0 0-3 3v.5a3 3 0 0 0-3 3 3 3 0 0 0 .5 5A3 3 0 0 0 9 17v.5a3 3 0 0 0 3 3 3 3 0 0 0 3-3V17a3 3 0 0 0 2.5-3.5 3 3 0 0 0 .5-5 3 3 0 0 0-3-3V5a3 3 0 0 0-3-3z"/>'
                       '<path d="M12 5v15"/></svg>'),
        'icon_chart': ('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" '
                       'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
                       'stroke-linejoin="round">'
                       '<path d="M3 3v18h18"/>'
                       '<polyline points="7 15 12 10 16 14 21 7"/>'
                       '</svg>'),
        'icon_gauge': ('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" '
                       'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
                       'stroke-linejoin="round">'
                       '<path d="M12 14 8 10"/>'
                       '<path d="M3.34 19a10 10 0 1 1 17.32 0"/>'
                       '</svg>'),
        'icon_signal':('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" '
                       'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
                       'stroke-linejoin="round">'
                       '<path d="M2 20h.01"/><path d="M7 20v-4"/>'
                       '<path d="M12 20v-8"/><path d="M17 20V8"/>'
                       '<path d="M22 4v16"/></svg>'),
    }

    # Hero card
    st.markdown(
        f'<div style="text-align:center;padding:40px 24px 20px;">'
        f'<div style="display:inline-flex;align-items:center;justify-content:center;'
        f'width:56px;height:56px;border-radius:16px;margin-bottom:16px;'
        f'background:linear-gradient(135deg,{_accent} 0%,#7C3AED 100%);'
        f'box-shadow:0 8px 24px {_accent}40;color:#fff">'
        f'<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        f'<path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/>'
        f'<path d="M2 14h2M20 14h2M15 13v2M9 13v2"/></svg></div>'
        f'<div style="font-size:20px;font-weight:800;color:{_fg};margin-bottom:8px;'
        f'letter-spacing:-0.3px">{title}</div>'
        f'<div style="font-size:13px;color:{_muted};max-width:560px;margin:0 auto 28px;'
        f'text-wrap:balance;-webkit-text-wrap:balance">'
        f'{_md_to_html(subtitle)}</div>'
        f'</div>',
        unsafe_allow_html=True)

    # 4 suggestion chips — 2×2 grid. Mỗi chip = st.button với label combined.
    _c1, _c2 = st.columns(2)
    _c3, _c4 = st.columns(2)
    _cols = [_c1, _c2, _c3, _c4]

    for i, (col, (ico_key, label, question)) in enumerate(zip(_cols, suggestions)):
        with col:
            # Label button = "LABEL • question" — CSS sẽ style thành card 2 dòng
            btn_label = f'{label}\n{question}'
            if st.button(btn_label, key=f'welcome_chip_{i}',
                         use_container_width=True):
                st.session_state['_pending_welcome_query'] = question
                st.rerun()


# ═══════════════════════════════════════════════════════════════
# MESSAGE RENDERING
# ═══════════════════════════════════════════════════════════════
def _render_user_message(content: str, timestamp: str, T: dict,
                         search_query: str = '', msg_idx: int = 0,
                         match_offset: int = 0, active_match: int = -1) -> int:
    """Render tin nhắn user. Return số match của search_query trong tin này."""
    _bg   = T.get('accent', '#1565C0')
    _dark = T.get('is_dark', False)
    _grad = (f'linear-gradient(135deg,{_bg} 0%,#1E40AF 100%)' if not _dark
             else f'linear-gradient(135deg,#1E40AF 0%,{_bg} 100%)')
    _ts   = ch.format_timestamp(timestamp) if timestamp else ''
    import html as _h
    _escaped = _h.escape(str(content))

    _match_count = 0
    if search_query and search_query.strip():
        _escaped, _match_count = _highlight_in_html(
            _escaped, search_query,
            start_offset=match_offset, active_idx=active_match)

    st.markdown(
        f'<div class="chat-row chat-user" id="msg-{msg_idx}">'
        f'<div class="chat-avatar" style="background:linear-gradient(135deg,#334155 0%,#475569 100%)'
        f';box-shadow:0 2px 8px rgba(0,0,0,.20)">YOU</div>'
        f'<div class="chat-bubble-wrap">'
        f'<div class="chat-meta" style="justify-content:flex-end">'
        f'<span class="chat-time">{_ts}</span>'
        f'<span class="chat-label">{t("chatbot.user_label")}</span></div>'
        f'<div class="chat-bubble chat-bubble-user" '
        f'style="background:{_grad};color:#FFFFFF">{_escaped}</div>'
        f'</div></div>',
        unsafe_allow_html=True)
    return _match_count


def _render_bot_message(content: str, timestamp: str, T: dict, diagram_html: str = None,
                        search_query: str = '', msg_idx: int = 0,
                        match_offset: int = 0, active_match: int = -1,
                        show_actions: bool = True, is_last_bot: bool = False) -> int:
    """Render tin nhắn bot với copy/regenerate buttons. Return số match."""
    _ts     = ch.format_timestamp(timestamp) if timestamp else ''
    _bg     = T.get('bg_elevated', '#F8FAFC')
    _border = T.get('border_strong', '#CBD5E1')
    _stripe = T.get('accent', '#1565C0')
    _fg     = T.get('text_primary', '#0F172A')
    _muted  = T.get('text_muted', '#94A3B8')

    _content_html = _md_to_html(content)
    _diag = diagram_html or ''

    _match_count = 0
    if search_query and search_query.strip():
        _content_html, _match_count = _highlight_in_html(
            _content_html, search_query,
            start_offset=match_offset, active_idx=active_match)

    # Copy/regenerate action icons (SVG tự build) — hide khi đang search để gọn
    _actions_html = ''
    if show_actions and not (search_query and search_query.strip()):
        import html as _h
        _safe = _h.escape(content or '').replace('\n', '\\n').replace('"', '&quot;')
        _svg_copy = (
            '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
            'stroke-linejoin="round">'
            '<rect width="13" height="13" x="8" y="8" rx="2"/>'
            '<path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>'
            '</svg>'
        )
        _svg_regen = (
            '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
            'stroke-linejoin="round">'
            '<path d="M3 12a9 9 0 0 1 15.5-6.36L21 8"/>'
            '<path d="M21 3v5h-5"/>'
            '<path d="M21 12a9 9 0 0 1-15.5 6.36L3 16"/>'
            '<path d="M3 21v-5h5"/></svg>'
        )
        _copy_label = 'Copy' if T.get('_lang') == 'EN' else 'Sao chép'
        _copied_label = 'Copied!' if T.get('_lang') == 'EN' else 'Đã copy!'
        _regen_label = 'Regenerate' if T.get('_lang') == 'EN' else 'Tạo lại'

        # Copy button: navigator.clipboard (mới) + execCommand fallback (iframe legacy)
        # → Work trên tất cả browser, kể cả Streamlit iframe không có clipboard-write permission
        _copy_btn = (
            f'<button class="msg-action-btn" title="{_copy_label}" '
            f'onclick="(function(b){{'
            f'var t=b.getAttribute(\'data-txt\').replace(/\\\\n/g,\'\\n\');'
            f'var done=function(){{'
            f'var o=b.innerHTML;b.innerHTML=\'{_copied_label}\';b.classList.add(\'copied\');'
            f'setTimeout(function(){{b.innerHTML=o;b.classList.remove(\'copied\');}},1500);'
            f'}};'
            # Modern API
            f'if(navigator.clipboard&&navigator.clipboard.writeText){{'
            f'navigator.clipboard.writeText(t).then(done).catch(function(){{'
            # Fallback: tạo textarea tạm, select, execCommand copy
            f'var ta=document.createElement(\'textarea\');'
            f'ta.value=t;ta.style.position=\'fixed\';ta.style.opacity=\'0\';'
            f'document.body.appendChild(ta);ta.select();'
            f'try{{document.execCommand(\'copy\');done();}}catch(e){{}}'
            f'document.body.removeChild(ta);'
            f'}});}} else {{'
            # Không support clipboard API ở all → fallback execCommand ngay
            f'var ta=document.createElement(\'textarea\');'
            f'ta.value=t;ta.style.position=\'fixed\';ta.style.opacity=\'0\';'
            f'document.body.appendChild(ta);ta.select();'
            f'try{{document.execCommand(\'copy\');done();}}catch(e){{}}'
            f'document.body.removeChild(ta);'
            f'}}'
            f'}})(this)" data-txt="{_safe}">{_svg_copy}<span>{_copy_label}</span></button>'
        )

        # Regenerate button (chỉ hiện trên tin cuối) — kích hoạt qua query param
        _regen_btn = ''
        if is_last_bot:
            _regen_btn = (
                f'<button class="msg-action-btn" title="{_regen_label}" '
                f'onclick="(function(){{'
                f'var u=new URL(window.parent.location.href);'
                f'u.searchParams.set(\'regen\',Date.now());'
                f'window.parent.location.href=u.toString();'
                f'}})()">{_svg_regen}<span>{_regen_label}</span></button>'
            )

        _actions_html = (
            f'<div class="msg-actions" style="display:flex;gap:6px;margin-top:8px;'
            f'opacity:0.7;transition:opacity 0.2s">'
            f'{_copy_btn}{_regen_btn}</div>'
        )

    st.markdown(
        f'<div class="chat-row chat-bot" id="msg-{msg_idx}">'
        f'<div class="chat-avatar">AI</div>'
        f'<div class="chat-bubble-wrap">'
        f'<div class="chat-meta">'
        f'<span class="chat-label" style="color:{_stripe}">{t("chatbot.bot_label")}</span>'
        f'<span class="chat-time">{_ts}</span></div>'
        f'<div class="chat-bubble chat-bubble-bot bot-msg-container" '
        f'style="background:{_bg};color:{_fg};border:1px solid {_border};'
        f'border-left:3px solid {_stripe}">'
        f'{_diag}{_content_html}'
        f'{_actions_html}'
        f'</div></div></div>',
        unsafe_allow_html=True)
    return _match_count


# ═══════════════════════════════════════════════════════════════
# SEARCH HELPERS
# ═══════════════════════════════════════════════════════════════
def _normalize_vn(s: str) -> str:
    """Lowercase + bỏ dấu tiếng Việt để search fuzzy."""
    import unicodedata
    s = s.lower().strip()
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.replace('đ', 'd').replace('Đ', 'd')
    return s


def _filter_conversations(convs: list, query: str) -> list:
    """Lọc conversations theo title match (không dấu, không phân biệt hoa thường)."""
    if not query or not query.strip():
        return convs
    q_norm = _normalize_vn(query)
    return [c for c in convs if q_norm in _normalize_vn(c.get('title', ''))]


def _highlight_title(title: str, query: str, accent: str) -> str:
    """Bọc từ khoá trong title bằng <mark> — return HTML safe."""
    import html as _hlib
    import re
    escaped_title = _hlib.escape(title)
    if not query or not query.strip():
        return escaped_title

    q_norm = _normalize_vn(query)
    t_norm = _normalize_vn(title)

    if len(q_norm) != len(query.strip().lower()):
        try:
            pat = re.compile(re.escape(query.strip()), re.IGNORECASE)
            return pat.sub(
                lambda m: f'<mark style="background:{accent};color:#FFFFFF;'
                          f'padding:0 3px;border-radius:3px;font-weight:700">'
                          f'{_hlib.escape(m.group(0))}</mark>',
                title
            )
        except Exception:
            return escaped_title

    if len(t_norm) != len(title):
        return escaped_title

    result = []
    i = 0
    while i < len(title):
        if t_norm[i:i+len(q_norm)] == q_norm:
            segment = title[i:i+len(q_norm)]
            result.append(
                f'<mark style="background:{accent};color:#FFFFFF;'
                f'padding:0 3px;border-radius:3px;font-weight:700">'
                f'{_hlib.escape(segment)}</mark>'
            )
            i += len(q_norm)
        else:
            result.append(_hlib.escape(title[i]))
            i += 1
    return ''.join(result)


# ═══════════════════════════════════════════════════════════════
# SIDEBAR CHAT HISTORY — Gemini-style
# ═══════════════════════════════════════════════════════════════
def _render_sidebar_history(T: dict):
    _convs = ch.list_conversations()
    active_id = st.session_state.get('active_conv_id')
    renaming_id = st.session_state.get('renaming_conv_id')
    _accent = T.get('accent', '#1565C0')

    # ── Identity header ──────────────────────────────────────────
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;'
        f'padding:2px 2px 14px;border-bottom:1px solid {T["border"]};margin-bottom:14px">'
        f'<div style="width:32px;height:32px;border-radius:9px;flex-shrink:0;'
        f'background:linear-gradient(135deg,#1565C0 0%,#7C3AED 100%);'
        f'display:flex;align-items:center;justify-content:center;'
        f'font-size:11px;font-weight:900;color:#fff;letter-spacing:-0.5px">AI</div>'
        f'<div style="line-height:1.3">'
        f'<div style="font-size:12px;font-weight:800;color:{T["text_primary"]}">CHATBOT AI</div>'
        f'<div style="font-size:9px;color:{T["text_muted"]};letter-spacing:0.4px">'
        f'{t("chatbot.sb_subtitle")}</div></div></div>',
        unsafe_allow_html=True)

    # ── New conversation ─────────────────────────────────────────
    if st.button(t('chatbot.new_conv'), key='new_conv',
                 use_container_width=True, type='secondary'):
        new_id = ch.create_conversation()
        st.session_state['active_conv_id'] = new_id
        st.session_state.pop('renaming_conv_id', None)
        st.session_state.pop('search_query_sb', None)
        st.rerun()

    # ── SEARCH BOX ───────────────────────────────────────────────
    _search_lang = st.session_state.get('lang', 'VI')
    _search_placeholder = ('Tìm tiêu đề hội thoại...' if _search_lang == 'VI'
                           else 'Search conversation title...')
    _sb_val = st.text_input(
        label='search_sb',
        key='search_query_sb',
        placeholder=_search_placeholder,
        label_visibility='collapsed',
    )
    if _sb_val != st.session_state.get('_last_search_sb', ''):
        st.session_state['_last_search_sb'] = _sb_val
        st.session_state['_search_active'] = _sb_val
    _search_q = st.session_state.get('_search_active', '') or _sb_val

    # ── Filter ───────────────────────────────────────────────────
    _convs_filtered = _filter_conversations(_convs, _search_q)
    _n_total = len(_convs)
    _n_shown = len(_convs_filtered)
    _is_searching = bool(_search_q and _search_q.strip())

    # ── Section header ───────────────────────────────────────────
    if _is_searching:
        _label = (f'Kết quả ({_n_shown}/{_n_total})' if _search_lang == 'VI'
                  else f'Results ({_n_shown}/{_n_total})')
    else:
        _label = f'{t("chatbot.history_label")} ({_n_total})'

    st.markdown(
        f'<div style="font-size:9px;font-weight:800;letter-spacing:1.5px;'
        f'text-transform:uppercase;color:{T["text_muted"]};'
        f'margin:14px 0 6px;display:flex;align-items:center;gap:5px">'
        f'<span style="width:5px;height:5px;border-radius:50%;display:inline-block;'
        f'background:{_accent}"></span>'
        f'{_label}</div>',
        unsafe_allow_html=True)

    if not _convs:
        st.markdown(
            f'<div style="text-align:center;padding:24px 8px 20px;'
            f'font-size:11px;color:{T["text_muted"]};font-style:italic;'
            f'border:1px dashed {T["border"]};border-radius:8px">'
            f'{t("chatbot.no_conv")}<br/>'
            f'<span style="opacity:0.65;font-size:10px">{t("chatbot.no_conv_hint")}</span>'
            f'</div>', unsafe_allow_html=True)
        return

    if _is_searching and _n_shown == 0:
        _no_result_txt = ('Không tìm thấy hội thoại nào khớp.' if _search_lang == 'VI'
                          else 'No conversations match your search.')
        _search_icon = _icon_search(T['text_muted'], 14)
        st.markdown(
            f'<div style="text-align:center;padding:20px 8px;'
            f'font-size:11px;color:{T["text_muted"]};font-style:italic;'
            f'border:1px dashed {T["border"]};border-radius:8px;margin-top:8px">'
            f'{_search_icon} <span style="margin-left:6px">{_no_result_txt}</span>'
            f'</div>', unsafe_allow_html=True)
        return

    # ── Conversation list ──────────────────────────────────────────
    for conv in _convs_filtered[:30]:
        cid = conv['id']
        is_active = cid == active_id

        if cid == renaming_id:
            new_title = st.text_input(
                '', value=conv['title'],
                key=f'rename_input_{cid}',
                label_visibility='collapsed')
            _rc1, _rc2 = st.columns(2)
            with _rc1:
                if st.button(t('chatbot.rename_save'), key=f'save_{cid}',
                             use_container_width=True, type='primary'):
                    if new_title.strip():
                        ch.rename_conversation(cid, new_title.strip())
                    st.session_state.pop('renaming_conv_id', None)
                    st.rerun()
            with _rc2:
                if st.button(t('chatbot.rename_cancel'), key=f'cancel_{cid}',
                             use_container_width=True):
                    st.session_state.pop('renaming_conv_id', None)
                    st.rerun()
            continue

        if _is_searching:
            _hl_title = _highlight_title(conv['title'], _search_q, _accent)
            _badge_bg = T.get('bg_elevated', '#F1F5F9')
            _sb_icon = _icon_search(_accent, 11)
            st.markdown(
                f'<div style="font-size:10px;padding:4px 10px;margin-bottom:-2px;'
                f'color:{T["text_secondary"]};background:{_badge_bg};'
                f'border-radius:6px 6px 0 0;border:1px solid {T["border"]};'
                f'border-bottom:none;display:flex;align-items:center;gap:6px;'
                f'overflow:hidden;white-space:nowrap">'
                f'{_sb_icon}<span style="overflow:hidden;text-overflow:ellipsis">'
                f'{_hl_title}</span></div>',
                unsafe_allow_html=True)

        _c1, _c2, _c3 = st.columns([5, 1, 1])
        with _c1:
            # Luôn dùng secondary — không bị Streamlit primary highlight xanh dính.
            # Active state đánh dấu bằng prefix ● ở title.
            _label_btn = f'●  {conv["title"]}' if is_active else conv['title']
            if st.button(_label_btn, key=f'conv_{cid}',
                         use_container_width=True, type='secondary'):
                st.session_state['active_conv_id'] = cid
                st.rerun()
        with _c2:
            if st.button('✎', key=f'rn_{cid}', help='Đổi tên',
                         use_container_width=True, type='secondary'):
                st.session_state['renaming_conv_id'] = cid
                st.rerun()
        with _c3:
            if st.button('🗑', key=f'del_{cid}', help='Xóa',
                         use_container_width=True, type='secondary'):
                ch.delete_conversation(cid)
                if active_id == cid:
                    st.session_state['active_conv_id'] = None
                st.rerun()

        _meta_color = _accent if is_active else T['text_muted']
        st.markdown(
            f'<div style="font-size:9px;color:{_meta_color};'
            f'margin:-5px 0 8px 2px;font-family:monospace;'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
            f'{t("chatbot.msg_count").replace("{n}", str(conv["message_count"]))} · '
            f'{ch.format_timestamp(conv["updated_at"])}</div>',
            unsafe_allow_html=True)

    st.markdown(
        f'<div style="margin-top:20px;padding:10px 4px 6px;'
        f'border-top:1px solid {T["border"]};'
        f'font-size:9px;color:{T["text_muted"]};text-align:center;line-height:1.8">'
        f'NCKH TDTU 2026 · HOSE<br/>'
        f'<span style="display:inline-flex;align-items:center;gap:4px">'
        f'<span style="width:5px;height:5px;border-radius:50%;background:#10B981;'
        f'display:inline-block"></span>Powered by Google Gemini</span>'
        f'</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# CONTEXT FALLBACK — khi AI fail, build câu trả lời từ số liệu thật
# ═══════════════════════════════════════════════════════════════
def _context_based_answer(query: str, context: dict, lang: str) -> str | None:
    """Sinh câu trả lời từ context khi AI không khả dụng.
    Trả về None nếu không match intent nào → caller fallback tiếp.
    """
    if not context:
        return None
    q = query.lower()
    ticker = context.get('ticker', '')

    _forecast_kw = ['dự báo', 'dự đoán', 'forecast', 'predict', 'phiên tới',
                    'phiên kế tiếp', 'next session', 'next day', 'giá ngày mai',
                    'tomorrow']
    _price_kw = ['giá', 'price', 'closing', 'đóng cửa', 'hiện tại', 'current']
    _mape_kw = ['mape', 'độ chính xác', 'accuracy', 'sai số', 'error']
    _analyze_kw = ['phân tích', 'analyze', 'analysis', 'tình hình', 'situation',
                   'đánh giá', 'assess']

    is_forecast = any(k in q for k in _forecast_kw)
    is_price    = any(k in q for k in _price_kw)
    is_mape     = any(k in q for k in _mape_kw)
    is_analyze  = any(k in q for k in _analyze_kw)

    if not (is_forecast or is_price or is_mape or is_analyze):
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
    """
    q = query.lower()
    data_kws = [
        'giá', 'price', 'đóng cửa', 'closing',
        'dự báo', 'forecast', 'predict',
        'biến động', 'volatility',
        'mape', 'rmse', 'mae',
        'phân tích', 'analyze', 'analysis',
        'phiên tới', 'next session', 'next day',
        'hôm nay', 'today', 'current',
        'tình hình', 'situation',
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

    # ── 4. GỌI AI — luôn cho AI trả lời thật ─────────────────
    if ai_ok:
        ai_resp = _ai_answer_with_retry(query, context, lang)
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
    """
    q = (query or '').lower()
    theory_kws = [
        # VI
        'là gì', 'là sao', 'nghĩa là', 'hoạt động', 'công thức', 'phương trình',
        'giải thích', 'định nghĩa', 'khác nhau', 'khác gì', 'so sánh',
        'nên chọn', 'khi nào', 'tại sao', 'ý nghĩa', 'thang đánh giá',
        # EN
        'what is', 'what are', 'how does', 'how do', 'explain', 'meaning',
        'difference', 'compare', 'formula', 'equation', 'when to use',
        'why', 'definition',
    ]
    # Exclude nếu có data-specific keywords
    data_kws = ['giá', 'price', 'dự báo', 'forecast', 'phân tích',
                'analyze', 'analysis', 'hiện tại', 'current',
                'phiên tới', 'next session', 'fpt', 'hpg', 'vnm']
    has_theory = any(k in q for k in theory_kws)
    has_data   = any(k in q for k in data_kws)
    return has_theory and not has_data


def _ai_answer_with_retry(query: str, context: dict, lang: str) -> str | None:
    """Multi-provider retry chain. Return None chỉ khi TẤT CẢ providers fail.

    Flow:
      1. Gemini full → rate limit/fail
      2. Gemini slim → rate limit/fail
      3. Groq 70B (nếu có GROQ_API_KEY) → LLaMA 3.3
      4. Groq 8B (nếu có GROQ_API_KEY) → LLaMA 3.1 Instant
      5. Countdown + Gemini retry cuối

    Groq free tier ~14k req/ngày, 30 req/phút. Khi Gemini cạn quota (20/phút),
    tự động switch sang Groq. Graceful nếu chưa config GROQ_API_KEY.
    """
    _rate_limit_wait = 0
    _groq_ready = is_groq_available()

    # Lý thuyết thuần → không gửi context (tiết kiệm token + share cache cross-ticker)
    _ctx_to_send = None if _is_theory_query(query) else context

    # ── Attempt 1: Gemini full ──
    try:
        with st.spinner('● ● ● ' + t('chatbot.thinking')):
            resp = ask_gemini(query, context=_ctx_to_send, lang=lang)
        if resp and resp.strip():
            return resp
        _log('[Chatbot] Gemini 1 empty')
    except QuotaExhaustedError:
        _log('[Chatbot] Gemini daily quota exhausted')
        if _groq_ready:
            r = _try_groq(query, _ctx_to_send, lang)
            if r:
                return r
        return None
    except RateLimitError as e:
        _rate_limit_wait = int(getattr(e, 'wait_seconds', 30) or 30)
        _rate_limit_wait = max(5, min(_rate_limit_wait, 60))
        _log(f'[Chatbot] Gemini rate limited, wait={_rate_limit_wait}s')
        st.session_state['_last_gemini_retry_s'] = _rate_limit_wait
        st.session_state['_last_gemini_error'] = str(e)
        # Fast path: có Groq → dùng Groq ngay thay vì đợi Gemini reset
        if _groq_ready:
            r = _try_groq(query, _ctx_to_send, lang)
            if r:
                return r
    except Exception as e:
        _log(f'[Chatbot] Gemini 1 error: {str(e)[:150]}')

    # ── Attempt 2: Gemini slim ──
    try:
        ticker = (context or {}).get('ticker', 'FPT')
        if lang == 'EN':
            slim = (f'User (analyzing HOSE ticker {ticker}) asked: "{query}"\n'
                    f'Reply naturally in 1-4 sentences.')
        else:
            slim = (f'Người dùng (đang phân tích mã HOSE {ticker}) hỏi: "{query}"\n'
                    f'Hãy trả lời tự nhiên 1-4 câu.')
        with st.spinner('● ● ● ' + t('chatbot.thinking')):
            resp = ask_gemini(slim, context=None, lang=lang, slim_system=True)
        if resp and resp.strip():
            return resp
        _log('[Chatbot] Gemini 2 empty')
    except RateLimitError as e:
        if _rate_limit_wait <= 0:
            _rate_limit_wait = int(getattr(e, 'wait_seconds', 30) or 30)
            _rate_limit_wait = max(5, min(_rate_limit_wait, 60))
    except Exception as e:
        _log(f'[Chatbot] Gemini 2 error: {str(e)[:150]}')

    # ── Attempt 3: Groq fallback (nếu đã config key) ──
    if _groq_ready:
        r = _try_groq(query, _ctx_to_send, lang)
        if r:
            return r

    # ── Attempt 4: countdown + Gemini retry cuối ──
    if _rate_limit_wait > 0:
        resp = _countdown_and_retry(query, context, lang, _rate_limit_wait)
        if resp:
            return resp

    return None


def _try_groq(query: str, context: dict, lang: str) -> str | None:
    """Thử Groq: LLaMA 3.3 70B → 3.1 8B. None nếu fail toàn bộ."""
    # 70B (chất lượng)
    try:
        with st.spinner('● ● ● ' + t('chatbot.thinking')):
            resp = ask_groq(query, context=context, lang=lang)
        if resp and resp.strip():
            _log('[Chatbot] Groq 70B OK')
            return resp
    except RateLimitError:
        _log('[Chatbot] Groq 70B rate limited — try 8B')
    except Exception as e:
        _log(f'[Chatbot] Groq 70B error: {str(e)[:150]}')

    # 8B (tốc độ, rate limit rộng hơn)
    try:
        ticker = (context or {}).get('ticker', 'FPT')
        if lang == 'EN':
            slim = f'Ticker {ticker}. User: "{query}". Reply naturally 1-4 sentences.'
        else:
            slim = f'Mã {ticker}. User: "{query}". Trả lời tự nhiên 1-4 câu.'
        with st.spinner('● ● ● ' + t('chatbot.thinking')):
            resp = ask_groq(slim, context=None, lang=lang, slim_system=True)
        if resp and resp.strip():
            _log('[Chatbot] Groq 8B OK')
            return resp
    except Exception as e:
        _log(f'[Chatbot] Groq 8B error: {str(e)[:150]}')
    return None


def _countdown_and_retry(query: str, context: dict, lang: str, wait_seconds: int) -> str | None:
    """Hiện countdown trong spinner rồi thử gọi Gemini lần cuối."""
    import time as _time

    # SVG hourglass tự build — 2 tam giác ngược + cát rơi, animation xoay 180deg
    _svg_hourglass = (
        '<svg class="hourglass-svg" width="16" height="16" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round" '
        'style="flex-shrink:0;animation:hg-flip 1.4s ease-in-out infinite">'
        '<path d="M5 22h14"/>'
        '<path d="M5 2h14"/>'
        '<path d="M17 22v-4.172a2 2 0 0 0-.586-1.414L12 12l-4.414 4.414'
        'A2 2 0 0 0 7 17.828V22"/>'
        '<path d="M7 2v4.172a2 2 0 0 0 .586 1.414L12 12l4.414-4.414'
        'A2 2 0 0 0 17 6.172V2"/>'
        '<path d="M9.5 8h5" stroke-width="1.5" opacity="0.5"/>'
        '</svg>'
    )
    _anim_css = (
        '<style>@keyframes hg-flip{'
        '0%,45%{transform:rotate(0deg)}'
        '55%,100%{transform:rotate(180deg)}'
        '}</style>'
    )

    _wait_label_fmt = ('Waiting {s}s for Gemini rate limit to reset…'
                       if lang == 'EN'
                       else 'Đang đợi {s}s để Gemini reset rate limit…')

    placeholder = st.empty()
    try:
        for remaining in range(wait_seconds, 0, -1):
            placeholder.markdown(
                f'{_anim_css}'
                f'<div style="display:flex;align-items:center;gap:8px;'
                f'padding:8px 14px;border-radius:8px;'
                f'background:rgba(96,165,250,0.12);'
                f'border:1px solid rgba(96,165,250,0.35);'
                f'color:#3B82F6;font-size:13px;font-weight:500">'
                f'{_svg_hourglass}'
                f'<span>{_wait_label_fmt.format(s=remaining)}</span></div>',
                unsafe_allow_html=True)
            _time.sleep(1)
        placeholder.empty()

        # Final retry với slim prompt
        ticker = (context or {}).get('ticker', 'FPT')
        if lang == 'EN':
            slim = f'User (ticker {ticker}) asked: "{query}"\nReply in 1-4 sentences.'
        else:
            slim = f'Người dùng (mã {ticker}) hỏi: "{query}"\nTrả lời 1-4 câu.'
        with st.spinner('● ● ● ' + t('chatbot.thinking')):
            resp = ask_gemini(slim, context=None, lang=lang, slim_system=True)
        if resp and resp.strip():
            return resp
    except Exception as e:
        _log(f'[Chatbot Countdown Retry Error] {str(e)[:200]}')
    finally:
        placeholder.empty()
    return None


# ═══════════════════════════════════════════════════════════════
# MAIN RENDER
# ═══════════════════════════════════════════════════════════════
def render(ticker, train_ratio, date_from, date_to, df, r1, r2, r3, m1, m2, m3, _T,
           ar_order=1):

    st.markdown(
        f'<div class="page-header">'
        f'<h1>{t("chatbot.title")}</h1>'
        f'<p>{t("chatbot.subtitle")}</p>'
        f'</div>', unsafe_allow_html=True)

    # AI ready nếu có Gemini OR Groq (hoặc cả hai)
    _ai_ok = is_ai_available() or is_groq_available()
    _lang = st.session_state.get('lang', 'VI')
    _is_dark = _T.get('is_dark', False)
    _T['_lang'] = _lang  # share lang với helper functions

    # ── Status banner — theme-aware ─────────────────────────────
    _status_dot_ok   = f'<span style="width:8px;height:8px;border-radius:50%;background:#10B981;display:inline-block;box-shadow:0 0 6px #10B981;flex-shrink:0"></span>'
    _status_dot_warn = f'<span style="width:8px;height:8px;border-radius:50%;background:#F59E0B;display:inline-block;box-shadow:0 0 6px #F59E0B;flex-shrink:0"></span>'
    if _ai_ok:
        st.markdown(
            f'<div class="chat-status chat-status-ok">{_status_dot_ok} {t("chatbot.ai_ok")}</div>',
            unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="chat-status chat-status-warn">{_status_dot_warn} {t("chatbot.ai_warn")}</div>',
            unsafe_allow_html=True)

    if 'active_conv_id' not in st.session_state:
        _convs = ch.list_conversations()
        if _convs:
            st.session_state['active_conv_id'] = _convs[0]['id']
        else:
            st.session_state['active_conv_id'] = ch.create_conversation()

    active_id = st.session_state['active_conv_id']

    # ═══════════════════════════════════════════════════════════
    # CSS CHATBOT v4 — DỨT ĐIỂM
    # ═══════════════════════════════════════════════════════════
    # Phát hiện quan trọng:
    # 1. Streamlit v1.56 render button với data-testid="stBaseButton-primary"
    #    hoặc "stBaseButton-secondary" (chữ 'st' viết thường đầu).
    # 2. DOMPurify strip <script> trong st.markdown → JS không chạy được
    # 3. Streamlit dùng emotion CSS-in-JS với !important ở một số nơi
    #
    # Giải pháp: CSS thuần + specificity cao + cover mọi variant
    # data-testid có thể xuất hiện:
    # - stBaseButton-primary / stBaseButton-secondary / stBaseButton-tertiary
    # - baseButton-primary / baseButton-secondary (legacy versions)
    _bg_btn     = _T['bg_elevated']
    _fg_btn     = _T['text_primary']
    _brd_btn    = _T['border_strong']
    _brd_soft   = _T['border']
    _accent     = _T['accent']
    _accent_hov = _T.get('accent_hover', _accent)
    _bg_card    = _T['bg_card']
    _fg_muted   = _T['text_muted']

    if _is_dark:
        _btn_bg      = _accent
        _btn_fg      = '#FFFFFF'
        _btn_border  = _accent
        _btn_hov_bg  = _accent_hov
        _btn_hov_fg  = '#0F172A'
        _icon_bg     = 'rgba(96,165,250,0.12)'
        _icon_fg     = '#BFDBFE'
        _icon_border = 'rgba(147,197,253,0.35)'
    else:
        _btn_bg      = _bg_btn
        _btn_fg      = _fg_btn
        _btn_border  = _brd_btn
        _btn_hov_bg  = _accent
        _btn_hov_fg  = '#FFFFFF'
        _icon_bg     = 'rgba(96,165,250,0.10)'
        _icon_fg     = '#93C5FD'
        _icon_border = 'rgba(96,165,250,0.40)'

    # SVG search-icon data URI cho ô text_input (placeholder-color)
    _c_muted = _fg_muted.replace('#', '%23')
    _search_icon_url = (
        f"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
        f"viewBox='0 0 24 24' fill='none' stroke='{_c_muted}' "
        f"stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E"
        f"%3Ccircle cx='11' cy='11' r='7'/%3E"
        f"%3Cpath d='m20 20-3.5-3.5'/%3E%3C/svg%3E"
    )

    _css_block = f"""<style>
/* ═══════════════════════════════════════════════════════════
   STICKY SIDEBAR
   ═══════════════════════════════════════════════════════════ */
/* Sticky sidebar — chỉ áp cho cột TRÁI CÙNG của layout chatbot (chứa conv list),
   KHÔNG áp cho nested columns như 4 welcome chips. Dùng :not(:has(welcome_chip))
   để loại trừ cột nội (cột của chip không bao giờ chứa welcome_chip_ bên trong
   vì welcome_chip NẰM TRONG chính nó, nhưng sidebar column lại không có). */
[data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child:not(:has([class*="st-key-welcome_chip_"])) {{
    position: sticky !important;
    top: 4px !important;
    max-height: calc(100vh - 80px) !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    background: {_bg_card} !important;
    border: 1px solid {_brd_soft} !important;
    border-radius: 12px !important;
    padding: 12px 8px 8px !important;
}}
[data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child:not(:has([class*="st-key-welcome_chip_"]))::-webkit-scrollbar {{ width: 3px; }}
[data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child:not(:has([class*="st-key-welcome_chip_"]))::-webkit-scrollbar-thumb {{
    background: rgba(100,116,139,0.25);
    border-radius: 2px;
}}
/* RESET explicit cho cột CHỨA welcome_chip — đảm bảo trông như chip bên phải */
[data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:has([class*="st-key-welcome_chip_"]) {{
    position: static !important;
    max-height: none !important;
    overflow: visible !important;
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    padding: 0 !important;
    box-shadow: none !important;
}}

[data-testid="stMain"] [data-testid="stHorizontalBlock"] [data-testid="stColumn"],
[data-testid="stMain"] [data-testid="stHorizontalBlock"] [data-testid="column"] {{
    background: transparent !important;
    background-color: transparent !important;
}}
[data-testid="stMain"] .element-container,
[data-testid="stMain"] [data-testid="element-container"],
[data-testid="stMain"] .stElementContainer {{
    background: transparent !important;
    background-color: transparent !important;
}}

/* ═══════════════════════════════════════════════════════════
   🎯 BUTTON OVERRIDE v4 — cover TẤT CẢ variant data-testid
   Specificity: html body + 3 classes = 0,0,3,2
   ═══════════════════════════════════════════════════════════ */

/* BASE: mọi button trong main (secondary là default) */
html body [data-testid="stMain"] div[data-testid="stButton"] button,
html body [data-testid="stMain"] div.stButton button,
html body [data-testid="stMain"] button[data-testid="stBaseButton-secondary"],
html body [data-testid="stMain"] button[data-testid="baseButton-secondary"],
html body [data-testid="stMain"] button[kind="secondary"] {{
    background-color: {_btn_bg} !important;
    background: {_btn_bg} !important;
    background-image: none !important;
    color: {_btn_fg} !important;
    border: 1px solid {_btn_border} !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: all .14s !important;
    box-shadow: 0 1px 3px rgba(0,0,0,.10) !important;
    user-select: none !important;
    -webkit-user-select: none !important;
}}
html body [data-testid="stMain"] div[data-testid="stButton"] button *,
html body [data-testid="stMain"] div.stButton button *,
html body [data-testid="stMain"] button[data-testid="stBaseButton-secondary"] *,
html body [data-testid="stMain"] button[data-testid="baseButton-secondary"] *,
html body [data-testid="stMain"] button[kind="secondary"] * {{
    color: {_btn_fg} !important;
    background: transparent !important;
    background-color: transparent !important;
}}

/* HOVER secondary */
html body [data-testid="stMain"] div[data-testid="stButton"] button:hover,
html body [data-testid="stMain"] div.stButton button:hover,
html body [data-testid="stMain"] button[data-testid="stBaseButton-secondary"]:hover,
html body [data-testid="stMain"] button[data-testid="baseButton-secondary"]:hover,
html body [data-testid="stMain"] button[kind="secondary"]:hover {{
    background-color: {_btn_hov_bg} !important;
    background: {_btn_hov_bg} !important;
    color: {_btn_hov_fg} !important;
    border-color: {_btn_hov_bg} !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 3px 10px rgba(0,0,0,.20) !important;
}}
html body [data-testid="stMain"] div[data-testid="stButton"] button:hover *,
html body [data-testid="stMain"] div.stButton button:hover *,
html body [data-testid="stMain"] button[data-testid="stBaseButton-secondary"]:hover *,
html body [data-testid="stMain"] button[data-testid="baseButton-secondary"]:hover *,
html body [data-testid="stMain"] button[kind="secondary"]:hover * {{
    color: {_btn_hov_fg} !important;
}}

/* PRIMARY: "Cuộc trò chuyện mới" + active conversation
   Style softer (KHÔNG solid blue) — bg như secondary + viền đậm + text accent.
   Cả light/dark đều đọc rõ chữ, không bị "dính" highlight xanh đậm. */
html body [data-testid="stMain"] button[data-testid="stBaseButton-primary"],
html body [data-testid="stMain"] button[data-testid="baseButton-primary"],
html body [data-testid="stMain"] button[kind="primary"] {{
    background-color: {_btn_bg} !important;
    background: {_btn_bg} !important;
    background-image: none !important;
    color: {_accent} !important;
    border: 2px solid {_accent} !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    box-shadow: 0 2px 6px rgba(0,0,0,.10) !important;
    user-select: none !important;
    -webkit-user-select: none !important;
}}
html body [data-testid="stMain"] button[data-testid="stBaseButton-primary"] *,
html body [data-testid="stMain"] button[data-testid="baseButton-primary"] *,
html body [data-testid="stMain"] button[kind="primary"] * {{
    color: {_accent} !important;
    background: transparent !important;
}}
html body [data-testid="stMain"] button[data-testid="stBaseButton-primary"]:hover,
html body [data-testid="stMain"] button[data-testid="baseButton-primary"]:hover,
html body [data-testid="stMain"] button[kind="primary"]:hover {{
    background-color: {_accent} !important;
    background: {_accent} !important;
    color: #FFFFFF !important;
    border-color: {_accent} !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(0,0,0,.20) !important;
}}
html body [data-testid="stMain"] button[data-testid="stBaseButton-primary"]:hover *,
html body [data-testid="stMain"] button[data-testid="baseButton-primary"]:hover *,
html body [data-testid="stMain"] button[kind="primary"]:hover * {{
    color: #FFFFFF !important;
}}

/* ═══════════════════════════════════════════════════════════
   ICON BUTTONS ✎ 🗑 — nested trong col 2&3 của sidebar
   ═══════════════════════════════════════════════════════════ */
html body [data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:not(:first-child) button {{
    border-radius: 8px !important;
    font-size: 0 !important;
    padding: 0 !important;
    min-height: 38px !important;
    height: 38px !important;
    min-width: 38px !important;
    font-weight: 500 !important;
    background-color: {_icon_bg} !important;
    background: {_icon_bg} !important;
    background-image: none !important;
    color: {_icon_fg} !important;
    border: 1px solid {_icon_border} !important;
    box-shadow: none !important;
    position: relative !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}}
html body [data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:not(:first-child) button * {{
    color: {_icon_fg} !important;
    background: transparent !important;
    font-size: 0 !important;
}}
html body [data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:not(:first-child) button:hover {{
    background-color: {_accent} !important;
    background: {_accent} !important;
    color: #FFFFFF !important;
    border-color: {_accent} !important;
}}
html body [data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:not(:first-child) button:hover * {{
    color: #FFFFFF !important;
}}

/* Pencil icon (cột 2 conv row = .st-key-rn_*) */
html body [class*="st-key-rn_"] button::before {{
    content: '';
    position: absolute !important;
    top: 50% !important;
    left: 50% !important;
    transform: translate(-50%, -50%) !important;
    width: 20px !important;
    height: 20px !important;
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%23{_icon_fg.lstrip('#')}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.83 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/><path d="m15 5 4 4"/></svg>');
    background-size: contain;
    background-repeat: no-repeat;
    background-position: center;
    pointer-events: none !important;
}}
html body [class*="st-key-rn_"] button:hover::before {{
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%23FFFFFF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.83 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/><path d="m15 5 4 4"/></svg>');
}}

/* Trash icon (cột 3 conv row = .st-key-del_*) */
html body [class*="st-key-del_"] button::before {{
    content: '';
    position: absolute !important;
    top: 50% !important;
    left: 50% !important;
    transform: translate(-50%, -50%) !important;
    width: 20px !important;
    height: 20px !important;
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%23{_icon_fg.lstrip('#')}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>');
    background-size: contain;
    background-repeat: no-repeat;
    background-position: center;
    pointer-events: none !important;
}}
html body [class*="st-key-del_"] button:hover::before {{
    background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%23FFFFFF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>');
}}

/* ═══════════════════════════════════════════════════════════
   SEARCH INPUT ICON — SVG kính lúp tự build (msg search + sidebar)
   ═══════════════════════════════════════════════════════════ */
html body [class*="st-key-msg_search_q"],
html body [class*="st-key-search_query_sb"],
html body .stElementContainer:has(> [data-testid="stElementContainer"] input[aria-label="search_sb"]) {{
    position: relative !important;
}}
html body [class*="st-key-msg_search_q"]::before,
html body [class*="st-key-search_query_sb"]::before {{
    content: '' !important;
    position: absolute !important;
    left: 14px !important;
    top: 50% !important;
    transform: translateY(-50%) !important;
    width: 16px !important;
    height: 16px !important;
    background-image: url({_search_icon_url}) !important;
    background-size: contain !important;
    background-repeat: no-repeat !important;
    background-position: center !important;
    pointer-events: none !important;
    z-index: 5 !important;
    opacity: 0.85 !important;
}}
html body [class*="st-key-msg_search_q"] input,
html body [class*="st-key-search_query_sb"] input {{
    padding-left: 38px !important;
}}

/* Flatten tất cả wrapper div bên ngoài của msg search — bỏ nested shape/bg/border
   để chỉ còn 1 viền duy nhất ở input innermost */
html body [class*="st-key-msg_search_q"],
html body [class*="st-key-msg_search_q"] > div,
html body [class*="st-key-msg_search_q"] [data-testid="stTextInput"],
html body [class*="st-key-msg_search_q"] [data-testid="stTextInput"] > div,
html body [class*="st-key-msg_search_q"] [data-testid="stTextInput"] > label {{
    background: transparent !important;
    background-color: transparent !important;
    background-image: none !important;
    border: none !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin: 0 !important;
}}
/* Căn chiều cao + shape chỉ trên innermost input wrapper = 38px */
html body [class*="st-key-msg_search_q"] [data-baseweb="input"],
html body [class*="st-key-msg_search_q"] [data-baseweb="base-input"] {{
    height: 38px !important;
    min-height: 38px !important;
    border-radius: 8px !important;
    border: 1px solid {_brd_soft} !important;
    background: {_bg_btn} !important;
    background-color: {_bg_btn} !important;
    box-shadow: none !important;
    padding: 0 !important;
}}
html body [class*="st-key-msg_search_q"] input,
html body [class*="st-key-search_query_sb"] input {{
    height: 38px !important;
    min-height: 38px !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    line-height: 38px !important;
    background: transparent !important;
    background-color: transparent !important;
    color: {_fg_btn} !important;
    caret-color: {_accent} !important;
}}
/* Placeholder text — đảm bảo contrast đủ ở cả dark & light mode */
html body [class*="st-key-msg_search_q"] input::placeholder,
html body [class*="st-key-search_query_sb"] input::placeholder {{
    color: {_fg_muted} !important;
    opacity: 0.85 !important;
}}
html body [class*="st-key-msg_search_q"] input::-webkit-input-placeholder,
html body [class*="st-key-search_query_sb"] input::-webkit-input-placeholder {{
    color: {_fg_muted} !important;
    opacity: 0.85 !important;
}}
html body [class*="st-key-msg_search_q"] input::-moz-placeholder,
html body [class*="st-key-search_query_sb"] input::-moz-placeholder {{
    color: {_fg_muted} !important;
    opacity: 0.85 !important;
}}

/* ═══════════════════════════════════════════════════════════
   SEARCH NAV BUTTONS — ◀ ▶ prev/next
   ═══════════════════════════════════════════════════════════ */
html body [class*="st-key-match_prev_btn"] button,
html body [class*="st-key-match_next_btn"] button {{
    height: 38px !important;
    min-height: 38px !important;
    padding: 0 !important;
    border-radius: 8px !important;
    background: {_bg_btn} !important;
    background-color: {_bg_btn} !important;
    border: 1px solid {_brd_soft} !important;
    color: {_accent} !important;
    font-size: 14px !important;
    font-weight: 700 !important;
    line-height: 1 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}}
html body [class*="st-key-match_prev_btn"] button *,
html body [class*="st-key-match_next_btn"] button * {{
    color: {_accent} !important;
    font-size: 14px !important;
}}
html body [class*="st-key-match_prev_btn"] button:hover,
html body [class*="st-key-match_next_btn"] button:hover {{
    background: {_accent} !important;
    background-color: {_accent} !important;
    color: #FFFFFF !important;
    border-color: {_accent} !important;
}}
html body [class*="st-key-match_prev_btn"] button:hover *,
html body [class*="st-key-match_next_btn"] button:hover * {{
    color: #FFFFFF !important;
}}
html body [class*="st-key-match_prev_btn"] button:disabled,
html body [class*="st-key-match_next_btn"] button:disabled {{
    opacity: 0.35 !important;
    cursor: not-allowed !important;
}}

/* ═══════════════════════════════════════════════════════════
   MSG ACTION BUTTONS — Copy / Regenerate trên tin AI
   ═══════════════════════════════════════════════════════════ */
.msg-actions {{
    padding-top: 6px;
    border-top: 1px dashed {_brd_soft};
    margin-top: 10px !important;
}}
button.msg-action-btn {{
    display: inline-flex !important;
    align-items: center !important;
    gap: 5px !important;
    padding: 4px 10px !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    color: {_fg_muted} !important;
    background: transparent !important;
    border: 1px solid {_brd_soft} !important;
    border-radius: 6px !important;
    cursor: pointer !important;
    transition: all 0.18s ease !important;
    font-family: inherit !important;
}}
button.msg-action-btn:hover {{
    color: {_accent} !important;
    border-color: {_accent} !important;
    background: rgba(96,165,250,0.08) !important;
}}
button.msg-action-btn.copied {{
    color: #10B981 !important;
    border-color: #10B981 !important;
    background: rgba(16,185,129,0.10) !important;
}}

/* ═══════════════════════════════════════════════════════════
   WELCOME CHIPS — card 2 dòng clickable (replace empty state)
   ═══════════════════════════════════════════════════════════ */
html body [class*="st-key-welcome_chip_"] button {{
    min-height: 72px !important;
    padding: 14px 18px !important;
    border-radius: 12px !important;
    background: {_bg_card} !important;
    background-color: {_bg_card} !important;
    border: 1.5px solid {_brd_soft} !important;
    color: {_fg_btn} !important;
    text-align: left !important;
    font-weight: 500 !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
    transition: all 0.2s ease !important;
    white-space: pre-line !important;
    line-height: 1.5 !important;
    position: relative !important;
    overflow: hidden !important;
}}
html body [class*="st-key-welcome_chip_"] button::before {{
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 3px;
    background: {_accent};
    opacity: 0.6;
}}
/* FIX: Streamlit wrap text trong div với display:flex + justify-content:center
   → label/question bị center. Force flex-start + width 100% để left-align thực sự. */
html body [class*="st-key-welcome_chip_"] button > div {{
    display: flex !important;
    flex-direction: column !important;
    align-items: flex-start !important;
    justify-content: flex-start !important;
    text-align: left !important;
    white-space: pre-line !important;
    width: 100% !important;
}}
html body [class*="st-key-welcome_chip_"] button > div > p {{
    text-align: left !important;
    white-space: pre-line !important;
    width: 100% !important;
    margin-left: 0 !important;
    padding-left: 0 !important;
}}
html body [class*="st-key-welcome_chip_"] button [data-testid="stMarkdownContainer"] {{
    display: flex !important;
    flex-direction: column !important;
    align-items: flex-start !important;
    text-align: left !important;
    width: 100% !important;
}}
/* Dòng đầu = label, dòng 2 = question. Dùng ::first-line để bold label */
html body [class*="st-key-welcome_chip_"] button p {{
    font-size: 13px !important;
    color: {_fg_muted} !important;
    margin: 0 !important;
}}
html body [class*="st-key-welcome_chip_"] button p::first-line {{
    color: {_accent} !important;
    font-size: 11px !important;
    font-weight: 800 !important;
    letter-spacing: 1.2px !important;
    text-transform: uppercase !important;
}}
html body [class*="st-key-welcome_chip_"] button:hover {{
    border-color: {_accent} !important;
    background: {_bg_card} !important;
    background-color: {_bg_card} !important;
    box-shadow: 0 4px 12px {_accent}25 !important;
    transform: translateY(-1px);
}}
html body [class*="st-key-welcome_chip_"] button:hover::before {{
    opacity: 1;
    width: 4px;
}}
html body [class*="st-key-welcome_chip_"] button:hover p {{
    color: {_fg_btn} !important;
}}
/* FIX quan trọng: chip #1 bị Streamlit auto-focus sau rerun → default primary
   fill xanh solid + text trắng / blue tint làm text faded → chip lẻ với 3 chip
   còn lại. Force :focus / :active hoàn toàn IDENTICAL với base (không ring,
   không tint, không shadow khác) → 4 chip nhất quán tuyệt đối. */
html body [class*="st-key-welcome_chip_"] button:focus,
html body [class*="st-key-welcome_chip_"] button:focus-visible,
html body [class*="st-key-welcome_chip_"] button:active,
html body [class*="st-key-welcome_chip_"] button[kind="primary"],
html body [class*="st-key-welcome_chip_"] button[kind="primaryFormSubmit"],
html body [class*="st-key-welcome_chip_"] button[data-baseweb="button"]:focus,
html body [class*="st-key-welcome_chip_"] button[data-baseweb="button"]:active {{
    background: {_bg_card} !important;
    background-color: {_bg_card} !important;
    color: {_fg_btn} !important;
    border: 1.5px solid {_brd_soft} !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
    outline: none !important;
    transform: none !important;
}}
/* Text color phải giữ nguyên giống base — KHÔNG tự biến faded */
html body [class*="st-key-welcome_chip_"] button:focus p,
html body [class*="st-key-welcome_chip_"] button:focus-visible p,
html body [class*="st-key-welcome_chip_"] button:active p {{
    color: {_fg_muted} !important;
    opacity: 1 !important;
}}
html body [class*="st-key-welcome_chip_"] button:focus p::first-line,
html body [class*="st-key-welcome_chip_"] button:focus-visible p::first-line,
html body [class*="st-key-welcome_chip_"] button:active p::first-line {{
    color: {_accent} !important;
}}
/* Accent stripe giữ nguyên opacity 0.6 trên focus (tránh nhấp nháy) */
html body [class*="st-key-welcome_chip_"] button:focus::before,
html body [class*="st-key-welcome_chip_"] button:focus-visible::before,
html body [class*="st-key-welcome_chip_"] button:active::before {{
    opacity: 0.6 !important;
    width: 3px !important;
}}

/* ═══════════════════════════════════════════════════════════
   ACTION BAR — Ẩn/Xuất/Xóa (dưới chat)
   Nền NHẠT (không phải xanh đậm), chữ xanh
   ═══════════════════════════════════════════════════════════ */
html body [data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) > div > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] > div > [data-testid="stButton"] button,
html body [data-testid="stMain"] button#toggle_sug_btn,
html body [data-testid="stMain"] button#export_btn,
html body [data-testid="stMain"] button#clear_conv_btn {{
    background-color: {_icon_bg} !important;
    background: {_icon_bg} !important;
    color: {_icon_fg} !important;
    border: 1px solid {_icon_border} !important;
    font-weight: 500 !important;
}}

/* ═══════════════════════════════════════════════════════════
   SUGGESTION CHIPS — Pill oval viền xanh (giống title conv)
   Nền trong suốt, viền xanh accent, chữ xanh accent
   ═══════════════════════════════════════════════════════════ */
html body [data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:not(:first-child)
    [data-testid="stHorizontalBlock"] button {{
    border-radius: 20px !important;
    font-size: 12px !important;
    padding: 5px 14px !important;
    min-height: 36px !important;
    font-weight: 500 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    background-color: {_icon_bg} !important;
    background: {_icon_bg} !important;
    color: {_icon_fg} !important;
    border: 1px solid {_icon_border} !important;
}}
html body [data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:not(:first-child)
    [data-testid="stHorizontalBlock"] button * {{
    color: {_icon_fg} !important;
    background: transparent !important;
}}
html body [data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:not(:first-child)
    [data-testid="stHorizontalBlock"] button:hover {{
    background-color: {_accent} !important;
    background: {_accent} !important;
    color: #FFFFFF !important;
    border-color: {_accent} !important;
}}
html body [data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:not(:first-child)
    [data-testid="stHorizontalBlock"] button:hover * {{
    color: #FFFFFF !important;
}}

/* ═══════════════════════════════════════════════════════════
   CHAT INPUT — toàn bộ div con cũng phải transparent
   (Streamlit nest nhiều div, 1 div sâu có bg trắng cứng đầu)
   ═══════════════════════════════════════════════════════════ */
html body div[data-testid="stChatInput"] {{
    background: transparent !important;
    background-color: transparent !important;
}}
html body div[data-testid="stChatInput"] > div {{
    background-color: {_bg_card} !important;
    background: {_bg_card} !important;
    background-image: none !important;
    border: 2px solid {_brd_soft} !important;
    border-radius: 14px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,.15) !important;
    padding: 6px 6px 6px 14px !important;
}}
html body div[data-testid="stChatInput"] > div:focus-within {{
    border-color: {_accent} !important;
    box-shadow: 0 4px 16px {_accent}30 !important;
}}
/* Tất cả div con — transparent để không lộ viền trắng */
html body div[data-testid="stChatInput"] > div > div,
html body div[data-testid="stChatInput"] > div div,
html body div[data-testid="stChatInput"] [data-baseweb],
html body div[data-testid="stChatInput"] [data-baseweb] > div {{
    background: transparent !important;
    background-color: transparent !important;
    background-image: none !important;
    border: none !important;
    border-radius: 0 !important;
    box-shadow: none !important;
}}
html body div[data-testid="stChatInput"] textarea,
html body div[data-testid="stChatInput"] [contenteditable],
html body div[data-testid="stChatInput"] input {{
    color: {_fg_btn} !important;
    background: transparent !important;
    background-color: transparent !important;
    caret-color: {_accent} !important;
    border: none !important;
    padding: 8px 2px !important;
    font-size: 14px !important;
}}
html body div[data-testid="stChatInput"] textarea::placeholder {{
    color: {_fg_muted} !important;
    opacity: 0.65 !important;
}}
html body div[data-testid="stChatInput"] button[data-testid="stChatInputSubmitButton"] {{
    background: {_accent} !important;
    background-color: {_accent} !important;
    background-image: none !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 10px !important;
    min-width: 36px !important;
    min-height: 36px !important;
    padding: 4px !important;
}}
html body div[data-testid="stChatInput"] button[data-testid="stChatInputSubmitButton"] svg,
html body div[data-testid="stChatInput"] button[data-testid="stChatInputSubmitButton"] svg path {{
    color: #FFFFFF !important;
    fill: #FFFFFF !important;
    stroke: #FFFFFF !important;
}}
html body div[data-testid="stChatInput"] button[data-testid="stChatInputSubmitButton"]:hover {{
    background: {_accent_hov} !important;
    background-color: {_accent_hov} !important;
    transform: scale(1.05) !important;
}}

/* Scrollable chat area */
[data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] {{
    background: transparent !important;
    background-color: transparent !important;
}}

/* ═══════════════════════════════════════════════════════════════
   TEXT INPUTS — đảm bảo text & placeholder luôn ĐỌC ĐƯỢC ở dark mode
   Applied to rename_input + bất kỳ text_input nào trong page
   ═══════════════════════════════════════════════════════════════ */
html body [data-testid="stMain"] [data-testid="stTextInput"] input,
html body [data-testid="stSidebar"] [data-testid="stTextInput"] input {{
    color: {_fg_btn} !important;
    caret-color: {_accent} !important;
}}
html body [data-testid="stMain"] [data-testid="stTextInput"] input::placeholder,
html body [data-testid="stSidebar"] [data-testid="stTextInput"] input::placeholder {{
    color: {_fg_muted} !important;
    opacity: 0.85 !important;
}}
html body [data-testid="stMain"] [data-testid="stTextInput"] input::-webkit-input-placeholder,
html body [data-testid="stSidebar"] [data-testid="stTextInput"] input::-webkit-input-placeholder {{
    color: {_fg_muted} !important;
    opacity: 0.85 !important;
}}

/* Chat status gradient */
.chat-status-ok {{
    {'background: linear-gradient(90deg,rgba(52,211,153,.15) 0%,rgba(52,211,153,0) 100%) !important; color: #34D399 !important; border-color: rgba(52,211,153,.35) !important;' if _is_dark else 'background: linear-gradient(90deg,rgba(16,185,129,.10) 0%,rgba(16,185,129,0) 100%) !important; color: #047857 !important; border-color: rgba(16,185,129,.30) !important;'}
}}
.chat-status-warn {{
    {'background: linear-gradient(90deg,rgba(251,191,36,.15) 0%,rgba(251,191,36,0) 100%) !important; color: #FBBF24 !important; border-color: rgba(251,191,36,.35) !important;' if _is_dark else 'background: linear-gradient(90deg,rgba(245,158,11,.10) 0%,rgba(245,158,11,0) 100%) !important; color: #92400E !important; border-color: rgba(245,158,11,.30) !important;'}
}}

/* Bot message colors */
.bot-msg-container,
.bot-msg-container p,
.bot-msg-container li,
.bot-msg-container h1, .bot-msg-container h2,
.bot-msg-container h3, .bot-msg-container h4 {{
    color: {_fg_btn} !important;
}}
.bot-msg-container code {{
    background: {'rgba(255,255,255,0.08)' if _is_dark else 'rgba(15,23,42,0.06)'} !important;
    color: {_accent} !important;
    padding: 1px 5px !important;
    border-radius: 4px !important;
    font-family: 'Fira Code', monospace !important;
    font-size: 0.92em !important;
}}
.bot-msg-container hr {{
    border-color: {_brd_soft} !important;
}}
</style>
"""
    st.markdown(_css_block, unsafe_allow_html=True)

    col_sb, col_chat = st.columns([1, 3], gap='medium')

    with col_sb:
        _render_sidebar_history(_T)

    with col_chat:
        if not active_id:
            st.info(t('chatbot.no_conv_sel'))
            return

        conv = ch.get_conversation(active_id)
        if not conv:
            st.session_state['active_conv_id'] = None
            st.rerun()
            return

        _context = _build_context(ticker, r1, r2, r3, m1, m2, m3, df, ar_order)

        # Mini header
        _msg_count = len(conv.get('messages', []))
        _msg_count_label = t('chatbot.msg_count').replace('{n}', str(_msg_count))
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:12px;'
            f'padding:10px 16px;margin-bottom:12px;'
            f'background:{_T["bg_card"]};border:1px solid {_T["border"]};'
            f'border-radius:10px">'
            f'<span style="width:8px;height:8px;border-radius:50%;'
            f'background:{_T.get("accent","#1565C0")};flex-shrink:0"></span>'
            f'<span style="font-weight:700;font-size:14px;color:{_T["text_primary"]};'
            f'flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'
            f'{conv["title"]}</span>'
            f'<span style="font-size:10px;color:{_T["text_muted"]};'
            f'font-family:monospace">{_msg_count_label}</span>'
            f'</div>',
            unsafe_allow_html=True)

        messages = conv.get('messages', [])

        _search_msg_q = st.session_state.get('msg_search_q', '')
        _total_hits = 0

        with st.container(height=520, border=False):
            if not messages:
                _render_welcome_screen(_T, _lang, ticker)
            # Reset active match khi query đổi
            _prev_q = st.session_state.get('_msg_search_q_prev', '')
            if _search_msg_q != _prev_q:
                st.session_state['_msg_match_idx'] = 0
                st.session_state['_msg_search_q_prev'] = _search_msg_q
            _active_match = st.session_state.get('_msg_match_idx', 0)

            # Preview total từ lần render trước (dùng để clamp prev/next)
            _prev_total = st.session_state.get('_msg_total_hits_prev', 0)
            if _prev_total > 0 and _search_msg_q.strip():
                _active_match = _active_match % _prev_total
            else:
                _active_match = -1

            # Tìm index của tin bot cuối cùng (để show regenerate button)
            _last_bot_idx = -1
            for _i, _m in enumerate(messages):
                if _m['role'] == 'assistant':
                    _last_bot_idx = _i

            for i, msg in enumerate(messages):
                if msg['role'] == 'user':
                    _hits = _render_user_message(
                        msg['content'], msg.get('timestamp', ''), _T,
                        search_query=_search_msg_q, msg_idx=i,
                        match_offset=_total_hits, active_match=_active_match)
                else:
                    _hits = _render_bot_message(
                        msg['content'], msg.get('timestamp', ''), _T,
                        msg.get('diagram'),
                        search_query=_search_msg_q, msg_idx=i,
                        match_offset=_total_hits, active_match=_active_match,
                        is_last_bot=(i == _last_bot_idx))
                _total_hits += _hits

            st.session_state['_msg_total_hits_prev'] = _total_hits

            # Anchor cuối khung chat để JS scroll tới — chỉ khi KHÔNG search
            # (search sẽ scroll đến .match-active, anchor này dùng cho new message)
            if not _search_msg_q.strip() and messages:
                st.markdown(
                    '<div id="chat-bottom-anchor" '
                    'style="height:1px;width:100%;margin-top:-1px"></div>',
                    unsafe_allow_html=True)

        # Auto-scroll xuống tin nhắn mới nhất (chỉ khi có messages + không searching)
        if messages and not _search_msg_q.strip():
            _last_msg_id = f"{len(messages)}_{(messages[-1].get('timestamp') or '')}"
            if st.session_state.get('_last_scrolled_msg_id') != _last_msg_id:
                import streamlit.components.v1 as _components_s
                import random as _random_s
                _sc_token = _random_s.randint(0, 1_000_000_000)
                _components_s.html(
                    f"""<div style='display:none'>t={_sc_token}</div>
<script>
(function() {{
    var doc = window.parent.document;
    function tryScroll(attempt) {{
        var anchor = doc.getElementById('chat-bottom-anchor');
        if (anchor) {{
            var scroller = anchor.parentElement;
            while (scroller && scroller !== doc.body) {{
                var style = window.getComputedStyle(scroller);
                var oy = style.overflowY;
                if ((oy === 'auto' || oy === 'scroll') && scroller.scrollHeight > scroller.clientHeight) {{
                    break;
                }}
                scroller = scroller.parentElement;
            }}
            if (scroller && scroller !== doc.body) {{
                scroller.scrollTo({{top: scroller.scrollHeight, behavior: 'smooth'}});
            }} else {{
                anchor.scrollIntoView({{behavior: 'smooth', block: 'end'}});
            }}
            return;
        }}
        if (attempt < 10) {{
            setTimeout(function() {{ tryScroll(attempt + 1); }}, 80);
        }}
    }}
    tryScroll(0);
}})();
</script>""",
                    height=0,
                )
                st.session_state['_last_scrolled_msg_id'] = _last_msg_id

        # Action bar — search + nav + count
        st.markdown(
            f"<hr style='border:none;border-top:1px solid {_T['border']};"
            f"margin:8px 0 6px'/>", unsafe_allow_html=True)

        _n_msg = len(messages)
        _bg_el = _T.get('bg_elevated', '#F1F5F9')
        _brd   = _T.get('border', '#E2E8F0')
        _muted = _T.get('text_muted', '#94A3B8')

        _svg_search_badge = (
            f'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="2.2" stroke-linecap="round" '
            f'stroke-linejoin="round" style="flex-shrink:0">'
            f'<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>'
        )
        _svg_chat = (
            f'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="2.2" stroke-linecap="round" '
            f'stroke-linejoin="round" style="flex-shrink:0">'
            f'<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>'
            f'</svg>'
        )
        _svg_clock = (
            f'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="2.2" stroke-linecap="round" '
            f'stroke-linejoin="round" style="flex-shrink:0">'
            f'<circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15 14"/>'
            f'</svg>'
        )

        _is_searching = bool(_search_msg_q.strip())

        if _is_searching:
            # 4 cols: search + prev + count + next
            _c_search, _c_prev, _c_count, _c_next = st.columns([5, 0.8, 2, 0.8])
            with _c_search:
                st.text_input(
                    '',
                    placeholder=t('chatbot.search_placeholder'),
                    key='msg_search_q',
                    label_visibility='collapsed',
                )
            with _c_prev:
                if st.button('◀', key='match_prev_btn',
                             help='Kết quả trước' if _lang == 'VI' else 'Previous',
                             use_container_width=True,
                             disabled=_total_hits == 0):
                    st.session_state['_msg_match_idx'] = (
                        (_active_match - 1) % max(1, _total_hits))
                    st.rerun()
            with _c_count:
                _cur_pos = (_active_match + 1) if _total_hits > 0 else 0
                _hit_color = _T.get('accent', '#1565C0') if _total_hits else _muted
                _hit_label = (
                    f'{_cur_pos}/{_total_hits} kết quả · {_n_msg} tin'
                    if _lang == 'VI'
                    else f'{_cur_pos}/{_total_hits} match · {_n_msg} msg'
                )
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:7px;'
                    f'height:38px;padding:0 12px;border-radius:8px;'
                    f'background:{_bg_el};border:1px solid {_brd};'
                    f'font-size:12px;font-weight:600;color:{_hit_color};'
                    f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
                    f'{_svg_search_badge}<span>{_hit_label}</span></div>',
                    unsafe_allow_html=True)
            with _c_next:
                if st.button('▶', key='match_next_btn',
                             help='Kết quả tiếp theo' if _lang == 'VI' else 'Next',
                             use_container_width=True,
                             disabled=_total_hits == 0):
                    st.session_state['_msg_match_idx'] = (
                        (_active_match + 1) % max(1, _total_hits))
                    st.rerun()

            # Auto-scroll đến match-active qua JS
            # Token ngẫu nhiên ép component re-mount mỗi lần rerun (nếu không
            # Streamlit cache iframe cũ → script không chạy lại khi prev/next).
            if _total_hits > 0:
                import streamlit.components.v1 as _components
                import random as _random
                _scroll_token = _random.randint(0, 1_000_000_000)
                _components.html(
                    f"""<div style='display:none'>token={_scroll_token}</div>
<script>
(function() {{
    var doc = window.parent.document;
    function tryScroll(attempt) {{
        var el = doc.querySelector('.match-active');
        if (el) {{
            // Tìm ancestor có overflow scrollable (container chat 520px)
            var scroller = el.parentElement;
            while (scroller && scroller !== doc.body) {{
                var style = window.getComputedStyle(scroller);
                var oy = style.overflowY;
                if ((oy === 'auto' || oy === 'scroll') && scroller.scrollHeight > scroller.clientHeight) {{
                    break;
                }}
                scroller = scroller.parentElement;
            }}
            if (scroller && scroller !== doc.body) {{
                var elRect = el.getBoundingClientRect();
                var scRect = scroller.getBoundingClientRect();
                var offset = elRect.top - scRect.top - (scRect.height / 2) + (elRect.height / 2);
                scroller.scrollBy({{top: offset, behavior: 'smooth'}});
            }} else {{
                el.scrollIntoView({{behavior: 'smooth', block: 'center'}});
            }}
            return true;
        }}
        if (attempt < 10) {{
            setTimeout(function() {{ tryScroll(attempt + 1); }}, 80);
        }}
    }}
    tryScroll(0);
}})();
</script>""",
                    height=0,
                )
        else:
            _c_search, _c_count = st.columns([5, 3])
            with _c_search:
                st.text_input(
                    '',
                    placeholder=t('chatbot.search_placeholder'),
                    key='msg_search_q',
                    label_visibility='collapsed',
                )
            with _c_count:
                _upd_raw = conv.get('updated_at', '')
                _upd_short = ch.format_timestamp(_upd_raw) if _upd_raw else '—'
                _lbl_msg = 'tin' if _lang == 'VI' else 'msg'
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:10px;'
                    f'height:38px;padding:0 12px;border-radius:8px;'
                    f'background:{_bg_el};border:1px solid {_brd};'
                    f'font-size:12px;font-weight:600;color:{_muted};'
                    f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
                    f'<span style="display:inline-flex;align-items:center;gap:5px">'
                    f'{_svg_chat}<span>{_n_msg} {_lbl_msg}</span></span>'
                    f'<span style="opacity:0.4">·</span>'
                    f'<span style="display:inline-flex;align-items:center;gap:5px">'
                    f'{_svg_clock}<span>{_upd_short}</span></span>'
                    f'</div>',
                    unsafe_allow_html=True)

        # ── Regenerate handler: URL có ?regen=<ts> → remove tin bot cuối + re-ask ──
        _regen_param = st.query_params.get('regen', None)
        _regen_last = st.session_state.get('_last_regen_ts', '')
        _regen_pending = None
        if _regen_param and _regen_param != _regen_last:
            st.session_state['_last_regen_ts'] = _regen_param
            if messages and messages[-1].get('role') == 'assistant':
                last_user_q = None
                for _m in reversed(messages[:-1]):
                    if _m.get('role') == 'user':
                        last_user_q = _m.get('content')
                        break
                if last_user_q:
                    ch.remove_last_message(active_id)
                    _regen_pending = last_user_q
            try:
                st.query_params.clear()
            except Exception:
                pass

        # Input
        _user_input = st.chat_input(t('chatbot.input_placeholder'))
        # Priority: regenerate > welcome chip > user typed
        _pending_chip = st.session_state.pop('_pending_welcome_query', None)
        _query = _regen_pending or _pending_chip or _user_input
        _skip_add_user = bool(_regen_pending)  # regen không thêm user msg mới

        if _query:
            if not _skip_add_user:
                ch.add_message(active_id, 'user', _query)

            # Auto-detect ticker user gõ — nếu khác ticker sidebar, build
            # context cho ticker đó để bot trả lời chính xác về mã user hỏi
            _q_ticker = _detect_ticker_in_query(_query, ticker)
            _runtime_ctx, _runtime_ticker, _runtime_df = _context, ticker, df
            if _q_ticker:
                try:
                    from data.fetcher import fetch_data
                    from models.ar   import run_ar
                    from models.mlr  import run_mlr
                    from models.cart import run_cart
                    from data.metrics import calc_metrics
                    _alt_df  = fetch_data(_q_ticker, date_from, date_to)
                    _alt_r1  = run_ar  (_q_ticker, train_ratio, p=ar_order)
                    _alt_r2  = run_mlr (_q_ticker, train_ratio, p=ar_order)
                    _alt_r3  = run_cart(_q_ticker, train_ratio, p=ar_order)
                    _alt_m1  = calc_metrics(_alt_r1['yte'], _alt_r1['pte'],
                                            k=ar_order)
                    _alt_m2  = calc_metrics(_alt_r2['yte'], _alt_r2['pte'],
                                            k=3 * ar_order)
                    _alt_m3  = calc_metrics(_alt_r3['yte'], _alt_r3['pte'],
                                            k=6 * ar_order)
                    _runtime_ctx = _build_context(
                        _q_ticker, _alt_r1, _alt_r2, _alt_r3,
                        _alt_m1, _alt_m2, _alt_m3, _alt_df, ar_order,
                    )
                    _runtime_ticker = _q_ticker
                    _runtime_df = _alt_df
                except Exception as _alt_err:
                    _log(f'[Chatbot] ticker switch failed: {_alt_err}')

            response, diagram_html = _process_query(
                _query, _runtime_ctx, ar_order,
                _runtime_ticker, _runtime_df, _lang, _ai_ok,
            )

            nav_target = _detect_navigation_intent(_query)
            if nav_target:
                response = response + '\n\n' + _render_nav_hint(nav_target, _T)

            ch.add_message(active_id, 'assistant', response, diagram=diagram_html)
            st.rerun()
