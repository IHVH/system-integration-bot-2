"""The module contains tests for checking atomic functions"""

import unittest
from bot_func_abc import AtomicBotFunctionABC
from load_atomic import load_atomic_functions
from app import _START_COMANDS

class TestTeleBot(unittest.TestCase):
    """Unittest test telebot atomic functions"""

    def test_class_inherit(self):
        """Check what is inherited from the required class"""
        atom_functions_list = load_atomic_functions()
        for funct in atom_functions_list:
            message = "Function class must be inherited from AtomicBotFunctionABC!"
            self.assertIs(type(funct).__base__, AtomicBotFunctionABC, msg=message)

    def test_command_count(self):
        """Checks that an atomic function contains at least one command"""
        atom_functions_list = load_atomic_functions()
        for funct in atom_functions_list:
            class_name = funct.__class__.__name__
            message = f"{class_name} - the atomic function must contain at least one command!"
            self.assertGreaterEqual(len(funct.commands), 1, msg=message)

    def test_unique_command(self):
        """Checks that an atomic function contains unique commands"""
        commands = _START_COMANDS
        atom_functions_list = load_atomic_functions()
        for funct in atom_functions_list:
            for cmd in funct.commands:
                message = f"Atomic function must contain unique commands! command={cmd}"
                self.assertFalse(cmd in commands, msg=message)
                commands.append(cmd)

    def test_authors_count(self):
        """Checks that an atomic function contains at least one author"""
        atom_functions_list = load_atomic_functions()
        for funct in atom_functions_list:
            class_name = funct.__class__.__name__
            message = f"{class_name} - the atomic function must contain at least one author!"
            self.assertGreaterEqual(len(funct.authors), 1, msg=message)

    def test_about_min_len(self):
        """Checks that an atomic function about text min lenght"""
        atom_functions_list = load_atomic_functions()
        for funct in atom_functions_list:
            lenght = 10
            class_name = funct.__class__.__name__
            message = (
                f"{class_name} - the atomic function must contain a field about"
                f"with a minimum length of {lenght} characters!")
            self.assertGreaterEqual(len(funct.about), lenght, msg=message)

    def test_about_max_len(self):
        """Checks that an atomic function about text max lenght"""
        atom_functions_list = load_atomic_functions()
        for funct in atom_functions_list:
            lenght = 30
            class_name = funct.__class__.__name__
            message = (
                f"{class_name} - the atomic function must contain a field about"
                f"with a maximum length of {lenght} characters!")
            self.assertLessEqual(len(funct.about), lenght, msg=message)

    def test_description_min_len(self):
        """Checks that an atomic function description text min lenght"""
        atom_functions_list = load_atomic_functions()
        for funct in atom_functions_list:
            lenght = 100
            class_name = funct.__class__.__name__
            message = (
                f"{class_name} - the atomic function must contain a field description"
                f"with a minimum length of {lenght} characters!")
            self.assertGreaterEqual(len(funct.description), lenght, msg=message)

    def test_description_max_len(self):
        """Checks that an atomic function description text max lenght"""
        atom_functions_list = load_atomic_functions()
        for funct in atom_functions_list:
            lenght = 500
            class_name = funct.__class__.__name__
            message = (
                f"{class_name} - the atomic function must contain a field description"
                f"with a maximum length of {lenght} characters!")
            self.assertLessEqual(len(funct.description), lenght, msg=message)


if __name__ == '__main__':
    unittest.main()
