from core.i18n import t


_SVG_ICONS = {
    'home':        '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
    'chart-bar':   '<line x1="12" y1="20" x2="12" y2="10"/><line x1="18" y1="20" x2="18" y2="4"/><line x1="6" y1="20" x2="6" y2="16"/>',
    'clock':       '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    'trending-up': '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>',
    'briefcase':   '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
    'award':       '<circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/>',
    'alert':       '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    'refresh':     '<polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>',
    'info':        '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>',
    'check':       '<polyline points="20 6 9 17 4 12"/>',
    'x':           '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
    'minus':       '<line x1="5" y1="12" x2="19" y2="12"/>',
    'activity':    '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
    'pie-chart':   '<path d="M21.21 15.89A10 10 0 1 1 8 2.83"/><path d="M22 12A10 10 0 0 0 12 2v10z"/>',
}


def svg_icon(name: str, size: int = 18, color: str = 'currentColor', stroke_w: float = 2) -> str:
    path = _SVG_ICONS.get(name, '')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="0 0 24 24" fill="none" stroke="{color}" '
            f'stroke-width="{stroke_w}" stroke-linecap="round" stroke-linejoin="round">'
            f'{path}</svg>')


def sparkline_svg(prices, color: str, width: int = 240, height: int = 56) -> str:
    prices = [float(p) for p in prices if p is not None]
    if len(prices) < 2: return ''
    mn, mx = min(prices), max(prices)
    rng = mx - mn if mx > mn else 1e-9
    pad_y = height * 0.10
    uid = color.replace('#', '')

    pts = []
    for i, p in enumerate(prices):
        x = i * width / (len(prices) - 1)
        y = height - pad_y - ((p - mn) / rng) * (height - 2 * pad_y)
        pts.append((x, y))

    path = 'M ' + ' L '.join(f'{x:.1f},{y:.1f}' for x, y in pts)
    area = path + f' L {width},{height} L 0,{height} Z'
    ex, ey = pts[-1]
    return (
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
        f'style="width:100%;height:{height}px;display:block;overflow:visible">'
        f'<defs>'
        f'<linearGradient id="sg{uid}" x1="0" x2="0" y1="0" y2="1">'
        f'<stop offset="0%" stop-color="{color}" stop-opacity="0.35"/>'
        f'<stop offset="100%" stop-color="{color}" stop-opacity="0.02"/>'
        f'</linearGradient></defs>'
        f'<path d="{area}" fill="url(#sg{uid})" stroke="none"/>'
        f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2.2" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
        f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="4.5" fill="{color}" stroke="white" stroke-width="2"/>'
        f'</svg>'
    )


def render_ai_insight(ticker: str,
                      overall_code: str,
                      overall_label: str,
                      score: int,
                      primary_label: str,
                      trading_label: str,
                      chikou_label: str,
                      future_label: str,
                      best_model: str,
                      best_mape: float,
                      best_r2adj: float,
                      next_price: float,
                      next_pct: float,
                      next_date: str,
                      T: dict) -> str:
    """
    AI Insight dựa trên Ichimoku consensus (4 tầng + score) + mô hình dự báo tốt nhất.

    Thay thế AI Insight cũ (dùng RSI/MA cross) — đồng bộ phương pháp luận
    với page Tín hiệu: chỉ dùng Ichimoku làm hệ cảnh báo.
    """
    # Màu & icon theo consensus
    if overall_code in ('strong_bull', 'mild_bull'):
        hdr_color = T['success']; hdr_icon  = '▲'
    elif overall_code in ('strong_bear', 'mild_bear'):
        hdr_color = T['danger'];  hdr_icon  = '▼'
    else:
        hdr_color = T['warning']; hdr_icon  = '='

    _score_s = f'+{score}' if score > 0 else str(score)

    # Kết luận Ichimoku — dùng trực tiếp overall_label (đã là i18n từ caller).
    # Caller (dashboard.py) truyền overall_label = t(f'ichi.overall.{_ov_code}')
    # → tự động đổi VI/EN theo session lang.
    line1 = (f'{t("ai_insight.signal_prefix")} '
             f'<b style="color:{hdr_color}">{hdr_icon} {overall_label}</b> '
             f'<span style="color:{T["text_muted"]}">'
             f'(score {_score_s}/5 — {t("ai_insight.consensus")})</span>')

    # Breakdown 4 tầng
    line2 = (f'<b>{t("ai_insight.tier1")}</b> {primary_label}  &nbsp;·&nbsp;  '
             f'<b>{t("ai_insight.tier2")}</b> {trading_label}')
    line3 = (f'<b>{t("ai_insight.tier3")}</b> {chikou_label}  &nbsp;·&nbsp;  '
             f'<b>{t("ai_insight.tier4")}</b> {future_label}')

    # Dự báo
    _pct_color = T['success'] if next_pct >= 0 else T['danger']
    _arr       = '▲' if next_pct >= 0 else '▼'
    line4 = (f'{t("ai_insight.best_model")} <b>{best_model}</b> '
             f'(MAPE test {best_mape:.2f}% · R²adj {best_r2adj:.4f})')
    line5 = (f'{t("ai_insight.forecast")} <b>{next_date}</b>: '
             f'<b>{next_price*1000:,.0f} đ</b> '
             f'<span style="color:{_pct_color};font-weight:700">{_arr} {abs(next_pct):.2f}%</span>')

    # Disclaimer học thuật
    line6 = (f'<span style="color:{T["text_muted"]};font-style:italic">'
             f'{t("ai_insight.disclaimer")}</span>')

    body = '<br>'.join([line1, line2, line3, line4, line5, line6])

    return (
        f'<div style="background:linear-gradient(135deg,{T["accent"]}12 0%,rgba(168,85,247,.08) 100%);'
        f'border:1px solid {T["border"]};border-left:4px solid {hdr_color};'
        f'border-radius:14px;padding:18px 20px;margin:16px 0">'
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">'
        f'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{hdr_color}" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        f'<rect x="3" y="11" width="18" height="10" rx="2"/>'
        f'<circle cx="12" cy="5" r="2"/><path d="M12 7v4"/>'
        f'<line x1="8" y1="16" x2="8.01" y2="16"/><line x1="16" y1="16" x2="16.01" y2="16"/>'
        f'</svg>'
        f'<span style="font-size:11px;color:{hdr_color};font-weight:800;letter-spacing:1px;text-transform:uppercase">'
        f'{t("ai_insight.header")}</span>'
        f'</div>'
        f'<div style="color:{T["text_primary"]};font-size:13px;line-height:1.9">{body}</div>'
        f'</div>'
    )


def render_training_overlay(title: str, subtitle: str, step: int, total: int,
                            current_task: str, T: dict) -> str:
    """Fullscreen TOTAL BLOCK overlay khi đang training mô hình.

    Block TRIỆT ĐỂ:
    - position:fixed + inset:0 + z-index max → che mọi thứ, kể cả sidebar
    - backdrop blur + opaque bg → KHÔNG thấy UI cũ phía dưới
    - pointer-events:all + body.overflow:hidden → user không interact được
    - inline <style> inject html/body rules → safe dù Streamlit chưa load xong CSS
    """
    _fg_s   = T['text_secondary']
    _muted  = T.get('text_muted', '#64748B')
    _bg     = T['bg_card']
    _border = T.get('border', '#E2E8F0')
    _accent = T.get('accent', '#1565C0')
    _is_dark = T.get('is_dark', False)

    # Backdrop gần như opaque → KHÔNG thấy content cũ (dù chỉ blur)
    _backdrop = ('rgba(15,23,42,0.96)' if _is_dark else 'rgba(248,250,252,0.96)')
    pct = int((step / max(1, total)) * 100)

    _bar_html = (
        f'<div style="background:{T.get("bg_elevated","#F1F5F9")};'
        f'height:8px;border-radius:4px;overflow:hidden;margin:18px 0 14px;'
        f'box-shadow:inset 0 1px 2px rgba(0,0,0,0.06)">'
        f'<div style="background:linear-gradient(90deg,{_accent} 0%,#7C3AED 100%);'
        f'width:{pct}%;height:100%;border-radius:4px;'
        f'box-shadow:0 0 8px {_accent}60;'
        f'transition:width 0.4s ease"></div>'
        f'</div>'
    )
    _spinner = (
        '<svg width="48" height="48" viewBox="0 0 24 24" fill="none" '
        'xmlns="http://www.w3.org/2000/svg" '
        'style="animation:tspin 0.85s linear infinite;display:block;margin:0 auto 20px">'
        f'<circle cx="12" cy="12" r="9" stroke="{_accent}22" stroke-width="2.5"/>'
        f'<path d="M21 12a9 9 0 0 1-9 9" stroke="{_accent}" stroke-width="2.5" '
        'stroke-linecap="round"/></svg>'
    )
    # Style injected vào html tag + animation keyframes + body scroll lock
    _inline_style = (
        '<style>'
        'html body{overflow:hidden !important;}'
        '[data-testid="stMain"],[data-testid="stSidebar"]{filter:blur(3px);pointer-events:none !important;}'
        '@keyframes tspin{to{transform:rotate(360deg)}}'
        '@keyframes tfade{from{opacity:0;transform:scale(0.96)}to{opacity:1;transform:scale(1)}}'
        '</style>'
    )
    return (
        f'{_inline_style}'
        f'<div class="training-fullscreen-overlay" '
        f'style="position:fixed;inset:0;z-index:2147483647;'
        f'display:flex;align-items:center;justify-content:center;'
        f'background:{_backdrop};'
        f'pointer-events:all;cursor:wait">'
        f'<div style="max-width:540px;width:90%;background:{_bg};'
        f'border:1px solid {_border};border-top:4px solid {_accent};'
        f'border-radius:16px;padding:36px 40px;'
        f'animation:tfade 0.25s cubic-bezier(0.16,1,0.3,1);'
        f'box-shadow:0 32px 80px rgba(0,0,0,0.32),0 12px 24px rgba(0,0,0,0.16)">'
        f'{_spinner}'
        f'<div style="text-align:center;font-size:15px;font-weight:800;'
        f'color:{_accent};letter-spacing:0.5px;text-transform:uppercase;'
        f'margin-bottom:8px">{title}</div>'
        f'<div style="text-align:center;font-size:13px;color:{_fg_s};'
        f'margin-bottom:4px">{subtitle}</div>'
        f'{_bar_html}'
        f'<div style="display:flex;justify-content:space-between;'
        f'font-size:11.5px;color:{_muted};font-family:monospace;'
        f'letter-spacing:0.3px">'
        f'<span>→ {current_task}</span>'
        f'<span style="color:{_accent};font-weight:700">{pct}%  ·  {step}/{total}</span>'
        f'</div>'
        f'</div></div>'
    )


def render_param_timeline(p: int, T: dict) -> str:
    """Mini SVG timeline: p past lags + NOW + 1-step-ahead forecast."""
    _fg     = T['text_primary']
    _muted  = T.get('text_muted', '#64748B')
    _accent = T.get('accent', '#1565C0')
    _past_c = '#6EA8D8'
    _fut_c  = '#E87258'

    if p <= 4:
        _past_lags = list(range(p, 0, -1))
    else:
        _past_lags = sorted(set([
            p,
            max(1, round(p * 0.75)),
            max(1, round(p * 0.50)),
            max(1, round(p * 0.25)),
        ]), reverse=True)

    _p_show = len(_past_lags)

    width   = 320
    height  = 72
    n_ticks = _p_show + 1 + 1
    x_pad   = 16
    x_step  = (width - 2 * x_pad) / max(1, n_ticks - 1)
    axis_y  = 36
    today_idx = _p_show

    svg_parts = [
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:block">',
        f'<line x1="{x_pad}" y1="{axis_y}" x2="{width - x_pad}" y2="{axis_y}" '
        f'stroke="{_muted}" stroke-width="1"/>',
    ]

    tick_positions = [x_pad + i * x_step for i in range(n_ticks)]

    if p > 0:
        x1 = tick_positions[0] - 6
        x2 = tick_positions[today_idx] + 6
        svg_parts += [
            f'<path d="M {x1} {axis_y-14} L {x1} {axis_y-22} '
            f'L {x2} {axis_y-22} L {x2} {axis_y-14}" '
            f'fill="none" stroke="{_past_c}" stroke-width="1.5"/>',
            f'<text x="{(x1+x2)/2}" y="{axis_y-26}" text-anchor="middle" '
            f'font-size="9" font-weight="700" fill="{_past_c}" '
            f'font-family="monospace" letter-spacing="0.5">p = {p}</text>',
        ]

    x1 = tick_positions[today_idx] + 6
    x2 = tick_positions[-1] + 6
    svg_parts += [
        f'<path d="M {x1} {axis_y+14} L {x1} {axis_y+22} '
        f'L {x2} {axis_y+22} L {x2} {axis_y+14}" '
        f'fill="none" stroke="{_fut_c}" stroke-width="1.5"/>',
        f'<text x="{(x1+x2)/2}" y="{axis_y+33}" text-anchor="middle" '
        f'font-size="9" font-weight="700" fill="{_fut_c}" '
        f'font-family="monospace" letter-spacing="0.5">NEXT</text>',
    ]

    for i, lag in enumerate(_past_lags):
        x = tick_positions[i]
        is_furthest = (lag == p)
        svg_parts += [
            f'<circle cx="{x}" cy="{axis_y}" r="{4 if is_furthest else 3}" '
            f'fill="{_past_c}" stroke="white" stroke-width="1.5"/>',
            f'<text x="{x}" y="{axis_y+50}" text-anchor="middle" '
            f'font-size="9" fill="{_fg}" font-family="monospace" '
            f'font-weight="{700 if is_furthest else 500}">t−{lag}</text>',
        ]

    x_now = tick_positions[today_idx]
    svg_parts += [
        f'<circle cx="{x_now}" cy="{axis_y}" r="5" fill="{_accent}" stroke="white" stroke-width="1.5"/>',
        f'<text x="{x_now}" y="{axis_y+50}" text-anchor="middle" '
        f'font-size="9" fill="{_fg}" font-family="monospace" font-weight="700">t</text>',
        f'<text x="{x_now}" y="{axis_y+62}" text-anchor="middle" '
        f'font-size="7" fill="{_accent}" font-family="monospace" '
        f'font-weight="700" letter-spacing="1">NOW</text>',
    ]

    x_next = tick_positions[-1]
    svg_parts += [
        f'<circle cx="{x_next}" cy="{axis_y}" r="4" '
        f'fill="{_fut_c}" stroke="white" stroke-width="1.5"/>',
        f'<text x="{x_next}" y="{axis_y+50}" text-anchor="middle" '
        f'font-size="9" fill="{_fg}" font-family="monospace" font-weight="700">t+1</text>',
    ]

    svg_parts.append('</svg>')
    return ''.join(svg_parts)


def render_param_badge(p: int, T: dict) -> str:
    """Pill badge showing current p value."""
    _fg     = T['text_primary']
    _muted  = T.get('text_muted', '#64748B')
    _bg_elv = T.get('bg_elevated', '#F1F5F9')
    _border = T.get('border', '#E2E8F0')
    _past_c = '#6EA8D8'

    return (
        f'<span style="display:inline-flex;align-items:center;gap:6px;'
        f'padding:4px 12px;border-radius:12px;background:{_bg_elv};'
        f'border:1px solid {_border};font-family:monospace;font-size:12px">'
        f'<span style="width:8px;height:8px;border-radius:50%;'
        f'background:{_past_c}"></span>'
        f'<span style="color:{_muted};font-weight:600">p =</span>'
        f'<span style="color:{_fg};font-weight:800;letter-spacing:0.3px">{p}</span>'
        f'</span>'
    )
