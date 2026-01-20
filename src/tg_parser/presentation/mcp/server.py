"""MCP server implementation for tg-parser.

Provides tools for parsing Telegram exports via MCP protocol.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from tg_parser.application.use_cases.get_statistics import GetStatisticsUseCase
from tg_parser.application.use_cases.parse_chat import ParseChatUseCase
from tg_parser.domain.value_objects.date_range import DateRange
from tg_parser.domain.value_objects.filter_spec import FilterSpecification

# Create server instance
server = Server("tg-parser")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="parse_telegram_export",
            description="Parse a Telegram Desktop JSON export file and return messages in LLM-friendly format.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to Telegram JSON export file (result.json)",
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date filter (YYYY-MM-DD format)",
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date filter (YYYY-MM-DD format)",
                    },
                    "senders": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter to include only messages from these senders",
                    },
                    "exclude_senders": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Exclude messages from these senders",
                    },
                    "topics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter to include only messages from these topics (partial match, case-insensitive)",
                    },
                    "exclude_topics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Exclude messages from these topics (partial match, case-insensitive)",
                    },
                    "contains": {
                        "type": "string",
                        "description": "Filter messages containing this text (regex)",
                    },
                    "include_service": {
                        "type": "boolean",
                        "description": "Include service/system messages",
                        "default": False,
                    },
                    "exclude_forwards": {
                        "type": "boolean",
                        "description": "Exclude forwarded messages",
                        "default": False,
                    },
                    "max_messages": {
                        "type": "integer",
                        "description": "Maximum number of messages to return",
                        "default": 1000,
                    },
                    "output_format": {
                        "type": "string",
                        "enum": ["markdown", "kb", "json", "csv"],
                        "description": "Output format: markdown (default), kb (with frontmatter), json, csv",
                        "default": "markdown",
                    },
                    "include_extraction_guide": {
                        "type": "boolean",
                        "description": "Append Russian-language artifact extraction template to output",
                        "default": False,
                    },
                    "streaming": {
                        "type": "boolean",
                        "description": "Force streaming mode for large files. Default: auto (>50MB uses streaming if ijson available).",
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="get_chat_statistics",
            description="Get statistics about a Telegram chat export (message counts, participants, topics, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to Telegram JSON export file (result.json)",
                    },
                    "top_senders": {
                        "type": "integer",
                        "description": "Number of top senders to include",
                        "default": 10,
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="list_chat_participants",
            description="List all participants in a Telegram chat export with their message counts.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to Telegram JSON export file (result.json)",
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="list_chat_topics",
            description="List all topics/threads in a Telegram forum (supergroup with topics enabled).",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to Telegram JSON export file (result.json)",
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="chunk_telegram_export",
            description="Chunk a Telegram export into LLM-friendly pieces using various strategies.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to Telegram JSON export file (result.json)",
                    },
                    "strategy": {
                        "type": "string",
                        "enum": ["fixed", "topic", "hybrid"],
                        "description": "Chunking strategy: fixed (by tokens), topic (by forum topic), hybrid (topic + time split)",
                        "default": "fixed",
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens per chunk",
                        "default": 8000,
                    },
                    "chunk_index": {
                        "type": "integer",
                        "description": "Return only this chunk (0-based index). If not provided, returns summary.",
                    },
                    "include_extraction_guide": {
                        "type": "boolean",
                        "description": "Append Russian-language artifact extraction template to output",
                        "default": False,
                    },
                    "streaming": {
                        "type": "boolean",
                        "description": "Force streaming mode for large files. Default: auto (>50MB uses streaming if ijson available).",
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="list_mentioned_users",
            description="Extract all @mentions from a Telegram chat with frequency counts and participant matching.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to Telegram JSON export file (result.json)",
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date filter (YYYY-MM-DD format)",
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date filter (YYYY-MM-DD format)",
                    },
                    "min_count": {
                        "type": "integer",
                        "description": "Minimum mention count to include",
                        "default": 1,
                    },
                },
                "required": ["file_path"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "parse_telegram_export":
            return await _parse_telegram_export(arguments)
        elif name == "get_chat_statistics":
            return await _get_chat_statistics(arguments)
        elif name == "list_chat_participants":
            return await _list_chat_participants(arguments)
        elif name == "list_chat_topics":
            return await _list_chat_topics(arguments)
        elif name == "chunk_telegram_export":
            return await _chunk_telegram_export(arguments)
        elif name == "list_mentioned_users":
            return await _list_mentioned_users(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except FileNotFoundError as e:
        return [TextContent(type="text", text=f"File not found: {e}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]


async def _parse_telegram_export(args: dict[str, Any]) -> list[TextContent]:
    """Parse Telegram export and return formatted messages."""
    import re

    from tg_parser.infrastructure.writers import (
        JSONWriter,
        KBTemplateWriter,
        MarkdownWriter,
    )

    file_path = Path(args["file_path"])
    max_messages = args.get("max_messages", 1000)
    output_format = args.get("output_format", "markdown")
    include_extraction_guide = args.get("include_extraction_guide", False)

    # Build filter specification
    date_range: DateRange | None = None
    if args.get("date_from") or args.get("date_to"):
        start = (
            datetime.fromisoformat(args["date_from"]) if args.get("date_from") else None
        )
        end = datetime.fromisoformat(args["date_to"]) if args.get("date_to") else None
        date_range = DateRange(start=start, end=end)

    senders = frozenset(args.get("senders", []))
    exclude_senders = frozenset(args.get("exclude_senders", []))
    topics = frozenset(args.get("topics", []))
    exclude_topics = frozenset(args.get("exclude_topics", []))

    content_pattern = None
    if args.get("contains"):
        content_pattern = re.compile(args["contains"], re.IGNORECASE)

    filter_spec = FilterSpecification(
        date_range=date_range,
        senders=senders if senders else frozenset(),
        exclude_senders=exclude_senders if exclude_senders else frozenset(),
        topics=topics if topics else frozenset(),
        exclude_topics=exclude_topics if exclude_topics else frozenset(),
        content_pattern=content_pattern,
        exclude_service=not args.get("include_service", False),
        exclude_forwards=args.get("exclude_forwards", False),
    )

    # Parse chat (with optional streaming mode)
    streaming = args.get("streaming")  # None = auto-detect
    use_case = ParseChatUseCase(streaming=streaming)
    chat = use_case.execute(file_path, filter_spec)

    # Limit messages if needed
    if len(chat.messages) > max_messages:
        # Create a modified chat with limited messages
        from tg_parser.domain.entities.chat import Chat

        chat = Chat(
            id=chat.id,
            name=chat.name,
            chat_type=chat.chat_type,
            messages=chat.messages[:max_messages],
            topics=chat.topics,
            participants=chat.participants,
        )

    # Format output based on requested format
    if output_format == "json":
        writer = JSONWriter(include_extraction_guide=include_extraction_guide)
        result = writer.format_to_string(chat)
    elif output_format == "kb":
        writer_kb = KBTemplateWriter(include_extraction_guide=include_extraction_guide)
        result = writer_kb.format_to_string(chat)
    else:
        writer_md = MarkdownWriter(include_extraction_guide=include_extraction_guide)
        result = writer_md.format_to_string(chat)

    return [TextContent(type="text", text=result)]


async def _get_chat_statistics(args: dict[str, Any]) -> list[TextContent]:
    """Get chat statistics."""
    file_path = Path(args["file_path"])
    top_senders = args.get("top_senders", 10)

    # Parse and get stats
    parse_use_case = ParseChatUseCase()
    chat = parse_use_case.execute(file_path)

    stats_use_case = GetStatisticsUseCase()
    stats = stats_use_case.execute(chat, top_senders_count=top_senders)

    # Format output
    date_range_data: dict[str, str] | None = None
    if stats.date_range:
        date_range_data = {
            "start": stats.date_range[0].isoformat(),
            "end": stats.date_range[1].isoformat(),
        }

    result: dict[str, Any] = {
        "chat_name": stats.chat_name,
        "chat_type": stats.chat_type,
        "total_messages": stats.total_messages,
        "participants_count": stats.participants_count,
        "estimated_tokens": stats.estimated_tokens,
        "date_range": date_range_data,
        "top_senders": stats.top_senders,
        "messages_by_topic": stats.messages_by_topic,
    }

    return [
        TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))
    ]


async def _list_chat_participants(args: dict[str, Any]) -> list[TextContent]:
    """List chat participants."""
    file_path = Path(args["file_path"])

    parse_use_case = ParseChatUseCase()
    chat = parse_use_case.execute(file_path)

    participants = [
        {
            "name": p.name,
            "id": p.id,
            "username": p.username,
            "message_count": p.message_count,
        }
        for p in sorted(
            chat.participants.values(),
            key=lambda x: x.message_count,
            reverse=True,
        )
    ]

    return [
        TextContent(
            type="text", text=json.dumps(participants, indent=2, ensure_ascii=False)
        )
    ]


async def _list_chat_topics(args: dict[str, Any]) -> list[TextContent]:
    """List chat topics."""
    file_path = Path(args["file_path"])

    parse_use_case = ParseChatUseCase()
    chat = parse_use_case.execute(file_path)

    if not chat.topics:
        return [
            TextContent(
                type="text", text="This chat does not have topics (not a forum)."
            )
        ]

    # Count messages per topic
    topic_message_counts: dict[int, int] = {}
    for msg in chat.messages:
        if msg.topic_id:
            current = topic_message_counts.get(msg.topic_id, 0)
            topic_message_counts[msg.topic_id] = current + 1

    topics = [
        {
            "id": topic.id,
            "title": topic.title,
            "is_general": topic.is_general,
            "created_at": topic.created_at.isoformat() if topic.created_at else None,
            "message_count": topic_message_counts.get(topic.id, 0),
        }
        for topic in sorted(
            chat.topics.values(),
            key=lambda x: topic_message_counts.get(x.id, 0),
            reverse=True,
        )
    ]

    result_json = json.dumps(topics, indent=2, ensure_ascii=False)
    return [TextContent(type="text", text=result_json)]


async def _chunk_telegram_export(args: dict[str, Any]) -> list[TextContent]:
    """Chunk Telegram export into LLM-friendly pieces."""
    from tg_parser.application.use_cases.chunk_chat import ChunkChatUseCase

    file_path = Path(args["file_path"])
    strategy = args.get("strategy", "fixed")
    max_tokens = args.get("max_tokens", 8000)
    chunk_index = args.get("chunk_index")
    streaming = args.get("streaming")  # None = auto-detect

    # Execute chunking (with optional streaming mode)
    use_case = ChunkChatUseCase(streaming=streaming)
    result = use_case.execute(file_path, strategy=strategy, max_tokens=max_tokens)

    if not result.chunks:
        return [TextContent(type="text", text="No messages to chunk.")]

    # If specific chunk requested, return it
    if chunk_index is not None:
        if chunk_index < 0 or chunk_index >= len(result.chunks):
            max_idx = len(result.chunks) - 1
            msg = f"Invalid chunk index: {chunk_index}. Valid range: 0-{max_idx}"
            return [TextContent(type="text", text=msg)]

        chunk_obj = result.chunks[chunk_index]
        return _format_single_chunk(chunk_obj, result)

    # Return summary
    return _format_chunk_summary(result)


def _format_single_chunk(chunk_obj: Any, result: Any) -> list[TextContent]:
    """Format a single chunk for MCP output."""
    meta = chunk_obj.metadata
    lines = []

    # Header
    lines.append(f"# Chunk {meta.chunk_index + 1} of {meta.total_chunks}")
    lines.append(f"Chat: {result.chat_name}")
    lines.append(f"Strategy: {meta.strategy}")

    if meta.topic_title:
        if meta.total_parts > 1:
            part_info = f"(Part {meta.part_number}/{meta.total_parts})"
            lines.append(f"Topic: {meta.topic_title} {part_info}")
        else:
            lines.append(f"Topic: {meta.topic_title}")

    if meta.date_range_start and meta.date_range_end:
        start = meta.date_range_start.isoformat()
        end = meta.date_range_end.isoformat()
        lines.append(f"Period: {start} to {end}")

    lines.append(f"Messages: {chunk_obj.message_count}")
    lines.append(f"Estimated tokens: {meta.estimated_tokens}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Messages
    current_date = None
    for msg in chunk_obj.messages:
        msg_date = msg.timestamp.date()
        if msg_date != current_date:
            current_date = msg_date
            lines.append(f"\n## {msg_date}\n")

        time_str = msg.timestamp.strftime("%H:%M")
        text = msg.text.replace("\n", " ").strip()
        if len(text) > 500:
            text = text[:500] + "..."

        lines.append(f"[{time_str}] **{msg.author_name}**: {text}")

    return [TextContent(type="text", text="\n".join(lines))]


def _format_chunk_summary(result: Any) -> list[TextContent]:
    """Format chunk summary for MCP output."""
    summary: dict[str, Any] = {
        "chat_name": result.chat_name,
        "strategy": result.strategy,
        "total_chunks": len(result.chunks),
        "total_messages": result.total_messages,
        "total_tokens": result.total_tokens,
        "chunks": [
            {
                "index": c.metadata.chunk_index,
                "messages": c.message_count,
                "tokens": c.metadata.estimated_tokens,
                "topic": c.metadata.topic_title,
                "part": (
                    f"{c.metadata.part_number}/{c.metadata.total_parts}"
                    if c.metadata.total_parts > 1
                    else None
                ),
                "date_range": {
                    "start": (
                        c.metadata.date_range_start.isoformat()
                        if c.metadata.date_range_start
                        else None
                    ),
                    "end": (
                        c.metadata.date_range_end.isoformat()
                        if c.metadata.date_range_end
                        else None
                    ),
                },
            }
            for c in result.chunks
        ],
    }

    result_json = json.dumps(summary, indent=2, ensure_ascii=False)
    return [TextContent(type="text", text=result_json)]


async def _list_mentioned_users(args: dict[str, Any]) -> list[TextContent]:
    """List mentioned users with statistics."""
    from tg_parser.application.use_cases.get_mentions import GetMentionsUseCase

    file_path = Path(args["file_path"])
    min_count = args.get("min_count", 1)

    # Build filter spec
    date_range: DateRange | None = None
    if args.get("date_from") or args.get("date_to"):
        date_from = args.get("date_from")
        date_to = args.get("date_to")
        start = datetime.fromisoformat(date_from) if date_from else None
        end = datetime.fromisoformat(date_to) if date_to else None
        date_range = DateRange(start=start, end=end)

    filter_spec = FilterSpecification(date_range=date_range)

    # Parse and analyze
    parse_use_case = ParseChatUseCase()
    chat = parse_use_case.execute(file_path, filter_spec)

    mentions_use_case = GetMentionsUseCase()
    result = mentions_use_case.execute(chat, min_count=min_count)

    # Format output (match CLI JSON format)
    output: dict[str, Any] = {
        "chat_name": result.chat_name,
        "date_range": {
            "start": result.date_range[0].isoformat() if result.date_range else None,
            "end": result.date_range[1].isoformat() if result.date_range else None,
        },
        "total_mentions": result.total_mentions,
        "unique_users": result.unique_users,
        "mentions": [
            {
                "mention": m.mention,
                "count": m.count,
                "participant_match": {
                    "id": m.participant_match.id,
                    "name": m.participant_match.name,
                    "username": m.participant_match.username,
                }
                if m.participant_match
                else None,
                "first_mention": m.first_mention.isoformat(),
                "last_mention": m.last_mention.isoformat(),
            }
            for m in result.mentions
        ],
    }

    result_json = json.dumps(output, indent=2, ensure_ascii=False)
    return [TextContent(type="text", text=result_json)]


def run_mcp_server() -> None:
    """Run the MCP server."""
    import asyncio

    asyncio.run(main())


async def main() -> None:
    """Main entry point for MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        init_options = server.create_initialization_options()
        await server.run(read_stream, write_stream, init_options)
