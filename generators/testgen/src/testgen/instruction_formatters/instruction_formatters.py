##################################
# instruction_formatters.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Instruction formatter registry with automatic discovery."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Literal

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.utils.exceptions import MissingInstructionFormatterError

# Type alias for instruction formatter functions
# The formatter function takes:
# - instr_name: str
# - test_data: TestData
# - params: InstructionParams
# and returns a tuple of three lists of strings: (setup_lines, test_lines, check_lines)
InstructionFormatter = Callable[[str, TestData, InstructionParams], tuple[list[str], list[str], list[str]]]


@dataclass
class InstructionTypeConfig:
    """Configuration for an instruction type."""

    required_params: set[str] | None = None
    reg_range: Iterable[int] | None = None
    imm_bits: int | Literal["xlen", "xlen_log2", "flen", "flen_log2"] | None = None
    imm_range: tuple[int, int] | None = None  # Explicit (min, max) range
    imm_signed: bool = True
    imm_nonzero: bool = False


# Registry: dict mapping instruction type to (instruction_formatter, instruction_type_config)
_INSTRUCTION_CONFIGS: dict[str, tuple[InstructionFormatter, InstructionTypeConfig]] = {}


def add_instruction_formatter(
    instr_type: str, instruction_type_config: InstructionTypeConfig
) -> Callable[[InstructionFormatter], InstructionFormatter]:
    """
    Decorator to register an instruction formatter for a given instruction type.

    Args:
        instr_type: The instruction type string (e.g., "R", "I", "S")
        instruction_type_config: Configuration for the instruction type specifying
                                 required params, reg ranges, imm ranges, etc.
    """

    def decorator(formatter_func: InstructionFormatter) -> InstructionFormatter:
        _INSTRUCTION_CONFIGS[instr_type] = (formatter_func, instruction_type_config)
        return formatter_func

    return decorator


def get_instr_type_config(instr_type: str) -> InstructionTypeConfig:
    """Get the configuration for an instruction type."""
    if instr_type not in _INSTRUCTION_CONFIGS:
        raise MissingInstructionFormatterError(instr_type, list(_INSTRUCTION_CONFIGS.keys()))
    return _INSTRUCTION_CONFIGS[instr_type][1]  # Return only the InstructionTypeConfig


def get_instr_type_formatter(instr_type: str) -> InstructionFormatter:
    """Get the instruction formatter function for an instruction type."""
    if instr_type not in _INSTRUCTION_CONFIGS:
        raise MissingInstructionFormatterError(instr_type, list(_INSTRUCTION_CONFIGS.keys()))
    return _INSTRUCTION_CONFIGS[instr_type][0]  # Return only the InstructionFormatter


def _discover_and_import_instruction_formatters() -> None:
    """Auto-import all instruction formatter modules to trigger decorator registration."""
    package_dir = Path(__file__).parent

    # Recursively import all Python files except instruction_formatters.py and files starting with _
    for module_file in package_dir.rglob("*.py"):
        if module_file.stem != "instruction_formatters" and not module_file.stem.startswith("_"):
            # Convert file path to module path
            relative_path = module_file.relative_to(package_dir)
            module_parts = [*list(relative_path.parts[:-1]), relative_path.stem]
            module_name = "testgen.instruction_formatters." + ".".join(module_parts)
            import_module(module_name)


# Discover and import instruction formatters at module load
_discover_and_import_instruction_formatters()


def format_instruction(
    instr_name: str, instr_type: str, test_data: TestData, params: InstructionParams
) -> tuple[str, str, str]:
    """
    Generate instruction test (setup, test, check).

    This generates register setup and the instruction itself, with signature update.
    Used when generating instruction sequences where each instruction result is captured.

    Args:
        instr_name: Instruction mnemonic
        instr_type: Instruction type code
        test_data: Test data context
        params: Instruction parameters

    Returns:
        Tuple of (setup_code, test_code, check_code) as strings
    """
    formatter = get_instr_type_formatter(instr_type)
    setup, test, check = formatter(instr_name, test_data, params)
    return "\n".join(setup), "\n".join(test), "\n".join(check)


def format_single_test(
    instr_name: str, instr_type: str, test_data: TestData, params: InstructionParams, desc: str
) -> str:
    """
    Generate a complete single-instruction test with setup and signature update.

    This is the main entry point for generating a full test case including:
    - Test description comment
    - Register initialization
    - The instruction itself
    - Signature update

    Args:
        instr_name: Instruction mnemonic
        instr_type: Instruction type code
        test_data: Test data context
        params: Instruction parameters
        desc: Test description (e.g., "cp_rd (Test destination rd = x5)")

    Returns:
        Complete test case as a string
    """
    test_lines = [f"# Testcase {desc}"]

    # Add test and signature update lines
    setup, test, check = format_instruction(instr_name, instr_type, test_data, params)
    test_lines.extend([setup, test, check])

    return "\n".join(test_lines)
