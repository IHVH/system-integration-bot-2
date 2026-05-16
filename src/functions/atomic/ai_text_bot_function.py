"""Модуль с функцией генерации текста через нейросеть Pollinations."""

from typing import List, Dict, Any
from urllib.parse import quote

import requests
import telebot
from telebot import types

from bot_func_abc import AtomicBotFunctionABC


class AiTextBotFunction(AtomicBotFunctionABC):
    """Класс для генерации текста с помощью нейросети Pollinations."""

    commands: List[str] = ["ai"]
    authors: List[str] = ["dashaveyder"]
    about: str = "Генерация текста с помощью нейросети"
    description: str = (
        "Функция отправляет запрос к нейросети и возвращает ответ. "
        "Пример: /ai придумай 5 идей для стартапа."
    )
    state: bool = True

    def get_info(self) -> Dict[str, Any]:
        """Возвращает информацию о функции.

        Returns:
            Словарь с информацией о командах, авторе, описании и состоянии.
        """
        return {
            "commands": self.commands,
            "authors": self.authors,
            "about": self.about,
            "description": self.description,
            "state": self.state,
        }

    def set_handlers(self, bot: telebot.TeleBot) -> None:
        """Установка обработчиков команд бота.

        Args:
            bot: Экземпляр телеграм-бота.
        """
        @bot.message_handler(commands=self.commands)
        def ai_text_handler(message: types.Message) -> None:
            """Обработчик команды /ai.

            Args:
                message: Объект сообщения от пользователя.
            """
            prompt = message.text.replace("/ai", "").strip()

            if not prompt:
                bot.reply_to(
                    message,
                    "Введите запрос. Пример: /ai расскажи про Python"
                )
                return

            try:
                answer = self.__get_ai_answer(prompt)
                bot.reply_to(message, answer[:4000])
            except requests.RequestException:
                bot.reply_to(message, "Ошибка при запросе к API.")

    @staticmethod
    def __get_ai_answer(prompt: str) -> str:
        """Отправка запроса к API нейросети Pollinations.

        Args:
            prompt: Текст запроса пользователя.

        Returns:
            Ответ нейросети в виде строки.

        Raises:
            requests.RequestException: При ошибках сетевого запроса.
        """
        url = f"https://text.pollinations.ai/{quote(prompt)}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.text
