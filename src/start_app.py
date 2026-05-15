"""Application setup and configuration"""

import logging
import sys
import os
from typing import List
import telebot
from load_atomic import load_atomic_functions
from bot_middleware import Middleware
from bot_callback_filter import BotCallbackCustomFilter
from dotenv import load_dotenv
load_dotenv()
class StartApp():
    """Configuring and running the application"""

    _LOGLEVEL_ENV_KEY = "LOGLEVEL"
    _TBOT_LOGLEVEL_ENV_KEY = "TBOT_LOGLEVEL"
    _TBOTTOKEN_ENV_KEY = "TBOTTOKEN"

    def __init__(self, start_comannds: List[str]):
        self.logger = self.get_logger()
        self.bot = self.__get_bot()
        self.atom_functions_list = load_atomic_functions()
        self.__decorate_atomic_functions()
        self.__decorate_defoult_functions(start_comannds)
        self.__add_middleware()
        self.__add_filter()

    def start_polling(self):
        """Start receiving messages"""
        self.logger.critical('-= START =-')
        self.bot.infinity_polling()

    def get_logger(self)-> logging.Logger:
        """Get a configured logger"""
        log = logging.getLogger(__name__)
        log.setLevel(self.__get_log_level(self._LOGLEVEL_ENV_KEY))
        handler = logging.FileHandler(f"{__name__}.log")
        formatter = logging.Formatter("%(name)s %(asctime)s %(levelname)s %(message)s")
        print("TBOTTOKEN =", os.environ.get("TBOTTOKEN"))
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

    def __get_bot(self)-> telebot.TeleBot:
        """Get a configured bot"""
        token = os.environ[self._TBOTTOKEN_ENV_KEY]
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
            except Exception as ex: # pylint: disable=broad-except
                self.logger.error(ex)
                funct.state = False
                self.logger.warning("%s - start EXCEPTION!", funct)

    def __decorate_defoult_functions(self, start_comannds: List[str]):
        """Decorate the function for handling startup commands
        and the function for handling uncaught messages"""

        @self.bot.message_handler(commands=start_comannds)
        def start_message(message):
            txt = "Доступные функции: \n"
            for funct in self.atom_functions_list:
                txt += f"/{funct.commands[0]} - {funct.about} \n"
            self.bot.send_message(text=txt, chat_id=message.chat.id)

        @self.bot.message_handler(func=lambda message: True)
        def text_messages(message):
            self.bot.reply_to(message, "Text = " + message.text)
            cmd = "\n /".join(start_comannds)
            msg = f"To begin, enter one of the commands \n /{cmd}"
            self.bot.send_message(text=msg, chat_id=message.chat.id)
