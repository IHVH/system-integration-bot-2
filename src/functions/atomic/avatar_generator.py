import requests
from bot_func_abc import AtomicBotFunctionABC
from telebot import types

class AvatarGenerator(AtomicBotFunctionABC):
    commands = ["/avatar"]
    authors = ["Fantom-Nightcore"]
    about = "Генератор аватаров через DiceBear API"
    description = """
    Генерирует уникальный аватар по сид-строке.
    Доступные стили: adventurer, avataaars, micah и др.
    """
    state = True

    STYLES = [
        "adventurer", "adventurer-neutral", "avataaars",
        "big-ears", "big-smile", "croodles", "micah"
    ]

    def __init__(self):
        super().__init__()
        #Добавляем обработчик запросов
        self.bot.callback_query_handler(
            func=lambda call: call.data.startswith('avatar_')
        )(self.callback_handler)

    def handle(self, message: types.Message):
        """Основной обработчик команды /avatar"""
        try:
            self.bot.send_message(
                message.chat.id,
                "Введите сид для аватара (любой набор символов):",
                reply_markup=types.ForceReply(selective=False)
            )
            self.bot.register_next_step_handler(
                message, 
                self.process_seed_input
            )
        except Exception as e:
            self.bot.reply_to(
                message, 
                f"Ошибка: {str(e)}"
            )

    def process_seed_input(self, message: types.Message):
        """Обработка введенного сида"""
        try:
            seed = message.text.strip()
            if not seed:
                raise ValueError("Сид не может быть пустым")
                
            markup = types.InlineKeyboardMarkup(row_width=2)
            #Группируем кнопки по 2 в строке
            buttons = [
                types.InlineKeyboardButton(
                    text=style,
                    callback_data=f"avatar_{style}_{seed}"
                ) 
                for style in self.STYLES
            ]
            markup.add(*buttons)
            
            self.bot.send_message(
                message.chat.id,
                "Выберите стиль аватара:",
                reply_markup=markup
            )
        except Exception as e:
            self.bot.reply_to(
                message,
                f"Ошибка: {str(e)}\nПопробуйте снова: /avatar"
            )

    def callback_handler(self, call: types.CallbackQuery):
        """Обработка выбора стиля"""
        try:
            data_parts = call.data.split('_')
            if len(data_parts) < 3:
                raise ValueError("Некорректные данные callback")
                
            style = data_parts[1]
            seed = '_'.join(data_parts[2:])  #На случай, если сид содержит "_"
            
            url = f"https://api.dicebear.com/9.x/{style}/svg?seed={seed}&size=400&backgroundColor=transparent"
            
            with requests.get(url, stream=True) as resp:
                if resp.status_code == 200:
                    self.bot.send_document(
                        call.message.chat.id,
                        ('avatar.svg', resp.raw),
                        caption=f"Стиль: {style}\nSeed: {seed}"
                    )
                else:
                    self.bot.answer_callback_query(
                        call.id,
                        "Ошибка генерации. Попробуйте другой сид.",
                        show_alert=True
                    )
        except Exception as e:
            self.bot.answer_callback_query(
                call.id,
                f"Ошибка: {str(e)}",
                show_alert=True
            )