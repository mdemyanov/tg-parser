# PRD: Telegram Chat Parser for LLM Processing

**Версия:** 1.0.0
**Дата:** 2026-01-20
**Автор:** CTO Office
**Статус:** v1.0.0 Released – Planning v1.1.0  

---

## 1. Executive Summary

### 1.1 Проблема

Руководители и специалисты тратят значительное время на отслеживание информации в корпоративных Telegram-чатах. Ключевые решения, задачи, договорённости и конфликты растворяются в потоке сообщений. Существующие инструменты либо не поддерживают специфику Telegram (топики, форвардинг, реакции), либо не оптимизированы для последующей LLM-обработки.

### 1.2 Решение

**tg-parser** — Python CLI/MCP инструмент для:
- Парсинга JSON-экспортов Telegram Desktop
- Очистки и нормализации данных для LLM
- Параметрической фильтрации по любым критериям
- Разделения по топикам/диалогам в отдельные файлы
- Подготовки данных для саммаризации через Claude

### 1.3 Целевая аудитория

| Персона | Потребность | Частота использования |
|---------|-------------|----------------------|
| CTO/руководитель | Еженедельный дайджест команды | 1-2 раза в неделю |
| Менеджер проекта | Трекинг задач и решений | Ежедневно |
| Аналитик | Исследование коммуникаций | По запросу |
| Разработчик | Интеграция в пайплайны | Автоматизация |

### 1.4 Метрики успеха

| Метрика | Baseline | Target |
|---------|----------|--------|
| Время подготовки данных | 30-60 мин (вручную) | < 2 мин |
| Качество очистки | N/A | > 95% релевантных сообщений |
| Потеря контекста | N/A | < 5% при chunking |
| Adoption | 0 | 10+ пользователей за 3 месяца |

### 1.5 Implementation Status (v1.0.0)

**Статус:** Production release опубликован на PyPI и GitHub

#### Реализовано ✅

| Компонент | Детали |
|-----------|--------|
| Domain Layer | Message, Chat, Topic, Participant entities; MessageId, UserId, TopicId, DateRange, FilterSpecification value objects |
| Application Layer | ParseChatUseCase, GetStatisticsUseCase, ChunkChatUseCase, GetMentionsUseCase (с поддержкой streaming) |
| Infrastructure Layer | TelegramJSONReader, TelegramStreamReader (ijson), MarkdownWriter, JSONWriter, KBTemplateWriter, 9 фильтров, SimpleTokenCounter, 3 chunking стратегии |
| CLI | `parse`, `stats`, `chunk`, `mentions` команды с фильтрами; --streaming/--no-streaming флаги с auto-detection |
| MCP Server | 6 инструментов: parse_telegram_export, chunk_telegram_export, get_chat_statistics, list_chat_participants, list_chat_topics, list_mentioned_users (все с поддержкой streaming) |
| Streaming | TelegramStreamReader с ijson, reader factory с auto-detection (>50MB), progress bars в CLI |
| GitHub & CI/CD | **Репозиторий на GitHub, 4 GitHub Actions workflows (tests, typecheck, lint, publish)** |
| PyPI | **Пакет опубликован как `tg-parser` v1.0.0** |
| Тесты | **261 тест** (unit + integration), pyright strict mode, 257/259 passing (99.2%) |

#### Не реализовано ❌

| Компонент | Приоритет | Описание |
|-----------|-----------|----------|
| split-topics команда | P1 | Отдельная команда разделения по топикам (работает через флаг `--split-topics` в parse) |
| CSV output | P2 | CSV формат вывода |
| tiktoken | P2 | Точный подсчёт токенов (есть SimpleTokenCounter) |
| Config file | P3 | Файл конфигурации |
| Anonymization | P3 | Анонимизация участников |

---

## 2. Функциональные требования

### 2.1 Поддерживаемые типы чатов

| Тип | Описание | Особенности парсинга |
|-----|----------|---------------------|
| **Personal** | Личная переписка 1-1 | Два участника, простая структура |
| **Group** | Обычная группа до 200 человек | Несколько участников, нет топиков |
| **Supergroup** | Супергруппа до 200K участников | Возможны топики, reply threads |
| **Supergroup (Forum)** | Супергруппа с топиками | Полноценные топики как подфорумы |
| **Channel** | Канал с комментариями | Посты + linked discussion group |

### 2.2 Входные данные

**Формат:** JSON-экспорт Telegram Desktop  
**Путь:** Локальный файл или директория с экспортами  
**Размер:** До 500MB на файл (streaming для больших)

**Структура экспорта Telegram Desktop:**
```json
{
  "name": "Chat Name",
  "type": "personal_chat | private_group | private_supergroup | public_supergroup | ...",
  "id": 123456789,
  "messages": [
    {
      "id": 1,
      "type": "message | service",
      "date": "2025-01-15T10:30:00",
      "date_unixtime": "1736937000",
      "from": "Иван Петров",
      "from_id": "user123456",
      "text": "Текст сообщения" | [{"type": "text_link", "text": "..."}],
      "reply_to_message_id": 42,
      "forwarded_from": "Channel Name",
      "media_type": "photo | video | voice_message | ...",
      "file": "photos/photo_1.jpg",
      "reactions": [{"emoji": "👍", "count": 3}],
      "text_entities": [...]
    }
  ]
}
```

### 2.3 Выходные данные

#### 2.3.1 Основной формат — Markdown (LLM-optimized)

```markdown
# Chat: Команда разработки
**Период:** 2025-01-13 — 2025-01-19  
**Участники:** Иван Петров, Мария Сидорова, Алексей Козлов  
**Сообщений:** 127  

---

## 2025-01-15

### 10:30 — Иван Петров
Коллеги, нужно обсудить архитектуру нового модуля.
> Ответ на: "Когда планируем старт?" от Мария Сидорова

### 10:35 — Мария Сидорова
@Алексей, подготовь диаграмму к завтра.
[📎 Файл: architecture_draft.pdf]

---
```

#### 2.3.2 Структурированный формат — JSON

```json
{
  "meta": {
    "chat_name": "Команда разработки",
    "chat_type": "supergroup_forum",
    "export_date": "2025-01-19T12:00:00Z",
    "filter_applied": {
      "date_from": "2025-01-13",
      "date_to": "2025-01-19",
      "senders": null,
      "topics": ["general", "architecture"]
    },
    "statistics": {
      "total_messages": 127,
      "filtered_messages": 98,
      "participants": 5,
      "tokens_estimate": 15000
    }
  },
  "messages": [
    {
      "id": 1234,
      "timestamp": "2025-01-15T10:30:00Z",
      "author": "Иван Петров",
      "author_id": "user123456",
      "text": "Коллеги, нужно обсудить архитектуру нового модуля.",
      "reply_to": {
        "id": 1230,
        "author": "Мария Сидорова",
        "preview": "Когда планируем старт?"
      },
      "mentions": ["Алексей Козлов"],
      "attachments": [],
      "reactions": {"👍": 3, "🔥": 1},
      "topic": "architecture"
    }
  ]
}
```

#### 2.3.3 Chunked формат для LLM

```
output/
├── chat_name/
│   ├── meta.json           # Метаданные чата
│   ├── full.md             # Полный экспорт
│   ├── topics/
│   │   ├── general.md
│   │   ├── architecture.md
│   │   └── bugs.md
│   └── chunks/
│       ├── chunk_001.md    # 3000 токенов
│       ├── chunk_002.md
│       └── manifest.json   # Индекс чанков
```

### 2.4 Параметры фильтрации

| Параметр | Тип | Описание | Пример |
|----------|-----|----------|--------|
| `--date-from` | date | Начальная дата | `2025-01-01` |
| `--date-to` | date | Конечная дата | `2025-01-19` |
| `--last-days` | int | Последние N дней | `7` |
| `--last-hours` | int | Последние N часов | `24` |
| `--senders` | list[str] | Фильтр по отправителям | `"Иван Петров,Мария"` |
| `--sender-ids` | list[str] | Фильтр по ID отправителей | `"user123,user456"` |
| `--exclude-senders` | list[str] | Исключить отправителей | `"Bot,System"` |
| `--topics` | list[str] | Только указанные топики | `"general,bugs"` |
| `--exclude-topics` | list[str] | Исключить топики | `"offtopic,flood"` |
| `--mentions` | list[str] | Сообщения с упоминанием | `"@Иван"` |
| `--contains` | str | Поиск по тексту (regex) | `"deadline\|срок"` |
| `--has-attachment` | bool | Только с вложениями | `true` |
| `--has-reactions` | bool | Только с реакциями | `true` |
| `--min-length` | int | Минимальная длина текста | `10` |
| `--exclude-forwards` | bool | Исключить пересланные | `true` |
| `--exclude-service` | bool | Исключить служебные | `true` (default) |

### 2.5 Streaming Mode

**Автоматический выбор режима:**

tg-parser автоматически выбирает оптимальный режим обработки на основе размера файла:

| Размер файла | Режим | Память | Скорость |
|--------------|-------|--------|----------|
| < 50MB | JSON Reader | O(n) - весь файл в памяти | Быстро |
| ≥ 50MB | Stream Reader (ijson) | O(1) - константная | Медленнее (~20% overhead) |

**Ручной выбор режима:**

```bash
# Auto-detection (рекомендуется)
tg-parser parse ./export.json -o ./output/

# Принудительный streaming (требует ijson)
tg-parser parse ./large_export.json --streaming -o ./output/

# Принудительный non-streaming (быстрее для малых файлов)
tg-parser parse ./small_export.json --no-streaming -o ./output/
```

**Progress tracking:**

При использовании streaming режима отображается прогресс-бар:

```
Parsing... ━━━━━━━━━━━━━━━━━━━━━━━━━━━ 75% 7500/10000 messages
```

**Требования:**

- Streaming режим требует установки `ijson>=3.2.0`
- Установка: `uv sync --extra streaming` или `pip install tg-parser[streaming]`
- Без ijson: автоматический fallback к JSON Reader

### 2.6 Режимы обработки

#### 2.6.1 CLI Mode

```bash
# Базовый парсинг (auto-detection streaming для файлов >50MB)
tg-parser parse ./export/result.json -o ./output/

# Принудительный streaming с прогресс-баром
tg-parser parse ./large_export.json --streaming -o ./output/

# С фильтрами
tg-parser parse ./export/result.json \
  --date-from 2025-01-01 \
  --senders "Иван Петров" \
  --topics "architecture" \
  --format markdown \
  -o ./output/

# Разделение по топикам (TODO: пока не реализовано)
tg-parser split-topics ./export/result.json -o ./output/topics/

# Chunking для LLM (с поддержкой streaming)
tg-parser chunk ./export/result.json \
  --strategy conversation \
  --max-tokens 3000 \
  --overlap 100 \
  --streaming \
  -o ./output/chunks/

# Статистика
tg-parser stats ./export/result.json

# Валидация экспорта (TODO: пока не реализовано)
tg-parser validate ./export/result.json
```

#### 2.5.2 MCP Mode

```json
{
  "mcpServers": {
    "tg-parser": {
      "command": "uvx",
      "args": ["tg-parser", "mcp"],
      "env": {
        "TG_PARSER_OUTPUT_DIR": "/path/to/output"
      }
    }
  }
}
```

**MCP Tools:**

| Tool | Описание |
|------|----------|
| `parse_telegram_export` | Парсинг JSON-экспорта с фильтрами |
| `chunk_telegram_export` | Chunking для LLM с выбором стратегии |
| `get_chat_statistics` | Статистика чата (сообщения, участники, топики) |
| `list_chat_participants` | Список участников с количеством сообщений |
| `list_chat_topics` | Список топиков форума с количеством сообщений |
| `list_mentioned_users` | Анализ @упоминаний с частотой |

### 2.6 Очистка данных

#### 2.6.1 Удаляемые элементы (по умолчанию)

| Категория | Примеры | Настройка |
|-----------|---------|-----------|
| Service messages | join/leave, pin, photo change | `--exclude-service` |
| Empty messages | Только медиа без текста | `--exclude-media-only` |
| System metadata | `text_entities`, внутренние ID | Всегда |
| Duplicate forwards | Повторные пересылки | `--dedupe-forwards` |
| Bot commands | `/start`, `/help` | `--exclude-commands` |
| Stickers (опционально) | Стикеры без текста | `--exclude-stickers` |

#### 2.6.2 Нормализация

| Поле | Исходный формат | Нормализованный |
|------|-----------------|-----------------|
| Дата | `"2025-01-15T10:30:00"` | ISO 8601 UTC |
| Текст (массив) | `[{"type":"bold","text":"Hi"}]` | `**Hi**` (markdown) |
| Упоминания | `@username` | `@Полное Имя` (если известно) |
| Ссылки | `text_link` entity | `[текст](url)` |
| Цитаты | `reply_to_message_id` | `> Цитата` + источник |

### 2.7 Chunking стратегии

| Стратегия | Описание | Когда использовать |
|-----------|----------|-------------------|
| `fixed` | Фиксированный размер токенов | Простые случаи |
| `conversation` | По временным промежуткам + размер | **Рекомендуется** |
| `topic` | По топикам (для forum) | Супергруппы с топиками |
| `daily` | По дням | Длинные периоды |
| `author` | По смене автора | Анализ диалогов |

**Параметры chunking:**

```bash
tg-parser chunk input.md \
  --strategy conversation \
  --max-tokens 3000 \        # Максимум токенов в чанке
  --min-tokens 500 \         # Минимум (избегать микрочанков)
  --time-gap 30 \            # Минут тишины для разрыва
  --overlap 100 \            # Токенов перекрытия
  --preserve-threads         # Не разрывать reply-цепочки
```

---

## 3. Нефункциональные требования

### 3.1 Производительность

| Метрика | Требование |
|---------|------------|
| Парсинг 100MB JSON | < 30 секунд |
| Парсинг 500MB JSON (streaming) | < 3 минут |
| Память при streaming | < 256MB |
| Chunking 10000 сообщений | < 5 секунд |

### 3.2 Надёжность

- Graceful handling невалидного JSON
- Продолжение при ошибках отдельных сообщений (с логированием)
- Идемпотентность: повторный запуск даёт идентичный результат
- Валидация входных данных с понятными ошибками

### 3.3 Совместимость

| Требование | Версия |
|------------|--------|
| Python | >= 3.11 |
| Telegram Desktop export | Текущий формат (2024-2025) |
| MCP Protocol | 1.0 |
| OS | macOS, Linux, Windows (WSL) |

### 3.4 Безопасность

- Локальная обработка (никаких внешних API для парсинга)
- Опциональная анонимизация имён участников
- Исключение чувствительных паттернов (номера карт, пароли)
- Не сохранение исходных файлов в output

---

## 4. Архитектура

### 4.1 Принципы

| Принцип | Применение |
|---------|------------|
| **Clean Architecture** | Разделение Domain / Application / Infrastructure |
| **Dependency Injection** | Через протоколы и фабрики |
| **Single Responsibility** | Один модуль = одна задача |
| **Open/Closed** | Расширение через плагины (стратегии, фильтры) |
| **Interface Segregation** | Узкие протоколы для каждой роли |

### 4.2 Слои архитектуры

```
┌─────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   CLI       │  │   MCP       │  │   Python API            │  │
│  │   (Typer)   │  │   Server    │  │   (Library mode)        │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
└─────────┼────────────────┼─────────────────────┼────────────────┘
          │                │                     │
          ▼                ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Use Cases                            │    │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌─────────┐  │    │
│  │  │ ParseChat │ │ SplitBy   │ │ ChunkFor  │ │ Get     │  │    │
│  │  │           │ │ Topics    │ │ LLM       │ │ Stats   │  │    │
│  │  └───────────┘ └───────────┘ └───────────┘ └─────────┘  │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Services                             │    │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌─────────┐  │    │
│  │  │ Filter    │ │ Normalizer│ │ Chunker   │ │ Token   │  │    │
│  │  │ Service   │ │ Service   │ │ Service   │ │ Counter │  │    │
│  │  └───────────┘ └───────────┘ └───────────┘ └─────────┘  │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
          │                │                     │
          ▼                ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                       DOMAIN LAYER                              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Entities                             │    │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌─────────┐  │    │
│  │  │ Chat      │ │ Message   │ │ Topic     │ │ Parti-  │  │    │
│  │  │           │ │           │ │           │ │ cipant  │  │    │
│  │  └───────────┘ └───────────┘ └───────────┘ └─────────┘  │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Value Objects                        │    │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌─────────┐  │    │
│  │  │ MessageId │ │ UserId    │ │ TopicId   │ │ Date    │  │    │
│  │  │           │ │           │ │           │ │ Range   │  │    │
│  │  └───────────┘ └───────────┘ └───────────┘ └─────────┘  │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Protocols (Ports)                    │    │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐              │    │
│  │  │ ChatReader│ │ ChatWriter│ │ Filter    │              │    │
│  │  │ Protocol  │ │ Protocol  │ │ Protocol  │              │    │
│  │  └───────────┘ └───────────┘ └───────────┘              │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
          │                │                     │
          ▼                ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    INFRASTRUCTURE LAYER                         │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Adapters                             │    │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌─────────┐  │    │
│  │  │ Telegram  │ │ Markdown  │ │ JSON      │ │ Tiktoken│  │    │
│  │  │ JSONReader│ │ Writer    │ │ Writer    │ │ Counter │  │    │
│  │  └───────────┘ └───────────┘ └───────────┘ └─────────┘  │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    External                             │    │
│  │  ┌───────────┐ ┌───────────┐                            │    │
│  │  │ File      │ │ Streaming │                            │    │
│  │  │ System    │ │ JSON      │                            │    │
│  │  └───────────┘ └───────────┘                            │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 Структура проекта

```
tg-parser/
├── pyproject.toml              # Конфигурация проекта (uv/hatch)
├── README.md                   # Документация
├── CLAUDE.md                   # Инструкции для AI-ассистента
├── LICENSE                     # MIT
│
├── src/
│   └── tg_parser/
│       ├── __init__.py
│       ├── __main__.py         # Entry point
│       ├── py.typed            # PEP 561 marker
│       │
│       ├── domain/             # === DOMAIN LAYER ===
│       │   ├── __init__.py
│       │   ├── entities/
│       │   │   ├── __init__.py
│       │   │   ├── chat.py         # Chat, ChatType, ChatMeta
│       │   │   ├── message.py      # Message, MessageType, Attachment
│       │   │   ├── topic.py        # Topic
│       │   │   └── participant.py  # Participant
│       │   │
│       │   ├── value_objects/
│       │   │   ├── __init__.py
│       │   │   ├── identifiers.py  # MessageId, UserId, TopicId
│       │   │   ├── date_range.py   # DateRange
│       │   │   └── filter_spec.py  # FilterSpecification
│       │   │
│       │   ├── protocols/
│       │   │   ├── __init__.py
│       │   │   ├── reader.py       # ChatReaderProtocol
│       │   │   ├── writer.py       # ChatWriterProtocol
│       │   │   ├── filter.py       # FilterProtocol
│       │   │   └── chunker.py      # ChunkerProtocol
│       │   │
│       │   └── exceptions.py       # Domain exceptions
│       │
│       ├── application/        # === APPLICATION LAYER ===
│       │   ├── __init__.py
│       │   ├── use_cases/
│       │   │   ├── __init__.py
│       │   │   ├── parse_chat.py       # ParseChatUseCase
│       │   │   ├── split_topics.py     # SplitByTopicsUseCase
│       │   │   ├── chunk_for_llm.py    # ChunkForLLMUseCase
│       │   │   ├── get_statistics.py   # GetStatisticsUseCase
│       │   │   └── search_messages.py  # SearchMessagesUseCase
│       │   │
│       │   ├── services/
│       │   │   ├── __init__.py
│       │   │   ├── filter_service.py   # Composite filter logic
│       │   │   ├── normalizer.py       # Text normalization
│       │   │   ├── chunker.py          # Chunking strategies
│       │   │   └── token_counter.py    # Token estimation
│       │   │
│       │   └── dto/
│       │       ├── __init__.py
│       │       ├── parse_request.py    # Input DTOs
│       │       └── parse_result.py     # Output DTOs
│       │
│       ├── infrastructure/     # === INFRASTRUCTURE LAYER ===
│       │   ├── __init__.py
│       │   ├── readers/
│       │   │   ├── __init__.py
│       │   │   ├── _parsing.py         # Shared parsing functions (NEW)
│       │   │   ├── telegram_json.py    # Standard JSON reader
│       │   │   └── telegram_stream.py  # Streaming for large files (NEW)
│       │   │
│       │   ├── writers/
│       │   │   ├── __init__.py
│       │   │   ├── markdown.py         # Markdown output
│       │   │   ├── json_writer.py      # JSON output
│       │   │   └── csv_writer.py       # CSV output
│       │   │
│       │   ├── filters/
│       │   │   ├── __init__.py
│       │   │   ├── date_filter.py
│       │   │   ├── sender_filter.py
│       │   │   ├── topic_filter.py
│       │   │   ├── content_filter.py
│       │   │   └── composite.py        # AND/OR composition
│       │   │
│       │   ├── chunkers/
│       │   │   ├── __init__.py
│       │   │   ├── fixed.py
│       │   │   ├── conversation.py
│       │   │   ├── topic_based.py
│       │   │   └── daily.py
│       │   │
│       │   └── token_counters/
│       │       ├── __init__.py
│       │       ├── tiktoken_counter.py # Accurate (requires tiktoken)
│       │       └── simple_counter.py   # Approximation (no deps)
│       │
│       ├── presentation/       # === PRESENTATION LAYER ===
│       │   ├── __init__.py
│       │   ├── cli/
│       │   │   ├── __init__.py
│       │   │   ├── app.py              # Typer app
│       │   │   ├── commands/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── parse.py
│       │   │   │   ├── split.py
│       │   │   │   ├── chunk.py
│       │   │   │   ├── stats.py
│       │   │   │   └── validate.py
│       │   │   └── formatters.py       # Rich output
│       │   │
│       │   └── mcp/
│       │       ├── __init__.py
│       │       ├── server.py           # MCP Server
│       │       └── tools.py            # Tool definitions
│       │
│       └── config/
│           ├── __init__.py
│           ├── settings.py             # Pydantic Settings
│           └── defaults.py             # Default configurations
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                     # Fixtures
│   ├── fixtures/                       # Test data
│   │   ├── personal_chat.json
│   │   ├── group_chat.json
│   │   ├── supergroup_forum.json
│   │   └── channel.json
│   │
│   ├── unit/
│   │   ├── domain/
│   │   ├── application/
│   │   └── infrastructure/
│   │
│   └── integration/
│       ├── test_cli.py
│       └── test_mcp.py
│
└── docs/
    ├── PRD.md                          # Этот документ
    ├── ARCHITECTURE.md
    └── examples/
        ├── basic_usage.md
        └── advanced_filters.md
```

### 4.4 Ключевые доменные модели

#### 4.4.1 Message Entity

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import NewType

MessageId = NewType("MessageId", int)
UserId = NewType("UserId", str)
TopicId = NewType("TopicId", int)


class MessageType(Enum):
    TEXT = "text"
    SERVICE = "service"
    MEDIA = "media"
    STICKER = "sticker"
    VOICE = "voice"
    VIDEO_NOTE = "video_note"


@dataclass(frozen=True, slots=True)
class Attachment:
    type: str  # photo, video, document, etc.
    file_path: str | None = None
    file_name: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None


@dataclass(frozen=True, slots=True)
class ReplyInfo:
    message_id: MessageId
    author: str | None = None
    preview: str | None = None


@dataclass(frozen=True, slots=True)
class Message:
    id: MessageId
    timestamp: datetime
    author_name: str
    author_id: UserId
    text: str
    message_type: MessageType = MessageType.TEXT
    topic_id: TopicId | None = None
    reply_to: ReplyInfo | None = None
    forward_from: str | None = None
    mentions: tuple[str, ...] = field(default_factory=tuple)
    attachments: tuple[Attachment, ...] = field(default_factory=tuple)
    reactions: dict[str, int] = field(default_factory=dict)
    
    @property
    def has_text(self) -> bool:
        return bool(self.text.strip())
    
    @property
    def is_service(self) -> bool:
        return self.message_type == MessageType.SERVICE
    
    @property
    def is_forward(self) -> bool:
        return self.forward_from is not None
```

#### 4.4.2 Chat Entity

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ChatType(Enum):
    PERSONAL = "personal"
    GROUP = "group"
    SUPERGROUP = "supergroup"
    SUPERGROUP_FORUM = "supergroup_forum"
    CHANNEL = "channel"


@dataclass(frozen=True, slots=True)
class Topic:
    id: TopicId
    title: str
    created_at: datetime | None = None
    is_general: bool = False


@dataclass(frozen=True, slots=True)
class Participant:
    id: UserId
    name: str
    username: str | None = None
    message_count: int = 0


@dataclass
class Chat:
    id: int
    name: str
    chat_type: ChatType
    messages: list[Message] = field(default_factory=list)
    topics: dict[TopicId, Topic] = field(default_factory=dict)
    participants: dict[UserId, Participant] = field(default_factory=dict)
    
    @property
    def is_forum(self) -> bool:
        return self.chat_type == ChatType.SUPERGROUP_FORUM
    
    @property
    def date_range(self) -> tuple[datetime, datetime] | None:
        if not self.messages:
            return None
        timestamps = [m.timestamp for m in self.messages]
        return min(timestamps), max(timestamps)
    
    def messages_by_topic(self, topic_id: TopicId) -> list[Message]:
        return [m for m in self.messages if m.topic_id == topic_id]
```

#### 4.4.3 FilterSpecification Value Object

```python
from dataclasses import dataclass, field
from datetime import datetime
import re


@dataclass(frozen=True)
class DateRange:
    start: datetime | None = None
    end: datetime | None = None
    
    def contains(self, dt: datetime) -> bool:
        if self.start and dt < self.start:
            return False
        if self.end and dt > self.end:
            return False
        return True


@dataclass(frozen=True)
class FilterSpecification:
    """Immutable specification for message filtering."""
    
    date_range: DateRange | None = None
    senders: frozenset[str] = field(default_factory=frozenset)
    sender_ids: frozenset[UserId] = field(default_factory=frozenset)
    exclude_senders: frozenset[str] = field(default_factory=frozenset)
    topics: frozenset[str] = field(default_factory=frozenset)
    exclude_topics: frozenset[str] = field(default_factory=frozenset)
    mentions: frozenset[str] = field(default_factory=frozenset)
    content_pattern: re.Pattern | None = None
    min_length: int = 0
    has_attachment: bool | None = None
    has_reactions: bool | None = None
    exclude_forwards: bool = False
    exclude_service: bool = True
    exclude_empty: bool = True
    
    def is_empty(self) -> bool:
        """Check if no filters are applied."""
        return (
            self.date_range is None
            and not self.senders
            and not self.sender_ids
            and not self.exclude_senders
            and not self.topics
            and not self.exclude_topics
            and not self.mentions
            and self.content_pattern is None
            and self.min_length == 0
            and self.has_attachment is None
            and self.has_reactions is None
            and not self.exclude_forwards
            and self.exclude_service  # default True doesn't count
            and self.exclude_empty  # default True doesn't count
        )
```

### 4.5 Протоколы (Ports)

```python
from typing import Protocol, Iterator
from pathlib import Path


class ChatReaderProtocol(Protocol):
    """Port for reading chat data from various sources."""
    
    def read(self, source: Path) -> Chat:
        """Read entire chat into memory."""
        ...
    
    def stream(self, source: Path) -> Iterator[Message]:
        """Stream messages for large files."""
        ...
    
    def validate(self, source: Path) -> list[str]:
        """Validate source and return list of warnings."""
        ...


class ChatWriterProtocol(Protocol):
    """Port for writing chat data to various formats."""
    
    def write(self, chat: Chat, destination: Path) -> None:
        """Write chat to destination."""
        ...
    
    def write_messages(
        self, 
        messages: list[Message], 
        destination: Path,
        metadata: dict | None = None
    ) -> None:
        """Write subset of messages."""
        ...


class FilterProtocol(Protocol):
    """Port for message filtering."""
    
    def matches(self, message: Message) -> bool:
        """Check if message matches filter criteria."""
        ...
    
    def filter(self, messages: Iterable[Message]) -> Iterator[Message]:
        """Filter messages lazily."""
        ...


class ChunkerProtocol(Protocol):
    """Port for chunking strategies."""
    
    def chunk(
        self, 
        messages: list[Message],
        max_tokens: int,
        **options
    ) -> list[list[Message]]:
        """Split messages into chunks."""
        ...
```

---

## 5. API Reference

### 5.1 CLI Commands

#### 5.1.1 `tg-parser parse`

Основная команда парсинга.

```bash
tg-parser parse <input> [OPTIONS]

Arguments:
  input                   Path to JSON export file or directory

Options:
  -o, --output PATH       Output directory [default: ./output]
  -f, --format FORMAT     Output format: markdown|json|kb [default: markdown]

  # Streaming mode
  --streaming             Force streaming mode (requires ijson)
  --no-streaming          Force non-streaming mode (faster for small files)
                          [default: auto-detect based on file size >50MB]

  # Date filters
  --date-from DATE        Start date (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
  --date-to DATE          End date
  --last-days INT         Last N days
  --last-hours INT        Last N hours
  
  # Sender filters
  --senders TEXT          Comma-separated sender names
  --sender-ids TEXT       Comma-separated sender IDs
  --exclude-senders TEXT  Exclude these senders
  
  # Topic filters
  --topics TEXT           Only these topics
  --exclude-topics TEXT   Exclude these topics
  
  # Content filters
  --mentions TEXT         Messages mentioning these users
  --contains TEXT         Regex pattern for content
  --min-length INT        Minimum message length [default: 0]
  
  # Type filters
  --has-attachment        Only messages with attachments
  --has-reactions         Only messages with reactions
  --exclude-forwards      Exclude forwarded messages
  --include-service       Include service messages [default: excluded]
  
  # Processing options
  --split-topics          Create separate file per topic
  --anonymize             Replace names with placeholders
  --include-stats         Add statistics to output
  
  # General
  -v, --verbose           Verbose output
  --dry-run               Show what would be done
  --help                  Show this help
```

**Примеры:**

```bash
# Базовый парсинг
tg-parser parse ./ChatExport/result.json

# Последние 7 дней, только конкретный участник
tg-parser parse ./export.json --last-days 7 --senders "Иван Петров"

# Разделить по топикам, JSON формат
tg-parser parse ./forum_export.json --split-topics -f json

# Поиск по паттерну
tg-parser parse ./export.json --contains "deadline|срочно|ASAP"

# Большой файл со streaming и прогресс-баром
tg-parser parse ./massive_chat_export.json --streaming -v
```

#### 5.1.2 `tg-parser chunk`

Разбиение на чанки для LLM.

```bash
tg-parser chunk <input> [OPTIONS]

Arguments:
  input                   Path to Telegram JSON export or parsed file

Options:
  -o, --output PATH       Output directory [default: ./chunks]
  -s, --strategy STRATEGY Chunking strategy [default: fixed]
                          Values: fixed|conversation|topic|daily|hybrid
  --max-tokens INT        Maximum tokens per chunk [default: 8000]

  # Streaming mode
  --streaming             Force streaming mode for reading (requires ijson)
  --no-streaming          Force non-streaming mode
                          [default: auto-detect based on file size >50MB]

  # Strategy-specific options
  --time-gap INT          Minutes of silence to split (conversation/hybrid) [default: 30]
  --preserve-threads      Don't break reply chains (conversation/hybrid)

  # Output options
  --format FORMAT         Output format: markdown|json|kb [default: markdown]
  --chunk-index INT       Return only specific chunk (0-based)
  --include-extraction-guide  Add Russian extraction template

  # General
  -v, --verbose           Verbose output
  --help                  Show this help
```

#### 5.1.3 `tg-parser stats`

Статистика чата.

```bash
tg-parser stats <input> [OPTIONS]

Options:
  --format FORMAT         Output: table|json|markdown [default: table]
  --top-senders INT       Show top N senders [default: 10]
  --by-topic              Group statistics by topic
  --by-day                Show daily breakdown
  --by-hour               Show hourly activity
```

**Пример вывода:**

```
╭─────────────────────────────────────────────────────────────╮
│                    Chat Statistics                          │
├─────────────────────────────────────────────────────────────┤
│  Chat Name:        Команда разработки                       │
│  Chat Type:        Supergroup (Forum)                       │
│  Period:           2025-01-01 — 2025-01-19                  │
│  Total Messages:   1,247                                    │
│  Participants:     12                                       │
│  Topics:           5                                        │
│  Est. Tokens:      ~45,000                                  │
├─────────────────────────────────────────────────────────────┤
│  Top Senders                                                │
│  ──────────────────────────────────────────────────         │
│  1. Иван Петров        342 messages (27.4%)                 │
│  2. Мария Сидорова     256 messages (20.5%)                 │
│  3. Алексей Козлов     198 messages (15.9%)                 │
├─────────────────────────────────────────────────────────────┤
│  Topics                                                     │
│  ──────────────────────────────────────────────────         │
│  • General             523 messages                         │
│  • Architecture        312 messages                         │
│  • Bugs                201 messages                         │
│  • DevOps              142 messages                         │
│  • Off-topic            69 messages                         │
╰─────────────────────────────────────────────────────────────╯
```

### 5.2 MCP Tools

#### 5.2.1 `tg_parse`

```json
{
  "name": "tg_parse",
  "description": "Parse Telegram JSON export with filters",
  "inputSchema": {
    "type": "object",
    "properties": {
      "input_path": {
        "type": "string",
        "description": "Path to JSON export file"
      },
      "output_format": {
        "type": "string",
        "enum": ["markdown", "json"],
        "default": "markdown"
      },
      "date_from": {
        "type": "string",
        "description": "Start date (ISO format)"
      },
      "date_to": {
        "type": "string",
        "description": "End date (ISO format)"
      },
      "last_days": {
        "type": "integer",
        "description": "Last N days"
      },
      "senders": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Filter by sender names"
      },
      "topics": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Filter by topic names"
      },
      "contains": {
        "type": "string",
        "description": "Regex pattern for content"
      },
      "split_topics": {
        "type": "boolean",
        "default": false
      },
      "streaming": {
        "type": "boolean",
        "description": "Force streaming mode. Default: auto (>50MB)"
      },
      "max_messages": {
        "type": "integer",
        "description": "Limit output to first N messages",
        "default": 1000
      }
    },
    "required": ["input_path"]
  }
}
```

#### 5.2.2 `tg_chunk`

```json
{
  "name": "tg_chunk",
  "description": "Split messages into LLM-friendly chunks",
  "inputSchema": {
    "type": "object",
    "properties": {
      "input_path": {
        "type": "string",
        "description": "Path to parsed file"
      },
      "strategy": {
        "type": "string",
        "enum": ["fixed", "conversation", "topic", "daily"],
        "default": "conversation"
      },
      "max_tokens": {
        "type": "integer",
        "default": 3000
      },
      "time_gap_minutes": {
        "type": "integer",
        "default": 30
      },
      "streaming": {
        "type": "boolean",
        "description": "Force streaming mode. Default: auto (>50MB)"
      },
      "chunk_index": {
        "type": "integer",
        "description": "Return only specific chunk (0-based)"
      }
    },
    "required": ["input_path"]
  }
}
```

#### 5.2.3 `tg_stats`

```json
{
  "name": "tg_stats",
  "description": "Get chat statistics",
  "inputSchema": {
    "type": "object",
    "properties": {
      "input_path": {
        "type": "string"
      },
      "include_top_senders": {
        "type": "integer",
        "default": 10
      },
      "group_by_topic": {
        "type": "boolean",
        "default": false
      }
    },
    "required": ["input_path"]
  }
}
```

### 5.3 Python Library API

```python
from tg_parser import parse_chat, chunk_messages, ChatFilter
from tg_parser.domain.value_objects import FilterSpecification, DateRange
from datetime import datetime, timedelta

# Простой парсинг
chat = parse_chat("./export/result.json")
print(f"Loaded {len(chat.messages)} messages")

# С фильтрами
filter_spec = FilterSpecification(
    date_range=DateRange(
        start=datetime.now() - timedelta(days=7),
        end=datetime.now()
    ),
    senders=frozenset(["Иван Петров", "Мария Сидорова"]),
    exclude_service=True
)

chat = parse_chat("./export/result.json", filter_spec=filter_spec)

# Фильтрация существующего чата
chat_filter = ChatFilter(filter_spec)
filtered_messages = list(chat_filter.filter(chat.messages))

# Chunking
from tg_parser.application.services.chunker import ConversationChunker

chunker = ConversationChunker(max_tokens=3000, time_gap_minutes=30)
chunks = chunker.chunk(filtered_messages)

for i, chunk in enumerate(chunks):
    print(f"Chunk {i}: {len(chunk)} messages")

# Экспорт
from tg_parser.infrastructure.writers import MarkdownWriter

writer = MarkdownWriter()
writer.write(chat, Path("./output/chat.md"))

# Или по чанкам
for i, chunk in enumerate(chunks):
    writer.write_messages(
        chunk, 
        Path(f"./output/chunks/chunk_{i:03d}.md"),
        metadata={"chunk_index": i, "total_chunks": len(chunks)}
    )
```

---

## 6. Конфигурация

### 6.1 Файл конфигурации

Путь: `~/.config/tg-parser/config.toml` или `TG_PARSER_CONFIG` env var.

```toml
[default]
output_format = "markdown"
output_dir = "~/Documents/tg-exports"

[filtering]
exclude_service = true
exclude_empty = true
min_message_length = 0

[chunking]
strategy = "conversation"
max_tokens = 3000
min_tokens = 500
overlap = 100
time_gap_minutes = 30
preserve_threads = true

[output.markdown]
include_reactions = true
include_attachments = true
timestamp_format = "%Y-%m-%d %H:%M"
collapse_forwards = true

[output.json]
indent = 2
include_raw_entities = false

[token_counter]
# "tiktoken" for accuracy, "simple" for no dependencies
backend = "tiktoken"
model = "cl100k_base"  # Claude/GPT-4 tokenizer

[anonymization]
enabled = false
prefix = "User"
preserve_mentions = false

[logging]
level = "INFO"
file = "~/.local/share/tg-parser/tg-parser.log"
```

### 6.2 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TG_PARSER_CONFIG` | Path to config file | `~/.config/tg-parser/config.toml` |
| `TG_PARSER_OUTPUT_DIR` | Default output directory | `./output` |
| `TG_PARSER_LOG_LEVEL` | Logging level | `INFO` |
| `TG_PARSER_TOKEN_BACKEND` | Token counter backend | `tiktoken` |

---

## 7. Тестирование

### 7.1 Тестовые сценарии

| Категория | Сценарий | Приоритет |
|-----------|----------|-----------|
| **Parsing** | Личный чат | P0 |
| | Групповой чат | P0 |
| | Супергруппа без топиков | P0 |
| | Супергруппа с топиками (forum) | P0 |
| | Канал с комментариями | P1 |
| | Пустой экспорт | P1 |
| | Очень большой файл (>100MB) | P1 |
| **Filtering** | По дате | P0 |
| | По отправителю | P0 |
| | По топику | P0 |
| | Комбинированные фильтры | P0 |
| | Regex поиск | P1 |
| | Исключающие фильтры | P1 |
| **Chunking** | Fixed strategy | P1 |
| | Conversation strategy | P0 |
| | Topic-based | P1 |
| | Preserve threads | P1 |
| **Output** | Markdown generation | P0 |
| | JSON generation | P0 |
| | Split by topics | P0 |
| **MCP** | All tools work | P0 |
| | Error handling | P1 |

### 7.2 Тестовые данные

Фикстуры в `tests/fixtures/`:

```
fixtures/
├── personal_chat.json          # Личный чат 1-1
├── group_chat.json             # Группа без топиков
├── supergroup_simple.json      # Супергруппа без топиков
├── supergroup_forum.json       # Супергруппа с топиками
├── channel_with_comments.json  # Канал
├── large_chat.json             # 10000+ сообщений
├── edge_cases/
│   ├── empty_chat.json
│   ├── only_service.json
│   ├── unicode_heavy.json
│   ├── malformed_dates.json
│   └── missing_fields.json
└── expected_outputs/
    ├── personal_chat.md
    ├── group_filtered.md
    └── forum_split/
```

### 7.3 Команды тестирования

```bash
# Все тесты
uv run pytest

# Только unit
uv run pytest tests/unit/

# Только integration
uv run pytest tests/integration/

# С покрытием
uv run pytest --cov=tg_parser --cov-report=html

# Конкретный тест
uv run pytest tests/unit/domain/test_message.py -v

# Property-based тесты
uv run pytest tests/unit/ -m hypothesis
```

---

## 8. Roadmap

### Phase 1: MVP ✅ DONE

| Задача | Статус |
|--------|--------|
| Domain entities (Message, Chat, Topic, Participant) | ✅ |
| Value objects (MessageId, UserId, TopicId, DateRange, FilterSpecification) | ✅ |
| Telegram JSON reader с поддержкой топиков | ✅ |
| Фильтры (date, sender, service, forward, content, length, attachment, reactions) | ✅ |
| Markdown writer (LLM-optimized) | ✅ |
| CLI: parse command | ✅ |
| CLI: stats command | ✅ |
| MCP server с 6 инструментами | ✅ |
| Unit + integration tests (261 тест) | ✅ |
| pyright strict mode | ✅ |

**Deliverable:** Работающий CLI и MCP сервер с базовым функционалом.

### Phase 2: Chunking & Topics ✅ DONE (v0.2.0)

| Задача | Приоритет | Статус |
|--------|-----------|--------|
| ConversationChunker | P0 | ✅ |
| FixedChunker | P0 | ✅ |
| TopicBasedChunker | P1 | ✅ |
| DailyChunker | P1 | ✅ |
| HybridChunker | P1 | ✅ |
| CLI: chunk command | P0 | ✅ |
| CLI: split-topics command | P1 | ❌ |
| MCP: chunk_telegram_export tool | P0 | ✅ |
| Тесты для chunking | P0 | ✅ |

**Deliverable:** Полноценный chunking для работы с LLM контекстом.

### Phase 3: Output Formats ✅ PARTIAL (v0.2.5)

| Задача | Приоритет | Статус |
|--------|-----------|--------|
| JSON writer | P2 | ✅ |
| KBTemplate writer (markdown с YAML frontmatter) | P2 | ✅ |
| CSV writer | P2 | ❌ |
| Extraction guide template (RU) | P2 | ✅ |

**Deliverable:** Дополнительные форматы вывода для разных use cases.

### Phase 4: Advanced Filtering ✅ PARTIAL (v0.2.5)

| Задача | Приоритет | Статус |
|--------|-----------|--------|
| Topic filter | P2 | ✅ |
| Content regex filter | P0 | ✅ |
| Attachment filter | P1 | ✅ |
| Forward filter | P1 | ✅ |
| Composite filter (AND/OR) | P0 | ✅ |
| CLI: расширенные фильтры | P2 | ✅ |
| MCP: list_mentioned_users tool | P2 | ✅ |

**Deliverable:** Продвинутая фильтрация сообщений.

### Phase 5: Streaming & Performance ✅ DONE (v0.3.0)

| Задача | Приоритет | Статус |
|--------|-----------|--------|
| Shared parsing module (_parsing.py) | P1 | ✅ |
| TelegramStreamReader с ijson | P1 | ✅ |
| Reader factory с auto-detection | P1 | ✅ |
| Progress bars в CLI (rich.progress) | P1 | ✅ |
| CLI: --streaming/--no-streaming флаги | P1 | ✅ |
| MCP: streaming параметр в tools | P1 | ✅ |
| Graceful fallback без ijson | P1 | ✅ |
| StreamingError exception | P2 | ✅ |
| Тесты для streaming (76 новых тестов) | P0 | ✅ |

**Deliverable:** Поддержка больших файлов (>50MB) без OOM, progress tracking.

**Performance characteristics:**
- Memory usage: O(n) → O(1) для streaming mode
- Auto-detection: файлы >50MB используют streaming автоматически
- Progress: точный прогресс с overhead ~1%
- 261 тест passing (unit + integration)

### Phase 6: Production Polish (v1.0.0) ✅ COMPLETE

**Completion Date:** 2026-01-19

| Задача | Приоритет | Статус |
|--------|-----------|--------|
| Version sync (pyproject.toml, __init__.py) | P0 | ✅ |
| **GitHub Setup** | | |
| GitHub repository creation | P0 | ✅ |
| Repository description, topics, README badges | P1 | ✅ |
| GitHub release creation (via gh CLI) | P1 | ✅ |
| **CI/CD Pipeline** | | |
| GitHub Actions: Tests workflow | P0 | ✅ |
| GitHub Actions: Type check workflow | P0 | ✅ |
| GitHub Actions: Lint workflow | P0 | ✅ |
| GitHub Actions: PyPI Test publish (on release) | P1 | ✅ |
| GitHub Actions: PyPI Prod publish (on release) | P0 | ✅ |
| GitHub Secrets: PyPI tokens | P0 | ✅ |
| **Quality & Docs** | | |
| Documentation restructure (CLAUDE.md, docs/) | P1 | ✅ |
| CHANGELOG.md creation | P1 | ✅ |
| PyPI badges and installation instructions | P1 | ✅ |
| split-topics command | P1 | ❌ (deferred to v1.1.0) |
| CSV writer | P2 | ❌ (deferred to v1.1.0) |
| tiktoken integration | P2 | ❌ (deferred to v1.1.0) |
| Config file support | P3 | ❌ (deferred to v1.1.0) |
| Anonymization | P3 | ❌ (deferred) |
| 90%+ code coverage | P2 | ❌ (deferred) |

**Deliverable:** ✅ Production-ready инструмент в PyPI с полным CI/CD.

**Release:** https://github.com/mdemyanov/tg-parser/releases/tag/v1.0.0
**PyPI:** https://pypi.org/project/tg-parser/

#### Phase 6 Implementation Details

##### GitHub Setup

**1. Repository Creation**

```bash
# Create public repository via GitHub CLI
gh repo create tg-parser --public \
  --description="Parse Telegram Desktop JSON exports for LLM processing" \
  --homepage="https://github.com/username/tg-parser"

# Add topics for discoverability
gh repo edit --add-topic telegram,parser,llm,mcp,claude,python

# Push code
git remote add origin https://github.com/username/tg-parser.git
git branch -M main
git push -u origin main
```

**2. Repository Configuration**

- Enable Issues
- Enable Discussions (optional)
- Add description: "Parse Telegram Desktop JSON exports for LLM processing"
- Add topics: `telegram`, `parser`, `llm`, `mcp`, `claude`, `python`, `cli`
- Add LICENSE (MIT already exists)

**3. Release Creation**

```bash
# Tag version
git tag v1.0.0 -m "Release v1.0.0 - Production Ready"
git push --tags

# Create GitHub release with CHANGELOG
gh release create v1.0.0 \
  --title "v1.0.0 - Production Ready" \
  --notes-file CHANGELOG.md \
  --latest
```

##### CI/CD Pipeline

**1. Tests Workflow** (`.github/workflows/tests.yml`)

```yaml
name: Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v2
      - name: Set up Python
        run: uv python install ${{ matrix.python-version }}
      - name: Install dependencies
        run: uv sync --all-extras
      - name: Run tests
        run: uv run pytest -v --cov=tg_parser --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

**2. Type Check Workflow** (`.github/workflows/typecheck.yml`)

```yaml
name: Type Check

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v2
      - name: Set up Python
        run: uv python install 3.12
      - name: Install dependencies
        run: uv sync --all-extras
      - name: Run pyright
        run: uv run pyright
```

**3. Lint Workflow** (`.github/workflows/lint.yml`)

```yaml
name: Lint

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v2
      - name: Set up Python
        run: uv python install 3.12
      - name: Install dependencies
        run: uv sync --all-extras
      - name: Run ruff check
        run: uv run ruff check
      - name: Run ruff format check
        run: uv run ruff format --check
```

**4. PyPI Publish Workflow** (`.github/workflows/publish.yml`)

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish-test:
    runs-on: ubuntu-latest
    environment: test-pypi
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v2
      - name: Set up Python
        run: uv python install 3.12
      - name: Install dependencies
        run: uv sync --all-extras
      - name: Build package
        run: uv build
      - name: Publish to Test PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.TEST_PYPI_TOKEN }}
        run: |
          uv run twine upload --repository testpypi dist/*

  publish-prod:
    needs: publish-test
    runs-on: ubuntu-latest
    environment: pypi
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v2
      - name: Set up Python
        run: uv python install 3.12
      - name: Install dependencies
        run: uv sync --all-extras
      - name: Build package
        run: uv build
      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
        run: |
          uv run twine upload dist/*
```

**5. GitHub Secrets Setup**

```bash
# Add PyPI tokens as repository secrets
gh secret set TEST_PYPI_TOKEN < test_pypi_token.txt
gh secret set PYPI_TOKEN < pypi_token.txt
```

Tokens can be obtained from:
- Test PyPI: https://test.pypi.org/manage/account/token/
- PyPI: https://pypi.org/manage/account/token/

Alternatively, extract tokens from `~/.pypirc`:
```bash
# Extract Test PyPI token
grep -A 3 '\[testpypi\]' ~/.pypirc | grep password | cut -d= -f2 | xargs

# Extract Production PyPI token
grep -A 3 '\[pypi\]' ~/.pypirc | grep password | cut -d= -f2 | xargs
```

**6. Release Process**

```bash
# 1. Update version in pyproject.toml
# [project]
# version = "1.0.0"

# 2. Update CHANGELOG.md with release notes

# 3. Commit changes
git add pyproject.toml CHANGELOG.md
git commit -m "Release v1.0.0"
git push

# 4. Create tag and GitHub release
git tag v1.0.0 -m "Release v1.0.0 - Production Ready"
git push --tags

gh release create v1.0.0 \
  --title "v1.0.0 - Production Ready" \
  --notes-file CHANGELOG.md \
  --latest

# 5. GitHub Actions will automatically:
#    - Run tests, typecheck, lint
#    - Build package
#    - Publish to Test PyPI
#    - Publish to PyPI (after test succeeds)
```

**7. Verification After Publish**

```bash
# Install from PyPI
pip install tg-parser

# Verify version
tg-parser --version

# Test basic functionality
tg-parser parse --help
```

##### Quality Metrics

**Code Coverage**

Target: 90%+ coverage

```bash
# Run coverage locally
uv run pytest --cov=tg_parser --cov-report=html

# View report
open htmlcov/index.html
```

Enable Codecov integration:
- Add to `.github/workflows/tests.yml` (already included above)
- Add badge to README.md: `[![codecov](https://codecov.io/gh/username/tg-parser/branch/main/graph/badge.svg)](https://codecov.io/gh/username/tg-parser)`

---

## 9. Риски и митигации

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Изменение формата экспорта Telegram | Средняя | Высокое | Версионирование парсера, абстракция reader |
| Слишком большие файлы | Средняя | Среднее | Streaming parser с ijson |
| Неточный подсчёт токенов | Низкая | Низкое | Использовать tiktoken, запас 10% |
| Сложность топиков в forum mode | Высокая | Среднее | Тщательное тестирование на реальных данных |
| MCP protocol changes | Низкая | Среднее | Следить за обновлениями, pinned версии |

---

## 10. Acceptance Criteria

### 10.1 MVP Ready ✅ ACHIEVED

- [x] Парсинг всех типов чатов (personal, group, supergroup, forum, channel)
- [x] Фильтрация по дате, отправителю работает корректно
- [x] Markdown output читаем и готов для LLM
- [x] CLI команды `parse`, `stats`, `chunk`, `mentions` работают
- [x] MCP server с 6 инструментами
- [x] 261 тест passing
- [x] pyright strict mode compliance
- [x] README с примерами использования

### 10.2 Chunking Ready ✅ ACHIEVED (v0.2.0)

- [x] Chunking стратегии (conversation, fixed, topic, daily, hybrid)
- [x] CLI команда `chunk`
- [x] MCP инструмент `chunk_telegram_export`
- [ ] split-topics команда

### 10.3 Streaming Ready ✅ ACHIEVED (v0.3.0)

- [x] Файлы >50MB обрабатываются без OOM (streaming с ijson)
- [x] Auto-detection режима (>50MB → streaming)
- [x] Progress bars в CLI
- [x] Graceful fallback без ijson
- [x] JSON формат вывода
- [x] KBTemplate формат (markdown + YAML frontmatter)
- [x] 261 тест passing
- [x] Все фильтры реализованы и протестированы

### 10.4 Production Ready (v1.0.0) ✅ ACHIEVED

- [x] Опубликован в PyPI (https://pypi.org/project/tg-parser/)
- [x] CI/CD настроен (4 GitHub Actions workflows)
- [x] GitHub repository создан (https://github.com/mdemyanov/tg-parser)
- [x] GitHub Release v1.0.0 с full release notes
- [x] Документация полная (README, ARCHITECTURE, DEVELOPMENT, TELEGRAM_FORMAT, PRD, CHANGELOG)
- [x] 261 тест, 99.2% passing
- [ ] CSV формат вывода (отложено на v1.1.0)
- [ ] tiktoken integration (отложено на v1.1.0)
- [ ] split-topics команда (отложено на v1.1.0)
- [ ] 90%+ code coverage (отложено)

---

## 11. Roadmap: Post-v1.0.0

### Phase 7: Enhanced Usability (v1.1.0) – PLANNED

**Приоритет:** P1-P2
**Цель:** Улучшить user experience и добавить недостающие форматы вывода

| Задача | Приоритет | Сложность | Статус |
|--------|-----------|-----------|--------|
| **CSV Writer** | | | |
| CSVWriter class в infrastructure/writers/ | P2 | Low | 📋 Planned |
| CLI: --format csv опция | P2 | Low | 📋 Planned |
| MCP: CSV format support | P2 | Low | 📋 Planned |
| Тесты для CSV writer | P2 | Low | 📋 Planned |
| **split-topics Command** | | | |
| Отдельная команда `tg-parser split-topics` | P1 | Low | 📋 Planned |
| Перенос логики из parse --split-topics | P1 | Low | 📋 Planned |
| CLI help и примеры | P1 | Low | 📋 Planned |
| Тесты для split-topics | P1 | Low | 📋 Planned |
| **tiktoken Integration** | | | |
| TiktokenCounter class | P2 | Medium | 📋 Planned |
| Fallback на SimpleTokenCounter | P2 | Low | 📋 Planned |
| CLI: --token-counter опция | P2 | Low | 📋 Planned |
| Тесты для tiktoken | P2 | Medium | 📋 Planned |
| **Config File Support** | | | |
| TOML config file parsing (pyproject.toml style) | P3 | Medium | 📋 Planned |
| Default config locations (~/.tg-parser.toml, ./tg-parser.toml) | P3 | Low | 📋 Planned |
| CLI: --config опция | P3 | Low | 📋 Planned |
| Config schema validation | P3 | Medium | 📋 Planned |

**Deliverable:** Более удобный инструмент с гибкими форматами вывода и конфигурацией

**ETA:** 2-3 недели

---

### Phase 8: Quality & Performance (v1.2.0) – PLANNED

**Приоритет:** P2-P3
**Цель:** Улучшить качество кода, покрытие тестами, производительность

| Задача | Приоритет | Сложность | Статус |
|--------|-----------|-----------|--------|
| **Code Coverage** | | | |
| Увеличить покрытие до 90%+ | P2 | Medium | 📋 Planned |
| Codecov integration в CI/CD | P2 | Low | 📋 Planned |
| Coverage badge в README | P2 | Low | 📋 Planned |
| **Test Quality** | | | |
| Исправить 2 провальных help text тестов | P1 | Low | 📋 Planned |
| Добавить edge case тесты | P2 | Medium | 📋 Planned |
| Property-based testing (hypothesis) | P3 | High | 📋 Planned |
| **Lint Fixes** | | | |
| Исправить 156 ruff warnings | P2 | Medium | 📋 Planned |
| Настроить pre-commit hooks | P2 | Low | 📋 Planned |
| **Performance Benchmarks** | | | |
| Benchmark suite для streaming | P3 | Medium | 📋 Planned |
| Memory profiling для больших файлов | P3 | Medium | 📋 Planned |
| Performance regression tests | P3 | High | 📋 Planned |

**Deliverable:** Высококачественный код с 90%+ coverage и производительностью benchmarks

**ETA:** 2-3 недели

---

### Phase 9: Advanced Features (v1.3.0+) – BACKLOG

**Приоритет:** P3
**Цель:** Расширенная функциональность для power users

| Задача | Приоритет | Сложность | Статус |
|--------|-----------|-----------|--------|
| **Anonymization** | | | |
| Анонимизация имен участников | P3 | Medium | 🔮 Backlog |
| Хеширование user IDs | P3 | Low | 🔮 Backlog |
| CLI: --anonymize флаг | P3 | Low | 🔮 Backlog |
| **Advanced Search** | | | |
| Full-text search по сообщениям | P3 | High | 🔮 Backlog |
| Regex search с capturing groups | P3 | Medium | 🔮 Backlog |
| Search результаты в JSON | P3 | Low | 🔮 Backlog |
| **Export Validation** | | | |
| Validate Telegram JSON schema | P3 | Medium | 🔮 Backlog |
| Report invalid/corrupted exports | P3 | Low | 🔮 Backlog |
| CLI: validate команда | P3 | Low | 🔮 Backlog |
| **Batch Processing** | | | |
| Обработка нескольких экспортов | P3 | Medium | 🔮 Backlog |
| Merge результатов из разных чатов | P3 | High | 🔮 Backlog |
| CLI: batch команда | P3 | Medium | 🔮 Backlog |
| **Web UI (Optional)** | | | |
| FastAPI web interface | P4 | Very High | 🔮 Backlog |
| Upload & parse через UI | P4 | High | 🔮 Backlog |
| Interactive filtering | P4 | Very High | 🔮 Backlog |

**Deliverable:** Полнофункциональный enterprise-ready инструмент

**ETA:** 3-6 месяцев

---

## 12. Приоритизация задач: v1.1.0

### P0 (Critical) – Must Have
*Нет критичных задач в v1.1.0 - v1.0.0 уже production-ready*

### P1 (High) – Should Have

1. **split-topics команда** (2-3 дня)
   - **Why:** Улучшает UX, текущий флаг `--split-topics` неинтуитивен
   - **Impact:** Средний - упрощает работу с forum-чатами
   - **Effort:** Low - логика уже есть, нужен рефакторинг
   - **Dependencies:** Нет

2. **Исправить 2 провальных теста** (1 день)
   - **Why:** Для 100% passing tests в CI
   - **Impact:** Низкий - косметическая проблема
   - **Effort:** Low - проблема в assertion, не в функциональности
   - **Dependencies:** Нет

### P2 (Medium) – Nice to Have

3. **CSV Writer** (3-4 дня)
   - **Why:** Табличный формат для анализа в Excel/Google Sheets
   - **Impact:** Средний - расширяет use cases (аналитика, отчеты)
   - **Effort:** Low-Medium - новый writer по аналогии с JSONWriter
   - **Dependencies:** Нет
   - **Fields:** timestamp, author, text, topic, reactions, attachments

4. **tiktoken integration** (4-5 дней)
   - **Why:** Точный подсчет токенов для OpenAI models
   - **Impact:** Средний - улучшает chunking precision
   - **Effort:** Medium - интеграция библиотеки, fallback logic
   - **Dependencies:** tiktoken package (optional dependency)

5. **Исправить 156 ruff warnings** (2-3 дня)
   - **Why:** Чистый код, пройденный lint в CI
   - **Impact:** Низкий - код уже работает
   - **Effort:** Medium - bulk edits, проверка что ничего не сломалось
   - **Dependencies:** Нет

6. **Увеличить code coverage до 90%** (5-7 дней)
   - **Why:** Уверенность в качестве кода
   - **Impact:** Средний - catch edge cases
   - **Effort:** Medium-High - написание тестов для uncovered code
   - **Dependencies:** Нет

### P3 (Low) – Could Have

7. **Config file support (TOML)** (4-5 дней)
   - **Why:** Удобство для регулярного использования (не надо передавать флаги)
   - **Impact:** Низкий - опытные пользователи оценят
   - **Effort:** Medium - parsing, validation, merge с CLI args
   - **Dependencies:** tomllib (built-in в Python 3.11+)

8. **Anonymization** (5-7 дней)
   - **Why:** Privacy для публичных датасетов
   - **Impact:** Низкий - niche use case
   - **Effort:** Medium - замена имен, хеширование IDs
   - **Dependencies:** Нет

### Рекомендуемый порядок для v1.1.0:

**Sprint 1 (1 неделя):**
1. Исправить 2 провальных теста (P1, 1 день)
2. split-topics команда (P1, 2-3 дня)
3. CSV Writer (P2, 3-4 дня)

**Sprint 2 (1 неделя):**
4. tiktoken integration (P2, 4-5 дней)
5. Начать исправление ruff warnings (P2, 2-3 дня)

**Sprint 3 (опционально, 1 неделя):**
6. Завершить ruff warnings
7. Config file support (P3, если есть время)

**Total ETA:** 2-3 недели для v1.1.0 release

---

## Appendix A: Примеры Telegram JSON структур

### A.1 Service message (topic created)

```json
{
  "id": 42,
  "type": "service",
  "date": "2025-01-10T09:00:00",
  "actor": "Иван Петров",
  "actor_id": "user123456",
  "action": "topic_created",
  "title": "Architecture"
}
```

### A.2 Message with formatting

```json
{
  "id": 100,
  "type": "message",
  "date": "2025-01-15T10:30:00",
  "from": "Мария Сидорова",
  "from_id": "user789",
  "text": [
    {"type": "bold", "text": "Важно: "},
    "нужно обсудить ",
    {"type": "mention", "text": "@Иван"},
    " вопрос по ",
    {"type": "text_link", "text": "документации", "href": "https://..."}
  ],
  "text_entities": [
    {"type": "bold", "offset": 0, "length": 7},
    {"type": "mention", "offset": 22, "length": 5},
    {"type": "text_link", "offset": 38, "length": 12, "href": "https://..."}
  ]
}
```

### A.3 Reply to topic message

```json
{
  "id": 150,
  "type": "message",
  "date": "2025-01-15T11:00:00",
  "from": "Алексей Козлов",
  "from_id": "user456",
  "text": "Согласен с предложением",
  "reply_to_message_id": 42,
  "reactions": [
    {"emoji": "👍", "count": 2, "recent": [{"user_id": "user123"}]}
  ]
}
```

---

## Appendix B: Глоссарий

| Термин | Определение |
|--------|-------------|
| **Forum mode** | Режим супергруппы с топиками (как подфорумы) |
| **Topic** | Тематический раздел в forum-группе |
| **General topic** | Дефолтный топик (id=1), всегда существует |
| **Service message** | Системное сообщение (join, leave, pin, etc.) |
| **Reply thread** | Цепочка ответов на сообщение |
| **Chunk** | Часть переписки, помещающаяся в контекст LLM |
| **Token** | Единица текста для LLM (≈4 символа для английского) |