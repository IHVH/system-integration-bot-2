"""Модуль для работы с API шуток через Telegram бота."""
import logging
from typing import List
import telebot
import requests
from telebot import types
from telebot.callback_data import CallbackData
from bot_func_abc import AtomicBotFunctionABC

class AtomicJokeBotFunction(AtomicBotFunctionABC):
    """Реализация функции бота для получения шуток из Official Joke API."""

    commands: List[str] = ["joke"]
    authors: List[str] = ["Ugolniy"]
    about: str = "Работа с API шуток"
    description: str = (
        "Доступные команды:\n"
        "/joke - интерактивное меню для работы со шутками.\n\n"
        "Возможности:\n"
        "• 🎲 Случайная шутка\n"
        "• 📚 10 случайных шуток\n"
        "• 🏷️ Шутка определённого типа (доступные типы загружаются из API)\n"
        "• 🔢 Шутка по ID\n"
        "Источник: Official Joke API"
    )
    state: bool = True

    bot: telebot.TeleBot
    callback_factory: CallbackData

    BASE_URL = "https://official-joke-api.appspot.com"

    def set_handlers(self, bot: telebot.TeleBot):
        """Регистрирует обработчики команд и callback-запросов."""
        self.bot = bot
        self.callback_factory = CallbackData('action', 'value', prefix=self.commands[0])

        @bot.message_handler(commands=self.commands)
        def joke_command_handler(message: types.Message):
            markup = self._generate_main_menu()
            bot.send_message(
                chat_id=message.chat.id,
                text="🃏 Выберите действие:",
                reply_markup=markup
            )

        @bot.callback_query_handler(func=None, config=self.callback_factory.filter())
        def callback_handler(call: types.CallbackQuery):
            data = self.callback_factory.parse(call.data)
            action = data['action']
            value = data['value']

            if action == 'random' and not value:
                self._send_random_joke(call.message.chat.id)
            elif action == 'random_ten' and not value:
                self._send_ten_random_jokes(call.message.chat.id)
            elif action == 'by_type' and not value:
                self._ask_for_type(call.message)
            elif action == 'type_selected' and value:
                self._send_joke_by_type(call.message.chat.id, joke_type=value)
            elif action == 'by_id' and not value:
                self._ask_for_id(call.message)
            elif action == 'id_submitted' and value:
                self._send_joke_by_id(call.message.chat.id, joke_id=value)
            else:
                self.bot.answer_callback_query(call.id, "⚠️ Неизвестное действие")
                return

            self.bot.answer_callback_query(call.id)

    def _generate_main_menu(self) -> types.InlineKeyboardMarkup:
        """Создаёт главное меню с кнопками выбора действий."""
        markup = types.InlineKeyboardMarkup(row_width=1)
        buttons = [
            ("🎲 Случайная шутка", "random", ""),
            ("📚 10 случайных шуток", "random_ten", ""),
            ("🏷️ Шутка по типу", "by_type", ""),
            ("🔢 Шутка по ID", "by_id", ""),
        ]
        for text, action, val in buttons:
            callback_data = self.callback_factory.new(action=action, value=val)
            markup.add(types.InlineKeyboardButton(text, callback_data=callback_data))
        return markup

    def _get_joke_types(self) -> List[str]:
        """Получает список доступных типов шуток из API."""
        try:
            resp = requests.get(f"{self.BASE_URL}/types", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return data
            return []
        except requests.exceptions.RequestException as e:
            logging.error("Failed to fetch joke types: %s", e)
            return []

    def _ask_for_type(self, message: types.Message):
        """Отправляет сообщение для выбора типа шутки, получая типы из API."""
        joke_types = self._get_joke_types()
        if not joke_types:

            joke_types = ["general", "programming", "knock-knock", "dad"]

        markup = types.InlineKeyboardMarkup(row_width=2)
        for t in joke_types:
            callback_data = self.callback_factory.new(action="type_selected", value=t)
            markup.add(types.InlineKeyboardButton(t.capitalize(), callback_data=callback_data))
        self.bot.send_message(
            chat_id=message.chat.id,
            text="Выберите тип шутки:",
            reply_markup=markup
        )

    def _ask_for_id(self, message: types.Message):
        """Запрашивает у пользователя ID шутки."""
        msg = self.bot.send_message(
            chat_id=message.chat.id,
            text="🔢 Введите числовой ID шутки (например, 5):",
            reply_markup=types.ForceReply(selective=False)
        )
        self.bot.register_next_step_handler(msg, self._process_id_input)

    def _process_id_input(self, message: types.Message):
        """Обрабатывает введённый ID и отправляет шутку."""
        try:
            joke_id = int(message.text.strip())
            self._send_joke_by_id(message.chat.id, joke_id)
        except ValueError:
            self.bot.send_message(
                chat_id=message.chat.id,
                text="❌ ID должен быть целым числом. Попробуйте ещё раз через меню /joke."
            )

    def _fetch_joke(self, endpoint: str):
        """Выполняет GET-запрос к API и возвращает JSON-ответ."""
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            logging.error("Joke API error: %s", e)
            return None

    def _send_random_joke(self, chat_id: int):
        """Отправляет одну случайную шутку."""
        data = self._fetch_joke("/random_joke")
        if data and isinstance(data, dict):
            text = f"🎭 *{data['setup']}*\n\n👉 *{data['punchline']}*"
            self.bot.send_message(chat_id, text, parse_mode='Markdown')
        else:
            self.bot.send_message(chat_id, "⚠️ Не удалось получить случайную шутку.")

    def _send_ten_random_jokes(self, chat_id: int):
        """Отправляет 10 случайных шуток."""
        data = self._fetch_joke("/random_ten")
        if data and isinstance(data, list):
            if not data:
                self.bot.send_message(chat_id, "😕 Шутки не найдены.")
                return
            parts = []
            for idx, joke in enumerate(data, 1):
                parts.append(f"{idx}. {joke['setup']} — *{joke['punchline']}*")
            full_text = "📚 *10 случайных шуток:*\n\n" + "\n\n".join(parts)
            if len(full_text) > 4096:
                for i in range(0, len(parts), 5):
                    chunk = "📚 *Случайные шутки:*\n\n" + "\n\n".join(parts[i:i+5])
                    self.bot.send_message(chat_id, chunk, parse_mode='Markdown')
            else:
                self.bot.send_message(chat_id, full_text, parse_mode='Markdown')
        else:
            self.bot.send_message(chat_id, "⚠️ Не удалось получить 10 случайных шуток.")

    def _send_joke_by_type(self, chat_id: int, joke_type: str):
        """Отправляет случайную шутку указанного типа."""
        data = self._fetch_joke(f"/jokes/{joke_type}/random")
        if data and isinstance(data, list) and len(data) > 0:
            joke = data[0]
            text = f"🏷️ *Тип: {joke_type}*\n\n🎭 {joke['setup']}\n\n👉 *{joke['punchline']}*"
            self.bot.send_message(chat_id, text, parse_mode='Markdown')
        else:
            self.bot.send_message(chat_id, f"⚠️ Не удалось найти шутку типа '{joke_type}'.")

    def _send_joke_by_id(self, chat_id: int, joke_id: int):
        """Отправляет шутку по указанному ID."""
        data = self._fetch_joke(f"/jokes/{joke_id}")
        if data and isinstance(data, dict) and 'setup' in data and 'punchline' in data:
            text = f"🔢 *ID: {joke_id}*\n\n🎭 {data['setup']}\n\n👉 *{data['punchline']}*"
            self.bot.send_message(chat_id, text, parse_mode='Markdown')
        else:
            self.bot.send_message(chat_id, f"❌ Шутка с ID {joke_id} не найдена.")
