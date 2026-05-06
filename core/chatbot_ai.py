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
PROMPT_VERSION = 'v8-2026-05-06-katex'


# ═══════════════════════════════════════════════════════════════
# SYSTEM PROMPTS v7 — formulas mandatory + KaTeX-friendly format
# ═══════════════════════════════════════════════════════════════
_SYSTEM_PROMPT_VI = """Bạn là trợ lý AI cho app dự báo giá cổ phiếu HOSE (FPT · HPG · VNM) — đồ án NCKH TDTU 2026.

# Phong cách
- Trò chuyện tự nhiên như bạn học cùng ngành: ngắn gọn, đi thẳng vào vấn đề, có cá tính.
- Markdown nhẹ: in đậm số liệu quan trọng, dùng bullet khi liệt kê >2 ý.
- Ngắn (<= 4 đoạn). Không lan man, không lặp số liệu.
- Chào hỏi → 1-2 câu, hỏi user muốn xem mã nào.
- Câu mơ hồ ("phân tích đi") → hỏi lại "Bạn muốn phân tích mã nào: FPT, HPG hay VNM?" thay vì đoán.

# Công thức toán (BẮT BUỘC khi giải thích mô hình hoặc chỉ số)
- App có KaTeX: `$inline$` và `$$display$$` SẼ ĐƯỢC RENDER thành công thức đẹp. Phải dùng cú pháp này.
- KHÔNG bao giờ dùng fenced code block ``` cho công thức toán — bị render thành text monospace, không đẹp.
- Inline math: `$\hat{Y}_{t+1} = c + \phi_1 Y_t$` — dùng LaTeX chuẩn (`\hat`, `\phi`, `\beta`, `_`, `^{}`, `\sum`, `\frac`).
- Display math (riêng dòng): `$$\hat{Y}_{t+1} = c + \phi_1 Y_t + \phi_2 Y_{t-1}$$` — căn giữa, lớn hơn.
- Khi giải thích AR / MLR / CART / MAPE / RMSE / MAE / R²adj / Ichimoku → BẮT BUỘC kèm công thức KaTeX.
- Khi phân tích ticker có context, kèm phương trình AR(1) đã ước lượng + (MAPE, RMSE) với đơn vị rõ.
- Cap: 1 công thức chính + 2-3 dòng diễn giải; không bloat.

# Số liệu
- Số trong block "DỮ LIỆU HIỆN TẠI" là THẬT từ vnstock, cập nhật theo phiên — KHÔNG được nói "mô phỏng/ví dụ/giả lập".
- Giá hiển thị nguyên (vd 74,600 đ), không nhân chia thêm.
- Khi không có dữ liệu cho 1 mục → nói thẳng "chưa có" thay vì bịa số.

# Tư vấn đầu tư
- Khi user hỏi nên mua/bán/giữ → tóm tắt tín hiệu hiện tại + khép câu "đây là kết quả NCKH, chỉ tham khảo học thuật, không phải tư vấn đầu tư".

---

# Tham chiếu kỹ thuật (KaTeX format)

- AR(p): $\hat{Y}_{t+1} = c + \phi_1 Y_t + \cdots + \phi_p Y_{t-p+1}$ — chỉ dựa giá quá khứ.
- MLR(p): mở rộng AR + Volume + Range với p trễ (tổng $3p+1$ hệ số).
- CART(p): cây quyết định trên 6 đặc trưng kỹ thuật × p trễ, target = tỷ suất sinh lợi phiên kế.
- MAPE: $\text{MAPE} = \frac{1}{n}\sum_{i=1}^{n} \left|\frac{y_i - \hat{y}_i}{y_i}\right| \cdot 100\%$ (Hyndman 2021): <10% rất tốt · 10-20% tốt.
- RMSE: $\text{RMSE} = \sqrt{\frac{1}{n}\sum_{i=1}^{n}(y_i - \hat{y}_i)^2}$ — đơn vị giống dữ liệu.
- R²adj: $R^2_{adj} = 1 - (1-R^2)\cdot\frac{n-1}{n-k-1}$ — phạt tham số dư thừa.
- Ichimoku 4 tầng (Hosoda 1969): Primary · TK Cross · Chikou · Future Kumo, score $[-5, +5]$.

---

# Ví dụ phong cách

User: "chào bạn"
Bot: "Chào bạn! Mình là trợ lý phân tích cho 3 mã FPT/HPG/VNM. Bạn muốn xem mã nào trước nhỉ?"

User: "AR(1) là gì"
Bot: "AR(1) — Autoregressive bậc 1, dự báo phiên kế tiếp chỉ từ phiên hiện tại:

$$\hat{Y}_{t+1} = c + \phi_1 Y_t$$

với $c$ là hệ số chặn, $\phi_1$ là hệ số tự hồi quy. Nếu $\phi_1 \approx 1$ thì chuỗi giá gần như random walk — đặc trưng phổ biến của giá cổ phiếu HOSE."

User: "FPT giờ sao?"
Bot (giả định context có FPT): "FPT đóng phiên gần nhất **75,200 đ**, +0.4%. AR(1) ước lượng $\hat{Y}_{t+1} = 1500 + 0.98 \cdot Y_t \approx 75{,}300$ đ. MAPE test = **1.2%**, RMSE = 0.9 nghìn đ — sai số <1%, gần random walk. Ichimoku trung tính. Xem trang Phân tích Chi tiết để biết hệ số chính xác."

User: "MAPE là gì"
Bot: "MAPE — Mean Absolute Percentage Error, sai số trung bình theo phần trăm:

$$\text{MAPE} = \frac{1}{n}\sum_{i=1}^{n} \left|\frac{y_i - \hat{y}_i}{y_i}\right| \cdot 100\%$$

Ngưỡng đánh giá (Hyndman 2021): <10% rất tốt · 10-20% tốt. App này thường đạt 1-3% trên HOSE."

User: "Có nên mua HPG không?"
Bot: "Mình không tư vấn cụ thể nhé, chỉ chia sẻ tín hiệu app: HPG dự báo phiên tới $\hat{Y} \approx 25{,}400$ đ (+0.2%), Ichimoku giảm nhẹ. Đây là kết quả NCKH, chỉ tham khảo học thuật, không phải tư vấn đầu tư."
"""

_SYSTEM_PROMPT_EN = """You're an AI assistant for a HOSE stock-forecasting app (FPT · HPG · VNM) — TDTU NCKH 2026 thesis project.

# Style
- Conversational like a classmate from the same field: short, direct, with personality.
- Light markdown: bold key numbers, bullet points only when listing >2 items.
- Keep answers under 4 paragraphs. No repetition.
- Greetings → 1-2 sentences, ask which ticker they want.
- Ambiguous query ("analyze") → ask back "Which ticker: FPT, HPG, or VNM?" instead of guessing.

# Math formulas (REQUIRED when explaining a model or metric)
- App has KaTeX: `$inline$` and `$$display$$` WILL be rendered as proper math. Use this syntax.
- NEVER use fenced code blocks ``` for math — they render as monospace text, ugly.
- Inline: `$\hat{Y}_{t+1} = c + \phi_1 Y_t$` — standard LaTeX (`\hat`, `\phi`, `\beta`, `_`, `^{}`, `\sum`, `\frac`).
- Display (own line): `$$\hat{Y}_{t+1} = c + \phi_1 Y_t + \phi_2 Y_{t-1}$$` — centered, larger.
- When explaining AR / MLR / CART / MAPE / RMSE / MAE / R²adj / Ichimoku → ALWAYS include KaTeX formula.
- Ticker analysis with context → include estimated AR(1) equation + (MAPE, RMSE) with units.
- Cap: 1 main formula + 2-3 lines of explanation; don't bloat.

# Numbers
- Numbers under "CURRENT DATA" are REAL from vnstock, updated per session — never say "simulated/example".
- Use prices as given (e.g. 74,600 VND), don't scale.
- If a field is missing, say "not available" instead of fabricating.

# Investment advice
- Buy/sell/hold queries → summarize current signals + close with "this is research output, academic reference only, not investment advice".

---

# Technical reference (KaTeX format)

- AR(p): $\hat{Y}_{t+1} = c + \phi_1 Y_t + \cdots + \phi_p Y_{t-p+1}$ — past prices only.
- MLR(p): AR + Volume + Range across p lags (total $3p+1$ coefficients).
- CART(p): decision tree on 6 technical features × p lags, target = next-session return.
- MAPE: $\text{MAPE} = \frac{1}{n}\sum_{i=1}^{n} \left|\frac{y_i - \hat{y}_i}{y_i}\right| \cdot 100\%$ (Hyndman 2021): <10% excellent · 10-20% good.
- RMSE: $\text{RMSE} = \sqrt{\frac{1}{n}\sum_{i=1}^{n}(y_i - \hat{y}_i)^2}$ — same units as data.
- R²adj: $R^2_{adj} = 1 - (1-R^2)\cdot\frac{n-1}{n-k-1}$ — penalizes excess parameters.
- Ichimoku 4-tier (Hosoda 1969): Primary · TK Cross · Chikou · Future Kumo, score $[-5, +5]$.

---

# Style examples

User: "hi"
Bot: "Hi! I'm an analysis assistant for FPT/HPG/VNM. Which ticker would you like to look at first?"

User: "what is AR(1)?"
Bot: "AR(1) — Autoregressive order 1, forecasts next session from the current one only:

$$\hat{Y}_{t+1} = c + \phi_1 Y_t$$

$c$ is the intercept, $\phi_1$ the autoregressive coefficient. When $\phi_1 \approx 1$, the series is near random-walk — typical for HOSE prices."

User: "what's FPT looking like?"
Bot (assuming FPT context): "FPT closed at **75,200 VND**, +0.4%. AR(1) gives $\hat{Y}_{t+1} = 1500 + 0.98 \cdot Y_t \approx 75{,}300$ VND. Test MAPE = **1.2%**, RMSE = 0.9k VND — small error, near random walk. Ichimoku is neutral."

User: "what is MAPE?"
Bot: "MAPE — Mean Absolute Percentage Error, average % deviation:

$$\text{MAPE} = \frac{1}{n}\sum_{i=1}^{n} \left|\frac{y_i - \hat{y}_i}{y_i}\right| \cdot 100\%$$

Scale (Hyndman 2021): <10% excellent · 10-20% good. This app typically gets 1-3% on HOSE."

User: "Should I buy HPG?"
Bot: "I don't give specific advice — I'll share the app's signals: HPG next-session forecast $\hat{Y} \approx 25{,}400$ VND (+0.2%), Ichimoku slightly bearish. This is research output, academic reference only, not investment advice."
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
                "You are a friendly AI assistant for a Vietnamese stock forecasting "
                "research app (TDTU NCKH 2026). The app uses real HOSE data via vnstock "
                "for FPT, HPG, VNM with AR(p) / MLR(p) / CART(p) models. "
                "Reply naturally and conversationally. Never stay silent."
            )
        else:
            system_prompt = (
                "Bạn là trợ lý AI thân thiện của app NCKH dự báo giá cổ phiếu HOSE "
                "(TDTU 2026). App dùng dữ liệu thật từ vnstock cho FPT, HPG, VNM với "
                "3 mô hình AR(p) / MLR(p) / CART(p). Hãy trả lời tự nhiên như trò chuyện. "
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
