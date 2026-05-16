"""Module implementation of the atomic function for scientific article search via CORE API."""

import os
import logging
from typing import List, Optional
import requests
import telebot
from telebot import types
from bot_func_abc import AtomicBotFunctionABC


class ArticleSearchBotFunction(AtomicBotFunctionABC):
    """Search research papers by topic or DOI using CORE API."""

    commands: List[str] = ["article_search", "core_search"]
    authors: List[str] = ["miksm"]
    about: str = "Поиск научных статей"
    description: str = (
        "Поиск научных публикаций через CORE API по теме или DOI. "
        "Команда /article_search: введите тему (например Covid) или DOI "
        "(10.1109/icassp.2014.6854684), затем число результатов от 1 до 100. "
        "Для каждой статьи выводятся название, ссылка на полный текст и DOI. "
        "Требуется переменная окружения CORE_API_TOKEN."
    )
    state: bool = True

    CORE_DOI_URL = "https://api.core.ac.uk/v3/works/doi/{doi}"
    CORE_SEARCH_URL = "https://api.core.ac.uk/v3/search/works"

    bot: telebot.TeleBot

    def set_handlers(self, bot: telebot.TeleBot) -> None:
        """Set message handlers for article search."""
        self.bot = bot

        @bot.message_handler(commands=self.commands)
        def article_search_start(message: types.Message) -> None:
            """Start interactive article search."""
            token = self.__get_core_token()
            if not token:
                bot.send_message(
                    message.chat.id,
                    "CORE API недоступен: задайте переменную окружения CORE_API_TOKEN.",
                )
                return
            bot.send_message(
                message.chat.id,
                'Введите тему для поиска или DOI '
                '(например, "Covid" или 10.1109/icassp.2014.6854684):',
                reply_markup=types.ForceReply(selective=False),
            )
            bot.register_next_step_handler(message, self.__process_search_query)

    def __get_core_token(self) -> Optional[str]:
        return os.environ.get("CORE_API_TOKEN")

    def __get_headers(self) -> Optional[dict]:
        token = self.__get_core_token()
        if not token:
            return None
        return {"Authorization": f"Bearer {token}"}

    def __process_search_query(self, message: types.Message) -> None:
        user_query = self.__normalize_query(message.text)
        if not user_query:
            self.bot.send_message(message.chat.id, "Запрос не может быть пустым.")
            return
        self.bot.send_message(
            message.chat.id,
            "Сколько результатов вы хотите получить? (1-100):",
            reply_markup=types.ForceReply(selective=False),
        )
        self.bot.register_next_step_handler(
            message,
            lambda msg: self.__get_search_results(user_query, msg),
        )

    def __get_search_results(self, query: str, message: types.Message) -> None:
        try:
            num_results = int(message.text.strip())
            if num_results <= 0 or num_results > 100:
                self.bot.send_message(
                    message.chat.id,
                    "Пожалуйста, введите число от 1 до 100.",
                )
                return

            headers = self.__get_headers()
            if not headers:
                self.bot.send_message(
                    message.chat.id,
                    "CORE API недоступен: задайте CORE_API_TOKEN.",
                )
                return

            if self.__is_doi(query):
                self.__search_by_doi(query, message.chat.id, headers)
                return

            self.__search_by_topic(query, message.chat.id, headers, num_results)

        except ValueError:
            self.bot.send_message(message.chat.id, "Число не корректно.")
        except requests.RequestException as exc:
            logging.exception("CORE API request failed: %s", exc)
            self.bot.send_message(message.chat.id, f"Ошибка запроса к API: {exc}")

    def __search_by_doi(self, doi: str, chat_id: int, headers: dict) -> None:
        url = self.CORE_DOI_URL.format(doi=doi)
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            article = response.json()
            self.bot.send_message(chat_id, self.__format_article(article, prefix="Найдено по DOI"))
            return
        self.bot.send_message(
            chat_id,
            f"DOI не найден. Ошибка: {response.status_code} ({response.text})",
        )

    def __search_by_topic(
        self,
        query: str,
        chat_id: int,
        headers: dict,
        num_results: int,
    ) -> None:
        params = {"q": query, "pageSize": num_results, "page": 1}
        response = requests.get(
            self.CORE_SEARCH_URL,
            headers=headers,
            params=params,
            timeout=15,
        )
        if response.status_code != 200:
            self.bot.send_message(
                chat_id,
                f"Ошибка API: {response.status_code}. Текст: {response.text}",
            )
            return

        results = response.json()
        articles = results.get("results") or []
        if not articles:
            self.bot.send_message(chat_id, "По вашему запросу ничего не найдено.")
            return

        for index, article in enumerate(articles[:num_results], start=1):
            text = self.__format_article(article, prefix=f"{index}.")
            self.bot.send_message(chat_id, f"{text}\n{'-' * 50}")

    @staticmethod
    def __normalize_query(query: str) -> str:
        normalized = (query or "").strip()
        if normalized.upper().startswith("DOI:"):
            normalized = normalized[4:].strip()
        return normalized

    @staticmethod
    def __is_doi(query: str) -> bool:
        return query.startswith("10.") and "/" in query

    @staticmethod
    def __format_article(article: dict, prefix: str = "") -> str:
        title = article.get("title", "Нет названия")
        doi = article.get("doi", "Нет DOI")
        link = ArticleSearchBotFunction.__extract_link(article)
        if prefix == "Найдено по DOI":
            return f"Найдено по DOI:\n\n{title}\nСсылка: {link}\nDOI: {doi}"
        if prefix:
            return f"{prefix} {title}\nСсылка: {link}\nDOI: {doi}"
        return f"{title}\nСсылка: {link}\nDOI: {doi}"

    @staticmethod
    def __extract_link(article: dict) -> str:
        for key in ("fullTextUrl", "url", "downloadUrl"):
            if article.get(key):
                return article[key]

        links = article.get("links", [])
        if isinstance(links, list):
            for link_obj in links:
                if not isinstance(link_obj, dict):
                    continue
                link_type = link_obj.get("type", "").lower()
                link_url = link_obj.get("url")
                if link_url and link_type in ("fulltext", "pdf", "document"):
                    return link_url
        return "Ссылка недоступна"
