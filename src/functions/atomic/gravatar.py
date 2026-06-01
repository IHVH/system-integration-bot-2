"""Атомарная функция Telegram-бота для генерации аватаров через Gravatar."""

import hashlib
import logging

import telebot
from telebot import types

from bot_func_abc import AtomicBotFunctionABC

logger = logging.getLogger(__name__)


class GravatarApiError(Exception):
    """Ошибка при генерации аватара через Gravatar."""

    def __init__(self, message: str) -> None:
        """Инициализирует ошибку с сообщением для пользователя."""

        self.message = message
        super().__init__(message)


class GravatarCommandError(Exception):
    """Ошибка в пользовательской команде /gravatar."""

    def __init__(self, message: str) -> None:
        """Инициализирует ошибку с сообщением для пользователя."""

        self.message = message
        super().__init__(message)


class GravatarApi:
    """Клиент для генерации URL аватаров через Gravatar."""

    BASE_URL = "https://www.gravatar.com/avatar/"
    ALLOWED_STYLES = (
        "monsterid",
        "identicon",
        "wavatar",
        "retro",
        "robohash",
    )

    def _verify_email(self, email: str) -> str:
        """Проверяет базовую корректность email и возвращает очищенное значение."""

        email = email.strip().lower()

        if not email:
            raise GravatarApiError("Email не должен быть пустым.")

        if email.count("@") != 1:
            raise GravatarApiError("Email должен содержать один символ @.")

        if " " in email:
            raise GravatarApiError("Email не должен содержать пробелы.")

        local_part, domain = email.split("@", maxsplit=1)

        if not local_part or not domain:
            raise GravatarApiError("Email должен содержать имя и домен.")

        if "." not in domain:
            raise GravatarApiError("Домен email должен содержать точку.")

        if domain.startswith(".") or domain.endswith("."):
            raise GravatarApiError("Домен email указан некорректно.")

        return email

    def _hash_email(self, email: str) -> str:
        """Хеширует email и возвращает хеш SHA-256."""

        return hashlib.sha256(email.encode()).hexdigest()

    def _validate_style(self, style: str) -> str:
        """Проверяет стиль аватара и возвращает очищенное значение."""

        style = style.strip().lower()

        if style not in self.ALLOWED_STYLES:
            allowed_styles = ", ".join(self.ALLOWED_STYLES)
            raise GravatarApiError(
                "Неподдерживаемый стиль аватара. "
                f"Доступные стили: {allowed_styles}."
            )

        return style

    def _create_url(self, email_hash: str, style: str) -> str:
        """Создает URL для хеша email и стиля аватара."""

        return f"{self.BASE_URL}{email_hash}?d={style}&f=y"

    def create_gravatar(self, email: str, style: str | None = None) -> list[str]:
        """Создает ссылки на аватары Gravatar."""

        email = self._verify_email(email)
        email_hash = self._hash_email(email)

        selected_styles = (
            self.ALLOWED_STYLES
            if style is None
            else [self._validate_style(style)]
        )

        return [
            self._create_url(email_hash, selected_style)
            for selected_style in selected_styles
        ]


class GravatarBotFunction(AtomicBotFunctionABC):
    """Функция бота для генерации аватаров через Gravatar."""

    commands: list[str] = ["gravatar"]
    authors: list[str] = ["ksenia-teplova"]
    about: str = "Генерация аватаров Gravatar"
    description: str = (
        "Команда /gravatar генерирует аватары Gravatar по email. "
        "Использование: /gravatar <email> [style]. "
        "style является необязательным параметром. "
        "Доступные стили: monsterid, identicon, wavatar, retro, robohash."
    )
    state: bool = True

    def __init__(self) -> None:
        """Инициализирует клиент Gravatar и хранилище бота."""

        self.gravatar: GravatarApi = GravatarApi()
        self.bot: telebot.TeleBot | None = None

    def set_handlers(self, bot: telebot.TeleBot) -> None:
        """Регистрирует обработчики сообщений."""

        self.bot = bot
        logger.info("Регистрируется обработчик команды /gravatar")

        @bot.message_handler(commands=self.commands)
        def gravatar_message_handler(message: types.Message) -> None:
            """Обрабатывает команду /gravatar."""

            logger.info(
                "Получена команда /gravatar: chat_id=%s user_id=%s",
                message.chat.id,
                message.from_user.id if message.from_user else None,
            )

            try:
                email, style = self._parse_gravatar_command(message.text)
                photos = self.gravatar.create_gravatar(email, style)
            except GravatarCommandError as error:
                logger.info(
                    "Некорректная команда /gravatar: chat_id=%s error=%s",
                    message.chat.id,
                    error.message,
                )
                bot.send_message(text=error.message, chat_id=message.chat.id)
                return
            except GravatarApiError as error:
                logger.warning(
                    "Ошибка генерации Gravatar: chat_id=%s error=%s",
                    message.chat.id,
                    error.message,
                )
                bot.send_message(text=error.message, chat_id=message.chat.id)
                return

            media_group = [
                types.InputMediaPhoto(media=photo) for photo in photos
            ]
            bot.send_media_group(media=media_group, chat_id=message.chat.id)

            logger.info(
                "Аватары Gravatar успешно отправлены: chat_id=%s count=%s style=%s",
                message.chat.id,
                len(photos),
                style,
            )

    def _parse_gravatar_command(self, command: str) -> tuple[str, str | None]:
        """Парсит команду /gravatar и возвращает email и стиль аватара."""

        parts = command.split()

        if len(parts) not in (2, 3):
            raise GravatarCommandError(
                "Неверное количество аргументов.\n"
                "Использование: /gravatar email@example.com [style]"
            )

        _, email, *optional = parts
        style = optional[0] if optional else None

        return email, style
