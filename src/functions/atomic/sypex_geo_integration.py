"""Module implementation of the atomic function: IPInfoFunction"""

from typing import List
import requests
import telebot
from telebot import types
from bot_func_abc import AtomicBotFunctionABC


class IPInfoFunction(AtomicBotFunctionABC):
    """Atomic function for obtaining IP information via sypexgeo.net"""

    commands: List[str] = ["ip_info"]
    authors: List[str] = ["Speedware"]
    about: str = "Информация по IP"
    description: str = (
    "Получение подробной информации по IP адресу через сервис "
    "sypexgeo.net. Команда позволяет определить страну, город, "
    "провайдера и другие сетевые данные для указанного IP адреса. "
    "Пример команды: /ip_info 8.8.8.8"
    )
    state: bool = True

    BASE_URL = "https://api.sypexgeo.net/json"
    TIMEOUT = 5

    bot: telebot.TeleBot

    def set_handlers(self, bot: telebot.TeleBot):
        """
        Получает данные об ip через SypexGeo API.
        """
        self.bot = bot

        @bot.message_handler(commands=self.commands)
        def ip_info_handler(message: types.Message):
            args = message.text.strip().split()

            if len(args) < 2:
                bot.send_message(
                    message.chat.id,
                    "Укажи IP: /ip_info 8.8.8.8"
                )
                return

            ip = args[1]

            try:
                response = requests.get(
                    f"{self.BASE_URL}/{ip}",
                    timeout=self.TIMEOUT
                )
                response.raise_for_status()
                data = response.json()

                if not data:
                    bot.send_message(message.chat.id, "Информация не найдена.")
                    return

                reply = (
                    f"🌍 IP: {data.get('ip')}\n\n"

                    f"🏳️ Страна:\n"
                    f"  {data.get('country', {}).get('name_ru')} "
                    f"({data.get('country', {}).get('iso')})\n"
                    f"  Столица: {data.get('country', {}).get('capital_ru')}\n"
                    f"  Валюта: {data.get('country', {}).get('cur_code')}\n\n"

                    f"📍 Регион:\n"
                    f"  {data.get('region', {}).get('name_ru')}\n"
                    f"  Таймзона: {data.get('region', {}).get('timezone')}\n\n"

                    f"🏙 Город:\n"
                    f"  {data.get('city', {}).get('name_ru')}\n"
                    f"  Население: {data.get('city', {}).get('population')}\n\n"

                    f"📌 Координаты:\n"
                    f"  Широта: {data.get('city', {}).get('lat')}\n"
                    f"  Долгота: {data.get('city', {}).get('lon')}\n"
                )

                bot.send_message(message.chat.id, reply)

            except requests.RequestException as err:
                status = getattr(err.response, "status_code", "N/A")
                bot.send_message(
                    message.chat.id,
                    f"Ошибка запроса (код {status})"
                )
