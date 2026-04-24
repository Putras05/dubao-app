"""Groq API fallback — dùng LLaMA 3.3 70B khi Gemini hết quota.

Free tier rộng rãi hơn nhiều (~14,000 req/ngày, 30 req/phút). Speed rất cao.
Không cần package mới — gọi REST API qua `requests` (đã có trong deps).

Setup: thêm GROQ_API_KEY vào .streamlit/secrets.toml
    Đăng ký free tại: https://console.groq.com/keys
"""
import streamlit as st

from core.chatbot_ai import (
    build_context_string, RateLimitError, QuotaExhaustedError,
    _SYSTEM_PROMPT_VI, _SYSTEM_PROMPT_EN,
)


# Thứ tự ưu tiên model — llama-3.3-70b cho chất lượng; 8b-instant cho fallback tốc độ
_MODEL_CANDIDATES = [
    'llama-3.3-70b-versatile',     # chất lượng cao nhất
    'llama-3.1-8b-instant',         # fallback tốc độ khi 70b bị rate limit
    'gemma2-9b-it',                 # fallback cuối (Google Gemma)
]


def _get_api_key() -> str:
    try:
        return st.secrets.get('GROQ_API_KEY', '') or ''
    except Exception:
        return ''


def is_groq_available() -> bool:
    return bool(_get_api_key())


def ask_groq(user_query: str, context: dict = None, lang: str = 'VI',
             slim_system: bool = False) -> str:
    """Gọi Groq API với retry đa model. Raises khi hết mọi option."""
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError('GROQ_API_KEY chưa cấu hình')

    import requests

    if slim_system:
        if lang == 'EN':
            system_prompt = (
                "You are a friendly AI assistant for a Vietnamese stock forecasting "
                "research app (TDTU NCKH 2026). The app uses real HOSE data for "
                "FPT, HPG, VNM with AR(p)/MLR(p)/CART(p) models. "
                "Reply naturally and conversationally. Never stay silent."
            )
        else:
            system_prompt = (
                "Bạn là trợ lý AI thân thiện của app NCKH dự báo giá cổ phiếu HOSE "
                "(TDTU 2026). App dùng dữ liệu thật cho FPT, HPG, VNM với 3 mô hình "
                "AR(p)/MLR(p)/CART(p). Hãy trả lời tự nhiên như trò chuyện. "
                "Không được im lặng."
            )
    else:
        system_prompt = _SYSTEM_PROMPT_VI if lang == 'VI' else _SYSTEM_PROMPT_EN

    context_str = build_context_string(context or {})
    if lang == 'EN':
        user_content = f"{context_str}\n\n## USER QUESTION:\n{user_query}"
    else:
        user_content = f"{context_str}\n\n## CÂU HỎI NGƯỜI DÙNG:\n{user_query}"

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }

    last_error = None
    all_rate_limited = True

    for model_name in _MODEL_CANDIDATES:
        try:
            body = {
                'model': model_name,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user',   'content': user_content},
                ],
                'temperature': 0.3,
                'top_p': 0.85,
                'max_tokens': 2048,
                'stream': False,
            }
            resp = requests.post(
                'https://api.groq.com/openai/v1/chat/completions',
                headers=headers, json=body, timeout=30,
            )

            if resp.status_code == 200:
                data = resp.json()
                text = ''
                try:
                    text = data['choices'][0]['message']['content'] or ''
                except Exception:
                    pass
                if text and text.strip():
                    return text.strip()
                all_rate_limited = False
                last_error = RuntimeError(f'{model_name}: empty response')
                continue

            err_body = ''
            try:
                err_body = resp.text[:500]
            except Exception:
                pass

            if resp.status_code == 429:
                try:
                    print(f'[Groq] {model_name} rate limited, trying next...')
                except UnicodeEncodeError:
                    pass
                last_error = RuntimeError(f'{model_name}: 429 {err_body[:200]}')
                continue

            if resp.status_code in (401, 403):
                raise RuntimeError(f'Groq auth failed ({resp.status_code}): {err_body[:200]}')

            if resp.status_code == 404:
                all_rate_limited = False
                last_error = RuntimeError(f'{model_name}: 404 not found')
                continue

            all_rate_limited = False
            last_error = RuntimeError(f'{model_name}: {resp.status_code} {err_body[:200]}')

        except requests.Timeout:
            last_error = RuntimeError(f'{model_name}: timeout')
            all_rate_limited = False
            continue
        except requests.RequestException as e:
            last_error = e
            all_rate_limited = False
            continue

    if all_rate_limited:
        raise RateLimitError(
            'Groq đang quá tải. Thử lại sau ít giây.',
            wait_seconds=15,
        )
    raise RuntimeError(f'Groq thất bại: {str(last_error)[:200]}')
