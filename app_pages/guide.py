import streamlit as st


def render(ticker, train_ratio, date_from, date_to, df, r1, r2, r3, m1, m2, m3, _T,
           ar_order=1):
    _is_en = st.session_state.get('lang', 'VI') == 'EN'
    # _T param từ caller — KHÔNG override bằng theme() (mất theme override nếu caller pass)

    st.markdown(f"""
<div style="background:{_T['banner_bg']};border-radius:14px;padding:24px 32px;
            margin-bottom:24px;border:1px solid {_T['border']}">
  <div style="display:flex;align-items:center;gap:16px">
    <div style="width:52px;height:52px;border-radius:12px;
                background:linear-gradient(135deg,#1E40AF,#3B82F6);
                display:flex;align-items:center;justify-content:center;flex-shrink:0">
      <svg width="26" height="26" viewBox="0 0 16 16" fill="#FFFFFF"><path d="M8.5 2.687c.654-.689 1.782-.886 3.112-.752 1.234.124 2.503.523 3.388.893v9.923c-.918-.35-2.107-.692-3.287-.81-1.094-.111-2.278-.039-3.213.492zM8 1.783C7.015.936 5.587.81 4.287.94c-1.514.153-3.042.672-3.994 1.105A.5.5 0 0 0 0 2.5v11a.5.5 0 0 0 .707.455c.882-.4 2.303-.881 3.68-1.02 1.409-.142 2.59.087 3.223.877a.5.5 0 0 0 .78 0c.633-.79 1.814-1.019 3.222-.877 1.378.139 2.8.62 3.681 1.02A.5.5 0 0 0 16 13.5v-11a.5.5 0 0 0-.293-.455c-.952-.433-2.48-.952-3.994-1.105C10.413.809 8.985.936 8 1.783"/></svg>
    </div>
    <div>
      <div style="font-size:22px;font-weight:800;color:{_T['banner_text']};line-height:1.2">
        {'User Guide' if _is_en else 'Hướng dẫn Sử dụng'}
      </div>
      <div style="font-size:13px;color:{_T['banner_subtext']};margin-top:4px">
        {'Stock Price Forecasting System · TDTU NCKH 2026'
         if _is_en else
         'Hệ thống Dự báo Giá Cổ phiếu · NCKH TDTU 2026'}
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    _SVGS = {
        'speedometer2': '<path d="M8 4a.5.5 0 1 1-1 0 .5.5 0 0 1 1 0zm3.5.5a.5.5 0 1 0 0-1 .5.5 0 0 0 0 1zm-7 1a.5.5 0 1 0 0-1 .5.5 0 0 0 0 1zm11 0a.5.5 0 1 1-1 0 .5.5 0 0 1 1 0zM4.354 8.646a.5.5 0 1 0-.708.708.5.5 0 0 0 .708-.708zm7.996-5.039a.5.5 0 1 0-.708.707.5.5 0 0 0 .708-.707zm-9.29 9.29a.5.5 0 1 0 .707-.708.5.5 0 0 0-.707.708zM8 1a7 7 0 1 0 0 14A7 7 0 0 0 8 1zM0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8z"/><path d="M8 7.5a.5.5 0 0 0-.354.854l.5.5a.5.5 0 0 0 .707 0l4-4a.5.5 0 0 0-.707-.707L8.5 7.793l-.146-.146A.5.5 0 0 0 8 7.5z"/>',
        'graph-up-arrow': '<path fill-rule="evenodd" d="M0 0h1v15h15v1H0zm10 3.5a.5.5 0 0 1 .5-.5h4a.5.5 0 0 1 .5.5v4a.5.5 0 0 1-1 0V4.9l-3.613 4.417a.5.5 0 0 1-.74.037L7.06 6.767l-3.656 5.027a.5.5 0 0 1-.808-.588l4-5.5a.5.5 0 0 1 .758-.06l2.609 2.61L13.445 4H10.5a.5.5 0 0 1-.5-.5z"/>',
        'clock-history':  '<path d="M8.515 1.019A7 7 0 0 0 8 1V0a8 8 0 0 1 .589.022zm2.004.45a7 7 0 0 0-.985-.299l.219-.976q.576.129 1.126.342zm1.37.71a7 7 0 0 0-.831-.556l.51-.857q.48.27.92.598zm1.658 1.545a7 7 0 0 0-.653-.796l.724-.69q.406.429.747.91zm.744 1.352a7 7 0 0 0-.394-.952l.893-.45a8 8 0 0 1 .45 1.088zm.53 2.507a7 7 0 0 0-.1-1.025l.985-.17q.1.58.116 1.17zm-.131 1.538q.05-.254.081-.51l.993.123a8 8 0 0 1-.23 1.155zm-.952 2.379q.276-.436.486-.908l.914.405q-.24.54-.555 1.038zm-1.243 1.81q.183-.183.35-.378l.758.653a8 8 0 0 1-.401.432zM8 1a7 7 0 1 0 4.95 11.95l.707.707A8.001 8.001 0 1 1 8 0z"/><path d="M7.5 3a.5.5 0 0 1 .5.5v5.21l3.248 1.856a.5.5 0 0 1-.496.868l-3.5-2A.5.5 0 0 1 7 9V3.5a.5.5 0 0 1 .5-.5z"/>',
        'activity':       '<path fill-rule="evenodd" d="M6 2a.5.5 0 0 1 .47.33L10 12.036l1.53-4.208A.5.5 0 0 1 12 7.5h3.5a.5.5 0 0 1 0 1h-3.15l-1.88 5.17a.5.5 0 0 1-.94 0L6 3.964 4.47 8.171A.5.5 0 0 1 4 8.5H.5a.5.5 0 0 1 0-1h3.15l1.88-5.17A.5.5 0 0 1 6 2z"/>',
        'briefcase':      '<path d="M6.5 1A1.5 1.5 0 0 0 5 2.5V3H1.5A1.5 1.5 0 0 0 0 4.5v8A1.5 1.5 0 0 0 1.5 14h13a1.5 1.5 0 0 0 1.5-1.5v-8A1.5 1.5 0 0 0 14.5 3H11v-.5A1.5 1.5 0 0 0 9.5 1zm0 1h3a.5.5 0 0 1 .5.5V3H6v-.5a.5.5 0 0 1 .5-.5zm1.886 6.914L15 7.151V12.5a.5.5 0 0 1-.5.5h-13a.5.5 0 0 1-.5-.5V7.15l6.614 1.764a1.5 1.5 0 0 0 .772 0zM1.5 4h13a.5.5 0 0 1 .5.5v1.616L8.129 7.948a.5.5 0 0 1-.258 0L1 6.116V4.5a.5.5 0 0 1 .5-.5z"/>',
        'sliders':        '<path d="M11.5 2a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zM9.05 3a2.5 2.5 0 0 1 4.9 0H16v1h-2.05a2.5 2.5 0 0 1-4.9 0H0V3zm-4.55 4a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zM2.05 8a2.5 2.5 0 0 1 4.9 0H16v1H6.95a2.5 2.5 0 0 1-4.9 0H0V8zm9.45 4a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm-2.45 1a2.5 2.5 0 0 1 4.9 0H16v1h-2.05a2.5 2.5 0 0 1-4.9 0H0v-1z"/>',
        'info-circle-fill':'<path d="M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zm.93-9.412-1 4.705c-.07.34.029.533.304.533.194 0 .487-.07.686-.246l-.088.416c-.287.346-.92.598-1.465.598-.703 0-1.002-.422-.808-1.319l.738-3.468c.064-.293.006-.399-.287-.47l-.451-.081.082-.381 2.29-.287zM8 5.5a1 1 0 1 1 0-2 1 1 0 0 1 0 2z"/>',
    }

    def _ic(name: str, color: str, size: int = 18) -> str:
        body = _SVGS.get(name, '<circle cx="8" cy="8" r="6"/>')
        return (f'<svg width="{size}" height="{size}" viewBox="0 0 16 16" '
                f'fill="{color}" xmlns="http://www.w3.org/2000/svg">{body}</svg>')

    def _guide_card(icon_name: str, title: str, color: str, body_html: str):
        icon_svg = _ic(icon_name, color, 18)
        st.markdown(f"""
<div style="background:{_T['bg_card']};border:1px solid {_T['border']};
            border-radius:12px;padding:20px 24px;margin-bottom:16px;
            border-left:4px solid {color}">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px">
    <div style="width:38px;height:38px;border-radius:9px;background:{color}28;
                display:flex;align-items:center;justify-content:center;flex-shrink:0">
      {icon_svg}
    </div>
    <div style="font-size:15px;font-weight:700;color:{_T['text_primary']}">{title}</div>
  </div>
  <div style="color:{_T['text_primary']};font-size:13px;line-height:1.75">
    {body_html}
  </div>
</div>
""", unsafe_allow_html=True)

    _SVGS['chat-dots'] = '<path d="M5 8a1 1 0 1 1-2 0 1 1 0 0 1 2 0zm4 0a1 1 0 1 1-2 0 1 1 0 0 1 2 0zm3 1a1 1 0 1 0 0-2 1 1 0 0 0 0 2z"/><path d="m2.165 15.803.02-.004c1.83-.363 2.948-.842 3.468-1.105A9 9 0 0 0 8 15c4.418 0 8-3.134 8-7s-3.582-7-8-7-8 3.134-8 7c0 1.76.743 3.37 1.97 4.6a10.4 10.4 0 0 1-.524 2.318l-.003.011a11 11 0 0 1-.244.637c-.079.186.074.394.273.362a22 22 0 0 0 .693-.125m.8-3.108a1 1 0 0 0-.287-.801C1.618 10.83 1 9.468 1 8c0-3.192 3.004-6 7-6s7 2.808 7 6-3.004 6-7 6a8 8 0 0 1-2.088-.272 1 1 0 0 0-.711.074c-.387.196-1.24.57-2.634.893a11 11 0 0 0 .398-2"/>'
    _SVGS['file-pdf']  = '<path d="M14 14V4.5L9.5 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2M9.5 3A1.5 1.5 0 0 0 11 4.5h2V14a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1h5.5z"/><path d="M4.603 14.087a.8.8 0 0 1-.438-.42c-.195-.388-.13-.776.08-1.102.198-.307.526-.568.897-.787a7.7 7.7 0 0 1 1.482-.645 19.7 19.7 0 0 0 1.062-2.227 7.3 7.3 0 0 1-.43-1.295c-.086-.4-.119-.796-.046-1.136.075-.354.274-.672.65-.823.192-.077.4-.12.602-.077a.7.7 0 0 1 .477.365c.088.164.12.356.127.538.007.188-.012.396-.047.614-.084.51-.27 1.134-.52 1.794a10.95 10.95 0 0 0 .98 1.686 5.753 5.753 0 0 1 1.334.05c.364.066.734.195.96.465.12.144.193.32.2.518.007.192-.047.382-.138.563a1.04 1.04 0 0 1-.354.416.86.86 0 0 1-.51.138c-.331-.014-.654-.196-.933-.417a5.712 5.712 0 0 1-.911-.95 11.651 11.651 0 0 0-1.997.406 11.307 11.307 0 0 1-1.02 1.51c-.292.35-.609.656-.927.787a.793.793 0 0 1-.58.029m1.379-1.901q-.25.115-.459.238c-.328.194-.541.383-.647.547-.094.145-.096.25-.04.361q.016.032.026.044l.035-.012c.137-.056.355-.235.635-.572a8 8 0 0 0 .45-.606zm1.64-1.33a13 13 0 0 1 1.01-.193 12 12 0 0 1-.51-.858 21 21 0 0 1-.5 1.05zm2.446.45q.226.244.435.41c.24.19.407.253.498.256a.1.1 0 0 0 .07-.015.3.3 0 0 0 .094-.125.44.44 0 0 0 .059-.2.1.1 0 0 0-.026-.063c-.052-.062-.2-.152-.518-.209a4 4 0 0 0-.612-.053zM8.078 7.8a7 7 0 0 0 .2-.828q.046-.282.038-.465a.6.6 0 0 0-.032-.198.5.5 0 0 0-.145.04c-.087.035-.158.106-.196.283-.04.192-.03.469.046.822q.036.167.09.346z"/>'

    _IC_DASH = 'speedometer2'
    _IC_ANA  = 'graph-up-arrow'
    _IC_HIST = 'clock-history'
    _IC_SIG  = 'activity'
    _IC_PORT = 'briefcase'
    _IC_AI   = 'chat-dots'
    _IC_SET  = 'sliders'
    _IC_PDF  = 'file-pdf'

    col_g1, col_g2 = st.columns(2)

    with col_g1:
        _guide_card(_IC_DASH, '1. Dashboard Tổng quan' if not _is_en else '1. Overview Dashboard',
                    '#3B82F6', f"""
<b style="color:{_T['text_primary']}">{'Mục đích:' if not _is_en else 'Purpose:'}</b>
{'Cung cấp cái nhìn nhanh về 3 cổ phiếu FPT · HPG · VNM.'
 if not _is_en else 'Quick snapshot of 3 stocks: FPT · HPG · VNM.'}<br><br>

<b style="color:{_T['text_primary']}">{'Các thông tin hiển thị:' if not _is_en else 'Information displayed:'}</b><br>
{'• Giá đóng cửa hiện tại và thay đổi so với phiên trước<br>'
 '• 3 card mô hình AR · MLR · CART với giá dự báo + KTC 95% + sparkline<br>'
 '• AI Insight tổng hợp: tín hiệu Ichimoku 4 tầng + dự báo phiên tới<br>'
 '• <b>Biểu đồ nến TradingView-style</b>: chọn khung 1D/1W/1M/3M, '
 'toggle SMA 5/20 và Ichimoku, info bar O/H/L/C, volume bar dưới<br>'
 '• Bảng xếp hạng mô hình theo MAPE'
 if not _is_en else
 '• Current close price and change vs. previous session<br>'
 '• 3 model cards AR · MLR · CART with forecast + 95% CI + sparkline<br>'
 '• AI Insight: Ichimoku 4-tier signal + next-session forecast<br>'
 '• <b>TradingView-style candlestick chart</b>: pick 1D/1W/1M/3M, '
 'toggle SMA 5/20 and Ichimoku, OHLC info bar, volume bars below<br>'
 '• Model ranking table by MAPE'}
""")

        _guide_card(_IC_HIST, '3. Lịch sử & Dữ liệu' if not _is_en else '3. History & Data',
                    '#F59E0B', f"""
<b style="color:{_T['text_primary']}">{'Mục đích:' if not _is_en else 'Purpose:'}</b>
{'Xem dữ liệu lịch sử và thống kê mô tả.'
 if not _is_en else 'Browse historical data and descriptive statistics.'}<br><br>

<b style="color:{_T['text_primary']}">{'Cách sử dụng:' if not _is_en else 'How to use:'}</b><br>
{'• Chọn khoảng thời gian bằng bộ lọc <b>Từ</b> / <b>Đến</b> ở sidebar<br>'
 '• Biểu đồ giá lịch sử tương tác (zoom/pan/download)<br>'
 '• Phân phối Return hàng ngày so với phân phối Chuẩn<br>'
 '• Bảng dữ liệu OHLCV đầy đủ có thể tải xuống'
 if not _is_en else
 '• Select date range using <b>From</b> / <b>To</b> filters in sidebar<br>'
 '• Interactive historical price chart (zoom/pan/download)<br>'
 '• Daily Return distribution vs. Normal distribution<br>'
 '• Full OHLCV data table downloadable'}
""")

        _guide_card(_IC_PORT, '5. Danh mục Đầu tư' if not _is_en else '5. Investment Portfolio',
                    '#10B981', f"""
<b style="color:{_T['text_primary']}">{'Mục đích:' if not _is_en else 'Purpose:'}</b>
{'So sánh hiệu quả dự báo và rủi ro của 3 cổ phiếu.'
 if not _is_en else 'Compare forecast performance and risk across 3 stocks.'}<br><br>

<b style="color:{_T['text_primary']}">{'Nội dung:' if not _is_en else 'Content:'}</b><br>
{'• Biểu đồ hiệu suất chuẩn hóa 3 mã (Base = 100) — so sánh tương đối<br>'
 '• Bảng MAPE · RMSE · MAE · R²adj cho cả 3 mô hình × 3 mã<br>'
 '• Card sparkline + thống kê Return (mean/std/min/max/up_days) cho mỗi mã'
 if not _is_en else
 '• Normalized performance chart (Base = 100) — relative comparison<br>'
 '• MAPE · RMSE · MAE · R²adj table for 3 models × 3 tickers<br>'
 '• Sparkline cards + Return stats (mean/std/min/max/up_days) per ticker'}
""")

        _guide_card(_IC_PDF, '7. Xuất báo cáo PDF' if not _is_en else '7. Export PDF Report',
                    '#DC2626', f"""
<b style="color:{_T['text_primary']}">{'Mục đích:' if not _is_en else 'Purpose:'}</b>
{'Xuất báo cáo đầy đủ 10 trang A4 — tổng hợp toàn bộ kết quả phân tích cho 1 mã cổ phiếu.'
 if not _is_en else 'Export a full 10-page A4 report — complete analysis results for one ticker.'}<br><br>

<b style="color:{_T['text_primary']}">{'Cách tải báo cáo:' if not _is_en else 'How to download:'}</b><br>
{'• <b>Bước 1:</b> Chọn mã cổ phiếu + tham số (Train Ratio, p, khoảng thời gian) ở sidebar<br>'
 '• <b>Bước 2:</b> Chờ huấn luyện xong (spinner biến mất) — nút <b>"⤓ Xuất báo cáo PDF"</b> hiện ở sidebar<br>'
 '• <b>Bước 3:</b> Bấm nút → chờ ~5-10 giây sinh PDF → bấm <b>"⬇ Tải báo cáo PDF"</b> để lưu file<br>'
 '• <b>Bước 4:</b> Muốn tạo bản mới với tham số khác → bấm <b>"↻ Tạo PDF mới"</b>'
 if not _is_en else
 '• <b>Step 1:</b> Select ticker + parameters (Train Ratio, p, date range) in sidebar<br>'
 '• <b>Step 2:</b> Wait for training to finish (spinner disappears) — button <b>"⤓ Export PDF Report"</b> appears in sidebar<br>'
 '• <b>Step 3:</b> Click → wait ~5-10s for PDF generation → click <b>"⬇ Download PDF Report"</b> to save<br>'
 '• <b>Step 4:</b> Want a new report with different params → click <b>"↻ Generate new PDF"</b>'}<br><br>

<b style="color:{_T['text_primary']}">{'Nội dung 10 trang báo cáo:' if not _is_en else '10-page report content:'}</b><br>
{'• <b>Trang 1:</b> Bìa — tên đề tài, ticker, ngày xuất<br>'
 '• <b>Trang 2:</b> Mục lục<br>'
 '• <b>Trang 3:</b> Chẩn đoán mô hình — 4 panel: Test set comparison, '
 'Bar MAPE/RMSE/MAE, ACF phần dư, Chuỗi phần dư theo thời gian<br>'
 '• <b>Trang 4:</b> Actual vs Predicted — 3 subplot xếp dọc cho từng mô hình<br>'
 '• <b>Trang 5:</b> Scatter y=x + OLS fit + hệ số AR/MLR chi tiết<br>'
 '• <b>Trang 6:</b> CART — độ quan trọng 6 đặc trưng + hyperparameters GridSearchCV<br>'
 '• <b>Trang 7:</b> CART — sơ đồ cây quyết định (custom visualization)<br>'
 '• <b>Trang 8:</b> Ichimoku — biểu đồ landscape (Close + Tenkan + Kijun + Kumo + Chikou)<br>'
 '• <b>Trang 9:</b> Ichimoku — phân tích 4 tầng tín hiệu + điểm đồng thuận<br>'
 '• <b>Trang 10:</b> Bảng metrics (MAPE · RMSE · MAE · R²adj) + kết luận'
 if not _is_en else
 '• <b>Page 1:</b> Cover — project title, ticker, export date<br>'
 '• <b>Page 2:</b> Table of contents<br>'
 '• <b>Page 3:</b> Model diagnostics — 4 panels: Test-set comparison, '
 'MAPE/RMSE/MAE bars, residual ACF, residual time series<br>'
 '• <b>Page 4:</b> Actual vs Predicted — 3 stacked subplots, one per model<br>'
 '• <b>Page 5:</b> Scatter y=x + OLS fit + detailed AR/MLR coefficients<br>'
 '• <b>Page 6:</b> CART — feature importance (6 features) + GridSearchCV hyperparameters<br>'
 '• <b>Page 7:</b> CART — decision tree diagram (custom visualization)<br>'
 '• <b>Page 8:</b> Ichimoku — landscape chart (Close + Tenkan + Kijun + Kumo + Chikou)<br>'
 '• <b>Page 9:</b> Ichimoku — 4-tier signal analysis + consensus score<br>'
 '• <b>Page 10:</b> Metrics table (MAPE · RMSE · MAE · R²adj) + conclusion'}<br><br>

<b style="color:{_T['text_primary']}">{'Lưu ý:' if not _is_en else 'Notes:'}</b><br>
{'• Tên file mặc định: <code>BaoCao_{{TICKER}}_{{YYYYMMDD_HHMM}}.pdf</code><br>'
 '• PDF nhẹ (~500KB-1MB) — dùng PdfPages của matplotlib, không cần cài thêm thư viện<br>'
 '• Đổi ngôn ngữ VI/EN trong sidebar không đổi nội dung PDF (PDF luôn tiếng Việt)'
 if not _is_en else
 '• Default filename: <code>BaoCao_{{TICKER}}_{{YYYYMMDD_HHMM}}.pdf</code><br>'
 '• PDF is lightweight (~500KB-1MB) — uses matplotlib PdfPages, no extra deps<br>'
 '• Changing sidebar language VI/EN does not change PDF content (PDF always in Vietnamese)'}
""")

    with col_g2:
        _guide_card(_IC_ANA, '2. Phân tích Chi tiết' if not _is_en else '2. Detailed Analysis',
                    '#8B5CF6', f"""
<b style="color:{_T['text_primary']}">{'Mục đích:' if not _is_en else 'Purpose:'}</b>
{'Xem chi tiết 3 mô hình dự báo phiên kế tiếp — phương trình, hệ số, hiệu năng Train/Test.'
 if not _is_en else 'Detailed view of 3 next-session forecasting models — equation, coefficients, Train/Test performance.'}<br><br>

<b style="color:{_T['text_primary']}">{'3 mô hình (tất cả dự báo Y(t+1)):' if not _is_en else '3 models (all forecast Y(t+1)):'}</b><br>
{(f'• <b>AR(p)</b> — Autoregressive bậc p theo Box-Jenkins. Dùng {ar_order} phiên quá khứ [Y(t), Y(t−1), ..., Y(t−p+1)]. Tổng <b>p+1</b> = {ar_order+1} hệ số.<br>'
  f'• <b>MLR(p)</b> — Hồi quy đa biến với Distributed Lag: Close + Volume + Range × p lag. Tổng <b>3p+1</b> = {3*ar_order+1} hệ số.<br>'
  f'• <b>CART(p)</b> — Decision Tree trên 6 đặc trưng kỹ thuật (Return, Volume_ratio, Range_ratio, MA5_ratio, MA20_ratio, RSI14) × p lag = <b>{6*ar_order}</b> features. Target = return phiên kế tiếp, phục hồi giá Ŷ = Y(t)·(1+R̂/100). Tối ưu bằng GridSearchCV + TimeSeriesSplit.')
 if not _is_en else
 (f'• <b>AR(p)</b> — Autoregressive order p (Box-Jenkins). Uses {ar_order} past sessions [Y(t), Y(t−1), ..., Y(t−p+1)]. Total <b>p+1</b> = {ar_order+1} coefficients.<br>'
  f'• <b>MLR(p)</b> — Multiple Linear Regression with Distributed Lag: Close + Volume + Range × p lags. Total <b>3p+1</b> = {3*ar_order+1} coefficients.<br>'
  f'• <b>CART(p)</b> — Decision Tree on 6 technical features (Return, Volume_ratio, Range_ratio, MA5_ratio, MA20_ratio, RSI14) × p lags = <b>{6*ar_order}</b> features. Target = next-session return, price recovered via Ŷ = Y(t)·(1+R̂/100). Tuned via GridSearchCV + TimeSeriesSplit.')
}<br><br>

<b style="color:{_T['text_primary']}">{'Biểu đồ hiển thị:' if not _is_en else 'Charts shown:'}</b><br>
{'• Lịch sử giá với vùng Train/Test được tô màu<br>'
 '• Kết quả dự báo: đường thực tế vs. dự báo theo thời gian<br>'
 '• Scatter thực tế vs. dự báo (R² = 1 là lý tưởng)<br>'
 '• Phương trình mô hình + bảng tham số ước lượng<br>'
 '• Sơ đồ cây quyết định CART (tương tác zoom/pan)'
 if not _is_en else
 '• Price history with Train/Test regions highlighted<br>'
 '• Forecast results: actual vs. forecast time series<br>'
 '• Actual vs. forecast scatter (ideal R² = 1)<br>'
 '• Model equation + estimated parameter table<br>'
 '• Interactive CART decision tree diagram (zoom/pan)'}
""")

        _guide_card(_IC_SIG, '4. Tín hiệu & Cảnh báo' if not _is_en else '4. Signals & Alerts',
                    '#EF4444', f"""
<b style="color:{_T['text_primary']}">{'Mục đích:' if not _is_en else 'Purpose:'}</b>
{'Phân tích xu hướng theo hệ thống Ichimoku Kinko Hyo (Hosoda 1969).'
 if not _is_en else 'Trend analysis using the Ichimoku Kinko Hyo system (Hosoda 1969).'}<br><br>

<b style="color:{_T['text_primary']}">{'Hệ thống 4 tầng + điểm đồng thuận (±5):' if not _is_en else '4-tier system + consensus score (±5):'}</b><br>
{'• <b>Tầng 1 — Xu hướng chính:</b> giá vs. Kumo (mây) → ±1 điểm<br>'
 '• <b>Tầng 2 — TK Cross:</b> Tenkan/Kijun cắt nhau + vị trí vs. Kumo → ±2/±1/0<br>'
 '• <b>Tầng 3 — Chikou Span:</b> đường trễ 26 phiên vs. giá quá khứ → ±1 điểm<br>'
 '• <b>Tầng 4 — Kumo tương lai:</b> hình dạng mây dự báo 26 phiên tới → ±1 điểm<br><br>'
 '• Score <b>+4/+5</b>: <span style="color:#4ADE80">Tăng mạnh</span> · '
 '<b>+2/+3</b>: <span style="color:#86EFAC">Tăng nhẹ</span> · '
 '<b>0/±1</b>: <span style="color:#94A3B8">Trung tính</span><br>'
 '• Score <b>−2/−3</b>: <span style="color:#FCA5A5">Giảm nhẹ</span> · '
 '<b>−4/−5</b>: <span style="color:#F87171">Giảm mạnh</span><br>'
 '• <b>Lưu ý:</b> Chỉ mang tính tham khảo học thuật, không phải lời khuyên đầu tư'
 if not _is_en else
 '• <b>Tier 1 — Primary trend:</b> price vs. Kumo (cloud) → ±1 point<br>'
 '• <b>Tier 2 — TK Cross:</b> Tenkan/Kijun crossover + position vs. Kumo → ±2/±1/0<br>'
 '• <b>Tier 3 — Chikou Span:</b> lagging line (−26) vs. past price → ±1 point<br>'
 '• <b>Tier 4 — Future Kumo:</b> projected cloud shape 26 sessions ahead → ±1 point<br><br>'
 '• Score <b>+4/+5</b>: <span style="color:#4ADE80">Strong bull</span> · '
 '<b>+2/+3</b>: <span style="color:#86EFAC">Mild bull</span> · '
 '<b>0/±1</b>: <span style="color:#94A3B8">Neutral</span><br>'
 '• Score <b>−2/−3</b>: <span style="color:#FCA5A5">Mild bear</span> · '
 '<b>−4/−5</b>: <span style="color:#F87171">Strong bear</span><br>'
 '• <b>Note:</b> For academic reference only, not investment advice'}
""")

        _guide_card(_IC_AI, '6. Trợ lý AI' if not _is_en else '6. AI Assistant',
                    '#0EA5E9', f"""
<b style="color:{_T['text_primary']}">{'Mục đích:' if not _is_en else 'Purpose:'}</b>
{'Hỏi đáp tự nhiên về mô hình dự báo, chỉ số đánh giá, tín hiệu Ichimoku, và phân tích mã đang chọn.'
 if not _is_en else 'Natural-language Q&A about forecasting models, evaluation metrics, Ichimoku signals, and analysis of the selected ticker.'}<br><br>

<b style="color:{_T['text_primary']}">{'Bạn có thể hỏi về:' if not _is_en else 'You can ask about:'}</b><br>
{'• Lý thuyết mô hình: <code>AR(p) là gì?</code>, <code>MLR và AR khác nhau thế nào?</code>, <code>CART hoạt động ra sao?</code><br>'
 '• Tham số: <code>nên chọn p bao nhiêu?</code>, <code>ý nghĩa tham số p</code><br>'
 '• Chỉ số: <code>MAPE, RMSE, MAE, R²adj</code> — công thức, so sánh, khi nào dùng<br>'
 '• Ichimoku: <code>4 tầng tín hiệu</code>, <code>Kumo là gì?</code>, <code>Chikou span</code><br>'
 '• Phân tích cụ thể: <code>phân tích FPT cho tôi</code>, <code>dự báo phiên tới</code>'
 if not _is_en else
 '• Model theory: <code>What is AR(p)?</code>, <code>AR vs MLR?</code>, <code>How does CART work?</code><br>'
 '• Parameters: <code>How to choose p?</code>, <code>Meaning of parameter p</code><br>'
 '• Metrics: <code>MAPE, RMSE, MAE, R²adj</code> — formulas, comparison, when to use<br>'
 '• Ichimoku: <code>4-tier signals</code>, <code>What is Kumo?</code>, <code>Chikou span</code><br>'
 '• Specific analysis: <code>Analyze FPT</code>, <code>Next-session forecast</code>'}<br><br>

<b style="color:{_T['text_primary']}">{'Tính năng hội thoại:' if not _is_en else 'Conversation features:'}</b><br>
{'• Nhiều hội thoại song song — tạo mới, đổi tên, xóa, lưu trữ lịch sử<br>'
 '• Tìm kiếm tin nhắn trong hội thoại hiện tại (highlight từ khoá)<br>'
 '• Sơ đồ trực quan tự động: AR lag diagram, thang MAPE, 4 tầng Ichimoku<br>'
 '• Song ngữ VI / EN theo ngôn ngữ app<br>'
 '• Cache câu trả lời 7 ngày — câu hỏi lặp lại trả lời tức thì<br>'
 '• Có chế độ rule-based khi AI không khả dụng (offline fallback)'
 if not _is_en else
 '• Multiple parallel conversations — create, rename, delete, preserve history<br>'
 '• In-conversation message search (keyword highlight)<br>'
 '• Auto-rendered visual diagrams: AR lag, MAPE scale, Ichimoku 4 tiers<br>'
 '• Bilingual VI / EN following app language<br>'
 '• 7-day response cache — repeated questions answered instantly<br>'
 '• Rule-based fallback when AI is unavailable (offline mode)'}
""")

        _guide_card(_IC_SET, 'Thanh điều khiển Sidebar' if not _is_en else 'Sidebar Controls',
                    '#64748B', f"""
<b style="color:{_T['text_primary']}">{'Điều hướng trang:' if not _is_en else 'Page navigation:'}</b><br>
{'• <b>Menu 7 trang</b> ở đầu sidebar: Dashboard · Phân tích · Lịch sử · Tín hiệu · Danh mục · Hướng dẫn · Trợ lý AI<br>'
 '• Bấm vào tên trang để chuyển qua lại — trạng thái mô hình được giữ nguyên (không train lại)'
 if not _is_en else
 '• <b>7-page menu</b> at top of sidebar: Dashboard · Analysis · History · Signals · Portfolio · Guide · AI Assistant<br>'
 '• Click a page name to switch — trained model state persists (no retraining)'}<br><br>

<b style="color:{_T['text_primary']}">{'Tham số mô hình:' if not _is_en else 'Model parameters:'}</b><br>
{'• <b>Mã cổ phiếu:</b> chọn FPT / HPG / VNM để xem dữ liệu tương ứng<br>'
 '• <b>Tỉ lệ Huấn luyện:</b> 70–90% — tỉ lệ dữ liệu dùng để train mô hình (còn lại để test)<br>'
 '• <b>Độ trễ (p):</b> số phiên quá khứ làm input cho AR/MLR/CART. Mặc định p=1; tăng 3–5 để thử. Quy tắc an toàn: p ≤ √n<br>'
 '• <b>Khoảng thời gian:</b> lọc dữ liệu lịch sử theo ngày <b>Từ</b> / <b>Đến</b> (định dạng YYYY/MM/DD)'
 if not _is_en else
 '• <b>Ticker:</b> select FPT / HPG / VNM to view corresponding data<br>'
 '• <b>Train Ratio:</b> 70–90% — proportion of data used for training (remainder for testing)<br>'
 '• <b>Lag Order (p):</b> past sessions as input for AR/MLR/CART. Default p=1; try 3–5. Safety: p ≤ √n<br>'
 '• <b>Date Range:</b> filter historical data by <b>From</b> / <b>To</b> (format YYYY/MM/DD)'}<br><br>

<b style="color:{_T['text_primary']}">{'Hành động & cài đặt:' if not _is_en else 'Actions & settings:'}</b><br>
{'• <b>Cập nhật dữ liệu</b> (nút trên cùng): xoá cache + tải lại dữ liệu mới nhất từ nguồn<br>'
 '• <b>Xuất báo cáo PDF</b> (hiện khi train xong): sinh PDF 10 trang → <b>Tải báo cáo PDF</b> → lưu file · Bấm <b>Tạo PDF mới</b> để làm lại<br>'
 '• <b>Dark / Light</b>: chuyển đổi chế độ giao diện sáng / tối (mọi biểu đồ + card đổi theo)<br>'
 '• <b>VI / EN</b>: chuyển đổi ngôn ngữ Tiếng Việt / English (cả sidebar, nội dung, và PDF đều đổi theo)'
 if not _is_en else
 '• <b>Refresh data</b> (top button): clears cache + reloads latest data from source<br>'
 '• <b>Export PDF Report</b> (appears after training): generates a 10-page PDF → <b>Download PDF Report</b> → save file · Click <b>Generate new PDF</b> to redo<br>'
 '• <b>Dark / Light</b>: toggle dark / light interface mode (all charts + cards follow)<br>'
 '• <b>VI / EN</b>: switch Vietnamese / English (sidebar, content, and PDF all follow)'}
""")

    st.markdown(f"""
<div style="background:{_T['bg_elevated']};border:1px solid {_T['border']};
            border-radius:12px;padding:20px 24px;margin-top:4px">
  <div style="font-size:14px;font-weight:700;color:{_T['text_primary']};margin-bottom:14px;
              display:flex;align-items:center;gap:8px">
    {_ic('info-circle-fill', _T['accent'], 17)}
    {'Chỉ số đánh giá mô hình' if not _is_en else 'Model Evaluation Metrics'}
  </div>
  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px">
    {''.join([
      f'<div style="background:{_T["bg_card"]};border-radius:8px;padding:12px 14px;'
      f'border:1px solid {_T["border"]}">'
      f'<div style="font-size:13px;font-weight:800;color:{c};margin-bottom:4px">{nm}</div>'
      f'<div style="font-size:11.5px;color:{_T["text_primary"]};line-height:1.5">{desc}</div>'
      f'</div>'
      for nm, c, desc in [
          ('MAPE', '#3B82F6',
           ('Sai số phần trăm tuyệt đối trung bình.<br><b>Mục tiêu:</b> &lt; 2%'
            if not _is_en else
            'Mean Absolute Percentage Error.<br><b>Target:</b> &lt; 2%')),
          ('RMSE', '#8B5CF6',
           ('Sai số bình phương trung bình gốc.<br><b>Đơn vị:</b> nghìn VNĐ'
            if not _is_en else
            'Root Mean Square Error.<br><b>Unit:</b> thousand VND')),
          ('MAE', '#F59E0B',
           ('Sai số tuyệt đối trung bình.<br><b>Đơn vị:</b> nghìn VNĐ'
            if not _is_en else
            'Mean Absolute Error.<br><b>Unit:</b> thousand VND')),
          ('R²adj', '#10B981',
           ('Hệ số xác định hiệu chỉnh.<br><b>Tốt nhất:</b> gần 1.0'
            if not _is_en else
            'Adjusted coefficient of determination.<br><b>Best:</b> close to 1.0')),
      ]
    ])}
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown(f"""
<div style="text-align:center;margin-top:20px;padding:14px;
            color:{_T['text_muted']};font-size:11px">
  {'Hệ thống được phát triển cho mục đích học thuật · NCKH TDTU 2026 · Không phải lời khuyên đầu tư'
   if not _is_en else
   'System developed for academic purposes · TDTU NCKH 2026 · Not investment advice'}
</div>
""", unsafe_allow_html=True)
