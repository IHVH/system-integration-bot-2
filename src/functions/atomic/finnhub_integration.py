"""Module implementation of the atomic function of the telegram bot: FinnhubIntegrationFunction"""

import os
from typing import List
import requests
import telebot
from telebot import types
from bot_func_abc import AtomicBotFunctionABC


class FinnhubIntegrationFunction(AtomicBotFunctionABC):
    """Atomic function for obtaining stock data via finnhub.io"""

    commands: List[str] = ["top_5", "info_company"]
    authors: List[str] = ["NikitkaZXC"]
    about: str = "Топ 5 бумаг через finnhub.io"
    description: str = (
        "Получение топ 5 акций по цене.\n"
        "Пример команды: /top_5\n\n"
        "Получение информации о компании.\n"
        "Пример команды: /info_company AAPL"
    )
    state: bool = True

    API_KEY_FINN_HUB = os.environ.get("API_KEY_FINN_HUB")

    BASE_URL = "https://finnhub.io/api/v1"
    TIMEOUT = 5

    bot: telebot.TeleBot

    def set_handlers(self, bot: telebot.TeleBot):
        """
        Получает данные о финансовом инструменте через Finnhub API.

        Args:
            symbol (str): тикер (например, AAPL)

        Returns:
            dict: ответ от API с данными по инструменту
        """
        self.bot = bot

        @bot.message_handler(commands=["top_5"])
        def top_5_handler(message: types.Message):
            try:
                response = requests.get(
                    f"{self.BASE_URL}/stock/symbol",
                    params={"exchange": "US", "token": self.API_KEY_FINN_HUB},
                    timeout=self.TIMEOUT
                )
                response.raise_for_status()
                data = response.json()

                symbols = [item["symbol"] for item in data[:50]]

                stocks = []

                for symbol in symbols:
                    try:
                        quote = requests.get(
                            f"{self.BASE_URL}/quote",
                            params={"symbol": symbol, "token": self.API_KEY_FINN_HUB},
                            timeout=self.TIMEOUT
                        ).json()

                        price = quote.get("c")

                        if price is not None and price > 0:
                            stocks.append({
                                "symbol": symbol,
                                "price": price
                            })

                    except requests.RequestException:
                        continue

                if not stocks:
                    bot.send_message(message.chat.id, "Не удалось получить данные.")
                    return

                stocks.sort(key=lambda x: x["price"], reverse=True)

                top5 = stocks[:5]

                reply = "💰 Топ 5 акций по стоимости:\n\n"
                for stock in top5:
                    reply += f"{stock['symbol']}: ${round(stock['price'], 2)}\n"

                bot.send_message(message.chat.id, reply)

            except requests.RequestException:
                bot.send_message(message.chat.id, "Ошибка при получении данных.")


        @bot.message_handler(commands=["info_company"])
        def info_company_handler(message: types.Message):
            args = message.text.strip().split()

            if len(args) < 2:
                bot.send_message(
                    message.chat.id,
                    "Укажи символ: /info_company AAPL"
                )
                return

            symbol = args[1].upper()

            try:
                response = requests.get(
                    f"{self.BASE_URL}/stock/profile2",
                    params={"symbol": symbol, "token": self.API_KEY_FINN_HUB},
                    timeout=self.TIMEOUT
                )
                response.raise_for_status()
                data = response.json()

                if not data:
                    bot.send_message(message.chat.id, "Компания не найдена.")
                    return

                reply = (
                    f"🏢 {data.get('name')}\n"
                    f"Символ: {symbol}\n"
                    f"Страна: {data.get('country')}\n"
                    f"Биржа: {data.get('exchange')}\n"
                    f"Отрасль: {data.get('finnhubIndustry')}\n"
                    f"Сайт: {data.get('weburl')}\n"
                )

                bot.send_message(message.chat.id, reply)

            except requests.RequestException as err:
                status = getattr(err.response, "status_code", "N/A")
                bot.send_message(
                    message.chat.id,
                    f"Ошибка запроса (код {status})"
                )
