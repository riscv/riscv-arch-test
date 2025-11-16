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

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData

# Type alias for instruction formatter functions
InstructionFormatter = Callable[[str, TestData, InstructionParams], tuple[list[str], list[str], list[str]]]


@dataclass
class InstructionTypeConfig:
    """Configuration for an instruction type."""

    formatter: InstructionFormatter
    required_params: set[str] | None = None
    reg_range: Iterable[int] | None = None
    imm_bits: int | str | None = None  # int or "xlen"/"xlen_log2"/etc.
    imm_range: tuple[int, int] | None = None  # Explicit (min, max) range
    imm_signed: bool = True
    imm_nonzero: bool = False


# Registry: dict mapping instruction type to its configuration
_INSTRUCTION_CONFIGS: dict[str, InstructionTypeConfig] = {}


def add_instruction_formatter(
    instr_type: str,
    *,
    required_params: set[str] | None = None,
    reg_range: Iterable[int] | None = None,
    imm_bits: int | str | None = None,
    imm_range: tuple[int, int] | None = None,
    imm_signed: bool = True,
    imm_nonzero: bool = False,
) -> Callable[[InstructionFormatter], InstructionFormatter]:
    """
    Decorator to register an instruction formatter for a given instruction type.

    Args:
        instr_type: The instruction type string (e.g., "R", "I", "S")
        required_params: Set of parameter names required by this instruction type (e.g., {"rd", "rs1", "rs1val", "immval"})
        reg_range: Allowed register range for this type (e.g., range(8, 16) for compressed instructions)
        imm_bits: Number of bits for immediate values - can be an integer (e.g., 12 for I-type, 5 for shifts)
            or a string expression "xlen_log2" for xlen-dependent shift widths (5 for RV32, 6 for RV64)
        imm_range: Explicit (min, max) value range for immediate (e.g., (0, 10) for IR type rnum field)
        imm_signed: Whether immediate values should be signed (default: True)
        imm_nonzero: If True, exclude zero from generated immediate values (e.g., for compressed instructions)
    """

    def decorator(formatter_func: InstructionFormatter) -> InstructionFormatter:
        config = InstructionTypeConfig(
            formatter=formatter_func,
            required_params=required_params,
            reg_range=reg_range,
            imm_bits=imm_bits,
            imm_range=imm_range,
            imm_signed=imm_signed,
            imm_nonzero=imm_nonzero,
        )
        _INSTRUCTION_CONFIGS[instr_type] = config
        return formatter_func

    return decorator


def get_type_config(instr_type: str) -> InstructionTypeConfig:
    """Get the complete configuration for an instruction type."""
    return _INSTRUCTION_CONFIGS[instr_type]


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


def _select_instruction_formatter(instr_name: str, instr_type: str) -> InstructionFormatter:
    """Select the appropriate instruction formatter based on instruction type (exact match)."""
    config = _INSTRUCTION_CONFIGS.get(instr_type)
    if config is not None:
        return config.formatter
    raise ValueError(
        f"No instruction formatter found for instruction type: {instr_type}. Needed by instruction: {instr_name}."
    )


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
    formatter = _select_instruction_formatter(instr_name, instr_type)
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
