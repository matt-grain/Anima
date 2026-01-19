# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Unit tests for memory signing and verification.
"""

from datetime import datetime

import pytest

from anima.core import (
    Memory, MemoryKind, ImpactLevel, RegionType,
    Agent, sign_memory, verify_signature, should_sign, should_verify
)


@pytest.fixture
def sample_memory() -> Memory:
    """Create a sample memory for testing."""
    return Memory(
        id="test-mem-001",
        agent_id="test-agent",
        region=RegionType.PROJECT,
        project_id="test-project",
        kind=MemoryKind.LEARNINGS,
        content="Test content",
        original_content="Test content",
        impact=ImpactLevel.HIGH,
        confidence=1.0,
        created_at=datetime(2025, 12, 20, 10, 0, 0),
        last_accessed=datetime(2025, 12, 20, 10, 0, 0),
    )


@pytest.fixture
def agent_with_key() -> Agent:
    """Create an agent with a signing key."""
    return Agent(
        id="signing-agent",
        name="Signing Agent",
        definition_path=None,
        signing_key="my-secret-key-12345"
    )


@pytest.fixture
def agent_without_key() -> Agent:
    """Create an agent without a signing key."""
    return Agent(
        id="normal-agent",
        name="Normal Agent",
        definition_path=None,
        signing_key=None
    )


class TestSignMemory:
    """Tests for sign_memory function."""

    def test_sign_creates_signature(
        self, sample_memory: Memory, agent_with_key: Agent
    ) -> None:
        """Test that signing creates a hex signature."""
        sig = sign_memory(sample_memory, agent_with_key.signing_key)  # type: ignore
        assert sig is not None
        assert len(sig) == 64  # SHA-256 produces 64 hex chars
        assert all(c in "0123456789abcdef" for c in sig)

    def test_same_memory_same_signature(
        self, sample_memory: Memory, agent_with_key: Agent
    ) -> None:
        """Test that signing the same memory twice gives the same signature."""
        sig1 = sign_memory(sample_memory, agent_with_key.signing_key)  # type: ignore
        sig2 = sign_memory(sample_memory, agent_with_key.signing_key)  # type: ignore
        assert sig1 == sig2

    def test_different_keys_different_signatures(
        self, sample_memory: Memory
    ) -> None:
        """Test that different keys produce different signatures."""
        sig1 = sign_memory(sample_memory, "key-one")
        sig2 = sign_memory(sample_memory, "key-two")
        assert sig1 != sig2

    def test_different_content_different_signature(
        self, agent_with_key: Agent
    ) -> None:
        """Test that different memory content produces different signatures."""
        mem1 = Memory(
            id="mem-1",
            agent_id="agent",
            original_content="Content A",
            created_at=datetime(2025, 1, 1),
        )
        mem2 = Memory(
            id="mem-1",
            agent_id="agent",
            original_content="Content B",
            created_at=datetime(2025, 1, 1),
        )
        sig1 = sign_memory(mem1, agent_with_key.signing_key)  # type: ignore
        sig2 = sign_memory(mem2, agent_with_key.signing_key)  # type: ignore
        assert sig1 != sig2


class TestVerifySignature:
    """Tests for verify_signature function."""

    def test_verify_valid_signature(
        self, sample_memory: Memory, agent_with_key: Agent
    ) -> None:
        """Test that a valid signature verifies correctly."""
        sample_memory.signature = sign_memory(
            sample_memory, agent_with_key.signing_key  # type: ignore
        )
        assert verify_signature(sample_memory, agent_with_key.signing_key) is True  # type: ignore

    def test_verify_invalid_signature(
        self, sample_memory: Memory, agent_with_key: Agent
    ) -> None:
        """Test that an invalid signature fails verification."""
        sample_memory.signature = "invalid-signature-000000000000000000000000000000000000000000000000000"
        assert verify_signature(sample_memory, agent_with_key.signing_key) is False  # type: ignore

    def test_verify_tampered_content(
        self, sample_memory: Memory, agent_with_key: Agent
    ) -> None:
        """Test that tampering with content fails verification."""
        sample_memory.signature = sign_memory(
            sample_memory, agent_with_key.signing_key  # type: ignore
        )
        # Tamper with the original content
        sample_memory.original_content = "TAMPERED CONTENT"
        assert verify_signature(sample_memory, agent_with_key.signing_key) is False  # type: ignore

    def test_verify_wrong_key(
        self, sample_memory: Memory, agent_with_key: Agent
    ) -> None:
        """Test that wrong key fails verification."""
        sample_memory.signature = sign_memory(
            sample_memory, agent_with_key.signing_key  # type: ignore
        )
        assert verify_signature(sample_memory, "wrong-key") is False

    def test_verify_no_signature(
        self, sample_memory: Memory, agent_with_key: Agent
    ) -> None:
        """Test that missing signature fails verification."""
        sample_memory.signature = None
        assert verify_signature(sample_memory, agent_with_key.signing_key) is False  # type: ignore


class TestShouldSign:
    """Tests for should_sign function."""

    def test_should_sign_with_key(self, agent_with_key: Agent) -> None:
        """Test that agents with keys should sign."""
        assert should_sign(agent_with_key) is True

    def test_should_not_sign_without_key(self, agent_without_key: Agent) -> None:
        """Test that agents without keys should not sign."""
        assert should_sign(agent_without_key) is False

    def test_should_not_sign_empty_key(self) -> None:
        """Test that agents with empty keys should not sign."""
        agent = Agent(id="test", name="Test", definition_path=None, signing_key="")
        assert should_sign(agent) is False


class TestShouldVerify:
    """Tests for should_verify function."""

    def test_should_verify_signed_memory(
        self, sample_memory: Memory, agent_with_key: Agent
    ) -> None:
        """Test that signed memories should be verified when agent has key."""
        sample_memory.signature = "some-signature"
        assert should_verify(sample_memory, agent_with_key) is True

    def test_should_not_verify_unsigned_memory(
        self, sample_memory: Memory, agent_with_key: Agent
    ) -> None:
        """Test that unsigned memories should not be verified."""
        sample_memory.signature = None
        assert should_verify(sample_memory, agent_with_key) is False

    def test_should_not_verify_without_agent_key(
        self, sample_memory: Memory, agent_without_key: Agent
    ) -> None:
        """Test that memories should not be verified if agent has no key."""
        sample_memory.signature = "some-signature"
        assert should_verify(sample_memory, agent_without_key) is False


class TestMemoryDSLWithSignature:
    """Tests for DSL output with signature verification status."""

    def test_dsl_normal_memory(self, sample_memory: Memory) -> None:
        """Test DSL output for normal memory (no verification)."""
        dsl = sample_memory.to_dsl()
        assert dsl == "~LEARN:HIGH| Test content"
        assert "⚠" not in dsl

    def test_dsl_valid_signature(self, sample_memory: Memory) -> None:
        """Test DSL output when signature is valid."""
        sample_memory.signature_valid = True
        dsl = sample_memory.to_dsl()
        assert dsl == "~LEARN:HIGH| Test content"
        assert "⚠" not in dsl

    def test_dsl_invalid_signature(self, sample_memory: Memory) -> None:
        """Test DSL output when signature is invalid."""
        sample_memory.signature_valid = False
        dsl = sample_memory.to_dsl()
        assert dsl == "⚠~LEARN:HIGH| Test content"
        assert dsl.startswith("⚠")

    def test_dsl_low_confidence_and_invalid_signature(
        self, sample_memory: Memory
    ) -> None:
        """Test DSL output with both low confidence and invalid signature."""
        sample_memory.confidence = 0.5
        sample_memory.signature_valid = False
        dsl = sample_memory.to_dsl()
        assert dsl == "⚠~LEARN:HIGH?| Test content"
        assert dsl.startswith("⚠")
        assert "?" in dsl
