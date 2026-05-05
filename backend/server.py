"""FastAPI server for Cantonese Learning App."""

import uuid
import asyncio
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from . import memory
from .llm import chat
from .tts import generate_audio, get_voices, DEFAULT_VOICE

app = FastAPI(title="粵語學習 App", version="1.0.0")

STATIC_DIR = Path(__file__).parent.parent / "frontend" / "static"


# ─── Models ───────────────────────────────────────────────

class ChatRequest(BaseModel):
    conversation_id: str
    message: str
    level: str = "beginner"


class HelpRequest(BaseModel):
    conversation_id: str


class CreateConversationRequest(BaseModel):
    title: str = "新對話"
    level: str = "beginner"


class UpdateLevelRequest(BaseModel):
    level: str


# ─── API Routes ───────────────────────────────────────────

@app.post("/api/chat")
async def api_chat(req: ChatRequest):
    """Send user message and get AI Cantonese response."""
    # Validate conversation exists
    conv = memory.get_conversation(req.conversation_id)
    if not conv:
        raise HTTPException(404, "對話唔存在")

    # Ensure level matches
    if conv["level"] != req.level:
        memory.update_level(req.conversation_id, req.level)

    # Save user message
    memory.add_message(
        conversation_id=req.conversation_id,
        role="user",
        user_text=req.message,
    )

    # Get conversation messages for context
    messages = memory.get_messages(req.conversation_id)

    # Call LLM
    try:
        result = chat(messages, level=req.level, help_mode=False)
    except Exception as e:
        raise HTTPException(500, f"AI 回應失敗：{str(e)}")

    # Save assistant message
    memory.add_message(
        conversation_id=req.conversation_id,
        role="assistant",
        cantonese=result["cantonese"],
        jyutping=result["jyutping"],
        mandarin_help=result.get("mandarin_help", ""),
    )

    return result


@app.post("/api/help")
async def api_help(req: HelpRequest):
    """Get Mandarin explanation for the last assistant message."""
    conv = memory.get_conversation(req.conversation_id)
    if not conv:
        raise HTTPException(404, "對話唔存在")

    messages = memory.get_messages(req.conversation_id)

    # Call LLM with help_mode=True
    try:
        result = chat(messages, level=conv["level"], help_mode=True)
    except Exception as e:
        raise HTTPException(500, f"AI 回應失敗：{str(e)}")

    help_text = result.get("mandarin_help", "")

    # If LLM returned new cantonese instead of help, extract help from text
    if not help_text and result.get("cantonese"):
        # The model may have put help in the cantonese field
        help_text = result["cantonese"]

    # Update last assistant message with help
    if help_text:
        db = memory.get_db()
        last = db.execute(
            "SELECT id FROM messages WHERE conversation_id = ? AND role = 'assistant' ORDER BY id DESC LIMIT 1",
            (req.conversation_id,),
        ).fetchone()
        if last:
            db.execute(
                "UPDATE messages SET mandarin_help = ? WHERE id = ?",
                (help_text, last["id"]),
            )
        db.commit()
        db.close()

    return {"mandarin_help": help_text}


@app.get("/api/tts")
async def api_tts(
    text: str = Query(...),
    voice: str = Query(DEFAULT_VOICE),
    rate: float = Query(1.0, ge=0.5, le=2.0),
):
    """Generate Cantonese TTS audio for the given text."""
    try:
        audio = await generate_audio(text, voice=voice, rate=rate)
    except Exception as e:
        raise HTTPException(500, f"語音生成失敗：{str(e)}")
    return Response(content=audio, media_type="audio/mpeg")


@app.get("/api/voices")
async def api_voices():
    """List available Cantonese TTS voices."""
    return await get_voices()


@app.get("/api/conversations")
async def api_list_conversations():
    """List all conversation sessions."""
    return memory.list_conversations()


@app.post("/api/conversations")
async def api_create_conversation(req: CreateConversationRequest):
    """Create a new conversation."""
    conv_id = uuid.uuid4().hex[:12]
    memory.create_conversation(conv_id, title=req.title, level=req.level)

    # Send initial greeting
    memory.add_message(
        conversation_id=conv_id,
        role="assistant",
        cantonese="你好！我係你嘅粵語老師。你想學啲乜嘢呀？",
        jyutping="nei5 hou2! ngo5 hai6 nei5 ge3 jyut6 jyu5 lou5 si1. nei5 soeng2 hok6 di1 mat1 je5 aa3?",
    )

    return {"id": conv_id, "title": req.title, "level": req.level}


@app.get("/api/conversations/{conv_id}")
async def api_get_conversation(conv_id: str):
    """Get conversation with messages."""
    conv = memory.get_conversation(conv_id)
    if not conv:
        raise HTTPException(404, "對話唔存在")
    return conv


@app.delete("/api/conversations/{conv_id}")
async def api_delete_conversation(conv_id: str):
    """Delete a conversation."""
    memory.delete_conversation(conv_id)
    return {"ok": True}


@app.patch("/api/conversations/{conv_id}/level")
async def api_update_level(conv_id: str, req: UpdateLevelRequest):
    """Update conversation difficulty level."""
    if req.level not in ("beginner", "elementary", "intermediate", "advanced"):
        raise HTTPException(400, "無效嘅程度")
    memory.update_level(conv_id, req.level)
    return {"ok": True}


# ─── Static Files ─────────────────────────────────────────

@app.get("/")
async def serve_index():
    return FileResponse(STATIC_DIR / "index.html")


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ─── Entrypoint ───────────────────────────────────────────

def main():
    import uvicorn
    uvicorn.run("backend.server:app", host="0.0.0.0", port=8899, reload=True)


if __name__ == "__main__":
    main()
