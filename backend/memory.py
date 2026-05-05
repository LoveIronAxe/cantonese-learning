"""JSON file-based conversation memory. Works on Vercel serverless + local."""

import json
import time
import os
import threading
from pathlib import Path

# On Vercel, use /tmp (the only writable directory). Locally use backend dir.
if os.environ.get("VERCEL"):
    STORE_PATH = Path("/tmp/memory.json")
else:
    STORE_PATH = Path(__file__).parent / "memory.json"

_lock = threading.Lock()


def _load() -> dict:
    if STORE_PATH.exists():
        try:
            with open(STORE_PATH, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"conversations": {}, "order": []}


def _save(data: dict):
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(STORE_PATH) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, str(STORE_PATH))


def create_conversation(conv_id: str, title: str = "新對話", level: str = "beginner"):
    with _lock:
        data = _load()
        data["conversations"][conv_id] = {
            "id": conv_id,
            "title": title,
            "level": level,
            "created_at": time.time(),
            "messages": [],
        }
        data["order"].insert(0, conv_id)
        _save(data)


def get_conversation(conv_id: str) -> dict | None:
    data = _load()
    return data["conversations"].get(conv_id)


def list_conversations() -> list[dict]:
    data = _load()
    result = []
    for cid in data["order"]:
        conv = data["conversations"].get(cid)
        if conv:
            result.append({
                "id": conv["id"],
                "title": conv["title"],
                "level": conv["level"],
                "created_at": conv["created_at"],
            })
    return result


def add_message(
    conversation_id: str,
    role: str,
    cantonese: str | None = None,
    jyutping: str | None = None,
    mandarin_help: str | None = None,
    user_text: str | None = None,
):
    with _lock:
        data = _load()
        conv = data["conversations"].get(conversation_id)
        if not conv:
            return
        msg = {
            "id": len(conv["messages"]) + 1,
            "role": role,
            "cantonese": cantonese,
            "jyutping": jyutping,
            "mandarin_help": mandarin_help,
            "user_text": user_text,
            "created_at": time.time(),
        }
        conv["messages"].append(msg)
        # Update title from first user message
        if role == "user" and user_text:
            user_count = sum(1 for m in conv["messages"] if m["role"] == "user")
            if user_count == 1:
                conv["title"] = user_text[:30] + ("..." if len(user_text) > 30 else "")
        _save(data)


def get_messages(conversation_id: str) -> list[dict]:
    conv = get_conversation(conversation_id)
    if not conv:
        return []
    return conv["messages"]


def update_level(conv_id: str, level: str):
    with _lock:
        data = _load()
        if conv_id in data["conversations"]:
            data["conversations"][conv_id]["level"] = level
            _save(data)


def delete_conversation(conv_id: str):
    with _lock:
        data = _load()
        data["conversations"].pop(conv_id, None)
        if conv_id in data["order"]:
            data["order"].remove(conv_id)
        _save(data)


def update_last_help(conv_id: str, help_text: str):
    """Update mandarin_help on the last assistant message."""
    with _lock:
        data = _load()
        conv = data["conversations"].get(conv_id)
        if not conv:
            return
        for m in reversed(conv["messages"]):
            if m["role"] == "assistant":
                m["mandarin_help"] = help_text
                _save(data)
                return
