"""Telegram Bot for Top 5 Richest People."""
import random
import telebot
import requests
from typing import List
from bs4 import BeautifulSoup as a
from bot_func_abc import AtomicBotFunctionABC

class RichestPeopleAPIIntegration(AtomicBotFunctionABC):
    """Реализация функции бота для получения анекдота."""

    commands: List[str] = ["anekdot"]
    authors: List[str] = ["Garik205"]
    about: str = "Хотите посмеяться?"
    description: str = """Этот бот предназначен для получения различных анекдотов."""
    state: bool = True
    bot: telebot.TeleBot
    
    def __init__(self):
        self.app_part = "anekdot_key_button"
        self.button_data = "anekdot"

    def set_handlers(self, bot: telebot.TeleBot):
        """Set message handlers""" 
        my_url = 'https://www.anekdot.ru/last/good/'

        def parser(url):
            r =requests.get(url)
            soup = a(r.text, 'html.parser')
            anekdots = soup.find_all('div', class_='text')
            return [c.text for c in anekdots]

        list_of_jokes = parser(my_url)
        random.shuffle(list_of_jokes)
        self.bot = bot
        @self.bot.message_handler(commands=self.commands)

        def welcome(message):
            bot.send_message(message.chat.id, "Здравствуйте! Чтобы посмеяться, введите любую цифру:")

        @bot.message_handler(content_types=['text'])
        def jokes(message):
            if message.text.lower() in '123456789':
                bot.send_message(message.chat.id, list_of_jokes[0])
            del list_of_jokes[0]

        bot.polling()