"""Функция получения информации о стране."""

from typing import List

import requests
import telebot
from telebot import types

from bot_func_abc import AtomicBotFunctionABC


class CountryInfoBotFunction(AtomicBotFunctionABC):
    """Класс функции получения информации о стране."""

    # pylint: disable=too-few-public-methods

    commands: List[str] = ["country"]
    authors: List[str] = ["lizikbusiness"]

    about: str = "Информация о стране"

    description: str = (
        "Функция получает информацию о стране через открытый REST Countries API. "
        "Пользователь указывает название страны, после чего бот выводит "
        "столицу, население, валюту, регион и официальный флаг государства."
    )

    state: bool = True

    def set_handlers(self, bot: telebot.TeleBot):
        """Устанавливает обработчик команды country."""

        @bot.message_handler(commands=self.commands)
        def country_handler(message: types.Message):
            country_name = message.text.replace("/country", "").strip()

            if not country_name:
                bot.reply_to(
                    message,
                    "Введите страну. Пример: /country Japan"
                )
                return

            try:
                country_data = self.__get_country(country_name)

                if country_data is None:
                    bot.reply_to(message, "Страна не найдена.")
                    return

                answer = self.__format_answer(country_data)

                bot.reply_to(message, answer)

            except requests.RequestException:
                bot.reply_to(message, "Ошибка при запросе к API.")

            except KeyError:
                bot.reply_to(message, "Ошибка обработки данных.")

    @staticmethod
    def __get_country(country_name: str):
        url = f"https://restcountries.com/v3.1/name/{country_name}"

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        if not data:
            return None

        return data[0]

    @staticmethod
    def __format_answer(country_data: dict) -> str:
        name = country_data["name"]["common"]

        capital = (
            country_data["capital"][0]
            if "capital" in country_data
            else "Нет данных"
        )

        population = country_data.get("population", "Нет данных")
        region = country_data.get("region", "Нет данных")

        currencies = country_data.get("currencies", {})

        currency = "Нет данных"

        if currencies:
            currency = list(currencies.keys())[0]

        flag = country_data["flags"]["png"]

        return (
            f"🌍 Страна: {name}\n\n"
            f"🏙 Столица: {capital}\n"
            f"👥 Население: {population}\n"
            f"🌎 Регион: {region}\n"
            f"💰 Валюта: {currency}\n\n"
            f"🚩 Флаг:\n{flag}"
        )
