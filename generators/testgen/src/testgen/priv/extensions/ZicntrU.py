##################################
# ZicntrU.py
#
# ZicntrU privileged extension test generator.
# ellyu@g.hmc.edu March 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZicntrU extension test generator: counter access from U-mode, with mcounteren written via T-SBI."""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

_COUNTERS = ["cycle", "time", "instret"]


def _read_counter(read_reg: int, i: int) -> list[str]:
    """Read counter i (and its high half on RV32) in U-mode."""
    if i < 3:
        name = _COUNTERS[i]
        return [f"csrr x{read_reg}, {name}", "#if __riscv_xlen == 32", f"csrr x{read_reg}, {name}h", "#endif"]
    return [
        "#ifdef ZIHPM_SUPPORTED",
        f"csrr x{read_reg}, hpmcounter{i} # read from hpmcounter{i} in U-mode",
        "#if __riscv_xlen == 32",
        f"csrr x{read_reg}, hpmcounter{i}h # read from hpmcounter{i}h in U-mode",
        "#endif",
        "#endif",
    ]


def _generate_mcounteren_access_u_tests(test_data: TestData) -> list[str]:
    """Generate mcounteren access u mode tests."""
    covergroup, coverpoint = "ZicntrU_cg", "cp_mcounteren_access_u"

    read_reg, walk_reg, inv_reg = test_data.int_regs.get_registers(3)

    lines = [
        comment_banner(
            coverpoint,
            "Write walking 1s and 0s to mcounteren via T-SBI.  Read from corresponding counter and counterh in U-mode",
        ),
        "",
        f"LI(x{walk_reg}, 1)",
    ]
    for i in range(32):
        lines.extend(
            [
                test_data.add_testcase(f"walking_1_{i}", coverpoint, covergroup),
                tsbi_call(f"csrw mcounteren, x{walk_reg}  # set only the current bit"),
                *_read_counter(read_reg, i),
                f"slli x{walk_reg}, x{walk_reg}, 1",
            ]
        )

    # walking a single 0
    lines.append(f"LI(x{walk_reg}, 1)")
    for i in range(32):
        lines.extend(
            [
                test_data.add_testcase(f"walking_0_{i}", coverpoint, covergroup),
                f"not x{inv_reg}, x{walk_reg}  # all bits but the current one",
                tsbi_call(f"csrw mcounteren, x{inv_reg}  # clear only the current bit"),
                *_read_counter(read_reg, i),
                f"slli x{walk_reg}, x{walk_reg}, 1",
            ]
        )
    test_data.int_regs.return_registers([read_reg, walk_reg, inv_reg])
    return lines


def _generate_mcounter_inc_inaccessible_tests(test_data: TestData) -> list[str]:
    """running in U mode
    enable counters and read instret
    mcounteren = 0s (and scounteren = 0s) via T-SBI so instret is inaccessible in U mode
    nop
    mcounteren = 1s (and scounteren = 1s) via T-SBI
    read and sigupd change in instret
    """
    covergroup, coverpoint = "ZicntrU_cg", "cp_mcounter_inc_inaccessible"

    old_reg, read_reg = test_data.int_regs.get_registers(2)

    lines = [
        comment_banner(coverpoint, _generate_mcounter_inc_inaccessible_tests.__doc__),
        "",
        test_data.add_testcase("U", coverpoint, covergroup),
        "# make counter accessible in U mode",
        f"LI(x{read_reg}, -1)",
        tsbi_call(f"csrw mcounteren, x{read_reg}"),
        "#ifdef S_SUPPORTED",
        tsbi_call(f"csrw scounteren, x{read_reg}"),
        "#endif",
        f"csrr x{old_reg}, instret",
        "# make counter inaccessible in U mode",
        tsbi_call("csrw mcounteren, zero"),
        "#ifdef S_SUPPORTED",
        tsbi_call("csrw scounteren, zero"),
        "#endif",
        "nop",
        "# make counter accessible in U mode",
        tsbi_call(f"csrw mcounteren, x{read_reg}"),
        "#ifdef S_SUPPORTED",
        tsbi_call(f"csrw scounteren, x{read_reg}"),
        "#endif",
        f"csrr x{read_reg}, instret",
        f"sub x{read_reg}, x{read_reg}, x{old_reg}",
        "# SIGUPD the difference in instret",
        write_sigupd(read_reg, test_data),
    ]
    test_data.int_regs.return_registers([old_reg, read_reg])
    return lines


@add_priv_test_generator(
    "ZicntrU",
    required_extensions=["U", "Zicntr"],
    march_extensions=["Zicntr", "Zihpm"],
    extra_defines=["#define BOOT_TO_UMODE"],
)
def make_zicntru(test_data: TestData) -> list[TestChunk]:
    """Generate tests for ZicntrU coverpoints"""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()
    tc.code.extend(_generate_mcounteren_access_u_tests(test_data))
    tc.code.extend(_generate_mcounter_inc_inaccessible_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
