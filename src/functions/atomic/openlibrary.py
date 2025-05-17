"""Module implementation of the atomic function of the telegram bot. Example of implementation."""

from typing import List
import telebot
from telebot import types
import requests
from bot_func_abc import AtomicBotFunctionABC

class OpenLibraryBotFunction(AtomicBotFunctionABC):
    """Open Library API"""

    commands: List[str] = ["find_book", "find_author"]
    authors: List[str] = ["311421"]
    state: bool = True
    about: str = "Интеграция с Open Library"
    description: str = """Реализация поиска по книге и автору в API Open Library.
    Ищет по книге. И по Автору тоже ищет. /find_book для поиска по книге. 
    /find_author ищет по автору."""

    bot: telebot.TeleBot

    def set_handlers(self, bot: telebot.TeleBot):
        """Модуль хэндлеров для обращения к Open Library"""
        self.bot = bot

        def __find_book_by_name(message):
            name = "+".join(message.text.replace(" ", "+").split("+")[1:])
            req = ("https://openlibrary.org/search.json?q=" + name +
                   "&page=1&limit=1&mode=everything")
            r = requests.get(url=req, timeout=5)
            bookdata = r.json()
            reply = (f"Автор: {bookdata['docs'][0]['author_name'][0]}, \nГод издания: "
                     f"{bookdata['docs'][0]['first_publish_year']}, "
                     f"\nСреднее количество страниц: "
                     f"{bookdata['docs'][0]['number_of_pages_median']}\n")
            self.bot.send_photo(caption=reply, photo="https://covers.openlibrary.org/b/OLID/" + str(
                dict(bookdata)["docs"][0]["cover_edition_key"]) + "-L.jpg", chat_id=message.chat.id)

        def __find_book_by_author(message):
            name = "+".join(message.text.replace(" ", "+").split("+")[1:])
            print(name)
            req = ("https://openlibrary.org/search/authors.json?q=" +
                   name + "&page=1&limit=3&mode=everything")
            r = requests.get(url=req, timeout=5)
            bookdata = r.json()
            print(bookdata)
            r = requests.get(
                f"https://openlibrary.org/authors/{str(dict(bookdata)['docs'][0]['key'])}/"
                f"works.json?limit=3", timeout=5)
            print(r.json())
            reply = f"Автор: {bookdata['docs'][0]['name']}\nПопулярные работы:\n"
            c = 1
            for e in r.json()["entries"]:
                reply += str(c) + ') ' + e["title"] + '\n'
                c += 1
            bot.send_photo(caption=reply, photo="https://covers.openlibrary.org/a/OLID/" + str(
                dict(bookdata)["docs"][0]["key"]) + "-L.jpg", chat_id=message.chat.id)

        @bot.message_handler(commands=[self.commands[0]])
        def find_book_by_name(message: types.Message):
            """Поиск по книге"""
            __find_book_by_name(message)

        @bot.message_handler(commands=[self.commands[1]])
        def find_book_by_author(message: types.Message):
            """Поиск по автору"""
            __find_book_by_author(message)
