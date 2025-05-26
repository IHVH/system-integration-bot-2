"""
Модуль для реализации функции бота для получения случайных шуток.
Использует Official Joke API.
"""

import logging
from typing import List, Dict, Any, Optional
import requests
import telebot
from telebot import types
from telebot.callback_data import CallbackData
from bot_func_abc import AtomicBotFunctionABC


class AtomicRandomJokeBotFunction(AtomicBotFunctionABC):
    """
    Модуль для получения случайных шуток различных типов.
    Поддерживает получение одной случайной шутки, шутки по ID,
    шутки по типу и нескольких случайных шуток.
    """

    commands = ["randomjoke", "joketype", "jokeid", "multijoke"]
    authors = ["IHVH"]  # Замените на ваш логин GitHub
    about = "Генератор случайных шуток!"
    description = """Команды:
                   /randomjoke - одна случайная шутка,
                   /joketype <тип> - шутка определенного типа,
                   /jokeid <id> - шутка по ID,
                   /multijoke <количество> - несколько случайных шуток (максимум 5).
                   """
    state = True
    BASE_URL = "https://official-joke-api.appspot.com"

    def __init__(self):
        self.bot = None
        self.joke_type_keyboard_factory = None

    def set_handlers(self, bot: telebot.TeleBot):
        """Set message handlers"""
        self.bot = bot
        self.joke_type_keyboard_factory = CallbackData('joke_type', prefix='joke')

        @bot.message_handler(commands=self.commands)
        def handle_commands(message: types.Message):
            cmd = message.text.split()[0][1:]
            if cmd == "randomjoke":
                self._send_random_joke(message)
            elif cmd == "joketype":
                self._handle_joke_type(message)
            elif cmd == "jokeid":
                self._handle_joke_id(message)
            elif cmd == "multijoke":
                self._handle_multi_joke(message)
        @bot.callback_query_handler(func=None, config=self.joke_type_keyboard_factory.filter())
        def joke_type_callback(call: types.CallbackQuery):
            callback_data = self.joke_type_keyboard_factory.parse(callback_data=call.data)
            joke_type = callback_data['joke_type']
            self._send_joke_by_type(call.message, joke_type)

    def _send_random_joke(self, message: types.Message):
        """Отправляет одну случайную шутку."""
        joke = self._get_random_joke()
        if joke:
            self._format_and_send_joke(message.chat.id, joke)
        else:
            self.bot.send_message(message.chat.id, "Не удалось получить шутку. Попробуйте позже.")

    def _handle_joke_type(self, message: types.Message):
        """Обрабатывает команду для получения шутки по типу."""
        args = message.text.split()
        if len(args) > 1:
            joke_type = args[1].lower()
            self._send_joke_by_type(message, joke_type)
        else:
            # Если тип не указан, показываем клавиатуру с доступными типами
            self._show_joke_types_keyboard(message)
    def _show_joke_types_keyboard(self, message: types.Message):
        """Показывает клавиатуру с доступными типами шуток."""
        try:
            joke_types = self._get_joke_types()
            if not joke_types:
                self.bot.send_message(message.chat.id,
                                      "Не удалось получить типы шуток. Попробуйте позже.")
                return
            markup = types.InlineKeyboardMarkup(row_width=2)
            buttons = []
            for joke_type in joke_types:
                callback_data = self.joke_type_keyboard_factory.new(joke_type=joke_type)
                buttons.append(types.InlineKeyboardButton(text=joke_type.capitalize(),
                                                        callback_data=callback_data))
            markup.add(*buttons)
            self.bot.send_message(message.chat.id, "Выберите тип шутки:", reply_markup=markup)
        except (AttributeError, ValueError) as e:
            logging.error("Error processing joke types data: %s", e)
            self.bot.send_message(message.chat.id,
                                  "Произошла ошибка при обработке типов шуток.")
        except KeyError as e:
            logging.error("Missing key in joke type data: %s", e)
            self.bot.send_message(message.chat.id,
                                  "Произошла ошибка в структуре данных типов шуток.")

    def _send_joke_by_type(self, message: types.Message, joke_type: str):
        """Отправляет шутку определенного типа."""
        joke = self._get_joke_by_type(joke_type)
        if joke:
            self._format_and_send_joke(message.chat.id, joke)
        else:
            self.bot.send_message(message.chat.id,
                                f"Не удалось получить шутку типа '{joke_type}'. "
                                f"Проверьте правильность типа или попробуйте позже.")

    def _handle_joke_id(self, message: types.Message):
        """Обрабатывает команду для получения шутки по ID."""
        try:
            joke_id = int(message.text.split()[1])
            joke = self._get_joke_by_id(joke_id)
            if joke:
                self._format_and_send_joke(message.chat.id, joke)
            else:
                self.bot.send_message(message.chat.id, f"Шутка с ID {joke_id} не найдена.")
        except (IndexError, ValueError):
            self.bot.send_message(message.chat.id, "Использование: /jokeid <число>")

    def _handle_multi_joke(self, message: types.Message):
        """Обрабатывает команду для получения нескольких случайных шуток."""
        try:
            count = int(message.text.split()[1])
            if 1 <= count <= 5:
                jokes = self._get_multiple_jokes(count)
                if jokes:
                    for joke in jokes:
                        self._format_and_send_joke(message.chat.id, joke)
                else:
                    self.bot.send_message(message.chat.id, "Не удалось получить шутки.")
            else:
                self.bot.send_message(message.chat.id, "Пожалуйста, укажите число от 1 до 5.")
        except (IndexError, ValueError):
            self.bot.send_message(message.chat.id, "Использование: /multijoke <число от 1 до 5>")

    def _format_and_send_joke(self, chat_id: int, joke: Dict[str, Any]):
        """Форматирует и отправляет шутку в чат."""
        joke_text = f"*{joke.get('setup', '')}*\n\n{joke.get('punchline', '')}"
        joke_type = joke.get('type', 'unknown').capitalize()
        joke_id = joke.get('id', 'unknown')
        # Добавляем информацию о типе и ID шутки
        joke_info = f"\n\nТип шутки: {joke_type}\nID шутки: {joke_id}"
        self.bot.send_message(chat_id, joke_text + joke_info, parse_mode='Markdown')

    def _get_random_joke(self) -> Optional[Dict[str, Any]]:
        """Получает одну случайную шутку."""
        try:
            response = requests.get(f"{self.BASE_URL}/random_joke", timeout=5)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, ValueError) as ex:
            logging.warning("Failed to fetch random joke: %s", ex)
            return None

    def _get_joke_types(self) -> List[str]:
        """Получает список доступных типов шуток."""
        try:
            response = requests.get(f"{self.BASE_URL}/types", timeout=5)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, ValueError) as ex:
            logging.warning("Failed to fetch joke types: %s", ex)
            return []

    def _get_joke_by_type(self, joke_type: str) -> Optional[Dict[str, Any]]:
        """Получает случайную шутку указанного типа."""
        try:
            response = requests.get(f"{self.BASE_URL}/jokes/{joke_type}/random", timeout=5)
            response.raise_for_status()
            jokes = response.json()
            # API возвращает список из одной шутки
            return jokes[0] if jokes else None
        except (requests.exceptions.RequestException, ValueError, IndexError) as ex:
            logging.warning("Failed to fetch joke by type '%s': %s", joke_type, ex)
            return None

    def _get_joke_by_id(self, joke_id: int) -> Optional[Dict[str, Any]]:
        """Получает шутку по ID."""
        try:
            response = requests.get(f"{self.BASE_URL}/jokes/{joke_id}", timeout=5)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, ValueError) as ex:
            logging.warning("Failed to fetch joke by ID %s: %s", joke_id, ex)
            return None

    def _get_multiple_jokes(self, count: int) -> List[Dict[str, Any]]:
        """Получает несколько случайных шуток."""
        try:
            if count <= 0:
                return []
            if count == 10:
                # Существует отдельный эндпоинт для 10 шуток
                response = requests.get(f"{self.BASE_URL}/random_ten", timeout=5)
            else:
                # Для произвольного количества шуток
                response = requests.get(f"{self.BASE_URL}/jokes/random/{count}", timeout=5)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, ValueError) as ex:
            logging.warning("Failed to fetch %s jokes: %s", count, ex)
            return []
