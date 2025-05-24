"""Модуль для команды /motivate: отправляет случайную мотивационную цитату через API Ninjas."""

from typing import List
import os
import logging
import requests
import telebot
from telebot import types
from bot_func_abc import AtomicBotFunctionABC


class AtomicMotivateFunction(AtomicBotFunctionABC):
    """Atomic-функция для отправки мотивационной цитаты по команде /motivate."""
    commands: List[str] = ["motivate"]
    authors: List[str] = ["Jorik887"]
    about: str = "Мотивационные цитаты"
    description: str = "Отправляет случайную мотивационную цитату.\nПример: /motivate"
    state: bool = True

    bot: telebot.TeleBot

    API_URL = "https://api.api-ninjas.com/v1/quotes"

    def set_handlers(self, bot: telebot.TeleBot):
        """Регистрирует обработчик команды /motivate."""
        self.bot = bot

        @bot.message_handler(commands=self.commands)
        def motivate_message_handler(message: types.Message):
            """Обрабатывает команду /motivate и отправляет цитату."""
            try:
                quote = self.__get_random_quote()
                if quote:
                    text = (
                        f"\u2757 *{quote['quote']}*\n_— {quote['author']}_"
                    )
                    bot.send_message(
                        message.chat.id, text, parse_mode="Markdown"
                    )
                else:
                    bot.send_message(
                        message.chat.id,
                        "Не удалось получить цитату. Попробуйте позже."
                    )
            except (RuntimeError, requests.RequestException) as ex:
                logging.exception("Error in /motivate: %s", ex)
                bot.send_message(message.chat.id, f"Ошибка: {str(ex)}")

    def __get_api_key(self) -> str:
        """Возвращает API-ключ для сервиса мотивационных цитат."""
        api_key = os.environ.get("MOTIVATION_API_KEY")
        if not api_key:
            logging.warning(
                "MOTIVATION_API_KEY not found in environment variables")
            raise RuntimeError("API ключ для мотивационных цитат не найден.")
        return api_key

    def __get_random_quote(self):
        """Запрашивает случайную мотивационную цитату через API."""
        headers = {"X-Api-Key": self.__get_api_key()}
        try:
            response = requests.get(self.API_URL, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list) and data:
                return data[0]
            return None
        except requests.RequestException as e:
            logging.error("API request error: %s", e)
            raise
