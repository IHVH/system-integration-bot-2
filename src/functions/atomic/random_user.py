"""Модуль генерации случайного пользователя через randomuser.me."""

import logging
from typing import List, Optional

import requests
import telebot
from telebot import types
from telebot.callback_data import CallbackData

from bot_func_abc import AtomicBotFunctionABC # pylint: disable=import-error

_API_URL = "https://randomuser.me/api/"

# pylint: disable=too-few-public-methods
class RandomUserBotFunction(AtomicBotFunctionABC):
    """Генерация случайного пользователя с полными данными."""

    commands: List[str] = ["randuser", "ruser"]
    authors: List[str] = ["SherdorNematov"]
    about: str = "Генерация случайного пользователя."
    description: str = (
        "Генерирует случайного пользователя с полными данными.\n"
        "Использование:\n"
        "`/randuser` — случайный пользователь\n"
        "`/randuser <seed>` — пользователь по конкретному сиду"
    )
    state: bool = True

    bot: telebot.TeleBot
    kb_factory: CallbackData

    def set_handlers(self, bot: telebot.TeleBot):
        """Регистрирует обработчики сообщений."""
        self.bot = bot
        self.kb_factory = CallbackData("action", "seed", prefix=self.commands[0])

        @bot.message_handler(commands=self.commands)
        def handle_command(message: types.Message):
            parts = message.text.strip().split(maxsplit=1)
            seed = parts[1].strip() if len(parts) > 1 else ""
            self._send_user(message.chat.id, seed)

        @bot.callback_query_handler(func=None, config=self.kb_factory.filter())
        def handle_callback(call: types.CallbackQuery):
            parsed = self.kb_factory.parse(callback_data=call.data)
            if parsed["action"] == "new":
                bot.answer_callback_query(call.id)
                self._send_user(call.message.chat.id, "")

    def _fetch_user(self, seed: str) -> Optional[dict]:
        """Запрашивает данные пользователя из API."""
        params = {"seed": seed} if seed else {}
        try:
            response = requests.get(_API_URL, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            logging.exception(exc)
            return None

    def _format_user(self, data: dict) -> tuple:
        """Форматирует данные пользователя. Возвращает (текст, url фото)."""
        user = data["results"][0]
        seed = data["info"]["seed"]
        name = user["name"]
        loc = user["location"]
        coord = loc["coordinates"]
        tz = loc["timezone"]
        login = user["login"]
        dob = user["dob"]
        reg = user["registered"]
        pic = user["picture"]

        lines = [
            f"👤 *{name['title']}. {name['first']} {name['last']}*",
            f"⚧ Пол: {user['gender']} | 🌍 Нац.: `{user['nat']}`",
            "",
            "📍 *Локация*",
            f"  {loc['country']}, {loc['state']}, {loc['city']}",
            f"  ул. {loc['street']['name']}, {loc['street']['number']}, {loc['postcode']}",
            f"  Коорд.: {coord['latitude']}, {coord['longitude']}",
            f"  Часовой пояс: {tz['offset']} ({tz['description']})",
            "",
            f"📧 `{user['email']}`",
            f"📞 `{user['phone']}` | 📱 `{user['cell']}`",
            "",
            "🔐 *Логин*",
            f"  UUID: `{login['uuid']}`",
            f"  Логин: `{login['username']}`",
            f"  Пароль: `{login['password']}`",
            f"  Salt: `{login['salt']}`",
            f"  MD5: `{login['md5']}`",
            f"  SHA1: `{login['sha1']}`",
            f"  SHA256: `{login['sha256']}`",
            "",
            f"🎂 ДР: {dob['date'][:10]} (возраст: {dob['age']})",
            f"📅 Рег.: {reg['date'][:10]} ({reg['age']} лет)",
            "",
            f"🪪 ID: {user['id']['name']} — `{user['id']['value']}`",
            "",
            f"🖼 [large]({pic['large']}) | [medium]({pic['medium']}) | [thumb]({pic['thumbnail']})",
            "",
            f"🌱 Сид: `{seed}`",
        ]
        return "\n".join(lines), pic["large"]

    def _send_user(self, chat_id: int, seed: str):
        """Отправляет карточку пользователя в чат."""
        data = self._fetch_user(seed)
        if not data:
            self.bot.send_message(chat_id, "❌ Не удалось получить данные. Попробуйте позже.")
            return
        text, photo_url = self._format_user(data)
        markup = types.InlineKeyboardMarkup()
        cb = self.kb_factory.new(action="new", seed="")
        markup.add(types.InlineKeyboardButton("🔄 Ещё одного", callback_data=cb))
        self.bot.send_message(
            chat_id,
            text,
            parse_mode="Markdown",
            reply_markup=markup,
            disable_web_page_preview=True,
        )
        self.bot.send_photo(chat_id, photo_url)
