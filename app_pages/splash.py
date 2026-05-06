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
    """Hiển thị splash/cover page với 2 logo, tên đề tài, GVHD, nhóm tác giả và nút Vào Ngay."""

    tdt_b64 = _img_b64('TDT_logo.jpg')
    khoa_b64 = _img_b64('khoa_logo.jpg')

    st.markdown("""
    <style>
        /* Ẩn sidebar trong splash */
        [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
        /* Toàn bộ background gradient */
        .stApp { background: linear-gradient(180deg, #EFF6FF 0%, #DBEAFE 100%) !important; }
        /* Container splash */
        .splash-wrap {
            max-width: 760px; margin: 0 auto; padding: 40px 20px 20px;
            text-align: center;
        }
        .splash-logos {
            display: flex; justify-content: space-between; align-items: center;
            gap: 20px; margin-bottom: 18px;
        }
        .splash-logos img { height: 92px; width: auto; }
        .splash-univ {
            font-weight: 800; color: #1E3A8A; font-size: 18px; line-height: 1.4;
            letter-spacing: 0.5px;
        }
        .splash-univ .small { font-size: 14px; font-weight: 600; color: #334155; }
        .splash-title {
            font-weight: 900; color: #B91C1C; font-size: 22px; line-height: 1.4;
            margin: 22px 0 8px; letter-spacing: 0.4px;
        }
        .splash-sub { color: #64748B; font-size: 13px; margin-bottom: 24px; }
        .splash-card {
            background: white; border: 1px solid #DBEAFE; border-radius: 16px;
            padding: 22px 24px; margin: 18px auto; max-width: 520px;
            box-shadow: 0 6px 20px rgba(30,58,138,0.08);
        }
        .splash-card .label {
            font-size: 12px; font-weight: 700; color: #1E3A8A;
            text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 6px;
        }
        .splash-card .value {
            font-size: 15px; color: #0F172A; font-weight: 600; line-height: 1.7;
        }
        /* Nút Vào Ngay — style trực tiếp st.button */
        div[data-testid="stButton"] > button {
            background: #1E3A8A !important; color: white !important;
            font-weight: 800 !important; font-size: 16px !important;
            padding: 14px 36px !important; border-radius: 12px !important;
            border: none !important; letter-spacing: 1px !important;
            box-shadow: 0 6px 16px rgba(30,58,138,0.25) !important;
            transition: all 0.2s ease !important;
            width: 100%; max-width: 320px;
        }
        div[data-testid="stButton"] > button:hover {
            background: #1E40AF !important;
            transform: translateY(-2px);
            box-shadow: 0 10px 22px rgba(30,58,138,0.35) !important;
        }
        div[data-testid="stButton"] { display: flex; justify-content: center; margin-top: 28px; }
    </style>
    """, unsafe_allow_html=True)

    logo_html = f"""
    <div class="splash-wrap">
        <div class="splash-logos">
            <img src="data:image/jpeg;base64,{tdt_b64}" alt="TDTU"/>
            <div class="splash-univ">
                TRƯỜNG ĐẠI HỌC TÔN ĐỨC THẮNG<br/>
                <span class="small">KHOA TOÁN -- THỐNG KÊ</span>
            </div>
            <img src="data:image/jpeg;base64,{khoa_b64}" alt="Faculty of Mathematics and Statistics"/>
        </div>
        <div class="splash-sub">Công trình Nghiên cứu khoa học sinh viên năm học 2025--2026</div>
        <div class="splash-title">
            XÂY DỰNG CHATBOT PHÂN TÍCH VÀ DỰ BÁO<br/>
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
