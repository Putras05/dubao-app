import streamlit as st
import pandas as pd
import numpy as np
from core.config import DATA_START, DATA_END, DATA_SOURCE, CACHE_TTL


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _fetch_raw(ticker: str) -> pd.DataFrame:
    """Fetch raw từ vnstock + indicator technical. Cache theo ticker (không
    phụ thuộc date_from/date_to) → đổi date range KHÔNG gọi lại network.
    """
    from vnstock import Vnstock
    s  = Vnstock().stock(symbol=ticker, source=DATA_SOURCE)
    df = s.quote.history(start=DATA_START, end=DATA_END, interval='1D')
    df = df.rename(columns={
        'time': 'Ngay', 'close': 'Close', 'open': 'Open',
        'high': 'High', 'low': 'Low', 'volume': 'Volume',
    })
    df['Ngay'] = pd.to_datetime(df['Ngay']).dt.date
    df = df.sort_values('Ngay').reset_index(drop=True)

    # Technical indicators
    df['MA5']    = df['Close'].rolling(5).mean()
    df['MA20']   = df['Close'].rolling(20).mean()
    df['MA50']   = df['Close'].rolling(50).mean()
    df['MA5_Vol']= df['Volume'].rolling(5).mean()

    delta = df['Close'].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    df['RSI14'] = 100 - 100 / (1 + gain / loss.replace(0, np.nan))

    df['MA5_ratio']    = (df['Close'] / df['MA5']  - 1) * 100
    df['MA20_ratio']   = (df['Close'] / df['MA20'] - 1) * 100
    df['Volume_ratio'] = df['Volume'] / df['MA5_Vol']
    df['Range']        = df['High'] - df['Low']
    df['Range_ratio']  = (df['High'] - df['Low']) / df['Close'] * 100
    df['Return']       = df['Close'].pct_change() * 100

    # Lag-1 features (for MLR and CART)
    df['Close_L1']        = df['Close'].shift(1)
    df['Volume_L1']       = df['Volume'].shift(1)
    df['Range_L1']        = df['Range'].shift(1)
    df['Return_L1']       = df['Return'].shift(1)
    df['Volume_ratio_L1'] = df['Volume_ratio'].shift(1)
    df['Range_ratio_L1']  = df['Range_ratio'].shift(1)
    df['MA5_ratio_L1']    = df['MA5_ratio'].shift(1)
    df['MA20_ratio_L1']   = df['MA20_ratio'].shift(1)
    df['RSI14_L1']        = df['RSI14'].shift(1)

    df = df.dropna().reset_index(drop=True)

    # Guard: nếu phiên cuối là HÔM NAY và HOSE chưa đóng cửa (trước 15:00 VN),
    # loại bỏ hàng cuối vì Close là giá intraday chưa chốt chính thức.
    import datetime as _dt
    try:
        from zoneinfo import ZoneInfo
        _now_vn = _dt.datetime.now(ZoneInfo('Asia/Ho_Chi_Minh'))
    except Exception:
        _now_vn = _dt.datetime.utcnow() + _dt.timedelta(hours=7)

    if len(df) > 0:
        _last_row_date = df['Ngay'].iloc[-1]
        _today_vn      = _now_vn.date()
        # HOSE đóng 14:45; buffer tới 15:00 để chắc chắn API đã cập nhật giá chốt
        _close_cutoff  = _dt.time(15, 0)
        if _last_row_date == _today_vn and _now_vn.time() < _close_cutoff:
            df = df.iloc[:-1].reset_index(drop=True)

    return df


def fetch_data(ticker: str, date_from=None, date_to=None) -> pd.DataFrame:
    """Public fetcher — lấy raw cache + filter theo date range (in-memory)."""
    df = _fetch_raw(ticker)
    if date_from:
        df = df[df['Ngay'] >= date_from]
    if date_to:
        df = df[df['Ngay'] <= date_to]
    return df.reset_index(drop=True)
