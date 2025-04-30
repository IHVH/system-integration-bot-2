"""
Модуль для интеграции с API Waifu.im и реализации функциональности поиска аниме-изображений.
"""

import logging
from typing import List
import requests
from telebot import TeleBot, types
from bot_func_abc import AtomicBotFunctionABC


class WaifuFunction(AtomicBotFunctionABC):
    """Функция для поиска изображений по тегу с использованием Waifu.im API."""

    commands: List[str] = ["waifu"]
    authors: List[str] = ["ТВОЙ_НИК"]
    about: str = "Поиск аниме изображений по тегу"
    description: str = (
        "Позволяет искать аниме изображения по тегу.\n"
        "Пример: /waifu maid 3\n"
        "Выведет 3 изображения с тегом 'maid'."
    )
    state: bool = True

    bot: TeleBot

    def set_handlers(self, bot: TeleBot):
        """Регистрирует обработчики команды /waifu."""
        self.bot = bot

        @bot.message_handler(commands=self.commands)
        def waifu_handler(message: types.Message):
            """Обработчик команды /waifu <тег> <кол-во>."""
            try:
                args = message.text.strip().split()[1:]  # Пропускаем /waifu
                if not args:
                    bot.send_message(
                        message.chat.id,
                        "Укажи тег и (опционально) количество. Пример: /waifu maid 3"
                    )
                    return

                tag = args[0]
                count = int(args[1]) if len(args) > 1 else 1
                images = self.__get_waifu_images(tag, count)

                if not images:
                    bot.send_message(message.chat.id, "Ничего не найдено по тегу.")
                    return

                for url in images:
                    bot.send_photo(message.chat.id, photo=url)

            except ValueError:
                bot.send_message(message.chat.id, "Неверный формат количества изображений.")
            except requests.exceptions.RequestException as err:  # Ловим только ошибки запросов
                logging.error("Ошибка при запросе к API Waifu.im: %s", err)
                bot.send_message(message.chat.id, "Ошибка при запросе к API.")
            except KeyboardInterrupt:
                logging.info("Прерывание работы пользователя.")
                bot.send_message(message.chat.id, "Запрос был прерван.")
            except Exception as err:  # Ловим непредвиденные ошибки, но избегаем широких исключений
                logging.error("Непредвиденная ошибка в процессе обработки: %s", err)
                bot.send_message(message.chat.id, "Произошла непредвиденная ошибка.")

    def __get_waifu_images(self, tag: str, count: int) -> List[str]:
        """Запрос к API Waifu.im и получение изображений."""
        url = "https://api.waifu.im/search"
        params = {
            "included_tags": [tag],
            "limit": count
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return [img["url"] for img in data.get("images", [])]
        except requests.exceptions.RequestException as err:
            logging.error("Ошибка при обращении к Waifu.im: %s", err)
            return []
