"""
Модуль для интеграции с API CheapShark и реализации функциональности поиска игровых сделок.

"""
import logging
from typing import List
import requests
from telebot import TeleBot, types
from telebot.callback_data import CallbackData
from bot_func_abc import AtomicBotFunctionABC

class GameDealsFunction(AtomicBotFunctionABC):
    """Функция для поиска игровых сделок с использованием CheapShark API."""

    commands: List[str] = ["search_deals", "deals"]
    authors: List[str] = ["VITAMINkaGG"]
    about: str = "Поиск выгодных игр"
    description: str = """
        Функция позволяет искать игровые предложения через API CheapShark.
        Используйте /search_deals для запуска. Доступны фильтры:
        - По названию игры
        - По максимальной цене
    """
    state: bool = True

    bot: TeleBot
    search_keyboard_factory: CallbackData

    def set_handlers(self, bot: TeleBot):
        self.bot = bot
        self.search_keyboard_factory = CallbackData('search', prefix=self.commands[0])

        @bot.message_handler(commands=self.commands)
        def search_deals_handler(message: types.Message):
            """Обработчик команды /search_deals."""
            keyboard = self.__generate_search_markup()
            bot.send_message(
                message.chat.id,
                "Выберите критерий поиска:",
                reply_markup=keyboard
            )

        @bot.callback_query_handler(func=None, config=self.search_keyboard_factory.filter())
        def search_callback_handler(call: types.CallbackQuery):
            """Обработчик выбора параметров поиска."""
            callback_data = self.search_keyboard_factory.parse(callback_data=call.data)
            search_mode = callback_data['search']

            match search_mode:
                case 'title':
                    bot.send_message(
                        call.message.chat.id,
                        "Введите название игры:",
                        reply_markup=types.ForceReply(selective=False)
                    )
                    bot.register_next_step_handler(call.message, self.__search_by_title)
                case 'price':
                    bot.send_message(
                        call.message.chat.id,
                        "Введите максимальную цену:",
                        reply_markup=types.ForceReply(selective=False)
                    )
                    bot.register_next_step_handler(call.message, self.__search_by_price)

    def __generate_search_markup(self):
        """Создаёт клавиатуру с выбором параметров поиска."""
        markup = types.InlineKeyboardMarkup()
        title_callback_data = self.search_keyboard_factory.new(search="title")
        price_callback_data = self.search_keyboard_factory.new(search="price")
        markup.add(
            types.InlineKeyboardButton("По названию", callback_data=title_callback_data),
            types.InlineKeyboardButton("По цене", callback_data=price_callback_data)
        )
        return markup

    def __search_by_title(self, message: types.Message):
        """Поиск сделок по названию игры."""
        title = message.text
        deals = self.__get_cheapshark_deals(title=title)
        self.__send_deals(message.chat.id, deals)

    def __search_by_price(self, message: types.Message):
        """Поиск сделок по максимальной цене."""
        try:
            max_price = float(message.text)
            deals = self.__get_cheapshark_deals(upper_price=max_price)
            self.__send_deals(message.chat.id, deals)
        except ValueError:
            self.bot.send_message(message.chat.id, "Пожалуйста, введите корректное число.")

    def __get_cheapshark_deals(self, store_id=None, upper_price=None, title=None):
        """Выполняет запрос к API CheapShark для получения списка сделок."""
        url = "https://www.cheapshark.com/api/1.0/deals"
        params = {}
        if store_id:
            params['storeID'] = store_id
        if upper_price:
            params['upperPrice'] = upper_price
        if title:
            params['title'] = title

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error("Ошибка при выполнении запроса: %s", e)
            return []


    def __send_deals(self, chat_id, deals):
        """Отправляет найденные сделки пользователю."""
        if not deals:
            self.bot.send_message(chat_id, "Не найдено никаких сделок.")
            return

        for deal in deals[:5]:  # Ограничиваем вывод первых 5 сделок
            self.bot.send_message(
                chat_id,
                f"Название: {deal['title']}\n"
                f"Цена: ${deal['salePrice']} (обычная: ${deal['normalPrice']})\n"
                f"Скидка: {deal['savings']}%\n"
                f"Ссылка: https://www.cheapshark.com/redirect?dealID={deal['dealID']}"
            )
