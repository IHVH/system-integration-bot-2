"""Функция для получения данных о последнем запуске SpaceX."""

from typing import List

import requests
import telebot
from telebot import types

from bot_func_abc import AtomicBotFunctionABC


class SpacexBotFunction(AtomicBotFunctionABC):
    """Класс функции получения данных SpaceX."""

    # pylint: disable=too-few-public-methods

    commands: List[str] = ["spacex"]
    authors: List[str] = ["timurbetboom"]

    about: str = "Запуски SpaceX"

    description: str = (
        "Функция получает информацию о последнем запуске SpaceX через "
        "открытый REST API, обрабатывает полученные данные и отправляет "
        "пользователю название миссии, дату запуска, описание, статус "
        "полёта и ссылку на трансляцию запуска."
    )

    state: bool = True

    def set_handlers(self, bot: telebot.TeleBot):
        """Устанавливает обработчик команды spacex."""

        @bot.message_handler(commands=self.commands)
        def spacex_handler(message: types.Message):
            try:
                launch_data = self.__get_latest_launch()

                answer = self.__format_answer(launch_data)

                bot.reply_to(message, answer)

            except requests.RequestException:
                bot.reply_to(message, "Ошибка при запросе к API.")

            except KeyError:
                bot.reply_to(message, "Ошибка обработки данных.")

    @staticmethod
    def __get_latest_launch():
        url = "https://api.spacexdata.com/v4/launches/latest"

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        return response.json()

    @staticmethod
    def __format_answer(launch_data: dict) -> str:
        name = launch_data.get("name", "Нет данных")
        date = launch_data.get("date_utc", "Нет данных")
        success = launch_data.get("success")
        details = launch_data.get("details")
        webcast = launch_data.get("links", {}).get("webcast")

        if success is True:
            status = "Успешный запуск"

        elif success is False:
            status = "Запуск не был успешным"

        else:
            status = "Статус неизвестен"

        if not details:
            details = "Описание отсутствует"

        if not webcast:
            webcast = "Ссылка отсутствует"

        return (
            f"🚀 Последний запуск SpaceX\n\n"
            f"Миссия: {name}\n"
            f"Дата запуска: {date}\n"
            f"Статус: {status}\n\n"
            f"Описание:\n{details}\n\n"
            f"Трансляция:\n{webcast}"
        )
