import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import plotly.graph_objects as go
from scipy.stats import norm as sp_norm

from core.themes import theme, set_mpl_theme
from core.constants import TICKERS, get_clr
from core.i18n import t
from charts.base import _plotly_layout_base


def chart_portfolio_compare_plotly(all_data: dict, train_ratio: float, T=None):
    """Hiệu suất chuẩn hóa 3 cổ phiếu — Plotly interactive."""
    if T is None:
        T = theme()

    is_dark = T.get('is_dark', False)
    colors = (
        {'FPT': '#60A5FA', 'HPG': '#C084FC', 'VNM': '#86EFAC'}
        if is_dark else
        {'FPT': '#1565C0', 'HPG': '#6A1B9A', 'VNM': '#2E7D32'}
    )

    fig = go.Figure()

    for tk in TICKERS:
        df_tk   = all_data[tk]
        dt_tk   = pd.to_datetime(df_tk['Ngay'])
        cl_tk   = df_tk['Close'].values
        norm_tk = cl_tk / cl_tk[0] * 100
        fig.add_trace(go.Scatter(
            x=dt_tk, y=norm_tk, mode='lines',
            name=f'{tk} ({cl_tk[-1]*1000:,.0f} đ → {norm_tk[-1]:.1f})',
            line=dict(color=colors[tk], width=2),
            hovertemplate=f'<b>{tk}</b><br>%{{x|%Y-%m-%d}}<br>Norm: %{{y:.1f}}<extra></extra>',
        ))

    nt_ref    = int(len(all_data['FPT']) * train_ratio)
    split_dt  = pd.to_datetime(all_data['FPT']['Ngay'].values[nt_ref])
    split_str = pd.Timestamp(split_dt).strftime('%Y-%m-%d')
    fig.add_vline(x=split_str, line=dict(color=T['text_muted'], width=1.5, dash='dash'))
    fig.add_annotation(
        x=split_str, y=1.04, yref='paper',
        text=t('chart.train_test_label'), showarrow=False,
        font=dict(size=10, color=T['text_secondary']),
        bgcolor=T['bg_card'], borderpad=3,
    )

    fig.add_hline(y=100, line=dict(color=T['text_muted'], width=0.8, dash='dot'))

    fig.update_layout(
        title=dict(
            text=t('chart.portfolio_title'),
            x=0.5, xanchor='center',
            font=dict(size=13, color=T['text_primary']),
        ),
        height=520,
        margin=dict(l=60, r=40, t=80, b=70),
        paper_bgcolor=T['bg_card'],
        plot_bgcolor=T['bg_card'],
        font=dict(family='Inter', size=11, color=T['text_primary']),
        hovermode='x unified',
        hoverlabel=dict(bgcolor=T['bg_elevated'], bordercolor=T['border'],
                        font_size=12, font_color=T['text_primary']),
        legend=dict(
            orientation='h', yanchor='top', y=-0.13,
            xanchor='center', x=0.5,
            bgcolor=T['bg_elevated'], bordercolor=T['border'], borderwidth=1,
            font=dict(size=11, color=T['text_primary']),
            itemsizing='constant',
        ),
        xaxis=dict(
            showgrid=False, showline=True, linecolor=T['border'],
            tickfont=dict(size=10, color=T['text_muted']),
            rangeselector=dict(
                buttons=[
                    dict(count=1, label='1Y', step='year', stepmode='backward'),
                    dict(count=3, label='3Y', step='year', stepmode='backward'),
                    dict(count=5, label='5Y', step='year', stepmode='backward'),
                    dict(step='all', label='All'),
                ],
                bgcolor=T['bg_card'], activecolor=T['accent'],
                bordercolor=T['border'], borderwidth=1,
                font=dict(color=T['text_primary'], size=10),
                x=0, y=1.08, yanchor='bottom',
            ),
        ),
        yaxis=dict(
            showgrid=True, gridcolor=T['grid'],
            tickformat=',.0f',
            tickfont=dict(size=10, color=T['text_muted']),
            title=dict(text=t('chart.normalized_base'),
                       font=dict(size=11, color=T['text_secondary'])),
        ),
    )

    return fig


def chart_correlation_plotly(corr, T=None):
    """Correlation heatmap — Plotly, high-contrast per-cell text via annotations."""
    if T is None:
        T = theme()

    is_dark = T.get('is_dark', False)
    z = corr.values

    colorscale = (
        [
            [0.0,  '#1E293B'], [0.3,  '#1E40AF'],
            [0.55, '#2563EB'], [0.75, '#3B82F6'],
            [0.9,  '#60A5FA'], [1.0,  '#93C5FD'],
        ]
        if is_dark else
        [
            [0.0,  '#EFF6FF'], [0.3,  '#BFDBFE'],
            [0.5,  '#60A5FA'], [0.7,  '#2563EB'],
            [0.85, '#1D4ED8'], [1.0,  '#1E3A8A'],
        ]
    )

    fig = go.Figure(data=go.Heatmap(
        z=z, x=list(corr.columns), y=list(corr.index),
        colorscale=colorscale, zmin=0.0, zmax=1.0,
        hovertemplate='<b>%{y} ↔ %{x}</b><br>r = %{z:.4f}<extra></extra>',
        xgap=3, ygap=3,
        colorbar=dict(
            title=dict(text='r', font=dict(color=T['text_secondary'], size=12)),
            tickfont=dict(color=T['text_muted'], size=10),
            outlinecolor=T['border'], outlinewidth=1,
            thickness=18, len=0.75,
            tickvals=[0, 0.25, 0.5, 0.75, 1.0],
        ),
    ))

    for i, row_name in enumerate(corr.index):
        for j, col_name in enumerate(corr.columns):
            v = float(z[i, j])
            txt_color = '#FFFFFF' if v > 0.55 else '#0F172A'
            fig.add_annotation(
                x=col_name, y=row_name,
                text=f'<b>{v:.3f}</b>',
                showarrow=False,
                font=dict(size=18, family='Inter', color=txt_color),
            )

    fig.update_layout(
        title=dict(
            text=t('chart.return_corr'),
            x=0.5, xanchor='center',
            font=dict(size=14, color=T['text_primary']),
        ),
        height=480,
        margin=dict(l=70, r=50, t=70, b=60),
        paper_bgcolor=T['bg_card'],
        plot_bgcolor=T['bg_card'],
        font=dict(family='Inter', color=T['text_primary']),
        xaxis=dict(side='bottom', tickfont=dict(size=14, color=T['text_primary'])),
        yaxis=dict(autorange='reversed', tickfont=dict(size=14, color=T['text_primary'])),
    )

    return fig


def chart_portfolio_compare(all_data: dict, train_ratio: float, T: dict = None):
    if T is None: T = theme()
    set_mpl_theme(T)
    is_dark = T.get('is_dark', False)
    bg = T['bg_chart']
    CLR_NOW   = get_clr(T)
    split_col = '#94A3B8' if is_dark else '#888888'

    fig, ax = plt.subplots(figsize=(14, 5))
    fig.patch.set_facecolor(bg); ax.set_facecolor(bg)
    for tk in TICKERS:
        df = all_data[tk]
        dt   = pd.to_datetime(df['Ngay'])
        cl   = df['Close'].values
        norm = cl / cl[0] * 100
        ax.plot(dt, norm, color=CLR_NOW[tk], lw=1.8,
                label=f'{tk}  (hiện tại: {cl[-1]*1000:,.0f} đ  →  {norm[-1]:.1f})')
    nt_ref   = int(len(all_data['FPT']) * train_ratio)
    split_dt = pd.to_datetime(all_data['FPT']['Ngay'].values[nt_ref])
    ax.axvline(split_dt, color=split_col, lw=1.3, ls='--', alpha=.6, label='Ranh giới Train/Test')
    ax.axhline(100, color=T['text_muted'], lw=0.8, ls=':', alpha=.45)
    ax.set_ylabel('Hiệu suất chuẩn hóa (Base = 100)', fontsize=9)
    ax.set_title('So sánh hiệu suất — FPT · HPG · VNM  (Chuẩn hóa về 100)', fontsize=11, fontweight='bold', pad=10)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.14), ncol=4,
              facecolor=T['bg_card'], edgecolor=T['border'],
              labelcolor=T['text_primary'], fontsize=9)
    ax.grid(True, alpha=.10, ls='--')
    for sp in ['top', 'right']: ax.spines[sp].set_visible(False)
    plt.tight_layout(rect=[0, 0, 1, 0.96]); return fig


def chart_returns_hist(df: pd.DataFrame, ticker: str, T: dict = None) -> go.Figure:
    """Histogram phân phối Return — Plotly, có toolbar đầy đủ."""
    if T is None: T = theme()
    CLR_NOW  = get_clr(T)
    col      = CLR_NOW[ticker]
    ret      = df['Return'].dropna()
    mu, sigma = float(ret.mean()), float(ret.std())
    x_norm   = np.linspace(float(ret.min()), float(ret.max()), 300)
    y_norm   = sp_norm.pdf(x_norm, mu, sigma)

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=ret, nbinsx=80, histnorm='probability density',
        marker=dict(color=col, opacity=0.65, line=dict(width=0)),
        hovertemplate='Return: %{x:.2f}%<br>Density: %{y:.4f}<extra></extra>',
        showlegend=True,
        name=f'{t("chart.daily_return_label")} (μ={mu:.3f}, σ={sigma:.3f})',
    ))
    fig.add_trace(go.Scatter(
        x=x_norm, y=y_norm, mode='lines',
        line=dict(color='#EF4444', width=2.2),
        name=t('chart.normal_label', mu=f'{mu:.3f}', sigma=f'{sigma:.3f}'),
        hovertemplate='x=%{x:.2f}<br>pdf=%{y:.4f}<extra></extra>',
    ))
    fig.add_vline(x=0,       line=dict(color=T['text_muted'], width=1.1, dash='dash'))
    fig.add_vline(x=float(mu), line=dict(color=col, width=1.2, dash='dot'))

    lay = _plotly_layout_base(T, height=400)
    lay.update(dict(
        title=dict(
            text=f'<b>{ticker}</b>  —  {t("chart.ret_hist_title")}',
            x=0.5, xanchor='center',
            font=dict(size=13, color=T['text_primary']),
        ),
        bargap=0.02,
        xaxis=dict(
            title=dict(text=t('chart.ret_axis'), font=dict(size=11, color=T['text_secondary'])),
            showgrid=False, showline=True, linecolor=T['border'],
            tickfont=dict(size=10, color=T['text_muted']), zeroline=False,
        ),
        yaxis=dict(
            title=dict(text=t('chart.density_axis'), font=dict(size=11, color=T['text_secondary'])),
            showgrid=True, gridcolor=T['grid'],
            tickfont=dict(size=10, color=T['text_muted']), zeroline=False,
        ),
        legend=dict(
            orientation='h', yanchor='top', y=-0.25,
            xanchor='center', x=0.5,
            bgcolor=T['bg_elevated'], bordercolor=T['border'], borderwidth=1,
            font=dict(size=10, color=T['text_primary']),
            itemsizing='constant',
        ),
        margin=dict(l=60, r=30, t=75, b=100),
        hovermode='x',
    ))
    fig.update_layout(lay)
    return fig
