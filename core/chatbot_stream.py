# -*- coding: utf-8 -*-
"""Streaming + function-calling Gemini client.

Wraps `google-genai` Client for the chat page. Yields a stream of typed events:

  {'type': 'text',        'delta': str}
  {'type': 'tool_call',   'name': str, 'args': dict}
  {'type': 'tool_result', 'name': str, 'value': any}
  {'type': 'done'}
  {'type': 'error',       'message': str, 'kind': 'rate_limit'|'quota'|'auth'|'other'}

If the new SDK call fails for any reason, the caller can fall through to the
legacy synchronous `core.chatbot_logic._process_query` chain.

The function-call protocol with google-genai (v1.x) supports two modes:

  1. **Automatic** — pass `tools=[fn1, fn2, ...]` and the SDK will run the
     callables itself, then insert tool_response parts back into the stream.
     The caller still sees the tool_call event in the chunk stream so we
     can show transparency in the UI.
  2. **Manual** — pass `Tool` objects with declared schemas; the SDK gives
     you back function_call parts and you execute + reply yourself.

We use mode 1 (automatic). It's simpler and matches "tools=[...] auto-
introspects schema from type hints + docstring" promised by the SDK docs.
"""
from __future__ import annotations

from typing import Iterator, List, Dict, Any
import streamlit as st

from core import chatbot_tools as _tools


def _get_gemini_key() -> str:
    """Read Gemini API key from st.secrets (lazy)."""
    try:
        return st.secrets.get('GEMINI_API_KEY', '') or ''
    except Exception:
        return ''


def _system_prompt(lang: str) -> str:
    try:
        from core.chatbot_ai import _SYSTEM_PROMPT_VI, _SYSTEM_PROMPT_EN
    except Exception:
        return ''
    return _SYSTEM_PROMPT_VI if lang == 'VI' else _SYSTEM_PROMPT_EN


def _context_string(context: dict | None) -> str:
    try:
        from core.chatbot_ai import build_context_string
        return build_context_string(context or {})
    except Exception:
        return ''


# Model preference — flash is the right balance for chat (low latency, function
# calling, free tier OK). Lite is too small for tool calls.
_MODEL_CANDIDATES = [
    'gemini-2.0-flash',
    'gemini-2.0-flash-001',
    'gemini-2.5-flash',
]


def is_streaming_available() -> bool:
    """True iff the new SDK can be imported AND a Gemini API key is configured."""
    if not _get_gemini_key():
        return False
    try:
        from google import genai  # noqa
        from google.genai import types  # noqa
        return True
    except Exception:
        return False


def _to_history_contents(history: List[Dict[str, str]], lang: str):
    """Convert {'role':'user'|'assistant','content':...} → list of types.Content.

    The google-genai SDK expects role='user' or 'model'. We trim per-message
    content to 600 chars and cap the total to last 4 messages — perf tuning
    v18 (2026-05-06): smaller payload → faster TTFB on Gemini streaming.
    """
    from google.genai import types
    history = history or []
    history = history[-4:]
    out = []
    for h in history:
        role = h.get('role', 'user')
        text = (h.get('content') or '').strip()
        if not text:
            continue
        if len(text) > 600:
            text = text[:600] + '…'
        sdk_role = 'model' if role == 'assistant' else 'user'
        try:
            part = types.Part.from_text(text=text)
        except TypeError:
            # Older SDK takes positional argument
            part = types.Part.from_text(text)
        out.append(types.Content(role=sdk_role, parts=[part]))
    return out


def _build_user_content(query: str, context_str: str, lang: str):
    """Wrap the current user query (+ context block) into a Content."""
    from google.genai import types
    if lang == 'EN':
        body = f"{context_str}\n\n## USER QUESTION:\n{query}" if context_str else query
    else:
        body = f"{context_str}\n\n## CÂU HỎI NGƯỜI DÙNG:\n{query}" if context_str else query
    try:
        part = types.Part.from_text(text=body)
    except TypeError:
        part = types.Part.from_text(body)
    return types.Content(role='user', parts=[part])


def _safety_settings(types_mod):
    return [
        types_mod.SafetySetting(category=types_mod.HarmCategory.HARM_CATEGORY_HARASSMENT,
                                 threshold=types_mod.HarmBlockThreshold.BLOCK_NONE),
        types_mod.SafetySetting(category=types_mod.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                                 threshold=types_mod.HarmBlockThreshold.BLOCK_NONE),
        types_mod.SafetySetting(category=types_mod.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                                 threshold=types_mod.HarmBlockThreshold.BLOCK_NONE),
        types_mod.SafetySetting(category=types_mod.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                                 threshold=types_mod.HarmBlockThreshold.BLOCK_NONE),
    ]


def _classify_error(err: Exception) -> str:
    s = str(err).lower()
    if 'per day' in s or 'daily' in s:
        return 'quota'
    if '429' in s or 'rate' in s or 'quota' in s or 'exhaust' in s:
        return 'rate_limit'
    if '401' in s or '403' in s or 'permission' in s or 'auth' in s or 'api key' in s:
        return 'auth'
    return 'other'


def _query_needs_data(query: str) -> bool:
    """True if the user clearly asks for live numbers — force a function_call.

    When True, we set tool_config mode='ANY' so Gemini MUST emit a tool call
    instead of hallucinating "I don't have access to that data".
    Theory questions ("AR là gì?", "MAPE là gì?") return False — answered
    from training knowledge with KaTeX, no tool needed.

    v18 additions: detect explicit date references (DD/MM, "ngày X",
    "tháng N", "Q1 2024", "tuần qua", "highest in March") so the model
    is forced to call get_price_on_date / get_price_range instead of
    making up historical numbers.
    """
    if not query:
        return False
    import re
    import unicodedata
    s = unicodedata.normalize('NFKD', query.lower())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.replace('đ', 'd')

    theory_markers = (
        'la gi', 'la sao', 'nghia la', 'cong thuc tong quat',
        'giai thich', 'dinh nghia', 'y nghia',
        'what is', 'what are', 'how does', 'how do', 'explain',
        'meaning', 'definition',
    )
    if any(m in s for m in theory_markers):
        return False

    # Date-shaped patterns → must consult historical data
    date_patterns = (
        r'\b\d{1,2}[/\-.]\d{1,2}([/\-.]\d{2,4})?\b',     # 20/3, 20-3-2024
        r'\bngay\s+\d{1,2}\b',                             # ngày 20
        r'\bthang\s+\d{1,2}\b',                            # tháng 3
        r'\bq[1-4]\s*\d{2,4}\b',                           # Q1 2024
        r'\bquy\s+[1-4]\b',                                # quý 1
        r'\bnam\s+\d{4}\b',                                # năm 2024
    )
    if any(re.search(p, s) for p in date_patterns):
        return True

    history_keywords = (
        'tuan qua', 'tuan truoc', 'last week',
        'thang qua', 'thang truoc', 'last month',
        'ngay qua', 'hom qua', 'yesterday',
        'cao nhat', 'thap nhat', 'highest', 'lowest',
        'trong khoang', 'tu ngay', 'den ngay',
        'between', 'from', 'to', 'period',
        'thang gieng', 'thang hai', 'thang ba', 'thang tu',
        'thang nam', 'thang sau', 'thang bay', 'thang tam',
        'thang chin', 'thang muoi', 'thang muoi mot', 'thang muoi hai',
        'january', 'february', 'march', 'april', 'may ', 'june',
        'july', 'august', 'september', 'october', 'november', 'december',
    )
    if any(k in s for k in history_keywords):
        return True

    data_signals = (
        'phan tich', 'analyze', 'analysis',
        'du bao', 'forecast', 'predict',
        'tinh du bao', 'tinh toan', 'compute', 'calculate',
        'gia hien tai', 'current price', 'gia dong cua',
        'phien toi', 'next session', 'phien tiep', 'phien gan nhat',
        'last session', 'mape cua', 'rmse cua', 'r2 cua',
        'tom tat', 'summary', 'tong quan',
        'so sanh ar', 'so sanh mlr', 'so sanh cart',
    )
    if any(sig in s for sig in data_signals):
        return True

    has_ticker = any(t in s for t in ('fpt', 'hpg', 'vnm'))
    if has_ticker and len(s) < 50:
        return True

    return False


def stream_answer(query: str, history: List[Dict[str, str]],
                  context: dict | None, lang: str = 'VI') -> Iterator[Dict[str, Any]]:
    """Stream a Gemini reply with native function calling.

    Yields events. Stops yielding on `done` or `error`. The caller is
    responsible for accumulating text and writing the final message to
    chat history.
    """
    api_key = _get_gemini_key()
    if not api_key:
        yield {'type': 'error', 'kind': 'auth',
               'message': 'GEMINI_API_KEY chưa cấu hình.'}
        return

    try:
        from google import genai
        from google.genai import types
    except Exception as e:
        yield {'type': 'error', 'kind': 'other',
               'message': f'google-genai chưa cài đặt: {e}'}
        return

    client = genai.Client(api_key=api_key)
    system_prompt = _system_prompt(lang)
    context_str = _context_string(context)

    # Build SDK contents: history + current user query
    contents = _to_history_contents(history, lang)
    contents.append(_build_user_content(query, context_str, lang))

    # Tools: pass Python callables — SDK auto-introspects.
    tool_callables = list(_tools.AVAILABLE_TOOLS)
    try:
        print(f'[chatbot_stream] Streaming with {len(tool_callables)} tools: '
              f'{[t.__name__ for t in tool_callables]}')
    except UnicodeEncodeError:
        pass

    last_err: Exception | None = None

    # Detect if user is asking for live numbers → force tool call if so.
    # mode='ANY' makes Gemini MUST emit a function_call instead of
    # hallucinating "I don't have access to that data".
    _force_tool = _query_needs_data(query)
    try:
        print(f'[chatbot_stream] force_tool={_force_tool} for query: '
              f'{query[:60]!r}')
    except UnicodeEncodeError:
        pass

    for model_name in _MODEL_CANDIDATES:
        try:
            cfg_kwargs: Dict[str, Any] = dict(
                system_instruction=system_prompt,
                temperature=0.5,
                top_p=0.9,
                max_output_tokens=2048,
                tools=tool_callables,
            )
            try:
                cfg_kwargs['safety_settings'] = _safety_settings(types)
            except Exception:
                pass

            # Force AUTO function calling mode — without this, some Gemini
            # models default to a "respond text-only" path and hallucinate
            # "I don't have access to that function". AUTO lets the model
            # decide per-turn whether to call a tool, which is what we want.
            try:
                cfg_kwargs['tool_config'] = types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode='ANY' if _force_tool else 'AUTO',
                    )
                )
            except Exception:
                pass  # SDK without ToolConfig — AUTO is the default anyway

            try:
                config = types.GenerateContentConfig(**cfg_kwargs)
            except Exception as _cfg_err:
                try:
                    print(f'[chatbot_stream] GenerateContentConfig failed: {_cfg_err}')
                except UnicodeEncodeError:
                    pass
                # Try without tool_config first (older SDK)
                cfg_kwargs.pop('tool_config', None)
                try:
                    config = types.GenerateContentConfig(**cfg_kwargs)
                except Exception:
                    # Last resort — drop tools AND log loudly so we can spot
                    # this in production. After this, function calling is OFF.
                    try:
                        print('[chatbot_stream] WARNING: tools dropped due '
                              'to SDK incompatibility — function calling is OFF')
                    except UnicodeEncodeError:
                        pass
                    cfg_kwargs.pop('tools', None)
                    config = types.GenerateContentConfig(**cfg_kwargs)

            stream = client.models.generate_content_stream(
                model=model_name,
                contents=contents,
                config=config,
            )

            # Drain the stream
            for chunk in stream:
                # Stop button check
                try:
                    if st.session_state.get('_chat_stop_streaming'):
                        st.session_state['_chat_stop_streaming'] = False
                        yield {'type': 'done', 'stopped': True}
                        return
                except Exception:
                    pass

                cands = getattr(chunk, 'candidates', None) or []
                if not cands:
                    # Some chunks just have aggregate text via .text property
                    text_chunk = ''
                    try:
                        text_chunk = chunk.text or ''
                    except Exception:
                        text_chunk = ''
                    if text_chunk:
                        yield {'type': 'text', 'delta': text_chunk}
                    continue
                # Walk parts of the first candidate
                content = getattr(cands[0], 'content', None)
                parts = getattr(content, 'parts', None) or []
                for p in parts:
                    fc = getattr(p, 'function_call', None)
                    fr = getattr(p, 'function_response', None)
                    txt = getattr(p, 'text', None)
                    if fc is not None and getattr(fc, 'name', None):
                        try:
                            args_dict = dict(fc.args) if fc.args is not None else {}
                        except Exception:
                            args_dict = {}
                        yield {'type': 'tool_call',
                               'name': str(fc.name), 'args': args_dict}
                    elif fr is not None and getattr(fr, 'name', None):
                        try:
                            resp = dict(fr.response) if fr.response is not None else {}
                        except Exception:
                            resp = {'_raw': str(fr.response)[:300]}
                        yield {'type': 'tool_result',
                               'name': str(fr.name), 'value': resp}
                    elif txt:
                        yield {'type': 'text', 'delta': txt}

            yield {'type': 'done'}
            return

        except Exception as e:
            last_err = e
            kind = _classify_error(e)
            if kind == 'quota':
                yield {'type': 'error', 'kind': 'quota',
                       'message': 'Hết quota miễn phí hôm nay (Gemini).'}
                return
            if kind == 'auth':
                yield {'type': 'error', 'kind': 'auth',
                       'message': f'Lỗi xác thực API: {str(e)[:200]}'}
                return
            # Try next model on rate_limit / other; surface error if last
            continue

    yield {'type': 'error',
           'kind': _classify_error(last_err) if last_err else 'other',
           'message': f'Streaming thất bại: {str(last_err)[:200]}' if last_err
                      else 'Streaming không khả dụng.'}
