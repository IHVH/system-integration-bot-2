"""Module for creating qr codes"""

from typing import List
from io import BytesIO
import telebot
import requests
from telebot import types
from bot_func_abc import AtomicBotFunctionABC

class QRBotFunction(AtomicBotFunctionABC):
    """Function work with qrtag api"""

    commands: List[str] = ["make_qr_png", "make_qr_svg"]
    authors: List[str] = ["Fant0mSeeker"]
    about: str = "Создает QR-код из ссылки"
    description: str = """Функция предназначена для создания QR-кода при помощи API QRtag.
        Для вызова функции можно использовать следующие команды:
        /make_qr_png для создания png
        /make_qr_svg для создания svg
        Параметры:
            Обязательные:
                [ссылка] 
            Необязательные:
                [размер]
        """
    state: bool = True

    bot: telebot.TeleBot

    def set_handlers(self, bot: telebot.TeleBot):
        """Set message handlers"""
        self.bot = bot

        @bot.message_handler(commands=self.commands)
        def qr_message_hendler(message: types.Message):
            self.get_qr(message)

    def get_qr(self, message: types.Message):
        """Get QR code"""
        parts = message.text[1:].split(" ")
        if parts[0] == self.commands[0]:
            self.qr_url(message,parts,"png")
        elif parts[0] == self.commands[1]:
            self.qr_url(message,parts,"svg")

    def qr_url(self, message: types.Message, parts: str, qrtype: str):
        """Getting url for get QR code"""

        req = ""
        match len(parts):
            case 1:
                self.bot.send_message(text="Добавте параметры!!!", chat_id=message.chat.id)
            case 2:
                req = ("https://qrtag.net/api/qr"+
                        f".{qrtype}" +
                        f"?url={parts[1]}")
            case 3:
                if parts[2].isdigit():
                    req = ("https://qrtag.net/api/qr" +
                            f"_{parts[2]}.{qrtype}" +
                            f"?url={parts[1]}")
                else:
                    self.bot.send_message(text="Команда должна выглядить так: " +
                        f"/make_qr_{qrtype} [ссылка] [размер]"  , chat_id=message.chat.id)
            case _:
                self.bot.send_message(text="Есть лишние параметры!!!", chat_id=message.chat.id)

        if req != "":
            if qrtype == "png":
                self.bot.send_photo(chat_id=message.chat.id,photo=req)
            else:
                response = requests.get(url=req, timeout=20)
                if response.status_code == 200:
                    svg_bytes = BytesIO(response.text.encode('utf-8'))
                    svg_bytes.name = 'output.svg'
                    self.bot.send_document(chat_id=message.chat.id,document=svg_bytes)
