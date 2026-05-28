"""
Module for aviation weather bot function.
"""

from typing import Dict, Optional, Any

import requests
import telebot
from telebot import types

from bot_func_abc import AtomicBotFunctionABC


class AviationWeatherBotFunction(AtomicBotFunctionABC):
    """
    Bot function that provides aviation weather (METAR) by ICAO airport code.
    """

    commands = ["aviation"]
    authors = ["cactius"]
    about = "Погода по ICAO-коду аэропорта"
    description = (
        "Функция показывает METAR по ICAO-коду аэропорта. "
        "Пример: /aviation ULLI, UUDD, UUWW, UNNT. "
        "Разработал студент ОУИТБ-ПИ01-23-1 ФИО."
    )
    state = True

    def set_handlers(self, bot: telebot.TeleBot) -> None:
        """
        Set message handlers for aviation weather command.
        """

        @bot.message_handler(commands=self.commands)
        def aviation_weather_handler(message: types.Message) -> None:
            """Handle /aviation command and reply with METAR data."""
            airport_id = message.text.replace("/aviation", "").strip().upper()

            if not airport_id:
                bot.reply_to(message, "Введите ICAO-код. Пример: /aviation ULLI")
                return

            try:
                metar_data = self._get_metar(airport_id)

                if metar_data is None:
                    bot.reply_to(message, "Данные по аэропорту не найдены.")
                    return

                answer = self._format_answer(metar_data)
                bot.reply_to(message, answer)

            except requests.RequestException as req_err:
                bot.reply_to(message, f"Ошибка при запросе к API: {req_err}")

            except KeyError as key_err:
                bot.reply_to(message, f"Ошибка обработки данных: {key_err}")

    @staticmethod
    def _get_metar(airport_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch METAR data from aviationweather.gov API.

        Args:
            airport_id: ICAO airport code (e.g., 'ULLI')

        Returns:
            Dictionary with METAR data or None if no data found.
        """
        url = "https://aviationweather.gov/api/data/metar"
        params = {
            "ids": airport_id,
            "format": "json",
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        if not data:
            return None

        return data[0]

    @staticmethod
    def _format_answer(metar_data: Dict[str, Any]) -> str:
        """
        Format METAR data into a readable string.

        Args:
            metar_data: Dictionary containing METAR information.

        Returns:
            Formatted weather report string.
        """
        airport_id = metar_data.get("icaoId", "Неизвестно")
        raw_text = metar_data.get("rawOb", "Нет данных")
        temperature = metar_data.get("temp", "Нет данных")
        dewpoint = metar_data.get("dewp", "Нет данных")
        wind_direction = metar_data.get("wdir", "Нет данных")
        wind_speed = metar_data.get("wspd", "Нет данных")
        visibility = metar_data.get("visib", "Нет данных")

        return (
            f"✈️ Авиационная погода: {airport_id}\n\n"
            f"🌡 Температура: {temperature}°C\n"
            f"💧 Точка росы: {dewpoint}°C\n"
            f"💨 Ветер: {wind_direction}° / {wind_speed} kt\n"
            f"👁 Видимость: {visibility}\n\n"
            f"METAR:\n{raw_text}"
        )

    def get_info(self) -> Dict[str, Any]:
        """
        Get information about this bot function.

        Returns:
            Dictionary with function metadata.
        """
        return {
            "commands": self.commands,
            "authors": self.authors,
            "about": self.about,
            "description": self.description,
            "state": self.state,
        }
