"""Модуль, дающее свое мнение"""

from typing import List
import telebot
import requests
from telebot import types
from bot_func_abc import AtomicBotFunctionABC

class AtomicExampleBotFunction(AtomicBotFunctionABC):
    """Модуль для получения двоичного ответа"""

    commands: List[str] = ["ask"]
    authors: List[str] = ["Geomoris"]
    about: str = "Спроси мнение бота!"
    description: str = """Бот помогает пользователю дать ответ, на крайне не очивидные вопросы,
    где все ресурсы человечества не способны почь, даёт мемный ответ да or нет."""
    state: bool = True

    bot: telebot.TeleBot

    def set_handlers(self, bot: telebot.TeleBot):
        """Обработка команд функций"""
        self.bot = bot
        def get_yes_no_answer():
            response = requests.get('https://yesno.wtf/api', timeout=10)
            if response.status_code == 200:
                return response.json()
            return {"answer": "Ошибка при получении ответа.", "image": None}

        @bot.message_handler(commands=self.commands)
        def yes_no_message_hendler(message: types.Message):
            answer_data = get_yes_no_answer()
            answer = answer_data['answer']
            image_url = answer_data['image']
            msg = (
                f"{message.from_user.first_name}, Мой ответ: {answer}"
            )
            bot.send_message(text=msg, chat_id=message.chat.id)
            bot.send_animation(chat_id=message.chat.id, animation=image_url)
