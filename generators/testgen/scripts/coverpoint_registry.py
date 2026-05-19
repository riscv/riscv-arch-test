# coverpoint_registry.py

from collections.abc import Callable
from typing import Any
import importlib
import pkgutil

REGISTRY: dict[str, Callable[..., Any]] = {}

def register(tag: str):
    """Decorator to register a function under a tag."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if tag in REGISTRY:
            raise ValueError(f"Duplicate registration for tag '{tag}'")
        REGISTRY[tag] = func
        return func
    return decorator

def import_all_modules(package):
    """
    Import every module in a package so decorators execute and register functions.
    Example: import_all_modules(handlers)
    """
    for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
        if is_pkg:
            continue  # skip subpackages for now (or recurse if you want)
        importlib.import_module(f"{package.__name__}.{module_name}")
