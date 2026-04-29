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

_TF_FREQ = {'1D': None, '1W': 'W-FRI', '1M': 'MS', '3M': 'QS'}
# Default zoom: 60 ngày (~45 nến) cho 1D — vừa thấy nhiều nến vừa đủ chi tiết.
_TF_DEFAULT_DAYS = {'1D': 60, '1W': 365, '1M': 1095, '3M': 1825}


def _resample_ohlc(df: pd.DataFrame, freq: str | None) -> pd.DataFrame:
    """Resample daily OHLC → weekly/monthly/quarterly. None = no-op (1D)."""
    if freq is None or len(df) == 0:
        return df.copy()
    g = df.set_index(pd.to_datetime(df['Ngay'])).resample(freq)
    out = pd.DataFrame({
        'Open':   g['Open'].first(),
        'High':   g['High'].max(),
        'Low':    g['Low'].min(),
        'Close':  g['Close'].last(),
        'Volume': g['Volume'].sum() if 'Volume' in df.columns else 0,
    }).dropna(subset=['Open', 'High', 'Low', 'Close'])
    out = out.reset_index().rename(columns={'index': 'Ngay'})
    if 'Ngay' not in out.columns and len(out.columns):
        out = out.rename(columns={out.columns[0]: 'Ngay'})
    return out


def chart_price_candlestick(df: pd.DataFrame, ticker: str, T: dict,
                            interval: str = '1D',
                            show_sma: bool = True,
                            show_ichimoku: bool = False) -> go.Figure:
    """Candlestick chart TradingView-style — multi-TF + Volume + toggle SMA/Ichimoku.

    Layout: 2 hàng share x-axis. Row 1 (75%) = nến + (optional) SMA + Ichimoku.
    Row 2 (25%) = volume bars (xanh/đỏ theo direction). KHÔNG dùng rangeslider
    nữa — thay bằng volume subplot. Pan/zoom qua scroll wheel + rangeselector.
    Layout không có legend (trang tổng quan); user bật/tắt SMA & Ichimoku
    qua toggle ở dashboard, KHÔNG qua legend click.
    """
    from plotly.subplots import make_subplots
    from data.ichimoku import add_ichimoku

    lang = st.session_state.get('lang', 'VI')
    label_all = 'Tất cả' if lang == 'VI' else 'All'

    # 1. Giới hạn 5 năm gần nhất
    if len(df) > 0:
        _last_date = pd.to_datetime(df['Ngay'].iloc[-1])
        _cutoff = _last_date - pd.Timedelta(days=5 * 365)
        df = df[pd.to_datetime(df['Ngay']) >= _cutoff].reset_index(drop=True)

    # 2. Resample theo timeframe
    df = _resample_ohlc(df, _TF_FREQ.get(interval))

    # 3. SMA tính lại trên (resampled) data
    if len(df) > 0:
        df['SMA5']  = df['Close'].rolling(5,  min_periods=5).mean()
        df['SMA20'] = df['Close'].rolling(20, min_periods=20).mean()

    # 4. Ichimoku (nếu bật) — yêu cầu đủ 52+26=78 bars cho cloud đầy đủ
    if show_ichimoku and len(df) > 30:
        try:
            df = add_ichimoku(df)
        except Exception:
            pass

    dates = pd.to_datetime(df['Ngay'])
    inc_color = '#10B981'
    dec_color = '#EF4444'
    sma5_color  = '#F59E0B'
    sma20_color = '#8B5CF6'

    # Volume colors theo direction từng nến
    if len(df) > 0:
        _vol_colors = [inc_color if c >= o else dec_color
                       for c, o in zip(df['Close'].values, df['Open'].values)]
    else:
        _vol_colors = []

    # 5. Build subplots — row 1 (75%) cho nến + SMA + Ichimoku, row 2 (25%) cho Volume
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.03,
    )

    # ── Row 1: Candlestick ───────────────────────────────────────────────
    fig.add_trace(go.Candlestick(
        x=dates,
        open=df['Open'].values,
        high=df['High'].values,
        low=df['Low'].values,
        close=df['Close'].values,
        increasing=dict(line=dict(color=inc_color, width=1), fillcolor=inc_color),
        decreasing=dict(line=dict(color=dec_color, width=1), fillcolor=dec_color),
        name=ticker,
        showlegend=False,
    ), row=1, col=1)

    # ── Row 1: Ichimoku Cloud — kỹ thuật giống trang Tín hiệu (sạch, không muddy)
    # Single color cloud theo state HIỆN TẠI (không mask per-point). Khi bull
    # hiện tại → toàn cloud xanh; khi bear → toàn cloud đỏ. Đơn giản & rõ.
    if show_ichimoku and 'Tenkan' in df.columns:
        sa = df['Senkou_A']
        sb = df['Senkou_B']

        _valid = sa.notna() & sb.notna()
        if _valid.any():
            _last_valid = sa[_valid].index[-1]
            _is_bull_now = sa.loc[_last_valid] >= sb.loc[_last_valid]
        else:
            _is_bull_now = True
        _fill_c = 'rgba(5,150,105,0.14)' if _is_bull_now else 'rgba(185,28,28,0.12)'

        # Senkou A — line emerald
        fig.add_trace(go.Scatter(
            x=dates, y=sa.values, mode='lines', name='Senkou A',
            line=dict(color='#059669', width=1.0),
            legendgroup='ichimoku', showlegend=False,
            hovertemplate='Senkou A: %{y:,.2f}<extra></extra>',
        ), row=1, col=1)
        # Senkou B — line red, fill='tonexty' tới Senkou A → cloud 1 màu
        fig.add_trace(go.Scatter(
            x=dates, y=sb.values, mode='lines', name='Senkou B',
            line=dict(color='#B91C1C', width=1.0),
            fill='tonexty', fillcolor=_fill_c,
            legendgroup='ichimoku', showlegend=False,
            hovertemplate='Senkou B: %{y:,.2f}<extra></extra>',
        ), row=1, col=1)

        # Tenkan red đậm + Kijun blue dashed (giống Ichimoku page)
        fig.add_trace(go.Scatter(
            x=dates, y=df['Tenkan'].values, mode='lines', name='Tenkan',
            line=dict(color='#DC2626', width=1.5),
            legendgroup='ichimoku', showlegend=False,
            hovertemplate='Tenkan: %{y:,.2f}<extra></extra>',
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=dates, y=df['Kijun'].values, mode='lines', name='Kijun',
            line=dict(color='#1565C0', width=1.8, dash='dash'),
            legendgroup='ichimoku', showlegend=False,
            hovertemplate='Kijun: %{y:,.2f}<extra></extra>',
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=dates, y=df['Chikou'].values, mode='lines', name='Chikou',
            line=dict(color='#7C3AED', width=1.2, dash='dot'),
            legendgroup='ichimoku', showlegend=False,
            hovertemplate='Chikou: %{y:,.2f}<extra></extra>',
        ), row=1, col=1)

    # ── Row 1: SMA overlays (toggle bật/tắt từ dashboard) ────────────────
    if show_sma and len(df) > 0:
        fig.add_trace(go.Scatter(
            x=dates, y=df['SMA5'].values, mode='lines', name='SMA 5',
            line=dict(color=sma5_color, width=1.3),
            hovertemplate='SMA 5: %{y:,.2f}<extra></extra>',
            showlegend=False,
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=dates, y=df['SMA20'].values, mode='lines', name='SMA 20',
            line=dict(color=sma20_color, width=1.3),
            hovertemplate='SMA 20: %{y:,.2f}<extra></extra>',
            showlegend=False,
        ), row=1, col=1)

    # ── Row 2: Volume bars ──────────────────────────────────────────────
    if len(df) > 0 and 'Volume' in df.columns:
        fig.add_trace(go.Bar(
            x=dates, y=df['Volume'].values,
            marker=dict(color=_vol_colors, line=dict(width=0)),
            name='Volume', showlegend=False,
            hovertemplate='Vol: %{y:,.0f}<extra></extra>',
        ), row=2, col=1)

    # 6. Default zoom theo interval (chỉ áp cho row 1; row 2 share)
    if len(dates) > 0:
        _last = dates.iloc[-1]
        _days = _TF_DEFAULT_DAYS.get(interval, 30)
        _xaxis_range = [_last - pd.Timedelta(days=_days), _last + pd.Timedelta(days=2)]
    else:
        _xaxis_range = None

    # 6.5. Fit Y-axis theo visible window — Plotly auto-Y dùng TOÀN BỘ data
    # nên với explicit X range, price sẽ bị squash. Tự tính Y range cho window.
    _yrange_price = None
    _yrange_volume = None
    if _xaxis_range is not None and len(df) > 0:
        _mask = (dates >= _xaxis_range[0]) & (dates <= _xaxis_range[1])
        _vis = df.loc[_mask.values]
        if len(_vis) > 0:
            _lo = float(_vis['Low'].min())
            _hi = float(_vis['High'].max())
            _pad = (_hi - _lo) * 0.08 if _hi > _lo else _hi * 0.02
            _yrange_price = [_lo - _pad, _hi + _pad]
            if 'Volume' in _vis.columns:
                _vmax = float(_vis['Volume'].max())
                if _vmax > 0:
                    _yrange_volume = [0, _vmax * 1.15]

    # 7. Rangebreaks chỉ áp dụng cho 1D
    _rangebreaks = [dict(bounds=['sat', 'mon'])] if interval == '1D' else None

    fig.update_layout(
        height=700,
        # right margin lớn hơn để vùng axis Y bên phải dễ click & drag
        margin=dict(l=30, r=70, t=50, b=30),
        paper_bgcolor=T['bg_chart'],
        plot_bgcolor=T['bg_chart'],
        font=dict(family='Inter, system-ui, sans-serif', size=11, color=T['text_primary']),
        showlegend=False,
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor=T['bg_card'], bordercolor=T['border'],
            font_size=12, font_color=T['text_primary'],
        ),
        uirevision=f'cs_{ticker}_{interval}',
        bargap=0.15,
        # TradingView-style: drag = pan, wheel = zoom
        dragmode='pan',
    )

    # axis-level uirevision: Plotly preserve user zoom/pan trên từng axis
    # khi figure rebuild (vd toggle SMA/Ichimoku) → không reset về initial range.
    _x_uirev = f'x_{ticker}_{interval}'
    _y_price_uirev = f'yp_{ticker}_{interval}'
    _y_vol_uirev = f'yv_{ticker}_{interval}'

    # X-axis chính (row 2, vì shared) — rangeselector đặt trên row 1
    fig.update_xaxes(
        range=_xaxis_range,
        uirevision=_x_uirev,
        type='date',
        showgrid=False, zeroline=False,
        showline=True, linecolor=T['border'], linewidth=1,
        ticks='outside', tickcolor=T['border'], ticklen=4,
        tickformat='%d/%m/%Y',
        tickfont=dict(size=10, color=T['text_muted']),
        showspikes=True, spikecolor=T['accent'], spikemode='across',
        spikesnap='cursor', spikedash='dot', spikethickness=1,
        **({'rangebreaks': _rangebreaks} if _rangebreaks else {}),
        row=2, col=1,
    )
    # X-axis row 1: gắn rangeselector
    fig.update_xaxes(
        uirevision=_x_uirev,
        type='date',
        showgrid=False, zeroline=False,
        showline=True, linecolor=T['border'], linewidth=1,
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
        rangeslider=dict(visible=False),
        **({'rangebreaks': _rangebreaks} if _rangebreaks else {}),
        row=1, col=1,
    )

    # Y-axis row 1 (price) — drag thanh để zoom Y; uirevision giữ user range
    fig.update_yaxes(
        range=_yrange_price,
        uirevision=_y_price_uirev,
        fixedrange=False,
        automargin=True,
        showgrid=True, gridcolor=T['grid'], gridwidth=1,
        zeroline=False,
        showline=True, linecolor=T['border'], linewidth=2,
        ticks='outside', tickcolor=T['border'], ticklen=10, tickwidth=2,
        tickformat=',.1f',
        tickfont=dict(size=12, color=T['text_secondary']),
        title=None,
        side='right',
        showspikes=True, spikecolor=T['accent'], spikemode='across',
        spikesnap='cursor', spikedash='dot', spikethickness=1,
        row=1, col=1,
    )
    # Y-axis row 2 (volume)
    fig.update_yaxes(
        range=_yrange_volume,
        uirevision=_y_vol_uirev,
        fixedrange=False,
        automargin=True,
        showgrid=True, gridcolor=T['grid'], gridwidth=1,
        zeroline=False,
        showline=True, linecolor=T['border'], linewidth=2,
        ticks='outside', tickcolor=T['border'], ticklen=8, tickwidth=1.5,
        tickformat='.2s',
        tickfont=dict(size=10, color=T['text_muted']),
        title=dict(text='Volume', font=dict(size=10, color=T['text_muted']), standoff=8),
        side='right',
        row=2, col=1,
    )

    return fig


def render_candlestick_info_bar(df: pd.DataFrame, ticker: str, interval: str,
                                 T: dict) -> str:
    """HTML info bar trên đầu chart — hiển thị O/H/L/C + change% + SMA giống TradingView."""
    if len(df) < 2:
        return ''
    df = _resample_ohlc(df, _TF_FREQ.get(interval))
    if len(df) < 2:
        return ''
    df['SMA5']  = df['Close'].rolling(5,  min_periods=5).mean()
    df['SMA20'] = df['Close'].rolling(20, min_periods=20).mean()

    last = df.iloc[-1]
    prev = df.iloc[-2]
    chg  = float(last['Close']) - float(prev['Close'])
    pct  = (chg / float(prev['Close']) * 100) if prev['Close'] else 0.0
    up   = chg >= 0
    chg_color = '#10B981' if up else '#EF4444'
    sign = '+' if up else ''

    def _fmt_sma(v):
        return f'{v:,.2f}' if pd.notna(v) else '—'

    return (
        f'<div style="display:flex;flex-wrap:wrap;gap:14px;align-items:center;'
        f'font-family:Inter,system-ui,sans-serif;font-size:12px;'
        f'background:{T["bg_card"]};border:1px solid {T["border"]};'
        f'padding:10px 14px;border-radius:8px;color:{T["text_primary"]};'
        f'margin-bottom:8px">'
        f'<span style="font-weight:800;color:{T["accent"]};letter-spacing:.5px">'
        f'{ticker} · {interval} · HOSE</span>'
        f'<span>O <b>{last["Open"]:,.2f}</b></span>'
        f'<span>H <b style="color:#10B981">{last["High"]:,.2f}</b></span>'
        f'<span>L <b style="color:#EF4444">{last["Low"]:,.2f}</b></span>'
        f'<span>C <b>{last["Close"]:,.2f}</b></span>'
        f'<span style="color:{chg_color};font-weight:700">'
        f'{sign}{chg:,.2f} ({sign}{pct:.2f}%)</span>'
        f'<span style="color:#F59E0B;margin-left:auto">SMA 5: <b>{_fmt_sma(last["SMA5"])}</b></span>'
        f'<span style="color:#8B5CF6">SMA 20: <b>{_fmt_sma(last["SMA20"])}</b></span>'
        f'</div>'
    )
