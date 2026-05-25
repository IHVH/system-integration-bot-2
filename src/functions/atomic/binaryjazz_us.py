"""
Модуль функции Telegram-бота для BinaryJazz Genrenator API.
"""

from typing import Any, Dict, List

import requests
import telebot
from telebot import types

from bot_func_abc import AtomicBotFunctionABC


class BinaryJazzGenrenatorFunction(AtomicBotFunctionABC):
    """
    Функция Telegram-бота для работы с BinaryJazz Genrenator API.
    """

    commands: List[str] = ["binaryjazz_genrenator"]
    authors: List[str] = ["vova.shevchishin.03"]
    about: str = "Генератор BinaryJazz"
    description: str = (
        "Функция работает с BinaryJazz Genrenator API. "
        "После команды /binaryjazz_genrenator появляется меню с кнопками: "
        "генерация музыкального жанра и генерация текста указанной длины."
    )
    state: bool = True

    API_URL = "https://binaryjazz.us/wp-json/genrenator/v1"

    def set_handlers(self, bot: telebot.TeleBot) -> None:
        """
        Установка обработчиков Telegram-бота.
        """

        @bot.message_handler(commands=self.commands)
        def start_handler(message: types.Message) -> None:
            """
            Показать главное меню BinaryJazz.
            """
            keyboard = types.InlineKeyboardMarkup()

            genre_button = types.InlineKeyboardButton(
                text="🎵 Сгенерировать жанр",
                callback_data="binaryjazz_genre",
            )

            story_button = types.InlineKeyboardButton(
                text="📝 Сгенерировать текст",
                callback_data="binaryjazz_story",
            )

            keyboard.add(genre_button)
            keyboard.add(story_button)

            bot.send_message(
                message.chat.id,
                "Выберите действие:",
                reply_markup=keyboard,
            )

        @bot.callback_query_handler(
            func=lambda call: call.data == "binaryjazz_genre"
        )
        def genre_callback(call: types.CallbackQuery) -> None:
            """
            Генерация случайного жанра.
            """
            try:
                genre = self._get_genre()

                bot.send_message(
                    call.message.chat.id,
                    f"🎵 Сгенерированный жанр:\n{genre}",
                )

            except requests.RequestException as error:
                bot.send_message(
                    call.message.chat.id,
                    f"Ошибка при запросе к API: {error}",
                )

        @bot.callback_query_handler(
            func=lambda call: call.data == "binaryjazz_story"
        )
        def story_callback(call: types.CallbackQuery) -> None:
            """
            Запрос количества текстов.
            """
            msg = bot.send_message(
                call.message.chat.id,
                "Введите количество текстов от 1 до 10:",
            )

            bot.register_next_step_handler(
                msg,
                process_story_count,
            )

        def process_story_count(message: types.Message) -> None:
            """
            Генерация текстов.
            """
            try:
                count = int(message.text)

                if count < 1 or count > 10:
                    bot.reply_to(
                        message,
                        "Введите число от 1 до 10.",
                    )
                    return

                stories = self._get_stories(count)

                bot.reply_to(
                    message,
                    self._format_stories(stories),
                )

            except ValueError:
                bot.reply_to(
                    message,
                    "Введите корректное число.",
                )

            except requests.RequestException as error:
                bot.reply_to(
                    message,
                    f"Ошибка при запросе к API: {error}",
                )

    @classmethod
    def _get_genre(cls) -> str:
        """
        Получить случайный музыкальный жанр.
        """
        response = requests.get(f"{cls.API_URL}/genre/", timeout=10)
        response.raise_for_status()

        return response.text.strip().replace('"', "")

    @classmethod
    def _get_stories(cls, count: int) -> List[str]:
        """
        Получить список сгенерированных текстов.
        """
        response = requests.get(f"{cls.API_URL}/story/{count}/", timeout=10)
        response.raise_for_status()

        data = response.json()

        if isinstance(data, list):
            return [str(item) for item in data]

        return [str(data)]

    @staticmethod
    def _format_stories(stories: List[str]) -> str:
        """
        Отформатировать список сгенерированных текстов.
        """
        if not stories:
            return "Тексты не найдены."

        result = ["📝 Сгенерированные тексты:\n"]

        for number, story in enumerate(stories, start=1):
            result.append(f"{number}. {story}")

        return "\n\n".join(result)

    def get_info(self) -> Dict[str, Any]:
        """
        Получить информацию о функции.
        """
        return {
            "commands": self.commands,
            "authors": self.authors,
            "about": self.about,
            "description": self.description,
            "state": self.state,
        }