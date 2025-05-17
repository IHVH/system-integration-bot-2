"""Модуль для поиска информации о ip-адресе"""

import os
import logging
from typing import List  # Стандартные библиотеки

import requests
import telebot
from telebot import types  # Сторонние библиотеки

from bot_func_abc import AtomicBotFunctionABC  # Локальные модули


class IPLookupBotFunction(AtomicBotFunctionABC):
    """Модуль для поиска информации о IP адресе с использованием API ipstack."""

    commands: List[str] = ["iplookup"]
    authors: List[str] = ["Icestorm-dev"]
    about: str = "Информация об IP-адресе."
    description: str = """Эта функция позволяет получать информацию об IP-адресах через API ipstack.
    Используйте команду /iplookup <IP-адрес>, чтобы получить данные."""
    state: bool = True

    bot: telebot.TeleBot

    def set_handlers(self, bot: telebot.TeleBot):
        """Устанавливает обработчики событий для бота."""
        self.bot = bot

        @bot.message_handler(commands=self.commands)
        def ip_lookup_handler(message: types.Message):
            args = message.text.split()
            if len(args) != 2:
                bot.send_message(
                    message.chat.id,
                    "\u274C Пожалуйста, укажите IP-адрес. Пример: /iplookup 134.201.250.155"
                )
                return

            ip_address = args[1]
            self.__fetch_ip_data(message, ip_address)

    def __fetch_ip_data(self, message: types.Message, ip_address: str):
        """Получить информацию об IP-адресе."""
        api_key = os.getenv("IPSTACK_API_KEY")
        if not api_key:
            self.bot.send_message(
                message.chat.id,
                "\u274C API-ключ не найден."
            )
            return

        url = f"http://api.ipstack.com/{ip_address}?access_key={api_key}"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                self.bot.send_message(
                    message.chat.id,
                    f"\u274C Ошибка: {data['error'].get('info', 'Неизвестная ошибка')}"
                )
                return

            # Format and send data
            # Форматирование и отправка данных
            languages = [
                lang.get('native', 'Неизвестно')
                for lang in data.get('location', {}).get('languages', [])
            ]
            info = (
                f"\U0001F4E7 Информация об IP-адресе {ip_address}:\n"
                f"🌐 Тип IP: {data.get('type', 'Неизвестно')}\n"
                f"🏳️ Страна: {data.get('country_name', 'Неизвестно')} "
                f"({data.get('country_code', 'Неизвестно')})\n"
                f"📍 Регион: {data.get('region_name', 'Неизвестно')} "
                f"({data.get('region_code', 'Неизвестно')})\n"
                f"🏙️ Город: {data.get('city', 'Неизвестно')}\n"
                f"📮 Почтовый индекс: {data.get('zip', 'Неизвестно')}\n"
                f"🌎 Континент: {data.get('continent_name', 'Неизвестно')} "
                f"({data.get('continent_code', 'Неизвестно')})\n"
                f"🗺️ Координаты: {data.get('latitude', 'Неизвестно')}° N, "
                f"{data.get('longitude', 'Неизвестно')}° E\n"
                f"📞 Код страны: +{data.get('location', {}).get('calling_code', 'Неизвестно')}\n"
                f"🗣️ Языки: {', '.join(languages)}\n"
            )

            self.bot.send_message(message.chat.id, info)
        except requests.exceptions.RequestException as e:
            logging.exception(e)
            self.bot.send_message(
                message.chat.id,
                "\u274C Не удалось получить данные. Проверьте соединение с интернетом."
            )
