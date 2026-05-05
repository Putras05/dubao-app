import streamlit as st
import warnings
import matplotlib
matplotlib.use('Agg')
warnings.filterwarnings('ignore')

from core.config import PAGE_TITLE, PAGE_ICON, LAYOUT, SIDEBAR_STATE
from core.themes import theme
from core.i18n import t
from data.fetcher import fetch_data
from data.metrics import calc_metrics
from models.ar   import run_ar
from models.mlr  import run_mlr
from models.cart import run_cart
from core.validate import validate_params
from ui.css import inject_global_css, inject_theme_css
from ui.js import inject_theme_js, force_sidebar_open_js, hide_streamlit_badges_js
from ui.sidebar import render_sidebar

import app_pages.dashboard  as _pg_dash
import app_pages.analysis   as _pg_ana
import app_pages.history    as _pg_hist
import app_pages.signals    as _pg_sig
import app_pages.portfolio  as _pg_port
import app_pages.guide      as _pg_guide

st.set_page_config(
    page_title=PAGE_TITLE,
    layout=LAYOUT,
    initial_sidebar_state=SIDEBAR_STATE,
    page_icon=PAGE_ICON,
)

if 'theme_mode' not in st.session_state:
    st.session_state['theme_mode'] = 'light'
if 'lang' not in st.session_state:
    st.session_state['lang'] = 'VI'

_T = theme()

# CSS/JS phải inject MỖI rerun — Streamlit garbage-collect các st.markdown
# element không re-render → gating bằng session_state làm sidebar dark blue
# biến mất sau rerun đầu. Trade-off: chấp nhận chi phí websocket.
inject_global_css()
inject_theme_css(_T)
inject_theme_js(_T)
force_sidebar_open_js()
hide_streamlit_badges_js()

# ẨN UI CHUẨN: dùng config.toml với toolbarMode="minimal" (đã set ở .streamlit/config.toml)
# → Manage app button, hamburger menu, header bị ẩn CHÍNH THỨC (không cần CSS hack)
# Badge "Hosted with Streamlit" — branding bắt buộc của Streamlit free tier,
# không có cách technical nào ẩn 100% (các hack CSS/JS hoạt động không ổn định).
st.markdown("""
<style>
    [class*="viewerBadge"], [class*="ViewerBadge"],
    [class*="_profileContainer_"], [class*="profileContainer"],
    [data-testid="stDecoration"],
    [data-testid="stToolbar"],
    [data-testid="stStatusWidget"],
    [data-testid*="manage-app"],
    .stDeployButton, .stAppDeployButton,
    a[href*="share.streamlit.io"]:not([href*="docs"]),
    #MainMenu {
        display: none !important;
        visibility: hidden !important;
    }
</style>
""", unsafe_allow_html=True)

# Splash/cover page: chỉ hiện 1 lần khi user vào app, click "Vào Ngay" để đến main app
if not st.session_state.get('_splash_done'):
    from app_pages import splash as _pg_splash
    _pg_splash.render()
    st.stop()

# Preload 3 tickers 1 lần duy nhất mỗi session → UX mượt hơn
from core.preload import preload_all_tickers, trigger_bg_cart
preload_all_tickers()

page, ticker, train_ratio, date_from, date_to, ar_order = render_sidebar()

# ── Validate tham số AR order trước khi train ─────
_df_for_validate = fetch_data(ticker, date_from, date_to)
_n_total = len(_df_for_validate)
_valid   = validate_params(ar_order, _n_total, train_ratio)

if _valid['overall'] == 'err':
    _err_html = (
        f'<div style="background:#FEE2E2;border:2px solid #DC2626;'
        f'border-radius:12px;padding:24px 28px;margin:20px 0">'
        f'<div style="font-size:14px;font-weight:800;color:#991B1B;'
        f'letter-spacing:1px;text-transform:uppercase;margin-bottom:10px">'
        f'{t("validate.blocked")}</div>'
        f'<div style="font-size:13px;color:#7F1D1D;'
        f'margin-bottom:6px;font-family:monospace">'
        f'{_valid["p_msg"]}</div>'
        f'</div>'
    )
    st.markdown(_err_html, unsafe_allow_html=True)
    st.stop()
elif _valid['overall'] == 'warn':
    st.warning(_valid['p_msg'])

_cache_key = f"{ticker}_{train_ratio:.3f}_{date_from}_{date_to}_p{ar_order}"
_need_reload = (
    '_data_cache_key' not in st.session_state or
    st.session_state._data_cache_key != _cache_key
)

if _need_reload:
    # Invalidate PDF cache khi data đổi → user sẽ thấy button "Xuất PDF" lại
    st.session_state.pop('_pdf_bytes', None)

    from ui.components import render_training_overlay
    import time as _time

    _prog_ph  = st.empty()
    _title    = 'Đang huấn luyện mô hình' if st.session_state.get('lang', 'VI') == 'VI' \
                else 'Training models'
    _subtitle = f'{ticker} · Train ratio {int(train_ratio*100)}% · p={ar_order}'

    def _show(step, total, task):
        _prog_ph.markdown(
            render_training_overlay(_title, _subtitle, step, total, task, _T),
            unsafe_allow_html=True)

    _show(0, 5, t('load.market'))
    df = fetch_data(ticker, date_from, date_to)

    _show(1, 5, t('load.ar1') + f' · AR({ar_order})')
    r1 = run_ar(ticker, train_ratio, p=ar_order,
                date_from=date_from, date_to=date_to)

    _show(2, 5, t('load.mlr') + f' · MLR({ar_order})')
    r2 = run_mlr(ticker, train_ratio, p=ar_order,
                 date_from=date_from, date_to=date_to)

    _show(3, 5, t('load.cart') + f' · CART({ar_order})')
    r3 = run_cart(ticker, train_ratio, p=ar_order,
                  date_from=date_from, date_to=date_to)

    _show(4, 5, t('load.metrics'))
    m1 = calc_metrics(r1['yte'], r1['pte'], k=ar_order)
    m2 = calc_metrics(r2['yte'], r2['pte'], k=3 * ar_order)
    m3 = calc_metrics(r3['yte'], r3['pte'], k=6 * ar_order)

    _show(5, 5, 'Done.')
    _time.sleep(0.3)
    _prog_ph.empty()
    st.session_state._data_cache_key = _cache_key
    st.session_state._df = df
    st.session_state._r1 = r1
    st.session_state._r2 = r2
    st.session_state._r3 = r3
    st.session_state._m1 = m1
    st.session_state._m2 = m2
    st.session_state._m3 = m3

    # Lần đầu load xong → rerun 1 lần duy nhất để sidebar tái render với
    # session_state đầy đủ → nút "Xuất PDF" hiện ngay không phải đợi
    # user click đi tab khác.
    if not st.session_state.get('_first_load_done'):
        st.session_state['_first_load_done'] = True
        trigger_bg_cart(ticker, ar_order, date_from, date_to)
        st.rerun()

    trigger_bg_cart(ticker, ar_order, date_from, date_to)
else:
    df = st.session_state._df
    r1 = st.session_state._r1
    r2 = st.session_state._r2
    r3 = st.session_state._r3
    m1 = st.session_state._m1
    m2 = st.session_state._m2
    m3 = st.session_state._m3

_args = (ticker, train_ratio, date_from, date_to, df, r1, r2, r3, m1, m2, m3, _T,
         ar_order)

if   page == 'Dashboard Tổng quan':   _pg_dash.render(*_args)
elif page == 'Phân tích Chi tiết':    _pg_ana.render(*_args)
elif page == 'Lịch sử & Dữ liệu':    _pg_hist.render(*_args)
elif page == 'Tín hiệu & Cảnh báo':  _pg_sig.render(*_args)
elif page == 'Danh mục Đầu tư':      _pg_port.render(*_args)
elif page == 'Hướng dẫn Sử dụng':    _pg_guide.render(*_args)
elif page == 'Trợ lý AI':
    from app_pages import chatbot as _pg_chatbot
    _pg_chatbot.render(*_args)
