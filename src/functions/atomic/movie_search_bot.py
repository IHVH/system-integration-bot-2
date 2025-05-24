"""Telegram bot module for searching movies using the OMDB API."""

import os
import logging
import html
from typing import Dict, List, Optional, Any
import requests
import telebot
from telebot import types


class AtomicBotFunctionABC:
    """Abstract base class for bot functions with required interface."""
    def get_commands(self) -> List[str]:
        """Return list of bot commands."""
        raise NotImplementedError

    def get_authors(self) -> List[str]:
        """Return list of authors."""
        raise NotImplementedError


class MovieSearchBotFunction(AtomicBotFunctionABC):
    """Telegram bot function for searching movies using OMDB API."""

    def __init__(self) -> None:
        """Initialize movie search bot function."""
        self._commands = ["movie", "searchmovie"]
        self._authors = ["IHVH"]
        self._about = "Search movies by title"
        self._description = (
            "Search movies by title using OMDB API.\n"
            "Usage: /movie <movie title>\n"
            "Example: /movie Inception\n"
            "Returns a list of movies. Click a movie for details."
        )
        self._state = True
        self._omdb_url = "http://www.omdbapi.com/"
        logging.basicConfig(level=logging.INFO)

    def get_commands(self) -> List[str]:
        """Return list of bot commands."""
        return self._commands

    def get_authors(self) -> List[str]:
        """Return list of authors."""
        return self._authors

    def set_handlers(self, bot: telebot.TeleBot) -> None:
        """Register bot handlers for movie search and details retrieval."""
        @bot.message_handler(commands=self._commands)
        def movie_search_handler(message: types.Message) -> None:
            self._process_movie_search(bot, message)

        @bot.callback_query_handler(
            func=lambda query: query.data.startswith('details_')
        )
        def movie_details_callback(callback_query: types.CallbackQuery) -> None:
            self._process_movie_details(bot, callback_query)

    def _process_movie_search(
        self,
        bot: telebot.TeleBot,
        message: types.Message
    ) -> None:
        """Process movie search request."""
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            bot.reply_to(message, "Provide a movie title. Example: /movie Inception")
            return

        movie_title = args[1].strip()
        if len(movie_title) < 2:
            bot.reply_to(message, "Please enter at least 2 characters for the title.")
            return

        movies = self._fetch_movies(movie_title)
        if not movies:
            bot.reply_to(message, "No movies found. Try another title.")
            return

        markup = self._generate_movie_buttons(movies)
        bot.send_message(message.chat.id, "Found movies:", reply_markup=markup)

    def _process_movie_details(
        self,
        bot: telebot.TeleBot,
        callback_query: types.CallbackQuery
    ) -> None:
        """Process movie details request."""
        movie_id = callback_query.data.split('_', 1)[1]
        movie_details = self._fetch_movie_details(movie_id)
        if not movie_details:
            logging.warning(
                "Failed to get movie details for callback: %s",
                callback_query.data
            )
            bot.answer_callback_query(
                callback_query.id,
                "Failed to get details, please try again later."
            )
            return

        response_text = self._format_movie_details(movie_details)
        bot.answer_callback_query(callback_query.id)
        bot.send_message(
            callback_query.message.chat.id,
            response_text,
            parse_mode='HTML'
        )

    def _generate_movie_buttons(
        self,
        movies: List[Dict[str, str]]
    ) -> types.InlineKeyboardMarkup:
        """Generate inline keyboard buttons for movies list."""
        markup = types.InlineKeyboardMarkup(row_width=1)
        for movie in movies[:10]:
            if 'imdbID' not in movie:
                continue
            button_text = f"{movie['Title']} ({movie['Year']})"
            callback_data = f"details_{movie['imdbID']}"
            markup.add(
                types.InlineKeyboardButton(button_text, callback_data=callback_data)
            )
        return markup

    def _fetch_omdb_token(self) -> str:
        """Fetch OMDB API token from environment."""
        token = os.environ.get("OMDB_API_TOKEN")
        if not token:
            logging.error("OMDB_API_TOKEN is not set")
            raise ValueError("OMDB API token is not configured")
        return token

    def _fetch_movies(self, title: str) -> List[Dict[str, str]]:
        """Search for movies matching the title."""
        return self._make_omdb_request({"s": title})

    def _fetch_movie_details(self, movie_id: str) -> Optional[Dict[str, str]]:
        """Fetch detailed movie information by IMDb ID."""
        return self._make_omdb_request({"i": movie_id})

    def _make_omdb_request(self, params: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Make a request to OMDB API and handle errors."""
        try:
            params["apikey"] = self._fetch_omdb_token()
            response = requests.get(self._omdb_url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            return data if data.get('Response') == 'True' else None
        except requests.RequestException as error:
            logging.error("OMDB API request failed: %s", error, exc_info=True)
            return None

    def _format_movie_details(self, movie: Dict[str, str]) -> str:
        """Format movie details into an HTML string."""
        details = [
            f"<b>{html.escape(movie.get('Title', 'N/A'))}</b> "
            f"({html.escape(movie.get('Year', 'N/A'))})",
            f"Genre: {html.escape(movie.get('Genre', 'N/A'))}",
            f"Director: {html.escape(movie.get('Director', 'N/A'))}",
            f"Actors: {html.escape(movie.get('Actors', 'N/A'))}",
            f"Plot: {html.escape(movie.get('Plot', 'N/A'))}",
            f"IMDb Rating: {html.escape(movie.get('imdbRating', 'N/A'))}",
            f"Runtime: {html.escape(movie.get('Runtime', 'N/A'))}"
        ]
        return "\n".join(details)
