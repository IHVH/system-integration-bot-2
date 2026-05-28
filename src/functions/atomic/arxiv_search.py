"""Модуль для поиска научных статей на arXiv."""

import logging
import xml.etree.ElementTree as ET
from typing import List, Optional, Tuple
import requests
import telebot
from telebot import types
from telebot.callback_data import CallbackData
from bot_func_abc import AtomicBotFunctionABC  # pylint: disable=import-error


logger = logging.getLogger(__name__)

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM_NS = "http://www.w3.org/2005/Atom"
DEFAULT_MAX_RESULTS = 10
HARD_MAX_RESULTS = 25
ABSTRACT_LIMIT = 280


class ArxivSearchBotFunction(AtomicBotFunctionABC):
    """Поиск научных статей на arXiv через Telegram бота."""

    commands: List[str] = ["arxiv"]
    authors: List[str] = ["kiri4is"]
    about: str = "Поиск статей на arXiv"
    description: str = (
        "Поиск научных статей на платформе arXiv.\n\n"
        "Использование:\n"
        "/arxiv <слово> — найти первые 10 статей по ключевому слову\n"
        "/arxiv <кол-во> <слово1> <слово2> ... — поиск по нескольким "
        "ключевым словам, вывести указанное количество результатов\n\n"
        "Примеры:\n"
        "/arxiv quantum\n"
        "/arxiv 5 machine learning transformer"
    )
    state: bool = True

    bot: telebot.TeleBot
    arxiv_keyboard_factory: CallbackData

    def set_handlers(self, bot: telebot.TeleBot):
        """Регистрирует обработчики команд бота."""
        self.bot = bot
        self.arxiv_keyboard_factory = CallbackData(
            "ax_button", prefix=self.commands[0]
        )

        @bot.message_handler(commands=self.commands)
        def handle_arxiv_command(message: types.Message):
            parts = message.text.split()[1:]

            if not parts:
                usage = (
                    "Укажите ключевое слово для поиска.\n"
                    "Пример: /arxiv quantum\n"
                    "Или: /arxiv 5 deep learning"
                )
                bot.send_message(message.chat.id, usage)
                return

            count, keywords = self._parse_args(parts)

            if not keywords:
                bot.send_message(
                    message.chat.id,
                    "После числа нужно указать ключевые слова.\n"
                    "Пример: /arxiv 5 neural network"
                )
                return

            query = " AND ".join(f"all:{kw}" for kw in keywords)
            bot.send_message(
                message.chat.id,
                f"Ищу статьи по запросу: {', '.join(keywords)}..."
            )

            articles, error = self.get_articles(query, count)

            if error:
                bot.send_message(message.chat.id, f"Ошибка запроса: {error}")
                return

            if not articles:
                bot.send_message(
                    message.chat.id,
                    "По вашему запросу ничего не найдено."
                )
                return

            for article in articles:
                bot.send_message(
                    message.chat.id,
                    article,
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                )

    def get_articles(
        self, query: str, max_results: int
    ) -> Tuple[List[str], Optional[str]]:
        """Запрашивает статьи из arXiv API.

        Возвращает кортеж (список статей, сообщение об ошибке или None).
        """
        params = {
            "search_query": query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        try:
            response = requests.get(ARXIV_API_URL, params=params, timeout=15)
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            logger.error("arXiv API недоступен")
            return [], "Не удалось подключиться к arXiv. Проверьте интернет."
        except requests.exceptions.Timeout:
            logger.error("arXiv API timeout")
            return [], "Сервер arXiv не ответил вовремя. Попробуйте позже."
        except requests.exceptions.HTTPError as exc:
            logger.error("arXiv HTTP error: %s", exc)
            return [], f"Сервер вернул ошибку: {exc.response.status_code}"

        articles = self._parse_feed(response.text)
        return articles, None

    @staticmethod
    def _parse_args(parts: List[str]):
        """Разбирает аргументы команды на количество и список ключевых слов."""
        if parts[0].isdigit():
            count = min(int(parts[0]), HARD_MAX_RESULTS)
            keywords = parts[1:]
        else:
            count = DEFAULT_MAX_RESULTS
            keywords = parts
        return count, keywords

    def _parse_feed(self, xml_text: str) -> List[str]:
        """Разбирает Atom-ответ arXiv и возвращает список строк для отправки."""
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            logger.error("Ошибка парсинга XML: %s", exc)
            return []

        articles = []
        for index, entry in enumerate(root.findall(f"{{{ATOM_NS}}}entry"), start=1):
            formatted = self._format_entry(entry, index)
            if formatted:
                articles.append(formatted)

        return articles

    def _format_entry(self, entry: ET.Element, index: int) -> Optional[str]:
        """Форматирует один элемент Atom в читаемое сообщение."""
        title_el = entry.find(f"{{{ATOM_NS}}}title")
        id_el = entry.find(f"{{{ATOM_NS}}}id")

        if title_el is None or id_el is None:
            return None

        title = (title_el.text or "").strip().replace("\n", " ")
        link = (id_el.text or "").strip()
        summary = self._extract_summary(entry)
        published = self._extract_published(entry)
        authors_str = self._extract_authors(entry)
        safe_title = title.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")

        return (
            f"*{index}. {safe_title}*\n"
            f"👤 {authors_str}\n"
            f"📅 {published}\n"
            f"_{summary}_\n"
            f"🔗 [Открыть на arXiv]({link})"
        )

    @staticmethod
    def _extract_summary(entry: ET.Element) -> str:
        """Извлекает и обрезает аннотацию статьи."""
        summary_el = entry.find(f"{{{ATOM_NS}}}summary")
        if summary_el is None:
            return ""
        summary = (summary_el.text or "").strip().replace("\n", " ")
        if len(summary) > ABSTRACT_LIMIT:
            summary = summary[:ABSTRACT_LIMIT] + "..."
        return summary

    @staticmethod
    def _extract_published(entry: ET.Element) -> str:
        """Извлекает дату публикации в формате YYYY-MM-DD."""
        published_el = entry.find(f"{{{ATOM_NS}}}published")
        if published_el is None or not published_el.text:
            return "?"
        return published_el.text[:10]

    @staticmethod
    def _extract_authors(entry: ET.Element) -> str:
        """Извлекает список авторов (не более трёх) из элемента статьи."""
        author_names = []
        for author_el in entry.findall(f"{{{ATOM_NS}}}author"):
            name_el = author_el.find(f"{{{ATOM_NS}}}name")
            if name_el is not None and name_el.text:
                author_names.append(name_el.text)

        if not author_names:
            return "Неизвестно"
        if len(author_names) > 3:
            return ", ".join(author_names[:3]) + " и др."
        return ", ".join(author_names)
