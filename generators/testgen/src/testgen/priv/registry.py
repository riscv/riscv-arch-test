##################################
# priv/registry.py
#
# Privileged test generator registry with automatic discovery.
# jcarlin@hmc.edu Jan 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Privileged test generator registry with automatic discovery."""

from collections.abc import Callable
from importlib import import_module
from pathlib import Path

from testgen.data.state import TestData
from testgen.exceptions import MissingPrivGeneratorError

# Type alias for priv test generator functions
PrivTestGenerator = Callable[[TestData], list[str]]

# Registry: dict mapping extension name to (priv_test_generator, extra_defines)
_PRIV_TEST_GENERATORS: dict[str, tuple[PrivTestGenerator, list[str]]] = {}


def add_priv_test_generator(
    extension: str,
    *,
    extra_defines: list[str] | None = None,
) -> Callable[[PrivTestGenerator], PrivTestGenerator]:
    """
    Decorator to register a privileged test generator.

    Args:
        extension: Extension name (e.g., "Sm")
        extra_defines: List of extra #define statements for the test header.
                       Trap handlers are added automatically based on extensions.
    """
    if extra_defines is None:
        extra_defines = []

    def decorator(func: PrivTestGenerator) -> PrivTestGenerator:
        _PRIV_TEST_GENERATORS[extension] = (func, extra_defines)
        return func

    return decorator


def get_priv_test_extensions() -> list[str]:
    """Get list of all registered privileged test extensions."""
    return list(_PRIV_TEST_GENERATORS.keys())


def get_priv_test_generator(extension: str) -> PrivTestGenerator:
    """Get the priv test generator function for an extension."""
    if extension not in _PRIV_TEST_GENERATORS:
        raise MissingPrivGeneratorError(extension, list(_PRIV_TEST_GENERATORS.keys()))
    return _PRIV_TEST_GENERATORS[extension][0]


def get_priv_test_defines(extension: str) -> list[str]:
    """Get the extra_defines for a priv extension."""
    if extension not in _PRIV_TEST_GENERATORS:
        raise MissingPrivGeneratorError(extension, list(_PRIV_TEST_GENERATORS.keys()))
    return _PRIV_TEST_GENERATORS[extension][1]


def _discover_and_import_priv_generators() -> None:
    """Auto-import all priv test generator modules to trigger decorator registration."""
    package_dir = Path(__file__).parent / "extensions"

    # Import all Python files in extensions/ that don't start with _
    for module_file in package_dir.rglob("*.py"):
        if not module_file.stem.startswith("_"):
            # Convert file path to module path
            relative_path = module_file.relative_to(package_dir)
            module_parts = [*list(relative_path.parts[:-1]), relative_path.stem]
            module_name = "testgen.priv.extensions." + ".".join(module_parts)
            import_module(module_name)


# Discover and import priv test generators at module load
_discover_and_import_priv_generators()
