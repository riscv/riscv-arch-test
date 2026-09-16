##################################
# priv/extensions/ZicfilpS.py
#
# ZicfilpS landing pad tests: run in S-mode, plus S-mode trap entry and SRET behavior.
# umer@riscv.org Sep 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZicfilpS privileged extension test generator for supervisor mode."""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZicfilpCommon import (
    JUMP_KINDS,
    RESUME,
    check_trap_count,
    jump,
    make_zicfilp_tests,
    set_lpe,
)
from testgen.priv.registry import add_priv_test_generator

covergroup = "ZicfilpS_cg"

SPP = {"S": 1, "U": 0}


def _trap_entry_s_tests(test_data: TestData) -> TestChunk:
    """A trap from S-mode into S-mode with ELP=NO_LP_EXPECTED saves SPELP=0.

    ELP=LP_EXPECTED is saved on the software-check exceptions of the shared S-mode tests.
    """
    coverpoint = "cp_pelp_trap_entry_s_zicfilp"
    temp_reg = test_data.int_regs.get_register()
    tc = test_data.begin_test_chunk()
    tc.code.extend(
        [
            comment_banner(
                coverpoint, "ebreak in S-mode with menvcfg.LPE=1 and ELP=NO_LP_EXPECTED saves sstatus.SPELP=0"
            ),
            *set_lpe("S", "S", temp_reg, True),
            test_data.add_testcase("ebreak_no_lp_expected", coverpoint, covergroup),
            "ebreak",
            "lpad 0 # resume point if the ebreak were wrongly a software-check exception",
            *check_trap_count(test_data, temp_reg),
            *set_lpe("S", "S", temp_reg, False),
        ]
    )
    test_data.int_regs.return_registers([temp_reg])
    return test_data.end_test_chunk()


def _guarded_trap_entry_s_tests(test_data: TestData) -> TestChunk:
    """Software-guarded branches (rs1 = x1/x5/x7) do not set ELP, so an ebreak at the target traps with SPELP=0."""
    coverpoint = "cp_pelp_trap_entry_s_guarded_zicfilp"
    save_reg, temp_reg = test_data.int_regs.get_registers(2)
    link_reg = test_data.int_regs.link_reg
    tc = test_data.begin_test_chunk()
    lines = [
        comment_banner(
            coverpoint,
            "menvcfg.LPE=1: jalr, c.jr, and c.jalr through x1, x5, and x7 to an ebreak.\n"
            "No landing pad is required, so the breakpoint is taken (not a software-check exception) with SPELP=0.",
        ),
        *set_lpe("S", "S", temp_reg, True),
    ]
    for kind in JUMP_KINDS:
        cp = coverpoint + ("" if kind == "jalr" else "_c")
        if kind != "jalr":
            lines.append("#ifdef ZCA_SUPPORTED")
        for rs1 in (1, 5, 7):
            test_data.add_testcase(f"{kind}_x{rs1}", cp, covergroup)
            label = test_data.current_testcase_label
            lines.extend(
                [
                    "",
                    *([f"mv x{save_reg}, x{link_reg} # save x{link_reg}"] if rs1 == link_reg else []),
                    f"LA(x{rs1}, {label}_target)",
                    f"{label}:",
                    jump(kind, rs1),
                    ".p2align 2",
                    f"{label}_target:",
                    "ebreak",
                    "lpad 0 # resume point if the ebreak were wrongly a software-check exception",
                    *([f"mv x{link_reg}, x{save_reg} # restore x{link_reg}"] if rs1 == link_reg else []),
                    *check_trap_count(test_data, temp_reg),
                ]
            )
        if kind != "jalr":
            lines.append("#endif")
    lines.extend(set_lpe("S", "S", temp_reg, False))
    tc.code.extend(lines)
    test_data.int_regs.return_registers([save_reg, temp_reg])
    return test_data.end_test_chunk()


def _elp_state_preservation_s_tests(test_data: TestData) -> TestChunk:
    """Traps from U-mode into S-mode save ELP in SPELP; SRET restores it."""
    coverpoint = "cp_elp_state_preservation_s_zicfilp"
    jump_reg, temp_reg = test_data.int_regs.get_registers(2)
    tc = test_data.begin_test_chunk()
    tc.code.extend(
        [
            comment_banner(
                coverpoint,
                "With senvcfg.LPE=1 in U-mode (software-check exceptions and U-mode ecalls are delegated to S-mode):\n"
                "jalr through a non-link register to a non-LPAD instruction traps with SPELP=LP_EXPECTED.\n"
                "SRET restores ELP, so the next non-LPAD instruction traps again before the lpad.\n"
                "The T-SBI ecall back to S-mode is taken with ELP=NO_LP_EXPECTED and saves SPELP=0.",
            ),
            *set_lpe("S", "U", temp_reg, True),
            "RVTEST_TSBI_GOTO_UMODE",
            f"LA(x{jump_reg}, {coverpoint}_target)",
            test_data.add_testcase("from_U_lp_expected", coverpoint, covergroup),
            f"jalr x0, 0(x{jump_reg})",
            ".p2align 2",
            f"{coverpoint}_target:",
            "addi x0, x0, 0 # non-LPAD target: software-check exception into S-mode",
            *RESUME,
            test_data.add_testcase("from_U_no_lp_expected", coverpoint, covergroup),
            "RVTEST_TSBI_GOTO_SMODE",
            *set_lpe("S", "U", temp_reg, False),
            *check_trap_count(test_data, temp_reg),
        ]
    )
    test_data.int_regs.return_registers([jump_reg, temp_reg])
    return test_data.end_test_chunk()


def _trap_return_s_tests(test_data: TestData) -> TestChunk:
    """SRET sets ELP=SPELP only if xLPE of the new mode is 1, and clears SPELP."""
    coverpoint = "cp_pelp_trap_return_s_zicfilp"
    temp_reg = test_data.int_regs.get_register()
    tc = test_data.begin_test_chunk()
    lines = [
        comment_banner(
            coverpoint,
            "SRET to S- and U-mode x new mode's xLPE = {0, 1} x SPELP = {0, 1}, returning to a non-LPAD\n"
            "instruction. Only SPELP=1 with xLPE=1 restores ELP=LP_EXPECTED and raises a software-check exception.",
        )
    ]
    for mode in ("S", "U"):
        if mode == "U":
            lines.append("#ifdef U_SUPPORTED")
        for lpe in (0, 1):
            for pelp in (0, 1):
                test_data.add_testcase(f"sret_to_{mode}_lpe_{lpe}_spelp_{pelp}", coverpoint, covergroup)
                label = test_data.current_testcase_label
                lines.extend(
                    [
                        "",
                        *set_lpe("S", mode, temp_reg, bool(lpe)),
                        f"# sstatus.SPP = {mode}-mode",
                        f"LI(x{temp_reg}, SSTATUS_SPP)",
                        f"{'csrs' if SPP[mode] else 'csrc'} sstatus, x{temp_reg}",
                        f"# sstatus.SPELP = {pelp}",
                        f"LI(x{temp_reg}, SSTATUS_SPELP)",
                        f"{'csrs' if pelp else 'csrc'} sstatus, x{temp_reg}",
                        f"LA(x{temp_reg}, {label}_target)",
                        f"csrw sepc, x{temp_reg}",
                        f"{label}:",
                        "sret",
                        ".p2align 2",
                        f"{label}_target:",
                        "addi x0, x0, 0 # software-check exception only if SPELP=1 and xLPE=1",
                        "lpad 0 # resume point after the software-check exception",
                        *(["RVTEST_TSBI_GOTO_SMODE"] if mode != "S" else []),
                        *(set_lpe("S", mode, temp_reg, False) if lpe else []),
                        *check_trap_count(test_data, temp_reg),
                    ]
                )
        if mode == "U":
            lines.append("#endif")
    tc.code.extend(lines)
    test_data.int_regs.return_registers([temp_reg])
    return test_data.end_test_chunk()


@add_priv_test_generator(
    "ZicfilpS",
    required_extensions=["S", "Zicfilp"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_zicfilps(test_data: TestData) -> list[TestChunk]:
    """Generate Zicfilp landing pad tests in S-mode."""
    return [
        *make_zicfilp_tests(test_data, "S", covergroup),
        _trap_entry_s_tests(test_data),
        _guarded_trap_entry_s_tests(test_data),
        _elp_state_preservation_s_tests(test_data),
        _trap_return_s_tests(test_data),
    ]
