"""Application setup and configuration"""

import logging
import sys
import os
from typing import List
import telebot
from telebot import types
from telebot.callback_data import CallbackData
from load_atomic import load_atomic_functions
from bot_middleware import Middleware
from bot_callback_filter import BotCallbackCustomFilter

class StartApp:
    """Configuring and running the application"""

    _LOGLEVEL_ENV_KEY = "LOGLEVEL"
    _TBOT_LOGLEVEL_ENV_KEY = "TBOT_LOGLEVEL"
    _TBOTTOKEN_ENV_KEY = "TBOTTOKEN"

    keyboard_factory: CallbackData

    def __init__(self, start_comannds: List[str]):
        self.logger = self.get_logger()
        self.bot = self._get_bot()
        self.atom_functions_list = load_atomic_functions()
        self.__decorate_atomic_functions()
        self.__decorate_defoult_functions(start_comannds)
        self.__add_middleware()
        self.__add_filter()

    def start_polling(self):
        """Start receiving messages"""
        self.logger.critical('-= START =-')
        self.bot.infinity_polling()

    def get_logger(self) -> logging.Logger:
        """Get a configured logger"""
        log = logging.getLogger(__name__)
        log.setLevel(self.__get_log_level(self._LOGLEVEL_ENV_KEY))
        handler = logging.FileHandler(f"{__name__}.log")
        formatter = logging.Formatter("%(name)s %(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(formatter)
        log.addHandler(handler)
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        log.addHandler(console_handler)
        return log

    def __get_log_level(self, env_key: str) -> int:
        """Get log level from environment variables"""
        str_level = os.environ.get(env_key)
        levels = logging.getLevelNamesMapping()
        if str_level in levels:
            return levels[str_level]
        return levels["INFO"]

    def _get_bot(self) -> telebot.TeleBot:
        """Get a configured bot"""
        token = os.environ.get(self._TBOTTOKEN_ENV_KEY)
        if not token:
            self.logger.critical("TBOTTOKEN not found in environment variables. Exiting...")
            sys.exit(1)
        log_level = self.__get_log_level(self._TBOT_LOGLEVEL_ENV_KEY)
        telebot.logger.setLevel(log_level)
        new_bot = telebot.TeleBot(token, use_class_middlewares=True)
        return new_bot

    def __add_middleware(self):
        """Registering Middleware for Bot"""
        self.bot.setup_middleware(Middleware(self.logger, self.bot))

    def __add_filter(self):
        """Add a custom filter for the bot"""
        self.bot.add_custom_filter(BotCallbackCustomFilter())

    def __decorate_atomic_functions(self):
        """Decorate handlers functions"""
        self.logger.info("Number of modules found - %d", len(self.atom_functions_list))
        for funct in self.atom_functions_list:
            try:
                if funct.state:
                    funct.set_handlers(self.bot)
                    self.logger.info("%s - start OK!", funct)
                else:
                    self.logger.info("%s - state FALSE!", funct)
            except Exception as ex:  # pylint: disable=broad-except
                self.logger.error(ex)
                funct.state = False
                self.logger.warning("%s - start EXCEPTION!", funct)

    def __decorate_defoult_functions(self, start_comannds: List[str]):
        """Decorate the function for handling startup commands
        and the function for handling uncaught messages"""

        self.logger.info("Setting up default functions with start commands: %s", start_comannds)
        self.keyboard_factory = CallbackData('app_key_button', prefix=start_comannds[0])
        description_callback_data = self.keyboard_factory.new(app_key_button="description")

        @self.bot.message_handler(commands=start_comannds)
        def start_message(message):
            self.logger.info("Received start command from user %s", message.from_user.username)
            txt = "Доступные функции: \n"
            active_functions = [funct for funct in self.atom_functions_list if funct.state]
            active_function_commands = [funct.commands[0] for funct in active_functions]
            self.logger.info("Active functions: %s", active_function_commands)
            if not active_functions:
                txt += "Нет доступных функций.\n"
            for funct in active_functions:
                cmd = funct.commands[0]
                about = funct.about
                txt += f"/{cmd} - {about}\n"
                self.logger.info("Added command to start message: /%s - %s", cmd, about)

            reply_markup = self.__gen_markup_button(description_callback_data)
            self.logger.info("Sending start message: %s", txt)
            self.bot.send_message(text=txt, chat_id=message.chat.id, reply_markup=reply_markup)

        @self.bot.callback_query_handler(func=None, config=self.keyboard_factory.filter())
        def example_keyboard_callback(call: types.CallbackQuery):
            callback_data: dict = self.keyboard_factory.parse(callback_data=call.data)
            button = callback_data['app_key_button']
            self.logger.info("Received callback query: %s", button)

            match (button):
                case ("description"):
                    self.__send_description_messages(call)
                case _:
                    self.bot.answer_callback_query(call.id, call.data)

        @self.bot.message_handler(func=lambda message: True)
        def text_messages(message):
            self.logger.info("Received text message: %s", message.text)
            self.bot.reply_to(message, "Text = " + message.text)
            cmd = "\n /".join(start_comannds)
            msg = f"To begin, enter one of the commands \n /{cmd}"
            self.bot.send_message(text=msg, chat_id=message.chat.id)

    def __gen_markup_button(self, callback_data):
        markup = types.InlineKeyboardMarkup()
        markup.row_width = 1
        markup.add(
            types.InlineKeyboardButton("Description", callback_data=callback_data)
        )
        return markup

    def __send_description_messages(self, call: types.CallbackQuery):
        for funct in self.atom_functions_list:
            authors = "\n "
            for author in funct.authors:
                authors += "https://github.com/" + author

            cmd = "\n /".join(funct.commands)
            msg = f"{funct.about} \n /{cmd} \n{funct.description} \n"
            msg += f"Авторы: {authors}"
            self.bot.send_message(text=msg, chat_id=call.message.chat.id)
