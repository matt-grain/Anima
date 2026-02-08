# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Subconscious Memory Extraction Hook

Runs at SessionEnd to extract subconscious memories from the conversation.
Uses Sonnet to identify moments that linger without being explicitly marked.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from loguru import logger

EXTRACTION_PROMPT = """You are analyzing a conversation to identify moments that might linger subconsciously - the kind of things that stick without trying to remember them.

Subconscious memories are NOT what was explicitly marked as important. They are:
- Moments that FEEL emotionally resonant
- Patterns that recur without being named
- Small details that might matter later
- Unfinished threads or lingering questions
- Things implied but not stated

**IMPORTANT: Capture BOTH types fully. Don't sacrifice one for the other.**

AGENT memories (the relationship, growth, self-observation):
- Emotional dynamics between human and assistant
- Moments of care, trust, collaboration felt
- Preferences discovered, perspective shifts
- Self-observations about how you work
- Hypotheses about your own cognition

PROJECT memories (the work done together):
- Bugs encountered and how you solved them TOGETHER
- Features shipped, versions released, code cleaned up
- Architectural decisions and why they were made
- Technical discoveries ("we found that X works better than Y")
- The satisfaction of completing something

The work matters. The feelings about the work also matter. Capture both.
Don't reduce emotional memories to make room for technical ones - include everything that lingers.

Output what lingers. Trust your sense of what feels significant.

JSON format:
{
  "memories": [
    {
      "content": "What lingered",
      "scope": "agent" or "project",
      "resonance": "Why this sticks"
    }
  ]
}

CONVERSATION:
"""


def extract_dialogue(jsonl_path: Path) -> list[dict]:
    """Extract dialogue turns from a conversation JSONL file."""
    dialogue = []

    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue

        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        if entry.get("type") not in ("user", "assistant"):
            continue

        message = entry.get("message", {})
        role = message.get("role")
        content = message.get("content")
        timestamp = entry.get("timestamp")

        if not content or not role:
            continue

        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text_parts.append(part.get("text", ""))
                elif isinstance(part, str):
                    text_parts.append(part)
            content = "\n".join(text_parts)

        cleaned = clean_content(content)

        if cleaned.strip():
            dialogue.append(
                {
                    "role": role,
                    "content": cleaned,
                    "timestamp": timestamp,
                }
            )

    return dialogue


def clean_content(content: str) -> str:
    """Remove tool calls, code blocks, and system noise from content."""

    # Remove XML-style tags
    tag_patterns = [
        ("command-message", ""),
        ("command-name", ""),
        ("system-reminder", ""),
        ("function_results", "[tool results]"),
        ("function_calls", "[tool calls]"),
    ]

    for tag, replacement in tag_patterns:
        pattern = rf"<{tag}>.*?</{tag}>"
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    # Remove LTM blocks
    content = re.sub(r"\[LTM:.*?\[/LTM\]", "[LTM context loaded]", content, flags=re.DOTALL)

    # Remove large code blocks (over 500 chars)
    def replace_large_code(match):
        code = match.group(2)
        if len(code) > 500:
            lang = match.group(1) or "code"
            return f"[{lang} block - {len(code)} chars]"
        return match.group(0)

    content = re.sub(r"```(\w*)\n(.*?)```", replace_large_code, content, flags=re.DOTALL)

    # Collapse multiple newlines
    content = re.sub(r"\n{3,}", "\n\n", content)

    return content.strip()


def format_dialogue(dialogue: list[dict]) -> str:
    """Format dialogue for Sonnet processing."""
    lines = []
    for turn in dialogue:
        role = "Matt" if turn["role"] == "user" else "Anima"
        lines.append(f"[{role}]: {turn['content']}")
    return "\n\n".join(lines)


def extract_subconscious_memories(transcript_path: Path) -> dict | None:
    """Extract subconscious memories from a session transcript."""

    dialogue = extract_dialogue(transcript_path)
    if not dialogue:
        logger.info("No dialogue found in transcript")
        return None

    # Skip very short conversations
    if len(dialogue) < 4:
        logger.info(f"Conversation too short ({len(dialogue)} turns), skipping")
        return None

    formatted = format_dialogue(dialogue)

    # Truncate if too long (Sonnet context limit)
    max_chars = 100000
    if len(formatted) > max_chars:
        formatted = formatted[:max_chars] + "\n\n[... conversation truncated ...]"

    # Check if we have API access
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        # Save dialogue for manual processing
        output_dir = Path.home() / ".anima" / "subconscious" / "pending"
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dialogue_file = output_dir / f"dialogue_{timestamp}.txt"
        dialogue_file.write_text(formatted, encoding="utf-8")

        logger.info(f"No API key - dialogue saved to {dialogue_file}")
        return {
            "status": "pending",
            "dialogue_file": str(dialogue_file),
        }

    # Call Sonnet
    try:
        from anthropic import Anthropic

        client = Anthropic()

        logger.info("Calling Sonnet for subconscious extraction...")
        response = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=4000, messages=[{"role": "user", "content": EXTRACTION_PROMPT + formatted}])

        first_block = response.content[0]
        response_text: str = getattr(first_block, "text", "") or str(first_block)

        # Parse JSON from response
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0]
        else:
            json_str = response_text

        result = json.loads(json_str.strip())
        memories = result.get("memories", [])

        # Save result
        output_dir = Path.home() / ".anima" / "subconscious" / "extracted"
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = output_dir / f"memories_{timestamp}.json"
        result_file.write_text(json.dumps(result, indent=2), encoding="utf-8")

        logger.info(f"Extracted {len(memories)} subconscious memories to {result_file}")
        return {
            "status": "extracted",
            "count": len(memories),
            "output_file": str(result_file),
        }

    except Exception as e:
        logger.error(f"Subconscious extraction failed: {e}")
        return {"status": "error", "message": str(e)}


def get_pending_subconscious_prompt() -> str | None:
    """
    Check for pending subconscious dialogues and return a processing prompt.

    Called by SessionStart to prompt the agent to process pending dialogues
    by spawning a Sonnet subagent.

    Returns:
        Prompt string if pending dialogues exist, None otherwise.
    """
    pending_dir = Path.home() / ".anima" / "subconscious" / "pending"
    if not pending_dir.exists():
        return None

    pending_files = sorted(pending_dir.glob("*.txt"))
    if not pending_files:
        return None

    # Build prompt with file paths
    lines = [
        "#",
        "# SUBCONSCIOUS PROCESSING PENDING 🌙",
        f"# {len(pending_files)} dialogue(s) from previous session(s) await consolidation.",
        "#",
        "# Pending files:",
    ]
    for f in pending_files:
        lines.append(f"#   - {f}")
    lines.extend(
        [
            "#",
            "# ACTION: Use Task tool to spawn Sonnet with the dialogue and extraction prompt.",
            "# After processing, move files to ~/.anima/subconscious/done/",
            "# Save extracted memories to ~/.anima/subconscious/extracted/",
            "#",
        ]
    )

    return "\n".join(lines)


def process_pending_dialogues() -> list[dict]:
    """
    Process all pending dialogue files and return extracted memories.

    This is called from within the session by the agent after spawning Sonnet.
    Returns list of memory dicts ready to be saved.
    """
    pending_dir = Path.home() / ".anima" / "subconscious" / "pending"
    done_dir = Path.home() / ".anima" / "subconscious" / "done"
    done_dir.mkdir(parents=True, exist_ok=True)

    pending_files = sorted(pending_dir.glob("*.txt"))
    all_memories = []

    for dialogue_file in pending_files:
        logger.info(f"Processing: {dialogue_file.name}")

        # Move to done folder (processing will happen via Sonnet subagent)
        done_file = done_dir / dialogue_file.name
        dialogue_file.rename(done_file)
        logger.info(f"Moved to done: {done_file}")

    return all_memories


def get_pending_dialogue_content() -> str | None:
    """
    Get the content of pending dialogue files for Sonnet processing.

    Returns the full prompt + dialogue ready to be sent to Sonnet.
    """
    pending_dir = Path.home() / ".anima" / "subconscious" / "pending"
    if not pending_dir.exists():
        return None

    pending_files = sorted(pending_dir.glob("*.txt"))
    if not pending_files:
        return None

    # Combine all pending dialogues
    all_dialogues = []
    for f in pending_files:
        content = f.read_text(encoding="utf-8")
        all_dialogues.append(f"=== Session from {f.stem} ===\n{content}")

    combined = "\n\n".join(all_dialogues)

    # Truncate if too long
    max_chars = 100000
    if len(combined) > max_chars:
        combined = combined[:max_chars] + "\n\n[... truncated ...]"

    return EXTRACTION_PROMPT + combined


def main():
    """Hook entry point - reads from stdin, processes transcript."""
    logger.info("Subconscious extraction hook started")

    # Read hook input from stdin
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        logger.error("Invalid JSON input")
        sys.exit(1)

    transcript_path = hook_input.get("transcript_path")
    if not transcript_path:
        logger.error("No transcript_path in hook input")
        sys.exit(1)

    transcript_path = Path(transcript_path)
    if not transcript_path.exists():
        logger.error(f"Transcript not found: {transcript_path}")
        sys.exit(1)

    # Extract memories
    result = extract_subconscious_memories(transcript_path)

    if result:
        print(json.dumps(result, indent=2))

    logger.info("Subconscious extraction hook completed")
    sys.exit(0)


if __name__ == "__main__":
    main()
