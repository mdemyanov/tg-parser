# Telegram JSON Export Format

## Overview

Telegram Desktop exports chats in JSON format with a specific structure. This document describes the format and how tg-parser handles it.

## Root Structure

```json
{
  "name": "Chat Name",
  "type": "private_supergroup",
  "id": 123456789,
  "messages": [
    // Array of message objects
  ]
}
```

### Root Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `name` | string | Chat display name | "Команда разработки" |
| `type` | string | Telegram chat type | "private_supergroup" |
| `id` | number | Telegram chat ID | 123456789 |
| `messages` | array | List of all messages | [...] |

## ChatType Mapping

Telegram uses different type strings than our domain model:

```python
TELEGRAM_TYPE_MAP = {
    "personal_chat": ChatType.PERSONAL,
    "private_group": ChatType.GROUP,
    "private_supergroup": ChatType.SUPERGROUP,
    "public_supergroup": ChatType.SUPERGROUP,
    "public_channel": ChatType.CHANNEL,
    "private_channel": ChatType.CHANNEL,
}
```

### Forum Detection

For forum supergroups, check for topic creation messages:

```python
if msg["type"] == "service" and msg.get("action") == "topic_created":
    chat_type = ChatType.SUPERGROUP_FORUM
```

## Message Structure

### Standard Message

```json
{
  "id": 1,
  "type": "message",
  "date": "2025-01-15T10:30:00",
  "date_unixtime": "1736936400",
  "from": "Иван Петров",
  "from_id": "user123456789",
  "text": "Коллеги, нужно обсудить архитектуру.",
  "reply_to_message_id": 42,
  "forwarded_from": "Source Name",
  "media_type": "photo",
  "photo": "(File not included...)",
  "reactions": [
    {"emoji": "👍", "count": 3}
  ]
}
```

### Service Message

```json
{
  "id": 2,
  "type": "service",
  "date": "2025-01-15T09:00:00",
  "actor": "Мария Сидорова",
  "actor_id": "user987654321",
  "action": "invite_members",
  "members": ["Алексей Иванов"],
  "text": ""
}
```

### Message Fields Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | number | ✅ | Unique message ID in chat |
| `type` | string | ✅ | "message" or "service" |
| `date` | string | ✅ | ISO 8601 timestamp |
| `date_unixtime` | string | ❌ | Unix timestamp |
| `from` | string | ✅ | Sender display name |
| `from_id` | string | ✅ | Sender ID (user/channel) |
| `text` | string \| array | ✅ | Message text (see Text Format below) |
| `reply_to_message_id` | number | ❌ | ID of replied message (for threading/topics) |
| `forwarded_from` | string | ❌ | Original sender if forwarded |
| `media_type` | string | ❌ | Type of media attachment |
| `photo` | string | ❌ | Photo placeholder text |
| `file` | string | ❌ | File placeholder text |
| `sticker_emoji` | string | ❌ | Emoji for sticker |
| `reactions` | array | ❌ | List of reactions |

## Text Format

### Simple Text

```json
{
  "text": "Simple text message"
}
```

### Formatted Text

Text with entities (bold, links, mentions) is an array:

```json
{
  "text": [
    "Hello ",
    {
      "type": "bold",
      "text": "world"
    },
    "! Check ",
    {
      "type": "link",
      "text": "https://example.com"
    },
    " and ",
    {
      "type": "mention",
      "text": "@username"
    }
  ]
}
```

### Text Normalization

Convert to plain string:

```python
def normalize_text(text_field: str | list | None) -> str:
    """Convert Telegram text field to plain string."""
    if text_field is None:
        return ""

    if isinstance(text_field, str):
        return text_field

    if isinstance(text_field, list):
        parts = []
        for item in text_field:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(item.get("text", ""))
        return "".join(parts)

    return str(text_field)
```

## Forum Topics

### Topic Creation

Topics in forum mode are created via service messages:

```json
{
  "id": 5,
  "type": "service",
  "date": "2025-01-10T12:00:00",
  "action": "topic_created",
  "title": "Архитектура",
  "text": "Topic 'Архитектура' was created"
}
```

### Topic Detection Algorithm

```python
# Step 1: Find all topic creation messages
topics: dict[TopicId, Topic] = {}
for msg in messages:
    if msg["type"] == "service" and msg.get("action") == "topic_created":
        topic_id = TopicId(msg["id"])
        topics[topic_id] = Topic(
            id=topic_id,
            title=msg.get("title", "Unknown"),
            created_at=parse_datetime(msg["date"]),
        )

# Step 2: Assign messages to topics
GENERAL_TOPIC_ID = TopicId(1)  # Default topic
for msg in messages:
    if msg["type"] == "service":
        continue

    # Messages reply to topic creation message
    reply_to = msg.get("reply_to_message_id")
    if reply_to and reply_to in topics:
        msg.topic_id = TopicId(reply_to)
    else:
        msg.topic_id = GENERAL_TOPIC_ID
```

### General Topic

The "General" topic (ID=1) is implicit and always exists in forums:

```python
topics[GENERAL_TOPIC_ID] = Topic(
    id=GENERAL_TOPIC_ID,
    title="General",
    is_general=True,
)
```

## Service Messages

### Common Service Actions

| Action | Description | Example |
|--------|-------------|---------|
| `invite_members` | User(s) added to chat | "Alice invited Bob" |
| `remove_members` | User(s) removed | "Alice removed Bob" |
| `join_group_by_link` | User joined via link | "Bob joined via invite link" |
| `pin_message` | Message pinned | "Alice pinned a message" |
| `edit_group_title` | Chat name changed | "Title changed to 'New Name'" |
| `edit_group_photo` | Chat photo changed | "Alice updated the group photo" |
| `topic_created` | Forum topic created | "Topic 'Feature X' was created" |
| `topic_edited` | Forum topic renamed | "Topic renamed to 'Feature Y'" |

### Service Message Structure

```json
{
  "id": 10,
  "type": "service",
  "date": "2025-01-15T11:00:00",
  "actor": "Мария Сидорова",
  "actor_id": "user987654321",
  "action": "pin_message",
  "message_id": 42,
  "text": "Мария Сидорова pinned a message"
}
```

### Filtering Service Messages

By default, tg-parser excludes service messages:

```python
filter_spec = FilterSpecification(
    exclude_service=True  # Default
)
```

To include them:

```bash
tg-parser parse ./export.json --include-service
```

## Media Attachments

### Photo

```json
{
  "id": 15,
  "type": "message",
  "media_type": "photo",
  "photo": "(File not included. Change data exporting settings to download.)",
  "text": "Caption text"
}
```

### File

```json
{
  "id": 16,
  "type": "message",
  "media_type": "file",
  "file": "(File not included. Change data exporting settings to download.)",
  "mime_type": "application/pdf",
  "text": ""
}
```

### Sticker

```json
{
  "id": 17,
  "type": "message",
  "media_type": "sticker",
  "sticker_emoji": "😀",
  "file": "(File not included...)",
  "text": ""
}
```

### Voice Message

```json
{
  "id": 18,
  "type": "message",
  "media_type": "voice_message",
  "duration_seconds": 5,
  "file": "(File not included...)",
  "text": ""
}
```

## Reactions

### Reaction Format

```json
{
  "reactions": [
    {
      "emoji": "👍",
      "count": 3
    },
    {
      "emoji": "❤️",
      "count": 1
    }
  ]
}
```

### Parsing Reactions

```python
def parse_reactions(reactions_field: list | None) -> dict[str, int]:
    """Parse reactions into emoji -> count mapping."""
    if not reactions_field:
        return {}

    result = {}
    for reaction in reactions_field:
        emoji = reaction.get("emoji", "")
        count = reaction.get("count", 0)
        if emoji:
            result[emoji] = count

    return result
```

## Mentions Detection

### In Text

Mentions appear as entities in formatted text:

```json
{
  "text": [
    "Hey ",
    {
      "type": "mention",
      "text": "@username"
    },
    ", check this out!"
  ]
}
```

### Extraction

```python
def extract_mentions(text_field: str | list | None) -> tuple[str, ...]:
    """Extract @mentions from text field."""
    if not text_field:
        return ()

    mentions = []
    if isinstance(text_field, list):
        for item in text_field:
            if isinstance(item, dict) and item.get("type") == "mention":
                mention = item.get("text", "")
                if mention.startswith("@"):
                    mentions.append(mention[1:])  # Remove @
    return tuple(mentions)
```

## Timestamps

### Date Format

ISO 8601 format with timezone:

```
"2025-01-15T10:30:00"
```

### Parsing

```python
from datetime import datetime

def parse_timestamp(date_str: str) -> datetime:
    """Parse Telegram timestamp to datetime."""
    return datetime.fromisoformat(date_str)
```

### Unix Timestamp

Sometimes included as alternative:

```json
{
  "date": "2025-01-15T10:30:00",
  "date_unixtime": "1736936400"
}
```

We prefer ISO format for readability.

## User IDs

### Format

User IDs are strings with prefix:

- `user123456789` — Regular user
- `channel123456789` — Channel/bot

### Extraction

```python
def parse_user_id(from_id: str) -> UserId:
    """Parse Telegram user ID."""
    return UserId(from_id)  # Keep as-is, no transformation
```

## Edge Cases

### Empty Text

Messages can have empty text (media-only):

```json
{
  "id": 20,
  "type": "message",
  "media_type": "photo",
  "photo": "...",
  "text": ""
}
```

Handle in normalization:

```python
text = normalize_text(msg.get("text"))
if not text.strip() and msg.get("media_type"):
    text = f"[{msg['media_type']}]"  # Placeholder
```

### Missing Fields

Some fields may be absent:

```python
# Always provide defaults
from_id = msg.get("from_id", "unknown")
reply_to = msg.get("reply_to_message_id")  # None if missing
```

### Duplicate IDs

In rare cases, IDs may not be unique across topics. Use (id, topic_id) as composite key if needed.

## Export Size Optimization

### Large Exports

For files >50MB, use streaming mode:

```bash
tg-parser parse ./large_export.json --streaming
```

Streaming uses ijson to avoid loading entire JSON into memory.

### Export Settings

To reduce file size:
1. Uncheck "Export media" in Telegram Desktop
2. Limit date range
3. Export specific topics only (for forums)

## Validation

### Required Fields Check

```python
def validate_export(data: dict) -> None:
    """Validate export structure."""
    if "messages" not in data:
        raise InvalidExportError("Missing 'messages' field")

    if "name" not in data:
        raise InvalidExportError("Missing 'name' field")

    if "type" not in data:
        raise InvalidExportError("Missing 'type' field")
```

### Message Validation

```python
def validate_message(msg: dict) -> None:
    """Validate single message."""
    required = ["id", "type", "date", "from", "from_id"]
    for field in required:
        if field not in msg:
            raise InvalidExportError(f"Message missing '{field}'")
```

## Examples

### Personal Chat Export

```json
{
  "name": "Иван Петров",
  "type": "personal_chat",
  "id": 123456,
  "messages": [
    {
      "id": 1,
      "type": "message",
      "date": "2025-01-15T10:00:00",
      "from": "Иван Петров",
      "from_id": "user123456",
      "text": "Привет!"
    }
  ]
}
```

### Forum Export

```json
{
  "name": "Dev Team",
  "type": "private_supergroup",
  "id": 789012,
  "messages": [
    {
      "id": 1,
      "type": "service",
      "action": "topic_created",
      "title": "Backend",
      "date": "2025-01-10T09:00:00"
    },
    {
      "id": 2,
      "type": "message",
      "date": "2025-01-10T09:05:00",
      "from": "Alice",
      "from_id": "user111",
      "reply_to_message_id": 1,
      "text": "Let's discuss API design"
    }
  ]
}
```

## References

- [Telegram Desktop Export Guide](https://telegram.org/blog/export-and-more)
- [tg-parser Readers](../src/tg_parser/infrastructure/readers/)
- [Message Entity](../src/tg_parser/domain/entities/message.py)
