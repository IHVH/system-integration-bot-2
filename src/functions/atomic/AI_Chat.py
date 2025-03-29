import asyncio
import os
import logging
from typing import List
import telebot
from telebot import types
from telebot.callback_data import CallbackData
from bot_func_abc import AtomicBotFunctionABC
from mistralai import Mistral

class AtomicExampleBotFunction(AtomicBotFunctionABC):
    """Example of implementation of atomic function with Neural Network integration"""

    commands: List[str] = ["example", "ebf"]
    authors: List[str] = ["Garik205"]
    about: str = "Пример функции бота с интеграцией нейронной сети!"
    description: str = "Реализация свободного общения с нейронной сетью"
    state: bool = True

    bot: telebot.TeleBot
    example_keyboard_factory: CallbackData
    neural_network: Mistral

    def __init__(self):
        self.neural_network = Mistral()  # Initialize the neural network module

    def set_handlers(self, bot: telebot.TeleBot):
        """Set message handlers"""

        self.bot = bot
        self.example_keyboard_factory = CallbackData('t_key_button', prefix=self.commands[0])

        @bot.message_handler(commands=self.commands)
        def example_message_handler(message: types.Message):
            asyncio.run(self.handle_nn_chat(message))

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

    async def handle_nn_chat(self, message: types.Message):
        user_message = message.text
        nn_response = await self.__get_nn_response(user_message)
        self.bot.send_message(message.chat.id, nn_response)

    async def __get_nn_response(self, content: str) -> str:
        # Use the neural network module to generate a response
        response = await Mistral.generate_response(content)
        return response

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

# Initialize the bot with the provided token
bot = telebot.TeleBot("7806305177:AAFiFhdPa3f9MWWYbSWjFY8ic8W0PxbWfRY")
atomic_function = AtomicExampleBotFunction()
atomic_function.set_handlers(bot)

# Start polling
bot.polling()