"""Функция для проверки URL через URLhaus API."""

import os
from typing import List

import requests
import telebot
from telebot import types

from bot_func_abc import AtomicBotFunctionABC


class UrlhausBotFunction(AtomicBotFunctionABC):
    """Класс функции проверки URL."""

    # pylint: disable=too-few-public-methods

    commands: List[str] = ["urlcheck"]
    authors: List[str] = ["anastasya-zakharova"]

    about: str = "Проверка URL"

    description: str = (
        "Функция проверяет ссылку через сервис URLhaus API, отправляет POST-запрос "
        "с URL-адресом и возвращает информацию о наличии угроз, статусе ссылки, "
        "дате добавления и возможных тегах вредоносной активности."
    )

    state: bool = True

    def set_handlers(self, bot: telebot.TeleBot):
        """Устанавливает обработчик команды urlcheck."""

        @bot.message_handler(commands=self.commands)
        def urlhaus_handler(message: types.Message):
            url = message.text.replace("/urlcheck", "").strip()

            if not url:
                bot.reply_to(
                    message,
                    "Введите ссылку. Пример: /urlcheck https://example.com"
                )
                return

            try:
                data = self.__check_url(url)
                answer = self.__format_answer(url, data)
                bot.reply_to(message, answer)

            except requests.RequestException:
                bot.reply_to(message, "Ошибка при запросе к API.")

            except KeyError:
                bot.reply_to(message, "Ошибка обработки данных.")

    @staticmethod
    def __check_url(url: str):
        api_key = os.getenv("c0fa9624343110a693c5d3cae67a50676d14d0ce32e43f6f")

        if not api_key:
            raise requests.RequestException

        api_url = "https://urlhaus-api.abuse.ch/v1/url/"

        headers = {
            "Auth-Key": api_key
        }

        data = {
            "url": url
        }

        response = requests.post(
            api_url,
            headers=headers,
            data=data,
            timeout=10
        )

        response.raise_for_status()

        return response.json()

    @staticmethod
    def __format_answer(url: str, data: dict) -> str:
        query_status = data.get("query_status", "Нет данных")

        if query_status == "no_results":
            return (
                f"🔎 Проверка URLhaus\n\n"
                f"URL: {url}\n"
                f"Результат: угрозы не найдены."
            )

        url_status = data.get("url_status", "Нет данных")
        threat = data.get("threat", "Нет данных")
        date_added = data.get("date_added", "Нет данных")
        tags = data.get("tags", [])

        if tags:
            tags_text = ", ".join(tags)
        else:
            tags_text = "Нет тегов"

        return (
            f"⚠️ Проверка URLhaus\n\n"
            f"URL: {url}\n"
            f"Статус запроса: {query_status}\n"
            f"Статус URL: {url_status}\n"
            f"Угроза: {threat}\n"
            f"Дата добавления: {date_added}\n"
            f"Теги: {tags_text}"
        )
