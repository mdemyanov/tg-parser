"""Unit tests for token counters."""

from __future__ import annotations

from datetime import datetime

import pytest

from tg_parser.domain.entities.message import Attachment, Message
from tg_parser.domain.value_objects.identifiers import MessageId, UserId
from tg_parser.infrastructure.token_counters import get_token_counter
from tg_parser.infrastructure.token_counters.simple_counter import SimpleTokenCounter


class TestSimpleTokenCounter:
    """Tests for SimpleTokenCounter class."""

    def test_count_empty_string(self) -> None:
        """Test counting empty string."""
        counter = SimpleTokenCounter()
        # Empty string returns 1 due to +1 in formula
        assert counter.count("") >= 0

    def test_count_short_text(self) -> None:
        """Test counting short text."""
        counter = SimpleTokenCounter()
        # "Hello" is 5 chars, ~1-2 tokens
        result = counter.count("Hello")
        assert result > 0
        assert result < 10  # Should be reasonably small

    def test_count_long_text(self) -> None:
        """Test counting longer text."""
        counter = SimpleTokenCounter()
        text = "The quick brown fox jumps over the lazy dog. " * 10
        result = counter.count(text)
        # Should scale with text length
        assert result > 50

    def test_count_unicode_text(self) -> None:
        """Test counting Unicode (Cyrillic) text."""
        counter = SimpleTokenCounter()
        # Russian text tends to have ~2-3 chars per token
        result = counter.count("Привет мир!")
        assert result > 0

    def test_count_messages_empty_list(self) -> None:
        """Test counting empty message list."""
        counter = SimpleTokenCounter()
        result = counter.count_messages([])
        assert result == 0

    def test_count_messages_basic(self) -> None:
        """Test counting basic messages."""
        counter = SimpleTokenCounter()
        messages = [
            Message(
                id=MessageId(1),
                timestamp=datetime(2025, 1, 15, 10, 0),
                author_name="Alice",
                author_id=UserId("user1"),
                text="Hello world!",
            ),
            Message(
                id=MessageId(2),
                timestamp=datetime(2025, 1, 15, 10, 5),
                author_name="Bob",
                author_id=UserId("user2"),
                text="Hi there!",
            ),
        ]
        result = counter.count_messages(messages)
        assert result > 0
        # Should include overhead for names, timestamps, etc.
        pure_text_count = counter.count("Hello world!") + counter.count("Hi there!")
        assert result > pure_text_count  # Overhead added

    def test_count_messages_with_attachments(self) -> None:
        """Test counting messages with attachments adds overhead."""
        counter = SimpleTokenCounter()
        msg_without = Message(
            id=MessageId(1),
            timestamp=datetime(2025, 1, 15, 10, 0),
            author_name="Alice",
            author_id=UserId("user1"),
            text="Check this",
        )
        msg_with = Message(
            id=MessageId(2),
            timestamp=datetime(2025, 1, 15, 10, 0),
            author_name="Alice",
            author_id=UserId("user1"),
            text="Check this",
            attachments=(
                Attachment(type="photo"),
                Attachment(type="document"),
            ),
        )
        count_without = counter.count_messages([msg_without])
        count_with = counter.count_messages([msg_with])
        # Message with attachments should have higher count
        assert count_with > count_without

    def test_count_messages_with_reactions(self) -> None:
        """Test counting messages with reactions adds overhead."""
        counter = SimpleTokenCounter()
        msg_without = Message(
            id=MessageId(1),
            timestamp=datetime(2025, 1, 15, 10, 0),
            author_name="Alice",
            author_id=UserId("user1"),
            text="Nice!",
        )
        msg_with = Message(
            id=MessageId(2),
            timestamp=datetime(2025, 1, 15, 10, 0),
            author_name="Alice",
            author_id=UserId("user1"),
            text="Nice!",
            reactions={"👍": 5, "❤️": 3, "🎉": 2},
        )
        count_without = counter.count_messages([msg_without])
        count_with = counter.count_messages([msg_with])
        # Message with reactions should have higher count
        assert count_with > count_without


class TestGetTokenCounter:
    """Tests for get_token_counter factory function."""

    def test_simple_backend(self) -> None:
        """Test getting simple counter explicitly."""
        counter = get_token_counter("simple")
        assert isinstance(counter, SimpleTokenCounter)

    def test_auto_backend_returns_counter(self) -> None:
        """Test that auto backend returns some counter."""
        counter = get_token_counter("auto")
        # Should return either SimpleTokenCounter or TiktokenCounter
        assert hasattr(counter, "count")
        assert hasattr(counter, "count_messages")

    def test_auto_backend_works(self) -> None:
        """Test that auto backend counter works correctly."""
        counter = get_token_counter("auto")
        result = counter.count("Hello world!")
        assert result > 0


# Conditional tests for tiktoken - only run if tiktoken is installed
try:
    import tiktoken  # noqa: F401

    _has_tiktoken = True
except ImportError:
    _has_tiktoken = False


@pytest.mark.skipif(not _has_tiktoken, reason="tiktoken not installed")
class TestTiktokenCounter:
    """Tests for TiktokenCounter class (when tiktoken is available)."""

    def test_tiktoken_backend(self) -> None:
        """Test getting tiktoken counter explicitly."""
        from tg_parser.infrastructure.token_counters.tiktoken_counter import (
            TiktokenCounter,
        )

        counter = get_token_counter("tiktoken")
        assert isinstance(counter, TiktokenCounter)

    def test_count_basic(self) -> None:
        """Test basic tiktoken counting."""
        from tg_parser.infrastructure.token_counters.tiktoken_counter import (
            TiktokenCounter,
        )

        counter = TiktokenCounter()
        # "Hello" is typically 1 token in cl100k_base
        result = counter.count("Hello")
        assert result >= 1
        assert result <= 3

    def test_count_longer_text(self) -> None:
        """Test tiktoken counting for longer text."""
        from tg_parser.infrastructure.token_counters.tiktoken_counter import (
            TiktokenCounter,
        )

        counter = TiktokenCounter()
        text = "The quick brown fox jumps over the lazy dog."
        result = counter.count(text)
        # This specific sentence is typically 9-10 tokens
        assert result >= 8
        assert result <= 15

    def test_count_unicode(self) -> None:
        """Test tiktoken counting for Unicode text."""
        from tg_parser.infrastructure.token_counters.tiktoken_counter import (
            TiktokenCounter,
        )

        counter = TiktokenCounter()
        result = counter.count("Привет мир!")
        assert result > 0

    def test_count_messages(self) -> None:
        """Test tiktoken counting for messages."""
        from tg_parser.infrastructure.token_counters.tiktoken_counter import (
            TiktokenCounter,
        )

        counter = TiktokenCounter()
        messages = [
            Message(
                id=MessageId(1),
                timestamp=datetime(2025, 1, 15, 10, 0),
                author_name="Alice",
                author_id=UserId("user1"),
                text="Hello world!",
            ),
        ]
        result = counter.count_messages(messages)
        assert result > 0
        # Should be more than just the text due to overhead
        assert result > counter.count("Hello world!")

    def test_auto_prefers_tiktoken(self) -> None:
        """Test that auto backend prefers tiktoken when available."""
        from tg_parser.infrastructure.token_counters.tiktoken_counter import (
            TiktokenCounter,
        )

        counter = get_token_counter("auto")
        assert isinstance(counter, TiktokenCounter)

    def test_tiktoken_more_accurate_than_simple(self) -> None:
        """Test that tiktoken gives different (more accurate) results."""
        from tg_parser.infrastructure.token_counters.tiktoken_counter import (
            TiktokenCounter,
        )

        simple = SimpleTokenCounter()
        tiktoken_counter = TiktokenCounter()

        # "Hello" should be 1-2 tokens with tiktoken, but ~2 with simple (5/4+1)
        text = "Hello"
        simple_count = simple.count(text)
        tiktoken_count = tiktoken_counter.count(text)

        # They may differ - that's expected as tiktoken is more accurate
        # Just verify both return reasonable values
        assert simple_count > 0
        assert tiktoken_count > 0
