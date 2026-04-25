"""Модуль содержит реализацию команд /film и /movie
для поиска фильмов через OMDb API в Telegram-боте."""


import os
import logging
from typing import List, Optional, Dict

import requests
import telebot
from telebot import types
from telebot.callback_data import CallbackData

from bot_func_abc import AtomicBotFunctionABC


class OMDbServiceError(Exception):
    """Исключение для ошибок при работе с OMDb API."""


class OMDbService:
    """Сервис для взаимодействия с OMDb API."""

    BASE_URL = "http://www.omdbapi.com/"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OMDB_API_KEY")

        if not self.api_key:
            raise ValueError("OMDb API key is required")

        self.logger = logging.getLogger(__name__)

    def _request(self, params: Dict) -> Dict:
        params["apikey"] = self.api_key

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()

        except requests.exceptions.RequestException as e:
            self.logger.exception("HTTP error during OMDb request")
            raise OMDbServiceError(f"HTTP error: {e}") from e

        except ValueError as e:
            self.logger.exception("Invalid JSON response")
            raise OMDbServiceError("Invalid JSON response from API") from e

        if data.get("Response") == "False":
            raise OMDbServiceError(data.get("Error", "Unknown API error"))

        return data

    def search(self, query: str) -> Dict:
        """Поиск фильмов по названию."""
        return self._request({"s": query})

    def get_movie(self, imdb_id: str) -> Dict:
        """Получение подробной информации по imdbID."""
        return self._request({"i": imdb_id})


class AtomicMovieSearchBotFunction(AtomicBotFunctionABC):
    """Команды для поиска фильмов через OMDb API."""

    commands: List[str] = ["movie", "film"]
    authors: List[str] = ["BLazzeD21"]
    about: str = "Поиск фильмов через OMDb"

    description: str = """
        Функция ищет фильмы по названию и показывает информацию в Telegram.

        Использование:
        /movie <название>
        /film <название>

        Примеры:
        /movie Batman
        /film Interstellar

        Если название не указано, бот попросит его ввести.

        После этого выводится список найденных фильмов с пагинацией. Выберите нужный фильм, чтобы получить детали: название, год, рейтинг, жанр, описание и постер (если есть).
    """

    state: bool = True
    PAGE_SIZE = 3

    bot: telebot.TeleBot
    cb_factory: CallbackData
    movie_service: Optional[OMDbService] = None

    search_cache: Dict[int, List[dict]] = {}

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def set_handlers(self, bot: telebot.TeleBot):
        """Регистрирует обработчики сообщений и callback-кнопок."""

        self.bot = bot
        self.cb_factory = CallbackData("action", "value", prefix=self.commands[0])

        self._init_service()

        @bot.message_handler(commands=self.commands)
        def movie_handler(message: types.Message):

            if not self.movie_service:
                self.bot.reply_to(message, "OMDbService is not initialized")
                return

            args = message.text.split(maxsplit=1)

            if len(args) < 2:
                msg = bot.send_message(
                    message.chat.id,
                    "🔍 _Enter movie title_",
                    parse_mode='MarkdownV2'
                )
                bot.register_next_step_handler(msg, self._search_next_step)
                return

            self._search_movie(message.chat.id, args[1])

        @bot.callback_query_handler(func=None, config=self.cb_factory.filter())
        def callback_handler(call: types.CallbackQuery):

            if not self.movie_service:
                bot.answer_callback_query(call.id, "OMDbService is not initialized")
                return

            data = self.cb_factory.parse(call.data)
            action = data["action"]
            value = data["value"]

            if action == "details":
                self._send_movie_details(call.message.chat.id, value)

            elif action == "page":
                self._render_page(
                    call.message.chat.id,
                    int(value),
                    call.message.message_id
                )

    def _init_service(self):
        try:
            self.movie_service = OMDbService()
        except ValueError as e:
            self.logger.error("Service init error: %s", e)
            self.movie_service = None

    def _search_next_step(self, message: types.Message):
        self._search_movie(message.chat.id, message.text)

    def _search_movie(self, chat_id: int, query: str):
        loading_msg = self.bot.send_message(
            chat_id,
            "⌛️ <i>Searching movies...</i>",
            parse_mode='HTML'
        )

        try:
            data = self.movie_service.search(query)
            movies = data.get("Search", [])

            self.bot.delete_message(chat_id, loading_msg.message_id)

            if not movies:
                self.bot.send_message(
                    chat_id,
                    "❌ _No results found_",
                    parse_mode='MarkdownV2'
                )
                return

            self.search_cache[chat_id] = movies
            self._render_page(chat_id, 0)

        except OMDbServiceError as e:
            self.bot.delete_message(chat_id, loading_msg.message_id)
            self.logger.error("Search error: %s", e)
            self.bot.send_message(
                chat_id,
                f"⛔️ <b>Error:</b> <i>{e}</i>",
                parse_mode='HTML'
            )

    def _render_page(self, chat_id: int, page: int, message_id: int = None):
        movies = self.search_cache.get(chat_id)

        if not movies:
            self.bot.send_message(
                chat_id,
                "_No cached results found_",
                parse_mode='MarkdownV2'
            )
            return

        total_pages = (len(movies) - 1) // self.PAGE_SIZE + 1

        start = page * self.PAGE_SIZE
        end = start + self.PAGE_SIZE
        page_movies = movies[start:end]

        markup = types.InlineKeyboardMarkup()

        for movie in page_movies:
            markup.add(
                types.InlineKeyboardButton(
                    f"{self._safe(movie.get('Title'))} ({self._safe(movie.get('Year'))})",
                    callback_data=self.cb_factory.new(
                        action="details",
                        value=movie.get("imdbID")
                    )
                )
            )

        markup.row(*self._build_navigation(page, total_pages))

        text = (
            f"🔍 <b>Found:</b> <i>{len(movies)}</i>\n\n"
            f"📃<b>Page:</b> <i>{page + 1}/{total_pages}</i>"
        )

        if message_id:
            try:
                self.bot.edit_message_text(
                    text,
                    chat_id,
                    message_id,
                    reply_markup=markup,
                    parse_mode="HTML"
                )
                return
            except telebot.apihelper.ApiTelegramException as e:
                self.logger.warning("Failed to edit message: %s", e)

        self.bot.send_message(
            chat_id,
            text,
            reply_markup=markup,
            parse_mode="HTML"
        )

    def _build_navigation(self, page: int, total_pages: int):
        nav = []

        if page > 0:
            nav.append(
                types.InlineKeyboardButton(
                    "⬅️ Previous",
                    callback_data=self.cb_factory.new(
                        action="page",
                        value=str(page - 1)
                    )
                )
            )

        nav.append(types.InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))

        if page < total_pages - 1:
            nav.append(
                types.InlineKeyboardButton(
                    "Next ➡️",
                    callback_data=self.cb_factory.new(
                        action="page",
                        value=str(page + 1)
                    )
                )
            )

        return nav

    def _send_movie_details(self, chat_id: int, imdb_id: str):
        loading_msg = self.bot.send_message(
            chat_id,
            "⌛️ <i>Loading...</i>",
            parse_mode='HTML'
        )

        try:
            data = self.movie_service.get_movie(imdb_id)
            self.bot.delete_message(chat_id, loading_msg.message_id)

        except OMDbServiceError as e:
            self.bot.delete_message(chat_id, loading_msg.message_id)
            self.bot.send_message(
                chat_id,
                f"⛔️ <b>Error:</b> <i>{e}</i>",
                parse_mode='HTML'
            )
            return

        text = (
            f"🎬 <b>Title:</b> <i>{self._safe(data.get('Title'))}</i>\n\n"
            f"📅 <b>Year:</b> <i>{self._safe(data.get('Year'))}</i>\n"
            f"⭐ <b>IMDB:</b> <i>{self._safe(data.get('imdbRating'))}</i>\n"
            f"🎭 <b>Genre:</b> <i>{self._safe(data.get('Genre'))}</i>\n\n"
            f"📕 <b>Plot:</b> <i>{self._safe(data.get('Plot'))}</i>"
        )

        poster = data.get("Poster")

        if poster and poster != "N/A":
            try:
                self.bot.send_photo(
                    chat_id,
                    poster,
                    caption=text,
                    parse_mode='HTML'
                )
                return
            except telebot.apihelper.ApiTelegramException as e:
                self.logger.info("Failed to send message with poster: %s", e)

        self.bot.send_message(
            chat_id,
            text,
            parse_mode='HTML'
        )

    def _safe(self, value, default="—"):
        return default if not value or value == "N/A" else value
