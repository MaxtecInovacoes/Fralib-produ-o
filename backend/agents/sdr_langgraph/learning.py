"""Lightweight SDR learning evaluator.

This module does not train a model. It promotes useful corrections and quality
signals into small reusable lessons that are injected into future SDR prompts.
"""


import json
import os
import re
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any


BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MEMORY_ROOT = os.path.join(BACKEND_DIR, "memory")

STAGE_ORDER = {
    "hook": 0,
    "qualify": 1,
    "pain": 2,
    "amplify": 3,
    "tease": 4,
    "proof": 5,
    "reveal": 6,
    "feedback": 7,
    "close": 8,
    "followup_24h": 9,
    "followup_72h": 10,
}

BASE_QUALITY_RULES = [
    "Use very few emojis; only one if it genuinely helps.",
    "Prefer 1-3 short WhatsApp messages instead of one long block.",
    "Do not repeat the last bot message or restart the script.",
    "Do not move backwards in the funnel unless the lead clearly changed context.",
    "Remember what was already said in the conversation history.",
    "Answer the lead's latest message before asking the next question.",
    "If a human corrected the bot, treat that correction as higher priority next time.",
]


def _tenant_dir(user_id: int) -> str:
    path = os.path.join(MEMORY_ROOT, f"u{int(user_id)}")
    os.makedirs(path, exist_ok=True)
    return path


def _learning_path(user_id: int) -> str:
    return os.path.join(_tenant_dir(user_id), "sdr_learning.json")


def _lead_learning_path(user_id: int, lead_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(lead_id or "unknown"))[:120]
    return os.path.join(_tenant_dir(user_id), f"sdr_learning_{safe}.json")


def _load_json(path: str, default: Any) -> Any:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def _save_json(path: str, payload: Any) -> None:
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def _similarity(a: str, b: str) -> float:
    a = " ".join((a or "").lower().split())
    b = " ".join((b or "").lower().split())
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _emoji_count(text: str) -> int:
    return sum(1 for ch in text or "" if ord(ch) > 0xFFFF or ch in "😀😁😂🤣😊😍😅😉🙂👍🔥🚀✅❌⚡")


def _line_count(text: str) -> int:
    return len([line for line in (text or "").splitlines() if line.strip()])


def _latest_assistant(history: list[dict[str, str]] | None) -> str:
    for item in reversed(history or []):
        if item.get("role") == "assistant" and (item.get("content") or "").strip():
            return item.get("content") or ""
    return ""


def _latest_user(history: list[dict[str, str]] | None) -> str:
    for item in reversed(history or []):
        if item.get("role") == "user" and (item.get("content") or "").strip():
            return item.get("content") or ""
    return ""


def _add_lesson(user_id: int, lesson: dict[str, Any]) -> None:
    path = _learning_path(user_id)
    payload = _load_json(path, {"version": 1, "lessons": [], "updated_at": ""})
    lessons = list(payload.get("lessons") or [])
    key = lesson.get("key") or lesson.get("text")
    for existing in lessons:
        if existing.get("key") == key:
            existing["count"] = int(existing.get("count") or 1) + 1
            existing["updated_at"] = datetime.now().isoformat()
            existing["last_example"] = lesson.get("last_example", existing.get("last_example", ""))
            break
    else:
        lesson = dict(lesson)
        lesson.setdefault("count", 1)
        lesson.setdefault("created_at", datetime.now().isoformat())
        lesson.setdefault("updated_at", datetime.now().isoformat())
        lessons.append(lesson)

    lessons = sorted(lessons, key=lambda x: (int(x.get("score") or 0), int(x.get("count") or 0)), reverse=True)[:80]
    payload["lessons"] = lessons
    payload["updated_at"] = datetime.now().isoformat()
    _save_json(path, payload)


def evaluate_bot_turn(
    *,
    user_id: int,
    lead_id: str,
    agent: str,
    reply: str,
    previous_stage: str,
    next_stage: str,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Evaluate one bot turn and promote reusable lessons when useful."""

    issues: list[str] = []
    last_bot = _latest_assistant(history)
    last_user = _latest_user(history)

    if _similarity(reply, last_bot) >= 0.88:
        issues.append("duplicate_reply")
        _add_lesson(user_id, {
            "key": "avoid_duplicate_reply",
            "agent": agent,
            "score": 8,
            "text": "Before replying, compare with the last assistant message and do not send a near-duplicate.",
            "last_example": reply[:240],
        })

    if len(reply or "") > 360 or _line_count(reply) > 4:
        issues.append("long_message")
        _add_lesson(user_id, {
            "key": "split_long_whatsapp_reply",
            "agent": agent,
            "score": 7,
            "text": "Split long WhatsApp replies into 1-3 short messages; avoid one large paragraph.",
            "last_example": reply[:240],
        })

    if _emoji_count(reply) > 1:
        issues.append("too_many_emojis")
        _add_lesson(user_id, {
            "key": "use_few_emojis",
            "agent": agent,
            "score": 6,
            "text": "Use at most one emoji, and only when it adds warmth.",
            "last_example": reply[:240],
        })

    prev_idx = STAGE_ORDER.get(previous_stage or "", -1)
    next_idx = STAGE_ORDER.get(next_stage or "", prev_idx)
    if prev_idx >= 0 and next_idx >= 0 and next_idx < prev_idx and "?" in last_user:
        issues.append("stage_regression")
        _add_lesson(user_id, {
            "key": "avoid_stage_regression",
            "agent": agent,
            "score": 7,
            "text": "Do not move backwards in the funnel after the lead asks a concrete question; answer and continue.",
            "last_example": f"{previous_stage}->{next_stage}: {reply[:180]}",
        })

    lead_payload = {
        "at": datetime.now().isoformat(),
        "agent": agent,
        "previous_stage": previous_stage,
        "next_stage": next_stage,
        "issues": issues,
        "reply": reply[:800],
    }
    path = _lead_learning_path(user_id, lead_id)
    lead_log = _load_json(path, {"version": 1, "events": []})
    events = list(lead_log.get("events") or [])
    events.append(lead_payload)
    lead_log["events"] = events[-100:]
    lead_log["updated_at"] = datetime.now().isoformat()
    _save_json(path, lead_log)

    return {"issues": issues, "useful": bool(issues)}


def record_human_correction(
    *,
    user_id: int,
    lead_id: str,
    agent: str = "human",
    human_message: str,
    previous_bot_message: str = "",
    context: str = "",
) -> dict[str, Any]:
    """Learn from a human takeover/correction when it differs from the bot."""

    if not (human_message or "").strip():
        return {"learned": False, "reason": "empty_human_message"}

    similarity = _similarity(human_message, previous_bot_message)
    if previous_bot_message and similarity > 0.82:
        return {"learned": False, "reason": "human_message_matches_bot"}

    if len(human_message.strip()) < 8:
        return {"learned": False, "reason": "too_short"}

    lesson_text = (
        "When a human takes over after the bot, compare the human wording with the bot reply. "
        "Prefer the human correction style for similar future contexts."
    )
    if _line_count(human_message) <= 3:
        lesson_text += " Human corrections are often shorter and better split for WhatsApp."

    _add_lesson(user_id, {
        "key": "human_correction_style",
        "agent": agent,
        "score": 10,
        "text": lesson_text,
        "last_example": human_message[:300],
    })

    path = _lead_learning_path(user_id, lead_id)
    lead_log = _load_json(path, {"version": 1, "events": []})
    events = list(lead_log.get("events") or [])
    events.append({
        "at": datetime.now().isoformat(),
        "agent": agent,
        "event": "human_correction",
        "similarity_to_bot": similarity,
        "previous_bot_message": previous_bot_message[:500],
        "human_message": human_message[:800],
        "context": context[:500],
    })
    lead_log["events"] = events[-100:]
    lead_log["updated_at"] = datetime.now().isoformat()
    _save_json(path, lead_log)
    return {"learned": True, "similarity_to_bot": similarity}


def learning_overlay(user_id: int, agent: str = "") -> str:
    """Return compact lessons to inject into the active agent prompt."""

    payload = _load_json(_learning_path(user_id), {"lessons": []})
    lessons = [
        lesson for lesson in payload.get("lessons", [])
        if not agent or lesson.get("agent") in {agent, "human", "", None}
    ][:8]
    lesson_lines = [f"- {lesson.get('text')}" for lesson in lessons if lesson.get("text")]
    if not lesson_lines:
        lesson_lines = ["- No promoted lessons yet; follow the base quality rules."]
    base_lines = [f"- {rule}" for rule in BASE_QUALITY_RULES]
    return "SDR LEARNING MEMORY:\n" + "\n".join(base_lines + lesson_lines)


def format_outgoing_messages(reply: str, max_messages: int = 3) -> list[str]:
    """Split a reply into human WhatsApp-sized chunks."""

    text = " ".join((reply or "").replace("\r", "\n").split())
    if not text:
        return []

    # Reduce emoji noise while preserving at most one.
    kept_emoji = False
    cleaned_chars: list[str] = []
    for ch in text:
        is_emoji = ord(ch) > 0xFFFF or ch in "😀😁😂🤣😊😍😅😉🙂👍🔥🚀✅❌⚡"
        if is_emoji:
            if kept_emoji:
                continue
            kept_emoji = True
        cleaned_chars.append(ch)
    text = "".join(cleaned_chars)

    if len(text) <= 170:
        return [text]

    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if not sentence:
            continue
        candidate = f"{current} {sentence}".strip()
        if len(candidate) <= 180:
            current = candidate
            continue
        if current:
            chunks.append(current)
        current = sentence
        if len(chunks) >= max_messages - 1:
            break
    if current and len(chunks) < max_messages:
        chunks.append(current)
    if not chunks:
        chunks = [text[:220]]
    return chunks[:max_messages]
