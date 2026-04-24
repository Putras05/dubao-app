"""
Trang "Tín hiệu & Cảnh báo Ichimoku" — hiển thị:
  1. Kết luận tổng hợp (consensus score ±5)
  2. Bốn tầng tín hiệu Ichimoku (Primary, Trading, Chikou, Future Kumo)
  3. Biểu đồ Ichimoku Kinko Hyo
  4. Ba đặc trưng dẫn xuất (TK Momentum, Cloud Distance, Chikou Momentum)

Toàn bộ logic dựa trên Ichimoku chuẩn Hosoda (1969) và các bài báo:
Patel (2010), Gurrib (2016), Deng & Zhao (2021), Shrestha (2022).
Xem data/ichimoku.py để biết chi tiết công thức và chứng minh anti-leak.
"""
import streamlit as st
import numpy as np

from core.i18n import t
from charts.base import _PLOTLY_CONFIG
from data.ichimoku import (
    add_ichimoku, classify_primary_trend, detect_tk_cross,
    classify_trading_signal, classify_chikou_confirmation,
    classify_future_kumo, aggregate_signals,
    _donchian_mid, SENKOU_N, DISPLACE,
)
from charts.ichimoku import chart_ichimoku_plotly


# ── Bảng phân loại màu/icon — exact set lookup, không dùng substring ────────
_BULL_CODES    = {'bull', 'strong_buy', 'weak_buy', 'bull_conf', 'bull_kumo',
                  'strong_bull', 'mild_bull'}
_BEAR_CODES    = {'bear', 'strong_sell', 'weak_sell', 'bear_conf', 'bear_kumo',
                  'strong_bear', 'mild_bear'}
_COUNTER_CODES = {'counter_buy', 'counter_sell'}


def _sig_color(code: str, is_dark: bool) -> str:
    if code in _COUNTER_CODES: return '#FBBF24' if is_dark else '#B45309'
    if code in _BULL_CODES:    return '#34D399' if is_dark else '#15803D'
    if code in _BEAR_CODES:    return '#F87171' if is_dark else '#C62828'
    return '#94A3B8' if is_dark else '#475569'


def _sig_bg(code: str, is_dark: bool) -> str:
    if code in _COUNTER_CODES: return 'rgba(251,191,36,0.12)' if is_dark else 'rgba(180,83,9,0.07)'
    if code in _BULL_CODES:    return 'rgba(52,211,153,0.10)'  if is_dark else 'rgba(21,128,61,0.07)'
    if code in _BEAR_CODES:    return 'rgba(248,113,113,0.12)' if is_dark else 'rgba(198,40,40,0.07)'
    return 'rgba(148,163,184,0.08)'


def _sig_icon(code: str) -> str:
    """Trả về SVG icon tự build (bolt cho counter, up-arrow cho bull, down-arrow cho bear)."""
    if code in _COUNTER_CODES:
        # SVG tia sét (bolt) — tự vẽ từ 2 polygon, không dùng emoji
        return (
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" '
            'stroke="currentColor" stroke-width="0.5" stroke-linejoin="round" '
            'style="display:inline-block;vertical-align:-2px">'
            '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>'
            '</svg>'
        )
    if code in _BULL_CODES:
        return (
            '<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" '
            'stroke="currentColor" stroke-width="1" stroke-linejoin="round" '
            'style="display:inline-block;vertical-align:-1px">'
            '<path d="M12 4 22 18H2z"/>'
            '</svg>'
        )
    if code in _BEAR_CODES:
        return (
            '<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" '
            'stroke="currentColor" stroke-width="1" stroke-linejoin="round" '
            'style="display:inline-block;vertical-align:-1px">'
            '<path d="M12 20 2 6h20z"/>'
            '</svg>'
        )
    # Neutral — em-dash char (không phải emoji)
    return ('<span style="display:inline-block;font-weight:700;'
            'font-family:monospace">—</span>')


def render(ticker, train_ratio, date_from, date_to, df, r1, r2, r3, m1, m2, m3, _T,
           ar_order=1):
    st.markdown(
        f'<div class="page-header">'
        f'<h1>{t("nav.signals")} — {ticker}</h1>'
        f'<p>{t("signal.subtitle", ticker=ticker) if "signal.subtitle" in __import__("core.i18n", fromlist=["TEXT"]).TEXT else "Hệ cảnh báo dựa trên Ichimoku Kinko Hyo — tham số chuẩn (9·26·52)."}</p>'
        f'</div>', unsafe_allow_html=True)

    is_dark  = _T.get('is_dark', False)
    _fg      = _T['text_primary']
    _fg_s    = _T['text_secondary']
    _bg_card = _T['bg_card']
    _bg_elev = _T['bg_elevated']
    _brd     = _T['border']
    _acc     = _T.get('accent', '#1565C0')
    _muted   = _T.get('text_muted', '#64748B')

    # ── Dữ liệu hiện tại ─────────────────────────────────────────────────
    ngay  = str(df['Ngay'].iloc[-1])
    close = float(df['Close'].iloc[-1])

    # ── Tính Ichimoku ────────────────────────────────────────────────────
    df_ichi = add_ichimoku(df)
    last    = df_ichi.iloc[-1]

    # ── Tầng 1 — Primary Trend ──────────────────────────────────────────
    primary_code, _ = classify_primary_trend(
        close,
        float(last['Kumo_top']) if not np.isnan(last['Kumo_top']) else float('nan'),
        float(last['Kumo_bot']) if not np.isnan(last['Kumo_bot']) else float('nan'),
    )
    primary_label = t(f'ichi.primary.{primary_code}')

    # ── Tầng 2 — TK Cross + Trading Signal ─────────────────────────────
    tk_code, _, _tk_off = detect_tk_cross(df_ichi['Tenkan'], df_ichi['Kijun'])
    tk_label = t(f'ichi.tk.{tk_code}', off=_tk_off if _tk_off is not None else 0)
    trading_code, _ = classify_trading_signal(tk_code, primary_code)
    trading_label = t(f'ichi.trading.{trading_code}')

    # ── Tầng 3 — Chikou Confirmation ───────────────────────────────────
    # So sánh: Close[t] vs Close[t-26]. Tại t cả 2 đều đã biết → không leak.
    close_now   = float(df_ichi['Close'].iloc[-1])
    close_26ago = float(df_ichi['Close'].iloc[-27]) if len(df_ichi) >= 27 else float('nan')
    chikou_code, _ = classify_chikou_confirmation(close_now, close_26ago)
    if not (np.isnan(close_now) or np.isnan(close_26ago) or close_26ago == 0):
        _chk_pct = (close_now - close_26ago) / close_26ago * 100.0
        chikou_label = t(f'ichi.chikou.{chikou_code}', pct=f'{_chk_pct:+.2f}')
    else:
        chikou_label = t('ichi.chikou.na')

    # ── Tầng 4 — Future Kumo tại T+26 ──────────────────────────────────
    # sen_a_future[t+26] = (Tenkan[t] + Kijun[t])/2  — dữ liệu tại t, không leak.
    _ten_now = float(df_ichi['Tenkan'].iloc[-1])
    _kij_now = float(df_ichi['Kijun'].iloc[-1])
    future_a = (_ten_now + _kij_now) / 2.0
    future_b = float(_donchian_mid(df['High'], df['Low'], SENKOU_N).iloc[-1])
    future_code, _ = classify_future_kumo(future_a, future_b)
    if not (np.isnan(future_a) or np.isnan(future_b)):
        _mid = (future_a + future_b) / 2.0
        _fut_pct = (future_a - future_b) / _mid * 100.0 if _mid != 0 else 0.0
        future_label = t(f'ichi.future.{future_code}', pct=f'{_fut_pct:+.2f}')
    else:
        future_label = t('ichi.future.na')

    # ── Tổng hợp ─────────────────────────────────────────────────────────
    overall_code, _, score = aggregate_signals(
        primary_code, trading_code, chikou_code, future_code
    )
    overall_label = t(f'ichi.overall.{overall_code}')

    # Share Ichimoku summary sang chatbot qua session_state → AI dùng trong context
    st.session_state['ichimoku_summary'] = {
        'label':        overall_label,
        'code':         overall_code,
        'score':        int(score),
        'primary':      primary_code,
        'trading':      trading_code,
        'chikou':       chikou_code,
        'future_kumo':  future_code,
    }

    # ════════════════════════════════════════════════════════════════════
    # PHẦN 1 — Kết luận tổng hợp
    # ════════════════════════════════════════════════════════════════════
    st.markdown(f'<div class="sec-hdr">{t("signal.summary_hdr")}</div>',
                unsafe_allow_html=True)

    _ov_color  = _sig_color(overall_code, is_dark)
    _ov_bg     = _sig_bg(overall_code, is_dark)
    _score_lbl = f'+{score}' if score > 0 else str(score)
    _bar_n     = min(abs(score), 5)

    # Score bar bằng SVG — render nhất quán trên mọi font/browser
    _cell_w, _cell_h, _cell_gap = 26, 10, 5
    _bar_w = 5 * _cell_w + 4 * _cell_gap
    _cells_svg = ''
    for _i in range(5):
        _x = _i * (_cell_w + _cell_gap)
        _fill = _ov_color if _i < _bar_n else _bg_elev
        _cells_svg += (
            f'<rect x="{_x}" y="0" width="{_cell_w}" height="{_cell_h}" '
            f'rx="2" fill="{_fill}"/>'
        )
    _bar_svg = (
        f'<svg width="{_bar_w}" height="{_cell_h}" '
        f'style="display:inline-block;vertical-align:middle;margin-left:8px">'
        f'{_cells_svg}</svg>'
    )

    _ov_title = t(f'signal.overall.{overall_code}')

    st.markdown(f"""
<div style="background:{_ov_bg};border:2px solid {_ov_color};border-radius:14px;
            padding:18px 22px;margin-bottom:18px;display:flex;
            align-items:center;gap:20px;flex-wrap:wrap">
  <div style="font-size:32px;font-weight:900;color:{_ov_color};min-width:52px;line-height:1">
    {_score_lbl}
  </div>
  <div style="flex:1;min-width:180px">
    <div style="font-size:19px;font-weight:800;color:{_ov_color}">{_ov_title}</div>
    <div style="font-size:13px;color:{_fg_s};margin-top:4px">{overall_label}</div>
    <div style="font-size:11px;color:{_muted};margin-top:3px;display:flex;align-items:center;gap:2px">
      <span style="font-family:monospace">Score {_score_lbl} / 5</span>
      {_bar_svg}
    </div>
  </div>
  <div style="font-size:12px;color:{_fg_s};text-align:right;white-space:nowrap">
    <div style="font-weight:700">{ticker} · {ngay}</div>
    <div>{t('common.price')}: {close*1000:,.0f} đ</div>
    <div style="font-size:11px;color:{_muted};margin-top:2px">
      {t('signal.kumo_range')} [{float(last["Kumo_bot"])*1000:,.0f} – {float(last["Kumo_top"])*1000:,.0f}]
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════
    # PHẦN 2 — Bốn tầng tín hiệu Ichimoku
    # ════════════════════════════════════════════════════════════════════
    st.markdown(f'<div class="sec-hdr">{t("signal.tiers_hdr")}</div>',
                unsafe_allow_html=True)

    _layers = [
        (t('signal.tier1_title'),
         primary_code, primary_label,
         t('signal.tier1_note')),

        (t('signal.tier2_title'),
         trading_code, trading_label,
         t('signal.tier2_note', status=tk_label)),

        (t('signal.tier3_title'),
         chikou_code, chikou_label,
         t('signal.tier3_note',
           now=f'{close*1000:,.0f}',
           past=f'{close_26ago*1000:,.0f}',
           muted=_muted)),

        (t('signal.tier4_title'),
         future_code, future_label,
         t('signal.tier4_note',
           a=f'{future_a:.3f}',
           b=f'{future_b:.3f}')),
    ]

    col_l1, col_l2 = st.columns(2)
    for _i, (title, code, label, note) in enumerate(_layers):
        _col   = col_l1 if _i % 2 == 0 else col_l2
        _c     = _sig_color(code, is_dark)
        _bg_ly = _sig_bg(code, is_dark)
        _ic    = _sig_icon(code)
        with _col:
            st.markdown(f"""
<div style="background:{_bg_ly};border:1px solid {_brd};border-radius:10px;
            padding:12px 14px;margin-bottom:10px">
  <div style="font-size:10px;font-weight:700;color:{_muted};text-transform:uppercase;
              letter-spacing:0.5px;margin-bottom:5px">{title}</div>
  <div style="font-size:15px;font-weight:800;color:{_c}">{_ic} {label}</div>
  <div style="font-size:11px;color:{_fg_s};margin-top:6px;line-height:1.4">{note}</div>
</div>
""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════
    # PHẦN 3 — Biểu đồ Ichimoku Kinko Hyo
    # ════════════════════════════════════════════════════════════════════
    st.markdown(
        f'<div class="sec-hdr" style="margin-top:16px">'
        f'{t("signal.ichi_chart_hdr", ticker=ticker)}</div>',
        unsafe_allow_html=True)
    try:
        _fig_ichi = chart_ichimoku_plotly(df_ichi, ticker, T=_T)
        st.plotly_chart(_fig_ichi, use_container_width=True,
            config={**_PLOTLY_CONFIG, 'toImageButtonOptions': {
                **_PLOTLY_CONFIG['toImageButtonOptions'],
                'filename': f'{ticker}_ichimoku',
            }})
    except Exception as _e:
        st.error(t('signal.error_ichi', e=str(_e)))

    # ════════════════════════════════════════════════════════════════════
    # PHẦN 4 — Ba đặc trưng dẫn xuất Ichimoku
    # ════════════════════════════════════════════════════════════════════
    st.markdown(f'<div class="sec-hdr" style="margin-top:16px">{t("signal.features_hdr")}</div>',
                unsafe_allow_html=True)

    _tk_mom   = float(df_ichi['TK_momentum'].iloc[-1])
    _cld_dist = float(df_ichi['Cloud_dist'].iloc[-1])
    _chk_mom  = float(df_ichi['Chikou_momentum'].iloc[-1])

    def _feat_card(col, title, formula, val_str, desc, code):
        _c = _sig_color(code, is_dark)
        col.markdown(f"""
<div style="background:{_bg_card};border:1px solid {_brd};border-radius:10px;
            padding:14px 16px;height:100%">
  <div style="font-size:11px;color:{_muted};font-weight:700;margin-bottom:3px">{title}</div>
  <div style="font-size:10px;color:{_muted};font-family:monospace;margin-bottom:6px;
              font-style:italic">{formula}</div>
  <div style="font-size:22px;font-weight:900;color:{_c}">{val_str}</div>
  <div style="font-size:11px;color:{_fg_s};margin-top:5px;line-height:1.4">{desc}</div>
</div>""", unsafe_allow_html=True)

    _f1, _f2, _f3 = st.columns(3)

    # [1] TK Momentum
    _tk_c    = ('bull' if _tk_mom >  0.05 else
                'bear' if _tk_mom < -0.05 else 'neut')
    _tk_str  = f'{_tk_mom:+.3f}%' if not np.isnan(_tk_mom) else 'N/A'
    _tk_desc = (t('signal.feat_tk_bull') if _tk_mom > 0.05 else
                (t('signal.feat_tk_bear') if _tk_mom < -0.05 else
                 t('signal.feat_tk_neut')))
    _feat_card(_f1, t('signal.feat_tk_momentum'),
               t('signal.feat_tk_formula'),
               _tk_str, _tk_desc, _tk_c)

    # [2] Cloud Distance
    _cd_c    = ('bull' if _cld_dist >  0.5 else
                'bear' if _cld_dist < -0.5 else 'neut')
    _cd_str  = f'{_cld_dist:+.3f}%' if not np.isnan(_cld_dist) else 'N/A'
    _cd_desc = (t('signal.feat_cd_bull') if _cld_dist > 0.5 else
                (t('signal.feat_cd_bear') if _cld_dist < -0.5 else
                 t('signal.feat_cd_neut')))
    _feat_card(_f2, t('signal.feat_cd_name'),
               t('signal.feat_cd_formula'),
               _cd_str, _cd_desc, _cd_c)

    # [3] Chikou Momentum
    _cm_c    = ('bull' if _chk_mom >  0.5 else
                'bear' if _chk_mom < -0.5 else 'neut')
    _cm_str  = f'{_chk_mom:+.3f}%' if not np.isnan(_chk_mom) else 'N/A'
    _cm_desc = (t('signal.feat_cm_bull') if _chk_mom > 0.5 else
                (t('signal.feat_cm_bear') if _chk_mom < -0.5 else
                 t('signal.feat_cm_neut')))
    _feat_card(_f3, t('signal.feat_cm_name'),
               t('signal.feat_cm_formula'),
               _cm_str, _cm_desc, _cm_c)
