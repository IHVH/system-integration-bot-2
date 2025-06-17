# src/functions/atomic/random_user_function.py

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
                    try:
                        formatted_data = self._format_user_data(api_response_data)
                        self.bot.send_message(
                            chat_id, formatted_data, parse_mode="Markdown"
                        )
                    except (KeyError, TypeError, IndexError, AttributeError) as fmt_e:
                        logging.exception("Error formatting user data: %s", fmt_e)
                        error_msg = (
                            f"Произошла ошибка при форматировании данных пользователя: {fmt_e}\n\n"
                            f"Сырые данные (частично):\n`{api_response_data}`"
                        )
                        self.bot.send_message(chat_id, error_msg)

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
            "Извлечение данных пользователя из %s " + "с параметрами: %s",
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

    def _format_name(self, user_data: Dict[str, Any]) -> str:
        """Форматирует блок 'name'."""
        name = user_data.get("name", {})
        full_name = (
            f"{name.get('title', '')} {name.get('first', '')} "
            f"{name.get('last', '')}"
        ).strip()
        return f"*Имя:* {full_name}\n"

    def _format_location(self, user_data: Dict[str, Any]) -> str:
        """Форматирует блок 'location'."""
        location = user_data.get("location", {})
        street = location.get("street", {})
        street_number_str = (
            str(street.get("number", "")) if street.get("number") is not None else ""
        )
        street_address = f"{street_number_str} {street.get('name', '')}".strip()

        coordinates = location.get("coordinates", {})
        latitude = coordinates.get("latitude", "")
        longitude = coordinates.get("longitude", "")
        timezone = location.get("timezone", {})
        timezone_offset = timezone.get("offset", "")
        timezone_description = timezone.get("description", "")

        return (
            f"*Локация:*\n"
            f"  Улица: {street_address}\n"
            f"  Город: {location.get('city', '')}\n"
            f"  Штат: {location.get('state', '')}\n"
            f"  Страна: {location.get('country', '')}\n"
            f"  Почтовый индекс: {location.get('postcode', '')}\n"
            f"  Координаты: {latitude}, "
            f"{longitude}\n"
            f"  Часовой пояс: {timezone_offset} ({timezone_description})\n\n"
        )

    def _format_contacts(self, user_data: Dict[str, Any]) -> str:
        """Форматирует контактные данные (email, phone, cell)."""
        return (
            f"*Контакты:*\n"
            f"  Email: `{user_data.get('email', '')}`\n"
            f"  Телефон: {user_data.get('phone', '')}\n"
            f"  Сотовый: {user_data.get('cell', '')}\n\n"
        )

    def _format_login(self, user_data: Dict[str, Any]) -> str:
        """Форматирует блок 'login'."""
        login = user_data.get("login", {})
        return (
            f"*Логин:*\n"
            f"  Имя пользователя: `{login.get('username', '')}`\n"
            f"  Пароль: `{login.get('password', '')}`\n"
            f"  UUID: `{login.get('uuid', '')}`\n\n"
        )

    def _format_dob_registered(self, user_data: Dict[str, Any]) -> str:
        """Форматирует блоки 'dob' и 'registered'."""
        dob = user_data.get("dob", {})
        registered = user_data.get("registered", {})

        dob_date_str = dob.get("date", "")
        reg_date_str = registered.get("date", "")

        return (
            f"*Дата рождения:*\n"
            f"  Дата: {dob_date_str}\n"
            f"  Возраст: {dob.get('age', '')}\n\n"
            f"*Дата регистрации:*\n"
            f"  Дата: {reg_date_str}\n"
            f"  Возраст: {registered.get('age', '')}\n\n"
        )

    def _format_id(self, user_data: Dict[str, Any]) -> str:
        """Форматирует блок 'id'."""
        user_id_info = user_data.get("id", {})
        return (
            f"*ID:*\n"
            f"  Тип: {user_id_info.get('name', '')}\n"
            f"  Значение: {user_id_info.get('value', '')}\n\n"
        )

    def _format_picture(self, user_data: Dict[str, Any]) -> str:
        """Форматирует блок 'picture'."""
        picture = user_data.get("picture", {})
        pic_large = picture.get("large", "")
        pic_medium = picture.get("medium", "")
        pic_thumbnail = picture.get("thumbnail", "")

        pic_text = ""
        if pic_large:
            pic_text += f"*Фото (Large):* {pic_large}\n"
        if pic_medium:
            pic_text += f"*Фото (Medium):* {pic_medium}\n"
        if pic_thumbnail:
            pic_text += f"*Фото (Thumbnail):* {pic_thumbnail}\n"

        return pic_text

    def _format_nat(self, user_data: Dict[str, Any]) -> str:
        """Форматирует национальность."""
        return f"*Национальность:* {user_data.get('nat', '')}\n\n"

    def _format_info(self, info_data: Dict[str, Any]) -> str:
        """Форматирует блок 'info' (сид и версия)."""
        seed_value = info_data.get("seed", "N/A")
        api_version = info_data.get("version", "N/A")
        return f"\n---\n" f"*Сид:* `{seed_value}`\n" f"*Версия API:* `{api_version}`"

    def _format_user_data(self, api_response_data: Dict[str, Any]) -> str:
        """
        Форматирует сырые данные ответа API (включая блок info) в удобочитаемую строку
        для отправки в сообщении Telegram, используя Markdown.

        Ловля общих исключений внутри этой функции (W0718) избегается за счет
        разбиения на мелкие функции и переноса общей обработки ошибки на уровень выше
        в handle_random_user, где вызывается эта функция.
        """
        # Извлекаем данные пользователя и info с безопасным доступом
        user_data = api_response_data.get("results", [{}])[0]
        info_data = api_response_data.get("info", {})

        formatted_text_parts = [
            "*Случайный Пользователь:*\n\n",
            self._format_name(user_data),
            f"*Пол:* {user_data.get('gender', '')}\n\n",
            self._format_location(user_data),
            self._format_contacts(user_data),
            self._format_login(user_data),
            self._format_dob_registered(user_data),
            self._format_id(user_data),
            self._format_picture(user_data),
            self._format_nat(user_data),
            self._format_info(info_data),
        ]

        formatted_text = "".join(formatted_text_parts)

        return formatted_text
