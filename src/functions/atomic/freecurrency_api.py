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

try:
    from bot_func_abc import AtomicBotFunctionABC
except ImportError:
    print("Ошибка импорта: bot_func_abc.py не найден. Проверьте путь импорта.")

    class AtomicBotFunctionABC:
        """Заглушка абстрактного класса, если bot_func_abc не найден."""

        commands: List[str] = []
        authors: List[str] = []
        about: str = ""
        description: str = ""
        state: bool = True

        def set_handlers(self):
            """Заглушка метода set_handlers."""
            return []

        def get_handlers(self) -> List:
            """Заглушка метода get_handlers."""
            return []


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
        except Exception as json_e:
            self.logger.warning(
                "Не удалось распарсить ответ ошибки как JSON: %s", json_e
            )

        raise FreeCurrencyAPIClientError(
            f"HTTP ошибка {status_code} от API."
        ) from http_error_exc

    def _make_request(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Внутренняя вспомогательная функция для выполнения запросов к API
        и обработки общих ошибок.

        Args:
            endpoint: Эндпоинт API (например, "latest", "currencies").
            params: Словарь параметров запроса.

        Returns:
            Словарь, содержащий часть 'data' ответа API.

        Raises:
            FreeCurrencyAPIClientError: Если запрос к API не удался,
                                        вернул статус ошибки,
                                        или вернул неожиданные данные.
        """
        url = self.BASE_URL + endpoint
        all_params = params.copy() if params else {}
        all_params["apikey"] = self.api_key

        response = None
        try:
            self.logger.debug(
                "Выполнение запроса к API %s с параметрами %s", url, all_params
            )
            response = requests.get(url, params=all_params, timeout=10)

            response.raise_for_status()

            data = response.json()

            if isinstance(data, dict) and "message" in data:
                api_msg_exc = requests.exceptions.RequestException(
                    f"Сообщение API: {data['message']}"
                )
                raise FreeCurrencyAPIClientError(
                    f"API вернуло ошибку: {data['message']}"
                ) from api_msg_exc

            if isinstance(data, dict) and "data" in data:
                return data["data"]

        except requests.exceptions.Timeout as e:
            raise FreeCurrencyAPIClientError(
                "Время ожидания запроса к API истекло (10 секунд)."
            ) from e

        except requests.exceptions.ConnectionError as e:
            raise FreeCurrencyAPIClientError(f"Ошибка соединения с API: {e}") from e

        except requests.exceptions.HTTPError as e:
            self._handle_api_specific_error(e.response, e.response.status_code)

        except requests.exceptions.RequestException as e:
            raise FreeCurrencyAPIClientError(f"HTTP запрос не удался: {e}") from e

        except ValueError as e:
            response_text = response.text[:500] if response else "N/A"
            self.logger.error(
                "Не удалось распарсить JSON. Текст ответа был: %s", response_text
            )
            raise FreeCurrencyAPIClientError(
                f"Не удалось распарсить JSON ответ от API: {e}"
            ) from e

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

        except Exception as e:
            self.logger.exception(
                "Непредвиденная ошибка в _get_and_send_currency_rate для чата %d: %s",
                chat_id,
                e,
            )
            self.bot.reply_to(message, f"Произошла непредвиденная ошибка: {e}")

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

        @bot.message_handler(commands=["currencies"])
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
            except Exception as e:
                self.logger.exception(
                    "Непредвиденная ошибка в handle_currencies для чата %d: %s",
                    chat_id,
                    e,
                )
                self.bot.reply_to(message, f"Произошла непредвиденная ошибка: {e}")

        @bot.message_handler(commands=["rate"])
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
