##################################
# priv/extensions/exceptions/ExceptionsHCommon.py
#
# Shared test generation for the H and HSm groups of the Exceptions suite.
# David_Harris@hmc.edu 24 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared test generation for the H and HSm groups of the Exceptions suite.

Modes are named as the T-SBI GOTO macros name them: m, s (HS), vs, u and vu.
"""

from collections.abc import Callable, Sequence
from typing import NamedTuple

from testgen.asm.helpers import arch_block, comment_banner, gated, write_sigupd
from testgen.data.state import TestData
from testgen.priv.extensions.exceptions.ExceptionsCommon import (
    DELEGATED_FAULT_KINDS,
    ZICFILP_LINK_REGS,
    generate_delegated_fault_tests,
    missing_lpad_tests,
)
from testgen.priv.extensions.Zicfilp import Mode, set_lpe

# hedeleg bits 0-8, 12, 13, 15, 18 and 19, which the spec requires to be writable (bit 0 only with IALIGN = 32;
# bits 18 and 19 only from Priv 1.13).  The tests write these values but never read hedeleg back.
HEDELEG_WRITABLE = 0xCB1FF

# hedeleg values: none, each of bits 0-8 alone, and all writable bits
HEDELEG_WALK = (0, *(1 << bit for bit in range(9)), HEDELEG_WRITABLE)

# The hedeleg coverpoint suffix for each exception generate_delegated_fault_tests raises
_HEDELEG_CP_SUFFIX = {
    "instrmisaligned": "instr_misaligned_jalr",
    "instraccessfault": "instr_access_fault",
    "illegalinstruction": "illegal_instruction",
    "ebreak": "breakpoint",
    "loadmisaligned": "load_misaligned",
    "loadaccessfault": "load_access_fault",
    "storemisaligned": "store_misaligned",
    "storeaccessfault": "store_access_fault",
    "ecall": "ecall",
}
assert set(_HEDELEG_CP_SUFFIX) == set(DELEGATED_FAULT_KINDS)

# Upper bound on traps from one generate_delegated_fault_tests call (RV64)
DELEGATED_FAULTS = 106


def hedeleg_tests(
    test_data: TestData, covergroup: str, mode: str, home: str, values: Sequence[int] = HEDELEG_WALK
) -> list[str]:
    """cp_hedeleg: raise each exception in mode with each hedeleg value, written in the home mode."""
    # HS-mode and U-mode walks have their own coverpoints in the H group
    prefix = "cp_hedeleg_hs_u" if mode in ("s", "u") else "cp_hedeleg"
    coverpoints = {kind: f"{prefix}_{suffix}" for kind, suffix in _HEDELEG_CP_SUFFIX.items()}
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
                    test_data, f"hdlg_{value:#07x}_{mode}", coverpoints, covergroup, (addr_reg, data_reg, check_reg)
                ),
                *([f"RVTEST_TSBI_GOTO_{home.upper()}MODE"] if mode != home else []),
            ]
        )
    lines.append(f"csrw hedeleg, x{save_reg}")
    test_data.int_regs.return_registers([save_reg, val_reg, addr_reg, data_reg, check_reg])
    return lines


# The T-SBI mode names of ExceptionsH and ExceptionsHSm, as Zicfilp names them
_ZICFILP_MODE: dict[str, Mode] = {"m": "M", "s": "S", "u": "U", "vs": "VS", "vu": "VU"}

# Traps from one software_check_tests call: two for each of 4 modes x 2 hedeleg values
SOFTWARE_CHECK_TRAPS = 16


def software_check_tests(test_data: TestData, covergroup: str, coverpoint: str, home: str) -> list[str]:
    """A missing landing pad in HS, U, VS and VU modes with hedeleg[18] = 0 and 1, set in the home mode.

    The home mode sets xLPE of the mode under test (menvcfg.LPE for HS, henvcfg.LPE for VS, senvcfg.LPE for U and
    VU) only around each case.  Each case raises two software-check exceptions (see missing_lpad_tests).
    """
    jump_reg = test_data.int_regs.get_register(exclude_regs=ZICFILP_LINK_REGS)
    temp_reg, save_reg = test_data.int_regs.get_registers(2)
    lines = [
        comment_banner(
            coverpoint,
            "With xLPE = 1 in HS, U, VS and VU modes and hedeleg[18] = 0 and 1, jalr to an instruction that is not\n"
            "an lpad: a software-check exception",
        ),
        f"csrr x{save_reg}, hedeleg",
    ]
    for mode in ("s", "u", "vs", "vu"):
        for hedeleg18 in (0, 1):
            lines.extend(
                [
                    f"LI(x{temp_reg}, {hedeleg18 << 18:#x})",
                    f"csrw hedeleg, x{temp_reg}",
                    *set_lpe(_ZICFILP_MODE[home], _ZICFILP_MODE[mode], temp_reg, True),
                    *([f"RVTEST_TSBI_GOTO_{mode.upper()}MODE"] if mode != home else []),
                    *missing_lpad_tests(test_data, f"{mode}_hedeleg18_{hedeleg18}", coverpoint, covergroup, jump_reg),
                    *([f"RVTEST_TSBI_GOTO_{home.upper()}MODE"] if mode != home else []),
                    *set_lpe(_ZICFILP_MODE[home], _ZICFILP_MODE[mode], temp_reg, False),
                ]
            )
    lines.append(f"csrw hedeleg, x{save_reg}")
    test_data.int_regs.return_registers([jump_reg, temp_reg, save_reg])
    return gated(lines, "defined(ZICFILP_SUPPORTED)")


def hlv_priority_tests(test_data: TestData, covergroup: str, mode: str, home: str) -> list[str]:
    """cp_loadstore_priv, cp_priority_hlv and cp_priority_hsv: hlv.w, hlvx.wu and hsv.w in mode with hstatus.HU = 0 and 1.

    vsatp and hgatp are Bare, so each guest virtual address is a physical address.  The cp_priority crosses access a word of
    scratch and the access-fault address, aligned and misaligned.  hsv.w results are read back from scratch.
    """
    addr_reg, data_reg, rd = test_data.int_regs.get_registers(3)
    lines = [
        comment_banner(
            f"cp_loadstore_priv, cp_priority_hlv, cp_priority_hsv ({mode.upper()}-mode)",
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
        for legal in (True, False):
            load_base = "scratch" if legal else "RVMODEL_ACCESS_FAULT_ADDRESS_LOAD"
            store_base = "scratch" if legal else "RVMODEL_ACCESS_FAULT_ADDRESS_STORE"
            for offset in (0, 1):
                name = f"{'legal' if legal else 'illegal'}_off{offset}_{suffix}"
                load_body = [
                    f"LA(x{addr_reg}, {load_base})" if legal else f"LI_FIXED_LEN(x{addr_reg}, {load_base})",
                    f"addi x{addr_reg}, x{addr_reg}, {offset}",
                    f"LI(x{rd}, 42)",
                    test_data.add_testcase(f"hlv.w_{name}", "cp_priority_hlv", covergroup),
                    f"hlv.w x{rd}, (x{addr_reg})",
                    write_sigupd(rd, test_data),
                ]
                store_body = [
                    *(
                        []
                        if legal
                        else [f"LI_FIXED_LEN(x{addr_reg}, {store_base})", f"addi x{addr_reg}, x{addr_reg}, {offset}"]
                    ),
                    f"LI(x{data_reg}, {0x600D0000 + 2 * offset + hu:#x})",
                    test_data.add_testcase(f"hsv.w_{name}", "cp_priority_hsv", covergroup),
                    f"hsv.w x{data_reg}, (x{addr_reg})",
                ]
                if legal:
                    store_body.append(f"LA(x{addr_reg}, scratch)")
                    for word in (0, 4):
                        store_body.extend([f"lw x{rd}, {word}(x{addr_reg})", write_sigupd(rd, test_data)])
                lines.extend(gated(load_body, None if legal else f"defined({load_base})"))
                lines.extend(gated(store_body, None if legal else f"defined({store_base})"))
        lines.extend([f"RVTEST_TSBI_GOTO_{home.upper()}MODE"] if mode != home else [])
    lines.extend([f"LI(x{data_reg}, HSTATUS_HU)", f"csrc hstatus, x{data_reg}"])
    test_data.int_regs.return_registers([addr_reg, data_reg, rd])
    return lines


class XtinstCase(NamedTuple):
    """One exception raised from VS-mode by xtinst_exception_tests."""

    coverpoint: str  # cp_xtinst_<coverpoint>
    bin_name: str
    gate: str | None  # preprocessor condition for the case
    setup: list[str]
    instr: list[str]  # the trapping instruction
    check: Callable[[], list[str]]  # lines after the trap that record what the instruction left behind
    extensions: tuple[str, ...] = ()  # enabled with .option arch around the trapping instruction


def xtinst_exception_tests(test_data: TestData, covergroup: str, home: str) -> list[str]:
    """cp_xtinst_*: exceptions from VS-mode with hedeleg = 0, taken in HS-mode (home "s") or M-mode (home "m").

    Before each one, the home mode writes a nonzero value to htval and htinst (mtval2 and mtinst) and enters VS-mode.
    The trap record holds the values the exception writes.  Explicit memory accesses by loads, stores, AMOs, LR/SC,
    CBOs and their compressed forms may write their transformed instruction; other exceptions write zero.
    """
    # Compressed loads and stores name registers x8-x15: addr_reg is their base and data_reg their data
    addr_reg, data_reg = test_data.int_regs.get_registers(2, reg_range=list(range(8, 16)))
    rd, rand_reg, temp_reg = test_data.int_regs.get_registers(3)
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

    def fault(kind: str) -> str:
        return f"LI_FIXED_LEN(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS_{kind})"

    def fault_gate(kind: str, extension: str | None = None) -> str:
        gate = f"defined(RVMODEL_ACCESS_FAULT_ADDRESS_{kind})"
        return f"defined({extension}_SUPPORTED) && {gate}" if extension else gate

    def check_reg(reg: int) -> list[str]:
        return [write_sigupd(reg, test_data)]

    def no_check() -> list[str]:
        return []

    def check_scratch(*offsets: int) -> list[str]:
        lines = [f"LA(x{addr_reg}, scratch)"]
        for offset in offsets:
            lines.extend([f"lw x{rd}, {offset}(x{addr_reg})", write_sigupd(rd, test_data)])
        return lines

    # Misaligned fetches trap only when IALIGN = 32, and misaligned loads and stores only when the hart does not
    # perform them
    misaligned_ldst_gate = "!defined(UDB_MISALIGNED_LDST)"
    cases = [
        XtinstCase(
            "instr_misaligned",
            "vs",
            "!defined(ZCA_SUPPORTED)",
            [".p2align 2"],
            ["jal x0, .+6", "addi x0, x2, 0", "nop"],
            no_check,
        ),
        XtinstCase("instr_access", "vs", fault_gate("FETCH"), [fault("FETCH")], [f"jalr x1, 0(x{addr_reg})"], no_check),
        XtinstCase("illegalinstr", "vs", None, [".p2align 2"], [".word 0x00000000"], no_check),
        XtinstCase("breakpoint", "vs", None, [], ["ebreak"], no_check),
        XtinstCase("virtinstr", "vs", None, [f"LI(x{rd}, 42)"], [f"csrr x{rd}, vstval"], lambda: check_reg(rd)),
        XtinstCase(
            "load_misaligned",
            "vs",
            misaligned_ldst_gate,
            [f"LA(x{addr_reg}, scratch)", f"LI(x{rd}, 42)"],
            [f"lw x{rd}, 1(x{addr_reg})"],
            lambda: check_reg(rd),
        ),
        XtinstCase(
            "load_access",
            "vs",
            fault_gate("LOAD"),
            [fault("LOAD"), f"LI(x{rd}, 42)"],
            [f"lw x{rd}, 0(x{addr_reg})"],
            lambda: check_reg(rd),
        ),
        XtinstCase(
            "store_misaligned",
            "vs",
            misaligned_ldst_gate,
            [f"LA(x{addr_reg}, scratch)", f"LI(x{data_reg}, 0xC0FFEE11)"],
            [f"sw x{data_reg}, 1(x{addr_reg})"],
            lambda: check_scratch(0, 4),
        ),
        XtinstCase(
            "store_access",
            "vs",
            fault_gate("STORE"),
            [fault("STORE"), f"LI(x{data_reg}, 0xC0FFEE22)"],
            [f"sw x{data_reg}, 0(x{addr_reg})"],
            no_check,
        ),
        XtinstCase("ecall", "vs", None, [], ["RVTEST_TSBI_ECALL_TEST"], no_check),
        # AMOs, LR and SC: H_trans_atomic
        XtinstCase(
            "amo_access",
            "vs_amoswap.w",
            fault_gate("AMO", "ZAAMO"),
            [fault("AMO"), f"LI(x{data_reg}, 0xC0FFEE33)", f"LI(x{rd}, 42)"],
            [f"amoswap.w x{rd}, x{data_reg}, (x{addr_reg})"],
            lambda: check_reg(rd),
            ("zaamo",),
        ),
        # scratch + 14 crosses a 16-byte boundary, so the word is outside any misaligned atomicity granule that
        # Zama16b guarantees: an address-misaligned or access fault unless the hart's granule is larger
        XtinstCase(
            "amo_misaligned",
            "vs_amoswap.w",
            "defined(ZAAMO_SUPPORTED)",
            [
                f"LA(x{addr_reg}, scratch)",
                f"addi x{addr_reg}, x{addr_reg}, 14",
                f"LI(x{data_reg}, 0xC0FFEE44)",
                f"LI(x{rd}, 42)",
            ],
            [f"amoswap.w x{rd}, x{data_reg}, (x{addr_reg})"],
            lambda: [*check_reg(rd), *check_scratch(12, 16)],
            ("zaamo",),
        ),
        XtinstCase(
            "lrsc_access",
            "vs_lr.w",
            fault_gate("LRSC", "ZALRSC"),
            [fault("LRSC"), f"LI(x{rd}, 42)"],
            [f"lr.w x{rd}, (x{addr_reg})"],
            lambda: check_reg(rd),
            ("zalrsc",),
        ),
        XtinstCase(
            "lrsc_access",
            "vs_sc.w",
            fault_gate("LRSC", "ZALRSC"),
            [fault("LRSC"), f"LI(x{data_reg}, 0xC0FFEE55)", f"LI(x{rd}, 42)"],
            [f"sc.w x{rd}, x{data_reg}, (x{addr_reg})"],
            lambda: check_reg(rd),
            ("zalrsc",),
        ),
        XtinstCase(
            "zabha_access",
            "vs_amoadd.b",
            fault_gate("AMO", "ZABHA"),
            [fault("AMO"), f"LI(x{data_reg}, 0x66)", f"LI(x{rd}, 42)"],
            [f"amoadd.b x{rd}, x{data_reg}, (x{addr_reg})"],
            lambda: check_reg(rd),
            ("zaamo", "zabha"),
        ),
        XtinstCase(
            "zacas_access",
            "vs_amocas.w",
            fault_gate("AMO", "ZACAS"),
            [fault("AMO"), f"LI(x{data_reg}, 0xC0FFEE77)", f"LI(x{rd}, 42)"],
            [f"amocas.w x{rd}, x{data_reg}, (x{addr_reg})"],
            lambda: check_reg(rd),
            ("zaamo", "zacas"),
        ),
        # Compressed loads and stores: H_trans_compressed_list
        XtinstCase(
            "c_load_access",
            "vs_c.lw",
            fault_gate("LOAD", "ZCA"),
            [fault("LOAD"), f"LI(x{data_reg}, 42)"],
            [f"c.lw x{data_reg}, 0(x{addr_reg})"],
            lambda: check_reg(data_reg),
            ("zca",),
        ),
        XtinstCase(
            "c_store_access",
            "vs_c.sw",
            fault_gate("STORE", "ZCA"),
            [fault("STORE"), f"LI(x{data_reg}, 0xC0FFEE88)"],
            [f"c.sw x{data_reg}, 0(x{addr_reg})"],
            no_check,
            ("zca",),
        ),
        XtinstCase(
            "zcb_access",
            "vs_c.lbu",
            fault_gate("LOAD", "ZCB"),
            [fault("LOAD"), f"LI(x{data_reg}, 42)"],
            [f"c.lbu x{data_reg}, 0(x{addr_reg})"],
            lambda: check_reg(data_reg),
            ("zca", "zcb"),
        ),
        # Cache-block operations: H_trans_cache.  The boot enables them in VS-mode (menvcfg and henvcfg
        # CBIE = 11, CBCFE = 1 and CBZE = 1).
        *(
            XtinstCase(
                "cbom_access",
                f"vs_{instr}",
                fault_gate("STORE", "ZICBOM"),
                [fault("STORE")],
                [f"{instr} (x{addr_reg})"],
                no_check,
                ("zicbom",),
            )
            for instr in ("cbo.clean", "cbo.flush", "cbo.inval")
        ),
        XtinstCase(
            "cboz_access",
            "vs_cbo.zero",
            fault_gate("STORE", "ZICBOZ"),
            [fault("STORE")],
            [f"cbo.zero (x{addr_reg})"],
            no_check,
            ("zicboz",),
        ),
    ]
    lines = [
        comment_banner(
            "cp_xtinst_*",
            f"From VS-mode with hedeleg = 0, raise each exception into {'M' if home == 'm' else 'HS'}-mode after "
            f"writing a nonzero value\nto {tval2} and {tinst}.  The trap record holds {tval2} (zero) and {tinst} "
            "(zero or a transformed load, store, AMO, LR/SC or CBO)",
        ),
        "csrw hedeleg, zero",
        f"LI(x{rand_reg}, 0x5A5A5A5B)",
    ]
    for case in cases:
        body = [
            f"csrw {tval2}, x{rand_reg}",
            f"csrw {tinst}, x{rand_reg}",
            *enter_vs,
            *case.setup,
            test_data.add_testcase(case.bin_name, f"cp_xtinst_{case.coverpoint}", covergroup),
            *arch_block(case.instr, *case.extensions),
            *case.check(),
            f"RVTEST_TSBI_GOTO_{home.upper()}MODE",
        ]
        lines.extend(gated(body, case.gate))
    test_data.int_regs.return_registers([addr_reg, data_reg, rd, rand_reg, temp_reg])
    return lines
