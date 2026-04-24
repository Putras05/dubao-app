import streamlit as st
import numpy as np
from sklearn.linear_model import LinearRegression
from data.fetcher import fetch_data


@st.cache_data(show_spinner=False)
def run_mlr(ticker: str, train_ratio: float, p: int = 1,
            date_from=None, date_to=None) -> dict:
    """
    MLR(p): Multiple Linear Regression với Distributed Lag — dự báo phiên kế tiếp.

        Ŷ_{t+1} = β₀
                + Σ_{k=0..p-1} β_{1,k}·Y_{t-k}
                + Σ_{k=0..p-1} β_{2,k}·V_{t-k}
                + Σ_{k=0..p-1} β_{3,k}·HL_{t-k}

    Default p=1 → tương đương MLR cổ điển.
    Tổng 3p features + 1 intercept.
    """
    if p < 1:
        raise ValueError(f'p must be >= 1, got p={p}')

    df = fetch_data(ticker, date_from, date_to)
    N  = len(df)
    nt = int(N * train_ratio)

    close  = df['Close'].values.astype(float)
    volume = df['Volume'].values.astype(float)
    range_ = df['Range'].values.astype(float)

    num_samples = N - p
    if num_samples < 10:
        raise ValueError(f'Not enough data: N={N}, p={p}')

    cols = []
    for k in range(p):
        cols.append(close [p - 1 - k : p - 1 - k + num_samples])
    for k in range(p):
        cols.append(volume[p - 1 - k : p - 1 - k + num_samples])
    for k in range(p):
        cols.append(range_[p - 1 - k : p - 1 - k + num_samples])
    X_full = np.column_stack(cols)
    Y_full = close[p : p + num_samples]

    nt_adj = max(10, min(nt - p, num_samples - 10))
    Xtr, Ytr = X_full[:nt_adj], Y_full[:nt_adj]
    Xte, Yte = X_full[nt_adj:], Y_full[nt_adj:]

    reg = LinearRegression().fit(Xtr, Ytr)
    ptr = reg.predict(Xtr)
    pte = reg.predict(Xte)

    x_next_y  = close [N - 1 : N - 1 - p : -1]
    x_next_v  = volume[N - 1 : N - 1 - p : -1]
    x_next_hl = range_[N - 1 : N - 1 - p : -1]
    x_next = np.concatenate([x_next_y, x_next_v, x_next_hl]).reshape(1, -1)
    next_pred = float(reg.predict(x_next)[0])

    dates_full = df['Ngay'].values
    dates_all  = dates_full[p : p + num_samples]
    dates_tr   = dates_all[:nt_adj]
    dates_te   = dates_all[nt_adj:]

    return dict(
        coef       = reg.coef_,
        intercept  = reg.intercept_,
        p          = p,
        nt         = nt_adj,
        ytr        = Ytr,
        ptr        = ptr,
        yte        = Yte,
        pte        = pte,
        dates_tr   = dates_tr,
        dates_te   = dates_te,
        next_pred  = next_pred,
        close_full = close,
        dates_full = dates_full,
    )
