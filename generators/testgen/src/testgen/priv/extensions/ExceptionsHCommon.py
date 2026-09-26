##################################
# priv/extensions/ExceptionsHCommon.py
#
# Shared test generation for the hypervisor exception suites.
# David_Harris@hmc.edu 24 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared test generation for the hypervisor exception suites (ExceptionsH, ExceptionsHSm, ExceptionsHF, ExceptionsHV).

Modes are named as the T-SBI GOTO macros name them: m, s (HS), vs, u and vu.
"""

from collections.abc import Callable, Sequence

from testgen.asm.csr import gen_csr_read_sigupd
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.priv.extensions.ExceptionsCommon import generate_delegated_fault_tests
from testgen.priv.extensions.HCommon import gated

# hedeleg bits 0-8, 12, 13, 15, 18 and 19, which the spec requires to be writable (bit 0 only with IALIGN = 32)
HEDELEG_WRITABLE = 0xCB1FF

# hedeleg values: none, each of bits 0-8 alone, and all writable bits
HEDELEG_WALK = (0, *(1 << bit for bit in range(9)), HEDELEG_WRITABLE)

# Upper bound on traps from one generate_delegated_fault_tests call (RV64)
DELEGATED_FAULTS = 105


def hedeleg_tests(
    test_data: TestData, covergroup: str, mode: str, home: str, values: Sequence[int] = HEDELEG_WALK
) -> list[str]:
    """cp_hedeleg: raise each exception in mode with each hedeleg value, written in the home mode."""
    save_reg, val_reg, addr_reg, data_reg, check_reg = test_data.int_regs.get_registers(5)
    lines = [
        comment_banner(
            f"cp_hedeleg ({mode.upper()}-mode)",
            f"Raise each exception in {mode.upper()}-mode with hedeleg = {', '.join(f'{v:#x}' for v in values)}",
        ),
        f"csrr x{save_reg}, hedeleg",
    ]
    for value in values:
        lines.extend(
            [
                f"LI(x{val_reg}, {value:#x})",
                f"csrw hedeleg, x{val_reg}",
                *([f"RVTEST_TSBI_GOTO_{mode.upper()}MODE"] if mode != home else []),
                *generate_delegated_fault_tests(
                    test_data, f"hdlg_{value:#07x}_{mode}", "cp_hedeleg", covergroup, (addr_reg, data_reg, check_reg)
                ),
                *([f"RVTEST_TSBI_GOTO_{home.upper()}MODE"] if mode != home else []),
            ]
        )
    lines.append(f"csrw hedeleg, x{save_reg}")
    test_data.int_regs.return_registers([save_reg, val_reg, addr_reg, data_reg, check_reg])
    return lines


def hlv_priority_tests(test_data: TestData, covergroup: str, mode: str, home: str) -> list[str]:
    """cp_loadstore_priv and cp_priority: hlv.w, hlvx.wu and hsv.w in mode with hstatus.HU = 0 and 1.

    vsatp and hgatp are Bare, so each guest virtual address is a physical address.  cp_priority accesses a word of
    scratch and the access-fault address, aligned and misaligned.  hsv.w results are read back from scratch.
    """
    addr_reg, data_reg, rd = test_data.int_regs.get_registers(3)
    lines = [
        comment_banner(
            f"cp_loadstore_priv, cp_priority ({mode.upper()}-mode)",
            f"In {mode.upper()}-mode with hstatus.HU = 0 and 1, execute hlv.w, hlvx.wu and hsv.w on scratch, then\n"
            "hlv.w and hsv.w on aligned and misaligned legal and access-fault addresses",
        )
    ]
    for hu in (0, 1):
        suffix = f"{mode}_hu{hu}"
        lines.extend(
            [
                f"LI(x{data_reg}, HSTATUS_HU)",
                f"{'csrs' if hu else 'csrc'} hstatus, x{data_reg}",
                *([f"RVTEST_TSBI_GOTO_{mode.upper()}MODE"] if mode != home else []),
                f"LA(x{addr_reg}, scratch)",
            ]
        )
        for instr in ("hlv.w", "hlvx.wu"):
            lines.extend(
                [
                    f"LI(x{rd}, 42)",
                    test_data.add_testcase(f"{instr}_{suffix}", "cp_loadstore_priv", covergroup),
                    f"{instr} x{rd}, (x{addr_reg})",
                    write_sigupd(rd, test_data),
                ]
            )
        lines.extend(
            [
                f"LI(x{data_reg}, {0x5EED0000 + hu:#x})",
                test_data.add_testcase(f"hsv.w_{suffix}", "cp_loadstore_priv", covergroup),
                f"hsv.w x{data_reg}, (x{addr_reg})",
                f"lw x{rd}, 0(x{addr_reg})",
                write_sigupd(rd, test_data),
            ]
        )
        for legal, base in ((True, "scratch"), (False, "RVMODEL_ACCESS_FAULT_ADDRESS")):
            for offset in (0, 1):
                name = f"{'legal' if legal else 'illegal'}_off{offset}_{suffix}"
                body = [
                    f"LA(x{addr_reg}, {base})",
                    f"addi x{addr_reg}, x{addr_reg}, {offset}",
                    f"LI(x{rd}, 42)",
                    test_data.add_testcase(f"hlv.w_{name}", "cp_priority", covergroup),
                    f"hlv.w x{rd}, (x{addr_reg})",
                    write_sigupd(rd, test_data),
                    f"LI(x{data_reg}, {0x600D0000 + 2 * offset + hu:#x})",
                    test_data.add_testcase(f"hsv.w_{name}", "cp_priority", covergroup),
                    f"hsv.w x{data_reg}, (x{addr_reg})",
                ]
                if legal:
                    body.append(f"LA(x{addr_reg}, scratch)")
                    for word in (0, 4):
                        body.extend([f"lw x{rd}, {word}(x{addr_reg})", write_sigupd(rd, test_data)])
                lines.extend(gated(body, None if legal else "defined(RVMODEL_ACCESS_FAULT_ADDRESS)"))
        lines.extend([f"RVTEST_TSBI_GOTO_{home.upper()}MODE"] if mode != home else [])
    lines.extend([f"LI(x{data_reg}, HSTATUS_HU)", f"csrc hstatus, x{data_reg}"])
    test_data.int_regs.return_registers([addr_reg, data_reg, rd])
    return lines


def xtinst_exception_tests(test_data: TestData, covergroup: str, home: str) -> list[str]:
    """cp_xtinst_*: exceptions from VS-mode with hedeleg = 0, taken in HS-mode (home "s") or M-mode (home "m").

    Before each one, the home mode writes a nonzero value to htval and htinst (mtval2 and mtinst) and enters VS-mode.
    The trap record holds the values the exception writes.
    """
    addr_reg, data_reg, rd, rand_reg, temp_reg = test_data.int_regs.get_registers(5)
    tval2, tinst = ("mtval2", "mtinst") if home == "m" else ("htval", "htinst")
    # M-mode enters VS-mode by mret; a T-SBI call would overwrite mtval2 and mtinst
    enter_vs = (
        [
            f"LI(x{temp_reg}, MSTATUS_MPP)",
            f"csrc mstatus, x{temp_reg}",
            f"LI(x{temp_reg}, MPP_SMODE)",
            f"csrs mstatus, x{temp_reg}",
            "#if __riscv_xlen == 64",
            f"LI(x{temp_reg}, MSTATUS_MPV)",
            f"csrs mstatus, x{temp_reg}",
            "#else",
            f"LI(x{temp_reg}, MSTATUSH_MPV)",
            f"csrs mstatush, x{temp_reg}",
            "#endif",
            f"LA(x{temp_reg}, 1f)",
            f"csrw mepc, x{temp_reg}",
            "mret",
            "1:",
        ]
        if home == "m"
        else ["RVTEST_TSBI_GOTO_VSMODE"]
    )
    fault = f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)"
    fault_gate = "defined(RVMODEL_ACCESS_FAULT_ADDRESS)"
    # Misaligned fetches trap only when IALIGN = 32, and misaligned loads and stores only when the hart does not
    # perform them
    misaligned_ldst_gate = "!defined(UDB_MISALIGNED_LDST)"
    # (coverpoint suffix, gate, setup, trapping instruction, result check: None, "rd" or "store")
    cases = [
        (
            "instr_misaligned",
            "!defined(ZCA_SUPPORTED)",
            [".p2align 2"],
            ["jal x0, .+6", "addi x0, x2, 0", "nop"],
            None,
        ),
        ("instr_access", fault_gate, [fault], [f"jalr x1, 0(x{addr_reg})"], None),
        ("illegalinstr", None, [".p2align 2"], [".word 0x00000000"], None),
        ("breakpoint", None, [], ["ebreak"], None),
        ("virtinstr", None, [f"LI(x{rd}, 42)"], [f"csrr x{rd}, vstval"], "rd"),
        (
            "load_misaligned",
            misaligned_ldst_gate,
            [f"LA(x{addr_reg}, scratch)", f"LI(x{rd}, 42)"],
            [f"lw x{rd}, 1(x{addr_reg})"],
            "rd",
        ),
        ("load_access", fault_gate, [fault, f"LI(x{rd}, 42)"], [f"lw x{rd}, 0(x{addr_reg})"], "rd"),
        (
            "store_misaligned",
            misaligned_ldst_gate,
            [f"LA(x{addr_reg}, scratch)", f"LI(x{data_reg}, 0xC0FFEE11)"],
            [f"sw x{data_reg}, 1(x{addr_reg})"],
            "store",
        ),
        (
            "store_access",
            fault_gate,
            [fault, f"LI(x{data_reg}, 0xC0FFEE22)"],
            [f"sw x{data_reg}, 0(x{addr_reg})"],
            None,
        ),
        ("ecall", None, [], ["RVTEST_TSBI_ECALL_RECORD"], None),
    ]
    lines = [
        comment_banner(
            "cp_xtinst_*",
            f"From VS-mode with hedeleg = 0, raise each exception into {'M' if home == 'm' else 'HS'}-mode after "
            f"writing a nonzero value\nto {tval2} and {tinst}.  The trap record holds {tval2} (zero) and {tinst} "
            "(zero or a transformed load or store)",
        ),
        "csrw hedeleg, zero",
        f"LI(x{rand_reg}, 0x5A5A5A5B)",
    ]
    for name, gate, setup, instr, check in cases:
        body = [
            f"csrw {tval2}, x{rand_reg}",
            f"csrw {tinst}, x{rand_reg}",
            *enter_vs,
            *setup,
            test_data.add_testcase("vs", f"cp_xtinst_{name}", covergroup),
            *instr,
        ]
        if check == "rd":
            body.append(write_sigupd(rd, test_data))
        elif check == "store":
            for word in (0, 4):
                body.extend([f"lw x{rd}, {word}(x{addr_reg})", write_sigupd(rd, test_data)])
        body.append(f"RVTEST_TSBI_GOTO_{home.upper()}MODE")
        lines.extend(gated(body, gate))
    test_data.int_regs.return_registers([addr_reg, data_reg, rd, rand_reg, temp_reg])
    return lines


def xstatus_tests(
    test_data: TestData,
    field: str,
    body: Callable[[str, int], list[str]],
    check: Callable[[int], list[str]] | None = None,
) -> list[str]:
    """Run body in HS, VS, U and VU with each mstatus.<field> and vsstatus.<field>; record both, then run check."""
    mask = f"MSTATUS_{field}"
    shift = 13 if field == "FS" else 9
    temp_reg, rd = test_data.int_regs.get_registers(2)
    lines = []
    for mode in ("s", "vs", "u", "vu"):
        for mval in range(4):
            for vsval in range(4):
                lines.extend(
                    [
                        f"RVTEST_TSBI_CSR_CLEAR(CSR_MSTATUS, {mask})",
                        *([f"RVTEST_TSBI_CSR_SET(CSR_MSTATUS, {mval << shift:#x})"] if mval else []),
                        f"LI(x{temp_reg}, {mask})",
                        f"csrc vsstatus, x{temp_reg}",
                        f"LI(x{temp_reg}, {vsval << shift:#x})",
                        f"csrs vsstatus, x{temp_reg}",
                        *([f"RVTEST_TSBI_GOTO_{mode.upper()}MODE"] if mode != "s" else []),
                        *body(f"{mode}_m{mval}_vs{vsval}", rd),
                        *(["RVTEST_TSBI_GOTO_SMODE"] if mode != "s" else []),
                        f"LI(x{temp_reg}, {mask})",
                        gen_csr_read_sigupd(rd, ("sstatus", 3 << shift), test_data, temp_reg),
                        gen_csr_read_sigupd(rd, ("vsstatus", 3 << shift), test_data, temp_reg),
                        *(check(rd) if check else []),
                    ]
                )
    test_data.int_regs.return_registers([temp_reg, rd])
    return lines
