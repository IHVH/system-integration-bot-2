"""
Модуль содержит реализацию атомарной функции телеграм-бота
для взаимодействия с FreeCurrencyAPI.
"""

import os
import logging
from typing import List, Optional, Dict, Any, Tuple

import requests
import telebot
from telebot import types
from bot_func_abc import AtomicBotFunctionABC


class FreeCurrencyAPIClientError(Exception):
    """Пользовательское исключение для ошибок клиента FreeCurrencyAPI."""


class FreeCurrencyAPIClient:
    """Клиент для взаимодействия с FreeCurrencyAPI."""

    BASE_URL = "https://api.freecurrencyapi.com/v1/"

    def __init__(self, api_key: Optional[str] = None):
        """
        Инициализирует клиент. Получает ключ API из аргумента или
        переменной окружения FREE_CURRENCY_API_KEY.

        Args:
            api_key: Необязательная строка с ключом API. Если None,
                     пытается прочитать из переменной окружения FREE_CURRENCY_API_KEY.

        Raises:
            ValueError: Если ключ API не предоставлен и переменная окружения не установлена.
        """
        self.api_key = api_key if api_key else os.environ.get("FREE_CURRENCY_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Требуется ключ API для FreeCurrencyAPI. "
                "Установите переменную окружения FREE_CURRENCY_API_KEY или передайте ключ."
            )
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def _handle_api_specific_error(
        self, response: requests.Response, status_code: int
    ) -> None:
        """
        Обрабатывает специфические HTTP-ошибки от API
        и вызывает FreeCurrencyAPIClientError.

        Args:
            response: Объект requests.Response.
            status_code: HTTP-код статуса.

        Raises:
            FreeCurrencyAPIClientError: Всегда вызывает исключение на основе деталей ошибки.
        """
        error_detail = response.text[:200] if response is not None else "N/A"
        self.logger.error(
            "HTTP ошибка %s от API. Тело ответа: %s", status_code, error_detail
        )

        http_error_exc = requests.exceptions.HTTPError(
            f"HTTP статус: {status_code}", response=response
        )

        if status_code == 401:
            raise FreeCurrencyAPIClientError(
                f"Неверный ключ API или неавторизованный запрос (Статус {status_code})."
            ) from http_error_exc

        if status_code == 403:
            raise FreeCurrencyAPIClientError(
                f"Лимит использования API превышен или проблема с подпиской (Статус {status_code})."
            ) from http_error_exc

        if status_code == 404:
            raise FreeCurrencyAPIClientError(
                f"Эндпоинт API не найден (Статус {status_code})."
            ) from http_error_exc

        try:
            if response is not None and response.text:
                error_data = response.json()
                if isinstance(error_data, dict) and "message" in error_data:
                    raise FreeCurrencyAPIClientError(
                        f"Ошибка API (Статус {status_code}): {error_data['message']}"
                    ) from http_error_exc
        except requests.exceptions.JSONDecodeError:
            pass

        raise FreeCurrencyAPIClientError(
            f"HTTP ошибка {status_code} от API."
        ) from http_error_exc

    def _process_response_data(
        self, data: Dict[str, Any], response: requests.Response
    ) -> Optional[Dict[str, Any]]:
        """
        Вспомогательная функция для обработки данных ответа API после парсинга JSON.
        Проверяет наличие сообщений об ошибках API и ключа 'data'.

        Args:
            data: Словарь с данными, полученными после парсинга JSON ответа.
            response: Оригинальный объект ответа requests (для контекста).

        Returns:
            Словарь, содержащий часть 'data' ответа API, если она присутствует
            и нет явных сообщений об ошибке API.
            Возвращает None, если ответ является словарем, но отсутствует
            ожидаемый ключ 'data' и не присутствует явное сообщение об ошибке API
            в ключе 'message'.
        """
        if isinstance(data, dict) and "message" in data:
            api_error_message = data.get(
                "message", "Неизвестное сообщение об ошибке API"
            )
            self.logger.error("API вернуло сообщение об ошибке: %s", api_error_message)
            raise FreeCurrencyAPIClientError(
                f"API вернуло ошибку: {api_error_message}"
            ) from requests.exceptions.RequestException(
                f"API message: {api_error_message}"
            )

        if isinstance(data, dict) and "data" in data:
            return data["data"]
        response_text_preview = response.text[:500] if response else "N/A"
        self.logger.warning(
            "Неожиданная структура ответа API. " + "Ожидали {'data': ...}, получили: %s",
            response_text_preview,
        )
        return None

    def _make_request(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Внутренняя вспомогательная функция для выполнения запросов к API.
        Выполняет запрос, обрабатывает сетевые ошибки, ошибки статуса HTTP
        и ошибки парсинга JSON. Делегирует обработку структуры данных
        методу _process_response_data.

        Args:
            endpoint: Эндпоинт API (например, "latest", "currencies").
            params: Словарь параметров запроса.

        Returns:
            Результат вызова _process_response_data (Dict[str, Any] или None).
        """
        url = self.BASE_URL + endpoint
        all_params = params.copy() if params else {}
        all_params["apikey"] = self.api_key

        response = None
        data = None

        try:
            log_message = "Выполнение запроса к API %s " + "с параметрами %s"
            self.logger.debug(log_message, url, all_params)

            response = requests.get(url, params=all_params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return self._process_response_data(data, response)

        except requests.exceptions.Timeout as e:
            self.logger.error("Время ожидания запроса к API истекло: %s", e)
            raise FreeCurrencyAPIClientError(
                "Время ожидания запроса к API истекло (10 секунд)."
            ) from e

        except requests.exceptions.ConnectionError as e:
            self.logger.error("Ошибка соединения с API: %s", e)
            raise FreeCurrencyAPIClientError(f"Ошибка соединения с API: {e}") from e

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else "N/A"
            error_details = f"Статус: {status_code}"
            if e.response is not None:
                try:
                    error_json = e.response.json()
                    if isinstance(error_json, dict) and "message" in error_json:
                        error_details += f", Сообщение API: {error_json['message']}"
                    else:
                        error_details += f", Ответ: {e.response.text[:200]}..."
                except requests.exceptions.JSONDecodeError:
                    error_details += f", Ответ (не JSON): {e.response.text[:200]}..."

            self.logger.error(
                "HTTP ошибка при запросе к API: %s (%s)", e, error_details
            )
            raise FreeCurrencyAPIClientError(
                f"HTTP ошибка при запросе к API: {e} ({error_details})"
            ) from e

        except requests.exceptions.JSONDecodeError as e:
            response_text_preview = response.text[:500] if response else "N/A"
            self.logger.error(
                "Не удалось распарсить JSON. Превью текста ответа: %s",
                response_text_preview,
            )
            raise FreeCurrencyAPIClientError(
                f"Не удалось распарсить JSON ответ от API: {e}"
            ) from e

        except requests.exceptions.RequestException as e:
            self.logger.error("Общая ошибка запроса requests: %s", e)
            raise FreeCurrencyAPIClientError(f"HTTP запрос не удался: {e}") from e

        except Exception as e:
            self.logger.exception(
                "Произошла непредвиденная ошибка во время запроса к API: %s", e
            )
            raise FreeCurrencyAPIClientError(
                f"Произошла непредвиденная ошибка во время взаимодействия с API: {e}"
            ) from e

    def get_supported_currencies(self) -> List[str]:
        """
        Получает список поддерживаемых кодов валют от API.

        Returns:
            Список кодов валют (например, ["AED", "AFN", ...]).

        Raises:
            FreeCurrencyAPIClientError: Если запрос к API не удался.
        """
        self.logger.info("Получение поддерживаемых валют...")
        try:
            currencies_data = self._make_request("currencies")
            # API возвращает словарь { "AED": {...}, "AFN": {...}, ... }
            # Извлекаем только коды валют (ключи словаря)
            currency_codes = list(currencies_data.keys())
            self.logger.info("Получено %d валют.", len(currency_codes))
            return currency_codes
        except FreeCurrencyAPIClientError as e:
            self.logger.error("Не удалось получить валюты: %s", e)
            raise

    def get_exchange_rate(
        self, target_currency: str, base_currency: str = "USD"
    ) -> float:
        """
        Получает последний курс обмена для целевой валюты
        относительно базовой валюты.

        Args:
            target_currency: Код валюты, курс которой нужно узнать (например, "EUR").
            base_currency: Код базовой валюты (например, "USD"). Бесплатный тариф
                           может ограничивать базовую валюту (часто разрешен только USD).

        Returns:
            Курс обмена (число с плавающей точкой).

        Raises:
            FreeCurrencyAPIClientError: Если запрос к API не удался или вернул ошибку
                                        (включая случай, когда курс не найден).
        """
        self.logger.info(
            "Получение курса для %s к %s...", target_currency, base_currency
        )
        # Эндпоинт API /latest требует символы, разделенные запятыми,
        # но мы запрашиваем только один
        params = {
            "base_currency": base_currency.upper(),
            "symbols": target_currency.upper(),
        }
        try:
            rates_data = self._make_request("latest", params=params)

            # API возвращает { "TARGET": значение_курса }. Проверяем наличие ключа.
            target_currency_upper = target_currency.upper()
            if target_currency_upper in rates_data:
                rate = rates_data[target_currency_upper]
                self.logger.info(
                    "Курс получен: 1 %s = %s %s",
                    base_currency.upper(),
                    rate,
                    target_currency_upper,
                )
                return rate

            self.logger.warning(
                "Курс для %s не найден в данных ответа для базовой валюты %s.",
                target_currency,
                base_currency,
            )
            raise FreeCurrencyAPIClientError(
                f"Данные курса для {target_currency} не найдены в ответе API "
                f"для базовой валюты {base_currency}."
            )

        except FreeCurrencyAPIClientError as e:
            self.logger.error(
                "Не удалось получить курс для %s/%s: %s",
                target_currency,
                base_currency,
                e,
            )
            raise


class AtomicCurrencyBotFunction(AtomicBotFunctionABC):
    """
    Функция Telegram-бота для получения информации о валютах из FreeCurrencyAPI.
    """

    commands: List[str] = ["currencies", "rate"]
    authors: List[str] = ["Yurmen2"]
    about: str = "Информация о валютах и курсах"
    description: str = """
    Предоставляет список поддерживаемых валют и их курсы
    через FreeCurrencyAPI.

    *Использование:*

    `/currencies` - Показать список всех кодов валют.

    `/rate <TARGET> <BASE>` - Показать курс обмена.
    `<TARGET>` - Код валюты, курс которой вы хотите узнать (напр., `EUR`).
    `<BASE>` - Код базовой валюты (напр., `USD`).
    Пример: `/rate EUR USD`

    Для работы функции требуется переменная окружения
    `FREE_CURRENCY_API_KEY` с вашим ключом API.
    """
    state: bool = True

    bot: telebot.TeleBot
    api_client: Optional[FreeCurrencyAPIClient] = None
    logger: logging.Logger

    def __init__(self):
        """Инициализация логгера."""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def _parse_rate_args(self, message_text: str) -> Optional[Tuple[str, str]]:
        """
        Парсит и валидирует коды валют из аргументов команды /rate.

        Args:
            message_text: Полный текст сообщения пользователя.

        Returns:
            Кортеж (целевая_валюта, базовая_валюта) в верхнем регистре,
            если аргументы валидны, иначе None.
        """
        args = message_text.split()[1:]

        if (
            len(args) != 2
            or not args[0].isalpha()
            or len(args[0]) != 3
            or not args[1].isalpha()
            or len(args[1]) != 3
        ):
            return None

        return args[0].upper(), args[1].upper()

    def _get_and_send_currency_rate(
        self,
        chat_id: int,
        target_currency: str,
        base_currency: str,
        message: types.Message,
    ) -> None:
        """
        Получает курс валюты и отправляет результат сообщения.
        Выделено из handle_rate для уменьшения количества операторов.

        Args:
            chat_id: ID чата Telegram для отправки сообщения.
            target_currency: Код целевой валюты.
            base_currency: Код базовой валюты.
            message: Исходный объект сообщения (для reply_to).
        """
        self.bot.send_message(
            chat_id,
            f"Загружаю курс {target_currency} к {base_currency}...",
        )

        try:
            if self.api_client is None:
                self.bot.send_message(
                    chat_id,
                    "Ошибка: API клиент не инициализирован. Не могу получить курс.",
                )
                return

            rate = self.api_client.get_exchange_rate(
                target_currency, base_currency=base_currency
            )

            # get_exchange_rate выбрасывает ошибку, если курс не найден
            if rate is not None:
                response_text = f"1 {base_currency} = {rate:.4f} {target_currency}"
                self.bot.send_message(chat_id, response_text)

        except FreeCurrencyAPIClientError as e:
            self.logger.error(
                "Ошибка при получении курса для %s/%s для чата %d: %s",
                target_currency,
                base_currency,
                chat_id,
                e,
            )
            self.bot.reply_to(message, f"Ошибка при получении курса: {e}")

    def set_handlers(self, bot: telebot.TeleBot):
        """Устанавливает обработчики сообщений для команд /currencies и /rate."""
        self.bot = bot
        try:
            # Инициализируем клиент API при установке хэндлеров
            self.api_client = FreeCurrencyAPIClient()
            self.logger.info("FreeCurrencyAPIClient успешно инициализирован.")
        except ValueError as e:
            self.logger.error(
                "Не удалось инициализировать FreeCurrencyAPIClient: %s", e
            )
            print(
                f"КРИТИЧЕСКАЯ ОШИБКА: Не удалось инициализировать FreeCurrencyAPIClient: {e}"
            )
            self.api_client = None  # Устанавливаем None, если инициализация не удалась

        @bot.message_handler(commands=[self.commands[0]])
        def handle_currencies_inner(message: types.Message):
            """Обрабатывает команду /currencies."""
            if self.api_client is None:
                self.bot.reply_to(
                    message, "Ошибка: API клиент не инициализирован. Проверьте логи."
                )
                return

            chat_id = message.chat.id
            self.logger.info("Получена команда /currencies из чата %d", chat_id)
            self.bot.send_message(chat_id, "Загружаю список поддерживаемых валют...")

            try:
                currencies = self.api_client.get_supported_currencies()
                if currencies:
                    currencies_list_text = ", ".join(sorted(currencies))
                    response_text = (
                        f"Поддерживаемые валюты ({len(currencies)}): \n"
                        f"`{currencies_list_text}`"
                    )
                    if len(response_text) > 4000:
                        response_text = (
                            f"Поддерживаемые валюты ({len(currencies)}): \n"
                            + ", ".join(sorted(currencies)[:200])
                            + "...\n(Список слишком длинный, показаны первые 200 кодов)"
                        )

                    self.bot.send_message(chat_id, response_text, parse_mode="Markdown")
                else:
                    self.bot.send_message(
                        chat_id, "Не удалось получить список поддерживаемых валют."
                    )

            except FreeCurrencyAPIClientError as e:
                self.logger.error(
                    "Ошибка при получении валют для чата %d: %s", chat_id, e
                )
                self.bot.reply_to(message, f"Ошибка при получении списка валют: {e}")

        @bot.message_handler(commands=[self.commands[1]])
        def handle_rate_inner(message: types.Message):
            """Обрабатывает команду /rate."""
            if self.api_client is None:
                self.bot.reply_to(
                    message, "Ошибка: API клиент не инициализирован. Проверьте логи."
                )
                return

            chat_id = message.chat.id
            self.logger.info("Получена команда /rate из чата %d", chat_id)

            arg_result = self._parse_rate_args(message.text)

            if arg_result is None:
                self.bot.reply_to(
                    message,
                    "Неверный формат команды. Используйте: `/rate <TARGET> <BASE>`\n"
                    "Пример: `/rate EUR USD`\n"
                    "Коды валют должны состоять из 3 букв (например, EUR, USD, RUB).",
                    parse_mode="Markdown",
                )
                return

            target_currency, base_currency = arg_result

            self._get_and_send_currency_rate(
                chat_id, target_currency, base_currency, message
            )
