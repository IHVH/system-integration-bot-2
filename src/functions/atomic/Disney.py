"""Модуль, присылающий информацию о персонажах Disney"""

from typing import List
import requests
import telebot
from telebot import types
from telebot.callback_data import CallbackData
from bot_func_abc import AtomicBotFunctionABC


class AtomicDisneyBotFunction(AtomicBotFunctionABC):
    """Модуль для получения информации о случайных персонажах Disney через Telegram бота."""

    commands: List[str] = ["disney"]
    authors: List[str] = ["YourName"]
    about: str = "Персонажи Disney" # Краткое описание
    description: str = (
        "Этот бот позволяет получать информацию о случайных персонажах Disney. "
        "Для получения персонажей используйте команду /disney <количество>"
    )
    state: bool = True

    bot: telebot.TeleBot
    disney_keyboard_factory: CallbackData

    def set_handlers(self, bot: telebot.TeleBot):
        """Устанавливает обработчики команд для бота."""
        self.bot = bot
        self.disney_keyboard_factory = CallbackData(
            'd_key_button', prefix=self.commands[0]
        )

        @bot.message_handler(commands=self.commands)
        def send_disney_characters(message: types.Message):
            try:
                # Получаем число после команды /disney
                num_characters = int(message.text.split()[1])
                # Ограничиваем количество, чтобы не перегружать API и чат
                if num_characters > 5:
                    num_characters = 5
                    bot.send_message(message.chat.id, "Максимальное количество персонажей за раз — 5. Будет отправлено 5.")
            except (IndexError, ValueError):
                msg = "Пожалуйста, укажите количество персонажей. Пример: /disney 3"
                bot.send_message(message.chat.id, msg)
                return

            characters = self.get_characters(num_characters)
            if not characters:
                bot.send_message(message.chat.id, "Не удалось получить информацию о персонажах.")
                return

            for character in characters:
                bot.send_message(message.chat.id, character, parse_mode='Markdown')

    def get_characters(self, num_characters: int) -> List[str]:
        """Получает информацию о случайных персонажах из Disney API."""
        characters_list = []
        for _ in range(num_characters):
            try:
                # Получаем случайного персонажа с помощью эндпоинта /character
                response = requests.get(
                    "https://api.disneyapi.dev/character", timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    # API возвращает список персонажей, берем первого
                    if data.get('data'):
                        character_data = data['data'][0]
                        # Извлекаем нужную информацию
                        name = character_data.get('name', 'Неизвестно')
                        films = character_data.get('films', [])
                        tv_shows = character_data.get('tvShows', [])

                        # Формируем красивое сообщение
                        character_info = f"*Имя:* {name}\n"

                        if films:
                            # Выводим до 3-х фильмов для читаемости
                            films_str = ', '.join(films[:3])
                            if len(films) > 3:
                                films_str += f" и еще {len(films) - 3}"
                            character_info += f"*Фильмы:* {films_str}\n"

                        if tv_shows:
                            shows_str = ', '.join(tv_shows[:3])
                            if len(tv_shows) > 3:
                                shows_str += f" и еще {len(tv_shows) - 3}"
                            character_info += f"*Сериалы:* {shows_str}\n"

                        # Добавляем ссылку на изображение, если оно есть
                        image_url = character_data.get('imageUrl')
                        if image_url:
                            character_info += f"[🖼️ Изображение]({image_url})"

                        characters_list.append(character_info)
            except requests.exceptions.RequestException as e:
                print(f"Ошибка при запросе к API Disney: {e}")
                continue

        return characters_list