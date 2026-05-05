"""Модуль для получения информации о сезонах Формула 1 и результатов отдельно взятых пилотов."""

import logging
import requests
import telebot
from telebot import types
from bot_func_abc import AtomicBotFunctionABC


class F1ApiBotFunction(AtomicBotFunctionABC):
    """Модуль для получения результатов выбранного сезона Формула 1."""
       
    commands: list[str] = ["f1"]
    authors: list[str] = ["sidorovt"]
    about: str = "Результаты сезонов Формула 1 с 1950г. по текущий."
    description: str = (
        "Показывает результаты сезона Формула 1."
        "Используйте: /f1 <год сезона> (например, /f1 2026)."
    )
    state: bool = False
    bot: telebot.TeleBot
    logger: logging.Logger
    api_url: str = "https://api.jolpi.ca/ergast/f1"

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(name)s %(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)
        self.logger.info("F1ApiBotFunction initialized")
    
    def set_handlers(self, bot: telebot.TeleBot):
        self.bot = bot
        self.logger.info("Setting handlers for /f1")
        
        @bot.message_handler(commands=["f1"])
        def get_season(message: types.Message):
            self.logger.info("Command /f1 triggered by user %s", message.from_user.username)
            
            parts = message.text.split()
            if len(parts) < 2:
                bot.send_message(message.chat.id, "Укажите год нужного вам сезона, например: /f1 2026")
                return
            
            season = parts[1]
            
            if not season.isdigit() or not (1950 <= int(season) <= 2026):
                bot.send_message(message.chat.id, "❌ Некорректный год. Укажите год от 1950 до текущего, например: /f1 2026")
                return
            
            bot.send_message(message.chat.id, f"🔍 Загружаю данные сезона {season}...")
            
            races = self._fetch_season_races(season)
            if races is None:
                bot.send_message(message.chat.id, "❌ Не удалось получить данные.")
                return
            
            if not races:
                bot.send_message(message.chat.id, f"⚠️ Гонки для сезона {season} не найдены.")
                return
            
            text = f"🏎️ *Сезон Формула 1 - {season}\nВсего этапов: {len(races)}\n\nВыберите гонку:"
            markup = types.InlineKeyboardMarkup(row_width=1)
            
            for race in races:
                round_num = race.get("round", "?")
                race_name = race.get("raceName", "Неизвестная гонка")
                date = race.get("date", "Дата неизвестна")
                label = f"Этап {round_num}: {race_name} ({date})"
                callback_data = f"f1_race_{season}_{round_num}"
                markup.add(types.InlineKeyboardButton(label, callback_data=callback_data))
            
            bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)
        
        @bot.callback_query_handler(func=lambda call: call.data.startswith("f1_race_"))
        def handle_race_selection(call: types.CallbackQuery):
            """Обрабатывает выбор гонки и показывает результаты."""
            _, _, season, round_num = call.data.split("_", 3)
            
            bot.answer_callback_query(call.id, f"Загружаю результаты этапа {round_num}...")
            
            results = self._fetch_race_results(season, round_num)
            if results is None:
                bot.send_message(call.message.chat.id, "❌ Не удалось получить результаты гонки.")
                return
            
            race_info = results.get("race", {})
            race_name = results.get("raceName", "Неизвестная гонка")
            race_date = results.get("date", "?")
            drivers = results.get("drivers", [])
            
            if not drivers:
                bot.send_message(call.message.chat.id, f"⚠️ Результаты гонки {race_name} пока недоступны.", parse_mode="Markdown")
                return
            
            lines = [f"🏁 {race_name} ({race_date})\n"]
            medals = {1: "🥇", 2: "🥈", 3: "🥉"}
            
            for driver in drivers:
                pos = driver.get("position", "?")
                name = driver.get("name", "Неизвестно")
                team = driver.get("constructor", "?")
                time = driver.get("time", driver.get("status", "-"))
                medal = medals.get(int(pos), f"{pos}.")
                lines.append(f"{medal} {name} ({team}) - {time}")
                
            bot.send_message(call.message.chat.id, "\n".join(lines), parse_mode="Markdown")
    
    def _fetch_season_races(self, season: str) -> list | None:
        '''Получает список гонок выбранного сезона'''
        self.logger.info("Fetching races started")
        url = f"{self.api_url}/{season}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            races = data["MRData"]["RaceTable"]["Races"]
            self.logger.info("Fetched %d races for season %s", len(races), season)
        except (requests.RequestException, KeyError) as e:
            self.logger.error("Failed to fetch %s: %s", season, e)
            return None
    
    def _fetch_race_results(self, season: str, round_num: str) -> dict | None:
        '''Получаем результаты конкретной гонки'''
        self.logger.info("Fetching results for round %s started", round_num)
        url = f"{self.api_url}/{season}/{round_num}/results"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            race = data["MRData"]["RaceTable"]["Races"][0]
            
            drivers = []
            for result in race.get("Results", []):
                drivers.append({
                    "position": result.get("position", "?"),
                    "name": f"{result['Driver']['givenName']} {result['Driver']['familyName']}",
                    "constructor": result["Constructor"]["name"],
                    "time": result.get("Time", {}).get("time", None),
                    "status": result.get("status", "-") 
                })
                
            return {"race": race, "drivers": drivers}
        
        except (requests.RequestException, KeyError, IndexError) as e:
            self.logger.error("Failed to fetch results for %s round %s: %s", season, round_num, e)
            return None