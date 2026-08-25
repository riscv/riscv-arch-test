##################################
# asm/sections.py
#
# Assembly data section generation.
# jcarlin@hmc.edu 5 Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Assembly data section generation."""

from testgen.asm.helpers import to_hex
from testgen.constants import VLEN_MAX
from testgen.data.random import random_int


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
    return "\n".join(data_strings)


def generate_vector_data_section(vector_data_labels: list[tuple[str, list[int], int]]) -> str:
    """
    Generate the .data section containing all vector data, aligned to eew

    Args:
        vector_data_labels: List of triples (label, data, eew) containing the vector data

    Returns:
        Assembly code for the .data section
    """
    lines: list[str] = []
    seen_labels: set[str] = set()

    for label, data, eew in vector_data_labels:
        if label in seen_labels:
            continue
        seen_labels.add(label)

        directives = {8: ".byte", 16: ".short", 32: ".word", 64: ".dword"}
        directive = directives[eew]

        lines.append(f".balign {eew // 8}")

        if label == "vector_ls_random_base":
            lines.extend(generate_vector_ls_random_base(eew))
            continue

        lines.append(f"{label}:")
        for value in data:
            hex_value = to_hex(value, eew)
            lines.append(f"{directive} {hex_value}")

    return "\n".join(lines)


def generate_vector_ls_random_base(eew: int) -> list[str]:
    """
    Generates a vector load-store base and header label, able to fit 8*vlmax bytes going forward
    to cover all possible lmul and segment combinations, and 2*vlmax bytes going backwards for the
    strided load-store instructions.

    TODO: Make this customizable by instruction type & cut down on the number of elements generated
    as this is probably too many
    """

    lines = ["vector_ls_random_header:"]
    directives = {8: ".byte", 16: ".short", 32: ".word", 64: ".dword"}
    directive = directives[eew]

    for i in range(2 * VLEN_MAX):
        value = random_int(eew)
        hex_value = to_hex(value, eew)
        lines.append(f"{directive} {hex_value}")

    lines.append("vector_ls_random_base:")
    for i in range(8 * VLEN_MAX):
        value = random_int(eew)
        hex_value = to_hex(value, eew)
        lines.append(f"{directive} {hex_value}")

    return lines
