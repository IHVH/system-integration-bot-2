import logging
import requests
from typing import List
import telebot
from telebot import types
from bot_func_abc import AtomicBotFunctionABC
import os

class CurrencyBotFunction(AtomicBotFunctionABC):
    commands: List[str] = ["currency"]
    authors: List[str] = ["p1aG790"]
    about: str = "Курс валют"
    description: str = "Показывает текущий курс валюты относительно рубля. Используйте: /currency <валюта> (например, /currency USD)"
    state: bool = True

    bot: telebot.TeleBot
    logger: logging.Logger
    api_key: str = os.environ.get("EXCHANGE_RATE_API_KEY")
    api_url: str = "https://v6.exchangerate-api.com/v6/{api_key}/latest/RUB"

    def __init__(self):
        
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(name)s %(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        
        self.logger.info("CurrencyBotFunction initialized")

        
        if not self.api_key:
            self.logger.critical("EXCHANGE_RATE_API_KEY is missing!")
            self.state = False

    def set_handlers(self, bot: telebot.TeleBot):
        self.bot = bot

        
        self.logger.info("Setting handlers for /currency")

        
        if not self.state:
            self.logger.warning("CurrencyBotFunction is disabled (state=False)")
            return

        
        @self.bot.message_handler(commands=self.commands)
        def get_currency(message: types.Message):
            self.logger.info("Command /currency triggered by user %s", message.from_user.username)

            try:
                currency = message.text.split()[1].upper()
                if not currency:
                    raise ValueError("Укажите валюту, например, /currency USD")
            except (IndexError, ValueError):
                bot.send_message(message.chat.id, "Ошибка: Укажите валюту, например, /currency USD")
                return

            rate = self.fetch_currency_rate(currency)
            if rate:
                bot.send_message(
                    message.chat.id,
                    f"Курс {currency} к RUB: {rate:.2f} (на {self.get_current_date()})"
                )
            else:
                bot.send_message(message.chat.id, f"Не удалось получить курс для {currency}.")

    def fetch_currency_rate(self, currency: str) -> float:
        """Получает курс валюты через ExchangeRate-API."""
        url = self.api_url.format(api_key=self.api_key)
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                self.logger.error("API request failed with status %d: %s", response.status_code, response.text)
                return None
            data = response.json()
            if data.get("result") != "success":
                self.logger.error("API error: %s", data.get("error-type", "Unknown error"))
                return None

            rates = data.get("conversion_rates", {})
            rate = rates.get(currency)
            if not rate:
                self.logger.error("Currency %s not found in API response", currency)
                return None

            self.logger.info("Raw rate (1 RUB to %s): %f", currency, rate)
            inverted_rate = 1 / rate if rate != 0 else None
            if inverted_rate is None:
                self.logger.error("Cannot calculate inverted rate for %s (rate is 0)", currency)
                return None

            self.logger.info("Inverted rate (1 %s to RUB): %f", currency, inverted_rate)
            return inverted_rate

        except requests.RequestException as e:
            self.logger.error("Error fetching currency rate: %s", str(e))
            return None

    def get_current_date(self) -> str:
        """Возвращает текущую дату в формате день.месяц.год."""
        from datetime import datetime
        return datetime.now().strftime("%d.%m.%Y")
