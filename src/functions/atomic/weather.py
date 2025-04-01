"""
Модуль для Telegram-бота, предоставляющий функционал получения текущей погоды
в указанном городе с использованием API OpenWeatherMap.
"""

import os
import logging
from typing import List
import requests
import telebot
from telebot import types
from telebot.callback_data import CallbackData
from bot_func_abc import AtomicBotFunctionABC

class WeatherBotFunction(AtomicBotFunctionABC):
    """Модуль для получения текущей погоды в указанном городе через Telegram-бота."""

    commands: List[str] = ["weather"]
    authors: List[str] = ["YourGitHubUsername"]
    about: str = "Погода в городе"
    description: str = (
        "Этот бот позволяет узнать текущую погоду в указанном городе. "
        "Используйте команду /weather <город> . Например: /w eather Москва"
    )
    state: bool = True

    bot: telebot.TeleBot
    weather_keyboard_factory: CallbackData
    logger: logging.Logger
    api_key: str
    api_url: str = "http://api.openweathermap.org/data/2.5/weather"

    def __init__(self):
        """Инициализация класса WeatherBotFunction."""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(name)s %(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        self.api_key = os.environ.get("OPENWEATHER_API_KEY")
        self.logger.info("Loaded API key: %s", self.api_key)
        self.api_key = self.api_key or "dummy_key"

    def set_handlers(self, bot: telebot.TeleBot):
        """Устанавливает обработчики команд для бота."""
        if not self.state:
            self.logger.warning("Function disabled due to missing API key.")
            return

        self.bot = bot
        self.weather_keyboard_factory = CallbackData(
            'weather_key_button', prefix=self.commands[0]
        )

        @bot.message_handler(commands=self.commands)
        def get_weather(message: types.Message):
            """Обрабатывает команду /weather."""
            try:
                city = " ".join(message.text.split()[1:]).strip()
                if not city:
                    raise ValueError("Город не указан.")
            except ValueError:
                msg = "Пожалуйста, укажите город. Пример: /weather Москва"
                bot.send_message(message.chat.id, msg)
                self.logger.warning(
                    "Invalid input for /weather: %s", message.text
                )
                return

            self.logger.info(
                "User %s requested weather for %s.",
                message.from_user.username,
                city
            )
            weather_data = self.fetch_weather(city)
            if not weather_data:
                bot.send_message(
                    message.chat.id,
                    f"Не удалось получить погоду для города {city}."
                )
                self.logger.error("Failed to fetch weather for %s.", city)
                return

            bot.send_message(message.chat.id, weather_data)

    def fetch_weather(self, city: str) -> str:
        """Получает данные о погоде для указанного города через OpenWeatherMap API."""
        params = {
            "q": city,
            "appid": self.api_key,
            "units": "metric",
            "lang": "ru"
        }

        try:
            response = requests.get(self.api_url, params=params, timeout=10)
            if response.status_code != 200:
                self.logger.error(
                    "API request failed with status %d: %s",
                    response.status_code,
                    response.text
                )
                return None

            data = response.json()
            if data.get("cod") != 200:
                self.logger.error(
                    "API error: %s",
                    data.get('message', 'Unknown error')
                )
                return None

            main = data["main"]
            weather = data["weather"][0]
            temperature = main["temp"]
            feels_like = main["feels_like"]
            description = weather["description"]
            humidity = main["humidity"]
            wind_speed = data["wind"]["speed"]

            weather_message = (
                f"Погода в городе {city}:\n"
                f"Температура: {temperature}°C\n"
                f"Ощущается как: {feels_like}°C\n"
                f"Описание: {description.capitalize()}\n"
                f"Влажность: {humidity}%\n"
                f"Скорость ветра: {wind_speed} м/с"
            )
            self.logger.info(
                "Successfully fetched weather for %s: %s°C, %s",
                city,
                temperature,
                description
            )
            return weather_message

        except requests.RequestException as e:
            self.logger.error("Error fetching weather from API: %s", e)
            return None
        except (KeyError, IndexError) as e:
            self.logger.error("Error parsing API response: %s", e)
            return None
