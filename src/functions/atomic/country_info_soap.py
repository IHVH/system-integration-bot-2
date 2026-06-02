"""
Получение информации о странах через SOAP сервис
"""

from typing import List

from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from zeep import Client

from bot_func_abc import AtomicBotFunctionABC


class CountryInfoSoap(
    AtomicBotFunctionABC
):
    """
    SOAP информация о странах
    """

    commands: List[str] = [
        "countries"
    ]

    authors: List[str] = [
        "elikman"
    ]

    about: str = (
        "Информация о странах через SOAP"
    )

    description: str = (
        "Получение списка стран "
        "и подробной информации "
        "о выбранной стране"
    )

    state: bool = True

    WSDL_URL = (
        "http://webservices.oorsprong.org/"
        "websamples.countryinfo/"
        "CountryInfoService.wso?WSDL"
    )

    def __init__(self):
        """
        Инициализация SOAP клиента
        """

        self.client = Client(
            self.WSDL_URL
        )

    def set_handlers(self, bot):
        """
        Регистрация handlers
        """

        @bot.message_handler(
            commands=self.commands
        )
        def command_handler(message):
            self.run(bot, message)

        @bot.callback_query_handler(
            func=lambda call: (
                call.data.startswith(
                    "country_"
                )
            )
        )
        def callback_handler(call):
            self.country_callback(
                bot,
                call
            )

    def run(
        self,
        bot,
        message: Message
    ):
        """
        Получить список стран
        """

        try:
            countries = (
                self.client.service
                .ListOfCountryNamesByName()
            )

            markup = (
                InlineKeyboardMarkup()
            )

            for country in countries:

                markup.add(
                    InlineKeyboardButton(
                        text=country.sName,
                        callback_data=(
                            "country_"
                            f"{country.sISOCode}"
                        )
                    )
                )

            bot.send_message(
                message.chat.id,
                "🌍 Выберите страну:",
                reply_markup=markup
            )

        except (
            ConnectionError,
            ValueError,
            TypeError
        ) as error:

            bot.reply_to(
                message,
                (
                    "Ошибка получения "
                    "списка стран:\n"
                    f"{error}"
                )
            )

    def country_callback(
        self,
        bot,
        call
    ):
        """
        Информация о стране
        """

        try:
            iso_code = (
                call.data.replace(
                    "country_",
                    ""
                )
            )

            country_name = (
                self.client.service
                .CountryName(
                    iso_code
                )
            )

            capital = (
                self.client.service
                .CapitalCity(
                    iso_code
                )
            )

            currency = (
                self.client.service
                .CountryCurrency(
                    iso_code
                )
            )

            phone_code = (
                self.client.service
                .CountryIntPhoneCode(
                    iso_code
                )
            )

            text = (
                f"🌍 Страна: "
                f"{country_name}\n"
                f"🏙 Столица: "
                f"{capital}\n"
                f"💰 Валюта: "
                f"{currency.sName}\n"
                f"📞 Код страны: "
                f"+{phone_code}"
            )

            bot.send_message(
                call.message.chat.id,
                text
            )

        except (
            ConnectionError,
            ValueError,
            TypeError
        ) as error:

            bot.send_message(
                call.message.chat.id,
                f"Ошибка:\n{error}"
            )
