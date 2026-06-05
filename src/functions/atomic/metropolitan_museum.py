"""Module implementation of the atomic function of the telegram bot. Met Museum Collection API integration."""
import logging
from typing import List
from urllib.parse import quote
import requests
import telebot
from telebot import types
from bot_func_abc import AtomicBotFunctionABC

class MetMuseumFunction(AtomicBotFunctionABC):
    """Интеграция с API коллекции Метрополитен-музея (США)."""
    commands: List[str] = ['metsearch', 'metinfo']
    authors: List[str] = ['Daniil-2005']
    about: str = 'Поиск по коллекции Метрополитен-музея'
    description: str = (
        '/metsearch [запрос] [кол-во] — поиск артефактов\n'
        '/metinfo [ID] — информация по объекту'
    )
    state: bool = True
    bot: telebot.TeleBot

    BASE_URL = "https://collectionapi.metmuseum.org/public/collection/v1"
    MAX_RESULTS = 10
    TIMEOUT = 5

    def set_handlers(self, bot: telebot.TeleBot):
        """Устанавливает обработчики команд."""
        self.bot = bot

        @bot.message_handler(commands=self.commands)
        def handle_met_museum(message: types.Message):
            self._route_command(message)

    def _route_command(self, message: types.Message):
        try:
            parts = message.text.split()
            command = parts[0].lstrip('/').lower()

            if command == 'metsearch':
                self._handle_search(message, parts)
            elif command == 'metinfo':
                self._handle_info(message, parts)
            else:
                self.bot.send_message(message.chat.id, self.description)
        except Exception as e:
            logging.exception("Ошибка маршрутизации команды Met Museum")
            self.bot.send_message(message.chat.id, "Внутренняя ошибка функции.")

    def _handle_search(self, message: types.Message, parts: List[str]):
        query = parts[1] if len(parts) > 1 else 'art'
        limit = self._parse_limit(parts[2] if len(parts) > 2 else '3')

        status_msg = self.bot.reply_to(message, f"Поиск: {query}...")

        try:
            encoded_query = quote(query)
            search_url = f"{self.BASE_URL}/search?q={encoded_query}&hasImages=true"
            response = requests.get(search_url, timeout=self.TIMEOUT)
            response.raise_for_status()
            search_data = response.json()

            object_ids = search_data.get('objectIDs', [])
            if not object_ids:
                self.bot.edit_message_text(
                    f"Ничего не найдено: «{query}»",
                    chat_id=message.chat.id,
                    message_id=status_msg.message_id
                )
                return

            selected_ids = object_ids[:min(limit, self.MAX_RESULTS)]
            self.bot.edit_message_text(
                f"Найдено: {len(selected_ids)}. Формирую ответ...",
                chat_id=message.chat.id,
                message_id=status_msg.message_id
            )

            for obj_id in selected_ids:
                self._send_object_details(message.chat.id, obj_id)

        except requests.RequestException as e:
            logging.error("Ошибка сети при поиске Met Museum: %s", e)
            self.bot.edit_message_text(
                "Ошибка сети. Попробуйте позже.",
                chat_id=message.chat.id,
                message_id=status_msg.message_id
            )
        except Exception as e:
            logging.exception("Непредвиденная ошибка поиска Met Museum")
            self.bot.edit_message_text(
                "Ошибка обработки данных.",
                chat_id=message.chat.id,
                message_id=status_msg.message_id
            )

    def _handle_info(self, message: types.Message, parts: List[str]):
        if len(parts) < 2:
            self.bot.reply_to(message, "Укажите ID объекта. Пример: /metinfo 437133")
            return
        try:
            object_id = int(parts[1])
        except ValueError:
            self.bot.reply_to(message, "ID должен быть числом.")
            return

        self._send_object_details(message.chat.id, object_id)

    def _send_object_details(self, chat_id: int, object_id: int):
        try:
            obj_url = f"{self.BASE_URL}/objects/{object_id}"
            response = requests.get(obj_url, timeout=self.TIMEOUT)
            response.raise_for_status()
            data = response.json()

            text = self._format_object_info(data)
            image_url = data.get('primaryImage')

            if image_url:
                try:
                    self.bot.send_photo(chat_id, photo=image_url, caption=text, parse_mode='HTML')
                    return
                except Exception:
                    pass
            self.bot.send_message(chat_id, text, parse_mode='HTML')

        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                self.bot.send_message(chat_id, f"Объект с ID {object_id} не найден.")
            else:
                logging.error("Ошибка API Met Museum (ID %s): %s", object_id, e)
                self.bot.send_message(chat_id, "Ошибка API.")
        except Exception as e:
            logging.exception("Ошибка загрузки деталей объекта %s", object_id)
            self.bot.send_message(chat_id, "Не удалось загрузить данные.")

    def _format_object_info(self, data: dict) -> str:
        title = data.get('title') or 'Без названия'
        artist = data.get('artistDisplayName') or 'Неизвестен'
        date = data.get('objectDate') or 'Датировка неизвестна'
        department = data.get('department') or 'Не указан'
        culture = data.get('culture')
        medium = data.get('medium')
        dimensions = data.get('dimensions')
        obj_url = data.get('objectURL')

        lines = [
            f"<b> {self._escape_html(title)}</b>",
            f" <i>{self._escape_html(artist)}</i>",
            f" {self._escape_html(date)}",
            f" Отдел: {self._escape_html(department)}",
        ]
        if culture:
            lines.append(f" Культура: {self._escape_html(culture)}")
        if medium:
            lines.append(f" Материал: {self._escape_html(medium)}")
        if dimensions:
            dim_text = self._escape_html(dimensions)
            lines.append(f" {dim_text[:100]}{'...' if len(dim_text) > 100 else ''}")
        if obj_url:
            lines.append(f"\n <a href='{obj_url}'>Страница на сайте музея</a>")

        return '\n'.join(lines)

    @staticmethod
    def _escape_html(text: str) -> str:
        if not text:
            return ""
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    @staticmethod
    def _parse_limit(value: str) -> int:
        try:
            limit = int(value)
            return max(1, min(limit, 20))
        except ValueError:
            return 3