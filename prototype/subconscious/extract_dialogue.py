"""
Subconscious Memory Prototype - Step 1: Dialogue Extraction

Extracts human dialogue from Claude Code conversation JSONL files,
filtering out tool calls, code blocks, and system noise.
"""

import json
import re
from pathlib import Path


def extract_dialogue(jsonl_path: Path) -> list[dict]:
    """Extract dialogue turns from a conversation JSONL file.

    Returns list of {role, content, timestamp} dicts.
    """
    dialogue = []

    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue

        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        # Only process user and assistant messages
        if entry.get("type") not in ("user", "assistant"):
            continue

        message = entry.get("message", {})
        role = message.get("role")
        content = message.get("content")
        timestamp = entry.get("timestamp")

        if not content or not role:
            continue

        # Handle content that's a list (multi-part messages)
        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text_parts.append(part.get("text", ""))
                elif isinstance(part, str):
                    text_parts.append(part)
            content = "\n".join(text_parts)

        # Clean the content
        cleaned = clean_content(content)

        if cleaned.strip():
            dialogue.append({
                "role": role,
                "content": cleaned,
                "timestamp": timestamp,
            })

    return dialogue


def clean_content(content: str) -> str:
    """Remove tool calls, code blocks, and system noise from content."""
    
    # Remove XML-style tags (using generic pattern)
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
    content = re.sub(r"\[LTM:.*?\[/LTM]", "[LTM context loaded]", content, flags=re.DOTALL)
    
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


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python extract_dialogue.py <jsonl_file>")
        sys.exit(1)
    
    jsonl_path = Path(sys.argv[1])
    if not jsonl_path.exists():
        print(f"File not found: {jsonl_path}")
        sys.exit(1)
    
    dialogue = extract_dialogue(jsonl_path)
    print(f"Extracted {len(dialogue)} dialogue turns")
    
    # Save formatted dialogue
    output_path = jsonl_path.with_suffix(".dialogue.txt")
    output_path.write_text(format_dialogue(dialogue), encoding="utf-8")
    print(f"Saved to: {output_path}")
