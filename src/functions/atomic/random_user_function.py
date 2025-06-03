"""Модуль реализации атомарной функции для генерации случайных пользователей."""

import logging
from typing import List, Dict, Any
import requests
import telebot
from telebot import types
from bot_func_abc import AtomicBotFunctionABC

RANDOM_USER_API_URL = "https://randomuser.me/api/"


class RandomUserBotFunction(AtomicBotFunctionABC):
    """
    Функция бота для генерации случайных пользовательских данных
    с использованием API Random User Generator.
    Поддерживает генерацию одного случайного пользователя или пользователя по определенному сиду.
    """

    commands: List[str] = ["randomuser", "ru"]
    authors: List[str] = ["doggyshield"]
    about: str = "Создает случайные данные юзера"
    description: str = (
        "Используйте эту команду для получения случайных данных пользователя"
        " (имя, email, адрес, фото и т.д.).\n\n"
        "*Использование:*\n"
        "`/randomuser` - Генерирует случайного пользователя.\n"
        "`/randomuser <seed>` - Генерирует пользователя по указанному сиду. "
        "Использование сида с тем же значением всегда будет возвращать одного "
        "и того же пользователя (для определенной версии API)."
    )
    state: bool = True

    bot: telebot.TeleBot

    def set_handlers(self, bot: telebot.TeleBot):
        """Устанавливает обработчики сообщений для функции случайного пользователя."""

        self.bot = bot

        @bot.message_handler(commands=self.commands)
        def handle_random_user(message: types.Message):
            logging.info(
                "Received command: %s from user %s", message.text, message.from_user.id
            )

            chat_id = message.chat.id
            args = message.text.split()[1:]

            seed = None
            if args:
                seed = args[0]
                logging.info("Seed provided: %s", seed)

            try:
                self.bot.send_chat_action(chat_id, "typing")

                api_response_data = self._fetch_random_user(seed)

                if (
                    api_response_data
                    and "results" in api_response_data
                    and len(api_response_data["results"]) > 0
                ):
                    formatted_data = self._format_user_data(api_response_data)
                    self.bot.send_message(
                        chat_id, formatted_data, parse_mode="Markdown"
                    )
                else:
                    logging.error(
                        "API response does not contain user data in 'results'."
                    )
                    self.bot.send_message(
                        chat_id, "Не удалось получить данные пользователя из API."
                    )

            except requests.exceptions.RequestException as e:
                logging.error("API request failed: %s", e)
                self.bot.send_message(chat_id, f"Ошибка при обращении к API: {e}")
            except Exception as e:
                logging.exception("An unexpected error occurred: %s", e)
                self.bot.send_message(chat_id, f"Произошла внутренняя ошибка: {e}")

    def _fetch_random_user(self, seed: str = None) -> Dict[str, Any] | None:
        """
        Извлекает данные случайного пользователя из API.

        Args:
            seed: Необязательная строка сида для воспроизводимых результатов.

        Returns:
            Словарь, содержащий полные данные ответа API, или None, если извлечение не удалось.
        """
        params = {"results": 1}
        if seed:
            params["seed"] = seed

        logging.info(
            "Извлечение данных пользователя из %s " "с параметрами: %s",
            RANDOM_USER_API_URL,
            params,
        )

        response = requests.get(RANDOM_USER_API_URL, params=params, timeout=10)

        response.raise_for_status()

        data = response.json()

        if "error" in data:
            logging.error("API returned error: %s", data["error"])
            raise requests.exceptions.RequestException(f"API error: {data['error']}")

        return data

    def _format_user_data(self, api_response_data: Dict[str, Any]) -> str:
        """
        Форматирует сырые данные ответа API (включая блок info) в удобочитаемую строку
        для отправки в сообщении Telegram, используя Markdown.
        """
        try:
            user_data = api_response_data.get("results", [{}])[0]
            info_data = api_response_data.get("info", {})

            name = user_data.get("name", {})
            full_name = (
                f"{name.get('title', '')} {name.get('first', '')} "
                f"{name.get('last', '')}"
            ).strip()

            location = user_data.get("location", {})
            street = location.get("street", {})
            street_number_str = (
                str(street.get("number", ""))
                if street.get("number") is not None
                else ""
            )
            street_address = f"{street_number_str} {street.get('name', '')}".strip()

            city = location.get("city", "")
            state = location.get("state", "")
            country = location.get("country", "")
            postcode = location.get("postcode", "")
            coordinates = location.get("coordinates", {})
            latitude = coordinates.get("latitude", "")
            longitude = coordinates.get("longitude", "")
            timezone = location.get("timezone", {})
            timezone_offset = timezone.get("offset", "")
            timezone_description = timezone.get("description", "")

            login = user_data.get("login", {})
            username = login.get("username", "")
            password = login.get("password", "")
            uuid = login.get("uuid", "")

            dob = user_data.get("dob", {})
            dob_date = dob.get("date", "")
            dob_age = dob.get("age", "")

            registered = user_data.get("registered", {})
            reg_date = registered.get("date", "")
            reg_age = registered.get("age", "")

            phone = user_data.get("phone", "")
            cell = user_data.get("cell", "")

            user_id_info = user_data.get("id", {})
            id_name = user_id_info.get("name", "")
            id_value = user_id_info.get("value", "")

            picture = user_data.get("picture", {})
            pic_large = picture.get("large", "")
            pic_medium = picture.get("medium", "")
            pic_thumbnail = picture.get("thumbnail", "")

            nat = user_data.get("nat", "")

            seed_value = info_data.get("seed", "N/A")
            api_version = info_data.get("version", "N/A")

            formatted_text = (
                f"*Случайный Пользователь:*\n\n"
                f"*Имя:* {full_name}\n"
                f"*Пол:* {user_data.get('gender', '')}\n\n"
                f"*Локация:*\n"
                f"  Улица: {street_address}\n"
                f"  Город: {city}\n"
                f"  Штат: {state}\n"
                f"  Страна: {country}\n"
                f"  Почтовый индекс: {postcode}\n"
                f"  Координаты: {latitude}, "
                f"{longitude}\n"
                f"  Часовой пояс: {timezone_offset} ({timezone_description})\n\n"
                f"*Контакты:*\n"
                f"  Email: `{user_data.get('email', '')}`\n"
                f"  Телефон: {phone}\n"
                f"  Сотовый: {cell}\n\n"
                f"*Логин:*\n"
                f"  Имя пользователя: `{username}`\n"
                f"  Пароль: `{password}`\n"
                f"  UUID: `{uuid}`\n\n"
                f"*ID:*\n"
                f"  Тип: {id_name}\n"
                f"  Значение: {id_value}\n\n"
                f"*Дата рождения:*\n"
                f"  Дата: {dob_date}\n"
                f"  Возраст: {dob_age}\n\n"
                f"*Дата регистрации:*\n"
                f"  Дата: {reg_date}\n"
                f"  Возраст: {reg_age}\n\n"
                f"*Национальность:* {nat}\n\n"
            )

            if pic_large:
                formatted_text += f"*Фото (Large):* {pic_large}\n"
            if pic_medium:
                formatted_text += f"*Фото (Medium):* {pic_medium}\n"
            if pic_thumbnail:
                formatted_text += f"*Фото (Thumbnail):* {pic_thumbnail}\n"

            formatted_text += (
                f"\n---\n" f"*Сид:* `{seed_value}`\n" f"*Версия API:* `{api_version}`"
            )

            return formatted_text

        except Exception as e:
            logging.exception("Error formatting user data: %s", e)
            return (
                f"Произошла ошибка при форматировании данных пользователя: {e}\n\n"
                f"Сырые данные (частично):\n`{api_response_data}`"
            )
