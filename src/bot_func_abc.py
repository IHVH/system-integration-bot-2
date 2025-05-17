"""The module contains an abstract class from which
the bot's atomic functions must be inherited."""

from typing import List
from abc import ABC, abstractmethod
import telebot

class AtomicBotFunctionABC(ABC):
    """A class for describing the required fields and methods 
    that students must implement in their atomic functions."""

    @property
    @abstractmethod
    def commands(self) -> List[str]:
        """Command list needed! """

    @property
    @abstractmethod
    def authors(self) -> List[str]:
        """Authors list needed! """

    @property
    @abstractmethod
    def about(self) -> str:
        """about string needed! """

    @property
    @abstractmethod
    def description(self) -> str:
        """description string needed! """

    @property
    @abstractmethod
    def state(self) -> bool:
        """state flag needed! """

    @abstractmethod
    def set_handlers(self, bot: telebot.TeleBot):
        """Message handlers need to be set! """

    def detailed_function_description(self) -> str:
        """Detailed information description of the bot function"""
        txt = self.about + " - " +self.description
        return txt
