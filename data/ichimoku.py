"""
Ichimoku Kinko Hyo — triển khai chuẩn theo Hosoda (1969) và các bài báo
học thuật về ứng dụng Ichimoku trong dự báo giá cổ phiếu.

THAM KHẢO:
    [1] Hosoda, G. (1969). Ichimoku Kinko Hyo (一目均衡表).
    [2] Patel, M. (2010). Trading with Ichimoku Clouds. Wiley.
    [3] Gurrib, I. (2016). Optimization of the Ichimoku Kinko Hyo trading
        system. International Journal of Monetary Economics and Finance.
    [4] Deng, S. & Zhao, Y. (2021). Ichimoku technical indicators for
        stock market prediction. Applied Economics Letters.
    [5] Shrestha, K. (2022). Ichimoku Cloud and the Japanese equity market.
        Journal of Asian Economics.

═══════════════════════════════════════════════════════════════════════════
  ĐỊNH NGHĨA 5 THÀNH PHẦN CHÍNH (Hosoda 1969, tham số chuẩn 9-26-52)
═══════════════════════════════════════════════════════════════════════════

  Tenkan-sen   = (max H_9  + min L_9)  / 2
  Kijun-sen    = (max H_26 + min L_26) / 2
  Senkou A     = (Tenkan + Kijun) / 2,           dịch TIẾN 26 phiên
  Senkou B     = (max H_52 + min L_52) / 2,      dịch TIẾN 26 phiên
  Chikou span  = Close[t],                        dịch LÙI 26 phiên

Các đường gốc dùng (max H + min L) / 2 — midpoint kiểu Donchian trên
cửa sổ n phiên. Đây là định nghĩa BẤT KHẢ XÂM PHẠM của Ichimoku:
đổi thành (H+L)/2 một phiên hay Close sẽ không còn là Ichimoku.

═══════════════════════════════════════════════════════════════════════════
  ANTI-LEAK
═══════════════════════════════════════════════════════════════════════════

  * Tenkan, Kijun: cửa sổ lùi  → luôn an toàn.
  * Senkou A/B: shift(+26) nên giá trị tại t tính từ t-26 → an toàn tại t.
  * Chikou: shift(-26) nên Chikou[t] = Close[t+26]. Chỉ dùng cho VẼ chart;
    KHÔNG dùng làm feature quyết định tại t.
  * Tín hiệu Chikou confirmation dùng Close[t] vs Close[t-26], tương đương
    về số học với "Chikou vẽ tại t-26 so Close tại t-26", tại t cả 2 đã biết.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import streamlit as st


TENKAN_N  = 9
KIJUN_N   = 26
SENKOU_N  = 52
DISPLACE  = 26


def _df_fingerprint(df: pd.DataFrame) -> tuple:
    """Hash O(1) cho DataFrame OHLC: (first_date, last_date, len, last_close).

    Thêm first_date phòng khi user kéo date_from về xa hơn nhưng len trùng cờ
    với 1 fingerprint cũ (collision rất hiếm nhưng có thể trả wrong cache).
    """
    if len(df) == 0:
        return ('empty', 'empty', 0, 0.0)
    try:
        return (
            str(df['Ngay'].iloc[0]),
            str(df['Ngay'].iloc[-1]),
            int(len(df)),
            float(df['Close'].iloc[-1]),
        )
    except Exception:
        return (id(df), id(df), int(len(df)), 0.0)


def _donchian_mid(high: pd.Series, low: pd.Series, n: int) -> pd.Series:
    """Midpoint kiểu Donchian: (max H + min L) / 2 trên cửa sổ n phiên."""
    return (high.rolling(n, min_periods=n).max()
            + low.rolling(n,  min_periods=n).min()) / 2.0


# Alias giữ backward compatibility với code import cũ
_rolling_midpoint = _donchian_mid


# ═════════════════════════════════════════════════════════════════════════
#  HÀM CHÍNH
# ═════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False, hash_funcs={pd.DataFrame: _df_fingerprint})
def add_ichimoku(df: pd.DataFrame,
                 tenkan_n: int = TENKAN_N,
                 kijun_n:  int = KIJUN_N,
                 senkou_n: int = SENKOU_N,
                 displace: int = DISPLACE) -> pd.DataFrame:
    """
    Thêm 5 thành phần Ichimoku + 3 đặc trưng dẫn xuất (dùng Close).

    Đặc trưng dẫn xuất:

    [1] TK_momentum = (Tenkan − Kijun) / Close × 100  [%]
        Động lượng ngắn hạn. Dương: bull, âm: bear.
        Deng & Zhao (2021): nhạy hơn ratio thuần.

    [2] Cloud_dist = khoảng cách Close tới BIÊN MÂY GẦN NHẤT [%]
        Trên mây:  (Close − Kumo_top) / Close × 100  (> 0)
        Dưới mây:  (Close − Kumo_bot) / Close × 100  (< 0)
        Trong mây: 0
        Patel (2010): đo lực xu hướng qua khoảng cách tới biên mây
        (support/resistance), không phải tâm mây.

    [3] Chikou_momentum = (Close[t-26] − Close[t-52]) / Close[t-52] × 100  [%]
        Return lịch sử 26 phiên tại vị trí hiển thị Chikou (t-26).
        Xác nhận động lượng mà Chikou span đang phản ánh.
        Anti-leak: chỉ dùng Close tại t-26 và t-52.
    """
    required = {'High', 'Low', 'Close'}
    missing  = required - set(df.columns)
    if missing:
        raise KeyError(f'add_ichimoku: df thiếu cột {missing}')

    out = df.copy()
    H, L, C = out['High'], out['Low'], out['Close']

    # ── 5 thành phần Ichimoku gốc (Hosoda 1969) ─────────────────────────
    tenkan = _donchian_mid(H, L, tenkan_n)
    kijun  = _donchian_mid(H, L, kijun_n)
    sen_a  = ((tenkan + kijun) / 2.0).shift(displace)
    sen_b  = _donchian_mid(H, L, senkou_n).shift(displace)
    chikou = C.shift(-displace)

    out['Tenkan']   = tenkan
    out['Kijun']    = kijun
    out['Senkou_A'] = sen_a
    out['Senkou_B'] = sen_b
    out['Chikou']   = chikou

    # ── Kumo boundaries ────────────────────────────────────────────────
    kumo_top = pd.concat([sen_a, sen_b], axis=1).max(axis=1)
    kumo_bot = pd.concat([sen_a, sen_b], axis=1).min(axis=1)
    out['Kumo_top'] = kumo_top
    out['Kumo_bot'] = kumo_bot

    # ── 3 đặc trưng dẫn xuất (chỉ dùng Close, anti-leak) ───────────────

    # [1] TK Momentum
    out['TK_momentum'] = (tenkan - kijun) / C.replace(0, np.nan) * 100.0

    # [2] Cloud Distance tới biên gần nhất
    _above = (C - kumo_top) / C.replace(0, np.nan) * 100.0
    _below = (C - kumo_bot) / C.replace(0, np.nan) * 100.0
    out['Cloud_dist'] = np.where(
        C > kumo_top, _above,
        np.where(C < kumo_bot, _below, 0.0))
    _mask_na = C.isna() | kumo_top.isna() | kumo_bot.isna()
    out.loc[_mask_na, 'Cloud_dist'] = np.nan

    # [3] Chikou Momentum (anti-leak)
    c_lag26 = C.shift(displace)
    c_lag52 = C.shift(displace * 2)
    out['Chikou_momentum'] = (c_lag26 - c_lag52) / c_lag52.replace(0, np.nan) * 100.0

    return out


# ═════════════════════════════════════════════════════════════════════════
#  HỆ 4 TẦNG TÍN HIỆU ICHIMOKU
#  (Gurrib 2016, Deng & Zhao 2021, Shrestha 2022)
# ═════════════════════════════════════════════════════════════════════════

# ── Tầng 1 ─────────────────────────────────────────────────────────────
def classify_primary_trend(close: float,
                            kumo_top: float,
                            kumo_bot: float) -> tuple[str, str]:
    """
    Tầng 1 — Xu hướng chính: vị trí Close so với mây Kumo.

    Close > Kumo_top  →  Bull regime
    Close < Kumo_bot  →  Bear regime
    Kumo_bot ≤ Close ≤ Kumo_top  →  Consolidation
    """
    if np.isnan(kumo_top) or np.isnan(kumo_bot) or np.isnan(close):
        return 'na', 'Không đủ dữ liệu'
    if close > kumo_top:
        return 'bull', 'Giá trên mây — Xu hướng tăng'
    if close < kumo_bot:
        return 'bear', 'Giá dưới mây — Xu hướng giảm'
    return 'neut', 'Giá trong mây — Tích lũy / Chuyển tiếp'


# ── Tầng 2 ─────────────────────────────────────────────────────────────
def detect_tk_cross(tenkan: pd.Series, kijun: pd.Series,
                    lookback: int = 5) -> tuple[str, str, int | None]:
    """
    Phát hiện Tenkan × Kijun cross trong `lookback` phiên gần nhất.
    Bullish: T[t-1] ≤ K[t-1] và T[t] > K[t].
    Bearish: T[t-1] ≥ K[t-1] và T[t] < K[t].
    """
    if len(tenkan) < lookback + 1:
        return 'na', 'Không đủ dữ liệu', None
    t = tenkan.values
    k = kijun.values
    n = len(t)
    for off in range(lookback):
        i = n - 1 - off
        if i <= 0 or np.isnan(t[i]) or np.isnan(k[i]) \
                  or np.isnan(t[i-1]) or np.isnan(k[i-1]):
            continue
        if t[i-1] <= k[i-1] and t[i] > k[i]:
            return 'bull_cross', f'Tenkan cắt lên Kijun ({off} phiên trước)', off
        if t[i-1] >= k[i-1] and t[i] < k[i]:
            return 'bear_cross', f'Tenkan cắt xuống Kijun ({off} phiên trước)', off
    return 'no_cross', 'Không có giao cắt gần đây', None


def classify_trading_signal(tk_cross_code: str,
                             primary_code: str) -> tuple[str, str]:
    """
    Tầng 2 — Tín hiệu giao dịch: TK cross + xác nhận xu hướng.

    Quy tắc Gurrib (2016):
      Cross CÙNG CHIỀU xu hướng mây → Strong signal
      Cross TRONG mây              → Weak signal
      Cross NGƯỢC CHIỀU xu hướng   → Counter-trend (rủi ro)
    """
    if tk_cross_code == 'bull_cross':
        if primary_code == 'bull': return 'strong_buy',  'Mua mạnh (cross + trên mây)'
        if primary_code == 'neut': return 'weak_buy',    'Mua yếu (cross trong mây)'
        if primary_code == 'bear': return 'counter_buy', 'Mua ngược xu hướng (rủi ro)'
    if tk_cross_code == 'bear_cross':
        if primary_code == 'bear': return 'strong_sell',  'Bán mạnh (cross + dưới mây)'
        if primary_code == 'neut': return 'weak_sell',    'Bán yếu (cross trong mây)'
        if primary_code == 'bull': return 'counter_sell', 'Bán ngược xu hướng (rủi ro)'
    return 'hold', 'Không có tín hiệu giao dịch'


# ── Tầng 3 ─────────────────────────────────────────────────────────────
def classify_chikou_confirmation(close_now: float,
                                  close_past_26: float) -> tuple[str, str]:
    """
    Tầng 3 — Chikou Confirmation (Hosoda 1969).

    Chikou span[t] = Close[t], được vẽ tại vị trí (t−26) trên trục thời gian.
    Tại vị trí hiển thị (t−26), so sánh Chikou với giá thực tại phiên đó:
      Chikou trên đường giá quá khứ → xác nhận xu hướng tăng
      Chikou dưới đường giá quá khứ → xác nhận xu hướng giảm

    Số học: (Close[t] − Close[t−26]) / Close[t−26] × 100

    Anti-leak: tại t, cả 2 giá trị đều đã biết.

    Tham số
    -------
    close_now      : Close[t]      — Chikou span (trước khi dịch)
    close_past_26  : Close[t−26]   — giá thực tại vị trí hiển thị Chikou
    """
    if np.isnan(close_now) or np.isnan(close_past_26) or close_past_26 == 0:
        return 'na', 'Không đủ dữ liệu'
    diff_pct = (close_now - close_past_26) / close_past_26 * 100.0
    if diff_pct >  0.5:
        return 'bull_conf', (f'Chikou trên đường giá quá khứ (+{diff_pct:.2f}%) '
                              f'— xác nhận xu hướng tăng')
    if diff_pct < -0.5:
        return 'bear_conf', (f'Chikou dưới đường giá quá khứ ({diff_pct:.2f}%) '
                              f'— xác nhận xu hướng giảm')
    return 'neut_conf', (f'Chikou gần đường giá quá khứ ({diff_pct:+.2f}%) '
                          f'— tín hiệu không rõ ràng')


# ── Tầng 4 ─────────────────────────────────────────────────────────────
def classify_future_kumo(senkou_a_future: float,
                          senkou_b_future: float) -> tuple[str, str]:
    """
    Tầng 4 — Mây tương lai tại t+26.

    Tại phiên t, mây sẽ hiển thị ở t+26 chính là giá trị RAW (chưa shift):
      Senkou_A_future = (Tenkan[t] + Kijun[t]) / 2
      Senkou_B_future = midpoint_52[t]

    Senkou_A > Senkou_B → Mây xanh (bullish momentum)
    Senkou_A < Senkou_B → Mây đỏ   (bearish momentum)

    Anti-leak: dùng dữ liệu tại t.
    """
    if np.isnan(senkou_a_future) or np.isnan(senkou_b_future):
        return 'na', 'Không đủ dữ liệu'
    mid_val = (senkou_a_future + senkou_b_future) / 2.0
    if mid_val == 0:
        return 'na', 'Không đủ dữ liệu'
    diff_pct = (senkou_a_future - senkou_b_future) / mid_val * 100.0
    if diff_pct >  0.3:
        return 'bull_kumo', f'Mây tương lai xanh (+{diff_pct:.2f}%) — momentum tăng'
    if diff_pct < -0.3:
        return 'bear_kumo', f'Mây tương lai đỏ ({diff_pct:.2f}%) — momentum giảm'
    return 'flat_kumo', f'Mây tương lai phẳng ({diff_pct:+.2f}%) — chuyển tiếp'


# ── Tổng hợp ───────────────────────────────────────────────────────────
def aggregate_signals(primary: str, trading: str,
                       chikou: str, future_kumo: str) -> tuple[str, str, int]:
    """
    Consensus score ∈ [−5, +5].

    Trọng số:
      Primary  : ±1
      Trading  : ±2 (strong), ±1 (weak), 0 (counter)
      Chikou   : ±1
      Future   : ±1

    Nhãn:
      ≥ +3: strong_bull
      ≥ +1: mild_bull
      ≤ −3: strong_bear
      ≤ −1: mild_bear
      else: neutral
    """
    score = 0
    if primary == 'bull': score += 1
    if primary == 'bear': score -= 1
    if trading == 'strong_buy':    score += 2
    if trading == 'weak_buy':      score += 1
    if trading == 'strong_sell':   score -= 2
    if trading == 'weak_sell':     score -= 1
    if chikou == 'bull_conf':      score += 1
    if chikou == 'bear_conf':      score -= 1
    if future_kumo == 'bull_kumo': score += 1
    if future_kumo == 'bear_kumo': score -= 1

    if   score >=  3: return 'strong_bull', 'Tăng mạnh (consensus)',  score
    elif score >=  1: return 'mild_bull',   'Tăng nhẹ',               score
    elif score <= -3: return 'strong_bear', 'Giảm mạnh (consensus)',  score
    elif score <= -1: return 'mild_bear',   'Giảm nhẹ',               score
    else:              return 'neutral',     'Trung tính / phân kỳ',   score


# ═════════════════════════════════════════════════════════════════════════
#  UI HELPERS — mapping code → i18n key (UI gọi t() với kwargs phù hợp).
#  Data layer KHÔNG import t(); đây chỉ là string mapping thuần.
# ═════════════════════════════════════════════════════════════════════════

def primary_i18n_key(code: str) -> str:
    return f'ichi.primary.{code}'

def tk_i18n_key(code: str) -> str:
    return f'ichi.tk.{code}'

def trading_i18n_key(code: str) -> str:
    return f'ichi.trading.{code}'

def chikou_i18n_key(code: str) -> str:
    return f'ichi.chikou.{code}'

def future_i18n_key(code: str) -> str:
    return f'ichi.future.{code}'

def overall_i18n_key(code: str) -> str:
    return f'ichi.overall.{code}'
