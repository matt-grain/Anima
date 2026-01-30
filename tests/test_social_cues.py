# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Tests for social cue detection (Phase 3B)."""

from anima.lifecycle.social_cues import (
    SocialCueType,
    SocialCue,
    detect_social_cue,
    detect_all_social_cues,
    extract_recall_query,
    requires_recall,
)


class TestDetectSharedDiscussion:
    """Tests for detecting shared discussion cues."""

    def test_as_we_discussed(self):
        """Detect 'as we discussed X' pattern."""
        cue = detect_social_cue("As we discussed, the API should use REST.")
        assert cue is not None
        assert cue.cue_type == SocialCueType.SHARED_DISCUSSION
        assert "api" in cue.topic.lower()

    def test_we_talked_about(self):
        """Detect 'we talked about X' pattern."""
        cue = detect_social_cue("We talked about caching strategies yesterday.")
        assert cue is not None
        assert cue.cue_type == SocialCueType.SHARED_DISCUSSION
        assert "caching" in cue.topic.lower()

    def test_when_we_discussed(self):
        """Detect question about discussion."""
        cue = detect_social_cue("When we discussed authentication?")
        assert cue is not None
        assert cue.is_question is True


class TestDetectAgentStatement:
    """Tests for detecting references to what the agent said."""

    def test_you_mentioned(self):
        """Detect 'you mentioned X' pattern."""
        cue = detect_social_cue("You mentioned something about error handling.")
        assert cue is not None
        assert cue.cue_type == SocialCueType.AGENT_STATEMENT
        assert "error handling" in cue.topic.lower()

    def test_you_said(self):
        """Detect 'you said X' pattern."""
        cue = detect_social_cue("You said the tests should be comprehensive.")
        assert cue is not None
        assert cue.cue_type == SocialCueType.AGENT_STATEMENT

    def test_like_you_suggested(self):
        """Detect 'like you suggested' pattern."""
        cue = detect_social_cue("Like you suggested, I added logging.")
        assert cue is not None
        assert cue.cue_type == SocialCueType.AGENT_STATEMENT

    def test_what_did_you_say(self):
        """Detect question about what agent said."""
        cue = detect_social_cue("What did you say about the database schema?")
        assert cue is not None
        assert cue.cue_type == SocialCueType.AGENT_STATEMENT
        assert cue.is_question is True


class TestDetectSharedDecision:
    """Tests for detecting shared decision cues."""

    def test_we_agreed(self):
        """Detect 'we agreed X' pattern."""
        cue = detect_social_cue("We agreed that JWT would be the auth method.")
        assert cue is not None
        assert cue.cue_type == SocialCueType.SHARED_DECISION
        assert "jwt" in cue.topic.lower()

    def test_we_decided(self):
        """Detect 'we decided X' pattern."""
        cue = detect_social_cue("We decided to use SQLite for storage.")
        assert cue is not None
        assert cue.cue_type == SocialCueType.SHARED_DECISION

    def test_the_decision_about(self):
        """Detect 'the decision about X' pattern."""
        cue = detect_social_cue("The decision about the API versioning.")
        assert cue is not None
        assert cue.cue_type == SocialCueType.SHARED_DECISION


class TestDetectCollaborativeWork:
    """Tests for detecting collaborative work cues."""

    def test_we_built(self):
        """Detect 'we built X' pattern."""
        cue = detect_social_cue("We built the memory system together.")
        assert cue is not None
        assert cue.cue_type == SocialCueType.COLLABORATIVE_WORK
        assert "memory system" in cue.topic.lower()

    def test_we_implemented(self):
        """Detect 'we implemented X' pattern."""
        cue = detect_social_cue("We implemented tiered loading.")
        assert cue is not None
        assert cue.cue_type == SocialCueType.COLLABORATIVE_WORK

    def test_when_we_worked_on(self):
        """Detect question about work."""
        cue = detect_social_cue("When we worked on the embeddings?")
        assert cue is not None
        assert cue.cue_type == SocialCueType.COLLABORATIVE_WORK
        assert cue.is_question is True


class TestDetectExplicitRecall:
    """Tests for detecting explicit recall requests."""

    def test_remember_when(self):
        """Detect 'remember when' pattern."""
        cue = detect_social_cue("Remember when we added semantic search?")
        assert cue is not None
        assert cue.cue_type == SocialCueType.EXPLICIT_RECALL

    def test_do_you_recall(self):
        """Detect 'do you recall' pattern."""
        cue = detect_social_cue("Do you recall the discussion about hooks?")
        assert cue is not None
        assert cue.cue_type == SocialCueType.EXPLICIT_RECALL

    def test_can_you_remind_me(self):
        """Detect 'remind me' pattern."""
        cue = detect_social_cue("Can you remind me about the architecture?")
        assert cue is not None
        assert cue.cue_type == SocialCueType.EXPLICIT_RECALL
        assert "architecture" in cue.topic.lower()


class TestNoSocialCue:
    """Tests for messages without social cues."""

    def test_technical_question(self):
        """Technical questions shouldn't trigger."""
        cue = detect_social_cue("How do I implement authentication?")
        assert cue is None

    def test_command(self):
        """Commands shouldn't trigger."""
        cue = detect_social_cue("Please add error handling to this function.")
        assert cue is None

    def test_simple_statement(self):
        """Simple statements shouldn't trigger."""
        cue = detect_social_cue("The code looks good.")
        assert cue is None


class TestDetectAllCues:
    """Tests for detecting multiple cues."""

    def test_multiple_cue_types(self):
        """Detect different cue types in one message."""
        text = "We discussed caching. You mentioned the API."
        cues = detect_all_social_cues(text)
        cue_types = {c.cue_type for c in cues}
        assert SocialCueType.SHARED_DISCUSSION in cue_types
        assert SocialCueType.AGENT_STATEMENT in cue_types

    def test_single_cue_returned_first(self):
        """First matching cue should be returned by detect_social_cue."""
        text = "We discussed caching. You mentioned the API."
        cue = detect_social_cue(text)
        assert cue is not None
        # First pattern that matches wins
        assert cue.cue_type == SocialCueType.SHARED_DISCUSSION


class TestExtractRecallQuery:
    """Tests for extracting search queries from cues."""

    def test_extract_topic(self):
        """Extract topic as query."""
        cue = SocialCue(
            cue_type=SocialCueType.SHARED_DISCUSSION,
            original_text="we discussed caching",
            topic="caching strategies",
        )
        query = extract_recall_query(cue)
        assert query == "caching strategies"

    def test_no_topic(self):
        """Handle cue without topic."""
        cue = SocialCue(
            cue_type=SocialCueType.SHARED_DISCUSSION,
            original_text="as we discussed",
            topic=None,
        )
        query = extract_recall_query(cue)
        assert query is None


class TestRequiresRecall:
    """Tests for quick recall check."""

    def test_discussion_requires_recall(self):
        """Discussion references need recall."""
        assert requires_recall("As we discussed earlier") is True

    def test_agent_statement_requires_recall(self):
        """Agent statement references need recall."""
        assert requires_recall("You mentioned the API") is True

    def test_simple_code_no_recall(self):
        """Simple code changes don't need recall."""
        assert requires_recall("Add a new function here") is False

    def test_question_no_recall(self):
        """Technical questions don't need recall."""
        assert requires_recall("What is a decorator?") is False


class TestTopicCleaning:
    """Tests for topic extraction and cleaning."""

    def test_removes_trailing_punctuation(self):
        """Topic should have trailing punctuation removed."""
        cue = detect_social_cue("We discussed the architecture.")
        assert cue is not None
        assert not cue.topic.endswith(".")

    def test_removes_filler_words(self):
        """Topic should have filler words removed from start."""
        cue = detect_social_cue("You mentioned that the caching approach.")
        assert cue is not None
        # "that the" should be removed
        assert not cue.topic.startswith("that")
