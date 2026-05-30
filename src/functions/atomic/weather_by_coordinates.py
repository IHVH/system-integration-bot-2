"""Погода через Weather.gov API"""

import json
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional
from bot_func_abc import AtomicBotFunctionABC

class WeatherBotFunction(AtomicBotFunctionABC):
    """Класс функции погоды для бота"""
    commands: List[str] = ["weather_by_coordinates", "stations"]
    authors: List[str] = ["KoLiSi"]
    about: str = "Погода и метеостанции"
    description: str = """
    Получает погоду и список метеостанций через Weather.gov API

    Команды:
    /weather_by_coordinates <широта> <долгота> - текущая погода по координатам
    /stations <широта> <долгота> - список ближайших метеостанций
    /stations <ID станции> - информация о метеостанции
    """

    state: bool = True
    API_BASE_URL = "https://api.weather.gov"

    def _make_request(self, url: str) -> Optional[Dict[str, Any]]:
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

    def execute(self, command: str, args: List[str]) -> str:
        """Returns weather data for coordinates."""
        if not self.state:
            return "Функция погоды временно отключена."

        if not args and command == "weather_by_coordinates":
            return self._show_help()
        if not args and command == "stations":
            return self._show_stations_help()

        if command == "weather_by_coordinates":
            return self._handle_weather(args)
        if command == "stations":
            return self._handle_stations(args)

        return f"Неизвестная команда: {command}"

    def _show_help(self) -> str:
        return """
Пожалуйста, введите координаты для получения погоды.

Использование:
/weather_by_coordinates <широта> <долгота>

Пример:
/weather_by_coordinates 38.6270 -90.1994
"""

    def _show_stations_help(self) -> str:
        return """
Пожалуста, введите координаты для получения списка метеостанций или ID станции для получения информации.

Варианты использования:
1. /stations <широта> <долгота> - станции рядом
2. /stations <ID станции> - информация о станции

Примеры:
/stations 38.6270 -90.1994
/stations KSTL
"""

    def _handle_weather(self, args: List[str]) -> str:
        if len(args) < 2:
            return "Укажите координаты!\nПример: /weather_by_coordinates 38.6270 -90.1994"

        try:
            lat = float(args[0])
            lon = float(args[1])
        except ValueError:
            return "Координаты должны быть числами!"

        if not -90 <= lat <= 90:
            return "Широта должна быть от -90 до 90"
        if not -180 <= lon <= 180:
            return "Долгота должна быть от -180 до 180"

        return self._get_weather(lat, lon)

    def _handle_stations(self, args: List[str]) -> str:
        first_arg = args[0]

        if first_arg.isalpha() and 3 <= len(first_arg) <= 4:
            return self._get_station_by_id(first_arg)

        if len(args) >= 2:
            try:
                lat = float(args[0])
                lon = float(args[1])
            except ValueError:
                return "Координаты должны быть числами!\nПример: /stations 38.6270 -90.1994"

            if not -90 <= lat <= 90:
                return "Широта должна быть от -90 до 90"
            if not -180 <= lon <= 180:
                return "Долгота должна быть от -180 до 180"

            return self._get_stations_nearby(lat, lon)

        return self._show_stations_help()

    def _get_weather(self, lat: float, lon: float) -> str:
        points_url = f"{self.API_BASE_URL}/points/{lat},{lon}"
        points_data = self._make_request(points_url)

        if "error" in points_data:
            if "404" in points_data["error"]:
                return f"Координаты {lat}, {lon} не найдены."
            return f"Ошибка: {points_data['error']}"


        props = points_data["properties"]

        rel_loc = props.get("relativeLocation", {})
        city = rel_loc.get("properties", {}).get("city", "Неизвестно")
        state = rel_loc.get("properties", {}).get("state", "")
        location = f"{city}, {state}" if state else city

        forecast_url = props.get("forecast")
        if not forecast_url:
            return "Прогноз недоступен для этих координат"

        forecast_data = self._make_request(forecast_url)
        if "error" in forecast_data:
            return f"Ошибка прогноза: {forecast_data['error']}"

        periods = forecast_data["properties"].get("periods", [])
        if not periods:
            return "Нет данных о погоде"

        current = periods[0]

        return (
    f"Место: {location}\n"
    f"Координаты: {lat}, {lon}\n\n"
    f"Температура: {current.get('temperature', '?')}°"
    f"{current.get('temperatureUnit', 'F')}\n"
    f"Описание: {current.get('shortForecast', 'Нет данных')}\n"
    f"Ветер: {current.get('windSpeed', '?')} "
    f"{current.get('windDirection', '')}\n"
    f"Влажность: "
    f"{current.get('relativeHumidity', {}).get('value', '?')}%\n\n"
    f"Подробнее: "
    f"{current.get('detailedForecast', '')[:300]}"
    f"{'...' if len(current.get('detailedForecast', '')) > 300 else ''}"
)

    def _get_stations_nearby(self, lat: float, lon: float) -> str:
        url = f"{self.API_BASE_URL}/points/{lat},{lon}/stations"
        data = self._make_request(url)

        if "error" in data:
            return f"Ошибка: {data['error']}"

        features = data.get("features", [])
        if not features:
            return f"Рядом с ({lat}, {lon}) нет метеостанций"

        result = f"Метеостанции рядом с ({lat}, {lon}):\n\n"
        for station in features[:10]:
            props = station.get("properties", {})
            station_id = props.get("stationIdentifier", "???")
            name = props.get("name", "Без названия")
            distance = props.get("distance", {}).get("value", 0)

            if distance:
                dist_km = distance / 1000
                result += f"{station_id} - {name}\n   Расстояние: {dist_km:.1f} км\n\n"
            else:
                result += f"{station_id} - {name}\n\n"

        result += "Подробнее о станции: /stations KSTL"
        return result

    def _get_station_by_id(self, station_id: str) -> str:
        url = f"{self.API_BASE_URL}/stations/{station_id.upper()}"
        data = self._make_request(url)

        if "error" in data:
            return f"Станция {station_id} не найдена.\nПопробуйте: KSTL, KJFK, KLAX, KORD"

        props = data.get("properties", {})
        if not props:
            return f"Станция {station_id.upper()} не найдена"

        name = props.get("name", "Неизвестно")
        timezone = props.get("timeZone", "?")
        elevation = props.get("elevation", {}).get("value", "?")

        coords = data.get("geometry", {}).get("coordinates", [0, 0])
        lon, lat = coords[0], coords[1]

        return f"""
Станция: {station_id.upper()}
Название: {name}
Координаты: {lat}, {lon}
Часовой пояс: {timezone}
Высота: {elevation} м
"""

    def set_handlers(self, bot):
        """Регистрирует обработчики команд для бота"""
        @bot.message_handler(commands=self.commands)
        def handle(message):
            parts = message.text.split()
            cmd = parts[0][1:]
            args = parts[1:] if len(parts) > 1 else []
            response = self.execute(cmd, args)
            bot.reply_to(message, response)

    def get_help(self) -> str:
        """Возвращает справку"""
        return self.description
