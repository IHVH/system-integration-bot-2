# -*- coding: utf-8 -*-
"""Модуль для перевода и анализа текста через MyMemory и Tisane API."""

import os
import requests
import telebot
from bot_func_abc import AtomicBotFunctionABC


class TranslateBotFunction(AtomicBotFunctionABC):
    """Перевод и анализ текста через MyMemory и Tisane APIs.

    Реализует единый обработчик команды /translate. Возвращает перевод, количество
    найденных оскорблений и топ‑3 темы. Не сохраняет отчёты в GitHub.
    """

    commands = ["translate"]
    authors = ["shiroyashinu"]
    about = "Перевод и анализ текста"
    description = (
        "Отправь любой текст на русском или английском, и бот вернёт перевод,\n"
        "информацию об оскорблениях и темах.\nПример: /translate привет мир"
    )
    state = True

    def __init__(self):
        """Инициализация функции перевода и анализа текста."""
        self.tisane_key = os.getenv("TISANE_API_KEY", "TISANE_KEY")
        # MyMemory не требует токена, но можно добавить переменную при необходимости

    @staticmethod
    def _is_russian(text: str) -> bool:
        """Определяет, содержит ли текст русские буквы."""
        return any('а' <= ch <= 'я' or ch == 'ё' for ch in text.lower())

    def _translate(self, text: str, target: str = "en") -> str:
        """Переводит текст через бесплатный API MyMemory."""
        source = "ru" if self._is_russian(text) else "en"
        url = "https://api.mymemory.translated.net/get"
        params = {"q": text, "langpair": f"{source}|{target}"}
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            translated = data.get("responseData", {}).get("translatedText", text)
            return (
                translated.replace("<i>", "")
                .replace("</i>", "")
                .replace("&quot;", '"')
            )
        except requests.RequestException as exc:
            print(f"Ошибка перевода: {exc}")
            return text

    def _analyze(self, text: str) -> dict:
        """Анализирует текст через Tisane API: оскорбления, тональность, темы."""
        url = "https://api.tisane.ai/parse"
        headers = {
            "Ocp-Apim-Subscription-Key": self.tisane_key,
            "Content-Type": "application/json",
        }
        payload = {
            "content": text,
            "language": "en",
            "settings": {"abuse": True, "sentiment": True, "topics": True},
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            print(f"Ошибка анализа: {exc}")
            return {"abuse": [], "sentiment_expressions": [], "topics": []}

    def set_handlers(self, bot: telebot.TeleBot):
        """Регистрирует обработчик команды /translate в боте."""
        @bot.message_handler(commands=self.commands)
        def handle(message: telebot.types.Message):
            # Получаем текст после команды
            text = message.text.partition(" ")[2].strip()
            if not text:
                bot.reply_to(message, "Укажите текст после команды. Пример: /translate привет")
                return

            bot.reply_to(message, "🔍 Обрабатываю ваш запрос…")

            # Определяем направление перевода
            if self._is_russian(text):
                translated = self._translate(text, "en")
                lang_info = "🇷🇺 Русский → 🇬🇧 Английский"
                analysis_input = translated
            else:
                translated = self._translate(text, "ru")
                lang_info = "🇬🇧 Английский → 🇷🇺 Русский"
                analysis_input = text

            # Выполняем анализ текста
            result = self._analyze(analysis_input)
            abuse_cnt = len(result.get("abuse", []))
            topics = result.get("topics", [])[:3]
            topics_str = ", ".join(topics) if topics else "не найдено"

            # Формируем ответ пользователю
            response = (
                f"✅ Готово!\n\n{lang_info}\n\n"
                f"📝 Оригинал: {text[:200]}\n"
                f"🌐 Перевод: {translated[:200]}\n\n"
                f"🚫 Оскорблений: {abuse_cnt}\n"
                f"📚 Темы: {topics_str}"
            )
            bot.reply_to(message, response)

    def main(self) -> None:
        """Заглушка для совместимости интерфейсов; реальный запуск бота обрабатывается внешне."""
        # Этот метод намеренно ничего не делает, так как выполнение бота обрабатывается внешне


def main() -> None:
    """Точка входа для автономного запуска (обычно не используется)."""
    # Заглушка для возможного автономного тестирования
    print("Этот модуль предназначен для использования в составе бота")


if __name__ == "__main__":
    main()
