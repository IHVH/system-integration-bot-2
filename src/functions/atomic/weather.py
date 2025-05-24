"""
Модуль предоставляет функционал получения текущей погоды
в указанном городе через Telegram-бот с использованием API OpenWeatherMap.
"""

import os
import requests
import telebot
from bot_func_abc import AtomicBotFunctionABC

class WeatherBotFunction(AtomicBotFunctionABC):
    """Модуль для получения текущей погоды через Telegram-бота."""

    commands = ["weather"]
    authors = ["Bervev"]
    about = "Погода в городе"
    description = (
        "Этот бот позволяет узнать текущую погоду в указанном городе. "
        "Используйте команду /weather <город> . Например: /weather Москва"
    )
    state = True

    def __init__(self):
        self.api_key = os.getenv("OPENWEATHER_API_KEY", "dummy_key")
        self.api_url = "http://api.openweathermap.org/data/2.5/weather"

    def set_handlers(self, bot: telebot.TeleBot):
        """Установка обработчиков для команды /weather."""
        @bot.message_handler(commands=self.commands)
        def handle_weather_command(message: telebot.types.Message):
            city = " ".join(message.text.split()[1:]).strip()
            if not city:
                bot.send_message(message.chat.id, "Укажите город. Пример: /weather Москва")
                return

            weather_data = self.fetch_weather(city)
            if weather_data:
                bot.send_message(message.chat.id, weather_data)
            else:
                bot.send_message(
                    message.chat.id,
                    f"Не удалось получить данные для города: {city}."
                )

    def fetch_weather(self, city: str) -> str:
        """Получение данных о погоде из API OpenWeatherMap."""
        params = {
            "q": city,
            "appid": self.api_key,
            "units": "metric",
            "lang": "ru"
        }
        try:
            response = requests.get(self.api_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("cod") != 200:
                return None

            weather_message = (
                f"Погода в городе {city}:\n"
                f"Температура: {data['main']['temp']}°C\n"
                f"Ощущается как: {data['main']['feels_like']}°C\n"
                f"Описание: {data['weather'][0]['description'].capitalize()}\n"
                f"Влажность: {data['main']['humidity']}%\n"
                f"Скорость ветра: {data['wind']['speed']} м/с"
            )
            return weather_message
        except requests.RequestException:
            return None
