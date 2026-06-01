"""Атомарная функция Telegram-бота для сокращения ссылок через Ulvis."""

import logging

import requests
import telebot
from telebot import types

from bot_func_abc import AtomicBotFunctionABC

logger = logging.getLogger(__name__)


class UlvisUrlShortenerError(Exception):
    """Ошибка при работе с сервисом сокращения ссылок Ulvis."""

    def __init__(self, message: str) -> None:
        """Инициализирует ошибку с сообщением для пользователя."""

        self.message = message
        super().__init__(message)


class ShortenCommandError(Exception):
    """Ошибка в пользовательской команде /shorten."""

    def __init__(self, message: str) -> None:
        """Инициализирует ошибку с сообщением для пользователя."""

        self.message = message
        super().__init__(message)


class UlvisUrlShortener:
    """Клиент для сокращения ссылок через API Ulvis."""

    DEFAULT_API_URL = "https://ulvis.net/API/write/post"
    DEFAULT_TIMEOUT = 10
    API_ERROR_MESSAGES = {
        "invalid url": (
            "Некорректная ссылка. "
            "Проверьте, что она начинается с http:// или https://."
        ),
        "custom-taken": "Это имя для короткой ссылки уже занято.",
    }
    DEFAULT_ERROR_MESSAGE = "Не удалось сократить ссылку. Попробуйте позже."

    def __init__(
        self,
        api_url: str = DEFAULT_API_URL,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Инициализирует клиент Ulvis API."""

        self.api_url = api_url
        self.timeout = timeout

    def _build_payload(
        self,
        url: str,
        custom_name: str | None = None,
        password: str | None = None,
    ) -> dict[str, str]:
        """Формирует данные запроса для сокращения ссылки."""

        payload: dict[str, str] = {
            "url": url,
            "type": "json",
        }

        if custom_name is not None:
            payload["custom"] = custom_name

        if password is not None:
            payload["password"] = password

        return payload

    def _send_request(self, payload: dict[str, str]) -> dict[str, object]:
        """Отправляет запрос в Ulvis API и возвращает JSON-ответ."""

        try:
            response = requests.post(
                url=self.api_url,
                data=payload,
                timeout=self.timeout,
            )

            response.raise_for_status()
            return response.json()

        except requests.RequestException as error:
            raise UlvisUrlShortenerError(
                self.DEFAULT_ERROR_MESSAGE,
            ) from error

        except ValueError as error:
            raise UlvisUrlShortenerError(
                "Сервис вернул некорректный ответ.",
            ) from error

    def _extract_short_url(self, data: dict[str, object]) -> str:
        """Извлекает короткую ссылку из ответа Ulvis API."""

        result = data.get("data", {})
        short_url = result.get("url")

        if short_url:
            return short_url

        message = data.get("error", {}).get("msg") or result.get("status")
        raise UlvisUrlShortenerError(
            self.API_ERROR_MESSAGES.get(
                message,
                self.DEFAULT_ERROR_MESSAGE,
            )
        )

    def shorten(
        self,
        url: str,
        custom_name: str | None = None,
        password: str | None = None,
    ) -> str:
        """Сокращает ссылку и возвращает короткий URL."""

        payload = self._build_payload(url, custom_name, password)
        response = self._send_request(payload=payload)
        return self._extract_short_url(response)


class UlvisShortenerBotFunction(AtomicBotFunctionABC):
    """Функция бота для сокращения ссылок через Ulvis."""

    commands: list[str] = ["shorten"]
    authors: list[str] = ["artemsekta"]
    about: str = "Сокращение ссылок"
    description: str = (
        "Команда /shorten сокращает длинную ссылку через сервис Ulvis. "
        "Использование: /shorten <url> [custom_name] [password]. "
        "custom_name и password являются необязательными параметрами."
    )
    state: bool = True

    USAGE_MESSAGE = "Использование: /shorten <url> [custom_name] [password]."
    PASSWORD_LENGTH_ERROR = "Пароль должен быть не длиннее 10 символов."

    def __init__(self) -> None:
        """Инициализирует клиент сокращателя ссылок и хранилище бота."""

        self.shortener: UlvisUrlShortener = UlvisUrlShortener()
        self.bot: telebot.TeleBot | None = None

    def set_handlers(self, bot: telebot.TeleBot) -> None:
        """Регистрирует обработчики сообщений."""

        self.bot = bot
        logger.info("Регистрируется обработчик команды /shorten")

        @bot.message_handler(commands=self.commands)
        def ulvis_shortener_handler(message: types.Message) -> None:
            logger.info(
                "Получена команда сокращения ссылки: chat_id=%s user_id=%s",
                message.chat.id,
                message.from_user.id if message.from_user else None,
            )
            self._handle_shorten_message(message)

    def _handle_shorten_message(self, message: types.Message) -> None:
        """Обрабатывает команду сокращения ссылки и отправляет ответ пользователю."""

        try:
            url, custom_name, password = self._parse_shorten_command(message.text)

            short_url = self.shortener.shorten(
                url=url,
                custom_name=custom_name,
                password=password,
            )

            self.bot.send_message(
                chat_id=message.chat.id,
                text=short_url,
            )
            logger.info(
                "Ссылка успешно сокращена: chat_id=%s custom_name=%s",
                message.chat.id,
                custom_name,
            )

        except ShortenCommandError as error:
            logger.info(
                "Некорректная команда сокращения ссылки: chat_id=%s error=%s",
                message.chat.id,
                error.message,
            )
            self.bot.send_message(
                chat_id=message.chat.id,
                text=error.message,
            )

        except UlvisUrlShortenerError as error:
            logger.warning(
                "Не удалось сократить ссылку через Ulvis: chat_id=%s error=%s",
                message.chat.id,
                error.message,
            )
            self.bot.send_message(
                chat_id=message.chat.id,
                text=error.message,
            )

    def _parse_shorten_command(
        self,
        text: str,
    ) -> tuple[str, str | None, str | None]:
        """Парсит команду /shorten и возвращает url, custom_name и password."""

        parts = text.split()

        if len(parts) > 4 or len(parts) < 2:
            raise ShortenCommandError(self.USAGE_MESSAGE)

        _, url, *optional = parts
        custom_name, password = (optional + [None, None])[:2]

        if password is not None and len(password) > 10:
            raise ShortenCommandError(self.PASSWORD_LENGTH_ERROR)

        return url, custom_name, password
