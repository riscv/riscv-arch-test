##################################
# priv/extensions/ZicfilpH.py
#
# ZicfilpH landing pad tests in VS-mode and VU-mode.
# David_Harris@hmc.edu 29 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZicfilpH test generator.

The suite boots to HS-mode and sets the landing pad enables from there: menvcfg.LPE through T-SBI, henvcfg.LPE
and senvcfg.LPE directly.  henvcfg.LPE enables landing pads in VS-mode and senvcfg.LPE in VU-mode.  hedeleg is 0,
so software-check exceptions are taken in HS-mode, except where a test delegates them to VS-mode.

A trap into VS-mode saves ELP in vsstatus.SPELP and a trap into HS-mode saves it in sstatus.SPELP.  An SRET
executed in VS-mode restores ELP from vsstatus.SPELP and one executed in HS-mode from sstatus.SPELP, in either
case only if the landing pad enable of the mode it returns to is 1.  The trap record does not hold SPELP, so the
tests observe it through the instruction after the handler returns: it raises a software-check exception
exactly when ELP was restored to LP_EXPECTED.  check_trap_count records the number of traps after each case.
"""

from itertools import product

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZicfilpCommon import (
    JUMP_KINDS,
    LABEL,
    LOW_BITS,
    OTHER_LABEL,
    RESUME,
    check_trap_count,
    jump_to_target,
)
from testgen.priv.registry import add_priv_test_generator

_CG = "ZicfilpH_cg"
# Targets of an ELP-setting indirect jump: a software-check exception whenever the landing pad enable is 1
_TARGETS = {
    "not_lpad": "addi x0, x0, 0 # non-LPAD target",
    "lpad_mismatch": f"lpad 0x{OTHER_LABEL:x} # label does not match x7[31:12]",
}
_X7_LABEL = f"LI(x7, 0x{(LABEL << 12) | LOW_BITS:x}) # expected landing pad label in x7[31:12]"


def _set_lpe(csr: str, enable: int, reg: int) -> list[str]:
    """Set or clear the LPE bit of menvcfg (through T-SBI), henvcfg or senvcfg from HS-mode."""
    if csr == "menvcfg":
        return [f"RVTEST_TSBI_CSR_{'SET' if enable else 'CLEAR'}(CSR_MENVCFG, MENVCFG_LPE)"]
    return [f"LI(x{reg}, {csr.upper()}_LPE)", f"{'csrs' if enable else 'csrc'} {csr}, x{reg}"]


def _compressed_guard(kind: str, lines: list[str]) -> list[str]:
    """Compressed jumps exist only with Zca."""
    return lines if kind == "jalr" else ["#ifdef ZCA_SUPPORTED", *lines, "#endif"]


def _enable_tests(test_data: TestData, mode: str) -> TestChunk:
    """Indirect jumps in VS or VU-mode to a non-LPAD instruction and to a mismatched LPAD, for each value of the
    enable that applies to the mode and of one that does not."""
    coverpoint = f"cp_{mode.lower()}_lpe"
    enables = ("henvcfg", "menvcfg") if mode == "VS" else ("senvcfg", "henvcfg")
    jump_reg, save_reg, temp_reg = test_data.int_regs.get_registers(3)
    tc = test_data.begin_test_chunk()
    lines = [
        comment_banner(
            coverpoint,
            f"In {mode}-mode, jalr, c.jr and c.jalr through a non-link register to a non-LPAD instruction and to an\n"
            f"LPAD whose label does not match x7[31:12], for each value of {enables[0]}.LPE and {enables[1]}.LPE.\n"
            f"Only {enables[0]}.LPE = 1 enables landing pads in {mode}-mode: the target then raises a software-check\n"
            "exception, taken in HS-mode.  With it clear, ELP stays NO_LP_EXPECTED and the LPAD is a no-op.",
        )
    ]
    for applies, other in product((0, 1), repeat=2):
        tag = f"{enables[0]}{applies}_{enables[1]}{other}"
        lines.extend(
            [
                "",
                *_set_lpe(enables[0], applies, temp_reg),
                *_set_lpe(enables[1], other, temp_reg),
                f"RVTEST_TSBI_GOTO_{mode}MODE",
            ]
        )
        for kind in JUMP_KINDS:
            body: list[str] = []
            for dest, target in _TARGETS.items():
                body.extend(
                    [
                        _X7_LABEL,
                        *jump_to_target(
                            test_data,
                            kind,
                            jump_reg,
                            0,
                            [target],
                            f"{kind}_{tag}_{dest}",
                            coverpoint,
                            _CG,
                            save_reg,
                        ),
                        *check_trap_count(test_data, temp_reg),
                    ]
                )
            lines.extend(_compressed_guard(kind, body))
        lines.append("RVTEST_TSBI_GOTO_SMODE")
    lines.extend([*_set_lpe(enables[0], 0, temp_reg), *_set_lpe(enables[1], 0, temp_reg)])
    tc.code.extend(lines)
    test_data.int_regs.return_registers([jump_reg, save_reg, temp_reg])
    return test_data.end_test_chunk()


def _trap_entry_tests(test_data: TestData) -> TestChunk:
    """Traps from VS and VU-mode into VS-mode and HS-mode with ELP = LP_EXPECTED and NO_LP_EXPECTED."""
    coverpoint = "cp_trap_entry_spelp"
    jump_reg, temp_reg = test_data.int_regs.get_registers(2)
    tc = test_data.begin_test_chunk()
    lines = [
        comment_banner(
            coverpoint,
            "With the landing pad enable of the mode set, trap from VS-mode and VU-mode into VS-mode (hedeleg[3] =\n"
            "hedeleg[18] = 1) and into HS-mode (hedeleg = 0).  jalr through a non-link register to a non-LPAD\n"
            "instruction traps with ELP = LP_EXPECTED, which the trap saves in vsstatus.SPELP or sstatus.SPELP.  The\n"
            "handler's SRET restores it, so the next non-LPAD instruction traps again before the lpad.  An ebreak\n"
            "that no indirect jump precedes traps with ELP = NO_LP_EXPECTED, so the instruction after it does not.",
        ),
        *_set_lpe("henvcfg", 1, temp_reg),
        *_set_lpe("senvcfg", 1, temp_reg),
    ]
    for handler, mode in product(("vs", "hs"), ("VS", "VU")):
        tag = f"{mode.lower()}_to_{handler}"
        lines.extend(
            [
                "",
                f"LI(x{temp_reg}, (1 << CAUSE_BREAKPOINT) | (1 << CAUSE_SOFTWARE_CHECK_FAULT))",
                f"{'csrs' if handler == 'vs' else 'csrc'} hedeleg, x{temp_reg}",
                f"RVTEST_TSBI_GOTO_{mode}MODE",
                f"LA(x{jump_reg}, {coverpoint}_{tag}_target)",
                test_data.add_testcase(f"{tag}_lp_expected", coverpoint, _CG),
                f"jalr x0, 0(x{jump_reg})",
                ".p2align 2",
                f"{coverpoint}_{tag}_target:",
                "addi x0, x0, 0 # non-LPAD target: software-check exception",
                *RESUME,
                *check_trap_count(test_data, temp_reg),
                test_data.add_testcase(f"{tag}_no_lp_expected", coverpoint, _CG),
                "ebreak",
                *RESUME,
                *check_trap_count(test_data, temp_reg),
                "RVTEST_TSBI_GOTO_SMODE",
            ]
        )
    lines.extend(
        [
            "csrw hedeleg, zero",
            *_set_lpe("henvcfg", 0, temp_reg),
            *_set_lpe("senvcfg", 0, temp_reg),
        ]
    )
    tc.code.extend(lines)
    test_data.int_regs.return_registers([jump_reg, temp_reg])
    return test_data.end_test_chunk()


def _vs_sret_tests(test_data: TestData) -> TestChunk:
    """SRET executed in VS-mode takes the previous ELP from vsstatus.SPELP, not sstatus.SPELP."""
    coverpoint = "cp_vs_sret_spelp"
    temp_reg, mask_reg = test_data.int_regs.get_registers(2)
    tc = test_data.begin_test_chunk()
    lines = [
        comment_banner(
            coverpoint,
            "In VS-mode, write vsstatus.SPP and vsstatus.SPELP through sstatus and SRET to a non-LPAD instruction\n"
            "in VS-mode or VU-mode, for each value of henvcfg.LPE and senvcfg.LPE.  HS-mode sets sstatus.SPELP to\n"
            "the opposite value first.  Only vsstatus.SPELP = 1 with the LPE of the new mode set raises a\n"
            "software-check exception.  After an SRET to VS-mode, vsstatus.SPELP must read 0.",
        )
    ]
    for target, h_lpe, s_lpe, pelp in product(("VS", "VU"), (0, 1), (0, 1), (0, 1)):
        test_data.add_testcase(f"to_{target.lower()}_henvcfg{h_lpe}_senvcfg{s_lpe}_spelp{pelp}", coverpoint, _CG)
        label = test_data.current_testcase_label
        lines.extend(
            [
                "",
                *_set_lpe("henvcfg", h_lpe, temp_reg),
                *_set_lpe("senvcfg", s_lpe, temp_reg),
                f"LI(x{temp_reg}, SSTATUS_SPELP)",
                f"{'csrc' if pelp else 'csrs'} sstatus, x{temp_reg} # HS-mode SPELP = {1 - pelp}",
                "RVTEST_TSBI_GOTO_VSMODE",
                f"# vsstatus.SPP = {target}-mode, vsstatus.SPELP = {pelp}",
                f"LI(x{temp_reg}, SSTATUS_SPP)",
                f"{'csrs' if target == 'VS' else 'csrc'} sstatus, x{temp_reg}",
                f"LI(x{temp_reg}, SSTATUS_SPELP)",
                f"{'csrs' if pelp else 'csrc'} sstatus, x{temp_reg}",
                f"LA(x{temp_reg}, {label}_target)",
                f"csrw sepc, x{temp_reg}",
                f"{label}:",
                "sret",
                ".p2align 2",
                f"{label}_target:",
                "addi x0, x0, 0 # software-check exception only if vsstatus.SPELP = 1 and the new mode's LPE = 1",
                "lpad 0 # resume point after the software-check exception",
            ]
        )
        if target == "VS":
            lines.extend(
                [
                    "# SRET cleared vsstatus.SPELP",
                    f"csrr x{temp_reg}, sstatus",
                    f"LI(x{mask_reg}, SSTATUS_SPELP)",
                    f"and x{temp_reg}, x{temp_reg}, x{mask_reg}",
                    write_sigupd(temp_reg, test_data),
                ]
            )
        lines.extend(["RVTEST_TSBI_GOTO_SMODE", *check_trap_count(test_data, temp_reg)])
    lines.extend([*_set_lpe("henvcfg", 0, temp_reg), *_set_lpe("senvcfg", 0, temp_reg)])
    tc.code.extend(lines)
    test_data.int_regs.return_registers([temp_reg, mask_reg])
    return test_data.end_test_chunk()


def _hs_sret_tests(test_data: TestData) -> TestChunk:
    """SRET executed in HS-mode into VS or VU-mode takes the previous ELP from sstatus.SPELP, not vsstatus.SPELP."""
    coverpoint = "cp_hs_sret_spelp"
    temp_reg, mask_reg = test_data.int_regs.get_registers(2)
    tc = test_data.begin_test_chunk()
    lines = [
        comment_banner(
            coverpoint,
            "In HS-mode, set hstatus.SPV = 1, sstatus.SPP for VS-mode or VU-mode, sstatus.SPELP, and vsstatus.SPELP\n"
            "to the opposite value, then SRET to a non-LPAD instruction, for each value of henvcfg.LPE and\n"
            "senvcfg.LPE.  Only sstatus.SPELP = 1 with the LPE of the new mode set raises a software-check\n"
            "exception.  Back in HS-mode, vsstatus.SPELP must be unchanged.",
        )
    ]
    for target, h_lpe, s_lpe, pelp in product(("VS", "VU"), (0, 1), (0, 1), (0, 1)):
        test_data.add_testcase(f"to_{target.lower()}_henvcfg{h_lpe}_senvcfg{s_lpe}_spelp{pelp}", coverpoint, _CG)
        label = test_data.current_testcase_label
        lines.extend(
            [
                "",
                *_set_lpe("henvcfg", h_lpe, temp_reg),
                *_set_lpe("senvcfg", s_lpe, temp_reg),
                f"# hstatus.SPV = 1, sstatus.SPP = {target}-mode, sstatus.SPELP = {pelp}, vsstatus.SPELP = {1 - pelp}",
                f"LI(x{temp_reg}, HSTATUS_SPV)",
                f"csrs hstatus, x{temp_reg}",
                f"LI(x{temp_reg}, SSTATUS_SPP)",
                f"{'csrs' if target == 'VS' else 'csrc'} sstatus, x{temp_reg}",
                f"LI(x{temp_reg}, SSTATUS_SPELP)",
                f"{'csrs' if pelp else 'csrc'} sstatus, x{temp_reg}",
                f"{'csrc' if pelp else 'csrs'} vsstatus, x{temp_reg}",
                f"LA(x{temp_reg}, {label}_target)",
                f"csrw sepc, x{temp_reg}",
                f"{label}:",
                "sret",
                ".p2align 2",
                f"{label}_target:",
                "addi x0, x0, 0 # software-check exception only if sstatus.SPELP = 1 and the new mode's LPE = 1",
                "lpad 0 # resume point after the software-check exception",
                "RVTEST_TSBI_GOTO_SMODE",
                "# vsstatus.SPELP is unchanged",
                f"csrr x{temp_reg}, vsstatus",
                f"LI(x{mask_reg}, SSTATUS_SPELP)",
                f"and x{temp_reg}, x{temp_reg}, x{mask_reg}",
                write_sigupd(temp_reg, test_data),
                *check_trap_count(test_data, temp_reg),
            ]
        )
    lines.extend(
        [
            f"LI(x{temp_reg}, SSTATUS_SPELP)",
            f"csrc vsstatus, x{temp_reg}",
            *_set_lpe("henvcfg", 0, temp_reg),
            *_set_lpe("senvcfg", 0, temp_reg),
        ]
    )
    tc.code.extend(lines)
    test_data.int_regs.return_registers([temp_reg, mask_reg])
    return test_data.end_test_chunk()


def _sstatus_alias_tests(test_data: TestData) -> TestChunk:
    """sstatus.SPELP in VS-mode is vsstatus.SPELP."""
    coverpoint = "cp_vs_sstatus_spelp"
    temp_reg, mask_reg = test_data.int_regs.get_registers(2)
    tc = test_data.begin_test_chunk()
    lines = [
        comment_banner(
            coverpoint,
            "In VS-mode, set and then clear sstatus.SPELP and read sstatus back.  After each write, HS-mode reads\n"
            "vsstatus.SPELP, which must hold the value VS-mode wrote.",
        ),
        f"LI(x{mask_reg}, SSTATUS_SPELP)",
    ]
    for op in ("csrs", "csrc"):
        lines.extend(
            [
                "",
                "RVTEST_TSBI_GOTO_VSMODE",
                test_data.add_testcase(f"{op}_spelp", coverpoint, _CG),
                f"{op} sstatus, x{mask_reg}",
                f"csrr x{temp_reg}, sstatus",
                f"and x{temp_reg}, x{temp_reg}, x{mask_reg}",
                write_sigupd(temp_reg, test_data),
                "RVTEST_TSBI_GOTO_SMODE",
                f"csrr x{temp_reg}, vsstatus",
                f"and x{temp_reg}, x{temp_reg}, x{mask_reg}",
                write_sigupd(temp_reg, test_data),
            ]
        )
    tc.code.extend(lines)
    test_data.int_regs.return_registers([temp_reg, mask_reg])
    return test_data.end_test_chunk()


@add_priv_test_generator(
    "ZicfilpH",
    required_extensions=["H", "Zicfilp"],
    extra_defines=["#define BOOT_TO_SMODE"],
    # VS and VU traps need the visible trap handler
    params=["TIME_CSR_IMPLEMENTED: true"],
)
def make_zicfilph(test_data: TestData) -> list[TestChunk]:
    """Generate Zicfilp landing pad tests in VS-mode and VU-mode."""
    return [
        _enable_tests(test_data, "VS"),
        _enable_tests(test_data, "VU"),
        _trap_entry_tests(test_data),
        _vs_sret_tests(test_data),
        _hs_sret_tests(test_data),
        _sstatus_alias_tests(test_data),
    ]
