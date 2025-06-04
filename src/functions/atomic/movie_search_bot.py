"""Telegram bot module for searching movies using OMDb API."""

import os
import logging
from typing import List, Dict, Any, Optional
import requests
import telebot
from telebot import types
from telebot.callback_data import CallbackData
from bot_func_abc import AtomicBotFunctionABC

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MovieSearchBotFunction(AtomicBotFunctionABC):
    """Atomic Telegram bot function for searching movies using OMDb API."""

    commands: List[str] = ["movie", "searchmovie"]
    authors: List[str] = ["astahov_alexander"]
    about: str = "Поиск фильмов по названию через OMDb API"
    description: str = (
        "Команда для поиска фильмов по названию с использованием OMDb API.\n"
        "Пример: /movie Interstellar\n"
        "Показывает список найденных фильмов, можно нажать на один для подробностей."
    )
    state: bool = True

    def __init__(self):
        self.bot = None
        self.omdb_url = "http://www.omdbapi.com/"
        self.movie_keyboard_factory = CallbackData("imdb_id", prefix="movie_detail")

    def set_handlers(self, bot: telebot.TeleBot):
        """Устанавливает обработчики команд и inline-кнопок."""
        self.bot = bot

        @bot.message_handler(commands=self.commands)
        def movie_search_handler(message: types.Message):
            try:
                args = message.text.split(maxsplit=1)
                if len(args) < 2:
                    bot.reply_to(message, "Укажите название фильма. Пример: /movie Interstellar")
                    return

                title = args[1].strip()
                if len(title) < 2:
                    bot.reply_to(message, "Введите хотя бы 2 символа.")
                    return

                movies = self._fetch_movies(title)
                if not movies:
                    bot.reply_to(message, "Фильмы не найдены.")
                    return

                markup = self._generate_movie_buttons(movies)
                bot.send_message(message.chat.id, "Найдено:", reply_markup=markup)
            except (ValueError, requests.exceptions.RequestException) as e:
                logger.error("Ошибка в обработчике поиска: %s", str(e))
                bot.reply_to(message, "Произошла ошибка при поиске фильмов")

        @bot.callback_query_handler(func=None, config=self.movie_keyboard_factory.filter())
        def movie_details_callback(call: types.CallbackQuery):
            try:
                callback_data = self.movie_keyboard_factory.parse(call.data)
                imdb_id = callback_data["imdb_id"]
                movie = self._fetch_movie_details(imdb_id)

                if not movie:
                    bot.answer_callback_query(call.id, "Ошибка при получении данных о фильме")
                    return

                response = self._format_movie_details(movie)

                if movie.get('Poster') and movie['Poster'] != 'N/A':
                    bot.send_photo(call.message.chat.id, movie['Poster'],
                                   caption=response, parse_mode='HTML')
                else:
                    bot.send_message(call.message.chat.id, response, parse_mode='HTML')

                bot.answer_callback_query(call.id)
            except (ValueError, requests.exceptions.RequestException) as e:
                logger.error("Ошибка в callback: %s", str(e))
                bot.answer_callback_query(call.id, "Произошла ошибка")

    def _fetch_movies(self, title: str) -> Optional[List[Dict[str, Any]]]:
        try:
            params = {
                "apikey": self._get_omdb_token(),
                "s": title,
                "type": "movie"
            }
            response = requests.get(self.omdb_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            logger.debug("API Response for '%s': %s", title, data)
            return data["Search"] if data.get("Response") == "True" else None
        except requests.exceptions.RequestException as e:
            logger.error("Ошибка при поиске фильмов: %s", str(e))
            return None

    def _fetch_movie_details(self, imdb_id: str) -> Optional[Dict[str, Any]]:
        try:
            params = {
                "apikey": self._get_omdb_token(),
                "i": imdb_id,
                "plot": "full"
            }
            response = requests.get(self.omdb_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            logger.debug("API Details for %s: %s", imdb_id, data)
            return data if data.get("Response") == "True" else None
        except requests.exceptions.RequestException as e:
            logger.error("Ошибка при получении деталей фильма: %s", str(e))
            return None

    def _get_omdb_token(self) -> str:
        token = os.getenv("OMDB_API_TOKEN")
        if not token:
            raise ValueError("OMDB_API_TOKEN не установлен в .env")
        return token

    def _generate_movie_buttons(self, movies: List[Dict[str, str]]) -> types.InlineKeyboardMarkup:
        markup = types.InlineKeyboardMarkup(row_width=1)
        for movie in movies[:5]:
            if 'imdbID' not in movie:
                continue
            btn_text = f"{movie['Title']} ({movie['Year']})"
            callback_data = self.movie_keyboard_factory.new(imdb_id=movie["imdbID"])
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=callback_data))
        return markup

    def _format_movie_details(self, movie: Dict[str, str]) -> str:
        return (
            f"<b>{movie.get('Title', 'N/A')}</b> ({movie.get('Year', 'N/A')})\n\n"
            f"<b>⭐ Рейтинг:</b> {movie.get('imdbRating', 'N/A')}/10\n"
            f"<b>📅 Дата выхода:</b> {movie.get('Released', 'N/A')}\n"
            f"<b>⏱ Длительность:</b> {movie.get('Runtime', 'N/A')}\n"
            f"<b>🎭 Жанр:</b> {movie.get('Genre', 'N/A')}\n"
            f"<b>👨‍💼 Режиссер:</b> {movie.get('Director', 'N/A')}\n"
            f"<b>👥 Актёры:</b> {movie.get('Actors', 'N/A')}\n\n"
            f"<b>📖 Сюжет:</b>\n{movie.get('Plot', 'Нет описания')}"
        )

"""Telegram bot module for searching movies using OMDb API."""

import os
import logging
from typing import List, Dict, Any, Optional
import requests
import telebot
from telebot import types
from bot_func_abc import AtomicBotFunctionABC

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MovieSearchBotFunction(AtomicBotFunctionABC):
    """Atomic Telegram bot function for searching movies using OMDb API."""

    commands: List[str] = ["movie", "searchmovie"]
    authors: List[str] = ["IHVH"]
    about: str = "Поиск фильмов по названию через OMDb API"
    description: str = (
        "Команда для поиска фильмов по названию с использованием OMDb API.\n"
        "Пример: /movie Interstellar\n"
        "Показывает список найденных фильмов, можно нажать на один для подробностей."
    )
    state: bool = True

    def __init__(self):
        self.bot = None
        self.omdb_url = "http://www.omdbapi.com/"

    def set_handlers(self, bot: telebot.TeleBot):
        """Устанавливает обработчики команд и inline-кнопок."""
        self.bot = bot

        @bot.message_handler(commands=self.commands)
        def movie_search_handler(message: types.Message):
            """Обработчик команды поиска фильма."""
            try:
                args = message.text.split(maxsplit=1)
                if len(args) < 2:
                    bot.reply_to(message, "Укажите название фильма. Пример: /movie Interstellar")
                    return

                title = args[1].strip()
                if len(title) < 2:
                    bot.reply_to(message, "Введите хотя бы 2 символа.")
                    return

                movies = self._fetch_movies(title)
                if not movies:
                    bot.reply_to(message, "Фильмы не найдены.")
                    return

                markup = self._generate_movie_buttons(movies)
                bot.send_message(message.chat.id, "Найдено:", reply_markup=markup)
            except (ValueError, requests.exceptions.RequestException) as e:
                logger.error("Ошибка в обработчике поиска: %s", str(e))
                bot.reply_to(message, "Произошла ошибка при поиске фильмов")

        @bot.callback_query_handler(func=lambda call: call.data.startswith('movie_detail:'))
        def movie_details_callback(call: types.CallbackQuery):
            """Обработчик нажатия на кнопку с фильмом."""
            try:
                imdb_id = call.data.split(':')[1]
                movie = self._fetch_movie_details(imdb_id)
                
                if not movie:
                    bot.answer_callback_query(call.id, "Ошибка при получении данных о фильме")
                    return

                response = self._format_movie_details(movie)
                
                if movie.get('Poster') and movie['Poster'] != 'N/A':
                    bot.send_photo(call.message.chat.id, movie['Poster'], 
                                 caption=response, parse_mode='HTML')
                else:
                    bot.send_message(call.message.chat.id, response, parse_mode='HTML')
                                    
                bot.answer_callback_query(call.id)
            except (ValueError, requests.exceptions.RequestException) as e:
                logger.error("Ошибка в callback: %s", str(e))
                bot.answer_callback_query(call.id, "Произошла ошибка")

    def _fetch_movies(self, title: str) -> Optional[List[Dict[str, Any]]]:
        """Ищет фильмы по названию."""
        try:
            params = {
                "apikey": self._get_omdb_token(),
                "s": title,
                "type": "movie"
            }
            response = requests.get(self.omdb_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            logger.debug("API Response for '%s': %s", title, data)
            return data["Search"] if data.get("Response") == "True" else None
        except requests.exceptions.RequestException as e:
            logger.error("Ошибка при поиске фильмов: %s", str(e))
            return None

    def _fetch_movie_details(self, imdb_id: str) -> Optional[Dict[str, Any]]:
        """Получает подробности о фильме по IMDb ID."""
        try:
            params = {
                "apikey": self._get_omdb_token(),
                "i": imdb_id,
                "plot": "full"
            }
            response = requests.get(self.omdb_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            logger.debug("API Details for %s: %s", imdb_id, data)
            return data if data.get("Response") == "True" else None
        except requests.exceptions.RequestException as e:
            logger.error("Ошибка при получении деталей фильма: %s", str(e))
            return None

    def _get_omdb_token(self) -> str:
        """Получает токен OMDb из переменных окружения."""
        token = os.getenv("OMDB_API_TOKEN")
        if not token:
            raise ValueError("OMDB_API_TOKEN не установлен в .env")
        return token

    def _generate_movie_buttons(self, movies: List[Dict[str, str]]) -> types.InlineKeyboardMarkup:
        """Создаёт inline-кнопки для списка фильмов."""
        markup = types.InlineKeyboardMarkup(row_width=1)
        for movie in movies[:5]:
            if 'imdbID' not in movie:
                continue
            btn_text = f"{movie['Title']} ({movie['Year']})"
            callback_data = f"movie_detail:{movie['imdbID']}"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=callback_data))
        return markup

    def _format_movie_details(self, movie: Dict[str, str]) -> str:
        """Форматирует подробности фильма в HTML-формат."""
        return (
            f"<b>{movie.get('Title', 'N/A')}</b> ({movie.get('Year', 'N/A')})\n\n"
            f"<b>⭐ Рейтинг:</b> {movie.get('imdbRating', 'N/A')}/10\n"
            f"<b>📅 Дата выхода:</b> {movie.get('Released', 'N/A')}\n"
            f"<b>⏱ Длительность:</b> {movie.get('Runtime', 'N/A')}\n"
            f"<b>🎭 Жанр:</b> {movie.get('Genre', 'N/A')}\n"
            f"<b>👨‍💼 Режиссер:</b> {movie.get('Director', 'N/A')}\n"
            f"<b>👥 Актёры:</b> {movie.get('Actors', 'N/A')}\n\n"
            f"<b>📖 Сюжет:</b>\n{movie.get('Plot', 'Нет описания')}"
        )
