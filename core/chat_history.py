"""Chat history manager — ISOLATED PER USER via st.session_state.

CRITICAL FIX 2026-04-24: trước đây dùng file `.chat_history.json` GLOBAL →
mọi user share chung lịch sử chat (bug privacy khi deploy cho nhiều người).

Giờ lưu trong `st.session_state['_chat_convs']` → Streamlit tự isolate mỗi
session (mỗi tab browser / user) → không bao giờ lẫn lộn giữa users.

Tradeoff: chat history mất khi user refresh / đóng tab. Phù hợp cho NCKH
demo — không cần persistence dài hạn, đổi lấy privacy tuyệt đối.

Public API giữ nguyên 100% → app_pages/chatbot.py KHÔNG cần sửa.
"""
import uuid
from datetime import datetime
import streamlit as st


_KEY_CONVS     = '_chat_convs'      # dict[cid, conversation]
_KEY_ACTIVE_ID = '_chat_active_id'  # str | None


def _store() -> dict:
    """Trả về dict conversations của session hiện tại (tạo mới nếu chưa có)."""
    if _KEY_CONVS not in st.session_state:
        st.session_state[_KEY_CONVS] = {}
    return st.session_state[_KEY_CONVS]


def list_conversations() -> list:
    """Trả về list conversations sorted by updated_at DESC."""
    convs_dict = _store()
    convs = []
    for cid, conv in convs_dict.items():
        convs.append({
            'id':            cid,
            'title':         conv.get('title', 'Hội thoại mới'),
            'created_at':    conv.get('created_at', ''),
            'updated_at':    conv.get('updated_at', ''),
            'message_count': len(conv.get('messages', [])),
        })
    convs.sort(key=lambda x: x['updated_at'], reverse=True)
    return convs


def create_conversation(title: str = None) -> str:
    """Tạo conversation mới, return ID."""
    convs = _store()
    cid = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat()
    convs[cid] = {
        'title':      title or 'Hội thoại mới',
        'created_at': now,
        'updated_at': now,
        'messages':   [],
    }
    st.session_state[_KEY_ACTIVE_ID] = cid
    return cid


def get_conversation(cid: str) -> dict:
    return _store().get(cid, {})


def add_message(cid: str, role: str, content: str, diagram: str = None):
    """Thêm message vào conversation, auto-title từ tin đầu tiên."""
    convs = _store()
    if cid not in convs:
        return
    msg = {
        'role':      role,
        'content':   content,
        'timestamp': datetime.now().isoformat(),
    }
    if diagram:
        msg['diagram'] = diagram
    conv = convs[cid]
    conv['messages'].append(msg)
    conv['updated_at'] = datetime.now().isoformat()
    if conv['title'] == 'Hội thoại mới' and role == 'user' and len(conv['messages']) == 1:
        conv['title'] = content[:40] + ('...' if len(content) > 40 else '')


def delete_conversation(cid: str):
    convs = _store()
    if cid in convs:
        del convs[cid]
        if st.session_state.get(_KEY_ACTIVE_ID) == cid:
            st.session_state[_KEY_ACTIVE_ID] = None


def remove_last_message(cid: str) -> dict | None:
    """Xoá tin nhắn cuối cùng khỏi conversation (dùng cho regenerate).
    Returns removed message dict, hoặc None nếu không có gì để xoá.
    """
    convs = _store()
    if cid not in convs:
        return None
    conv = convs[cid]
    msgs = conv.get('messages', [])
    if not msgs:
        return None
    removed = msgs.pop()
    conv['updated_at'] = datetime.now().isoformat()
    return removed


def rename_conversation(cid: str, new_title: str):
    convs = _store()
    if cid in convs:
        convs[cid]['title'] = new_title


def get_active_id() -> str:
    return st.session_state.get(_KEY_ACTIVE_ID)


def set_active_id(cid: str):
    st.session_state[_KEY_ACTIVE_ID] = cid


def export_to_markdown(cid: str) -> str:
    conv = get_conversation(cid)
    if not conv:
        return ''
    lines = [
        f'# {conv["title"]}',
        '',
        f'**Tạo lúc**: {conv["created_at"]}',
        f'**Cập nhật**: {conv["updated_at"]}',
        f'**Số tin nhắn**: {len(conv["messages"])}',
        '',
        '---',
        '',
    ]
    for msg in conv['messages']:
        role = '**BẠN**' if msg['role'] == 'user' else '**TRỢ LÝ AI**'
        ts = msg.get('timestamp', '')[:19].replace('T', ' ')
        lines.append(f'### {role} — *{ts}*')
        lines.append('')
        lines.append(msg['content'])
        lines.append('')
        lines.append('---')
        lines.append('')
    return '\n'.join(lines)


def format_timestamp(iso_str: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_str)
        now = datetime.now()
        delta = now - dt
        if delta.days == 0:
            return dt.strftime('%H:%M')
        elif delta.days == 1:
            return f'Hôm qua {dt.strftime("%H:%M")}'
        elif delta.days < 7:
            return f'{delta.days} ngày trước'
        else:
            return dt.strftime('%d/%m/%Y')
    except Exception:
        return iso_str[:16] if iso_str else ''
