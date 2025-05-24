"""Модуль для интеграции с API Grawatar и реализации функциональности вывода аватарок по почте."""
import hashlib
import os
import logging
from urllib.parse import urlencode
from typing import List

import requests
import telebot
from telebot import types

from bot_func_abc import AtomicBotFunctionABC


class GravatarBotFunction(AtomicBotFunctionABC):
    """Модуль для генерации Gravatar URL по email адресу"""

    commands: List[str] = ["gravatar", "getavatar"]
    authors: List[str] = ["HOllooo"]
    about: str = "Генерация Gravatar по email"
    description: str = """Получайте URL аватарки Gravatar по email адресу.
Используйте: /gravatar example@domain.com"""
    state: bool = True

    bot: telebot.TeleBot

    def set_handlers(self, bot: telebot.TeleBot):
        """Регистрацию обработчиков команд для бота"""
        self.bot = bot

        @bot.message_handler(commands=self.commands)
        def gravatar_handler(message: types.Message):
            args = message.text.split()
            if len(args) != 2:
                self.bot.send_message(
                    message.chat.id,
                    "\u274C Укажите email после команды. Пример: /gravatar user@example.com"
                )
                return

            email = args[1]
            self.__generate_gravatar(message, email)

    def __generate_gravatar(self, message: types.Message, email: str):
        """Генерация Gravatar URL"""
        try:
            if '@' not in email:
                raise ValueError("Некорректный email адрес")

            # Получение настроек из переменных окружения
            default_avatar = os.getenv("GRAVATAR_DEFAULT", "https://example.com/default.png")
            avatar_size = int(os.getenv("GRAVATAR_SIZE", "80"))

            # Генерация хеша
            email_hash = hashlib.sha256(email.lower().encode('utf-8')).hexdigest()
            query = urlencode({'d': default_avatar, 's': avatar_size})
            gravatar_url = f"https://www.gravatar.com/avatar/{email_hash}?{query}"

            # Форматированный ответ
            response = (
                f"\U0001F464 Gravatar для {email}:\n"
                f"\U0001F4CE Размер: {avatar_size}px\n"
                f"\U0001F4F0 Дефолтная аватарка: {default_avatar}\n\n"
                f"\U0001F517 Ссылка: {gravatar_url}"
            )

            self.bot.send_message(message.chat.id, response)
            self.bot.send_photo(message.chat.id, gravatar_url)

        except ValueError as e:
            self.bot.send_message(message.chat.id, f"\u274C Ошибка: {str(e)}")
        except requests.exceptions.RequestException as e:
            logging.exception("Gravatar API request failed: %s", e)
            self.bot.send_message(
                message.chat.id,
                "\u274C Произошла ошибка при генерации Gravatar"
            )
