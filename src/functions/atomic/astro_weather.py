"""
Модуль предоставляет графический астрономический прогноз погоды
для Москвы и Санкт-Петербурга через 7Timer! API.
"""

from typing import Dict, Optional, Tuple
import requests
import telebot
from telebot import types
from telebot.callback_data import CallbackData
from bot_func_abc import AtomicBotFunctionABC # pylint: disable=import-error

CITIES: Dict[str, Tuple[float, float]] = {
    "Москва": (55.7558, 37.6173),
    "Санкт-Петербург": (59.9343, 30.3351),
}

API_URL = "http://www.7timer.info/bin/astro.php"


class AstroWeatherBotFunction(AtomicBotFunctionABC):
    """Модуль для получения астрономического прогноза погоды через 7Timer! API."""

    commands = ["astro"]
    authors = ["IlyaNikolin"]
    about = "Астро прогноз для Москвы и СПб"
    description = (
        "Отображает графический астрономический прогноз погоды "
        "для Москвы и Санкт-Петербурга на 3 дня. "
        "Включает облачность, астрономический сиинг и прозрачность атмосферы. "
        "Используйте команду /astro для получения прогноза."
    )
    state = True

    def __init__(self) -> None:
        self.keyboard_factory = CallbackData("city", prefix=self.commands[0])

    def set_handlers(self, bot: telebot.TeleBot) -> None:
        """Установка обработчиков для команды /astro."""

        @bot.message_handler(commands=self.commands)
        def handle_astro_command(message: telebot.types.Message) -> None:
            markup = types.InlineKeyboardMarkup()
            for city in CITIES:
                callback_data = self.keyboard_factory.new(city=city)
                markup.add(types.InlineKeyboardButton(city, callback_data=callback_data))
            bot.send_message(
                message.chat.id,
                "🔭 Выберите город:",
                reply_markup=markup,
            )

        @bot.callback_query_handler(func=None, config=self.keyboard_factory.filter())
        def handle_city_callback(call: types.CallbackQuery) -> None:
            city = self.keyboard_factory.parse(callback_data=call.data)["city"]
            if city not in CITIES:
                bot.answer_callback_query(call.id, "Неизвестный город")
                return
            bot.answer_callback_query(call.id)
            lat, lon = CITIES[city]
            image_bytes = self.fetch_astro_image(lat, lon)
            if image_bytes:
                bot.send_photo(
                    call.message.chat.id,
                    image_bytes,
                    caption=f"🔭 Астро прогноз: {city}",
                )
            else:
                bot.send_message(
                    call.message.chat.id,
                    f"❌ Не удалось получить прогноз для города {city}.",
                )

    def fetch_astro_image(self, lat: float, lon: float) -> Optional[bytes]:
        """Получение графического астро прогноза из 7Timer! API."""
        params = {
            "lat": lat,
            "lon": lon,
            "ac": 0,
            "lang": "ru",
            "unit": "metric",
            "output": "internal",
            "tzshift": 0,
        }
        try:
            response = requests.get(API_URL, params=params, timeout=15)
            response.raise_for_status()
            return response.content
        except requests.RequestException:
            return None
