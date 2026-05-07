# priv_coverpoint_registry.py

import importlib
import pkgutil
from collections.abc import Callable
from types import ModuleType
from typing import Any

PRIV_REGISTRY: dict[str, Callable[..., Any]] = {}


def register(tag: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to register a priv coverpoint function under a tag."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if tag in PRIV_REGISTRY:
            raise ValueError(f"Duplicate registration for tag '{tag}'")
        PRIV_REGISTRY[tag] = func
        return func

    return decorator


def import_all_modules(package: ModuleType) -> None:
    """Import every module in a package so decorators execute and register functions."""
    for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
        if is_pkg:
            continue
        importlib.import_module(f"{package.__name__}.{module_name}")
