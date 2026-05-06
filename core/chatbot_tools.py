# -*- coding: utf-8 -*-
"""Chatbot tool functions — exposed to Gemini via native function calling.

Each public function here is registered with the google-genai SDK as a tool.
The SDK introspects the function's type hints + docstring and builds the
JSON schema automatically. Functions MUST:

  - have JSON-serializable return values (dict / list / scalars)
  - have descriptive docstrings (the LLM reads them to decide when to call)
  - take only primitive type-annotated parameters

The active app state (df, model results, sidebar config) is set once at the
top of `app_pages.chatbot.render()` via `set_app_state(...)`. Tools then read
that state via `_state()` — no need to thread arguments through the SDK.
"""
from __future__ import annotations

import threading
import streamlit as st


# ═══════════════════════════════════════════════════════════════════
# STATE — set by the page each render; tools read it back.
# Stored as a module global (one Streamlit script run = one thread).
# ═══════════════════════════════════════════════════════════════════
_LOCK = threading.Lock()
_STATE: dict = {}


def set_app_state(*, ticker: str, train_ratio: float, date_from, date_to,
                  df, r1, r2, r3, m1, m2, m3, ar_order: int, lang: str = 'VI') -> None:
    """Called once per page render. Stores app state for tool access."""
    with _LOCK:
        _STATE.clear()
        _STATE.update(dict(
            ticker=ticker, train_ratio=float(train_ratio),
            date_from=date_from, date_to=date_to,
            df=df, r1=r1, r2=r2, r3=r3, m1=m1, m2=m2, m3=m3,
            ar_order=int(ar_order), lang=lang,
        ))


def _state() -> dict:
    return _STATE


def has_state() -> bool:
    return bool(_STATE)


# ═══════════════════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════════════════
def _safe_float(x, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _safe_str(x) -> str:
    try:
        return str(x)
    except Exception:
        return ''


# ═══════════════════════════════════════════════════════════════════
# TOOLS — public, exposed to Gemini
# ═══════════════════════════════════════════════════════════════════
def get_current_ticker_data() -> dict:
    """Get the ticker, last close price, session change %, latest trading date,
    daily/annualized volatility, and the active sidebar configuration
    (train ratio, AR order, date range). Use this whenever the user asks
    about the currently selected stock or its recent price.

    Returns a dict with keys: ticker, last_close_vnd, return_pct, date_last,
    daily_vol_pct, annualized_vol_pct, train_ratio, ar_order, date_from,
    date_to, n_sessions.
    """
    s = _state()
    if not s:
        return {'error': 'app_state_not_initialized'}
    df = s.get('df')
    out: dict = {
        'ticker': s.get('ticker', ''),
        'train_ratio': s.get('train_ratio', 0.0),
        'ar_order': s.get('ar_order', 1),
        'date_from': _safe_str(s.get('date_from', '')),
        'date_to': _safe_str(s.get('date_to', '')),
    }
    try:
        if df is not None and len(df):
            out['n_sessions'] = int(len(df))
            out['last_close_vnd'] = _safe_float(df['Close'].iloc[-1]) * 1000
            out['date_last'] = _safe_str(df['Ngay'].iloc[-1])[:10]
            if 'Return' in df.columns:
                out['return_pct'] = _safe_float(df['Return'].iloc[-1])
            ret = df['Return'].tail(30).dropna() if 'Return' in df.columns else None
            if ret is not None and len(ret) > 0:
                import numpy as np
                out['daily_vol_pct'] = _safe_float(ret.std())
                out['annualized_vol_pct'] = _safe_float(ret.std() * np.sqrt(252))
    except Exception as e:
        out['warning'] = f'partial_data: {str(e)[:80]}'
    return out


def get_forecast_results() -> dict:
    """Get the next-session forecast (in VND) and test-set evaluation metrics
    (MAPE, RMSE, MAE, R²adj) for the three trained models AR(p), MLR(p),
    CART(p). Use when the user asks for a forecast, "dự báo", "phiên tới",
    or wants to compare model accuracy.

    Returns a dict: forecasts={ar,mlr,cart} (VND), mape={ar,mlr,cart} (%),
    rmse={ar,mlr,cart} (k VND), mae={ar,mlr,cart} (k VND),
    r2adj={ar,mlr,cart}, ar_order, best_by_mape (string).
    """
    s = _state()
    if not s:
        return {'error': 'app_state_not_initialized'}
    r1, r2, r3 = s.get('r1') or {}, s.get('r2') or {}, s.get('r3') or {}
    m1, m2, m3 = s.get('m1') or {}, s.get('m2') or {}, s.get('m3') or {}
    out = {
        'forecasts_vnd': {
            'ar':   _safe_float(r1.get('next_pred', 0)) * 1000,
            'mlr':  _safe_float(r2.get('next_pred', 0)) * 1000,
            'cart': _safe_float(r3.get('next_pred', 0)) * 1000,
        },
        'mape': {
            'ar':   _safe_float(m1.get('MAPE', 0)),
            'mlr':  _safe_float(m2.get('MAPE', 0)),
            'cart': _safe_float(m3.get('MAPE', 0)),
        },
        'rmse': {
            'ar':   _safe_float(m1.get('RMSE', 0)),
            'mlr':  _safe_float(m2.get('RMSE', 0)),
            'cart': _safe_float(m3.get('RMSE', 0)),
        },
        'mae': {
            'ar':   _safe_float(m1.get('MAE', 0)),
            'mlr':  _safe_float(m2.get('MAE', 0)),
            'cart': _safe_float(m3.get('MAE', 0)),
        },
        'r2adj': {
            'ar':   _safe_float(m1.get('R2adj', 0)),
            'mlr':  _safe_float(m2.get('R2adj', 0)),
            'cart': _safe_float(m3.get('R2adj', 0)),
        },
        'ar_order': s.get('ar_order', 1),
    }
    try:
        # Best model = lowest MAPE
        mapes = out['mape']
        out['best_by_mape'] = min(mapes, key=lambda k: mapes[k])
    except Exception:
        out['best_by_mape'] = 'ar'
    return out


def get_technical_signals() -> dict:
    """Get the Ichimoku 4-tier consensus signal (label, score in [-5..+5],
    primary trend, TK cross, Chikou confirmation, future Kumo) plus latest
    RSI14 and 5/20/50-session moving averages. Use when the user asks
    about technical signals, Ichimoku, "nên mua/bán", trend direction.

    Returns a dict: ichimoku={label,score,primary,trading,chikou,future_kumo},
    rsi14, ma5, ma20, ma50, latest_close_vnd.
    """
    s = _state()
    if not s:
        return {'error': 'app_state_not_initialized'}
    df = s.get('df')
    out: dict = {}

    # Ichimoku — prefer cached summary from session_state (matches Signals page)
    ichi = None
    try:
        ichi = st.session_state.get('ichimoku_summary')
    except Exception:
        pass
    if not ichi and df is not None:
        try:
            from data.ichimoku import (
                add_ichimoku, classify_primary_trend, detect_tk_cross,
                classify_trading_signal, classify_chikou_confirmation,
                classify_future_kumo, aggregate_signals, _donchian_mid, SENKOU_N,
            )
            import numpy as _np
            _df_i = add_ichimoku(df)
            _last = _df_i.iloc[-1]
            _close_now = float(_last['Close'])
            _kt = float(_last['Kumo_top']) if not _np.isnan(_last['Kumo_top']) else float('nan')
            _kb = float(_last['Kumo_bot']) if not _np.isnan(_last['Kumo_bot']) else float('nan')
            _prim, _ = classify_primary_trend(_close_now, _kt, _kb)
            _tk, _, _ = detect_tk_cross(_df_i['Tenkan'], _df_i['Kijun'])
            _trd, _ = classify_trading_signal(_tk, _prim)
            _c26 = float(_df_i['Close'].iloc[-27]) if len(_df_i) >= 27 else float('nan')
            _chk, _ = classify_chikou_confirmation(_close_now, _c26)
            _ten = float(_last['Tenkan']); _kij = float(_last['Kijun'])
            _fa = (_ten + _kij) / 2.0
            _fb = float(_donchian_mid(df['High'], df['Low'], SENKOU_N).iloc[-1])
            _fut, _ = classify_future_kumo(_fa, _fb)
            _ov_code, _ov_label, _score = aggregate_signals(_prim, _trd, _chk, _fut)
            ichi = {
                'label': _ov_label, 'code': _ov_code, 'score': int(_score),
                'primary': _prim, 'trading': _trd,
                'chikou': _chk, 'future_kumo': _fut,
            }
        except Exception as e:
            ichi = {'error': str(e)[:120]}
    if ichi:
        out['ichimoku'] = ichi

    try:
        if df is not None and len(df):
            out['latest_close_vnd'] = _safe_float(df['Close'].iloc[-1]) * 1000
            for k_src, k_out in (('RSI14', 'rsi14'), ('MA5', 'ma5_vnd'),
                                  ('MA20', 'ma20_vnd'), ('MA50', 'ma50_vnd')):
                if k_src in df.columns:
                    val = df[k_src].iloc[-1]
                    if k_src.startswith('MA'):
                        out[k_out] = _safe_float(val) * 1000
                    else:
                        out[k_out] = _safe_float(val)
    except Exception:
        pass
    return out


def get_price_history(days: int = 30) -> dict:
    """Get OHLCV history for the latest N trading sessions (capped at 60).
    Use when the user asks for recent prices, "30 phiên gần nhất", "lịch sử
    giá", or wants to see the price trend.

    Args:
        days: number of recent sessions to return (1..60)

    Returns:
        dict with keys: ticker, n, rows (list of {date, open, high, low,
        close_vnd, volume}).
    """
    s = _state()
    if not s:
        return {'error': 'app_state_not_initialized'}
    df = s.get('df')
    if df is None or not len(df):
        return {'error': 'no_data'}
    n = max(1, min(60, int(days or 30)))
    tail = df.tail(n)
    rows = []
    for _, r in tail.iterrows():
        try:
            rows.append({
                'date': _safe_str(r.get('Ngay', ''))[:10],
                'open_vnd':  _safe_float(r.get('Open', 0)) * 1000,
                'high_vnd':  _safe_float(r.get('High', 0)) * 1000,
                'low_vnd':   _safe_float(r.get('Low', 0)) * 1000,
                'close_vnd': _safe_float(r.get('Close', 0)) * 1000,
                'volume':    int(_safe_float(r.get('Volume', 0))),
            })
        except Exception:
            continue
    return {'ticker': s.get('ticker', ''), 'n': len(rows), 'rows': rows}


def get_price_on_date(date: str) -> dict:
    """Get the OHLCV price of the active ticker on a specific calendar date.
    If the date is not a trading day, returns the closest trading day within
    ±5 days (e.g. weekend → previous Friday). Use when the user asks "giá
    ngày DD/MM/YYYY", "phiên ngày X", "đóng cửa hôm 20/3/2024", etc.

    Args:
        date: any human date string. Accepted: "20/3/2024", "20-03-2024",
              "2024-03-20", "20.3.2024". Day-first is assumed for ambiguous
              cases like "3/4" (=3 April, not 4 March).

    Returns:
        dict with: ticker, requested_date, matched_date, offset_days,
        open_vnd, high_vnd, low_vnd, close_vnd, volume, return_pct.
        On failure: {'error': '...'}.
    """
    s = _state()
    if not s:
        return {'error': 'app_state_not_initialized'}
    df = s.get('df')
    if df is None or not len(df):
        return {'error': 'no_data'}
    try:
        import pandas as pd
        target = pd.to_datetime(date, dayfirst=True, errors='coerce')
        if pd.isna(target):
            return {'error': f'unparseable_date: {date}'}
        dts = pd.to_datetime(df['Ngay'], errors='coerce')
        diffs = (dts - target).dt.days
        # Closest within ±5 days, prefer same/earlier
        mask = diffs.abs() <= 5
        if not mask.any():
            return {'error': f'no_session_within_5d_of: {date}'}
        idx = diffs[mask].abs().idxmin()
        row = df.loc[idx]
        offset = int(diffs.loc[idx])
        return {
            'ticker': s.get('ticker', ''),
            'requested_date': _safe_str(target.date()),
            'matched_date': _safe_str(row.get('Ngay', ''))[:10],
            'offset_days': offset,
            'open_vnd':  _safe_float(row.get('Open', 0)) * 1000,
            'high_vnd':  _safe_float(row.get('High', 0)) * 1000,
            'low_vnd':   _safe_float(row.get('Low', 0)) * 1000,
            'close_vnd': _safe_float(row.get('Close', 0)) * 1000,
            'volume':    int(_safe_float(row.get('Volume', 0))),
            'return_pct': _safe_float(row.get('Return', 0)),
        }
    except Exception as e:
        return {'error': f'date_lookup_failed: {str(e)[:120]}'}


def get_price_range(start_date: str, end_date: str, summary: bool = True) -> dict:
    """Get price statistics or full OHLCV rows for a date range. Use when
    the user asks "giá tuần trước", "tháng 3/2024", "Q1 2024", "từ ngày X
    đến ngày Y", "giá cao nhất trong tháng qua".

    Args:
        start_date: range start (any human format, day-first)
        end_date:   range end (any human format, day-first)
        summary: True (default) → return aggregate stats only;
                 False → return all rows (capped at 60).

    Returns:
        If summary=True: dict with n_sessions, first_date, last_date,
        open_first_vnd, close_last_vnd, high_max_vnd, low_min_vnd,
        avg_close_vnd, total_volume, return_period_pct, max_close_date,
        min_close_date.
        If summary=False: dict with n + rows[] (same shape as get_price_history).
    """
    s = _state()
    if not s:
        return {'error': 'app_state_not_initialized'}
    df = s.get('df')
    if df is None or not len(df):
        return {'error': 'no_data'}
    try:
        import pandas as pd
        d0 = pd.to_datetime(start_date, dayfirst=True, errors='coerce')
        d1 = pd.to_datetime(end_date, dayfirst=True, errors='coerce')
        if pd.isna(d0) or pd.isna(d1):
            return {'error': f'unparseable_range: {start_date} -> {end_date}'}
        if d0 > d1:
            d0, d1 = d1, d0
        dts = pd.to_datetime(df['Ngay'], errors='coerce')
        mask = (dts >= d0) & (dts <= d1)
        sub = df.loc[mask]
        if not len(sub):
            return {'error': f'no_sessions_in_range: {start_date} -> {end_date}'}
        if not summary:
            sub2 = sub.tail(60)
            rows = []
            for _, r in sub2.iterrows():
                rows.append({
                    'date': _safe_str(r.get('Ngay', ''))[:10],
                    'open_vnd':  _safe_float(r.get('Open', 0)) * 1000,
                    'high_vnd':  _safe_float(r.get('High', 0)) * 1000,
                    'low_vnd':   _safe_float(r.get('Low', 0)) * 1000,
                    'close_vnd': _safe_float(r.get('Close', 0)) * 1000,
                    'volume':    int(_safe_float(r.get('Volume', 0))),
                })
            return {'ticker': s.get('ticker', ''), 'n': len(rows),
                    'truncated': len(sub) > 60, 'rows': rows}
        # Summary mode
        first = sub.iloc[0]; last = sub.iloc[-1]
        idx_max = sub['Close'].idxmax(); idx_min = sub['Close'].idxmin()
        open_first = _safe_float(first.get('Open', 0)) * 1000
        close_last = _safe_float(last.get('Close', 0)) * 1000
        ret = ((close_last / open_first) - 1.0) * 100 if open_first else 0.0
        return {
            'ticker': s.get('ticker', ''),
            'n_sessions': int(len(sub)),
            'first_date': _safe_str(first.get('Ngay', ''))[:10],
            'last_date':  _safe_str(last.get('Ngay', ''))[:10],
            'open_first_vnd': open_first,
            'close_last_vnd': close_last,
            'high_max_vnd':  _safe_float(sub['High'].max()) * 1000,
            'low_min_vnd':   _safe_float(sub['Low'].min()) * 1000,
            'avg_close_vnd': _safe_float(sub['Close'].mean()) * 1000,
            'total_volume':  int(_safe_float(sub['Volume'].sum())),
            'return_period_pct': round(ret, 3),
            'max_close_date': _safe_str(df.loc[idx_max, 'Ngay'])[:10],
            'min_close_date': _safe_str(df.loc[idx_min, 'Ngay'])[:10],
        }
    except Exception as e:
        return {'error': f'range_lookup_failed: {str(e)[:120]}'}


def get_portfolio() -> dict:
    """Get the user's current investment portfolio (holdings, weights, P&L).
    The portfolio page in this app is read-only/demo at the moment, so this
    returns a placeholder with `available=False` until portfolio configuration
    is populated by the user.

    Returns:
        dict with keys: available (bool), holdings (list, possibly empty),
        message (str).
    """
    try:
        port = st.session_state.get('portfolio') or st.session_state.get('_portfolio')
    except Exception:
        port = None
    if port:
        return {'available': True, 'holdings': port,
                'message': 'Portfolio loaded from session.'}
    return {
        'available': False,
        'holdings': [],
        'message': ('Người dùng chưa cấu hình danh mục đầu tư trên trang '
                    '"Danh mục Đầu tư". Hãy nói rõ thông tin này thay vì bịa.'),
    }


def compute_metric(metric_name: str, model: str = 'ar') -> dict:
    """Compute or fetch a single evaluation metric for one model on the test
    set. Use when the user explicitly wants ONE number, e.g. "RMSE của AR
    là bao nhiêu".

    Args:
        metric_name: one of MAPE, RMSE, MAE, R2adj (case-insensitive)
        model: one of ar, mlr, cart

    Returns:
        dict with: metric, model, value, unit (% or 'k VND' or '').
    """
    s = _state()
    if not s:
        return {'error': 'app_state_not_initialized'}
    metric = (metric_name or '').strip().upper()
    mdl = (model or '').strip().lower()
    valid_metrics = {'MAPE', 'RMSE', 'MAE', 'R2ADJ', 'R²ADJ', 'R2'}
    if metric not in valid_metrics and metric.replace('²', '2') not in valid_metrics:
        return {'error': f'unknown_metric: {metric_name}'}
    if mdl not in ('ar', 'mlr', 'cart'):
        return {'error': f'unknown_model: {model}'}
    src = {'ar': s.get('m1') or {}, 'mlr': s.get('m2') or {},
           'cart': s.get('m3') or {}}[mdl]
    metric_norm = metric.replace('²', '2')
    keymap = {'MAPE': 'MAPE', 'RMSE': 'RMSE', 'MAE': 'MAE',
              'R2ADJ': 'R2adj', 'R2': 'R2adj'}
    key = keymap[metric_norm]
    val = _safe_float(src.get(key, 0))
    unit = '%' if metric_norm == 'MAPE' else (
        'k VND' if metric_norm in ('RMSE', 'MAE') else '')
    return {'metric': metric_norm, 'model': mdl, 'value': val, 'unit': unit}


def switch_ticker(ticker: str) -> dict:
    """Switch the in-memory data context to a different ticker for THIS
    answer only. Useful when the user explicitly asks about FPT but the
    sidebar is on HPG, etc. Re-trains AR/MLR/CART on the requested ticker.
    Supported: FPT, HPG, VNM.

    Args:
        ticker: one of FPT, HPG, VNM

    Returns:
        dict with: switched (bool), ticker, last_close_vnd.
    """
    s = _state()
    if not s:
        return {'error': 'app_state_not_initialized'}
    tk = (ticker or '').strip().upper()
    if tk not in ('FPT', 'HPG', 'VNM'):
        return {'error': f'unsupported_ticker: {ticker}'}
    if tk == (s.get('ticker') or '').upper():
        return {'switched': False, 'ticker': tk,
                'message': 'already_active', 'note': 'no change'}
    try:
        from data.fetcher import fetch_data
        from models.ar import run_ar
        from models.mlr import run_mlr
        from models.cart import run_cart
        from data.metrics import calc_metrics
        date_from = s.get('date_from')
        date_to = s.get('date_to')
        train_ratio = s.get('train_ratio', 0.8)
        ar_order = s.get('ar_order', 1)
        df = fetch_data(tk, date_from, date_to)
        r1 = run_ar(tk, train_ratio, p=ar_order, date_from=date_from, date_to=date_to)
        r2 = run_mlr(tk, train_ratio, p=ar_order, date_from=date_from, date_to=date_to)
        r3 = run_cart(tk, train_ratio, p=ar_order, date_from=date_from, date_to=date_to)
        m1 = calc_metrics(r1['yte'], r1['pte'], k=ar_order)
        m2 = calc_metrics(r2['yte'], r2['pte'], k=3 * ar_order)
        m3 = calc_metrics(r3['yte'], r3['pte'], k=6 * ar_order)
        # Update state in place
        with _LOCK:
            _STATE.update(dict(ticker=tk, df=df, r1=r1, r2=r2, r3=r3,
                                m1=m1, m2=m2, m3=m3))
        last_close = _safe_float(df['Close'].iloc[-1]) * 1000 if len(df) else 0.0
        return {'switched': True, 'ticker': tk,
                'last_close_vnd': last_close,
                'message': f'context updated to {tk}'}
    except Exception as e:
        return {'error': f'switch_failed: {str(e)[:200]}'}


# ═══════════════════════════════════════════════════════════════════
# REGISTRY — list of callables exposed to Gemini
# ═══════════════════════════════════════════════════════════════════
AVAILABLE_TOOLS = [
    get_current_ticker_data,
    get_forecast_results,
    get_technical_signals,
    get_price_history,
    get_price_on_date,
    get_price_range,
    get_portfolio,
    compute_metric,
    switch_ticker,
]


