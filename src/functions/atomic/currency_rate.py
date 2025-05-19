"""Module implementation of the atomic function for currency exchange rates."""
import os
import logging
from typing import List
import requests
import telebot
from telebot import types
from telebot.callback_data import CallbackData
from dotenv import load_dotenv

# Assuming bot_func_abc is available in the project
from bot_func_abc import AtomicBotFunctionABC

# Load environment variables from .env file
load_dotenv()

API_KEY = os.getenv('CURRENCY_API_KEY')
API_URL = f"https://api.freecurrencyapi.com/v1/latest?apikey= {API_KEY}"
REQUEST_TIMEOUT = 10  # Define a constant for timeout


class AtomicCurrencyFunction(AtomicBotFunctionABC):
    """Implementation of atomic function for currency exchange rates"""

    commands: List[str] = ["currency"]
    authors: List[str] = ["Jorik"]  # Replace with your name or alias
    about: str = "Узнать курс валют"
    description: str = """Функция предоставляет актуальный курс выбранной валюты к рублю.
    Использование: /currency"""
    state: bool = True

    bot: telebot.TeleBot
    currency_keyboard_factory: CallbackData

    def set_handlers(self, bot: telebot.TeleBot):
        """Set message handlers"""

        self.bot = bot
        # Define callback data factory for currency buttons
        self.currency_keyboard_factory = CallbackData(
            "currency_action", "currency_code", prefix=self.commands[0]
        )

        @bot.message_handler(commands=self.commands)
        def currency_message_handler(message: types.Message):
            self.show_currency_options(message)

        @bot.callback_query_handler(
            func=None, config=self.currency_keyboard_factory.filter()
        )
        def currency_keyboard_callback(call: types.CallbackQuery):
            self.handle_currency_button(call)

    def show_currency_options(self, message: types.Message) -> None:
        """Отправляет сообщение с кнопками выбора валюты."""
        # Define the inline keyboard layout
        keyboard = [
            [
                types.InlineKeyboardButton(
                    "USD",
                    callback_data=self.currency_keyboard_factory.new(
                        currency_action="get_rate", currency_code="USD"
                    )
                ),
                types.InlineKeyboardButton(
                    "EUR",
                    callback_data=self.currency_keyboard_factory.new(
                        currency_action="get_rate", currency_code="EUR"
                    )
                ),
                types.InlineKeyboardButton(
                    "GBP",
                    callback_data=self.currency_keyboard_factory.new(
                        currency_action="get_rate", currency_code="GBP"
                    )
                ),
            ],
            [
                types.InlineKeyboardButton(
                    "JPY",
                    callback_data=self.currency_keyboard_factory.new(
                        currency_action="get_rate", currency_code="JPY"
                    )
                ),
                types.InlineKeyboardButton(
                    "CNY",
                    callback_data=self.currency_keyboard_factory.new(
                        currency_action="get_rate", currency_code="CNY"
                    )
                ),
                types.InlineKeyboardButton(
                    "CHF",
                    callback_data=self.currency_keyboard_factory.new(
                        currency_action="get_rate", currency_code="CHF"
                    )
                ),
            ],
            [
                types.InlineKeyboardButton(
                    "RUB",
                    callback_data=self.currency_keyboard_factory.new(
                        currency_action="get_rate", currency_code="RUB"
                    )
                ),
            ],
        ]

        reply_markup = types.InlineKeyboardMarkup(keyboard)

        self.bot.send_message(
            chat_id=message.chat.id,
            text='Выберите валюту, чтобы узнать её курс (в RUB):',
            reply_markup=reply_markup
        )

    def handle_currency_button(self, call: types.CallbackQuery) -> None:
        """Обрабатывает нажатия кнопок с выбором валюты."""
        # Acknowledge the callback query
        self.bot.answer_callback_query(call.id)

        try:
            # Parse callback data to get action and currency code
            callback_data: dict = self.currency_keyboard_factory.parse(
                callback_data=call.data
            )
            action = callback_data["currency_action"]
            currency = callback_data["currency_code"]

            if action != "get_rate":
                self.bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text="Неизвестное действие кнопки."
                )
                return

            # Get currency rates from API
            response = requests.get(
                API_URL,
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()

            if not isinstance(data, dict) or 'data' not in data:
                self.bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text="Ошибка: неверный формат данных от API."
                )
                return

            rates = data['data']

            if currency not in rates or 'RUB' not in rates:
                self.bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"Не удалось получить курс для {currency} или RUB."
                )
                return

            rate_usd = rates[currency]
            rub_rate_usd = rates['RUB']

            if rub_rate_usd == 0:
                self.bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text="Невозможно рассчитать курс к RUB (курс RUB к USD равен 0)."
                )
                return

            rate_rub = rate_usd / rub_rate_usd

            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"1 {currency} = {rate_rub:.4f} RUB"
            )

        except requests.exceptions.RequestException as e:
            logging.exception("Error fetching currency rates from API: %s", e)
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"Произошла ошибка при получении данных от API: {str(e)}"
            )

        except (KeyError, TypeError, ValueError) as e:
            logging.exception("Error processing API response data: %s", e)
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"Ошибка обработки данных: {str(e)}"
            )
