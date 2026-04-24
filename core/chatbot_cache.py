"""Response cache — two layers: session-state (fast) + disk JSON (persistent, 24-hour TTL).

- Cache key gồm PROMPT_VERSION → bump version khi đổi system prompt → cache cũ tự ignore
- TTL 24 giờ (tránh giá đóng cửa lỗi thời trong demo)
- Fuzzy matching: normalize query (bỏ dấu, bỏ dấu câu, bỏ stop words nhẹ) →
  "AR là gì?" và "AR la sao" cùng hit cache
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

# Stop words nhẹ để fuzzy — chỉ loại từ nối không thay đổi nghĩa câu hỏi
_FUZZY_STOP = {
    # VI filler
    'la', 'thi', 'ma', 'nhe', 'vay', 'nha', 'ban', 'minh', 'toi', 'a',
    'co', 'nao', 'sao', 'gi', 'the', 'di', 'duoc', 'dc', 'voi', 'cua',
    # EN filler
    'is', 'the', 'a', 'an', 'what', 'how', 'please', 'can', 'you', 'me',
}


def _normalize_query(query: str) -> str:
    """Chuẩn hoá câu hỏi để fuzzy match: lowercase, bỏ dấu tiếng Việt,
    bỏ dấu câu, bỏ stop words nhẹ, sort tokens để thứ tự không ảnh hưởng.

    Ví dụ:
      'AR là gì?'          → 'ar'
      'AR la sao?'          → 'ar'
      'MLR hoạt động thế nào'→ 'hoat dong mlr'
    """
    if not query:
        return ''
    s = query.strip().lower()
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.replace('đ', 'd').replace('Đ', 'd')
    s = re.sub(r'[^\w\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    tokens = [w for w in s.split() if w and w not in _FUZZY_STOP and len(w) > 0]
    tokens.sort()
    return ' '.join(tokens)


def _is_theory_query(query: str) -> bool:
    """Câu hỏi lý thuyết — cache có thể share cross-ticker (bỏ ticker khỏi key)."""
    q = (query or '').lower()
    theory_kws = [
        'là gì', 'là sao', 'nghĩa là', 'hoạt động', 'công thức', 'phương trình',
        'giải thích', 'định nghĩa', 'khác nhau', 'khác gì', 'so sánh',
        'nên chọn', 'khi nào', 'tại sao', 'ý nghĩa', 'thang đánh giá',
        'what is', 'what are', 'how does', 'how do', 'explain', 'meaning',
        'difference', 'compare', 'formula', 'equation', 'when to use',
        'why', 'definition',
    ]
    data_kws = ['giá', 'price', 'dự báo', 'forecast', 'phân tích',
                'analyze', 'analysis', 'hiện tại', 'current',
                'phiên tới', 'next session', 'fpt', 'hpg', 'vnm']
    return any(k in q for k in theory_kws) and not any(k in q for k in data_kws)


# ── Key helpers ──────────────────────────────────────────────────────────────
def _make_key(query: str, context: dict, lang: str) -> str:
    """Fuzzy key: normalize query → câu tương tự cùng hit.
    Câu lý thuyết: KHÔNG include ticker/p → cache share giữa các ticker (tối đa hiệu quả).
    """
    normalized = _normalize_query(query)
    if _is_theory_query(query):
        # Share cache cross-ticker for pure theory questions
        raw = f"{PROMPT_VERSION}|theory|{normalized}|{lang}"
    else:
        ticker = (context or {}).get('ticker', '')
        p      = (context or {}).get('p', 0)
        raw = f"{PROMPT_VERSION}|{normalized}|{ticker}|{p}|{lang}"
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
    """Return cached response or None."""
    key = _make_key(query, context, lang)

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
    """Save response to both memory and disk cache."""
    key = _make_key(query, context, lang)

    _mem_set(key, response)

    data = _load()
    now  = datetime.now()
    data[key] = {
        'response': response,
        'created':  now.isoformat(),
        'accessed': now.isoformat(),
        'expires':  (now + timedelta(hours=_TTL_HOURS)).isoformat(),
        'version':  PROMPT_VERSION,  # audit trail
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
