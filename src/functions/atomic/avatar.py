"""Модуль генерации аватара. PNG через Pillow, SVG через avatar.oxro.io."""

import io
from typing import Dict, List, Optional, Tuple

import requests
from PIL import Image, ImageDraw, ImageFont

import telebot
from telebot import types
from telebot.callback_data import CallbackData

from bot_func_abc import AtomicBotFunctionABC  # pylint: disable=import-error


_API_URL = "https://avatar.oxro.io/avatar.svg"

_COLORS: Dict[str, dict] = {
    "e53935": {"rgb": (229, 57,  53),  "label": "🔴 Красный"},
    "d81b60": {"rgb": (216, 27,  96),  "label": "🩷 Розовый"},
    "8e24aa": {"rgb": (142, 36, 170),  "label": "🟣 Фиолетовый"},
    "3949ab": {"rgb": (57,  73, 171),  "label": "💜 Индиго"},
    "1e88e5": {"rgb": (30, 136, 229),  "label": "🔵 Синий"},
    "00acc1": {"rgb": (0,  172, 193),  "label": "🩵 Бирюзовый"},
    "43a047": {"rgb": (67, 160,  71),  "label": "🟢 Зелёный"},
    "fb8c00": {"rgb": (251, 140,  0),  "label": "🟠 Оранжевый"},
    "fdd835": {"rgb": (253, 216, 53),  "label": "🟡 Жёлтый"},
    "c0ca33": {"rgb": (192, 202, 51),  "label": "🍋 Лаймовый"},
    "00897b": {"rgb": (0,  137, 123),  "label": "🌊 Морская волна"},
    "1565c0": {"rgb": (21,  101, 192), "label": "🔷 Тёмно-синий"},
    "6d4c41": {"rgb": (109, 76,  65),  "label": "🟤 Коричневый"},
    "546e7a": {"rgb": (84,  110, 122), "label": "🩶 Серо-синий"},
    "b71c1c": {"rgb": (183, 28,  28),  "label": "🍷 Тёмно-красный"},
    "26a69a": {"rgb": (38,  166, 154), "label": "🌿 Мятный"},
}

_SHAPES: Dict[str, dict] = {
    "circle": {"rounded": "250", "radius_ratio": 0.5, "label": "⭕ Круг"},
    "soft":   {"rounded": "50",  "radius_ratio": 0.1, "label": "🔲 Скруглённый"},
    "square": {"rounded": "0",   "radius_ratio": 0.0, "label": "⬛ Квадрат"},
}

_FORMATS: Dict[str, str] = {
    "png": "PNG",
    "svg": "SVG",
}

_FONT_PATHS: List[str] = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


class AvatarBotFunction(AtomicBotFunctionABC):
    """Генератор аватара. Шаг 1 — цвет, шаг 2 — форма и формат."""

    commands = ["avatar"]
    authors  = ["Kirillka93"]
    about    = "Генерация аватара"
    description = (
        "Генерирует персональный аватар по имени пользователя.\n"
        "Команда /avatar запускает двухшаговый мастер:\n"
        "  1. Выбор цвета фона.\n"
        "  2. Выбор формы и формата (PNG или SVG)."
    )
    state = True

    def __init__(self) -> None:
        prefix = self.commands[0]
        self._color_factory = CallbackData("bg_color", prefix=f"{prefix}_c")
        self._opts_factory  = CallbackData("bg_color", "shape_key", "fmt", prefix=f"{prefix}_o")

    def __repr__(self):
        """Возвращает строковое представление объекта."""
        return f"<AvatarBotFunction команды={self.commands}>"

    def set_handlers(self, bot: telebot.TeleBot) -> None:
        """Регистрирует обработчики команды /avatar и callback-кнопок."""
        @bot.message_handler(commands=self.commands)
        def handle_avatar_command(message: telebot.types.Message) -> None:
            bot.send_message(
                chat_id=message.chat.id,
                text="🖼 <b>Генератор аватара</b>\n\nШаг 1 из 2 — выберите цвет фона:",
                reply_markup=self._build_color_keyboard(),
                parse_mode="HTML",
            )

        @bot.callback_query_handler(func=None, config=self._color_factory.filter())
        def handle_color_selection(call: types.CallbackQuery) -> None:
            parsed   = self._color_factory.parse(callback_data=call.data)
            bg_color = parsed.get("bg_color", "")
            if bg_color not in _COLORS:
                bot.answer_callback_query(call.id, "❌ Неверный выбор цвета")
                return
            bot.answer_callback_query(call.id)
            bot.edit_message_text(
                text=(
                    f"✅ Цвет: {_COLORS[bg_color]['label']}\n\n"
                    "Шаг 2 из 2 — выберите форму и формат:"
                ),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=self._build_opts_keyboard(bg_color),
                parse_mode="HTML",
            )

        @bot.callback_query_handler(func=None, config=self._opts_factory.filter())
        def handle_opts_selection(call: types.CallbackQuery) -> None:
            parsed    = self._opts_factory.parse(callback_data=call.data)
            bg_color  = parsed.get("bg_color", "")
            shape_key = parsed.get("shape_key", "")
            fmt       = parsed.get("fmt", "")
            if bg_color not in _COLORS or shape_key not in _SHAPES or fmt not in _FORMATS:
                bot.answer_callback_query(call.id, "❌ Неверный выбор")
                return
            bot.answer_callback_query(call.id, "⏳ Генерирую аватар…")
            username = self._resolve_display_name(call.from_user)
            shape    = _SHAPES[shape_key]
            if fmt == "png":
                self._send_as_photo(bot, call, username, bg_color, shape)
            else:
                self._send_as_svg(bot, call, username, bg_color, shape)

    @staticmethod
    def _send_as_photo(bot, call, username, bg_color, shape):
        png_buf = AvatarBotFunction._generate_png(
            username, _COLORS[bg_color]["rgb"], shape["radius_ratio"]
        )
        caption = (
            f"🖼 <b>Аватар</b>: {username}\n"
            f"🎨 {_COLORS[bg_color]['label']}  🔲 {shape['label']}  📁 PNG"
        )
        bot.send_photo(
            chat_id=call.message.chat.id,
            photo=png_buf,
            caption=caption,
            parse_mode="HTML",
        )

    @staticmethod
    def _send_as_svg(bot, call, username, bg_color, shape):
        svg_buf, error = AvatarBotFunction._fetch_svg(
            name=username,
            bg_color=bg_color,
            rounded=str(shape["rounded"]),
        )
        if error or svg_buf is None:
            bot.send_message(
                chat_id=call.message.chat.id,
                text=f"❌ Не удалось получить SVG.\nПричина: <code>{error}</code>",
                parse_mode="HTML",
            )
            return
        caption = (
            f"🖼 <b>Аватар</b>: {username}\n"
            f"🎨 {_COLORS[bg_color]['label']}  🔲 {shape['label']}  📁 SVG"
        )
        bot.send_document(
            chat_id=call.message.chat.id,
            document=svg_buf,
            caption=caption,
            parse_mode="HTML",
        )

    def _build_color_keyboard(self):
        markup = types.InlineKeyboardMarkup(row_width=2)
        buttons = [
            types.InlineKeyboardButton(
                text=str(info["label"]),
                callback_data=self._color_factory.new(bg_color=hex_code),
            )
            for hex_code, info in _COLORS.items()
        ]
        markup.add(*buttons)
        return markup

    def _build_opts_keyboard(self, bg_color):
        """Форма и формат объединены: 3 строки x 2 кнопки (PNG / SVG)."""
        markup = types.InlineKeyboardMarkup(row_width=2)
        buttons = [
            types.InlineKeyboardButton(
                text=f"{shape['label']} {fmt_label}",
                callback_data=self._opts_factory.new(
                    bg_color=bg_color, shape_key=shape_key, fmt=fmt_key
                ),
            )
            for shape_key, shape in _SHAPES.items()
            for fmt_key, fmt_label in _FORMATS.items()
        ]
        markup.add(*buttons)
        return markup

    @staticmethod
    def _load_font(size: int) -> ImageFont.FreeTypeFont:
        for path in _FONT_PATHS:
            try:
                return ImageFont.truetype(path, size)
            except (IOError, OSError):
                continue
        try:
            return ImageFont.load_default(size=size)  # type: ignore[call-arg]
        except TypeError:
            return ImageFont.load_default()  # type: ignore[return-value]

    @staticmethod
    def _get_initials(name: str) -> str:
        """'Иван Петров' -> 'ИП', 'Алекс' -> 'АЛ'"""
        parts = name.strip().split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[1][0]).upper()
        return name[:2].upper() if len(name) >= 2 else name[0].upper()

    @staticmethod
    def _generate_png(
        username: str,
        rgb: Tuple[int, int, int],
        radius_ratio: float,
    ) -> io.BytesIO:
        size     = 512
        initials = AvatarBotFunction._get_initials(username)

        img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        radius = int(size * radius_ratio)

        if radius_ratio >= 0.5:
            draw.ellipse([0, 0, size - 1, size - 1], fill=rgb)
        elif radius > 0:
            draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=rgb)
        else:
            draw.rectangle([0, 0, size - 1, size - 1], fill=rgb)

        font = AvatarBotFunction._load_font(size // 3)
        bbox = draw.textbbox((0, 0), initials, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        pos = ((size - text_w) / 2 - bbox[0], (size - text_h) / 2 - bbox[1])
        draw.text(pos, initials, fill=(255, 255, 255), font=font)

        img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        buf.name = f"avatar_{username}.png"
        return buf

    @staticmethod
    def _fetch_svg(
        name: str, bg_color: str, rounded: str
    ) -> Tuple[Optional[io.BytesIO], Optional[str]]:
        params = {
            "name": name, "background": bg_color,
            "color": "ffffff", "bold": "true",
            "rounded": rounded, "length": "2",
        }
        try:
            resp = requests.get(_API_URL, params=params, timeout=10)
            resp.raise_for_status()
            buf = io.BytesIO(resp.content)
            buf.name = f"avatar_{name}.svg"
            return buf, None
        except requests.exceptions.Timeout:
            return None, "Превышено время ожидания ответа от avatar.oxro.io"
        except requests.exceptions.ConnectionError:
            return None, "Нет соединения с avatar.oxro.io"
        except requests.exceptions.HTTPError as exc:
            return None, f"HTTP {exc.response.status_code}"
        except requests.RequestException as exc:
            return None, str(exc)

    @staticmethod
    def _resolve_display_name(user: types.User) -> str:
        return user.username or user.first_name or "User"
