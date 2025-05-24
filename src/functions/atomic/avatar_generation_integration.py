"""
Модуль генерации аватара с avatar.oxro.io.
"""

import os
import tempfile
from typing import List

import requests
import telebot
from telebot import types

from bot_func_abc import AtomicBotFunctionABC


class AvatarGenBotFunction(AtomicBotFunctionABC):
    """
    Класс-обёртка для генерации аватара через avatar.oxro.io.
    Позволяет задать имя, цвет фона и количество букв (только SVG).
    """

    commands: List[str] = ["avarka"]
    authors: List[str] = ["SlavaMuratov"]
    about: str = "Генерация аватара по имени"
    description: str = (
        "Генератор аватара через avatar.oxro.io\n"
        "Позволяет задать имя, цвет фона и количество букв (только svg).\n\n"
        "*Формат ввода:*\n"
        "`username HEX_color length`\n\n"
        "*Пример:*\n"
        "`ivanov FF5733 2`\n"
        "`masha 000000 1`"
    )
    bot: telebot.TeleBot

    def set_handlers(self, bot: telebot.TeleBot):
        """
        Устанавливает обработчики команд бота.
        """
        self.bot = bot

        @bot.message_handler(commands=self.commands)
        def avatar_message_handler(message: types.Message):
            self.bot.send_message(
                message.chat.id,
                "Введите параметры в формате:\n"
                "`username HEX_color length`\n\n"
                "Пример:\n`ivanov FF5733 2`",
                parse_mode="Markdown"
            )
            self.bot.register_next_step_handler(message, self.__process_avatar_request)

    def __process_avatar_request(self, message: types.Message):
        """
        Обрабатывает запрос на генерацию аватара.
        """
        try:
            args = message.text.strip().split()
            if len(args) != 3:
                self.bot.send_message(message.chat.id, "Неверный формат. Попробуйте снова.")
                return

            name, color, length_str = args
            length = int(length_str)
            trimmed_name = name[:length]

            url = f"https://avatar.oxro.io/avatar.svg?name={trimmed_name}&background={color}"

            response = requests.get(url, timeout=5)
            if response.status_code != 200:
                self.bot.send_message(message.chat.id, "Ошибка при получении"
                                                       " изображения. Попробуйте позже.")
                return

            with tempfile.NamedTemporaryFile(delete=False, suffix=".svg") as tmp_file:
                tmp_file.write(response.content)
                tmp_file_path = tmp_file.name

            with open(tmp_file_path, "rb") as file:
                self.bot.send_document(message.chat.id, file)

            os.remove(tmp_file_path)

        except requests.RequestException as error:
            self.bot.send_message(message.chat.id, f"Произошла ошибка:"
                                                   f" {error}", parse_mode="Markdown")
