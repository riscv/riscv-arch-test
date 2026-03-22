##################################
# coverpoints/registry.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Coverpoint generator registry with automatic discovery."""

from collections.abc import Callable
from importlib import import_module
from pathlib import Path
from random import seed

from testgen.asm.helpers import comment_banner, reproducible_hash
from testgen.constants import SKIP_COVERPOINTS
from testgen.data.state import TestData
from testgen.data.testcase import TestCase
from testgen.exceptions import MissingRegistryItemError

# Type alias for coverpoint generator functions
# The generator function takes:
# - instr_name: str
# - instr_type: str
# - coverpoint: str
# - test_data: TestData
# and returns a list of TestCase objects
CoverpointGenerator = Callable[[str, str, str, TestData], list[TestCase]]


class MissingCoverpointGeneratorError(MissingRegistryItemError):
    """Raised when no coverpoint generator is registered for a given coverpoint."""

    def __init__(self, coverpoint: str, available_patterns: list[str] | None = None) -> None:
        registry_location = Path(__file__).parent
        super().__init__(
            coverpoint,
            available_patterns,
            item_type="coverpoint generator",
            registry_location=registry_location,
        )
        self.coverpoint = coverpoint


# Registry: list of (pattern, generator) tuples sorted by pattern length (longest first)
_COVERPOINT_GENERATORS: list[tuple[str, CoverpointGenerator]] = []


def add_coverpoint_generator(*patterns: str) -> Callable[[CoverpointGenerator], CoverpointGenerator]:
    """
    Decorator to register a generator for one or more coverpoint patterns.

    Args:
        patterns: One or more coverpoint prefixes this generator can process
    """

    def decorator(func: CoverpointGenerator) -> CoverpointGenerator:
        for pattern in patterns:
            # Insert in sorted position (longest patterns first)
            # This ensures the most specific generator is matched
            pattern_len = len(pattern)
            insert_pos = 0
            for i, (existing_pattern, _) in enumerate(_COVERPOINT_GENERATORS):
                if pattern_len > len(existing_pattern):
                    insert_pos = i
                    break
                insert_pos = i + 1
            _COVERPOINT_GENERATORS.insert(insert_pos, (pattern, func))
        return func

    return decorator


def _discover_and_import_coverpoint_generators() -> None:
    """Auto-import all generator modules to trigger decorator registration."""
    current_file = Path(__file__)
    package_dir = current_file.parent

    # Recursively import all Python files except this file and files starting with _
    for module_file in package_dir.rglob("*.py"):
        if module_file.stem != current_file and not module_file.stem.startswith("_"):
            # Convert file path to module path (e.g., special/branch.py -> testgen.coverpoints.special.branch)
            relative_path = module_file.relative_to(package_dir)
            module_parts = [*list(relative_path.parts[:-1]), relative_path.stem]
            module_name = "testgen.coverpoints." + ".".join(module_parts)
            import_module(module_name)


# Discover and import coverpoint generators at module load
_discover_and_import_coverpoint_generators()


def _select_coverpoint_generator(coverpoint: str) -> CoverpointGenerator:
    """Select generator using longest-prefix matching."""
    for pattern, generator in _COVERPOINT_GENERATORS:
        if coverpoint.startswith(pattern):
            return generator
    available_patterns = [pattern for pattern, _ in _COVERPOINT_GENERATORS]
    raise MissingCoverpointGeneratorError(coverpoint, available_patterns)


def generate_tests_for_coverpoint(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestCase]:
    """Generate tests for a specific coverpoint."""
    if coverpoint in SKIP_COVERPOINTS:
        return []

    generator = _select_coverpoint_generator(coverpoint)
    hashval = reproducible_hash(instr_name + coverpoint)
    seed(hashval)
    test_cases = generator(instr_name, instr_type, coverpoint, test_data)

    # Set section banner on first TestCase
    if test_cases:
        test_cases[0].section_header = comment_banner(coverpoint)

    return test_cases
