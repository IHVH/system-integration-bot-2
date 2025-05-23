"""Module implementation of the Steam API fetcher bot functions."""

import os
import logging
from typing import List
import requests
import telebot
from telebot import types
from telebot.callback_data import CallbackData
from bot_func_abc import AtomicBotFunctionABC


class SteamBotFunction(AtomicBotFunctionABC):
    """Bot function for fetching Steam popular tags, tag-based games, and player stats."""

    commands: List[str] = ["steam", "steam stats", "steam tag"]
    authors: List[str] = ["Semsemch"]
    about: str = "Получение данных из Steam API!"
    description: str = """Функции для получения популярных тегов, игр по тегу и статистики игроков.
    Примеры вызова:
    /steam — показать 10 популярных тегов.
    /steam tag <tagid> — показать игры по тегу.
    /steam stats — показать статистику пользователей."""
    state: bool = True

    bot: telebot.TeleBot
    keyboard_factory: CallbackData

    def set_handlers(self, bot: telebot.TeleBot):
        self.bot = bot
        self.keyboard_factory = CallbackData("steam_button", prefix=self.commands[0])

        @bot.message_handler(commands=self.commands)
        def steam_message_handler(message: types.Message):
            try:
                args = message.text.strip().split()
                if len(args) == 1:
                    self.__send_popular_tags(message.chat.id)
                elif args[1] == "tag" and len(args) == 3:
                    self.__send_games_by_tag(message.chat.id, args[2])
                elif args[1] == "stats":
                    self.__send_player_stats(message.chat.id)
                else:
                    bot.send_message(chat_id=message.chat.id, text="Неверная команда.")
            except Exception as e:
                logging.exception(e)
                bot.send_message(chat_id=message.chat.id, text=f"Ошибка: {e}")

    def __send_popular_tags(self, chat_id: int):
        url = "https://store.steampowered.com/tagdata/populartags/english"
        response = requests.get(url)
        if response.ok:
            tags = response.json()[:10]
            tag_texts = [f"{tag['name']} (id: {tag['tagid']})" for tag in tags]
            self.bot.send_message(chat_id=chat_id, text="Популярные теги:\n" + "\n".join(tag_texts))
        else:
            self.bot.send_message(chat_id=chat_id, text="Не удалось получить теги.")

    def __send_games_by_tag(self, chat_id: int, tag_id: str):
        url = f"https://store.steampowered.com/search/results/?tags={tag_id}&category1=998&ndl=1&json=1"
        response = requests.get(url)
        if response.ok:
            data = response.json()
            items = data.get("items", [])
            if items:
                messages = [f"{item['name']}\n{item['logo']}" for item in items[:5]]
                self.bot.send_message(chat_id=chat_id, text="Игры по тегу:\n"+"\n\n".join(messages))
            else:
                self.bot.send_message(chat_id=chat_id, text="Нет игр для данного тега.")
        else:
            self.bot.send_message(chat_id=chat_id, text="Ошибка при получении игр по тегу.")

    def __send_player_stats(self, chat_id: int):
        url = "https://www.valvesoftware.com/about/stats"
        response = requests.get(url)
        if response.ok:
            data = response.json()
            users_online = data.get("users_online", "Неизвестно")
            users_ingame = data.get("users_ingame", "Неизвестно")
            self.bot.send_message(chat_id=chat_id, text=f"Игроков онлайн: {users_online}\nИграют сейчас: {users_ingame}")
        else:
            self.bot.send_message(chat_id=chat_id, text="Ошибка при получении статистики игроков.")
