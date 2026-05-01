"""Функция Telegram-бота для получения курсов валют через API ЦБ РФ.

Модуль добавляет одну команду:
    /cbrmenu — главное кнопочное меню функции.

Через меню пользователь может:
    1. Получить курс одной валюты к другой.
    2. Перевести сумму из одной валюты в другую.
    3. Посмотреть список пересчёта выбранной валюты.
    4. Открыть инструкцию по использованию.

Данные берутся из официального XML-сервиса Центрального банка России.
API-ключ для работы функции не требуется.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree

import requests
import telebot
from telebot import types

from bot_func_abc import AtomicBotFunctionABC


class CbrCurrencyBotFunction(AtomicBotFunctionABC):
    """Атомарная функция бота для работы с курсами валют ЦБ РФ.

    Функция работает только через кнопочное меню. В списке команд бота
    отображается одна команда /cbrmenu.

    Все пересчёты выполняются через рубль, потому что ЦБ РФ публикует курсы
    иностранных валют по отношению к российскому рублю.
    """

    commands: List[str] = ["cbrmenu"]
    authors: List[str] = ["IHVH"]
    about: str = "Меню курсов валют ЦБ РФ"
    description: str = (
        "Открывает меню работы с курсами валют ЦБ РФ. "
        "Через меню можно узнать курс одной валюты к другой, "
        "перевести сумму между валютами, посмотреть список валют "
        "и открыть инструкцию."
    )
    state: bool = True

    api_url: str = "https://www.cbr.ru/scripts/XML_daily.asp"
    timeout: int = 10

    popular_currencies: Tuple[Tuple[str, str, str], ...] = (
        ("RUB", "🇷🇺", "Российский рубль"),
        ("USD", "🇺🇸", "Доллар США"),
        ("EUR", "🇪🇺", "Евро"),
        ("CNY", "🇨🇳", "Китайский юань"),
        ("TRY", "🇹🇷", "Турецкая лира"),
        ("GBP", "🇬🇧", "Фунт стерлингов"),
        ("JPY", "🇯🇵", "Японская иена"),
        ("CHF", "🇨🇭", "Швейцарский франк"),
        ("KZT", "🇰🇿", "Казахстанский тенге"),
        ("BYN", "🇧🇾", "Белорусский рубль"),
        ("AMD", "🇦🇲", "Армянский драм"),
        ("GEL", "🇬🇪", "Грузинский лари"),
        ("AED", "🇦🇪", "Дирхам ОАЭ"),
    )

    bot: telebot.TeleBot
    user_rate_states: Dict[int, Dict[str, str]]
    user_conversion_states: Dict[int, Dict[str, object]]

    def __init__(self) -> None:
        """Создать внутренние состояния для кнопочных сценариев."""
        self.user_rate_states = {}
        self.user_conversion_states = {}

    def set_handlers(self, bot: telebot.TeleBot) -> None:
        """Зарегистрировать обработчики команды и кнопок Telegram-бота.

        Args:
            bot: Объект Telegram-бота из библиотеки pyTelegramBotAPI.
        """
        self.bot = bot

        @bot.message_handler(commands=[self.commands[0]])
        def cbr_menu_handler(message: types.Message) -> None:
            """Обработать команду /cbrmenu."""
            self._show_main_menu(message.chat.id)

        @bot.callback_query_handler(
            func=lambda call: bool(call.data)
            and call.data.startswith("cbr:")
        )
        def cbr_callback_handler(call: types.CallbackQuery) -> None:
            """Обработать нажатие кнопки из меню ЦБ РФ."""
            self._handle_callback(call)

    def _handle_callback(self, call: types.CallbackQuery) -> None:
        """Обработать callback-запрос от inline-кнопок.

        Args:
            call: Callback-запрос Telegram после нажатия inline-кнопки.
        """
        self.bot.answer_callback_query(call.id)
        chat_id = call.message.chat.id
        data = call.data or ""
        parts = data.split(":")
        action = parts[1] if len(parts) > 1 else ""

        try:
            if action == "menu":
                self._show_main_menu(chat_id)
            elif action == "help":
                self._send_help_message(chat_id)
            elif action == "rate_start":
                self._start_rate_button_flow(chat_id)
            elif action == "rate_source" and len(parts) == 3:
                self._choose_rate_source(chat_id, parts[2])
            elif action == "rate_target" and len(parts) == 3:
                self._finish_rate_button_flow(chat_id, parts[2])
            elif action == "convert_start":
                self._start_convert_button_flow(chat_id)
            elif action == "convert_source" and len(parts) == 3:
                self._choose_convert_source(chat_id, parts[2])
            elif action == "convert_target" and len(parts) == 3:
                self._finish_convert_button_flow(chat_id, parts[2])
            elif action == "list_start":
                self._start_currency_list_flow(chat_id)
            elif action == "list_source" and len(parts) == 3:
                self._finish_currency_list_flow(chat_id, parts[2])
            else:
                self.bot.send_message(chat_id, "Неизвестное действие меню.")
        except (
            requests.RequestException,
            ElementTree.ParseError,
            ValueError,
        ) as error:
            self.bot.send_message(chat_id, f"Ошибка: {error}")

    def _show_main_menu(self, chat_id: int) -> None:
        """Показать главное меню функции ЦБ РФ с inline-кнопками.

        Args:
            chat_id: Идентификатор чата Telegram.
        """
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton(
                "Курс одной валюты",
                callback_data="cbr:rate_start",
            ),
            types.InlineKeyboardButton(
                "Перевод суммы",
                callback_data="cbr:convert_start",
            ),
            types.InlineKeyboardButton(
                "Список валют",
                callback_data="cbr:list_start",
            ),
            types.InlineKeyboardButton(
                "Инструкция",
                callback_data="cbr:help",
            ),
        )
        self.bot.send_message(
            chat_id,
            "Меню курсов валют ЦБ РФ:",
            reply_markup=markup,
        )

    def _start_rate_button_flow(self, chat_id: int) -> None:
        """Начать кнопочный сценарий получения курса валюты."""
        self.user_rate_states[chat_id] = {}
        self._send_currency_keyboard(
            chat_id,
            "Выберите исходную валюту:",
            "rate_source",
        )

    def _choose_rate_source(self, chat_id: int, source: str) -> None:
        """Запомнить исходную валюту для сценария курса.

        Args:
            chat_id: Идентификатор чата Telegram.
            source: Код выбранной исходной валюты.
        """
        source = source.upper()
        self.user_rate_states[chat_id] = {"source": source}
        self._send_currency_keyboard(
            chat_id,
            f"Исходная валюта: {source}\n"
            "Теперь выберите валюту, в которую показать курс:",
            "rate_target",
        )

    def _finish_rate_button_flow(self, chat_id: int, target: str) -> None:
        """Завершить кнопочный сценарий курса и отправить результат.

        Args:
            chat_id: Идентификатор чата Telegram.
            target: Код выбранной целевой валюты.
        """
        state = self.user_rate_states.get(chat_id)
        if not state or "source" not in state:
            self.bot.send_message(
                chat_id,
                "Сценарий устарел. Нажмите /cbrmenu ещё раз.",
            )
            return

        source = state["source"]
        target = target.upper()
        rates, rate_date = self._fetch_rates()
        rate = self.get_cross_rate(source, target, rates)
        self.user_rate_states.pop(chat_id, None)

        text = (
            f"Курс ЦБ РФ на {rate_date} "
            f"в {self._get_request_time()}:\n"
            f"1 {source} = {self._format_number(rate)} {target}"
        )
        self._send_text_with_back_button(chat_id, text)

    def _start_convert_button_flow(self, chat_id: int) -> None:
        """Начать кнопочный сценарий перевода суммы между валютами."""
        self.user_conversion_states[chat_id] = {}
        self._send_currency_keyboard(
            chat_id,
            "Выберите валюту, из которой будем переводить:",
            "convert_source",
        )

    def _choose_convert_source(self, chat_id: int, source: str) -> None:
        """Запомнить исходную валюту и попросить ввести сумму.

        Args:
            chat_id: Идентификатор чата Telegram.
            source: Код выбранной исходной валюты.
        """
        source = source.upper()
        self.user_conversion_states[chat_id] = {"source": source}
        message = self.bot.send_message(
            chat_id,
            f"Введите сумму в {source}:\n"
            "Например: 100 или 100,50",
        )
        self.bot.register_next_step_handler(
            message,
            self._handle_convert_amount_input,
        )

    def _handle_convert_amount_input(self, message: types.Message) -> None:
        """Получить сумму от пользователя в кнопочном сценарии перевода.

        Args:
            message: Сообщение пользователя с введённой суммой.
        """
        chat_id = message.chat.id
        state = self.user_conversion_states.get(chat_id)
        if not state or "source" not in state:
            self.bot.send_message(
                chat_id,
                "Сценарий устарел. Нажмите /cbrmenu ещё раз.",
            )
            return

        if message.text and message.text.startswith("/"):
            self.user_conversion_states.pop(chat_id, None)
            self.bot.send_message(chat_id, "Ввод суммы отменён.")
            return

        try:
            amount = self._parse_amount(message.text or "")
        except ValueError as error:
            retry_message = self.bot.send_message(
                chat_id,
                f"Ошибка: {error}. Введите сумму ещё раз:",
            )
            self.bot.register_next_step_handler(
                retry_message,
                self._handle_convert_amount_input,
            )
            return

        state["amount"] = amount
        source = str(state["source"])
        self._send_currency_keyboard(
            chat_id,
            f"Сумма: {self._format_number(amount)} {source}\n"
            "Теперь выберите валюту, в которую будем переводить:",
            "convert_target",
        )

    def _finish_convert_button_flow(self, chat_id: int, target: str) -> None:
        """Завершить кнопочный сценарий перевода и отправить результат.

        Args:
            chat_id: Идентификатор чата Telegram.
            target: Код выбранной целевой валюты.
        """
        state = self.user_conversion_states.get(chat_id)
        if not state or "source" not in state or "amount" not in state:
            self.bot.send_message(
                chat_id,
                "Сценарий устарел. Нажмите /cbrmenu ещё раз.",
            )
            return

        source = str(state["source"])
        amount = float(state["amount"])
        target = target.upper()
        rates, rate_date = self._fetch_rates()
        result = self.convert_amount(amount, source, target, rates)
        self.user_conversion_states.pop(chat_id, None)

        text = (
            f"Перевод по курсу ЦБ РФ на {rate_date} "
            f"в {self._get_request_time()}:\n"
            f"{self._format_number(amount)} {source} = "
            f"{self._format_number(result)} {target}"
        )
        self._send_text_with_back_button(chat_id, text)

    def _start_currency_list_flow(self, chat_id: int) -> None:
        """Начать сценарий показа списка пересчёта валют."""
        self._send_currency_keyboard(
            chat_id,
            "Выберите валюту, для которой показать список курсов:",
            "list_source",
        )

    def _finish_currency_list_flow(self, chat_id: int, source: str) -> None:
        """Показать пересчёт выбранной валюты во все валюты ЦБ РФ.

        Args:
            chat_id: Идентификатор чата Telegram.
            source: Код выбранной исходной валюты.
        """
        source = source.upper()
        rates, rate_date = self._fetch_rates()
        text = self._build_currency_list_text(source, rates, rate_date)
        self._send_text_with_back_button(chat_id, text)

    def _build_currency_list_text(
        self,
        source: str,
        rates: Dict[str, Dict[str, float]],
        rate_date: str,
    ) -> str:
        """Сформировать текст со списком курсов выбранной валюты.

        Args:
            source: Код исходной валюты.
            rates: Словарь курсов валют.
            rate_date: Дата курса из ответа ЦБ РФ.

        Returns:
            Текст со списком пересчёта выбранной валюты.
        """
        self._get_rate_to_rub(source, rates)

        lines = [
            f"Список курсов ЦБ РФ на {rate_date} "
            f"в {self._get_request_time()}:",
            f"Исходная валюта: {source}",
            "",
        ]

        for target in self._get_currency_order(rates):
            if target == source:
                continue

            rate = self.get_cross_rate(source, target, rates)
            lines.append(
                f"1 {source} = {self._format_number(rate)} {target}"
            )

        return "\n".join(lines)

    def _send_currency_keyboard(
        self,
        chat_id: int,
        title: str,
        callback_action: str,
    ) -> None:
        """Отправить пользователю клавиатуру с популярными валютами.

        Args:
            chat_id: Идентификатор чата Telegram.
            title: Текст над клавиатурой.
            callback_action: Часть callback_data, определяющая действие.
        """
        markup = types.InlineKeyboardMarkup(row_width=3)
        buttons = []

        for code, flag, _name in self.popular_currencies:
            buttons.append(
                types.InlineKeyboardButton(
                    f"{code} {flag}",
                    callback_data=f"cbr:{callback_action}:{code}",
                )
            )

        markup.add(*buttons)
        markup.add(
            types.InlineKeyboardButton(
                "Назад в меню",
                callback_data="cbr:menu",
            )
        )
        self.bot.send_message(chat_id, title, reply_markup=markup)

    def _send_help_message(self, chat_id: int) -> None:
        """Отправить инструкцию с кнопкой возврата в меню.

        Args:
            chat_id: Идентификатор чата Telegram.
        """
        self.bot.send_message(
            chat_id,
            self._help_text(),
            reply_markup=self._back_to_menu_markup(),
        )

    def _send_text_with_back_button(self, chat_id: int, text: str) -> None:
        """Отправить текстовое сообщение с кнопкой возврата в меню.

        Args:
            chat_id: Идентификатор чата Telegram.
            text: Текст сообщения.
        """
        self.bot.send_message(
            chat_id,
            text,
            reply_markup=self._back_to_menu_markup(),
        )

    @staticmethod
    def _back_to_menu_markup() -> types.InlineKeyboardMarkup:
        """Создать inline-кнопку возврата в меню.

        Returns:
            Клавиатура с кнопкой возврата в меню.
        """
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton(
                "Назад в меню",
                callback_data="cbr:menu",
            )
        )
        return markup

    def convert_amount(
        self,
        amount: float,
        source: str,
        target: str,
        rates: Dict[str, Dict[str, float]],
    ) -> float:
        """Перевести сумму из одной валюты в другую.

        Args:
            amount: Сумма для перевода.
            source: Код исходной валюты, например USD.
            target: Код целевой валюты, например EUR.
            rates: Словарь курсов валют, полученный из XML ЦБ РФ.

        Returns:
            Итоговая сумма в целевой валюте.
        """
        return amount * self.get_cross_rate(source, target, rates)

    def get_cross_rate(
        self,
        source: str,
        target: str,
        rates: Dict[str, Dict[str, float]],
    ) -> float:
        """Получить курс одной валюты к другой валюте.

        Args:
            source: Код исходной валюты.
            target: Код целевой валюты.
            rates: Словарь курсов валют.

        Returns:
            Количество единиц целевой валюты за одну единицу исходной.
        """
        source_rate = self._get_rate_to_rub(source, rates)
        target_rate = self._get_rate_to_rub(target, rates)
        return source_rate / target_rate

    def _fetch_rates(
        self,
        date_req: Optional[str] = None,
    ) -> Tuple[Dict[str, Dict[str, float]], str]:
        """Получить курсы валют с сайта ЦБ РФ.

        Args:
            date_req: Дата в формате ДД/ММ/ГГГГ для запроса к ЦБ РФ.

        Returns:
            Кортеж из словаря курсов валют и даты, на которую получены курсы.
        """
        params = {"date_req": date_req} if date_req else None
        response = requests.get(
            self.api_url,
            params=params,
            timeout=self.timeout,
            headers={"User-Agent": "system-integration-bot-2"},
        )
        response.raise_for_status()

        root = ElementTree.fromstring(response.content)
        rate_date = root.attrib.get("Date", "неизвестная дата")
        rates = self._parse_rates(root)
        return rates, rate_date

    @staticmethod
    def _parse_rates(root: ElementTree.Element) -> Dict[str, Dict[str, float]]:
        """Разобрать XML-ответ ЦБ РФ и получить словарь курсов.

        Args:
            root: Корневой XML-элемент ответа ЦБ РФ.

        Returns:
            Словарь, где ключ — код валюты, а значение — номинал и курс.
        """
        rates: Dict[str, Dict[str, float]] = {
            "RUB": {
                "nominal": 1.0,
                "value": 1.0,
            }
        }

        for item in root.findall("Valute"):
            char_code = item.findtext("CharCode")
            nominal = item.findtext("Nominal")
            value = item.findtext("Value")

            if char_code and nominal and value:
                rates[char_code.upper()] = {
                    "nominal": float(nominal.replace(",", ".")),
                    "value": float(value.replace(",", ".")),
                }

        return rates

    @staticmethod
    def _get_rate_to_rub(
        currency: str,
        rates: Dict[str, Dict[str, float]],
    ) -> float:
        """Получить стоимость одной единицы валюты в рублях.

        Args:
            currency: Код валюты, например USD, EUR или RUB.
            rates: Словарь курсов валют.

        Returns:
            Стоимость одной единицы валюты в рублях.

        Raises:
            ValueError: Если указанная валюта не найдена.
        """
        currency_code = currency.upper()
        if currency_code not in rates:
            raise ValueError(f"валюта {currency_code} не найдена")

        currency_rate = rates[currency_code]
        return currency_rate["value"] / currency_rate["nominal"]

    @staticmethod
    def _get_currency_order(
        rates: Dict[str, Dict[str, float]],
    ) -> List[str]:
        """Получить отсортированный список кодов валют для вывода.

        Args:
            rates: Словарь курсов валют.

        Returns:
            Список кодов валют, где RUB выводится первым.
        """
        codes = sorted(rates.keys())
        if "RUB" in codes:
            codes.remove("RUB")
            return ["RUB"] + codes

        return codes

    @staticmethod
    def _parse_amount(raw_amount: str) -> float:
        """Преобразовать сумму из текста в число.

        Args:
            raw_amount: Сумма из сообщения пользователя.

        Returns:
            Сумма в виде числа float.

        Raises:
            ValueError: Если сумма не является числом или меньше нуля.
        """
        try:
            amount = float(raw_amount.replace(",", "."))
        except ValueError as error:
            raise ValueError("сумма должна быть числом") from error

        if amount <= 0:
            raise ValueError("сумма должна быть больше нуля")

        return amount

    @staticmethod
    def _format_number(value: float) -> str:
        """Отформатировать число для красивого вывода пользователю.

        Args:
            value: Число для форматирования.

        Returns:
            Строка с аккуратно отформатированным числом.
        """
        return f"{value:.4f}".rstrip("0").rstrip(".")

    @staticmethod
    def _get_request_time() -> str:
        """Получить текущее время обращения пользователя.

        Returns:
            Текущее время в формате ЧЧ:ММ:СС.
        """
        return datetime.now().strftime("%H:%M:%S")

    @staticmethod
    def _help_text() -> str:
        """Вернуть короткую справку по использованию меню.

        Returns:
            Текст подсказки для пользователя Telegram-бота.
        """
        return (
            "Инструкция по работе с функцией ЦБ РФ.\n\n"
            "Основная команда:\n"
            "/cbrmenu — открыть меню с кнопками.\n\n"
            "В меню доступны разделы:\n"
            "1. Курс одной валюты — сначала выберите исходную валюту, "
            "затем валюту, в которую нужно показать курс.\n"
            "2. Перевод суммы — выберите исходную валюту, введите сумму "
            "и выберите валюту для перевода.\n"
            "3. Список валют — выберите валюту, и бот покажет её курс "
            "ко всем валютам из ответа ЦБ РФ.\n"
            "4. Инструкция — показывает это сообщение.\n\n"
            "Данные берутся из официального сервиса Центрального банка РФ. "
            "API-ключ не требуется."
        )
