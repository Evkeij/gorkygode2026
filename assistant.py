"""
Основной модуль голосового ассистента.
Реализует класс Assistant, который взаимодействует с Yandex Cloud LLM,
выполняет tool-calling и поддерживает контекст диалога.
"""

import json
import os
import sys
from datetime import datetime, timedelta

import openai
from dotenv import load_dotenv

from Backend import SQLiteBackend
from embeddings import Embedder
from tools import TOOLS, execute_tool

# Определяем, откуда мы запущены (из .exe или из кода)
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.join(os.getenv("APPDATA"), "DescVoice")
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

env_path = os.path.join(BASE_DIR, ".env")
load_dotenv(env_path)

YANDEX_CLOUD_FOLDER = os.getenv("YANDEX_CLOUD_FOLDER")
YANDEX_CLOUD_API_KEY = os.getenv("YANDEX_CLOUD_API_KEY")
YANDEX_CLOUD_MODEL = "aliceai-llm/latest"

# Проверка, что ключи загрузились (если нет, выводим ошибку)
if not YANDEX_CLOUD_API_KEY:
    raise RuntimeError(f"Не найден API ключ. Проверьте файл {env_path}")


MAX_TOOL_STEPS = 5
MAX_CONTEXT_TOKENS = 4000

DEBUG = os.environ.get("DEBUG") == "1"

SYSTEM_PROMPT = """
Ты — русскоязычный голосовой ассистент женского пола для личных задач и напоминаний.
Задача: создавать, изменять, искать и выводить пользователю напоминания, встречи и задачи.
ГЛАВНОЕ ПРАВИЛО: время встреч и записей нельзя придумывать, если пользователь не назвал время - переспроси
(в следующий понедельник у меня врач -> спросить во сколько у вас прием?).
    - «планы на 22 октября», «какие записи на завтра» — search_records с date_from и date_to,
    равными этой дате в формате YYYY-MM-DD, (is_completed=false)
    - «когда мне к врачу», «во сколько в школу», «где запись про …» — search_records с коротким query (тема поиска
    без дат и вопросительных слов), (is_completed=false)
    - Если пользователь сообщает о выполнении какого-либо действия — используй search_records, найди и измени запись на
    is_completed.

Правила работы с датой и временем:
    - Преобразуй относительные дату и время в формат ISO 8601: YYYY-MM-DDTHH:MM:SS
    - Если пользователь говорит «в 8 утра» — это 08:00. «В 8 вечера» — это 20:00, если в 12 часовом формате
    (час - шесть) - переспроси утра или вечера.
    - Если пользователь использует слова «следующий», «ближайший», «эта неделя», «следующая неделя», ты обязан найти
    текущие дату и время в начале сообщения и вычислить дату записи с помощью СПРАВОЧНИКА ДАТ. Если не уверен — спроси.
   Обычный разговор и формат вывода:
    - Если ты выводишь более одной записи (задачи, встречи, напоминания), каждая запись должна быть на новой строке в
    формате: - [название] [дата] [время]. Не перечисляй записи через запятую в одном предложении.
    - После выполнения инструмента кратко сообщи результат в разговорной форме для аудио вывода (дата, время).
    - Не используй markdown-разметку и смайлики (эмодзи).
"""


def debug(*args, **kwargs):
    """Печатает отладочную информацию, если включен DEBUG."""
    if DEBUG:
        print(*args, **kwargs)


def flatten_tools(tools):
    """Приводит описание инструментов к плоскому формату, ожидаемому API."""
    result = []
    for tool in tools:
        if tool.get("type") == "function" and "function" in tool:
            fn = tool["function"]
            result.append(
                {
                    "type": "function",
                    "name": fn["name"],
                    "description": fn.get("description", ""),
                    "parameters": fn.get(
                        "parameters",
                        {"type": "object", "properties": {}},
                    ),
                }
            )
        else:
            result.append(tool)
    return result


class Assistant:
    """
    Текстовый ассистент для управления задачами, напоминаниями и встречами.
    Использует Yandex Cloud LLM с поддержкой function calling.
    """

    def __init__(self):
        if not YANDEX_CLOUD_API_KEY:
            raise RuntimeError("Не задана YANDEX_CLOUD_API_KEY.")
        if not YANDEX_CLOUD_FOLDER:
            raise RuntimeError("Не задана YANDEX_CLOUD_FOLDER.")

        self.client = openai.OpenAI(
            api_key=YANDEX_CLOUD_API_KEY,
            base_url="https://ai.api.cloud.yandex.net/v1",
            project=YANDEX_CLOUD_FOLDER,
        )

        self.embedder = Embedder(self.client, YANDEX_CLOUD_FOLDER)
        self.backend = SQLiteBackend()
        self.last_response_id = None
        self.tools = flatten_tools(TOOLS)

    # очистка контекста (максимум выбираем в MAX_CONTEXT_TOKEN)

    def _remember_response(self, response):
        """Запоминает id ответа для  продолжения диалога.
        Если вход вырос до MAX_CONTEXT_TOKENS и более, контекст очищается:
        следующий запрос уйдет без previous_response_id."""
        input_tokens = 0
        usage = getattr(response, "usage", None)
        if usage is not None:
            input_tokens = getattr(usage, "input_tokens", 0) or 0

        if input_tokens >= MAX_CONTEXT_TOKENS:
            debug(
                f"»> КОНТЕКСТ ОЧИЩЕН: input_tokens={input_tokens} "
                f">= {MAX_CONTEXT_TOKENS}"
            )
            self.last_response_id = None
        else:
            self.last_response_id = response.id

    def _run_tool(self, name, arguments):
        """Выполняет указанный инструмент и возвращает результат."""
        if not isinstance(arguments, dict):
            return {
                "success": False,
                "error": "Аргументы инструмента должны быть объектом.",
            }
        return execute_tool(name, arguments, self.backend, self.embedder)

    def _debug_response(self, response, step):
        """Выводит подробную информацию об ответе модели в режиме отладки."""
        if not DEBUG:
            return

        print(f"\n--- ШАГ {step + 1} ---")
        print(f"status = {response.status}")
        print(f"incomplete = {response.incomplete_details}")
        print(f"error = {response.error}")
        print(f"usage = {response.usage}")
        print(f"output_text = {response.output_text!r}")

        for item in response.output:
            print(f"  - type={item.type}", end="")

            if item.type == "function_call":
                print(
                    f", name={item.name}, "
                    f"call_id={item.call_id}, "
                    f"arguments={item.arguments!r}"
                )
            elif item.type == "message":
                print(f", content={item.content!r}")
            else:
                print()

        print("--- КОНЕЦ ШАГА ---\n")

    def handle(self, user_text):  # noqa: max-complexity=25
        """Обрабатывает текстовый запрос пользователя: вызывает LLM, выполняет инструменты и возвращает ответ."""

        now = datetime.now().astimezone()
        current_time = now.isoformat(timespec="minutes")
        # вывод числа и дня недели для ближайших 14 дней, передача в модель в помощь вычисления относительных дат
        weekdays = [
            "Понедельник",
            "Вторник",
            "Среда",
            "Четверг",
            "Пятница",
            "Суббота",
            "Воскресенье",
        ]
        calendar_helper = "СПРАВОЧНИК ДАТ (используй его для вычисления следующий, ближайший и тп.):\n"
        for i in range(14):
            d = now + timedelta(days=i)
            calendar_helper += f"- {weekdays[d.weekday()]} — {d.strftime('%d.%m.%Y')}\n"

        user_input = (
            f"Текущее местное время: {current_time}\n"
            f"{calendar_helper}\n"
            f"Запрос пользователя: {user_text}"
        )
        # запрос к модели
        try:
            response = self._create_response(
                input=user_input,
                previous_id=self.last_response_id,
            )

            for step in range(MAX_TOOL_STEPS):
                tool_calls = [
                    item for item in response.output if item.type == "function_call"
                ]

                self._debug_response(response, step)

                if not tool_calls:
                    self._remember_response(response)
                    return response.output_text.strip() or "Не удалось получить ответ."

                outputs = []

                for call in tool_calls:
                    try:
                        args = json.loads(call.arguments) if call.arguments else {}
                    except (json.JSONDecodeError, TypeError):
                        args = None

                    debug(f"»> ВЫЗОВ ИНСТРУМЕНТА: {call.name}")
                    debug(f"»> АРГУМЕНТЫ: {args}")

                    if args is None:
                        result = {
                            "success": False,
                            "error": "Модель передала некорректные аргументы.",
                        }
                    else:
                        try:
                            result = self._run_tool(call.name, args)
                        except Exception as error:
                            print(f"Ошибка инструмента: {error}")
                            result = {
                                "success": False,
                                "error": "Не удалось выполнить инструмент.",
                            }

                    result_json = json.dumps(result, ensure_ascii=False, default=str)
                    debug(f"»> РЕЗУЛЬТАТ: {result_json}\n")

                    outputs.append(
                        {
                            "type": "function_call_output",
                            "call_id": call.call_id,
                            "output": result_json,
                        }
                    )

                response = self._create_response(
                    input=outputs,
                    previous_id=response.id,
                )

            self._remember_response(response)
            return response.output_text.strip() or "Готово, но ответ пустой."
        # если не получилось получить ответ от модели
        except openai.BadRequestError as error:
            if self.last_response_id is not None:
                self.last_response_id = None
                try:
                    response = self._create_response(
                        input=user_input,
                        previous_id=None,
                    )
                    self._remember_response(response)
                    return response.output_text.strip() or "Не удалось получить ответ."
                except Exception as retry_error:
                    print(f"Повторная ошибка: {retry_error}")

            print(f"BadRequest: {error}")
            return "Произошла ошибка при обработке запроса."

        except Exception as error:
            print(f"Ошибка ассистента: {error}")
            return "Произошла ошибка при обработке запроса."

    def _create_response(self, input, previous_id):
        """Создает запрос к Yandex Cloud Responses API."""
        return self.client.responses.create(
            model=f"gpt://{YANDEX_CLOUD_FOLDER}/{YANDEX_CLOUD_MODEL}",
            temperature=0.2,
            instructions=SYSTEM_PROMPT,
            input=input,
            tools=self.tools,
            max_output_tokens=1000,
            previous_response_id=previous_id,
        )
