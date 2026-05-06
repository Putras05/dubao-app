import streamlit as st
import base64
from pathlib import Path


def _img_b64(filename: str) -> str:
    """Đọc ảnh từ static/ và encode base64 để nhúng inline."""
    p = Path(__file__).resolve().parent.parent / 'static' / filename
    if not p.exists():
        return ''
    return base64.b64encode(p.read_bytes()).decode()


def render():
    """Splash/cover page — premium navy theme.

    Strategy: shotgun selectors (target every plausible Streamlit container)
    + body fallback + defensive card opacity + multi-layer text-shadow.
    Each layer is a defense against a different failure mode:
      - selector mismatch (Streamlit DOM differs across versions)
      - `.streamlit/config.toml` theme baking white into CSS variables
      - card text invisibility if everything else fails
    """

    tdt_b64 = _img_b64('TDT_logo.png')
    khoa_b64 = _img_b64('khoa_logo.png')

    st.markdown("""
<style>
    /* ═══════════════════════════════════════════════════════
       SPLASH PAGE — NAVY GRADIENT BACKGROUND
       Target every possible Streamlit container selector
       (Streamlit changes DOM between versions)
       ═══════════════════════════════════════════════════════ */

    /* Hide sidebar entirely on splash */
    [data-testid="stSidebar"],
    [data-testid="collapsedControl"],
    section[data-testid="stSidebar"] {
        display: none !important;
    }

    /* SHOTGUN: paint navy on every possible top-level Streamlit container */
    html body .stApp,
    html body [data-testid="stAppViewContainer"],
    html body [data-testid="stApp"],
    html body div[class*="appview-container"],
    html body div[class*="StyledApp"],
    html body section.main,
    html body [data-testid="stMain"] {
        background:
            radial-gradient(ellipse at 20% 0%, rgba(56,124,255,0.18) 0, transparent 55%),
            radial-gradient(ellipse at 80% 100%, rgba(30,64,175,0.32) 0, transparent 60%),
            linear-gradient(165deg, #060E26 0%, #0B1B45 40%, #0F2660 100%) !important;
        background-attachment: fixed !important;
        min-height: 100vh !important;
    }

    /* Body fallback — last line of defense */
    html, body {
        background: #060E26 !important;
        min-height: 100vh !important;
    }

    /* Header bar transparent so navy flows edge-to-edge */
    [data-testid="stHeader"],
    header[data-testid="stHeader"] {
        background: transparent !important;
        background-color: transparent !important;
        box-shadow: none !important;
    }

    /* Inner containers transparent so navy shows through */
    .stApp > .main,
    .main .block-container,
    [data-testid="stMain"] .block-container,
    [data-testid="block-container"],
    div[class*="block-container"] {
        background: transparent !important;
        padding-top: 1.5rem !important;
        max-width: 920px !important;
    }

    /* Subtle grid pattern overlay — anchored to Streamlit container */
    [data-testid="stAppViewContainer"]::before,
    .stApp::before {
        content: '';
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        pointer-events: none;
        z-index: 0;
        background-image:
            linear-gradient(rgba(147,197,253,0.04) 1px, transparent 1px),
            linear-gradient(90deg, rgba(147,197,253,0.04) 1px, transparent 1px);
        background-size: 48px 48px;
        mask-image: radial-gradient(ellipse at center, black 30%, transparent 75%);
        -webkit-mask-image: radial-gradient(ellipse at center, black 30%, transparent 75%);
    }

    /* ── SPLASH CONTENT — z-index above grid ── */
    .splash-wrap {
        position: relative;
        z-index: 10;
        max-width: 820px;
        margin: 0 auto;
        padding: 24px 24px 16px;
        text-align: center;
        animation: splash-fade-in 0.8s ease-out;
    }
    @keyframes splash-fade-in {
        from { opacity: 0; transform: translateY(12px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    /* Logo strip */
    .splash-logos {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 28px;
        margin-bottom: 24px;
    }
    .splash-logos img {
        height: 96px; width: auto;
        filter: drop-shadow(0 6px 18px rgba(0,0,0,0.45));
    }
    .splash-univ { text-align: center; flex: 1; }
    .splash-univ .name {
        display: block;
        font-weight: 800;
        color: #FFFFFF !important;
        font-size: 17px;
        line-height: 1.4;
        letter-spacing: 0.6px;
        text-shadow: 0 2px 12px rgba(0,0,0,0.6), 0 0 20px rgba(96,165,250,0.3);
    }
    .splash-univ .faculty {
        display: inline-block;
        margin-top: 8px;
        padding: 5px 16px;
        font-size: 12px;
        font-weight: 700;
        color: #BFDBFE !important;
        letter-spacing: 2.2px;
        background: rgba(56,124,255,0.18);
        border: 1px solid rgba(147,197,253,0.40);
        border-radius: 999px;
    }

    /* NCKH badge */
    .splash-badge {
        display: inline-block;
        margin: 18px 0 14px;
        padding: 6px 18px;
        font-size: 11px;
        font-weight: 700;
        color: #BFDBFE !important;
        letter-spacing: 2.5px;
        text-transform: uppercase;
        background: linear-gradient(90deg, transparent, rgba(56,124,255,0.25), transparent);
        border-top: 1px solid rgba(147,197,253,0.30);
        border-bottom: 1px solid rgba(147,197,253,0.30);
    }

    /* TITLE — FORCE WHITE with strong shadow as defense */
    .splash-title {
        font-family: 'Cambria','Times New Roman', Georgia, serif;
        font-weight: 700;
        color: #FFFFFF !important;
        font-size: 30px;
        line-height: 1.35;
        margin: 14px 0 6px;
        letter-spacing: 0.4px;
        text-shadow:
            0 2px 16px rgba(56,124,255,0.45),
            0 0 30px rgba(0,0,0,0.5),
            0 1px 2px rgba(0,0,0,0.8);
    }
    .splash-title-em {
        color: #60A5FA !important;
        font-style: italic;
        text-shadow: 0 0 20px rgba(96,165,250,0.6);
    }

    .splash-sep {
        display: block;
        width: 80px; height: 3px;
        margin: 18px auto 24px;
        background: linear-gradient(90deg, transparent, #60A5FA, transparent);
        border-radius: 2px;
    }

    /* ── CARDS — MUCH HIGHER OPACITY AS DEFENSE AGAINST BG FAILURE ── */
    .splash-card {
        background: linear-gradient(135deg,
            rgba(15,38,96,0.95) 0%,
            rgba(11,27,69,0.98) 100%) !important;
        border: 1px solid rgba(147,197,253,0.40);
        border-left: 4px solid #60A5FA;
        border-radius: 12px;
        padding: 20px 28px;
        margin: 14px auto;
        max-width: 560px;
        box-shadow:
            0 10px 28px rgba(0,0,0,0.4),
            0 0 0 1px rgba(96,165,250,0.15),
            inset 0 1px 0 rgba(255,255,255,0.06);
        text-align: left;
        position: relative;
        z-index: 5;
    }
    .splash-card .label {
        display: block;
        font-size: 10.5px;
        font-weight: 800;
        color: #93C5FD !important;
        text-transform: uppercase;
        letter-spacing: 2.4px;
        margin-bottom: 10px;
    }
    .splash-card .value {
        font-size: 15px;
        color: #F8FAFC !important;
        font-weight: 600;
        line-height: 1.85;
    }
    .splash-card .value .author-id {
        color: #CBD5E1 !important;
        font-weight: 500;
        font-size: 13.5px;
        margin-left: 6px;
    }

    /* "VÀO NGAY" button — solid blue, prominent */
    div[data-testid="stButton"] {
        display: flex;
        justify-content: center;
        margin: 32px auto 12px;
        position: relative;
        z-index: 5;
    }
    div[data-testid="stButton"] > button {
        background: linear-gradient(135deg, #3B82F6 0%, #1E40AF 100%) !important;
        color: #FFFFFF !important;
        font-weight: 800 !important;
        font-size: 15px !important;
        padding: 14px 44px !important;
        border-radius: 999px !important;
        border: 1px solid rgba(147,197,253,0.45) !important;
        letter-spacing: 2.5px !important;
        box-shadow:
            0 10px 28px rgba(56,124,255,0.55),
            inset 0 1px 0 rgba(255,255,255,0.25) !important;
        transition: transform 0.18s ease, box-shadow 0.18s ease !important;
        min-width: 220px;
    }
    div[data-testid="stButton"] > button:hover {
        background: linear-gradient(135deg, #60A5FA 0%, #2563EB 100%) !important;
        transform: translateY(-3px) scale(1.02);
        box-shadow:
            0 16px 36px rgba(56,124,255,0.70),
            inset 0 1px 0 rgba(255,255,255,0.35) !important;
    }
    div[data-testid="stButton"] > button:active {
        transform: translateY(-1px) scale(0.99);
    }

    /* Footer microcopy */
    .splash-footer {
        margin-top: 18px;
        font-size: 11px;
        color: #94A3B8 !important;
        letter-spacing: 1.6px;
        text-transform: uppercase;
        position: relative;
        z-index: 5;
    }
    .splash-footer .dot { color: #64748B; margin: 0 10px; }
</style>
""", unsafe_allow_html=True)

    logo_html = f"""
    <div class="splash-wrap">
        <div class="splash-logos">
            <img src="data:image/png;base64,{tdt_b64}" alt="TDTU"/>
            <div class="splash-univ">
                <span class="name">TRƯỜNG ĐẠI HỌC TÔN ĐỨC THẮNG</span>
                <span class="faculty">KHOA TOÁN — THỐNG KÊ</span>
            </div>
            <img src="data:image/png;base64,{khoa_b64}" alt="Faculty of Mathematics and Statistics"/>
        </div>

        <div class="splash-badge">Công trình Nghiên cứu khoa học sinh viên · 2025–2026</div>

        <div class="splash-title">
            XÂY DỰNG <span class="splash-title-em">CHATBOT</span><br/>
            PHÂN TÍCH VÀ DỰ BÁO CHỨNG KHOÁN<br/>
            DỰA TRÊN MÔ HÌNH THỐNG KÊ VÀ HỌC MÁY
        </div>

        <span class="splash-sep"></span>

        <div class="splash-card">
            <span class="label">Giảng viên hướng dẫn</span>
            <div class="value">ThS. Chế Ngọc Hà</div>
        </div>

        <div class="splash-card">
            <span class="label">Nhóm tác giả</span>
            <div class="value">
                Nguyễn Thành Danh<span class="author-id">— C2300014</span><br/>
                Nguyễn Nhật Anh Huy<span class="author-id">— C2200153</span><br/>
                Mai Phan Vũ<span class="author-id">— C2200141</span>
            </div>
        </div>
    </div>
    """
    st.markdown(logo_html, unsafe_allow_html=True)

    if st.button('VÀO NGAY', key='splash_enter'):
        st.session_state['_splash_done'] = True
        st.rerun()

    st.markdown(
        '<div class="splash-footer" style="text-align:center">'
        'TDTU <span class="dot">·</span> NCKH 2026 '
        '<span class="dot">·</span> HOSE Stock Forecasting'
        '</div>',
        unsafe_allow_html=True,
    )
