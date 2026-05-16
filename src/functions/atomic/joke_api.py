"""Функция для получения случайной шутки."""

from typing import List

import requests
import telebot
from telebot import types

from bot_func_abc import AtomicBotFunctionABC


class JokeBotFunction(AtomicBotFunctionABC):
    """Класс функции получения случайной шутки."""

    # pylint: disable=too-few-public-methods

    commands: List[str] = ["joke"]
    authors: List[str] = ["GITHUB_ЛОГИН"]

    about: str = "Случайная шутка"

    description: str = (
        "Функция получает случайную шутку через открытый API "
        "и отправляет её пользователю в Telegram. "
        "Использование: /joke. "
        "Поддерживается работа с внешним REST API."
    )

    state: bool = True

    def set_handlers(self, bot: telebot.TeleBot):
        """Устанавливает обработчик команды joke."""

        @bot.message_handler(commands=self.commands)
        def joke_handler(message: types.Message):
            try:
                joke = self.__get_joke()

                bot.reply_to(
                    message,
                    f"😂 Случайная шутка:\n\n{joke}"
                )

            except requests.RequestException:
                bot.reply_to(message, "Ошибка при запросе к API.")

            except KeyError:
                bot.reply_to(message, "Ошибка обработки данных.")

    @staticmethod
    def __get_joke() -> str:
        url = "https://official-joke-api.appspot.com/random_joke"

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        return (
            f"{data['setup']}\n"
            f"{data['punchline']}"
        )
