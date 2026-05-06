"""Response cache — narrow scope after Phase-4 (2026-05-06).

Phase-4: cache fires ONLY for pure-theory questions that match a known
keyword set (AR, MAPE, RMSE, Ichimoku, Kumo, etc.) AND have no ticker
context. Everything else bypasses the cache entirely so live answers
always reflect fresh prices.

The fuzzy MD5 cross-ticker layer is gone — cache key is now an EXACT
normalized query string + lang only. No more sharing across ambiguous
inputs.
"""
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path
import streamlit as st

from core.chatbot_ai import PROMPT_VERSION

_CACHE_FILE = Path(__file__).parent.parent / '.chatbot_cache.json'
_MAX_ITEMS  = 300
_TTL_HOURS  = 24
_MEM_KEY    = '_ai_mem_cache'
_MEM_MAX    = 200

# Hard-list of theory keywords. The query MUST contain at least one of
# these tokens (case-insensitive, diacritic-insensitive) AND be a clear
# theory question to be eligible for cache.
_THEORY_TOKENS = {
    'ar(1)', 'ar(p)', 'ar(2)', 'ar(3)', 'ar', 'mlr', 'cart',
    'mape', 'rmse', 'mae', 'r2adj', 'r²adj', 'r2', 'r²',
    'ichimoku', 'kumo', 'tenkan', 'kijun', 'chikou', 'senkou',
    'autoregressive', 'random walk', 'random-walk',
    'volatility', 'sigma', 'std',
}

_THEORY_QUESTION_MARKERS = (
    'la gi', 'la sao', 'nghia la', 'cong thuc', 'phuong trinh',
    'giai thich', 'dinh nghia', 'hoat dong', 'y nghia',
    'what is', 'what are', 'how does', 'how do', 'explain',
    'meaning', 'formula', 'equation', 'definition', 'derivation',
)

_TICKER_TOKENS = {'fpt', 'hpg', 'vnm'}


def _normalize_query(query: str) -> str:
    """Strict normalization: lowercase, strip diacritics, collapse whitespace,
    strip punctuation. Tokens are NOT sorted (order-sensitive cache key)."""
    if not query:
        return ''
    s = query.strip().lower()
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.replace('đ', 'd').replace('Đ', 'd')
    s = re.sub(r'[^\w\s\(\)\^\.²³]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def _is_pure_theory_query(query: str) -> bool:
    """True iff the query is a clear theory question with no ticker context.

    Requires:
      - At least one theory question marker ("la gi", "what is", ...)
      - At least one theory token (AR, MAPE, Ichimoku, ...)
      - No ticker name (FPT/HPG/VNM)
      - No data-dependent words (phan tich, du bao, gia, current, ...)
    """
    norm = _normalize_query(query)
    if not norm:
        return False
    tokens = frozenset(norm.split())

    if any(t in tokens for t in _TICKER_TOKENS):
        return False

    has_marker = any(m in norm for m in _THEORY_QUESTION_MARKERS)
    if not has_marker:
        return False

    has_theory_token = (
        any(tok in norm for tok in _THEORY_TOKENS)
        or any(tok in tokens for tok in _THEORY_TOKENS)
    )
    if not has_theory_token:
        return False

    data_kws = ['phan tich', 'du bao', 'gia', 'price', 'forecast',
                'analyze', 'analysis', 'hien tai', 'current',
                'phien toi', 'next session', 'today', 'hom nay']
    if any(k in norm for k in data_kws):
        return False
    return True


# ── Key helpers ──────────────────────────────────────────────────────────────
def _make_key(query: str, lang: str) -> str:
    """Phase-4 strict key: PROMPT_VERSION | normalized-query | lang.
    No ticker/p in key — only theory queries reach this function."""
    normalized = _normalize_query(query)
    raw = f"{PROMPT_VERSION}|theory|{normalized}|{lang}"
    return hashlib.md5(raw.encode()).hexdigest()


# ── Memory (session-state) layer ─────────────────────────────────────────────
def _mem_get(key: str):
    return st.session_state.get(_MEM_KEY, {}).get(key)


def _mem_set(key: str, value: str):
    if _MEM_KEY not in st.session_state:
        st.session_state[_MEM_KEY] = {}
    cache = st.session_state[_MEM_KEY]
    cache[key] = value
    if len(cache) > _MEM_MAX:
        oldest = next(iter(cache))
        del cache[oldest]


# ── Disk layer ───────────────────────────────────────────────────────────────
def _load() -> dict:
    if not _CACHE_FILE.exists():
        return {}
    try:
        with open(_CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data: dict):
    try:
        with open(_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f'Cache save error: {e}')


# ── Public API ────────────────────────────────────────────────────────────────
def get(query: str, context: dict = None, lang: str = 'VI'):
    """Return cached response, or None if the query is not a pure-theory hit
    or no cache entry exists. Phase-4: only theory queries are cached."""
    if not _is_pure_theory_query(query):
        return None
    key = _make_key(query, lang)

    mem = _mem_get(key)
    if mem:
        return mem

    data  = _load()
    entry = data.get(key)
    if not entry:
        return None
    try:
        expires = datetime.fromisoformat(entry['expires'])
        if datetime.now() > expires:
            return None
        response = entry['response']
        entry['accessed'] = datetime.now().isoformat()
        _save(data)
        _mem_set(key, response)
        return response
    except Exception:
        return None


def set(query: str, context: dict = None, response: str = '', lang: str = 'VI'):
    """Save response to both memory and disk cache — only for pure-theory
    queries. Calls on non-theory queries are silently ignored."""
    if not _is_pure_theory_query(query):
        return
    key = _make_key(query, lang)

    _mem_set(key, response)

    data = _load()
    now  = datetime.now()
    data[key] = {
        'response': response,
        'created':  now.isoformat(),
        'accessed': now.isoformat(),
        'expires':  (now + timedelta(hours=_TTL_HOURS)).isoformat(),
        'version':  PROMPT_VERSION,
    }
    if len(data) > _MAX_ITEMS:
        sorted_keys = sorted(data, key=lambda k: data[k].get('accessed', ''))
        for old_key in sorted_keys[:len(data) - _MAX_ITEMS]:
            del data[old_key]
    _save(data)


def clear():
    """Clear cả memory và disk cache."""
    if _MEM_KEY in st.session_state:
        st.session_state[_MEM_KEY] = {}
    _save({})


def stats() -> dict:
    data  = _load()
    now   = datetime.now()
    valid = sum(
        1 for v in data.values()
        if datetime.fromisoformat(v.get('expires', '2000-01-01')) > now
    )
    # Đếm entries theo version
    by_version = {}
    for v in data.values():
        ver = v.get('version', 'unknown')
        by_version[ver] = by_version.get(ver, 0) + 1

    mem_size = len(st.session_state.get(_MEM_KEY, {}))
    return {
        'total':       len(data),
        'valid':       valid,
        'expired':     len(data) - valid,
        'memory':      mem_size,
        'versions':    by_version,
        'current_ver': PROMPT_VERSION,
    }
