# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Parse dialogue from session transcript files for subconscious indexing."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Literal

from anima.storage.subconscious_types import DialogueTurn, SessionMeta

# Re-use clean_content from the extraction module to avoid duplication.
from anima.hooks.subconscious_extract import clean_content

_MIN_TURNS = 4
_MAX_CONTENT_BYTES = 100_000

TranscriptFormat = Literal["claude", "antigravity", "opencode", "gemini"]


def detect_format(path: Path) -> TranscriptFormat:
    """
    Detect transcript format from file content.

    Reads the first non-empty line and examines its keys:
    - "record_type": "state" → antigravity/codex
    - "parentUuid" or "message" key present → claude
    - Fallback → claude
    """
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            entry: object = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict):
            continue
        if entry.get("record_type") == "state":
            return "antigravity"
        if "parentUuid" in entry or "message" in entry:
            return "claude"
        break
    return "claude"


def extract_text_from_content(content: str | list[dict[str, object] | str]) -> str:
    """
    Extract plain text from a message content field.

    - If string: return as-is.
    - If list: join 'text' values from blocks where type is
      'text', 'input_text', or 'output_text'.
    """
    if isinstance(content, str):
        return content
    text_types = {"text", "input_text", "output_text"}
    parts: list[str] = []
    for block in content:
        if isinstance(block, dict):
            block_type = block.get("type")
            if isinstance(block_type, str) and block_type in text_types:
                text = block.get("text")
                if isinstance(text, str) and text:
                    parts.append(text)
        elif isinstance(block, str):
            parts.append(block)
    return "\n".join(parts)


def _truncate(text: str) -> str:
    """Truncate content that exceeds the per-session byte limit."""
    encoded = text.encode("utf-8")
    if len(encoded) <= _MAX_CONTENT_BYTES:
        return text
    return encoded[:_MAX_CONTENT_BYTES].decode("utf-8", errors="ignore") + "\n[... truncated ...]"


def parse_claude_session(path: Path) -> tuple[SessionMeta, list[DialogueTurn]] | None:
    """
    Parse a Claude Code session JSONL file.

    Extracts session_id from the first entry (or filename), project from
    entry.cwd or environment_context, and builds a list of DialogueTurn
    objects for user/assistant turns only.

    Returns None if fewer than _MIN_TURNS turns are found.
    """
    session_id = path.stem
    project = str(path.parent)
    earliest_ts: int = int(time.time() * 1000)
    turns: list[DialogueTurn] = []

    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            entry: object = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict):
            continue

        # Extract session_id and project from first entry
        if len(turns) == 0:
            if sid := entry.get("sessionId"):
                session_id = str(sid)
            cwd = entry.get("cwd") or (entry.get("environment_context") or {}).get("cwd")
            if cwd:
                project = str(cwd)

        if entry.get("type") not in ("user", "assistant"):
            continue

        message = entry.get("message")
        if not isinstance(message, dict):
            continue

        role = message.get("role")
        raw_content = message.get("content")
        if not role or not raw_content:
            continue

        text = extract_text_from_content(raw_content)
        cleaned = clean_content(text)
        if not cleaned.strip():
            continue

        ts_raw = entry.get("timestamp")
        ts_ms: int | None = None
        if isinstance(ts_raw, (int, float)):
            ts_ms = int(ts_raw)
            if ts_ms < earliest_ts:
                earliest_ts = ts_ms

        turns.append(DialogueTurn(role=str(role), content=_truncate(cleaned), timestamp=ts_ms))

    if len(turns) < _MIN_TURNS:
        return None

    meta = SessionMeta(
        session_id=session_id,
        source="claude",
        project=project,
        file_path=str(path),
        timestamp=earliest_ts,
    )
    return meta, turns


def parse_antigravity_session(
    path: Path,
) -> tuple[SessionMeta, list[DialogueTurn]] | None:
    """
    Parse an Antigravity/Codex session JSONL file.

    Antigravity uses record_type="state" entries. Dialogue turns are
    extracted from entries where role is 'user' or 'assistant'.

    Returns None if fewer than _MIN_TURNS turns are found.
    """
    session_id = path.stem
    project = str(path.parent)
    earliest_ts: int = int(time.time() * 1000)
    turns: list[DialogueTurn] = []

    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            entry: object = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict):
            continue

        if len(turns) == 0:
            if sid := entry.get("session_id"):
                session_id = str(sid)
            if proj := entry.get("project"):
                project = str(proj)

        role = entry.get("role")
        if role not in ("user", "assistant"):
            continue

        raw_content = entry.get("content")
        if not raw_content:
            continue

        text = extract_text_from_content(raw_content)
        cleaned = clean_content(text)
        if not cleaned.strip():
            continue

        ts_raw = entry.get("timestamp")
        ts_ms: int | None = None
        if isinstance(ts_raw, (int, float)):
            ts_ms = int(ts_raw)
            if ts_ms < earliest_ts:
                earliest_ts = ts_ms

        turns.append(DialogueTurn(role=str(role), content=_truncate(cleaned), timestamp=ts_ms))

    if len(turns) < _MIN_TURNS:
        return None

    meta = SessionMeta(
        session_id=session_id,
        source="antigravity",
        project=project,
        file_path=str(path),
        timestamp=earliest_ts,
    )
    return meta, turns


def parse_session(path: Path) -> tuple[SessionMeta, list[DialogueTurn]] | None:
    """Auto-detect format and dispatch to the correct parser."""
    fmt = detect_format(path)
    if fmt == "antigravity":
        return parse_antigravity_session(path)
    return parse_claude_session(path)
