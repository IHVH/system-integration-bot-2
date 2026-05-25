"""YouTube Video Downloader Bot Function."""

import os
import re
import tempfile
from typing import List

import telebot
from telebot import types
from telebot.callback_data import CallbackData
from bot_func_abc import AtomicBotFunctionABC


try:
    import yt_dlp
    from yt_dlp.utils import DownloadError
    import imageio_ffmpeg
except ImportError as exc:
    raise ImportError("yt-dlp or imageio_ffmpeg is required: pip install yt-dlp") from exc



YOUTUBE_REGEX = re.compile(
    r"(https?://)?(www\.)?"
    r"(youtube\.com/(watch\?v=|shorts/)|youtu\.be/)[\w\-]+"
)




class YouTubeDownloaderFunction(AtomicBotFunctionABC):
    """Скачивает видео с YouTube и отправляет пользователю."""

    commands: List[str] = ["yt" , "youtube"]
    authors: List[str] = ["sahilisgandarov"]
    about: str = "Загрузчик видео с YouTube."
    description: str = (
        "Отправьте ссылку на YouTube — покажу информацию о видео и доступные качества.\n"
        "После выбора качества скачаю видео и отправлю вам.\n\n"
        "Использование: /youtube или просто отправьте ссылку на YouTube."
    )
    state: bool = True

    def __init__(self):
        self._cb = CallbackData("yt_action", "video_id", "fmt_id", prefix=self.commands[0])
        self._sessions: dict = {}
        self._ffmpeg_path = None
        self.bot = None
        try:
            self._ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        except RuntimeError as e:
            print(f"Failed to get ffmpeg via imageio-ffmpeg: {e}")
            self._ffmpeg_path = None


    def set_handlers(self, bot: telebot.TeleBot):
        """Зарегистрируйте все обработчики сообщений и обратных вызовов в боте."""
        self.bot = bot
        @bot.message_handler(commands=self.commands)
        def cmd_youtube(message: types.Message):
            """Обработайте команду /youtube."""
            bot.send_message(
                message.chat.id,
                "🎬 Отправьте ссылку на YouTube:",
            )
            bot.register_next_step_handler(message, self._handle_link)

        @bot.message_handler(func=lambda m: bool(YOUTUBE_REGEX.search(m.text or "")))
        def inline_link(message: types.Message):
            """Обрабатывать встроенные ссылки YouTube, отправляемые в виде обычных сообщений."""
            self._handle_link(message)

        @bot.callback_query_handler(func=None, config=self._cb.filter())
        def quality_callback(call: types.CallbackQuery):
            """Обрабатывать запросы обратного вызова для выбора качества."""
            data = self._cb.parse(call.data)
            self._download_and_send(call, data["video_id"], data["fmt_id"])


    def _handle_link(self, message: types.Message):
        """ Извлеките URL-адрес YouTube из сообщения и предоставьте и
        нформацию о видео с возможностью выбора качества."""
        text = message.text or ""
        match = YOUTUBE_REGEX.search(text)
        if not match:
            self.bot.reply_to(message, "❌ Не удалось найти корректную ссылку на YouTube.")
            return

        url = match.group(0)
        if not url.startswith("http"):
            url = "https://" + url

        wait_msg = self.bot.send_message(message.chat.id, "🔍 Получаю информацию о видео…")

        try:
            info = self._fetch_info(url)
        except DownloadError as exc:
            self.bot.edit_message_text(
                f"❌ Ошибка: {exc}", message.chat.id, wait_msg.message_id
            )
            return

        _, caption, markup = self._build_video_card(message.chat.id, url, info)

        try:
            thumb = info.get("thumbnail")
            if thumb:
                self.bot.delete_message(message.chat.id, wait_msg.message_id)
                self.bot.send_photo(
                    message.chat.id, thumb,
                    caption=caption, reply_markup=markup, parse_mode="Markdown"
                )
            else:
                self.bot.edit_message_text(
                    caption, message.chat.id, wait_msg.message_id,
                    reply_markup=markup, parse_mode="Markdown"
                )
        except Exception: # pylint: disable=broad-except
            self.bot.send_message(
                message.chat.id, caption,
                reply_markup=markup, parse_mode="Markdown"
            )

    def _build_video_card(self, chat_id : int, url : str, info : dict):
        video_id  = (info.get("id") or "unknown")[:16]
        title     = info.get("title", "Неизвестно")
        duration  = self._fmt_duration(info.get("duration", 0))
        channel   = info.get("uploader", "?")
        views     = info.get("view_count")
        views_str = f"👁 {views:,}".replace(",", " ") if views else ""

        formats = self._pick_formats(info.get("formats", []))
        self._sessions[chat_id] = {
            "video_id": video_id,
            "url":      url,
            "formats":  formats,
        }

        caption = (
            f"🎬 *{self._esc(title)}*\n"
            f"👤 {self._esc(channel)}\n"
            f"⏱ {duration}"
            + (f"    {views_str}" if views_str else "")
            + "\n\nВыберите качество:"
        )

        markup = self._build_quality_markup(video_id, formats)
        return video_id, caption, markup

    def _build_ydl_opts(self, tmpdir: str, fmt_id: str, chosen: dict) -> dict:
        """Создать параметры yt-dlp для выбранного формата."""
        out_tmpl   = os.path.join(tmpdir, "%(title)s.%(ext)s")
        audio_only = chosen.get("audio_only", False)

        ydl_opts = {
            "outtmpl":     out_tmpl,
            "quiet":       True,
            "no_warnings": True,
            "noplaylist":  True,
            "ffmpeg_location":  self._ffmpeg_path,
            }

        if audio_only:
            ydl_opts["format"] = "bestaudio/best"
            ydl_opts["postprocessors"] = [{
                "key":            "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                }]
        else:
            ydl_opts["format"] = (
                f"{fmt_id}+bestaudio/best[height<={chosen.get('height', 1080)}]"
                )
            ydl_opts["merge_output_format"] = "mp4"

        return ydl_opts

    def _send_downloaded_file(self, chat_id: int, tmpdir: str,
           audio_only: bool, status_msg_id: int):
        files = os.listdir(tmpdir)
        if not files:
            raise FileNotFoundError("Файл не был создан.")

        filepath = os.path.join(tmpdir, files[0])
        size     = os.path.getsize(filepath)
        max_size = int(os.environ.get("MAX_BOT_FILE_SIZE", 50 * 1024 * 1024))

        if size > max_size:
            self.bot.edit_message_text(
                f"⚠️ Файл слишком большой ({size // (1024 * 1024)} МБ).\n"
                "Telegram не принимает файлы больше 50 МБ.\n"
                "Пожалуйста, выберите качество пониже.",
                chat_id, status_msg_id
                )
            return

        self.bot.edit_message_text(
            "📤 Загружаю в Telegram…", chat_id, status_msg_id
            )

        with open(filepath, "rb") as f:
            if audio_only:
                self.bot.send_audio(chat_id, f)
            else:
                self.bot.send_video(chat_id, f, supports_streaming=True)

            self.bot.delete_message(chat_id, status_msg_id)

    def _download_and_send(self, call: types.CallbackQuery, video_id: str, fmt_id: str):
        chat_id = call.message.chat.id
        session = self._sessions.get(chat_id)

        if not session or session["video_id"] != video_id:
            self.bot.answer_callback_query(
                call.id, "⚠️ Сессия устарела. Отправьте ссылку заново."
            )
            return

        url     = session["url"]
        formats = session["formats"]
        chosen  = next((f for f in formats if f["format_id"] == fmt_id), None)

        if not chosen:
            self.bot.answer_callback_query(call.id, "❌ Формат не найден.")
            return

        self.bot.answer_callback_query(call.id, "⬇️ Скачиваю…")
        status_msg = self.bot.send_message(
            chat_id,
            f"⬇️ Скачиваю *{self._esc(chosen['label'])}*, подождите…",
            parse_mode="Markdown"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts   = self._build_ydl_opts(tmpdir, fmt_id, chosen)
            audio_only = chosen.get("audio_only", False)

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                    self._send_downloaded_file(chat_id, tmpdir, audio_only, status_msg.message_id)
            except DownloadError as exc:
                self.bot.edit_message_text(
                    f"❌ Ошибка при скачивании: {exc}", chat_id, status_msg.message_id
                )


    def _fetch_info(self, url: str) -> dict:
        ydl_opts = {"quiet": True, "no_warnings": True, "noplaylist": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    def _pick_formats(self, raw_formats: list) -> list:
        """
        Отбирает популярные разрешения из доступных форматов
        и добавляет опцию MP3.
        """
        seen_heights = set()
        result = []

        video_fmts = [
            f for f in raw_formats
            if f.get("vcodec", "none") != "none"
            and f.get("ext") in ("mp4", "webm")
            and f.get("height")
        ]
        video_fmts.sort(key=lambda x: x.get("height", 0), reverse=True)

        for f in video_fmts:
            h = f["height"]
            if h in seen_heights:
                continue
            if h not in (2160, 1440, 1080, 720, 480, 360, 240, 144):
                continue
            seen_heights.add(h)
            filesize = f.get("filesize") or f.get("filesize_approx") or 0
            size_str = f" (~{filesize // (1024 * 1024)} МБ)" if filesize else ""
            result.append({
                "format_id":  f["format_id"],
                "label":      f"🎥 {h}p{size_str}",
                "height":     h,
                "audio_only": False,
            })

        result.append({
            "format_id":  "mp3",
            "label":      "🎵 Только аудио (MP3)",
            "audio_only": True,
        })

        return result

    def _build_quality_markup(self, video_id: str, formats: list) -> types.InlineKeyboardMarkup:
        markup = types.InlineKeyboardMarkup(row_width=2)
        buttons = [
            types.InlineKeyboardButton(
                fmt["label"],
                callback_data=self._cb.new(
                    yt_action="dl",
                    video_id=video_id,
                    fmt_id=fmt["format_id"]
                )
            )
            for fmt in formats
        ]
        markup.add(*buttons)
        return markup

    @staticmethod
    def _fmt_duration(seconds: int) -> str:
        if not seconds:
            return "?"
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

    @staticmethod
    def _esc(text: str) -> str:
        """Экранирование спецсимволов Markdown."""
        for ch in r"_*[]()~`>#+-=|{}.!":
            text = text.replace(ch, f"\\{ch}")
        return text
