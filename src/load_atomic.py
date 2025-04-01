"""The module contains the function of reading and loading atomic modules into a list"""

import inspect
import os
from pathlib import Path
from typing import List
from bot_func_abc import AtomicBotFunctionABC

def load_atomic_functions(
    func_dir: str = "functions",
    atomic_dir: str = "atomic"
) -> List[AtomicBotFunctionABC]:
    """Loading atomic functions into a list"""
    atomic_func_path = Path.cwd() / "src" / func_dir / atomic_dir
    suffix = ".py"
    lst = os.listdir(atomic_func_path)
    function_objects: List[AtomicBotFunctionABC] = []

    print(f"Looking for atomic functions in: {atomic_func_path}")
    print(f"Files found: {lst}")

    for fn_str in lst:
        if suffix in fn_str:
            module_name = fn_str.removesuffix(suffix)
            print(f"Attempting to load module: {module_name}")
            try:
                module = __import__(f"{func_dir}.{atomic_dir}.{module_name}", fromlist=["*"])
                for name, cls in inspect.getmembers(module):
                    if inspect.isclass(cls) and cls.__base__ is AtomicBotFunctionABC:
                        obj: AtomicBotFunctionABC = cls()
                        function_objects.append(obj)
                        print(f"{name} - Added!")
            except ImportError as e:  # Уточняем тип исключения
                print(f"Error loading module {module_name}: {e}")

    print(f"Total functions loaded: {len(function_objects)}")
    return function_objects
