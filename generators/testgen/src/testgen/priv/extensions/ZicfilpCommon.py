##################################
# priv/extensions/ZicfilpCommon.py
#
# Shared generators for the ZicfilpSm / ZicfilpS / ZicfilpU landing pad test suites.
# umer@riscv.org Sep 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared Zicfilp landing pad test generators, parameterized by the privilege mode the suite runs in."""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk

LABEL = 0x12345
OTHER_LABEL = 0x54321
ALL_ONES_LABEL = 0xFFFFF

JUMP_KINDS = ("jalr", "c.jr", "c.jalr")

# After a software-check exception the trap handler resumes at the next instruction, and xRET restores
# ELP=LP_EXPECTED from xPELP. This non-LPAD instruction therefore traps again, and the lpad after it is
# where execution resumes. When no exception was taken, the nop checks that ELP was left clear.
RESUME = [
    "addi x0, x0, 0 # ELP must be NO_LP_EXPECTED here, otherwise software-check exception",
    "lpad 0         # resume point after a software-check exception on the nop",
]


def csr_access(priv: str, instr: str, csr_priv: str) -> str:
    """CSR instruction for a csr_priv-level CSR; a T-SBI call when the test runs below that level."""
    direct = priv == "M" or (priv == "S" and csr_priv == "S")
    return instr if direct else tsbi_call(instr)


def set_lpe(priv: str, mode: str, reg: int, enable: bool) -> list[str]:
    """Set or clear xLPE of `mode` from a test running in `priv`."""
    op = "csrs" if enable else "csrc"
    action = "Enable" if enable else "Disable"
    if mode == "M":
        return [
            f"# {action} landing pads in M-mode (mseccfg.MLPE)",
            f"LI(x{reg}, MSECCFG_MLPE)",
            csr_access(priv, f"{op} mseccfg, x{reg}", "M"),
        ]
    if mode == "S":
        return [
            f"# {action} landing pads in S-mode (menvcfg.LPE)",
            f"LI(x{reg}, MENVCFG_LPE)",
            csr_access(priv, f"{op} menvcfg, x{reg}", "M"),
        ]
    return [
        f"# {action} landing pads in U-mode (senvcfg.LPE with S-mode, menvcfg.LPE without)",
        "#ifdef S_SUPPORTED",
        f"LI(x{reg}, SENVCFG_LPE)",
        csr_access(priv, f"{op} senvcfg, x{reg}", "S"),
        "#else",
        f"LI(x{reg}, MENVCFG_LPE)",
        csr_access(priv, f"{op} menvcfg, x{reg}", "M"),
        "#endif",
    ]


def jump(kind: str, rs1: int, rd: int = 0) -> str:
    """Indirect jump through rs1. Compressed jumps are raw halfwords because Zca is not in the suite's march."""
    if kind == "jalr":
        return f"jalr x{rd}, 0(x{rs1})"
    encoding = (0x8002 if kind == "c.jr" else 0x9002) | (rs1 << 7)
    return f".hword 0x{encoding:04x} # {kind} x{rs1}"


def check_trap_count(test_data: TestData, reg: int) -> list[str]:
    """Record the running trap count, so a missing or extra trap is attributed to the current testcase."""
    return [
        f"LA(x{reg}, rvtest_trap_count)",
        f"LREG x{reg}, 0(x{reg})",
        write_sigupd(reg, test_data),
    ]


def jump_to_target(
    test_data: TestData,
    kind: str,
    rs1: int,
    rd: int,
    target: list[str],
    bin_name: str,
    coverpoint: str,
    covergroup: str,
    save_reg: int,
) -> list[str]:
    """Jump through rs1 to a 4-byte aligned target, followed by the RESUME sequence.

    rs1 may be one of the signature, data, temp, or link registers; it is saved in save_reg and restored.
    """
    int_regs = test_data.int_regs
    protected = rs1 in (int_regs.sig_reg, int_regs.data_reg, int_regs.temp_reg, int_regs.link_reg)
    lines = [f"mv x{save_reg}, x{rs1} # save x{rs1}"] if protected else []
    label = test_data.add_testcase(bin_name, coverpoint, covergroup)
    target_label = f"{test_data.current_testcase_label}_target"
    lines.extend(
        [
            f"LA(x{rs1}, {target_label})",
            label,
            jump(kind, rs1, rd),
            ".p2align 2",
            f"{target_label}:",
            *target,
            *RESUME,
        ]
    )
    if protected:
        lines.append(f"mv x{rs1}, x{save_reg} # restore x{rs1}")
    return lines


def indirect_elp_state_update_tests(test_data: TestData, priv: str, covergroup: str, kind: str) -> TestChunk:
    """Every rs1 x {LPE disabled, enabled} x {LPAD, non-LPAD target} for one indirect jump kind."""
    coverpoint = "cp_zicfilp_indirect_elp_state_update" + ("" if kind == "jalr" else "_c")
    save_reg, temp_reg = test_data.int_regs.get_registers(2)
    tc = test_data.begin_test_chunk()
    lines = [
        comment_banner(
            f"{coverpoint} ({kind})",
            f"{kind} through every rs1 (x1-x31) to an LPAD and to a non-LPAD target, with {priv}-mode xLPE = 0 and 1.\n"
            "With xLPE=1 and rs1 other than x1/x5/x7, a non-LPAD target raises a software-check exception.",
        )
    ]
    if kind != "jalr":
        lines.append("#ifdef ZCA_SUPPORTED")
    for lpe in (0, 1):
        lines.extend(set_lpe(priv, priv, temp_reg, bool(lpe)))
        for rs1 in range(1, 32):
            # jalr is an indirect jump/return (rd=x0) for odd rs1, including x1/x5/x7, and an indirect call otherwise
            rd = 0 if rs1 % 2 else 1
            for dest in ("lpad", "not_lpad"):
                target = ["lpad 0"] if dest == "lpad" else ["addi x0, x0, 0 # non-LPAD target"]
                lines.extend(
                    [
                        "",
                        *jump_to_target(
                            test_data,
                            kind,
                            rs1,
                            rd,
                            target,
                            f"{kind}_lpe_{lpe}_x{rs1}_{dest}",
                            coverpoint,
                            covergroup,
                            save_reg,
                        ),
                        *check_trap_count(test_data, temp_reg),
                    ]
                )
        if lpe:
            lines.extend(set_lpe(priv, priv, temp_reg, False))
    if kind != "jalr":
        lines.append("#endif")
    tc.code.extend(lines)
    test_data.int_regs.return_registers([save_reg, temp_reg])
    return test_data.end_test_chunk()


def lpad_label_tests(test_data: TestData, priv: str, covergroup: str) -> TestChunk:
    """LPAD label checking with ELP=LP_EXPECTED (after an indirect jump) and ELP=NO_LP_EXPECTED (sequential)."""
    jump_reg, save_reg, temp_reg = test_data.int_regs.get_registers(3)
    tc = test_data.begin_test_chunk()
    lines = [
        comment_banner(
            "cp_zicfilp_lpad_*",
            f"LPAD label checks in {priv}-mode with xLPE=1. x7[31:12] holds the expected label.\n"
            "Reached by jalr through a non-link register (ELP=LP_EXPECTED): LPL=0 and LPL=x7[31:12] pass;\n"
            "a non-LPAD instruction, or LPL!=0 not matching x7[31:12], raises a software-check exception.\n"
            "Executed sequentially (ELP=NO_LP_EXPECTED): every LPAD is a no-op.",
        ),
        *set_lpe(priv, priv, temp_reg, True),
    ]
    jump_cases = [
        ("lp_expected_lpl_zero_x7_zero", "cp_zicfilp_lpad_zero_label_bypass", 0, "lpad 0"),
        ("lp_expected_lpl_zero_x7_nonzero", "cp_zicfilp_lpad_zero_label_bypass", LABEL << 12, "lpad 0"),
        ("lp_expected_lpl_match", "cp_zicfilp_lpad_valid_execution", LABEL << 12, f"lpad 0x{LABEL:x}"),
        (
            "lp_expected_lpl_match_all_ones",
            "cp_zicfilp_lpad_valid_execution",
            ALL_ONES_LABEL << 12,
            f"lpad 0x{ALL_ONES_LABEL:x}",
        ),
        ("lp_expected_lpl_mismatch", "cp_zicfilp_lpad_label_mismatch", LABEL << 12, f"lpad 0x{OTHER_LABEL:x}"),
        (
            "lp_expected_lpl_nonzero_x7_zero",
            "cp_zicfilp_lpad_label_match_mismatch",
            0,
            f"lpad 0x{LABEL:x}",
        ),
        (
            "lp_expected_not_lpad",
            "cp_zicfilp_lpad_missing_instruction_exception",
            LABEL << 12,
            "addi x0, x0, 0 # non-LPAD target",
        ),
        (
            "lp_expected_illegal_instruction",
            "cp_zicfilp_lpad_missing_instruction_exception",
            LABEL << 12,
            ".word 0xFFFFFFFF # illegal instruction target: the software-check exception has priority",
        ),
    ]
    for bin_name, coverpoint, x7, target in jump_cases:
        lines.extend(
            [
                "",
                f"LI(x7, 0x{x7:x}) # expected landing pad label in x7[31:12]",
                *jump_to_target(test_data, "jalr", jump_reg, 0, [target], bin_name, coverpoint, covergroup, save_reg),
                *check_trap_count(test_data, temp_reg),
            ]
        )
    lines.extend(
        [
            "",
            "#if __riscv_xlen == 64",
            "# Only x7[31:12] is compared with the label, not the upper bits",
            f"LI(x7, 0xabcd0000{LABEL << 12:08x})",
            *jump_to_target(
                test_data,
                "jalr",
                jump_reg,
                0,
                [f"lpad 0x{LABEL:x}"],
                "lp_expected_lpl_match_x7_upper_bits_set",
                "cp_zicfilp_lpad_valid_execution",
                covergroup,
                save_reg,
            ),
            *check_trap_count(test_data, temp_reg),
            "#endif",
        ]
    )
    sequential_cases = [
        ("no_lp_expected_lpl_zero_x7_zero", "cp_zicfilp_lpad_zero_label_bypass", 0, "lpad 0"),
        ("no_lp_expected_lpl_zero_x7_nonzero", "cp_zicfilp_lpad_zero_label_bypass", LABEL << 12, "lpad 0"),
        ("no_lp_expected_lpl_match", "cp_zicfilp_lpad_valid_execution", LABEL << 12, f"lpad 0x{LABEL:x}"),
        ("no_lp_expected_lpl_mismatch", "cp_zicfilp_lpad_label_mismatch", LABEL << 12, f"lpad 0x{OTHER_LABEL:x}"),
    ]
    for bin_name, coverpoint, x7, instr in sequential_cases:
        lines.extend(
            [
                "",
                f"LI(x7, 0x{x7:x}) # expected landing pad label in x7[31:12]",
                ".p2align 2",
                test_data.add_testcase(bin_name, coverpoint, covergroup),
                f"{instr} # ELP=NO_LP_EXPECTED: no label check",
                *RESUME,
                *check_trap_count(test_data, temp_reg),
            ]
        )
    lines.extend(set_lpe(priv, priv, temp_reg, False))
    tc.code.extend(lines)
    test_data.int_regs.return_registers([jump_reg, save_reg, temp_reg])
    return test_data.end_test_chunk()


def disabled_tests(test_data: TestData, priv: str, covergroup: str) -> TestChunk:
    """With xLPE=0, indirect jumps need no landing pad and LPAD never checks its label."""
    coverpoint = "cp_disabled_zicfilp"
    jump_reg, save_reg, temp_reg = test_data.int_regs.get_registers(3)
    tc = test_data.begin_test_chunk()
    lines = [
        comment_banner(
            coverpoint,
            f"{priv}-mode xLPE=0: jalr through a non-link register to an LPAD with a mismatched label\n"
            "and to a non-LPAD instruction. Neither raises an exception.",
        ),
        *set_lpe(priv, priv, temp_reg, False),
    ]
    cases = [
        ("lpe_0_lpl_mismatch", f"lpad 0x{OTHER_LABEL:x}"),
        ("lpe_0_not_lpad", "addi x0, x0, 0 # non-LPAD target"),
    ]
    for bin_name, target in cases:
        lines.extend(
            [
                "",
                f"LI(x7, 0x{LABEL << 12:x}) # expected landing pad label in x7[31:12]",
                *jump_to_target(test_data, "jalr", jump_reg, 0, [target], bin_name, coverpoint, covergroup, save_reg),
                *check_trap_count(test_data, temp_reg),
            ]
        )
    tc.code.extend(lines)
    test_data.int_regs.return_registers([jump_reg, save_reg, temp_reg])
    return test_data.end_test_chunk()


def exception_priority_tests(test_data: TestData, priv: str, covergroup: str) -> TestChunk:
    """An instruction access fault at the target of an ELP-setting jump outranks the software-check exception."""
    coverpoint = "cp_exception_priority_zicfilp"
    jump_reg, temp_reg = test_data.int_regs.get_registers(2)
    tc = test_data.begin_test_chunk()
    tc.code.extend(
        [
            "#ifdef RVMODEL_ACCESS_FAULT_ADDRESS",
            comment_banner(
                coverpoint,
                f"{priv}-mode xLPE=1: jalr through a non-link register to RVMODEL_ACCESS_FAULT_ADDRESS.\n"
                "The instruction access fault is taken with xPELP=LP_EXPECTED. The handler resumes at ra and\n"
                "xRET restores ELP, so the non-LPAD instruction there raises a software-check exception.",
            ),
            *set_lpe(priv, priv, temp_reg, True),
            f"LA(x{jump_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
            test_data.add_testcase("lpe_1_instr_access_fault", coverpoint, covergroup),
            f"jalr x1, 0(x{jump_reg}) # instruction access fault; the handler resumes at ra",
            *RESUME,
            *check_trap_count(test_data, temp_reg),
            *set_lpe(priv, priv, temp_reg, False),
            "#endif",
        ]
    )
    test_data.int_regs.return_registers([jump_reg, temp_reg])
    return test_data.end_test_chunk()


def make_zicfilp_tests(test_data: TestData, priv: str, covergroup: str) -> list[TestChunk]:
    """Tests shared by every Zicfilp suite."""
    return [
        *(indirect_elp_state_update_tests(test_data, priv, covergroup, kind) for kind in JUMP_KINDS),
        lpad_label_tests(test_data, priv, covergroup),
        disabled_tests(test_data, priv, covergroup),
        exception_priority_tests(test_data, priv, covergroup),
    ]
