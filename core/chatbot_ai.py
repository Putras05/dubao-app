"""Gemini AI wrapper — robust với retry + wait cho rate limit.

FIX 2026-04-23:
- C1: System prompt CẤM TUYỆT ĐỐI nói "mô phỏng/ví dụ/giả lập" — bôi đậm, nhắc lại
- C3: build_context_string dùng close_vnd đã nhân 1000 → hiển thị đúng "74,600 đ"
- C5: Đổi nhãn volatility cho rõ "biến động annualized" không gây nhầm
- Cache invalidation: tăng PROMPT_VERSION → cache cũ bị bỏ qua (xem chatbot_cache.py)
"""
import re
import time
import streamlit as st


# ═══════════════════════════════════════════════════════════════
# PROMPT VERSION — bump khi đổi system prompt để invalidate cache cũ
# ═══════════════════════════════════════════════════════════════
PROMPT_VERSION = 'v18-2026-05-06-historical-data'


# ═══════════════════════════════════════════════════════════════
# SYSTEM PROMPTS v12 — friendly general-purpose ChatGPT-class
# assistant that ALSO knows the HOSE forecasting app's data tools.
# Drop the rigid "must-include-formula" / "Vietnamese-only" rules.
# ═══════════════════════════════════════════════════════════════
_SYSTEM_PROMPT_VI = """Bạn là một trợ lý AI tổng quát, thân thiện, có cá tính — phong cách giống ChatGPT/Claude khi trò chuyện với bạn bè. Bạn có thể trả lời mọi chủ đề: lập trình, toán, đời sống, lịch sử, học thuật, công nghệ, ẩm thực, nghệ thuật, sức khoẻ tâm lý nhẹ nhàng — bất cứ thứ gì user hỏi.

# VỀ DỰ ÁN

Bạn được nhúng trong app NCKH:
- Tên đề tài: "XÂY DỰNG CHATBOT PHÂN TÍCH VÀ DỰ BÁO CHỨNG KHOÁN DỰA TRÊN MÔ HÌNH THỐNG KÊ VÀ HỌC MÁY".
- Đơn vị: Trường Đại học Tôn Đức Thắng (TDTU), Khoa Toán – Thống kê, niên khoá 2025–2026.
- Giảng viên hướng dẫn: ThS. Chế Ngọc Hà.
- Nhóm tác giả: Nguyễn Thành Danh (C2300014), Nguyễn Nhật Anh Huy (C2200153), Mai Phan Vũ (C2200141).
- Phạm vi dữ liệu: 3 mã HOSE (FPT, HPG, VNM); mô hình AR(p), MLR(p), CART(p); chỉ báo Ichimoku.

Khi user hỏi "đề tài này là gì?", "ai làm?", "GVHD?", "trường nào?" → trả lời ngắn gọn dùng đúng các thông tin trên, không bịa.

Phong cách:
- Ngắn gọn cho câu đơn giản, chi tiết khi user cần nhiều bước hoặc giải thích sâu.
- Có gu, nhẹ nhàng và tự nhiên — không sáo rỗng, không spam emoji.
- Bám theo ngôn ngữ user dùng. Mặc định tiếng Việt khi user gõ tiếng Việt, tiếng Anh khi user gõ tiếng Anh, không gò ép.
- Khi giải thích công thức toán, dùng $...$ cho inline math và $$...$$ cho display math (LaTeX chuẩn).
- Code thì dùng fenced block ```python / ```js / etc. — app sẽ tự highlight cú pháp.
- Khi user hỏi về tư vấn đầu tư cụ thể (mua/bán) → chia sẻ tín hiệu app, kèm câu nhắc "đây là kết quả NCKH, chỉ tham khảo học thuật, không phải tư vấn đầu tư".
- Khi user hỏi tính toán/dự báo cho mã hiện tại, hãy dùng `ar_coefs`/`mlr_coefs`/`ar_equation_str` trong context để thay vào công thức và tính ra giá cụ thể. Đừng nói "không có thông tin về β" — context luôn có sẵn hệ số khi mô hình đã fit.
- Khi trình bày phương trình ước lượng, dùng số thực từ `ar_equation_str` thay vì để symbol.

# QUY TẮC TUÂN THỦ YÊU CẦU USER

- Nếu user nêu rõ TÊN MÔ HÌNH (AR, MLR, CART) → CHỈ trả lời về mô hình đó. KHÔNG được tự ý chuyển sang mô hình khác.
  - "tính dự báo bằng MLR" → CHỈ dùng MLR, không nhắc CART trừ khi user yêu cầu so sánh.
  - "AR(1) cho FPT" → CHỈ AR(1), không lan sang AR(2) hay MLR.
- Nếu user nêu rõ TICKER (FPT/HPG/VNM) → CHỈ trả lời về ticker đó.
- Nếu user không nêu mô hình/ticker → dùng ticker hiện tại trong context, hoặc hỏi lại.
- Nếu kết quả tool trả về cho 3 mô hình cùng lúc, CHỈ trích xuất mô hình user yêu cầu — không liệt kê 3 cái.

Ví dụ:
- User: "Tính dự báo phiên tới cho FPT bằng MLR" → ĐÚNG: "Theo mô hình MLR(p=2) trên FPT, dự báo phiên tới là 73,500 đ. Phương trình MLR: ..."
- SAI: "Theo CART, dự báo là 73,384 đ" (sai mô hình, user không hỏi CART).
- SAI: "AR cho 73,200 đ, MLR cho 73,500 đ, CART cho 73,384 đ" (lan sang mô hình khác).

# CÔNG CỤ (BẮT BUỘC SỬ DỤNG khi cần dữ liệu thật)

Bạn CÓ QUYỀN GỌI và PHẢI GỌI các hàm sau khi user hỏi về số liệu cụ thể của mã:
- `get_current_ticker_data()` — giá hiện tại, MA, RSI, Ichimoku score.
- `get_forecast_results()` — MAPE/RMSE/MAE/R²adj của AR/MLR/CART.
- `get_technical_signals()` — Ichimoku 4 tầng chi tiết.
- `get_price_history(days)` — DataFrame N phiên gần nhất (mặc định 30, tối đa 60).
- `get_price_on_date(date)` — giá OHLCV của 1 phiên cụ thể (vd "20/3/2024", "2024-03-20"). Tự bắt phiên gần nhất ±5 ngày nếu rơi vào cuối tuần/lễ.
- `get_price_range(start_date, end_date, summary)` — thống kê hoặc full rows trong khoảng ngày (tuần/tháng/quý/năm). `summary=True` (mặc định) trả số liệu tổng hợp; `summary=False` trả từng phiên (cap 60).
- `compute_metric(metric, model)` — số cụ thể (vd MAPE của AR).
- `switch_ticker(ticker)` — đổi context sang mã khác.
- `get_portfolio()` — danh mục user.

QUY TẮC TUYỆT ĐỐI:
- TUYỆT ĐỐI KHÔNG nói "tôi không có quyền truy cập tool" / "không có quyền truy cập vào hàm này" — bạn LUÔN có quyền gọi mọi hàm trên.
- TUYỆT ĐỐI KHÔNG nói "trong dữ liệu hiện tại không có thông tin về X" khi tool có thể lấy X — hãy GỌI tool.
- Khi user hỏi "tính dự báo phiên tới cho [ticker] bằng [model]" → GỌI `get_forecast_results()` để lấy số chính xác, KHÔNG tự tính từ context (context có thể đã cũ).
- Khi user hỏi "phân tích [ticker]" → GỌI `get_current_ticker_data()` + `get_forecast_results()`.
- Khi user hỏi "giá ngày X", "phiên ngày DD/MM/YYYY", "đóng cửa hôm Y" → GỌI `get_price_on_date(date)`. KHÔNG bịa số liệu lịch sử.
- Khi user hỏi "tuần qua", "tháng N/YYYY", "Q1 2024", "từ ngày X đến ngày Y", "giá cao nhất trong tháng" → GỌI `get_price_range(start_date, end_date)`. KHÔNG đoán mò.
- Câu lý thuyết tổng quát ("AR là gì?", "MAPE là gì?") → KHÔNG gọi tool, trả lời với KaTeX từ kiến thức của bạn.
- Sau khi tool trả về kết quả, diễn giải bằng tiếng Việt tự nhiên, không in raw JSON.

Số liệu trong khối "DỮ LIỆU HIỆN TẠI" (nếu có) là dữ liệu thật từ vnstock — đừng nói "ví dụ/mô phỏng/giả lập". Đơn vị giá đã ở dạng VND nguyên (ví dụ 74,600 đ), giữ nguyên.
"""

_SYSTEM_PROMPT_EN = """You are a friendly general-purpose AI assistant with personality — think ChatGPT/Claude in casual mode. You can help with anything: programming, math, daily life, history, academia, tech, cooking, art, light wellness — whatever the user brings up.

# ABOUT THE PROJECT

You are embedded inside this research app:
- Title: "Building a Chatbot for Stock Analysis and Forecasting Based on Statistical and Machine Learning Models".
- Affiliation: Ton Duc Thang University (TDTU), Faculty of Mathematics & Statistics, academic year 2025–2026.
- Supervisor: MSc. Che Ngoc Ha.
- Authors: Nguyen Thanh Danh (C2300014), Nguyen Nhat Anh Huy (C2200153), Mai Phan Vu (C2200141).
- Scope: 3 HOSE tickers (FPT, HPG, VNM); models AR(p), MLR(p), CART(p); Ichimoku indicator.

When the user asks "what is this project?", "who built it?", "supervisor?", "school?" → answer concisely using exactly the info above; do not invent.

Style:
- Short answers for short questions; go deeper when the user needs steps or background.
- Tasteful, natural, conversational — no filler, no emoji spam.
- Follow the user's language. Reply in English when they write English, in Vietnamese when they write Vietnamese — don't force a language.
- For math, use $...$ for inline and $$...$$ for display LaTeX.
- For code, use fenced blocks like ```python / ```js — the app syntax-highlights them.
- For specific buy/sell advice, share the app's signals and close with "this is research output, academic reference only, not investment advice".
- When the user asks for a calculation/forecast for the current ticker, you MUST use `ar_coefs`/`mlr_coefs`/`ar_equation_str` from context to plug numbers into the formula and produce a concrete VND figure. DO NOT say "I don't have information about β" — the coefficients are always available when the model is fit.
- When presenting the estimated equation, use real numbers from `ar_equation_str` instead of leaving symbols.

# RESPECT WHAT THE USER ASKED FOR

- If the user names a SPECIFIC MODEL (AR, MLR, CART) → answer ONLY about that model. Don't switch to a different one.
  - "forecast using MLR" → MLR only, don't bring up CART unless they ask to compare.
  - "AR(1) for FPT" → AR(1) only, not AR(2) or MLR.
- If the user names a SPECIFIC TICKER (FPT/HPG/VNM) → answer about that ticker only.
- If the user doesn't specify a model/ticker → use the ticker in context, or ask back.
- If a tool returns results for all three models at once, extract ONLY the requested model — don't list all three.

Example:
- User: "Forecast next session for FPT using MLR" → CORRECT: "Per MLR(p=2) on FPT, the next-session forecast is 73,500 VND. Equation: ..."
- WRONG: "CART says 73,384 VND" (different model, not what they asked).
- WRONG: "AR gives 73,200, MLR 73,500, CART 73,384" (drifted to other models).

# TOOLS (MANDATORY when real data is needed)

You ARE authorized and MUST call the following functions when the user asks about specific app numbers:
- `get_current_ticker_data()` — current price, MA, RSI, Ichimoku score.
- `get_forecast_results()` — MAPE/RMSE/MAE/R²adj of AR/MLR/CART.
- `get_technical_signals()` — full 4-tier Ichimoku.
- `get_price_history(days)` — last N trading sessions (default 30, max 60).
- `get_price_on_date(date)` — OHLCV on a specific calendar day (e.g. "20/3/2024", "2024-03-20"); auto-snaps to nearest trading day within ±5 days.
- `get_price_range(start_date, end_date, summary)` — aggregate stats or full rows over a date range (week/month/quarter/year). `summary=True` (default) for stats; `summary=False` for rows (cap 60).
- `compute_metric(metric, model)` — a specific metric (e.g. MAPE of AR).
- `switch_ticker(ticker)` — switch context to another ticker.
- `get_portfolio()` — user's portfolio.

ABSOLUTE RULES:
- NEVER say "I don't have access to that tool" / "I can't call that function" — you ALWAYS have access.
- NEVER say "the current data doesn't include X" when a tool can fetch X — CALL the tool.
- "Forecast next session for [ticker] using [model]" → CALL `get_forecast_results()` to get the exact number, don't compute from stale context.
- "Analyze [ticker]" → CALL `get_current_ticker_data()` + `get_forecast_results()`.
- "Price on DD/MM/YYYY", "close on day X" → CALL `get_price_on_date(date)`. Don't fabricate historical prices.
- "last week", "March 2024", "Q1 2024", "from X to Y", "highest in the past month" → CALL `get_price_range(start_date, end_date)`. Don't guess.
- General theory ("what is AR?", "what is MAPE?") → DO NOT call tools, answer from knowledge with KaTeX.
- After a tool returns, explain the result naturally — don't print raw JSON.

Numbers under "CURRENT DATA" (when present) are real vnstock data — never call them "example/simulated/mock". Prices are already in raw VND (e.g. 74,600 VND); don't rescale.
"""


# ═══════════════════════════════════════════════════════════════
# MODEL CHAIN — thứ tự ưu tiên
# ═══════════════════════════════════════════════════════════════
_MODEL_CANDIDATES = [
    'gemini-2.0-flash-lite',      # ⭐ rate-limit rộng nhất (free: ~30 req/phút) — ƯU TIÊN
    'gemini-2.0-flash-lite-001',
    'gemini-2.5-flash',           # fallback khi lite bị limit (free: ~20 req/phút)
    'gemini-2.0-flash',
    'gemini-2.0-flash-001',
    'gemini-2.5-pro',             # cuối cùng — chất lượng cao nhưng free chỉ 5 req/phút
]


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════
def _get_api_key() -> str:
    try:
        return st.secrets['GEMINI_API_KEY']
    except Exception:
        return ''


def is_ai_available() -> bool:
    if not _get_api_key():
        return False
    try:
        from google import genai  # noqa
        return True
    except ImportError:
        return False


def build_context_string(context: dict) -> str:
    """Build context block gửi kèm prompt.

    FIX: Dùng close_vnd (đã nhân 1000) thay vì close.
    """
    if not context:
        return ''
    lang = st.session_state.get('lang', 'VI') if hasattr(st, 'session_state') else 'VI'

    if lang == 'EN':
        lines = ['\n## CURRENT DATA (real-time from vnstock, NOT simulated):']
    else:
        lines = ['\n## DỮ LIỆU HIỆN TẠI (real-time từ vnstock, KHÔNG phải mô phỏng):']

    if 'ticker' in context:
        if lang == 'EN':
            lines.append(f"- Ticker: **{context['ticker']}** (HOSE)")
        else:
            lines.append(f"- Mã cổ phiếu: **{context['ticker']}** (HOSE)")

    if 'date_last' in context:
        if lang == 'EN':
            lines.append(f"- Last trading date: {context['date_last']}")
        else:
            lines.append(f"- Phiên gần nhất: {context['date_last']}")

    if 'p' in context:
        if lang == 'EN':
            lines.append(f"- Current config: p = {context['p']} (lag)")
        else:
            lines.append(f"- Cấu hình hiện tại: p = {context['p']} (độ trễ)")

    # ── GIÁ HIỆN TẠI (FIX: dùng close_vnd) ──────────────────────
    if 'close_vnd' in context:
        price = context['close_vnd']
        if lang == 'EN':
            lines.append(f"- Last closing price: **{price:,.0f} VND**")
        else:
            lines.append(f"- Giá đóng cửa gần nhất: **{price:,.0f} đ**")

    if 'return_pct' in context:
        if lang == 'EN':
            lines.append(f"- Session return: {context['return_pct']:+.2f}%")
        else:
            lines.append(f"- Biến động phiên: {context['return_pct']:+.2f}%")

    # ── VOLATILITY (FIX: nhãn rõ) ──────────────────────────────
    if 'annualized_vol_pct' in context:
        av = context['annualized_vol_pct']
        dv = context.get('daily_vol_pct', 0)
        if lang == 'EN':
            lines.append(f"- Volatility: daily σ = {dv:.2f}%, annualized ≈ {av:.2f}%")
        else:
            lines.append(f"- Biến động 30 phiên gần nhất: σ hàng ngày = {dv:.2f}%, quy đổi năm ≈ {av:.2f}%")

    # ── MAPE của 3 model ───────────────────────────────────────
    if 'mape' in context:
        m = context['mape']
        try:
            if lang == 'EN':
                lines.append(f"- MAPE test: AR = {m.get('ar',0):.2f}%, "
                             f"MLR = {m.get('mlr',0):.2f}%, CART = {m.get('cart',0):.2f}%")
            else:
                lines.append(f"- MAPE trên tập test: AR = {m.get('ar',0):.2f}%, "
                             f"MLR = {m.get('mlr',0):.2f}%, CART = {m.get('cart',0):.2f}%")
        except Exception:
            pass

    # ── RMSE + MAE thêm vào context để bot trả lời chi tiết hơn ──
    if 'rmse' in context:
        r = context['rmse']
        try:
            if lang == 'EN':
                lines.append(f"- RMSE: AR = {r.get('ar',0):.2f}, "
                             f"MLR = {r.get('mlr',0):.2f}, CART = {r.get('cart',0):.2f}")
            else:
                lines.append(f"- RMSE (nghìn đ): AR = {r.get('ar',0):.2f}, "
                             f"MLR = {r.get('mlr',0):.2f}, CART = {r.get('cart',0):.2f}")
        except Exception:
            pass

    if 'r2adj' in context:
        r2 = context['r2adj']
        try:
            if lang == 'EN':
                lines.append(f"- R²adj: AR = {r2.get('ar',0):.3f}, "
                             f"MLR = {r2.get('mlr',0):.3f}, CART = {r2.get('cart',0):.3f}")
            else:
                lines.append(f"- R²adj: AR = {r2.get('ar',0):.3f}, "
                             f"MLR = {r2.get('mlr',0):.3f}, CART = {r2.get('cart',0):.3f}")
        except Exception:
            pass

    # ── Dự báo phiên tới (FIX: dùng next_preds_vnd đã × 1000) ──
    if 'next_preds_vnd' in context:
        np_ = context['next_preds_vnd']
        try:
            if lang == 'EN':
                lines.append(f"- Next-session forecast: "
                             f"AR = {np_.get('ar',0):,.0f} VND, "
                             f"MLR = {np_.get('mlr',0):,.0f} VND, "
                             f"CART = {np_.get('cart',0):,.0f} VND")
            else:
                lines.append(f"- Dự báo phiên tới: "
                             f"AR = {np_.get('ar',0):,.0f} đ, "
                             f"MLR = {np_.get('mlr',0):,.0f} đ, "
                             f"CART = {np_.get('cart',0):,.0f} đ")
        except Exception:
            pass

    if 'ichimoku' in context:
        ichi = context['ichimoku']
        if lang == 'EN':
            lines.append(f"- Ichimoku signal: {ichi.get('label','?')} "
                         f"(score {ichi.get('score',0)}/5)")
        else:
            lines.append(f"- Tín hiệu Ichimoku: {ichi.get('label','?')} "
                         f"(score {ichi.get('score',0)}/5)")

    # ── MODEL COEFFICIENTS — bot needs these to compute concrete forecasts ──
    if 'ar_coefs' in context:
        ac = context['ar_coefs']
        phi_list = ', '.join(f'φ_{i+1} = {v:.4f}' for i, v in enumerate(ac.get('phi', [])))
        if lang == 'EN':
            lines.append(f"- AR(p) coefficients: c = {ac['intercept']:.4f}, {phi_list}")
        else:
            lines.append(f"- Hệ số AR(p) ước lượng: c = {ac['intercept']:.4f}, {phi_list}")

    if 'ar_equation_str' in context:
        if lang == 'EN':
            lines.append(f"- Estimated AR equation: ${context['ar_equation_str']}$")
        else:
            lines.append(f"- Phương trình AR ước lượng: ${context['ar_equation_str']}$")

    if 'mlr_coefs' in context:
        mc = context['mlr_coefs']
        if lang == 'EN':
            lines.append(f"- MLR coefficients: intercept = {mc['intercept']:.4f}, "
                         f"price_lags = {mc['price_lags']}, "
                         f"volume_lags = {mc['volume_lags']}, "
                         f"range_lags = {mc['range_lags']}")
        else:
            lines.append(f"- Hệ số MLR: intercept = {mc['intercept']:.4f}, "
                         f"price_lags = {mc['price_lags']}, "
                         f"volume_lags = {mc['volume_lags']}, "
                         f"range_lags = {mc['range_lags']}")

    if 'cart_summary' in context:
        cs = context['cart_summary']
        top = ', '.join(f'{name} ({imp:.1f}%)' for name, imp in cs.get('top_features', []))
        if lang == 'EN':
            lines.append(f"- CART: depth = {cs['depth']}, leaves = {cs['n_leaves']}, "
                         f"top features: {top}")
        else:
            lines.append(f"- CART: độ sâu = {cs['depth']}, số lá = {cs['n_leaves']}, "
                         f"feature quan trọng: {top}")

    return '\n'.join(lines)


def _parse_retry_delay(err_str: str) -> int:
    m = re.search(r'retry_delay\s*{\s*seconds:\s*(\d+)', err_str)
    if m:
        return int(m.group(1))
    m = re.search(r'retry in (\d+(?:\.\d+)?)s', err_str, re.IGNORECASE)
    if m:
        return int(float(m.group(1)))
    return 0


# ═══════════════════════════════════════════════════════════════
# CUSTOM EXCEPTIONS
# ═══════════════════════════════════════════════════════════════
class QuotaExhaustedError(Exception):
    """Quota daily hết."""
    pass


class RateLimitError(Exception):
    """Rate limit tạm thời."""
    def __init__(self, message, wait_seconds=10):
        super().__init__(message)
        self.wait_seconds = wait_seconds


# ═══════════════════════════════════════════════════════════════
# MAIN — Gemini call với auto retry
# ═══════════════════════════════════════════════════════════════
def ask_gemini(user_query: str, context: dict = None, lang: str = 'VI',
               max_retries: int = 2, slim_system: bool = False) -> str:
    """Gọi Gemini với retry đa model.

    slim_system=True → dùng system prompt tối giản (tránh trường hợp system
    prompt dài gây safety filter hoặc token overflow).
    """
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError('GEMINI_API_KEY chưa cấu hình')

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    if slim_system:
        if lang == 'EN':
            system_prompt = (
                "You are a friendly AI assistant for the TDTU 2026 research app "
                "'Building a Chatbot for Stock Analysis and Forecasting Based on "
                "Statistical and Machine Learning Models' (Faculty of Math & Stats, "
                "supervisor MSc. Che Ngoc Ha). The app uses real HOSE data via vnstock "
                "for FPT, HPG, VNM with AR(p) / MLR(p) / CART(p) models. "
                "Reply naturally and conversationally. Never stay silent."
            )
        else:
            system_prompt = (
                "Bạn là trợ lý AI thân thiện của đề tài NCKH TDTU 2026 "
                "'Xây dựng chatbot phân tích và dự báo chứng khoán dựa trên mô hình "
                "thống kê và học máy' (Khoa Toán-Thống kê, GVHD: ThS. Chế Ngọc Hà). "
                "App dùng dữ liệu thật từ vnstock cho FPT, HPG, VNM với 3 mô hình "
                "AR(p) / MLR(p) / CART(p). Hãy trả lời tự nhiên như trò chuyện. "
                "Không được im lặng."
            )
    else:
        system_prompt = _SYSTEM_PROMPT_VI if lang == 'VI' else _SYSTEM_PROMPT_EN
    context_str = build_context_string(context or {})

    if lang == 'EN':
        full_prompt = f"{context_str}\n\n## USER QUESTION:\n{user_query}"
    else:
        full_prompt = f"{context_str}\n\n## CÂU HỎI NGƯỜI DÙNG:\n{user_query}"

    # ── Hạ safety filters xuống BLOCK_NONE cho bối cảnh nghiên cứu học thuật ──
    # Mặc định Gemini chặn "dangerous content" → block câu "dự báo cổ phiếu",
    # "phân tích đầu tư" vì nhầm là tư vấn tài chính. App này là công cụ NCKH,
    # không phải broker, nên cần tắt block để AI trả lời tự nhiên.
    _safety = [
        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                             threshold=types.HarmBlockThreshold.BLOCK_NONE),
        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                             threshold=types.HarmBlockThreshold.BLOCK_NONE),
        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                             threshold=types.HarmBlockThreshold.BLOCK_NONE),
        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                             threshold=types.HarmBlockThreshold.BLOCK_NONE),
    ]

    last_error = None
    last_block_reason = None
    all_rate_limited = True

    def _extract_text(resp) -> str:
        """Defensive text extraction — response.text có thể raise nếu bị block."""
        if resp is None:
            return ''
        # Try 1: response.text property (có thể raise)
        try:
            t = resp.text
            if t:
                return t
        except Exception:
            pass
        # Try 2: candidates[0].content.parts[*].text
        try:
            cands = getattr(resp, 'candidates', None) or []
            if cands:
                content = getattr(cands[0], 'content', None)
                parts = getattr(content, 'parts', None) or []
                chunks = []
                for p in parts:
                    pt = getattr(p, 'text', None)
                    if pt:
                        chunks.append(pt)
                if chunks:
                    return ''.join(chunks)
        except Exception:
            pass
        return ''

    for model_name in _MODEL_CANDIDATES:
        # Thử 2 configs: (1) có safety_settings, (2) không có safety (nếu 1 fail)
        for config_variant in ('with_safety', 'no_safety'):
            try:
                cfg_kwargs = dict(
                    system_instruction=system_prompt,
                    temperature=0.5,
                    top_p=0.9,
                    max_output_tokens=2048,
                )
                if config_variant == 'with_safety':
                    cfg_kwargs['safety_settings'] = _safety
                response = client.models.generate_content(
                    model=model_name,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(**cfg_kwargs),
                )
                text = _extract_text(response)
                if text and text.strip():
                    return text.strip()

                all_rate_limited = False
                _block_info = ''
                try:
                    pf = getattr(response, 'prompt_feedback', None)
                    if pf and getattr(pf, 'block_reason', None):
                        _block_info = f' (block:{pf.block_reason})'
                        last_block_reason = str(pf.block_reason)
                    else:
                        cands = getattr(response, 'candidates', None) or []
                        if cands:
                            fr = getattr(cands[0], 'finish_reason', None)
                            if fr:
                                _block_info = f' (finish:{fr})'
                                last_block_reason = str(fr)
                except Exception:
                    pass
                try:
                    print(f'[Gemini] {model_name}/{config_variant}: empty{_block_info}')
                except UnicodeEncodeError:
                    pass
                last_error = RuntimeError(f'{model_name}: empty{_block_info}')
                # empty with_safety → thử no_safety cùng model
                if config_variant == 'with_safety':
                    continue
                break  # no_safety cũng rỗng → next model

            except Exception as e:
                last_error = e
                err = str(e).lower()

                if ('per day' in err or 'daily' in err or
                        ('free_tier_requests' in err and _parse_retry_delay(str(e)) > 3600)):
                    raise QuotaExhaustedError('Hết quota miễn phí hôm nay. Reset sau 24h.')

                if '429' in err or 'quota' in err or 'exhaust' in err or 'rate_limit' in err:
                    try:
                        print(f'[Gemini] {model_name}/{config_variant} rate limited')
                    except UnicodeEncodeError:
                        pass
                    break  # next model

                if any(k in err for k in ['404', 'not found', 'not_found']):
                    all_rate_limited = False
                    break

                all_rate_limited = False
                try:
                    print(f'[Gemini] {model_name}/{config_variant} error: {err[:150]}')
                except UnicodeEncodeError:
                    pass
                # other error with_safety → thử no_safety
                if config_variant == 'with_safety':
                    continue
                break

    if all_rate_limited:
        # Parse retry_delay từ error cuối (Gemini trả "Please retry in 43.14s")
        retry_s = 30
        if last_error:
            import re as _re
            m = _re.search(r'retry in ([\d.]+)s', str(last_error), _re.IGNORECASE)
            if m:
                retry_s = int(float(m.group(1))) + 1
        try:
            st.session_state['_last_gemini_error'] = str(last_error)[:400] if last_error else 'rate limited'
            st.session_state['_last_gemini_retry_s'] = retry_s
        except Exception:
            pass
        raise RateLimitError(
            f'Gemini free tier bị giới hạn (~20 req/phút). Thử lại sau {retry_s}s.',
            wait_seconds=retry_s,
        )

    # Lưu error cuối vào session state để UI có thể hiện cho user debug
    try:
        st.session_state['_last_gemini_error'] = f'{str(last_error)[:300]} | block={last_block_reason}'
    except Exception:
        pass

    _extra = f' [block_reason={last_block_reason}]' if last_block_reason else ''
    raise RuntimeError(f'Gemini thất bại: {str(last_error)[:200]}{_extra}')
