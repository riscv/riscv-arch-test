##################################
# priv/registry.py
#
# Privileged test generator registry with automatic discovery.
# jcarlin@hmc.edu Jan 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Privileged test generator registry with automatic discovery."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from testgen.constants import TESTCASES_PER_PRIV_FILE
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.discovery import discover_and_import_modules
from testgen.exceptions import MissingRegistryItemError

# Type alias for privileged test generators
PrivTestGenerator = Callable[[TestData], Sequence[TestChunk]]


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
    generator_name: str
    extra_defines: list[str] = field(default_factory=list)
    required_extensions: list[str | list[str]] | None = None
    march_extensions: list[str] | None = None
    params: list[str] | None = None
    testcases_per_file: int = TESTCASES_PER_PRIV_FILE


# Registry: dict mapping each testsuite name to one or more generator entries
_PRIV_TEST_GENERATORS: dict[str, list[PrivTestRegistryEntry]] = {}


def add_priv_test_generator(
    testsuite: str,
    *,
    name: str | None = None,
    extra_defines: list[str] | None = None,
    required_extensions: list[str | list[str]] | None = None,
    march_extensions: list[str] | None = None,
    params: list[str] | None = None,
    testcases_per_file: int = TESTCASES_PER_PRIV_FILE,
) -> Callable[[PrivTestGenerator], PrivTestGenerator]:
    """Return a decorator that registers one privileged test generator."""

    def decorator(func: PrivTestGenerator) -> PrivTestGenerator:
        entry = PrivTestRegistryEntry(
            generator=func,
            generator_name=name or func.__name__,
            extra_defines=extra_defines or [],
            required_extensions=required_extensions,
            march_extensions=march_extensions,
            params=params,
            testcases_per_file=testcases_per_file,
        )
        _PRIV_TEST_GENERATORS.setdefault(testsuite, []).append(entry)
        return func

    return decorator


def get_priv_test_suites() -> list[str]:
    """Get the names of all registered privileged test suites."""
    return list(_PRIV_TEST_GENERATORS)


def get_priv_test_generators(testsuite: str) -> list[PrivTestRegistryEntry]:
    """Get all generator entries for a privileged testsuite."""
    if testsuite not in _PRIV_TEST_GENERATORS:
        raise MissingPrivGeneratorError(testsuite, list(_PRIV_TEST_GENERATORS))
    return _PRIV_TEST_GENERATORS[testsuite]


# Discover and import priv test generators at module load
discover_and_import_modules(Path(__file__).parent / "extensions", "testgen.priv.extensions")
