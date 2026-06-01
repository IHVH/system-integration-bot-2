from typing import List, Dict, Optional
import logging
import requests
import telebot
from telebot import types

try:
    from bot_func_abc import AtomicBotFunctionABC
except ImportError:
    class AtomicBotFunctionABC:  # pylint: disable=R0903
        commands: List[str] = []
        authors: List[str] = []
        about: str = ""
        description: str = ""
        state: bool = True

        def set_handlers(self, bot):
            _ = bot 


logger = logging.getLogger(__name__)


class CocktailSearchBotFunction(AtomicBotFunctionABC):

    commands: List[str] = ["cocktail"]
    authors: List[str] = ["ILENTI"]
    about: str = "Поиск коктейлей"
    description: str = "Поиск коктейлей. Используй /cocktail название"
    state: bool = True

    bot: telebot.TeleBot
    base_url: str = "https://www.thecocktaildb.com/api/json/v1/1/search.php"

    def set_handlers(self, bot: telebot.TeleBot):
        self.bot = bot
        self._setup_callback_handler()

        @bot.message_handler(commands=self.commands)
        def search_cocktail(message: types.Message):
            parts = message.text.split()
            if len(parts) < 2:
                bot.send_message(
                    message.chat.id,
                    "❌ Напиши название коктейля.\nПример: /cocktail margarita"
                )
                return

            cocktail_name = ' '.join(parts[1:])
            bot.send_message(message.chat.id, f"🔍 Ищу {cocktail_name}...")
            cocktails = self.search_cocktails(cocktail_name)

            if not cocktails:
                bot.send_message(
                    message.chat.id,
                    f"❌ Коктейль '{cocktail_name}' не найден."
                )
                return

            self.show_cocktails_list(message.chat.id, cocktails)

    def _setup_callback_handler(self):
        @self.bot.callback_query_handler(func=lambda call: True)
        def handle_buttons(call):
            try:
                if call.data == "new_search":
                    self.bot.answer_callback_query(call.id)

                    try:
                        self.bot.delete_message(
                            call.message.chat.id,
                            call.message.message_id
                        )
                    except telebot.apihelper.ApiTelegramException as e:
                        logger.error("Ошибка удаления сообщения: %s", str(e))

                    self.bot.send_message(
                        call.message.chat.id,
                        "🔍 Напиши название коктейля командой /cocktail"
                    )
                    return

                if call.data.startswith("cocktail_"):
                    drink_id = call.data.replace("cocktail_", "")
                    cocktail = self.get_cocktail_by_id(drink_id)

                    if cocktail:
                        self.bot.answer_callback_query(call.id)

                        try:
                            self.bot.delete_message(
                                call.message.chat.id,
                                call.message.message_id
                            )
                        except telebot.apihelper.ApiTelegramException as e:
                            logger.error("Ошибка удаления сообщения: %s", str(e))

                        self.show_cocktail_details(
                            call.message.chat.id,
                            cocktail
                        )
                    else:
                        self.bot.answer_callback_query(
                            call.id,
                            "❌ Коктейль не найден!",
                            show_alert=True
                        )

            except telebot.apihelper.ApiTelegramException as e:
                logger.error("Ошибка Telegram API в callback handler: %s", str(e))
                try:
                    self.bot.answer_callback_query(
                        call.id,
                        "❌ Ошибка Telegram API!",
                        show_alert=True
                    )
                except telebot.apihelper.ApiTelegramException:
                    pass
            except requests.exceptions.RequestException as e:
                logger.error("Ошибка сети в callback handler: %s", str(e))
                try:
                    self.bot.answer_callback_query(
                        call.id,
                        "❌ Ошибка сети!",
                        show_alert=True
                    )
                except telebot.apihelper.ApiTelegramException:
                    pass
            except (KeyError, AttributeError, ValueError) as e:
                logger.error("Ошибка данных в callback handler: %s", str(e))
                try:
                    self.bot.answer_callback_query(
                        call.id,
                        "❌ Ошибка обработки данных!",
                        show_alert=True
                    )
                except telebot.apihelper.ApiTelegramException:
                    pass

    def search_cocktails(self, name: str) -> List[Dict]:
        try:
            response = requests.get(
                self.base_url,
                params={"s": name},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            drinks = data.get("drinks", [])
            return drinks if drinks else []
        except requests.exceptions.RequestException as e:
            logger.error("Ошибка запроса: %s", str(e))
            return []

    def show_cocktails_list(self, chat_id: int, cocktails: List[Dict]):
        markup = types.InlineKeyboardMarkup(row_width=1)

        for cocktail in cocktails:
            name = cocktail.get("strDrink", "Коктейль")
            btn = types.InlineKeyboardButton(
                f"🍸 {name}",
                callback_data=f"cocktail_{cocktail.get('idDrink', '')}"
            )
            markup.add(btn)

        markup.add(types.InlineKeyboardButton(
            "🔄 Новый поиск",
            callback_data="new_search"
        ))

        self.bot.send_message(
            chat_id,
            "🍸 *Найденные коктейли:*\nВыбери один из них:",
            parse_mode='Markdown',
            reply_markup=markup
        )

    def get_cocktail_by_id(self, drink_id: str) -> Optional[Dict]:
        try:
            url = "https://www.thecocktaildb.com/api/json/v1/1/lookup.php"
            response = requests.get(url, params={"i": drink_id}, timeout=10)
            response.raise_for_status()
            data = response.json()
            drinks = data.get("drinks", [])
            return drinks[0] if drinks else None
        except requests.exceptions.RequestException as e:
            logger.error("Ошибка запроса: %s", str(e))
            return None

    def _format_ingredients(self, cocktail: Dict) -> str:
        ingredients = []
        for i in range(1, 16):
            ingredient = cocktail.get(f"strIngredient{i}")
            measure = cocktail.get(f"strMeasure{i}")
            if ingredient:
                measure_text = f" - {measure}" if measure else ""
                ingredients.append(f"• {ingredient}{measure_text}")
        return "\n".join(ingredients) if ingredients else "Не указаны"

    def show_cocktail_details(self, chat_id: int, cocktail: Dict):
        name = cocktail.get("strDrink", "Неизвестно")
        category = cocktail.get("strCategory", "Не указана")
        glass = cocktail.get("strGlass", "Не указан")
        instructions = cocktail.get("strInstructions", "Нет инструкции")
        image_url = cocktail.get("strDrinkThumb", "")

        ingredients_text = self._format_ingredients(cocktail)

        message = (
            f"🍸 *{name}*\n\n"
            f"📋 *Категория:* {category}\n"
            f"🥃 *Бокал:* {glass}\n\n"
            f"📝 *Ингредиенты:*\n{ingredients_text}\n\n"
            f"📖 *Рецепт:*\n{instructions[:300]}"
        )

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            "🔍 Новый поиск",
            callback_data="new_search"
        ))

        if image_url:
            try:
                self.bot.send_photo(
                    chat_id, image_url, caption=message,
                    parse_mode='Markdown', reply_markup=markup
                )
            except (requests.exceptions.RequestException,
                    telebot.apihelper.ApiTelegramException) as e:
                logger.error("Ошибка отправки фото: %s", str(e))
                self.bot.send_message(
                    chat_id, message,
                    parse_mode='Markdown', reply_markup=markup
                )
        else:
            self.bot.send_message(
                chat_id, message,
                parse_mode='Markdown', reply_markup=markup
            )
