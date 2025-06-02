"""Модуль для интеграции с API Grawatar и реализации функциональности вывода аватарок по почте."""
import hashlib
import logging
from urllib.parse import urlencode
from typing import List

import requests
import telebot
from telebot import types

from bot_func_abc import AtomicBotFunctionABC


class GravatarBotFunction(AtomicBotFunctionABC):
    """Модуль для генерации Gravatar URL по email адресу."""

    commands: List[str] = ["gravatar", "getavatar"]
    authors: List[str] = ["HOllooo"]
    about: str = "Генерация Gravatar по email"
    description: str = (
        "Получайте URL аватарки Gravatar по email адресу.\n"
        "Используйте: /gravatar example@domain.com [стиль]\n"
        "Доступные стили: monsterid, identicon, wavatar, retro, robohash"
    )
    state: bool = True

    bot: telebot.TeleBot

    def set_handlers(self, bot: telebot.TeleBot):
        """Регистрацию обработчиков команд для бота."""
        self.bot = bot

        @bot.message_handler(commands=self.commands)
        def gravatar_handler(message: types.Message):
            args = message.text.split()
            if len(args) < 2:
                self.bot.send_message(
                    message.chat.id,
                    "\u274C Укажите email после команды. "
                    "Пример: /gravatar user@example.com [стиль]"
                )
                return

            email = args[1]
            avatar_style = args[2] if len(args) > 2 else None
            self.__generate_gravatar(message, email, avatar_style)

    def __generate_gravatar(self, message: types.Message, email: str,
                           avatar_style: str = None):
        """Генерация Gravatar URL с возможностью выбора стиля."""
        try:
            if '@' not in email:
                raise ValueError("Некорректный email адрес")

            # Генерация хеша
            email_hash = hashlib.md5(email.lower().encode('utf-8')).hexdigest()

            # Параметры запроса
            params = {'s': 200}  # Размер по умолчанию 200px

            # Добавляем стиль если он указан и валиден
            valid_styles = {
                'monsterid', 'identicon', 'wavatar', 'retro', 'robohash'
            }
            if avatar_style:
                if avatar_style.lower() in valid_styles:
                    params['d'] = avatar_style.lower()
                else:
                    raise ValueError(
                        f"Недопустимый стиль аватара. "
                        f"Допустимые стили: {', '.join(valid_styles)}"
                    )

            query = urlencode(params)
            gravatar_url = f"https://www.gravatar.com/avatar/{email_hash}?{query}"

            # Форматированный ответ
            response = (
                f"\U0001F464 Gravatar для {email}:\n"
                f"\U0001F4CE Размер: {params['s']}px\n"
            )

            if avatar_style:
                response += f"\U0001F3A8 Стиль: {avatar_style}\n"

            response += f"\n\U0001F517 Ссылка: {gravatar_url}"

            self.bot.send_message(message.chat.id, response)
            self.bot.send_photo(message.chat.id, gravatar_url)

        except ValueError as e:
            self.bot.send_message(message.chat.id, f"\u274C Ошибка: {str(e)}")
        except Exception as e:
            logging.exception("Gravatar request failed: %s", e)
            self.bot.send_message(
                message.chat.id,
                "\u274C Произошла ошибка при генерации Gravatar"
            )
