"""Module implementation of the atomic function of the telegram bot.
English word generator integration."""

from typing import List
import logging

import json
import requests
import telebot
from telebot import types

from bot_func_abc import AtomicBotFunctionABC


class EnglishWordsFunction(AtomicBotFunctionABC):
    """Интеграция с API случайных английских слов."""
    commands: List[str] = ["engrndword"]
    authors: List[str] = ["anastava"]
    about: str = "Случайные английские слова"
    description: str = (
        "/engrndword [число] — получить от 1 до 5 случайных английских слов "
        "с определением и произношением. Если число не указано — будет показано одно слово. "
        "Источник: Random Words API."
    )
    state: bool = True

    URL = "https://random-words-api.vercel.app/word"
    TIMEOUT = 5

    bot: telebot.TeleBot

    def set_handlers(self, bot: telebot.TeleBot):
        """Устанавливает обработчики команд."""
        self.bot = bot

        @bot.message_handler(commands=self.commands)
        def handle_engwords(message: types.Message):
            try:
                parts = message.text.strip().split()
                count = int(parts[1]) if len(parts) > 1 else 1
                count = max(1, min(count, 5))
            except (IndexError, ValueError):
                count = 1

            words = self.get_random_words(count)
            if words:
                self.bot.send_message(message.chat.id, "\n\n".join(words))
            else:
                self.bot.send_message(message.chat.id, "Не удалось получить слова.")

    def get_random_word(self) -> str:
        """Получает одно случайное слово с определением и произношением."""
        try:
            response = requests.get(self.URL, timeout=self.TIMEOUT)
            response.raise_for_status()
            data = response.json()
            word = data.get("word", "—")
            definition = data.get("definition", "Нет определения.")
            pronunciation = data.get("pronunciation", "")
            return (f"word: {word}\n\npronunciation: {pronunciation}\n\ndefinition: "
                    f"{definition}\n_____")
        except requests.RequestException:
            logging.exception("Ошибка запроса к API random-words")
            return "Ошибка при получении слова."
        except json.JSONDecodeError:
            logging.exception("Ошибка декодирования JSON")
            return "Ошибка при обработке данных от API."

    def get_random_words(self, count: int) -> List[str]:
        """Возвращает список случайных слов."""
        return [self.get_random_word() for _ in range(count)]
