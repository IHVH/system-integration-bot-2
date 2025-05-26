"""Модуль реализации функции бота для интеграции с MediaWiki API"""

import logging
from typing import List, Optional, Tuple
import requests
import telebot
from telebot import types
from bot_func_abc import AtomicBotFunctionABC


class WikiBotFunction(AtomicBotFunctionABC):
    """Функция бота для получения информации из Википедии на основе запросов пользователей."""

    commands: List[str] = ["wiki"]
    authors: List[str] = ["essanedev"]
    about: str = "Поиск информации в Wikipedia"
    description: str = (
        "Функция для получения информации из Wikipedia по запросу. "
        "Пример использования: /wiki <запрос> — поиск статьи и вывод краткого содержания. "
        "Например: /wiki Квантовая физика. Возвращает краткое описание статьи, "
        "изображение и ссылку. Источник данных: ru.wikipedia.org."
    )
    state: bool = True

    WIKI_API_URL = "https://ru.wikipedia.org/w/api.php"
    PLACEHOLDER_IMAGE_URL = (
        "https://upload.wikimedia.org/wikipedia/commons/thumb/8/80/Wikipedia-logo-v2.svg/200px-Wikipedia-logo-v2.svg.png" # pylint: disable=line-too-long
    )
    bot: telebot.TeleBot

    def set_handlers(self, bot: telebot.TeleBot):
        """Set message handlers for Wikipedia search command."""
        self.bot = bot

        @bot.message_handler(commands=self.commands)
        def wiki_handler(message: types.Message):
            try:
                query = ' '.join(message.text.split()[1:]).strip()
                if not query:
                    self.bot.reply_to(message, "Введите запрос: /wiki <запрос>")
                    return

                page_id = self.__search_wiki_page(query)
                if not page_id:
                    self.bot.reply_to(message, "Ничего не найдено.")
                    return

                summary, image_url, article_url = self.__get_page_data(page_id)

                response = f"📖 {summary}\n\n🌐 {article_url}"
                self.bot.send_photo(message.chat.id, image_url, caption=response)

            except (requests.RequestException, KeyError) as e:
                logging.exception("Ошибка обработки: %s", e)
                self.bot.reply_to(message, "Ошибка обработки запроса")

    def __search_wiki_page(self, query: str) -> Optional[str]:
        """Search Wikipedia page by query and return page ID."""
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json"
        }
        try:
            response = requests.get(self.WIKI_API_URL, params=params, timeout=10)
            response.raise_for_status()
            search_results = response.json().get("query", {}).get("search", [])
            if search_results:
                return str(search_results[0]["pageid"])
            return None
        except (requests.RequestException, KeyError) as e:
            logging.exception("Ошибка поиска страницы: %s", e)
            return None

    def __get_page_data(self, page_id: str) -> Tuple[str, str, str]:
        """Fetch page summary, thumbnail image, and URL from Wikipedia API."""
        params = {
            "action": "query",
            "pageids": page_id,
            "prop": "extracts|pageimages|info",
            "exintro": True,
            "explaintext": True,
            "piprop": "thumbnail",
            "pithumbsize": 400,
            "inprop": "url",
            "format": "json"
        }
        try:
            response = requests.get(self.WIKI_API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            page_data = data.get("query", {}).get("pages", {}).get(page_id, {})

            summary = page_data.get("extract", "Описание отсутствует")
            # Обрезаем текст для Telegram (ограничение 1024 символа для подписи)
            max_summary_length = 950  # Резерв для формата и URL
            if len(summary) > max_summary_length:
                summary = summary[:max_summary_length].rstrip() + "…"

            # Получаем миниатюру
            image_url = (
                page_data.get("thumbnail", {})
                .get("source", self.PLACEHOLDER_IMAGE_URL)
            )

            article_url = page_data.get("fullurl", "https://ru.wikipedia.org")

            # Финишная проверка длины
            full_caption = f"📖 {summary}\n\n🌐 {article_url}"
            if len(full_caption) > 1024:
                overflow = len(full_caption) - 1024
                summary = summary[:max_summary_length - overflow].rstrip() + "…"
                full_caption = f"📖 {summary}\n\n🌐 {article_url}"

            return summary, image_url, article_url
        except (requests.RequestException, KeyError) as e:
            logging.exception("Ошибка получения данных страницы: %s", e)
            return "Информация недоступна", self.PLACEHOLDER_IMAGE_URL, "https://ru.wikipedia.org"
