
"""Module implementation of the atomic function for Pokémon data using PokéAPI."""

import logging
import random
from typing import List, Dict, Any
import requests
import telebot
from telebot import types as telebot_types
from telebot.callback_data import CallbackData
from bot_func_abc import AtomicBotFunctionABC


class AtomicPokeFunction(AtomicBotFunctionABC):
    """Implementation of atomic function for Pokémon data"""

    commands: List[str] = ["pokemon", "pokedex"]
    authors: List[str] = ["dantess998"]
    about: str = "Информация о покемонах"
    description: str = """Функция предоставляет информацию о покемонах из PokéAPI.
    Вы можете получить базовую информацию о любом покемоне, включая его тип, способности и статистику.
    
    Примеры использования:
    /pokemon pikachu - информация о Пикачу
    /pokedex - случайный покемон из Покедекса
    """
    state: bool = True

    bot: telebot.TeleBot
    pokemon_keyboard_factory: CallbackData

    # API configuration
    API_URL_BASE = "https://pokeapi.co/api/v2/"

    def set_handlers(self, bot: telebot.TeleBot):
        """Set message handlers"""

        self.bot = bot
        self.pokemon_keyboard_factory = CallbackData(
            "action", 
            "pokemon_name", 
            prefix=self.commands[0]
        )

        @bot.message_handler(commands=self.commands)
        def pokemon_message_handler(message: telebot_types.Message):
            try:
                command = message.text.split()[0][1:]  # Remove the '/' and get the command

                if command == "pokemon":
                    # Check if a Pokémon name was provided
                    if len(message.text.split()) > 1:
                        pokemon_name = message.text.split(maxsplit=1)[1].lower()
                        self.__handle_pokemon_info(message, pokemon_name)
                    else:
                        self.bot.reply_to(
                            message,
                            "Пожалуйста, укажите имя покемона. Например: /pokemon pikachu. "
                            "Или используйте команду /pokedex для получения случайного покемона."
                        )
                elif command == "pokedex":
                    self.__handle_random_pokemon(message)
                else:
                    self.__send_help(message)
            except (ValueError, IndexError) as ex:
                logging.exception("Error processing command: %s", ex)
                bot.reply_to(message, f"Произошла ошибка: {str(ex)}")

        @bot.callback_query_handler(
            func=None, config=self.pokemon_keyboard_factory.filter()
        )
        def pokemon_keyboard_callback(call: telebot_types.CallbackQuery):
            callback_data: dict = self.pokemon_keyboard_factory.parse(
                callback_data=call.data
            )
            action = callback_data["action"]
            pokemon_name = callback_data["pokemon_name"]

            try:
                if action == "stats":
                    self.__send_pokemon_stats(call.message.chat.id, pokemon_name)
                elif action == "abilities":
                    self.__send_pokemon_abilities(call.message.chat.id, pokemon_name)
                elif action == "back":
                    self.__handle_pokemon_info(call.message, pokemon_name)
                else:
                    bot.answer_callback_query(call.id, "Неизвестное действие")
            except (ValueError, KeyError, RuntimeError) as ex:
                logging.exception("Error processing callback: %s", ex)
                bot.answer_callback_query(call.id, f"Ошибка: {str(ex)}")

    def __make_api_request(
        self, endpoint: str, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Make a request to the PokéAPI"""
        url = f"{self.API_URL_BASE}{endpoint}"

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error("API request error: %s", e)
            raise RuntimeError(f"Ошибка API запроса: {str(e)}") from e

    def __handle_pokemon_info(self, message: telebot_types.Message, pokemon_name: str) -> None:
        """Handle request for Pokémon information"""
        chat_id = message.chat.id

        self.bot.send_message(chat_id, f"Получаю информацию о покемоне {pokemon_name}...")

        try:
            # Get Pokémon data
            data = self.__make_api_request(f"pokemon/{pokemon_name.lower()}")
            # Format response
            response = self.__format_pokemon_info(data)
            # Create markup with actions
            markup = self.__create_pokemon_detail_markup(pokemon_name)
            # Send Pokémon sprite if available
            if data.get("sprites") and data["sprites"].get("front_default"):
                self.bot.send_photo(
                    chat_id,
                    data["sprites"]["front_default"],
                    caption=response,
                    parse_mode="Markdown",
                    reply_markup=markup
                )
            else:
                self.bot.send_message(
                    chat_id,
                    response,
                    parse_mode="Markdown",
                    reply_markup=markup
                )

        except (KeyError, ValueError, RuntimeError) as ex:
            logging.exception("Error fetching Pokémon info: %s", ex)
            self.bot.send_message(chat_id, f"Ошибка при получении данных: {str(ex)}")

    def __handle_random_pokemon(self, message: telebot_types.Message) -> None:
        """Handle request for a random Pokémon"""
        chat_id = message.chat.id
        self.bot.send_message(chat_id, "Выбираю случайного покемона из Покедекса...")

        try:
            # Get total count of Pokémon
            data = self.__make_api_request("pokemon-species")
            count = data.get("count", 898)  # Default to 898 if count not available
            # Get a random Pokémon ID (limiting to original 898 to avoid forms)
            random_id = random.randint(1, min(count, 898))
            # Get Pokémon data
            pokemon_data = self.__make_api_request(f"pokemon/{random_id}")
            pokemon_name = pokemon_data["name"]
            # Show the Pokémon info
            self.__handle_pokemon_info(message, pokemon_name)
        except (KeyError, ValueError, RuntimeError) as ex:
            logging.exception("Error fetching random Pokémon: %s", ex)
            self.bot.send_message(chat_id, f"Ошибка при получении данных: {str(ex)}")

    def __format_pokemon_info(self, pokemon_data: Dict[str, Any]) -> str:
        """Format Pokémon information"""
        # Get basic info
        name = pokemon_data["name"].capitalize()
        pokemon_id = pokemon_data["id"]
        height = pokemon_data["height"] / 10  # Convert to meters
        weight = pokemon_data["weight"] / 10  # Convert to kg
        # Get types
        types = [t["type"]["name"].capitalize() for t in pokemon_data["types"]]
        types_str = ", ".join(types)
        # Format response
        response = (
            f"🔍 *{name}* (#{pokemon_id})\n\n"
            f"📊 *Тип:* {types_str}\n"
            f"📏 *Рост:* {height} м\n"
            f"⚖️ *Вес:* {weight} кг\n\n"
        )
        # Add base experience
        if "base_experience" in pokemon_data:
            response += f"✨ *Базовый опыт:* {pokemon_data['base_experience']}\n\n"
        return response

    def __create_pokemon_detail_markup(self, pokemon_name: str):
        """Create markup for Pokémon details"""
        markup = telebot_types.InlineKeyboardMarkup(row_width=2)
        stats_callback = self.pokemon_keyboard_factory.new(
            action="stats",
            pokemon_name=pokemon_name
        )
        abilities_callback = self.pokemon_keyboard_factory.new(
            action="abilities",
            pokemon_name=pokemon_name
        )

        markup.add(
            telebot_types.InlineKeyboardButton("📊 Статистика", callback_data=stats_callback),
            telebot_types.InlineKeyboardButton("✨ Способности", callback_data=abilities_callback),
        )

        return markup

    def __send_pokemon_stats(self, chat_id: int, pokemon_name: str) -> None:
        """Send statistics for a specific Pokémon"""
        try:
            # Get Pokémon data
            data = self.__make_api_request(f"pokemon/{pokemon_name.lower()}")
            # Format stats
            stats = data["stats"]
            stats_text = f"📊 *Статистика {pokemon_name.capitalize()}:*\n\n"
            for stat in stats:
                stat_name = stat["stat"]["name"]
                base_value = stat["base_stat"]
                # Translate stat names to Russian
                if stat_name == "hp":
                    stat_name = "HP (здоровье)"
                elif stat_name == "attack":
                    stat_name = "Атака"
                elif stat_name == "defense":
                    stat_name = "Защита"
                elif stat_name == "special-attack":
                    stat_name = "Спец. атака"
                elif stat_name == "special-defense":
                    stat_name = "Спец. защита"
                elif stat_name == "speed":
                    stat_name = "Скорость"
                stats_text += f"• *{stat_name}:* {base_value}\n"
            # Create markup with back button
            markup = telebot_types.InlineKeyboardMarkup()
            back_callback = self.pokemon_keyboard_factory.new(
                action="back", pokemon_name=pokemon_name
            )
            markup.add(
                telebot_types.InlineKeyboardButton(
                    "🔙 Назад", callback_data=back_callback
                )
            )
            self.bot.send_message(
                chat_id,
                stats_text,
                parse_mode="Markdown",
                reply_markup=markup
            )
        except (KeyError, ValueError, RuntimeError) as ex:
            logging.exception("Error fetching Pokémon stats: %s", ex)
            self.bot.send_message(chat_id, f"Ошибка при получении статистики: {str(ex)}")

    def __send_pokemon_abilities(self, chat_id: int, pokemon_name: str) -> None:
        """Send abilities for a specific Pokémon"""
        try:
            # Get Pokémon data
            data = self.__make_api_request(f"pokemon/{pokemon_name.lower()}")
            # Format abilities
            abilities = data["abilities"]
            abilities_text = f"✨ *Способности {pokemon_name.capitalize()}:*\n\n"
            for ability in abilities:
                ability_name = ability["ability"]["name"].replace("-", " ").capitalize()
                is_hidden = ability["is_hidden"]
                if is_hidden:
                    abilities_text += f"• *{ability_name}* (скрытая)\n"
                else:
                    abilities_text += f"• *{ability_name}*\n"
                # Get ability description
                try:
                    ability_data = self.__make_api_request(f"ability/{ability['ability']['name']}")
                    # Find Russian or English description
                    description = None
                    for entry in ability_data["effect_entries"]:
                        if entry["language"]["name"] == "en":
                            description = entry["effect"]
                            break
                    if description:
                        # Truncate if too long
                        if len(description) > 100:
                            description = description[:97] + "..."
                        abilities_text += f"  {description}\n\n"
                    else:
                        abilities_text += "\n"
                except (requests.RequestException, KeyError, ValueError) as ex:
                    logging.debug("Error fetching ability details: %s", ex)
                    abilities_text += "\n"
            # Create markup with back button
            markup = telebot_types.InlineKeyboardMarkup()
            back_callback = self.pokemon_keyboard_factory.new(
                action="back", pokemon_name=pokemon_name
            )
            markup.add(
                telebot_types.InlineKeyboardButton(
                    "🔙 Назад", callback_data=back_callback
                )
            )
            self.bot.send_message(
                chat_id,
                abilities_text,
                parse_mode="Markdown",
                reply_markup=markup
            )
        except (KeyError, ValueError, RuntimeError) as ex:
            logging.exception("Error fetching Pokémon abilities: %s", ex)
            self.bot.send_message(chat_id, f"Ошибка при получении способностей: {str(ex)}")

    def __send_help(self, message: telebot_types.Message) -> None:
        """Send help information about available commands"""
        help_text = (
            "*Команды для работы с Покемонами:*\n\n"
            "/pokemon [имя] - показать информацию о конкретном покемоне\n"
            "/pokedex - показать случайного покемона из Покедекса\n\n"
            "Используйте эти команды для получения информации о покемонах."
        )

        self.bot.send_message(message.chat.id, help_text, parse_mode="Markdown")
