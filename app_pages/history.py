import streamlit as st
import io

from core.i18n import t
from charts.price import chart_price_history_plotly
from charts.portfolio import chart_returns_hist
from charts.base import _PLOTLY_CONFIG


def render(ticker, train_ratio, date_from, date_to, df, r1, r2, r3, m1, m2, m3, _T,
           ar_order=1):
    st.markdown(
        f'<div class="page-header">'
        f'<h1>{t("history.title")} — {ticker}</h1>'
        f'<p>{t("history.subtitle", ticker=ticker)}</p>'
        f'</div>', unsafe_allow_html=True)

    min_date = df['Ngay'].iloc[0]; max_date = df['Ngay'].iloc[-1]
    # Dùng date_from/date_to từ sidebar, clamp vào phạm vi data
    date_from_h = max(min_date, min(date_from, max_date)) if date_from else min_date
    date_to_h   = max(min_date, min(date_to,   max_date)) if date_to   else max_date
    if date_from_h > date_to_h:
        date_from_h, date_to_h = date_to_h, date_from_h

    # Thông tin split train/test (từ mô hình — toàn bộ dữ liệu)
    _nt        = r1['nt']
    _split_dt  = str(r1['dates_te'][0]) if len(r1['dates_te']) else '—'
    _train_s   = str(r1['dates_tr'][0])
    _train_e   = str(r1['dates_tr'][-1])
    _test_e    = str(r1['dates_te'][-1]) if len(r1['dates_te']) else '—'
    _n_total   = len(r1['dates_full'])
    _pct_tr    = int(round(_nt / _n_total * 100))
    _acc       = _T.get('accent', '#1565C0')
    _muted     = _T.get('text_muted', '#64748B')
    _card      = _T.get('bg_elevated', '#F1F5F9')
    _brd       = _T.get('border', '#E2E8F0')

    # Badge "đang hiển thị" theo bộ lọc sidebar
    _n_display = int(((df['Ngay'] >= date_from_h) & (df['Ngay'] <= date_to_h)).sum())
    _disp_clr  = '#059669' if not _T.get('is_dark') else '#34D399'
    st.markdown(
        f"<div style='display:flex;gap:8px;margin-bottom:10px;flex-wrap:wrap;align-items:center'>"
        # Badge hiển thị (màu xanh lá — bộ lọc sidebar)
        f"<div style='background:{_card};border:1.5px solid {_disp_clr};border-radius:8px;"
        f"padding:6px 13px;font-size:12px;color:{_muted};white-space:nowrap'>"
        f"<b style='color:{_disp_clr}'>{t('history.badge.showing')}</b>&nbsp; {date_from_h} → {date_to_h}"
        f"&nbsp;({_n_display:,} {t('history.sessions')})</div>"
        # Divider nhỏ
        f"<span style='color:{_muted};font-size:16px'>|</span>"
        # Badge train
        f"<div style='background:{_card};border:1px solid {_brd};border-radius:8px;"
        f"padding:6px 13px;font-size:12px;color:{_muted};white-space:nowrap'>"
        f"<b style='color:{_acc}'>TRAIN {_pct_tr}%</b>&nbsp; {_train_s} → {_train_e}"
        f"&nbsp;({_nt:,} {t('history.sessions')})</div>"
        # Badge test
        f"<div style='background:{_card};border:1px solid {_brd};border-radius:8px;"
        f"padding:6px 13px;font-size:12px;color:{_muted};white-space:nowrap'>"
        f"<b style='color:#EF4444'>TEST {100-_pct_tr}%</b>&nbsp; {_split_dt} → {_test_e}"
        f"&nbsp;({_n_total-_nt:,} {t('history.sessions')})</div>"
        # Badge tổng
        f"<div style='background:{_card};border:1px solid {_brd};border-radius:8px;"
        f"padding:6px 13px;font-size:12px;color:{_muted};white-space:nowrap'>"
        f"<b style='color:{_muted}'>{t('history.badge.total')}</b>&nbsp; {_n_total:,} {t('history.sessions')}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown(f'<div class="sec-hdr">{t("history.chart_hdr")}</div>', unsafe_allow_html=True)
    try:
        fig_hist = chart_price_history_plotly(r1, ticker, date_from_h, date_to_h, T=_T)
        st.plotly_chart(fig_hist, use_container_width=True, config={**_PLOTLY_CONFIG, 'toImageButtonOptions': {**_PLOTLY_CONFIG['toImageButtonOptions'], 'filename': f'{ticker}_history'}})
    except Exception as _e:
        st.error(t('error.hist_chart', e=_e))

    # Bảng & thống kê lọc theo date filter
    col_tbl, col_dist = st.columns([6, 4])
    mask = (df['Ngay'] >= date_from_h) & (df['Ngay'] <= date_to_h)

    # Tất cả cột có thể chọn: (key trong df, nhãn hiển thị, có nhân 1000 không, kiểu format)
    _COL_META = {
        'Close':  (t('col.close_vnd'),   True,  'price'),
        'Open':   ('Open (VNĐ)',          True,  'price'),
        'High':   ('High (VNĐ)',          True,  'price'),
        'Low':    ('Low (VNĐ)',           True,  'price'),
        'MA5':    (t('col.ma5'),          True,  'price'),
        'MA20':   (t('col.ma20'),         True,  'price'),
        'MA50':   ('MA50 (VNĐ)',          True,  'price'),
        'Volume': (t('col.volume'),       False, 'vol'),
        'RSI14':  (t('col.rsi14'),        False, 'rsi'),
        'Range':  (t('col.range'),        True,  'price'),
        'Return': (t('col.return_pct'),   False, 'ret'),
    }
    _DEFAULT_COLS = ['Close', 'MA5', 'MA20', 'RSI14', 'Volume', 'Range', 'Return']

    _col_labels = {k: v[0] for k, v in _COL_META.items()}

    with col_tbl:
        _hdr_col, _rows_col = st.columns([3, 2])
        with _hdr_col:
            st.markdown(f'<div class="sec-hdr">{t("history.table_hdr")}</div>', unsafe_allow_html=True)
        with _rows_col:
            n_rows = st.select_slider(t('history.rows_label'), options=[10, 20, 30, 50, 100], value=20)

        # Expander chọn cột — ẩn mặc định, mở khi cần
        _sel_keys = []
        with st.expander(t('history.col_picker'), expanded=False):
            _col_keys_list = list(_COL_META.keys())
            _ck_cols = st.columns(4)
            for _ci, _ck in enumerate(_col_keys_list):
                with _ck_cols[_ci % 4]:
                    if st.checkbox(_COL_META[_ck][0], value=(_ck in _DEFAULT_COLS),
                                   key=f'hcol_{_ck}'):
                        _sel_keys.append(_ck)
        if not _sel_keys:
            _sel_keys = _DEFAULT_COLS

        _all_cols = ['Ngay'] + _sel_keys
        _df_filtered = df[mask][_all_cols].tail(n_rows).copy()

        if _df_filtered.empty:
            # SVG inbox-empty icon tự build (thay 📭 emoji)
            _svg_empty = (
                '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" '
                'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
                'stroke-linejoin="round" style="display:inline-block;vertical-align:-6px;opacity:0.55">'
                '<polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/>'
                '<path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89'
                'A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>'
                '</svg>'
            )
            st.markdown(
                '<div class="info-box" style="text-align:center;padding:28px">'
                f'{_svg_empty} {t("history.empty")}<br>'
                f'<small>{t("history.empty_hint")}</small>'
                '</div>', unsafe_allow_html=True)
        else:
            _is_dk_hist = _T.get('is_dark', False)
            _bg1    = _T.get('bg_card', '#FFFFFF')
            _bg2    = _T.get('bg_elevated', '#F8FAFC')
            _fg     = _T.get('text_primary', '#0F172A')
            _fg_m   = _T.get('text_muted', '#64748B')
            _hdr_bg = '#1E293B' if _is_dk_hist else '#1E3A8A'
            _brd    = _T.get('border', '#E2E8F0')
            _col_ret_lbl = _col_labels.get('Return', 'Return')
            _col_rsi_lbl = _col_labels.get('RSI14', 'RSI14')
            _col_vol_lbl = _col_labels.get('Volume', 'Volume')
            _col_date_lbl = t('col.date')

            # Đổi tên cột và format giá trị
            _df_disp = _df_filtered.rename(columns={'Ngay': _col_date_lbl,
                                                     **{k: v[0] for k, v in _COL_META.items()}})
            for k, (lbl, x1k, _) in _COL_META.items():
                if k in _sel_keys and lbl in _df_disp.columns:
                    if x1k:
                        _df_disp[lbl] = (_df_disp[lbl] * 1000).round(0).astype(int)
                    elif k == 'RSI14':
                        _df_disp[lbl] = _df_disp[lbl].round(1)
                    elif k == 'Return':
                        _df_disp[lbl] = _df_disp[lbl].round(2)

            _tbl_css = f"""
<style>
.hist-tbl {{
    width:100%; border-collapse:collapse; font-size:13px;
    border-radius:10px; overflow:hidden;
    border: 1px solid {_brd};
}}
.hist-tbl th {{
    background:{_hdr_bg}; color:#FFFFFF; font-weight:700;
    padding:9px 10px; text-align:right; white-space:nowrap;
    font-size:12px; letter-spacing:0.03em;
}}
.hist-tbl th:first-child {{ text-align:left; }}
.hist-tbl td {{
    padding:7px 10px; text-align:right; color:{_fg};
    white-space:nowrap; border-bottom:1px solid {_brd};
}}
.hist-tbl td:first-child {{ text-align:left; color:{_fg_m}; }}
.hist-tbl tr:nth-child(odd) td {{ background:{_bg1}; }}
.hist-tbl tr:nth-child(even) td {{ background:{_bg2}; }}
.hist-tbl-wrap {{ max-height:420px; overflow-y:auto; border-radius:10px; }}
</style>"""

            _hdrs     = _df_disp.columns.tolist()
            _hdr_html = ''.join(f'<th>{h}</th>' for h in _hdrs)
            _rows_html = ''
            for _, row in _df_disp.iterrows():
                _cells = ''
                for col in _hdrs:
                    val    = row[col]
                    _extra = ''
                    if col == _col_ret_lbl:
                        if isinstance(val, (int, float)) and val > 0:
                            _extra = ('color:#34D399;background:rgba(52,211,153,0.18);font-weight:700'
                                      if _is_dk_hist else
                                      'color:#1B6B2F;background:#E8F5E9;font-weight:600')
                        elif isinstance(val, (int, float)) and val < 0:
                            _extra = ('color:#F87171;background:rgba(248,113,113,0.18);font-weight:700'
                                      if _is_dk_hist else
                                      'color:#C62828;background:#FFEBEE;font-weight:600')
                        disp = f'{val:+.2f}%' if isinstance(val, (int, float)) else str(val)
                    elif col == _col_rsi_lbl:
                        if isinstance(val, (int, float)):
                            if val > 70:
                                _extra = f'color:{"#F87171" if _is_dk_hist else "#C62828"};font-weight:700'
                            elif val < 30:
                                _extra = f'color:{"#60A5FA" if _is_dk_hist else "#1565C0"};font-weight:700'
                        disp = f'{val:.1f}' if isinstance(val, (int, float)) else str(val)
                    elif col == _col_vol_lbl:
                        disp = f'{val:,.0f}' if isinstance(val, (int, float)) else str(val)
                    else:
                        disp = str(val)
                    _style_attr = f' style="{_extra}"' if _extra else ''
                    _cells += f'<td{_style_attr}>{disp}</td>'
                _rows_html += f'<tr>{_cells}</tr>'

            st.markdown(
                _tbl_css +
                f'<div class="hist-tbl-wrap"><table class="hist-tbl">'
                f'<thead><tr>{_hdr_html}</tr></thead>'
                f'<tbody>{_rows_html}</tbody>'
                f'</table></div>',
                unsafe_allow_html=True,
            )
            # CSV chỉ chứa cột đang hiển thị
            csv_buf = io.StringIO()
            df[mask][_all_cols].to_csv(csv_buf, index=False)
            st.download_button(t('history.download'), data=csv_buf.getvalue(),
                               file_name=f'{ticker}_history.csv', mime='text/csv',
                               use_container_width=True)

    with col_dist:
        st.markdown(f'<div class="sec-hdr">{t("history.return_hdr")}</div>', unsafe_allow_html=True)
        df_period = df[mask]
        fig_ret   = chart_returns_hist(df_period, ticker, T=_T)
        st.plotly_chart(fig_ret, use_container_width=True, config=_PLOTLY_CONFIG)
        ret_vals = df_period['Return'].dropna()
        c1, c2 = st.columns(2)
        c1.metric(t('history.stats_up'),   f"{(ret_vals > 0).mean()*100:.1f}%")
        c2.metric(t('history.stats_down'), f"{(ret_vals < 0).mean()*100:.1f}%")
        c1.metric(t('stats.return_avg'),   f"{ret_vals.mean():+.3f}%")
        c2.metric(t('stats.std'),          f"{ret_vals.std():.3f}%")
