import streamlit as st
import numpy as np
from sklearn.tree import DecisionTreeRegressor
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from data.fetcher import fetch_data

FEATS_RAW = ['Return', 'Volume_ratio', 'Range_ratio',
             'MA5_ratio', 'MA20_ratio', 'RSI14']


@st.cache_data(show_spinner=False)
def run_cart(ticker: str, train_ratio: float, p: int = 1,
             date_from=None, date_to=None) -> dict:
    """
    CART(p): Decision Tree với Distributed Lag — dự báo phiên kế tiếp.

    Features: 6 technical indicators × p lag = 6p features
        X_t = [Return_t, Volume_ratio_t, Range_ratio_t,
               MA5_ratio_t, MA20_ratio_t, RSI14_t,
               Return_{t-1}, ..., RSI14_{t-p+1}]

    Target: next-session return
        R_target = 100 * (Close_{t+1} / Close_t - 1)

    Phục hồi giá: Ŷ_{t+1} = Y_t · (1 + R̂/100)

    Default p=1 → tương đương CART cổ điển.
    """
    if p < 1:
        raise ValueError(f'p must be >= 1, got p={p}')

    df = fetch_data(ticker, date_from, date_to)
    N  = len(df)
    nt = int(N * train_ratio)

    close = df['Close'].values.astype(float)
    raw   = df[FEATS_RAW].values.astype(float)

    num_samples = N - p
    if num_samples < 20:
        raise ValueError(f'Not enough data: N={N}, p={p}')

    cols = []
    for k in range(p):
        cols.append(raw[p - 1 - k : p - 1 - k + num_samples, :])
    X_full = np.hstack(cols)

    close_at_t    = close[p - 1 : p - 1 + num_samples]
    close_at_t_1  = close[p : p + num_samples]
    Y_return      = 100.0 * (close_at_t_1 / close_at_t - 1.0)

    mask = ~(np.isnan(X_full).any(axis=1) | np.isnan(Y_return))
    X_full       = X_full[mask]
    Y_return     = Y_return[mask]
    close_at_t   = close_at_t[mask]
    close_at_t_1 = close_at_t_1[mask]

    if len(X_full) < 20:
        raise ValueError(f'Not enough valid samples after NaN removal: {len(X_full)}')

    nt_adj = max(10, min(nt - p, len(X_full) - 10))

    Xtr            = X_full[:nt_adj]
    Ytr_ret        = Y_return[:nt_adj]
    Xte            = X_full[nt_adj:]
    Yte_close      = close_at_t_1[nt_adj:]
    close_at_t_tr  = close_at_t[:nt_adj]
    close_at_t_te  = close_at_t[nt_adj:]
    Ytr_close      = close_at_t_1[:nt_adj]

    gs = GridSearchCV(
        DecisionTreeRegressor(random_state=42),
        {'max_depth': [3, 5, 7], 'min_samples_leaf': [10, 30]},
        cv=TimeSeriesSplit(n_splits=3),
        scoring='neg_mean_absolute_error',
        n_jobs=2,
    )
    gs.fit(Xtr, Ytr_ret)
    model = DecisionTreeRegressor(random_state=42, **gs.best_params_).fit(Xtr, Ytr_ret)

    ret_tr = model.predict(Xtr)
    ret_te = model.predict(Xte)
    ptr = close_at_t_tr * (1 + ret_tr / 100.0)
    pte = close_at_t_te * (1 + ret_te / 100.0)

    x_cols = []
    for k in range(p):
        x_cols.append(raw[N - 1 - k, :])
    x_next   = np.concatenate(x_cols).reshape(1, -1)
    ret_next  = float(model.predict(x_next)[0])
    next_pred = float(close[-1] * (1 + ret_next / 100.0))

    imp_raw = model.feature_importances_
    imp_grouped = {}
    for i, fname in enumerate(FEATS_RAW):
        idxs = [i + 6 * k for k in range(p)]
        imp_grouped[fname] = float(imp_raw[idxs].sum())

    dates_full = df['Ngay'].values
    base_idx   = p
    idxs_valid = np.arange(num_samples)[mask]
    dates_all  = dates_full[base_idx + idxs_valid]
    dates_tr   = dates_all[:nt_adj]
    dates_te   = dates_all[nt_adj:]

    return dict(
        best         = gs.best_params_,
        importances  = imp_grouped,
        model        = model,
        p            = p,
        nt           = nt_adj,
        ytr          = Ytr_close,
        ptr          = ptr,
        yte          = Yte_close,
        pte          = pte,
        dates_tr     = dates_tr,
        dates_te     = dates_te,
        next_pred    = next_pred,
        ret_pred     = ret_next,
        close_full   = close,
        dates_full   = dates_full,
    )
