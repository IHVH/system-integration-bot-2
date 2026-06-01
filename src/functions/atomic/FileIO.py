import io
from typing import List
import requests
import telebot
from telebot import types

# Импортируем абстрактный класс. 
# ПРИМЕЧАНИЕ: Измените путь импорта, если в вашем проекте ABC-класс лежит в другом месте.
from src.functions.atomic.abc import AtomicBotFunctionABC


class FileIoFunction(AtomicBotFunctionABC):
    # ==========================================
    # ОБЯЗАТЕЛЬНЫЕ АТРИБУТЫ ФРЕЙМВОРКА
    # ==========================================
    commands: List[str] = ["fileio", "file"]
    authors: List[str] = ["твой_логин_на_github"]
    about: str = "Загрузка и скачивание файлов через сервис file.io."
    description: str = (
        "Позволяет загрузить любой документ в облако file.io с ограничением по времени жизни, "
        "либо скачать файл обратно в Telegram, передав боту прямую ссылку.\n"
        "Параметры: функция работает в интерактивном режиме после вызова команды."
    )
    state: bool = True

    def __init__(self):
        # Временное хранилище для состояний пользователей внутри этого класса
        self.user_data = {}

    # ==========================================
    # ОСНОВНОЙ МЕТОД ВХОДА (РЕАЛИЗАЦИЯ ABC)
    # ==========================================
    def handle(self, message: types.Message, bot: telebot.TeleBot):
        """
        Этот метод автоматически вызывается фреймворком, когда пользователь пишет /fileio.
        Обратите внимание: если в вашем AtomicBotFunctionABC метод называется иначе 
        (например, execute или run), просто переименуйте его сюда.
        """
        chat_id = message.chat.id
        
        text = (
            "⏳ **Добро пожаловать в модуль file.io!**\n\n"
            "• Чтобы **загрузить** файл, отправьте его мне (документом) в следующем сообщении.\n"
            "• Чтобы **скачать** файл, отправьте мне ссылку вида `https://file.io/...`"
        )
        msg = bot.send_message(chat_id, text, parse_mode="Markdown")
        
        # Регистрируем следующий шаг: ожидаем от пользователя либо файл, либо ссылку
        bot.register_next_step_handler(msg, self._process_user_input, bot)

    # ==========================================
    # ВНУТРЕННЯЯ ЛОГИКА ШАГОВ И ОБРАБОТКИ
    # ==========================================
    def _process_user_input(self, message: types.Message, bot: telebot.TeleBot):
        chat_id = message.chat.id

        # Вариант 1: Пользователь отправил документ (Загрузка)
        if message.content_type == 'document':
            file_id = message.document.file_id
            file_name = message.document.file_name

            bot.send_message(chat_id, "Скачиваю файл из Telegram...")
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)

            self.user_data[chat_id] = {
                'file_bytes': downloaded_file,
                'file_name': file_name
            }

            markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            markup.add('1 час (1h)', '1 день (1d)', '1 неделя (1w)', '1 месяц (1m)')

            msg = bot.send_message(
                chat_id, 
                "Выбери, сколько времени файл будет доступен на file.io:", 
                reply_markup=markup
            )
            bot.register_next_step_handler(msg, self._process_expiration_step, bot)

        # Вариант 2: Пользователь отправил ссылку (Скачивание)
        elif message.text and message.text.strip().startswith("https://file.io/"):
            file_url = message.text.strip()
            bot.send_message(chat_id, "🔄 Запрашиваю файл у file.io...")
            
            file_bytes, file_name = self._download_from_fileio(file_url)

            if file_bytes and file_name:
                bot.send_message(chat_id, f"📥 Файл «{file_name}» получен. Отправляю...")
                file_object = io.BytesIO(file_bytes)
                bot.send_document(chat_id, document=file_object, visible_file_name=file_name)
            else:
                bot.send_message(chat_id, "❌ Ошибка скачивания. Возможно, ссылка устарела или файл уже удален.")
        
        # Вариант 3: Непонятный ввод
        else:
            bot.send_message(chat_id, "❌ Отмена операции. Ожидался документ или ссылка на file.io.")

    def _process_expiration_step(self, message: types.Message, bot: telebot.TeleBot):
        chat_id = message.chat.id
        user_choice = message.text

        if chat_id not in self.user_data:
            bot.send_message(chat_id, "Что-то пошло не так. Попробуйте вызвать команду заново.")
            return

        expiry_mapping = {
            '1 час (1h)': '1h',
            '1 день (1d)': '1d',
            '1 неделя (1w)': '1w',
            '1 месяц (1m)': '1m'
        }
        expires = expiry_mapping.get(user_choice, '1d')

        bot.send_message(chat_id, "⏳ Загружаю на file.io...")
        
        file_bytes = self.user_data[chat_id]['file_bytes']
        file_name = self.user_data[chat_id]['file_name']

        download_link = self._upload_to_fileio(file_bytes, file_name, expires)

        if download_link:
            bot.send_message(
                chat_id,
                f"✅ **Успешно!**\n\n🔗 Ссылка:\n{download_link}\n\n"
                f"⏱ Срок действия: {expires}. _Файл удалится после первого скачивания!_",
                parse_mode="Markdown",
                reply_markup=types.ReplyKeyboardRemove()
            )
        else:
            bot.send_message(chat_id, "❌ Не удалось загрузить файл на file.io.")

        self.user_data.pop(chat_id, None)

    # ==========================================
    # СЕРВИСНЫЕ МЕТОДЫ ДЛЯ РАБОТЫ С API FILE.IO
    # ==========================================
    def _upload_to_fileio(self, file_bytes: bytes, file_name: str, expires: str) -> getattr:
        url = "https://file.io"
        files = {"file": (file_name, file_bytes)}
        data = {"expires": expires}
        try:
            response = requests.post(url, files=files, data=data)
            if response.status_code == 200:
                res_json = response.json()
                if res_json.get("success"):
                    return res_json.get("link")
            return None
        except Exception as e:
            print(f"Ошибка file.io upload: {e}")
            return None

    def _download_from_fileio(self, file_url: str):
        try:
            response = requests.get(file_url, stream=True)
            if response.status_code == 200:
                content_disp = response.headers.get('content-disposition')
                if content_disp and "filename=" in content_disp:
                    file_name = content_disp.split("filename=")[1].strip('"')
                else:
                    file_name = file_url.split("/")[-1] or "downloaded_file"
                return response.content, file_name
            return None, None
        except Exception as e:
            print(f"Ошибка file.io download: {e}")
            return None, None