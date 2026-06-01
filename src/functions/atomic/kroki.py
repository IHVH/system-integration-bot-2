"""Функция для генерации диаграмм через Kroki API."""

import base64
import zlib
from typing import List

import telebot
from telebot import types

from bot_func_abc import AtomicBotFunctionABC


class DiagramBotFunction(AtomicBotFunctionABC):
    """Класс функции генерации диаграмм."""

    # pylint: disable=too-few-public-methods

    commands: List[str] = ["diagram"]
    authors: List[str] = ["moiseeva-anastasia"]

    about: str = "Диаграмма по тексту"

    description: str = (
        "Функция генерирует диаграмму по текстовому описанию через Kroki API. "
        "Пользователь передаёт краткую инструкцию в формате Mermaid, после чего "
        "бот создаёт ссылку на PNG-изображение диаграммы и отправляет её в чат."
    )

    state: bool = True

    def set_handlers(self, bot: telebot.TeleBot):
        """Устанавливает обработчик команды diagram."""

        @bot.message_handler(commands=self.commands)
        def diagram_handler(message: types.Message):
            diagram_text = message.text.replace("/diagram", "").strip()

            if not diagram_text:
                bot.reply_to(
                    message,
                    "Введите описание диаграммы. Пример:\n"
                    "/diagram graph TD; A[Начало] --> B[Конец]"
                )
                return

            image_url = self.__get_diagram_url(diagram_text)

            bot.send_photo(
                message.chat.id,
                image_url,
                caption="Готовая диаграмма"
            )

    @staticmethod
    def __get_diagram_url(diagram_text: str) -> str:
        encoded = base64.urlsafe_b64encode(
            zlib.compress(diagram_text.encode("utf-8"), 9)
        ).decode("ascii")

        return f"https://kroki.io/mermaid/png/{encoded}"
