##################################
# priv/extensions/Sstc.py
#
# Sstc privileged extension test generator.
# sanarayanan@hmc.edu April 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Sstc stimecmp access tests"""

from testgen.asm.csr import write_stce
from testgen.asm.helpers import comment_banner
from testgen.asm.tsbi import tsbi_call, tsbi_call_or_direct
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

_CG = "Sstc_cg"
_CG_SM = "Sstc_Sm_cg"


def csr_op(instr: str, mode: str) -> str:
    """An M-mode CSR instruction, issued directly in machine mode and through T-SBI otherwise."""
    return tsbi_call_or_direct(instr, "M" if mode == "machine" else "S")  # user tests do their setup in S-mode


def mcounteren_tm(test_data: TestData, enable: bool, mode: str) -> list[str]:
    """Set or clear mcounteren.TM (bit 1)."""
    reg = test_data.int_regs.get_register()
    lines = [f"LI(x{reg}, 0x2)", csr_op(f"{'csrs' if enable else 'csrc'} mcounteren, x{reg}", mode)]
    test_data.int_regs.return_register(reg)
    return lines


def access_stimecmp(test_data: TestData) -> list[str]:
    """Read stimecmp, and stimecmph on RV32, to check whether the reads are permitted; the values are discarded."""
    reg = test_data.int_regs.get_register()
    lines = [
        f"csrr x{reg}, stimecmp",
        "#if __riscv_xlen == 32",
        f"csrr x{reg}, stimecmph",
        "#endif",
    ]
    test_data.int_regs.return_register(reg)
    return lines


def tm_tests(test_data: TestData, covergroup: str, mode: str) -> list[str]:
    """Read stimecmp with mcounteren.TM = 0/1 and STCE = 1; user mode also crosses scounteren.TM = 0/1.

    Below M-mode, TM = 0 makes the read trap; coverage is sampled at the csrr before the trap.  The suite rests
    with mcounteren.TM = scounteren.TM = 1 and STCE = 0, and these tests restore that state.
    """
    coverpoint = f"cp_{mode}_tm"
    user = mode == "user"
    lines = [
        comment_banner(coverpoint, f"{mode[0].upper()}-mode stimecmp read: mcounteren.TM = 0/1, STCE = 1"),
        "",
        *write_stce(test_data, True, mode[0].upper()),
    ]
    for tm_val in (0, 1):
        lines += mcounteren_tm(test_data, bool(tm_val), mode)
        for stm_val in (1, 0) if user else (1,):
            lines += [
                "",
                f"# {coverpoint}: TM = {tm_val}" + (f", scounteren.TM = {stm_val}" if user else ""),
                *([] if stm_val else ["csrci scounteren, 0x2"]),
                *(["RVTEST_TSBI_GOTO_UMODE"] if user else []),
                test_data.add_testcase(f"tm{tm_val}_stm{stm_val}" if user else f"tm{tm_val}", coverpoint, covergroup),
                *access_stimecmp(test_data),
                *(["RVTEST_TSBI_GOTO_SMODE"] if user else []),
                *([] if stm_val else ["csrsi scounteren, 0x2"]),
            ]
    return [*lines, "", *write_stce(test_data, False, mode[0].upper())]


def stce_tests(test_data: TestData, covergroup: str, mode: str) -> list[str]:
    """Read stimecmp with menvcfg.STCE = 0/1; mcounteren.TM = scounteren.TM = 1 from the suite's resting state.

    Below M-mode, STCE = 0 makes the read trap; coverage is sampled at the csrr before the trap.
    """
    coverpoint = f"cp_{mode}_stce"
    user = mode == "user"
    lines = [comment_banner(coverpoint, f"{mode[0].upper()}-mode stimecmp read: menvcfg.STCE = 0/1"), ""]
    for stce_val in (0, 1):
        lines += [
            "",
            f"# {coverpoint}: STCE = {stce_val}",
            *write_stce(test_data, bool(stce_val), mode[0].upper()),
            *(["RVTEST_TSBI_GOTO_UMODE"] if user else []),
            test_data.add_testcase(f"stce{stce_val}", coverpoint, covergroup),
            *access_stimecmp(test_data),
            *(["RVTEST_TSBI_GOTO_SMODE"] if user else []),
        ]
    return [*lines, "", *write_stce(test_data, False, mode[0].upper())]


def _tsbi_stimecmp_max(test_data: TestData) -> list[str]:
    """stimecmp = -1 through T-SBI, for use while STCE = 0 makes stimecmp inaccessible below M-mode."""
    reg = test_data.int_regs.get_register()
    lines = [
        f"LI(x{reg}, -1)",
        "#if __riscv_xlen == 32",
        tsbi_call(f"csrw stimecmph, x{reg}"),
        "#endif",
        tsbi_call(f"csrw stimecmp, x{reg}"),
    ]
    test_data.int_regs.return_register(reg)
    return lines


def emit_lower_tests(test_data: TestData, covergroup: str, mode: str) -> list[TestChunk]:
    """All Sstc tests for one lower mode as one chunk; starts and ends in S-mode."""
    tc = test_data.begin_test_chunk()
    tc.code = [
        comment_banner("Sstc", f"Supervisor timer (Sstc) stimecmp access tests from {mode} mode"),
        "",
        "# Boot state: mcounteren=-1, scounteren=-1, STCE=0, so S-mode can access stimecmp once",
        "# STCE=1 and only mcounteren.TM/STCE gate U-mode reads. stimecmp has no reset value, so",
        "# park it at -1 before any test sets STCE.",
        *_tsbi_stimecmp_max(test_data),
        "",
    ]
    tc.code += tm_tests(test_data, covergroup, mode)
    tc.code += stce_tests(test_data, covergroup, mode)
    return [test_data.end_test_chunk()]


@add_priv_test_generator(
    "Sstc",
    required_extensions=["Sstc"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_sstc(test_data: TestData) -> list[TestChunk]:
    """Generate tests for Sstc coverpoints."""
    test_chunks: list[TestChunk] = []
    for mode in ("supervisor", "user"):
        test_chunks.extend(emit_lower_tests(test_data, _CG, mode))
    return test_chunks


@add_priv_test_generator(
    "Sstc",
    required_extensions=["Sm", "Sstc"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_sstcsm(test_data: TestData) -> list[TestChunk]:
    """Generate tests for Sm-group Sstc coverpoints; the group boots to and stays in M-mode."""
    tc = test_data.begin_test_chunk("Sm")
    tc.code = [
        comment_banner("Sstc_Sm", "Supervisor timer (Sstc) stimecmp access tests from M-mode"),
        "",
    ]
    tc.code += tm_tests(test_data, _CG_SM, "machine")
    tc.code += stce_tests(test_data, _CG_SM, "machine")
    return [test_data.end_test_chunk()]
