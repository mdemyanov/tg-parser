"""Application use cases."""

from __future__ import annotations

from tg_parser.application.use_cases.chunk_chat import ChunkChatUseCase, ChunkResult
from tg_parser.application.use_cases.get_mentions import (
    GetMentionsUseCase,
    MentionInfo,
    MentionsResult,
)
from tg_parser.application.use_cases.get_statistics import GetStatisticsUseCase
from tg_parser.application.use_cases.parse_chat import ParseChatUseCase

__all__ = [
    "ChunkChatUseCase",
    "ChunkResult",
    "GetMentionsUseCase",
    "GetStatisticsUseCase",
    "MentionInfo",
    "MentionsResult",
    "ParseChatUseCase",
]
