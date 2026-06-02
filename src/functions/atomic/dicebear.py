"""Генерация аватаров через DiceBear API."""

from __future__ import annotations

from io import BytesIO
from secrets import token_urlsafe
from typing import Final, List
from urllib.parse import urlencode

import requests
import telebot
from telebot import types
from telebot.callback_data import CallbackData

from bot_func_abc import AtomicBotFunctionABC

DICEBEAR_API_URL: Final[str] = "https://api.dicebear.com/9.x"
AVATAR_FORMAT: Final[str] = "png"
AVATAR_SIZE: Final[int] = 256
REQUEST_TIMEOUT: Final[int] = 15

DEFAULT_STYLE: Final[str] = "bottts"

STYLES: Final[dict[str, str]] = {
    "adventurer": "🧭 Adventurer",
    "avataaars": "🙂 Avataaars",
    "bottts": "🤖 Bottts",
    "identicon": "🔷 Identicon",
    "initials": "🔤 Initials",
    "lorelei": "🧑 Lorelei",
    "micah": "🎨 Micah",
    "personas": "🧍 Personas",
    "pixel-art": "👾 Pixel Art",
    "thumbs": "👍 Thumbs",
}


class DiceBearAvatarBotFunction(AtomicBotFunctionABC):
    """Функция Telegram-бота для генерации аватаров через DiceBear API."""

    commands: List[str] = ["dicebear"]
    authors: List[str] = ["solitudo66"]
    about: str = "Генератор аватаров DiceBear"
    description: str = (
        "Генерирует аватар по выбранному стилю и seed пользователя через "
        "DiceBear API. Команда `/avatar` открывает меню с кнопками. "
        "Также можно вызвать `/avatar seed`, чтобы сразу создать аватар. "
        "Если использовать один и тот же стиль и seed, получится одинаковая картинка."
    )
    state: bool = True

    bot: telebot.TeleBot
    keyboard_factory: CallbackData

    def __init__(self) -> None:
        """Создаёт хранилище выбранных стилей пользователей."""
        self.user_styles: dict[int, str] = {}

    def set_handlers(self, bot: telebot.TeleBot) -> None:
        """Регистрирует обработчики команды и кнопок DiceBear."""
        self.bot = bot
        self.keyboard_factory = CallbackData(
            "dicebear_action",
            "dicebear_value",
            prefix=self.commands[0],
        )

        @bot.message_handler(commands=self.commands)
        def avatar_message_handler(message: types.Message) -> None:
            self.__handle_avatar_command(message)

        @bot.callback_query_handler(func=None, config=self.keyboard_factory.filter())
        def avatar_keyboard_callback(call: types.CallbackQuery) -> None:
            self.__handle_callback(call)

    def __handle_avatar_command(self, message: types.Message) -> None:
        """Обрабатывает команду /avatar или быструю генерацию по seed."""
        parts = message.text.split(maxsplit=2)

        if len(parts) == 1:
            self.__send_menu(message.chat.id, message.from_user.id)
            return

        if len(parts) >= 3 and parts[1] in STYLES:
            self.user_styles[message.from_user.id] = parts[1]
            self.__send_avatar(message.chat.id, message.from_user.id, parts[2])
            return

        seed = " ".join(parts[1:]).strip()
        self.__send_avatar(message.chat.id, message.from_user.id, seed)

    def __handle_callback(self, call: types.CallbackQuery) -> None:
        """Обрабатывает нажатия на inline-кнопки."""
        callback_data = self.keyboard_factory.parse(callback_data=call.data)
        action = callback_data["dicebear_action"]
        value = callback_data["dicebear_value"]

        match action:
            case "style_menu":
                self.bot.answer_callback_query(call.id)
                self.__send_style_menu(call.message.chat.id)
            case "style":
                self.__set_style(call, value)
            case "seed":
                self.bot.answer_callback_query(call.id)
                self.__ask_seed(call.message)
            case "random":
                self.bot.answer_callback_query(call.id)
                seed = f"avatar-{token_urlsafe(8)}"
                self.__send_avatar(call.message.chat.id, call.from_user.id, seed)
            case "instruction":
                self.bot.answer_callback_query(call.id)
                self.__send_instruction(call.message.chat.id)
            case "menu":
                self.bot.answer_callback_query(call.id)
                self.__send_menu(call.message.chat.id, call.from_user.id)
            case _:
                self.bot.answer_callback_query(call.id, "Неизвестное действие")

    def __send_menu(self, chat_id: int, user_id: int) -> None:
        """Отправляет главное меню генератора аватаров."""
        current_style = self.__get_user_style(user_id)
        text = (
            "🖼 <b>Генератор аватаров DiceBear</b>\n\n"
            f"Текущий стиль: <code>{current_style}</code>\n\n"
            "Выбери действие на панели управления."
        )
        self.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=self.__main_markup(),
        )

    def __send_style_menu(self, chat_id: int) -> None:
        """Отправляет меню выбора стиля."""
        self.bot.send_message(
            chat_id=chat_id,
            text="🎨 Выбери стиль аватара:",
            reply_markup=self.__styles_markup(),
        )

    def __set_style(self, call: types.CallbackQuery, style: str) -> None:
        """Сохраняет выбранный пользователем стиль."""
        if style not in STYLES:
            self.bot.answer_callback_query(call.id, "Такого стиля нет", show_alert=True)
            return

        self.user_styles[call.from_user.id] = style
        self.bot.answer_callback_query(call.id, "Стиль выбран")
        self.bot.send_message(
            chat_id=call.message.chat.id,
            text=(
                f"✅ Выбран стиль: <b>{STYLES[style]}</b>\n\n"
                "Теперь нажми «✍️ Ввести seed» или используй случайный seed."
            ),
            parse_mode="HTML",
            reply_markup=self.__main_markup(),
        )

    def __ask_seed(self, message: types.Message) -> None:
        """Просит пользователя ввести seed и регистрирует следующий шаг."""
        force_reply = types.ForceReply(selective=False)
        sent_message = self.bot.send_message(
            chat_id=message.chat.id,
            text=(
                "✍️ Введи seed для генерации аватара.\n\n"
                "Например: <code>slon123</code>, <code>student</code>, "
                "<code>avatar-test</code>."
            ),
            parse_mode="HTML",
            reply_markup=force_reply,
        )
        self.bot.register_next_step_handler(sent_message, self.__process_seed)

    def __process_seed(self, message: types.Message) -> None:
        """Принимает seed и запускает генерацию аватара."""
        seed = message.text.strip() if message.text else ""

        if not seed:
            self.bot.send_message(message.chat.id, "❌ Seed не должен быть пустым.")
            return

        self.__send_avatar(message.chat.id, message.from_user.id, seed)

    def __send_instruction(self, chat_id: int) -> None:
        """Отправляет инструкцию по работе с функцией."""
        self.bot.send_message(
            chat_id=chat_id,
            text=(
                "ℹ️ <b>Инструкция</b>\n\n"
                "Бот создаёт аватар через DiceBear API.\n\n"
                "1. Нажми «🎨 Выбрать стиль».\n"
                "2. Выбери подходящий стиль.\n"
                "3. Нажми «✍️ Ввести seed».\n"
                "4. Напиши любое слово или строку.\n"
                "5. Бот отправит готовую картинку.\n\n"
                "Seed — это основа генерации. Если повторить тот же seed "
                "и тот же стиль, получится такой же аватар.\n\n"
                "Быстрый вызов: <code>/avatar slon123</code>\n"
                "Со стилем: <code>/avatar pixel-art slon123</code>"
            ),
            parse_mode="HTML",
            reply_markup=self.__main_markup(),
        )

    def __send_avatar(self, chat_id: int, user_id: int, seed: str) -> None:
        """Получает PNG-аватар из DiceBear API и отправляет его в Telegram."""
        style = self.__get_user_style(user_id)
        avatar_url = self.__build_avatar_url(style, seed)

        try:
            response = requests.get(avatar_url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException:
            self.bot.send_message(
                chat_id=chat_id,
                text=(
                    "❌ Не удалось получить аватар от DiceBear API.\n"
                    "Проверь интернет или попробуй позже."
                ),
            )
            return

        image = BytesIO(response.content)
        image.name = "dicebear_avatar.png"

        self.bot.send_photo(
            chat_id=chat_id,
            photo=image,
            caption=(
                "✅ <b>Аватар готов!</b>\n\n"
                f"🎨 Стиль: <code>{style}</code>\n"
                f"🔑 Seed: <code>{seed}</code>\n\n"
                f"🔗 API-запрос:\n{avatar_url}"
            ),
            parse_mode="HTML",
            reply_markup=self.__main_markup(),
        )

    def __get_user_style(self, user_id: int) -> str:
        """Возвращает выбранный стиль пользователя или стиль по умолчанию."""
        return self.user_styles.get(user_id, DEFAULT_STYLE)

    def __build_avatar_url(self, style: str, seed: str) -> str:
        """Формирует URL запроса к DiceBear API."""
        query_params = urlencode(
            {
                "seed": seed,
                "size": AVATAR_SIZE,
                "radius": 50,
            }
        )
        return f"{DICEBEAR_API_URL}/{style}/{AVATAR_FORMAT}?{query_params}"

    def __main_markup(self) -> types.InlineKeyboardMarkup:
        """Создаёт главное inline-меню функции."""
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton(
                "🎨 Выбрать стиль",
                callback_data=self.keyboard_factory.new(
                    dicebear_action="style_menu",
                    dicebear_value="none",
                ),
            ),
            types.InlineKeyboardButton(
                "✍️ Ввести seed",
                callback_data=self.keyboard_factory.new(
                    dicebear_action="seed",
                    dicebear_value="none",
                ),
            ),
            types.InlineKeyboardButton(
                "🎲 Случайный seed",
                callback_data=self.keyboard_factory.new(
                    dicebear_action="random",
                    dicebear_value="none",
                ),
            ),
            types.InlineKeyboardButton(
                "ℹ️ Инструкция",
                callback_data=self.keyboard_factory.new(
                    dicebear_action="instruction",
                    dicebear_value="none",
                ),
            ),
        )
        return markup

    def __styles_markup(self) -> types.InlineKeyboardMarkup:
        """Создаёт inline-меню выбора стиля."""
        markup = types.InlineKeyboardMarkup(row_width=2)
        buttons = [
            types.InlineKeyboardButton(
                title,
                callback_data=self.keyboard_factory.new(
                    dicebear_action="style",
                    dicebear_value=style,
                ),
            )
            for style, title in STYLES.items()
        ]
        markup.add(*buttons)
        markup.add(
            types.InlineKeyboardButton(
                "⬅️ Назад в меню",
                callback_data=self.keyboard_factory.new(
                    dicebear_action="menu",
                    dicebear_value="none",
                ),
            )
        )
        return markup
