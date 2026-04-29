"""Ichimoku Kinko Hyo chart — 120 phiên lịch sử + 26 phiên tương lai (mây dẫn trước)."""
from __future__ import annotations
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from core.themes import theme
from core.constants import get_clr
from core.i18n import t
from data.ichimoku import _rolling_midpoint, SENKOU_N, DISPLACE


def chart_ichimoku_plotly(df_ichi: pd.DataFrame, ticker: str, T: dict = None) -> go.Figure:
    """
    Vẽ Ichimoku Kinko Hyo đầy đủ 5 đường + mây Kumo bull/bear.
    df_ichi phải đã qua add_ichimoku().
    120 phiên lịch sử + 26 phiên tương lai (để hiện mây dẫn trước).
    """
    if T is None:
        T = theme()

    is_dark   = T.get('is_dark', False)
    _clr      = get_clr(T)
    col_close  = _clr.get(ticker, '#1565C0')
    col_tenkan = '#F87171' if is_dark else '#DC2626'
    col_kijun  = '#60A5FA' if is_dark else '#1565C0'
    col_chikou = '#C084FC' if is_dark else '#7C3AED'
    # col_senA/col_senB đã bỏ vì border lines bị xoá (cloud fill đã đủ màu)
    # Cloud opacity bump để mây xanh/đỏ rõ hơn (per-period mask)
    col_bull   = 'rgba(52,211,153,0.28)' if is_dark else 'rgba(5,150,105,0.22)'
    col_bear   = 'rgba(248,113,113,0.30)' if is_dark else 'rgba(185,28,28,0.20)'
    bg         = T['bg_card']
    fg         = T['text_primary']
    muted      = T.get('text_muted', '#64748B')
    grid_c     = T.get('grid', '#E2E8F0')
    border_c   = T.get('border', '#E2E8F0')

    # Lấy tối đa 120 phiên lịch sử
    hist = df_ichi.tail(min(120, len(df_ichi))).copy().reset_index(drop=True)
    dates_h   = pd.to_datetime(hist['Ngay'])
    last_date = dates_h.iloc[-1]

    # 26 ngày giao dịch tương lai để vẽ mây dẫn trước
    fut_dates = pd.bdate_range(start=last_date + pd.Timedelta(days=1), periods=DISPLACE)

    # Tính Senkou A/B tương lai:
    # sen_a_fut[k] = (Tenkan[N-DISPLACE+k] + Kijun[N-DISPLACE+k]) / 2, k=0..25
    # sen_b_fut[k] = rolling_midpoint_52[N-DISPLACE+k]  (trước khi shift)
    n = len(df_ichi)
    tk_slice = df_ichi['Tenkan'].values[max(0, n - DISPLACE):]
    kj_slice = df_ichi['Kijun'].values[max(0, n - DISPLACE):]
    sb_raw   = _rolling_midpoint(df_ichi['High'], df_ichi['Low'], SENKOU_N).values[max(0, n - DISPLACE):]

    # Pad nếu dữ liệu ngắn hơn DISPLACE
    pad = DISPLACE - len(tk_slice)
    if pad > 0:
        tk_slice = np.concatenate([np.full(pad, np.nan), tk_slice])
        kj_slice = np.concatenate([np.full(pad, np.nan), kj_slice])
        sb_raw   = np.concatenate([np.full(pad, np.nan), sb_raw])

    sa_fut = (tk_slice + kj_slice) / 2.0
    sb_fut = sb_raw

    # Ghép lịch sử + tương lai cho mây
    all_dates = list(dates_h) + list(fut_dates)
    sa_all    = list(hist['Senkou_A'].values) + list(sa_fut)
    sb_all    = list(hist['Senkou_B'].values) + list(sb_fut)

    sa_np = np.array(sa_all, dtype=float)
    sb_np = np.array(sb_all, dtype=float)

    # FIX root cause "vùng xám": dùng `fill='toself'` self-closing polygon
    # thay vì 4 trace `tonexty` chia chung x-domain (Plotly merge polygon
    # giữa các trace cùng axis → alpha blend xanh+đỏ → muddy).
    valid = ~(np.isnan(sa_np) | np.isnan(sb_np))

    fig = go.Figure()

    if valid.any():
        x_arr = np.array(all_dates, dtype=object)
        x_v   = x_arr[valid]
        sa_v  = sa_np[valid]
        sb_v  = sb_np[valid]
        bull_mask = sa_v >= sb_v

        # Polygon BULL: top = sa khi bull, ngoài bull collapse về sb (height=0)
        top_bull = np.where(bull_mask, sa_v, sb_v)
        xs_bull = np.concatenate([x_v, x_v[::-1]])
        ys_bull = np.concatenate([top_bull, sb_v[::-1]])
        fig.add_trace(go.Scatter(
            x=xs_bull, y=ys_bull,
            fill='toself', fillcolor=col_bull,
            line=dict(width=0, color='rgba(0,0,0,0)'),
            name=t('ichi_chart.senkou_a'),
            hoverinfo='skip', showlegend=False,
        ))

        # Polygon BEAR: top = sb khi bear, ngoài bear collapse về sa
        top_bear = np.where(~bull_mask, sb_v, sa_v)
        xs_bear = np.concatenate([x_v, x_v[::-1]])
        ys_bear = np.concatenate([top_bear, sa_v[::-1]])
        fig.add_trace(go.Scatter(
            x=xs_bear, y=ys_bear,
            fill='toself', fillcolor=col_bear,
            line=dict(width=0, color='rgba(0,0,0,0)'),
            name=t('ichi_chart.senkou_b'),
            hoverinfo='skip', showlegend=False,
        ))

    # ── Tenkan-sen ──
    fig.add_trace(go.Scatter(
        x=dates_h, y=hist['Tenkan'], mode='lines',
        name=t('ichi_chart.tenkan'),
        line=dict(color=col_tenkan, width=1.5),
        hovertemplate='Tenkan: %{y:,.3f}<extra></extra>',
    ))

    # ── Kijun-sen ──
    fig.add_trace(go.Scatter(
        x=dates_h, y=hist['Kijun'], mode='lines',
        name=t('ichi_chart.kijun'),
        line=dict(color=col_kijun, width=1.8, dash='dash'),
        hovertemplate='Kijun: %{y:,.3f}<extra></extra>',
    ))

    # ── Chikou span — Close[t] vẽ LÙI 26 phiên giao dịch ───────────────
    # Theo định nghĩa Hosoda (1969): Chikou = Close[t] plotted at position t-26.
    # Implement: vẽ Close thực tế tại toạ độ (Ngay[t] - 26 BDay, Close[t]).
    # Kết quả: đường Chikou nằm ở QUÁ KHỨ trên chart, không bị cắt ở cuối.
    chikou_x = dates_h - pd.tseries.offsets.BDay(DISPLACE)
    chikou_y = hist['Close']
    fig.add_trace(go.Scatter(
        x=chikou_x, y=chikou_y, mode='lines',
        name=t('ichi_chart.chikou'),
        line=dict(color=col_chikou, width=1.2, dash='dot'),
        hovertemplate='<b>%{x|%Y-%m-%d}</b><br>Chikou: %{y:,.3f}<extra></extra>',
    ))

    # ── Giá đóng cửa / Close price (trên cùng) ──
    fig.add_trace(go.Scatter(
        x=dates_h, y=hist['Close'], mode='lines',
        name=t('ichi_chart.close', ticker=ticker),
        line=dict(color=col_close, width=2.2),
        hovertemplate=f'<b>%{{x|%Y-%m-%d}}</b><br>{t("ichi_chart.hover_price")}: %{{y:,.3f}}<extra></extra>',
    ))

    # ── Đường dọc phân tách hiện tại / tương lai ──
    # Dùng add_shape thay add_vline để tránh bug Plotly int+str với date axis
    fig.add_shape(
        type='line',
        x0=last_date, x1=last_date,
        y0=0, y1=1, yref='paper',
        line=dict(color=muted, width=1.0, dash='dash'),
    )
    fig.add_annotation(
        x=last_date, y=1.01, yref='paper',
        text=t('ichi_chart.today'), showarrow=False,
        font=dict(size=9, color=muted),
        xanchor='left', yanchor='bottom',
    )

    fig.update_layout(
        height=500,
        paper_bgcolor=bg,
        plot_bgcolor=bg,
        font=dict(family='Inter', size=11, color=fg),
        hovermode='x unified',
        hoverlabel=dict(bgcolor=T['bg_elevated'], bordercolor=border_c,
                        font_size=11, font_color=fg, font_family='Inter'),
        legend=dict(
            orientation='h', yanchor='bottom', y=-0.32,
            xanchor='center', x=0.5,
            font=dict(size=10, color=fg), bgcolor='rgba(0,0,0,0)',
            itemsizing='constant',
        ),
        margin=dict(l=65, r=30, t=50, b=130),
        xaxis=dict(
            showgrid=False, showline=True, linecolor=border_c,
            tickfont=dict(size=10, color=muted), automargin=True,
        ),
        yaxis=dict(
            showgrid=True, gridcolor=grid_c, zeroline=False,
            tickformat=',.3f', tickfont=dict(size=10, color=muted),
            title=dict(text=t('ichi_chart.y_axis'), font=dict(size=11, color=muted)),
        ),
    )

    return fig
