"""Default Bot Functions."""

from typing import List
import telebot
from telebot import types
from telebot.callback_data import CallbackData
from bot_func_abc import AtomicBotFunctionABC

class DefoultBotFunction(AtomicBotFunctionABC):
    """Bot default functions. To display information about the connected functions"""

    commands: List[str] = ["start"]
    authors: List[str] = ["IHVH"]
    about: str = "Дефолтная функция бота."
    description: str = """Дефолтная функция бота. Для вывода информации о подключаемых функциях."""
    state: bool = True

    bot: telebot.TeleBot
    atom_functions_list: List[AtomicBotFunctionABC]

    def __init__(self, start_comands: List[str], functions_list: List[AtomicBotFunctionABC]):
        self.commands = start_comands
        self.atom_functions_list = functions_list
        self.app_part = "app_key_button"
        self.keyboard_factory = CallbackData(self.app_part, "func_index", prefix=self.commands[0])
        self.button_data = "description"

    def set_handlers(self, bot: telebot.TeleBot):
        """Set message handlers"""

        self.bot = bot
        @self.bot.message_handler(commands=self.commands)
        def start_message(message):
            txt = "Доступные функции: \n"
            for funct in self.atom_functions_list:
                txt += f"/{funct.commands[0]} - {funct.about} \n"

            description_callback_data = self.keyboard_factory.new(
                app_key_button=self.button_data,
                func_index=0
            )
            reply_markup=self.__gen_markup_button("Description", description_callback_data)
            self.bot.send_message(text=txt, chat_id=message.chat.id, reply_markup=reply_markup)

        @self.bot.callback_query_handler(func=None, config=self.keyboard_factory.filter())
        def example_keyboard_callback(call: types.CallbackQuery):
            callback_data: dict = self.keyboard_factory.parse(callback_data=call.data)
            button = callback_data[self.app_part]
            func_index = callback_data["func_index"]
            match (button):
                case (self.button_data):
                    self.__send_description_messages(call, func_index)
                case _:
                    self.bot.answer_callback_query(call.id, call.data)

        @self.bot.message_handler(func=lambda message: True)
        def text_messages(message):
            self.bot.reply_to(message, "Text = " + message.text)
            cmds = "\n /".join(self.commands)
            msg = f"To begin, enter one of the commands \n /{cmds}"
            self.bot.send_message(text=msg, chat_id=message.chat.id)

    def __gen_markup_button(self, text: str, callback_data: str):
        markup = types.InlineKeyboardMarkup()
        markup.row_width = 1
        markup.add(
            types.InlineKeyboardButton(text, callback_data=callback_data)
        )
        return markup

    def __send_description_messages(self, call: types.CallbackQuery, digit: str):
        func_index = 0
        if digit.isdigit():
            func_index = int(digit)
        funct = self.atom_functions_list[func_index]
        txt = self.__get_atomic_function_description(funct)
        next_index = func_index + 1
        if next_index < len(self.atom_functions_list):
            button_data = self.button_data
            description_callback_data = self.keyboard_factory.new(
                app_key_button=button_data,
                func_index=next_index
            )
            reply_markup=self.__gen_markup_button("Next ->", description_callback_data)
            self.bot.send_message(text=txt, chat_id=call.message.chat.id,
            reply_markup=reply_markup, parse_mode="Markdown")
        else:
            self.bot.send_message(text=txt, chat_id=call.message.chat.id, parse_mode="Markdown")

    def __get_atomic_function_description(self, funct: AtomicBotFunctionABC) -> str:
        authors = "\n "
        for author in funct.authors:
            authors += "https://github.com/" + author

        cmd = "\n /".join(funct.commands)
        msg = f"{funct.about} \n /{cmd} \n{funct.description} \n"
        msg += f"Авторы: {authors}"
        return msg
