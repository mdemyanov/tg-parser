"""Tests for Message entity."""

from __future__ import annotations

from datetime import datetime

import pytest

from tg_parser.domain.entities.message import (
    Attachment,
    Message,
    MessageType,
    ReplyInfo,
)
from tg_parser.domain.value_objects.identifiers import MessageId, UserId


class TestMessage:
    """Test Message entity."""

    def test_create_text_message(self) -> None:
        """Test creating a simple text message."""
        msg = Message(
            id=MessageId(1),
            timestamp=datetime(2024, 1, 15, 10, 30),
            author_name="Alice",
            author_id=UserId("user111"),
            text="Hello!",
        )
        assert msg.id == MessageId(1)
        assert msg.author_name == "Alice"
        assert msg.text == "Hello!"
        assert msg.message_type == MessageType.TEXT

    def test_message_is_immutable(self) -> None:
        """Test that message is frozen."""
        msg = Message(
            id=MessageId(1),
            timestamp=datetime(2024, 1, 15, 10, 30),
            author_name="Alice",
            author_id=UserId("user111"),
            text="Hello!",
        )
        with pytest.raises(AttributeError):
            msg.text = "Changed"  # type: ignore[misc]

    def test_message_with_reply(self) -> None:
        """Test message with reply info."""
        reply = ReplyInfo(
            message_id=MessageId(5),
            author="Bob",
        )
        msg = Message(
            id=MessageId(10),
            timestamp=datetime(2024, 1, 15, 11, 0),
            author_name="Alice",
            author_id=UserId("user111"),
            text="Reply message",
            reply_to=reply,
        )
        assert msg.reply_to is not None
        assert msg.reply_to.message_id == MessageId(5)
        assert msg.reply_to.author == "Bob"

    def test_message_with_attachment(self) -> None:
        """Test message with attachment."""
        attachment = Attachment(
            type="document",
            file_name="document.pdf",
            file_path="files/document.pdf",
            size_bytes=12345,
            mime_type="application/pdf",
        )
        msg = Message(
            id=MessageId(1),
            timestamp=datetime(2024, 1, 15, 10, 30),
            author_name="Alice",
            author_id=UserId("user111"),
            text="See attached",
            attachments=(attachment,),
        )
        assert msg.has_attachments is True
        assert msg.attachments[0].file_name == "document.pdf"
        assert msg.attachments[0].size_bytes == 12345

    def test_message_with_reactions(self) -> None:
        """Test message with reactions."""
        msg = Message(
            id=MessageId(1),
            timestamp=datetime(2024, 1, 15, 10, 30),
            author_name="Alice",
            author_id=UserId("user111"),
            text="Great news!",
            reactions={"👍": 5, "❤": 2},
        )
        assert msg.reactions["👍"] == 5
        assert msg.reactions["❤"] == 2
        assert msg.has_reactions is True
        assert msg.total_reactions == 7

    def test_message_with_mentions(self) -> None:
        """Test message with mentions."""
        msg = Message(
            id=MessageId(1),
            timestamp=datetime(2024, 1, 15, 10, 30),
            author_name="Alice",
            author_id=UserId("user111"),
            text="Hey @bob, check this!",
            mentions=("bob", "charlie"),
        )
        assert "bob" in msg.mentions
        assert "charlie" in msg.mentions

    def test_has_text_property(self) -> None:
        """Test has_text property."""
        msg_with_text = Message(
            id=MessageId(1),
            timestamp=datetime(2024, 1, 15, 10, 30),
            author_name="Alice",
            author_id=UserId("user111"),
            text="Hello!",
        )
        assert msg_with_text.has_text is True

        msg_empty = Message(
            id=MessageId(2),
            timestamp=datetime(2024, 1, 15, 10, 30),
            author_name="Alice",
            author_id=UserId("user111"),
            text="",
        )
        assert msg_empty.has_text is False

    def test_is_service_property(self) -> None:
        """Test is_service property."""
        text_msg = Message(
            id=MessageId(1),
            timestamp=datetime(2024, 1, 15, 10, 30),
            author_name="Alice",
            author_id=UserId("user111"),
            text="Hello!",
            message_type=MessageType.TEXT,
        )
        assert text_msg.is_service is False

        service_msg = Message(
            id=MessageId(2),
            timestamp=datetime(2024, 1, 15, 10, 30),
            author_name="System",
            author_id=UserId("system"),
            text="Group created",
            message_type=MessageType.SERVICE,
        )
        assert service_msg.is_service is True

    def test_is_forward_property(self) -> None:
        """Test is_forward property."""
        regular_msg = Message(
            id=MessageId(1),
            timestamp=datetime(2024, 1, 15, 10, 30),
            author_name="Alice",
            author_id=UserId("user111"),
            text="Hello!",
        )
        assert regular_msg.is_forward is False

        forwarded_msg = Message(
            id=MessageId(2),
            timestamp=datetime(2024, 1, 15, 10, 30),
            author_name="Alice",
            author_id=UserId("user111"),
            text="Forwarded content",
            forward_from="Bob",
        )
        assert forwarded_msg.is_forward is True


class TestMessageType:
    """Test MessageType enum."""

    def test_message_types(self) -> None:
        """Test all message types exist."""
        assert MessageType.TEXT.value == "text"
        assert MessageType.SERVICE.value == "service"
        assert MessageType.MEDIA.value == "media"
        assert MessageType.STICKER.value == "sticker"
        assert MessageType.VOICE.value == "voice"
        assert MessageType.VIDEO_NOTE.value == "video_note"


class TestAttachment:
    """Test Attachment value object."""

    def test_attachment_creation(self) -> None:
        """Test creating attachment."""
        attachment = Attachment(
            type="photo",
            file_name="photo.jpg",
            file_path="photos/photo.jpg",
            size_bytes=54321,
            mime_type="image/jpeg",
        )
        assert attachment.file_name == "photo.jpg"
        assert attachment.type == "photo"

    def test_attachment_minimal(self) -> None:
        """Test attachment with minimal data."""
        attachment = Attachment(type="document")
        assert attachment.type == "document"
        assert attachment.file_path is None
        assert attachment.file_name is None
        assert attachment.size_bytes is None


class TestReplyInfo:
    """Test ReplyInfo value object."""

    def test_reply_info_creation(self) -> None:
        """Test creating reply info."""
        reply = ReplyInfo(
            message_id=MessageId(42),
            author="Charlie",
        )
        assert reply.message_id == MessageId(42)
        assert reply.author == "Charlie"

    def test_reply_info_without_author(self) -> None:
        """Test reply info without author."""
        reply = ReplyInfo(message_id=MessageId(42))
        assert reply.message_id == MessageId(42)
        assert reply.author is None
