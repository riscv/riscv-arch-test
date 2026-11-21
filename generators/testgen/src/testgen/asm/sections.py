##################################
# asm/sections.py
#
# Assembly data section generation.
# jcarlin@hmc.edu 5 Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Assembly data section generation."""

from testgen.asm.helpers import to_hex
from testgen.constants import VECTOR_DATA_BYTES_PER_LINE, VLEN_MAX
from testgen.data.random import random_int


def generate_test_data_section(data_values: list[int], xlen: int, flen: int, vdsew: int) -> str:
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
    data_size = max(xlen, flen, vdsew)
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

        # Repack into .dword chunks
        if eew == 256:
            data = [(val >> (64 * i)) & (2**64 - 1) for val in data for i in range(4)]
            eew = 64

        directives = {8: ".byte", 16: ".short", 32: ".word", 64: ".dword", 128: ".octa"}
        directive = directives[eew]

        lines.append(f".balign {eew // 8}")

        if label == "vector_ls_random_base":
            lines.extend(generate_vector_ls_random_base(eew))
            continue

        lines.append(f"{label}:")
        lines.extend(pack_data_directives(directive, data, eew))

    return "\n".join(lines)


def pack_data_directives(directive: str, values: list[int], eew: int) -> list[str]:
    """
    Emit values as data directives holding VECTOR_DATA_BYTES_PER_LINE bytes per line. Elements narrower than 64
    bits are combined into little-endian .dword values, which lay out the same bytes in memory with shorter text.
    Elements left over after the last full doubleword keep their own directive.
    """
    if eew >= 64:
        return _data_lines(directive, values, eew)
    per_dword = 64 // eew
    full = len(values) - len(values) % per_dword
    dwords = [
        sum((values[i + k] & ((1 << eew) - 1)) << (k * eew) for k in range(per_dword))
        for i in range(0, full, per_dword)
    ]
    return _data_lines(".dword", dwords, 64) + _data_lines(directive, values[full:], eew)


def _data_lines(directive: str, values: list[int], eew: int) -> list[str]:
    per_line = max(1, VECTOR_DATA_BYTES_PER_LINE * 8 // eew)
    return [
        f"{directive} " + ", ".join(to_hex(value, eew) for value in values[i : i + per_line])
        for i in range(0, len(values), per_line)
    ]


def generate_vector_ls_random_base(eew: int) -> list[str]:
    """
    Generates a vector load-store base and header label, able to fit 8*VLEN_MAX bytes going forward
    to cover all possible lmul and segment combinations, and 2*VLEN_MAX bytes going backwards for the
    strided load-store instructions.

    The random stream always draws 2*VLEN_MAX header and 8*VLEN_MAX base elements so that the emitted
    values do not depend on eew. Only the elements within the byte window are emitted: the last
    elements of the header and the first elements of the base.
    """

    directives = {8: ".byte", 16: ".short", 32: ".word", 64: ".dword"}
    directive = directives[eew]
    eew_bytes = eew // 8

    header = [random_int(eew) for _ in range(2 * VLEN_MAX)]
    base = [random_int(eew) for _ in range(8 * VLEN_MAX)]

    return [
        "vector_ls_random_header:",
        *pack_data_directives(directive, header[len(header) - 2 * VLEN_MAX // eew_bytes :], eew),
        "vector_ls_random_base:",
        *pack_data_directives(directive, base[: 8 * VLEN_MAX // eew_bytes], eew),
    ]
