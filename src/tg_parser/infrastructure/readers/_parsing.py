"""Shared parsing functions for Telegram JSON exports.

This module contains common parsing logic used by both
TelegramJSONReader and TelegramStreamReader.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from tg_parser.domain.entities.chat import TELEGRAM_TYPE_MAP, ChatType
from tg_parser.domain.entities.message import (
    Attachment,
    Message,
    MessageType,
    ReplyInfo,
)
from tg_parser.domain.entities.topic import Topic
from tg_parser.domain.value_objects.identifiers import (
    GENERAL_TOPIC_ID,
    MessageId,
    TopicId,
    UserId,
)


def normalize_text(text_field: Any) -> str:
    """Convert Telegram text field to plain string.

    Telegram text can be:
    - A simple string: "Hello"
    - An array with formatting: [{"type": "bold", "text": "Hi"}, " world"]

    Args:
        text_field: Raw text field from Telegram JSON.

    Returns:
        Normalized plain text string.
    """
    if text_field is None:
        return ""
    if isinstance(text_field, str):
        return text_field
    if isinstance(text_field, list):
        parts: list[str] = []
        text_list: list[Any] = text_field
        for item in text_list:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                item_dict: dict[str, Any] = item
                text_val: str = str(item_dict.get("text", ""))
                parts.append(text_val)
        return "".join(parts)
    return str(text_field)


def parse_datetime(date_str: str | None) -> datetime | None:
    """Parse ISO datetime string.

    Args:
        date_str: ISO format datetime string.

    Returns:
        Parsed datetime or None if invalid/empty.
    """
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        return None


def determine_chat_type(data: dict[str, Any]) -> ChatType:
    """Determine chat type from Telegram type string.

    Args:
        data: Raw chat data with 'type' field.

    Returns:
        Appropriate ChatType enum value.
    """
    tg_type = data.get("type", "")
    if tg_type in TELEGRAM_TYPE_MAP:
        return TELEGRAM_TYPE_MAP[tg_type]

    # Fallback heuristics
    tg_type_lower = tg_type.lower()
    if "personal" in tg_type_lower:
        return ChatType.PERSONAL
    if "channel" in tg_type_lower:
        return ChatType.CHANNEL
    if "group" in tg_type_lower:
        return ChatType.GROUP

    return ChatType.SUPERGROUP  # Default


def determine_topic(
    raw: dict[str, Any],
    topics: dict[TopicId, Topic],
) -> TopicId | None:
    """Determine which topic a message belongs to.

    In forum mode, messages are assigned to topics via reply_to_message_id
    pointing to the topic creation service message.

    Args:
        raw: Raw message dict.
        topics: Extracted topics map.

    Returns:
        Topic ID or None for non-forum chats.
    """
    if not topics:
        return None

    # Check reply_to_message_id for topic routing
    reply_id = raw.get("reply_to_message_id")
    if reply_id:
        topic_id = TopicId(reply_id)
        if topic_id in topics:
            return topic_id

    # Default to General topic for forum chats
    return GENERAL_TOPIC_ID


def parse_reply(raw: dict[str, Any]) -> ReplyInfo | None:
    """Parse reply information.

    Args:
        raw: Raw message dict.

    Returns:
        ReplyInfo or None if not a reply.
    """
    reply_id = raw.get("reply_to_message_id")
    if not reply_id:
        return None

    return ReplyInfo(
        message_id=MessageId(reply_id),
        author=None,  # Would need second pass to resolve
        preview=None,
    )


def parse_attachments(raw: dict[str, Any]) -> list[Attachment]:
    """Parse media attachments.

    Args:
        raw: Raw message dict.

    Returns:
        List of Attachment objects.
    """
    attachments: list[Attachment] = []

    media_type = raw.get("media_type")
    if media_type:
        attachments.append(
            Attachment(
                type=media_type,
                file_path=raw.get("file"),
                file_name=raw.get("file_name"),
                mime_type=raw.get("mime_type"),
                size_bytes=raw.get("file_size"),
            )
        )

    # Handle photo specifically (sometimes separate from media_type)
    photo = raw.get("photo")
    if photo and not media_type:
        attachments.append(
            Attachment(
                type="photo",
                file_path=photo if isinstance(photo, str) else None,
            )
        )

    return attachments


def extract_mentions(raw: dict[str, Any]) -> list[str]:
    """Extract mentioned users from text entities.

    Args:
        raw: Raw message dict.

    Returns:
        List of mention strings (e.g., "@username").
    """
    mentions: list[str] = []

    text_field: Any = raw.get("text")
    if isinstance(text_field, list):
        text_list: list[Any] = text_field
        for item in text_list:
            if isinstance(item, dict):
                item_dict: dict[str, Any] = item
                if item_dict.get("type") == "mention":
                    text: str = str(item_dict.get("text", ""))
                    if text:
                        mentions.append(text)

    # Also check text_entities array
    for entity in raw.get("text_entities", []):
        if entity.get("type") == "mention":
            text = entity.get("text", "")
            if text and text not in mentions:
                mentions.append(text)

    return mentions


def parse_reactions(raw: dict[str, Any]) -> dict[str, int]:
    """Parse reactions into emoji -> count mapping.

    Args:
        raw: Raw message dict.

    Returns:
        Dict mapping emoji to reaction count.
    """
    reactions: dict[str, int] = {}

    for reaction in raw.get("reactions", []):
        emoji = reaction.get("emoji", "")
        count = reaction.get("count", 1)
        if emoji:
            reactions[emoji] = count

    return reactions


def parse_message(
    raw: dict[str, Any],
    topics: dict[TopicId, Topic],
) -> Message | None:
    """Parse a single message from raw dict.

    Args:
        raw: Raw message dict from Telegram JSON.
        topics: Extracted topics map for forum chats.

    Returns:
        Message entity or None if parsing fails.
    """
    msg_type_str = raw.get("type", "message")

    # Determine message type
    if msg_type_str == "service":
        message_type = MessageType.SERVICE
    elif raw.get("media_type") == "sticker":
        message_type = MessageType.STICKER
    elif raw.get("media_type") in ("voice_message", "audio_file"):
        message_type = MessageType.VOICE
    elif raw.get("media_type") == "video_message":
        message_type = MessageType.VIDEO_NOTE
    elif raw.get("media_type"):
        message_type = MessageType.MEDIA
    else:
        message_type = MessageType.TEXT

    # Parse text (can be string or array with formatting)
    text = normalize_text(raw.get("text"))

    # Parse author
    author_name = raw.get("from") or raw.get("actor") or "Unknown"
    author_id_raw = raw.get("from_id") or raw.get("actor_id") or ""
    author_id = UserId(str(author_id_raw))

    # Parse topic
    topic_id = determine_topic(raw, topics)

    # Parse reply info
    reply_to = parse_reply(raw)

    # Parse attachments
    attachments = parse_attachments(raw)

    # Parse mentions
    mentions = extract_mentions(raw)

    # Parse reactions
    reactions = parse_reactions(raw)

    timestamp = parse_datetime(raw.get("date"))
    if timestamp is None:
        timestamp = datetime.min

    return Message(
        id=MessageId(raw.get("id", 0)),
        timestamp=timestamp,
        author_name=author_name,
        author_id=author_id,
        text=text,
        message_type=message_type,
        topic_id=topic_id,
        reply_to=reply_to,
        forward_from=raw.get("forwarded_from"),
        mentions=tuple(mentions),
        attachments=tuple(attachments),
        reactions=reactions,
    )


def extract_topics(raw_messages: list[dict[str, Any]]) -> dict[TopicId, Topic]:
    """Extract topics from service messages.

    Args:
        raw_messages: List of raw message dicts.

    Returns:
        Dict mapping TopicId to Topic entity.
    """
    topics: dict[TopicId, Topic] = {}

    for raw in raw_messages:
        action = raw.get("action", "")

        # topic_created action
        if raw.get("type") == "service" and action == "topic_created":
            topic_id = TopicId(raw.get("id", 0))
            topics[topic_id] = Topic(
                id=topic_id,
                title=raw.get("title", "Unknown"),
                created_at=parse_datetime(raw.get("date")),
                is_general=False,
            )

        # topic_edit on General topic (id=1 or first message)
        if raw.get("type") == "service" and action == "topic_edit":
            # This typically happens for General topic renaming
            new_title = raw.get("new_title", "")
            if new_title and GENERAL_TOPIC_ID not in topics:
                topics[GENERAL_TOPIC_ID] = Topic(
                    id=GENERAL_TOPIC_ID,
                    title=new_title,
                    created_at=parse_datetime(raw.get("date")),
                    is_general=True,
                )

    # Always ensure General topic exists if we have other topics
    if topics and GENERAL_TOPIC_ID not in topics:
        topics[GENERAL_TOPIC_ID] = Topic(
            id=GENERAL_TOPIC_ID,
            title="General",
            is_general=True,
        )

    return topics
