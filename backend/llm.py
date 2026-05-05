"""LLM integration for Cantonese teacher using Anthropic API.

Uses structured text output format since the DeepSeek proxy doesn't support tool_choice.
"""

import os
import re
from anthropic import Anthropic
from dotenv import load_dotenv
from .prompts import get_system_prompt, HELP_MODE_EXTRA

load_dotenv()

API_KEY = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
BASE_URL = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

client = Anthropic(api_key=API_KEY, base_url=BASE_URL)

OUTPUT_FORMAT = """
【输出格式 - 必须严格遵守】
每次回覆必须用以下格式：

【粵】<粤语口语文本，用繁体字>
【拼】<粤拼注音，每个音节用空格分隔>
【普】<普通话解释 - 只在学生按求助时填写，否则留空>

不要输出其他内容，只输出以上三个标签。
"""


def build_messages(conversation_messages: list[dict], level: str, help_mode: bool = False):
    """Build the messages array for the LLM API call."""
    system_prompt = get_system_prompt(level) + "\n" + OUTPUT_FORMAT
    if help_mode:
        system_prompt += HELP_MODE_EXTRA

    messages = []
    for msg in conversation_messages:
        if msg["role"] == "user":
            text = msg["user_text"] or ""
            messages.append({"role": "user", "content": text})
        elif msg["role"] == "assistant":
            content = f"【粵】{msg['cantonese'] or ''}\n【拼】{msg['jyutping'] or ''}"
            if msg.get("mandarin_help") and msg["mandarin_help"].strip():
                content += f"\n【普】{msg['mandarin_help']}"
            else:
                content += "\n【普】"
            messages.append({"role": "assistant", "content": content})

    # In help mode, add an explicit help request as the last user message
    if help_mode:
        messages.append({
            "role": "user",
            "content": "我㩒咗求助掣！請你用普通話解釋你最後一句粵語嘅意思，每個字點解，語法點樣用。（不要生成新粵語，只要普通話解釋！）"
        })

    return system_prompt, messages


def chat(conversation_messages: list[dict], level: str, help_mode: bool = False) -> dict:
    """Send a chat request and return structured Cantonese response."""
    system_prompt, messages = build_messages(conversation_messages, level, help_mode)

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=messages,
    )

    text = ""
    for block in response.content:
        if hasattr(block, "text"):
            text += block.text

    return _parse_response(text)


def _parse_response(text: str) -> dict:
    """Parse the structured text response into components."""
    result = {"cantonese": "", "jyutping": "", "mandarin_help": ""}

    # Extract 【普】 first (may contain any characters)
    pu_match = re.search(r"【普】\s*(.+)", text, re.DOTALL)
    if pu_match:
        result["mandarin_help"] = pu_match.group(1).strip()

    # Extract 【粤】 (content between 【粤】 and next tag)
    yue_match = re.search(r"【粵】\s*(.*?)\s*【拼】", text, re.DOTALL)
    if yue_match:
        val = yue_match.group(1).strip()
        if val:
            result["cantonese"] = val

    # Extract 【拼】 (content between 【拼】 and 【普】 or end)
    pin_match = re.search(r"【拼】\s*(.*?)\s*(?:【普】|$)", text, re.DOTALL)
    if pin_match:
        val = pin_match.group(1).strip()
        if val:
            result["jyutping"] = val

    return result
