"""Функция для проверки качества воздуха в городе."""

from typing import List

import requests
import telebot
from telebot import types

from bot_func_abc import AtomicBotFunctionABC


class AirQualityBotFunction(AtomicBotFunctionABC):
    """Класс функции проверки качества воздуха."""

    # pylint: disable=too-few-public-methods

    commands: List[str] = ["air"]
    authors: List[str] = ["Morpho-development"]
    about: str = "Качества воздуха в городе"
    description: str = (
        "Функция показывает качество воздуха по названию города. "
        "Пример: /air Москва. "
        "Разработал студент ОУИТБ-ПИ01-23-1 Артёмов Дмитрий."
    )
    state: bool = True

    def set_handlers(self, bot: telebot.TeleBot):
        """Устанавливает обработчик команды air."""

        @bot.message_handler(commands=self.commands)
        def air_quality_handler(message: types.Message):
            city = message.text.replace("/air", "").strip()
            if not city:
                bot.reply_to(message, "Введите город. Пример: /air Москва")
                return
            try:
                coordinates = self.__get_city_coordinates(city)
                if coordinates is None:
                    bot.reply_to(message, "Город не найден.")
                    return
                air_data = self.__get_air_quality(
                    coordinates["latitude"],
                    coordinates["longitude"]
                )
                answer = self.__format_answer(
                    coordinates["name"],
                    air_data
                )
                bot.reply_to(message, answer)
            except requests.RequestException:
                bot.reply_to(message, "Ошибка при запросе к API.")
            except KeyError:
                bot.reply_to(message, "Ошибка обработки данных.")

    @staticmethod
    def __get_city_coordinates(city: str):
        url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {
            "name": city,
            "count": 1,
            "language": "ru",
            "format": "json",
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if "results" not in data:
            return None
        location = data["results"][0]
        return {
            "name": location["name"],
            "latitude": location["latitude"],
            "longitude": location["longitude"],
        }

    @staticmethod
    def __get_air_quality(latitude: float, longitude: float):
        url = "https://air-quality-api.open-meteo.com/v1/air-quality"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide",
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def __format_answer(city_name: str, air_data: dict) -> str:
        current = air_data["current"]
        pm25 = current["pm2_5"]
        pm10 = current["pm10"]
        carbon_monoxide = current["carbon_monoxide"]
        nitrogen_dioxide = current["nitrogen_dioxide"]
        level = AirQualityBotFunction.__get_air_level(pm25)
        return (
            f"🌫 Качество воздуха в городе {city_name}\n\n"
            f"PM2.5: {pm25} мкг/м³\n"
            f"PM10: {pm10} мкг/м³\n"
            f"CO: {carbon_monoxide} мкг/м³\n"
            f"NO₂: {nitrogen_dioxide} мкг/м³\n\n"
            f"Оценка: {level}\n\n"
            f"👨‍💻 Студент ОУИТБ-ПИ01-23-1 Артёмов Дмитрий"
        )

    @staticmethod
    def __get_air_level(pm25: float) -> str:
        if pm25 <= 10:
            return "🟢 Хорошее качество воздуха"
        if pm25 <= 25:
            return "🟡 Среднее качество воздуха"
        if pm25 <= 50:
            return "🟠 Повышенное загрязнение"
        return "🔴 Плохое качество воздуха"
