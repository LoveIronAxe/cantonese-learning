"""SQLite-based conversation memory."""

import sqlite3
import json
import time
from pathlib import Path

DB_PATH = Path(__file__).parent / "memory.db"


def get_db() -> sqlite3.Connection:
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    return db


def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT '新對話',
            level TEXT NOT NULL DEFAULT 'beginner',
            created_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            cantonese TEXT,
            jyutping TEXT,
            mandarin_help TEXT,
            user_text TEXT,
            created_at REAL NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conversation_id, id);
    """)
    db.commit()
    db.close()


def create_conversation(conv_id: str, title: str = "新對話", level: str = "beginner"):
    db = get_db()
    db.execute(
        "INSERT INTO conversations (id, title, level, created_at) VALUES (?, ?, ?, ?)",
        (conv_id, title, level, time.time()),
    )
    db.commit()
    db.close()


def get_conversation(conv_id: str) -> dict | None:
    db = get_db()
    row = db.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
    if not row:
        db.close()
        return None
    conv = dict(row)
    msgs = db.execute(
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id", (conv_id,)
    ).fetchall()
    conv["messages"] = [dict(m) for m in msgs]
    db.close()
    return conv


def list_conversations() -> list[dict]:
    db = get_db()
    rows = db.execute(
        "SELECT * FROM conversations ORDER BY created_at DESC"
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def add_message(
    conversation_id: str,
    role: str,
    cantonese: str | None = None,
    jyutping: str | None = None,
    mandarin_help: str | None = None,
    user_text: str | None = None,
):
    db = get_db()
    db.execute(
        """INSERT INTO messages (conversation_id, role, cantonese, jyutping, mandarin_help, user_text, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (conversation_id, role, cantonese, jyutping, mandarin_help, user_text, time.time()),
    )
    # Update conversation title from first user message
    if role == "user" and user_text:
        existing = db.execute(
            "SELECT COUNT(*) as c FROM messages WHERE conversation_id = ? AND role = 'user'",
            (conversation_id,),
        ).fetchone()
        if existing["c"] == 1:
            title = user_text[:30] + ("..." if len(user_text) > 30 else "")
            db.execute(
                "UPDATE conversations SET title = ? WHERE id = ?",
                (title, conversation_id),
            )
    db.commit()
    db.close()


def get_messages(conversation_id: str) -> list[dict]:
    db = get_db()
    rows = db.execute(
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id",
        (conversation_id,),
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def update_level(conv_id: str, level: str):
    db = get_db()
    db.execute("UPDATE conversations SET level = ? WHERE id = ?", (level, conv_id))
    db.commit()
    db.close()


def delete_conversation(conv_id: str):
    db = get_db()
    db.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
    db.commit()
    db.close()


# Initialize on import
init_db()
