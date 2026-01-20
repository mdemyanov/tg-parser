"""Integration tests for MCP list_mentioned_users tool."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import json
from pathlib import Path

import pytest


class TestMCPListMentionedUsers:
    """Test list_mentioned_users MCP tool."""

    @pytest.mark.asyncio
    async def test_list_mentioned_users_tool(
        self, supergroup_with_topics_path: Path
    ) -> None:
        """Test MCP tool returns correct structure."""
        from tg_parser.presentation.mcp.server import _list_mentioned_users

        result = await _list_mentioned_users(
            {
                "file_path": str(supergroup_with_topics_path),
                "min_count": 1,
            }
        )

        assert len(result) == 1
        data = json.loads(result[0].text)

        assert "chat_name" in data
        assert "total_mentions" in data
        assert "unique_users" in data
        assert "mentions" in data
        assert isinstance(data["mentions"], list)

    @pytest.mark.asyncio
    async def test_list_mentioned_users_with_date_filter(
        self, supergroup_with_topics_path: Path
    ) -> None:
        """Test date filtering in MCP tool."""
        from tg_parser.presentation.mcp.server import _list_mentioned_users

        result = await _list_mentioned_users(
            {
                "file_path": str(supergroup_with_topics_path),
                "date_from": "2025-01-01",
                "date_to": "2025-12-31",
            }
        )

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert "date_range" in data

    @pytest.mark.asyncio
    async def test_list_mentioned_users_min_count_filter(
        self, supergroup_with_topics_path: Path
    ) -> None:
        """Test min_count filtering in MCP tool."""
        from tg_parser.presentation.mcp.server import _list_mentioned_users

        result = await _list_mentioned_users(
            {
                "file_path": str(supergroup_with_topics_path),
                "min_count": 100,  # High threshold should return no mentions
            }
        )

        assert len(result) == 1
        data = json.loads(result[0].text)
        # With high min_count, unique_users should be 0 or very few
        assert data["unique_users"] == 0 or len(data["mentions"]) == 0

    @pytest.mark.asyncio
    async def test_list_mentioned_users_mention_structure(
        self, supergroup_with_topics_path: Path
    ) -> None:
        """Test mention object structure in MCP tool response."""
        from tg_parser.presentation.mcp.server import _list_mentioned_users

        result = await _list_mentioned_users(
            {
                "file_path": str(supergroup_with_topics_path),
            }
        )

        data = json.loads(result[0].text)

        for mention in data["mentions"]:
            assert "mention" in mention
            assert "count" in mention
            assert "participant_match" in mention  # Can be None
            assert "first_mention" in mention
            assert "last_mention" in mention


class TestMCPParseWithExtractionGuide:
    """Test parse_telegram_export MCP tool with extraction guide."""

    @pytest.mark.asyncio
    async def test_parse_with_extraction_guide_markdown(
        self, personal_chat_path: Path
    ) -> None:
        """Test MCP parse includes extraction guide in markdown."""
        from tg_parser.presentation.mcp.server import _parse_telegram_export

        result = await _parse_telegram_export(
            {
                "file_path": str(personal_chat_path),
                "output_format": "markdown",
                "include_extraction_guide": True,
            }
        )

        assert len(result) == 1
        content = result[0].text
        assert "Инструкция по извлечению артефактов" in content
        assert "Решения" in content

    @pytest.mark.asyncio
    async def test_parse_with_extraction_guide_json(
        self, personal_chat_path: Path
    ) -> None:
        """Test MCP parse includes extraction guide in JSON meta."""
        from tg_parser.presentation.mcp.server import _parse_telegram_export

        result = await _parse_telegram_export(
            {
                "file_path": str(personal_chat_path),
                "output_format": "json",
                "include_extraction_guide": True,
            }
        )

        assert len(result) == 1
        data = json.loads(result[0].text)
        assert "extraction_guide" in data["meta"]
        assert "Инструкция" in data["meta"]["extraction_guide"]

    @pytest.mark.asyncio
    async def test_parse_without_extraction_guide(
        self, personal_chat_path: Path
    ) -> None:
        """Test MCP parse without extraction guide flag."""
        from tg_parser.presentation.mcp.server import _parse_telegram_export

        result = await _parse_telegram_export(
            {
                "file_path": str(personal_chat_path),
                "output_format": "markdown",
                # include_extraction_guide not set, defaults to False
            }
        )

        assert len(result) == 1
        content = result[0].text
        assert "Инструкция по извлечению артефактов" not in content
