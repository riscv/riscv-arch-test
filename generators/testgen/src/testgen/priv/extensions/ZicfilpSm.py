##################################
# priv/extensions/ZicfilpSm.py
#
# ZicfilpSm landing pad tests: run in M-mode, plus M-mode trap entry and MRET behavior.
# umer@riscv.org Sep 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZicfilpSm privileged extension test generator for machine mode."""

from testgen.asm.helpers import comment_banner, write_sigupd
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

covergroup = "ZicfilpSm_cg"

MODE_GUARD = {"M": None, "S": "S_SUPPORTED", "U": "U_SUPPORTED"}
MPP = {"M": 3, "S": 1, "U": 0}


def _set_mpelp(reg: int, value: int) -> list[str]:
    """Write mstatus.MPELP (mstatush.MPELP on RV32)."""
    op = "csrs" if value else "csrc"
    return [
        f"# mstatus.MPELP = {value}",
        "#if __riscv_xlen == 64",
        f"LI(x{reg}, MSTATUS_MPELP)",
        f"{op} mstatus, x{reg}",
        "#else",
        f"LI(x{reg}, 0x200) # mstatush.MPELP",
        f"{op} mstatush, x{reg}",
        "#endif",
    ]


def _trap_entry_m_tests(test_data: TestData) -> TestChunk:
    """A trap from M-mode into M-mode with ELP=NO_LP_EXPECTED saves MPELP=0.

    ELP=LP_EXPECTED is saved on the software-check exceptions of the shared M-mode tests.
    """
    coverpoint = "cp_pelp_trap_entry_m_zicfilp"
    temp_reg = test_data.int_regs.get_register()
    tc = test_data.begin_test_chunk()
    tc.code.extend(
        [
            comment_banner(coverpoint, "ecall from M-mode with MLPE=1 and ELP=NO_LP_EXPECTED saves MPELP=0"),
            *set_lpe("M", "M", temp_reg, True),
            test_data.add_testcase("ecall_no_lp_expected", coverpoint, covergroup),
            "RVTEST_TSBI_ECALL_TEST # returns mepc in a0",
            write_sigupd(10, test_data),
            *set_lpe("M", "M", temp_reg, False),
        ]
    )
    test_data.int_regs.return_registers([temp_reg])
    return test_data.end_test_chunk()


def _guarded_trap_entry_tests(test_data: TestData) -> TestChunk:
    """Software-guarded branches (rs1 = x1/x5/x7) do not set ELP, so an ecall at the target traps with MPELP=0."""
    coverpoint = "cp_pelp_trap_entry_m_guarded_zicfilp"
    save_reg, temp_reg = test_data.int_regs.get_registers(2)
    link_reg = test_data.int_regs.link_reg
    tc = test_data.begin_test_chunk()
    lines = [
        comment_banner(
            coverpoint,
            "MLPE=1: jalr, c.jr, and c.jalr through x1, x5, and x7 to an ecall.\n"
            "No landing pad is required, so the ecall is taken (not a software-check exception) with MPELP=0.",
        ),
        *set_lpe("M", "M", temp_reg, True),
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
                    "LI(a0, TSBI_ECALL_TEST) # T-SBI ecall test operation",
                    f"LA(x{rs1}, {label}_target)",
                    f"{label}:",
                    jump(kind, rs1),
                    ".p2align 2",
                    f"{label}_target:",
                    "ecall # returns mepc in a0",
                    "lpad 0 # resume point if the ecall were wrongly a software-check exception",
                    *([f"mv x{link_reg}, x{save_reg} # restore x{link_reg}"] if rs1 == link_reg else []),
                    write_sigupd(10, test_data),
                ]
            )
        if kind != "jalr":
            lines.append("#endif")
    lines.extend(set_lpe("M", "M", temp_reg, False))
    tc.code.extend(lines)
    test_data.int_regs.return_registers([save_reg, temp_reg])
    return test_data.end_test_chunk()


def _elp_state_preservation_tests(test_data: TestData) -> TestChunk:
    """Traps from S/U-mode into M-mode save ELP in MPELP; MRET restores it."""
    coverpoint = "cp_elp_state_preservation_zicfilp"
    jump_reg, temp_reg = test_data.int_regs.get_registers(2)
    tc = test_data.begin_test_chunk()
    lines = [
        comment_banner(
            coverpoint,
            "With xLPE=1 in S- or U-mode (medeleg=0, so traps go to M-mode):\n"
            "jalr through a non-link register to a non-LPAD instruction traps with MPELP=LP_EXPECTED.\n"
            "MRET restores ELP, so the next non-LPAD instruction traps again before the lpad.\n"
            "The T-SBI ecall back to M-mode is taken with ELP=NO_LP_EXPECTED and saves MPELP=0.",
        )
    ]
    for mode in ("S", "U"):
        lines.extend(
            [
                "",
                f"#ifdef {MODE_GUARD[mode]}",
                *set_lpe("M", mode, temp_reg, True),
                f"RVTEST_TSBI_GOTO_{mode}MODE",
                f"LA(x{jump_reg}, {coverpoint}_{mode}_target)",
                test_data.add_testcase(f"from_{mode}_lp_expected", coverpoint, covergroup),
                f"jalr x0, 0(x{jump_reg})",
                ".p2align 2",
                f"{coverpoint}_{mode}_target:",
                "addi x0, x0, 0 # non-LPAD target: software-check exception into M-mode",
                *RESUME,
                test_data.add_testcase(f"from_{mode}_no_lp_expected", coverpoint, covergroup),
                "RVTEST_TSBI_GOTO_MMODE",
                *set_lpe("M", mode, temp_reg, False),
                *check_trap_count(test_data, temp_reg),
                "#endif",
            ]
        )
    tc.code.extend(lines)
    test_data.int_regs.return_registers([jump_reg, temp_reg])
    return test_data.end_test_chunk()


def _trap_return_tests(test_data: TestData) -> TestChunk:
    """MRET sets ELP=MPELP only if xLPE of the new mode is 1, and clears MPELP."""
    coverpoint = "cp_pelp_trap_return_m_zicfilp"
    temp_reg = test_data.int_regs.get_register()
    tc = test_data.begin_test_chunk()
    lines = [
        comment_banner(
            coverpoint,
            "MRET to M-, S-, and U-mode x new mode's xLPE = {0, 1} x MPELP = {0, 1}, returning to a non-LPAD\n"
            "instruction. Only MPELP=1 with xLPE=1 restores ELP=LP_EXPECTED and raises a software-check exception.",
        )
    ]
    for mode in ("M", "S", "U"):
        guard = MODE_GUARD[mode]
        if guard:
            lines.append(f"#ifdef {guard}")
        for lpe in (0, 1):
            for pelp in (0, 1):
                test_data.add_testcase(f"mret_to_{mode}_lpe_{lpe}_mpelp_{pelp}", coverpoint, covergroup)
                label = test_data.current_testcase_label
                lines.extend(
                    [
                        "",
                        *set_lpe("M", mode, temp_reg, bool(lpe)),
                        f"# mstatus.MPP = {mode}-mode",
                        f"LI(x{temp_reg}, MSTATUS_MPP)",
                        f"csrc mstatus, x{temp_reg}",
                        f"LI(x{temp_reg}, 0x{MPP[mode] << 11:x})",
                        f"csrs mstatus, x{temp_reg}",
                        *_set_mpelp(temp_reg, pelp),
                        f"LA(x{temp_reg}, {label}_target)",
                        f"csrw mepc, x{temp_reg}",
                        f"{label}:",
                        "mret",
                        ".p2align 2",
                        f"{label}_target:",
                        "addi x0, x0, 0 # software-check exception only if MPELP=1 and xLPE=1",
                        "lpad 0 # resume point after the software-check exception",
                        *(["RVTEST_TSBI_GOTO_MMODE"] if mode != "M" else []),
                        *(set_lpe("M", mode, temp_reg, False) if lpe else []),
                        *check_trap_count(test_data, temp_reg),
                    ]
                )
        if guard:
            lines.append("#endif")
    tc.code.extend(lines)
    test_data.int_regs.return_registers([temp_reg])
    return test_data.end_test_chunk()


@add_priv_test_generator(
    "ZicfilpSm",
    required_extensions=["Sm", "Zicfilp"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_zicfilpsm(test_data: TestData) -> list[TestChunk]:
    """Generate Zicfilp landing pad tests in M-mode."""
    return [
        *make_zicfilp_tests(test_data, "M", covergroup),
        _trap_entry_m_tests(test_data),
        _guarded_trap_entry_tests(test_data),
        _elp_state_preservation_tests(test_data),
        _trap_return_tests(test_data),
    ]
