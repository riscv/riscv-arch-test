# testgen/formatters/__init__.py
"""Instruction formatters with automatic discovery."""

from testgen.formatters.params import generate_random_params
from testgen.formatters.registry import (
    InstructionTypeConfig,
    add_instruction_formatter,
    format_instruction,
    format_single_test,
    get_instr_type_config,
)

__all__ = [
    "InstructionTypeConfig",
    "add_instruction_formatter",
    "format_instruction",
    "format_single_test",
    "generate_random_params",
    "get_instr_type_config",
]
