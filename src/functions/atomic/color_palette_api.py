"""Модуль функции поиска цветовых палитр через ColorMagic API."""

import logging
from datetime import datetime
from typing import List

import requests
import telebot
from telebot import types
from telebot.callback_data import CallbackData

# pylint: disable=import-error
from bot_func_abc import AtomicBotFunctionABC

# pylint: disable=too-few-public-methods
class ColorPaletteBotFunction(AtomicBotFunctionABC):
    """Поиск цветовых палитр через colormagic.app"""

    commands: List[str] = ["palette", "color"]
    authors: List[str] = ["tr1mdirt13"]
    about: str = "Поиск цветовых палитр по ключевому слову."
    description: str = """Ищет цветовые палитры через ColorMagic API.
    Использование: `/palette green` или `/color sunset`
    Отображает название, цвета, теги и количество лайков для каждой палитры."""
    state: bool = True

    bot: telebot.TeleBot
    keyboard_factory: CallbackData

    _api_url: str = "https://colormagic.app/api/palette/search"
    _timeout: int = 10

    def set_handlers(self, bot: telebot.TeleBot):
        """Установка обработчиков сообщений."""

        self.bot = bot
        self.keyboard_factory = CallbackData("palette_nav", "query", "page",
                                              prefix=self.commands[0])

        @bot.message_handler(commands=self.commands)
        def palette_message_handler(message: types.Message):
            query = self.__extract_query(message.text)
            if not query:
                bot.send_message(
                    chat_id=message.chat.id,
                    text="Укажите запрос. Пример: `/palette forest`",
                    parse_mode="Markdown"
                )
                return
            self.__search_and_send(message.chat.id, query, page=0)

        @bot.callback_query_handler(func=None, config=self.keyboard_factory.filter())
        def palette_callback_handler(call: types.CallbackQuery):
            data = self.keyboard_factory.parse(callback_data=call.data)
            query = data["query"]
            page = int(data["page"]) if data["page"].isdigit() else 0
            self.__search_and_send(call.message.chat.id, query, page=page)
            bot.answer_callback_query(call.id)

    def __extract_query(self, text: str) -> str:
        parts = text.strip().split(maxsplit=1)
        return parts[1].strip() if len(parts) > 1 else ""

    def __fetch_palettes(self, query: str) -> list:
        try:
            response = requests.get(
                self._api_url,
                params={"q": query},
                timeout=self._timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as ex:
            logging.error("Ошибка запроса к ColorMagic API: %s", ex)
            return []

    def __search_and_send(self, chat_id: int, query: str, page: int):
        palettes = self.__fetch_palettes(query)
        if not palettes:
            self.bot.send_message(
                chat_id=chat_id,
                text=f"По запросу *{query}* ничего не найдено.",
                parse_mode="Markdown"
            )
            return

        total = len(palettes)
        palette = palettes[page]
        text = self.__format_palette(palette, page, total, query)

        markup = self.__build_nav_markup(query, page, total)
        self.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=markup
        )

    def __format_palette(self, palette: dict, index: int, total: int, query: str) -> str:
        name = palette.get("text", "—")
        colors = palette.get("colors", [])
        tags = palette.get("tags", [])
        likes = palette.get("likesCount", 0)
        created_raw = palette.get("createdAt", "")
        palette_id = palette.get("id", "—")

        created = self.__format_date(created_raw)
        color_hex = "\n".join(f"  `{c}`" for c in colors)
        tags_str = ", ".join(tags) if tags else "—"
        preview_url = f"https://colormagic.app/palette/{palette_id}"

        return (
            f"🎨 *{name}*  ({index + 1}/{total})\n"
            f"Запрос: `{query}`\n\n"
            f"*Цвета:*\n{color_hex}\n\n"
            f"{'  '.join(colors)}\n\n"
            f"🏷 *Теги:* {tags_str}\n"
            f"❤️ *Лайки:* {likes}\n"
            f"📅 *Добавлена:* {created}\n"
            f"🆔 `{palette_id}`\n"
            f"🔗 [Посмотреть палитру]({preview_url})"
        )

    def __format_date(self, raw: str) -> str:
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return dt.strftime("%d.%m.%Y %H:%M")
        except (ValueError, AttributeError):
            return raw

    def __build_nav_markup(self, query: str, page: int, total: int):
        markup = types.InlineKeyboardMarkup()
        buttons = []

        if page > 0:
            prev_data = self.keyboard_factory.new(
                palette_nav="nav", query=query, page=str(page - 1)
            )
            buttons.append(types.InlineKeyboardButton("← Назад", callback_data=prev_data))

        if page < total - 1:
            next_data = self.keyboard_factory.new(
                palette_nav="nav", query=query, page=str(page + 1)
            )
            buttons.append(types.InlineKeyboardButton("Вперёд →", callback_data=next_data))

        if buttons:
            markup.row(*buttons)

        return markup if buttons else None
