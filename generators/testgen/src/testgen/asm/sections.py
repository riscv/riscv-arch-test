##################################
# asm/sections.py
#
# Assembly data section generation.
# jcarlin@hmc.edu 5 Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Assembly data section generation."""

from testgen.asm.helpers import to_hex


def generate_test_data_section(data_values: list[int], xlen: int, flen: int) -> str:
    """
    Generate the .data section containing all test values.

    Args:
        data_values: List of integer values for the data section
        xlen: Target XLEN (32 or 64)
        flen: Target FLEN (0, 32, or 64)

    Returns:
        Assembly code for the .data section
    """
    lines: list[str] = []

    # Use .word for 32-bit, .dword for 64-bit
    data_size = max(xlen, flen)
    directive = ".word" if data_size == 32 else ".dword"  # TODO: handle Q extension

    for value in data_values:
        hex_value = to_hex(value, data_size)
        lines.append(f"{directive} {hex_value}")

    return "\n".join(lines)


def generate_test_string_section(data_strings: list[str]) -> str:
    """
    Generate the .data section containing all test strings.

    Args:
        data_strings: List of debug strings for the data section

    Returns:
        Assembly code for the .data section
    """
    lines: list[str] = ['canary_mismatch: .string "Testcase signature canary mismatch!"']
    lines.extend(data_strings)

    return "\n".join(lines)
