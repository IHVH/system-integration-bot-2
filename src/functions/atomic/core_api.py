"""Поиск научных статей через CORE API по теме и DOI."""

import logging
import os
from typing import List

import requests
import telebot
from telebot import types
from telebot.callback_data import CallbackData

from bot_func_abc import AtomicBotFunctionABC  # pylint: disable=import-error

_CORE_API = "https://api.core.ac.uk/v3/search/works"
_MAX_LIMIT = 10
_DEFAULT_LIMIT = 5
_TIMEOUT = 10


class CoreSearchBotFunction(AtomicBotFunctionABC):  # pylint: disable=too-few-public-methods
    """Поиск научных статей через CORE API по теме или DOI."""

    commands: List[str] = ["core"]
    authors: List[str] = ["Talaniaeli"]
    about: str = "Поиск статей через CORE API."
    description: str = (
        "Поиск научных статей по теме или DOI.\n\n"
        "*Способ 1* — через меню:\n"
        "`/core` — открыть меню выбора типа поиска\n\n"
        "*Способ 2* — напрямую:\n"
        "`/core machine learning 5` — поиск по теме\n"
        "`/core 10.1000/xyz 3` — поиск по DOI\n\n"
        "Число в конце — количество результатов (макс. 10)."
    )
    state: bool = True

    bot: telebot.TeleBot
    keyboard_factory: CallbackData

    def set_handlers(self, bot: telebot.TeleBot):
        """Регистрация обработчиков сообщений."""
        self.bot = bot
        self.keyboard_factory = CallbackData("action", prefix=self.commands[0])

        @bot.message_handler(commands=self.commands)
        def cmd_handler(message: types.Message):
            args = message.text.partition(" ")[2].strip()
            if not args:
                bot.send_message(
                    message.chat.id,
                    "Выберите тип поиска или введите запрос напрямую:\n"
                    "`/core machine learning 5`",
                    reply_markup=self._main_markup(),
                    parse_mode="Markdown",
                )
                return
            query, limit = self._parse_args(args)
            field = "doi" if self._is_doi(query) else "topic"
            self._search_and_send(message.chat.id, query, limit, field)

        @bot.callback_query_handler(func=None, config=self.keyboard_factory.filter())
        def callback_handler(call: types.CallbackQuery):
            action = self.keyboard_factory.parse(call.data)["action"]
            prompts = {
                "topic": "Введите тему и количество:\nПример: `machine learning 5`",
                "doi":   "Введите DOI и количество:\nПример: `10.1000/xyz 3`",
            }
            if action not in prompts:
                return
            handlers = {"topic": self._handle_topic, "doi": self._handle_doi}
            msg = bot.send_message(call.message.chat.id, prompts[action], parse_mode="Markdown")
            bot.register_next_step_handler(msg, handlers[action])

    def _main_markup(self) -> types.InlineKeyboardMarkup:
        """Генерация главного меню."""
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "🔍 По теме", callback_data=self.keyboard_factory.new(action="topic")
            ),
            types.InlineKeyboardButton(
                "📄 По DOI", callback_data=self.keyboard_factory.new(action="doi")
            ),
        )
        return markup

    def _handle_topic(self, message: types.Message):
        """Обработка поиска по теме через меню."""
        query, limit = self._parse_args(message.text)
        self._search_and_send(message.chat.id, query, limit, "topic")

    def _handle_doi(self, message: types.Message):
        """Обработка поиска по DOI через меню."""
        doi, limit = self._parse_args(message.text)
        self._search_and_send(message.chat.id, doi, limit, "doi")

    @staticmethod
    def _build_query(text: str, field: str) -> str:
        """Построение поискового запроса в зависимости от типа."""
        if field == "doi":
            return f'doi:"{text}"'
        if " " in text:
            return f'title:"{text}"'
        return f"title:{text}"

    @staticmethod
    def _parse_args(text: str) -> tuple:
        """Разбор текста на запрос и лимит."""
        parts = text.rsplit(" ", 1)
        if len(parts) == 2 and parts[1].isdigit():
            return parts[0].strip(), min(int(parts[1]), _MAX_LIMIT)
        return text.strip(), _DEFAULT_LIMIT

    @staticmethod
    def _is_doi(text: str) -> bool:
        """Определение, является ли текст DOI."""
        return text.startswith("10.") and "/" in text

    def _search_and_send(self, chat_id: int, query: str, limit: int, field: str):
        """Выполнение запроса и отправка результатов."""
        built_query = self._build_query(query, field)
        results = self._fetch(built_query, limit)

        if not results and field == "topic":
            logging.info("Title search empty, falling back to fulltext: %s", query)
            results = self._fetch(query, limit)

        if not results:
            self.bot.send_message(chat_id, "По вашему запросу ничего не найдено.")
            return
        for item in results:
            self.bot.send_message(chat_id, self._format_result(item), parse_mode="Markdown")

    def _fetch(self, query: str, limit: int) -> list:
        """Запрос к CORE API."""
        token = os.environ.get("CORE_API_KEY", "")
        try:
            response = requests.get(
                _CORE_API,
                headers={"Authorization": f"Bearer {token}"},
                params={"q": query, "limit": limit},
                timeout=_TIMEOUT,
            )
            if response.status_code in (200, 500):
                results = response.json().get("results", [])
                if results:
                    return results
            logging.warning("CORE API %s: %s", response.status_code, response.text[:100])
        except requests.RequestException as exc:
            logging.exception(exc)
        return []

    def _format_result(self, item: dict) -> str:
        """Форматирование одного результата поиска."""
        title = item.get("title") or "Без названия"
        authors = ", ".join(
            a.get("name", "") for a in item.get("authors", [])[:3] if a.get("name")
        )
        year = item.get("yearPublished") or "—"
        doi = item.get("doi", "")
        url = item.get("downloadUrl", "")

        lines = [f"*{title}*"]
        if authors:
            lines.append(f"👤 {authors}")
        lines.append(f"📅 {year}")
        if doi:
            lines.append(f"DOI: `{doi}`")
        if url:
            lines.append(f"[Скачать PDF]({url})")
        return "\n".join(lines)
