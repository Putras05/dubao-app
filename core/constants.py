import streamlit as st

TICKERS = ['FPT', 'HPG', 'VNM']
TICKER_INFO = {
    'FPT': 'Công nghệ thông tin · HOSE',
    'HPG': 'Thép — Vật liệu xây dựng · HOSE',
    'VNM': 'Thực phẩm — Đồ uống · HOSE',
}
TICKER_DESC = {
    'FPT': 'Cổ phiếu tăng trưởng bền vững, xu hướng tăng tuyến tính dài hạn.',
    'HPG': 'Cổ phiếu chu kỳ biến động cao, nhạy cảm với giá thép và đầu tư công.',
    'VNM': 'Cổ phiếu phòng thủ xu hướng giảm, biên độ thấp và ổn định.',
}
CLR      = {'FPT': '#1565C0', 'HPG': '#6A1B9A', 'VNM': '#2E7D32', 'pred': '#C62828'}
CLR_DARK = {'FPT': '#60A5FA', 'HPG': '#C084FC', 'VNM': '#34D399', 'pred': '#F87171'}

COLORS = {
    'buy': '#2E7D32', 'sell': '#C62828', 'warn': '#F9A825', 'neut': '#546E8A',
    'text_primary': '#1A2A4A', 'text_secondary': '#556888', 'text_muted': '#8090B0',
    'border': '#DDE8F5', 'bg_card': '#FFFFFF', 'blue': '#1565C0', 'purple': '#6A1B9A',
}


def get_clr(T: dict) -> dict:
    return CLR_DARK if T.get('is_dark', False) else CLR
