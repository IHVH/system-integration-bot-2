"""
Модуль для реализации функции бота для получения интересных фактов о собаках.
"""

from typing import List
import logging
import telebot
import requests
from telebot import types
from telebot.callback_data import CallbackData
from bot_func_abc import AtomicBotFunctionABC



class DogFactBotFunction(AtomicBotFunctionABC):
    """
    Реализация функции бота для получения интересных фактов о собаках.
    """

    commands: List[str] = ["dogfact"]
    authors: List[str] = ["brokenk1d"]
    about: str = "Интересные факты о собаках."
    description: str = """Эта функция позволяет получать интересные факты о собаках.
    Просто вызовите команду /dogfact, и бот предоставит вам увлекательный факт.
    Узнайте больше о наших четвероногих друзьях!"""
    state: bool = True

    DOG_FACT_API_URL = "https://dog-api.kinduff.com/api/facts"

    def __init__(self):
        super().__init__()
        self.bot = None
        self.dog_fact_keyboard_factory = CallbackData('t_key_button', prefix=self.commands[0])

    def set_handlers(self, bot: telebot.TeleBot):
        """
        Устанавливает обработчики команд для бота.

        :param bot: Экземпляр TeleBot.
        """
        self.bot = bot

        @self.bot.message_handler(commands=self.commands)
        def dog_fact_message_handler(message: types.Message):
            chat_id_msg = f"\nCHAT ID = {message.chat.id}"
            num_facts = 1  # По умолчанию выводим один факт

            # Проверяем, указал ли пользователь число после команды
            command_parts = message.text.split()
            if len(command_parts) > 1:
                try:
                    num_facts = int(command_parts[1])  # Преобразуем второй элемент в целое число
                    if num_facts <= 0:
                        raise ValueError("Количество фактов должно быть положительным числом.")
                except ValueError:
                    self.bot.send_message(chat_id=message.chat.id, text="Неверный формат числа.")
                    return

            all_facts = []
            while len(all_facts) < num_facts:
                try:
                    response = requests.get(
                        DogFactBotFunction.DOG_FACT_API_URL,
                        params={'limit': min(num_facts - len(all_facts), 10)},
                        timeout=5
                    )

                    if response.status_code == 200:
                        facts_data = response.json()
                        new_facts = facts_data['facts']
                        all_facts.extend(new_facts)
                    else:
                        error_message = f"Статус-код: {response.status_code}.Текст: {response.text}"
                        logging.error(error_message)
                        break
                except requests.exceptions.RequestException as e:
                    logging.error("Произошла ошибка при запросе к API: %s", e)
                    break

            # Убедимся, что мы собрали хотя бы одно сообщение
            if not all_facts:
                self.bot.send_message(chat_id=message.chat.id, text="Попробуйте позже.")
                return

            # Формируем итоговое сообщение
            msg = (
                f"Ваш запрос обработан в DogFactBotFunction! {chat_id_msg}\n"
                f"ФАКТЫ:\n" + "\n".join(all_facts[:num_facts])
            )
            self.bot.send_message(chat_id=message.chat.id, text=msg)

    def check_bot_state(self) -> bool:
        """
        Проверяет состояние бота перед выполнением основной функции.

        :return: True, если состояние бота активно, иначе False.
        """
        return self.state
