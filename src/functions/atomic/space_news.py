"""
Модуль для интеграции с Spaceflight News API v4.
Позволяет получать последние новости космонавтики.
"""
import logging
from typing import List

import requests
import telebot
from telebot import types

# Импортируем базовый класс для всех функций бота
from bot_func_abc import AtomicBotFunctionABC

class SpaceNewsBotFunction(AtomicBotFunctionABC):
    """
    Класс для получения и отображения последних космических новостей
    через Spaceflight News API.
    """
    # Список команд, на которые будет реагировать эта функция
    commands: List[str] = ["space_news", "sn"]
    # Ваш логин на GitHub (укажите свой)
    authors: List[str] = ["your_github_username"]
    # Краткое описание функции
    about: str = "Показывает последние новости космонавтики."
    # Подробное описание, которое будет показано пользователю
    description: str = (
        "Используйте команду /space_news или /sn, "
        "чтобы получить последние новости из мира космонавтики. "
        "Источник: Spaceflight News API."
    )
    # Функция включена по умолчанию
    state: bool = True

    # URL API
    API_URL = "https://api.spaceflightnewsapi.net/v4/articles/?limit=5"

    def __init__(self):
        self.bot = None
        self.logger = logging.getLogger(__name__)

    def set_handlers(self, bot: telebot.TeleBot):
        """
        Регистрирует обработчики команд для функции.
        Этот метод вызывается ядром бота.
        """
        self.bot = bot
        self.logger.info("Регистрация обработчиков Spaceflight News API")

        # Обработчик для команд из списка self.commands
        @bot.message_handler(commands=self.commands)
        def space_news_handler(message: types.Message):
            """
            Обрабатывает входящую команду, делает запрос к API
            и отправляет результат пользователю.
            """
            try:
                self.logger.info("Запрос к Spaceflight News API...")
                # Делаем GET-запрос к API
                response = requests.get(self.API_URL, timeout=10)
                # Проверяем статус ответа
                response.raise_for_status()
                data = response.json()

                articles = data.get('results', [])
                if not articles:
                    bot.reply_to(message, "К сожалению, новостей не найдено.")
                    return

                # Формируем сообщение для пользователя
                news_message = "🗞 **Последние новости космонавтики:**\n\n"
                for i, article in enumerate(articles[:5], 1):
                    title = article.get('title', 'Без заголовка')
                    url = article.get('url', '#')
                    news_site = article.get('news_site', 'Неизвестный источник')
                    news_message += f"{i}. [{title}]({url}) - _{news_site}_\n"

                # Отправляем сообщение с поддержкой Markdown
                bot.send_message(
                    message.chat.id,
                    news_message,
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                )

            except requests.exceptions.RequestException as e:
                self.logger.error("Ошибка сети или API: %s", e)
                bot.reply_to(message, f"Не удалось получить новости. Ошибка: {e}")
            except (KeyError, TypeError, ValueError) as e:
                self.logger.error("Ошибка обработки данных: %s", e)
                bot.reply_to(message, "Произошла ошибка при обработке данных.")
