"""Module implementation of the atomic function of the telegram bot.
Star Wars API integration."""

import logging
from typing import List

import requests
import telebot
from telebot import types
from telebot.callback_data import CallbackData
from bot_func_abc import AtomicBotFunctionABC


class StarWarsFunction(AtomicBotFunctionABC):
    """Бот-функция для работы с API Star Wars."""

    commands: List[str] = ["starwars"]
    authors: List[str] = ["metronom-afk"]
    about: str = "Персонажи Star Wars"
    description: str = (
        "/starwars — получить список персонажей из вселенной Star Wars с возможностью "
        "просматривать подробную информацию по каждому из них через кнопки Telegram."
    )
    state: bool = True

    BASE_URL = "https://www.swapi.tech/api/"
    TIMEOUT = 15
    PAGE_SIZE = 10

    bot: telebot.TeleBot
    characters_callback_factory: CallbackData

    def set_handlers(self, bot: telebot.TeleBot):
        """Устанавливает хендлеры команд и колбэков."""
        self.bot = bot
        self.characters_callback_factory = CallbackData('action', 'value', prefix=self.commands[0])

        @bot.message_handler(commands=self.commands)
        def list_characters(message: types.Message):
            self.send_characters_page(message.chat.id, page=1)

        @bot.callback_query_handler(func=None, config=self.characters_callback_factory.filter())
        def callback_handler(call: types.CallbackQuery):
            data = self.characters_callback_factory.parse(call.data)
            action = data['action']
            value = data['value']

            if action == "page":
                try:
                    page = int(value)
                except ValueError:
                    page = 1
                self.send_characters_page(call.message.chat.id, page=page, call=call)
            elif action == "char":
                self.show_character(call, char_id=value)

    def build_characters_markup(self, characters, page):
        """Создает и возвращает inline-разметку с персонажами и кнопками пагинации."""
        markup = types.InlineKeyboardMarkup(row_width=2)

        for char in characters:
            name = char.get("name") or "(Без имени)"
            uid = char.get("uid")
            if uid:
                callback_data = self.characters_callback_factory.new(action="char", value=uid)
                markup.add(types.InlineKeyboardButton(text=name, callback_data=callback_data))

        nav_buttons = []
        if page > 1:
            prev_cb = self.characters_callback_factory.new(action="page",
                                                           value=str(page - 1))
            nav_buttons.append(types.InlineKeyboardButton(text="<-- Предыдущая",
                                                          callback_data=prev_cb))

        # SWAPI возвращает общее количество персонажей в поле 'total_records'
        if len(characters) == self.PAGE_SIZE:
            next_cb = self.characters_callback_factory.new(action="page",
                                                           value=str(page + 1))
            nav_buttons.append(types.InlineKeyboardButton(text="Следующая -->",
                                                          callback_data=next_cb))
        if nav_buttons:
            markup.row(*nav_buttons)

        return markup

    def send_characters_page(self, chat_id: int, page: int = 1, call=None):
        """Отправляет список персонажей с кнопками выбора и пагинацией."""
        try:
            response = requests.get(
                f"{self.BASE_URL}people?page={page}&limit={self.PAGE_SIZE}",
                timeout=self.TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            characters = data.get("results", [])
        except requests.RequestException:
            logging.exception("Ошибка при получении списка персонажей")
            if call:
                self.bot.answer_callback_query(call.id, "Ошибка при получении данных.")
            else:
                self.bot.send_message(chat_id, "Произошла ошибка при получении списка персонажей.")
            return

        markup = self.build_characters_markup(characters, page)
        text = f"Страница {page}. Выберите персонажа:"

        if call:
            self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=markup
            )
            self.bot.answer_callback_query(call.id)
        else:
            self.bot.send_message(chat_id, text, reply_markup=markup)

    def show_character(self, call: types.CallbackQuery, char_id: str):
        """Показывает информацию о выбранном персонаже."""
        url = f"{self.BASE_URL}people/{char_id}"
        try:
            response = requests.get(url, timeout=self.TIMEOUT)
            response.raise_for_status()
            data = response.json()
            character = data.get("result", {}).get("properties", {})
        except requests.RequestException:
            logging.exception("Ошибка при получении информации о персонаже")
            self.bot.send_message(call.message.chat.id,
                                  "Произошла ошибка при получении информации о персонаже.")
            return

        info = [
            f"Name: {character.get('name') or '(Без имени)'}",
            f"Height: {character.get('height') or '—'}",
            f"Mass: {character.get('mass') or '—'}",
            f"Hair Color: {character.get('hair_color') or '—'}",
            f"Skin Color: {character.get('skin_color') or '—'}",
            f"Eye Color: {character.get('eye_color') or '—'}",
            f"Birth Year: {character.get('birth_year') or '—'}",
            f"Gender: {character.get('gender') or '—'}",
            f"URL: {url}"
        ]
        self.bot.send_message(call.message.chat.id, "\n".join(info))
        self.bot.answer_callback_query(call.id)
