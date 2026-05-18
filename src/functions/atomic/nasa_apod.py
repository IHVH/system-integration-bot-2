"""Module implementation of the atomic function for NASA's 
Astronomy Picture of the Day (APOD) API and Earth API."""

import os
import logging
from typing import List, Dict, Any, Optional
import requests
import telebot
from telebot import types
from bot_func_abc import AtomicBotFunctionABC


class AtomicNasaApodFunction(AtomicBotFunctionABC):
    """Implementation of atomic function for NASA Astronomy Picture o the Day and Earth imagery"""

    commands: List[str] = ["nasa", "earth"]
    authors: List[str] = ["mitochka"]
    about: str = "Астрономическое снимки от NASA"
    description: str = """NASA сервисы:
    1. APOD: /nasa - фото дня
    2. Earth: /earth 37.7749,-122.4194 - снимок Земли
    """
    state: bool = True

    # API configuration
    APOD_API_URL = "https://api.nasa.gov/planetary/apod"
    EARTH_API_URL = "https://api.nasa.gov/planetary/earth/imagery"
    def __init__(self):
        self.bot = None
        self.logger = logging.getLogger(__name__)

    def set_handlers(self, bot: telebot.TeleBot):
        """Set message handlers"""
        self.bot = bot
        self.logger.info("Регистрация обработчиков команд NASA API")

        @bot.message_handler(commands=[self.commands[0]])
        def nasa_message_handler(message: types.Message):
            try:
                command_parts = message.text.split()

                # Check if the command has additional parameters
                if len(command_parts) > 1 and command_parts[1].lower() == "random":
                    self.__handle_random_apod(message)
                else:
                    self.__handle_today_apod(message)
            except (telebot.apihelper.ApiException, KeyError, ValueError) as ex:
                logging.exception("Ошибка при обработке команды: %s", ex)
                bot.reply_to(message, f"Произошла ошибка: {str(ex)}")
            except requests.exceptions.RequestException as ex:
                logging.exception("Сетевая ошибка: %s", ex)
                bot.reply_to(message, f"Ошибка сети: {str(ex)}")
            except (TypeError, AttributeError, RuntimeError) as ex:
                logging.critical("Неожиданная ошибка: %s", ex)
                bot.reply_to(message, "Произошла ошибка. Координаты стран СНГ не поддерживаются.")
        @bot.message_handler(commands=[self.commands[1]])
        def earth_message_handler(message: types.Message):
            try:
                command_parts = message.text.split()
                if len(command_parts) < 2:
                    bot.reply_to(
                        message,
                        "Пожалуйста, укажите координаты в формате: /earth <широта>,<долгота>\n"
                        "Например: /earth 37.7749,-122.4194 (Сан-Франциско)"
                    )
                    return
                # Parse coordinates
                try:
                    coords = command_parts[1].split(',')
                    if len(coords) != 2:
                        raise ValueError("Неверный формат координат")
                    lat = float(coords[0])
                    lon = float(coords[1])
                    # Validate coordinates
                    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
                        raise ValueError("Координаты вне допустимого диапазона")
                    self.__handle_earth_imagery(message, lat, lon)
                except ValueError as e:
                    bot.reply_to(
                        message,
                        f"Ошибка в координатах: {str(e)}\n"
                        "Используйте формат: /earth <широта>,<долгота>\n"
                        "Например: /earth 37.7749,-122.4194 (Сан-Франциско)"
                    )
            except (telebot.apihelper.ApiException, KeyError, ValueError) as ex:
                self.logger.exception("Ошибка при обработке команды Earth: %s", ex)
                bot.reply_to(message, f"Произошла ошибка: {str(ex)}")
            except requests.exceptions.RequestException as ex:
                self.logger.exception("Сетевая ошибка при обработке команды Earth: %s", ex)
                bot.reply_to(message, f"Ошибка сети: {str(ex)}")
            except (TypeError, AttributeError, RuntimeError) as ex:
                self.logger.critical("Неожиданная ошибка при обработке команды Earth: %s", ex)
                bot.reply_to(message, "Произошла ошибка. Координаты стран СНГ не поддерживаются.")

    def __get_api_key(self) -> str:
        """Get NASA API key from environment variables"""
        api_key = os.environ.get("NASA_API_KEY")
        if not api_key:
            self.logger.warning("NASA_API_KEY не найден в переменных окружения")
            # Fallback to demo key for development
            return "DEMO_KEY"
        return api_key

    def __make_api_request(self, url: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Make a request to NASA APIs"""
        if params is None:
            params = {}

        # Always include the API key
        params["api_key"] = self.__get_api_key()

        try:
            self.logger.debug("Запрос к NASA API: %s с параметрами %s", url, params)
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            # Check if response is JSON or binary data
            content_type = response.headers.get('Content-Type', '')
            if 'application/json' in content_type:
                return response.json()
            return response.content
        except requests.exceptions.RequestException as e:
            self.logger.error("Ошибка запроса к NASA API: %s", e)
            raise RuntimeError(f"Ошибка API запроса: {str(e)}") from e

    def __handle_today_apod(self, message: types.Message) -> None:
        """Handle request for today's Astronomy Picture of the Day"""
        chat_id = message.chat.id

        self.bot.send_message(chat_id, "Получаю астрономическое фото дня...")

        try:
            data = self.__make_api_request(self.APOD_API_URL)
            self.__send_apod_data(chat_id, data)
        except (telebot.apihelper.ApiException, KeyError, ValueError) as ex:
            logging.exception("Ошибка при обработке данных: %s", ex)
            self.bot.send_message(chat_id, f"Ошибка при отправке данных: {str(ex)}")
        except requests.exceptions.RequestException as ex:
            logging.exception("Сетевая ошибка: %s", ex)
            self.bot.send_message(chat_id, f"Ошибка сети: {str(ex)}")
        except (TypeError, AttributeError, RuntimeError) as ex:
            self.logger.critical("Неожиданная ошибка при отправке данных: %s", ex)
            self.bot.send_message(chat_id, "Произошла неожиданная ошибка")

    def __handle_random_apod(self, message: types.Message) -> None:
        """Handle request for a random Astronomy Picture of the Day"""
        chat_id = message.chat.id

        self.bot.send_message(chat_id, "Получаю случайное астрономическое фото...")

        try:
            data = self.__make_api_request(self.APOD_API_URL, {"count": 1})
            # API returns a list with one item for random requests
            self.__send_apod_data(chat_id, data[0])
        except (telebot.apihelper.ApiException, KeyError, ValueError) as ex:
            logging.exception("Ошибка при обработке данных: %s", ex)
            self.bot.send_message(chat_id, f"Ошибка при отправке данных: {str(ex)}")
        except requests.exceptions.RequestException as ex:
            logging.exception("Сетевая ошибка: %s", ex)
            self.bot.send_message(chat_id, f"Ошибка сети: {str(ex)}")
        except (TypeError, AttributeError, RuntimeError) as ex:
            self.logger.critical("Неожиданная ошибка при отправке данных: %s", ex)
            self.bot.send_message(chat_id, "Произошла неожиданная ошибка")
    def __handle_earth_imagery(self, message: types.Message, lat: float, lon: float) -> None:
        """Handle request for Earth imagery at specific coordinates"""
        chat_id = message.chat.id

        self.bot.send_message(
            chat_id,
            f"Получаю спутниковый снимок для координат: {lat}, {lon}..."
        )

        try:
            # Prepare parameters for Earth API
            params = {
                "lat": lat,
                "lon": lon,
                "dim": 0.15,  # Size in degrees (~15-20km)
                "date": "2020-01-01"  # Use a recent date with good coverage
            }
            # Make request to Earth API
            image_data = self.__make_api_request(self.EARTH_API_URL, params)
            caption = (
                f"🛰 *Спутниковый снимок Земли*\n"
                f"📍 Координаты: {lat}, {lon}\n"
                f"🗓 Дата съемки: 2020-01-01\n\n"
                f"Изображение предоставлено NASA Earth API"
            )
            self.bot.send_photo(
                chat_id,
                image_data,
                caption=caption,
                parse_mode="Markdown"
            )
            # Send a link to Google Maps for these coordinates
            maps_url = f"https://www.google.com/maps/@{lat},{lon},12z"
            self.bot.send_message(
                chat_id,
                f"[🗺 Открыть эту локацию в Google Maps]({maps_url})",
                parse_mode="Markdown",
                disable_web_page_preview=False
            )
        except (telebot.apihelper.ApiException, KeyError, ValueError) as ex:
            logging.exception("Ошибка при обработке данных: %s", ex)
            self.bot.send_message(
                chat_id,
                f"Ошибка при получении снимка: {str(ex)}\n"
                "Возможно, для указанных координат нет доступных снимков."
            )
        except requests.exceptions.RequestException as ex:
            logging.exception("Сетевая ошибка: %s", ex)
            self.bot.send_message(chat_id, f"Ошибка сети: {str(ex)}")
        except (
            TypeError,
            AttributeError,
            IndexError,
            ConnectionError,
            TimeoutError,
            IOError
        ) as ex:
            logging.critical("Неожиданная ошибка при получении снимка: %s", ex)
            self.bot.send_message(
                chat_id,
                f"Ошибка при получении снимка: {str(ex)}\n"
                "Возможно, для указанных координат нет доступных снимков."
            )

    def __send_apod_data(self, chat_id: int, data: Dict[str, Any]) -> None:
        """Send APOD data to the user"""
        try:
            # Check if we have all required fields
            if not all(key in data for key in ["title", "date", "explanation"]):
                self.bot.send_message(chat_id, "Получены неполные данные от NASA API.")
                return

            # Format the caption
            caption = f"🔭 *{data['title']}*\n" f"📅 Дата: {data['date']}\n\n"

            # Add copyright information if available
            if "copyright" in data:
                caption += f"© {data['copyright']}\n\n"

            # Add explanation (truncate if too long for Telegram)
            explanation = data["explanation"]
            if len(explanation) > 800:
                explanation = explanation[:797] + "..."
            caption += explanation

            # Check media type and send appropriate message
            if data.get("media_type") == "image":
                # For images, send photo with caption
                self.bot.send_photo(
                    chat_id, data["url"], caption=caption, parse_mode="Markdown"
                )
            elif data.get("media_type") == "video":
                # For videos, send the thumbnail as photo and video URL in caption
                if "thumbnail_url" in data:
                    full_caption = caption + f"\n\n[🎬 Смотреть видео]({data['url']})"
                    self.bot.send_photo(
                        chat_id,
                        data["thumbnail_url"],
                        caption=full_caption,
                        parse_mode="Markdown",
                    )
                else:
                    # If no thumbnail, just send text with video link
                    full_caption = caption + f"\n\n[🎬 Смотреть видео]({data['url']})"
                    self.bot.send_message(
                        chat_id,
                        full_caption,
                        parse_mode="Markdown",
                        disable_web_page_preview=False,
                    )
            else:
                # For other media types, send as text
                full_caption = caption #+ f"\n\n[🔗 Открыть ресурс]({data['url']})"
                self.bot.send_message(
                    chat_id,
                    full_caption,
                    parse_mode="Markdown",
                    disable_web_page_preview=False,
                )

        except (telebot.apihelper.ApiException, KeyError, ValueError) as ex:
            logging.exception("Ошибка при обработке данных: %s", ex)
            self.bot.send_message(chat_id, f"Ошибка при отправке данных: {str(ex)}")
        except requests.exceptions.RequestException as ex:
            logging.exception("Сетевая ошибка: %s", ex)
            self.bot.send_message(chat_id, f"Ошибка сети: {str(ex)}")
        except (TypeError, AttributeError, RuntimeError) as ex:
            logging.critical("Неожиданная ошибка при отправке данных: %s", ex)
            self.bot.send_message(chat_id, "Произошла неожиданная ошибка.")
