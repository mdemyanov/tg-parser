"""Tests for GetMentionsUseCase."""

from __future__ import annotations

from datetime import datetime

import pytest

from tg_parser.application.use_cases.get_mentions import (
    GetMentionsUseCase,
    MentionInfo,
    MentionsResult,
)
from tg_parser.domain.entities.chat import Chat, ChatType
from tg_parser.domain.entities.message import Message
from tg_parser.domain.entities.participant import Participant
from tg_parser.domain.value_objects.identifiers import MessageId, UserId


class TestGetMentionsUseCase:
    """Test GetMentionsUseCase."""

    def test_counts_mentions_correctly(self, chat_with_mentions: Chat) -> None:
        """Test that mentions are counted correctly."""
        use_case = GetMentionsUseCase()
        result = use_case.execute(chat_with_mentions)

        # 3 mentions for alice, 1 for bob
        assert result.total_mentions == 4
        assert result.unique_users == 2

    def test_min_count_filter(self, chat_with_mentions: Chat) -> None:
        """Test min_count filters out low-frequency mentions."""
        use_case = GetMentionsUseCase()
        result = use_case.execute(chat_with_mentions, min_count=2)

        # Only alice has 2+ mentions
        assert result.unique_users == 1
        assert result.mentions[0].mention == "alice"

    def test_participant_matching_by_username(
        self, chat_with_mentions: Chat
    ) -> None:
        """Test that mentions are matched to participants by username."""
        use_case = GetMentionsUseCase()
        result = use_case.execute(chat_with_mentions)

        alice_mention = next(
            (m for m in result.mentions if m.mention == "alice"), None
        )
        assert alice_mention is not None
        assert alice_mention.participant_match is not None
        assert alice_mention.participant_match.name == "Alice"

    def test_participant_matching_by_name(
        self, chat_with_mentions: Chat
    ) -> None:
        """Test partial name matching for mentions."""
        use_case = GetMentionsUseCase()
        result = use_case.execute(chat_with_mentions)

        # Check that @bob matches participant with "bob" in name
        bob_mention = next(
            (m for m in result.mentions if m.mention == "bob"), None
        )
        assert bob_mention is not None
        assert bob_mention.participant_match is not None
        assert bob_mention.participant_match.name == "Bob Smith"

    def test_mention_date_range(self, chat_with_mentions: Chat) -> None:
        """Test first_mention and last_mention dates."""
        use_case = GetMentionsUseCase()
        result = use_case.execute(chat_with_mentions)

        for m in result.mentions:
            assert m.first_mention <= m.last_mention

    def test_sorted_by_count_descending(
        self, chat_with_mentions: Chat
    ) -> None:
        """Test mentions are sorted by count in descending order."""
        use_case = GetMentionsUseCase()
        result = use_case.execute(chat_with_mentions)

        counts = [m.count for m in result.mentions]
        assert counts == sorted(counts, reverse=True)

    def test_empty_chat_no_mentions(self) -> None:
        """Test empty chat returns zero mentions."""
        chat = Chat(
            id=1,
            name="Empty Chat",
            chat_type=ChatType.SUPERGROUP,
            messages=[],
            topics={},
            participants={},
        )
        use_case = GetMentionsUseCase()
        result = use_case.execute(chat)

        assert result.total_mentions == 0
        assert result.unique_users == 0
        assert result.mentions == []

    def test_normalizes_mention_prefix(self) -> None:
        """Test that @ prefix is stripped from mentions."""
        messages = [
            Message(
                id=MessageId(1),
                timestamp=datetime(2025, 1, 15, 10, 0),
                author_name="User1",
                author_id=UserId("user1"),
                text="Hey @alice and alice",
                mentions=("@alice", "alice"),
            ),
        ]
        chat = Chat(
            id=1,
            name="Test",
            chat_type=ChatType.SUPERGROUP,
            messages=messages,
            topics={},
            participants={},
        )

        use_case = GetMentionsUseCase()
        result = use_case.execute(chat)

        # Both should be normalized to "alice"
        assert result.unique_users == 1
        assert result.total_mentions == 2
        assert result.mentions[0].mention == "alice"

    def test_no_participant_match(self) -> None:
        """Test mention without matching participant."""
        messages = [
            Message(
                id=MessageId(1),
                timestamp=datetime(2025, 1, 15, 10, 0),
                author_name="User1",
                author_id=UserId("user1"),
                text="Hey @unknown",
                mentions=("@unknown",),
            ),
        ]
        chat = Chat(
            id=1,
            name="Test",
            chat_type=ChatType.SUPERGROUP,
            messages=messages,
            topics={},
            participants={},
        )

        use_case = GetMentionsUseCase()
        result = use_case.execute(chat)

        assert result.mentions[0].participant_match is None


class TestMentionInfo:
    """Test MentionInfo dataclass."""

    def test_mention_info_creation(self) -> None:
        """Test MentionInfo dataclass creation."""
        info = MentionInfo(
            mention="alice",
            count=5,
            participant_match=None,
            first_mention=datetime(2025, 1, 1, 10, 0),
            last_mention=datetime(2025, 1, 15, 10, 0),
        )
        assert info.mention == "alice"
        assert info.count == 5


class TestMentionsResult:
    """Test MentionsResult dataclass."""

    def test_mentions_result_creation(self) -> None:
        """Test MentionsResult dataclass creation."""
        result = MentionsResult(
            chat_name="Test Chat",
            date_range=(datetime(2025, 1, 1), datetime(2025, 1, 31)),
            total_mentions=10,
            unique_users=3,
            mentions=[],
        )
        assert result.chat_name == "Test Chat"
        assert result.total_mentions == 10


@pytest.fixture
def chat_with_mentions() -> Chat:
    """Create a chat with various mentions for testing."""
    messages = [
        Message(
            id=MessageId(1),
            timestamp=datetime(2025, 1, 15, 10, 0),
            author_name="User1",
            author_id=UserId("user1"),
            text="Hey @alice, can you check this?",
            mentions=("@alice",),
        ),
        Message(
            id=MessageId(2),
            timestamp=datetime(2025, 1, 15, 11, 0),
            author_name="User1",
            author_id=UserId("user1"),
            text="@alice @bob please review",
            mentions=("@alice", "@bob"),
        ),
        Message(
            id=MessageId(3),
            timestamp=datetime(2025, 1, 16, 9, 0),
            author_name="User2",
            author_id=UserId("user2"),
            text="Thanks @alice!",
            mentions=("@alice",),
        ),
    ]

    participants = {
        UserId("user_alice"): Participant(
            id=UserId("user_alice"),
            name="Alice",
            username="alice",
            message_count=0,
        ),
        UserId("user_bob"): Participant(
            id=UserId("user_bob"),
            name="Bob Smith",
            username="bobsmith",
            message_count=0,
        ),
    }

    return Chat(
        id=123,
        name="Test Chat",
        chat_type=ChatType.SUPERGROUP,
        messages=messages,
        topics={},
        participants=participants,
    )
