import streamlit as st
import base64
from pathlib import Path


def _img_b64(filename: str) -> str:
    """Đọc ảnh từ static/ và encode base64."""
    p = Path(__file__).resolve().parent.parent / 'static' / filename
    if not p.exists():
        return ''
    return base64.b64encode(p.read_bytes()).decode()


def render():
    """Splash page — light theme. Avoids Streamlit's 4-space-indent
    code-block trap by joining HTML parts WITHOUT leading whitespace."""

    tdt_b64 = _img_b64('TDT_logo.png')
    khoa_b64 = _img_b64('khoa_logo.png')

    # ── CSS — raw triple-string, no f-string, no indent traps ──
    css = """<style>
[data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
html body .stApp, html body [data-testid="stAppViewContainer"], html body [data-testid="stMain"], html body section.main {
background: radial-gradient(ellipse at 20% 0%, rgba(59,130,246,0.08) 0, transparent 55%), radial-gradient(ellipse at 80% 100%, rgba(30,64,175,0.06) 0, transparent 60%), linear-gradient(165deg, #FFFFFF 0%, #F8FAFC 50%, #F1F5F9 100%) !important;
background-attachment: fixed !important;
min-height: 100vh !important;
}
[data-testid="stHeader"] { background: transparent !important; box-shadow: none !important; }
.main .block-container { padding-top: 1.5rem !important; max-width: 920px !important; background: transparent !important; }
[data-testid="stAppViewContainer"]::before, .stApp::before {
content: ''; position: fixed; inset: 0; pointer-events: none; z-index: 0;
background-image: linear-gradient(rgba(30,64,175,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(30,64,175,0.04) 1px, transparent 1px);
background-size: 48px 48px;
mask-image: radial-gradient(ellipse at center, black 30%, transparent 75%);
-webkit-mask-image: radial-gradient(ellipse at center, black 30%, transparent 75%);
}
.splash-wrap { position: relative; z-index: 10; max-width: 880px; margin: 0 auto; padding: 24px 32px 16px; text-align: center; animation: splash-fade-in 0.8s ease-out; }
@keyframes splash-fade-in { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
.splash-logos { display: flex; justify-content: center; align-items: center; gap: 56px; margin-bottom: 24px; flex-wrap: wrap; }
.splash-logos img { height: 92px; width: auto; filter: drop-shadow(0 6px 16px rgba(30,64,175,0.15)); }
.splash-univ { text-align: center; flex: 0 1 320px; min-width: 240px; }
.splash-univ .name { display: block; font-weight: 800; color: #1E40AF !important; font-size: 17px; line-height: 1.4; letter-spacing: 0.6px; }
.splash-univ .faculty { display: inline-block; margin-top: 8px; padding: 6px 18px; font-size: 12px; font-weight: 700; color: #1E40AF !important; letter-spacing: 2px; background: rgba(59,130,246,0.10); border: 1px solid rgba(59,130,246,0.30); border-radius: 999px; }
.splash-badge { display: inline-block; margin: 18px 0 14px; padding: 7px 20px; font-size: 11px; font-weight: 700; color: #475569 !important; letter-spacing: 2.2px; text-transform: uppercase; background: rgba(241,245,249,0.7); border-top: 1px solid rgba(148,163,184,0.30); border-bottom: 1px solid rgba(148,163,184,0.30); }
.splash-title { font-family: 'Cambria','Times New Roman', Georgia, serif; font-weight: 700; color: #0F172A !important; font-size: 30px; line-height: 1.35; margin: 14px 0 6px; letter-spacing: 0.4px; }
.splash-title-accent { color: #1E40AF !important; font-style: italic; }
.splash-sep { display: block; width: 80px; height: 3px; margin: 18px auto 24px; background: linear-gradient(90deg, transparent, #1E40AF, transparent); border-radius: 2px; }
.splash-card { background: #FFFFFF !important; border: 1px solid rgba(148,163,184,0.25); border-left: 4px solid #1E40AF; border-radius: 12px; padding: 20px 28px; margin: 14px auto; max-width: 600px; box-shadow: 0 4px 14px rgba(15,23,42,0.06), 0 1px 3px rgba(15,23,42,0.04); text-align: left; position: relative; z-index: 5; }
.splash-card .label { display: block; font-size: 10.5px; font-weight: 800; color: #1E40AF !important; text-transform: uppercase; letter-spacing: 2.2px; margin-bottom: 10px; }
.splash-card .value { font-size: 15px; color: #0F172A !important; font-weight: 600; line-height: 1.85; }
.splash-card .value .author-id { color: #64748B !important; font-weight: 500; font-size: 13.5px; margin-left: 6px; }
div[data-testid="stButton"] { display: flex; justify-content: center; margin: 32px auto 12px; position: relative; z-index: 5; }
div[data-testid="stButton"] > button { background: linear-gradient(135deg, #1E40AF 0%, #3B82F6 100%) !important; color: #FFFFFF !important; font-weight: 800 !important; font-size: 15px !important; padding: 14px 44px !important; border-radius: 999px !important; border: none !important; letter-spacing: 2.5px !important; box-shadow: 0 6px 20px rgba(30,64,175,0.35), inset 0 1px 0 rgba(255,255,255,0.20) !important; transition: transform 0.2s ease, box-shadow 0.2s ease !important; min-width: 220px; }
div[data-testid="stButton"] > button:hover { transform: translateY(-3px) scale(1.02); box-shadow: 0 12px 28px rgba(30,64,175,0.50) !important; }
.splash-footer { margin-top: 18px; font-size: 11px; color: #94A3B8 !important; letter-spacing: 1.6px; text-transform: uppercase; position: relative; z-index: 5; text-align: center; }
.splash-footer .dot { color: #CBD5E1; margin: 0 10px; }
</style>"""

    st.markdown(css, unsafe_allow_html=True)

    # ── HTML — list-join trick: ghép thành 1 string KHÔNG có \n đầu / indent
    # → Streamlit's CommonMark KHÔNG nhầm thành <pre><code>.
    html_parts = [
        '<div class="splash-wrap">',
        '<div class="splash-logos">',
        f'<img src="data:image/png;base64,{tdt_b64}" alt="TDTU"/>',
        '<div class="splash-univ">',
        '<span class="name">TRƯỜNG ĐẠI HỌC TÔN ĐỨC THẮNG</span>',
        '<br/>',
        '<span class="faculty">KHOA TOÁN — THỐNG KÊ</span>',
        '</div>',
        f'<img src="data:image/png;base64,{khoa_b64}" alt="Faculty"/>',
        '</div>',
        '<div class="splash-badge">Công trình Nghiên cứu khoa học sinh viên · 2025–2026</div>',
        '<div class="splash-title">',
        'XÂY DỰNG <span class="splash-title-accent">CHATBOT</span><br/>',
        'PHÂN TÍCH VÀ DỰ BÁO CHỨNG KHOÁN<br/>',
        'DỰA TRÊN MÔ HÌNH THỐNG KÊ VÀ HỌC MÁY',
        '</div>',
        '<span class="splash-sep"></span>',
        '<div class="splash-card">',
        '<span class="label">Giảng viên hướng dẫn</span>',
        '<div class="value">ThS. Chế Ngọc Hà</div>',
        '</div>',
        '<div class="splash-card">',
        '<span class="label">Nhóm tác giả</span>',
        '<div class="value">',
        'Nguyễn Thành Danh<span class="author-id">— C2300014</span><br/>',
        'Nguyễn Nhật Anh Huy<span class="author-id">— C2200153</span><br/>',
        'Mai Phan Vũ<span class="author-id">— C2200141</span>',
        '</div>',
        '</div>',
        '</div>',
    ]
    logo_html = ''.join(html_parts)
    st.markdown(logo_html, unsafe_allow_html=True)

    if st.button('VÀO NGAY', key='splash_enter'):
        st.session_state['_splash_done'] = True
        st.rerun()

    footer_html = (
        '<div class="splash-footer">'
        'TDTU <span class="dot">·</span> NCKH 2026 '
        '<span class="dot">·</span> HOSE Stock Forecasting'
        '</div>'
    )
    st.markdown(footer_html, unsafe_allow_html=True)
