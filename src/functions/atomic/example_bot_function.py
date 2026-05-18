"""Module implementation of the atomic function of the telegram bot. Example of implementation."""

import os
import logging
from typing import List
import telebot
from telebot import types
from telebot.callback_data import CallbackData
from bot_func_abc import AtomicBotFunctionABC

class AtomicExampleBotFunction(AtomicBotFunctionABC):
    """Example of implementation of atomic function
    """

    commands: List[str] = ["example", "ebf"]
    authors: List[str] = ["IHVH"]
    about: str = "Пример функции бота!"
    description: str = """В поле  *description* поместите подробную информацию о работе функции.
    Описание способов использования, логики работы. Примеры вызова функции - /ebf 
    Возможные параметры функции `/example`  """
    state: bool = True

    bot: telebot.TeleBot
    example_keyboard_factory: CallbackData

    def set_handlers(self, bot: telebot.TeleBot):
        """Set message handlers"""

        self.bot = bot
        self.example_keyboard_factory = CallbackData('t_key_button', prefix=self.commands[0])

        @bot.message_handler(commands=self.commands)
        def example_message_hendler(message: types.Message):
            chat_id_msg = f"\nCHAT ID = {message.chat.id}"
            msg = (
                f"Ваш запрос обработан в AtomicExampleBotFunction! {chat_id_msg}\n"
                f"USER ID = {message.from_user.id} \nEXAMPLETOKEN = {self.__get_example_token()}"
            )
            bot.send_message(text=msg, chat_id=message.chat.id, reply_markup=self.__gen_markup())

        @bot.callback_query_handler(func=None, config=self.example_keyboard_factory.filter())
        def example_keyboard_callback(call: types.CallbackQuery):
            callback_data: dict = self.example_keyboard_factory.parse(callback_data=call.data)
            t_key_button = callback_data['t_key_button']

            match (t_key_button):
                case ('cb_yes'):
                    bot.answer_callback_query(call.id, "Ответ ДА!")
                case ('cb_no'):
                    bot.answer_callback_query(call.id, "Ответ НЕТ!")
                case ('force_reply'):
                    force_reply = types.ForceReply(selective=False)
                    text = "Отправьте текст для обработки в process_next_step"
                    bot.send_message(call.message.chat.id, text, reply_markup=force_reply)
                    bot.register_next_step_handler(call.message, self.__process_next_step)
                case _:
                    bot.answer_callback_query(call.id, call.data)

    def __get_example_token(self):
        token = os.environ.get("EXAMPLETOKEN")
        return token

    def __gen_markup(self):
        markup = types.InlineKeyboardMarkup()
        markup.row_width = 2
        yes_callback_data = self.example_keyboard_factory.new(t_key_button="cb_yes")
        no_callback_data = self.example_keyboard_factory.new(t_key_button="cb_no")
        force_reply_callback_data = self.example_keyboard_factory.new(t_key_button="force_reply")
        markup.add(
            types.InlineKeyboardButton("Да", callback_data=yes_callback_data),
            types.InlineKeyboardButton("Нет", callback_data=no_callback_data),
            types.InlineKeyboardButton("ForceReply", callback_data=force_reply_callback_data)
        )
        return markup

    def __process_next_step(self, message):
        try:
            chat_id = message.chat.id
            txt = message.text
            if txt != "exit":
                force_reply = types.ForceReply(selective=False)
                text = f"text = {txt}; chat.id = {chat_id}; \n Для выхода из диалога введите - exit"
                msg = self.bot.send_message(message.chat.id, text, reply_markup=force_reply)
                self.bot.register_next_step_handler(msg, self.__process_next_step)
        except ValueError as ex:
            logging.exception(ex)
            self.bot.reply_to(message, f"Exception - {ex}")
