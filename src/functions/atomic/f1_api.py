"""Модуль для получения информации о сезонах Формула 1 и результатов отдельно взятых пилотов."""

import logging
import requests
import telebot
from telebot import types
from bot_func_abc import AtomicBotFunctionABC


class F1ApiBotFunction(AtomicBotFunctionABC):
    """Модуль для получения результатов выбранного сезона Формула 1."""
       
    commands: list[str] = ["f1"]
    authors: list[str] = ["sidorovt"]
    about: str = "Результаты сезонов Формула 1 с 1950г. по текущий."
    description: str = (
        "Показывает результаты сезона Формула 1."
        "Используйте: /f1 <год сезона> (например, /f1 2026)."
    )
    state: bool = False
    bot: telebot.TeleBot
    logger: logging.Logger
    api_url: str = "https://api.jolpi.ca/ergast/f1"

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(name)s %(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)
        self.logger.info("F1ApiBotFunction initialized")