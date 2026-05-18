"""Модуль с функцией для вывода случайных фактов с использованием API."""

from typing import List
import json
import requests
from requests.exceptions import RequestException
from telebot.types import Message
from bot_func_abc import AtomicBotFunctionABC


class FactSvNFunction(AtomicBotFunctionABC):
    """Класс для обработки команды /factsvn, выводящей случайные факты."""

    commands = ["factsvn"]
    authors = ["Kylon2308"]
    about = "Вывод случайного факта"
    description = "Команда /factsvn показывает указанное количество случайных " \
    "фактов с внешнего API команда так же может выводить несколько фактов"
    state = True

    def set_handlers(self, bot):
        """Устанавливает обработчики команд для бота."""

        @bot.message_handler(commands=self.commands)
        def handle_factsvn(message: Message):
            """Обработчик команды /factsvn."""
            try:
                arr = message.text.strip().split()
                count = 1  # По умолчанию один факт
                if len(arr) == 2 and arr[1].isdigit():
                    count = int(arr[1])
                    count = min(count, 10)  # ограничим до 10 фактов

                facts: List[str] = []
                for i in range(count):
                    response = requests.get(
                        "https://uselessfacts.jsph.pl/api/v2/facts/random?language=en", timeout=5
                    )
                    response.raise_for_status()
                    fact = response.json().get("text", "Не удалось получить факт.")
                    facts.append(f"{i + 1}. {fact}")

                message_text = "💡 Did you know?\n\n" + "\n\n".join(facts)
                bot.send_message(message.chat.id, message_text)

            except (RequestException, json.JSONDecodeError) as e:
                bot.send_message(message.chat.id, f"Произошла ошибка: {e}")
