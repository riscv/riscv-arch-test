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
from testgen.exceptions import MissingRegistryItemError

# Type alias for priv test generator functions
PrivTestGenerator = Callable[[TestData], list[str]]


class MissingPrivGeneratorError(MissingRegistryItemError):
    """Raised when no priv test generator is registered for a given testsuite."""

    def __init__(self, testsuite: str, available_extensions: list[str] | None = None) -> None:
        registry_location = Path(__file__).parent / "extensions"
        super().__init__(
            testsuite,
            available_extensions,
            item_type="privileged test generator",
            registry_location=registry_location,
        )
        self.testsuite = testsuite


# Registry: dict mapping testsuite name to (priv_test_generator, extra_defines, required_extensions, march_extensions)
_PRIV_TEST_GENERATORS: dict[str, tuple[PrivTestGenerator, list[str], list[str] | None, list[str] | None]] = {}


def add_priv_test_generator(
    testsuite: str,
    *,
    extra_defines: list[str] | None = None,
    required_extensions: list[str] | None = None,
    march_extensions: list[str] | None = None,
) -> Callable[[PrivTestGenerator], PrivTestGenerator]:
    """
    Decorator to register a privileged test generator.

    Args:
        testsuite: Testsuite name (e.g., "ExceptionsSm")
        extra_defines: List of extra #define statements for the test header.
                       Trap handlers are added automatically based on extensions.
        required_extensions: List of RISC-V extensions required for the test (e.g., ["Sm", "Zicsr"]).
                             Used for generating the march string and header defines.
        march_extensions: Optional list of extensions to use for the march string.
                          If None, march is built from required_extensions.
    """
    if extra_defines is None:
        extra_defines = []

    def decorator(func: PrivTestGenerator) -> PrivTestGenerator:
        _PRIV_TEST_GENERATORS[testsuite] = (func, extra_defines, required_extensions, march_extensions)
        return func

    return decorator


def get_priv_test_extensions() -> list[str]:
    """Get list of all registered privileged test extensions."""
    return list(_PRIV_TEST_GENERATORS.keys())


def get_priv_test_generator(testsuite: str) -> PrivTestGenerator:
    """Get the priv test generator function for an testsuite."""
    if testsuite not in _PRIV_TEST_GENERATORS:
        raise MissingPrivGeneratorError(testsuite, list(_PRIV_TEST_GENERATORS.keys()))
    return _PRIV_TEST_GENERATORS[testsuite][0]


def get_priv_test_defines(testsuite: str) -> list[str]:
    """Get the extra_defines for a priv testsuite."""
    if testsuite not in _PRIV_TEST_GENERATORS:
        raise MissingPrivGeneratorError(testsuite, list(_PRIV_TEST_GENERATORS.keys()))
    return _PRIV_TEST_GENERATORS[testsuite][1]


def get_priv_test_required_extensions(testsuite: str) -> list[str] | None:
    """Get the required RISC-V extensions for a priv testsuite."""
    if testsuite not in _PRIV_TEST_GENERATORS:
        raise MissingPrivGeneratorError(testsuite, list(_PRIV_TEST_GENERATORS.keys()))
    return _PRIV_TEST_GENERATORS[testsuite][2]


def get_priv_test_march_extensions(testsuite: str) -> list[str] | None:
    """Get the march extensions for a priv testsuite, if explicitly set."""
    if testsuite not in _PRIV_TEST_GENERATORS:
        raise MissingPrivGeneratorError(testsuite, list(_PRIV_TEST_GENERATORS.keys()))
    return _PRIV_TEST_GENERATORS[testsuite][3]


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
