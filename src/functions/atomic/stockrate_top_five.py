"""Модуль с функцией для вывода курсов топ-5 ценных бумаг с использованием Finnhub API."""

import json
import os
import requests
from requests.exceptions import RequestException
from telebot.types import Message
from bot_func_abc import AtomicBotFunctionABC

class StockRateFunction(AtomicBotFunctionABC):
    commands = ["stockrate"]
    authors = ["Garik205"]
    about = "Вывод курсов топ-5 ценных бумаг"
    description = "Команда /stockrate показывает текущие курсы для топ-5 ценных бумаг."
    state = True

    def set_handlers(self, bot):

        @bot.message_handler(commands=self.commands)
        def handle_stockrate(message: Message):
            try:
                api_key = os.getenv("FINNHUB_API_KEY")
                if not api_key:
                    bot.send_message(message.chat.id, "API ключ не найден. Пожалуйста, настройте переменную среды FINNHUB_API_KEY.")
                    return
                symbols = ['AAPL', 'GOOGL', 'AMZN', 'MSFT', 'TSLA']
                stock_info = {
                    'AAPL': 'Apple Inc.',
                    'GOOGL': 'Alphabet Inc.',
                    'AMZN': 'Amazon.com Inc.',
                    'MSFT': 'Microsoft Corp.',
                    'TSLA': 'Tesla Inc.'
                }

                message_text = "📈 Курсы топ-5 ценных бумаг:\n\n"
                for symbol in symbols:
                    response = requests.get(
                        f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={api_key}",timeout=5
                    )
                    response.raise_for_status()
                    data = response.json()
                    current_price = data.get('c', 'N/A')
                    description = stock_info.get(symbol, 'Неизвестная ценная бумага')
                    message_text += f"{symbol} ({description}): {current_price}\n"

                bot.send_message(message.chat.id, message_text)

            except (RequestException, json.JSONDecodeError) as e:
                bot.send_message(message.chat.id, f"Произошла ошибка: {e}")
                