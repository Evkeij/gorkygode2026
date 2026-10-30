import re
from datetime import datetime

from embeddings import build_embedding_text
from Backend import (
    DEFAULT_TOP_K,
    MAX_TOP_K,
    RECORD_TYPES,
    error,
    parse_iso,
)

_WORD_RE = re.compile(r"[а-яёa-z0-9]{3,}", re.IGNORECASE)


TOOLS = [
    # СОЗДАНИЕ
    {
        "type": "function",
        "function": {
            "name": "create_record",
            "description": (
                "Создать запись пользователя: встречу, напоминание или задачу. "
                "Определи тип, название и дату по запросу и контексту. "
                "created_at — дата создания, is_completed — статус выполнения. "
                "Если необходимая дата неоднозначна, задай уточняющий вопрос."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["meeting", "reminder", "task"],
                        "description": (
                            "Тип записи: meeting — встреча, "
                            "reminder — напоминание, task — задача"
                        ),
                    },
                    "title": {"type": "string", "description": "Название записи"},
                    "date": {
                        "type": ["string", "null"],
                        "description": (
                            "Дата и время в формате ISO 8601, например "
                            "2026-10-21T15:00:00. Для задачи это крайний "
                            "срок, для встречи или напоминания — дата события. "
                            "Обязательно уточни время события, если пользователь его не указал"
                        ),
                    },
                    "created_at": {
                        "type": "string",
                        "description": (
                            "Дата и время создания записи в формате ISO 8601. "
                            "Используй текущее местное время из контекста."
                        ),
                    },
                    "is_completed": {
                        "type": "boolean",
                        "description": "Статус выполнения новой записи. Всегда false.",
                    },
                },
                "required": ["type", "title", "date", "created_at", "is_completed"],
                "additionalProperties": False,
            },
        },
    },
     # ПОИСК
    {
        "type": "function",
        "function": {
            "name": "search_records",
            "description": (
                "Найти записи пользователя по смыслу и/или фильтрам. "
                "Используй для вопросов вроде «когда мне к врачу?», "
                "«что у меня на этой неделе?», «какие задачи не выполнены?». "
                "Все параметры необязательные: передавай только те, "
                "которые нужны для запроса. Результаты отсортированы по "
                "близости к query (поле score), а без query — по дате."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": ["string", "null"],
                        "description": (
                            "Короткая смысловая фраза о теме записи, например "
                            "«врач больница» или «отчёт». Без дат и вопросительных "
                            "слов. Если поиск идёт только по фильтрам, не указывай."
                        ),
                    },
                    "type": {
                        "type": ["string", "null"],
                        "enum": ["meeting", "reminder", "task", None],
                        "description": "Фильтр по типу записи.",
                    },
                    "date_from": {
                        "type": ["string", "null"],
                        "description": (
                            "Начало диапазона дат записи, ISO 8601 "
                            "(например 2026-10-21 или 2026-10-21T00:00:00)."
                        ),
                    },
                    "date_to": {
                        "type": ["string", "null"],
                        "description": (
                            "Конец диапазона дат записи включительно, ISO 8601. "
                            "Если указана только дата, берётся конец этого дня."
                        ),
                    },
                    "is_completed": {
                        "type": ["boolean", "null"],
                        "description": (
                            "true — только выполненные, false — только "
                            "невыполненные, не указывай — любые."
                        ),
                    },
                    "top_k": {
                        "type": ["integer", "null"],
                        "description": (
                            f"Сколько записей вернуть (1–{MAX_TOP_K}), "
                            f"по умолчанию {DEFAULT_TOP_K}."
                        ),
                    },
                },
                "required": [],
                "additionalProperties": False,
            },
        },
    },
     # ИЗМЕНЕНИЕ
    {
        "type": "function",
        "function": {
            "name": "update_record",
            "description": (
                "Изменить существующую запись: название, тип, дату или статус "
                "выполнения. Сначала найди запись через search_records"
                "и возьми её id. Передавай только "
                "те поля, которые нужно изменить. Если подходящих записей "
                "несколько и неясно, какую менять, уточни у пользователя."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "id изменяемой записи."},
                    "type": {
                        "type": ["string", "null"],
                        "enum": ["meeting", "reminder", "task", None],
                        "description": "Новый тип записи.",
                    },
                    "title": {"type": ["string", "null"], "description": "Новое название записи."},
                    "date": {
                        "type": ["string", "null"],
                        "description": (
                            "Новая дата и время, ISO 8601. Для переноса "
                            "(«перенеси на 15:00») укажи полную новую дату."
                        ),
                    },
                    "clear_date": {
                        "type": ["boolean", "null"],
                        "description": (
                            "true — убрать дату у записи. "
                            "Нельзя для встречи. Не сочетай с date."
                        ),
                    },
                    "is_completed": {
                        "type": ["boolean", "null"],
                        "description": (
                            "true — отметить выполненной, false — вернуть "
                            "в невыполненные."
                        ),
                    },
                },
                "required": ["id"],
                "additionalProperties": False,
            },
        },
    },
     # УДАЛЕНИЕ
    {
        "type": "function",
        "function": {
            "name": "delete_record",
            "description": (
                "Удалить существующую запись (встречу, напоминание или задачу). "
                "Сначала найди запись через search_records"
                "и возьми её id — не выдумывай id. Если подходящих записей "
                "несколько и неясно, какую удалять, уточни у пользователя."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "integer",
                        "description": "id удаляемой записи.",
                    },
                },
                "required": ["id"],
                "additionalProperties": False,
            },
        },
    }
    
]

 # ДЛЯ ПРОВЕРКИ ПРАВИЛЬНОГО ФОРМАТА ДАТ
def _optional_date(arguments, key, end_of_day=False):
    value = arguments.get(key)
    if value is None:
        return None, None
    if not isinstance(value, str):
        return None, f"Параметр {key} должен быть строкой в ISO 8601."
    try:
        parsed = parse_iso(value)
    except ValueError:
        return None, f"Параметр {key} должен быть в ISO 8601."
    if end_of_day and len(value.strip()) <= 10:
        parsed = parsed.replace(hour=23, minute=59, second=59)
    return parsed, None

 # СОЗДАНИЕ
def _execute_create_record(arguments, backend, embedder=None):
    record_type = arguments.get("type")
    title = arguments.get("title")
    record_date = arguments.get("date")
    created_at = arguments.get("created_at")
    is_completed = arguments.get("is_completed")

    if record_type not in RECORD_TYPES:
        return error("Некорректный тип записи.")
    if not isinstance(title, str) or not title.strip():
        return error("Не указано название записи.")
    if record_date is not None:
        if not isinstance(record_date, str):
            return error("Некорректная дата записи.")
        try:
            datetime.fromisoformat(record_date)
        except ValueError:
            return error("Дата записи должна быть в ISO 8601.")
    if record_type == "meeting" and record_date is None:
        return error("Для встречи необходимо указать дату и время.")
    if not isinstance(created_at, str):
        return error("Не указана дата создания.")
    try:
        datetime.fromisoformat(created_at)
    except ValueError:
        return error("Некорректная дата создания.")
    if not isinstance(is_completed, bool):
        return error("Статус выполнения должен быть true или false.")
    if is_completed:
        return error("Новая запись должна иметь статус false.")

    title = title.strip()
    embedding = None
    if embedder is not None:
        try:
            embedding = embedder.embed_document(
                build_embedding_text(record_type, title)
            )
        except Exception as e:
            print(f"Эмбеддинг не посчитан: {e}")

    return backend.create_record(
        record_type=record_type,
        title=title,
        record_date=record_date,
        created_at=created_at,
        is_completed=False,
        embedding=embedding,
    )
 # ПОИСК

def _execute_search_records(arguments, backend, embedder=None):
    query = arguments.get("query")
    record_type = arguments.get("type")
    is_completed = arguments.get("is_completed")
    top_k = arguments.get("top_k")

    if record_type is not None and record_type not in RECORD_TYPES:
        return error("Некорректный тип записи.")
    if is_completed is not None and not isinstance(is_completed, bool):
        return error("Параметр is_completed должен быть true или false.")
    if top_k is None:
        top_k = DEFAULT_TOP_K
    elif isinstance(top_k, bool) or not isinstance(top_k, int):
        return error("Параметр top_k должен быть целым числом.")
    top_k = max(1, min(top_k, MAX_TOP_K))

    date_from, err = _optional_date(arguments, "date_from")
    if err:
        return error(err)
    date_to, err = _optional_date(arguments, "date_to", end_of_day=True)
    if err:
        return error(err)
    if date_from and date_to and date_from > date_to:
        return error("date_from не может быть позже date_to.")

    if query is not None and not isinstance(query, str):
        return error("Параметр query должен быть строкой.")

    if not query or not query.strip():
        return backend.search_records(
            query_embedding=None,
            record_type=record_type,
            date_from=date_from,
            date_to=date_to,
            is_completed=is_completed,
            top_k=top_k,
        )

    words = _WORD_RE.findall(query.strip().lower())

    if words:
        text_result = backend.search_records_by_text(
            words,
            record_type=record_type,
            date_from=date_from,
            date_to=date_to,
            is_completed=is_completed,
            top_k=top_k,
        )
        if text_result.get("records"):
            return text_result

    if embedder is None:
        return {"success": True, "total_found": 0, "records": []}

    try:
        query_embedding = embedder.embed_query(query.strip())
    except Exception as e:
        print(f"Ошибка эмбеддинга запроса: {e}")
        query_embedding = None

    if query_embedding is None:
        return {"success": True, "total_found": 0, "records": []}

    vector_result = backend.search_records(
        query_embedding=query_embedding,
        record_type=record_type,
        date_from=date_from,
        date_to=date_to,
        is_completed=is_completed,
        top_k=top_k,
    )

    if vector_result.get("records"):
        return vector_result

    return {"success": True, "total_found": 0, "records": []}

 # ИЗМЕНЕНИЕ
def _execute_update_record(arguments, backend, embedder=None):
    record_id = arguments.get("id")
    if isinstance(record_id, bool) or not isinstance(record_id, int):
        return error("Не указан id записи.")
    record = backend.get_record(record_id)
    if record is None:
        return error(f"Запись с id={record_id} не найдена.")

    changes = {}
    new_type = arguments.get("type")
    if new_type is not None:
        if new_type not in RECORD_TYPES:
            return error("Некорректный тип записи.")
        changes["type"] = new_type

    new_title = arguments.get("title")
    if new_title is not None:
        if not isinstance(new_title, str) or not new_title.strip():
            return error("Название записи не может быть пустым.")
        changes["title"] = new_title.strip()

    new_date = arguments.get("date")
    clear_date = arguments.get("clear_date")
    if clear_date is not None and not isinstance(clear_date, bool):
        return error("Параметр clear_date должен быть true или false.")
    if new_date is not None and clear_date:
        return error("Нельзя одновременно указать date и clear_date.")
    if new_date is not None:
        if not isinstance(new_date, str):
            return error("Некорректная дата записи.")
        try:
            datetime.fromisoformat(new_date)
        except ValueError:
            return error("Дата записи должна быть в ISO 8601.")
        changes["date"] = new_date
    elif clear_date:
        changes["date"] = None

    new_completed = arguments.get("is_completed")
    if new_completed is not None:
        if not isinstance(new_completed, bool):
            return error("Статус выполнения должен быть true или false.")
        changes["is_completed"] = new_completed

    if not changes:
        return error("Не указано, что нужно изменить.")

    final_type = changes.get("type", record["type"])
    final_date = changes.get("date", record["date"])
    if final_type == "meeting" and final_date is None:
        return error("Для встречи необходимо указать дату и время.")

    embedding = None
    if embedder is not None and ("type" in changes or "title" in changes):
        try:
            embedding = embedder.embed_document(
                build_embedding_text(
                    final_type, changes.get("title", record["title"])
                )
            )
        except Exception as e:
            print(f"Эмбеддинг не пересчитан: {e}")

    return backend.update_record(record_id, changes, embedding=embedding)

 # УДАЛЕНИЕ
def _execute_delete_record(arguments, backend):
    record_id = arguments.get("id")
    if isinstance(record_id, bool) or not isinstance(record_id, int):
        return error("Не указан id записи.")

    record = backend.get_record(record_id)
    if record is None:
        return error(f"Запись с id={record_id} не найдена.")

    return backend.delete_record(record_id)

def execute_tool(name, arguments, backend, embedder=None):
    if not isinstance(arguments, dict):
        return error("Некорректные аргументы.")
    if backend is None:
        return error("Backend не подключён.")

    if name == "create_record":
        return _execute_create_record(arguments, backend, embedder)

    if name == "search_records":
        return _execute_search_records(arguments, backend, embedder)

    if name == "update_record":
        return _execute_update_record(arguments, backend, embedder)

    if name == "delete_record":
        return _execute_delete_record(arguments, backend)
    
    return error(f"Неизвестный инструмент: {name}")