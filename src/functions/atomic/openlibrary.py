"""Module implementation of the atomic function of the telegram bot.
Open Library API integration."""

import logging
import time
from typing import Dict, List, Optional

import requests
import telebot
from telebot import types

from bot_func_abc import AtomicBotFunctionABC

logger = logging.getLogger(__name__)

class OpenLibraryBotFunction(AtomicBotFunctionABC):
    """Integration with OpenLibrary API for book searching."""

    commands: List[str] = ["find_book", "find_author"]
    authors: List[str] = ["Ankik-69"]
    state: bool = True
    about: str = "Поиск книг в OpenLibrary"
    description: str = (
        "Интеграция с API OpenLibrary.\n\n"
        "Команды:\n"
        "/find_book — интерактивный поиск (меню с 3 опциями)\n"
        "/find_author <имя> — быстрый поиск книг по автору\n\n"
        "Опции в /find_book:\n"
        "• По названию — поиск по заголовку книги\n"
        "• По автору — список всех книг автора\n"
        "• Онлайн-чтение — книги, доступные для чтения/скачивания"
    )

    BASE_URL = "https://openlibrary.org/"
    SEARCH_URL = BASE_URL + "search.json"
    BOOKS_URL = BASE_URL + "books/"
    TIMEOUT = 10
    MAX_RESULTS = 5

    bot: telebot.TeleBot
    _user_states: Dict[int, Dict[str, str]] = {}

    def set_handlers(self, bot: telebot.TeleBot):
        """Register all message and callback handlers for the bot."""
        self.bot = bot

        @bot.message_handler(commands=[self.commands[0]])
        def handle_find_book(message: types.Message):
            logger.info("Command /find_book from user %s", message.from_user.id)
            self._show_search_menu(message.chat.id)

        @bot.message_handler(commands=[self.commands[1]])
        def handle_find_author(message: types.Message):
            logger.info("Command /find_author from user %s", message.from_user.id)
            args = message.text.split(maxsplit=1)
            if len(args) < 2:
                self.bot.send_message(
                    message.chat.id,
                    "Укажите имя автора.\nПример: `/find_author Shaw`",
                    parse_mode="Markdown"
                )
                return

            author_name = args[1].strip()
            self.bot.send_chat_action(message.chat.id, "typing")
            results = self._search_books(author_name, search_type="author")
            self._send_results(message.chat.id, results, f"по автору \"{author_name}\"")

        @bot.callback_query_handler(
            func=lambda call: call.data.startswith(self.commands[0])
        )
        def handle_search_type_callback(call: types.CallbackQuery):
            chat_id = call.message.chat.id
            action = call.data.replace(self.commands[0], "")

            self._user_states[chat_id] = {"step": "waiting_query", "search_type": action}

            prompts = {
                "title": "Введите название книги:",
                "author": "Введите имя автора:",
                "online": "Введите название для поиска книг онлайн:"
            }

            self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=prompts.get(action, "Введите запрос:")
            )
            self.bot.answer_callback_query(call.id)

        @bot.message_handler(func=lambda msg: msg.chat.id in self._user_states)
        def handle_user_query(message: types.Message):
            chat_id = message.chat.id
            state = self._user_states.get(chat_id)

            if not state or state.get("step") != "waiting_query":
                return

            query = message.text.strip()
            search_type = state.get("search_type", "title")

            self.bot.send_chat_action(chat_id, "typing")

            if search_type == "online":
                results = self._search_online_books(query)
            else:
                results = self._search_books(query, search_type=search_type)

            mode_names = {"title": "по названию", "author": "по автору", "online": "онлайн"}
            mode_label = mode_names.get(search_type, "по запросу")
            mode_text = f'{mode_label} "{query}"'
            self._send_results(chat_id, results, mode_text)

            self._user_states.pop(chat_id, None)

    def _show_search_menu(self, chat_id: int):
        markup = types.InlineKeyboardMarkup(row_width=1)
        cmd = self.commands[0]

        btn_title = types.InlineKeyboardButton(
            "По названию книги",
            callback_data=f"{cmd}title"
        )
        btn_author = types.InlineKeyboardButton(
            "Книги автора",
            callback_data=f"{cmd}author"
        )
        btn_online = types.InlineKeyboardButton(
            "Доступно онлайн",
            callback_data=f"{cmd}online"
        )
        markup.add(btn_title, btn_author, btn_online)

        self.bot.send_message(
            chat_id,
            "Выберите тип поиска:",
            reply_markup=markup
        )

    def _search_books(
        self,
        query: str,
        search_type: str = "title",
        limit: Optional[int] = None
    ) -> List[dict]:
        if limit is None:
            limit = self.MAX_RESULTS

        if search_type in ("title", "author"):
            q = f'{search_type}:"{query}"'
        else:
            q = query
        params = {"q": q, "limit": limit * 2}

        try:
            response = requests.get(self.SEARCH_URL, params=params, timeout=self.TIMEOUT)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.exception("OpenLibrary API request failed")
            return [{"error": str(e)}]

        results = []
        for doc in data.get("docs", [])[:limit]:
            book = {
                "title": doc.get("title", "Без названия"),
                "authors": ", ".join(doc.get("author_name", ["Автор неизвестен"])),
                "first_publish_year": doc.get("first_publish_year", "Год не указан"),
                "edition_key": doc.get("cover_edition_key"),
                "key": doc.get("key", ""),
            }
            results.append(book)

        return results

    def _search_online_books(self, query: str, limit: Optional[int] = None) -> List[dict]:
        if limit is None:
            limit = self.MAX_RESULTS

        books = self._search_books(query, search_type="title", limit=limit * 3)
        online_books = []

        for book in books:
            if not book.get("edition_key"):
                continue
            try:
                time.sleep(0.3)
                url = f"{self.BOOKS_URL}{book['edition_key']}.json"
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    if "ocaid" in data:
                        book["read_url"] = f"https://archive.org/details/{data['ocaid']}"
                        book["pages"] = data.get("number_of_pages", "—")
                        online_books.append(book)
                        if len(online_books) >= limit:
                            break
            except Exception as e:  # pylint: disable=broad-except
                logger.warning("Failed to fetch details for %s: %s", book.get("title"), e)
                continue

        return online_books

    def _send_results(self, chat_id: int, books: List[dict], context: str):
        if not books or ("error" in books[0] if isinstance(books, list) and books else False):
            self.bot.send_message(chat_id, "Ничего не найдено или произошла ошибка.")
            return

        lines = [f"Найдено: {len(books)} книг {context}\n"]

        for i, book in enumerate(books, 1):
            title = self._escape_md(book["title"])
            lines.append(f"{i}. *{title}*")
            lines.append(f"   {book['authors']}")
            lines.append(f"   {book['first_publish_year']}")

            if book.get("read_url"):
                lines.append(f"   [Читать/Скачать]({book['read_url']})")
            elif book.get("key"):
                ol_link = f"https://openlibrary.org{book['key']}"
                lines.append(f"   [Страница в OpenLibrary]({ol_link})")

            lines.append("")

        text = "\n".join(lines).strip()
        self.bot.send_message(
            chat_id,
            text,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

    @staticmethod
    def _escape_md(text: str) -> str:
        text = text.replace("_", "\\_").replace("*", "\\*")
        text = text.replace("[", "\\[").replace("`", "\\`")
        return text.replace("]", "\\]")
