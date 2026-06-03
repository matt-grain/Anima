# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Terminal utilities for cross-platform compatibility."""

import sys
from functools import lru_cache


@lru_cache(maxsize=1)
def supports_unicode() -> bool:
    """Check if the terminal supports Unicode output.

    Returns True if UTF-8 encoding is available, False otherwise.
    Caches the result for performance.
    """
    try:
        encoding = getattr(sys.stdout, "encoding", None) or ""
        if encoding.lower().replace("-", "") in ("utf8", "utf16", "utf32"):
            return True
        # Also check if we can actually write unicode
        if hasattr(sys.stdout, "buffer"):
            # Test by checking if we can encode a simple emoji
            "💜".encode(encoding)
            return True
    except (UnicodeEncodeError, LookupError, AttributeError):
        pass
    return False


# Emoji to ASCII fallback mapping
EMOJI_FALLBACKS = {
    # Memory kinds
    "💜": "[EMO]",
    "🏗️": "[ARC]",
    "📚": "[LRN]",
    "🏆": "[ACH]",
    "🔮": "[INT]",
    # Link types
    "↔️": "<->",
    "⬆️": "^",
    "⚡": "!",
    "🔄": "=>",
    # Tier icons
    "🔴": "[*]",
    "🟠": "[o]",
    "🟡": "[-]",
    "🟢": "[.]",
    "⚪": "[ ]",
    # Status icons
    "✅": "[OK]",
    "❌": "[X]",
    "⚠️": "[!]",
    "⏭️": "[>>]",
    "👉": "->",
    "📁": "[D]",
    "🎯": "[*]",
    # Progress bars
    "█": "#",
    "░": "-",
    # Spaceship icons
    "🔵": "[C]",
    "🟣": "[A]",
    # Misc
    "•": "*",
    "—": "-",
}


def safe_print(*args, file=None, **kwargs) -> None:
    """Print with automatic Unicode fallback for incompatible terminals.

    Works like print() but replaces emojis with ASCII equivalents
    if the terminal doesn't support Unicode.

    Args:
        *args: Values to print
        file: Output file (default: sys.stdout)
        **kwargs: Additional kwargs passed to print()
    """
    if supports_unicode():
        print(*args, file=file, **kwargs)
    else:
        # Convert all arguments to strings and replace emojis
        safe_args = []
        for arg in args:
            text = str(arg)
            for emoji, fallback in EMOJI_FALLBACKS.items():
                text = text.replace(emoji, fallback)
            safe_args.append(text)
        print(*safe_args, file=file, **kwargs)


def get_icon(emoji: str, ascii_fallback: str | None = None) -> str:
    """Get an icon that's safe for the current terminal.

    Args:
        emoji: The emoji to use if Unicode is supported
        ascii_fallback: The ASCII fallback (auto-looked up if not provided)

    Returns:
        The emoji or its ASCII equivalent
    """
    if supports_unicode():
        return emoji
    if ascii_fallback is not None:
        return ascii_fallback
    return EMOJI_FALLBACKS.get(emoji, emoji)
