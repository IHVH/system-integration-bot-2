"""
Интеграция с API waifu.im — отправка изображений по тегу.
"""

import logging
from typing import List
import requests
from telebot import TeleBot, types
from telebot.callback_data import CallbackData
from bot_func_abc import AtomicBotFunctionABC


class WaifuImageFunction(AtomicBotFunctionABC):
    """Функция для получения изображений из API waifu.im."""

    commands: List[str] = ["waifu"]
    authors: List[str] = ["Герлеман Андрей Антонович, Github: fckngraccoon"]
    about: str = "Отправка изображений по тегам с сайта waifu.im"
    description: str = (
        "Позволяет искать и отправлять изображения с сайта waifu.im по тегам. "
        "Введите тег и количество изображений (от 1 до 10)."
    )
    state: bool = True

    bot: TeleBot
    callback_factory: CallbackData

    def set_handlers(self, bot: TeleBot):
        """Устанавливает обработчики команд и колбэков."""
        self.bot = bot
        self.callback_factory = CallbackData("waifu_action", prefix=self.commands[0])

        @bot.message_handler(commands=self.commands)
        def command_handler(message: types.Message):
            tags = self.__get_available_tags()
            if not tags:
                bot.send_message(message.chat.id, "Не удалось получить список тегов.")
                return

            tags_str = ", ".join(tags)
            prompt = (
                f"Введите тег (доступные: {tags_str}) и количество изображений (1–10), "
                "например: `waifu 3`"
            )
            bot.send_message(message.chat.id, prompt, parse_mode="Markdown")
            bot.register_next_step_handler(message, self.__process_waifu_request)

    def __process_waifu_request(self, message: types.Message):
        """Обрабатывает команду /waifu: получает изображения по тегу и количеству."""
        try:
            parts = message.text.strip().split()
            if len(parts) != 2:
                self.bot.send_message(message.chat.id, "Введите тег и количество через пробел.")
                return

            tag, count_str = parts
            count = int(count_str)
            if not 1 <= count <= 10:
                self.bot.send_message(
                    message.chat.id,
                    "Количество изображений должно быть от 1 до 10."
                )
                return

            images = self.__fetch_waifu_images(tag, count)
            if not images:
                self.bot.send_message(message.chat.id, "Изображения не найдены.")
                return

            for image in images:
                self.bot.send_photo(message.chat.id, image["url"])

        except ValueError:
            self.bot.send_message(message.chat.id, "Количество должно быть числом.")
        except requests.exceptions.RequestException as exc:
            logging.exception("Ошибка при обращении к API waifu.im: %s", exc)
            self.bot.send_message(message.chat.id, "Произошла ошибка при получении изображений.")


    def __fetch_waifu_images(self, tag: str, count: int) -> List[dict]:
        """Отправляет запрос к API waifu.im и возвращает список изображений."""
        try:
            response = requests.get(
                "https://api.waifu.im/search/",
                params={"included_tags": tag, "many": "true", "amount": count},
                timeout=10
            )
            response.raise_for_status()
            return response.json().get("images", [])
        except requests.exceptions.RequestException as exc:
            logging.error("Ошибка при обращении к API waifu.im: %s", exc)
            return []

    def __get_available_tags(self) -> List[str]:
        """Получает список доступных тегов из API."""
        try:
            response = requests.get("https://api.waifu.im/tags", timeout=10)
            response.raise_for_status()
            return [tag["name"] for tag in response.json().get("versatile", [])]
        except requests.exceptions.RequestException as exc:
            logging.warning("Не удалось получить теги с waifu.im: %s", exc)
            return []
