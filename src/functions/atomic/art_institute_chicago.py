"""
Функция Telegram-бота для работы с API Art Institute of Chicago.
"""

from typing import Any, Dict, List, Optional

import requests
import telebot
from telebot import types

from bot_func_abc import AtomicBotFunctionABC


class ArtInstituteChicagoBotFunction(AtomicBotFunctionABC):
    """
    Функция бота для поиска произведений искусства.
    """

    commands: List[str] = [
        "art_institute_chicago",
        "artworks",
        "artwork",
        "artsearch",
    ]
    authors: List[str] = ["polina.tsvetkova.05@mail.ru"]
    about: str = "Интеграция с Art Institute of Chicago"
    description: str = (
        "Функция работает с API Art Institute of Chicago. "
        "Команды: /artworks — получить список работ; "
        "/artwork ID — получить подробную информацию по ID; "
        "/artsearch текст — поиск работ по названию или ключевым словам. "
        "Разработал студент ОУИТБ-ПИ01-23-3 Цветкова Полина."
    )
    state: bool = True

    API_URL = "https://api.artic.edu/api/v1/artworks"
    FIELDS = (
        "id,title,artist_display,date_display,place_of_origin,"
        "medium_display,dimensions,department_title,artwork_type_title"
    )

    def set_handlers(self, bot: telebot.TeleBot) -> None:
        """
        Настройка команд и кнопок бота.
        """

        @bot.message_handler(commands=["art_institute_chicago"])
        def info_handler(message: types.Message) -> None:
            """Показать описание функции и кнопки."""

            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton(
                "🎨 Список работ", callback_data="artworks"
            ))
            keyboard.add(types.InlineKeyboardButton(
                "🔎 Поиск работ", callback_data="artsearch"
            ))
            keyboard.add(types.InlineKeyboardButton(
                "🖼 Информация по ID", callback_data="artwork"
            ))

            bot.reply_to(message, self.description, reply_markup=keyboard)

        @bot.message_handler(commands=["artworks"])
        def artworks_handler(message: types.Message) -> None:
            """Обработка команды /artworks."""

            bot.reply_to(message, self._safe_artworks_answer())

        @bot.message_handler(commands=["artwork"])
        def artwork_handler(message: types.Message) -> None:
            """Обработка команды /artwork."""

            artwork_id = self._get_argument(message.text, "/artwork")

            if not artwork_id:
                bot.reply_to(message, "Введите ID работы. Пример: /artwork 129884")
                return

            bot.reply_to(message, self._safe_artwork_by_id_answer(artwork_id))

        @bot.message_handler(commands=["artsearch"])
        def artsearch_handler(message: types.Message) -> None:
            """Обработка команды /artsearch."""

            query = self._get_argument(message.text, "/artsearch")

            if not query:
                bot.reply_to(message, "Введите текст для поиска. Пример: /artsearch van gogh")
                return

            bot.reply_to(message, self._safe_search_answer(query))

        @bot.callback_query_handler(func=lambda call: call.data in self.commands)
        def button_handler(call: types.CallbackQuery) -> None:
            """Обработка нажатий на кнопки."""

            if call.data == "artworks":
                bot.send_message(call.message.chat.id, self._safe_artworks_answer())

            elif call.data == "artsearch":
                bot.send_message(
                    call.message.chat.id,
                    "Введите текст для поиска так:\n/artsearch van gogh"
                )

            elif call.data == "artwork":
                bot.send_message(
                    call.message.chat.id,
                    "Введите ID работы так:\n/artwork 129884"
                )

            bot.answer_callback_query(call.id)

    @staticmethod
    def _get_argument(message_text: Optional[str], command: str) -> str:
        """
        Получить текст после команды.
        """

        if not message_text:
            return ""

        return message_text.replace(command, "", 1).strip()

    @classmethod
    def _get_data(cls, url: str, params: Dict[str, Any]) -> Any:
        """
        Получить данные из API.
        """

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json().get("data", [])

    @classmethod
    def _get_artworks(cls) -> List[Dict[str, Any]]:
        """
        Получить список работ.
        """

        return cls._get_data(
            cls.API_URL,
            {
                "limit": 5,
                "fields": cls.FIELDS,
            }
        )

    @classmethod
    def _get_artwork_by_id(cls, artwork_id: str) -> Optional[Dict[str, Any]]:
        """
        Получить работу по ID.
        """

        return cls._get_data(
            f"{cls.API_URL}/{artwork_id}",
            {
                "fields": cls.FIELDS,
            }
        )

    @classmethod
    def _search_artworks(cls, query: str) -> List[Dict[str, Any]]:
        """
        Найти работы по тексту.
        """

        return cls._get_data(
            f"{cls.API_URL}/search",
            {
                "q": query,
                "limit": 5,
                "fields": cls.FIELDS,
            }
        )

    @classmethod
    def _safe_artworks_answer(cls) -> str:
        """
        Безопасно получить ответ со списком работ.
        """

        try:
            return cls._format_artworks(cls._get_artworks())
        except requests.RequestException as error:
            return f"Ошибка при запросе к API: {error}"

    @classmethod
    def _safe_artwork_by_id_answer(cls, artwork_id: str) -> str:
        """
        Безопасно получить ответ по ID.
        """

        try:
            artwork = cls._get_artwork_by_id(artwork_id)

            if not artwork:
                return "Работа с таким ID не найдена."

            return cls._format_artwork(artwork)

        except requests.RequestException as error:
            return f"Ошибка при запросе к API: {error}"

    @classmethod
    def _safe_search_answer(cls, query: str) -> str:
        """
        Безопасно получить ответ поиска.
        """

        try:
            return cls._format_artworks(cls._search_artworks(query))
        except requests.RequestException as error:
            return f"Ошибка при запросе к API: {error}"

    @classmethod
    def _format_artworks(cls, artworks: List[Dict[str, Any]]) -> str:
        """
        Оформить список работ.
        """

        if not artworks:
            return "Работы не найдены."

        return "\n\n-------------------\n\n".join(
            cls._format_artwork(artwork) for artwork in artworks
        )

    @staticmethod
    def _format_artwork(artwork: Dict[str, Any]) -> str:
        """
        Оформить одну работу.
        """

        return (
            "🎨 Детальная информация\n\n"
            f"ID: {artwork.get('id', 'Нет данных')}\n"
            f"Название: {artwork.get('title', 'Нет данных')}\n"
            f"Автор: {artwork.get('artist_display', 'Нет данных')}\n"
            f"Дата: {artwork.get('date_display', 'Нет данных')}\n"
            f"Происхождение: {artwork.get('place_of_origin', 'Нет данных')}\n"
            f"Материал: {artwork.get('medium_display', 'Нет данных')}\n"
            f"Размеры: {artwork.get('dimensions', 'Нет данных')}\n"
            f"Отдел: {artwork.get('department_title', 'Нет данных')}\n"
            f"Тип: {artwork.get('artwork_type_title', 'Нет данных')}"
        )

    def get_info(self) -> Dict[str, Any]:
        """
        Получить информацию о функции.
        """

        return {
            "commands": self.commands,
            "authors": self.authors,
            "about": self.about,
            "description": self.description,
            "state": self.state,
        }