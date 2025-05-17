"""
Модуль для получения курса валют через freecurrencyapi.com для Telegram-бота.
"""
import os
from typing import List

import requests
import telebot
from telebot import types
from bot_func_abc import AtomicBotFunctionABC


class CurrencyRateFunction(AtomicBotFunctionABC):
    """Показывает список валют и текущий курс выбранной валюты."""
    commands: List[str] = ["currency", "курс"]
    authors: List[str] = ["<jorik>"]
    about: str = "Курс валют"
    description: str = (
        "Позволяет получить текущий курс выбранной валюты относительно рубля, используя "
        "freecurrencyapi.com.\nПри вводе команды /currency (или /курс) выводится набор "
        "кнопок с кодами валют. По нажатию на кнопку бот отправит актуальный курс."
    )
    state: bool = True

    def __init__(self):
        """Initialize the class and call init() method."""
        super().__init__()
        self.bot = None
        self.init()

    def init(self):
        """Инициализирует начальные значения для атрибутов."""
        self.api_key = os.getenv("FREECURRENCY_API_KEY")
        if not self.api_key:
            self.state = False
            print("Warning: FREECURRENCY_API_KEY not set. Currency rate function will be disabled.")

    # фиксированный список валют (можно расширять)
    currency_list = ["USD", "EUR", "GBP", "JPY", "CNY", "CHF", "RUB"]

    def set_handlers(self, bot: telebot.TeleBot):
        """
        Регистрирует обработчики команд и callback для бота.
        """
        self.bot = bot

        @bot.message_handler(commands=self.commands)
        def send_currency_list(message: types.Message):
            if not self.api_key:
                bot.send_message(
                    chat_id=message.chat.id,
                    text="Сервис курсов валют временно недоступен. Пожалуйста, попробуйте позже."
                )
                return

            markup = types.InlineKeyboardMarkup(row_width=3)
            buttons = []
            for cur in self.currency_list:
                callback_data = f"currency_{cur}"
                buttons.append(types.InlineKeyboardButton(cur, callback_data=callback_data))
            markup.add(*buttons)

            bot.send_message(
                chat_id=message.chat.id,
                text="Выберите валюту, чтобы узнать её курс (в RUB):",
                reply_markup=markup
            )

        @bot.callback_query_handler(func=lambda call: call.data.startswith("currency_"))
        def currency_callback(call: types.CallbackQuery):
            if not self.api_key:
                bot.answer_callback_query(
                    call.id, "Сервис курсов валют временно недоступен"
                )
                return

            code = call.data.split("_")[1]
            try:
                resp = requests.get(
                    "https://api.freecurrencyapi.com/v1/latest",
                    params={
                        "apikey": self.api_key,
                        "base_currency": "RUB",
                        "currencies": code
                    },
                    timeout=5
                )
                resp.raise_for_status()
                json_data = resp.json()
                rate_per_rub = json_data["data"].get(code)
                if rate_per_rub:
                    rate = 1 / rate_per_rub
                    text = f"1 {code} = {rate:.4f} RUB"
                else:
                    text = "Не удалось получить курс для выбранной валюты."
            except requests.exceptions.RequestException as e:
                text = f"Ошибка при запросе курса: {str(e)}"
            # pylint: disable=broad-exception-caught
            except Exception as e:  # В данном случае ловим любые неожиданные ошибки
                text = f"Произошла ошибка: {str(e)}"

            bot.answer_callback_query(call.id)
            bot.send_message(chat_id=call.message.chat.id, text=text)
