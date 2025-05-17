"""Module implementation of the atomic function of the telegram bot. Game of Thrones
 API integration."""

import logging
from typing import List

import requests
import telebot
from telebot import types
from bot_func_abc import AtomicBotFunctionABC



class IceAndFireFunction(AtomicBotFunctionABC):
    """Бот-функция для работы с API Game of Thrones."""
    commands: List[str] = ["got"]
    authors: List[str] = ["Kirill792905"]
    about: str = "Персонажи Game of Thrones (Ice and Fire API)"
    description: str = (
        "/got — получить список персонажей"
    )
    state: bool = True

    BASE_URL = "https://anapioficeandfire.com/api/"
    TIMEOUT = 15
    PAGE_SIZE = 10

    bot: telebot.TeleBot

    def set_handlers(self, bot: telebot.TeleBot):
        """Устанавливает хендлеры команд и колбэков."""
        self.bot = bot

        @bot.message_handler(commands=['got'])
        def list_characters(message: types.Message):
            self.send_characters_page(message.chat.id, page=1)

        @bot.callback_query_handler(func=lambda call: call.data and call.data.startswith("got_"))
        def callback_handler(call: types.CallbackQuery):
            data = call.data.split("_")
            action = data[1]
            if action == "page":
                try:
                    page = int(data[2])
                except (IndexError, ValueError):
                    page = 1
                self.send_characters_page(call.message.chat.id, page=page, call=call)
            elif action == "char":
                try:
                    char_id = data[2]
                except IndexError:
                    self.bot.send_message(call.message.chat.id, "Некорректные данные для запроса.")
                    return
                self.show_character(call, char_id)

    def send_characters_page(self, chat_id: int, page: int = 1, call=None):
        """ Отправляет список персонажей с кнопками выбора и пагинацией. """
        try:
            response = requests.get(
                f"{self.BASE_URL}characters?page={page}&pageSize={self.PAGE_SIZE}",
                timeout=self.TIMEOUT
            )
            response.raise_for_status()
            characters = response.json()
        except requests.RequestException:
            logging.exception("Ошибка при получении списка персонажей")
            if call:
                self.bot.answer_callback_query(call.id, "Ошибка при получении данных.")
            else:
                self.bot.send_message(chat_id, "Произошла ошибка"
                                               " при получении списка персонажей.")
            return

        markup = types.InlineKeyboardMarkup(row_width=2)
        for char in characters:
            name = char.get("name") or (char.get("aliases")[0] if char.get("aliases")
                                        else "(Без имени)")
            url = char.get("url")
            if url:
                char_id = url.split("/")[-1]
                callback_data = f"got_char_{char_id}"
                button = types.InlineKeyboardButton(text=name, callback_data=callback_data)
                markup.add(button)

        nav_buttons = []
        if page > 1:
            nav_buttons.append(
                types.InlineKeyboardButton(
                    text="<-- Предыдущая",
                    callback_data=f"got_page_{page - 1}"
                )
            )
        if len(characters) == self.PAGE_SIZE:
            nav_buttons.append(
                types.InlineKeyboardButton(
                    text="Следующая -->",
                    callback_data=f"got_page_{page + 1}"
                )
            )
        if nav_buttons:
            markup.row(*nav_buttons)

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
        """ Показывает информацию о выбранном персонаже. """

        url = f"{self.BASE_URL}characters/{char_id}"
        try:
            response = requests.get(url, timeout=self.TIMEOUT)
            response.raise_for_status()
            character = response.json()
        except requests.RequestException:
            logging.exception("Ошибка при получении информации о персонаже")
            self.bot.send_message(call.message.chat.id, "Произошла ошибка"
                                                        " при получении информации о персонаже.")
            return

        info = [
            f"Name: {character.get('name') or '(Без имени)'}",
            f"Gender: {character.get('gender') or '—'}",
            f"Culture: {character.get('culture') or '—'}",
            f"Born: {character.get('born') or '—'}",
            f"Died: {character.get('died') or '—'}",
            f"Titles: {', '.join(character.get('titles') or []) or '—'}",
            f"Aliases: {', '.join(character.get('aliases') or []) or '—'}",
            f"URL: {url}"
        ]
        self.bot.send_message(call.message.chat.id, "\n".join(info))
        self.bot.answer_callback_query(call.id)
