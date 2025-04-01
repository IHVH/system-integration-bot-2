"""Module implement github API"""

from typing import List
import requests
import telebot
from telebot import types
from bot_func_abc import AtomicBotFunctionABC


class GithubAPICommits(AtomicBotFunctionABC):
    """Function work with github API
    """

    commands: List[str] = ["github", "git"]
    authors: List[str] = ["IHVH"]
    about: str = "Информация о коммитах"
    description: str = """Функция предназначена для получения информации о
      коммитах в репозитори https://github.com/IHVH/system-integration-bot-2 
      для вызова функции можно использовать команды `/git` `/github`  
      """
    state: bool = True

    bot: telebot.TeleBot

    def set_handlers(self, bot: telebot.TeleBot):
        """Set message handlers"""

        self.bot = bot

        @bot.message_handler(commands=self.commands)
        def message_hendler_for_github_api(message: types.Message):
            messeges = self.get_data(count=2)
            for commit in messeges:
                bot.send_message(text=commit, chat_id=message.chat.id)

    def get_data(self, count: int = 5):
        """Get data from githab """

        result = []
        owner = "IHVH"
        repo = "system-integration-bot-2"
        url = f'https://api.github.com/repos/{owner}/{repo}/commits?per_page={count}'

        response = requests.get(url, timeout=30)

        list_commits = []
        list_commits = response.json()

        for commit in list_commits:

            date = commit['commit']['author']['date']
            author = commit['commit']['author']['name']
            commit_url = commit['html_url']
            msg = commit['commit']['message']

            message = f"author - {author} \n{msg} \n{date} {commit_url}"
            result.append(message)

        return result
