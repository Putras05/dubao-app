import streamlit as st
import numpy as np

import plotly.graph_objects as go

from core.i18n import t
from data.metrics import calc_metrics
from charts.price import chart_price_history_plotly
from charts.comparison import chart_test_result_plotly
from charts.tree import render_decision_tree_cart
from charts.base import _PLOTLY_CONFIG


def render(ticker, train_ratio, date_from, date_to, df, r1, r2, r3, m1, m2, m3, _T,
           ar_order=1):
    st.markdown(
        f'<div class="page-header">'
        f'<h1>{t("analysis.title")} — {ticker}</h1>'
        f'<p>{t("sector."+ticker)} &nbsp;·&nbsp; {t("desc."+ticker)}</p>'
        f'</div>', unsafe_allow_html=True)

    import datetime as _dt
    _last_date_a = df['Ngay'].iloc[-1]
    if isinstance(_last_date_a, str):
        _last_date_a = _dt.datetime.strptime(_last_date_a, '%Y-%m-%d').date()
    _next_date_a = _last_date_a
    while True:
        _next_date_a += _dt.timedelta(days=1)
        if _next_date_a.weekday() < 5:
            break
    if ar_order == 1:
        _src_desc = f'{t("dash.based_on_close")} {_last_date_a}'
    else:
        _first_date_a = df['Ngay'].iloc[-ar_order]
        if isinstance(_first_date_a, str):
            _first_date_a = _dt.datetime.strptime(_first_date_a, '%Y-%m-%d').date()
        _src_desc = t('dash.based_on_close_range',
                      p=ar_order, d0=_first_date_a, d1=_last_date_a)
    _next_lbl = (
        f'<span style="font-size:11px;font-weight:600;color:{_T["text_muted"]};'
        f'margin-left:6px">'
        f'· {t("dash.forecast_for")} <b style="color:{_T["accent"]}">{_next_date_a.strftime("%Y-%m-%d")}</b> '
        f'({_src_desc})</span>'
    )

    tab_ar1, tab_mlr, tab_cart = st.tabs([f'  AR({ar_order})  ', '  MLR  ', '  CART  '])

    with tab_ar1:
        m_tr1 = calc_metrics(r1['ytr'], r1['ptr'])
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric(t('metric.mape_train'), f"{m_tr1['MAPE']:.2f}%")
        c2.metric(t('metric.mape_test'),  f"{m1['MAPE']:.2f}%")
        c3.metric("RMSE",                 f"{m1['RMSE']:.4f}")
        c4.metric("MAE",                  f"{m1['MAE']:.4f}")
        c5.metric("R²adj",                f"{m1['R2adj']:.4f}")
        st.markdown(
            f'<div class="info-box">'
            + t('analysis.train_range_info',
                d0=str(r1['dates_tr'][0]), d1=str(r1['dates_tr'][-1]), n=r1['nt'],
                t0=str(r1['dates_te'][0]), t1=str(r1['dates_te'][-1]), m=len(r1['yte']))
            + _next_lbl
            + f'</div>', unsafe_allow_html=True)
        with st.expander(t('analysis.equation_ar1')):
            _p_a = r1.get('p', 1)
            _h_a = r1.get('h', 1)
            _coefs_a = r1.get('coefs', [r1.get('rho', 0)])
            _c_a = r1.get('c', r1.get('intercept', 0))

            _ar_terms = []
            for _k, _rho_k in enumerate(_coefs_a):
                _sub = 't' if _k == 0 else f't-{_k}'
                if _k == 0:
                    _ar_terms.append(f'{float(_rho_k):.6f} \\cdot Y_{{{_sub}}}')
                else:
                    _sign = '+' if _rho_k >= 0 else '-'
                    _ar_terms.append(f'{_sign} {abs(float(_rho_k)):.6f} \\cdot Y_{{{_sub}}}')
            _ar_eq_body = ' '.join(_ar_terms)
            _c_sign = '+' if _c_a >= 0 else '-'
            _ar_eq = f'$$\\hat{{Y}}_{{t+{_h_a}}} = {_ar_eq_body} {_c_sign} {abs(float(_c_a)):.6f}$$'

            _rows = [f'| $\\hat{{c}}$ | {float(_c_a):.6f} | {t("ar1.intercept")} |']
            _is_en_tbl = st.session_state.get('lang', 'VI') == 'EN'
            _coef_meaning = 'Order' if _is_en_tbl else 'Hệ số bậc'
            for _k, _rho_k in enumerate(_coefs_a):
                _lag_label = 't' if _k == 0 else f't-{_k}'
                _rows.append(f'| $\\hat{{\\rho}}_{{{_k+1}}}$ ($Y_{{{_lag_label}}}$) | {float(_rho_k):.6f} | {_coef_meaning} {_k+1} |')
            _coef_table = '\n'.join(_rows)

            st.markdown(f"""
{t('ar1.model_header')} — AR({_p_a}, h={_h_a})

{_ar_eq}

| {t('ar1.param')} | {t('ar1.value')} | {t('ar1.meaning')} |
|---------|---------|---------|
{_coef_table}

- $\\hat{{\\rho}}_1 \\approx 1$ → **{t('ar1.unit_root')}**
- {t('ar1.tomorrow')}
            """)
        try:
            _cfg = {**_PLOTLY_CONFIG, 'toImageButtonOptions': {**_PLOTLY_CONFIG['toImageButtonOptions'], 'filename': f'{ticker}_AR1_history'}}
            fig_h1 = chart_price_history_plotly(r1, ticker, date_from, date_to, T=_T)
            st.plotly_chart(fig_h1, use_container_width=True, config=_cfg)
            fig_t1 = chart_test_result_plotly(r1, ticker, f'AR({ar_order})', m1, T=_T)
            st.plotly_chart(fig_t1, use_container_width=True, config={**_PLOTLY_CONFIG, 'toImageButtonOptions': {**_PLOTLY_CONFIG['toImageButtonOptions'], 'filename': f'{ticker}_AR1_forecast'}})
        except Exception as _e:
            st.error(t('error.ar1_chart', e=_e))

    with tab_mlr:
        _p_m = r2.get('p', 1)
        m_tr2 = calc_metrics(r2['ytr'], r2['ptr'], k=3 * _p_m)
        b0 = r2['intercept']
        _mlr_coef = r2['coef']
        b1 = float(_mlr_coef[0])
        b2 = float(_mlr_coef[_p_m])
        b3 = float(_mlr_coef[2 * _p_m])
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric(t('metric.mape_train'), f"{m_tr2['MAPE']:.2f}%")
        c2.metric(t('metric.mape_test'),  f"{m2['MAPE']:.2f}%")
        c3.metric("RMSE",                 f"{m2['RMSE']:.4f}")
        c4.metric("MAE",                  f"{m2['MAE']:.4f}")
        c5.metric("R²adj",                f"{m2['R2adj']:.4f}")
        st.markdown(
            f'<div class="info-box">'
            + t('analysis.train_range_info',
                d0=str(r2['dates_tr'][0]), d1=str(r2['dates_tr'][-1]), n=r2['nt'],
                t0=str(r2['dates_te'][0]), t1=str(r2['dates_te'][-1]), m=len(r2['yte']))
            + _next_lbl
            + f'</div>', unsafe_allow_html=True)
        with st.expander(t('analysis.equation_mlr')):
            _h_m = r2.get('h', 1)
            if _p_m == 1:
                _b2_exp   = int(f'{b2:.2e}'.split('e')[1]) if b2 != 0 else 0
                _b2_mant  = b2 / (10 ** _b2_exp) if b2 != 0 else 0
                _b2_latex = (f'{_b2_mant:.3f} \\times 10^{{{_b2_exp}}}'
                             if abs(b2) < 1e-3 or abs(b2) > 1e4 else f'{b2:.6f}')
                _mlr_eq = (
                    f'$$\\hat{{Y}}_{{t+{_h_m}}} = {b0:.4f}'
                    f' + {b1:.6f}\\cdot Y_{{t}}'
                    f' + {_b2_latex}\\cdot V_{{t}}'
                    f' + {b3:.4f}\\cdot (H_{{t}}-L_{{t}})$$'
                )
                _mlr_rows = [
                    f'| $\\hat{{\\beta}}_0$ | {b0:.4f} | {t("mlr.intercept")} |',
                    f'| $\\hat{{\\beta}}_{{Y,1}}$ ($Y_{{t}}$) | {b1:.6f} | {t("mlr.prev_price")} |',
                    f'| $\\hat{{\\beta}}_{{V,1}}$ ($V_{{t}}$) | ${_b2_latex}$ | {t("mlr.vol_pressure")} |',
                    f'| $\\hat{{\\beta}}_{{R,1}}$ ($(H-L)_{{t}}$) | {b3:.4f} | {t("mlr.range_vol")} |',
                ]
            else:
                _mlr_eq = (
                    f'$$\\hat{{Y}}_{{t+{_h_m}}} = \\hat{{\\beta}}_0'
                    f' + \\sum_{{j=1}}^{{{_p_m}}} \\hat{{\\beta}}_{{Y,j}}\\cdot Y_{{t-j+1}}'
                    f' + \\sum_{{j=1}}^{{{_p_m}}} \\hat{{\\beta}}_{{V,j}}\\cdot V_{{t-j+1}}'
                    f' + \\sum_{{j=1}}^{{{_p_m}}} \\hat{{\\beta}}_{{R,j}}\\cdot (H-L)_{{t-j+1}}$$'
                )
                _mlr_rows = [f'| $\\hat{{\\beta}}_0$ | {b0:.4f} | {t("mlr.intercept")} |']
                for _j in range(_p_m):
                    _lag_lbl = 't' if _j == 0 else f't-{_j}'
                    _cy = float(_mlr_coef[_j])
                    _cv = float(_mlr_coef[_p_m + _j])
                    _cr = float(_mlr_coef[2 * _p_m + _j])
                    _mlr_rows += [
                        f'| $\\hat{{\\beta}}_{{Y,{_j+1}}}$ ($Y_{{{_lag_lbl}}}$) | {_cy:.6f} | {t("mlr.prev_price")} lag {_j+1} |',
                        f'| $\\hat{{\\beta}}_{{V,{_j+1}}}$ ($V_{{{_lag_lbl}}}$) | {_cv:.4e} | {t("mlr.vol_pressure")} lag {_j+1} |',
                        f'| $\\hat{{\\beta}}_{{R,{_j+1}}}$ ($(H-L)_{{{_lag_lbl}}}$) | {_cr:.6f} | {t("mlr.range_vol")} lag {_j+1} |',
                    ]
            _mlr_table = '\n'.join(_mlr_rows)
            st.markdown(f"""
{t('mlr.model_header')} — MLR({_p_m}, h={_h_m})

{_mlr_eq}

| {t('mlr.coef')} | {t('ar1.value')} | {t('ar1.meaning')} |
|-------|---------|---------|
{_mlr_table}
            """)
        try:
            fig_h2 = chart_price_history_plotly(r2, ticker, date_from, date_to, T=_T)
            st.plotly_chart(fig_h2, use_container_width=True, config={**_PLOTLY_CONFIG, 'toImageButtonOptions': {**_PLOTLY_CONFIG['toImageButtonOptions'], 'filename': f'{ticker}_MLR_history'}})
            fig_t2 = chart_test_result_plotly(r2, ticker, 'MLR', m2, T=_T)
            st.plotly_chart(fig_t2, use_container_width=True, config={**_PLOTLY_CONFIG, 'toImageButtonOptions': {**_PLOTLY_CONFIG['toImageButtonOptions'], 'filename': f'{ticker}_MLR_forecast'}})
        except Exception as _e:
            st.error(t('error.mlr_chart', e=_e))

    with tab_cart:
        _p_c = r3.get('p', 1)
        m_tr3 = calc_metrics(r3['ytr'], r3['ptr'], k=6 * _p_c)
        best  = r3['best']; imp = r3['importances']
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric(t('metric.mape_train'), f"{m_tr3['MAPE']:.2f}%")
        c2.metric(t('metric.mape_test'),  f"{m3['MAPE']:.2f}%")
        c3.metric("RMSE",                 f"{m3['RMSE']:.4f}")
        c4.metric("MAE",                  f"{m3['MAE']:.4f}")
        c5.metric("R²adj",                f"{m3['R2adj']:.4f}")
        st.markdown(
            f'<div class="info-box">'
            + t('cart.hyper_info', d=best["max_depth"], l=best["min_samples_leaf"])
            + f' &nbsp;·&nbsp; {t("analysis.ret_pred_next")}: <b>{r3["ret_pred"]:+.4f}%</b>'
            + _next_lbl
            + f'</div>', unsafe_allow_html=True)

        with st.expander(t('analysis.config_cart'), expanded=True):
            _cx = _T['bg_card']; _cxe = _T['bg_elevated']
            _cf = _T['text_primary']; _cfs = _T['text_secondary']
            _cb = _T['border'];  _ca = _T['accent']
            st.markdown(f"""
<div style="background:{_cx};color:{_cf};padding:4px 2px;font-size:13px;line-height:1.7">
<div style="font-weight:800;font-size:14px;color:{_ca};margin-bottom:8px">
  Decision Tree Regressor (CART)
</div>
<div style="margin-bottom:6px">
  <span style="color:{_cfs};font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px">{t('cart.obj_header').replace('**','')}</span><br>
  <div style="color:{_cf};padding:3px 0 3px 8px;font-size:13px;font-style:italic">
    R<sub>t</sub> = (Y<sub>t</sub> − Y<sub>t-1</sub>) / Y<sub>t-1</sub> × 100
  </div>
</div>
<div style="margin-bottom:10px">
  <span style="color:{_cfs};font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px">{t('cart.price_recovery').replace('**','')}</span><br>
  <div style="color:{_cf};padding:3px 0 3px 8px;font-size:13px;font-style:italic">
    Ŷ<sub>t</sub> = Y<sub>t-1</sub> × (1 + R̂<sub>t</sub>/100)
  </div>
</div>
<div style="margin-bottom:8px;color:{_cfs};font-size:12px">
  {t('cart.optimize').replace('**','')} <b style="color:{_cf}">GridSearchCV + TimeSeriesSplit(5)</b>
</div>
<table style="width:100%;border-collapse:collapse;margin-bottom:8px;font-size:12px">
<thead><tr>
  <th style="background:{_cxe};color:{_cfs};padding:5px 10px;border:1px solid {_cb};text-align:left">{t('cart.hyper_col')}</th>
  <th style="background:{_cxe};color:{_cfs};padding:5px 10px;border:1px solid {_cb};text-align:center">{t('ar1.value')}</th>
</tr></thead>
<tbody>
  <tr><td style="background:{_cx};color:{_cf};padding:5px 10px;border:1px solid {_cb}">max_depth</td>
      <td style="background:{_cx};color:{_ca};padding:5px 10px;border:1px solid {_cb};text-align:center;font-weight:700">{best['max_depth']}</td></tr>
  <tr><td style="background:{_cxe};color:{_cf};padding:5px 10px;border:1px solid {_cb}">min_samples_leaf</td>
      <td style="background:{_cxe};color:{_ca};padding:5px 10px;border:1px solid {_cb};text-align:center;font-weight:700">{best['min_samples_leaf']}</td></tr>
</tbody></table>
<div style="color:{_cfs};font-size:11px">{t('cart.features_6').replace('**','')} (6 × p={_p_c} = <b style="color:{_ca}">{6*_p_c}</b> features total)<br>
  <span style="color:{_cf};font-weight:600">Return, Vol_ratio, Range, MA5_ratio, MA20_ratio, RSI14</span>
  {'<span style="color:'+_cfs+'"> × lags L1…L'+str(_p_c)+'</span>' if _p_c > 1 else ''}
</div>
</div>
""", unsafe_allow_html=True)

        try:
            fig_h3 = chart_price_history_plotly(r3, ticker, date_from, date_to, T=_T)
            st.plotly_chart(fig_h3, use_container_width=True, config={**_PLOTLY_CONFIG, 'toImageButtonOptions': {**_PLOTLY_CONFIG['toImageButtonOptions'], 'filename': f'{ticker}_CART_history'}})
            fig_t3 = chart_test_result_plotly(r3, ticker, 'CART', m3, T=_T, show_scatter=False)
            st.plotly_chart(fig_t3, use_container_width=True, config={**_PLOTLY_CONFIG, 'toImageButtonOptions': {**_PLOTLY_CONFIG['toImageButtonOptions'], 'filename': f'{ticker}_CART_forecast'}})
            st.markdown(
                f'<div class="sec-hdr" style="margin-top:18px">'
                + t('cart.feat_imp_title') + f' — {ticker}</div>',
                unsafe_allow_html=True)
            # _imp_lookup: keys trong imp dict (grouped by feature, không có _L1)
            # _imp_keys:   columns trong df (có _L1 suffix) để vẽ time series
            _imp_lookup = ['Return', 'Volume_ratio', 'Range_ratio',
                           'MA5_ratio', 'MA20_ratio', 'RSI14']
            _imp_keys   = ['Return_L1', 'Volume_ratio_L1', 'Range_ratio_L1',
                           'MA5_ratio_L1', 'MA20_ratio_L1', 'RSI14_L1']
            _imp_names  = ['Return(t-1)', 'Vol.ratio(t-1)', 'Range%(t-1)',
                           'MA5_ratio(t-1)', 'MA20_ratio(t-1)', 'RSI14(t-1)']
            _imp_arr    = np.array([imp.get(k, 0) for k in _imp_lookup])
            _imp_order = np.argsort(_imp_arr)
            _is_dk_fi  = _T.get('is_dark', False)
            _base_c    = '#60A5FA' if _is_dk_fi else '#3B82F6'
            _top_c     = '#F59E0B' if _is_dk_fi else '#F97316'
            _bar_c     = [_top_c if i == len(_imp_order) - 1 else _base_c
                          for i in range(len(_imp_order))]
            _fig_fi2 = go.Figure()
            _fig_fi2.add_trace(go.Bar(
                y=[_imp_names[i] for i in _imp_order],
                x=_imp_arr[_imp_order],
                orientation='h',
                marker=dict(color=_bar_c, line=dict(width=0)),
                text=[f'{v:.4f}' if v > 0 else '' for v in _imp_arr[_imp_order]],
                textposition='outside',
                textfont=dict(size=11, color=_T['text_primary']),
                hovertemplate='<b>%{y}</b><br>Importance: %{x:.4f}<extra></extra>',
            ))
            _fig_fi2.update_layout(
                title=dict(
                    text=f'<b>{t("cart.feat_imp_title")}</b> — {ticker}',
                    x=0.5, xanchor='center',
                    font=dict(size=13, color=_T['text_primary']),
                ),
                height=max(280, 80 + len(_imp_keys) * 48),
                paper_bgcolor=_T['bg_card'],
                plot_bgcolor=_T['bg_card'],
                font=dict(family='Inter', color=_T['text_primary']),
                xaxis=dict(
                    title=dict(text='Feature Importance',
                               font=dict(size=11, color=_T['text_secondary'])),
                    showgrid=True, gridcolor=_T.get('grid', '#E2E8F0'),
                    tickfont=dict(size=10, color=_T.get('text_muted', '#64748B')),
                    range=[0, float(_imp_arr.max()) * 1.35],
                    zeroline=False,
                ),
                yaxis=dict(tickfont=dict(size=12, color=_T['text_primary'])),
                margin=dict(l=20, r=80, t=70, b=40),
            )
            st.plotly_chart(_fig_fi2, use_container_width=True,
                config={**_PLOTLY_CONFIG, 'toImageButtonOptions': {
                    **_PLOTLY_CONFIG['toImageButtonOptions'],
                    'filename': f'{ticker}_CART_feature_importance',
                }})

            # Biểu đồ time series riêng cho từng đặc trưng có đóng góp (importance > 0)
            _contrib = [(df_k, name, imp.get(imp_k, 0))
                        for imp_k, df_k, name in zip(_imp_lookup, _imp_keys, _imp_names)
                        if imp.get(imp_k, 0) > 0]
            _contrib.sort(key=lambda x: x[2], reverse=True)
            if _contrib:
                _is_en_ana = st.session_state.get('lang', 'VI') == 'EN'
                _sec_title = (f'Minh họa đặc trưng đóng góp — {ticker}' if not _is_en_ana
                              else f'Feature contribution visualization — {ticker}')
                st.markdown(
                    f'<div class="sec-hdr" style="margin-top:20px">'
                    f'{_sec_title}</div>',
                    unsafe_allow_html=True)

                _W       = 40   # số phiên minh họa (lấy cuối cùng)
                _is_dk_c = _T.get('is_dark', False)
                _bg_c    = _T['bg_card']
                _fg_c    = _T['text_primary']
                _muted_c = _T.get('text_muted', '#64748B')
                _grid_c  = _T.get('grid', '#E2E8F0')
                _brd_c   = _T.get('border', '#E2E8F0')

                # Song ngữ: labels cho chart + legend + hover
                _L_imp       = 'Imp' if _is_en_ana else 'Imp'
                _L_session   = 'Session' if _is_en_ana else 'Phiên giao dịch'
                _L_session_s = 'Session' if _is_en_ana else 'Phiên'
                _L_thresh    = 'Avg threshold' if _is_en_ana else 'Ngưỡng TB'
                _L_active    = 'High (> 1.0)' if _is_en_ana else 'Sôi động (> 1,0)'
                _L_calm      = 'Low (< 1.0)' if _is_en_ana else 'Trầm lặng (< 1,0)'
                _L_vol_high  = 'High volatility' if _is_en_ana else 'Biến động cao'
                _L_stable    = 'Stable' if _is_en_ana else 'Ổn định'
                _L_close     = 'Close' if _is_en_ana else 'Giá đóng cửa'
                _L_close_r   = 'Close (relative)' if _is_en_ana else 'Giá đóng cửa (đơn vị tương đối)'
                _L_ma5_leg   = 'MA5 (5 sessions)' if _is_en_ana else 'MA5 (5 phiên)'
                _L_ma20_leg  = 'MA20 (20 sessions)' if _is_en_ana else 'MA20 (20 phiên)'
                _L_price_t   = 'Price (avg)' if _is_en_ana else 'Giá (tb)'
                _L_up        = 'Up (> 0)' if _is_en_ana else 'Tăng (> 0)'
                _L_down      = 'Down (< 0)' if _is_en_ana else 'Giảm (< 0)'
                _L_overbuy   = 'Overbought (70)' if _is_en_ana else 'Quá mua (70)'
                _L_oversell  = 'Oversold (30)' if _is_en_ana else 'Quá bán (30)'

                def _paper_chart(fk, fn, fv):
                    """Trả về Plotly Figure đúng kiểu bài báo cho từng loại đặc trưng."""
                    _df_w  = df.dropna(subset=[fk]).tail(_W).reset_index(drop=True)
                    _x     = list(range(1, len(_df_w) + 1))
                    _s     = _df_w[fk].values
                    _title = (f'<b>{fn}</b><br>'
                              f'<span style="font-size:10px;color:{_muted_c}">{_L_imp} = {fv:.4f}</span>')
                    _lay_base = dict(
                        height=320, paper_bgcolor=_bg_c, plot_bgcolor=_bg_c,
                        font=dict(family='Inter', size=10, color=_fg_c),
                        xaxis=dict(title=dict(text=_L_session,
                                              font=dict(size=10, color=_muted_c),
                                              standoff=8),
                                   showgrid=False, showline=True, linecolor=_brd_c,
                                   tickfont=dict(size=9, color=_muted_c),
                                   automargin=True),
                        margin=dict(l=60, r=20, t=95, b=95),
                        hovermode='x',
                    )

                    fig = go.Figure()

                    if fk == 'Volume_ratio_L1':
                        _clrs = ['#FB923C' if v > 1.0 else
                                 ('#475569' if _is_dk_c else '#94A3B8') for v in _s]
                        fig.add_trace(go.Bar(
                            x=_x, y=_s, marker_color=_clrs,
                            hovertemplate=f'{_L_session_s} %{{x}}<br>Vol.ratio: %{{y:.3f}}<extra></extra>',
                            showlegend=False,
                        ))
                        fig.add_hline(
                            y=1.0,
                            line=dict(color='#EF4444', width=1.5, dash='dash'),
                            annotation_text=f'{_L_thresh} = 1.0',
                            annotation_font=dict(size=9, color='#EF4444'),
                            annotation_position='top right',
                            annotation_xanchor='right',
                            annotation_yshift=10,
                        )
                        # Legend thủ công
                        for clr, lbl in [('#FB923C', _L_active),
                                         ('#94A3B8', _L_calm)]:
                            fig.add_trace(go.Bar(x=[None], y=[None],
                                                 marker_color=clr, name=lbl, showlegend=True))
                        _lay_base['yaxis'] = dict(
                            title=dict(text='Volume ratio Vᵢ / V̄⁽⁵⁾',
                                       font=dict(size=10, color=_muted_c)),
                            showgrid=True, gridcolor=_grid_c,
                            tickfont=dict(size=9, color=_muted_c))

                    elif fk == 'Range_ratio_L1':
                        _mean = float(np.nanmean(_s))
                        _clrs = ['#EF4444' if v > _mean else
                                 ('#818CF8' if _is_dk_c else '#A78BFA') for v in _s]
                        fig.add_trace(go.Bar(
                            x=_x, y=_s, marker_color=_clrs,
                            hovertemplate=f'{_L_session_s} %{{x}}<br>Range: %{{y:.2f}}%<extra></extra>',
                            showlegend=False,
                        ))
                        fig.add_hline(
                            y=_mean,
                            line=dict(color='#EF4444', width=1.5, dash='dash'),
                            annotation_text=f'{_L_thresh} ≈ {_mean:.1f}%',
                            annotation_font=dict(size=9, color='#EF4444'),
                            annotation_position='top right',
                            annotation_xanchor='right',
                            annotation_yshift=10,
                        )
                        for clr, lbl in [('#EF4444', _L_vol_high),
                                         ('#A78BFA', _L_stable)]:
                            fig.add_trace(go.Bar(x=[None], y=[None],
                                                 marker_color=clr, name=lbl, showlegend=True))
                        _lay_base['yaxis'] = dict(
                            title=dict(text='Range_ratio (%)',
                                       font=dict(size=10, color=_muted_c)),
                            showgrid=True, gridcolor=_grid_c,
                            tickfont=dict(size=9, color=_muted_c))

                    elif fk in ('MA5_ratio_L1', 'MA20_ratio_L1'):
                        _close = _df_w['Close'].values
                        _ma5   = _df_w['MA5'].values
                        _ma20  = _df_w['MA20'].values
                        _base  = _close[0] if _close[0] != 0 else 1
                        fig.add_trace(go.Scatter(
                            x=_x, y=_close / _base * 100, mode='lines',
                            name=_L_close,
                            line=dict(color='#64748B' if not _is_dk_c else '#94A3B8', width=1.4),
                            hovertemplate=f'{_L_session_s} %{{x}}<br>{_L_price_t}: %{{y:.1f}}<extra></extra>'))
                        fig.add_trace(go.Scatter(
                            x=_x, y=_ma5 / _base * 100, mode='lines',
                            name=_L_ma5_leg,
                            line=dict(color='#3B82F6', width=2.0),
                            hovertemplate=f'{_L_session_s} %{{x}}<br>MA5: %{{y:.1f}}<extra></extra>'))
                        fig.add_trace(go.Scatter(
                            x=_x, y=_ma20 / _base * 100, mode='lines',
                            name=_L_ma20_leg,
                            line=dict(color='#EF4444', width=1.8, dash='dash'),
                            hovertemplate=f'{_L_session_s} %{{x}}<br>MA20: %{{y:.1f}}<extra></extra>'))
                        _lay_base['yaxis'] = dict(
                            title=dict(text=_L_close_r,
                                       font=dict(size=10, color=_muted_c)),
                            showgrid=True, gridcolor=_grid_c,
                            tickfont=dict(size=9, color=_muted_c))
                        _lay_base['showlegend'] = True
                        _lay_base['legend'] = dict(
                            orientation='h', yanchor='top', y=-0.22,
                            xanchor='center', x=0.5,
                            font=dict(size=9, color=_fg_c), bgcolor='rgba(0,0,0,0)')

                    elif fk == 'Return_L1':
                        _clrs = ['#22C55E' if v > 0 else '#EF4444' for v in _s]
                        fig.add_trace(go.Bar(
                            x=_x, y=_s, marker_color=_clrs,
                            hovertemplate=f'{_L_session_s} %{{x}}<br>Return: %{{y:+.2f}}%<extra></extra>',
                            showlegend=False,
                        ))
                        fig.add_hline(y=0, line=dict(color=_muted_c, width=1, dash='dot'))
                        for clr, lbl in [('#22C55E', _L_up), ('#EF4444', _L_down)]:
                            fig.add_trace(go.Bar(x=[None], y=[None],
                                                 marker_color=clr, name=lbl, showlegend=True))
                        _lay_base['yaxis'] = dict(
                            title=dict(text='Return (%)',
                                       font=dict(size=10, color=_muted_c)),
                            showgrid=True, gridcolor=_grid_c,
                            tickfont=dict(size=9, color=_muted_c))

                    elif fk == 'RSI14_L1':
                        fig.add_trace(go.Scatter(
                            x=_x, y=_s, mode='lines', name='RSI14',
                            line=dict(color='#8B5CF6', width=1.6),
                            hovertemplate=f'{_L_session_s} %{{x}}<br>RSI14: %{{y:.1f}}<extra></extra>'))
                        fig.add_hline(y=70, line=dict(color='#EF4444', width=1.2, dash='dash'),
                                      annotation_text=_L_overbuy,
                                      annotation_font=dict(size=9, color='#EF4444'),
                                      annotation_position='top right')
                        fig.add_hline(y=30, line=dict(color='#3B82F6', width=1.2, dash='dash'),
                                      annotation_text=_L_oversell,
                                      annotation_font=dict(size=9, color='#3B82F6'),
                                      annotation_position='bottom right')
                        _lay_base['yaxis'] = dict(
                            title=dict(text='RSI14', font=dict(size=10, color=_muted_c)),
                            showgrid=True, gridcolor=_grid_c,
                            tickfont=dict(size=9, color=_muted_c),
                            range=[0, 100])
                    else:
                        fig.add_trace(go.Scatter(x=_x, y=_s, mode='lines', showlegend=False))
                        _lay_base['yaxis'] = dict(showgrid=True, gridcolor=_grid_c)

                    # Legend chung cho bar charts (đặt dưới)
                    if 'showlegend' not in _lay_base:
                        _lay_base['showlegend'] = True
                        _lay_base['legend'] = dict(
                            orientation='h', yanchor='top', y=-0.22,
                            xanchor='center', x=0.5,
                            font=dict(size=9, color=_fg_c), bgcolor='rgba(0,0,0,0)')

                    fig.update_layout(
                        title=dict(text=_title, x=0.5, xanchor='center',
                                   font=dict(size=12, color=_fg_c)),
                        **_lay_base,
                    )
                    return fig

                _ncols = min(len(_contrib), 3)
                _fcols = st.columns(_ncols)
                for _ci, (fk, fn, fv) in enumerate(_contrib):
                    if fk not in df.columns:
                        continue
                    with _fcols[_ci % _ncols]:
                        _fig_feat = _paper_chart(fk, fn, fv)
                        st.plotly_chart(_fig_feat, use_container_width=True,
                            config={**_PLOTLY_CONFIG,
                                    'displayModeBar': 'hover',
                                    'toImageButtonOptions': {
                                **_PLOTLY_CONFIG['toImageButtonOptions'],
                                'filename': f'{ticker}_{fk}',
                            }})

            st.markdown(
                f'<div class="sec-hdr" style="margin-top:24px">'
                + t('cart.tree_hdr', ticker=ticker) + '</div>',
                unsafe_allow_html=True)
            st.markdown(
                f'<div class="info-box" style="margin-bottom:12px">'
                + t('cart.tree_guide') +
                f'</div>', unsafe_allow_html=True)
            try:
                with st.spinner(t('load.tree')):
                    fig_tree = render_decision_tree_cart(ticker, train_ratio, T=_T, best_params=best)
                _max_d = best.get('max_depth', 3)
                _fig_h = max(620, (_max_d + 1) * 170 + 160)
                # Tăng margin trái/phải thật mạnh — đảm bảo annotation node rìa
                # không bao giờ bị clip, dù scale to container width bao nhiêu
                fig_tree.update_layout(
                    height=_fig_h,
                    autosize=True,
                    margin=dict(l=80, r=80, t=110, b=50),
                )
                st.plotly_chart(fig_tree, use_container_width=True,
                                config=_PLOTLY_CONFIG)
            except Exception as _et:
                st.warning(t('cart.tree_error', e=_et))

        except Exception as _e:
            st.error(t('error.cart_chart', e=_e))
