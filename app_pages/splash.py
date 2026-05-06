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
    """Splash/cover page — navy theme, logo nền trong suốt, hợp với app."""

    tdt_b64 = _img_b64('TDT_logo.png')
    khoa_b64 = _img_b64('khoa_logo.png')

    st.markdown("""
    <style>
        /* Ẩn sidebar trong splash */
        [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
        /* Toàn bộ background — gradient navy như app */
        .stApp {
            background:
                radial-gradient(circle at 18% 12%, rgba(37,99,235,0.22) 0, transparent 45%),
                radial-gradient(circle at 82% 88%, rgba(30,64,175,0.28) 0, transparent 50%),
                linear-gradient(160deg, #0B1B3D 0%, #0F2A5C 45%, #122F66 100%) !important;
            color: #E2E8F0 !important;
        }
        /* Container splash */
        .splash-wrap {
            max-width: 780px; margin: 0 auto; padding: 50px 20px 30px;
            text-align: center;
        }
        .splash-logos {
            display: flex; justify-content: space-between; align-items: center;
            gap: 24px; margin-bottom: 20px;
        }
        /* Logo PNG đã transparent — không cần khung trắng */
        .splash-logos img {
            height: 100px; width: auto;
            filter: drop-shadow(0 4px 12px rgba(0,0,0,0.25));
        }
        .splash-univ {
            font-weight: 800; color: #FFFFFF; font-size: 18px; line-height: 1.45;
            letter-spacing: 0.6px; text-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }
        .splash-univ .small {
            font-size: 14px; font-weight: 600; color: #93C5FD;
            letter-spacing: 1.2px;
        }
        .splash-title {
            font-weight: 900; color: #FFFFFF; font-size: 24px; line-height: 1.45;
            margin: 28px 0 10px; letter-spacing: 0.5px;
            text-shadow: 0 2px 14px rgba(37,99,235,0.45);
        }
        .splash-title .accent { color: #FBBF24; }
        .splash-sub {
            color: #94A3B8; font-size: 13px; margin-bottom: 28px;
            letter-spacing: 0.5px;
        }
        /* Card glass-morphism trên nền navy */
        .splash-card {
            background: rgba(255,255,255,0.06);
            backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
            border: 1px solid rgba(147,197,253,0.18);
            border-radius: 16px;
            padding: 22px 26px; margin: 16px auto; max-width: 540px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.18),
                        inset 0 1px 0 rgba(255,255,255,0.05);
        }
        .splash-card .label {
            font-size: 11px; font-weight: 700; color: #93C5FD;
            text-transform: uppercase; letter-spacing: 1.8px; margin-bottom: 8px;
        }
        .splash-card .value {
            font-size: 15px; color: #F1F5F9; font-weight: 600; line-height: 1.75;
        }
        /* Nút Vào Ngay */
        div[data-testid="stButton"] > button {
            background: linear-gradient(135deg,#2563EB 0%,#1E40AF 100%) !important;
            color: #FFFFFF !important;
            font-weight: 800 !important; font-size: 16px !important;
            padding: 14px 38px !important; border-radius: 12px !important;
            border: 1px solid rgba(147,197,253,0.35) !important;
            letter-spacing: 1.5px !important;
            box-shadow: 0 8px 24px rgba(37,99,235,0.40),
                        inset 0 1px 0 rgba(255,255,255,0.18) !important;
            transition: all 0.2s ease !important;
            width: 100%; max-width: 320px;
        }
        div[data-testid="stButton"] > button:hover {
            background: linear-gradient(135deg,#3B82F6 0%,#2563EB 100%) !important;
            transform: translateY(-2px);
            box-shadow: 0 12px 30px rgba(37,99,235,0.55),
                        inset 0 1px 0 rgba(255,255,255,0.25) !important;
        }
        div[data-testid="stButton"] { display: flex; justify-content: center; margin-top: 30px; }
    </style>
    """, unsafe_allow_html=True)

    logo_html = f"""
    <div class="splash-wrap">
        <div class="splash-logos">
            <img src="data:image/png;base64,{tdt_b64}" alt="TDTU"/>
            <div class="splash-univ">
                TRƯỜNG ĐẠI HỌC TÔN ĐỨC THẮNG<br/>
                <span class="small">KHOA TOÁN -- THỐNG KÊ</span>
            </div>
            <img src="data:image/png;base64,{khoa_b64}" alt="Faculty of Mathematics and Statistics"/>
        </div>
        <div class="splash-sub">Công trình Nghiên cứu khoa học sinh viên năm học 2025--2026</div>
        <div class="splash-title">
            <span class="accent">XÂY DỰNG CHATBOT</span> PHÂN TÍCH VÀ DỰ BÁO<br/>
            CHỨNG KHOÁN DỰA TRÊN MÔ HÌNH<br/>
            THỐNG KÊ VÀ HỌC MÁY
        </div>
        <div class="splash-card">
            <div class="label">Giảng viên hướng dẫn</div>
            <div class="value">ThS. Chế Ngọc Hà</div>
        </div>
        <div class="splash-card">
            <div class="label">Nhóm tác giả</div>
            <div class="value">
                Nguyễn Thành Danh &mdash; C2300014<br/>
                Nguyễn Nhật Anh Huy &mdash; C2200153<br/>
                Mai Phan Vũ &mdash; C2200141
            </div>
        </div>
    </div>
    """
    st.markdown(logo_html, unsafe_allow_html=True)

    if st.button('VÀO NGAY', key='splash_enter'):
        st.session_state['_splash_done'] = True
        st.rerun()
