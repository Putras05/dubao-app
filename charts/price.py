import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import plotly.graph_objects as go

from core.themes import theme, set_mpl_theme
from core.constants import CLR, CLR_DARK, get_clr
from core.i18n import t
from charts.base import _plotly_layout_base


def chart_price_history(res: dict, ticker: str, date_from=None, date_to=None, T: dict = None):
    if T is None: T = theme()
    set_mpl_theme(T)
    is_dark = T.get('is_dark', False)
    CLR_NOW    = get_clr(T)
    col        = CLR_NOW[ticker]
    pred_col   = CLR_NOW['pred']
    train_fill = (CLR_DARK['FPT'] if is_dark else CLR[ticker], 0.12 if is_dark else 0.10)
    test_fill  = (CLR_NOW['pred'], 0.10 if is_dark else 0.08)
    bg = T['bg_chart']

    dt_all = pd.to_datetime(res['dates_full'])
    cl_all = res['close_full']
    nt     = res['nt']
    mask   = np.ones(len(dt_all), bool)
    if date_from: mask &= dt_all >= pd.Timestamp(date_from)
    if date_to:   mask &= dt_all <= pd.Timestamp(date_to)
    if mask.sum() < 2: mask = np.ones(len(dt_all), bool)
    dt_show = dt_all[mask]; cl_show = cl_all[mask]
    train_mask = mask & (np.arange(len(dt_all)) < nt)
    test_mask  = mask & (np.arange(len(dt_all)) >= nt)
    split_dt   = dt_all[nt] if nt < len(dt_all) else None

    fig, ax = plt.subplots(figsize=(13, 3.8))
    fig.patch.set_facecolor(bg); ax.set_facecolor(bg)
    if train_mask.any():
        ax.fill_between(dt_all[train_mask], cl_all[train_mask], alpha=train_fill[1], color=train_fill[0])
    if test_mask.any():
        ax.fill_between(dt_all[test_mask], cl_all[test_mask], alpha=test_fill[1], color=test_fill[0])
    ax.plot(dt_show, cl_show, color=col, lw=1.5, zorder=4)
    if split_dt is not None:
        ax.axvline(split_dt, color=pred_col, lw=1.4, ls='--', alpha=.65)
    if train_mask.any() and test_mask.any():
        tr_v = dt_all[train_mask]; te_v = dt_all[test_mask]; ym = cl_show.max()
        ax.text(tr_v[len(tr_v)//2], ym*.96, 'TRAIN', ha='center', fontsize=8, color=col, alpha=.65, fontweight='700')
        ax.text(te_v[len(te_v)//2], ym*.96, 'TEST',  ha='center', fontsize=8, color=pred_col, alpha=.65, fontweight='700')
    d0 = str(dt_show[0].date()); d1 = str(dt_show[-1].date())
    ax.set_title(f'{ticker}  —  Lịch sử giá đóng cửa  ({d0} → {d1})', fontsize=11, fontweight='bold', pad=8)
    ax.set_ylabel('Giá đóng cửa (nghìn VNĐ)', fontsize=9)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.xaxis.set_major_locator(mdates.YearLocator(max(1, (dt_show[-1] - dt_show[0]).days // 365 // 7)))
    plt.tight_layout(); return fig


def chart_price_history_plotly(res: dict, ticker: str,
                                date_from=None, date_to=None, T: dict = None) -> go.Figure:
    if T is None: T = theme()
    is_dark = T.get('is_dark', False)

    dt_all = pd.to_datetime(res['dates_full'])
    cl_all = np.array(res['close_full'], dtype=float)
    nt     = res['nt']

    mask = np.ones(len(dt_all), bool)
    if date_from: mask &= dt_all >= pd.Timestamp(date_from)
    if date_to:   mask &= dt_all <= pd.Timestamp(date_to)
    if mask.sum() < 2: mask = np.ones(len(dt_all), bool)

    dt_show = dt_all[mask]
    idx_all  = np.arange(len(dt_all))
    train_idx = np.where((idx_all < nt) & mask)[0]
    test_idx  = np.where((idx_all >= nt) & mask)[0]
    split_date = dt_all[nt] if nt < len(dt_all) else None

    x_train = list(dt_all[train_idx].to_pydatetime()) if len(train_idx) else []
    x_test  = list(dt_all[test_idx].to_pydatetime())  if len(test_idx) else []
    split_date_str = split_date.strftime('%Y-%m-%d') if split_date is not None else None

    line_train = '#2962FF' if is_dark else '#1565C0'
    line_test  = '#F87171' if is_dark else '#EF4444'
    fill_train = 'rgba(41,98,255,0.14)' if is_dark else 'rgba(21,101,192,0.09)'
    fill_test  = 'rgba(248,113,113,0.12)' if is_dark else 'rgba(239,68,68,0.08)'

    fig = go.Figure()

    if len(x_train):
        fig.add_trace(go.Scatter(
            x=x_train, y=cl_all[train_idx], mode='lines', name='TRAIN',
            line=dict(color=line_train, width=1.6),
            fill='tozeroy', fillcolor=fill_train,
            hovertemplate=f'<b>%{{x|%Y-%m-%d}}</b><br>{t("chart.hover_price")}: %{{y:,.2f}} {t("chart.hover_unit")}<br>'
                          '<span style="color:#60A5FA">● TRAIN</span><extra></extra>',
        ))
    if len(x_test):
        fig.add_trace(go.Scatter(
            x=x_test, y=cl_all[test_idx], mode='lines', name='TEST',
            line=dict(color=line_test, width=1.6),
            fill='tozeroy', fillcolor=fill_test,
            hovertemplate=f'<b>%{{x|%Y-%m-%d}}</b><br>{t("chart.hover_price")}: %{{y:,.2f}} {t("chart.hover_unit")}<br>'
                          '<span style="color:#F87171">● TEST</span><extra></extra>',
        ))

    if split_date_str is not None:
        fig.add_vline(x=split_date_str, line=dict(color=T['text_muted'], width=1.8, dash='dash'))
        fig.add_annotation(
            x=split_date_str, xref='x',
            y=1.02, yref='paper',
            text=t('chart.train_test_split'),
            showarrow=False, xanchor='center',
            font=dict(size=10, color=T['text_secondary']),
            bgcolor=T['bg_card'], borderpad=4,
        )

    d0 = str(dt_show[0].date()); d1 = str(dt_show[-1].date())
    lay = _plotly_layout_base(T, height=420)
    lay['title'] = dict(
        text=t('chart.price_history_title', ticker=ticker)
             + f'<span style="color:{T["text_muted"]};font-size:12px"> ({d0} → {d1})</span>',
        x=0.5, xanchor='center',
        font=dict(size=13, family='Inter', color=T['text_primary']),
        pad=dict(t=8, b=6),
    )
    lay['xaxis'] = dict(
        showgrid=False, zeroline=False,
        showline=True, linecolor=T['border'], linewidth=1,
        ticks='outside', tickcolor=T['border'], ticklen=4,
        tickfont=dict(size=10, color=T['text_muted']),
        showspikes=True, spikecolor=T['accent'], spikemode='across',
        spikesnap='cursor', spikedash='dot', spikethickness=1,
        rangeselector=dict(
            buttons=[
                dict(count=1, label='1N', step='year', stepmode='backward'),
                dict(count=3, label='3N', step='year', stepmode='backward'),
                dict(count=5, label='5N', step='year', stepmode='backward'),
                dict(step='all', label=t('chart.all_btn')),
            ],
            bgcolor=T['bg_card'], activecolor=T['accent'],
            bordercolor=T['border'], borderwidth=1,
            font=dict(color=T['text_primary'], size=10, family='Inter'),
            x=0, y=1.08, yanchor='bottom',
        ),
        type='date',
    )
    lay['yaxis'] = dict(
        showgrid=True, gridcolor=T['grid'], gridwidth=1,
        zeroline=False, showline=False, ticks='',
        tickformat=',.1f',
        tickfont=dict(size=10, color=T['text_muted']),
        title=dict(text=t('chart.price_axis'), font=dict(size=11, color=T['text_secondary']), standoff=14),
        showspikes=True, spikecolor=T['accent'], spikemode='across',
        spikesnap='cursor', spikedash='dot', spikethickness=1,
    )
    fig.update_layout(**lay)
    return fig
