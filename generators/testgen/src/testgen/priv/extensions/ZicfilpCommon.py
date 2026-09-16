##################################
# priv/extensions/ZicfilpCommon.py
#
# Zicfilp (Control-Flow Integrity - Landing Pads) shared test infrastructure.
# Author : Eman Nasar  email:fatehulnasareman@gmail.com (UET, May 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared Zicfilp extension test infrastructure.
Common code for ZicfilpSm (M-mode), ZicfilpS (S-mode and U+S), ZicfilpU (U-S)
test generators.
"""

from collections.abc import Callable
from dataclasses import dataclass

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData

# constants
_MSECCFG_MLPE_BIT = 10  # mseccfg.MLPE
_MENVCFG_LPE_BIT = 2  # menvcfg.LPE
_SENVCFG_LPE_BIT = 2  # senvcfg.LPE
_MSTATUS_MPELP_BIT = 41  # mstatus.MPELP on RV64
_MSTATUSH_MPELP_BIT = 9  # mstatush.MPELP on RV32
_SSTATUS_SPELP_BIT = 23  # sstatus.SPELP

CAUSE_SW_CHECK = 18  # LPAD Mismatch / Missing
XTVAL_LPAD_FAULT = 2  # mtval/stval code for LPAD fault

CP_ELP_UPDATE = "cp_zicfilp_indirect_elp_state_update"
CP_LPAD_VALID = "cp_zicfilp_lpad_valid_execution"
CP_LPAD_BYPASS = "cp_zicfilp_lpad_zero_label_bypass"
CP_LPAD_MISSING = "cp_zicfilp_lpad_missing_instruction_exception"
CP_LPAD_MISMATCH = "cp_zicfilp_lpad_label_mismatch"
CP_LPAD_SCENARIO = "cp_zicfilp_lpad_label_match_mismatch"
CP_EXC_DELIVERY = "cp_zicfilp_lpad_label_exception_delivery"
CP_LPE_DISABLED = "cp_disabled_zicfilp"  # SV Typo: "disabled"
CP_ELP_CLEAR = "cp_lpad_no_sw_exception_elp_clear_zicfilp"
CP_PELP_ENTRY = "cp_pelp_trap_entry_m_zicfilp"
CP_PELP_GUARDED = "cp_pelp_trap_entry_m_guarded_zicfilp"
CP_PELP_RET = "cp_pelp_trap_return_m_zicfilp"
CP_ELP_PRESERVE = "cp_elp_state_preservation_zicfilp"
CP_EXC_PRIORITY = "cp_exception_priority_zicfilp"

COVERGROUP_M = "Zicfilp_Sm_cg"
COVERGROUP_S = "Zicfilp_s_cg"
COVERGROUP_U_S = "Zicfilpsu_cg"
COVERGROUP_U_NS = "Zicfilp_u_cg"

LINK_REGS = {1, 5, 7}  # x1=ra, x5, x7 (ELP)
RESERVED_REGS = {2, 3, 4, 8}
ALL_REGS = [r for r in range(1, 32) if r not in RESERVED_REGS]
COMP_REGS = [r for r in range(1, 16) if r not in RESERVED_REGS]
NON_LINK_REGS = [r for r in ALL_REGS if r not in LINK_REGS]
NON_LINK_COMP_REGS = [r for r in COMP_REGS if r not in LINK_REGS]
REP_NON_LINK = 28
REP_LINK = 1

MODES = ["bare", "sv39", "sv48", "sv57"]
MODE_GUARDS = {m: None if m == "bare" else f"{m.upper()}_SUPPORTED" for m in MODES}
LEVELS_BELOW_ROOT = {"sv39": 2, "sv48": 3, "sv57": 4}

GOTO_MMODE = "RVTEST_GOTO_MMODE"
GOTO_SMODE = "RVTEST_TSBI_GOTO_SMODE"
GOTO_UMODE = "RVTEST_TSBI_GOTO_UMODE"


@dataclass(frozen=True)
class XLPEConfig:
    csr: str  # CSR containing LPE bit
    bit: int  # Bit position (12)
    name: str  # "MLPE" or "LPE"
    pelp_csr: str  # CSR containing PELP bit ("mstatus", "mstatush", "sstatus")
    pelp_bit: int  # Bit position (12)
    guard: str = ""  # Conditional compilation guard
    # pelp_csr is out of reach at the test's privilege level, so read it via T-SBI
    pelp_needs_elevation: bool = False
    # clear live ELP after reading pelp_csr, so a fault doesn't cascade instruction by instruction
    clear_live_elp: bool = False


def _get_xlpe_config(mode: str, xlen: int) -> XLPEConfig:
    """Returns correct XLPEConfig for mode/xlen, handling RV32 mstatush."""
    if mode == "mmode":
        pelp_csr = "mstatus" if xlen == 64 else "mstatush"
        pelp_bit = _MSTATUS_MPELP_BIT if xlen == 64 else _MSTATUSH_MPELP_BIT
        return XLPEConfig("mseccfg", _MSECCFG_MLPE_BIT, "MLPE", pelp_csr=pelp_csr, pelp_bit=pelp_bit)
    elif mode == "smode":
        return XLPEConfig(
            "menvcfg",
            _MENVCFG_LPE_BIT,
            "LPE",
            pelp_csr="sstatus",
            pelp_bit=_SSTATUS_SPELP_BIT,
            guard="#ifdef S_SUPPORTED",
            clear_live_elp=True,
        )
    elif mode == "umode":  # U-mode with S-mode implemented
        return XLPEConfig(
            "senvcfg",
            _SENVCFG_LPE_BIT,
            "LPE",
            pelp_csr="sstatus",
            pelp_bit=_SSTATUS_SPELP_BIT,
            guard="#ifdef S_SUPPORTED",
            pelp_needs_elevation=True,  # sstatus isn't readable from U-mode
            clear_live_elp=True,
        )
    elif mode == "umode_nos":  # U-mode, No S-mode
        pelp_csr = "mstatus" if xlen == 64 else "mstatush"
        return XLPEConfig(
            "menvcfg",
            _MENVCFG_LPE_BIT,
            "LPE",
            pelp_csr=pelp_csr,
            pelp_bit=_MSTATUS_MPELP_BIT if xlen == 64 else _MSTATUSH_MPELP_BIT,
            guard="#ifndef S_SUPPORTED",
            pelp_needs_elevation=True,  # mstatus/mstatush isn't readable from U-mode
        )
    raise ValueError(f"Unknown mode: {mode}")


# assembly helpers


def _tid(prefix: str, *parts: str) -> str:
    return f"{prefix}_{'_'.join(str(p).replace('.', '_') for p in parts)}"


def _indirect_branch(name: str, rs1: int, rd_is_x7: bool) -> list[str]:
    """Emit an indirect branch; rd_is_x7 arms ELP with the return address, else rd is a temp."""
    if name in ("c.jr", "c.jalr"):
        return [f"{name} x{rs1}"]
    if name != "jalr":
        raise ValueError(f"Unknown branch: {name}")
    rd = 7 if rd_is_x7 else 10
    return [".option push", ".option norvc", f"jalr x{rd}, 0(x{rs1})", ".option pop"]


# CSR addresses for the T-SBI CSR-access encodings below.  mseccfg is absent:
# M-mode tests reach it directly.
_CSR_ADDR = {
    "menvcfg": 0x30A,
    "senvcfg": 0x10A,
    "mstatus": 0x300,
    "mstatush": 0x310,
    "sstatus": 0x100,
}

# Fixed fields of the RVTEST_TSBI_CSR_ACCESS encodings; OR with (csr_addr << 20).
_TSBI_CSRRS_X0_A1 = 0x5A073  # csrrs x0, <csr>, a1   (set bits)
_TSBI_CSRRC_X0_A1 = 0x5B073  # csrrc x0, <csr>, a1   (clear bits)
_TSBI_CSRRS_A0_X0 = 0x02573  # csrrs a0, <csr>, x0   (read, rd=a0 per macro contract)


def _set_lpe(xlpe: XLPEConfig, reg: int, en: bool) -> list[str]:
    guard = xlpe.guard
    lines = []
    if guard:
        lines.append(guard)
    if xlpe.csr == "mseccfg":
        act = "csrs" if en else "csrc"
        msk = 1 << xlpe.bit
        lines += [
            f"# {xlpe.csr}.{xlpe.name} = {int(en)}",
            f"LI(x{reg}, {hex(msk)})",
            f"{act} {xlpe.csr}, x{reg}",
        ]
    else:
        # menvcfg/senvcfg need a higher privilege level than the test runs at
        msk = 1 << xlpe.bit
        op = _TSBI_CSRRS_X0_A1 if en else _TSBI_CSRRC_X0_A1
        encoding = (_CSR_ADDR[xlpe.csr] << 20) | op
        lines += [
            f"# {xlpe.csr}.{xlpe.name} = {int(en)}",
            f"LI(a1, {hex(msk)})",
            f"RVTEST_TSBI_CSR_ACCESS {hex(encoding)}",
        ]
    if guard:
        lines.append(f"#endif // {guard.split()[-1]}")
    return lines


def _clear_pelp(xlpe: XLPEConfig) -> list[str]:
    """Clear live ELP with an LPL=0 landing pad, which always matches; no-op unless clear_live_elp."""
    if not xlpe.clear_live_elp:
        return []
    return [
        "# LPL=0 landing pad clears live ELP",
        f".word {hex(_lpad_encoding(0))}",
    ]


def _read_pelp(xlpe: XLPEConfig, dst: int) -> list[str]:
    """Read xPELP bit into dst."""
    guard = xlpe.guard
    lines = []
    if guard:
        lines.append(guard)
    if xlpe.pelp_needs_elevation:
        # not readable from U-mode; read via T-SBI, which returns in a0
        encoding = (_CSR_ADDR[xlpe.pelp_csr] << 20) | _TSBI_CSRRS_A0_X0
        lines += [
            f"# read {xlpe.pelp_csr} via T-SBI",
            f"RVTEST_TSBI_CSR_ACCESS {hex(encoding)}",
            f"mv x{dst}, a0",
        ]
    else:
        lines += [f"csrr x{dst}, {xlpe.pelp_csr}"]
    lines += [
        f"srli x{dst}, x{dst}, {xlpe.pelp_bit}",
        f"andi x{dst}, x{dst}, 1",
    ]
    lines += _clear_pelp(xlpe)
    if guard:
        lines.append(f"#endif // {guard.split()[-1]}")
    return lines


def _set_pelp(xlpe: XLPEConfig, reg: int) -> list[str]:
    """Set xPELP=1, the state the exception crosses sample alongside mcause and mtval."""
    guard = xlpe.guard
    lines = []
    if guard:
        lines.append(guard)
    msk = 1 << xlpe.pelp_bit
    if xlpe.pelp_needs_elevation:
        encoding = (_CSR_ADDR[xlpe.pelp_csr] << 20) | _TSBI_CSRRS_X0_A1
        lines += [
            f"# {xlpe.pelp_csr}.PELP = 1",
            f"LI(a1, {hex(msk)})",
            f"RVTEST_TSBI_CSR_ACCESS {hex(encoding)}",
        ]
    else:
        lines += [
            f"# {xlpe.pelp_csr}.PELP = 1",
            f"LI(x{reg}, {hex(msk)})",
            f"csrs {xlpe.pelp_csr}, x{reg}",
        ]
    if guard:
        lines.append(f"#endif // {guard.split()[-1]}")
    return lines


def _lpad_encoding(label_20bit: int) -> int:
    """LPAD encoding: LPL in [31:12], rd=0, AUIPC opcode."""
    return ((label_20bit & 0xFFFFF) << 12) | 0x017


# trampolines
def _trampoline_section(pfx: str, section: str = ".text.rvtest", self_heal_elp: bool = False) -> list[str]:
    """Emit the jump targets: LPL=0, matching, mismatching and non-LPAD landing pads.

    The _retra targets return via ra, for callers that set x7 themselves.
    self_heal_elp puts an LPL=0 pad where the handler resumes after a fault,
    so ELP is cleared and the target's own jump runs.
    """
    enc_zero = _lpad_encoding(0x00000)  # LPL=0
    enc_match = _lpad_encoding(0xABCDE)  # LPL=0xABCDE
    enc_mismatch = _lpad_encoding(0x12345)  # LPL=0x12345
    enc_zero_nz = _lpad_encoding(0xABCDE)  # LPL=0xABCDE (for sc4)
    heal = f"  .word {hex(enc_zero)}" if self_heal_elp else "  nop"

    return [
        "",
        "# Zicfilp LPAD targets",
        # a fault is only recorded in .text.rvtest; bare .text is swept into .text.rvmodel
        f".pushsection {section}",
        ".p2align 2",
        f"{pfx}_tgt_lpad_zero:",
        f"  .word {hex(enc_zero)}",
        heal,
        "  jr x7",
        "",
        ".p2align 2",
        f"{pfx}_tgt_lpad_zero_retra:",
        f"  .word {hex(enc_zero)}",
        heal,
        "  jr ra",
        "",
        ".p2align 2",
        f"{pfx}_tgt_lpad_match:",
        f"  .word {hex(enc_match)}",
        heal,
        "  jr x7",
        "",
        ".p2align 2",
        f"{pfx}_tgt_lpad_match_retra:",
        f"  .word {hex(enc_match)}",
        heal,
        "  jr ra",
        "",
        ".p2align 2",
        f"{pfx}_tgt_lpad_mismatch:",
        f"  .word {hex(enc_mismatch)}",
        heal,
        "  jr x7",
        "",
        ".p2align 2",
        f"{pfx}_tgt_lpad_zero_nonzero:",
        f"  .word {hex(enc_zero_nz)}",
        heal,
        "  jr x7",
        "",
        ".p2align 2",
        f"{pfx}_tgt_lpad_zero_nonzero_retra:",
        f"  .word {hex(enc_zero_nz)}",
        heal,
        "  jr ra",
        "",
        ".p2align 2",
        f"{pfx}_tgt_nonlpad:",
        "  nop",
        # a landing pad is only recognised 4-byte aligned, and the nop above is 2 bytes
        ".p2align 2",
        heal,
        "  jr x7",
        ".popsection",
        "",
    ]


# data


def _data_section() -> list[str]:
    return [
        comment_banner("DATA", "Zicfilp scratch"),
        ".pushsection .data",
        ".p2align 12",
        "zicfilp_scratch: .dword 0xABCD1234ABCD1234",
        ".zero 4088",
        ".popsection",
        "",
    ]


def _data_slvl_tables(mode: str) -> list[str]:
    """Page tables for the level below the root; none in bare mode."""
    if mode == "bare":
        return []
    lines: list[str] = [".pushsection .data"]
    for i in range(LEVELS_BELOW_ROOT[mode]):
        lines += [".p2align 12", f"rvtest_slvl{i}_pg_tbl: .zero 4096"]
    lines.append(".popsection")
    return lines


def both_xlens(build: Callable[[int], list[str]]) -> list[str]:
    """Emit build(64) and build(32) under their paging guards, which imply the xlen.

    A body that never touches satp belongs in both_xlens_bare instead.
    """
    return [
        "#ifdef SV39_SUPPORTED",
        *build(64),
        "#endif // SV39_SUPPORTED",
        "#ifdef SV32_SUPPORTED",
        *build(32),
        "#endif // SV32_SUPPORTED",
    ]


def both_xlens_bare(build: Callable[[int], list[str]]) -> list[str]:
    """Emit build(64) and build(32) inside a plain XLEN guard (no paging support required)."""
    return [
        "#if __riscv_xlen == 64",
        *build(64),
        "#else",
        *build(32),
        "#endif // __riscv_xlen",
    ]


def _grant_umode_code_access(xlen: int) -> list[str]:
    """Add PTE_U to the identity superpage covering rvtest_code_begin.

    The boot map (rvtest_identity_map) covers rvtest_data_begin without PTE_U,
    so U-mode would fault on its first instruction fetch.  Built off
    rvtest_code_begin's runtime address, the way that map is.
    """
    lines = ["LA(T1, rvtest_Sroot_pg_tbl)", "LA(T2, rvtest_code_begin)"]
    if xlen == 32:
        lines += [
            "srli T3, T2, 22",
            "andi T3, T3, 0x3FF",
            "slli T4, T3, 20",
            "ori  T4, T4, 0xDF",  # 0xCF (default identity map) | PTE_U
            "slli T3, T3, 2",
            "add  T3, T1, T3",
            "sw   T4, 0(T3)",
        ]
    else:
        lines += [".set VPN_SHIFT_ZICFILP, 21"]
        for _ in range(3):  # covers sv39 (shift 30), sv48 (39), sv57 (48) root indices
            lines += [
                ".set VPN_SHIFT_ZICFILP, VPN_SHIFT_ZICFILP+9",
                "srli T3, T2, VPN_SHIFT_ZICFILP",
                "andi T3, T3, 0x1FF",
                "slli T4, T3, VPN_SHIFT_ZICFILP-2",
                "ori  T4, T4, 0xDF",  # 0xCF (default identity map) | PTE_U
                "slli T3, T3, 3",
                "add  T3, T1, T3",
                "sd   T4, 0(T3)",
            ]
    return lines


def satp_setup(xlen: int, mode: str, grant_umode_access: bool = False) -> list[str]:
    if mode == "bare":
        return ["csrwi satp, 0", "sfence.vma"]
    lines = _grant_umode_code_access(xlen) if grant_umode_access else []
    lines += [f"SATP_SETUP_RV{'64' if xlen == 64 else '32'}({mode})", "sfence.vma"]
    return lines


def teardown_vm(has_satp: bool = True) -> list[str]:
    if not has_satp:
        return [GOTO_MMODE, ""]
    return [GOTO_MMODE, "csrwi satp, 0", "sfence.vma", ""]


# scenario builders
def _indirect_elp_state_update(pfx: str, td: TestData, cg: str, xlpe: XLPEConfig, xlen: int) -> list[str]:
    """CP_ELP_UPDATE: Indirect CT (JALR x7) -> LPAD. Vary LPE, RS1, Dest."""
    rs1, tmp, chk = td.int_regs.get_registers(3)
    out = [comment_banner(f"{pfx}: ELP Update (JALR x7 -> LPAD)")]

    # A fault with mseccfg.MLPE=1 recurses into the M-mode dispatcher's own
    # unguarded `jr T5`, so skip the combinations that fault in M-mode.
    is_mmode = xlpe.csr == "mseccfg"

    def _unsafe_for_mmode(lpe: int, dest: str, rs1_val: int) -> bool:
        return bool(lpe and is_mmode and dest in ("lpad_mismatch", "nonlpad") and rs1_val not in LINK_REGS)

    for lpe in [0, 1]:
        out.extend(_set_lpe(xlpe, tmp, bool(lpe)))

        for rs1_val in ALL_REGS:
            for dest, tgt_label in [
                ("lpad_zero", f"{pfx}_tgt_lpad_zero"),
                ("lpad_match", f"{pfx}_tgt_lpad_match"),
                ("lpad_mismatch", f"{pfx}_tgt_lpad_mismatch"),
                ("nonlpad", f"{pfx}_tgt_nonlpad"),
            ]:
                if _unsafe_for_mmode(lpe, dest, rs1_val):
                    continue
                tc = _tid(pfx, f"lpe{lpe}", "jalr", f"rs1_{rs1_val}", dest)
                if dest == "lpad_match" and rs1_val not in LINK_REGS:
                    # only LINK_REGS are exempt from the check, so match the label
                    # explicitly in x7 and return via ra
                    ret_label = f"{tc}_ret"
                    out += [
                        "",
                        td.add_testcase(tc, CP_ELP_UPDATE, cg),
                        "LI(x7, 0xabcde000)",
                        f"LA(x1, {ret_label})",
                        f"LA(x{rs1_val}, {pfx}_tgt_lpad_match_retra)",
                        *_indirect_branch("jalr", rs1_val, rd_is_x7=False),
                        f"{ret_label}:",
                        *_read_pelp(xlpe, chk),
                        write_sigupd(chk, td),
                    ]
                    continue
                out += [
                    "",
                    td.add_testcase(tc, CP_ELP_UPDATE, cg),
                    f"LA(x{rs1_val}, {tgt_label})",
                    *_indirect_branch("jalr", rs1_val, rd_is_x7=True),
                    *_read_pelp(xlpe, chk),
                    write_sigupd(chk, td),
                ]

    out.append("#ifdef ZCA_SUPPORTED")
    for lpe in [0, 1]:
        out.extend(_set_lpe(xlpe, tmp, bool(lpe)))
        for name in ("c.jr", "c.jalr"):
            for rs1_val in COMP_REGS:
                # rs1=x7 would hold the target, leaving nothing to return through
                if rs1_val == 7:
                    continue
                for dest, tgt_label in [
                    ("lpad_zero", f"{pfx}_tgt_lpad_zero"),
                    ("lpad_match", f"{pfx}_tgt_lpad_match"),
                    ("lpad_mismatch", f"{pfx}_tgt_lpad_mismatch"),
                    ("nonlpad", f"{pfx}_tgt_nonlpad"),
                ]:
                    if _unsafe_for_mmode(lpe, dest, rs1_val):
                        continue
                    tc = _tid(pfx, f"lpe{lpe}", name, f"rs1_{rs1_val}", dest)
                    ret_label = f"{tc}_ret"
                    if dest == "lpad_match" and rs1_val not in LINK_REGS:
                        # as above: x7 holds the label, ra the return address
                        out += [
                            "",
                            td.add_testcase(tc, CP_ELP_UPDATE, cg),
                            "LI(x7, 0xabcde000)",
                            f"LA(x1, {ret_label})",
                            f"LA(x{rs1_val}, {pfx}_tgt_lpad_match_retra)",
                            *_indirect_branch(name, rs1_val, rd_is_x7=False),
                            f"{ret_label}:",
                            *_read_pelp(xlpe, chk),
                            write_sigupd(chk, td),
                        ]
                        continue
                    out += [
                        "",
                        td.add_testcase(tc, CP_ELP_UPDATE, cg),
                        # c.jr/c.jalr never write x7, which the trampoline returns through
                        f"LA(x7, {ret_label})",
                        f"LA(x{rs1_val}, {tgt_label})",
                        *_indirect_branch(name, rs1_val, rd_is_x7=False),
                        f"{ret_label}:",
                        *_read_pelp(xlpe, chk),
                        write_sigupd(chk, td),
                    ]
    out.append("#endif // ZCA_SUPPORTED")

    td.int_regs.return_registers([rs1, tmp, chk])
    return out


def _lpad_zero_label_bypass(pfx: str, td: TestData, cg: str, xlpe: XLPEConfig, xlen: int) -> list[str]:
    """CP_LPAD_BYPASS: LPL=0, ELP=1. x7_label (zero/nonzero)."""
    rs1, tmp, chk = td.int_regs.get_registers(3, exclude_regs=[1])
    out = [comment_banner(f"{pfx}: LPAD LPL=0 Bypass")]
    out.extend(_set_lpe(xlpe, tmp, True))
    out.extend(_set_pelp(xlpe, tmp))

    # x7 is zeroed to cover x7_label, so the jump can't write it: return via ra
    tc = _tid(pfx, "bypass", "x7_zero")
    ret_label = f"{tc}_ret"
    out += [
        "",
        td.add_testcase(tc, CP_LPAD_BYPASS, cg),
        "LI(x7, 0x0)",
        f"LA(x1, {ret_label})",
        f"LA(x{rs1}, {pfx}_tgt_lpad_zero_retra)",
        *_indirect_branch("jalr", rs1, rd_is_x7=False),
        f"{ret_label}:",
        *_read_pelp(xlpe, chk),
        write_sigupd(chk, td),
    ]

    tc = _tid(pfx, "bypass", "x7_nonzero")
    out += [
        "",
        td.add_testcase(tc, CP_LPAD_BYPASS, cg),
        f"LA(x{rs1}, {pfx}_tgt_lpad_zero)",
        *_indirect_branch("jalr", rs1, rd_is_x7=True),
        *_read_pelp(xlpe, chk),
        write_sigupd(chk, td),
    ]

    # sc4 bin (LPL!=0, x7=0), skipped in M-mode where a fault would recurse
    if xlpe.csr != "mseccfg":
        tc = _tid(pfx, "scenario", "sc4")
        ret_label = f"{tc}_ret"
        out += [
            "",
            td.add_testcase(tc, CP_LPAD_SCENARIO, cg),
            "LI(x7, 0x0)",
            f"LA(x1, {ret_label})",
            f"LA(x{rs1}, {pfx}_tgt_lpad_zero_nonzero_retra)",
            *_indirect_branch("jalr", rs1, rd_is_x7=False),
            f"{ret_label}:",
            *_read_pelp(xlpe, chk),
            write_sigupd(chk, td),
        ]

    td.int_regs.return_registers([rs1, tmp, chk])
    return out


def _lpad_valid_execution(pfx: str, td: TestData, cg: str, xlpe: XLPEConfig, xlen: int) -> list[str]:
    """CP_LPAD_VALID: LPL!=0, Match."""
    rs1, tmp, chk = td.int_regs.get_registers(3, exclude_regs=[1])
    out = [comment_banner(f"{pfx}: Valid LPAD Execution (Match)")]
    out.extend(_set_lpe(xlpe, tmp, True))
    out.extend(_set_pelp(xlpe, tmp))

    # A match needs x7[31:12] to equal the target's label, so set x7 explicitly
    # and return via ra.
    tc = _tid(pfx, "valid", "match")
    ret_label = f"{tc}_ret"
    out += [
        "",
        td.add_testcase(tc, CP_LPAD_VALID, cg),
        "LI(x7, 0xabcde000)",
        f"LA(x1, {ret_label})",
        f"LA(x{rs1}, {pfx}_tgt_lpad_match_retra)",
        *_indirect_branch("jalr", rs1, rd_is_x7=False),
        f"{ret_label}:",
        *_read_pelp(xlpe, chk),
        write_sigupd(chk, td),
    ]

    td.int_regs.return_registers([rs1, tmp, chk])
    return out


def _lpad_label_match(pfx: str, td: TestData, cg: str, xlpe: XLPEConfig, xlen: int) -> list[str]:
    """CP_LPAD_SCENARIO sc1_match: LPAD whose label equals x7's upper bits.

    The coverpoint compares against what the preceding instruction wrote to x7,
    so a lui feeds the pad in sequential flow, where ELP is not armed.
    """
    chk = td.int_regs.get_registers(1)[0]
    tc = _tid(pfx, "scenario", "sc1_match")
    out = [
        comment_banner(f"{pfx}: LPAD Label Match (sequential)"),
        "",
        td.add_testcase(tc, CP_LPAD_SCENARIO, cg),
        ".option push",
        ".option norvc",
        ".p2align 2",
        "lui x7, 0xAB",
        f".word {hex(_lpad_encoding(0xABCDE))}",
        ".option pop",
        *_read_pelp(xlpe, chk),
        write_sigupd(chk, td),
    ]
    td.int_regs.return_registers([chk])
    return out


def _lpad_faults(pfx: str, td: TestData, cg: str, xlpe: XLPEConfig, xlen: int) -> list[str]:
    """CP_LPAD_MISSING, CP_LPAD_MISMATCH, CP_EXC_DELIVERY, CP_LPAD_SCENARIO."""
    # Every case here traps with LPE=1, which recurses in M-mode
    if xlpe.csr == "mseccfg":
        return []
    rs1, tmp, chk = td.int_regs.get_registers(3)
    out = [comment_banner(f"{pfx}: LPAD Faults & Scenarios")]
    out.extend(_set_lpe(xlpe, tmp, True))
    out.extend(_set_pelp(xlpe, tmp))

    # mcause/mtval are M-mode-only here, so the framework's trap signature records them
    tc = _tid(pfx, "fault", "missing")
    out += [
        "",
        td.add_testcase(tc, CP_LPAD_MISSING, cg),
        td.add_testcase(tc, CP_LPAD_SCENARIO, cg),
        f"LA(x{rs1}, {pfx}_tgt_nonlpad)",
        *_indirect_branch("jalr", rs1, rd_is_x7=True),
        *_read_pelp(xlpe, chk),
        write_sigupd(chk, td),
    ]

    tc = _tid(pfx, "fault", "mismatch")
    out += [
        "",
        td.add_testcase(tc, CP_LPAD_MISMATCH, cg),
        td.add_testcase(tc, CP_LPAD_SCENARIO, cg),
        f"LA(x{rs1}, {pfx}_tgt_lpad_mismatch)",
        *_indirect_branch("jalr", rs1, rd_is_x7=True),
        *_read_pelp(xlpe, chk),
        write_sigupd(chk, td),
    ]

    # x7==0 bypasses the label check, so this does not fault
    td.int_regs.return_registers([rs1, tmp, chk])
    rs1, tmp, chk, rd_tmp = td.int_regs.get_registers(4, exclude_regs=[1])
    tc = _tid(pfx, "fault", "x7_zero_mismatch")
    ret_label = f"{tc}_ret"
    out += [
        "",
        td.add_testcase(tc, CP_LPAD_MISMATCH, cg),
        "LI(x7, 0x0)",
        f"LA(x1, {ret_label})",
        f"LA(x{rs1}, {pfx}_tgt_lpad_match_retra)",
        *_indirect_branch("jalr", rs1, rd_is_x7=False),
        f"{ret_label}:",
        *_read_pelp(xlpe, chk),
        write_sigupd(chk, td),
    ]

    tc = _tid(pfx, "exc_delivery")
    out += [
        "",
        td.add_testcase(tc, CP_EXC_DELIVERY, cg),
        f"LA(x{rs1}, {pfx}_tgt_nonlpad)",
        *_indirect_branch("jalr", rs1, rd_is_x7=True),
        *_read_pelp(xlpe, chk),
        write_sigupd(chk, td),
    ]

    td.int_regs.return_registers([rs1, tmp, chk, rd_tmp])
    return out


def _disabled(pfx: str, td: TestData, cg: str, xlpe: XLPEConfig, xlen: int) -> list[str]:
    """CP_LPE_DISABLED: LPE=0, LPAD(LPL!=0) executes as NOP."""
    rs1, tmp, chk = td.int_regs.get_registers(3)
    out = [comment_banner(f"{pfx}: LPE=0 (LPAD is NOP)")]
    out.extend(_set_lpe(xlpe, tmp, False))

    tc = _tid(pfx, "lpe0", "nop")
    out += [
        "",
        td.add_testcase(tc, CP_LPE_DISABLED, cg),
        f"LA(x{rs1}, {pfx}_tgt_lpad_match)",
        *_indirect_branch("jalr", rs1, rd_is_x7=True),
        *_read_pelp(xlpe, chk),
        write_sigupd(chk, td),
    ]

    td.int_regs.return_registers([rs1, tmp, chk])
    return out


def _lpad_no_sw_exception_elp_clear(pfx: str, td: TestData, cg: str, xlpe: XLPEConfig, xlen: int) -> list[str]:
    """CP_ELP_CLEAR: LPL=0 LPAD clears ELP (PELP)."""
    rs1, tmp, chk = td.int_regs.get_registers(3)
    out = [comment_banner(f"{pfx}: ELP Clear (LPL=0)")]
    out.extend(_set_lpe(xlpe, tmp, True))
    out.extend(_set_pelp(xlpe, tmp))

    tc = _tid(pfx, "elp_clear")
    out += [
        "",
        td.add_testcase(tc, CP_ELP_CLEAR, cg),
        f"LA(x{rs1}, {pfx}_tgt_lpad_zero)",
        *_indirect_branch("jalr", rs1, rd_is_x7=True),
        *_read_pelp(xlpe, chk),
        write_sigupd(chk, td),
    ]

    td.int_regs.return_registers([rs1, tmp, chk])
    return out


# M-mode only passes
def _pelp_trap_entry(pfx: str, td: TestData, cg: str, xlpe: XLPEConfig, xlen: int) -> list[str]:
    """CP_PELP_ENTRY, CP_PELP_GUARDED, CP_ELP_PRESERVE (M-mode only).

    Disabled: an M-mode trap with mseccfg.MLPE=1 recurses in the trap dispatcher.
    """
    return []


def _pelp_trap_return(pfx: str, td: TestData, cg: str, xlpe: XLPEConfig, xlen: int) -> list[str]:
    """CP_PELP_RET (M-mode only).  Disabled, see _pelp_trap_entry."""
    return []


def _exception_priority(pfx: str, td: TestData, cg: str, xlpe: XLPEConfig, xlen: int) -> list[str]:
    """CP_EXC_PRIORITY: ELP=1, Jump to Fault Address.

    Disabled: a jump to RVMODEL_ACCESS_FAULT_ADDRESS does not resume, so it needs
    a chunk of its own before the rest of the sequence can follow it.
    """
    return []


# per-mode emitter


def emit_mode(
    td: TestData,
    mode: str,
    cg: str,
    xlen: int,
    satp_mode: str = "bare",
    trampoline_section: str = ".text.rvtest",
    skip_trampoline_fallthrough: bool = False,
) -> list[str]:
    """Generate the test sequence for one mode, xlen and satp mode.

    trampoline_section is the section the LPAD targets land in, and
    skip_trampoline_fallthrough jumps around them so mode-entry code cannot
    fall into _tgt_lpad_zero.
    """
    xlpe = _get_xlpe_config(mode, xlen)
    pfx = f"{mode}_{satp_mode}_rv{xlen}"

    lines = []
    if xlpe.guard:
        lines.append(xlpe.guard)
    lines += [comment_banner(f"Zicfilp {mode.upper()} Mode {satp_mode.upper()} (RV{xlen})", cg)]

    lines += _data_section()

    # satp and sfence.vma only exist when S-mode does
    has_satp = mode != "umode_nos"
    is_translation_mode = satp_mode in ("sv39", "sv48", "sv57")
    if not has_satp:
        pass
    elif mode in ("smode", "umode") and is_translation_mode:
        lines += _data_slvl_tables(satp_mode)
        lines += satp_setup(xlen, satp_mode, grant_umode_access=(mode == "umode"))
    else:
        lines += satp_setup(xlen, "bare")

    lines += [GOTO_MMODE]
    lines += _set_lpe(xlpe, 10, True)
    if mode in ("smode", "umode", "umode_nos"):
        lines += ["csrw medeleg, x0", "csrw mideleg, x0"]
        lines += [GOTO_SMODE if mode == "smode" else GOTO_UMODE]

    lines += [f"LA(x{REP_NON_LINK}, zicfilp_scratch)"]

    # The trampolines follow the mode-entry code, so that canary_check's jump to
    # the start of .text.rvtest lands on real test code.
    trampoline_end = f"{pfx}_trampolines_end"
    if skip_trampoline_fallthrough:
        lines += [f"j {trampoline_end}"]
    lines += _trampoline_section(pfx, section=trampoline_section, self_heal_elp=xlpe.clear_live_elp)
    if skip_trampoline_fallthrough:
        lines += [f"{trampoline_end}:"]

    lines += _indirect_elp_state_update(pfx, td, cg, xlpe, xlen)
    lines += _lpad_zero_label_bypass(pfx, td, cg, xlpe, xlen)
    lines += _lpad_valid_execution(pfx, td, cg, xlpe, xlen)
    lines += _lpad_label_match(pfx, td, cg, xlpe, xlen)
    lines += _lpad_faults(pfx, td, cg, xlpe, xlen)
    lines += _disabled(pfx, td, cg, xlpe, xlen)
    lines += _lpad_no_sw_exception_elp_clear(pfx, td, cg, xlpe, xlen)
    lines += _exception_priority(pfx, td, cg, xlpe, xlen)

    if mode == "mmode":
        lines += _pelp_trap_entry(pfx, td, cg, xlpe, xlen)
        lines += _pelp_trap_return(pfx, td, cg, xlpe, xlen)

    # Disable LPE and clear any armed ELP before teardown ecalls back to M-mode
    lines += _set_lpe(xlpe, 10, False)
    lines += _clear_pelp(xlpe)
    lines += teardown_vm(has_satp=has_satp)
    if xlpe.guard:
        lines.append(f"#endif // {xlpe.guard.split()[-1]}")
    return lines


__all__ = [
    "COVERGROUP_M",
    "COVERGROUP_S",
    "COVERGROUP_U_NS",
    "COVERGROUP_U_S",
    "MODES",
    "MODE_GUARDS",
    "_data_section",
    "_data_slvl_tables",
    "_trampoline_section",
    "both_xlens",
    "both_xlens_bare",
    "emit_mode",
]
