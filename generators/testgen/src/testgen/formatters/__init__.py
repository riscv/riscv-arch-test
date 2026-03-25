# testgen/formatters/__init__.py
"""Instruction formatters with automatic discovery."""

from testgen.formatters.params import generate_random_params
from testgen.formatters.registry import (
    InstructionTypeConfig,
    add_instruction_formatter,
    format_instruction,
    format_single_testcase,
    get_instr_type_config,
)

__all__ = [
    "InstructionTypeConfig",
    "add_instruction_formatter",
    "format_instruction",
    "format_single_testcase",
    "generate_random_params",
    "get_instr_type_config",
]
