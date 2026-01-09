##################################
# priv_generators.py
#
# Jordan Carlin jcarlin@hmc.edu Jan 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Privileged test generator registry with automatic discovery."""

from collections.abc import Callable
from importlib import import_module
from pathlib import Path

# from random import seed
from testgen.data.test_config import TestConfig
from testgen.data.test_data import TestData

# from testgen.utils.common import reproducible_hash
from testgen.utils.exceptions import MissingPrivGeneratorError
from testgen.utils.test_writer import write_test_file

# Type alias for priv test generator functions
# The generator function takes:
# - test_data: TestData
# and returns a list of strings (test lines)
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
    return _PRIV_TEST_GENERATORS[extension][0]  # Return only the PrivTestGenerator


def get_priv_test_defines(extension: str) -> list[str]:
    """Get the extra_defines for a priv extension."""
    if extension not in _PRIV_TEST_GENERATORS:
        raise MissingPrivGeneratorError(extension, list(_PRIV_TEST_GENERATORS.keys()))
    return _PRIV_TEST_GENERATORS[extension][1]  # Return only the extra_defines


def _discover_and_import_priv_generators() -> None:
    """Auto-import all priv priv test generator modules to trigger decorator registration."""
    package_dir = Path(__file__).parent

    # Recursively import all Python files except priv_generators.py and files starting with _
    for module_file in package_dir.rglob("*.py"):
        if module_file.stem != "priv_generators" and not module_file.stem.startswith("_"):
            # Convert file path to module path
            relative_path = module_file.relative_to(package_dir)
            module_parts = [*list(relative_path.parts[:-1]), relative_path.stem]
            module_name = "testgen.priv_generators." + ".".join(module_parts)
            import_module(module_name)


# Discover and import priv test generators at module load
_discover_and_import_priv_generators()


def generate_priv_test(extension: str, output_test_dir: Path) -> None:
    """
    Generate tests for a privileged extension.

    Args:
        extension: Extension name (e.g., "Sm")
        output_dir: Base directory to output generated tests
    """

    # Output always goes to priv/<extension>
    output_path = output_test_dir / "priv" / extension
    output_path.mkdir(parents=True, exist_ok=True)

    # Create test configuration - privileged tests are config_dependent and don't have a fixed xlen
    # The xlen=0 indicates this is a multi-xlen test that uses preprocessor conditionals
    test_config = TestConfig(
        xlen=0,  # One test for all XLENs
        flen=0,
        extension=extension,
        E_ext=False,
        config_dependent=True,
    )

    # Create test data
    test_data = TestData(test_config)

    # Generate test body
    priv_test_generator = get_priv_test_generator(extension)
    body_lines = priv_test_generator(test_data)

    print(f"Generating tests for {output_path}")
    write_test_file(
        test_data,
        body_lines,
        output_path,
        extra_defines=get_priv_test_defines(extension),
    )
