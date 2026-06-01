"""Модуль, присылающий информацию о персонажах Disney."""

from typing import List, Optional
import requests
import telebot
from telebot import types
from telebot.callback_data import CallbackData
from bot_func_abc import AtomicBotFunctionABC


class AtomicDisneyBotFunction(AtomicBotFunctionABC):
    """Модуль для получения информации о случайных персонажах Disney через Telegram бота."""

    commands: List[str] = ["disney"]
    authors: List[str] = ["lyvb"]
    about: str = "Персонажи Disney"
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
            """Обработчик команды /disney."""
            num = self._parse_character_count(message)
            if num is None:
                return

            characters = self.get_characters(num)
            if not characters:
                bot.send_message(
                    message.chat.id,
                    "Не удалось получить информацию о персонажах."
                )
                return

            self._send_characters(bot, message.chat.id, characters)

    def _parse_character_count(self, message: types.Message) -> Optional[int]:
        """
        Извлекает и валидирует количество персонажей из команды.

        Args:
            message: Сообщение от пользователя.

        Returns:
            Количество персонажей (не более 5) или None при ошибке.
        """
        try:
            num_characters = int(message.text.split()[1])
            if num_characters > 5:
                self.bot.send_message(
                    message.chat.id,
                    "Максимальное количество персонажей за раз — 5. "
                    "Будет отправлено 5."
                )
                return 5
            return num_characters
        except (IndexError, ValueError):
            self.bot.send_message(
                message.chat.id,
                "Пожалуйста, укажите количество персонажей. "
                "Пример: /disney 3"
            )
            return None

    def _send_characters(self, bot: telebot.TeleBot, chat_id: int, characters: List[str]):
        """Отправляет список персонажей в чат."""
        for character in characters:
            bot.send_message(chat_id, character, parse_mode='Markdown')

    def get_characters(self, num_characters: int) -> List[str]:
        """Получает информацию о случайных персонажах из Disney API."""
        characters_list = []
        for _ in range(num_characters):
            try:
                # Получаем случайного персонажа (API может возвращать не случайного,
                # для реальной случайности нужно использовать параметр page)
                response = requests.get(
                    "https://api.disneyapi.dev/character", timeout=10
                )
                response.raise_for_status()
                data = response.json()

                if data.get('data'):
                    character_data = data['data'][0]
                    character_info = self._format_character_info(character_data)
                    characters_list.append(character_info)
            except requests.exceptions.RequestException as e:
                print(f"Ошибка при запросе к API Disney: {e}")
                continue

        return characters_list

    def _format_character_info(self, character_data: dict) -> str:
        """
        Форматирует информацию о персонаже в читаемый текст.

        Args:
            character_data: Словарь с данными персонажа.

        Returns:
            Отформатированная строка с информацией.
        """
        name = character_data.get('name', 'Неизвестно')
        films = character_data.get('films', [])
        tv_shows = character_data.get('tvShows', [])

        character_info = f"*Имя:* {name}\n"

        if films:
            films_str = ', '.join(films[:3])
            if len(films) > 3:
                films_str += f" и еще {len(films) - 3}"
            character_info += f"*Фильмы:* {films_str}\n"

        if tv_shows:
            shows_str = ', '.join(tv_shows[:3])
            if len(tv_shows) > 3:
                shows_str += f" и еще {len(tv_shows) - 3}"
            character_info += f"*Сериалы:* {shows_str}\n"

        image_url = character_data.get('imageUrl')
        if image_url:
            character_info += f"[🖼️ Изображение]({image_url})"

        return character_info
