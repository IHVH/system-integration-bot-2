"""Модуль создания коротких ссылок с возможностью 
собственного названия используя Free Url Shortener API"""

from typing import List
import time
import telebot
import requests
from telebot import types
from bot_func_abc import AtomicBotFunctionABC

class AtomicCreatingLinksFunction(AtomicBotFunctionABC):
    """Модуль создания ссылок"""

    commands: List[str] = ["createlink", "customlink"]
    authors: List[str] = ["MrNightFox"]
    about: str = "Создание коротких ссылок"
    description: str = """/createlink - создание короткой ссылки
/customlink - создание короткой ссылки со своим названием
    """
    state: bool = True

    bot: telebot.TeleBot

    def set_handlers(self, bot: telebot.TeleBot):
        """Обработка команд функций"""
        self.bot = bot

        def fetch_url(url):
            try:
                response = requests.get(url, timeout=10)
                return response
            except requests.exceptions.RequestException:
                return None

        @bot.message_handler(commands=[self.commands[0]])
        def create_link(message: types.Message):
            '''Функция создания простой ссылки'''
            url = ' '.join(message.text.split()[1:])
            if not url:
                bot.send_message(message.chat.id,
                f'Используйте: /{self.commands[0]} <URL>')
                return

            api_url = f'https://ulvis.net/api.php?url={url}&private=1'
            start_time = time.time()
            timeout = 30

            while True:
                response = fetch_url(api_url)
                if response and response.status_code == 200:
                    bot.send_message(message.chat.id, f'Ответ от сервера: {response.text}')
                    return
                if response:
                    bot.send_message(message.chat.id, f'Ошибка: {response.text}.')
                    return
                if time.time() - start_time > timeout:
                    bot.send_message(message.chat.id, 'Ошибка: превышено время ожидания.')
                    return
                time.sleep(2)

        @bot.message_handler(commands=[self.commands[1]])
        def create_custom_link(message: types.Message):
            '''Функция создания простой ссылки со своим названием'''
            args = message.text.split()
            if len(args) < 3:
                bot.send_message(message.chat.id,
                f'Используйте: /{self.commands[1]} <URL> <Кастомное имя>')
                return

            url = args[1]
            custom_name = args[2]

            api_url = f'https://ulvis.net/api.php?url={url}&custom={custom_name}&private=1'
            start_time = time.time()
            timeout = 30

            while True:
                response = fetch_url(api_url)
                if response and response.status_code == 200:
                    bot.send_message(message.chat.id, f'Ответ от сервера: {response.text}')
                    return
                if response:
                    bot.send_message(message.chat.id, f'Ошибка: {response.text}.')
                    return
                if time.time() - start_time > timeout:
                    bot.send_message(message.chat.id, 'Ошибка: превышено время ожидания.')
                    return
                time.sleep(2)
