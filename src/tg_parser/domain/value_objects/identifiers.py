"""Domain identifiers as NewType for type safety."""

from __future__ import annotations

from typing import NewType

MessageId = NewType("MessageId", int)
UserId = NewType("UserId", str)
TopicId = NewType("TopicId", int)

# General topic constant for forum groups (topic_id=1 is always "General")
GENERAL_TOPIC_ID: TopicId = TopicId(1)
