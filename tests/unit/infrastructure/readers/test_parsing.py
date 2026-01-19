"""Tests for shared parsing functions."""

from __future__ import annotations

from datetime import datetime

from tg_parser.domain.entities.chat import ChatType
from tg_parser.domain.entities.message import MessageType
from tg_parser.domain.entities.topic import Topic
from tg_parser.domain.value_objects.identifiers import GENERAL_TOPIC_ID, TopicId
from tg_parser.infrastructure.readers._parsing import (
    determine_chat_type,
    determine_topic,
    extract_mentions,
    extract_topics,
    normalize_text,
    parse_attachments,
    parse_datetime,
    parse_message,
    parse_reactions,
    parse_reply,
)


class TestNormalizeText:
    """Test normalize_text function."""

    def test_simple_string(self) -> None:
        """Test normalizing simple string."""
        assert normalize_text("Hello world") == "Hello world"

    def test_none_returns_empty(self) -> None:
        """Test None returns empty string."""
        assert normalize_text(None) == ""

    def test_empty_string(self) -> None:
        """Test empty string returns empty."""
        assert normalize_text("") == ""

    def test_array_with_strings(self) -> None:
        """Test array with plain strings."""
        text = ["Hello ", "world"]
        assert normalize_text(text) == "Hello world"

    def test_array_with_formatting_objects(self) -> None:
        """Test array with formatting objects."""
        text = [
            "Normal ",
            {"type": "bold", "text": "bold"},
            " ",
            {"type": "italic", "text": "italic"},
        ]
        assert normalize_text(text) == "Normal bold italic"

    def test_array_mixed(self) -> None:
        """Test array with mixed content."""
        text = [
            {"type": "mention", "text": "@user"},
            " said hello",
        ]
        assert normalize_text(text) == "@user said hello"

    def test_number_coerced_to_string(self) -> None:
        """Test number is coerced to string."""
        assert normalize_text(123) == "123"


class TestParseDatetime:
    """Test parse_datetime function."""

    def test_valid_iso_format(self) -> None:
        """Test parsing valid ISO datetime."""
        result = parse_datetime("2024-01-15T10:30:00")
        assert result == datetime(2024, 1, 15, 10, 30, 0)

    def test_none_returns_none(self) -> None:
        """Test None returns None."""
        assert parse_datetime(None) is None

    def test_empty_string_returns_none(self) -> None:
        """Test empty string returns None."""
        assert parse_datetime("") is None

    def test_invalid_format_returns_none(self) -> None:
        """Test invalid format returns None."""
        assert parse_datetime("not-a-date") is None


class TestDetermineChatType:
    """Test determine_chat_type function."""

    def test_personal_chat(self) -> None:
        """Test personal chat type."""
        data = {"type": "personal_chat"}
        assert determine_chat_type(data) == ChatType.PERSONAL

    def test_private_supergroup(self) -> None:
        """Test private supergroup type."""
        data = {"type": "private_supergroup"}
        assert determine_chat_type(data) == ChatType.SUPERGROUP

    def test_public_channel(self) -> None:
        """Test public channel type."""
        data = {"type": "public_channel"}
        assert determine_chat_type(data) == ChatType.CHANNEL

    def test_private_group(self) -> None:
        """Test private group type."""
        data = {"type": "private_group"}
        assert determine_chat_type(data) == ChatType.GROUP

    def test_unknown_with_personal_keyword(self) -> None:
        """Test fallback for unknown type with personal keyword."""
        data = {"type": "some_personal_type"}
        assert determine_chat_type(data) == ChatType.PERSONAL

    def test_unknown_defaults_to_supergroup(self) -> None:
        """Test unknown type defaults to supergroup."""
        data = {"type": "unknown_type"}
        assert determine_chat_type(data) == ChatType.SUPERGROUP


class TestDetermineTopic:
    """Test determine_topic function."""

    def test_no_topics_returns_none(self) -> None:
        """Test no topics returns None."""
        raw = {"reply_to_message_id": 123}
        assert determine_topic(raw, {}) is None

    def test_reply_to_topic_id(self) -> None:
        """Test reply to topic creation message."""
        topic_id = TopicId(100)
        topics = {topic_id: Topic(id=topic_id, title="Test")}
        raw = {"reply_to_message_id": 100}
        assert determine_topic(raw, topics) == topic_id

    def test_defaults_to_general(self) -> None:
        """Test defaults to general topic."""
        topic_id = TopicId(100)
        topics = {topic_id: Topic(id=topic_id, title="Test")}
        raw = {"reply_to_message_id": 999}  # Not a topic
        assert determine_topic(raw, topics) == GENERAL_TOPIC_ID

    def test_no_reply_id_returns_general(self) -> None:
        """Test no reply_to returns general."""
        topic_id = TopicId(100)
        topics = {topic_id: Topic(id=topic_id, title="Test")}
        raw = {}
        assert determine_topic(raw, topics) == GENERAL_TOPIC_ID


class TestParseReply:
    """Test parse_reply function."""

    def test_no_reply(self) -> None:
        """Test message without reply."""
        assert parse_reply({}) is None

    def test_with_reply(self) -> None:
        """Test message with reply."""
        raw = {"reply_to_message_id": 42}
        reply = parse_reply(raw)
        assert reply is not None
        assert reply.message_id == 42


class TestParseAttachments:
    """Test parse_attachments function."""

    def test_no_attachments(self) -> None:
        """Test message without attachments."""
        assert parse_attachments({}) == []

    def test_with_media_type(self) -> None:
        """Test message with media_type."""
        raw = {
            "media_type": "photo",
            "file": "photos/photo_1.jpg",
            "file_name": "photo.jpg",
        }
        attachments = parse_attachments(raw)
        assert len(attachments) == 1
        assert attachments[0].type == "photo"

    def test_photo_without_media_type(self) -> None:
        """Test photo field without media_type."""
        raw = {"photo": "photos/photo_1.jpg"}
        attachments = parse_attachments(raw)
        assert len(attachments) == 1
        assert attachments[0].type == "photo"


class TestExtractMentions:
    """Test extract_mentions function."""

    def test_no_mentions(self) -> None:
        """Test message without mentions."""
        assert extract_mentions({"text": "Hello"}) == []

    def test_mentions_in_text_array(self) -> None:
        """Test mentions in text array."""
        raw = {
            "text": [
                {"type": "mention", "text": "@user1"},
                " and ",
                {"type": "mention", "text": "@user2"},
            ]
        }
        mentions = extract_mentions(raw)
        assert "@user1" in mentions
        assert "@user2" in mentions

    def test_mentions_in_text_entities(self) -> None:
        """Test mentions in text_entities array."""
        raw = {
            "text": "Hello @user",
            "text_entities": [{"type": "mention", "text": "@user"}],
        }
        mentions = extract_mentions(raw)
        assert "@user" in mentions


class TestParseReactions:
    """Test parse_reactions function."""

    def test_no_reactions(self) -> None:
        """Test message without reactions."""
        assert parse_reactions({}) == {}

    def test_with_reactions(self) -> None:
        """Test message with reactions."""
        raw = {
            "reactions": [
                {"emoji": "👍", "count": 5},
                {"emoji": "❤️", "count": 2},
            ]
        }
        reactions = parse_reactions(raw)
        assert reactions["👍"] == 5
        assert reactions["❤️"] == 2


class TestParseMessage:
    """Test parse_message function."""

    def test_basic_text_message(self) -> None:
        """Test parsing basic text message."""
        raw = {
            "id": 1,
            "type": "message",
            "date": "2024-01-15T10:30:00",
            "from": "Test User",
            "from_id": "user123",
            "text": "Hello world",
        }
        msg = parse_message(raw, {})
        assert msg is not None
        assert msg.id == 1
        assert msg.author_name == "Test User"
        assert msg.text == "Hello world"
        assert msg.message_type == MessageType.TEXT

    def test_service_message(self) -> None:
        """Test parsing service message."""
        raw = {
            "id": 1,
            "type": "service",
            "date": "2024-01-15T10:30:00",
            "actor": "Test User",
            "actor_id": "user123",
            "text": "",
        }
        msg = parse_message(raw, {})
        assert msg is not None
        assert msg.message_type == MessageType.SERVICE

    def test_sticker_message(self) -> None:
        """Test parsing sticker message."""
        raw = {
            "id": 1,
            "type": "message",
            "date": "2024-01-15T10:30:00",
            "from": "User",
            "from_id": "user1",
            "media_type": "sticker",
            "text": "",
        }
        msg = parse_message(raw, {})
        assert msg is not None
        assert msg.message_type == MessageType.STICKER

    def test_voice_message(self) -> None:
        """Test parsing voice message."""
        raw = {
            "id": 1,
            "type": "message",
            "date": "2024-01-15T10:30:00",
            "from": "User",
            "from_id": "user1",
            "media_type": "voice_message",
            "text": "",
        }
        msg = parse_message(raw, {})
        assert msg is not None
        assert msg.message_type == MessageType.VOICE


class TestExtractTopics:
    """Test extract_topics function."""

    def test_no_topics(self) -> None:
        """Test messages without topics."""
        messages = [
            {"id": 1, "type": "message", "text": "Hello"},
        ]
        assert extract_topics(messages) == {}

    def test_topic_created(self) -> None:
        """Test topic_created service message."""
        messages = [
            {
                "id": 100,
                "type": "service",
                "action": "topic_created",
                "title": "Finances",
                "date": "2024-01-15T10:00:00",
            },
        ]
        topics = extract_topics(messages)
        assert TopicId(100) in topics
        assert topics[TopicId(100)].title == "Finances"
        # Should also create General topic
        assert GENERAL_TOPIC_ID in topics

    def test_topic_edit_creates_general(self) -> None:
        """Test topic_edit creates General topic."""
        messages = [
            {
                "id": 1,
                "type": "service",
                "action": "topic_edit",
                "new_title": "Announcements",
                "date": "2024-01-15T10:00:00",
            },
        ]
        topics = extract_topics(messages)
        assert GENERAL_TOPIC_ID in topics
        assert topics[GENERAL_TOPIC_ID].title == "Announcements"
