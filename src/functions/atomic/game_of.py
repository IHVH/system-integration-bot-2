"""Module implementation of the atomic function for Telegram Bot."""

import logging
from typing import List
import requests
import telebot
from telebot import types
from bot_func_abc import AtomicBotFunctionABC

logger = logging.getLogger(__name__)

class GameOfThronesQuotesBotFunction(AtomicBotFunctionABC):
    """Function to get Game of Thrones quotes from API by command"""

    commands: List[str] = ["got", "gots"]
    authors: List[str] = ["bolse119"]
    about: str = "Цитаты из Игры Престолов!"
    description: str = (
        "Функция позволяет получить цитаты персонажей Игры Престолов.\n"
        "Использование:\n"
        "/got - сначала покажет список персонажей, затем укажите имя\n"
        "Пример: /got tyrion\n"
        "API: https://api.gameofthronesquotes.xyz"
    )
    state: bool = True

    bot: telebot.TeleBot

    characters: List[dict] = [
        {"name": "Tyrion Lannister", "slug": "tyrion"},
        {"name": "Jon Snow", "slug": "jon"},
        {"name": "Daenerys Targaryen", "slug": "daenerys"},
        {"name": "Jaime Lannister", "slug": "jaime"},
        {"name": "Sansa Stark", "slug": "sansa"},
        {"name": "Petyr Baelish", "slug": "petyr"},
        {"name": "Cersei Lannister", "slug": "cersei"},
        {"name": "Arya Stark", "slug": "arya"},
        {"name": "Eddard Stark", "slug": "eddard"},
        {"name": "Theon Greyjoy", "slug": "theon"},
        {"name": "Samwell Tarly", "slug": "samwell"},
        {"name": "Varys", "slug": "varys"}
    ]

    def set_handlers(self, bot: telebot.TeleBot):
        """Set message handlers"""
        logger.info("Инициализация обработчиков команд: %s", self.commands)
        self.bot = bot

        @self.bot.message_handler(commands=self.commands)
        def got_message_handler(message: types.Message):
            logger.info("Получена команда %s", message.text)

            command_args = message.text.split(maxsplit=1)
            if len(command_args) < 2:
                self.__show_character_list(message.chat.id)
                return  # Если не указан персонаж, показываем список

            character_input = command_args[1].lower().strip()
            character = next(
                (char for char in self.characters
                 if char["slug"].lower() == character_input),
                None
            )

            if not character:
                self.bot.send_message(
                    message.chat.id,
                    f"❌ Персонаж `{character_input}` не найден!\n"
                    f"Попробуйте еще раз, выбрав **slug** из списка ниже."
                )
                self.__show_character_list(message.chat.id)  # Показываем список после ошибки
                return

            quote = self.__get_got_quote(character["slug"])

            if quote:
                self.bot.send_message(
                    message.chat.id,
                    f"📜 \"{quote['sentence']}\"\n— {quote['character']['name']}"
                )
            else:
                self.bot.send_message(
                    message.chat.id,
                    f"😔 Не удалось получить цитату для {character['name']}.\nПопробуйте еще раз."
                )

            self.__show_character_list(message.chat.id)  # Показываем список после цитаты

    def __show_character_list(self, chat_id: int):
        """Отправляет список доступных персонажей в колонку"""
        characters_list = "\n".join(
            f"- {char['name']} (`{char['slug']}`)" for char in self.characters
        )
        self.bot.send_message(
            chat_id,
            f"📜 **Доступные персонажи:**\n{characters_list}\n"
            "Введите имя персонажа после команды `/got`, например: `/got tyrion`\n", 
            parse_mode="Markdown"
        )

    @staticmethod
    def __get_got_quote(slug: str) -> dict:
        """Get random quote for specific character"""
        try:
            response = requests.get(
                f"https://api.gameofthronesquotes.xyz/v1/author/{slug}/2",
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            return data[0] if isinstance(data, list) and len(data) > 0 else None
        except requests.RequestException:
            return None
