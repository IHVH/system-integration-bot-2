"""Модуль для получения информации о сезонах Формула 1 и результатов отдельно взятых пилотов."""

import io
import logging
import re
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import requests
import telebot
from telebot import types
from bot_func_abc import AtomicBotFunctionABC


def _lap_time_to_seconds(raw: str) -> float | None:
    if not raw:
        return None
    parts = raw.strip().split(":")
    try:
        if len(parts) == 1:
            return float(parts[0])
        if len(parts) == 2:
            return float(parts[0]) * 60.0 + float(parts[1])
        if len(parts) == 3:
            return float(parts[0]) * 3600.0 + float(parts[1]) * 60.0 + float(parts[2])
    except ValueError:
        return None
    return None


class F1ApiBotFunction(AtomicBotFunctionABC):
    """Модуль для получения результатов выбранного сезона Формула 1."""

    commands: list[str] = ["f1"]
    authors: list[str] = ["sidorovt"]
    about: str = "Результаты сезонов Формула 1 с 1950г. по текущий."
    description: str = (
        "Показывает результаты сезона Формула 1."
        "Используйте: /f1 <год сезона> (например, /f1 2026)."
    )
    state: bool = True
    bot: telebot.TeleBot
    logger: logging.Logger
    api_url: str = "https://api.jolpi.ca/ergast/f1"
    _driver_ref_pattern: re.Pattern[str] = re.compile(r"^[a-z][a-z0-9_]*$")

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(name)s %(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)
        self._pending_laps_context: dict[tuple[int, int], dict[str, str]] = {}
        self.logger.info("F1ApiBotFunction initialized")

    def _context_key(self, message: types.Message) -> tuple[int, int]:
        uid = message.from_user.id if message.from_user else message.chat.id
        return (message.chat.id, uid)

    def _has_pending_laps_context(self, message: types.Message) -> bool:
        if not message.text or message.text.startswith("/"):
            return False
        return self._context_key(message) in self._pending_laps_context

    def _clear_laps_context(self, message: types.Message) -> None:
        self._pending_laps_context.pop(self._context_key(message), None)

    def _build_laps_chart(self, laps: list[dict], title: str) -> io.BytesIO | None:
        xs: list[int] = []
        ys: list[float] = []
        for lap in laps:
            sec = _lap_time_to_seconds(lap.get("time") or "")
            if sec is None:
                continue
            try:
                xs.append(int(lap["lap"]))
            except (TypeError, ValueError):
                continue
            ys.append(sec)
        if len(xs) < 2:
            return None
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(xs, ys, marker="o", markersize=2, linewidth=1)
        ax.set_xlabel("Круг")
        ax.set_ylabel("Время круга, с")
        ax.set_title(title[:120])
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=120)
        plt.close(fig)
        buf.seek(0)
        return buf

    def set_handlers(self, bot: telebot.TeleBot):
        """Метод для обработки сообщений пользователя."""

        self.bot = bot
        self.logger.info("Setting handlers for /f1")
        max_year = datetime.now().year

        @bot.message_handler(commands=["f1"])
        def get_season(message: types.Message):
            self.logger.info("Command /f1 triggered by user %s", message.from_user.username)

            parts = message.text.split()
            if len(parts) < 2:
                bot.send_message(message.chat.id, "Укажите год нужного вам сезона, например: /f1 2026")
                return

            season = parts[1]

            if not season.isdigit() or not (1950 <= int(season) <= max_year):
                bot.send_message(
                    message.chat.id,
                    f"❌ Некорректный год. Укажите год от 1950 до {max_year}, например: /f1 {max_year}",
                )
                return

            bot.send_message(message.chat.id, f"🔍 Загружаю данные сезона {season}...")

            races = self._fetch_season_races(season)
            if races is None:
                bot.send_message(message.chat.id, "❌ Не удалось получить данные.")
                return

            if not races:
                bot.send_message(message.chat.id, f"⚠️ Гонки для сезона {season} не найдены.")
                return

            text = f"🏎️ *Сезон Формула 1 - {season}*\nВсего этапов: {len(races)}\n\nВыберите гонку:"
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
            """Метод для обработки выбора гонки и вывода результата."""

            _, _, season, round_num = call.data.split("_", 3)

            bot.answer_callback_query(call.id, f"Загружаю результаты этапа {round_num}...")

            results = self._fetch_race_results(season, round_num)
            if results is None:
                bot.send_message(call.message.chat.id, "❌ Не удалось получить результаты гонки.")
                return

            race_name = results.get("raceName", "Неизвестная гонка")
            race_date = results.get("date", "?")
            drivers = results.get("drivers", [])

            if not drivers:
                bot.send_message(
                    call.message.chat.id,
                    f"⚠️ Результаты гонки *{race_name}* пока недоступны.",
                    parse_mode="Markdown",
                )
                return

            lines = [f"🏁 *{race_name}* ({race_date})\n"]
            medals = {1: "🥇", 2: "🥈", 3: "🥉"}

            for driver in drivers:
                pos = driver.get("position", "?")
                name = driver.get("name", "Неизвестно")
                team = driver.get("constructor", "?")
                time = driver.get("time", driver.get("status", "-"))
                try:
                    medal = medals.get(int(pos), f"{pos}.")
                except (TypeError, ValueError):
                    medal = f"{pos}."
                lines.append(f"{medal} {name} ({team}) - {time}")

            bot.send_message(call.message.chat.id, "\n".join(lines), parse_mode="Markdown")

            uid = call.from_user.id if call.from_user else call.message.chat.id
            self._pending_laps_context[(call.message.chat.id, uid)] = {
                "season": season,
                "round": round_num,
            }

            hint = (
                "Если вас интересуют результаты конкретного пилота по кругам, напишите его фамилию "
                "маленькими буквами (как в API Ergast), например, для Charles Leclerc — "
                "`leclerc`, для Max Verstappen — `max_verstappen`."
            )
            bot.send_message(call.message.chat.id, hint, parse_mode="Markdown")

        @bot.message_handler(func=self._has_pending_laps_context)
        def handle_driver_laps_request(message: types.Message):
            raw = (message.text or "").strip().lower()
            if not self._driver_ref_pattern.fullmatch(raw):
                bot.send_message(
                    message.chat.id,
                    "❌ Укажите один идентификатор пилота латиницей в нижнем регистре "
                    "(буквы, при необходимости цифры и `_`), например: `leclerc` или `max_verstappen`.",
                    parse_mode="Markdown",
                )
                return

            ctx = self._pending_laps_context.get(self._context_key(message))
            if not ctx:
                bot.send_message(
                    message.chat.id,
                    "Сначала выберите гонку через /f1 и кнопку этапа.",
                )
                return

            season, round_num = ctx["season"], ctx["round"]
            bot.send_message(message.chat.id, f"🔍 Загружаю круги для `{raw}`...", parse_mode="Markdown")

            laps_payload = self._fetch_driver_laps(season, round_num, raw)
            if laps_payload is None:
                bot.send_message(
                    message.chat.id,
                    "❌ Не удалось получить данные по кругам (ошибка сети или сервера).",
                )
                return

            laps = laps_payload.get("laps") or []
            race_title = laps_payload.get("raceName", "Гонка")

            if not laps:
                bot.send_message(
                    message.chat.id,
                    f"⚠️ Нет данных по кругам для `{raw}` на этом этапе.",
                    parse_mode="Markdown",
                )
                self._clear_laps_context(message)
                return

            text_lines = [
                f"⏱️ *{race_title}* — `{raw}` (сезон {season}, этап {round_num})\n",
            ]
            for lap in laps:
                lap_no = lap.get("lap", "?")
                t = lap.get("time", "?")
                pos = lap.get("position")
                pos_part = f", позиция на круге {pos}" if pos else ""
                text_lines.append(f"Круг {lap_no} — {t}{pos_part}")

            chunk: list[str] = []
            length = 0
            for line in text_lines:
                if length + len(line) + 1 > 4000:
                    bot.send_message(message.chat.id, "\n".join(chunk), parse_mode="Markdown")
                    chunk = [line]
                    length = len(line)
                else:
                    chunk.append(line)
                    length += len(line) + 1
            if chunk:
                bot.send_message(message.chat.id, "\n".join(chunk), parse_mode="Markdown")

            chart_buf = self._build_laps_chart(
                laps,
                f"{race_title} — {raw}",
            )
            if chart_buf:
                bot.send_photo(
                    message.chat.id,
                    chart_buf,
                    caption=f"{race_title} — {raw}: время круга по номерам",
                )

            self._clear_laps_context(message)

    def _fetch_season_races(self, season: str) -> list | None:
        """Метод получающий список гонок выбранного сезона."""

        self.logger.info("Fetching races started")
        url = f"{self.api_url}/{season}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            races = data["MRData"]["RaceTable"]["Races"]
            self.logger.info("Fetched %d races for season %s", len(races), season)
            return races
        except (requests.RequestException, KeyError) as e:
            self.logger.error("Failed to fetch %s: %s", season, e)
            return None

    def _fetch_race_results(self, season: str, round_num: str) -> dict | None:
        """Метод получающий результаты конкретной гонки."""

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
                    "status": result.get("status", "-"),
                })

            return {
                "race": race,
                "raceName": race.get("raceName", "Неизвестная гонка"),
                "date": race.get("date", "?"),
                "drivers": drivers,
            }

        except (requests.RequestException, KeyError, IndexError) as e:
            self.logger.error("Failed to fetch results for %s round %s: %s", season, round_num, e)
            return None

    def _fetch_driver_laps(self, season: str, round_num: str, driver_ref: str) -> dict | None:
        """Загружает круги пилота на этапе (Ergast / Jolpi)."""

        self.logger.info("Fetching laps for %s/%s driver %s", season, round_num, driver_ref)
        url = f"{self.api_url}/{season}/{round_num}/drivers/{driver_ref}/laps.json"
        params = {"limit": 200}
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            races = data["MRData"]["RaceTable"].get("Races") or []
            if not races:
                return {"raceName": "", "laps": []}
            race = races[0]
            race_name = race.get("raceName", "")
            laps_out: list[dict] = []
            for lap in race.get("Laps") or []:
                lap_no = lap.get("number")
                timings = lap.get("Timings") or []
                time_val = timings[0].get("time") if timings else None
                position = timings[0].get("position") if timings else None
                laps_out.append({
                    "lap": lap_no,
                    "time": time_val,
                    "position": position,
                })
            return {"raceName": race_name, "laps": laps_out}
        except (requests.RequestException, KeyError, IndexError) as e:
            self.logger.error(
                "Failed to fetch laps for %s round %s driver %s: %s",
                season,
                round_num,
                driver_ref,
                e,
            )
            return None