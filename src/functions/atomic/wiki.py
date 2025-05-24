"""Модуль реализации функции бота для интеграции с MediaWiki API"""

import logging
from typing import List
import requests
import telebot
from telebot import types
from bot_func_abc import AtomicBotFunctionABC


class WikiBotFunction(AtomicBotFunctionABC):
    """Функция бота для получения информации из Википедии на основе запросов пользователей."""

    commands: List[str] = ["wiki"]
    authors: List[str] = ["KolpakovDanila(essanedev)"]
    about: str = "Поиск информации в Wikipedia"
    description: str = (
        "Функция для получения информации из Wikipedia по запросу. "
        "Пример использования: /wiki <запрос> — поиск статьи и вывод краткого содержания. "
        "Например: /wiki Квантовая физика. Возвращает краткое описание статьи, "
        "изображение и ссылку. Источник данных: ru.wikipedia.org."
    )
    state: bool = True

    WIKI_API_URL = "https://ru.wikipedia.org/w/api.php"
    bot: telebot.TeleBot

    def set_handlers(self, bot: telebot.TeleBot):
        """Set message handlers for Wikipedia search command."""
        self.bot = bot

        @bot.message_handler(commands=self.commands)
        def wiki_handler(message: types.Message):
            try:
                query = ' '.join(message.text.split()[1:])
                if not query:
                    self.bot.reply_to(message, "Введите запрос: /wiki <запрос>")
                    return

                page_id = self.__search_wiki_page(query)
                if not page_id:
                    self.bot.reply_to(message, "Ничего не найдено.")
                    return

                summary, image_url, article_url = self.__get_page_data(page_id)

                response = f"📖 {summary}\n\n🌐 {article_url}"
                if image_url:
                    self.bot.send_photo(message.chat.id, image_url, caption=response)
                else:
                    self.bot.send_message(message.chat.id, response)

            except (requests.RequestException, KeyError) as e:
                logging.exception("Ошибка обработки: %s", e)
                self.bot.reply_to(message, "Ошибка обработки запроса")

    def __search_wiki_page(self, query: str) -> str:
        """Search Wikipedia page by query and return page ID."""
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json"
        }
        try:
            response = requests.get(self.WIKI_API_URL, params=params, timeout=10)
            return str(response.json()["query"]["search"][0]["pageid"]) if response.ok else None
        except (requests.RequestException, KeyError):
            return None

    def __get_page_data(self, page_id: str) -> tuple:
        """Fetch page summary, image and URL from Wikipedia API."""
        params = {
            "action": "query",
            "pageids": page_id,
            "prop": "extracts|pageimages|info",
            "exintro": True,
            "explaintext": True,
            "piprop": "original",
            "format": "json"
        }
        try:
            data = requests.get(self.WIKI_API_URL, params=params, timeout=10).json()
            page_data = data["query"]["pages"][page_id]
            summary = f"{page_data.get('extract', 'Описание отсутствует')[:500]}..."
            return (
                summary,
                page_data.get("original", {}).get("source"),
                page_data.get("fullurl", "https://ru.wikipedia.org")
            )
        except (requests.RequestException, KeyError):
            return "Информация недоступна", None, "https://ru.wikipedia.org"
