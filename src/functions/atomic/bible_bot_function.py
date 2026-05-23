"""Module for Bible API integration."""
import logging
from typing import Dict, List

import requests
import telebot
from telebot import types
from telebot.callback_data import CallbackData

from bot_func_abc import AtomicBotFunctionABC


class BibleBotFunction(AtomicBotFunctionABC):
    """Atomic function for Bible API integration with step-by-step navigation."""

    commands: List[str] = ["bible", "bib"]
    authors: List[str] = ["ymhhhhh"]
    about: str = "Поиск библейских стихов через Bible API"
    description: str = """
    Функция для поиска библейских стихов.
    Поддерживает навигацию по переводам, книгам, главам и стихам.
    Примеры вызова:
    /bible - начать поиск
    /bib - тоже самое
    """
    state: bool = True
    bot: telebot.TeleBot
    user_data: Dict[int, Dict] = {}

    def __init__(self):
        """Initialize the Bible bot function."""
        super().__init__()
        self.keyboard_factory = None

    def set_handlers(self, bot: telebot.TeleBot):
        """Register message and callback query handlers for the Bible function."""
        self.bot = bot
        self.keyboard_factory = CallbackData('action', 'value', prefix='bible')

        @bot.message_handler(commands=self.commands)
        def bible_command_handler(message: types.Message):
            self._start_bible_session(message.chat.id)

        self.bot.register_callback_query_handler(
            self._bible_callback_handler,
            func=lambda call: call.data.startswith('bible:')
        )

    def _send_translation_list(self, chat_id: int):
        """Send a list of available Bible translations as inline buttons."""
        try:
            response = requests.get('https://bible-api.com/data', timeout=10)
            translations = response.json()['translations']

            self.user_data[chat_id] = {
                'step': 'translation_selection',
                'translations': translations,
                'selected_translation': None,
                'selected_book': None,
                'selected_chapter': None,
                'selected_verse': None
            }

            markup = types.InlineKeyboardMarkup(row_width=2)
            buttons = []
            for trans in translations[:20]:
                cb_data = self.keyboard_factory.new(
                    action='select_translation',
                    value=trans['identifier']
                )
                buttons.append(
                    types.InlineKeyboardButton(trans['name'], callback_data=cb_data)
                )
            markup.add(*buttons)

            self.bot.send_message(
                chat_id,
                "📖 Выберите перевод Библии:",
                reply_markup=markup
            )
        except (requests.exceptions.RequestException, KeyError, ValueError) as e:
            logging.exception(e)
            self.bot.send_message(
                chat_id,
                "❌ Ошибка при получении списка переводов. Попробуйте позже."
            )

    def _send_books_list(self, chat_id: int, translation_id: str):
        """Send a list of Bible books for the selected translation."""
        try:
            response = requests.get(
                f'https://bible-api.com/data/{translation_id}', timeout=10
            )
            books = response.json()['books']

            self.user_data[chat_id]['selected_translation'] = translation_id

            markup = types.InlineKeyboardMarkup(row_width=2)
            buttons = []
            for book in books[:30]:
                cb_data = self.keyboard_factory.new(
                    action='select_book',
                    value=book['id']
                )
                buttons.append(
                    types.InlineKeyboardButton(book['name'], callback_data=cb_data)
                )
            markup.add(*buttons)

            back_cb = self.keyboard_factory.new(action='back_to_translations', value='')
            markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data=back_cb))

            self.bot.send_message(
                chat_id,
                "📚 Выберите книгу Библии:",
                reply_markup=markup
            )
        except (requests.exceptions.RequestException, KeyError, ValueError) as e:
            logging.exception(e)
            self.bot.send_message(chat_id, "❌ Ошибка при получении списка книг.")

    def _send_chapters_list(self, chat_id: int, book_id: str):
        """Send a list of chapters for the selected book."""
        try:
            translation_id = self.user_data[chat_id]['selected_translation']
            response = requests.get(
                f'https://bible-api.com/data/{translation_id}/{book_id}', timeout=10
            )
            chapters = response.json()['chapters']
            total_chapters = len(chapters)

            self.user_data[chat_id]['selected_book'] = book_id

            markup = types.InlineKeyboardMarkup(row_width=5)
            buttons = []
            for ch in range(1, total_chapters + 1):
                cb_data = self.keyboard_factory.new(
                    action='select_chapter',
                    value=str(ch)
                )
                buttons.append(types.InlineKeyboardButton(str(ch), callback_data=cb_data))
            for i in range(0, len(buttons), 5):
                markup.add(*buttons[i:i+5])

            back_cb = self.keyboard_factory.new(action='back_to_books', value='')
            markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data=back_cb))

            self.bot.send_message(
                chat_id,
                f"📖 Книга: {book_id}\nВыберите главу:",
                reply_markup=markup
            )
        except (requests.exceptions.RequestException, KeyError, ValueError) as e:
            logging.exception(e)
            self.bot.send_message(chat_id, "❌ Ошибка при получении списка глав.")

    def _send_verses_list(self, chat_id: int, chapter: int):
        """Send a list of verses for the selected chapter."""
        try:
            tid = self.user_data[chat_id]['selected_translation']
            bid = self.user_data[chat_id]['selected_book']
            resp = requests.get(
                f'https://bible-api.com/data/{tid}/{bid}/{chapter}', timeout=10
            )
            verses = resp.json()['verses']
            self.user_data[chat_id]['selected_chapter'] = chapter

            markup = types.InlineKeyboardMarkup(row_width=5)
            btns = []
            for v in verses[:100]:
                vn = v.get('verse')
                if vn:
                    cd = self.keyboard_factory.new('select_verse', str(vn))
                    btns.append(types.InlineKeyboardButton(str(vn), callback_data=cd))
            for i in range(0, len(btns), 5):
                markup.add(*btns[i:i+5])

            back_cb = self.keyboard_factory.new('back_to_chapters', '')
            markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data=back_cb))

            self.bot.send_message(
                chat_id, f"📖 Глава {chapter}\nВыберите стих:", reply_markup=markup
            )
        except (requests.exceptions.RequestException, KeyError, ValueError) as e:
            logging.exception(e)
            self.bot.send_message(chat_id, "❌ Ошибка при получении списка стихов.")

    def _send_verse_text(self, chat_id: int, verse_number: int):
        """Send the text of the selected verse."""
        try:
            tid = self.user_data[chat_id]['selected_translation']
            bid = self.user_data[chat_id]['selected_book']
            ch = self.user_data[chat_id]['selected_chapter']
            resp = requests.get(
                f'https://bible-api.com/data/{tid}/{bid}/{ch}', timeout=10
            )
            verses = resp.json()['verses']

            verse_text = None
            for v in verses:
                if v.get('verse') == verse_number:
                    verse_text = v.get('text')
                    break

            if not verse_text:
                self.bot.send_message(chat_id, "❌ Стих не найден.")
                return

            self.user_data[chat_id]['selected_verse'] = verse_number

            response_text = (
                f"📖 *{bid} {ch}:{verse_number}*\n"
                f"_{tid}_\n\n"
                f"{verse_text}"
            )
            self.bot.send_message(chat_id, response_text, parse_mode='Markdown')

            new_cb = self.keyboard_factory.new('new_search', '')
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(
                "🔄 Начать новый поиск", callback_data=new_cb
            ))
            self.bot.send_message(chat_id, "Что дальше?", reply_markup=markup)
        except (requests.exceptions.RequestException, KeyError, ValueError) as e:
            logging.exception(e)
            self.bot.send_message(chat_id, "❌ Ошибка при получении текста стиха.")

    def _bible_callback_handler(self, call: types.CallbackQuery):
        """Route callback queries to the corresponding methods."""
        data = self.keyboard_factory.parse(callback_data=call.data)
        action = data['action']
        value = data['value']
        chat_id = call.message.chat.id

        try:
            if action == 'select_translation':
                self._send_books_list(chat_id, value)
            elif action == 'select_book':
                self._send_chapters_list(chat_id, value)
            elif action == 'select_chapter':
                self._send_verses_list(chat_id, int(value))
            elif action == 'select_verse':
                self._send_verse_text(chat_id, int(value))
            elif action == 'back_to_translations':
                self._send_translation_list(chat_id)
            elif action == 'back_to_books':
                self._send_books_list(
                    chat_id, self.user_data[chat_id]['selected_translation']
                )
            elif action == 'back_to_chapters':
                self._send_chapters_list(
                    chat_id, self.user_data[chat_id]['selected_book']
                )
            elif action == 'new_search':
                self._send_translation_list(chat_id)

            self.bot.delete_message(chat_id, call.message.message_id)
        except (KeyError, ValueError) as e:
            logging.exception(e)
            self.bot.answer_callback_query(
                call.id, "⚠️ Произошла ошибка. Попробуйте снова."
            )

    def _start_bible_session(self, chat_id: int):
        """Start a new Bible selection session."""
        self._send_translation_list(chat_id)
