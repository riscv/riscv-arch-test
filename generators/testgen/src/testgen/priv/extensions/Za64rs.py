##################################
# priv/extensions/Za64rs.py
#
# Za64rs privileged extension test generator.
# Written:  Ammarah Wakeel  email:ammarahwakeel9@gmail.com (UET, April 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

"""Za64rs extension test generator.

Reservation sets are contiguous, naturally aligned, and at most 64 bytes.
An SC outside the aligned 64-byte block that contains the LR must fail.
"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

# scratch is 256-byte aligned and 264 bytes. scratch+64 is the block under test, so
# the word before it and the first word of the next block both stay inside scratch.
_BLOCK_BASE = 64
_COVERGROUP = "Za64rs_cg"


def _neighbor_tests(
    test_data: TestData,
    *,
    width: str,
    coverpoint: str,
    step: int,
    data_imm: str,
) -> list[str]:
    """LR anywhere in the block. SC at the next block and at the last access of the previous block."""
    base, lr_addr, sc_addr, src, dest = test_data.int_regs.get_registers(5)
    store = "sw" if width == "w" else "sd"
    load = "lw" if width == "w" else "ld"
    # +step is the first access of the next block. -step is the last access of the previous block.
    sc_offsets = ((_BLOCK_BASE, "next"), (-step, "prev"))
    lines = [
        comment_banner(
            coverpoint,
            f"Za64rs: lr.{width} anywhere in a naturally aligned 64-byte block.\n"
            f"sc.{width} at the next block and the previous block must fail, and must not store.",
        ),
        "",
        f"LA(x{base}, scratch)",
        f"addi x{base}, x{base}, {_BLOCK_BASE}",
        "",
    ]
    for lr_off in range(0, _BLOCK_BASE, step):
        for sc_off, side in sc_offsets:
            label = test_data.add_testcase(f"lr{lr_off}_{side}", coverpoint, _COVERGROUP)
            lines.extend(
                [
                    f"# lr.{width} at block+{lr_off}; sc.{width} at block{sc_off:+d} ({side} block)",
                    # ~data flips every bit this SC would write, so a store cannot leave the canary in place.
                    f"LI(x{src}, {data_imm})",
                    f"xori x{src}, x{src}, -1",
                    f"{store} x{src}, {sc_off}(x{base})",
                    f"xori x{src}, x{src}, -1",
                    f"addi x{lr_addr}, x{base}, {lr_off}",
                    f"addi x{sc_addr}, x{base}, {sc_off}",
                    f"lr.{width} x0, (x{lr_addr})",
                    label,
                    f"sc.{width} x{dest}, x{src}, (x{sc_addr})",
                    write_sigupd(dest, test_data),
                    f"{load} x{dest}, {sc_off}(x{base})",
                    write_sigupd(dest, test_data),
                    "",
                ]
            )
    test_data.int_regs.return_registers([base, lr_addr, sc_addr, src, dest])
    return lines


def _generate_za64rs_tests(test_data: TestData) -> list[str]:
    lines = _neighbor_tests(
        test_data,
        width="w",
        coverpoint="cp_za64rs",
        step=4,
        data_imm="0xA5A5A5A5",
    )
    lines.append("#if __riscv_xlen == 64")
    lines.extend(
        _neighbor_tests(
            test_data,
            width="d",
            coverpoint="cp_za64rs_d",
            step=8,
            data_imm="0xA5A5A5A5A5A5A5A5",
        )
    )
    lines.extend(["#endif", ""])
    return lines


@add_priv_test_generator(
    "Za64rs",
    required_extensions=["Zalrsc", "Za64rs"],
)
def make_za64rs(test_data: TestData) -> list[TestChunk]:
    """Generate tests for the Za64rs reservation-set size extension."""
    chunk = test_data.begin_test_chunk()
    chunk.code.extend(_generate_za64rs_tests(test_data))
    return [test_data.end_test_chunk()]
