##################################
# priv/registry.py
#
# Privileged test generator registry with automatic discovery.
# jcarlin@hmc.edu Jan 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Privileged test generator registry with automatic discovery."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from testgen.data.state import TestData
from testgen.discovery import discover_and_import_modules
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


@dataclass
class PrivTestRegistryEntry:
    """Metadata for a registered privileged test generator."""

    generator: PrivTestGenerator
    extra_defines: list[str] = field(default_factory=list)
    required_extensions: list[str] | None = None
    march_extensions: list[str] | None = None
    params: list[str] | None = None


# Registry: dict mapping testsuite name to its registry entry
_PRIV_TEST_GENERATORS: dict[str, PrivTestRegistryEntry] = {}


def add_priv_test_generator(
    testsuite: str,
    *,
    extra_defines: list[str] | None = None,
    required_extensions: list[str] | None = None,
    march_extensions: list[str] | None = None,
    params: list[str] | None = None,
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
        params: Optional list of parameter constraints for the test (e.g., ["NUM_PMP_ENTRIES: '>=16'"]).
                These are included in the test YAML header for test selection.
    """

    def decorator(func: PrivTestGenerator) -> PrivTestGenerator:
        _PRIV_TEST_GENERATORS[testsuite] = PrivTestRegistryEntry(
            generator=func,
            extra_defines=extra_defines or [],
            required_extensions=required_extensions,
            march_extensions=march_extensions,
            params=params,
        )
        return func

    return decorator


def _get_entry(testsuite: str) -> PrivTestRegistryEntry:
    """Get the registry entry for a testsuite, raising a helpful error if not found."""
    if testsuite not in _PRIV_TEST_GENERATORS:
        raise MissingPrivGeneratorError(testsuite, list(_PRIV_TEST_GENERATORS.keys()))
    return _PRIV_TEST_GENERATORS[testsuite]


def get_priv_test_extensions() -> list[str]:
    """Get list of all registered privileged test extensions."""
    return list(_PRIV_TEST_GENERATORS.keys())


def get_priv_test_generator(testsuite: str) -> PrivTestGenerator:
    """Get the priv test generator function for a testsuite."""
    return _get_entry(testsuite).generator


def get_priv_test_defines(testsuite: str) -> list[str]:
    """Get the extra_defines for a priv testsuite."""
    return _get_entry(testsuite).extra_defines


def get_priv_test_required_extensions(testsuite: str) -> list[str] | None:
    """Get the required RISC-V extensions for a priv testsuite."""
    return _get_entry(testsuite).required_extensions


def get_priv_test_march_extensions(testsuite: str) -> list[str] | None:
    """Get the march extensions for a priv testsuite, if explicitly set."""
    return _get_entry(testsuite).march_extensions


def get_priv_test_params(testsuite: str) -> list[str] | None:
    """Get the parameter constraints for a priv testsuite."""
    return _get_entry(testsuite).params


# Discover and import priv test generators at module load
discover_and_import_modules(Path(__file__).parent / "extensions", "testgen.priv.extensions")
