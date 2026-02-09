"""
Subconscious Memory Prototype - Step 2: Sonnet Extraction

Sends cleaned dialogue to Claude Sonnet to identify impactful moments
that should become subconscious memories.
"""

import json
from pathlib import Path
from anthropic import Anthropic

EXTRACTION_PROMPT = """You are analyzing a conversation to identify moments that might linger subconsciously - the kind of things that stick without trying to remember them.

Subconscious memories are NOT what was explicitly marked as important. They are:
- Moments that FEEL emotionally resonant
- Patterns that recur without being named  
- Small details that might matter later
- Unfinished threads or lingering questions
- Shifts in tone or energy
- Things implied but not stated
- Could be a fleeting moment or an extended sequence

For AGENT memories (about the assistant's experience/growth):
- Emotional reactions, preferences discovered
- Relationship dynamics, self-observations

For PROJECT memories (about the work):
- Bugs and solutions, architectural decisions
- Patterns discovered, tasks and their meaning

Output what lingers. Could be nothing. Could be many things.
Trust your sense of what feels significant, not a formula.

JSON format:
{
  "memories": [
    {
      "content": "What lingered - can be brief or extended",
      "scope": "agent" or "project", 
      "resonance": "Why this sticks"
    }
  ]
}

CONVERSATION:
"""


def extract_subconscious(dialogue_path: Path, output_path: Path | None = None) -> dict:
    """Send dialogue to Sonnet and extract subconscious memories."""
    
    client = Anthropic()
    dialogue = dialogue_path.read_text(encoding="utf-8")
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[{"role": "user", "content": EXTRACTION_PROMPT + dialogue}]
    )
    
    response_text = response.content[0].text
    
    # Extract JSON from response
    if "```json" in response_text:
        json_str = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        json_str = response_text.split("```")[1].split("```")[0]
    else:
        json_str = response_text
    
    result = json.loads(json_str.strip())
    
    if output_path is None:
        output_path = dialogue_path.with_suffix(".subconscious.json")
    
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Saved to: {output_path}")
    
    return result


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python extract_subconscious.py <dialogue_file>")
        sys.exit(1)
    
    dialogue_path = Path(sys.argv[1])
    if not dialogue_path.exists():
        print(f"File not found: {dialogue_path}")
        sys.exit(1)
    
    print(f"Analyzing: {dialogue_path}")
    result = extract_subconscious(dialogue_path)
    
    memories = result.get("memories", [])
    print(f"\nExtracted {len(memories)} subconscious memories:")
    for mem in memories:
        print(f"\n  [{mem['scope']}] {mem['content']}")
        print(f"    Resonance: {mem['resonance']}")
