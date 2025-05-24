"""
Интеграция с API waifu.im.
Позволяет запрашивать изображения по тегам, указывать количество и смотреть доступные теги.
"""

import logging
from typing import List
import requests
from telebot import TeleBot, types
from telebot.callback_data import CallbackData
from bot_func_abc import AtomicBotFunctionABC


class WaifuFunction(AtomicBotFunctionABC):
    """
    Функция для получения изображений с waifu.im по тегу.
    Поддерживает команды /waifu и /waifu_tags.
    """

    commands: List[str] = ["waifu", "waifu_tags"]
    authors: List[str] = ["fckngraccoon"]
    about: str = "Случайные waifu"
    description: str = (
        "Используйте /waifu <тег> <количество (по желанию)>.\n"
        "Пример: /waifu waifu 3\n"
        "Также доступна команда /waifu_tags для получения списка тегов."
    )
    state: bool = True

    bot: TeleBot
    keyboard_factory: CallbackData

    def set_handlers(self, bot: TeleBot):
        """Устанавливает обработчики команд."""
        self.bot = bot

        @bot.message_handler(commands=["prefix=self.commands[0]"])
        def waifu_handler(message: types.Message):
            """Обработчик команды /waifu."""
            self.__process_waifu_request(message)

        @bot.message_handler(commands=["prefix=self.commands[1]"])
        def waifu_tags_handler(message: types.Message):
            """Обработчик команды /waifu_tags."""
            try:
                tags = self.__get_available_tags()
                tags_list = ", ".join(tags)
                self.bot.send_message(
                    message.chat.id,
                    f"Доступные теги:\n{tags_list}"
                )
            except requests.exceptions.RequestException as exc:
                logging.exception("Ошибка при получении тегов: %s", exc)
                self.bot.send_message(
                    message.chat.id,
                    "Не удалось получить список тегов. Попробуйте позже."
                )

    def __process_waifu_request(self, message: types.Message):
        """Обрабатывает запрос пользователя по команде /waifu."""
        args = message.text.split()[1:]

        if not args:
            self.bot.send_message(
                message.chat.id,
                "Пожалуйста, укажите тег. Пример: /waifu waifu 3"
            )
            return

        tag = args[0]
        try:
            amount = int(args[1]) if len(args) > 1 else 1
            if amount < 1 or amount > 10:
                self.bot.send_message(
                    message.chat.id,
                    "Количество должно быть от 1 до 10."
                )
                return
        except ValueError:
            self.bot.send_message(
                message.chat.id,
                "Количество должно быть числом."
            )
            return

        try:
            images = self.__fetch_waifu_images(tag, amount)
            if not images:
                self.bot.send_message(
                    message.chat.id,
                    "Изображения не найдены. Проверьте тег."
                )
                return

            for img in images:
                self.bot.send_photo(
                    message.chat.id,
                    img["url"]
                )
        except requests.exceptions.RequestException as exc:
            logging.exception("Ошибка при обращении к API waifu.im: %s", exc)
            self.bot.send_message(
                message.chat.id,
                "Произошла ошибка при получении изображений."
            )

    def __fetch_waifu_images(self, tag: str, amount: int) -> List[dict]:
        """Получает изображения по тегу."""
        url = "https://api.waifu.im/search/"
        params = {"included_tags": tag, "many": "true", "limit": amount}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("images", [])

    def __get_available_tags(self) -> List[str]:
        """Получает список доступных тегов с API."""
        response = requests.get("https://api.waifu.im/tags", timeout=10)
        response.raise_for_status()
        data = response.json()
        return [tag["name"] for tag in data.get("versatile", [])]
