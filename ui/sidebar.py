import streamlit as st
import datetime as _dt
from streamlit_option_menu import option_menu

from core.constants import TICKERS
from core.i18n import t


_PAGE_KEYS = [
    'Dashboard Tổng quan', 'Phân tích Chi tiết', 'Lịch sử & Dữ liệu',
    'Tín hiệu & Cảnh báo', 'Danh mục Đầu tư', 'Hướng dẫn Sử dụng',
    'Trợ lý AI',
]
_NAV_BOOTSTRAP_ICONS = [
    'speedometer2', 'graph-up-arrow', 'clock-history', 'activity', 'briefcase',
    'book-half', 'chat-dots',
]


def render_sidebar() -> tuple:
    """Render sidebar. Returns:
    (page_key, ticker, train_ratio, date_from, date_to, ar_order)
    """
    _PAGE_NAV_LABELS = [
        t('nav.dashboard'), t('nav.analysis'), t('nav.history'),
        t('nav.signals'),   t('nav.portfolio'), t('nav.guide'),
        t('nav.chatbot'),
    ]

    with st.sidebar:
        st.markdown(
            f"<div style='text-align:center;padding:20px 0 16px'>"
            f"<div style='font-size:15px;font-weight:800;color:#FFFFFF;"
            f"letter-spacing:0.5px'>{t('app.title')}</div>"
            f"<div style='font-size:10px;font-weight:600;color:rgba(191,219,254,0.75);"
            f"letter-spacing:1px;margin-top:5px;text-transform:uppercase'>NCKH TDTU 2026</div>"
            f"</div>", unsafe_allow_html=True)
        st.markdown("<hr style='border-color:rgba(255,255,255,0.12);margin:0 0 6px'/>",
                    unsafe_allow_html=True)

        if '_page_key' not in st.session_state:
            st.session_state['_page_key'] = 'Dashboard Tổng quan'
        _cur_idx = _PAGE_KEYS.index(st.session_state['_page_key']) \
                   if st.session_state['_page_key'] in _PAGE_KEYS else 0

        if st.session_state.get('_option_menu_nav') not in _PAGE_NAV_LABELS:
            st.session_state['_option_menu_nav'] = _PAGE_NAV_LABELS[_cur_idx]

        _nav_sel_idx = option_menu(
            menu_title=None,
            options=_PAGE_NAV_LABELS,
            icons=_NAV_BOOTSTRAP_ICONS,
            default_index=_cur_idx,
            styles={
                'container': {
                    'padding': '0',
                    'background-color': 'transparent',
                },
                'nav-link': {
                    'font-size': '12px',
                    'font-weight': '500',
                    'color': '#D0E0F5',
                    'padding': '8px 12px',
                    'border-radius': '8px',
                    'border-left': '3px solid transparent',
                    'margin': '1px 0',
                    'white-space': 'nowrap',
                    'background-color': 'transparent',
                },
                'nav-link-selected': {
                    'font-weight': '700',
                    'color': '#FFFFFF',
                    'background-color': 'rgba(255,255,255,0.12)',
                    'border-left': '3px solid #7AA4D4',
                },
                'icon': {
                    'color': '#7AA4D4',
                    'font-size': '15px',
                },
            },
            key='_option_menu_nav',
        )
        page = _PAGE_KEYS[_PAGE_NAV_LABELS.index(_nav_sel_idx)]
        st.session_state['_page_key'] = page

        st.markdown("<hr style='border-color:rgba(255,255,255,0.12);margin:6px 0 10px'/>",
                    unsafe_allow_html=True)

        st.markdown(f"<div style='font-size:10px;font-weight:700;letter-spacing:1px;"
                    f"text-transform:uppercase;color:rgba(191,219,254,0.75);margin-bottom:4px'>"
                    f"{t('sidebar.ticker')}</div>",
                    unsafe_allow_html=True)
        ticker = st.selectbox('Ticker', TICKERS, label_visibility='collapsed')

        st.markdown(f"<div style='font-size:10px;font-weight:700;letter-spacing:1px;"
                    f"text-transform:uppercase;color:rgba(191,219,254,0.75);margin:8px 0 4px'>"
                    f"{t('sidebar.train_ratio')}</div>",
                    unsafe_allow_html=True)
        train_ratio = st.slider('Train Ratio', 70, 90, 80, step=5, format='%d%%',
                                label_visibility='collapsed') / 100

        # ── AR Order (p) ──────────────────────────────────────────────
        st.markdown(f"<div style='font-size:10px;font-weight:700;letter-spacing:1px;"
                    f"text-transform:uppercase;color:rgba(191,219,254,0.75);margin:10px 0 4px'>"
                    f"{t('sidebar.ar_order')}</div>",
                    unsafe_allow_html=True)
        if 'sb_ar_order' not in st.session_state:
            st.session_state['sb_ar_order'] = 1
        ar_order = st.number_input(
            'AR Order', min_value=1, max_value=100, value=st.session_state['sb_ar_order'],
            step=1, key='sb_ar_order', label_visibility='collapsed',
            help=t('sidebar.ar_order_help'),
        )

        st.markdown("<hr style='border-color:rgba(255,255,255,0.12);margin:10px 0'/>",
                    unsafe_allow_html=True)

        st.markdown(f"<div style='font-size:10px;font-weight:700;letter-spacing:1px;"
                    f"text-transform:uppercase;color:rgba(191,219,254,0.75);margin-bottom:4px'>"
                    f"{t('sidebar.date_range')}</div>",
                    unsafe_allow_html=True)
        _today = _dt.date.today()
        if 'sb_date_from' not in st.session_state:
            st.session_state['sb_date_from'] = _dt.date(2016, 1, 1)
        if 'sb_date_to' not in st.session_state:
            st.session_state['sb_date_to'] = _today
        date_from = st.date_input(t('sidebar.from'), key='sb_date_from',
                                   format='YYYY/MM/DD', label_visibility='visible')
        date_to   = st.date_input(t('sidebar.to'), key='sb_date_to',
                                   format='YYYY/MM/DD', label_visibility='visible')

        st.markdown("<hr style='border-color:rgba(255,255,255,0.12);margin:10px 0'/>",
                    unsafe_allow_html=True)

        st.markdown('<div class="btn-refresh">', unsafe_allow_html=True)
        if st.button(t('common.refresh'), use_container_width=True):
            for _k in ['_data_cache_key', '_df', '_r1', '_r2', '_r3', '_m1', '_m2', '_m3']:
                st.session_state.pop(_k, None)
            try:
                st.cache_data.clear()
            except Exception:
                pass
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # ── PDF Export — chỉ hiện khi data đã train xong ──────────────
        _sb_is_en = st.session_state.get('lang', 'VI') == 'EN'
        if all(k in st.session_state for k in ('_df', '_r1', '_r2', '_r3', '_m1', '_m2', '_m3')):
            _pdf_label = 'Xuất báo cáo PDF' if not _sb_is_en else 'Export PDF Report'
            _pdf_help = ('Sinh báo cáo đầy đủ 10 trang A4 (cover · TOC · 3 mô hình · '
                         'CART tree · Ichimoku · metrics)' if not _sb_is_en else
                         'Generate a full 10-page A4 report (cover · TOC · 3 models · '
                         'CART tree · Ichimoku · metrics)')
            if st.session_state.get('_pdf_bytes') is None:
                if st.button(f'⤓  {_pdf_label}',
                             key='btn_pdf', use_container_width=True,
                             help=_pdf_help):
                    try:
                        from core.pdf_report import generate_pdf_report
                        _spin_msg = ('Đang tạo PDF...' if not _sb_is_en
                                     else 'Generating PDF...')
                        with st.spinner(_spin_msg):
                            _pdf_bytes = generate_pdf_report(
                                ticker=ticker,
                                df=st.session_state._df,
                                r1=st.session_state._r1,
                                r2=st.session_state._r2,
                                r3=st.session_state._r3,
                                m1=st.session_state._m1,
                                m2=st.session_state._m2,
                                m3=st.session_state._m3,
                                ar_order=int(ar_order),
                                ichi=st.session_state.get('ichimoku_summary'),
                                lang=st.session_state.get('lang', 'VI'),
                            )
                            st.session_state['_pdf_bytes'] = _pdf_bytes
                        st.rerun()
                    except Exception as _pdf_err:
                        _err_prefix = ('Lỗi tạo PDF: ' if not _sb_is_en
                                       else 'PDF generation error: ')
                        st.error(f'{_err_prefix}{str(_pdf_err)[:200]}')
            else:
                # Filename theo lang: BaoCao_* (VI) / Report_* (EN)
                _fname_prefix = 'BaoCao' if not _sb_is_en else 'Report'
                _fname = f'{_fname_prefix}_{ticker}_{_dt.datetime.now().strftime("%Y%m%d_%H%M")}.pdf'
                _dl_label = ('⬇  Tải báo cáo PDF' if not _sb_is_en
                             else '⬇  Download PDF Report')
                st.download_button(
                    label=_dl_label,
                    data=st.session_state['_pdf_bytes'],
                    file_name=_fname,
                    mime='application/pdf',
                    key='btn_pdf_dl',
                    use_container_width=True,
                )
                # Cho phép tạo lại PDF mới
                _regen_label = ('↻ Tạo PDF mới' if not _sb_is_en
                                else '↻ Generate new PDF')
                if st.button(_regen_label, key='btn_pdf_regen',
                             use_container_width=True):
                    st.session_state['_pdf_bytes'] = None
                    st.rerun()

        st.markdown("<hr style='border-color:rgba(255,255,255,0.12);margin:10px 0'/>",
                    unsafe_allow_html=True)
        _tc1, _tc2 = st.columns(2)
        with _tc1:
            _is_dark = st.session_state.get('theme_mode', 'light') == 'dark'
            if st.button('Light' if _is_dark else 'Dark',
                         use_container_width=True, key='btn_dark'):
                st.session_state.theme_mode = 'light' if _is_dark else 'dark'
                st.rerun()
        with _tc2:
            _is_en = st.session_state.get('lang', 'VI') == 'EN'
            if st.button('VI' if _is_en else 'EN',
                         use_container_width=True, key='btn_lang'):
                st.session_state.lang = 'VI' if _is_en else 'EN'
                # Invalidate PDF cache vì nội dung PDF bilingual → cần regen
                # theo ngôn ngữ mới sau khi user switch VI↔EN
                st.session_state.pop('_pdf_bytes', None)
                st.rerun()

        st.markdown(
            "<div style='font-size:10px;color:rgba(191,219,254,0.55);text-align:center;margin-top:14px'>"
            "TDTU · NCKH 2026</div>", unsafe_allow_html=True)

    return page, ticker, train_ratio, date_from, date_to, int(ar_order)
