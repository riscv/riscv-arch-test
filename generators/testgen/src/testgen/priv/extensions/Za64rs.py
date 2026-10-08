##################################
# priv/extensions/Za64rs.py
#
# Za64rs privileged extension test generator.
# Written:  Ammarah Wakeel  email:ammarahwakeel9@gmail.com (UET, April 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

"""Za64rs extension test generator.
Reservation sets are contiguous, naturally aligned, and at most 64 bytes.
"""

from testgen.asm.helpers import comment_banner, lrsc_retry_loop, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator


def _generate_za64rs_tests(test_data: TestData) -> list[str]:
    covergroup = "Za64rs_cg"
    coverpoint = "cp_za64rs"

    base_reg, src_reg, dest_reg, temp_reg, retry_reg = test_data.int_regs.get_registers(5)

    lines = [
        comment_banner(
            coverpoint,
            "Za64rs: Reservation set size test",
        ),
        "",
        f"LA(x{base_reg}, scratch)",
        f"LI(x{src_reg}, 0xA5A5A5A5)",
        "",
    ]

    for offset in range(0, 65, 4):
        binname = f"offset_{offset}"
        label_line = test_data.add_testcase(binname, coverpoint, covergroup)
        lr_sc = [
            f"lr.w x{dest_reg}, (x{base_reg})",
            label_line,
            f"sc.w x{dest_reg}, x{src_reg}, (x{temp_reg})",
        ]
        # Offsets 0-60 can lie in the LR's reservation set, so the sc.w there may succeed.
        # Za64rs puts offset 64 outside it, so that sc.w must fail and needs no retry.
        if offset < 64:
            retry_start, retry_end = lrsc_retry_loop(test_data.current_testcase_label, retry_reg, dest_reg)
            lr_sc = [*retry_start, *lr_sc, *retry_end]
        lines.extend(
            [
                f"# Za64rs: sc.w at offset={offset} within reservation set",
                f"addi x{temp_reg}, x{base_reg}, {offset}",
                *lr_sc,
                write_sigupd(dest_reg, test_data),
                "",
            ]
        )

    test_data.int_regs.return_registers([base_reg, src_reg, dest_reg, temp_reg, retry_reg])
    return lines


@add_priv_test_generator(
    "Za64rs",
    required_extensions=["Zalrsc", "Za64rs"],
)
def make_za64rs(test_data: TestData) -> list[TestChunk]:
    """Generate tests for Za64rs reservation-set size extension."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()
    tc.code.extend(_generate_za64rs_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
