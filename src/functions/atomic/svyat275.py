"""
Модуль для работы с функцией проверки email через API Disify.
Этот модуль содержит класс AtomicExampleBotFunction, который реализует функцию для проверки
корректности email через внешний сервис Disify. Функция принимает email, проверяет его формат,
проверяет, является ли он одноразовым и имеет ли он DNS записи. Используется библиотека Telebot
для взаимодействия с пользователями через Telegram бота.
"""
import os
import logging
from typing import List
import telebot
from telebot import types
from telebot.callback_data import CallbackData
import requests  # для отправки HTTP-запросов
from bot_func_abc import AtomicBotFunctionABC

class AtomicExampleBotFunction(AtomicBotFunctionABC):
    """Example of implementation of atomic function"""

    commands: List[str] = ["checkemail", "checkemail_unique"]  # Убедитесь, что команды уникальны
    authors: List[str] = ["svyat"]

    # Сокращена длина строки до 30 символов
    about: str = "Проверка email"  # Теперь длина 16 символов (меньше 30)

    # Длина description больше 100 символов, должно быть около 100-500
    description: str = (
    "Пример использования: /checkemail <email>. Вы можете использовать email для проверки "
    "формата, домена и одноразовости адреса."
    )


    state: bool = True

    bot: telebot.TeleBot
    example_keyboard_factory: CallbackData

    def set_handlers(self, bot: telebot.TeleBot):
        self.bot = bot
        self.example_keyboard_factory = CallbackData('t_key_button', prefix=self.commands[0])

        @bot.message_handler(commands=self.commands)
        def example_message_handler(message: types.Message):
            if message.text.startswith("/checkemail"):
                email = (message.text.split(" ", 1)[1]
                    if len(message.text.split(" ", 1)) > 1 else None)

                if email:
                    self.__check_email(message, email)
                else:
                    bot.send_message(
                        message.chat.id,
                        "Пожалуйста, укажите email для проверки"
                        "после команды '/checkemail'"
                    )

            else:
                chat_id_msg = f"\nCHAT ID = {message.chat.id}"
                msg = (
                    f"USER ID = {message.from_user.id} \n"
                    f"EXAMPLETOKEN = {self.__get_example_token()}"
                )

                bot.send_message(
                    text=msg,
                    chat_id=message.chat.id,
                    reply_markup=self.__gen_markup()
                )

        @bot.callback_query_handler(func=None, config=self.example_keyboard_factory.filter())
        def example_keyboard_callback(call: types.CallbackQuery):
            callback_data: dict = self.example_keyboard_factory.parse(callback_data=call.data)
            t_key_button = callback_data['t_key_button']

            match (t_key_button):
                case ('cb_yes'):
                    bot.answer_callback_query(call.id, "Ответ ДА!")
                case ('cb_no'):
                    bot.answer_callback_query(call.id, "Ответ НЕТ!")
                case ('force_reply'):
                    force_reply = types.ForceReply(selective=False)
                    text = "Отправьте текст для обработки в process_next_step"
                    bot.send_message(call.message.chat.id, text, reply_markup=force_reply)
                    bot.register_next_step_handler(call.message, self.__process_next_step)
                case _:
                    bot.answer_callback_query(call.id, call.data)

    def __get_example_token(self):
        token = os.environ.get("EXAMPLETOKEN")
        return token

    def __gen_markup(self):
        markup = types.InlineKeyboardMarkup()
        markup.row_width = 2
        yes_callback_data = self.example_keyboard_factory.new(t_key_button="cb_yes")
        no_callback_data = self.example_keyboard_factory.new(t_key_button="cb_no")
        force_reply_callback_data = self.example_keyboard_factory.new(t_key_button="force_reply")
        markup.add(
            types.InlineKeyboardButton("Да", callback_data=yes_callback_data),
            types.InlineKeyboardButton("Нет", callback_data=no_callback_data),
            types.InlineKeyboardButton("ForceReply", callback_data=force_reply_callback_data)
        )
        return markup

    def __process_next_step(self, message):
        try:
            chat_id = message.chat.id
            txt = message.text
            if txt != "exit":
                force_reply = types.ForceReply(selective=False)
                text = f"text = {txt}; chat.id = {chat_id}; \n Для выхода из диалога введите - exit"
                msg = self.bot.send_message(message.chat.id, text, reply_markup=force_reply)
                self.bot.register_next_step_handler(msg, self.__process_next_step)
        except ValueError as ex:
            logging.exception(ex)
            self.bot.reply_to(message, f"Exception - {ex}")

    def __check_email(self, message: types.Message, email: str):
        """Отправка запроса на сервис Disify для проверки email"""
        try:
            # Отправляем GET запрос к API Disify
            url = f"https://www.disify.com/api/email/{email}"
            response = requests.get(url, timeout=10)  # Timeout of 10 seconds


            if response.status_code == 200:
                data = response.json()
                if data.get("format"):
                    disposable = "Да" if data.get("disposable") else "Нет"
                    dns = "Да" if data.get("dns") else "Нет"
                    result = f"Информация о email {email}:\n" \
                             f"Формат правильный: {'Да' if data['format'] else 'Нет'}\n" \
                             f"Домейн: {data['domain']}\n" \
                             f"Используется одноразовый адрес: {disposable}\n" \
                             f"DNS записей для домена найдено: {dns}"
                else:
                    result = (
                        f"Ошибка при проверке email {email}. "
                        "Ответ сервиса не соответствует ожиданиям."
                    )
            else:
                result = f"Ошибка при подключении к сервису Disify. Статус: {response.status_code}"

            # Отправляем результат пользователю
            self.bot.send_message(message.chat.id, result)

        except requests.exceptions.RequestException as e:
            logging.error("Ошибка при запросе к Disify: %s", e)
            self.bot.send_message(message.chat.id, "Произошла ошибка при проверке email.")
