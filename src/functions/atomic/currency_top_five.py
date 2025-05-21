"""Модуль с функцией для вывода курсов топ-5 валют с использованием API."""

import json
import requests
from requests.exceptions import RequestException
from telebot.types import Message
from bot_func_abc import AtomicBotFunctionABC

class CurrencyRateFunction(AtomicBotFunctionABC):
    """Класс для обработки команды /currencyrate, выводящей курсы топ-5 валют."""

    commands = ["currencyrate"]
    authors = ["YourName"]
    about = "Вывод курсов топ-5 валют"
    description = "Команда /currencyrate показывает курсы обмена для топ-5 валют мира."
    state = True

    def set_handlers(self, bot):
        """Устанавливает обработчики команд для бота."""

        @bot.message_handler(commands=self.commands)
        def handle_currencyrate(message: Message):
            """Обработчик команды /currencyrate."""
            try:
                response = requests.get(
                    "https://api.exchangerate-api.com/v4/latest/USD", timeout=5
                )
                response.raise_for_status()
                data = response.json()

                top_currencies = ['EUR', 'JPY', 'GBP', 'AUD', 'CAD']
                currency_info = {
                    'EUR': 'Евро',
                    'JPY': 'Японская иена',
                    'GBP': 'Британский фунт',
                    'AUD': 'Австралийский доллар',
                    'CAD': 'Канадский доллар'
                }
                rates ={currency: data['rates'].get(currency, 'N/A') for currency in top_currencies}

                message_text = "💱 Курсы обмена для топ-5 валют:\n\n"
                for currency, rate in rates.items():
                    description = currency_info.get(currency, 'Неизвестная валюта')
                    message_text += f"{currency} ({description}): {rate}\n"

                bot.send_message(message.chat.id, message_text)

                additional_info = (
                    "🟢 EUR: Евро - валюта Европейского союза, используется в 19 из 27 стран ЕС.\n"
                    "🟠 JPY: Японская иена - валюта Японии, одна из самых торгуемых валют в мире.\n"
                    "🔴 GBP: Британский фунт - валюта Великобритании, одна из старейших "
                    "валют в мире.\n"
                    "⚫ AUD: Австралийский доллар - валюта Австралии, популярная в торговле "
                    "сырьевыми товарами.\n"
                    "🟤 CAD: Канадский доллар - валюта Канады, часто используется в торговле нефтью."
                )
                bot.send_message(message.chat.id, additional_info)

            except (RequestException, json.JSONDecodeError) as e:
                bot.send_message(message.chat.id, f"Произошла ошибка: {e}")
