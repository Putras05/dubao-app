import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats as sp_stats
import streamlit as st

from core.themes import theme, set_mpl_theme
from core.constants import CLR, get_clr
from core.i18n import t
from charts.base import _plotly_axes_style, _plotly_layout_base


def chart_test_result(res: dict, ticker: str, method: str, m_te: dict, T: dict = None):
    if T is None: T = theme()
    set_mpl_theme(T)
    is_dark = T.get('is_dark', False)
    bg = T['bg_chart']
    CLR_NOW    = get_clr(T)
    col        = CLR_NOW[ticker]
    pred_col   = CLR_NOW['pred']
    fill_pos   = '#10B981' if is_dark else CLR[ticker]
    fill_neg   = CLR_NOW['pred']
    diag_col   = '#94A3B8' if is_dark else '#888888'
    scat_alpha = 0.45 if is_dark else 0.28

    td = pd.to_datetime(res['dates_te'])
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    for ax in (ax1, ax2):
        fig.patch.set_facecolor(bg); ax.set_facecolor(bg)

    ax1.plot(td, res['yte'], color=col, lw=1.6, label='Thực tế', zorder=3)
    ax1.plot(td, res['pte'], color=pred_col, lw=1.2, ls='--', alpha=.90,
             label=f'Dự báo  MAPE={m_te["MAPE"]:.2f}%', zorder=4)
    ax1.fill_between(td, res['yte'], res['pte'],
                     where=(res['yte'] >= res['pte']), color=fill_pos, alpha=.09, interpolate=True)
    ax1.fill_between(td, res['yte'], res['pte'],
                     where=(res['yte'] < res['pte']),  color=fill_neg, alpha=.09, interpolate=True)
    ax1.set_title(f'Kết quả dự báo — {method} · {ticker}\n'
                  f'{str(res["dates_te"][0])} → {str(res["dates_te"][-1])}',
                  fontsize=11, fontweight='bold', pad=14)
    ax1.set_ylabel('Giá đóng cửa (nghìn VNĐ)', fontsize=9)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%Y'))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=28, ha='right', fontsize=8)
    ax1.legend(fontsize=8.5)

    sl, ic, rv, *_ = sp_stats.linregress(res['yte'], res['pte'])
    xl = np.linspace(res['yte'].min(), res['yte'].max(), 300)
    ax2.scatter(res['yte'], res['pte'], color=col, alpha=scat_alpha, s=14, edgecolors='none', zorder=3)
    ax2.plot(xl, ic + sl * xl, color=pred_col, lw=2.0, zorder=5, label=f'OLS  R²={rv**2:.4f}')
    mn = min(res['yte'].min(), res['pte'].min()) * .975
    mx = max(res['yte'].max(), res['pte'].max()) * 1.025
    ax2.plot([mn, mx], [mn, mx], color=diag_col, lw=1.0, ls=':', alpha=.6, zorder=2, label='y = x (lý tưởng)')
    ax2.set_xlim(mn, mx); ax2.set_ylim(mn, mx)
    ax2.set_title(f'Thực tế vs Dự báo — MAPE={m_te["MAPE"]:.2f}%  R²={rv**2:.4f}',
                  fontsize=11, fontweight='bold', pad=14)
    ax2.set_xlabel('Thực tế (nghìn VNĐ)', fontsize=9)
    ax2.set_ylabel('Dự báo (nghìn VNĐ)', fontsize=9)
    ax2.legend(fontsize=8.5)
    plt.tight_layout(); return fig


def chart_test_result_plotly(res: dict, ticker: str, method: str,
                              m_te: dict, T: dict = None,
                              show_scatter: bool = True) -> go.Figure:
    if T is None: T = theme()
    is_dark = T.get('is_dark', False)

    td_raw = pd.to_datetime(res['dates_te'])
    td  = list(td_raw.to_pydatetime())
    yte = np.array(res['yte'], dtype=float)
    pte = np.array(res['pte'], dtype=float)

    actual_color  = '#F1F5F9' if is_dark else '#0F172A'
    pred_color    = '#F87171' if is_dark else '#EF4444'
    scatter_color = T['accent'] if is_dark else '#1565C0'
    ols_color     = '#F87171' if is_dark else '#EF4444'
    diag_color    = T['text_muted']

    residuals = yte - pte
    resid_std = float(np.std(residuals))
    upper = pte + 1.96 * resid_std
    lower = pte - 1.96 * resid_std

    sl, ic, rv, *_ = sp_stats.linregress(yte, pte)
    xl = np.linspace(yte.min(), yte.max(), 300)

    _is_cart = 'CART' in str(method).upper() or 'TREE' in str(method).upper()
    _is_mlr  = 'MLR' in str(method).upper()
    _is_ar1  = 'AR' in str(method).upper() and not _is_mlr

    # ── Annotation text ──────────────────────────────────────────────────────
    if _is_cart:
        _annot_text = (f'{t("chart.diagnostic")}<br>'
                       f'<b>R²</b> = {rv**2:.4f}<br>'
                       f'<b>MAPE</b> = {m_te["MAPE"]:.2f}%')
    elif _is_ar1:
        _c   = float(res.get('c', ic))
        _rho = float(res.get('rho', sl))
        _sign = '+' if _c >= 0 else '−'
        _annot_text = (f'<b>{t("chart.ar1_equation")}</b><br>'
                       f'Ŷₜ = {_rho:.4f}·Yₜ₋₁ {_sign} {abs(_c):.3f}<br>'
                       f'<b>R²</b> = {rv**2:.4f}  |  MAPE = {m_te["MAPE"]:.2f}%')
    elif _is_mlr:
        _b0  = float(res.get('intercept', ic))
        _b   = res.get('coef', [sl, 0, 0])
        _b1, _b2, _b3 = float(_b[0]), float(_b[1]), float(_b[2])
        def _fmt(v):
            return f'{v:.4f}' if abs(v) >= 0.0001 else f'{v:.3e}'
        _s0 = '+' if _b0 >= 0 else '−'
        _s2 = '+' if _b2 >= 0 else '−'
        _s3 = '+' if _b3 >= 0 else '−'
        _annot_text = (f'<b>{t("chart.mlr_equation")}</b><br>'
                       f'Ŷₜ = {_fmt(abs(_b1))}·Yₜ₋₁ {_s2} {_fmt(abs(_b2))}·Vₜ₋₁<br>'
                       f'&nbsp;&nbsp;&nbsp;&nbsp;{_s3} {_fmt(abs(_b3))}·HLₜ₋₁ {_s0} {_fmt(abs(_b0))}<br>'
                       f'<b>R²</b> = {rv**2:.4f}  |  MAPE = {m_te["MAPE"]:.2f}%')
    else:
        _annot_text = f'<b>R²</b> = {rv**2:.4f}  |  MAPE = {m_te["MAPE"]:.2f}%'

    # ── Chế độ không có scatter (chỉ một biểu đồ dự báo) ────────────────────
    if not show_scatter:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=td, y=yte, mode='lines', name=t('chart.actual_trace'),
            line=dict(color=actual_color, width=1.8),
            hovertemplate=f'<b>%{{x|%Y-%m-%d}}</b><br>{t("chart.hover_actual")}: %{{y:,.2f}}<extra></extra>',
        ))
        fig.add_trace(go.Scatter(
            x=td, y=pte, mode='lines',
            name=t('chart.forecast_trace', mape=f'{m_te["MAPE"]:.2f}'),
            line=dict(color=pred_color, width=1.4, dash='dot'),
            hovertemplate=f'<b>%{{x|%Y-%m-%d}}</b><br>{t("chart.hover_forecast")}: %{{y:,.2f}}<extra></extra>',
        ))
        fig.add_trace(go.Scatter(
            x=td, y=upper, mode='lines', line=dict(width=0),
            showlegend=False, hoverinfo='skip',
        ))
        fig.add_trace(go.Scatter(
            x=td, y=lower, mode='lines', line=dict(width=0),
            fill='tonexty', fillcolor='rgba(248,113,113,0.08)',
            name='95% CI', hoverinfo='skip',
        ))
        fig.add_annotation(
            xref='paper', yref='paper',
            x=0.01, y=0.97, xanchor='left', yanchor='top',
            text=_annot_text, showarrow=False,
            font=dict(size=10, color=T['text_secondary']),
            bgcolor=T['bg_elevated'], bordercolor=T['border'],
            borderwidth=1, borderpad=6, align='left',
        )
        fig.update_layout(
            title=dict(
                text=t('chart.forecast_title', ticker=ticker, method=method),
                x=0.5, xanchor='center',
                font=dict(size=13, color=T['text_primary']),
            ),
            height=440,
            margin=dict(l=55, r=30, t=70, b=70),
            paper_bgcolor=T['bg_card'],
            plot_bgcolor=T['bg_card'],
            font=dict(family='Inter, system-ui, sans-serif', size=11, color=T['text_primary']),
            hovermode='x unified',
            hoverlabel=dict(bgcolor=T['bg_elevated'], bordercolor=T['border'],
                            font_size=12, font_color=T['text_primary']),
            legend=dict(
                orientation='h', yanchor='bottom', y=-0.18,
                xanchor='center', x=0.5,
                bgcolor='rgba(0,0,0,0)',
                font=dict(size=11, color=T['text_primary']),
            ),
        )
        _plotly_axes_style(fig, T)
        fig.update_xaxes(tickformat='%m/%Y')
        fig.update_yaxes(
            title=dict(text=t('chart.price_axis'),
                       font=dict(size=11, color=T['text_secondary']), standoff=10),
        )
        return fig

    # ── Chế độ đầy đủ: dự báo + scatter ─────────────────────────────────────
    _subtitle_r = t('chart.actual_vs_pred_diag') if _is_cart else t('chart.actual_vs_pred')
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=(
            t('chart.forecast_title', ticker=ticker, method=method),
            _subtitle_r,
        ),
        column_widths=[0.62, 0.38],
        horizontal_spacing=0.10,
    )

    fig.add_trace(go.Scatter(
        x=td, y=yte, mode='lines', name=t('chart.actual_trace'),
        line=dict(color=actual_color, width=1.8),
        hovertemplate=f'<b>%{{x|%Y-%m-%d}}</b><br>{t("chart.hover_actual")}: %{{y:,.2f}}<extra></extra>',
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=td, y=pte, mode='lines',
        name=t('chart.forecast_trace', mape=f'{m_te["MAPE"]:.2f}'),
        line=dict(color=pred_color, width=1.4, dash='dot'),
        hovertemplate=f'<b>%{{x|%Y-%m-%d}}</b><br>{t("chart.hover_forecast")}: %{{y:,.2f}}<extra></extra>',
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=td, y=upper, mode='lines', line=dict(width=0),
        showlegend=False, hoverinfo='skip',
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=td, y=lower, mode='lines', line=dict(width=0),
        fill='tonexty', fillcolor='rgba(248,113,113,0.08)',
        name='95% CI', hoverinfo='skip',
    ), row=1, col=1)

    # Vertical line at last test date to mark the forecast cutoff
    _h_chart = res.get('h', 1)
    if len(res.get('dates_te', [])) > 0:
        _last_test_date = res['dates_te'][-1]
        _y_vals = list(res.get('yte', [])) + list(res.get('pte', []))
        if _y_vals:
            _y_min = float(min(_y_vals)) * 0.95
            _y_max = float(max(_y_vals)) * 1.05
        else:
            _y_min, _y_max = 0, 1
        fig.add_shape(
            type='line',
            xref='x', yref='y',
            x0=_last_test_date, x1=_last_test_date,
            y0=_y_min, y1=_y_max,
            line=dict(color=T.get('accent', '#1565C0'), width=1.5, dash='dash'),
            opacity=0.6,
            row=1, col=1,
        )
        fig.add_annotation(
            x=_last_test_date, y=_y_max,
            text=f'h+{_h_chart}' if _h_chart > 1 else 'NOW',
            showarrow=False,
            font=dict(size=9, color=T.get('accent', '#1565C0'), family='monospace'),
            xanchor='right', yanchor='top',
            bgcolor=T.get('bg_card', '#FFFFFF'),
            bordercolor=T.get('border', '#E2E8F0'),
            borderpad=2,
            row=1, col=1,
        )

    mn = min(yte.min(), pte.min()) * 0.978
    mx = max(yte.max(), pte.max()) * 1.022
    fig.add_trace(go.Scatter(
        x=[mn, mx], y=[mn, mx], mode='lines',
        line=dict(color=diag_color, width=1, dash='dot'),
        name=t('chart.ideal_line'),
        legend='legend2', showlegend=True, hoverinfo='skip',
    ), row=1, col=2)
    fig.add_trace(go.Scatter(
        x=yte, y=pte, mode='markers',
        marker=dict(color=scatter_color, size=5, opacity=0.45, line=dict(width=0)),
        name=t('chart.scatter_points'),
        legend='legend2', showlegend=True,
        hovertemplate=f'{t("chart.hover_actual")}: %{{x:,.2f}}<br>'
                      f'{t("chart.hover_forecast")}: %{{y:,.2f}}<extra></extra>',
    ), row=1, col=2)
    fig.add_trace(go.Scatter(
        x=xl, y=ic + sl * xl, mode='lines',
        line=dict(color=ols_color, width=2),
        name=f'{t("chart.ols_fit")} (R²={rv**2:.4f})',
        legend='legend2', showlegend=True, hoverinfo='skip',
    ), row=1, col=2)

    fig.add_annotation(
        xref='x2 domain', yref='y2 domain',
        x=0.04, y=0.96, xanchor='left', yanchor='top',
        text=_annot_text, showarrow=False,
        font=dict(size=10, color=T['text_secondary']),
        bgcolor=T['bg_elevated'], bordercolor=T['border'],
        borderwidth=1, borderpad=6, align='left',
    )

    fig.update_layout(
        height=560,
        margin=dict(l=55, r=30, t=80, b=100),
        paper_bgcolor=T['bg_card'],
        plot_bgcolor=T['bg_card'],
        font=dict(family='Inter, system-ui, sans-serif', size=11, color=T['text_primary']),
        hovermode='x unified',
        hoverlabel=dict(bgcolor=T['bg_elevated'], bordercolor=T['border'],
                        font_size=12, font_color=T['text_primary']),
        legend=dict(
            orientation='h',
            yanchor='top', y=-0.14,
            xanchor='center', x=0.25,
            bgcolor=T.get('bg_elevated', 'rgba(0,0,0,0)'),
            bordercolor=T['border'], borderwidth=1,
            font=dict(size=10, color=T['text_primary']),
            itemsizing='constant',
        ),
        legend2=dict(
            orientation='h',
            yanchor='top', y=-0.14,
            xanchor='center', x=0.80,
            bgcolor=T.get('bg_elevated', 'rgba(0,0,0,0)'),
            bordercolor=T['border'], borderwidth=1,
            font=dict(size=10, color=T['text_primary']),
            itemsizing='constant',
        ),
    )
    fig.update_annotations(font=dict(size=12, color=T['text_primary']))
    _plotly_axes_style(fig, T)
    fig.update_xaxes(tickformat='%m/%Y', row=1, col=1)
    fig.update_yaxes(
        title=dict(text=t('chart.price_axis'), font=dict(size=11, color=T['text_secondary']), standoff=10),
        row=1, col=1,
    )
    fig.update_xaxes(
        title=dict(text=t('chart.actual_axis'), font=dict(size=11, color=T['text_secondary']), standoff=10),
        tickformat=',.1f', row=1, col=2,
    )
    fig.update_yaxes(
        title=dict(text=t('chart.forecast_axis'), font=dict(size=11, color=T['text_secondary']), standoff=10),
        tickformat=',.1f', range=[mn, mx], row=1, col=2,
    )
    fig.update_xaxes(range=[mn, mx], row=1, col=2)
    return fig

def chart_price_candlestick(df: pd.DataFrame, ticker: str, T: dict) -> go.Figure:
    """Candlestick chart kiểu TradingView — pan/zoom 5 năm gần nhất.

    Giới hạn 5 năm để Plotly render mượt (1260 nến vs 3500+). Default zoom
    1 tháng cuối → mỗi nến ~60px. Có rangeselector + rangeslider để pan/zoom.
    """
    is_dark = T.get('is_dark', False)
    lang = st.session_state.get('lang', 'VI')

    # Giới hạn 5 năm gần nhất → app mượt hơn nhiều (rangeslider không phải
    # render 3500+ nến trong mini view).
    if len(df) > 0:
        _last_date = pd.to_datetime(df['Ngay'].iloc[-1])
        _cutoff = _last_date - pd.Timedelta(days=5 * 365)
        df = df[pd.to_datetime(df['Ngay']) >= _cutoff].reset_index(drop=True)

    dates = pd.to_datetime(df['Ngay'])

    inc_color = '#10B981'
    dec_color = '#EF4444'
    label_all = 'Tất cả' if lang == 'VI' else 'All'

    fig = go.Figure(data=[go.Candlestick(
        x=dates,
        open=df['Open'].values,
        high=df['High'].values,
        low=df['Low'].values,
        close=df['Close'].values,
        increasing=dict(
            line=dict(color=inc_color, width=1),
            fillcolor=inc_color,
        ),
        decreasing=dict(
            line=dict(color=dec_color, width=1),
            fillcolor=dec_color,
        ),
        name=ticker,
        showlegend=False,
    )])

    # Default zoom = 1 tháng cuối → nến to ~60px, rõ ràng
    if len(dates) > 0:
        _last = dates.iloc[-1]
        _start_default = _last - pd.Timedelta(days=30)
        _xaxis_range = [_start_default, _last + pd.Timedelta(days=2)]
    else:
        _xaxis_range = None

    fig.update_layout(
        height=520,
        margin=dict(l=50, r=30, t=50, b=30),
        paper_bgcolor=T['bg_chart'],
        plot_bgcolor=T['bg_chart'],
        font=dict(family='Inter, system-ui, sans-serif', size=11, color=T['text_primary']),
        showlegend=False,
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor=T['bg_card'], bordercolor=T['border'],
            font_size=12, font_color=T['text_primary'],
        ),
        uirevision=f'candlestick_{ticker}',
        xaxis=dict(
            range=_xaxis_range,
            type='date',
            showgrid=False, zeroline=False,
            showline=True, linecolor=T['border'], linewidth=1,
            ticks='outside', tickcolor=T['border'], ticklen=4,
            tickformat='%d/%m/%Y',
            tickfont=dict(size=10, color=T['text_muted']),
            showspikes=True, spikecolor=T['accent'], spikemode='across',
            spikesnap='cursor', spikedash='dot', spikethickness=1,
            rangeselector=dict(
                buttons=[
                    dict(count=1, label='1M', step='month', stepmode='backward'),
                    dict(count=3, label='3M', step='month', stepmode='backward'),
                    dict(count=6, label='6M', step='month', stepmode='backward'),
                    dict(count=1, label='1N', step='year',  stepmode='backward'),
                    dict(step='all', label=label_all),
                ],
                bgcolor=T['bg_card'],
                activecolor=T['accent'],
                bordercolor=T['border'],
                borderwidth=1,
                font=dict(color=T['text_primary'], size=11),
                x=0, y=1.10, yanchor='bottom',
            ),
            rangeslider=dict(
                visible=True,
                bgcolor=T['bg_card'],
                bordercolor=T['border'],
                borderwidth=1,
                thickness=0.04,
            ),
            rangebreaks=[dict(bounds=['sat', 'mon'])],
        ),
        yaxis=dict(
            showgrid=True, gridcolor=T['grid'], gridwidth=1,
            zeroline=False, showline=False, ticks='',
            tickformat=',.1f',
            tickfont=dict(size=10, color=T['text_muted']),
            title=None,
            showspikes=True, spikecolor=T['accent'], spikemode='across',
            spikesnap='cursor', spikedash='dot', spikethickness=1,
        ),
    )
    return fig
