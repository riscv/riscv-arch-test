##################################
# asm/sections.py
#
# Assembly data section generation.
# jcarlin@hmc.edu 5 Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Assembly data section generation."""

from testgen.asm.helpers import to_hex
from testgen.data.state import TestData


def generate_test_data_section(test_data: TestData) -> str:
    """
    Generate the .data section containing all test values.

    Args:
        test_data: TestData object containing the values to generate

    Returns:
        Assembly code for the .data section
    """
    lines: list[str] = []

    # Use .word for 32-bit, .dword for 64-bit
    data_size = max(test_data.xlen, test_data.flen)
    directive = ".word" if data_size == 32 else ".dword"  # TODO: handle Q extension

    for value in test_data.test_data_values:
        hex_value = to_hex(value, data_size)
        lines.append(f"{directive} {hex_value}")

    return "\n".join(lines)


def generate_test_string_section(test_data: TestData) -> str:
    """
    Generate the .data section containing all test strings.

    Args:
        test_data: TestData object containing the strings to generate

    Returns:
        Assembly code for the .data section
    """
    lines: list[str] = ['canary_mismatch: .string "Testcase signature canary mismatch!"']
    lines.extend(test_data.test_data_strings)

    return "\n".join(lines)
