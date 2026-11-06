##################################
# priv/extensions/Zic64b.py
#
# Zic64b privileged extension test generator.
# Ammarah Wakeel  email:ammarahwakeel9@gmail.com (UET, April 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

"""Zic64b extension test generator.

Zic64b: cache blocks are 64 bytes and naturally aligned.
Zicboz: cbo.zero writes zeros to every byte of the block that contains rs1.
"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

# scratch is 256-byte aligned and 264 bytes long. scratch+128 keeps rs1[6:0]
# equal to the logical offset and leaves one guard byte on either side of two blocks.
_WORK_BASE = 128
_BLOCK = 64
# 0 and 63 are the ends of one block, 1 is an unaligned byte inside it, and 64 is the next block.
_OFFSETS = (0, 1, 63, 64)
_COVERGROUP = "Zic64b_cg"
_COVERPOINT = "cp_zic64b"


def _fill(base: int, val: int, start: int, stop: int) -> list[str]:
    """Store 0xFF to each byte in [start, stop). ``start`` may be negative."""
    lines = [f"LI(x{val}, 0xFF)"]
    lines.extend(f"sb x{val}, {offset}(x{base})" for offset in range(start, stop))
    return lines


def _sample(test_data: TestData, base: int, val: int, offsets: list[int]) -> list[str]:
    lines: list[str] = []
    for offset in offsets:
        lines.append(f"lbu x{val}, {offset}(x{base})")
        lines.append(write_sigupd(val, test_data))
    return lines


def _generate_zic64b_tests(test_data: TestData) -> list[str]:
    """Check that cbo.zero clears exactly the aligned 64-byte block containing rs1."""
    base, tmp, val = test_data.int_regs.get_registers(3)
    lines = [
        comment_banner(
            _COVERPOINT,
            "Zic64b + Zicboz: cbo.zero clears the naturally aligned 64-byte block containing rs1.\n"
            "work_base = scratch+128. rs1 offsets 0, 1, 63 and 64.\n"
            "Read every byte of the cleared block and the bytes immediately before and after it.",
        ),
        "",
        f"LA(x{base}, scratch)",
        f"addi x{base}, x{base}, {_WORK_BASE}",
        "",
    ]

    for offset in _OFFSETS:
        if offset < _BLOCK:
            zero_lo, zero_hi = 0, _BLOCK - 1
            guard_before, guard_after = -1, _BLOCK
        else:
            zero_lo, zero_hi = _BLOCK, 2 * _BLOCK - 1
            guard_before, guard_after = _BLOCK - 1, 2 * _BLOCK
        lines.extend(_fill(base, val, -1, 2 * _BLOCK + 1))
        lines.extend(
            [
                "",
                f"# rs1 = work_base+{offset}; block bytes [{zero_lo}, {zero_hi}]",
                f"addi x{tmp}, x{base}, {offset}",
                test_data.add_testcase(f"offset_{offset}", _COVERPOINT, _COVERGROUP),
                f"cbo.zero 0(x{tmp})",
                "",
            ]
        )
        lines.extend(
            _sample(
                test_data,
                base,
                val,
                [guard_before, *range(zero_lo, zero_hi + 1), guard_after],
            )
        )
        lines.append("")

    test_data.int_regs.return_registers([base, tmp, val])
    return lines


@add_priv_test_generator(
    "Zic64b",
    required_extensions=["Zicboz", "Zic64b"],
)
def make_zic64b(test_data: TestData) -> list[TestChunk]:
    """Generate the Zic64b cache-block size test."""
    chunk = test_data.begin_test_chunk("Zicboz")
    chunk.code.extend(_generate_zic64b_tests(test_data))
    return [test_data.end_test_chunk()]
