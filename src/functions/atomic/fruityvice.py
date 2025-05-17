<<<<<<< HEAD
"""Модуль для работы с API фруктов через Telegram бота."""
import logging
from typing import List
import telebot
import requests
from telebot import types
from telebot.callback_data import CallbackData
from bot_func_abc import AtomicBotFunctionABC

class AtomicFruitBotFunction(AtomicBotFunctionABC):
    """Реализация функции бота для работы с вывода списка фруктов и
       проверки состава фрукта по выбору пользователя"""

    commands: List[str] = ["fruitbot"]
    authors: List[str] = ["Twinteko"]
    about: str = "Работа с базой данных фруктов"
    description: str = (
        "Доступные команды:\n"
        "/fruitbot - интерактивное меню для работы с фруктами.\n"
        "Позволяет получить список фруктов и подробную информацию о каждом.\n"
        "Источник данных: Fruityvice API, предоставляющий актуальную информацию о составе фруктов."
    )
    state: bool = True

    bot: telebot.TeleBot
    fruit_keyboard_factory: CallbackData

    def __init__(self):
        self.cache = {}
        self.api_url = "https://fruityvice.com/api/fruit"

    def set_handlers(self, bot: telebot.TeleBot):
        """a"""
        self.bot = bot
        self.fruit_keyboard_factory = CallbackData('fruit_action', prefix=self.commands[0])

        @bot.message_handler(commands=self.commands)
        def fruit_message_handler(message: types.Message):
            msg = "Выберите действие с фруктами:"
            bot.send_message(
                chat_id=message.chat.id,
                text=msg,
                reply_markup=self.__gen_markup()
            )

        @bot.callback_query_handler(func=None, config=self.fruit_keyboard_factory.filter())
        def fruit_keyboard_callback(call: types.CallbackQuery):
            callback_data: dict = self.fruit_keyboard_factory.parse(call.data)
            action = callback_data['fruit_action']

            if action == 'list':
                fruits = self.get_all_fruits()
                self.bot.send_message(call.message.chat.id, fruits)
            elif action == 'info':
                force_reply = types.ForceReply(selective=False)
                msg = self.bot.send_message(
                    call.message.chat.id,
                    "Введите название фрукта:",
                    reply_markup=force_reply
                )
                self.bot.register_next_step_handler(msg, self.__process_fruit_input)
            self.bot.answer_callback_query(call.id)

    def __gen_markup(self):
        markup = types.InlineKeyboardMarkup()
        markup.row_width = 2
        list_data = self.fruit_keyboard_factory.new(fruit_action="list")
        info_data = self.fruit_keyboard_factory.new(fruit_action="info")

        markup.add(
            types.InlineKeyboardButton("🍎 Список", callback_data=list_data),
            types.InlineKeyboardButton("📊 Информация", callback_data=info_data)
        )
        return markup

    def get_all_fruits(self) -> str:
        """Получить список всех фруктов"""
        try:
            response = requests.get(f"{self.api_url}/all", timeout=10)
            response.raise_for_status()
            fruits = response.json()
            fruit_list = "\n".join([f"• {fruit['name']}" for fruit in fruits])
            return f"🍍 Доступные фрукты:\n{fruit_list}\n\n(показано {len(fruits)})"
        except requests.exceptions.RequestException as e:
            logging.error("Fruit API error: %s", str(e))
            return "⚠️ Ошибка при получении списка фруктов"

    def get_fruit_info(self, name: str) -> str:
        """Получить информацию о конкретном фрукте"""
        try:
            response = requests.get(f"{self.api_url}/{name.lower()}", timeout=10)
            response.raise_for_status()
            fruit = response.json()

            nutritions = fruit.get('nutritions', {})
            info = (
                f"🌳 {fruit['name']}\n"
                f"Семейство: {fruit['family']}\n"
                f"Калории: {nutritions.get('calories', 'N/A')}\n"
                f"Белки: {nutritions.get('protein', 'N/A')}г\n"
                f"Жиры: {nutritions.get('fat', 'N/A')}г\n"
                f"Углеводы: {nutritions.get('carbohydrates', 'N/A')}г\n"
                f"Сахар: {nutritions.get('sugar', 'N/A')}г"
            )
            return info
        except requests.HTTPError:
            return f"❌ Фрукт '{name}' не найден"
        except requests.exceptions.RequestException as e:
            logging.error("Fruit info error: %s", str(e))
            return "⚠️ Ошибка при получении данных"

    def __process_fruit_input(self, message: types.Message):
        try:
            fruit_name = message.text.strip()
            info = self.get_fruit_info(fruit_name)
            self.bot.send_message(
                chat_id=message.chat.id,
                text=info,
                parse_mode='Markdown'
            )
        except (AttributeError, ValueError) as e:
            logging.error("Processing error: %s", str(e))
            self.bot.send_message(
                chat_id=message.chat.id,
                text=f"⚠️ Ошибка обработки запроса: {str(e)}"
            )
=======
"""Модуль для работы с API фруктов через Telegram бота."""
import logging
from typing import List
import telebot
import requests
from telebot import types
from telebot.callback_data import CallbackData
from bot_func_abc import AtomicBotFunctionABC

class AtomicFruitBotFunction(AtomicBotFunctionABC):
    """Реализация функции бота для работы с вывода списка фруктов и
       проверки состава фрукта по выбору пользователя"""

    commands: List[str] = ["fruitbot"]
    authors: List[str] = ["Twinteko"]
    about: str = "Работа с базой данных фруктов"
    description: str = (
        "Доступные команды:\n"
        "/fruitbot - интерактивное меню для работы с фруктами.\n"
        "Позволяет получить список фруктов и подробную информацию о каждом.\n"
        "Источник данных: Fruityvice API, предоставляющий актуальную информацию о составе фруктов."
    )
    state: bool = True

    bot: telebot.TeleBot
    fruit_keyboard_factory: CallbackData

    def __init__(self):
        self.cache = {}
        self.api_url = "https://fruityvice.com/api/fruit"

    def set_handlers(self, bot: telebot.TeleBot):
        """a"""
        self.bot = bot
        self.fruit_keyboard_factory = CallbackData('fruit_action', prefix=self.commands[0])

        @bot.message_handler(commands=self.commands)
        def fruit_message_handler(message: types.Message):
            msg = "Выберите действие с фруктами:"
            bot.send_message(
                chat_id=message.chat.id,
                text=msg,
                reply_markup=self.__gen_markup()
            )

        @bot.callback_query_handler(func=None, config=self.fruit_keyboard_factory.filter())
        def fruit_keyboard_callback(call: types.CallbackQuery):
            callback_data: dict = self.fruit_keyboard_factory.parse(call.data)
            action = callback_data['fruit_action']

            if action == 'list':
                fruits = self.get_all_fruits()
                self.bot.send_message(call.message.chat.id, fruits)
            elif action == 'info':
                force_reply = types.ForceReply(selective=False)
                msg = self.bot.send_message(
                    call.message.chat.id,
                    "Введите название фрукта:",
                    reply_markup=force_reply
                )
                self.bot.register_next_step_handler(msg, self.__process_fruit_input)
            self.bot.answer_callback_query(call.id)

    def __gen_markup(self):
        markup = types.InlineKeyboardMarkup()
        markup.row_width = 2
        list_data = self.fruit_keyboard_factory.new(fruit_action="list")
        info_data = self.fruit_keyboard_factory.new(fruit_action="info")

        markup.add(
            types.InlineKeyboardButton("🍎 Список", callback_data=list_data),
            types.InlineKeyboardButton("📊 Информация", callback_data=info_data)
        )
        return markup

    def get_all_fruits(self) -> str:
        """Получить список всех фруктов"""
        try:
            response = requests.get(f"{self.api_url}/all", timeout=10)
            response.raise_for_status()
            fruits = response.json()
            fruit_list = "\n".join([f"• {fruit['name']}" for fruit in fruits])
            return f"🍍 Доступные фрукты:\n{fruit_list}\n\n(показано {len(fruits)})"
        except requests.exceptions.RequestException as e:
            logging.error("Fruit API error: %s", str(e))
            return "⚠️ Ошибка при получении списка фруктов"

    def get_fruit_info(self, name: str) -> str:
        """Получить информацию о конкретном фрукте"""
        try:
            response = requests.get(f"{self.api_url}/{name.lower()}", timeout=10)
            response.raise_for_status()
            fruit = response.json()

            nutritions = fruit.get('nutritions', {})
            info = (
                f"🌳 {fruit['name']}\n"
                f"Семейство: {fruit['family']}\n"
                f"Калории: {nutritions.get('calories', 'N/A')}\n"
                f"Белки: {nutritions.get('protein', 'N/A')}г\n"
                f"Жиры: {nutritions.get('fat', 'N/A')}г\n"
                f"Углеводы: {nutritions.get('carbohydrates', 'N/A')}г\n"
                f"Сахар: {nutritions.get('sugar', 'N/A')}г"
            )
            return info
        except requests.HTTPError:
            return f"❌ Фрукт '{name}' не найден"
        except requests.exceptions.RequestException as e:
            logging.error("Fruit info error: %s", str(e))
            return "⚠️ Ошибка при получении данных"

    def __process_fruit_input(self, message: types.Message):
        try:
            fruit_name = message.text.strip()
            info = self.get_fruit_info(fruit_name)
            self.bot.send_message(
                chat_id=message.chat.id,
                text=info,
                parse_mode='Markdown'
            )
        except (AttributeError, ValueError) as e:
            logging.error("Processing error: %s", str(e))
            self.bot.send_message(
                chat_id=message.chat.id,
                text=f"⚠️ Ошибка обработки запроса: {str(e)}"
            )
>>>>>>> cd8cb6737e2e5662ba2d973a3c3adf02c3523214
