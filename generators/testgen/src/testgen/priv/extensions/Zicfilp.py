##################################
# priv/extensions/Zicfilp.py
#
# Landing pad test generators for the Zicfilp suites (Sm, S and U groups).
# umer@riscv.org Sep 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZicfilpSm, ZicfilpS and ZicfilpU privileged test generators, shared helpers and per-mode registrations."""

from itertools import product
from typing import Literal

from testgen.asm.helpers import arch_block, comment_banner, write_sigupd
from testgen.asm.tsbi import tsbi_call_or_direct
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

Priv = Literal["M", "S"]
Mode = Literal["M", "S", "U"]

LABEL = 0x12345
OTHER_LABEL = 0x54321
ALL_ONES_LABEL = 0xFFFFF
# The label check reads x7[31:12] only, so every x7 that carries a label also carries
# nonzero low bits. A DUT that compares x7[31:0] with {LPL,12'b0} then fails the match cases.
LOW_BITS = 0xABC

JumpKind = Literal["jalr", "c.jr", "c.jalr"]
JUMP_KINDS: tuple[JumpKind, ...] = ("jalr", "c.jr", "c.jalr")

# After a software-check exception the trap handler resumes at the next instruction, and xRET restores
# ELP=LP_EXPECTED from xPELP. This non-LPAD instruction therefore traps again, and the lpad after it is
# where execution resumes. When no exception was taken, the nop checks that ELP was left clear.
RESUME = [
    "addi x0, x0, 0 # ELP must be NO_LP_EXPECTED here, otherwise software-check exception",
    "lpad 0         # resume point after a software-check exception on the nop",
]


def _split(covergroup: str) -> str:
    """Split name for a test chunk: the group (Sm, S or U) of the covergroup."""
    return covergroup.removeprefix("Zicfilp_").removesuffix("_cg")


def set_lpe(priv: Mode, mode: Mode, reg: int, enable: bool) -> list[str]:
    """Set or clear xLPE of `mode` from a test running in `priv`."""
    op = "csrs" if enable else "csrc"
    action = "Enable" if enable else "Disable"
    if mode == "M":
        return [
            f"# {action} landing pads in M-mode (mseccfg.MLPE)",
            f"LI(x{reg}, MSECCFG_MLPE)",
            tsbi_call_or_direct(f"{op} mseccfg, x{reg}", priv),
        ]
    if mode == "S":
        return [
            f"# {action} landing pads in S-mode (menvcfg.LPE)",
            f"LI(x{reg}, MENVCFG_LPE)",
            tsbi_call_or_direct(f"{op} menvcfg, x{reg}", priv),
        ]
    return [
        f"# {action} landing pads in U-mode (senvcfg.LPE with S-mode, menvcfg.LPE without)",
        "#ifdef S_SUPPORTED",
        f"LI(x{reg}, SENVCFG_LPE)",
        tsbi_call_or_direct(f"{op} senvcfg, x{reg}", priv),
        "#else",
        f"LI(x{reg}, MENVCFG_LPE)",
        tsbi_call_or_direct(f"{op} menvcfg, x{reg}", priv),
        "#endif",
    ]


def jump_to_target(
    test_data: TestData,
    kind: JumpKind,
    rs1: int,
    rd: int,
    target: list[str],
    bin_name: str,
    coverpoint: str,
    covergroup: str,
    save_reg: int,
) -> list[str]:
    """Jump through rs1 to a 4-byte aligned target, followed by the RESUME sequence.

    rs1 may be one of the signature, data, temp, or link registers;
    it is saved in save_reg and restored if it is the signature, data, or link register.
    """
    int_regs = test_data.int_regs
    protected = rs1 in (int_regs.sig_reg, int_regs.data_reg, int_regs.link_reg)
    lines = [f"mv x{save_reg}, x{rs1} # save x{rs1}"] if protected else []
    testcase = test_data.add_testcase(bin_name, coverpoint, covergroup)
    target_label = f"{test_data.current_testcase_label}_target"
    lines.extend(
        [
            f"LA(x{rs1}, {target_label})",
            testcase,
            *(arch_block([f"{kind} x{rs1}"], "zca") if kind != "jalr" else [f"jalr x{rd}, 0(x{rs1})"]),
            ".p2align 2",
            f"{target_label}:",
            *target,
            *RESUME,
        ]
    )
    if protected:
        lines.append(f"mv x{rs1}, x{save_reg} # restore x{rs1}")
    return lines


def _guard_if_compressed(kind: JumpKind, lines: list[str]) -> list[str]:
    """Compressed jumps exist only with Zca."""
    return lines if kind == "jalr" else ["#ifdef ZCA_SUPPORTED", *lines, "#endif"]


def indirect_elp_state_update_tests(test_data: TestData, priv: Mode, covergroup: str, kind: JumpKind) -> TestChunk:
    """Every rs1 x {LPE disabled, enabled} x {LPAD, non-LPAD target} for one indirect jump kind."""
    coverpoint = f"cp_zicfilp_indirect_elp_state_update{'_c' if kind != 'jalr' else ''}"
    save_reg, temp_reg = test_data.int_regs.get_registers(2)
    tc = test_data.begin_test_chunk(_split(covergroup))
    tc.code.append(
        comment_banner(
            f"{coverpoint} ({kind})",
            f"{kind} through every rs1 (x1-x31) to an LPAD and to a non-LPAD target, with {priv}-mode xLPE = 0 and 1.\n"
            "With xLPE=1 and rs1 other than x1/x5/x7, a non-LPAD target raises a software-check exception.",
        )
    )

    body: list[str] = []
    for lpe in (0, 1):
        body.extend(set_lpe(priv, priv, temp_reg, bool(lpe)))
        for rs1 in range(1, 32):
            # jalr is an indirect jump/return (rd=x0) for odd rs1, including x1/x5/x7, and an indirect call otherwise
            rd = 0 if rs1 % 2 else 1
            for dest in ("lpad", "not_lpad"):
                target = ["lpad 0"] if dest == "lpad" else ["addi x0, x0, 0 # non-LPAD target"]
                body.extend(
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
                    ]
                )
        if lpe:
            body.extend(set_lpe(priv, priv, temp_reg, False))
    tc.code.extend(_guard_if_compressed(kind, body))
    test_data.int_regs.return_registers([save_reg, temp_reg])
    return test_data.end_test_chunk()


def lpad_label_tests(test_data: TestData, priv: Mode, covergroup: str) -> TestChunk:
    """LPAD at the target of an ELP-setting jalr, c.jr and c.jalr: LPL and x7 label combinations."""
    jump_reg, save_reg, temp_reg = test_data.int_regs.get_registers(3)
    tc = test_data.begin_test_chunk(_split(covergroup))
    lines = [
        comment_banner(
            "cp_zicfilp_lpad_*",
            f"{priv}-mode xLPE=1. Each target is reached by jalr, c.jr and c.jalr through a non-link register,\n"
            "so ELP=LP_EXPECTED. x7[31:12] holds the expected label. LPL=0 and LPL=x7[31:12] pass;\n"
            "a non-LPAD instruction, or LPL!=0 not matching x7[31:12], raises a software-check exception.",
        ),
        *set_lpe(priv, priv, temp_reg, True),
    ]
    cases = (
        ("lpl_zero_x7_zero", "cp_zicfilp_lpad_zero_label_bypass", 0, "lpad 0"),
        ("lpl_zero_x7_nonzero", "cp_zicfilp_lpad_zero_label_bypass", (LABEL << 12) | LOW_BITS, "lpad 0"),
        ("lpl_match", "cp_zicfilp_lpad_valid_execution", (LABEL << 12) | LOW_BITS, f"lpad {LABEL:#x}"),
        (
            "not_lpad",
            "cp_zicfilp_lpad_missing_instruction_exception",
            (LABEL << 12) | LOW_BITS,
            "addi x0, x0, 0 # non-LPAD",
        ),
        ("lpl_mismatch", "cp_zicfilp_lpad_label_mismatch", (LABEL << 12) | LOW_BITS, f"lpad {OTHER_LABEL:#x}"),
        ("lpl_nonzero_x7_zero", "cp_zicfilp_lpad_label_match_mismatch", 0, f"lpad {LABEL:#x}"),
    )
    for bin_name, coverpoint, x7, target in cases:
        for kind in JUMP_KINDS:
            lines.extend(
                _guard_if_compressed(
                    kind,
                    [
                        "",
                        f"LI(x7, {x7:#x}) # expected landing pad label in x7[31:12]",
                        *jump_to_target(
                            test_data,
                            kind,
                            jump_reg,
                            0,
                            [target],
                            f"{kind}_{bin_name}",
                            coverpoint,
                            covergroup,
                            save_reg,
                        ),
                    ],
                )
            )
    extra_matches = [
        ("jalr_lpl_match_all_ones", (ALL_ONES_LABEL << 12) | LOW_BITS, ALL_ONES_LABEL, None),
        ("jalr_lpl_match_x7_upper_bits_set", (0xABCD0000 << 32) | (LABEL << 12) | LOW_BITS, LABEL, "UDB_MXLEN == 64"),
    ]
    for bin_name, x7, lpl, condition in extra_matches:
        case = [
            "",
            f"LI(x7, {x7:#x}) # only x7[31:12] is compared with the label",
            *jump_to_target(
                test_data,
                "jalr",
                jump_reg,
                0,
                [f"lpad {lpl:#x}"],
                bin_name,
                "cp_zicfilp_lpad_valid_execution",
                covergroup,
                save_reg,
            ),
        ]
        lines.extend([f"#if {condition}", *case, "#endif"] if condition else case)
    lines.extend(set_lpe(priv, priv, temp_reg, False))
    tc.code.extend(lines)
    test_data.int_regs.return_registers([jump_reg, save_reg, temp_reg])
    return test_data.end_test_chunk()


def lpe_disabled_tests(test_data: TestData, priv: Mode, covergroup: str) -> TestChunk:
    """With xLPE=0, an LPAD reached by an indirect jump never checks its label."""
    coverpoint = "cp_disabled_zicfilp"
    jump_reg, save_reg, temp_reg = test_data.int_regs.get_registers(3)
    tc = test_data.begin_test_chunk(_split(covergroup))
    lines = [
        comment_banner(
            coverpoint,
            f"{priv}-mode xLPE=0: jalr, c.jr and c.jalr through a non-link register to an LPAD whose\n"
            "label does not match x7[31:12]. No exception is raised.",
        ),
        *set_lpe(priv, priv, temp_reg, False),
    ]
    for kind in JUMP_KINDS:
        lines.extend(
            _guard_if_compressed(
                kind,
                [
                    "",
                    f"LI(x7, {(LABEL << 12) | LOW_BITS:#x}) # expected landing pad label in x7[31:12]",
                    *jump_to_target(
                        test_data,
                        kind,
                        jump_reg,
                        0,
                        [f"lpad {OTHER_LABEL:#x}"],
                        f"{kind}_lpe_0_lpl_mismatch",
                        coverpoint,
                        covergroup,
                        save_reg,
                    ),
                ],
            )
        )
    tc.code.extend(lines)
    test_data.int_regs.return_registers([jump_reg, save_reg, temp_reg])
    return test_data.end_test_chunk()


def exception_priority_tests(test_data: TestData, priv: Mode, covergroup: str) -> TestChunk:
    """Instruction access fault > software-check exception > illegal-instruction exception at an LPAD target."""
    coverpoint = "cp_exception_priority_zicfilp"
    jump_reg, save_reg, temp_reg = test_data.int_regs.get_registers(3)
    tc = test_data.begin_test_chunk(_split(covergroup))
    tc.code.extend(
        [
            comment_banner(
                coverpoint,
                f"{priv}-mode xLPE=1, jalr through a non-link register:\n"
                "to RVMODEL_ACCESS_FAULT_ADDRESS, the instruction access fault is taken with xPELP=LP_EXPECTED;\n"
                "the handler resumes at ra and xRET restores ELP, so the non-LPAD instruction there traps.\n"
                "To an illegal instruction, the software-check exception is taken instead of the illegal instruction.",
            ),
            *set_lpe(priv, priv, temp_reg, True),
            "#ifdef RVMODEL_ACCESS_FAULT_ADDRESS",
            f"LA(x{jump_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
            test_data.add_testcase("instr_access_fault", coverpoint, covergroup),
            f"jalr x1, 0(x{jump_reg}) # instruction access fault; the handler resumes at ra",
            *RESUME,
            "#endif",
            "",
            *jump_to_target(
                test_data,
                "jalr",
                jump_reg,
                0,
                [".word 0xFFFFFFFF # illegal instruction target"],
                "illegal_instruction",
                coverpoint,
                covergroup,
                save_reg,
            ),
            *set_lpe(priv, priv, temp_reg, False),
        ]
    )
    test_data.int_regs.return_registers([jump_reg, save_reg, temp_reg])
    return test_data.end_test_chunk()


def lpad_nop_tests(test_data: TestData, priv: Mode, covergroup: str) -> TestChunk:
    """With xLPE=1 but ELP=NO_LP_EXPECTED, an LPAD is a no-op whatever its label or alignment."""
    coverpoint = "cp_lpad_nop_no_lp_expected_zicfilp"
    temp_reg = test_data.int_regs.get_register()
    tc = test_data.begin_test_chunk(_split(covergroup))
    tc.code.extend(
        [
            comment_banner(
                coverpoint,
                f"{priv}-mode xLPE=1 and no Indirect_CT before the LPAD, so ELP=NO_LP_EXPECTED. An LPAD whose label\n"
                "does not match x7[31:12] and, with Zca, an LPAD at pc[1:0]=2 are no-ops: no software-check exception.",
            ),
            *set_lpe(priv, priv, temp_reg, True),
            f"LI(x7, {(LABEL << 12):#x}) # expected landing pad label in x7[31:12]",
            test_data.add_testcase("lpl_mismatch", coverpoint, covergroup),
            f"lpad {OTHER_LABEL:#x} # label mismatch, but ELP=NO_LP_EXPECTED",
            "#ifdef ZCA_SUPPORTED",
            ".p2align 2",
            test_data.add_testcase("misaligned", coverpoint, covergroup),
            *arch_block(
                [
                    "c.nop # puts the lpad at pc[1:0]=2",
                    "lpad 0 # lpad 0 at pc[1:0]=2, but ELP=NO_LP_EXPECTED",
                ],
                "zca",
            ),
            "#endif",
            *set_lpe(priv, priv, temp_reg, False),
        ]
    )
    test_data.int_regs.return_registers([temp_reg])
    return test_data.end_test_chunk()


def lpad_alignment_tests(test_data: TestData, priv: Mode, covergroup: str) -> TestChunk:
    """With Zca an indirect jump may reach an LPAD at pc[1:0]=2, which raises a software-check exception."""
    coverpoint = "cp_lpad_alignment_exception_zicfilp"
    jump_reg, temp_reg = test_data.int_regs.get_registers(2)
    tc = test_data.begin_test_chunk(_split(covergroup))
    lines = [
        "#ifdef ZCA_SUPPORTED",
        comment_banner(
            coverpoint,
            f"{priv}-mode xLPE=1: jalr, c.jr and c.jalr through a non-link register to an lpad 0 that is\n"
            "2-byte but not 4-byte aligned. The misaligned LPAD raises a software-check exception. xRET restores\n"
            "ELP, so the c.nop after it traps again, and the aligned lpad after that clears ELP.",
        ),
        *set_lpe(priv, priv, temp_reg, True),
    ]
    for kind in JUMP_KINDS:
        test_data.add_testcase(f"{kind}_misaligned_lpad", coverpoint, covergroup)
        label = test_data.current_testcase_label
        lines.extend(
            [
                "",
                f"LA(x{jump_reg}, {label}_target)",
                f"{label}:",
                *(arch_block([f"{kind} x{jump_reg}"], "zca") if kind != "jalr" else [f"jalr x0, 0(x{jump_reg})"]),
                ".p2align 2",
                *arch_block(["c.nop # never executed: puts the lpad at pc[1:0]=2"], "zca"),
                f"{label}_target:",
                "lpad 0 # lpad 0 at pc[1:0]=2: software-check exception",
                *arch_block(["c.nop # ELP restored by xRET, so software-check exception"], "zca"),
                "lpad 0 # 4-byte aligned: clears ELP",
                "addi x0, x0, 0 # ELP must be NO_LP_EXPECTED here",
            ]
        )
    lines.extend(
        [
            *set_lpe(priv, priv, temp_reg, False),
            "#endif",
        ]
    )
    tc.code.extend(lines)
    test_data.int_regs.return_registers([jump_reg, temp_reg])
    return test_data.end_test_chunk()


def direct_jump_tests(test_data: TestData, priv: Mode, covergroup: str) -> TestChunk:
    """Direct jumps and taken branches are not indirect jumps, so they leave ELP=NO_LP_EXPECTED."""
    coverpoint = "cp_zicfilp_direct_ct_no_elp"
    temp_reg = test_data.int_regs.get_register()
    tc = test_data.begin_test_chunk(_split(covergroup))
    lines = [
        comment_banner(
            coverpoint,
            f"{priv}-mode xLPE=1: jal, c.j, c.jal and a taken branch to a non-LPAD target. Only indirect jumps\n"
            "set ELP=LP_EXPECTED, so the target and the nop after it execute without a software-check exception.",
        ),
        *set_lpe(priv, priv, temp_reg, True),
    ]
    # Every jump skips the instruction after it, so a taken branch is distinguishable from falling through.
    # Compressed jumps enable Zca for their own lines. c.jal exists only on RV32.
    skip = "addi x0, x0, 0 # skipped"
    cases = [
        ("jal_x0", ["jal x0, {target}", skip], None),
        ("jal_x1", ["jal x1, {target}", skip], None),
        ("c_j", arch_block(["c.j {target}", "c.nop # skipped"], "zca"), "defined(ZCA_SUPPORTED)"),
        (
            "c_jal",
            arch_block(["c.jal {target}", "c.nop # skipped"], "zca"),
            "defined(ZCA_SUPPORTED) && UDB_MXLEN == 32",
        ),
        ("branch_taken", ["beq x0, x0, {target}", skip], None),
    ]
    for bin_name, jump_lines, condition in cases:
        label = test_data.add_testcase(bin_name, coverpoint, covergroup)
        target_label = f"{test_data.current_testcase_label}_target"
        case = [
            "",
            ".p2align 2",
            label,
            *(line.format(target=target_label) for line in jump_lines),
            ".p2align 2",
            f"{target_label}:",
            "addi x0, x0, 0 # non-LPAD target",
            *RESUME,
        ]
        lines.extend([f"#if {condition}", *case, "#endif"] if condition else case)
    lines.extend(set_lpe(priv, priv, temp_reg, False))
    tc.code.extend(lines)
    test_data.int_regs.return_registers([temp_reg])
    return test_data.end_test_chunk()


def make_zicfilp_tests(test_data: TestData, priv: Mode, covergroup: str) -> list[TestChunk]:
    """Tests shared by every Zicfilp suite"""
    return [
        *(indirect_elp_state_update_tests(test_data, priv, covergroup, kind) for kind in JUMP_KINDS),
        direct_jump_tests(test_data, priv, covergroup),
        lpad_label_tests(test_data, priv, covergroup),
        lpe_disabled_tests(test_data, priv, covergroup),
        exception_priority_tests(test_data, priv, covergroup),
        lpad_nop_tests(test_data, priv, covergroup),
        lpad_alignment_tests(test_data, priv, covergroup),
    ]


def trap_entry_tests(test_data: TestData, priv: Mode, covergroup: str) -> TestChunk:
    """A trap taken with ELP=NO_LP_EXPECTED saves xPELP=0, so xRET does not restore ELP."""
    coverpoint = "cp_pelp_trap_entry_zicfilp"
    temp_reg = test_data.int_regs.get_register()
    tc = test_data.begin_test_chunk(_split(covergroup))
    tc.code.extend(
        [
            comment_banner(
                coverpoint,
                f"Illegal instruction in {priv}-mode with xLPE=1 and ELP=NO_LP_EXPECTED saves xPELP=0.\n"
                "The non-LPAD instruction after it would trap if xRET wrongly restored ELP=LP_EXPECTED.",
            ),
            *set_lpe(priv, priv, temp_reg, True),
            test_data.add_testcase("illegal_no_lp_expected", coverpoint, covergroup),
            ".word 0x00000000 # illegal instruction",
            *RESUME,
            *set_lpe(priv, priv, temp_reg, False),
        ]
    )
    test_data.int_regs.return_registers([temp_reg])
    return test_data.end_test_chunk()


def guarded_trap_entry_tests(test_data: TestData, priv: Mode, covergroup: str) -> TestChunk:
    """Software-guarded branches (rs1 = x1/x5/x7) do not set ELP, so a trap at the target saves xPELP=0."""
    coverpoint = "cp_pelp_trap_entry_guarded_zicfilp"
    save_reg, temp_reg = test_data.int_regs.get_registers(2)
    tc = test_data.begin_test_chunk(_split(covergroup))
    lines = [
        comment_banner(
            coverpoint,
            f"{priv}-mode xLPE=1: jalr, c.jr, and c.jalr through x1, x5, and x7 to an illegal instruction.\n"
            "No landing pad is required, so the illegal instruction is taken (not a software-check exception) "
            "with xPELP=0.",
        ),
        *set_lpe(priv, priv, temp_reg, True),
    ]
    for kind in JUMP_KINDS:
        cp = coverpoint + ("" if kind == "jalr" else "_c")
        body: list[str] = []
        for rs1 in (1, 5, 7):
            body.extend(
                [
                    "",
                    *jump_to_target(
                        test_data,
                        kind,
                        rs1,
                        0,
                        [".word 0x00000000 # illegal instruction"],
                        f"{kind}_x{rs1}",
                        cp,
                        covergroup,
                        save_reg,
                    ),
                ]
            )
        lines.extend(_guard_if_compressed(kind, body))
    lines.extend(set_lpe(priv, priv, temp_reg, False))
    tc.code.extend(lines)
    test_data.int_regs.return_registers([save_reg, temp_reg])
    return test_data.end_test_chunk()


def elp_state_preservation_tests(test_data: TestData, priv: Mode, covergroup: str) -> TestChunk:
    """Traps from a lower mode into `priv` save ELP in xPELP; xRET restores it."""
    coverpoint = "cp_elp_state_preservation_zicfilp"
    origins = ("S", "U") if priv == "M" else ("U",)
    jump_reg, temp_reg = test_data.int_regs.get_registers(2)
    tc = test_data.begin_test_chunk(_split(covergroup))
    lines = [
        comment_banner(
            coverpoint,
            f"xLPE=1 in {'/'.join(origins)}-mode, whose traps are taken in {priv}-mode:\n"
            f"jalr through a non-link register to a non-LPAD instruction traps into {priv}-mode with xPELP=LP_EXPECTED.\n"
            "xRET restores ELP, so the next non-LPAD instruction traps again before the lpad.\n"
            f"The T-SBI ecall back to {priv}-mode is taken with ELP=NO_LP_EXPECTED and saves xPELP=0.",
        )
    ]
    for origin in origins:
        guard = f"{origin}_SUPPORTED" if priv == "M" else None
        body = [
            "",
            *set_lpe(priv, origin, temp_reg, True),
            f"RVTEST_TSBI_GOTO_{origin}MODE",
            f"LA(x{jump_reg}, {coverpoint}_{origin}_target)",
            test_data.add_testcase(f"from_{origin}_lp_expected", coverpoint, covergroup),
            f"jalr x0, 0(x{jump_reg})",
            ".p2align 2",
            f"{coverpoint}_{origin}_target:",
            f"addi x0, x0, 0 # non-LPAD target: software-check exception into {priv}-mode",
            *RESUME,
            test_data.add_testcase(f"from_{origin}_no_lp_expected", coverpoint, covergroup),
            f"RVTEST_TSBI_GOTO_{priv}MODE",
            *set_lpe(priv, origin, temp_reg, False),
        ]
        lines.extend([f"#ifdef {guard}", *body, "#endif"] if guard else body)
    tc.code.extend(lines)
    test_data.int_regs.return_registers([jump_reg, temp_reg])
    return test_data.end_test_chunk()


def _set_xret_status(priv: Priv, target: Mode, pelp: Literal[0, 1], reg: int) -> list[str]:
    """Set xPP to the xRET target mode and xPELP to pelp."""
    if priv == "S":
        return [
            f"# sstatus.SPP = {target}-mode, sstatus.SPELP = {pelp}",
            f"LI(x{reg}, SSTATUS_SPP)",
            f"{'csrs' if target == 'S' else 'csrc'} sstatus, x{reg}",
            f"LI(x{reg}, SSTATUS_SPELP)",
            f"{'csrs' if pelp else 'csrc'} sstatus, x{reg}",
        ]
    mpp = {"M": 3, "S": 1, "U": 0}[target]
    op = "csrs" if pelp else "csrc"
    return [
        f"# mstatus.MPP = {target}-mode, mstatus.MPELP = {pelp} (mstatush.MPELP on RV32)",
        f"LI(x{reg}, MSTATUS_MPP)",
        f"csrc mstatus, x{reg}",
        f"LI(x{reg}, {mpp << 11:#x})",
        f"csrs mstatus, x{reg}",
        "#if __riscv_xlen == 64",
        f"LI(x{reg}, MSTATUS_MPELP)",
        f"{op} mstatus, x{reg}",
        "#else",
        f"LI(x{reg}, MSTATUSH_MPELP)",
        f"{op} mstatush, x{reg}",
        "#endif",
    ]


def _record_pelp_after_xret(test_data: TestData, priv: Priv, reg: int, mask_reg: int) -> list[str]:
    """Record xPELP after an xRET to the same mode; xRET must clear it."""
    if priv == "S":
        return [
            "# SRET cleared sstatus.SPELP",
            f"csrr x{reg}, sstatus",
            f"LI(x{mask_reg}, SSTATUS_SPELP)",
            f"and x{reg}, x{reg}, x{mask_reg}",
            write_sigupd(reg, test_data),
        ]
    return [
        "# MRET cleared mstatus.MPELP (mstatush.MPELP on RV32)",
        "#if __riscv_xlen == 64",
        f"csrr x{reg}, mstatus",
        f"LI(x{mask_reg}, MSTATUS_MPELP)",
        "#else",
        f"csrr x{reg}, mstatush",
        f"LI(x{mask_reg}, MSTATUSH_MPELP)",
        "#endif",
        f"and x{reg}, x{reg}, x{mask_reg}",
        write_sigupd(reg, test_data),
    ]


def _trap_return_cases(
    test_data: TestData,
    priv: Priv,
    covergroup: str,
    targets: tuple[Mode, ...],
    lpe_modes: tuple[Mode, ...],
    suffix: str,
    temp_reg: int,
    mask_reg: int,
) -> list[str]:
    """xRET to each target x every combination of the xLPE bits in lpe_modes x xPELP."""
    coverpoint = "cp_pelp_trap_return_zicfilp"
    xret = "mret" if priv == "M" else "sret"
    xepc = "mepc" if priv == "M" else "sepc"
    lines: list[str] = []
    for target in targets:
        guard = f"{target}_SUPPORTED" if priv == "M" and suffix == "" and target != "M" else None
        body: list[str] = []
        for lpes in product((0, 1), repeat=len(lpe_modes)):
            lpe_name = "_".join(f"{mode.lower()}lpe{lpe}" for mode, lpe in zip(lpe_modes, lpes))
            for pelp in (0, 1):
                test_data.add_testcase(f"{xret}_to_{target}_{lpe_name}_pelp_{pelp}{suffix}", coverpoint, covergroup)
                label = test_data.current_testcase_label
                body.extend(["", *_set_xret_status(priv, target, pelp, temp_reg)])
                for mode, lpe in zip(lpe_modes, lpes):
                    body.extend(set_lpe(priv, mode, temp_reg, bool(lpe)))
                body.extend(
                    [
                        f"LA(x{temp_reg}, {label}_target)",
                        f"csrw {xepc}, x{temp_reg}",
                        f"{label}:",
                        xret,
                        ".p2align 2",
                        f"{label}_target:",
                        f"addi x0, x0, 0 # software-check exception only if xPELP=1 and {target}-mode xLPE=1",
                        "lpad 0 # resume point after the software-check exception",
                        *(
                            _record_pelp_after_xret(test_data, priv, temp_reg, mask_reg)
                            if target == priv
                            else [f"RVTEST_TSBI_GOTO_{priv}MODE"]
                        ),
                    ]
                )
                for mode, lpe in zip(lpe_modes, lpes):
                    if lpe:
                        body.extend(set_lpe(priv, mode, temp_reg, False))
        lines.extend([f"#ifdef {guard}", *body, "#endif"] if guard else body)
    return lines


def async_interrupt_tests(test_data: TestData, covergroup: str) -> TestChunk:
    """An interrupt taken right after an MRET that restored ELP=LP_EXPECTED saves MPELP=1."""
    coverpoint = "cp_elp_async_interrupt_zicfilp"
    temp_reg, save_reg, mie_reg = test_data.int_regs.get_registers(3)
    tc = test_data.begin_test_chunk(_split(covergroup))
    tc.code.extend(
        [
            "#ifdef S_SUPPORTED",
            comment_banner(
                coverpoint,
                "MRET to S-mode with MPELP=1 and menvcfg.LPE=1 restores ELP=LP_EXPECTED, while an S-mode software\n"
                "interrupt is pending, enabled and not delegated. Interrupts are evaluated right after the MRET, so the\n"
                "interrupt is taken before the non-LPAD target and saves MPELP=1. Returning from it restores ELP, so the\n"
                "target then raises a software-check exception. A hart that does not save ELP on interrupts takes one trap.",
            ),
            *set_lpe("M", "S", temp_reg, True),
            f"csrrci x{mie_reg}, mstatus, MSTATUS_MIE # the SSI must not be taken in M-mode",
            f"csrr x{save_reg}, mideleg",
            "csrci mideleg, 1 << 1 # SSI is taken in M-mode",
            "csrsi mie, 1 << 1     # mie.SSIE",
            "RVTEST_SET_SSW_INT_M  # pending, but not taken in M-mode with mstatus.MIE=0",
            *_set_xret_status("M", "S", 1, temp_reg),
            f"LA(x{temp_reg}, {coverpoint}_target)",
            f"csrw mepc, x{temp_reg}",
            test_data.add_testcase("mret_to_s_pelp_1_ssi_pending", coverpoint, covergroup),
            "mret",
            ".p2align 2",
            f"{coverpoint}_target:",
            "addi x0, x0, 0 # SSI taken here first; then a software-check exception",
            "lpad 0         # resume point after the software-check exception",
            "RVTEST_TSBI_GOTO_MMODE",
            "csrci mie, 1 << 1",
            f"csrw mideleg, x{save_reg}",
            f"andi x{mie_reg}, x{mie_reg}, MSTATUS_MIE",
            f"csrs mstatus, x{mie_reg} # restore mstatus.MIE",
            *set_lpe("M", "S", temp_reg, False),
            "#endif",
        ]
    )
    test_data.int_regs.return_registers([temp_reg, save_reg, mie_reg])
    return test_data.end_test_chunk()


def trap_return_tests(test_data: TestData, priv: Priv, covergroup: str) -> TestChunk:
    """xRET sets ELP=xPELP only if xLPE of the new mode is 1, and clears xPELP."""
    coverpoint = "cp_pelp_trap_return_zicfilp"
    temp_reg, mask_reg = test_data.int_regs.get_registers(2)
    tc = test_data.begin_test_chunk(_split(covergroup))
    lines = [
        comment_banner(
            coverpoint,
            f"{'MRET' if priv == 'M' else 'SRET'} to each lower-or-equal mode x every combination of the xLPE bits\n"
            "x xPELP = {0, 1}, returning to a non-LPAD instruction. Only xPELP=1 with xLPE=1 of the new mode\n"
            "restores ELP=LP_EXPECTED and raises a software-check exception. A return to the same mode also\n"
            "records xPELP, which the xRET must have cleared.",
        )
    ]
    if priv == "M":
        lines.extend(
            [
                "#ifdef S_SUPPORTED",
                *_trap_return_cases(
                    test_data, "M", covergroup, ("M", "S", "U"), ("M", "S", "U"), "", temp_reg, mask_reg
                ),
                "#elif defined(U_SUPPORTED)",
                *_trap_return_cases(test_data, "M", covergroup, ("M", "U"), ("M", "U"), "_no_s", temp_reg, mask_reg),
                "#else",
                *_trap_return_cases(test_data, "M", covergroup, ("M",), ("M",), "_m_only", temp_reg, mask_reg),
                "#endif",
            ]
        )
    else:  # priv == "S"
        lines.extend(_trap_return_cases(test_data, "S", covergroup, ("S", "U"), ("S", "U"), "", temp_reg, mask_reg))
    tc.code.extend(lines)
    test_data.int_regs.return_registers([temp_reg, mask_reg])
    return test_data.end_test_chunk()


@add_priv_test_generator(
    "Zicfilp",
    required_extensions=["Sm", "Zicfilp"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_zicfilpsm(test_data: TestData) -> list[TestChunk]:
    """Generate Zicfilp landing pad tests in M-mode."""
    covergroup = "Zicfilp_Sm_cg"
    return [
        *make_zicfilp_tests(test_data, "M", covergroup),
        trap_entry_tests(test_data, "M", covergroup),
        guarded_trap_entry_tests(test_data, "M", covergroup),
        elp_state_preservation_tests(test_data, "M", covergroup),
        trap_return_tests(test_data, "M", covergroup),
        async_interrupt_tests(test_data, covergroup),
    ]


@add_priv_test_generator(
    "Zicfilp",
    required_extensions=["S", "Zicfilp"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_zicfilps(test_data: TestData) -> list[TestChunk]:
    """Generate Zicfilp landing pad tests in S-mode."""
    covergroup = "Zicfilp_S_cg"
    return [
        *make_zicfilp_tests(test_data, "S", covergroup),
        trap_entry_tests(test_data, "S", covergroup),
        guarded_trap_entry_tests(test_data, "S", covergroup),
        elp_state_preservation_tests(test_data, "S", covergroup),
        trap_return_tests(test_data, "S", covergroup),
    ]


@add_priv_test_generator(
    "Zicfilp",
    required_extensions=["U", "Zicfilp"],
)
def make_zicfilpu(test_data: TestData) -> list[TestChunk]:
    """Generate Zicfilp landing pad tests in U-mode."""
    return make_zicfilp_tests(test_data, "U", "Zicfilp_U_cg")
