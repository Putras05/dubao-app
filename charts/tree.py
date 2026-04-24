import plotly.graph_objects as go
from sklearn.tree import DecisionTreeRegressor

from core.themes import theme
from core.i18n import t
from data.fetcher import fetch_data

FEATS      = ['Return_L1', 'Volume_ratio_L1', 'Range_ratio_L1',
              'MA5_ratio_L1', 'MA20_ratio_L1', 'RSI14_L1']
FEAT_NAMES = ['Return', 'Vol/MA5', 'Range%', 'MA5_ratio', 'MA20_ratio', 'RSI14']


def render_decision_tree_cart(ticker: str, train_ratio: float, T=None, best_params: dict = None) -> go.Figure:
    """Vẽ sơ đồ cây CART — Plotly, kết nối vuông góc, có toolbar đầy đủ."""
    if T is None:
        T = theme()

    df_local = fetch_data(ticker)
    N  = len(df_local)
    nt = int(N * train_ratio)

    Xtr = df_local[FEATS].values[:nt]
    Ytr = df_local['Return'].values[:nt]

    params = best_params if best_params else {'max_depth': 3, 'min_samples_leaf': 20}
    model  = DecisionTreeRegressor(random_state=42, **params).fit(Xtr, Ytr)

    is_dark   = T.get('is_dark', False)
    bg        = T['bg_card']
    fg        = T['text_primary']
    fg_sec    = T['text_secondary']
    brd       = T['border']
    edge_clr  = '#475569' if is_dark else '#94A3B8'
    label_clr = '#94A3B8' if is_dark else '#64748B'

    # Diverging: blue (low/negative return) → yellow → orange/red (high/positive return)
    palette_light = ['#4575B4', '#91BFDB', '#E0F3F8', '#FEE090', '#FC8D59', '#D73027']
    palette_dark  = ['#313695', '#4575B4', '#74ADD1', '#FDAE61', '#F46D43', '#A50026']
    palette   = palette_dark if is_dark else palette_light

    tree_     = model.tree_
    node_vals = tree_.value.flatten()
    v_min, v_max = node_vals.min(), node_vals.max()
    v_range   = (v_max - v_min) if v_max > v_min else 1.0

    def node_color(nid):
        norm = (node_vals[nid] - v_min) / v_range
        idx  = min(int(norm * (len(palette) - 1)), len(palette) - 1)
        return palette[idx], idx

    SPACING = 2.4
    NW_INT, NH_INT   = 0.90, 0.32
    NW_LEAF, NH_LEAF = 0.78, 0.30

    def _nw(nid): return NW_INT  if tree_.children_left[nid] != -1 else NW_LEAF
    def _nh(nid): return NH_INT  if tree_.children_left[nid] != -1 else NH_LEAF

    leaf_order = []
    def dfs_leaves(n):
        if tree_.children_left[n] == -1: leaf_order.append(n)
        else: dfs_leaves(tree_.children_left[n]); dfs_leaves(tree_.children_right[n])
    dfs_leaves(0)

    n_leaves   = len(leaf_order)
    leaf_x_map = {n: float(i * SPACING) for i, n in enumerate(leaf_order)}

    def subtree_cx(n):
        if tree_.children_left[n] == -1: return leaf_x_map[n]
        return (subtree_cx(tree_.children_left[n]) + subtree_cx(tree_.children_right[n])) / 2

    def tree_depth(n):
        if tree_.children_left[n] == -1: return 0
        return 1 + max(tree_depth(tree_.children_left[n]), tree_depth(tree_.children_right[n]))

    max_d = tree_depth(0)
    pos   = {}

    def build_pos(n, depth=0):
        pos[n] = (subtree_cx(n), float(max_d - depth))
        if tree_.children_left[n] != -1:
            build_pos(tree_.children_left[n],  depth + 1)
            build_pos(tree_.children_right[n], depth + 1)
    build_pos(0)

    # Translate all nodes so the root sits at the visual centre of the x-axis
    _root_cx = pos[0][0]
    _offset  = (n_leaves - 1) * SPACING / 2 - _root_cx
    if abs(_offset) > 1e-9:
        for _nid in pos:
            pos[_nid] = (pos[_nid][0] + _offset, pos[_nid][1])

    x_span = (n_leaves - 1) * SPACING
    # Padding tăng mạnh để node rìa + annotation KHÔNG bị clip khi scale.
    # Annotation text có thể rộng ~1-1.5 x-units → cần buffer >= 2x.
    pad_x  = max(2.8, NW_INT + 1.8)
    pad_y  = 1.2

    line_x, line_y    = [], []
    lbl_annotations   = []

    def add_split(par, lc, rc):
        """Vẽ connector từ parent xuống 2 children — KHÔNG overlap vertical segment.

        Cấu trúc:
          parent ↓ (vẽ 1 lần)
                 ├── left child (vẽ horizontal + vertical xuống)
                 └── right child (vẽ horizontal + vertical xuống)
        """
        px, py = pos[par]
        lcx, lcy = pos[lc]; rcx, rcy = pos[rc]
        ph   = _nh(par)
        lch, rch = _nh(lc), _nh(rc)
        mid_y_l = (py - ph + lcy + lch) / 2
        mid_y_r = (py - ph + rcy + rch) / 2
        mid_y   = min(mid_y_l, mid_y_r)

        # 1. Vertical từ đáy parent xuống mid_y (vẽ MỘT LẦN duy nhất)
        line_x.extend([px, px, None])
        line_y.extend([py - ph, mid_y, None])

        # 2. Horizontal bar nối sang left child
        line_x.extend([px, lcx, None])
        line_y.extend([mid_y, mid_y, None])
        # Vertical xuống left child
        line_x.extend([lcx, lcx, None])
        line_y.extend([mid_y, lcy + lch, None])

        # 3. Horizontal bar nối sang right child
        line_x.extend([px, rcx, None])
        line_y.extend([mid_y, mid_y, None])
        # Vertical xuống right child
        line_x.extend([rcx, rcx, None])
        line_y.extend([mid_y, rcy + rch, None])

        # Labels TRUE/FALSE
        for child_x, cy, ch, is_left in [(lcx, lcy, lch, True), (rcx, rcy, rch, False)]:
            lbl = t('cart.lbl_true') if is_left else t('cart.lbl_false')
            lbl_annotations.append(dict(
                x=(px + child_x) / 2, y=mid_y + 0.08,
                text=lbl, showarrow=False,
                font=dict(size=9, color=label_clr, family='Inter'),
                xanchor='center', yanchor='bottom', bgcolor='rgba(0,0,0,0)',
            ))

    def traverse(n=0):
        lc, rc = tree_.children_left[n], tree_.children_right[n]
        if lc != -1:
            add_split(n, lc, rc)
            traverse(lc); traverse(rc)
    traverse()

    shapes, node_annotations = [], []

    for nid in range(tree_.node_count):
        x, y     = pos[nid]
        clr, idx = node_color(nid)
        txt_clr  = '#FFFFFF' if (is_dark or idx in {0, 4, 5}) else '#0F172A'
        nw, nh   = _nw(nid), _nh(nid)
        is_leaf  = tree_.children_left[nid] == -1
        ns       = tree_.n_node_samples[nid]
        val      = node_vals[nid]

        if is_leaf:
            sign = '+' if val >= 0 else ''
            txt = f'n = {ns}<br><b>{sign}{val:.3f}%</b>'
        else:
            fi, thresh = tree_.feature[nid], tree_.threshold[nid]
            txt = f'<b>{FEAT_NAMES[fi]} ≤ {thresh:.3f}</b><br>n = {ns} · val = {val:.3f}%'

        shapes.append(dict(
            type='rect', layer='above',
            x0=x - nw, y0=y - nh, x1=x + nw, y1=y + nh,
            fillcolor=clr,
            # Border cùng màu fill — tránh aliasing "viền sáng" ở subpixel
            line=dict(color=clr, width=0),
        ))
        node_annotations.append(dict(
            x=x, y=y, text=txt, showarrow=False,
            font=dict(size=10, color=txt_clr, family='Inter'),
            xanchor='center', yanchor='middle', align='center',
            bgcolor='rgba(0,0,0,0)',
            # Không clip theo plot area → text luôn hiện dù node sát rìa
            xref='x', yref='y',
        ))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=line_x, y=line_y, mode='lines',
        line=dict(color=edge_clr, width=1.7),
        hoverinfo='skip', showlegend=False,
    ))
    for clr_leg, lbl_leg in [
        (palette[0],               t('cart.tree_legend_low')),
        (palette[len(palette)//2], t('cart.tree_legend_mid')),
        (palette[-1],              t('cart.tree_legend_high')),
    ]:
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode='markers',
            marker=dict(color=clr_leg, size=13, symbol='square',
                        line=dict(color=brd, width=1)),
            name=lbl_leg, showlegend=True,
        ))

    _n_train  = int(model.tree_.n_node_samples[0])
    subtitle = (f'max_depth = {params["max_depth"]}  ·  '
                f'min_samples_leaf = {params["min_samples_leaf"]}  ·  '
                f'n_train = {_n_train:,}  ·  '
                f'{t("cart.tree_subtitle_tail")}')
    fig.update_layout(
        shapes=shapes,
        annotations=lbl_annotations + node_annotations,
        title=dict(
            text=(f'<b>{t("cart.tree_title_full", ticker=ticker)}</b><br>'
                  f'<span style="font-size:11px">{subtitle}</span>'),
            x=0.5, xanchor='center',
            font=dict(size=15, color=fg, family='Inter'),
        ),
        xaxis=dict(range=[-pad_x, x_span + pad_x],
                   showgrid=False, showticklabels=False, zeroline=False, showline=False,
                   fixedrange=False,
                   automargin=True),
        yaxis=dict(range=[-pad_y, max_d + pad_y],
                   showgrid=False, showticklabels=False, zeroline=False, showline=False,
                   automargin=True),
        paper_bgcolor=bg, plot_bgcolor=bg,
        font=dict(family='Inter', color=fg),
        height=max(520, (max_d + 1) * 145 + 120),
        margin=dict(l=20, r=20, t=110, b=20),
        legend=dict(
            orientation='h', yanchor='bottom', y=-0.04,
            xanchor='center', x=0.5,
            bgcolor=T['bg_elevated'], bordercolor=brd, borderwidth=1,
            font=dict(size=10, color=fg),
            itemsizing='constant',
        ),
        hovermode=False,
    )
    return fig
