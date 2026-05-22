"""Module implementation of the atomic function of the telegram bot. JokeAPI integration."""

import logging
from collections import deque
from typing import Deque, Dict, List, Optional, Tuple

import requests
import telebot
from telebot import types
from telebot.callback_data import CallbackData

from bot_func_abc import AtomicBotFunctionABC


class JokeApiBotFunction(AtomicBotFunctionABC):
    """Integration with the public JokeAPI (https://v2.jokeapi.dev)."""

    commands: List[str] = ["joke", "jk"]
    authors: List[str] = ["ABOBIQUE"]
    about: str = "Случайная шутка из JokeAPI"
    description: str = (
        "Возвращает случайную шутку с публичного сервиса JokeAPI (v2.jokeapi.dev) "
        "вместе с переводом на русский через MyMemory Translation API.\n"
        "Использование:\n"
        "`/joke` — случайная шутка из любой категории.\n"
        "`/joke <category>` — шутка из конкретной категории.\n"
        "Доступные категории: Any, Programming, Misc, Pun, Spooky, Christmas, Dark.\n"
        "После вызова появится клавиатура для выбора другой категории."
    )
    state: bool = True

    API_URL = "https://v2.jokeapi.dev/joke/{category}"
    TRANSLATE_URL = "https://api.mymemory.translated.net/get"
    CATEGORIES = ["Any", "Programming", "Misc", "Pun", "Spooky", "Christmas", "Dark"]
    SAFE_BLACKLIST = "nsfw,religious,political,racist,sexist,explicit"
    TIMEOUT = 10
    HISTORY_SIZE = 5
    MAX_RETRIES = 5

    bot: telebot.TeleBot
    joke_keyboard_factory: CallbackData
    __history: Dict[int, Deque[int]] = {}

    def set_handlers(self, bot: telebot.TeleBot):
        """Register message and callback handlers."""
        self.bot = bot
        self.joke_keyboard_factory = CallbackData("category", prefix=self.commands[0])

        @bot.message_handler(commands=self.commands)
        def joke_message_handler(message: types.Message):
            category = self.__parse_category(message.text)
            self.__send_joke(
                chat_id=message.chat.id,
                user_id=message.from_user.id,
                category=category,
            )

        @bot.callback_query_handler(func=None, config=self.joke_keyboard_factory.filter())
        def joke_callback_handler(call: types.CallbackQuery):
            data = self.joke_keyboard_factory.parse(callback_data=call.data)
            category = data["category"]
            if category not in self.CATEGORIES:
                bot.answer_callback_query(call.id, "Неизвестная категория")
                return
            bot.answer_callback_query(call.id, f"Категория: {category}")
            self.__send_joke(
                chat_id=call.message.chat.id,
                user_id=call.from_user.id,
                category=category,
            )

    def __parse_category(self, text: str) -> str:
        parts = (text or "").strip().split(maxsplit=1)
        if len(parts) < 2:
            return "Any"
        requested = parts[1].strip().capitalize()
        for cat in self.CATEGORIES:
            if cat.lower() == requested.lower():
                return cat
        return "Any"

    def __send_joke(self, chat_id: int, user_id: int, category: str) -> None:
        history = self.__history.setdefault(user_id, deque(maxlen=self.HISTORY_SIZE))
        data: Optional[dict] = None
        error_text: Optional[str] = None
        for _ in range(self.MAX_RETRIES):
            data, error_text = self.__fetch_joke(category)
            if error_text is not None:
                break
            joke_id = data.get("id") if data else None
            if joke_id is None or joke_id not in history:
                break
        if error_text is not None:
            joke_text = error_text
        else:
            joke_id = data.get("id") if data else None
            if joke_id is not None:
                history.append(joke_id)
            joke_text = self.__format_joke(data or {})
        self.bot.send_message(
            chat_id=chat_id,
            text=joke_text,
            reply_markup=self.__gen_markup(),
            parse_mode="Markdown",
        )

    def __fetch_joke(self, category: str) -> Tuple[Optional[dict], Optional[str]]:
        url = self.API_URL.format(category=category)
        params = {"blacklistFlags": self.SAFE_BLACKLIST}
        try:
            response = requests.get(url, params=params, timeout=self.TIMEOUT)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as ex:
            logging.exception("JokeAPI request failed: %s", ex)
            return None, "Не удалось получить шутку. Попробуйте позже."
        except ValueError as ex:
            logging.exception("JokeAPI returned invalid JSON: %s", ex)
            return None, "Сервис вернул некорректный ответ."

        if data.get("error"):
            message = data.get("message", "Неизвестная ошибка")
            return None, f"JokeAPI error: {message}"

        return data, None

    def __format_joke(self, data: dict) -> str:
        if data.get("type") == "twopart":
            setup = data.get("setup", "").strip()
            delivery = data.get("delivery", "").strip()
            joke_en = f"{setup}\n{delivery}"
        else:
            joke_en = data.get("joke", "").strip()
        if not joke_en:
            return "Шутка не найдена."
        joke_ru = self.__translate(joke_en)
        return f"🇬🇧 *English*\n{joke_en}\n\n🇷🇺 *Русский*\n{joke_ru}"

    def __translate(self, text: str) -> str:
        if not text:
            return ""
        try:
            response = requests.get(
                self.TRANSLATE_URL,
                params={"q": text, "langpair": "en|ru"},
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as ex:
            logging.exception("Translation request failed: %s", ex)
            return "(перевод недоступен)"
        except ValueError as ex:
            logging.exception("Translation returned invalid JSON: %s", ex)
            return "(перевод недоступен)"
        translated = (data.get("responseData") or {}).get("translatedText", "").strip()
        return translated or "(перевод недоступен)"

    def __gen_markup(self) -> types.InlineKeyboardMarkup:
        markup = types.InlineKeyboardMarkup(row_width=3)
        buttons = [
            types.InlineKeyboardButton(
                text=cat,
                callback_data=self.joke_keyboard_factory.new(category=cat),
            )
            for cat in self.CATEGORIES
        ]
        markup.add(*buttons)
        return markup
