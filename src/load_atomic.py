"""The module contains the function of reading and loading atomic modules into a list"""

import inspect
import os
from pathlib import Path
from typing import List
from bot_func_abc import AtomicBotFunctionABC

def load_atomic_functions(func_dir:str = "functions",
atomic_dir:str = "atomic") -> List[AtomicBotFunctionABC]:
    """Loading atomic functions into a list"""
    atomic_func_path = Path.cwd() / func_dir / atomic_dir
    suffix = ".py"
    lst = os.listdir(atomic_func_path)
    function_objects: List[AtomicBotFunctionABC] = []
    for fn_str in lst:
        if suffix in fn_str:
            module_name = fn_str.removesuffix(suffix)
            module = __import__(f"{func_dir}.{atomic_dir}.{module_name}", fromlist = ["*"])
            for name, cls in inspect.getmembers(module):
                if inspect.isclass(cls) and cls.__base__ is AtomicBotFunctionABC:
                    obj: AtomicBotFunctionABC = cls()
                    function_objects.append(obj)
                    print(f"{name} - Added!")
    return function_objects
