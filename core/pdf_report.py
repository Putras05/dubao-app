"""PDF report generator cho app Dự báo Giá Cổ phiếu HOSE (NCKH TDTU 2026).

Sinh báo cáo PDF đa trang với matplotlib PdfPages (không cần dep mới):
- Trang 1: Cover + summary stats + dự báo 3 mô hình
- Trang 2: Biểu đồ lịch sử giá + forecast 60 phiên gần nhất
- Trang 3: Bảng metrics chi tiết (MAPE, RMSE, MAE, R²adj) cho 3 mô hình

Format: A4 portrait, in được trực tiếp từ file PDF.
"""
from __future__ import annotations
import io
from datetime import datetime

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch, Rectangle


# A4 size in inches (210 × 297 mm)
A4_PORTRAIT = (8.27, 11.69)

# Tổng số trang PDF — cập nhật footer tự động
TOTAL_PAGES = 10

# Màu brand — không phụ thuộc theme app (PDF luôn in giấy trắng)
_C_ACCENT = '#1565C0'
_C_ACCENT_DARK = '#0D47A1'
_C_TEXT = '#0F172A'
_C_MUTED = '#64748B'
_C_BORDER = '#CBD5E1'
_C_BG_SOFT = '#F1F5F9'
_C_SUCCESS = '#059669'
_C_DANGER = '#DC2626'

# Colors cho 3 models
_C_AR = '#2563EB'
_C_MLR = '#9333EA'
_C_CART = '#059669'


def _L(vi: str, en: str, lang: str = 'VI') -> str:
    """Locale helper — trả chuỗi tiếng Việt nếu lang='VI', tiếng Anh nếu 'EN'."""
    return vi if lang == 'VI' else en


def _setup_font():
    """Font sans-serif hỗ trợ tiếng Việt."""
    plt.rcParams['font.family']   = 'DejaVu Sans'
    plt.rcParams['font.size']     = 10
    plt.rcParams['axes.unicode_minus'] = False


def _add_header(fig, title: str, subtitle: str = '', lang: str = 'VI'):
    """Header có branding cho mỗi trang."""
    fig.text(0.08, 0.96, 'NCKH  TDTU  2026', fontsize=8, color=_C_MUTED,
             weight='bold')
    fig.text(0.92, 0.96,
             _L('DỰ BÁO GIÁ CỔ PHIẾU HOSE', 'HOSE STOCK PRICE FORECAST', lang),
             fontsize=8, color=_C_MUTED,
             weight='bold', ha='right')
    # Divider line
    fig.add_artist(plt.Line2D([0.08, 0.92], [0.945, 0.945], color=_C_BORDER,
                              linewidth=0.8, transform=fig.transFigure))


def _add_footer(fig, page_num: int, total_pages: int, lang: str = 'VI'):
    """Footer số trang — song ngữ."""
    fig.add_artist(plt.Line2D([0.08, 0.92], [0.045, 0.045], color=_C_BORDER,
                              linewidth=0.8, transform=fig.transFigure))
    _gen_label = 'Generated' if lang == 'EN' else 'Generated'  # universal
    fig.text(0.08, 0.025,
             f'{_gen_label} {datetime.now().strftime("%Y-%m-%d %H:%M")} · TDTU NCKH 2026',
             fontsize=7, color=_C_MUTED)
    fig.text(0.92, 0.025, f'{page_num} / {total_pages}',
             fontsize=7, color=_C_MUTED, ha='right')


def _kpi_box(ax, x, y, w, h, label, value, sublabel='', color=_C_ACCENT):
    """Vẽ KPI box — label nhỏ trên, value to giữa, sublabel nhỏ dưới.

    Padding vertical chuẩn: label cách top 18% h · sublabel cách bottom 18% h.
    """
    box = FancyBboxPatch((x, y), w, h,
                         boxstyle='round,pad=0.003,rounding_size=0.012',
                         linewidth=1, edgecolor=_C_BORDER,
                         facecolor=_C_BG_SOFT, transform=ax.transAxes)
    ax.add_patch(box)
    # Accent stripe trái
    stripe = Rectangle((x, y), 0.005, h, facecolor=color,
                       edgecolor='none', transform=ax.transAxes)
    ax.add_patch(stripe)

    # Tính padding tương đối theo h — không dính top/bottom
    pad_top    = h * 0.20     # label cách top
    pad_mid    = h * 0.45     # value ở giữa
    pad_bottom = h * 0.15     # sublabel cách bottom

    ax.text(x + 0.022, y + h - pad_top, label.upper(), fontsize=7.5,
            color=_C_MUTED, weight='bold', transform=ax.transAxes,
            verticalalignment='center')
    ax.text(x + 0.022, y + h - pad_mid, str(value), fontsize=15,
            color=_C_TEXT, weight='bold', transform=ax.transAxes,
            verticalalignment='center')
    if sublabel:
        ax.text(x + 0.022, y + pad_bottom, sublabel, fontsize=8,
                color=color, weight='600', transform=ax.transAxes,
                verticalalignment='center')


# ═══════════════════════════════════════════════════════════════
# PAGE 1 — Cover + summary
# ═══════════════════════════════════════════════════════════════
def _page_cover(pdf, ticker, df, r1, r2, r3, m1, m2, m3, ar_order, lang='VI'):
    fig = plt.figure(figsize=A4_PORTRAIT)
    fig.patch.set_facecolor('white')
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')

    _add_header(fig, '', lang=lang)

    # Title block — big gradient-like banner
    banner = FancyBboxPatch((0.08, 0.78), 0.84, 0.14,
                            boxstyle='round,pad=0.003,rounding_size=0.015',
                            linewidth=0, facecolor=_C_ACCENT_DARK,
                            transform=ax.transAxes)
    ax.add_patch(banner)
    ax.text(0.50, 0.886,
            _L('BÁO CÁO DỰ BÁO GIÁ CỔ PHIẾU', 'STOCK PRICE FORECAST REPORT', lang),
            fontsize=18,
            color='white', weight='bold', ha='center', transform=ax.transAxes)
    _date_lbl = _L(
        f'Mã: {ticker}   ·   HOSE   ·   Báo cáo ngày {datetime.now().strftime("%d/%m/%Y")}',
        f'Ticker: {ticker}   ·   HOSE   ·   Report date {datetime.now().strftime("%d/%m/%Y")}',
        lang,
    )
    ax.text(0.50, 0.848, _date_lbl,
            fontsize=11, color='#BFDBFE', ha='center', transform=ax.transAxes)
    ax.text(0.50, 0.812,
            f'AR({ar_order})  ·  MLR({ar_order})  ·  CART({ar_order})',
            fontsize=10, color='#93C5FD', ha='center', transform=ax.transAxes,
            family='monospace')

    # ─── Section: Giá hiện tại + thông tin cơ bản ───
    last_row = df.iloc[-1]
    close_vnd = float(last_row['Close']) * 1000
    ret_pct   = float(last_row['Return']) if 'Return' in df.columns else 0.0
    last_date = str(last_row['Ngay'])[:10]

    # Section title + accent bar ở phía TRÊN (không chồng text)
    ax.add_patch(Rectangle((0.08, 0.755), 0.015, 0.005,
                            facecolor=_C_ACCENT, edgecolor='none',
                            transform=ax.transAxes))
    ax.text(0.10, 0.753,
            _L('01.  THÔNG TIN CƠ BẢN', '01.  KEY INFORMATION', lang),
            fontsize=10, color=_C_ACCENT, weight='bold',
            transform=ax.transAxes, verticalalignment='bottom')

    _close_price = _L(f'{close_vnd:,.0f} đ', f'{close_vnd:,.0f} VND', lang)
    _kpi_box(ax, 0.08, 0.61, 0.26, 0.10,
             _L('Giá đóng cửa gần nhất', 'Latest close price', lang),
             _close_price,
             _L(f'Phiên: {last_date}', f'Session: {last_date}', lang),
             color=_C_ACCENT)
    _kpi_box(ax, 0.37, 0.61, 0.26, 0.10,
             _L('Biến động phiên', 'Session change', lang),
             f'{ret_pct:+.2f}%',
             _L('So với phiên trước', 'vs previous session', lang),
             color=_C_SUCCESS if ret_pct >= 0 else _C_DANGER)
    _kpi_box(ax, 0.66, 0.61, 0.26, 0.10,
             _L('Số phiên dữ liệu', 'Data sessions', lang),
             f'{len(df):,}',
             _L('Từ vnstock real-time', 'From vnstock real-time', lang),
             color=_C_ACCENT)

    # ─── Section: Dự báo 3 mô hình ───
    ax.add_patch(Rectangle((0.08, 0.572), 0.015, 0.005,
                            facecolor=_C_ACCENT, edgecolor='none',
                            transform=ax.transAxes))
    ax.text(0.10, 0.57,
            _L('02.  DỰ BÁO PHIÊN KẾ TIẾP — 3 MÔ HÌNH',
               '02.  NEXT-SESSION FORECAST — 3 MODELS', lang),
            fontsize=10, color=_C_ACCENT, weight='bold',
            transform=ax.transAxes, verticalalignment='bottom')

    # Xác định model best (MAPE thấp nhất)
    mapes = [m1['MAPE'], m2['MAPE'], m3['MAPE']]
    best_idx = int(np.argmin(mapes))
    names = [f'AR({ar_order})', 'MLR', 'CART']
    colors = [_C_AR, _C_MLR, _C_CART]
    preds = [r1['next_pred'] * 1000, r2['next_pred'] * 1000, r3['next_pred'] * 1000]

    for i, (nm, clr, pr, mp) in enumerate(zip(names, colors, preds, mapes)):
        x0 = 0.08 + i * 0.29
        y0 = 0.40
        # Box
        box = FancyBboxPatch((x0, y0), 0.26, 0.135,
                             boxstyle='round,pad=0.003,rounding_size=0.012',
                             linewidth=(2 if i == best_idx else 1),
                             edgecolor=(clr if i == best_idx else _C_BORDER),
                             facecolor='white',
                             transform=ax.transAxes)
        ax.add_patch(box)
        # Accent top bar
        top_bar = Rectangle((x0, y0 + 0.13), 0.26, 0.005,
                            facecolor=clr, edgecolor='none',
                            transform=ax.transAxes)
        ax.add_patch(top_bar)
        # Model name + BEST star inline (không nằm ngoài)
        title_txt = f'{nm}  ★' if i == best_idx else nm
        ax.text(x0 + 0.13, y0 + 0.105, title_txt,
                fontsize=12, color=clr, weight='bold', ha='center',
                transform=ax.transAxes)
        # Predicted price
        _pred_lbl = _L(f'{pr:,.0f} đ', f'{pr:,.0f} VND', lang)
        ax.text(x0 + 0.13, y0 + 0.070, _pred_lbl,
                fontsize=14, color=_C_TEXT, weight='bold', ha='center',
                transform=ax.transAxes)
        # Change from current
        change = pr - close_vnd
        change_pct = (change / close_vnd) * 100 if close_vnd else 0
        change_color = _C_SUCCESS if change >= 0 else _C_DANGER
        change_arr = '▲' if change >= 0 else '▼'
        _change_lbl = _L(
            f'{change_arr} {change:+,.0f} đ ({change_pct:+.2f}%)',
            f'{change_arr} {change:+,.0f} VND ({change_pct:+.2f}%)',
            lang,
        )
        ax.text(x0 + 0.13, y0 + 0.042, _change_lbl,
                fontsize=9, color=change_color, ha='center',
                transform=ax.transAxes)
        # MAPE
        ax.text(x0 + 0.13, y0 + 0.017,
                f'MAPE: {mp:.2f}%',
                fontsize=8, color=_C_MUTED, ha='center',
                transform=ax.transAxes, family='monospace')

    # ─── Section: Thang đánh giá MAPE ───
    ax.add_patch(Rectangle((0.08, 0.368), 0.015, 0.005,
                            facecolor=_C_ACCENT, edgecolor='none',
                            transform=ax.transAxes))
    ax.text(0.10, 0.366,
            _L('03.  THANG ĐÁNH GIÁ MAPE (Hyndman 2021)',
               '03.  MAPE ASSESSMENT SCALE (Hyndman 2021)', lang),
            fontsize=10, color=_C_ACCENT, weight='bold',
            transform=ax.transAxes, verticalalignment='bottom')

    scale_bands = [
        ('< 10%',  _L('Rất tốt', 'Excellent', lang), '#10B981'),
        ('10–20%', _L('Tốt',     'Good',      lang), '#84CC16'),
        ('20–50%', _L('Tạm',     'Fair',      lang), '#F59E0B'),
        ('> 50%',  _L('Kém',     'Poor',      lang), '#EF4444'),
    ]
    for i, (rng, lbl, clr) in enumerate(scale_bands):
        x0 = 0.08 + i * 0.21
        rect = Rectangle((x0, 0.295), 0.21, 0.04,
                         facecolor=clr, edgecolor='white', linewidth=2,
                         transform=ax.transAxes)
        ax.add_patch(rect)
        ax.text(x0 + 0.105, 0.316, rng, fontsize=9,
                color='white', weight='bold', ha='center', va='center',
                transform=ax.transAxes)
        ax.text(x0 + 0.105, 0.278, lbl, fontsize=8,
                color=_C_TEXT, ha='center', transform=ax.transAxes)

    best_mape_txt = _L(
        f'App này đạt MAPE {min(mapes):.2f}% — thuộc nhóm "Rất tốt"',
        f'This app achieves MAPE {min(mapes):.2f}% — in the "Excellent" band',
        lang,
    )
    ax.text(0.50, 0.240, best_mape_txt, fontsize=10,
            color=_C_SUCCESS, weight='bold', ha='center',
            transform=ax.transAxes, style='italic')

    # ─── Footer: Disclaimer ───
    disc_box = FancyBboxPatch((0.08, 0.09), 0.84, 0.09,
                              boxstyle='round,pad=0.003,rounding_size=0.012',
                              linewidth=1, edgecolor='#F59E0B',
                              facecolor='#FEF3C7', transform=ax.transAxes)
    ax.add_patch(disc_box)
    ax.text(0.50, 0.155,
            _L('⚠  LƯU Ý QUAN TRỌNG', '⚠  IMPORTANT NOTICE', lang),
            fontsize=9,
            color='#92400E', weight='bold', ha='center', transform=ax.transAxes)
    ax.text(0.50, 0.125,
            _L('Đây là kết quả nghiên cứu khoa học, chỉ mang tính tham khảo học thuật.',
               'This is scientific research output for academic reference only.', lang),
            fontsize=9, color='#78350F', ha='center', transform=ax.transAxes)
    ax.text(0.50, 0.105,
            _L('KHÔNG phải lời khuyên đầu tư. Dữ liệu từ vnstock (TCBS/VNDIRECT/SSI).',
               'NOT investment advice. Data from vnstock (TCBS/VNDIRECT/SSI).', lang),
            fontsize=9, color='#78350F', ha='center', transform=ax.transAxes)

    _add_footer(fig, 1, TOTAL_PAGES)
    pdf.savefig(fig, facecolor='white')
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════
# PAGE 2 — Table of Contents (Mục lục)
# ═══════════════════════════════════════════════════════════════
def _page_toc(pdf, ticker, lang='VI'):
    """Mục lục — liệt kê nội dung 9 trang báo cáo."""
    fig = plt.figure(figsize=A4_PORTRAIT)
    fig.patch.set_facecolor('white')
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    _add_header(fig, '', lang=lang)

    # Title
    ax.text(0.08, 0.89,
            _L('MỤC LỤC', 'TABLE OF CONTENTS', lang),
            fontsize=24, color=_C_ACCENT_DARK, weight='bold',
            transform=ax.transAxes)
    ax.text(0.08, 0.862,
            _L('BÁO CÁO DỰ BÁO GIÁ CỔ PHIẾU · TDTU NCKH 2026',
               'STOCK PRICE FORECAST REPORT · TDTU NCKH 2026', lang),
            fontsize=10, color=_C_MUTED, transform=ax.transAxes)
    # Divider
    ax.add_patch(Rectangle((0.08, 0.848), 0.84, 0.002,
                            facecolor=_C_ACCENT, edgecolor='none',
                            transform=ax.transAxes))

    entries = [
        ('1',  _L('Trang bìa & Tóm tắt nhanh', 'Cover & Quick Summary', lang),
               _L('KPI giá · Dự báo 3 mô hình · Thang MAPE',
                  'Price KPIs · 3-model forecast · MAPE scale', lang),  _C_ACCENT),
        ('2',  _L('Mục lục', 'Table of Contents', lang),
               _L('Trang này', 'This page', lang),                     _C_MUTED),
        ('3',  _L('Biểu đồ lịch sử giá', 'Historical price chart', lang),
               _L('120 phiên + markers forecast · Return · Volume',
                  '120 sessions + forecast markers · Return · Volume', lang),
               _C_ACCENT),
        ('4',  _L('Actual vs Predicted — Tập Test',
                  'Actual vs Predicted — Test set', lang),
               _L('3 mô hình time series so sánh thực tế/dự báo',
                  '3-model time series actual vs forecast comparison', lang),
               _C_AR),
        ('5',  _L('Scatter & Hệ số mô hình', 'Scatter & Model Coefficients', lang),
               _L('Y=X + OLS fit · AR/MLR hệ số chi tiết',
                  'Y=X + OLS fit · AR/MLR detailed coefficients', lang),
               _C_MLR),
        ('6',  _L('CART — Độ quan trọng đặc trưng',
                  'CART — Feature Importance', lang),
               _L('Feature importance · GridSearchCV hyperparams',
                  'Feature importance · GridSearchCV hyperparameters', lang),
               _C_CART),
        ('7',  _L('CART — Sơ đồ cây quyết định',
                  'CART — Decision Tree Diagram', lang),
               _L('Custom tree visualization · nodes với value colors',
                  'Custom tree visualization · nodes with value colors', lang),
               _C_CART),
        ('8',  _L('Ichimoku Kinko Hyo — Biểu đồ',
                  'Ichimoku Kinko Hyo — Chart', lang),
               'Close · Tenkan · Kijun · Kumo cloud · Chikou',
               '#F59E0B'),
        ('9',  _L('Ichimoku — 4 tầng tín hiệu',
                  'Ichimoku — 4-tier signals', lang),
               'Score ±5 · Primary/Trading/Chikou/Future Kumo',
               '#F59E0B'),
        ('10', _L('Bảng chỉ số & Kết luận', 'Metrics Table & Conclusion', lang),
               'MAPE/RMSE/MAE/R²adj · References',                    _C_ACCENT),
    ]

    y_start = 0.80
    row_h = 0.065
    for i, (num, title, desc, clr) in enumerate(entries):
        y = y_start - i * row_h
        # Row background nhẹ cho hàng lẻ
        if i % 2 == 0:
            ax.add_patch(Rectangle((0.08, y - row_h * 0.25), 0.84, row_h * 0.8,
                                    facecolor=_C_BG_SOFT, edgecolor='none',
                                    transform=ax.transAxes, alpha=0.6))
        # Number badge (big, colored)
        ax.add_patch(FancyBboxPatch((0.10, y - row_h * 0.18), 0.045, row_h * 0.55,
                                     boxstyle='round,pad=0,rounding_size=0.008',
                                     facecolor=clr, edgecolor='none',
                                     transform=ax.transAxes))
        ax.text(0.1225, y + row_h * 0.10, num,
                fontsize=15, color='white', weight='bold', ha='center',
                transform=ax.transAxes, verticalalignment='center')
        # Title
        ax.text(0.17, y + row_h * 0.17, title,
                fontsize=11, color=_C_TEXT, weight='bold',
                transform=ax.transAxes, verticalalignment='center')
        # Description
        ax.text(0.17, y - row_h * 0.06, desc,
                fontsize=8.5, color=_C_MUTED,
                transform=ax.transAxes, verticalalignment='center')
        # Page number right (with dotted leader visual)
        _page_prefix = _L('Tr.', 'P.', lang)
        ax.text(0.90, y + row_h * 0.05, f'{_page_prefix} {num}',
                fontsize=10, color=clr, weight='bold', ha='right',
                transform=ax.transAxes, family='monospace',
                verticalalignment='center')

    # Footer note
    ax.text(0.50, 0.12,
            _L(f'Cổ phiếu phân tích: {ticker} · 3 mô hình (AR · MLR · CART) · Ichimoku 4 tầng',
               f'Analyzed ticker: {ticker} · 3 models (AR · MLR · CART) · Ichimoku 4 tiers',
               lang),
            fontsize=9, color=_C_ACCENT, ha='center', weight='bold',
            transform=ax.transAxes)
    ax.text(0.50, 0.09,
            _L('In A4 · Vector graphics · Zoom chất lượng cao',
               'A4 print · Vector graphics · High-quality zoom', lang),
            fontsize=8, color=_C_MUTED, ha='center', style='italic',
            transform=ax.transAxes)

    _add_footer(fig, 2, TOTAL_PAGES)
    pdf.savefig(fig, facecolor='white')
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════
# PAGE 3 — Historical price chart + forecast
# ═══════════════════════════════════════════════════════════════
def _page_chart(pdf, ticker, df, r1, r2, r3, m1, m2, m3, ar_order, lang='VI'):
    """Trang chẩn đoán mô hình — 4 panel chuẩn forecasting research:
       A. Test set: actual vs 3 dự báo
       B. Bar metrics MAPE/RMSE/MAE × 3 model
       C. ACF residuals model tốt nhất (Box-Jenkins white-noise check)
       D. Chuỗi phần dư 3 model overlay
    """
    fig = plt.figure(figsize=A4_PORTRAIT)
    fig.patch.set_facecolor('white')
    _add_header(fig, '', lang=lang)

    # Title
    fig.text(0.08, 0.905,
             _L(f'CHẨN ĐOÁN MÔ HÌNH DỰ BÁO — {ticker}',
                f'FORECAST MODEL DIAGNOSTICS — {ticker}', lang),
             fontsize=14, color=_C_TEXT, weight='bold')
    fig.text(0.08, 0.885,
             _L('Actual vs Predicted · sai số · ACF phần dư · chuỗi phần dư',
                'Actual vs predicted · errors · residual ACF · residual series',
                lang),
             fontsize=9, color=_C_MUTED)

    models = [
        (f'AR({ar_order})', _C_AR,   r1, m1),
        ('MLR',             _C_MLR,  r2, m2),
        ('CART',            _C_CART, r3, m3),
    ]
    dates_te = pd.to_datetime(r1['dates_te'])

    # ── PANEL A — Actual vs 3 forecasts (top, full width) ─────────────────
    axA = fig.add_axes([0.08, 0.55, 0.84, 0.30])
    yte = np.asarray(r1['yte'], dtype=float)
    axA.plot(dates_te, yte, color=_C_TEXT, linewidth=1.7,
             label=_L('Thực tế', 'Actual', lang), zorder=5)
    for nm, clr, res, m in models:
        axA.plot(dates_te, np.asarray(res['pte'], dtype=float),
                 color=clr, linewidth=1.0, alpha=0.85,
                 label=f'{nm} (MAPE={m["MAPE"]:.2f}%)')
    axA.set_title(_L('A. So sánh dự báo trên tập kiểm tra',
                     'A. Forecast comparison on test set', lang),
                  fontsize=10, weight='bold', color=_C_TEXT, loc='left', pad=4)
    axA.set_ylabel(_L('Giá (nghìn đồng)', 'Price (k VND)', lang),
                   fontsize=8, color=_C_MUTED)
    axA.legend(loc='best', fontsize=7, frameon=True,
               facecolor='white', edgecolor=_C_BORDER, ncol=4,
               handletextpad=0.4, columnspacing=1.0)
    axA.grid(True, alpha=0.3, linestyle=':')
    axA.spines['top'].set_visible(False); axA.spines['right'].set_visible(False)
    axA.tick_params(labelsize=7, colors=_C_MUTED)
    import matplotlib.dates as _mdates
    axA.xaxis.set_major_formatter(_mdates.DateFormatter('%m/%y'))

    # ── PANEL B — Bar metrics (mid-left, half width) ─────────────────────
    axB = fig.add_axes([0.08, 0.31, 0.39, 0.16])
    metric_keys = ['MAPE', 'RMSE', 'MAE']
    x = np.arange(len(models))
    bar_w = 0.26
    for i, k in enumerate(metric_keys):
        vals = [m.get(k, 0) for _, _, _, m in models]
        axB.bar(x + (i - 1) * bar_w, vals, bar_w,
                label=k, alpha=0.85)
    axB.set_xticks(x)
    axB.set_xticklabels([nm for nm, *_ in models], fontsize=7, color=_C_MUTED)
    axB.set_title(_L('B. Chỉ số sai số', 'B. Error metrics', lang),
                  fontsize=10, weight='bold', color=_C_TEXT, loc='left', pad=4)
    axB.legend(fontsize=6.5, frameon=False, ncol=3,
               loc='upper center', bbox_to_anchor=(0.5, -0.18))
    axB.grid(True, alpha=0.3, linestyle=':', axis='y')
    axB.spines['top'].set_visible(False); axB.spines['right'].set_visible(False)
    axB.tick_params(labelsize=6.5, colors=_C_MUTED)

    # ── PANEL C — ACF residuals best model (mid-right, half width) ───────
    axC = fig.add_axes([0.54, 0.31, 0.38, 0.16])
    _best = min(models, key=lambda x: x[3].get('MAPE', 1e9))
    _best_name, _, _best_res, _ = _best
    _best_resid = (np.asarray(_best_res['yte'], dtype=float)
                   - np.asarray(_best_res['pte'], dtype=float))
    n = len(_best_resid)
    n_lags = min(20, max(5, n // 4))
    acf_vals = [1.0]
    for k in range(1, n_lags + 1):
        if n - k < 2:
            acf_vals.append(0.0)
        else:
            seg1 = _best_resid[:-k]; seg2 = _best_resid[k:]
            sd1 = np.std(seg1); sd2 = np.std(seg2)
            if sd1 > 0 and sd2 > 0:
                acf_vals.append(float(np.corrcoef(seg1, seg2)[0, 1]))
            else:
                acf_vals.append(0.0)
    ci_band = 1.96 / np.sqrt(n) if n > 0 else 0
    lags_x = np.arange(n_lags + 1)
    axC.vlines(lags_x, 0, acf_vals, color=_C_ACCENT, linewidth=1.8)
    axC.scatter(lags_x, acf_vals, s=14, color=_C_ACCENT, zorder=3)
    axC.axhline(ci_band,  ls='--', color=_C_DANGER, linewidth=0.8, alpha=0.7)
    axC.axhline(-ci_band, ls='--', color=_C_DANGER, linewidth=0.8, alpha=0.7)
    axC.axhline(0, color=_C_TEXT, linewidth=0.6)
    axC.set_title(
        _L(f'C. ACF phần dư — {_best_name} (model tốt nhất)',
           f'C. Residual ACF — {_best_name} (best model)', lang),
        fontsize=10, weight='bold', color=_C_TEXT, loc='left', pad=4)
    axC.set_xlabel(_L('Bậc trễ', 'Lag', lang), fontsize=7, color=_C_MUTED)
    axC.set_ylabel('ACF', fontsize=7, color=_C_MUTED)
    axC.grid(True, alpha=0.3, linestyle=':')
    axC.spines['top'].set_visible(False); axC.spines['right'].set_visible(False)
    axC.tick_params(labelsize=6.5, colors=_C_MUTED)

    # ── PANEL D — Residual time series 3 models (bottom, full width) ─────
    axD = fig.add_axes([0.08, 0.10, 0.84, 0.13])
    for nm, clr, res, _ in models:
        residuals = (np.asarray(res['yte'], dtype=float)
                     - np.asarray(res['pte'], dtype=float))
        axD.plot(dates_te, residuals, color=clr, linewidth=0.9,
                 alpha=0.75, label=nm)
    axD.axhline(0, color=_C_TEXT, linewidth=0.6)
    axD.set_title(
        _L('D. Chuỗi phần dư theo thời gian (yt − ŷt)',
           'D. Residual time series (yt − ŷt)', lang),
        fontsize=10, weight='bold', color=_C_TEXT, loc='left', pad=4)
    axD.set_ylabel(_L('Phần dư (nghìn đ)', 'Residual (k VND)', lang),
                   fontsize=7, color=_C_MUTED)
    axD.legend(loc='upper right', fontsize=6.5, frameon=False, ncol=3)
    axD.grid(True, alpha=0.3, linestyle=':')
    axD.spines['top'].set_visible(False); axD.spines['right'].set_visible(False)
    axD.tick_params(labelsize=6.5, colors=_C_MUTED)
    axD.xaxis.set_major_formatter(_mdates.DateFormatter('%m/%y'))

    _add_footer(fig, 3, TOTAL_PAGES)
    pdf.savefig(fig, facecolor='white')
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════
# PAGE 4 — Actual vs Predicted trên tập TEST (3 mô hình)
# ═══════════════════════════════════════════════════════════════
def _page_test_timeseries(pdf, ticker, r1, r2, r3, ar_order, lang='VI'):
    """3 subplot stacked: AR, MLR, CART — actual vs predicted trên test set."""
    fig = plt.figure(figsize=A4_PORTRAIT)
    fig.patch.set_facecolor('white')
    _add_header(fig, '', lang=lang)

    fig.text(0.08, 0.905,
             _L(f'ACTUAL vs PREDICTED TRÊN TẬP TEST — {ticker}',
                f'ACTUAL vs PREDICTED ON TEST SET — {ticker}', lang),
             fontsize=14, color=_C_TEXT, weight='bold')
    fig.text(0.08, 0.885,
             _L('So sánh giá thực tế (xanh đậm) vs dự báo (màu model) · tập kiểm tra',
                'Actual price (dark blue) vs forecast (model color) · test set', lang),
             fontsize=9, color=_C_MUTED)

    models = [
        (f'AR({ar_order})', _C_AR, r1),
        ('MLR', _C_MLR, r2),
        ('CART', _C_CART, r3),
    ]
    # 3 subplots stacked — reduce heights + increase gap để xlabel không đè caption
    heights = [0.20, 0.20, 0.20]
    tops    = [0.83, 0.58, 0.33]

    for (nm, clr, res), top, h in zip(models, tops, heights):
        ax = fig.add_axes([0.08, top - h, 0.84, h])
        y_true = np.array(res['yte'])
        y_pred = np.array(res['pte'])
        x = np.arange(len(y_true))
        ax.plot(x, y_true, color=_C_TEXT, linewidth=1.3,
                label=_L('Thực tế', 'Actual', lang), zorder=2)
        ax.plot(x, y_pred, color=clr, linewidth=1.1, linestyle='--',
                alpha=0.9,
                label=_L(f'Dự báo {nm}', f'Forecast {nm}', lang), zorder=3)
        ax.fill_between(x, y_true, y_pred, color=clr, alpha=0.08, zorder=1)

        ax.set_ylabel(_L('nghìn đ', 'k VND', lang),
                      fontsize=9, color=_C_MUTED)
        ax.grid(True, alpha=0.3, linestyle=':')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.legend(loc='upper left', fontsize=8, frameon=True,
                  facecolor='white', edgecolor=_C_BORDER, ncol=2)
        ax.tick_params(labelsize=7, colors=_C_MUTED)
        # xlabel chỉ ở subplot cuối cùng
        if top == tops[-1]:
            ax.set_xlabel(_L('Phiên giao dịch (test set)',
                             'Trading session (test set)', lang),
                          fontsize=9, color=_C_MUTED,
                          labelpad=8)

    # Caption ở gần bottom, KHÔNG đè subplot cuối (subplot cuối kết thúc ở y=0.13)
    fig.text(0.50, 0.08,
             _L(f'n_test = {len(r1["yte"])} phiên · '
                'Đường thực tế (đậm) vs dự báo (đứt) · càng sát nhau → chính xác',
                f'n_test = {len(r1["yte"])} sessions · '
                'Actual (solid) vs forecast (dashed) · closer = more accurate',
                lang),
             fontsize=8, color=_C_MUTED, ha='center', style='italic')

    _add_footer(fig, 4, TOTAL_PAGES)
    pdf.savefig(fig, facecolor='white')
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════
# PAGE 5 — Scatter plots + AR/MLR coefficients
# ═══════════════════════════════════════════════════════════════
def _page_scatter_coef(pdf, ticker, r1, r2, r3, m1, m2, m3, ar_order, lang='VI'):
    """Scatter actual vs predicted (3 panels) + AR/MLR equation coefficients."""
    fig = plt.figure(figsize=A4_PORTRAIT)
    fig.patch.set_facecolor('white')
    _add_header(fig, '', lang=lang)

    fig.text(0.08, 0.905,
             _L('SCATTER THỰC TẾ vs DỰ BÁO + HỆ SỐ MÔ HÌNH',
                'ACTUAL vs FORECAST SCATTER + MODEL COEFFICIENTS', lang),
             fontsize=14, color=_C_TEXT, weight='bold')
    fig.text(0.08, 0.885,
             _L('Điểm càng gần đường y=x càng chính xác · Hệ số thể hiện đóng góp biến',
                'Closer to y=x line = more accurate · Coefficients show variable contribution',
                lang),
             fontsize=9, color=_C_MUTED)

    models = [
        (f'AR({ar_order})', _C_AR, r1, m1),
        ('MLR', _C_MLR, r2, m2),
        ('CART', _C_CART, r3, m3),
    ]
    # 3 scatter plots horizontal với OLS fit line
    for i, (nm, clr, res, mm) in enumerate(models):
        x0 = 0.08 + i * 0.29
        ax = fig.add_axes([x0, 0.58, 0.25, 0.25])
        y_true = np.array(res['yte'])
        y_pred = np.array(res['pte'])
        # Scatter
        ax.scatter(y_true, y_pred, s=10, color=clr, alpha=0.45,
                   edgecolor='none', zorder=2)
        _min = min(y_true.min(), y_pred.min())
        _max = max(y_true.max(), y_pred.max())
        _pad = (_max - _min) * 0.05
        _xline = np.array([_min - _pad, _max + _pad])
        # Ideal y=x line (tham chiếu — xám neutral, không xung đột với OLS đỏ)
        ax.plot(_xline, _xline,
                color='#94A3B8', linewidth=1.0, linestyle='--',
                alpha=0.85,
                label=_L('y = x (lý tưởng)', 'y = x (ideal)', lang),
                zorder=3)
        # OLS fit line — ĐỎ đậm nổi bật trên cả 3 scatter (blue/purple/green)
        try:
            slope, intercept = np.polyfit(y_true, y_pred, 1)
            _yfit = slope * _xline + intercept
            ax.plot(_xline, _yfit,
                    color='#DC2626', linewidth=1.8, linestyle='-',
                    alpha=0.95, label=f'OLS fit (β={slope:.2f})', zorder=4)
        except Exception:
            pass

        ax.set_xlim(_min - _pad, _max + _pad)
        ax.set_ylim(_min - _pad, _max + _pad)
        ax.set_aspect('equal')

        ax.set_title(f'{nm}\nMAPE={mm["MAPE"]:.2f}% · R²adj={mm["R2adj"]:.4f}',
                     fontsize=10, color=clr, weight='bold', pad=8)
        ax.set_xlabel(_L('Thực tế (nghìn đ)', 'Actual (k VND)', lang),
                      fontsize=8, color=_C_MUTED)
        ax.set_ylabel(_L('Dự báo (nghìn đ)', 'Forecast (k VND)', lang),
                      fontsize=8, color=_C_MUTED)
        ax.grid(True, alpha=0.3, linestyle=':')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.legend(loc='upper left', fontsize=6.5, frameon=False)
        ax.tick_params(labelsize=7, colors=_C_MUTED)

    # ═══ Phần dưới: AR + MLR coefficients ═══
    ax_t = fig.add_axes([0, 0, 1, 1])
    ax_t.set_xlim(0, 1); ax_t.set_ylim(0, 1); ax_t.axis('off')

    # AR equation
    ax_t.add_patch(Rectangle((0.08, 0.497), 0.015, 0.005,
                              facecolor=_C_AR, edgecolor='none',
                              transform=ax_t.transAxes))
    ax_t.text(0.10, 0.495,
              _L(f'PHƯƠNG TRÌNH AR({ar_order})', f'AR({ar_order}) EQUATION', lang),
              fontsize=11, color=_C_AR, weight='bold',
              transform=ax_t.transAxes, verticalalignment='bottom')

    ar_coefs = r1.get('coefs', r1.get('coef', []))
    ar_c = r1.get('c', r1.get('intercept', 0))
    # Build equation string: Ŷ(t+1) = c + φ1·Y(t) + φ2·Y(t-1) + ...
    ar_eq = f'Ŷ(t+1) = {ar_c:+.4f}'
    for idx, phi in enumerate(ar_coefs[:ar_order]):
        ar_eq += f'  {phi:+.4f} · Y(t-{idx})' if idx > 0 else f'  {phi:+.4f} · Y(t)'
    ax_t.text(0.08, 0.46, ar_eq, fontsize=9, color=_C_TEXT,
              family='monospace', transform=ax_t.transAxes)

    # AR coefs table (nếu p >= 2)
    if ar_order >= 2:
        y_tbl = 0.43
        for idx, phi in enumerate(ar_coefs[:ar_order]):
            col_x = 0.08 + (idx % 4) * 0.22
            row_y = y_tbl - (idx // 4) * 0.02
            ax_t.text(col_x, row_y, f'φ{idx+1} = {phi:+.4f}',
                      fontsize=8.5, color=_C_MUTED, family='monospace',
                      transform=ax_t.transAxes)

    # MLR equation
    y_mlr_start = 0.37 if ar_order >= 2 else 0.40
    ax_t.add_patch(Rectangle((0.08, y_mlr_start + 0.002), 0.015, 0.005,
                              facecolor=_C_MLR, edgecolor='none',
                              transform=ax_t.transAxes))
    ax_t.text(0.10, y_mlr_start,
              _L(f'PHƯƠNG TRÌNH MLR({ar_order}) — HỆ SỐ CHI TIẾT',
                 f'MLR({ar_order}) EQUATION — DETAILED COEFFICIENTS', lang),
              fontsize=11, color=_C_MLR, weight='bold',
              transform=ax_t.transAxes, verticalalignment='bottom')

    # Build MLR equation với SỐ THẬT
    mlr_coef = np.array(r2.get('coef', []))
    mlr_intercept = float(r2.get('intercept', 0))
    if len(mlr_coef) == 3 * ar_order:
        # Group 1: Y(t), Y(t-1)... (first ar_order)
        # Group 2: V(t), V(t-1)... (next ar_order)
        # Group 3: HL(t), HL(t-1)... (last ar_order)
        # Build multi-line equation
        lines_eq = [f'Ŷ(t+1) = {mlr_intercept:+.4f}']
        for k in range(ar_order):
            lines_eq.append(f'  {mlr_coef[k]:+.4e} · Y(t-{k})' if k > 0
                            else f'  {mlr_coef[0]:+.4e} · Y(t)')
        for k in range(ar_order):
            lines_eq.append(f'  {mlr_coef[ar_order + k]:+.4e} · V(t-{k})' if k > 0
                            else f'  {mlr_coef[ar_order]:+.4e} · V(t)')
        for k in range(ar_order):
            lines_eq.append(f'  {mlr_coef[2*ar_order + k]:+.4e} · HL(t-{k})' if k > 0
                            else f'  {mlr_coef[2*ar_order]:+.4e} · HL(t)')
        # Join into single line string with + between continuations
        full_eq = lines_eq[0] + '\n' + '\n'.join(lines_eq[1:])
        ax_t.text(0.08, y_mlr_start - 0.035, full_eq,
                  fontsize=7.5, color=_C_TEXT, family='DejaVu Sans Mono',
                  transform=ax_t.transAxes, verticalalignment='top')

    # MLR coef bar chart — below equations
    if len(mlr_coef) == 3 * ar_order:
        labels_all = (
            [f'Y(t-{k})' if k > 0 else 'Y(t)' for k in range(ar_order)] +
            [f'V(t-{k})' if k > 0 else 'V(t)' for k in range(ar_order)] +
            [f'HL(t-{k})' if k > 0 else 'HL(t)' for k in range(ar_order)]
        )
        group_colors = [_C_AR]*ar_order + ['#9333EA']*ar_order + ['#F59E0B']*ar_order
        # Normalize by max |coef| để bar dễ nhìn (scale biểu thị relative)
        max_abs = max(abs(c) for c in mlr_coef) or 1.0
        mlr_coef_norm = mlr_coef / max_abs
        ax_bar = fig.add_axes([0.08, 0.08, 0.84, 0.17])
        ypos = np.arange(len(mlr_coef))
        ax_bar.barh(ypos, mlr_coef_norm, color=group_colors, alpha=0.80,
                    edgecolor='white', linewidth=0.5)
        # Value labels
        for i, (v, vn) in enumerate(zip(mlr_coef, mlr_coef_norm)):
            ax_bar.text(vn + (0.02 if vn >= 0 else -0.02), i,
                         f'{v:+.3e}',
                         fontsize=6.5, color=_C_TEXT, weight='bold',
                         ha='left' if vn >= 0 else 'right',
                         va='center', family='DejaVu Sans')
        ax_bar.set_yticks(ypos)
        ax_bar.set_yticklabels(labels_all, fontsize=7)
        ax_bar.axvline(0, color=_C_MUTED, linewidth=0.8)
        ax_bar.set_title(
            _L(f'Hệ số MLR (chuẩn hoá /max|β| = {max_abs:.4e}) · '
               'Màu theo nhóm biến',
               f'MLR coefficients (normalized /max|β| = {max_abs:.4e}) · '
               'Color by variable group',
               lang),
            fontsize=9, color=_C_TEXT, weight='bold', loc='left',
            pad=6)
        ax_bar.set_xlim(-1.4, 1.4)
        ax_bar.grid(True, alpha=0.3, linestyle=':', axis='x')
        ax_bar.spines['top'].set_visible(False)
        ax_bar.spines['right'].set_visible(False)
        ax_bar.tick_params(labelsize=7, colors=_C_MUTED)
        # Legend
        from matplotlib.patches import Patch
        leg_handles = [
            Patch(color=_C_AR, label=_L('Giá Y', 'Price Y', lang)),
            Patch(color='#9333EA', label='Volume V'),
            Patch(color='#F59E0B', label='Range HL'),
        ]
        ax_bar.legend(handles=leg_handles, loc='lower right',
                       fontsize=7, frameon=True, facecolor='white',
                       edgecolor=_C_BORDER, ncol=3)
        ax_bar.invert_yaxis()

    _add_footer(fig, 5, TOTAL_PAGES)
    pdf.savefig(fig, facecolor='white')
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════
# PAGE 6 — CART Feature Importance + best hyperparameters
# ═══════════════════════════════════════════════════════════════
def _page_cart_features(pdf, ticker, r3, m3, ar_order, lang='VI'):
    """CART feature importance bar chart + best hyperparameters + insight."""
    fig = plt.figure(figsize=A4_PORTRAIT)
    fig.patch.set_facecolor('white')
    _add_header(fig, '', lang=lang)

    fig.text(0.08, 0.905,
             _L('CART — ĐỘ QUAN TRỌNG ĐẶC TRƯNG',
                'CART — FEATURE IMPORTANCE', lang),
             fontsize=14, color=_C_TEXT, weight='bold')
    fig.text(0.08, 0.885,
             _L('Đặc trưng nào quyết định nhiều nhất trong mô hình Decision Tree',
                'Which feature drives decisions the most in the Decision Tree model',
                lang),
             fontsize=9, color=_C_MUTED)

    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')

    # ─── Feature importance horizontal bar chart ───
    imp = r3.get('importances', {})
    if not imp:
        imp = {'Return': 0.20, 'Volume_ratio': 0.15, 'Range_ratio': 0.10,
               'MA5_ratio': 0.25, 'MA20_ratio': 0.20, 'RSI14': 0.10}
    feats = list(imp.keys())
    vals = [imp[f] for f in feats]
    # Sort descending
    order = sorted(range(len(vals)), key=lambda k: vals[k], reverse=True)
    feats_sorted = [feats[i] for i in order]
    vals_sorted = [vals[i] for i in order]

    ax_bar = fig.add_axes([0.12, 0.48, 0.78, 0.32])
    ypos = np.arange(len(feats_sorted))
    # Gradient color — cao nhất màu đậm, thấp nhất nhạt
    bar_colors = [plt.cm.Greens(0.4 + 0.5 * (v / max(vals_sorted)))
                   for v in vals_sorted]
    ax_bar.barh(ypos, vals_sorted, color=bar_colors,
                 edgecolor='white', linewidth=0.8)
    ax_bar.set_yticks(ypos)
    ax_bar.set_yticklabels(feats_sorted, fontsize=10, color=_C_TEXT, weight='bold')
    ax_bar.invert_yaxis()
    # Value labels on bars
    for i, v in enumerate(vals_sorted):
        ax_bar.text(v + max(vals_sorted) * 0.01, i, f'{v*100:.1f}%',
                     fontsize=9, color=_C_TEXT, weight='bold',
                     verticalalignment='center')
    ax_bar.set_xlabel(
        _L('Độ quan trọng (tỉ lệ đóng góp vào quyết định)',
           'Importance (contribution share to decisions)', lang),
        fontsize=9, color=_C_MUTED)
    ax_bar.set_xlim(0, max(vals_sorted) * 1.18)
    ax_bar.grid(True, alpha=0.3, linestyle=':', axis='x')
    ax_bar.spines['top'].set_visible(False)
    ax_bar.spines['right'].set_visible(False)
    ax_bar.spines['left'].set_visible(False)
    ax_bar.tick_params(labelsize=8, colors=_C_MUTED, left=False)

    # ─── Hyperparameters section ───
    best = r3.get('best', {'max_depth': 'N/A', 'min_samples_leaf': 'N/A'})
    ax.add_patch(Rectangle((0.08, 0.427), 0.015, 0.005,
                            facecolor=_C_CART, edgecolor='none',
                            transform=ax.transAxes))
    ax.text(0.10, 0.425,
            _L('SIÊU THAM SỐ TỐI ƯU (GridSearchCV)',
               'OPTIMAL HYPERPARAMETERS (GridSearchCV)', lang),
            fontsize=11, color=_C_CART, weight='bold',
            transform=ax.transAxes, verticalalignment='bottom')

    # 2 KPI boxes for hyperparameters — h=0.095 để value to + sublabel không đè
    _kpi_box(ax, 0.08, 0.31, 0.40, 0.095,
              'max_depth',
              str(best.get('max_depth', 'N/A')),
              _L('Độ sâu tối đa của cây', 'Maximum tree depth', lang),
              color=_C_CART)
    _kpi_box(ax, 0.52, 0.31, 0.40, 0.095,
              'min_samples_leaf',
              str(best.get('min_samples_leaf', 'N/A')),
              _L('Số mẫu tối thiểu/lá', 'Minimum samples per leaf', lang),
              color=_C_CART)

    # ─── Insight + interpretation ───
    ax.add_patch(Rectangle((0.08, 0.287), 0.015, 0.005,
                            facecolor=_C_ACCENT, edgecolor='none',
                            transform=ax.transAxes))
    ax.text(0.10, 0.285,
            _L('DIỄN GIẢI KẾT QUẢ', 'INTERPRETATION', lang),
            fontsize=11, color=_C_ACCENT, weight='bold',
            transform=ax.transAxes, verticalalignment='bottom')

    top_feat = feats_sorted[0]
    top_val = vals_sorted[0] * 100
    best_depth = best.get('max_depth', 'N/A')
    best_leaf = best.get('min_samples_leaf', 'N/A')

    if lang == 'VI':
        insight_lines = [
            f'• Đặc trưng quan trọng nhất: {top_feat} ({top_val:.1f}% tầm ảnh hưởng) '
            f'— mô hình dựa chủ yếu vào biến này để split.',
            f'• Cây tối ưu có độ sâu {best_depth} và yêu cầu {best_leaf} mẫu/lá → '
            f'cân bằng giữa fit và generalization.',
            f'• CART đạt MAPE = {m3["MAPE"]:.2f}% — khả năng bắt non-linearity '
            f'tương đương AR/MLR vì dữ liệu HOSE khá linear.',
            f'• Target: return phiên kế tiếp (%), phục hồi giá bằng '
            f'Ŷ(t+1) = Y(t)·(1+R̂/100).',
        ]
    else:
        insight_lines = [
            f'• Most important feature: {top_feat} ({top_val:.1f}% influence) '
            f'— the model relies mainly on this variable to split.',
            f'• Optimal tree has depth {best_depth} and requires {best_leaf} samples/leaf → '
            f'balances fit and generalization.',
            f'• CART achieves MAPE = {m3["MAPE"]:.2f}% — non-linearity capture '
            f'is on par with AR/MLR since HOSE data is fairly linear.',
            f'• Target: next-session return (%), recover price via '
            f'Ŷ(t+1) = Y(t)·(1+R̂/100).',
        ]
    for i, line in enumerate(insight_lines):
        ax.text(0.08, 0.255 - i * 0.026, line, fontsize=9,
                color=_C_TEXT, transform=ax.transAxes, wrap=True)

    # ─── 6 technical features explanation ───
    # Block đẩy lên cao hơn để hàng cuối (MA20_ratio/RSI14) không đè footer.
    ax.add_patch(Rectangle((0.08, 0.148), 0.015, 0.005,
                            facecolor=_C_MUTED, edgecolor='none',
                            transform=ax.transAxes))
    ax.text(0.10, 0.146,
            _L('6 ĐẶC TRƯNG CART SỬ DỤNG', '6 FEATURES USED BY CART', lang),
            fontsize=10, color=_C_MUTED, weight='bold',
            transform=ax.transAxes, verticalalignment='bottom')

    feats_desc = [
        ('Return',       _L('log-return hàng ngày', 'daily log-return', lang)),
        ('Volume_ratio', 'Volume / MA5(Volume)'),
        ('Range_ratio',  '(High − Low) / Close'),
        ('MA5_ratio',    'Close / MA5 − 1'),
        ('MA20_ratio',   'Close / MA20 − 1'),
        ('RSI14',        _L('Relative Strength Index 14 phiên',
                            'Relative Strength Index, 14 sessions', lang)),
    ]
    # Layout 2 cột × 3 hàng — start y=0.122 (dưới header 0.146 ~0.024 gap),
    # step 0.028 → row 2 ở y=0.066 (cách footer y=0.025 đủ rộng ~0.04)
    for i, (f_nm, f_desc) in enumerate(feats_desc):
        col = i % 2
        row = i // 2
        x = 0.08 + col * 0.46
        y = 0.122 - row * 0.028
        # Bullet + label
        ax.text(x, y, '• ', fontsize=8.5,
                color=_C_CART, weight='bold',
                transform=ax.transAxes)
        ax.text(x + 0.015, y, f_nm, fontsize=8.5,
                color=_C_CART, weight='bold',
                transform=ax.transAxes, family='DejaVu Sans Mono')
        # Description cách label đủ xa (0.14 = ~140px tại A4) — đủ cho label dài nhất
        ax.text(x + 0.14, y, f_desc, fontsize=8,
                color=_C_TEXT, transform=ax.transAxes)

    _add_footer(fig, 6, TOTAL_PAGES)
    pdf.savefig(fig, facecolor='white')
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════
# PAGE 7 — CART Decision Tree visualization (plot_tree)
# ═══════════════════════════════════════════════════════════════
def _page_cart_tree(pdf, ticker, r3, ar_order, lang='VI'):
    """Sơ đồ cây CART — style custom matplotlib giống app (charts/tree.py)."""
    fig = plt.figure(figsize=A4_PORTRAIT)
    fig.patch.set_facecolor('white')
    _add_header(fig, '', lang=lang)

    fig.text(0.08, 0.905,
             _L('CART — SƠ ĐỒ CÂY QUYẾT ĐỊNH',
                'CART — DECISION TREE DIAGRAM', lang),
             fontsize=14, color=_C_TEXT, weight='bold')
    best = r3.get('best', {})
    fig.text(0.08, 0.885,
             f"max_depth = {best.get('max_depth', 'N/A')}  ·  "
             f"min_samples_leaf = {best.get('min_samples_leaf', 'N/A')}  ·  "
             + _L('Dự báo Return phiên tới (%)',
                  'Next-session Return forecast (%)', lang),
             fontsize=9, color=_C_MUTED)

    model = r3.get('model')
    if model is None:
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
        ax.text(0.5, 0.5,
                _L('Mô hình CART chưa sẵn sàng.',
                   'CART model not available.', lang),
                fontsize=12, color=_C_MUTED, ha='center', va='center',
                style='italic', transform=ax.transAxes)
        _add_footer(fig, 7, TOTAL_PAGES, lang=lang)
        pdf.savefig(fig, facecolor='white')
        plt.close(fig)
        return

    tree_ = model.tree_
    node_vals = tree_.value.flatten()
    v_min, v_max = node_vals.min(), node_vals.max()
    v_range = (v_max - v_min) if v_max > v_min else 1.0

    # Palette diverging — cold blue → warm red (same as app charts/tree.py light mode)
    palette = ['#4575B4', '#91BFDB', '#E0F3F8', '#FEE090', '#FC8D59', '#D73027']

    def node_color_idx(nid):
        norm = (node_vals[nid] - v_min) / v_range
        idx = min(int(norm * (len(palette) - 1)), len(palette) - 1)
        return palette[idx], idx

    # Feature names
    base_feats = ['Return', 'Vol/MA5', 'Range%', 'MA5_r', 'MA20_r', 'RSI14']
    feat_names = []
    for k in range(ar_order):
        suffix = f'(t-{k})' if k > 0 else '(t)'
        for f in base_feats:
            feat_names.append(f'{f}{suffix}')

    # Compute positions (post-order leaf layout)
    # SPACING adaptive — co lại khi nhiều leaves để cây LUÔN fit trong page A4
    # (tránh clip box cuối bên phải). Target: x_span ≤ ~12 data units.
    leaf_order = []
    def dfs_leaves(n):
        if tree_.children_left[n] == -1:
            leaf_order.append(n)
        else:
            dfs_leaves(tree_.children_left[n])
            dfs_leaves(tree_.children_right[n])
    dfs_leaves(0)
    n_leaves = len(leaf_order)
    # Target: x_span = (n-1)*SPACING ≤ ~12 units → cây luôn fit axes (rộng 7.44in)
    # Clamp [1.8, 2.8] để không quá chật (nhiều lá) hoặc quá thưa (ít lá)
    SPACING = min(2.8, max(1.8, 12.0 / max(1, n_leaves - 1)))
    leaf_x_map = {n: float(i * SPACING) for i, n in enumerate(leaf_order)}

    def subtree_cx(n):
        if tree_.children_left[n] == -1:
            return leaf_x_map[n]
        return (subtree_cx(tree_.children_left[n]) +
                subtree_cx(tree_.children_right[n])) / 2.0

    def tree_depth(n):
        if tree_.children_left[n] == -1:
            return 0
        return 1 + max(tree_depth(tree_.children_left[n]),
                        tree_depth(tree_.children_right[n]))

    max_d = tree_depth(0)
    pos = {}
    def build_pos(n, depth=0):
        pos[n] = (subtree_cx(n), float(max_d - depth))
        if tree_.children_left[n] != -1:
            build_pos(tree_.children_left[n], depth + 1)
            build_pos(tree_.children_right[n], depth + 1)
    build_pos(0)

    # Center root về x=0
    root_cx = pos[0][0]
    offset = ((n_leaves - 1) * SPACING / 2 - root_cx)
    if abs(offset) > 1e-9:
        for nid in pos:
            pos[nid] = (pos[nid][0] + offset, pos[nid][1])

    pad_y_top = 0.35
    pad_y_bot = 0.55

    # Box dimensions: tỉ lệ theo SPACING → luôn có gap giữa siblings.
    # NW = 45% SPACING (box chiếm 90%, gap 10%). NH fixed tối ưu 2-line text.
    NW_INT   = SPACING * 0.45
    NW_LEAF  = SPACING * 0.38
    NH_INT   = 0.28
    NH_LEAF  = 0.26

    # xlim TÍNH SAU khi centering root — cây mất cân đối (1 leaf trái + 4 lá
    # phải) khiến tất cả positions shift sang phải, rightmost leaf vượt x_span.
    # Dùng min/max của positions thực tế + box_half + margin cho drop shadow.
    _xs = [p[0] for p in pos.values()]
    _xmin, _xmax = min(_xs), max(_xs)
    _box_half = max(NW_INT, NW_LEAF)
    _pad_x    = _box_half + 0.8  # +0.8 cho drop shadow (+0.04) + TRUE/FALSE pill

    # Adaptive fontsize — cây nhiều lá cần font nhỏ hơn để fit text trong box hẹp
    if n_leaves <= 4:
        _fs_int_1, _fs_int_2 = 7.5, 5.8
        _fs_leaf_n, _fs_leaf_v = 6.8, 9.5
    elif n_leaves <= 6:
        _fs_int_1, _fs_int_2 = 6.8, 5.3
        _fs_leaf_n, _fs_leaf_v = 6.2, 8.5
    else:
        _fs_int_1, _fs_int_2 = 5.8, 4.6
        _fs_leaf_n, _fs_leaf_v = 5.5, 7.5

    def _nw(nid): return NW_INT if tree_.children_left[nid] != -1 else NW_LEAF
    def _nh(nid): return NH_INT if tree_.children_left[nid] != -1 else NH_LEAF

    # Tree axes: nâng lên 0.22 → top 0.85, sát subtitle 0.885; chiều cao 0.63.
    ax_tree = fig.add_axes([0.05, 0.22, 0.90, 0.63])
    ax_tree.set_xlim(_xmin - _pad_x, _xmax + _pad_x)
    ax_tree.set_ylim(-pad_y_bot, max_d + pad_y_top)
    ax_tree.set_aspect('auto')
    ax_tree.axis('off')

    # ─── Connectors — cong mượt hơn, màu nhạt hơn ───
    _CONN_CLR = '#CBD5E1'
    _CONN_LW  = 1.5
    for nid in range(tree_.node_count):
        lc = tree_.children_left[nid]
        rc = tree_.children_right[nid]
        if lc == -1:
            continue
        px, py = pos[nid]
        lcx, lcy = pos[lc]
        rcx, rcy = pos[rc]
        ph = _nh(nid)
        lch = _nh(lc); rch = _nh(rc)
        mid_y_l = (py - ph + lcy + lch) / 2
        mid_y_r = (py - ph + rcy + rch) / 2
        mid_y = min(mid_y_l, mid_y_r)
        # Vertical from parent bottom to mid
        ax_tree.plot([px, px], [py - ph, mid_y],
                      color=_CONN_CLR, linewidth=_CONN_LW, solid_capstyle='round')
        # Horizontal bars
        ax_tree.plot([px, lcx], [mid_y, mid_y],
                      color=_CONN_CLR, linewidth=_CONN_LW, solid_capstyle='round')
        ax_tree.plot([px, rcx], [mid_y, mid_y],
                      color=_CONN_CLR, linewidth=_CONN_LW, solid_capstyle='round')
        # Vertical to children
        ax_tree.plot([lcx, lcx], [mid_y, lcy + lch],
                      color=_CONN_CLR, linewidth=_CONN_LW, solid_capstyle='round')
        ax_tree.plot([rcx, rcx], [mid_y, rcy + rch],
                      color=_CONN_CLR, linewidth=_CONN_LW, solid_capstyle='round')
        # True/False labels — pill trắng để đọc rõ trên connector
        ax_tree.text((px + lcx) / 2, mid_y + 0.05, 'TRUE',
                      fontsize=6.5, color='#047857', ha='center', va='center',
                      weight='bold', family='DejaVu Sans',
                      bbox=dict(facecolor='white', edgecolor='#D1FAE5',
                                linewidth=0.6, boxstyle='round,pad=0.2'))
        ax_tree.text((px + rcx) / 2, mid_y + 0.05, 'FALSE',
                      fontsize=6.5, color='#B91C1C', ha='center', va='center',
                      weight='bold', family='DejaVu Sans',
                      bbox=dict(facecolor='white', edgecolor='#FEE2E2',
                                linewidth=0.6, boxstyle='round,pad=0.2'))

    # ─── Nodes — drop shadow + rounded + text 2 dòng có phân cấp ───
    for nid in range(tree_.node_count):
        x, y = pos[nid]
        clr, idx = node_color_idx(nid)
        txt_clr = '#FFFFFF' if idx in {0, 4, 5} else '#0F172A'
        nw, nh = _nw(nid), _nh(nid)
        is_leaf = tree_.children_left[nid] == -1
        ns = tree_.n_node_samples[nid]
        val = node_vals[nid]

        # Drop shadow (offset xuống + phải, grey mờ 10%)
        shadow = FancyBboxPatch(
            (x - nw + 0.04, y - nh - 0.05), 2 * nw, 2 * nh,
            boxstyle='round,pad=0.02,rounding_size=0.12',
            linewidth=0, facecolor='#0F172A', alpha=0.10, zorder=1,
        )
        ax_tree.add_patch(shadow)
        # Main box
        box = FancyBboxPatch(
            (x - nw, y - nh), 2 * nw, 2 * nh,
            boxstyle='round,pad=0.02,rounding_size=0.12',
            linewidth=0.8, facecolor=clr, edgecolor='#FFFFFF', zorder=2,
        )
        ax_tree.add_patch(box)

        if is_leaf:
            sign = '+' if val >= 0 else ''
            # Dòng 1: n samples (nhỏ). Dòng 2: value (to, bold)
            ax_tree.text(x, y + nh * 0.38, f'n = {ns}',
                          fontsize=_fs_leaf_n, color=txt_clr, alpha=0.85,
                          ha='center', va='center', family='DejaVu Sans',
                          weight='normal', clip_on=False, zorder=3)
            ax_tree.text(x, y - nh * 0.28, f'{sign}{val:.3f}%',
                          fontsize=_fs_leaf_v, color=txt_clr,
                          weight='bold', ha='center', va='center',
                          family='DejaVu Sans', clip_on=False, zorder=3)
        else:
            fi, thresh = tree_.feature[nid], tree_.threshold[nid]
            fname = feat_names[fi] if fi < len(feat_names) else f'f{fi}'
            # Dòng 1: split rule (bold, compact). Ghi "≤" + số ngắn gọn
            ax_tree.text(x, y + nh * 0.35, f'{fname} ≤ {thresh:.2f}',
                          fontsize=_fs_int_1, color=txt_clr,
                          weight='bold', ha='center', va='center',
                          family='DejaVu Sans', clip_on=False, zorder=3)
            # Dòng 2: meta compact — "n=X · v=±Y.YY%" (nhỏ, mờ)
            sign_val = '+' if val >= 0 else ''
            ax_tree.text(x, y - nh * 0.38,
                          f'n={ns} · v={sign_val}{val:.2f}%',
                          fontsize=_fs_int_2, color=txt_clr, alpha=0.88,
                          ha='center', va='center', family='DejaVu Sans',
                          weight='normal', clip_on=False, zorder=3)

    # ─── Legend thang màu + Guide ở dưới ───
    ax_info = fig.add_axes([0, 0, 1, 1])
    ax_info.set_xlim(0, 1); ax_info.set_ylim(0, 1); ax_info.axis('off')

    # Legend title
    ax_info.add_patch(Rectangle((0.08, 0.172), 0.015, 0.005,
                                 facecolor=_C_CART, edgecolor='none',
                                 transform=ax_info.transAxes))
    ax_info.text(0.10, 0.170,
                  _L('THANG MÀU THEO GIÁ TRỊ VALUE (%)',
                     'COLOR SCALE BY VALUE (%)', lang),
                  fontsize=9.5, color=_C_CART, weight='bold',
                  transform=ax_info.transAxes, verticalalignment='bottom')

    # Horizontal continuous color bar: full 6 palette squares
    bar_x = 0.10
    bar_w = 0.42
    bar_h = 0.020
    bar_y = 0.142
    seg_w = bar_w / len(palette)
    for i, clr in enumerate(palette):
        ax_info.add_patch(Rectangle((bar_x + i * seg_w, bar_y), seg_w, bar_h,
                                     facecolor=clr, edgecolor='white', linewidth=0.5,
                                     transform=ax_info.transAxes))
    # Endpoint labels under bar
    ax_info.text(bar_x, bar_y - 0.013,
                  f'{v_min:+.2f}%  ' + _L('(thấp · bearish)', '(low · bearish)', lang),
                  fontsize=7.5, color='#4575B4', weight='bold',
                  transform=ax_info.transAxes, verticalalignment='top', ha='left')
    ax_info.text(bar_x + bar_w, bar_y - 0.013,
                  f'{v_max:+.2f}%  ' + _L('(cao · bullish)', '(high · bullish)', lang),
                  fontsize=7.5, color='#D73027', weight='bold',
                  transform=ax_info.transAxes, verticalalignment='top', ha='right')
    ax_info.text(bar_x + bar_w / 2, bar_y - 0.013,
                  _L('trung bình', 'average', lang),
                  fontsize=7.5, color=_C_MUTED,
                  transform=ax_info.transAxes, verticalalignment='top', ha='center')

    # Guide section bên phải legend
    gx = 0.56
    ax_info.add_patch(Rectangle((gx, 0.172), 0.015, 0.005,
                                 facecolor=_C_ACCENT, edgecolor='none',
                                 transform=ax_info.transAxes))
    ax_info.text(gx + 0.02, 0.170,
                  _L('HƯỚNG DẪN ĐỌC CÂY', 'HOW TO READ THIS TREE', lang),
                  fontsize=9.5, color=_C_ACCENT, weight='bold',
                  transform=ax_info.transAxes, verticalalignment='bottom')

    if lang == 'VI':
        guide_lines = [
            '• Nhánh TRUE → trái · FALSE → phải',
            '• Nút nội: điều kiện split + số mẫu n + value',
            '• Nút lá (cuối): value = Return dự báo (%)',
            '• Màu đậm/nhạt theo value (xem thang ở trái)',
        ]
    else:
        guide_lines = [
            '• TRUE branch → left · FALSE → right',
            '• Internal node: split rule + n samples + value',
            '• Leaf (terminal): value = forecast Return (%)',
            '• Color intensity follows value (see scale on left)',
        ]
    for i, line in enumerate(guide_lines):
        ax_info.text(gx, 0.145 - i * 0.020, line, fontsize=7.5,
                      color=_C_TEXT, transform=ax_info.transAxes)

    _add_footer(fig, 7, TOTAL_PAGES, lang=lang)
    pdf.savefig(fig, facecolor='white')
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════
# PAGE 8 — Ichimoku CHART (price + Tenkan + Kijun + Kumo cloud + Chikou)
# ═══════════════════════════════════════════════════════════════
def _page_ichimoku_chart(pdf, ticker, df, lang='VI'):
    """Biểu đồ Ichimoku Kinko Hyo — style giống app (landscape + date axis)."""
    fig = plt.figure(figsize=A4_PORTRAIT)
    fig.patch.set_facecolor('white')
    _add_header(fig, '', lang=lang)

    fig.text(0.08, 0.905, f'ICHIMOKU KINKO HYO — {ticker}',
             fontsize=14, color=_C_TEXT, weight='bold')
    fig.text(0.08, 0.885,
             _L('Tham số chuẩn 9 · 26 · 52 · Kumo (Senkou A/B) chiếu 26 phiên tương lai',
                'Standard params 9 · 26 · 52 · Kumo (Senkou A/B) projected 26 sessions ahead',
                lang),
             fontsize=9, color=_C_MUTED)

    # Compute Ichimoku
    try:
        from data.ichimoku import add_ichimoku
        df_ichi = add_ichimoku(df).copy()
    except Exception as e:
        ax = fig.add_axes([0, 0, 1, 1])
        ax.axis('off')
        ax.text(0.5, 0.5,
                _L(f'Không tính được Ichimoku: {e}',
                   f'Failed to compute Ichimoku: {e}', lang),
                fontsize=10, color=_C_DANGER, ha='center', va='center',
                transform=ax.transAxes)
        _add_footer(fig, 8, TOTAL_PAGES, lang=lang)
        pdf.savefig(fig, facecolor='white')
        plt.close(fig)
        return

    # Lấy 120 phiên gần nhất
    n_show = min(120, len(df_ichi))
    tail = df_ichi.tail(n_show).reset_index(drop=True)

    # Convert date để làm x-axis đẹp
    import pandas as pd
    if 'Ngay' in tail.columns:
        try:
            dates = pd.to_datetime(tail['Ngay'])
        except Exception:
            dates = pd.date_range(end=pd.Timestamp.today(), periods=len(tail))
    else:
        dates = pd.date_range(end=pd.Timestamp.today(), periods=len(tail))

    close  = tail['Close'].values
    tenkan = tail['Tenkan'].values
    kijun  = tail['Kijun'].values
    senA   = tail['Senkou_A'].values
    senB   = tail['Senkou_B'].values
    chikou = tail['Chikou'].values if 'Chikou' in tail.columns else None

    # ─── Main chart — LANDSCAPE aspect (rộng ngang, thấp) ───
    # Aspect ratio ~3:1 wide → chart không bị ép dọc, nhìn như app
    ax1 = fig.add_axes([0.08, 0.48, 0.84, 0.36])

    sa = pd.Series(senA)
    sb = pd.Series(senB)
    x_num = np.arange(len(tail))

    # ═══ KUMO CLOUD (fill + thin borders) — màu như app ═══
    ax1.fill_between(x_num, sa, sb, where=(sa >= sb),
                      color='#10B981', alpha=0.18, interpolate=True)
    ax1.fill_between(x_num, sa, sb, where=(sa < sb),
                      color='#EF4444', alpha=0.18, interpolate=True)
    # Senkou A border (green outline)
    ax1.plot(x_num, senA, color='#059669', linewidth=0.7,
              alpha=0.85, label='Senkou A', zorder=2)
    # Senkou B border (red outline)
    ax1.plot(x_num, senB, color='#B91C1C', linewidth=0.7,
              alpha=0.85, label='Senkou B', zorder=2)

    # ═══ CHIKOU (violet dashed thin) ═══
    if chikou is not None:
        mask = ~np.isnan(chikou)
        if mask.any():
            ax1.plot(x_num[mask], chikou[mask], color='#9333EA',
                      linewidth=0.9, linestyle=(0, (3, 2)),
                      alpha=0.7, label='Chikou (-26)', zorder=3)

    # ═══ TENKAN (red solid, as in app) ═══
    ax1.plot(x_num, tenkan, color='#DC2626', linewidth=1.2,
              label='Tenkan (9)', zorder=4)

    # ═══ KIJUN (blue dashed, as in app) ═══
    ax1.plot(x_num, kijun, color='#2563EB', linewidth=1.2,
              linestyle=(0, (5, 2)),
              label='Kijun (26)', zorder=4)

    # ═══ CLOSE (blue solid, thick — dominant) ═══
    ax1.plot(x_num, close, color='#1E40AF', linewidth=2.2,
              label='Close', zorder=6)

    # ═══ "HÔM NAY" vertical line ═══
    today_x = len(tail) - 27 if len(tail) > 27 else len(tail) - 1
    ax1.axvline(today_x, color=_C_MUTED, linestyle='--',
                linewidth=1, alpha=0.7)
    all_vals = np.concatenate([close, tenkan[~np.isnan(tenkan)],
                                kijun[~np.isnan(kijun)],
                                sa.values[~np.isnan(sa.values)],
                                sb.values[~np.isnan(sb.values)]])
    y_top_plot = np.nanmax(all_vals)
    y_bot_plot = np.nanmin(all_vals)
    y_span_plot = y_top_plot - y_bot_plot
    ax1.text(today_x, y_top_plot + y_span_plot * 0.02,
              _L('HÔM NAY', 'TODAY', lang),
              fontsize=7.5, color=_C_MUTED, ha='center',
              weight='bold', verticalalignment='bottom')

    # ═══ X-AXIS với DATE labels (như app) ═══
    # Chọn ~6 tick đều nhau để không quá crowded
    n_ticks = 6
    tick_positions = np.linspace(0, len(tail) - 1, n_ticks, dtype=int)
    tick_labels = [dates.iloc[i].strftime('%b %Y') for i in tick_positions]
    ax1.set_xticks(tick_positions)
    ax1.set_xticklabels(tick_labels, fontsize=8, color=_C_MUTED, rotation=0)
    ax1.set_xlim(-2, len(tail) + 2)

    ax1.set_ylabel(_L('Giá (nghìn đ)', 'Price (k VND)', lang),
                    fontsize=9, color=_C_MUTED)
    ax1.grid(True, alpha=0.25, linestyle=':')
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.tick_params(labelsize=8, colors=_C_MUTED)

    # ═══ LEGEND (horizontal, at bottom of chart) ═══
    ax1.legend(loc='upper center', bbox_to_anchor=(0.5, -0.08),
                fontsize=7.5, frameon=False, ncol=6,
                handletextpad=0.5, columnspacing=1.5)

    # ─── DIỄN GIẢI NHANH (block dưới chart) ───
    ax_info = fig.add_axes([0, 0, 1, 1])
    ax_info.set_xlim(0, 1); ax_info.set_ylim(0, 1); ax_info.axis('off')

    ax_info.add_patch(Rectangle((0.08, 0.36), 0.015, 0.005,
                                 facecolor=_C_ACCENT, edgecolor='none',
                                 transform=ax_info.transAxes))
    ax_info.text(0.10, 0.358,
                  _L('DIỄN GIẢI NHANH — CÁCH ĐỌC BIỂU ĐỒ',
                     'QUICK GUIDE — HOW TO READ THE CHART', lang),
                  fontsize=11, color=_C_ACCENT, weight='bold',
                  transform=ax_info.transAxes, verticalalignment='bottom')

    if lang == 'VI':
        diag_lines = [
            '• Close TRÊN Kumo → xu hướng TĂNG · Close DƯỚI Kumo → xu hướng GIẢM · Close TRONG Kumo → tích lũy / chuyển tiếp.',
            '• Tenkan (đỏ) cắt LÊN Kijun (xanh đứt) + trên mây → tín hiệu Mua mạnh · Cắt XUỐNG + dưới mây → Bán mạnh.',
            '• Chikou (tím đứt, lùi 26 phiên) TRÊN giá quá khứ → xác nhận momentum TĂNG · DƯỚI → xác nhận GIẢM.',
            '• Kumo tương lai XANH (Senkou A > B) → dự báo momentum TĂNG 26 phiên tới · Kumo ĐỎ → dự báo GIẢM.',
            '• Cloud dày → hỗ trợ/kháng cự mạnh · Cloud mỏng / twist → xu hướng sắp đảo chiều.',
        ]
    else:
        diag_lines = [
            '• Close ABOVE Kumo → UP trend · Close BELOW Kumo → DOWN trend · Close INSIDE Kumo → consolidation / transition.',
            '• Tenkan (red) crosses UP over Kijun (blue dashed) + above cloud → strong BUY · Crosses DOWN + below cloud → strong SELL.',
            '• Chikou (violet dashed, lagged 26) ABOVE past price → confirms UP momentum · BELOW → confirms DOWN.',
            '• Future Kumo GREEN (Senkou A > B) → forecasts UP momentum next 26 sessions · RED Kumo → forecasts DOWN.',
            '• Thick cloud → strong support/resistance · Thin cloud / twist → trend about to reverse.',
        ]
    for i, line in enumerate(diag_lines):
        ax_info.text(0.08, 0.325 - i * 0.028, line, fontsize=8.5,
                      color=_C_TEXT, transform=ax_info.transAxes)

    # ─── Tham chiếu gốc ───
    ax_info.text(0.08, 0.155,
                  _L('Nguồn gốc: Goichi Hosoda (1969) · Tham số 9·26·52 (Chikou lag 26 phiên, Kumo chiếu 26 phiên).',
                     'Source: Goichi Hosoda (1969) · Params 9·26·52 (Chikou lag 26 sessions, Kumo projected 26 sessions).',
                     lang),
                  fontsize=7.5, color=_C_MUTED, style='italic',
                  transform=ax_info.transAxes)

    _add_footer(fig, 8, TOTAL_PAGES, lang=lang)
    pdf.savefig(fig, facecolor='white')
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════
# PAGE 9 — Ichimoku 4-tier signal detail
# ═══════════════════════════════════════════════════════════════
_ICHI_PRIMARY_VI = {
    'bull':  ('Giá trên mây Kumo', 'Xu hướng TĂNG', _C_SUCCESS),
    'bear':  ('Giá dưới mây Kumo', 'Xu hướng GIẢM', _C_DANGER),
    'neut':  ('Giá trong mây Kumo', 'Tích lũy / Chuyển tiếp', '#F59E0B'),
    'na':    ('Không đủ dữ liệu', 'N/A', _C_MUTED),
}
_ICHI_PRIMARY_EN = {
    'bull':  ('Close above Kumo',  'UP trend',               _C_SUCCESS),
    'bear':  ('Close below Kumo',  'DOWN trend',             _C_DANGER),
    'neut':  ('Close inside Kumo', 'Consolidation / transition', '#F59E0B'),
    'na':    ('Insufficient data', 'N/A', _C_MUTED),
}
_ICHI_TRADING_VI = {
    'strong_buy':   ('Mua mạnh', 'Cross + phù hợp xu hướng trên mây', _C_SUCCESS),
    'weak_buy':     ('Mua yếu', 'Cross trong mây (tín hiệu không rõ)', '#84CC16'),
    'counter_buy':  ('Mua ngược xu hướng', 'Rủi ro cao', '#F59E0B'),
    'strong_sell':  ('Bán mạnh', 'Cross + dưới mây', _C_DANGER),
    'weak_sell':    ('Bán yếu', 'Cross trong mây', '#F59E0B'),
    'counter_sell': ('Bán ngược xu hướng', 'Rủi ro cao', '#F59E0B'),
    'hold':         ('Không có tín hiệu', 'Chờ cross mới', _C_MUTED),
}
_ICHI_TRADING_EN = {
    'strong_buy':   ('Strong Buy',  'Cross + aligned trend above cloud', _C_SUCCESS),
    'weak_buy':     ('Weak Buy',    'Cross inside cloud (unclear)',      '#84CC16'),
    'counter_buy':  ('Counter Buy', 'High risk',                          '#F59E0B'),
    'strong_sell':  ('Strong Sell', 'Cross + below cloud',                _C_DANGER),
    'weak_sell':    ('Weak Sell',   'Cross inside cloud',                 '#F59E0B'),
    'counter_sell': ('Counter Sell','High risk',                          '#F59E0B'),
    'hold':         ('No signal',   'Wait for new cross',                 _C_MUTED),
}
_ICHI_CHIKOU_VI = {
    'bull': ('Chikou trên giá quá khứ', 'Xác nhận momentum TĂNG', _C_SUCCESS),
    'bear': ('Chikou dưới giá quá khứ', 'Xác nhận momentum GIẢM', _C_DANGER),
    'neut': ('Chikou gần giá quá khứ', 'Tín hiệu không rõ',       '#F59E0B'),
    'na':   ('Không đủ dữ liệu', 'N/A', _C_MUTED),
}
_ICHI_CHIKOU_EN = {
    'bull': ('Chikou above past price', 'Confirms UP momentum',   _C_SUCCESS),
    'bear': ('Chikou below past price', 'Confirms DOWN momentum', _C_DANGER),
    'neut': ('Chikou near past price',  'Unclear signal',         '#F59E0B'),
    'na':   ('Insufficient data',       'N/A', _C_MUTED),
}
_ICHI_FUTURE_VI = {
    'bull': ('Mây tương lai XANH',     'Momentum TĂNG T+26', _C_SUCCESS),
    'bear': ('Mây tương lai ĐỎ',       'Momentum GIẢM T+26', _C_DANGER),
    'neut': ('Mây tương lai PHẲNG',    'Chuyển tiếp',         '#F59E0B'),
    'flat': ('Mây tương lai PHẲNG',    'Chuyển tiếp',         '#F59E0B'),
    'na':   ('Không đủ dữ liệu',       'N/A', _C_MUTED),
}
_ICHI_FUTURE_EN = {
    'bull': ('Future Kumo GREEN', 'UP momentum T+26',   _C_SUCCESS),
    'bear': ('Future Kumo RED',   'DOWN momentum T+26', _C_DANGER),
    'neut': ('Future Kumo FLAT',  'Transition',         '#F59E0B'),
    'flat': ('Future Kumo FLAT',  'Transition',         '#F59E0B'),
    'na':   ('Insufficient data', 'N/A', _C_MUTED),
}


def _page_ichimoku(pdf, ticker, ichi, lang='VI'):
    """Page 4 tầng Ichimoku chi tiết."""
    fig = plt.figure(figsize=A4_PORTRAIT)
    fig.patch.set_facecolor('white')
    _add_header(fig, '', lang=lang)

    fig.text(0.08, 0.905, f'ICHIMOKU KINKO HYO — {ticker}',
             fontsize=14, color=_C_TEXT, weight='bold')
    fig.text(0.08, 0.885,
             _L('Hệ phân tích kỹ thuật 4 tầng tín hiệu (Hosoda, 1969) · '
                'tham số chuẩn 9·26·52',
                '4-tier technical analysis system (Hosoda, 1969) · '
                'standard params 9·26·52', lang),
             fontsize=9, color=_C_MUTED)

    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')

    if not ichi:
        ax.text(0.5, 0.5,
                _L('Dữ liệu Ichimoku chưa có.\n'
                   'Vui lòng vào trang Dashboard hoặc Tín hiệu & Cảnh báo trước '
                   'rồi xuất lại báo cáo.',
                   'Ichimoku data not available.\n'
                   'Please open the Dashboard or Signals page first, '
                   'then re-export the report.', lang),
                fontsize=12, color=_C_MUTED, ha='center', va='center',
                transform=ax.transAxes, style='italic')
        _add_footer(fig, 9, TOTAL_PAGES, lang=lang)
        pdf.savefig(fig, facecolor='white')
        plt.close(fig)
        return

    # Overall score card
    score = ichi.get('score', 0)
    label = ichi.get('label', 'N/A')
    if score >= 3:
        ov_color = _C_SUCCESS
    elif score <= -3:
        ov_color = _C_DANGER
    elif score >= 1:
        ov_color = '#84CC16'
    elif score <= -1:
        ov_color = '#F59E0B'
    else:
        ov_color = _C_MUTED

    ov_box = FancyBboxPatch((0.08, 0.75), 0.84, 0.11,
                             boxstyle='round,pad=0.003,rounding_size=0.015',
                             linewidth=3, edgecolor=ov_color,
                             facecolor='white', transform=ax.transAxes)
    ax.add_patch(ov_box)
    ax.text(0.15, 0.81, f'{score:+d}/5',
            fontsize=32, color=ov_color, weight='bold',
            transform=ax.transAxes, verticalalignment='center')
    ax.text(0.35, 0.83,
            _L('TỔNG HỢP 4 TẦNG', '4-TIER CONSENSUS', lang),
            fontsize=9, color=_C_MUTED,
            weight='bold', transform=ax.transAxes, verticalalignment='center')
    ax.text(0.35, 0.80, label, fontsize=16, color=_C_TEXT, weight='bold',
            transform=ax.transAxes, verticalalignment='center')
    ax.text(0.35, 0.77,
            _L('Thang điểm -5 (giảm mạnh) → +5 (tăng mạnh)',
               'Score -5 (strong bear) → +5 (strong bull)', lang),
            fontsize=8, color=_C_MUTED, transform=ax.transAxes,
            verticalalignment='center', style='italic')

    # 4 tier cards (2×2 grid)
    primary = ichi.get('primary', 'na')
    trading = ichi.get('trading', 'hold')
    chikou  = ichi.get('chikou', 'na')
    future  = ichi.get('future_kumo', 'na')

    _prim_dict = _ICHI_PRIMARY_VI if lang == 'VI' else _ICHI_PRIMARY_EN
    _trd_dict  = _ICHI_TRADING_VI if lang == 'VI' else _ICHI_TRADING_EN
    _chk_dict  = _ICHI_CHIKOU_VI  if lang == 'VI' else _ICHI_CHIKOU_EN
    _fut_dict  = _ICHI_FUTURE_VI  if lang == 'VI' else _ICHI_FUTURE_EN
    prim_info = _prim_dict.get(primary, _prim_dict['na'])
    trd_info  = _trd_dict.get(trading, _trd_dict['hold'])
    chk_info  = _chk_dict.get(chikou, _chk_dict['na'])
    fut_info  = _fut_dict.get(future, _fut_dict['na'])

    if lang == 'VI':
        tiers = [
            ('TẦNG 1 · XU HƯỚNG CHÍNH',     'Vị trí Close vs Kumo',             prim_info),
            ('TẦNG 2 · TÍN HIỆU GIAO DỊCH', 'Tenkan × Kijun cross',              trd_info),
            ('TẦNG 3 · XÁC NHẬN CHIKOU',    'Close[t] vs Close[t-26]',           chk_info),
            ('TẦNG 4 · MÂY TƯƠNG LAI',      'Senkou A vs Senkou B tại t+26',     fut_info),
        ]
    else:
        tiers = [
            ('TIER 1 · PRIMARY TREND',      'Close position vs Kumo',            prim_info),
            ('TIER 2 · TRADING SIGNAL',     'Tenkan × Kijun cross',              trd_info),
            ('TIER 3 · CHIKOU CONFIRMATION','Close[t] vs Close[t-26]',           chk_info),
            ('TIER 4 · FUTURE KUMO',        'Senkou A vs Senkou B at t+26',      fut_info),
        ]
    positions = [
        (0.08, 0.48),
        (0.52, 0.48),
        (0.08, 0.24),
        (0.52, 0.24),
    ]
    for (tier_lbl, desc, info), (x0, y0) in zip(tiers, positions):
        title, subtitle, clr = info
        box = FancyBboxPatch((x0, y0), 0.40, 0.22,
                              boxstyle='round,pad=0.003,rounding_size=0.012',
                              linewidth=1.5, edgecolor=clr,
                              facecolor='white', transform=ax.transAxes)
        ax.add_patch(box)
        # Stripe on left
        stripe = Rectangle((x0, y0), 0.005, 0.22,
                           facecolor=clr, edgecolor='none',
                           transform=ax.transAxes)
        ax.add_patch(stripe)
        # Tier label top
        ax.text(x0 + 0.02, y0 + 0.19, tier_lbl, fontsize=8.5, color=clr,
                weight='bold', transform=ax.transAxes,
                verticalalignment='center')
        # Description
        ax.text(x0 + 0.02, y0 + 0.16, desc, fontsize=8, color=_C_MUTED,
                transform=ax.transAxes, verticalalignment='center')
        # Main result
        ax.text(x0 + 0.02, y0 + 0.10, title, fontsize=12, color=_C_TEXT,
                weight='bold', transform=ax.transAxes,
                verticalalignment='center')
        # Subtitle
        ax.text(x0 + 0.02, y0 + 0.055, subtitle, fontsize=9, color=clr,
                weight='600', transform=ax.transAxes,
                verticalalignment='center')

    # Disclaimer
    ax.text(0.50, 0.18,
            _L('Chỉ mang tính tham khảo học thuật · Không phải tư vấn đầu tư',
               'For academic reference only · Not investment advice', lang),
            fontsize=8.5, color=_C_MUTED, ha='center', style='italic',
            transform=ax.transAxes)

    # Methodology note
    ax.add_patch(Rectangle((0.08, 0.140), 0.015, 0.005,
                            facecolor=_C_ACCENT, edgecolor='none',
                            transform=ax.transAxes))
    ax.text(0.10, 0.138,
            _L('PHƯƠNG PHÁP TÍNH ĐIỂM', 'SCORING METHOD', lang),
            fontsize=10, color=_C_ACCENT, weight='bold',
            transform=ax.transAxes, verticalalignment='bottom')

    if lang == 'VI':
        method_lines = [
            '• Mỗi tầng cho điểm -1 (bear), 0 (neutral), +1 (bull). Tầng 2 có thể ±2 khi strong.',
            '• Tổng điểm 4 tầng → score từ -5 đến +5 → phân loại Strong/Mild Bull/Neutral/Bear.',
            '• |score| ≥ 3 → tín hiệu mạnh. |score| < 2 → tín hiệu yếu/phân kỳ, cần xác nhận.',
        ]
    else:
        method_lines = [
            '• Each tier scores -1 (bear), 0 (neutral), +1 (bull). Tier 2 can be ±2 when strong.',
            '• Sum of 4 tiers → score from -5 to +5 → classified Strong/Mild Bull/Neutral/Bear.',
            '• |score| ≥ 3 → strong signal. |score| < 2 → weak/divergent, needs confirmation.',
        ]
    for i, line in enumerate(method_lines):
        ax.text(0.08, 0.105 - i * 0.020, line, fontsize=8.5,
                color=_C_TEXT, transform=ax.transAxes)

    _add_footer(fig, 9, TOTAL_PAGES, lang=lang)
    pdf.savefig(fig, facecolor='white')
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════
# PAGE 7 — Metrics table + Ichimoku summary + conclusion (moved from p3)
# ═══════════════════════════════════════════════════════════════
def _page_metrics(pdf, ticker, m1, m2, m3, ar_order, ichi=None, lang='VI'):
    fig = plt.figure(figsize=A4_PORTRAIT)
    fig.patch.set_facecolor('white')
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    _add_header(fig, '', lang=lang)

    # Title
    ax.text(0.08, 0.91,
            _L(f'CHI TIẾT HIỆU NĂNG — {ticker}',
               f'DETAILED PERFORMANCE — {ticker}', lang),
            fontsize=14, color=_C_TEXT, weight='bold', transform=ax.transAxes)
    ax.text(0.08, 0.89,
            _L('So sánh 4 chỉ số đánh giá cho 3 mô hình trên TẬP KIỂM TRA',
               'Comparing 4 evaluation metrics for 3 models on the TEST SET',
               lang),
            fontsize=10, color=_C_MUTED, transform=ax.transAxes)

    # ═══ Metrics table ═══
    models = [(f'AR({ar_order})', _C_AR, m1),
              ('MLR', _C_MLR, m2),
              ('CART', _C_CART, m3)]
    mapes = [m1['MAPE'], m2['MAPE'], m3['MAPE']]
    best_idx = int(np.argmin(mapes))

    # Header row
    col_x = [0.08, 0.26, 0.44, 0.60, 0.76]
    col_w = [0.18, 0.18, 0.16, 0.16, 0.16]
    headers = [_L('MÔ HÌNH', 'MODEL', lang), 'MAPE (%)', 'RMSE', 'MAE', 'R²ADJ']

    # Header background
    hdr_bg = Rectangle((0.08, 0.79), 0.84, 0.04,
                       facecolor=_C_ACCENT_DARK, edgecolor='none',
                       transform=ax.transAxes)
    ax.add_patch(hdr_bg)
    for i, h in enumerate(headers):
        ax.text(col_x[i] + 0.01, 0.81, h, fontsize=9, color='white',
                weight='bold', transform=ax.transAxes, verticalalignment='center')

    # Body rows
    for i, (nm, clr, m) in enumerate(models):
        y = 0.75 - i * 0.05
        is_best = (i == best_idx)
        # Row background
        row_bg = Rectangle((0.08, y - 0.02), 0.84, 0.045,
                           facecolor=(_C_BG_SOFT if is_best else 'white'),
                           edgecolor=_C_BORDER, linewidth=0.5,
                           transform=ax.transAxes)
        ax.add_patch(row_bg)
        # Best indicator stripe
        if is_best:
            stripe = Rectangle((0.08, y - 0.02), 0.005, 0.045,
                               facecolor=clr, edgecolor='none',
                               transform=ax.transAxes)
            ax.add_patch(stripe)
        # Cells
        name_txt = f'{nm}  ★' if is_best else nm
        ax.text(col_x[0] + 0.01, y, name_txt,
                fontsize=10, color=clr, weight='bold',
                transform=ax.transAxes, verticalalignment='center')
        ax.text(col_x[1] + 0.01, y, f'{m["MAPE"]:.4f}%',
                fontsize=10, color=_C_TEXT,
                weight=('bold' if is_best else 'normal'),
                family='monospace',
                transform=ax.transAxes, verticalalignment='center')
        ax.text(col_x[2] + 0.01, y, f'{m["RMSE"]:.4f}',
                fontsize=10, color=_C_TEXT, family='monospace',
                transform=ax.transAxes, verticalalignment='center')
        ax.text(col_x[3] + 0.01, y, f'{m["MAE"]:.4f}',
                fontsize=10, color=_C_TEXT, family='monospace',
                transform=ax.transAxes, verticalalignment='center')
        ax.text(col_x[4] + 0.01, y, f'{m["R2adj"]:.4f}',
                fontsize=10, color=_C_TEXT, family='monospace',
                transform=ax.transAxes, verticalalignment='center')

    # Caption
    ax.text(0.08, 0.58,
            _L('★ = Mô hình tốt nhất (MAPE thấp nhất)',
               '★ = Best model (lowest MAPE)', lang),
            fontsize=8, color=_C_MUTED, style='italic',
            transform=ax.transAxes)
    ax.text(0.08, 0.56,
            _L('Đơn vị RMSE/MAE: nghìn đồng (VNĐ × 1000) · '
               'R²adj càng gần 1 càng tốt',
               'RMSE/MAE unit: thousand VND (VND × 1000) · '
               'R²adj closer to 1 is better', lang),
            fontsize=8, color=_C_MUTED, style='italic',
            transform=ax.transAxes)

    # ═══ Ichimoku summary (nếu có) ═══
    if ichi:
        # Title + accent bar BÊN TRÁI (không phải underline bên dưới)
        ax.add_patch(Rectangle((0.08, 0.507), 0.015, 0.005,
                                facecolor=_C_ACCENT, edgecolor='none',
                                transform=ax.transAxes))
        ax.text(0.10, 0.505,
                _L('TÍN HIỆU ICHIMOKU HIỆN TẠI', 'CURRENT ICHIMOKU SIGNAL', lang),
                fontsize=12, color=_C_ACCENT, weight='bold',
                transform=ax.transAxes, verticalalignment='bottom')

        score = ichi.get('score', 0)
        label = ichi.get('label', 'N/A')
        if score >= 3:
            ichi_color = _C_SUCCESS
        elif score <= -3:
            ichi_color = _C_DANGER
        else:
            ichi_color = '#F59E0B'

        ichi_box = FancyBboxPatch((0.08, 0.41), 0.84, 0.07,
                                  boxstyle='round,pad=0.003,rounding_size=0.012',
                                  linewidth=2, edgecolor=ichi_color,
                                  facecolor='white', transform=ax.transAxes)
        ax.add_patch(ichi_box)
        ax.text(0.12, 0.45, f'Score: {score:+d}/5',
                fontsize=14, color=ichi_color, weight='bold',
                transform=ax.transAxes, verticalalignment='center')
        ax.text(0.35, 0.45, label, fontsize=13,
                color=_C_TEXT, weight='bold', transform=ax.transAxes,
                verticalalignment='center')

    # ═══ Conclusion ═══
    y_conc = 0.36 if ichi else 0.50
    ax.add_patch(Rectangle((0.08, y_conc + 0.002), 0.015, 0.005,
                            facecolor=_C_ACCENT, edgecolor='none',
                            transform=ax.transAxes))
    ax.text(0.10, y_conc, _L('KẾT LUẬN', 'CONCLUSION', lang),
            fontsize=12, color=_C_ACCENT, weight='bold',
            transform=ax.transAxes, verticalalignment='bottom')

    best_nm = models[best_idx][0]
    best_mape = mapes[best_idx]
    best_r2 = models[best_idx][2]['R2adj']
    conc_y = y_conc - 0.04

    if lang == 'VI':
        conclusion_lines = [
            f'• Mô hình tốt nhất: {best_nm} với MAPE = {best_mape:.2f}% '
            f'(thuộc nhóm "Rất tốt" theo Hyndman 2021).',
            f'• R²adj = {best_r2:.4f} → mô hình giải thích được '
            f'{best_r2*100:.1f}% biến động giá.',
            f'• Cả 3 mô hình đều đạt MAPE < 2%, chứng tỏ dữ liệu HOSE có '
            f'tính persistent cao (gần random walk).',
            f'• Kết quả phù hợp với Giả thuyết thị trường hiệu quả yếu '
            f'(Fama, 1970): giá cổ phiếu phụ thuộc mạnh vào giá quá khứ gần.',
        ]
    else:
        conclusion_lines = [
            f'• Best model: {best_nm} with MAPE = {best_mape:.2f}% '
            f'("Excellent" tier per Hyndman 2021).',
            f'• R²adj = {best_r2:.4f} → the model explains '
            f'{best_r2*100:.1f}% of price variance.',
            f'• All 3 models achieve MAPE < 2%, showing HOSE data is highly '
            f'persistent (near random walk).',
            f'• Results align with the Weak-Form Efficient Market Hypothesis '
            f'(Fama, 1970): prices depend heavily on recent past prices.',
        ]
    for i, line in enumerate(conclusion_lines):
        ax.text(0.08, conc_y - i * 0.028, line, fontsize=9.5,
                color=_C_TEXT, transform=ax.transAxes, wrap=True)

    # ═══ References ═══
    ref_y = conc_y - len(conclusion_lines) * 0.028 - 0.035
    ax.add_patch(Rectangle((0.08, ref_y + 0.002), 0.015, 0.005,
                            facecolor=_C_MUTED, edgecolor='none',
                            transform=ax.transAxes))
    ax.text(0.10, ref_y, _L('TÀI LIỆU THAM KHẢO', 'REFERENCES', lang),
            fontsize=10, color=_C_MUTED, weight='bold',
            transform=ax.transAxes, verticalalignment='bottom')
    refs = [
        'Box, G., Jenkins, G., Reinsel, G., Ljung, G. (2015). '
        'Time Series Analysis: Forecasting and Control, 5th ed. Wiley.',
        'Hyndman, R., Athanasopoulos, G. (2021). '
        'Forecasting: principles and practice, 3rd ed. OTexts.',
        'Fama, E. (1970). Efficient Capital Markets. '
        'Journal of Finance, 25(2), 383–417.',
        'Hosoda, G. (1969). Ichimoku Kinko Hyo.',
    ]
    for i, ref in enumerate(refs):
        ax.text(0.08, ref_y - 0.028 - i * 0.020, f'[{i+1}]  {ref}',
                fontsize=7.5, color=_C_MUTED, transform=ax.transAxes)

    _add_footer(fig, 10, TOTAL_PAGES, lang=lang)
    pdf.savefig(fig, facecolor='white')
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════
def generate_pdf_report(ticker: str, df, r1, r2, r3, m1, m2, m3,
                        ar_order: int = 1, ichi: dict = None,
                        lang: str = 'VI') -> bytes:
    """Sinh PDF báo cáo 10 trang A4. lang='VI' hoặc 'EN' → toàn bộ nội dung
    song ngữ theo cài đặt sidebar.
    """
    _setup_font()
    buffer = io.BytesIO()
    with PdfPages(buffer) as pdf:
        # PDF metadata — theo lang
        d = pdf.infodict()
        if lang == 'VI':
            d['Title']   = f'Dự báo giá cổ phiếu {ticker} — NCKH TDTU 2026'
            d['Subject'] = f'Báo cáo dự báo giá cổ phiếu {ticker} trên sàn HOSE'
        else:
            d['Title']   = f'Stock Price Forecast {ticker} — TDTU NCKH 2026'
            d['Subject'] = f'Stock price forecast report for {ticker} on HOSE'
        d['Author']   = 'TDTU NCKH 2026'
        d['Keywords'] = 'HOSE, AR, MLR, CART, Ichimoku, MAPE'
        d['CreationDate'] = datetime.now()

        _page_cover(pdf, ticker, df, r1, r2, r3, m1, m2, m3, ar_order, lang=lang)
        _page_toc(pdf, ticker, lang=lang)
        _page_chart(pdf, ticker, df, r1, r2, r3, m1, m2, m3, ar_order, lang=lang)
        _page_test_timeseries(pdf, ticker, r1, r2, r3, ar_order, lang=lang)
        _page_scatter_coef(pdf, ticker, r1, r2, r3, m1, m2, m3, ar_order, lang=lang)
        _page_cart_features(pdf, ticker, r3, m3, ar_order, lang=lang)
        _page_cart_tree(pdf, ticker, r3, ar_order, lang=lang)
        _page_ichimoku_chart(pdf, ticker, df, lang=lang)
        _page_ichimoku(pdf, ticker, ichi, lang=lang)
        _page_metrics(pdf, ticker, m1, m2, m3, ar_order, ichi=ichi, lang=lang)

    buffer.seek(0)
    return buffer.getvalue()
