"""Module implementation of the atomic function of the telegram bot. Cat Facts API integration."""

from typing import List
import logging

import requests
import telebot
from telebot import types

from bot_func_abc import AtomicBotFunctionABC



class CatFactsFunction(AtomicBotFunctionABC):
    """Интеграция с API случайных фактов про кошек."""
    commands: List[str] = ["catfacts"]
    authors: List[str] = ["Bolbesx"]
    about: str = "Факты о кошках"
    description: str = (
        "/catfacts [число] — получить от 1 до 10 случайных фактов о кошках. "
        "Если число не указано, будет показан 1 факт. "
        "Факты получаются из внешнего API Cat Facts."
    )
    state: bool = True

    URL = "https://catfact.ninja/fact"
    TIMEOUT = 5

    bot: telebot.TeleBot

    def set_handlers(self, bot: telebot.TeleBot):
        """Устанавливает обработчики команд и callback'ов."""
        self.bot = bot

        @bot.message_handler(commands=self.commands)
        def handle_catfacts(message: types.Message):
            try:
                parts = message.text.strip().split()
                count = int(parts[1]) if len(parts) > 1 else 1
                count = max(1, min(count, 10))  # Ограничим от 1 до 10
            except (IndexError, ValueError):
                count = 1

            facts = self.get_cat_facts(count)
            if facts:
                text = "\n\n".join(facts)
                self.bot.send_message(message.chat.id, text)
            else:
                self.bot.send_message(message.chat.id, "Не удалось получить факты о кошках.")

    def get_cat_fact(self) -> str:
        """Отправляет указанное количество случайных фактов."""
        try:
            response = requests.get(self.URL, timeout=self.TIMEOUT)
            response.raise_for_status()
            return response.json().get("fact", "Факт не найден.")
        except requests.RequestException:
            logging.exception("Ошибка при получении факта о кошках")
            return "Ошибка при получении факта."

    def get_cat_facts(self, count: int) -> List[str]:
        """Обрабатывает callback от inline-кнопок."""
        return [self.get_cat_fact() for _ in range(count)]
