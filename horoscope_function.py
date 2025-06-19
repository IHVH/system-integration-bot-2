
from typing import List
import requests
from requests.exceptions import RequestException
from telebot.types import Message
from bot_func_abc import AtomicBotFunctionABC


class HoroscopeFunction(AtomicBotFunctionABC):
    """Класс для обработки команды /horoscope, выводящей гороскоп по знаку зодиака."""

    commands = ["horoscope"]
    authors = ["Kylon2308"]
    about = "Гороскоп по знаку зодиака"
    description = (
        "Команда /horoscope [знак] показывает гороскоп на сегодня для выбранного знака.\n"
        "Пример: /horoscope leo"
    )
    state = True

    def set_handlers(self, bot):
        """Устанавливает обработчики команд для бота."""

        @bot.message_handler(commands=self.commands)
        def handle_horoscope(message: Message):
            """Обработчик команды /horoscope."""

            try:
                arr = message.text.strip().split()
                if len(arr) != 2:
                    bot.send_message(message.chat.id, "Пожалуйста, укажите знак зодиака.\nПример: /horoscope virgo")
                    return

                sign = arr[1].lower()
                valid_signs = [
                    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
                    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"
                ]

                if sign not in valid_signs:
                    bot.send_message(message.chat.id, f"Недопустимый знак зодиака: {sign}")
                    return

                response = requests.post(
                    f"https://aztro.sameerkumar.website/?sign={sign}&day=today",
                    timeout=5
                )
                response.raise_for_status()
                data = response.json()

                # Формируем сообщение
                text = (
                    f"🔮 *Гороскоп на сегодня для {sign.capitalize()}*\n\n"
                    f"*📅 Дата:* {data['current_date']}\n"
                    f"*📝 Описание:* {data['description']}\n"
                    f"*💘 Совместимость:* {data['compatibility']}\n"
                    f"*🎯 Удачное число:* {data['lucky_number']}\n"
                    f"*🎨 Цвет:* {data['color']}\n"
                    f"*🕐 Удачное время:* {data['lucky_time']}\n"
                    f"*😌 Настроение:* {data['mood']}"
                )

                bot.send_message(message.chat.id, text, parse_mode="Markdown")

            except (RequestException, ValueError) as e:
                bot.send_message(message.chat.id, f"Произошла ошибка при получении гороскопа: {e}")
