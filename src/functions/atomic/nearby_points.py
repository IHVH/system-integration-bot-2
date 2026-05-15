"""Модуль для поиска ближайших пунктов через API petersburg.ru по геолокации."""

import logging
from typing import List

import requests
import telebot
from telebot import types

from bot_func_abc import AtomicBotFunctionABC


class NearbyPointsBotFunction(AtomicBotFunctionABC):
    """
    Функция бота: запрос геолокации у пользователя и получение списка ближайших пунктов
    с использованием API petersburg.ru.
    """

    commands: List[str] = ["nearby", "points"]
    authors: List[str] = ["6yKeT_GePaHeK"]
    about: str = "Поиск ближайших пунктов"
    description: str = (
        "Эта функция позволяет найти ближайшие пункты (например, аптеки, магазины, "
        "пункты выдачи) в Санкт-Петербурге на основе вашей текущей геолокации. "
        "После вызова команды /nearby, бот попросит вас поделиться местоположением. "
        "На основе полученных координат выполняется запрос к API petersburg.ru, "
        "и вы получаете список ближайших пунктов с указанием названия и адреса. "
        "Если API возвращает дополнительные данные (расстояние, график работы), "
        "они также будут отображены."
    )
    state: bool = True

    API_URL = "https://petersburg.ru/mainPortal/api_services/view/2251"

    def __init__(self):
        super().__init__()
        self.bot: telebot.TeleBot | None = None

    def set_handlers(self, bot: telebot.TeleBot) -> None:
        """Регистрирует обработчики команд и колбэков для данной функции."""
        self.bot = bot

        @bot.message_handler(commands=self.commands)
        def request_location(message: types.Message) -> None:
            """
            Обработчик команды: отправляет запрос на отправку геолокации
            и устанавливает следующий шаг.
            """
            sent_msg = bot.send_message(
                message.chat.id,
                "📍 Пожалуйста, отправьте ваше текущее местоположение, "
                "используя кнопку прикрепления геопозиции.",
                reply_markup=types.ReplyKeyboardRemove()
            )
            # Регистрируем обработчик следующего сообщения от этого пользователя
            bot.register_next_step_handler(sent_msg, self.process_location)

    def process_location(self, message: types.Message) -> None:
        """
        Обработчик ответа пользователя. Проверяет, что получена геолокация,
        затем запрашивает API и выводит результаты.
        """
        chat_id = message.chat.id

        # Проверяем, что пользователь отправил именно локацию
        if message.location is None:
            self.bot.send_message(
                chat_id,
                "❌ Вы не отправили геолокацию. Попробуйте ещё раз командой /nearby."
            )
            return

        lat = message.location.latitude
        lon = message.location.longitude

        # Уведомляем пользователя о начале поиска
        processing_msg = self.bot.send_message(
            chat_id,
            f"🔍 Ищем ближайшие пункты по координатам: {lat:.4f}, {lon:.4f}..."
        )

        try:
            # Выполняем запрос к API
            response = requests.get(
                self.API_URL,
                params={"lat": lat, "lon": lon},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            # Формируем читаемый ответ
            result_text = self._format_api_response(data, lat, lon)

            # Удаляем сообщение "Ищем..." и отправляем результат
            self.bot.delete_message(chat_id, processing_msg.message_id)
            self.bot.send_message(chat_id, result_text, parse_mode="HTML")

        except requests.exceptions.Timeout:
            self.bot.send_message(chat_id, "⏰ Превышено время ожидания ответа от API.")
        except requests.exceptions.RequestException as e:
            logging.exception("Ошибка при запросе к API: %s", e)
            self.bot.send_message(
                chat_id,
                "⚠️ Не удалось получить данные от сервера. Попробуйте позже."
            )
        except Exception as e:  # pylint: disable=broad-except
            logging.exception("Непредвиденная ошибка: %s", e)
            self.bot.send_message(chat_id, "❌ Произошла внутренняя ошибка.")

    def _format_api_response(self, data: dict, lat: float, lon: float) -> str:
        """
        Преобразует JSON-ответ API в текст для отправки пользователю.
        Ожидаемая структура ответа может уточняться по документации.
        """
        # Попытка извлечь список пунктов из наиболее вероятных полей
        points = None
        if isinstance(data, list):
            points = data
        elif isinstance(data, dict):
            for key in ("data", "results", "items", "points"):
                if key in data and isinstance(data[key], list):
                    points = data[key]
                    break
            if points is None and "features" in data:  # GeoJSON
                points = data["features"]

        if not points:
            # Если структура не распознана, выводим сырые данные
            return (
                f"📡 Получен ответ от API (координаты: {lat:.4f}, {lon:.4f}):\n"
                f"<code>{str(data)[:500]}</code>"
            )

        if len(points) == 0:
            return "😕 Рядом с вами ничего не найдено."

        # Формируем красивое сообщение
        lines = [f"🏙 <b>Ближайшие пункты</b> (координаты: {lat:.4f}, {lon:.4f}):\n"]
        for i, point in enumerate(points[:10], 1):  # не более 10 пунктов
            # Пытаемся извлечь название и адрес из разных вариантов структуры
            if isinstance(point, dict):
                name = point.get("name") or point.get("title") or point.get("Название") or f"Пункт {i}"
                address = point.get("address") or point.get("Адрес") or point.get("location") or "Адрес не указан"
                distance = point.get("distance")
                dist_str = f" ({distance:.0f} м)" if isinstance(distance, (int, float)) else ""
                lines.append(f"{i}. <b>{name}</b>{dist_str}\n   📍 {address}")
            else:
                lines.append(f"{i}. {str(point)[:100]}")
        return "\n".join(lines)