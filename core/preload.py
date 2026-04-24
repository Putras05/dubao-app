"""Preload data + model results at session start → slider/p changes instant.

Strategy:
  - fetch_data cho 3 tickers (parallel) — warm disk cache
  - run_ar / run_mlr cho 3 tickers × 5 train ratios × 3 p values (1,3,5) — FAST (~ms)
  - run_cart trong daemon thread background — SLOW (GridSearchCV ~3-5s/lần)
  - User đổi ticker / train_ratio / p (thuộc common values) → cache hit → 0s
  - Chỉ khi đổi sang giá trị NGOÀI common → training overlay hiện 3-5s
"""
import streamlit as st
import threading
from concurrent.futures import ThreadPoolExecutor
from data.fetcher import fetch_data
from core.constants import TICKERS

_SLIDER_VALUES = [0.70, 0.75, 0.80, 0.85, 0.90]
_COMMON_P       = [1, 3, 5]                    # common p values — preload hết
_DEFAULT_P      = 1

_cart_threads: list = []


# ── Background CART precompute ───────────────────────────────────────────────
def _bg_cart(ticker: str, ar_order: int,
             date_from=None, date_to=None) -> None:
    """Run CART cho 5 slider values × common p values, trong daemon thread."""
    from models.cart import run_cart
    for p in _COMMON_P:
        for tr in _SLIDER_VALUES:
            try:
                run_cart(ticker, tr, p=p,
                         date_from=date_from, date_to=date_to)
            except Exception:
                pass


def trigger_bg_cart(ticker: str, ar_order: int,
                    date_from=None, date_to=None) -> None:
    """Launch CART background precompute nếu chưa chạy cho ticker này."""
    bg_key = f'_cart_bg_{ticker}'
    if st.session_state.get(bg_key):
        return
    st.session_state[bg_key] = True
    th = threading.Thread(
        target=_bg_cart,
        args=(ticker, ar_order, date_from, date_to),
        daemon=True,
    )
    th.start()
    _cart_threads.append(th)


def trigger_bg_cart_all() -> None:
    """Warm CART cho TẤT CẢ tickers × p values ở background.

    Gọi sau preload_all_tickers → lúc user đang đọc Dashboard, CART background
    đã train xong cho mọi combo → switch page = instant.
    """
    for tk in TICKERS:
        trigger_bg_cart(tk, _DEFAULT_P)


# ── Parallel ticker fetch — 3 tickers fetch đồng thời thay vì tuần tự ────────
def _fetch_all_parallel() -> None:
    """Fetch 3 tickers đồng thời → giảm thời gian khởi tạo lần đầu."""
    with ThreadPoolExecutor(max_workers=len(TICKERS)) as ex:
        futures = [ex.submit(fetch_data, tk) for tk in TICKERS]
        for f in futures:
            try:
                f.result(timeout=30)
            except Exception:
                pass


# ── Main preload ─────────────────────────────────────────────────────────────
def preload_all_tickers() -> None:
    """Warm cache cho 3 tickers × 5 ratios × 3 p values.

    Chạy 1 lần mỗi session (gated bởi session_state `_preloaded`).
    Tổng khoảng 45 model AR + 45 model MLR → ~5-8s trên máy thường.
    CART background song song, không block UI.
    """
    if st.session_state.get('_preloaded'):
        return

    from models.ar  import run_ar
    from models.mlr import run_mlr

    _loader   = st.empty()
    _progress = st.empty()

    with _loader.container():
        st.markdown(
            '<div style="background:rgba(21,101,192,0.08);'
            'border:1px solid rgba(21,101,192,0.2);'
            'border-radius:10px;padding:12px 18px;margin-bottom:8px">'
            '<div style="font-size:12px;font-weight:700;color:#1565C0;'
            'letter-spacing:0.5px;text-transform:uppercase">'
            'Khởi tạo dữ liệu · First launch</div>'
            '<div style="font-size:11px;color:#64748B;margin-top:4px">'
            'Tải dữ liệu 3 ticker (song song) + huấn luyện sẵn AR/MLR cho '
            'mọi tỉ lệ và p={1,3,5}...</div>'
            '</div>', unsafe_allow_html=True)

    _bar = _progress.progress(0, text='')

    # Step 1: Fetch song song
    _bar.progress(5, text='Tải dữ liệu 3 ticker (song song)...')
    _fetch_all_parallel()

    # Step 2: AR + MLR song song — 90 combos chạy đồng thời trong 8 worker
    # → giảm cold start từ ~5-8s xuống ~1-2s trên máy 4+ cores.
    jobs = []
    for tk in TICKERS:
        for p in _COMMON_P:
            for tr in _SLIDER_VALUES:
                jobs.append(('AR',  tk, tr, p))
                jobs.append(('MLR', tk, tr, p))
    total = len(jobs)

    def _train_one(job):
        kind, tk, tr, p = job
        try:
            if kind == 'AR':
                run_ar(tk, tr, p=p)
            else:
                run_mlr(tk, tr, p=p)
        except Exception:
            pass

    _bar.progress(10, text=f'Huấn luyện {total} mô hình AR+MLR (song song)...')
    done = 0
    from concurrent.futures import as_completed
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(_train_one, j): j for j in jobs}
        for fut in as_completed(futures):
            done += 1
            if done % 6 == 0 or done == total:  # cập nhật progress mỗi 6 jobs
                pct = 10 + int(done / total * 85)
                kind, tk, tr, p = futures[fut]
                _bar.progress(pct,
                              text=f'{kind}({p}) · {tk} · {int(tr*100)}% · {done}/{total}')

    _bar.progress(100, text='Hoàn tất · CART đang precompute ngầm')
    _loader.empty()
    _progress.empty()
    st.session_state['_preloaded'] = True

    # Step 3: CART background cho tất cả tickers × common p
    trigger_bg_cart_all()
