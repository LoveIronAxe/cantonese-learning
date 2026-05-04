"""Cantonese TTS using edge-tts with adjustable speed and caching."""

import hashlib
import asyncio
import tempfile
from pathlib import Path
import edge_tts

CACHE_DIR = Path(__file__).parent / "tts_cache"
CACHE_DIR.mkdir(exist_ok=True)

# Cantonese voices available in edge-tts
VOICES = {
    "female1": "zh-HK-HiuGaaiNeural",   # 曉佳 - clear, standard
    "female2": "zh-HK-HiuMaanNeural",   # 曉曼 - warm, natural
    "male": "zh-HK-WanLungNeural",      # 雲龍 - deep, clear
}

DEFAULT_VOICE = "female1"
DEFAULT_RATE = "+0%"  # normal speed, range: -50% to +50%


def _rate_to_string(rate: float) -> str:
    """Convert rate percentage to edge-tts format.

    rate: float from 0.5 to 2.0 (0.5=half speed, 1.0=normal, 2.0=double)
    """
    pct = int((rate - 1.0) * 100)
    return f"{pct:+d}%"


def _cache_key(text: str, voice: str, rate_str: str) -> str:
    raw = f"{text}|{voice}|{rate_str}"
    return hashlib.md5(raw.encode()).hexdigest()


async def generate_audio(
    text: str,
    voice: str = DEFAULT_VOICE,
    rate: float = 1.0,
) -> bytes:
    """Generate Cantonese TTS audio, returns MP3 bytes. Cached by content."""
    voice_name = VOICES.get(voice, VOICES[DEFAULT_VOICE])
    rate_str = _rate_to_string(rate)
    key = _cache_key(text, voice_name, rate_str)
    cache_file = CACHE_DIR / f"{key}.mp3"

    if cache_file.exists():
        return cache_file.read_bytes()

    communicate = edge_tts.Communicate(
        text=text,
        voice=voice_name,
        rate=rate_str,
    )

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        await communicate.save(tmp_path)
        data = Path(tmp_path).read_bytes()
        cache_file.write_bytes(data)
        return data
    finally:
        Path(tmp_path).unlink(missing_ok=True)


async def get_voices() -> list[dict]:
    """List available Cantonese voices."""
    return [
        {"id": k, "name": v, "label": {"female1": "曉佳 (女-清晰)", "female2": "曉曼 (女-自然)", "male": "雲龍 (男-沉穩)"}[k]}
        for k, v in VOICES.items()
    ]
