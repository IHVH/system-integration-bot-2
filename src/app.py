"""Main module for running the application"""

from dotenv import load_dotenv
import os
from start_app import StartApp

# Загружаем переменные из .env
load_dotenv()

_START_COMANDS = ["start", "help", "info", "s", "h", "i"]

if __name__ == '__main__':
    app = StartApp(_START_COMANDS)  
    app.start_polling()