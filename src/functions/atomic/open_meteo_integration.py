"""Module implementation of the atomic function of the telegram bot. Weather API integration."""

from typing import List
import logging

import requests
import telebot
from telebot import types

from bot_func_abc import AtomicBotFunctionABC


class WeatherFunction(AtomicBotFunctionABC):
    """Интеграция с Open-Meteo API для получения текущей погоды в Санкт-Петербурге."""

    commands: List[str] = ["spbweather"]
    authors: List[str] = ["Kksenia2004"]
    about: str = "Погода в Санкт-Петербурге"
    description: str = (
        "/spbweather — получить текущую погоду в Санкт-Петербурге"
        " (температура, облачность, ветер). "
        "Данные предоставлены Open-Meteo API."
    )
    state: bool = True

    URL = "https://api.open-meteo.com/v1/forecast"
    TIMEOUT = 5

    LAT = 59.9386
    LON = 30.3141

    bot: telebot.TeleBot

    def set_handlers(self, bot: telebot.TeleBot):
        """Устанавливает обработчик команды /weather."""
        self.bot = bot

        @bot.message_handler(commands=self.commands)
        def handle_weather(message: types.Message):
            weather = self.get_weather()
            self.bot.send_message(message.chat.id, weather)

    def get_weather(self) -> str:
        """Получает текущую погоду в Санкт-Петербурге через Open-Meteo API."""
        params = {
            "latitude": self.LAT,
            "longitude": self.LON,
            "current_weather": True
        }
        try:
            response = requests.get(self.URL, params=params, timeout=self.TIMEOUT)
            response.raise_for_status()
            data = response.json().get("current_weather", {})
            if not data:
                return "Не удалось получить погоду."
            temperature = data.get("temperature")
            wind = data.get("windspeed")
            winddirect = data.get("winddirection")

            return (
                f"Погода в Санкт-Петербурге:\n"
                f"Температура: {temperature}°C\n"
                f"Ветер: {wind} км/ч\n"
                f"Направление ветра: {winddirect}°\n"

            )
        except requests.RequestException:
            logging.exception("Ошибка при получении данных о погоде")
            return "Ошибка при получении погоды."
