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

from collections.abc import Sequence

from testgen.asm.helpers import arch_block, comment_banner, gated, write_sigupd
from testgen.data.state import TestData
from testgen.priv.extensions.exceptions.ExceptionsCommon import DELEGATED_FAULT_KINDS, generate_delegated_fault_tests

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


def _enter(home: str, mode: str, temp_reg: int) -> list[str]:
    """Enter mode from the home mode without writing the second trap value or xtinst.

    M-mode enters the other modes by mret, because a T-SBI call would overwrite mtval2 and mtinst.
    """
    if mode == home:
        return []
    if home != "m":
        return [f"RVTEST_TSBI_GOTO_{mode.upper()}MODE"]
    mpv = "csrs" if mode in ("vs", "vu") else "csrc"
    return [
        f"LI(x{temp_reg}, MSTATUS_MPP)",
        f"csrc mstatus, x{temp_reg}",
        *([f"LI(x{temp_reg}, MPP_SMODE)", f"csrs mstatus, x{temp_reg}"] if mode in ("s", "vs") else []),
        "#if __riscv_xlen == 64",
        f"LI(x{temp_reg}, MSTATUS_MPV)",
        f"{mpv} mstatus, x{temp_reg}",
        "#else",
        f"LI(x{temp_reg}, MSTATUSH_MPV)",
        f"{mpv} mstatush, x{temp_reg}",
        "#endif",
        f"LA(x{temp_reg}, 1f)",
        f"csrw mepc, x{temp_reg}",
        "mret",
        "1:",
    ]


def xtinst_exception_tests(test_data: TestData, covergroup: str, home: str) -> list[str]:
    """cp_xtinst_*: exceptions from VS-mode with hedeleg = 0, taken in HS-mode (home "s") or M-mode (home "m").

    Before each one, the home mode writes a nonzero value to htval and htinst (mtval2 and mtinst) and enters VS-mode.
    The trap record holds the values the exception writes.
    """
    addr_reg, data_reg, rd, rand_reg, temp_reg = test_data.int_regs.get_registers(5)
    tval2, tinst = ("mtval2", "mtinst") if home == "m" else ("htval", "htinst")
    enter_vs = _enter(home, "vs", temp_reg)

    def fault(kind: str) -> str:
        return f"LI_FIXED_LEN(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS_{kind})"

    def fault_gate(kind: str) -> str:
        return f"defined(RVMODEL_ACCESS_FAULT_ADDRESS_{kind})"

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
        ("instr_access", fault_gate("FETCH"), [fault("FETCH")], [f"jalr x1, 0(x{addr_reg})"], None),
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
        ("load_access", fault_gate("LOAD"), [fault("LOAD"), f"LI(x{rd}, 42)"], [f"lw x{rd}, 0(x{addr_reg})"], "rd"),
        (
            "store_misaligned",
            misaligned_ldst_gate,
            [f"LA(x{addr_reg}, scratch)", f"LI(x{data_reg}, 0xC0FFEE11)"],
            [f"sw x{data_reg}, 1(x{addr_reg})"],
            "store",
        ),
        (
            "store_access",
            fault_gate("STORE"),
            [fault("STORE"), f"LI(x{data_reg}, 0xC0FFEE22)"],
            [f"sw x{data_reg}, 0(x{addr_reg})"],
            None,
        ),
        ("ecall", None, [], ["RVTEST_TSBI_ECALL_TEST"], None),
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


# Floating-point loads and stores, which H_trans_load and H_trans_store list, and their compressed forms
# (H_trans_compressed_list): (instruction, access-fault address, preprocessor condition, extensions to assemble it)
_XTINST_FP = (
    ("flw", "LOAD", "defined(F_SUPPORTED)", ("f",)),
    ("fsw", "STORE", "defined(F_SUPPORTED)", ("f",)),
    ("fld", "LOAD", "defined(D_SUPPORTED)", ("d",)),
    ("fsd", "STORE", "defined(D_SUPPORTED)", ("d",)),
    ("flh", "LOAD", "defined(ZFHMIN_SUPPORTED) || defined(ZFH_SUPPORTED)", ("f", "zfhmin")),
    ("fsh", "STORE", "defined(ZFHMIN_SUPPORTED) || defined(ZFH_SUPPORTED)", ("f", "zfhmin")),
    ("c.flw", "LOAD", "defined(ZCF_SUPPORTED)", ("f", "zca", "zcf")),
    ("c.fsw", "STORE", "defined(ZCF_SUPPORTED)", ("f", "zca", "zcf")),
    ("c.fld", "LOAD", "defined(ZCD_SUPPORTED)", ("d", "zca", "zcd")),
    ("c.fsd", "STORE", "defined(ZCD_SUPPORTED)", ("d", "zca", "zcd")),
)


def xtinst_fp_tests(test_data: TestData, covergroup: str, home: str) -> list[str]:
    """cp_xtinst_fp_load_access and cp_xtinst_fp_store_access: each floating-point load and store, and its compressed
    form, at the access-fault address in VS-mode with hedeleg = 0, taken in HS-mode (home "s") or M-mode (home "m").

    As in xtinst_exception_tests, the home mode first writes a nonzero value to htval and htinst (mtval2 and mtinst).
    The boot sets FS in mstatus and vsstatus.  The trap record holds xtinst: zero, or the transformed instruction, which
    for a compressed instruction is its 32-bit expansion transformed, with bit 1 cleared.
    """
    # Compressed loads and stores name registers x8-x15 and f8-f15
    addr_reg = test_data.int_regs.get_register(reg_range=list(range(8, 16)))
    rand_reg, temp_reg = test_data.int_regs.get_registers(2)
    freg = test_data.float_regs.get_register(reg_range=list(range(8, 16)))
    tval2, tinst = ("mtval2", "mtinst") if home == "m" else ("htval", "htinst")
    lines = [
        comment_banner(
            "cp_xtinst_fp_load_access, cp_xtinst_fp_store_access",
            "From VS-mode with hedeleg = 0, execute each floating-point load and store and its compressed form at the\n"
            f"access-fault address after writing a nonzero value to {tval2} and {tinst}.  The access fault goes to "
            f"{'M' if home == 'm' else 'HS'}-mode, and\nthe trap record holds {tinst}: zero or the transformed instruction",
        ),
        "csrw hedeleg, zero",
        f"LI(x{rand_reg}, 0x5A5A5A5B)",
    ]
    for instr, kind, gate, extensions in _XTINST_FP:
        cp = f"cp_xtinst_fp_{kind.lower()}_access"
        body = [
            f"csrw {tval2}, x{rand_reg}",
            f"csrw {tinst}, x{rand_reg}",
            *_enter(home, "vs", temp_reg),
            f"LI_FIXED_LEN(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS_{kind})",
            test_data.add_testcase(f"vs_{instr}", cp, covergroup),
            *arch_block([f"{instr} f{freg}, 0(x{addr_reg})"], *extensions),
            f"RVTEST_TSBI_GOTO_{home.upper()}MODE",
        ]
        lines.extend(gated(body, f"({gate}) && defined(RVMODEL_ACCESS_FAULT_ADDRESS_{kind})"))
    test_data.int_regs.return_registers([addr_reg, rand_reg, temp_reg])
    test_data.float_regs.return_register(freg)
    return lines


def xtinst_v0_tests(test_data: TestData, covergroup: str, home: str) -> list[str]:
    """cp_xtinst_v0_illegalinstr and cp_xtinst_v0_load_access: illegal instruction and a load access fault from each
    mode with V = 0 that traps to the home mode (HS-mode and U-mode into HS-mode, or M-mode, HS-mode and U-mode into
    M-mode, which delegates nothing).

    Before each one, the home mode writes a nonzero value to htval and htinst (mtval2 and mtinst).  The trap record
    holds the values the trap writes: zero in htval (mtval2), and zero or the transformed lw in htinst (mtinst).
    """
    addr_reg, rd, rand_reg, temp_reg = test_data.int_regs.get_registers(4)
    tval2, tinst = ("mtval2", "mtinst") if home == "m" else ("htval", "htinst")
    modes = ("m", "s", "u") if home == "m" else ("s", "u")
    lines = [
        comment_banner(
            "cp_xtinst_v0_illegalinstr, cp_xtinst_v0_load_access",
            f"In {' and '.join(f'{m.upper()}-mode' for m in modes).replace('S-mode', 'HS-mode')}, raise illegal "
            f"instruction and a load access fault after writing a nonzero value\nto {tval2} and {tinst}.  The trap record "
            f"holds {tval2} (zero) and {tinst} (zero, or the transformed lw)",
        ),
        f"LI(x{rand_reg}, 0x5A5A5A5B)",
    ]
    for mode in modes:
        name = "hs" if mode == "s" else mode
        leave = [] if mode == home else [f"RVTEST_TSBI_GOTO_{home.upper()}MODE"]
        preset = [f"csrw {tval2}, x{rand_reg}", f"csrw {tinst}, x{rand_reg}", *_enter(home, mode, temp_reg)]
        lines.extend(
            [
                *preset,
                ".p2align 2",
                test_data.add_testcase(name, "cp_xtinst_v0_illegalinstr", covergroup),
                ".word 0x00000000",
                *leave,
            ]
        )
        body = [
            *preset,
            f"LI_FIXED_LEN(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS_LOAD)",
            f"LI(x{rd}, 42)",
            test_data.add_testcase(name, "cp_xtinst_v0_load_access", covergroup),
            f"lw x{rd}, 0(x{addr_reg})",
            write_sigupd(rd, test_data),
            *leave,
        ]
        lines.extend(gated(body, "defined(RVMODEL_ACCESS_FAULT_ADDRESS_LOAD)"))
    test_data.int_regs.return_registers([addr_reg, rd, rand_reg, temp_reg])
    return lines


# (CSR, line that loads its preset value into x{r}, write instruction, mask of the fields a trap may write or None)
TrapCsrPreset = tuple[str, str, str, str | None]

# Presets for the HS-level CSRs a trap into VS-mode must leave alone (H_trap_vs_csrwrites).  mstatus holds the
# HS-level sstatus.  The values are legal: an aligned code address, a supported exception code and a data address.
HS_TRAP_CSRS: tuple[TrapCsrPreset, ...] = (
    ("hstatus", "LI(x{r}, HSTATUS_SPV | HSTATUS_SPVP | HSTATUS_GVA)", "csrs", None),
    ("mstatus", "LI(x{r}, SSTATUS_SPP | SSTATUS_SPIE)", "csrs", "SSTATUS_SPP | SSTATUS_SPIE | SSTATUS_SIE"),
    ("sepc", "LA(x{r}, rvtest_code_begin)", "csrw", None),
    ("scause", "LI(x{r}, CAUSE_BREAKPOINT)", "csrw", None),
    ("stval", "LA(x{r}, scratch)", "csrw", None),
    ("htval", "LI(x{r}, 0x5A5A5A5B)", "csrw", None),
    ("htinst", "LI(x{r}, 0x5A5A5A5B)", "csrw", None),
)

# Presets for the VS CSRs a trap into HS-mode must leave alone (H_trap_hs_csrwrites)
VS_TRAP_CSRS: tuple[TrapCsrPreset, ...] = (
    ("vsstatus", "LI(x{r}, SSTATUS_SPP | SSTATUS_SPIE)", "csrs", None),
    ("vsepc", "LA(x{r}, rvtest_code_begin)", "csrw", None),
    ("vscause", "LI(x{r}, CAUSE_BREAKPOINT)", "csrw", None),
    ("vstval", "LA(x{r}, scratch)", "csrw", None),
)


def trap_isolation_tests(
    test_data: TestData, covergroup: str, coverpoint: str, home: str, presets: Sequence[TrapCsrPreset]
) -> list[str]:
    """Write presets to the CSRs of the privilege level that does not take the trap, then raise illegal instruction in
    VS-mode and VU-mode, and record each CSR XORed with its value before the trap.

    The trap must leave the CSRs alone, so every record is zero, whatever values the CSRs legalized the presets to.  The
    readbacks are kept in scratch.  For a mask, only the fields in it are compared.  The caller sets the delegation
    that takes the trap to the level that the presets do not belong to.
    """
    base, val, old = test_data.int_regs.get_registers(3)
    lines = [
        comment_banner(
            coverpoint,
            f"Write {', '.join(csr for csr, *_ in presets)}, raise illegal instruction in VS-mode and VU-mode,\n"
            "and record each CSR XORed with its value before the trap: zero",
        )
    ]
    for mode in ("vs", "vu"):
        lines.append(f"LA(x{base}, scratch)")
        for i, (csr, load, op, _) in enumerate(presets):
            lines.extend(
                [
                    load.format(r=val),
                    f"{op} {csr}, x{val}",
                    f"csrr x{val}, {csr}",
                    f"SREG x{val}, {i}*REGWIDTH(x{base})",
                ]
            )
        lines.extend(
            [
                f"RVTEST_TSBI_GOTO_{mode.upper()}MODE",
                ".p2align 2",
                test_data.add_testcase(mode, coverpoint, covergroup),
                ".word 0x00000000",
                f"RVTEST_TSBI_GOTO_{home.upper()}MODE",
                f"LA(x{base}, scratch)",
            ]
        )
        for i, (csr, _, _, mask) in enumerate(presets):
            lines.extend(
                [
                    f"csrr x{val}, {csr}",
                    f"LREG x{old}, {i}*REGWIDTH(x{base})",
                    f"xor x{val}, x{val}, x{old}",
                    *([f"LI(x{old}, {mask})", f"and x{val}, x{val}, x{old}"] if mask else []),
                    write_sigupd(val, test_data),
                ]
            )
        # Clear the status bits that were set; the other presets are overwritten by the next trap
        for csr, load, op, _ in presets:
            if op == "csrs":
                lines.extend([load.format(r=val), f"csrc {csr}, x{val}"])
    test_data.int_regs.return_registers([base, val, old])
    return lines
