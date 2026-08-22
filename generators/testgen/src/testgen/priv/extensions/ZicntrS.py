##################################
# ZicntrS.py
#
# ZicntrS privileged extension test generator.
# ellyu@g.hmc.edu March 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZicntrS extension test generator: counter access from S/U-mode"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

_COUNTERS = ["cycle", "time", "instret"]


def _read_counter(read_reg: int, i: int, mode: str) -> list[str]:
    """Read counter i (and its high half on RV32) in the current mode."""
    if i < 3:
        name = _COUNTERS[i]
        return [f"csrr x{read_reg}, {name}", "#if __riscv_xlen == 32", f"csrr x{read_reg}, {name}h", "#endif"]
    return [
        "#ifdef ZIHPM_SUPPORTED",
        f"csrr x{read_reg}, hpmcounter{i} # read from hpmcounter{i} in {mode}",
        "#if __riscv_xlen == 32",
        f"csrr x{read_reg}, hpmcounter{i}h # read from hpmcounter{i}h in {mode}",
        "#endif",
        "#endif",
    ]


def _write_counteren(csr: str, value_reg: int) -> str:
    """Write the walking value to csr: mcounteren is M-mode only, so through T-SBI; scounteren directly from S-mode."""
    instr = f"csrw {csr}, x{value_reg}"
    return tsbi_call(instr) if csr == "mcounteren" else instr


def _walk_counteren(
    test_data: TestData, coverpoint: str, covergroup: str, *, csrs: list[str], read_mode: str
) -> list[str]:
    """
    Walk a 1 and then a 0 through every bit of each CSR in csrs (the same value in each), reading the
    corresponding counter after each write. Reads happen in S-mode, or in U-mode.
    """
    read_reg, ones_reg, walk_reg, inv_reg = test_data.int_regs.get_registers(4)
    lines = [f"LI(x{ones_reg}, -1)"]
    if "mcounteren" not in csrs:
        lines.append(tsbi_call(f"csrw mcounteren, x{ones_reg}  # enable all counters in M-mode"))
    goto_read = ["RVTEST_TSBI_GOTO_UMODE"] if read_mode == "U-mode" else []
    goto_back = ["RVTEST_TSBI_GOTO_SMODE"] if read_mode == "U-mode" else []

    lines.append(f"LI(x{walk_reg}, 1)")
    for i in range(32):
        lines.append(test_data.add_testcase(f"walking_1_{i}", coverpoint, covergroup))
        lines.extend(_write_counteren(csr, walk_reg) for csr in csrs)
        lines.extend([*goto_read, *_read_counter(read_reg, i, read_mode), *goto_back])
        lines.append(f"slli x{walk_reg}, x{walk_reg}, 1")

    # walking a single 0
    lines.append(f"LI(x{walk_reg}, 1)")
    for i in range(32):
        lines.append(test_data.add_testcase(f"walking_0_{i}", coverpoint, covergroup))
        lines.append(f"not x{inv_reg}, x{walk_reg}  # all bits but the current one")
        lines.extend(_write_counteren(csr, inv_reg) for csr in csrs)
        lines.extend([*goto_read, *_read_counter(read_reg, i, read_mode), *goto_back])
        lines.append(f"slli x{walk_reg}, x{walk_reg}, 1")
    test_data.int_regs.return_registers([read_reg, ones_reg, walk_reg, inv_reg])
    return lines


def _generate_mcounteren_access_s_tests(test_data: TestData) -> list[str]:
    """Generate mcounteren access s mode tests."""
    covergroup, coverpoint = "ZicntrS_cg", "cp_mcounteren_access_s"
    return [
        comment_banner(
            coverpoint,
            "Write walking 1s and 0s to mcounteren via T-SBI.  Read from corresponding counter and counterh in S-mode",
        ),
        "",
        *_walk_counteren(test_data, coverpoint, covergroup, csrs=["mcounteren"], read_mode="S-mode"),
    ]


def _generate_scounteren_access_s_tests(test_data: TestData) -> list[str]:
    """Generate scounteren access s mode tests."""
    covergroup, coverpoint = "ZicntrS_cg", "cp_scounteren_access_s"
    return [
        comment_banner(
            coverpoint,
            "Write walking 1s and 0s to scounteren with mcounteren = all 1s.  Read from corresponding counter and counterh in S-mode",
        ),
        "",
        *_walk_counteren(test_data, coverpoint, covergroup, csrs=["scounteren"], read_mode="S-mode"),
    ]


def _generate_scounteren_access_u_tests(test_data: TestData) -> list[str]:
    """Generate scounteren access u mode tests."""
    covergroup, coverpoint = "ZicntrS_cg", "cp_scounteren_access_u"
    return [
        comment_banner(
            coverpoint,
            "Write walking 1s and 0s to scounteren with mcounteren = all 1s.  Read from corresponding counter and counterh in U-mode",
        ),
        "",
        *_walk_counteren(test_data, coverpoint, covergroup, csrs=["scounteren"], read_mode="U-mode"),
    ]


def _generate_mscounteren_access_u_tests(test_data: TestData) -> list[str]:
    """Generate mcounteren access u mode tests."""
    covergroup, coverpoint = "ZicntrS_cg", "cp_mcounteren_access_u"
    return [
        comment_banner(
            coverpoint,
            "Write walking 1s and 0s to both mcounteren (via T-SBI) and scounteren (same value in each).  Read from corresponding counter and counterh in U-mode",
        ),
        "",
        *_walk_counteren(test_data, coverpoint, covergroup, csrs=["mcounteren", "scounteren"], read_mode="U-mode"),
    ]


def _generate_mcounter_inc_inaccessible_tests(test_data: TestData) -> list[str]:
    """running in S mode
    mcounteren = 1s via T-SBI and read instret
    mcounteren = 0s via T-SBI so instret is inaccessible in S mode
    nop
    mcounteren = 1s via T-SBI
    read and sigupd change in instret
    """
    covergroup, coverpoint = "ZicntrS_cg", "cp_mcounter_inc_inaccessible"

    old_reg, read_reg = test_data.int_regs.get_registers(2)

    lines = [
        comment_banner(coverpoint, _generate_mcounter_inc_inaccessible_tests.__doc__),
        "",
        test_data.add_testcase("S", coverpoint, covergroup),
        "# make counter accessible in S mode",
        f"LI(x{read_reg}, -1)",
        tsbi_call(f"csrw mcounteren, x{read_reg}"),
        f"csrr x{old_reg}, instret",
        "# make counter inaccessible in S mode",
        tsbi_call("csrw mcounteren, zero"),
        "nop",
        "# make counter accessible in S mode",
        tsbi_call(f"csrw mcounteren, x{read_reg}"),
        f"csrr x{read_reg}, instret",
        f"sub x{read_reg}, x{read_reg}, x{old_reg}",
        "# SIGUPD the difference in instret",
        write_sigupd(read_reg, test_data),
    ]
    test_data.int_regs.return_registers([old_reg, read_reg])
    return lines


@add_priv_test_generator(
    "ZicntrS",
    required_extensions=["S", "Zicntr"],
    march_extensions=["Zicntr", "Zihpm"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_zicntrs(test_data: TestData) -> list[TestChunk]:
    """Generate tests for ZicntrS coverpoints"""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()

    tc.code.extend(_generate_mcounteren_access_s_tests(test_data))
    tc.code.extend(_generate_scounteren_access_s_tests(test_data))
    tc.code.extend(_generate_scounteren_access_u_tests(test_data))
    tc.code.extend(_generate_mscounteren_access_u_tests(test_data))
    tc.code.extend(_generate_mcounter_inc_inaccessible_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
