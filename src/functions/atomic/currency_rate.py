"""Module implementation of the atomic function for currency rates using currencyfreaks.com API."""

import os
import logging
from typing import List
import requests
import telebot
from telebot import types
from telebot.callback_data import CallbackData
from bot_func_abc import AtomicBotFunctionABC

class AtomicCurrencyRateFunction(AtomicBotFunctionABC):
    """Implementation of atomic function for currency rates."""

    commands: List[str] = ["currency"]
    authors: List[str] = ["Jorik887"]
    about: str = "Узнать курс валют"
    description: str = (
        "Функция выводит список валют и позволяет узнать их курс к RUB.\n"
        "Используйте команду /currency и выберите валюту.\n"
        "Требуется переменная окружения FREE_CURRENCY_API_KEY в .env"
    )
    state: bool = True

    bot: telebot.TeleBot
    currency_keyboard_factory: CallbackData
    API_URL = "https://api.freecurrencyapi.com/v1/latest"
    CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CNY", "CHF", "RUB"]

    def set_handlers(self, bot: telebot.TeleBot):
        """Set message and callback handlers for currency rates."""
        self.bot = bot
        self.currency_keyboard_factory = CallbackData("currency", "code", prefix=self.commands[0])

        @bot.message_handler(commands=self.commands)
        def currency_message_handler(message: types.Message):
            markup = self.__gen_currency_markup()
            bot.send_message(
                message.chat.id,
                "Выберите валюту, чтобы узнать её курс (в RUB):",
                reply_markup=markup
            )

        @bot.callback_query_handler(func=None, config=self.currency_keyboard_factory.filter())
        def currency_keyboard_callback(call: types.CallbackQuery):
            callback_data: dict = self.currency_keyboard_factory.parse(callback_data=call.data)
            code = callback_data["code"]
            try:
                rate = self.__get_currency_rate(code)
                if rate is not None:
                    text = f"1 {code} = {rate:.4f} RUB"
                else:
                    text = f"Не удалось получить курс для {code}."
                bot.answer_callback_query(call.id)
                bot.send_message(call.message.chat.id, text)
            except requests.RequestException as ex:
                logging.exception("Ошибка при получении курса валюты: %s", ex)
                bot.answer_callback_query(call.id, "Ошибка при получении курса.")
            except Exception as ex:  # pylint: disable=broad-except
                logging.exception("Неизвестная ошибка: %s", ex)
                bot.answer_callback_query(call.id, "Неизвестная ошибка при получении курса.")

    def __get_api_key(self) -> str:
        """Get currencyfreaks API key from environment variables."""
        api_key = os.environ.get("FREE_CURRENCY_API_KEY")
        if not api_key:
            raise RuntimeError("FREE_CURRENCY_API_KEY не найден в переменных окружения!")
        return api_key

    def __get_currency_rate(self, code: str) -> float:
        """Get currency rate for selected code to RUB."""
        if code == "RUB":
            return 1.0
        params = {
            "apikey": self.__get_api_key(),
            "base": code,
            "symbols": "RUB"
        }
        response = requests.get(self.API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        rub_rate = data.get("rates", {}).get("RUB")
        if rub_rate:
            return float(rub_rate)
        return None

    def __gen_currency_markup(self) -> types.InlineKeyboardMarkup:
        """Generate inline keyboard for currency selection."""
        markup = types.InlineKeyboardMarkup(row_width=3)
        buttons = [
            types.InlineKeyboardButton(
                code, callback_data=self.currency_keyboard_factory.new(code=code)
            ) for code in self.CURRENCIES
        ]
        # Разбиваем на строки по 3 кнопки, как на скриншоте
        for i in range(0, len(buttons)-1, 3):
            markup.row(*buttons[i:i+3])
        # Последнюю кнопку (RUB) в отдельную строку
        markup.row(buttons[-1])
        return markup
