"""Rule-based matcher cho các câu hỏi FAQ về app.
Match trước khi gọi AI → tiết kiệm API + trả lời instant.

FIX 2026-04-23:
- C6: Thêm patterns cho MSE (thường bị nhầm với RMSE), metrics overview rộng hơn
- Xử lý câu ngắn: "h là gì", "p là gì", "mape"
- Thêm answer mới: 'mse_explain' (khác RMSE)
- Phân tích ticker → rule-based cụ thể thay vì generic
"""
import re


_ANSWERS_VI = {
    'ar_explain': """### Mô hình AR(p) — Autoregressive bậc p (Box-Jenkins)

Dự báo giá phiên kế tiếp chỉ dựa vào giá quá khứ:

`Ŷ(t+1) = c + φ₁·Y(t) + φ₂·Y(t-1) + ... + φₚ·Y(t-p+1)`

**Tham số:**
- `p` — số phiên quá khứ dùng (lag order)

**Ví dụ:**
- `p=1` → AR(1) cổ điển: dự báo phiên kế tiếp từ phiên hôm nay
- `p=3` → dùng 3 phiên gần nhất (t, t-1, t-2)

**Ưu điểm:** đơn giản, nhanh, không cần nhiều feature.
**Nhược điểm:** không tận dụng được Volume, Range và các chỉ báo kỹ thuật khác.

*Tham khảo: Box, Jenkins, Reinsel & Ljung (2015). Time Series Analysis, 5th ed., Wiley.*""",

    'mlr_explain': """### MLR(p) — Multiple Linear Regression với Distributed Lag

Mở rộng AR bằng cách thêm Volume và Range (High-Low):

`Ŷ(t+1) = β₀ + Σ β₁ₖ·Y(t-k) + Σ β₂ₖ·V(t-k) + Σ β₃ₖ·HL(t-k)`

**Đặc điểm:**
- Tổng `3p + 1` tham số
- Với p=3 → 10 tham số cần ước lượng
- Dự báo phiên kế tiếp

**Phát hiện thực nghiệm trên HOSE:**
MLR cho MAPE gần bằng AR, chứng tỏ Volume và Range đóng góp ít vào dự báo giá — phản ánh tính hiệu quả thông tin của thị trường Việt Nam.""",

    'cart_explain': """### CART(p) — Decision Tree Regression

Chia không gian dữ liệu bằng cây quyết định, không giả định quan hệ tuyến tính.

**Thiết kế:**
- Target: return phiên kế tiếp `R = 100 × (Y(t+1)/Y(t) − 1)`
- Features: Return, Volume_ratio, Range_ratio, MA5/MA20, RSI14 × p lag
- Tổng `6p` features
- Phục hồi giá: `Ŷ(t+1) = Y(t) × (1 + R̂/100)`

**Ưu điểm:** nắm bắt quan hệ phi tuyến, không cần giả định phân phối.
**Nhược điểm:** dễ overfit nếu max_depth lớn, khó ngoại suy ngoài khoảng train.

Dùng GridSearchCV (TimeSeriesSplit n=5) để chọn tự động `max_depth` và `min_samples_leaf` tối ưu.""",

    'p_explain': """### Ý nghĩa tham số p

`p` là số phiên quá khứ dùng để dự báo, áp dụng cho cả 3 mô hình AR, MLR, CART.

**Ví dụ:**
- `p=1` → dùng phiên t-1 (AR(1) cổ điển)
- `p=3` → dùng 3 phiên liên tiếp t-1, t-2, t-3
- `p` lớn → capture pattern dài hơn nhưng dễ overfit

**Quy tắc chọn p an toàn:**
- `p ≤ √n` (n = số quan sát huấn luyện)
- Tránh `p > n/10` để không dư thừa tham số

Với ~2000 quan sát, p ≤ 45 là an toàn. Thực tế p từ 1 đến 5 là đủ cho dữ liệu giá cổ phiếu.""",

    'mape_explain': """### MAPE — Mean Absolute Percentage Error

`MAPE = (1/n) · Σ |Y_actual − Y_pred| / |Y_actual| × 100%`

**Thang đánh giá (Hyndman & Athanasopoulos, 2021):**
- `< 10%` — Rất tốt
- `10 – 20%` — Tốt
- `20 – 50%` — Tạm
- `> 50%` — Kém

**Ưu điểm:** không phụ thuộc đơn vị (scale-free) → so sánh được giữa các mã HOSE có giá khác nhau (FPT ~75 nghìn, HPG ~25 nghìn, VNM ~60 nghìn).

**App này thường đạt MAPE 1-3% trên HOSE** — thuộc nhóm "Rất tốt".""",

    'rmse_explain': """### RMSE — Root Mean Squared Error

`RMSE = √(1/n · Σ (Y_actual − Y_pred)²)`

**Đặc điểm:**
- Đơn vị giống dữ liệu gốc (VNĐ với app này)
- Phạt sai số lớn nặng hơn MAE (do bình phương)
- Phù hợp khi outlier đáng lo

**So với MAPE:**
- RMSE tuyệt đối → không so sánh được giữa FPT và HPG (giá khác nhau)
- MAPE tương đối → so sánh cross-ticker được

Kết hợp cả 2: MAPE để so sánh, RMSE để thấy sai số thực tế theo VNĐ.""",

    'mae_explain': """### MAE — Mean Absolute Error

`MAE = (1/n) · Σ |Y_actual − Y_pred|`

**Đặc điểm:**
- Đơn vị giống dữ liệu gốc (VNĐ)
- Bền với outlier hơn RMSE (không bình phương)
- Trực quan: "trung bình lệch X đồng"

**So với RMSE:**
- Nếu MAE ≈ RMSE → sai số đồng đều
- Nếu RMSE >> MAE → có vài dự báo lệch rất nhiều (outliers)

Trong luận văn, nên báo cáo cả MAE lẫn RMSE để người đọc hiểu phân phối sai số.""",

    'r2_explain': """### R² và R²adj

**R² (Coefficient of Determination):**
`R² = 1 − SS_res / SS_tot`

Tỉ lệ phương sai được giải thích bởi mô hình. Giá trị `[0, 1]`, càng cao càng tốt.

**R²adj (Adjusted R²):**
`R²adj = 1 − (1 − R²) · (n−1)/(n−k−1)`

Trong đó `k` = số tham số. R²adj **phạt mô hình có nhiều tham số không đóng góp**.

**Ngưỡng tham khảo:**
- `> 0.9` — Rất tốt
- `0.7 − 0.9` — Tốt
- `< 0.5` — Yếu

**Lưu ý:** R² có thể lạm dụng — mô hình overfit đạt R² cao trên train nhưng thấp trên test. Báo cáo R²adj trên TEST mới đáng tin.""",

    'mse_explain': """### MSE — Mean Squared Error

`MSE = (1/n) · Σ (Y_actual − Y_pred)²`

**Đặc điểm:**
- Đơn vị là **bình phương** của dữ liệu gốc → khó diễn giải trực tiếp
- Thường được dùng làm **loss function** trong training (đạo hàm được)

**Quan hệ với RMSE:**
`RMSE = √MSE`

Trong báo cáo NCKH, thường dùng RMSE thay cho MSE vì đơn vị dễ hiểu hơn (VNĐ thay vì VNĐ²).""",

    'metrics_overview': """### 4 chỉ số đánh giá chính

| Chỉ số | Công thức | Đơn vị | Vai trò |
|---|---|---|---|
| **MAPE** | `mean(|e|/|y|) × 100` | `%` | So sánh cross-ticker (chính) |
| **RMSE** | `√mean(e²)` | `VNĐ` | Phạt sai số lớn |
| **MAE**  | `mean(|e|)` | `VNĐ` | Sai số trung bình trực quan |
| **R²adj** | `1−SS_res/SS_tot, adj k` | `[0,1]` | Giải thích phương sai |

trong đó `e = Y_actual − Y_pred`.

**MAPE là chính vì:** không phụ thuộc đơn vị → so sánh được FPT (giá cao) với HPG (giá thấp).""",

    'model_compare': """### So sánh 3 mô hình (tất cả dự báo 1 phiên kế tiếp)

| Mô hình | Số tham số | Tính chất | MAPE điển hình HOSE |
|---|---|---|---|
| **AR(p)** | `p+1` | Tuyến tính, đơn giản | 1-3% |
| **MLR(p)** | `3p+1` | Tuyến tính đa biến (Y+V+HL) | 1-3% |
| **CART(p)** | biến động | Phi tuyến (6p features) | 1-3% |

**Phát hiện trên HOSE:** 3 mô hình cho MAPE rất gần nhau (chênh ~0.1-0.2%), phản ánh:
- Giá cổ phiếu có độ ngẫu nhiên cao (gần **random walk**)
- AR(1) đơn giản đã "đủ tốt" — thêm Volume/Range hay non-linearity không cải thiện rõ
- Phù hợp với **Giả thuyết thị trường hiệu quả yếu** (Fama, 1970)

**Khuyến nghị chọn:**
- Baseline NCKH → AR(1)
- Muốn thêm biến kỹ thuật → MLR
- Cần phi tuyến + feature importance → CART""",

    'ichimoku_explain': """### Ichimoku Kinko Hyo (一目均衡表)

Hệ thống phân tích kỹ thuật của **Goichi Hosoda** (Nhật, 1969). App triển khai đầy đủ **4 tầng tín hiệu**:

**1. Primary Trend** — vị trí giá so với mây Kumo
- Giá trên Kumo = xu hướng tăng
- Giá trong Kumo = đi ngang
- Giá dưới Kumo = xu hướng giảm

**2. Trading Signal** — Tenkan-sen (9) cắt Kijun-sen (26)
- Vàng (TK cắt KJ lên) + phù hợp xu hướng chính = mua mạnh
- Chết (TK cắt KJ xuống) + xu hướng giảm = bán mạnh

**3. Chikou Confirmation** — giá t plot lùi 26 phiên
- Xác nhận momentum: giá hiện tại vs giá 26 phiên trước

**4. Future Kumo** — Senkou A/B projected 26 phiên sau
- A > B → Kumo xanh (future bullish)
- A < B → Kumo đỏ (future bearish)

**Tổng hợp:** Score từ `-5` (strong bear) đến `+5` (strong bull). Xem trang "Tín hiệu & Cảnh báo" để biết score hiện tại.""",

    'choose_p': """### Hướng dẫn chọn p (lag order)

**Các bước đề xuất:**
- Bắt đầu: `p = 1` (AR(1) cổ điển)
- Thử nâng lên: `p = 3, 5` để xem có cải thiện không
- Quy tắc an toàn: `p ≤ √n` (n = số sample train)
- Tránh `p > n/10` (dư thừa tham số, dễ overfit)

**Thực tế trên HOSE (~2000 phiên):**
- `p = 1-5` thường là đủ
- `p = 1` cho MAPE rất gần với `p = 3` hoặc `p = 5` → thị trường gần random walk
- Khuyến nghị NCKH: so sánh `p = 1, 3, 5` để minh hoạ""",

    'data_source': """### Nguồn dữ liệu — vnstock (thật, không mô phỏng)

App lấy dữ liệu qua thư viện **vnstock** (Python, tác giả Thinh Vu):
- Kết nối các API công khai: TCBS, VNDIRECT, SSI
- OHLCV (Open/High/Low/Close/Volume) của **HOSE**
- Cập nhật sau 14:45 VN mỗi phiên giao dịch
- Phạm vi: 2016 đến hiện tại

**Chỉ báo kỹ thuật** (MA5, MA20, RSI14, Ichimoku...) được tính trực tiếp từ OHLCV này trong code.

**Đây KHÔNG phải dữ liệu mô phỏng hay giả lập.**""",

    'app_pages': """### 5 trang chính của app

1. **Dashboard Tổng quan** — biểu đồ giá, KPI, dự báo 3 model, tín hiệu Ichimoku tóm tắt
2. **Phân tích Chi tiết** — phương trình mô hình, hệ số, cây CART, scatter residuals
3. **Lịch sử & Dữ liệu** — bảng OHLCV, histogram return, export CSV
4. **Tín hiệu & Cảnh báo** — Ichimoku 4 tầng đầy đủ, score -5 đến +5
5. **Danh mục Đầu tư** — so sánh hiệu suất 3 ticker, correlation matrix
6. **Trợ lý AI** — hội thoại với bot (trang này)""",

    'fpt_info': """### FPT — Tập đoàn FPT

- **Mã**: FPT (HOSE)
- **Ngành**: Công nghệ thông tin, viễn thông, giáo dục
- **Đặc trưng**: tăng trưởng tuyến tính dài hạn, biên độ vừa phải
- **Phù hợp**: AR(1-3), MLR

FPT thường cho **MAPE thấp nhất** trong 3 ticker do xu hướng tương đối ổn định.""",

    'hpg_info': """### HPG — Hòa Phát Group

- **Mã**: HPG (HOSE)
- **Ngành**: Thép, vật liệu xây dựng
- **Đặc trưng**: cổ phiếu **chu kỳ**, biến động cao, nhạy cảm với giá thép thế giới và đầu tư công
- **Phù hợp**: MLR (tận dụng Volume), CART (bắt non-linearity)

HPG thường có **MAPE cao hơn** FPT/VNM do tính chu kỳ.""",

    'vnm_info': """### VNM — Vinamilk

- **Mã**: VNM (HOSE)
- **Ngành**: Sữa và thực phẩm (FMCG)
- **Đặc trưng**: cổ phiếu **phòng thủ**, biên độ thấp, xu hướng giảm dài hạn gần đây
- **Phù hợp**: AR(1-2), biến động ngắn hạn thấp

VNM có **volatility thấp nhất** trong 3 ticker.""",
}


_ANSWERS_EN = {
    'ar_explain':       "### AR(p) Model (Box-Jenkins)\n\n`Ŷ(t+1) = c + φ₁·Y(t) + ... + φₚ·Y(t-p+1)`\n\n**AR** forecasts the next session using only past prices. `p` = number of lags. Simple baseline. Ref: Box, Jenkins, Reinsel & Ljung (2015).",
    'mlr_explain':      "### MLR(p)\n\nExtends AR with Volume + Range (High-Low). Total `3p+1` parameters. Forecasts next session. On HOSE, MAPE ≈ AR → Volume/Range add little value (efficient market).",
    'cart_explain':     "### CART(p)\n\nDecision Tree regression on 6 technical features × p lags = `6p` features. Target = next-session return. Price recovered by `Ŷ(t+1) = Y(t)·(1+R̂/100)`. Non-linear, but can overfit.",
    'p_explain':        "### Parameter `p`\n\n`p` = number of past sessions used as input. Rule of thumb: `p ≤ √n` to avoid overfitting. For HOSE (~2000 obs), p=1-5 is typical.",
    'mape_explain':     "### MAPE\n\n`MAPE = mean(|y-ŷ|/|y|) × 100%`. Scale (Hyndman & Athanasopoulos, 2021): <10% excellent, 10-20% good, 20-50% ok, >50% poor. Scale-free → compares FPT/HPG/VNM.",
    'ichimoku_explain': "### Ichimoku Kinko Hyo\n\nHosoda (1969) — 4-tier signal system:\n1. **Primary Trend** — price vs Kumo cloud\n2. **Trading** — Tenkan × Kijun cross\n3. **Chikou** — 26-period confirmation\n4. **Future Kumo** — 26-period projection\n\nScore -5 (strong bear) to +5 (strong bull).",
    'choose_p':         "### Choosing p\n\nStart with `p=1`. Try `p=3, 5` to compare. Avoid `p > √n` (overfit). On HOSE, `p=1` is usually nearly as good as higher p — near random-walk behavior.",
    'rmse_explain':     "### RMSE\n\n`RMSE = √mean((y-ŷ)²)`. Same units as data (VND). Penalizes large errors more than MAE. Use with MAPE — MAPE for comparison, RMSE for absolute error.",
    'mae_explain':      "### MAE\n\n`MAE = mean(|y-ŷ|)`. Average absolute deviation in VND. Robust to outliers. `MAE ≈ RMSE` → uniform errors. `RMSE >> MAE` → some large outliers.",
    'r2_explain':       "### R² and R²adj\n\n`R² = 1 - SS_res/SS_tot`. Proportion of variance explained. `R²adj` penalizes extra parameters: `1-(1-R²)·(n-1)/(n-k-1)`. Always report R²adj on TEST set.",
    'mse_explain':      "### MSE\n\n`MSE = mean((y-ŷ)²)`. Same as RMSE² — units are squared VND, hard to interpret. Used as loss function during training. For reports, prefer RMSE.",
    'metrics_overview': "### 4 Evaluation Metrics\n\n- **MAPE** (%) — scale-free, primary metric\n- **RMSE** (VND) — penalizes large errors\n- **MAE** (VND) — intuitive average error\n- **R²adj** — variance explained, penalized for k\n\nMAPE is primary because it compares across tickers with different price levels.",
    'model_compare':    "### AR vs MLR vs CART\n\nOn HOSE all 3 give MAPE within 0.1-0.2% of each other. AR(1) is the best baseline — the efficient-market-like behavior means extra features don't help much. Reference: Fama (1970).",
    'data_source':      "### Data Source\n\nReal HOSE market data via **vnstock** Python library (TCBS/VNDIRECT/SSI APIs). OHLCV updated after 14:45 VN each trading session. Range: 2016-present. NOT simulated.",
    'app_pages':        "### 6 App Pages\n\n1. Dashboard Overview\n2. Detailed Analysis\n3. History & Data\n4. Signals & Alerts\n5. Portfolio\n6. AI Assistant (this page)",
    'fpt_info':         "### FPT — FPT Corporation\n\nHOSE. IT/Telecom/Education. Steady growth, moderate volatility. Suited for AR(1-3). Typically lowest MAPE among 3 tickers.",
    'hpg_info':         "### HPG — Hoa Phat Group\n\nHOSE. Steel/Construction. Cyclical, high volatility, sensitive to steel prices. Suited for MLR, CART. Higher MAPE typical.",
    'vnm_info':         "### VNM — Vinamilk\n\nHOSE. Dairy/FMCG. Defensive stock, lowest volatility. Suited for AR(1-2). Long-term downtrend recently.",
}


# ═══════════════════════════════════════════════════════════════
# PATTERNS — được order theo độ cụ thể (specific trước)
# FIX C6: Thêm nhiều pattern cho câu ngắn, bổ sung MSE
# ═══════════════════════════════════════════════════════════════
_PATTERNS = [
    # ── Metrics comparison — ưu tiên KHỚP TRƯỚC specific metrics ──
    (r'(mse|mape|rmse|mae|r[\²2])\s*(và|vs|,|/)\s*(mse|mape|rmse|mae|r[\²2])', 'metrics_overview'),
    (r'(các|all|tất cả|những)\s*(chỉ số|metric|đánh giá|evaluation)', 'metrics_overview'),
    (r'(chỉ số|metric)\s+(đánh giá|evaluation|đo|performance)', 'metrics_overview'),
    (r'(đánh giá|evaluation)\s+(mô hình|model)', 'metrics_overview'),
    (r'(so sánh|compare)\s+(mape|rmse|mae|chỉ số)', 'metrics_overview'),

    # ── MSE riêng (tránh nhầm với RMSE) ──────────────────────────
    (r'\bmse\b(?!\s*rmse)', 'mse_explain'),  # MSE nhưng không phải RMSE

    # ── MAPE ────────────────────────────────────────────────────
    (r'\bmape\b', 'mape_explain'),
    (r'mean absolute percentage', 'mape_explain'),
    (r'(thang|scale|đánh giá).*mape', 'mape_explain'),

    # ── RMSE ────────────────────────────────────────────────────
    (r'\brmse\b', 'rmse_explain'),
    (r'root mean squared?\s*error', 'rmse_explain'),

    # ── MAE ─────────────────────────────────────────────────────
    (r'\bmae\b', 'mae_explain'),
    (r'mean absolute error', 'mae_explain'),

    # ── R² ──────────────────────────────────────────────────────
    (r'r[\²2][\s_-]?(adj|adjusted|hiệu chỉnh)', 'r2_explain'),
    (r'r[\s-]?squared?', 'r2_explain'),
    (r'hệ số xác định', 'r2_explain'),
    (r'coefficient of determination', 'r2_explain'),

    # ── AR ──────────────────────────────────────────────────────
    (r'\bar\s*\(\s*\d+\s*\)', 'ar_explain'),   # AR(1), AR(3)...
    (r'\bar\b.*(là gì|là sao|nghĩa|hoạt động|how|what|explain|work)', 'ar_explain'),
    (r'(là gì|là sao|nghĩa|what|explain).*\bar\b', 'ar_explain'),
    (r'autoregressive', 'ar_explain'),
    (r'(mô hình|model)\s+(tự hồi quy)', 'ar_explain'),

    # ── MLR ─────────────────────────────────────────────────────
    (r'\bmlr\b', 'mlr_explain'),
    (r'multiple linear', 'mlr_explain'),
    (r'hồi quy (bội|đa biến)', 'mlr_explain'),

    # ── CART ────────────────────────────────────────────────────
    (r'\bcart\b', 'cart_explain'),
    (r'decision tree', 'cart_explain'),
    (r'cây quyết định', 'cart_explain'),

    # ── Choose p ───────────────────────────────────────────────
    (r'(chọn|choose|pick|select|nên dùng|recommend)\s*(p|lag)', 'choose_p'),
    (r'(tối ưu|optimal|best)\s*(p|tham số|parameter)', 'choose_p'),

    # ── p ngắn ─────────────────────────────────────────────────
    (r'^\s*p\s*(là gì|nghĩa|what|meaning)\s*\??\s*$', 'p_explain'),
    (r'\btham số\s*p\b', 'p_explain'),
    (r'(ý nghĩa|giải thích|explain)\s+(tham số\s+)?p\b', 'p_explain'),
    (r'(what\s+is|what.s|what.re|whats?)\s+(the\s+)?(parameter\s+)?p\b', 'p_explain'),
    (r'\blag order\b|\bar order\b|\bđộ trễ\b', 'p_explain'),

    # ── Model comparison (phải đứng sau ar/mlr/cart riêng) ─────
    (r'(so sánh|compare|khác nhau|difference|vs|versus)\s.*(ar|mlr|cart|mô hình)', 'model_compare'),
    (r'(ar|mlr|cart)\s.*(so sánh|compare|khác|tốt hơn|better|vs)', 'model_compare'),
    (r'(mô hình nào|which model)\s.*(tốt|best|tốt hơn|chính xác|accurate|reliable|đáng tin)', 'model_compare'),
    (r'(ưu|nhược)\s*điểm\s.*(mô hình|model)', 'model_compare'),

    # ── Ichimoku ────────────────────────────────────────────────
    (r'\b(ichimoku|kinko hyo|kumo|tenkan|kijun|chikou|senkou)\b', 'ichimoku_explain'),
    (r'(mây)\s+(ichimoku|kumo)', 'ichimoku_explain'),
    (r'(tín hiệu|signal)\s.*(4 tầng|score|ichimoku)', 'ichimoku_explain'),

    # ── Data source ────────────────────────────────────────────
    (r'(nguồn|source)\s+(dữ liệu|data)', 'data_source'),  # "nguồn dữ liệu" (word order VI)
    (r'(dữ liệu|data)\s.*(từ đâu|lấy từ|nguồn|source|where)', 'data_source'),
    (r'(dữ liệu|data)\s.*(thật|real|mô phỏng|simulated|fake|giả lập)', 'data_source'),
    (r'\bvnstock\b', 'data_source'),
    (r'\btcbs\b|\bvndirect\b|\bssi\b', 'data_source'),

    # ── App pages ──────────────────────────────────────────────
    (r'(các trang|app page|trang nào|tính năng|feature)\s.*(có gì|gồm|bao gồm|list)', 'app_pages'),
    (r'(ứng dụng|app)\s.*(có những gì|gồm những|includes|contains|overview)', 'app_pages'),

    # ── Ticker info ────────────────────────────────────────────
    (r'\bfpt\b.*(là gì|giới thiệu|company|doanh nghiệp|ngành|what is|about|info)', 'fpt_info'),
    (r'(giới thiệu|about|info|là gì|what is|what.s)\s.*\bfpt\b', 'fpt_info'),
    (r'\bhpg\b.*(là gì|giới thiệu|company|doanh nghiệp|ngành|what is|about|info)', 'hpg_info'),
    (r'(giới thiệu|about|info|là gì|what is|what.s)\s.*\bhpg\b', 'hpg_info'),
    (r'(hòa phát|hoa phat|hoà phát)', 'hpg_info'),
    (r'\bvnm\b.*(là gì|giới thiệu|company|doanh nghiệp|ngành|what is|about|info)', 'vnm_info'),
    (r'(giới thiệu|about|info|là gì|what is|what.s)\s.*\bvnm\b', 'vnm_info'),
    (r'\bvinamilk\b', 'vnm_info'),

    # NOTE: "phân tích FPT/HPG/VNM" KHÔNG còn match rule cứng — để AI dùng
    # context (giá thật, MAPE, dự báo) đưa ra phân tích động thay vì
    # company-info tĩnh. User muốn xem company info → "FPT là gì" / "FPT info".
]


def _strip_diacritics(s: str) -> str:
    """Strip dấu tiếng Việt + đ/Đ → cho phép user gõ không dấu cũng match.
    Ví dụ: 'là gì' → 'la gi', 'chọn' → 'chon'.
    """
    import unicodedata
    s = s.replace('đ', 'd').replace('Đ', 'D')
    return ''.join(c for c in unicodedata.normalize('NFKD', s)
                   if not unicodedata.combining(c))


# Pre-compile diacritic-stripped patterns (1 lần lúc import) → match nhanh + accent-insensitive
_PATTERNS_STRIPPED = [
    (re.compile(_strip_diacritics(p)), intent) for p, intent in _PATTERNS
]


def match_intent(query: str):
    """Match query → intent key hoặc None.

    Accent-insensitive: 'la gi' khớp pattern 'là gì'.
    """
    if not query:
        return None
    q = _strip_diacritics(query.lower().strip().rstrip('?!.,;:'))
    for pat, intent in _PATTERNS_STRIPPED:
        if pat.search(q):
            return intent
    return None


def get_rule_answer(query: str, lang: str = 'VI'):
    """Match rule → câu trả lời, hoặc None."""
    intent = match_intent(query)
    if not intent:
        return None
    answers = _ANSWERS_VI if lang == 'VI' else _ANSWERS_EN
    return answers.get(intent)
