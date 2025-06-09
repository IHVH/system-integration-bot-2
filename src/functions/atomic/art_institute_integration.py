"""Module implementation of the Art Institute of Chicago API fetcher bot functions."""

import logging
from typing import List
import requests
import telebot
from telebot import types
from telebot.callback_data import CallbackData
from src.bot_func_abc import AtomicBotFunctionABC


class ArtBotFunction(AtomicBotFunctionABC):
    """Bot function for fetching artworks, details by ID,
     and search from Art Institute of Chicago API."""

    commands: List[str] = ["art"]
    authors: List[str] = ["makogooon"]
    about: str = "Работы из Art Institute"
    description: str = """Функция бота для получения списка artworks, информации по ID и поиска.
    Примеры вызова:
    /art — получить список работ.
    /art id <artwork_id> — получить подробности по ID.
    /art search <запрос> — выполнить поиск по работам."""
    state: bool = True

    bot: telebot.TeleBot
    keyboard_factory: CallbackData

    def set_handlers(self, bot: telebot.TeleBot):
        """Set Telegram bot handlers."""
        self.bot = bot
        self.keyboard_factory = CallbackData("art_button", prefix=self.commands[0])

        @bot.message_handler(commands=self.commands)
        def art_message_handler(message: types.Message):
            try:
                args = message.text.strip().split()
                if len(args) == 1:
                    self.__send_artworks(message.chat.id)
                elif args[1] == "id" and len(args) == 3:
                    self.__send_artwork_by_id(message.chat.id, args[2])
                elif args[1] == "search" and len(args) >= 3:
                    query = " ".join(args[2:])
                    self.__search_artworks(message.chat.id, query)
                else:
                    bot.send_message(chat_id=message.chat.id, text="Неверная команда.")
            except requests.RequestException as e:
                logging.exception(e)
                bot.send_message(chat_id=message.chat.id, text=f"Ошибка: {e}")

    def __send_artworks(self, chat_id: int):
        url = "https://api.artic.edu/api/v1/artworks"
        response = requests.get(url, timeout=10)
        if response.ok:
            data = response.json()
            artworks = data.get("data", [])[:5]
            messages = [f"{art['title']} (ID: {art['id']})" for art in artworks]
            self.bot.send_message(chat_id=chat_id, text="Список работ:\n" + "\n".join(messages))
        else:
            self.bot.send_message(chat_id=chat_id, text="Не удалось получить список работ.")

    def __send_artwork_by_id(self, chat_id: int, artwork_id: str):
        url = f"https://api.artic.edu/api/v1/artworks/{artwork_id}"
        response = requests.get(url, timeout=10)
        if response.ok:
            data = response.json().get("data", {})
            title = data.get("title", "Без названия")
            artist = data.get("artist_display",
                              "Неизвестный автор")
            date = data.get("date_display", "Без даты")
            self.bot.send_message(chat_id=chat_id, text=f"Название: "
                                                        f"{title}\nАвтор: {artist}\nДата: {date}")
        else:
            self.bot.send_message(chat_id=chat_id,
                                  text="Работа не найдена.")

    def __search_artworks(self, chat_id: int, query: str):
        url = f"https://api.artic.edu/api/v1/artworks/search?q={query}"
        response = requests.get(url, timeout=10)
        if response.ok:
            data = response.json()
            results = data.get("data",
                               [])[:5]
            if results:
                messages = [f"{art['title']} (ID: {art['id']})" for art in results]
                self.bot.send_message(chat_id=chat_id, text="Результаты"
                                                            " поиска:\n" + "\n".join(messages))
            else:
                self.bot.send_message(chat_id=chat_id, text="Ничего не найдено.")
        else:
            self.bot.send_message(chat_id=chat_id, text="Ошибка при поиске.")
