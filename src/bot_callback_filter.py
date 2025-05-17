"""Custom callback data filter"""

from telebot import types
from telebot.callback_data import CallbackDataFilter
from telebot.custom_filters import AdvancedCustomFilter

class BotCallbackCustomFilter(AdvancedCustomFilter): # pylint: disable=too-few-public-methods
    """Callback query custom filter"""
    key = 'config'
    def check(self, message: types.CallbackQuery, text: CallbackDataFilter):
        return text.check(query=message)
