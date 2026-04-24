import io
import base64
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import plotly.graph_objects as go

from core.themes import theme, set_mpl_theme, lighten_color
from core.constants import get_clr


_PLOTLY_CONFIG = {
    'displayModeBar': True, 'displaylogo': False,
    'modeBarButtonsToRemove': [
        'lasso2d', 'select2d', 'autoScale2d',
        'hoverClosestCartesian', 'hoverCompareCartesian', 'toggleSpikelines',
    ],
    'toImageButtonOptions': {'format': 'png', 'scale': 2},
}


def calc_r2(y_true, y_pred) -> float:
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    return float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0


def _plotly_axes_style(fig: go.Figure, T: dict) -> None:
    fig.update_xaxes(
        showgrid=False, zeroline=False,
        showline=True, linecolor=T['border'], linewidth=1,
        ticks='outside', tickcolor=T['border'], ticklen=4,
        tickfont=dict(size=10, color=T['text_muted']),
        showspikes=True, spikecolor=T['accent'], spikemode='across',
        spikesnap='cursor', spikedash='dot', spikethickness=1,
    )
    fig.update_yaxes(
        showgrid=True, gridcolor=T['grid'], gridwidth=1,
        zeroline=False, showline=False, ticks='',
        tickformat=',.2f',
        tickfont=dict(size=10, color=T['text_muted']),
        showspikes=True, spikecolor=T['accent'], spikemode='across',
        spikesnap='cursor', spikedash='dot', spikethickness=1,
    )


def _plotly_layout_base(T: dict, height: int = 360) -> dict:
    return dict(
        height=height,
        paper_bgcolor=T['bg_card'],
        plot_bgcolor=T['bg_card'],
        font=dict(family='Inter, system-ui, sans-serif', size=11, color=T['text_primary']),
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor=T['bg_elevated'], bordercolor=T['border'],
            font_size=12, font_color=T['text_primary'], font_family='Inter',
        ),
        legend=dict(
            orientation='h', yanchor='bottom', y=1.04,
            xanchor='right', x=1.0,
            bgcolor='rgba(0,0,0,0)',
            font=dict(size=11, color=T['text_primary']),
            itemsizing='constant',
        ),
        margin=dict(l=55, r=20, t=70, b=45),
    )


def sparkline_b64(prices, next_price, col, T: dict = None):
    if T is None: T = theme()
    set_mpl_theme(T)
    is_dark = T.get('is_dark', False)
    bg = T['bg_card']
    line_col = lighten_color(col, 0.20) if is_dark else col
    prices = list(prices)
    fig, ax = plt.subplots(figsize=(3.6, 1.3))
    fig.patch.set_facecolor(bg); ax.set_facecolor(bg)
    n = len(prices)
    ax.plot(range(n), prices, color=line_col, lw=2.0, solid_capstyle='round', zorder=3)
    chg     = next_price - prices[-1]
    seg_col = '#10B981' if chg >= 0 else '#EF4444'
    ax.plot([n-1, n], [prices[-1], next_price], color=seg_col, lw=1.8, ls='--', alpha=.75, zorder=2)
    ax.scatter([n], [next_price], color=seg_col, s=55, zorder=5)
    for sp in ax.spines.values(): sp.set_visible(False)
    ax.set_xticks([]); ax.set_yticks([])
    plt.tight_layout(pad=0.1)
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor=bg, edgecolor=bg)
    plt.close(fig); buf.seek(0)
    return base64.b64encode(buf.read()).decode()
