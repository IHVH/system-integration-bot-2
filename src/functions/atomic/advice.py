"""Советы из Advice Slip API."""

import json
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional
from bot_func_abc import AtomicBotFunctionABC


class AdviceBotFunction(AtomicBotFunctionABC):
    """Класс функции советов для бота."""

    commands: List[str] = ["random_advice", "search_advice", "advice_by_id"]
    authors: List[str] = ["Dmitry-ter"]
    about: str = "Случайные советы и поиск"
    description: str = """
    Получает советы из Advice Slip API

    Команды:
    /random_advice - случайный совет
    /random_advice <число> - несколько случайных советов (1-10)
    /search_advice <текст> - поиск советов по ключевому слову
    /advice_by_id <номер> - совет по его ID
    """

    state: bool = True
    BASE_URL = "https://api.adviceslip.com"

    def _make_request(self, url: str) -> Optional[Dict[str, Any]]:
        """Отправляет запрос к API."""
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                    "Accept": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return {"error": f"Ошибка HTTP {e.code}"}
        except urllib.error.URLError as e:
            return {"error": f"Ошибка URL: {e.reason}"}
        except (ValueError, KeyError) as e:
            return {"error": f"Ошибка обработки данных: {e}"}

    def execute(self, command: str, args: List[str]) -> str:
        """Главный метод, вызываемый ботом."""
        if not self.state:
            return "Функция советов временно отключена."

        if command == "random_advice":
            return self._handle_random_advice(args)
        if command == "search_advice":
            return self._handle_search_advice(args)
        if command == "advice_by_id":
            return self._handle_advice_by_id(args)

        return f"Неизвестная команда: {command}"

    def _handle_random_advice(self, args: List[str]) -> str:
        """Обрабатывает команду random_advice."""
        if not args:
            return self._get_random_advice()

        try:
            count = int(args[0])
            if count < 1:
                return "Число должно быть больше 0"
            if count > 10:
                return "Не больше 10 советов за раз"
            return self._get_multiple_advice(count)
        except ValueError:
            return "Укажите число. Пример: /random_advice 3"

    def _handle_search_advice(self, args: List[str]) -> str:
        """Обрабатывает команду search_advice."""
        if not args:
            return self._show_search_help()

        query = " ".join(args)
        return self._search_advice(query)

    def _handle_advice_by_id(self, args: List[str]) -> str:
        """Обрабатывает команду advice_by_id."""
        if not args:
            return "Укажите ID совета. Пример: /advice_by_id 42"

        slip_id = args[0]

        if not slip_id.isdigit():
            return "ID должен быть числом"

        return self._get_advice_by_id(slip_id)

    def _show_search_help(self) -> str:
        """Показывает помощь по поиску."""
        return """
Помощь по команде /search_advice

Использование:
/search_advice <поисковая фраза>

Примеры:
/search_advice love
/search_advice smile
/search_advice happy

Примечание: поиск работает только на английском языке.
"""

    def _get_random_advice(self) -> str:
        """Возвращает один случайный совет."""
        data = self._make_request(f"{self.BASE_URL}/advice")

        if "error" in data:
            return f"Ошибка: {data['error']}"

        slip = data.get("slip")
        if not slip:
            return "Не удалось получить совет"

        advice = slip.get("advice", "Совет не найден")
        slip_id = slip.get("slip_id", "?")

        return f"Совет #{slip_id}:\n\"{advice}\""

    def _get_multiple_advice(self, count: int) -> str:
        """Возвращает N уникальных случайных советов."""
        advice_list = []
        attempts = 0

        while len(advice_list) < count and attempts < 50:
            data = self._make_request(f"{self.BASE_URL}/advice")

            if "error" in data:
                return f"Ошибка: {data['error']}"

            slip = data.get("slip")
            if slip:
                advice = slip.get("advice", "")
                if advice not in advice_list:
                    advice_list.append(advice)
            attempts += 1

        if not advice_list:
            return "Не удалось получить советы"

        result = f"{count} случайных советов:\n\n"
        for i, adv in enumerate(advice_list, 1):
            result += f"{i}. {adv}\n\n"

        return result.strip()

    def _search_advice(self, query: str) -> str:
        """Ищет советы по ключевой фразе."""
        url = f"{self.BASE_URL}/advice/search/{query}"
        data = self._make_request(url)

        if "error" in data:
            return f"Ошибка: {data['error']}"

        if "message" in data:
            return f"По запросу '{query}' ничего не найдено."

        total_str = data.get("total_results", "0")
        try:
            total = int(total_str)
        except ValueError:
            total = 0

        if total == 0:
            return f"По запросу '{query}' ничего не найдено."

        slips = data.get("slips", [])
        if not slips:
            return f"Найдено {total} результатов, но не удалось их получить"

        result = f"Найдено советов: {total}\n\n"
        for i, slip in enumerate(slips[:5], 1):
            advice = slip.get("advice", "Нет текста")
            result += f"{i}. {advice}\n\n"

        if total > 5:
            result += f"Показано 5 из {total}. Уточните запрос."

        return result.strip()

    def _get_advice_by_id(self, slip_id: str) -> str:
        """Возвращает совет по его ID."""
        url = f"{self.BASE_URL}/advice/{slip_id}"
        data = self._make_request(url)

        if "error" in data:
            return f"Ошибка: {data['error']}"

        if "message" in data:
            return f"Совет с ID {slip_id} не найден."

        slip = data.get("slip")
        if not slip:
            return f"Совет {slip_id} не найден"

        advice = slip.get("advice", "")
        return f"Совет #{slip_id}:\n\"{advice}\""

    def set_handlers(self, bot):
        """Регистрирует обработчики команд для бота."""
        @bot.message_handler(commands=self.commands)
        def handle(message):
            try:
                parts = message.text.split()
                cmd = parts[0][1:]
                args = parts[1:] if len(parts) > 1 else []
                response = self.execute(cmd, args)
                bot.reply_to(message, response)
            except (ValueError, KeyError, AttributeError) as e:
                bot.reply_to(message, f"Ошибка обработки: {str(e)}")

    def get_help(self) -> str:
        """Возвращает справку."""
        return self.description
