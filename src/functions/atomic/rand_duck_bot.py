"""
 Модуль для реализации функции бота для получения случайных картинок уток.
 Использует API RandomDuck.
 """

import logging
import requests
import telebot
from telebot import types
from bot_func_abc import AtomicBotFunctionABC

class AtomicRandomDuckBotFunction(AtomicBotFunctionABC):

    """
    Модуль для создания одной или нескольких картинок уток.
    Также изображение с указанным расширением.
    """

    commands = ["randomduck", "multiduck", "ducktype"]
    authors = ["GrandGeraldio"]
    about = "Генератор картинок уток!"
    description = """Команды: /randomduck - одно изображение,
                   /multiduck <1-7> - несколько,
                   /ducktype <gif|jpg|jpeg|png> - по типу.
                   """
    state = True

    def __init__(self):
        self.bot = None

    def set_handlers(self, bot: telebot.TeleBot):
        """Set message handlers"""
        self.bot = bot

        @bot.message_handler(commands=self.commands)
        def handle_commands(message: types.Message):
            cmd = message.text.split()[0][1:]
            if cmd == "randomduck":
                self._send_duck_images(message, count=1)
            elif cmd == "multiduck":
                try:
                    count = int(message.text.split()[1])
                    if 1 <= count <= 7:
                        self._send_duck_images(message, count)
                    else:
                        bot.send_message(message.chat.id, "Число от 1 до 7!")
                except (IndexError, ValueError):
                    bot.send_message(message.chat.id, "Использование: /multiduck <1-7>")
            elif cmd == "ducktype":
                try:
                    ext = message.text.split()[1].lower()
                    if ext in ('gif', 'jpg', 'jpeg', 'png'):
                        self._send_duck_images(message, count=1, extension=ext)
                    else:
                        bot.send_message(message.chat.id, "Тип: gif, jpg, jpeg, png")
                except IndexError:
                    bot.send_message(message.chat.id, "Использование: /ducktype <gif|jpg|jpeg|png>")

    def _send_duck_images(self, message: types.Message, count=1, extension=None):
        images = self._get_random_duck_images(count, extension)
        if not images:
            self.bot.send_message(message.chat.id,
                                  f"Не удалось получить {'изо-ние' if count == 1 else 'изо-ния'}.")
            return
        for img in images:
            self.bot.send_photo(message.chat.id, img)

    def _get_random_duck_images(self, count=1, extension=None):
        images = []
        for _ in range(count * 7):
            if len(images) >= count:
                break
            try:
                response = requests.get("https://random-d.uk/api/v2/random", timeout=5)
                response.raise_for_status()
                img_url = response.json().get("url")
                if not isinstance(img_url, str):
                    continue
                if extension and not img_url.lower().endswith(f".{extension}"):
                    continue
                if img_url and img_url not in images:
                    images.append(img_url)
            except (requests.exceptions.RequestException, ValueError) as ex:
                logging.warning("Failed to fetch duck image: %s", ex)
        return images
