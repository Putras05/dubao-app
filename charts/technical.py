import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from core.themes import theme, set_mpl_theme
from core.constants import CLR, get_clr
from core.i18n import t


def chart_technical(df: pd.DataFrame, ticker: str, T: dict = None):
    if T is None: T = theme()
    set_mpl_theme(T)
    is_dark = T.get('is_dark', False)
    bg      = T['bg_chart']
    CLR_NOW = get_clr(T)
    col     = CLR_NOW[ticker]
    pred_col = CLR_NOW['pred']
    ma5_col    = '#26C6A5' if is_dark else '#00897B'
    ma20_col   = '#FFB74D' if is_dark else '#F57C00'
    rsi_col    = '#CE93D8' if is_dark else '#6A1B9A'
    hline_col  = '#64748B' if is_dark else '#888888'
    zero_col   = '#94A3B8' if is_dark else '#333333'

    fig, axes = plt.subplots(4, 1, figsize=(14, 11), sharex=True,
                             gridspec_kw={'height_ratios': [3, 1.5, 1.5, 1.5]})
    fig.patch.set_facecolor(bg)
    dt = pd.to_datetime(df['Ngay'])

    ax0 = axes[0]; ax0.set_facecolor(bg)
    ax0.fill_between(dt, df['Close'], alpha=.10, color=col)
    ax0.plot(dt, df['Close'], color=col,     lw=1.4, label='Close', zorder=4)
    ax0.plot(dt, df['MA5'],   color=ma5_col, lw=1.0, ls='--', alpha=.85, label='MA5')
    ax0.plot(dt, df['MA20'],  color=ma20_col, lw=1.1, ls='--', alpha=.85, label='MA20')
    ax0.set_ylabel('Giá (nghìn VNĐ)', fontsize=9)
    ax0.set_title(f'{ticker}  —  Chỉ số kỹ thuật & Đặc trưng CART', fontsize=12, fontweight='bold', pad=10)
    ax0.legend(fontsize=8.5, loc='upper left', ncol=3)

    ax1 = axes[1]; ax1.set_facecolor(bg)
    vr = df['Volume_ratio'].fillna(1)
    ax1.bar(dt, vr, color=col, alpha=.40, width=2)
    ax1.axhline(1.0, color=hline_col, lw=1.2, ls='--', alpha=.65)
    ax1.axhline(2.0, color=pred_col, lw=1.0, ls=':', alpha=.55)
    ax1.set_ylabel('Vol/MA5', fontsize=9)

    ax2 = axes[2]; ax2.set_facecolor(bg)
    ax2.fill_between(dt, df['RSI14'], 70, where=(df['RSI14'] >= 70),
                     color=pred_col, alpha=.20, interpolate=True)
    ax2.fill_between(dt, df['RSI14'], 30, where=(df['RSI14'] <= 30),
                     color='#42A5F5' if is_dark else '#1565C0', alpha=.20, interpolate=True)
    ax2.plot(dt, df['RSI14'], color=rsi_col, lw=1.2)
    ax2.axhline(70, color=pred_col,  lw=1.1, ls='--', alpha=.65, label='70')
    ax2.axhline(30, color='#42A5F5' if is_dark else '#1565C0', lw=1.1, ls='--', alpha=.65, label='30')
    ax2.axhline(50, color=hline_col, lw=0.8, ls=':', alpha=.45)
    ax2.set_ylim(0, 100); ax2.set_ylabel('RSI14', fontsize=9)
    ax2.legend(fontsize=8, loc='upper left', ncol=2)

    ax3 = axes[3]; ax3.set_facecolor(bg)
    ret = df['Return'].fillna(0)
    ax3.bar(dt, ret, color=[col if r >= 0 else pred_col for r in ret], alpha=.55, width=2)
    ax3.axhline(0, color=zero_col, lw=1.0, alpha=.6)
    ax3.set_ylabel('Return (%)', fontsize=9)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax3.xaxis.set_major_locator(mdates.YearLocator(2))

    for ax in axes:
        for sp in ['top', 'right']: ax.spines[sp].set_visible(False)
    plt.tight_layout(h_pad=0.5); return fig


def chart_technical_plotly(df, ticker: str, T=None):
    """Chart 4-panel kỹ thuật & đặc trưng CART — Plotly interactive."""
    if T is None:
        T = theme()

    is_dark   = T.get('is_dark', False)
    CLR_NOW   = get_clr(T)
    col_close = CLR_NOW[ticker]
    col_pred  = CLR_NOW['pred']
    col_ma5   = '#26C6A5' if is_dark else '#00897B'
    col_ma20  = '#FFB74D' if is_dark else '#F57C00'
    col_rsi   = '#CE93D8' if is_dark else '#6A1B9A'
    col_ob    = '#F87171' if is_dark else '#EF4444'
    col_os    = '#60A5FA' if is_dark else '#1565C0'
    col_up    = '#10B981'
    col_down  = col_pred

    dt = pd.to_datetime(df['Ngay'])

    r_c = int(col_close[1:3], 16)
    g_c = int(col_close[3:5], 16)
    b_c = int(col_close[5:7], 16)
    fill_close = f'rgba({r_c},{g_c},{b_c},0.10)'

    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        row_heights=[0.38, 0.22, 0.22, 0.18],
        vertical_spacing=0.07,
        subplot_titles=(
            f'<b>{ticker}</b> — Giá đóng cửa · MA5 · MA20',
            '<b>Volume / MA5</b> — Khối lượng chuẩn hóa (>2× = bất thường)',
            '<b>RSI 14</b> — Chỉ số sức mạnh tương đối  (>70 quá mua · <30 quá bán)',
            '<b>Return (%)</b> — Phần trăm thay đổi giá hàng ngày',
        ),
    )

    fig.add_trace(go.Scatter(
        x=dt, y=df['Close'], mode='lines', name='Close',
        line=dict(color=col_close, width=2.2),
        fill='tozeroy', fillcolor=fill_close,
        hovertemplate='<b>%{x|%Y-%m-%d}</b><br>Close: %{y:,.2f}<extra></extra>',
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=dt, y=df['MA5'], mode='lines', name='MA5',
        line=dict(color=col_ma5, width=1.5, dash='dash'),
        hovertemplate='MA5: %{y:,.2f}<extra></extra>',
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=dt, y=df['MA20'], mode='lines', name='MA20',
        line=dict(color=col_ma20, width=1.5, dash='dot'),
        hovertemplate='MA20: %{y:,.2f}<extra></extra>',
    ), row=1, col=1)

    vr = df['Volume_ratio'].fillna(1).values
    vr_colors = [col_ob if v > 2.0 else (col_up if v > 1.0 else T['text_muted'])
                 for v in vr]
    fig.add_trace(go.Bar(
        x=dt, y=vr, name='Vol/MA5',
        marker=dict(color=vr_colors, opacity=0.65),
        showlegend=False,
        hovertemplate='<b>%{x|%Y-%m-%d}</b><br>Vol/MA5: %{y:.2f}×<extra></extra>',
    ), row=2, col=1)
    fig.add_hline(y=1.0, line=dict(color=T['text_muted'], width=1,   dash='dash'), row=2, col=1)
    fig.add_hline(y=2.0, line=dict(color=col_pred,        width=1,   dash='dot'),  row=2, col=1)

    fig.add_hrect(y0=70, y1=100, fillcolor=col_ob, opacity=0.08, line_width=0, row=3, col=1)
    fig.add_hrect(y0=0,  y1=30,  fillcolor=col_os, opacity=0.08, line_width=0, row=3, col=1)
    fig.add_trace(go.Scatter(
        x=dt, y=df['RSI14'], mode='lines', name='RSI14',
        line=dict(color=col_rsi, width=1.8),
        showlegend=False,
        hovertemplate='<b>%{x|%Y-%m-%d}</b><br>RSI: %{y:.1f}<extra></extra>',
    ), row=3, col=1)
    fig.add_hline(y=70, line=dict(color=col_ob,       width=1,   dash='dash'), row=3, col=1)
    fig.add_hline(y=30, line=dict(color=col_os,       width=1,   dash='dash'), row=3, col=1)
    fig.add_hline(y=50, line=dict(color=T['text_muted'], width=0.7, dash='dot'), row=3, col=1)

    ret = df['Return'].fillna(0).values
    ret_colors = [col_up if r >= 0 else col_down for r in ret]
    fig.add_trace(go.Bar(
        x=dt, y=ret, name='Return',
        marker=dict(color=ret_colors, opacity=0.70),
        showlegend=False,
        hovertemplate='<b>%{x|%Y-%m-%d}</b><br>Return: %{y:+.2f}%<extra></extra>',
    ), row=4, col=1)
    fig.add_hline(y=0, line=dict(color=T['text_muted'], width=1), row=4, col=1)

    fig.update_layout(
        height=1080,
        margin=dict(l=70, r=40, t=100, b=50),
        paper_bgcolor=T['bg_card'],
        plot_bgcolor=T['bg_card'],
        font=dict(family='Inter, system-ui, sans-serif', size=12, color=T['text_primary']),
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor=T['bg_elevated'], bordercolor=T['border'],
            font_size=13, font_color=T['text_primary'],
        ),
        legend=dict(
            orientation='h', yanchor='bottom', y=1.04,
            xanchor='right', x=1.0,
            bgcolor='rgba(0,0,0,0)',
            font=dict(size=12, color=T['text_primary']),
            itemsizing='constant',
        ),
        bargap=0.15,
    )
    fig.update_annotations(font=dict(size=13, color=T['text_secondary'], family='Inter'))

    fig.update_xaxes(
        showgrid=False, zeroline=False,
        showline=True, linecolor=T['border'], linewidth=1,
        tickfont=dict(size=11, color=T['text_muted']),
        showspikes=True, spikecolor=T['accent'],
        spikemode='across', spikesnap='cursor',
        spikedash='dot', spikethickness=1,
    )
    fig.update_yaxes(
        showgrid=True, gridcolor=T['grid'], gridwidth=1,
        zeroline=False, showline=False,
        tickfont=dict(size=11, color=T['text_muted']),
    )
    fig.update_yaxes(
        title=dict(text='Giá (nghìn VNĐ)', font=dict(size=11, color=T['text_secondary'])),
        tickformat=',.1f', row=1, col=1,
    )
    fig.update_yaxes(
        title=dict(text='Vol / MA5', font=dict(size=11, color=T['text_secondary'])),
        row=2, col=1,
    )
    fig.update_yaxes(
        title=dict(text='RSI 14', font=dict(size=11, color=T['text_secondary'])),
        range=[0, 100], tickvals=[0, 30, 50, 70, 100],
        ticktext=['0', '30 QB', '50', '70 QM', '100'],
        row=3, col=1,
    )
    fig.update_yaxes(
        title=dict(text='Return (%)', font=dict(size=11, color=T['text_secondary'])),
        row=4, col=1,
    )
    fig.update_xaxes(tickformat='%Y', tickfont=dict(size=12), row=4, col=1)

    return fig
