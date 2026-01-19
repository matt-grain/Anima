# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Memory signing and verification using HMAC-SHA256.

Provides tamper detection for memories when agents have signing keys.
If an agent has no signing key, memories are created without signatures
and verification is skipped.
"""

import hmac
import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from anima.core.memory import Memory
    from anima.core.agent import Agent


def _get_signing_payload(memory: "Memory") -> bytes:
    """
    Create the canonical payload for signing.

    Includes fields that shouldn't change after creation:
    - id, agent_id, region, project_id, kind
    - original_content (not content, which may compact)
    - impact, created_at
    """
    parts = [
        memory.id,
        memory.agent_id,
        memory.region.value,
        memory.project_id or "",
        memory.kind.value,
        memory.original_content,
        memory.impact.value,
        memory.created_at.isoformat() if memory.created_at else "",
    ]
    return "|".join(parts).encode("utf-8")


def sign_memory(memory: "Memory", signing_key: str) -> str:
    """
    Sign a memory using HMAC-SHA256.

    Args:
        memory: The memory to sign
        signing_key: The agent's signing key (base64 or plain string)

    Returns:
        Hex-encoded signature string
    """
    payload = _get_signing_payload(memory)
    key_bytes = signing_key.encode("utf-8")
    signature = hmac.new(key_bytes, payload, hashlib.sha256)
    return signature.hexdigest()


def verify_signature(memory: "Memory", signing_key: str) -> bool:
    """
    Verify a memory's signature.

    Args:
        memory: The memory to verify
        signing_key: The agent's signing key

    Returns:
        True if signature is valid, False otherwise
    """
    if not memory.signature:
        return False

    expected = sign_memory(memory, signing_key)
    return hmac.compare_digest(memory.signature, expected)


def should_sign(agent: "Agent") -> bool:
    """Check if an agent requires memory signing."""
    return agent.signing_key is not None and agent.signing_key != ""


def should_verify(memory: "Memory", agent: "Agent") -> bool:
    """
    Check if a memory should be verified.

    Only verify if:
    - Agent has a signing key
    - Memory has a signature
    """
    return should_sign(agent) and memory.signature is not None
