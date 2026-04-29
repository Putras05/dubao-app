import streamlit as st
import matplotlib.pyplot as plt
import colorsys

THEMES = {
    'light': {
        'bg_app':          '#F8FAFC',
        'bg_sidebar':      '#FFFFFF',
        'bg_card':         '#FFFFFF',
        'bg_elevated':     '#F1F5F9',
        'bg_chart':        '#FFFFFF',
        'text_primary':    '#0F172A',
        'text_secondary':  '#475569',
        'text_muted':      '#94A3B8',
        'border':          '#E2E8F0',
        'border_strong':   '#CBD5E1',
        'divider':         '#F1F5F9',
        'accent':          '#1565C0',
        'accent_hover':    '#0D47A1',
        'nav_active_bg':   '#DBEAFE',
        'nav_active_text': '#1E40AF',
        'banner_bg':       'linear-gradient(135deg,#0D1F4A 0%,#1B3D8C 60%,#2756C0 100%)',
        'banner_text':     '#FFFFFF',
        'banner_subtext':  '#BFDBFE',
        'success':         '#059669',
        'success_bg':      '#D1FAE5',
        'danger':          '#DC2626',
        'danger_bg':       '#FEE2E2',
        'warning':         '#D97706',
        'warning_bg':      '#FEF3C7',
        'grad_ar':         'linear-gradient(135deg,#EFF6FF 0%,#DBEAFE 100%)',
        'grad_mlr':        'linear-gradient(135deg,#FAF5FF 0%,#F3E8FF 100%)',
        'grad_cart':       'linear-gradient(135deg,#F0FDF4 0%,#DCFCE7 100%)',
        'grid':            'rgba(15,23,42,0.06)',
        'actual_line':     '#0F172A',
        'ar_line':         '#2563EB',
        'mlr_line':        '#9333EA',
        'dt_line':         '#059669',
        'shadow_sm':       '0 1px 2px rgba(15,23,42,0.05)',
        'shadow_md':       '0 4px 12px rgba(15,23,42,0.08)',
        'shadow_lg':       '0 8px 24px rgba(15,23,42,0.12)',
        'hover_bg':        '#F1F5F9',
        'shadow':          'rgba(15,23,42,0.08)',
    },
    'dark': {
        'bg_app':          '#0F172A',
        'bg_sidebar':      '#1E293B',
        'bg_card':         '#1E293B',
        'bg_elevated':     '#334155',
        'bg_chart':        '#1E293B',
        'text_primary':    '#F1F5F9',
        'text_secondary':  '#CBD5E1',
        'text_muted':      '#94A3B8',
        'border':          '#334155',
        'border_strong':   '#475569',
        'divider':         '#1E293B',
        'accent':          '#60A5FA',
        'accent_hover':    '#93C5FD',
        'nav_active_bg':   'rgba(96,165,250,0.15)',
        'nav_active_text': '#93C5FD',
        'banner_bg':       'linear-gradient(135deg,#1E3A8A 0%,#1E40AF 60%,#2563EB 100%)',
        'banner_text':     '#F1F5F9',
        'banner_subtext':  '#93C5FD',
        'success':         '#34D399',
        'success_bg':      'rgba(52,211,153,0.15)',
        'danger':          '#F87171',
        'danger_bg':       'rgba(248,113,113,0.15)',
        'warning':         '#FBBF24',
        'warning_bg':      'rgba(251,191,36,0.15)',
        'grad_ar':         'linear-gradient(135deg,rgba(37,99,235,0.18) 0%,rgba(37,99,235,0.06) 100%)',
        'grad_mlr':        'linear-gradient(135deg,rgba(147,51,234,0.18) 0%,rgba(147,51,234,0.06) 100%)',
        'grad_cart':       'linear-gradient(135deg,rgba(5,150,105,0.18) 0%,rgba(5,150,105,0.06) 100%)',
        'grid':            'rgba(241,245,249,0.08)',
        'actual_line':     '#F1F5F9',
        'ar_line':         '#60A5FA',
        'mlr_line':        '#C084FC',
        'dt_line':         '#34D399',
        'shadow_sm':       '0 1px 2px rgba(0,0,0,0.30)',
        'shadow_md':       '0 4px 12px rgba(0,0,0,0.40)',
        'shadow_lg':       '0 8px 24px rgba(0,0,0,0.50)',
        'hover_bg':        '#334155',
        'shadow':          'rgba(0,0,0,0.40)',
    },
}


_THEME_CACHE: dict = {}
_THEME_LOCK = __import__('threading').Lock()


def theme() -> dict:
    """Trả theme dict — cùng id() giữa các rerun để @st.cache_data hash stable.

    `THEMES[mode].copy()` trước đây trả NEW dict mỗi lần gọi → mọi
    `@st.cache_data` nhận T làm arg đều miss cache mỗi rerun. Cache theo mode
    để giữ same object ref. `_THEME_LOCK` bảo vệ dict mutation cho trường hợp
    helper từ ThreadPoolExecutor (vd portfolio model load) gọi `theme()`.
    """
    mode = st.session_state.get('theme_mode', 'light')
    cached = _THEME_CACHE.get(mode)
    if cached is not None:
        return cached
    with _THEME_LOCK:
        cached = _THEME_CACHE.get(mode)
        if cached is None:
            d = THEMES[mode].copy()
            d['is_dark'] = (mode == 'dark')
            _THEME_CACHE[mode] = d
            cached = d
    return cached


def lighten_color(hex_color: str, amount: float = 0.3) -> str:
    hex_color = hex_color.lstrip('#')
    r, g, b = (int(hex_color[i:i+2], 16) / 255 for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = min(1.0, l + amount)
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'


def set_mpl_theme(T: dict) -> None:
    if T.get('is_dark', False):
        plt.rcParams.update({
            'figure.facecolor':   '#0F1C33',
            'axes.facecolor':     '#0F1C33',
            'axes.edgecolor':     '#334155',
            'axes.labelcolor':    '#CBD5E1',
            'axes.titlecolor':    '#F1F5F9',
            'xtick.color':        '#94A3B8',
            'ytick.color':        '#94A3B8',
            'grid.color':         '#1E293B',
            'grid.alpha':         0.6,
            'text.color':         '#F1F5F9',
            'legend.facecolor':   '#1E293B',
            'legend.edgecolor':   '#334155',
            'legend.labelcolor':  '#F1F5F9',
            'savefig.facecolor':  '#0F1C33',
            'savefig.edgecolor':  '#0F1C33',
            'axes.spines.top':    False,
            'axes.spines.right':  False,
            'font.family':        'DejaVu Sans',
            'font.size':          10,
        })
    else:
        plt.rcParams.update({
            'figure.facecolor':   '#FFFFFF',
            'axes.facecolor':     '#FAFBFF',
            'axes.edgecolor':     '#DDE8F5',
            'axes.labelcolor':    '#556888',
            'axes.titlecolor':    '#1A2A4A',
            'xtick.color':        '#8090B0',
            'ytick.color':        '#8090B0',
            'grid.color':         '#E2E8F0',
            'grid.alpha':         0.35,
            'text.color':         '#1A2A4A',
            'legend.facecolor':   '#FFFFFF',
            'legend.edgecolor':   '#DDE8F5',
            'legend.labelcolor':  '#1A2A4A',
            'savefig.facecolor':  '#FFFFFF',
            'savefig.edgecolor':  '#FFFFFF',
            'axes.spines.top':    False,
            'axes.spines.right':  False,
            'font.family':        'DejaVu Sans',
            'font.size':          10,
        })
