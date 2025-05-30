
"""
Модуль для реализации функции бота для генерации аватара через avatargen.io
"""

from typing import List
import logging
import telebot
import requests
from telebot import types
from telebot.callback_data import CallbackData
from bot_func_abc import AtomicBotFunctionABC


class AvatarGenBotFunction(AtomicBotFunctionABC):
    """
    Реализация функции бота для генерации аватара через avatargen.io
    """

    commands: List[str] = ["avatar"]
    authors: List[str] = ["brokenk1d"]
    about: str = "Генерация аватара через avatargen.io"
    description: str = """Позволяет пользователю выбрать стиль и сгенерировать аватар.
Просто введите /avatar и следуйте инструкциям."""
    state: bool = True

    AVATAR_API_URL = "https://api.avatargen.io/avatar"

    def __init__(self):
        super().__init__()
        self.bot = None
        self.styles = ["adventurer", "bottts", "fun-emoji", "pixel-art", "croodles"]
        self.avatar_style_keyboard_factory = CallbackData('style_choice', prefix='style')

    def register(self, bot: telebot.TeleBot):
        self.bot = bot

        @bot.message_handler(commands=self.commands)
        def handle_avatar_command(message: types.Message):
            markup = types.InlineKeyboardMarkup()
            for style in self.styles:
                markup.add(types.InlineKeyboardButton(
                    text=style,
                    callback_data=self.avatar_style_keyboard_factory.new(style_choice=style)
                ))
            bot.send_message(message.chat.id, "Выберите стиль аватара:", reply_markup=markup)

        @bot.callback_query_handler(func=lambda call: call.data.startswith(self.avatar_style_keyboard_factory.prefix))
        def handle_style_choice(call: types.CallbackQuery):
            style = self.avatar_style_keyboard_factory.parse(callback_data=call.data)['style_choice']
            seed = str(call.from_user.id)
            avatar_url = f"{self.AVATAR_API_URL}?style={style}&seed={seed}"
            bot.send_photo(call.message.chat.id, avatar_url, caption=f"Ваш аватар в стиле '{style}'")
