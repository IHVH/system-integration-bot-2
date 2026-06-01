import io
import logging
from typing import List
import requests
import telebot
from telebot import types
from bot_func_abc import AtomicBotFunctionABC

class FileIoBotFunction(AtomicBotFunctionABC):
    
    commands: List[str] = ["fileio", "file"]
    authors: List[str] = ["MuertoTheDeath"]
    about: str = "Загрузка файлов на file.io и их скачивание обратно в чат."
    description: str = """Модуль для работы с временным файлообменником file.io.
    
Вызовите команду `/fileio` или `/file`, после чего бот перейдет в интерактивный режим:
1. Если вы отправите **документ**, бот предложит выбрать время его жизни и вернет ссылку.
2. Если вы отправите **ссылку** вида `https://file.io/...`, бот скачает этот файл и пришлет его вам."""
    state: bool = True
    bot: telebot.TeleBot
    def __init__(self):
        self.user_data = {}

    # РЕГИСТРАЦИЯ ХЭНДЛЕРОВ (ГЛАВНЫЙ МЕТОД)
    def set_handlers(self, bot: telebot.TeleBot):
        """Регистрация обработчиков сообщений для данной функции"""
        self.bot = bot

        @bot.message_handler(commands=self.commands)
        def fileio_start_handler(message: types.Message):
            text = (
                "👋 **Добро пожаловать в модуль file.io!**\n\n"
                "• Чтобы **загрузить** файл, отправьте его (документом) в следующем сообщении.\n"
                "• Чтобы **скачать** файл, отправьте ссылку вида `https://file.io/...`"
            )
            msg = self.bot.send_message(message.chat.id, text, parse_mode="Markdown")
            
            self.bot.register_next_step_handler(msg, self.__process_user_input)


    # ВНУТРЕННЯЯ ЛОГИКА И ШАГИ (ПРИВАТНЫЕ МЕТОДЫ)
    def __process_user_input(self, message: types.Message):
        chat_id = message.chat.id

        try:
            # Сценарий 1: Пользователь отправил файл (Загрузка)
            if message.content_type == 'document':
                file_id = message.document.file_id
                file_name = message.document.file_name

                self.bot.send_message(chat_id, "📥 Скачиваю файл из Telegram...")
                file_info = self.bot.get_file(file_id)
                downloaded_file = self.bot.download_file(file_info.file_path)

                self.user_data[chat_id] = {
                    'file_bytes': downloaded_file,
                    'file_name': file_name
                }

                markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
                markup.add('1 час (1h)', '1 день (1d)', '1 неделя (1w)', '1 месяц (1m)')

                msg = self.bot.send_message(
                    chat_id, 
                    "Выбери, сколько времени файл будет доступен на file.io:", 
                    reply_markup=markup
                )
                self.bot.register_next_step_handler(msg, self.__process_expiration_step)

            # Сценарий 2: Пользователь отправил ссылку (Скачивание)
            elif message.text and message.text.strip().startswith("https://file.io/"):
                file_url = message.text.strip()
                self.bot.send_message(chat_id, "🔄 Запрашиваю файл у file.io...")
                
                file_bytes, file_name = self.__download_from_fileio(file_url)

                if file_bytes and file_name:
                    self.bot.send_message(chat_id, f"✅ Файл «{file_name}» получен. Отправляю в чат...")
                    file_object = io.BytesIO(file_bytes)
                    self.bot.send_document(chat_id, document=file_object, visible_file_name=file_name)
                else:
                    self.bot.send_message(
                        chat_id, 
                        "❌ Ошибка скачивания. Возможно, ссылка неверна, "
                        "истек срок действия или файл уже был скачан ранее."
                    )
            
            # Сценарий 3: Пользователь отправил что-то не то
            else:
                self.bot.send_message(
                    chat_id, 
                    "❌ Отмена операции. Ожидался документ или ссылка на file.io.\n"
                    "Для повторного запуска пропишите команду заново."
                )

        except Exception as ex:
            logging.exception(ex)
            self.bot.send_message(chat_id, f"Произошла ошибка при обработке: {ex}")


    def __process_expiration_step(self, message: types.Message):
        chat_id = message.chat.id
        user_choice = message.text

        if chat_id not in self.user_data:
            self.bot.send_message(chat_id, "Ошибка: сессия утеряна. Вызовите команду заново.")
            return

        expiry_mapping = {
            '1 час (1h)': '1h',
            '1 день (1d)': '1d',
            '1 неделя (1w)': '1w',
            '1 месяц (1m)': '1m'
        }
        expires = expiry_mapping.get(user_choice, '1d')

        self.bot.send_message(chat_id, "⏳ Загружаю файл на сервер file.io...")
        
        file_bytes = self.user_data[chat_id]['file_bytes']
        file_name = self.user_data[chat_id]['file_name']

        download_link = self.__upload_to_fileio(file_bytes, file_name, expires)

        if download_link:
            self.bot.send_message(
                chat_id,
                f"✅ **Файл успешно загружен!**\n\n🔗 Ссылка для скачивания:\n{download_link}\n\n"
                f"⏱ Время действия: {expires}. _Помни, что после первого скачивания файл удалится автоматически!_",
                parse_mode="Markdown",
                reply_markup=types.ReplyKeyboardRemove()
            )
        else:
            self.bot.send_message(chat_id, "❌ Не удалось загрузить файл на file.io. Попробуйте позже.")

        self.user_data.pop(chat_id, None)


    # СЕТЕВЫЕ МЕТОДЫ ДЛЯ РАБОТЫ С API FILE.IO
    def __upload_to_fileio(self, file_bytes: bytes, file_name: str, expires: str) -> str:
        url = "https://file.io"
        files = {"file": (file_name, file_bytes)}
        data = {"expires": expires}
        try:
            response = requests.post(url, files=files, data=data, timeout=30)
            if response.status_code == 200:
                res_json = response.json()
                if res_json.get("success"):
                    return res_json.get("link")
            return None
        except Exception as e:
            logging.error(f"Ошибка file.io upload: {e}")
            return None

    def __download_from_fileio(self, file_url: str):
        try:
            response = requests.get(file_url, stream=True, timeout=30)
            if response.status_code == 200:
                content_disp = response.headers.get('content-disposition')
                if content_disp and "filename=" in content_disp:
                    file_name = content_disp.split("filename=")[1].strip('"')
                else:
                    file_name = file_url.split("/")[-1] or "downloaded_file"
                return response.content, file_name
            return None, None
        except Exception as e:
            logging.error(f"Ошибка file.io download: {e}")
            return None, None
