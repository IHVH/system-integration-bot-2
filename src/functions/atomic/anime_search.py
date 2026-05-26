"""Функция для поиска аниме по названию."""

from typing import List

import requests
import telebot
from telebot import types

from bot_func_abc import AtomicBotFunctionABC


class AnimeSearchBotFunction(AtomicBotFunctionABC):
    """Класс функции поиска аниме."""

    # pylint: disable=too-few-public-methods

    commands: List[str] = ["anime"]
    authors: List[str] = ["Ddt132"]
    about: str = "Поиск аниме"
    description: str = (
        "Функция выполняет поиск аниме по названию через открытый API Jikan, "
        "получает данные из MyAnimeList и отправляет пользователю название, "
        "рейтинг, количество серий, статус, описание и изображение."
    )
    state: bool = True

    def set_handlers(self, bot: telebot.TeleBot):
        """Устанавливает обработчик команды anime."""

        @bot.message_handler(commands=self.commands)
        def anime_handler(message: types.Message):
            anime_name = message.text.replace("/anime", "").strip()

            if not anime_name:
                bot.reply_to(
                    message,
                    "Введите название аниме. Пример: /anime Naruto"
                )
                return

            try:
                anime_data = self.__get_anime(anime_name)

                if anime_data is None:
                    bot.reply_to(message, "Аниме не найдено.")
                    return

                answer = self.__format_answer(anime_data)
                image_url = anime_data["images"]["jpg"]["image_url"]

                bot.send_photo(
                    message.chat.id,
                    image_url,
                    caption=answer
                )

            except requests.RequestException:
                bot.reply_to(message, "Ошибка при запросе к API.")

            except KeyError:
                bot.reply_to(message, "Ошибка обработки данных.")

    @staticmethod
    def __get_anime(anime_name: str):
        url = "https://api.jikan.moe/v4/anime"

        params = {
            "q": anime_name,
            "limit": 1,
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        if not data["data"]:
            return None

        return data["data"][0]

    @staticmethod
    def __format_answer(anime_data: dict) -> str:
        title = anime_data["title"]
        score = anime_data["score"]
        episodes = anime_data["episodes"]
        status = anime_data["status"]
        synopsis = anime_data["synopsis"]

        if synopsis:
            synopsis = synopsis[:300] + "..."

        return (
            f"🎌 {title}\n\n"
            f"⭐ Рейтинг: {score}\n"
            f"🎬 Серий: {episodes}\n"
            f"📺 Статус: {status}\n\n"
            f"📝 Описание:\n{synopsis}"
        )
