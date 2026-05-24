"""
Модуль для Telegram бота, который переводит текст и анализирует его на наличие оскорблений и тем.
Использует MyMemory API для перевода и Tisane API для анализа.
"""

import json
from datetime import datetime

import telebot
import requests
from github import Github, Auth

# Конфигурация (в production использовать переменные окружения)
TELEGRAM_TOKEN = "TG_BOT_KEY"
TISANE_API_KEY = "TISANE_KEY"
GITHUB_TOKEN = "GIT_TOKEN"
GITHUB_REPO = "shiroyashinu/zadanie_bot"

# Инициализация клиентов
bot = telebot.TeleBot(TELEGRAM_TOKEN)
# Используем новый способ авторизации через Auth.Token
auth = Auth.Token(GITHUB_TOKEN)
github = Github(auth=auth)
repo = github.get_repo(GITHUB_REPO)


def is_russian(text: str) -> bool:
    """Проверяет, содержит ли текст русские символы."""
    return any('а' <= character <= 'я' or character == 'ё' for character in text.lower())


def translate_text(text: str, target_lang: str = "en") -> str:
    """
    Переводит текст через MyMemory API.

    Args:
        text: Текст для перевода
        target_lang: Целевой язык (по умолчанию "en")

    Returns:
        Переведенный текст или оригинал в случае ошибки
    """
    source = "ru" if is_russian(text) else "en"

    url = "https://api.mymemory.translated.net/get"
    params = {
        "q": text,
        "langpair": f"{source}|{target_lang}"
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        result = response.json()
        translated = result.get("responseData", {}).get("translatedText", text)
        # Очистка от HTML-тегов
        translated = translated.replace("<i>", "").replace("</i>", "")
        translated = translated.replace("&quot;", '"')
        return translated
    except requests.exceptions.RequestException as error:
        print(f"Translation error: {error}")
        return text


def analyze_text(text: str) -> dict:
    """
    Анализирует текст через Tisane API для определения оскорблений, тем и тональности.

    Args:
        text: Текст для анализа (на английском языке)

    Returns:
        Словарь с результатами анализа
    """
    url = "https://api.tisane.ai/parse"
    headers = {
        "Ocp-Apim-Subscription-Key": TISANE_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "content": text,
        "language": "en",
        "settings": {
            "abuse": True,
            "sentiment": True,
            "topics": True
        }
    }

    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as error:
        print(f"Analysis error: {error}")
        return {"abuse": [], "sentiment_expressions": [], "topics": []}


def save_to_github(original_text: str, translated_text: str, result: dict) -> str:
    """
    Сохраняет результаты анализа в GitHub репозиторий.

    Args:
        original_text: Оригинальный текст
        translated_text: Переведенный текст
        result: Результаты анализа от Tisane API

    Returns:
        URL сохраненного файла
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"analysis_{timestamp}.json"

    report = {
        "timestamp": timestamp,
        "original_text": original_text,
        "translated_text": translated_text,
        "abuse": result.get("abuse", []),
        "sentiment_expressions": result.get("sentiment_expressions", []),
        "topics": result.get("topics", [])
    }

    repo.create_file(
        filename,
        f"Analysis {timestamp}",
        json.dumps(report, indent=2, ensure_ascii=False)
    )
    return f"https://github.com/{GITHUB_REPO}/blob/main/{filename}"


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message: telebot.types.Message) -> None:
    """Отправляет приветственное сообщение с инструкцией."""
    welcome_text = (
        "🌍 Я переводчик и анализатор текста\n\n"
        "📌 Отправь текст на русском или английском\n"
        "📊 Анализирую: оскорбления (abuse), темы (topics)"
    )
    bot.reply_to(message, welcome_text)


@bot.message_handler(func=lambda message: True)
def handle_message(message: telebot.types.Message) -> None:
    """
    Обрабатывает входящие текстовые сообщения.
    Выполняет перевод, анализ и сохраняет результат в GitHub.
    """
    text = message.text

    # Игнорируем команды
    if text.startswith('/'):
        return

    bot.reply_to(message, "🔍 Анализ текста...")

    try:
        # Определяем направление перевода
        if is_russian(text):
            translated = translate_text(text, "en")
            lang_info = "🇷🇺 Русский → 🇬🇧 Английский"
            text_for_analysis = translated
        else:
            translated = translate_text(text, "ru")
            lang_info = "🇬🇧 Английский → 🇷🇺 Русский"
            text_for_analysis = text

        # Анализируем текст
        result = analyze_text(text_for_analysis)

        # Сохраняем в GitHub
        file_url = save_to_github(text, translated, result)

        # Формируем ответ
        abuse_count = len(result.get("abuse", []))
        topics = result.get("topics", [])
        topics_text = ", ".join(topics[:3]) if topics else "не найдено"

        response_text = (
            f"✅ Готово!\n\n"
            f"{lang_info}\n\n"
            f"📝 Оригинал: {text[:100]}\n"
            f"🌐 Перевод: {translated[:100]}\n\n"
            f"🚫 Оскорблений: {abuse_count}\n"
            f"📚 Темы: {topics_text}\n\n"
            f"📁 Отчёт: {file_url}"
        )

        bot.reply_to(message, response_text)

    except requests.exceptions.RequestException as error:
        error_msg = f"❌ Ошибка сети: {error}"
        bot.reply_to(message, error_msg)
    except Exception as error:  # pylint: disable=broad-exception-caught
        # Ловим общие исключения для предотвращения падения бота
        error_msg = f"❌ Непредвиденная ошибка: {error}"
        bot.reply_to(message, error_msg)


def main() -> None:
    """Запускает Telegram бота."""
    print("🤖 Бот запущен...")
    bot.infinity_polling()


if __name__ == "__main__":
    main()
    