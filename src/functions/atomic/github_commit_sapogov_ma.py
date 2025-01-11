"""Модуль для работы с ISO-кодами стран и их административными единицами."""

from typing import List
import requests
import telebot
from telebot import types
from telebot.callback_data import CallbackData
from bot_func_abc import AtomicBotFunctionABC

class CountryCodesBot(AtomicBotFunctionABC):
    """Класс для получения ISO-кодов стран и их административных единиц."""
    commands: List[str] = ["Countries"]  # Keep only "Countries"
    authors: List[str] = ["TestStudentMichael"]
    about: str = "ISO-коды и адм.ед стран"
    description: str = (
        "`/Countries` - функция выводит список доступных ISO-кодов стран, "
        "а после принимает код от пользователя и выводит в ответ административные единицы."
    )
    state: bool = True

    bot: telebot.TeleBot
    example_keyboard_factory: CallbackData

    def set_handlers(self, bot: telebot.TeleBot):
        """Устанавливает обработчики событий для бота."""
        self.bot = bot

        @bot.message_handler(commands=self.commands)  # Use self.commands here
        def handle_countries_command(message: types.Message):
            """Обрабатывает команду получения списка стран."""
            iso_country_codes = self.get_iso_country_codes()
            text = '\n'.join(iso_country_codes)

            bot.reply_to(message, f"Вот ISO-коды стран:\n{text}\n\nВведите код страны:")
            bot.register_next_step_handler(message, handle_user_input)

        def handle_user_input(message: types.Message):
            """Обрабатывает ввод кода страны от пользователя."""
            country_code = message.text.strip().upper()

            if country_code in self.get_iso_country_codes():
                administrative_divisions = self.get_administrative_divisions(country_code)

                if administrative_divisions:
                    text = '\n'.join(administrative_divisions)
                    bot.reply_to(message, f"Адм.ед. для страны с кодом {country_code}:\n{text}")
                else:
                    bot.reply_to(message, f"Не найти адм.ед. для страны с кодом {country_code}")
            else:
                bot.reply_to(message, f"Код страны {country_code} не найден в доступных ISO")

    def get_iso_country_codes(self):
        """Получает список ISO-кодов стран."""
        url = "https://restcountries.com/v3.1/all"
        response = requests.get(url, timeout=10)  # Добавлен таймаут

        if response.status_code == 200:
            countries_data = response.json()
            country_codes = []

            for country in countries_data:
                if 'cca2' in country:
                    country_codes.append(country['cca2'])

            return country_codes
        print("Ошибка при получении данных")
        return []  # Возвращаем пустой список в случае ошибки

    def get_administrative_divisions(self, country_code):
        """Получает административные единицы страны по её коду."""
        url_part1 = "https://rawcdn.githack.com/kamikazechaser/administrative-divisions-db/"
        url_part2 = f"master/api/{country_code}.json"

        # Соединяем части обратно
        url = url_part1 + url_part2

        try:
            response = requests.get(url, timeout=10)  # Добавлен таймаут
            response.raise_for_status()
            divisions = response.json()
            return divisions
        except requests.exceptions.HTTPError as err:
            print(f"Произошла ошибка HTTP: {err}")
            return []  # Возвращаем пустой список при ошибке
        except requests.exceptions.Timeout as timeout_err:
            print(f"Время ожидания истекло: {timeout_err}")
        return []  # Return an empty list on timeout error
