import streamlit as st
import numpy as np

from core.i18n import t
from core.constants import CLR
from core.themes import theme
from data.metrics import _ci95, _star
from data.ichimoku import (
    add_ichimoku, classify_primary_trend, detect_tk_cross,
    classify_trading_signal, classify_chikou_confirmation,
    classify_future_kumo, aggregate_signals,
    _donchian_mid, SENKOU_N,
)
from ui.components import (
    sparkline_svg, render_ai_insight,
    render_param_timeline, render_param_badge,
)
from charts.comparison import chart_price_candlestick, render_candlestick_info_bar
from charts.base import _PLOTLY_CONFIG


@st.fragment
def _candlestick_section(df, ticker, _T, _is_en_cmp):
    """Toggle/zoom chart KHÔNG rerun toàn page — chỉ rerun fragment này.

    Streamlit 1.32+ st.fragment isolates reruns — đổi SMA/Ichimoku/Timeframe
    không gọi lại render() cha (KPI, forecast cards). Cảm giác instant.
    """
    _tf_col, _sma_col, _ichi_col = st.columns([3, 1, 1])
    with _tf_col:
        _tf_label = 'Khung thời gian' if not _is_en_cmp else 'Timeframe'
        _selected_tf = st.segmented_control(
            _tf_label,
            options=['1D', '1W', '1M', '3M'],
            default='1D',
            key=f'cs_tf_{ticker}',
            label_visibility='collapsed',
        )
    with _sma_col:
        _show_sma = st.toggle(
            'SMA 5/20', value=True, key=f'cs_sma_{ticker}',
            help=('Hiển thị 2 đường trung bình động SMA 5 (cam) & SMA 20 (tím)'
                  if not _is_en_cmp else
                  'Show SMA 5 (orange) & SMA 20 (purple) moving averages'),
        )
    with _ichi_col:
        _show_ichimoku = st.toggle(
            'Ichimoku', value=False, key=f'cs_ichi_{ticker}',
            help=('Hiển thị Tenkan, Kijun, Mây Kumo, Chikou (cần ≥30 phiên)'
                  if not _is_en_cmp else
                  'Show Tenkan, Kijun, Kumo cloud, Chikou (needs ≥30 bars)'),
        )
    if _selected_tf is None:
        _selected_tf = '1D'

    if _show_ichimoku and _selected_tf == '3M':
        st.caption(
            'ℹ️ Khung 3M có ≤20 phiên — Ichimoku chỉ hiển thị một phần.'
            if not _is_en_cmp else
            'ℹ️ 3M timeframe has ≤20 bars — Ichimoku will be partial.'
        )

    _cmp_hint = (
        'Đơn vị giá: <b>nghìn đ</b> · Chọn khung thời gian <b>1D/1W/1M/3M</b> · '
        'Nến <span style="color:#10B981">xanh</span> = tăng, '
        '<span style="color:#EF4444">đỏ</span> = giảm · '
        'Đường <span style="color:#F59E0B">SMA 5</span> & '
        '<span style="color:#8B5CF6">SMA 20</span> · '
        'Kéo <b>thanh price bên phải</b> để zoom giá.'
        if not _is_en_cmp else
        'Price unit: <b>k VND</b> · Pick timeframe <b>1D/1W/1M/3M</b> · '
        '<span style="color:#10B981">Green</span> = up, '
        '<span style="color:#EF4444">red</span> = down · '
        '<span style="color:#F59E0B">SMA 5</span> & '
        '<span style="color:#8B5CF6">SMA 20</span> overlays · '
        'Drag <b>right price scale</b> to zoom price.'
    )
    st.markdown(
        f'<div style="font-size:11px;color:{_T["text_muted"]};margin:-4px 0 6px;'
        f'line-height:1.5">{_cmp_hint}</div>',
        unsafe_allow_html=True,
    )

    _info_bar = render_candlestick_info_bar(df, ticker, _selected_tf, _T)
    if _info_bar:
        st.markdown(_info_bar, unsafe_allow_html=True)

    try:
        fig_cmp = chart_price_candlestick(
            df, ticker, _T,
            interval=_selected_tf,
            show_sma=_show_sma,
            show_ichimoku=_show_ichimoku,
        )
        _candle_config = {
            **_PLOTLY_CONFIG,
            'scrollZoom': True,
            'doubleClick': 'reset',
        }
        # key= → Streamlit persist UI state (zoom/pan) khi toggle SMA/Ichimoku
        st.plotly_chart(
            fig_cmp,
            use_container_width=True,
            config=_candle_config,
            key=f'candlestick_chart_{ticker}_{_selected_tf}',
        )
    except Exception as _e:
        st.error(f'Chart error: {_e}')


def render(ticker, train_ratio, date_from, date_to, df, r1, r2, r3, m1, m2, m3, _T,
           ar_order=1):
    col_t = CLR[ticker]

    T    = df.iloc[-1]
    ngay = str(df['Ngay'].iloc[-1])

    # ── Tính toán Ichimoku cho card tín hiệu tổng hợp ──────────────────
    _df_ichi   = add_ichimoku(df)
    _ichi_last = _df_ichi.iloc[-1]
    _close_now = float(_ichi_last['Close'])

    _prim_code, _ = classify_primary_trend(
        _close_now,
        float(_ichi_last['Kumo_top']) if not np.isnan(_ichi_last['Kumo_top']) else float('nan'),
        float(_ichi_last['Kumo_bot']) if not np.isnan(_ichi_last['Kumo_bot']) else float('nan'),
    )
    _tk_code, _, _ = detect_tk_cross(_df_ichi['Tenkan'], _df_ichi['Kijun'])
    _trd_code, _   = classify_trading_signal(_tk_code, _prim_code)
    _c26 = float(_df_ichi['Close'].iloc[-27]) if len(_df_ichi) >= 27 else float('nan')
    _chk_code, _   = classify_chikou_confirmation(_close_now, _c26)
    _ten_n = float(_ichi_last['Tenkan']); _kij_n = float(_ichi_last['Kijun'])
    _fa = (_ten_n + _kij_n) / 2.0
    _fb = float(_donchian_mid(df['High'], df['Low'], SENKOU_N).iloc[-1])
    _fut_code, _   = classify_future_kumo(_fa, _fb)

    _ov_code, _ov_label, _score = aggregate_signals(
        _prim_code, _trd_code, _chk_code, _fut_code)

    # Share Ichimoku summary sang chatbot qua session_state để AI trả lời đúng
    import streamlit as _st_ref
    _st_ref.session_state['ichimoku_summary'] = {
        'label':        _ov_label,
        'code':         _ov_code,
        'score':        int(_score),
        'primary':      _prim_code,
        'trading':      _trd_code,
        'chikou':       _chk_code,
        'future_kumo':  _fut_code,
    }

    st.markdown(
        f'<div style="background:{_T["banner_bg"]};'
        f'border-radius:14px;padding:14px 24px 12px;margin-bottom:12px;'
        f'box-shadow:{_T["shadow_lg"]}">'
        f'<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">'
        f'<span style="font-size:20px;font-weight:800;color:{_T["banner_text"]};letter-spacing:-.3px">'
        f'{t("dash.title", ticker=ticker)}</span>'
        f'<span style="font-size:11px;background:rgba(255,255,255,.15);color:{_T["banner_subtext"]};'
        f'padding:3px 10px;border-radius:20px;font-weight:600">{t("sector."+ticker)}</span>'
        f'</div>'
        f'<p style="color:{_T["banner_subtext"]};margin:4px 0 0;font-size:11.5px">'
        f'<span class="live-dot"></span>'
        f'<span style="color:#10B981;font-weight:700;font-size:10px;letter-spacing:1px">{t("dash.live")}</span>'
        f' &nbsp;·&nbsp; {t("dash.updated")}: <b style="color:{_T["banner_text"]}">{ngay}</b>'
        f' &nbsp;·&nbsp; {t("dash.train_test_info", tr=int(train_ratio*100), te=100-int(train_ratio*100))}'
        f' &nbsp;·&nbsp; AR({ar_order}) · MLR · CART</p>'
        f'</div>', unsafe_allow_html=True)

    ret_color   = '#1B6B2F' if T['Return'] >= 0 else '#C62828'
    ret_arr     = '▲' if T['Return'] >= 0 else '▼'
    vol_ratio_v = float(T['Volume_ratio'])
    vol_color   = '#C62828' if vol_ratio_v > 2 else ('#F9A825' if vol_ratio_v > 1.5 else '#2E7D32')
    sp30_svg    = sparkline_svg(df['Close'].values[-30:] * 1000, col_t)

    _CARD_STYLE = (
        f'background:{_T["bg_card"]};border-radius:14px;padding:18px 14px;'
        f'box-shadow:{_T["shadow_md"]};border:1px solid {_T["border"]};'
        f'min-height:160px;box-sizing:border-box;'
    )
    c_hero, c_rsi, c_ma, c_vol = st.columns([4, 2, 2, 2])
    with c_hero:
        st.markdown(
            f'<div style="{_CARD_STYLE}border-top:5px solid {col_t};padding:18px 20px;">'
            f'<div style="font-size:10px;font-weight:700;color:{_T["text_secondary"]};letter-spacing:.7px;'
            f'text-transform:uppercase;margin-bottom:8px">'
            f'{t("dash.latest_price")} &nbsp;·&nbsp; <b>{ngay}</b> '
            f'<span style="font-size:9px;color:#10B981;margin-left:4px">● {t("common.settled")}</span></div>'
            f'<div style="display:flex;align-items:flex-end;gap:12px;flex-wrap:wrap">'
            f'<div style="font-size:36px;font-weight:800;color:{_T["text_primary"]};line-height:1">'
            f'{T["Close"]*1000:,.0f} <span style="font-size:16px;color:{_T["text_muted"]}">đ</span></div>'
            f'<div style="display:inline-block;font-size:14px;font-weight:700;padding:5px 14px;'
            f'border-radius:20px;color:{ret_color};background:{_T["success_bg"] if T["Return"]>=0 else _T["danger_bg"]}">'
            f'{ret_arr} {abs(T["Return"]):.2f}%</div>'
            f'</div>'
            f'<div style="font-size:9px;color:{_T["text_muted"]};margin:8px 0 4px">{t("dash.last_30")}</div>'
            f'{sp30_svg}'
            f'</div>', unsafe_allow_html=True)
    with c_rsi:
        # Màu theo chiều consensus
        if   _ov_code in ('strong_bull', 'mild_bull'):  _ichi_col = '#2E7D32'
        elif _ov_code in ('strong_bear', 'mild_bear'):  _ichi_col = '#C62828'
        else:                                            _ichi_col = '#F9A825'

        # Nhãn hiển thị — dùng i18n (signal.overall.* đã include arrow)
        _ov_title_full = t(f'signal.overall.{_ov_code}')
        _ov_arrows_map = {
            'strong_bull': '▲▲', 'mild_bull': '▲',
            'neutral':     '=',
            'mild_bear':   '▼',  'strong_bear': '▼▼',
        }
        _ov_arrow = _ov_arrows_map.get(_ov_code, '=')
        _ov_title = _ov_title_full.replace(_ov_arrow, '').strip()

        # Mini-icon cho 4 tầng
        def _mini_icon(code):
            if 'counter' in code: return '⚡'
            if any(x in code for x in ('bull', 'buy')):  return '▲'
            if any(x in code for x in ('bear', 'sell')): return '▼'
            return '─'

        _mini_p = _mini_icon(_prim_code)
        _mini_t = _mini_icon(_trd_code)
        _mini_c = _mini_icon(_chk_code)
        _mini_f = _mini_icon(_fut_code)

        _bar_n   = min(abs(_score), 5)
        _score_s = f'+{_score}' if _score > 0 else str(_score)

        # Score bar bằng SVG: 5 ô vuông nhỏ, ô nào "on" thì đổ màu
        _cell_w, _cell_h, _cell_gap = 22, 8, 4
        _bar_w = 5 * _cell_w + 4 * _cell_gap
        _cells_svg = ''
        for _i in range(5):
            _x = _i * (_cell_w + _cell_gap)
            _fill = _ichi_col if _i < _bar_n else _T['bg_elevated']
            _cells_svg += (
                f'<rect x="{_x}" y="0" width="{_cell_w}" height="{_cell_h}" '
                f'rx="2" fill="{_fill}"/>'
            )
        _bar_svg = (
            f'<svg width="{_bar_w}" height="{_cell_h}" '
            f'style="display:block;margin:4px 0">{_cells_svg}</svg>'
        )

        st.markdown(
            f'<div style="{_CARD_STYLE}border-top:5px solid {_ichi_col}">'
            f'<div style="font-size:10px;font-weight:700;color:{_T["text_secondary"]};letter-spacing:.7px;'
            f'text-transform:uppercase;margin-bottom:6px">{t("dash.ichi_signal")}</div>'
            f'<div style="display:flex;align-items:baseline;gap:8px">'
            f'<div style="font-size:26px;font-weight:800;color:{_ichi_col};line-height:1">'
            f'{_ov_arrow} {_score_s}</div>'
            f'</div>'
            f'<div style="font-size:13px;font-weight:700;color:{_ichi_col};margin-top:4px">{_ov_title}</div>'
            f'<div style="font-size:10px;color:{_T["text_muted"]};margin-top:8px">Score {_score_s}/5</div>'
            f'{_bar_svg}'
            f'<div style="font-size:13px;color:{_T["text_secondary"]};margin-top:6px;letter-spacing:4px">'
            f'{_mini_p}&nbsp;{_mini_t}&nbsp;{_mini_c}&nbsp;{_mini_f}'
            f'</div>'
            f'<div style="font-size:9px;color:{_T["text_muted"]};margin-top:2px">'
            f'Trend · TK · Chikou · Future</div>'
            f'</div>', unsafe_allow_html=True)
    with c_ma:
        # ── Card BIẾN ĐỘNG 30 NGÀY (Volatility) ──────────────────────
        _ret30 = df['Return'].dropna().tail(30)
        if len(_ret30) >= 10:
            _vol_30d        = float(_ret30.std())
            _vol_annualized = _vol_30d * (252 ** 0.5)
        else:
            _vol_30d        = float('nan')
            _vol_annualized = float('nan')

        if   np.isnan(_vol_30d): _risk_col, _risk_key = '#94A3B8', 'dash.risk_na'
        elif _vol_30d < 1.5:     _risk_col, _risk_key = '#2E7D32', 'dash.risk_low'
        elif _vol_30d < 2.5:     _risk_col, _risk_key = '#F9A825', 'dash.risk_medium'
        else:                    _risk_col, _risk_key = '#C62828', 'dash.risk_high'
        _risk_label = t(_risk_key)
        _vol_str    = f'{_vol_30d:.2f}%' if not np.isnan(_vol_30d) else 'N/A'
        _ann_str    = f'{_vol_annualized:.1f}%' if not np.isnan(_vol_annualized) else 'N/A'

        st.markdown(
            f'<div style="{_CARD_STYLE}border-top:5px solid {_risk_col}">'
            f'<div style="font-size:10px;font-weight:700;color:{_T["text_secondary"]};letter-spacing:.7px;'
            f'text-transform:uppercase;margin-bottom:6px">{t("dash.volatility_title")}</div>'
            f'<div style="font-size:28px;font-weight:800;color:{_risk_col};line-height:1">{_vol_str}</div>'
            f'<div style="font-size:11px;color:{_T["text_secondary"]};margin-top:10px">'
            f'{t("dash.vol_annualized")}: <b>{_ann_str}</b></div>'
            f'<div style="display:inline-block;font-size:11px;font-weight:700;padding:3px 10px;'
            f'border-radius:12px;color:{_risk_col};'
            f'background:{_T["success_bg"] if _risk_col=="#2E7D32" else (_T["warning_bg"] if _risk_col=="#F9A825" else _T["danger_bg"])};'
            f'margin-top:8px">{t("dash.risk_label")}: {_risk_label}</div>'
            f'</div>', unsafe_allow_html=True)

    with c_vol:
        if vol_ratio_v > 2.5:   vol_label = t('dash.vol_very_high')
        elif vol_ratio_v > 1.5: vol_label = t('dash.vol_high')
        elif vol_ratio_v < 0.5: vol_label = t('dash.vol_low')
        else:                    vol_label = t('dash.vol_normal')
        st.markdown(
            f'<div style="{_CARD_STYLE}border-top:5px solid {vol_color}">'
            f'<div style="font-size:10px;font-weight:700;color:{_T["text_secondary"]};letter-spacing:.7px;'
            f'text-transform:uppercase;margin-bottom:6px">{t("dash.volume_title").upper()}</div>'
            f'<div style="font-size:28px;font-weight:800;color:{_T["text_primary"]};line-height:1">'
            f'{T["Volume"]/1e6:.2f}M</div>'
            f'<div style="display:inline-block;font-size:11px;font-weight:700;padding:3px 10px;'
            f'border-radius:12px;color:{vol_color};'
            f'background:{_T["danger_bg"] if vol_ratio_v>2 else _T["warning_bg"] if vol_ratio_v>1.5 else _T["success_bg"]};'
            f'margin-top:14px">{vol_label}</div>'
            f'</div>', unsafe_allow_html=True)

    st.markdown("<div style='margin:18px 0 12px'></div>", unsafe_allow_html=True)

    import datetime as _dt
    _last_date = df['Ngay'].iloc[-1]
    if isinstance(_last_date, str):
        _last_date = _dt.datetime.strptime(_last_date, '%Y-%m-%d').date()
    _next_date = _last_date
    while True:
        _next_date += _dt.timedelta(days=1)
        if _next_date.weekday() < 5:
            break

    _hdr_title = t('dash.forecast_1')
    if ar_order == 1:
        _sess_desc = f'{t("dash.based_on_close")} {_last_date}'
    else:
        _first_date = df['Ngay'].iloc[-ar_order]
        if isinstance(_first_date, str):
            _first_date = _dt.datetime.strptime(_first_date, '%Y-%m-%d').date()
        _sess_desc = t('dash.based_on_close_range',
                       p=ar_order, d0=_first_date, d1=_last_date)
    _model_spec_label = t('dash.model_spec', p=ar_order)

    st.markdown(
        f'<div class="sec-hdr">{_hdr_title} '
        f'<span style="font-size:11px;font-weight:600;color:{_T["text_muted"]};'
        f'margin-left:8px">'
        f'<b style="color:{_T["accent"]}">{_next_date.strftime("%Y-%m-%d")}</b> '
        f'({_sess_desc})</span></div>',
        unsafe_allow_html=True)

    _badges_html  = render_param_badge(ar_order, _T)
    _timeline_svg = render_param_timeline(ar_order, _T)
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:20px;flex-wrap:wrap;'
        f'margin:-4px 0 14px;padding:10px 16px;background:{_T["bg_card"]};'
        f'border:1px solid {_T["border"]};border-radius:10px">'
        f'<div style="flex:0 0 auto">{_badges_html}</div>'
        f'<div style="flex:0 0 auto">{_timeline_svg}</div>'
        f'<div style="flex:1;min-width:200px;font-size:11px;color:{_T["text_muted"]};'
        f'font-family:monospace;letter-spacing:0.3px">{_model_spec_label}</div>'
        f'</div>',
        unsafe_allow_html=True)

    best_i  = int(np.argmin([m1['MAPE'], m2['MAPE'], m3['MAPE']]))
    last30  = df['Close'].values[-30:] * 1000
    ci_vals = [
        _ci95(r1['yte'], r1['pte']) * 1000,
        _ci95(r2['yte'], r2['pte']) * 1000,
        _ci95(r3['yte'], r3['pte']) * 1000,
    ]
    _card_bg = {
        f'AR({ar_order})': _T['grad_ar'],
        'MLR':             _T['grad_mlr'],
        'CART':            _T['grad_cart'],
    }
    mc1, mc2, mc3 = st.columns(3)
    model_defs = [
        (f'AR({ar_order})', r1['next_pred'], m1, '#1565C0'),
        ('MLR',             r2['next_pred'], m2, '#6A1B9A'),
        ('CART',            r3['next_pred'], m3, '#2E7D32'),
    ]
    for mi, (mcol, (lbl, npred, mm, col_m)) in enumerate(zip([mc1, mc2, mc3], model_defs)):
        npred_d  = npred * 1000
        chg      = npred_d - T['Close'] * 1000
        pct      = chg / (T['Close'] * 1000) * 100
        arr      = '▲' if chg >= 0 else '▼'
        chg_col  = '#1B6B2F' if chg >= 0 else '#C62828'
        chg_bg   = 'rgba(27,107,47,.12)' if chg >= 0 else 'rgba(198,40,40,.12)'
        ci_d     = ci_vals[mi]
        rng_lo   = min(last30); rng_hi = max(last30)
        sp_svg   = sparkline_svg(last30, col_m)
        _stars   = _star(mm['MAPE'])
        _rank_here = [int(np.argmin([m1['MAPE'], m2['MAPE'], m3['MAPE']])),
                      int(np.argsort([m1['MAPE'], m2['MAPE'], m3['MAPE']])[1]),
                      int(np.argsort([m1['MAPE'], m2['MAPE'], m3['MAPE']])[2])]
        _my_rank = _rank_here.index(mi) if mi in _rank_here else 2
        if _my_rank == 0:
            best_bd = (
                f'<div style="display:inline-block;margin-top:10px;'
                f'background:linear-gradient(135deg,#F9A825 0%,#FFC107 100%);'
                f'color:#1A2A4A;font-size:10px;font-weight:800;'
                f'padding:4px 12px;border-radius:6px;letter-spacing:.5px;'
                f'box-shadow:0 2px 8px rgba(249,168,37,0.4)">'
                f'{t("dash.best_badge")} {_stars}</div>'
            )
        elif _my_rank == 1:
            best_bd = (
                f'<div style="display:inline-block;margin-top:10px;'
                f'background:rgba(148,163,184,0.18);color:{_T["text_secondary"]};'
                f'font-size:10px;font-weight:800;padding:4px 12px;border-radius:6px;letter-spacing:.5px">'
                f'{t("dash.second_badge")} {_stars}</div>'
            )
        else:
            best_bd = (
                f'<div style="display:inline-block;margin-top:10px;'
                f'background:rgba(180,83,9,0.15);color:{_T["warning"]};'
                f'font-size:10px;font-weight:800;padding:4px 12px;border-radius:6px;letter-spacing:.5px">'
                f'{t("dash.third_badge")} {_stars}</div>'
            )
        best_border = f'border:2px solid {_T["warning"]};' if mi == best_i else f'border:1px solid {_T["border"]};'
        best_class  = 'best-model-card' if mi == best_i else ''
        _sp_bg = 'rgba(255,255,255,0.12)' if st.session_state.get('theme_mode','light')=='dark' else 'rgba(255,255,255,0.65)'
        with mcol:
            st.markdown(
                f'<div class="{best_class}" style="background:{_card_bg[lbl]};border-radius:16px;padding:20px 18px;'
                f'{best_border}position:relative;overflow:hidden">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:4px">'
                f'<div style="font-size:11px;font-weight:600;color:{_T["text_secondary"]};letter-spacing:1.2px;'
                f'text-transform:uppercase">{t("col.model")}</div>'
                f'<div style="font-size:10px;color:{_T["text_muted"]};font-weight:500">MAPE test {mm["MAPE"]:.2f}%</div>'
                f'</div>'
                f'<div style="font-size:26px;font-weight:800;color:{_T["text_primary"]};letter-spacing:-.5px">{lbl}</div>'
                f'<div style="font-size:34px;font-weight:800;color:{_T["text_primary"]};line-height:1;margin:10px 0 0">'
                f'{npred_d:,.0f} <span style="font-size:16px;color:{_T["text_secondary"]};font-weight:500">đ</span></div>'
                f'<div style="display:inline-block;background:{chg_bg};color:{chg_col};font-size:13px;'
                f'font-weight:700;padding:5px 14px;border-radius:20px;margin:8px 0 0">'
                f'{arr} {abs(chg):,.0f} đ ({pct:+.2f}%)</div>'
                f'<div style="margin:12px 0 0;padding:10px;background:{_sp_bg};'
                f'border-radius:10px">'
                f'{sp_svg}'
                f'</div>'
                f'<div style="display:flex;justify-content:space-between;margin-top:8px;'
                f'font-size:10.5px;color:{_T["text_secondary"]}">'
                f'<span>{t("dash.last_30")}</span>'
                f'<span style="font-weight:600">Range: {rng_lo:,.0f}–{rng_hi:,.0f}</span>'
                f'</div>'
                f'<div style="font-size:10px;color:{_T["text_muted"]};margin-top:6px">'
                f'{t("dash.ci95")}: <b style="color:{chg_col}">[{npred_d-ci_d:,.0f} – {npred_d+ci_d:,.0f}]</b>'
                f'</div>'
                f'{best_bd}'
                f'</div>', unsafe_allow_html=True)

    # ── Labels i18n 4 tầng Ichimoku cho AI Insight ──────────────────────
    _prim_lbl = t(f'ichi.primary.{_prim_code}')
    _trd_lbl  = t(f'ichi.trading.{_trd_code}')

    if not (np.isnan(_close_now) or np.isnan(_c26) or _c26 == 0):
        _chk_pct2 = (_close_now - _c26) / _c26 * 100.0
        _chk_lbl  = t(f'ichi.chikou.{_chk_code}', pct=f'{_chk_pct2:+.2f}')
    else:
        _chk_lbl = t('ichi.chikou.na')

    if not (np.isnan(_fa) or np.isnan(_fb)):
        _mid2     = (_fa + _fb) / 2.0
        _fut_pct2 = (_fa - _fb) / _mid2 * 100.0 if _mid2 != 0 else 0.0
        _fut_lbl  = t(f'ichi.future.{_fut_code}', pct=f'{_fut_pct2:+.2f}')
    else:
        _fut_lbl = t('ichi.future.na')

    # Dự báo best model
    _best_model_name = [f'AR({ar_order})', 'MLR', 'CART'][best_i]
    _best_metrics    = [m1, m2, m3][best_i]
    _best_next_pred  = [r1, r2, r3][best_i]['next_pred']
    _best_pct        = (_best_next_pred - _close_now) / _close_now * 100.0

    st.markdown(render_ai_insight(
        ticker=ticker,
        overall_code=_ov_code,
        overall_label=t(f'ichi.overall.{_ov_code}'),
        score=_score,
        primary_label=_prim_lbl,
        trading_label=_trd_lbl,
        chikou_label=_chk_lbl,
        future_label=_fut_lbl,
        best_model=_best_model_name,
        best_mape=_best_metrics['MAPE'],
        best_r2adj=_best_metrics['R2adj'],
        next_price=_best_next_pred,
        next_pct=_best_pct,
        next_date=_next_date.strftime('%Y-%m-%d'),
        T=_T,
    ), unsafe_allow_html=True)

    st.markdown("<div style='margin:8px 0 12px'></div>", unsafe_allow_html=True)

    st.markdown(f'<div class="sec-hdr">{t("dash.comparison")}</div>', unsafe_allow_html=True)
    _is_en_cmp = st.session_state.get('lang', 'VI') == 'EN'

    # Chart trong fragment → toggle/timeframe đổi KHÔNG rerun KPI/forecast
    _candlestick_section(df, ticker, _T, _is_en_cmp)

    st.markdown("<div style='margin:12px 0 8px'></div>", unsafe_allow_html=True)
    st.markdown(f'<div class="sec-hdr">{t("dash.rank")}</div>', unsafe_allow_html=True)
    _medals     = [
        '<span style="background:#F9A825;color:#1A2A4A;font-weight:800;padding:4px 10px;border-radius:8px;font-size:12px;letter-spacing:0.5px">1ST</span>',
        '<span style="background:#94A3B8;color:#fff;font-weight:800;padding:4px 10px;border-radius:8px;font-size:12px;letter-spacing:0.5px">2ND</span>',
        '<span style="background:#CD7F32;color:#fff;font-weight:800;padding:4px 10px;border-radius:8px;font-size:12px;letter-spacing:0.5px">3RD</span>',
    ]
    _sorted_idx = list(np.argsort([m1['MAPE'], m2['MAPE'], m3['MAPE']]))
    _rank_of    = {v: i for i, v in enumerate(_sorted_idx)}
    _all_mapes  = [m1['MAPE'], m2['MAPE'], m3['MAPE']]
    _max_mape   = max(_all_mapes)
    _rows_html  = ''
    for _mi2, (_mn, _mm) in enumerate([(f'AR({ar_order})', m1), ('MLR', m2), ('CART', m3)]):
        _r        = _rank_of[_mi2]
        _bg       = f'background:{_T["warning_bg"]}' if _r == 0 else (f'background:{_T["bg_elevated"]}' if _r == 1 else f'background:{_T["bg_card"]}')
        _stars_td = _star(_mm['MAPE'])
        _mape_col = _T['success'] if _mm['MAPE'] < 1.5 else (_T['warning'] if _mm['MAPE'] < 2 else _T['danger'])
        _bar_pct  = 100 - (_mm['MAPE'] / _max_mape * 75)
        _rows_html += (
            f'<tr style="{_bg};color:{_T["text_primary"]};border-top:1px solid {_T["divider"]}">'
            f'<td style="padding:10px 12px;font-size:18px">{_medals[_r]}</td>'
            f'<td style="padding:10px 12px;font-weight:700">{_mn}</td>'
            f'<td style="padding:10px 12px;color:{_mape_col};font-weight:700">'
            f'{_mm["MAPE"]:.2f}% {_stars_td}</td>'
            f'<td style="padding:10px 14px;min-width:130px">'
            f'<div style="background:{_T["border"]};border-radius:4px;height:6px;overflow:hidden">'
            f'<div style="background:{_mape_col};width:{_bar_pct:.0f}%;height:100%"></div></div></td>'
            f'<td style="padding:10px 12px">{_mm["RMSE"]:.4f}</td>'
            f'<td style="padding:10px 12px">{_mm["MAE"]:.4f}</td>'
            f'<td style="padding:10px 12px;color:{_T["success"] if _mm["R2adj"]>0.95 else _T["text_secondary"]}">'
            f'{_mm["R2adj"]:.4f}</td>'
            f'</tr>'
        )
    st.markdown(
        f'<div style="border-radius:12px;overflow:hidden;border:1px solid {_T["border"]}">'
        f'<table style="width:100%;border-collapse:collapse;font-size:13px">'
        f'<thead><tr style="background:{_T["accent"]};color:#fff">'
        f'<th style="padding:10px 12px;text-align:left">{t("col.rank")}</th>'
        f'<th style="padding:10px 12px;text-align:left">{t("col.model")}</th>'
        f'<th style="padding:10px 12px;text-align:left">MAPE</th>'
        f'<th style="padding:10px 14px;text-align:left">Performance</th>'
        f'<th style="padding:10px 12px;text-align:left">RMSE</th>'
        f'<th style="padding:10px 12px;text-align:left">MAE</th>'
        f'<th style="padding:10px 12px;text-align:left">R²adj</th>'
        f'</tr></thead><tbody>{_rows_html}</tbody></table></div>',
        unsafe_allow_html=True)
