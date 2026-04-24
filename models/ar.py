import streamlit as st
import numpy as np
from data.fetcher import fetch_data


@st.cache_data(show_spinner=False)
def run_ar(ticker: str, train_ratio: float, p: int = 1,
           date_from=None, date_to=None) -> dict:
    """
    AR(p) — Box-Jenkins chuẩn.

        Y_t = c + φ₁·Y_{t-1} + φ₂·Y_{t-2} + ... + φ_p·Y_{t-p} + ε_t

    Dự báo 1 phiên kế tiếp:
        Ŷ_{t+1} = c + φ₁·Y_t + φ₂·Y_{t-1} + ... + φ_p·Y_{t-p+1}

    Tham chiếu: Box, Jenkins, Reinsel & Ljung (2015). Time Series Analysis:
    Forecasting and Control, 5th ed., Wiley.
    """
    if p < 1:
        raise ValueError(f'AR order p must be >= 1, got p={p}')

    df = fetch_data(ticker, date_from, date_to)
    N  = len(df)
    nt = int(N * train_ratio)
    y  = df['Close'].values.astype(float)

    num_samples = N - p
    if num_samples < 10:
        raise ValueError(f'Not enough data: N={N}, p={p} → only {num_samples} samples')

    X_full = np.column_stack([
        y[p - 1 - k : p - 1 - k + num_samples]
        for k in range(p)
    ])
    Y_full = y[p : p + num_samples]

    nt_adj = max(10, min(nt - p, num_samples - 10))
    Xtr, Ytr = X_full[:nt_adj], Y_full[:nt_adj]
    Xte, Yte = X_full[nt_adj:], Y_full[nt_adj:]

    X_design_tr = np.column_stack([Xtr, np.ones(len(Xtr))])
    beta, *_   = np.linalg.lstsq(X_design_tr, Ytr, rcond=None)
    phi = beta[:p]
    c   = float(beta[p])

    ptr = X_design_tr @ beta
    X_design_te = np.column_stack([Xte, np.ones(len(Xte))])
    pte = X_design_te @ beta

    x_next = y[N - 1 : N - 1 - p : -1]
    next_pred = float(phi @ x_next + c)

    dates_full = df['Ngay'].values
    dates_all  = dates_full[p : p + num_samples]
    dates_tr   = dates_all[:nt_adj]
    dates_te   = dates_all[nt_adj:]

    return dict(
        coefs     = phi,
        c         = c,
        p         = p,
        rho       = float(phi[0]),
        intercept = c,
        nt        = nt_adj,
        ytr       = Ytr,
        ptr       = ptr,
        yte       = Yte,
        pte       = pte,
        dates_tr  = dates_tr,
        dates_te  = dates_te,
        next_pred = next_pred,
        close_full = y,
        dates_full = dates_full,
    )
