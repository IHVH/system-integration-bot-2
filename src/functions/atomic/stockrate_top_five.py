"""Модуль с функцией для вывода курсов топ-5 ценных бумаг с использованием Finnhub API."""

import json
import os
import requests
from requests.exceptions import RequestException
from telebot.types import Message
from bot_func_abc import AtomicBotFunctionABC

class StockRateFunction(AtomicBotFunctionABC):
    """Класс для получения и отображения курсов топ-5 ценных бумаг с использованием Finnhub API."""
    commands = ["stockrate", "companyinfo"]
    authors = ["Garik205"]
    about = "Вывод курсов топ-5 ценных бумаг\n/companyinfo a - информация о компании"
    description = "Команда /stockrate показывает текущие курсы для топ-5 ценных бумаг."
    state = True

    def set_handlers(self, bot):
        """Реализация функции"""
        @bot.message_handler(commands=self.commands[0])
        def handle_stockrate(message: Message):
            try:
                api_key = os.getenv("FINNHUB_API_KEY")
                if not api_key:
                    bot.send_message(message.chat.id, "API ключ не " \
                    "найден. Пожалуйста, настройте переменную среды FINNHUB_API_KEY.")
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
        @bot.message_handler(commands=self.commands[1])
        def handle_company_info(message: Message):
            try:
                api_key = os.getenv("FINNHUB_API_KEY")
                if not api_key:
                    bot.send_message(message.chat.id, "API ключ не " \
                    "найден. Пожалуйста, настройте переменную среды FINNHUB_API_KEY.")
                    return

                parts = message.text.split()
                if len(parts) < 2:
                    bot.send_message(message.chat.id, "Пожалуйста, укажите символ компании после " \
                    "команды /companyinfo или название одной из " \
                    "ценных бумаг. Формат: /companyinfo aapl")
                    return

                symbol = parts[1].upper()
                response = requests.get(
                    f"https://finnhub.io/api/v1/stock/profile2?symbol={symbol}&token={api_key}",
                    timeout=5
                )
                response.raise_for_status()
                data = response.json()

                if not data:
                    bot.send_message(
                        message.chat.id, f"Информация о компании для символа {symbol} не найдена."
                    )
                    return

                company_info = (
                    f"Информация о компании {symbol}:\n"
                    f"Название: {data.get('name', 'N/A')}\n"
                    f"Страна: {data.get('country', 'N/A')}\n"
                    f"Отрасль: {data.get('finnhubIndustry', 'N/A')}\n"
                    f"Вебсайт: {data.get('weburl', 'N/A')}\n"
                )

                bot.send_message(message.chat.id, company_info)

            except (RequestException, json.JSONDecodeError) as e:
                bot.send_message(message.chat.id, f"Произошла ошибка: {e}")
