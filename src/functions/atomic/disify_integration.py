"""Module implementation of the atomic function of the telegram bot: DisifyIntegrationFunction"""

from typing import List
import requests
import telebot
from telebot import types
from bot_func_abc import AtomicBotFunctionABC

class DisifyIntegrationFunction(AtomicBotFunctionABC):
    """Atomic function for checking email information via the Disify API"""
    commands: List[str] = ["disify", "check_email"]
    authors: List[str] = ["Mityashka"]
    about: str = "Проверка e-mail через Disify"
    description: str = (
        "Проверка email-адресов через API Disify: disposable, формат, alias, DNS.\n"
        "Пример команды: /disify someone@mail.com"
    )
    state: bool = True

    API_URL = "https://www.disify.com/api/email/"
    TIMEOUT = 5

    bot: telebot.TeleBot

    def set_handlers(self, bot: telebot.TeleBot):
        """Set message handlers for Disify email verification command"""
        self.bot = bot

        @bot.message_handler(commands=self.commands)
        def disify_handler(message: types.Message):
            args = message.text.strip().split()
            if len(args) < 2:
                bot.send_message(message.chat.id, "Укажите email: `/disify test@example.com`")
                return

            email = args[1]

            try:
                response = requests.get(f"{self.API_URL}{email}", timeout=self.TIMEOUT)
                response.raise_for_status()
            except requests.RequestException as err:
                status = getattr(err.response, "status_code", "N/A")
                bot.send_message(message.chat.id, f"Ошибка запроса (код {status}).")
                return

            data = response.json()

            reply = (
                f"domain: {data.get('domain')}\n"
                f"Format Valid: {data.get('format')}\n"
                f"Alias: {data.get('alias')}\n"
                f"Disposable: {data.get('disposable')}\n"
                f"DNS Valid: {data.get('dns')}\n"
            )
            bot.send_message(message.chat.id, reply)
