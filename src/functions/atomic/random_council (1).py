"""Atomic function that fetches and returns random advice from api.adviceslip.com."""

from typing import List
import logging
import requests
import telebot
from telebot import types
from telebot.callback_data import CallbackData
from bot_func_abc import AtomicBotFunctionABC


class AtomicAdviceBotFunction(AtomicBotFunctionABC):
    """Atomic function that returns random advice."""

    commands: List[str] = ["advice"]
    authors: List[str] = ["Stepa2281337225"]
    about: str = "Получить случайный совет"
    description: str = (
        "Функция отправляет случайный совет, используя API https://api.adviceslip.com. "
        "Пример использования: /advice — Получить один совет. "
        "Нажмите кнопку 'Еще совет', чтобы получить другой."
    )

    state: bool = True

    bot: telebot.TeleBot
    advice_keyboard_factory: CallbackData

    def set_handlers(self, bot: telebot.TeleBot):
        """Set message and callback handlers."""
        self.bot = bot
        self.advice_keyboard_factory = CallbackData("advice_btn", prefix=self.commands[0])

        @bot.message_handler(commands=self.commands)
        def advice_message_handler(message: types.Message):
            advice = self.__get_random_advice()
            bot.send_message(
                chat_id=message.chat.id,
                text=f"💡 Совет: {advice}",
                reply_markup=self.__gen_markup()
            )

        @bot.callback_query_handler(func=None, config=self.advice_keyboard_factory.filter())
        def advice_callback_handler(call: types.CallbackQuery):
            callback_data: dict = self.advice_keyboard_factory.parse(callback_data=call.data)
            btn_action = callback_data["advice_btn"]

            if btn_action == "more_advice":
                advice = self.__get_random_advice()
                self.bot.send_message(
                    chat_id=call.message.chat.id,
                    text=f"💡 Новый совет: {advice}",
                    reply_markup=self.__gen_markup()
                )
                bot.answer_callback_query(call.id, "Еще один совет!")

    def __get_random_advice(self) -> str:
        """Fetch random advice from the API."""
        try:
            response = requests.get("https://api.adviceslip.com/advice", timeout=5)
            response.raise_for_status()
            data = response.json()
            return data["slip"]["advice"]
        except requests.exceptions.RequestException as ex:
            logging.exception("Ошибка при получении совета: %s", ex)
            return "Не удалось получить совет. Попробуйте позже."

    def __gen_markup(self) -> types.InlineKeyboardMarkup:
        """Generate inline keyboard markup for requesting more advice."""
        markup = types.InlineKeyboardMarkup()
        more_advice_cb = self.advice_keyboard_factory.new(advice_btn="more_advice")
        markup.add(types.InlineKeyboardButton("Еще совет", callback_data=more_advice_cb))
        return markup
