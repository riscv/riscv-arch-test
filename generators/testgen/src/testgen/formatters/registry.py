##################################
# formatters/registry.py
#
# Instruction formatter registry with automatic discovery.
# jcarlin@hmc.edu Jan 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Instruction formatter registry with automatic discovery."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Literal

from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.exceptions import MissingRegistryItemError

# Type alias for instruction formatter functions
InstructionFormatter = Callable[[str, TestData, InstructionParams], tuple[list[str], list[str], list[str]]]


class MissingInstructionFormatterError(MissingRegistryItemError):
    """Raised when no instruction formatter is registered for a given instruction type."""

    def __init__(self, instr_type: str, available_types: list[str] | None = None) -> None:
        registry_location = Path(__file__).parent / "types"
        super().__init__(
            instr_type,
            available_types,
            item_type="instruction formatter",
            registry_location=registry_location,
        )
        self.instr_type = instr_type


@dataclass
class InstructionTypeConfig:
    """Configuration for an instruction type.

    This dataclass holds metadata about an instruction type needed for parameter
    generation and validation, such as required parameters, register ranges, and
    immediate value constraints.

    Attributes:
        required_params: Set of parameters required for this instruction type (rs1, rdval, immval, etc.).
        reg_range: Iterable of valid register numbers for this instruction type.
        imm_bits: Number of bits for immediates. Can also be "xlen", "xlen_log2", "flen", or "flen_log2".
        imm_range: Explicit (min, max) range for immediate values. Mutually exclusive with imm_bits.
        imm_signed: Whether the immediate value is signed (default: True).
        imm_nonzero: Whether the immediate value must be nonzero (default: False).
        pair_regs: Set of registers that use even register pairs (e.g., {"rd", "rs2"}).
    """

    required_params: set[str] | None = None
    reg_range: Iterable[int] | None = None
    imm_bits: int | Literal["xlen", "xlen_log2", "flen", "flen_log2"] | None = None
    imm_range: tuple[int, int] | None = None  # Explicit (min, max) range
    imm_signed: bool = True
    imm_nonzero: bool = False
    pair_regs: set[str] | None = None  # Registers that use register pairs (e.g., {"rd", "rs2"})


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
    return _INSTRUCTION_CONFIGS[instr_type][1]


def get_instr_type_formatter(instr_type: str) -> InstructionFormatter:
    """Get the instruction formatter function for an instruction type."""
    if instr_type not in _INSTRUCTION_CONFIGS:
        raise MissingInstructionFormatterError(instr_type, list(_INSTRUCTION_CONFIGS.keys()))
    return _INSTRUCTION_CONFIGS[instr_type][0]


def _discover_and_import_formatters() -> None:
    """Auto-import all formatter modules in types/ to trigger decorator registration."""
    types_dir = Path(__file__).parent / "types"

    # Import all Python files in types/ directory
    for module_file in types_dir.rglob("*.py"):
        if not module_file.stem.startswith("_"):
            relative_path = module_file.relative_to(types_dir)
            module_parts = [*list(relative_path.parts[:-1]), relative_path.stem]
            module_name = "testgen.formatters.types." + ".".join(module_parts)
            import_module(module_name)


# Discover and import formatters at module load
_discover_and_import_formatters()


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
    test_lines.extend([setup, f"test_{test_data.test_count}:", test, check])

    return "\n".join(test_lines)
