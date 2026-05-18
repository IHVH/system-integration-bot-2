import json
import telebot
import requests
from github import Github
from datetime import datetime

TELEGRAM_TOKEN = "TG_API_KEY"
TISANE_API_KEY = "TISANE_API_KEY"
GITHUB_TOKEN = "GITHUB_KEY"
GITHUB_REPO = "shiroyashinu/zadanie_bot"

bot = telebot.TeleBot(TELEGRAM_TOKEN)
github = Github(GITHUB_TOKEN)
repo = github.get_repo(GITHUB_REPO)

def is_russian(text):
    return any('а' <= c <= 'я' or c == 'ё' for c in text.lower())

def translate_text(text, target_lang="en"):
    """Перевод через MyMemory API"""
    if is_russian(text):
        source = "ru"
    else:
        source = "en"
    
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
        translated = translated.replace("<i>", "").replace("</i>", "").replace("&quot;", '"')
        return translated
    except Exception as e:
        print(f"Translation error: {e}")
        return text

def analyze_text(text):
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
    response = requests.post(url, json=data, headers=headers)
    return response.json()

def save_to_github(original_text, translated_text, result):
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
    repo.create_file(filename, f"Analysis {timestamp}", json.dumps(report, indent=2, ensure_ascii=False))
    return f"https://github.com/{GITHUB_REPO}/blob/main/{filename}"

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "🌍 Я переводчик и анализатор текста\n\n📌 Отправь текст на русском или английском\n📊 Анализирую: оскорбления (abuse), темы (topics)")

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    text = message.text
    if text.startswith('/'):
        return

    bot.reply_to(message, "🔍 Анализ текста...")

    try:
        if is_russian(text):
            translated = translate_text(text, "en")
            lang_info = "🇷🇺 Русский → 🇬🇧 Английский"
            text_for_analysis = translated
        else:
            translated = translate_text(text, "ru")
            lang_info = "🇬🇧 Английский → 🇷🇺 Русский"
            text_for_analysis = text

        result = analyze_text(text_for_analysis)
        url = save_to_github(text, translated, result)

        abuse_count = len(result.get("abuse", []))
        topics = result.get("topics", [])
        topics_text = ", ".join(topics[:3]) if topics else "не найдено"

        response = f"""✅ Готово!

{lang_info}

📝 Оригинал: {text[:100]}
🌐 Перевод: {translated[:100]}

🚫 Оскорблений: {abuse_count}
📚 Темы: {topics_text}

📁 Отчёт: {url}"""

        bot.reply_to(message, response)

    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

print("🤖 Бот запущен...")
bot.infinity_polling()