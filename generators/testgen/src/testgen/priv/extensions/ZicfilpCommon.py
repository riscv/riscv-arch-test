##################################
# priv/extensions/ZicfilpCommon.py
#
# Zicfilp (Control-Flow Integrity - Landing Pads) shared test infrastructure.
# Author : Eman Nasar  email:fatehulnasareman@gmail.com (UET, May 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared Zicfilp extension test infrastructure.
Common code for ZicfilpSm (M-mode), ZicfilpS (S-mode), ZicfilpUS (U+S), ZicfilpU (U-S)
test generators.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS & ISA ENCODINGS (Priv Spec 1.12)
# ═══════════════════════════════════════════════════════════════════════════

# CSR Bit Positions (ALL Bit 12 per Spec)
_MSECCFG_MLPE_BIT = 10  # mseccfg.MLPE
_MENVCFG_LPE_BIT = 12  # menvcfg.LPE
_SENVCFG_LPE_BIT = 12  # senvcfg.LPE
_MSTATUS_MPELP_BIT = 41  # mstatus.MPELP on RV64
_MSTATUSH_MPELP_BIT = 9  # mstatush.MPELP on RV32
_SSTATUS_SPELP_BIT = 23  # sstatus.SPELP

# Exception Constants
CAUSE_SW_CHECK = 18  # LPAD Mismatch / Missing
XTVAL_LPAD_FAULT = 2  # mtval/stval code for LPAD fault

# Coverpoint Names (Exact match to SVH)
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

# Covergroup Names
COVERGROUP_M = "Zicfilp_Sm_cg"
COVERGROUP_S = "Zicfilp_s_cg"
COVERGROUP_U_S = "Zicfilpsu_cg"
COVERGROUP_U_NS = "Zicfilp_u_cg"

# Register Constraints
LINK_REGS = {1, 5, 7}  # x1=ra, x5, x7 (ELP)
RESERVED_REGS = {2, 3, 4, 8}
ALL_REGS = [r for r in range(1, 32) if r not in RESERVED_REGS]
COMP_REGS = [r for r in range(1, 16) if r not in RESERVED_REGS]
NON_LINK_REGS = [r for r in ALL_REGS if r not in LINK_REGS]
NON_LINK_COMP_REGS = [r for r in COMP_REGS if r not in LINK_REGS]
REP_NON_LINK = 28
REP_LINK = 1

# SATP Modes
MODES = ["bare", "sv39", "sv48", "sv57"]
MODE_GUARDS = {m: None if m == "bare" else f"{m.upper()}_SUPPORTED" for m in MODES}
LEVELS_BELOW_ROOT = {"sv39": 2, "sv48": 3, "sv57": 4}

GOTO_MMODE = "RVTEST_GOTO_MMODE"
GOTO_SMODE = "RVTEST_TSBI_GOTO_SMODE"
GOTO_UMODE = "RVTEST_TSBI_GOTO_UMODE"

# ═══════════════════════════════════════════════════════════════════════════
# MODE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class XLPEConfig:
    csr: str  # CSR containing LPE bit
    bit: int  # Bit position (12)
    name: str  # "MLPE" or "LPE"
    pelp_csr: str  # CSR containing PELP bit ("mstatus", "mstatush", "sstatus")
    pelp_bit: int  # Bit position (12)
    guard: str = ""  # Conditional compilation guard


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
        )
    elif mode == "umode":  # U-mode with S-mode implemented
        return XLPEConfig(
            "senvcfg",
            _SENVCFG_LPE_BIT,
            "LPE",
            pelp_csr="sstatus",
            pelp_bit=_SSTATUS_SPELP_BIT,
            guard="#ifdef S_SUPPORTED",
        )
    elif mode == "umode_nos":  # U-mode, No S-mode
        pelp_csr = "mstatus" if xlen == 64 else "mstatush"
        return XLPEConfig(
            "menvcfg",
            _MENVCFG_LPE_BIT,
            "LPE",
            pelp_csr=pelp_csr,
            pelp_bit=_MSTATUS_MPELP_BIT,
            guard="#ifndef S_SUPPORTED",
        )
    raise ValueError(f"Unknown mode: {mode}")


# ═══════════════════════════════════════════════════════════════════════════
# ASSEMBLY HELPERS
# ═══════════════════════════════════════════════════════════════════════════


def _fixed(instr: str) -> list[str]:
    return [".option push", ".option norvc", instr, ".option pop"]


def _fixed_block(body: list[str]) -> list[str]:
    return [".option push", ".option norvc", *body, ".option pop"]


def _tid(prefix: str, *parts: str) -> str:
    return f"{prefix}_{'_'.join(str(p).replace('.', '_') for p in parts)}"


def _la(reg: int, label: str) -> list[str]:
    return [f"LA(x{reg}, {label})"]


def _li(reg: int, val: int) -> list[str]:
    return [f"LI(x{reg}, {hex(val)})"]


def _csrr(dst: int, csr: str) -> list[str]:
    return [f"csrr x{dst}, {csr}"]


def _csrw(csr: str, src: int) -> list[str]:
    return [f"csrw {csr}, x{src}"]


def _csrrc(csr: str, src: int) -> list[str]:
    return [f"csrc {csr}, x{src}"]


def _csrrs(csr: str, src: int) -> list[str]:
    return [f"csrs {csr}, x{src}"]


def _emit_jalr_rd_x7(rs1: int) -> str:
    """JALR x7, 0(rs1) -- Updates ELP (x7) with Return Address (PC+4)."""
    return f"jalr x7, 0(x{rs1})"


def _emit_c_jr(rs1: int) -> str:
    return f"c.jr x{rs1}"


def _emit_c_jalr(rs1: int) -> str:
    return f"c.jalr x{rs1}"


def _indirect_branch(name: str, rs1: int, rd_is_x7: bool) -> list[str]:
    """Emit indirect branch. If rd_is_x7, uses JALR x7 (updates ELP). Else uses temp rd."""
    if name == "jalr":
        if rd_is_x7:
            return _fixed(_emit_jalr_rd_x7(rs1))
        else:
            rd = 10  # temp
            return _fixed(f"jalr x{rd}, 0(x{rs1})")
    elif name == "c.jr":
        return [_emit_c_jr(rs1)]
    elif name == "c.jalr":
        return [_emit_c_jalr(rs1)]
    raise ValueError(f"Unknown branch: {name}")


def _set_lpe(xlpe: XLPEConfig, reg: int, en: bool) -> list[str]:
    act = "csrs" if en else "csrc"
    msk = 1 << xlpe.bit
    guard = xlpe.guard
    lines = []
    if guard:
        lines.append(guard)
    lines += [
        f"# {xlpe.csr}.{xlpe.name} = {int(en)}",
        f"LI(x{reg}, {hex(msk)})",
        f"{act} {xlpe.csr}, x{reg}",
    ]
    if guard:
        lines.append(f"#endif // {guard.split()[-1]}")
    return lines


def _read_pelp(xlpe: XLPEConfig, dst: int) -> list[str]:
    """Read xPELP bit into dst."""
    guard = xlpe.guard
    lines = []
    if guard:
        lines.append(guard)
    lines += [
        f"csrr x{dst}, {xlpe.pelp_csr}",
        f"srli x{dst}, x{dst}, {xlpe.pelp_bit}",
        f"andi x{dst}, x{dst}, 1",
    ]
    if guard:
        lines.append(f"#endif // {guard.split()[-1]}")
    return lines


# ═══════════════════════════════════════════════════════════════════════════
# LPAD ENCODING HELPER
# ═══════════════════════════════════════════════════════════════════════════


def _lpad_encoding(label_20bit: int) -> int:
    """
    LPAD Custom Encoding:
    [31:12] = LPL (20 bits)
    [11:7]  = rd = 0
    [6:0]   = AUIPC opcode 0x17
    """
    return ((label_20bit & 0xFFFFF) << 12) | 0x017


# ═══════════════════════════════════════════════════════════════════════════
# TEXT-SECTION TRAMPOLINES (Jump Targets)
# ═══════════════════════════════════════════════════════════════════════════


def _trampoline_section(pfx: str) -> list[str]:
    """
    Emits LPAD targets with CORRECT encoding (rs1=x7).
    Labels:
      _tgt_lpad_zero          : Label=0,     LPL=0 (0x017)
      _tgt_lpad_match         : Label=PC+4,  LPL=1 (0x117) -- Match occurs naturally if JALR x7 falls through
      _tgt_lpad_mismatch      : Label=0x12345, LPL=1
      _tgt_lpad_zero_nonzero  : Label=0xABCDE, LPL=0 (For sc4 bin)
      _tgt_nonlpad            : NOP
    """
    enc_zero = _lpad_encoding(0x00000)  # LPL=0
    enc_match = _lpad_encoding(0xABCDE)  # LPL=0xABCDE
    enc_mismatch = _lpad_encoding(0x12345)  # LPL=0x12345
    enc_zero_nz = _lpad_encoding(0xABCDE)  # LPL=0xABCDE (for sc4)

    return [
        "",
        "# ── Zicfilp LPAD Targets (rs1=x7 encoded) ─────────────────",
        ".pushsection .text",
        ".p2align 2",
        f"{pfx}_tgt_lpad_zero:",
        f"  .word {hex(enc_zero)}",
        "  nop",
        "  jr x7",
        "",
        ".p2align 2",
        f"{pfx}_tgt_lpad_match:",
        f"  .word {hex(enc_match)}",
        "  nop",
        "  jr x7",
        "",
        ".p2align 2",
        f"{pfx}_tgt_lpad_mismatch:",
        f"  .word {hex(enc_mismatch)}",
        "  nop",
        "  jr x7",
        "",
        ".p2align 2",
        f"{pfx}_tgt_lpad_zero_nonzero:",
        f"  .word {hex(enc_zero_nz)}",
        "  nop",
        "  jr x7",
        "",
        ".p2align 2",
        f"{pfx}_tgt_nonlpad:",
        "  nop",
        "  nop",
        "  jr x7",
        ".popsection",
        "",
    ]


# ═══════════════════════════════════════════════════════════════════════════
# DATA SECTION
# ═══════════════════════════════════════════════════════════════════════════


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
    """SAFE: Returns empty list for 'bare' mode."""
    if mode == "bare":
        return []
    lines: list[str] = []
    for i in range(LEVELS_BELOW_ROOT[mode]):
        lines += [".p2align 12", f"rvtest_slvl{i}_pg_tbl: .zero 4096"]
    return lines


# ═══════════════════════════════════════════════════════════════════════════
# XLEN / MODE HELPERS
# ═══════════════════════════════════════════════════════════════════════════


def both_xlens(build: Callable[[int], list[str]]) -> list[str]:
    """Emit build(64) and build(32) inside XLEN guards."""
    return [
        "#if __riscv_xlen == 64",
        "#ifdef SV39_SUPPORTED",
        *build(64),
        "#endif // SV39_SUPPORTED",
        "#else",
        "#ifdef SV32_SUPPORTED",
        *build(32),
        "#endif // SV32_SUPPORTED",
        "#endif // __riscv_xlen",
    ]


def satp_setup(xlen: int, mode: str) -> list[str]:
    if mode == "bare":
        return ["csrwi satp, 0", "sfence.vma"]
    return [f"SATP_SETUP_RV{'64' if xlen == 64 else '32'}({mode})", "sfence.vma"]


def teardown_vm() -> list[str]:
    return [GOTO_MMODE, "csrwi satp, 0", "sfence.vma", ""]


# ═══════════════════════════════════════════════════════════════════════════
# SCENARIO BUILDERS (Return List[str] for a specific xlen)
# ═══════════════════════════════════════════════════════════════════════════

# NOTE: write_sigupd returns one multiline assembly string.


def _build_elp_update(pfx: str, td: TestData, cg: str, xlpe: XLPEConfig, xlen: int) -> list[str]:
    """CP_ELP_UPDATE: Indirect CT (JALR x7) -> LPAD. Vary LPE, RS1, Dest."""
    rs1, tmp, chk = td.int_regs.get_registers(3)
    out = [comment_banner(f"{pfx}: ELP Update (JALR x7 -> LPAD)")]

    for lpe in [0, 1]:
        out.extend(_set_lpe(xlpe, tmp, bool(lpe)))

        # 1. Uncompressed JALR (rd=x7)
        for rs1_val in ALL_REGS:
            for dest, tgt_label in [
                ("lpad_zero", f"{pfx}_tgt_lpad_zero"),
                ("lpad_match", f"{pfx}_tgt_lpad_match"),
                ("lpad_mismatch", f"{pfx}_tgt_lpad_mismatch"),
                ("nonlpad", f"{pfx}_tgt_nonlpad"),
            ]:
                tc = _tid(pfx, f"lpe{lpe}", "jalr", f"rs1_{rs1_val}", dest)
                out += [
                    "",
                    td.add_testcase(tc, CP_ELP_UPDATE, cg),
                    f"# LPE={lpe} JALR x7 rs1=x{rs1_val} -> {dest}",
                    *_la(rs1_val, tgt_label),
                    *_indirect_branch("jalr", rs1_val, rd_is_x7=True),
                    *_read_pelp(xlpe, chk),
                    write_sigupd(chk, td),
                ]
                if lpe and dest in ("nonlpad", "lpad_mismatch"):
                    out += [*_csrr(chk, "mcause"), write_sigupd(chk, td), *_csrr(chk, "mtval"), write_sigupd(chk, td)]

    # 2. Compressed (ZCA) - Outside outer lpe loop to prevent duplication
    out.append("#ifdef ZCA_SUPPORTED")
    for lpe in [0, 1]:
        out.extend(_set_lpe(xlpe, tmp, bool(lpe)))
        for name in ("c.jr", "c.jalr"):
            for rs1_val in COMP_REGS:
                for dest, tgt_label in [
                    ("lpad_zero", f"{pfx}_tgt_lpad_zero"),
                    ("lpad_match", f"{pfx}_tgt_lpad_match"),
                    ("lpad_mismatch", f"{pfx}_tgt_lpad_mismatch"),
                    ("nonlpad", f"{pfx}_tgt_nonlpad"),
                ]:
                    tc = _tid(pfx, f"lpe{lpe}", name, f"rs1_{rs1_val}", dest)
                    out += [
                        "",
                        td.add_testcase(tc, CP_ELP_UPDATE, cg),
                        f"# LPE={lpe} {name} rs1=x{rs1_val} -> {dest}",
                        *_la(rs1_val, tgt_label),
                        *_indirect_branch(name, rs1_val, rd_is_x7=False),
                        *_read_pelp(xlpe, chk),
                        write_sigupd(chk, td),
                    ]
    out.append("#endif // ZCA_SUPPORTED")

    td.int_regs.return_registers([rs1, tmp, chk])
    return out


def _build_bypass(pfx: str, td: TestData, cg: str, xlpe: XLPEConfig, xlen: int) -> list[str]:
    """CP_LPAD_BYPASS: LPL=0, ELP=1. x7_label (zero/nonzero)."""
    rs1, tmp, chk = td.int_regs.get_registers(3)
    out = [comment_banner(f"{pfx}: LPAD LPL=0 Bypass")]
    out.extend(_set_lpe(xlpe, tmp, True))

    # Case 1: x7_label.zero (ins.prev.x_wdata[7] == 0)
    tc = _tid(pfx, "bypass", "x7_zero")
    out += [
        "",
        td.add_testcase(tc, CP_LPAD_BYPASS, cg),
        *_li(7, 0),
        *_la(rs1, f"{pfx}_tgt_lpad_zero"),
        *_indirect_branch("jalr", rs1, rd_is_x7=False),
        *_read_pelp(xlpe, chk),
        write_sigupd(chk, td),
    ]

    # Case 2: x7_label.nonzero
    tc = _tid(pfx, "bypass", "x7_nonzero")
    out += [
        "",
        td.add_testcase(tc, CP_LPAD_BYPASS, cg),
        *_la(rs1, f"{pfx}_tgt_lpad_zero"),
        *_indirect_branch("jalr", rs1, rd_is_x7=True),
        *_read_pelp(xlpe, chk),
        write_sigupd(chk, td),
    ]

    # Case 3: sc4 bin (LPL=0, Label!=0, x7=0)
    tc = _tid(pfx, "scenario", "sc4")
    out += [
        "",
        td.add_testcase(tc, CP_LPAD_SCENARIO, cg),
        *_li(7, 0),
        *_la(rs1, f"{pfx}_tgt_lpad_zero_nonzero"),
        *_indirect_branch("jalr", rs1, rd_is_x7=False),
        *_read_pelp(xlpe, chk),
        write_sigupd(chk, td),
    ]

    td.int_regs.return_registers([rs1, tmp, chk])
    return out


def _build_valid(pfx: str, td: TestData, cg: str, xlpe: XLPEConfig, xlen: int) -> list[str]:
    """CP_LPAD_VALID: LPL!=0, Match."""
    rs1, tmp, chk = td.int_regs.get_registers(3)
    out = [comment_banner(f"{pfx}: Valid LPAD Execution (Match)")]
    out.extend(_set_lpe(xlpe, tmp, True))

    tc = _tid(pfx, "valid", "match")
    out += [
        "",
        td.add_testcase(tc, CP_LPAD_VALID, cg),
        *_la(rs1, f"{pfx}_tgt_lpad_match"),
        *_indirect_branch("jalr", rs1, rd_is_x7=True),
        *_read_pelp(xlpe, chk),
        write_sigupd(chk, td),
    ]

    td.int_regs.return_registers([rs1, tmp, chk])
    return out


def _build_faults(pfx: str, td: TestData, cg: str, xlpe: XLPEConfig, xlen: int) -> list[str]:
    """CP_LPAD_MISSING, CP_LPAD_MISMATCH, CP_EXC_DELIVERY, CP_LPAD_SCENARIO."""
    rs1, tmp, chk = td.int_regs.get_registers(3)
    out = [comment_banner(f"{pfx}: LPAD Faults & Scenarios")]
    out.extend(_set_lpe(xlpe, tmp, True))

    # 1. Missing Instruction -> sc3_not_lpad
    tc = _tid(pfx, "fault", "missing")
    out += [
        "",
        td.add_testcase(tc, CP_LPAD_MISSING, cg),
        td.add_testcase(tc, CP_LPAD_SCENARIO, cg),
        *_la(rs1, f"{pfx}_tgt_nonlpad"),
        *_indirect_branch("jalr", rs1, rd_is_x7=True),
        *_csrr(chk, "mcause"),
        write_sigupd(chk, td),
        *_csrr(chk, "mtval"),
        write_sigupd(chk, td),
        *_read_pelp(xlpe, chk),
        write_sigupd(chk, td),
    ]

    # 2. Label Mismatch -> sc2_mismatch
    tc = _tid(pfx, "fault", "mismatch")
    out += [
        "",
        td.add_testcase(tc, CP_LPAD_MISMATCH, cg),
        td.add_testcase(tc, CP_LPAD_SCENARIO, cg),
        *_la(rs1, f"{pfx}_tgt_lpad_mismatch"),
        *_indirect_branch("jalr", rs1, rd_is_x7=True),
        *_csrr(chk, "mcause"),
        write_sigupd(chk, td),
        *_csrr(chk, "mtval"),
        write_sigupd(chk, td),
        *_read_pelp(xlpe, chk),
        write_sigupd(chk, td),
    ]

    # 3. x7=0, LPL!=0, Label!=0
    td.int_regs.return_registers([rs1, tmp, chk])
    rs1, tmp, chk, rd_tmp = td.int_regs.get_registers(4)
    tc = _tid(pfx, "fault", "x7_zero_mismatch")
    out += [
        "",
        td.add_testcase(tc, CP_LPAD_MISMATCH, cg),
        *_li(7, 0),
        *_la(rs1, f"{pfx}_tgt_lpad_match"),
        *_indirect_branch("jalr", rs1, rd_is_x7=False),
        *_csrr(chk, "mcause"),
        write_sigupd(chk, td),
        *_csrr(chk, "mtval"),
        write_sigupd(chk, td),
        *_read_pelp(xlpe, chk),
        write_sigupd(chk, td),
    ]

    # 4. Exception Delivery Cross
    tc = _tid(pfx, "exc_delivery")
    out += [
        "",
        td.add_testcase(tc, CP_EXC_DELIVERY, cg),
        *_la(rs1, f"{pfx}_tgt_nonlpad"),
        *_indirect_branch("jalr", rs1, rd_is_x7=True),
        *_csrr(chk, "mcause"),
        write_sigupd(chk, td),
        *_csrr(chk, "mtval"),
        write_sigupd(chk, td),
    ]

    td.int_regs.return_registers([rs1, tmp, chk, rd_tmp])
    return out


def _build_disabled(pfx: str, td: TestData, cg: str, xlpe: XLPEConfig, xlen: int) -> list[str]:
    """CP_LPE_DISABLED: LPE=0, LPAD(LPL!=0) executes as NOP."""
    rs1, tmp, chk = td.int_regs.get_registers(3)
    out = [comment_banner(f"{pfx}: LPE=0 (LPAD is NOP)")]
    out.extend(_set_lpe(xlpe, tmp, False))

    tc = _tid(pfx, "lpe0", "nop")
    out += [
        "",
        td.add_testcase(tc, CP_LPE_DISABLED, cg),
        *_la(rs1, f"{pfx}_tgt_lpad_match"),
        *_indirect_branch("jalr", rs1, rd_is_x7=True),
        *_read_pelp(xlpe, chk),
        write_sigupd(chk, td),
    ]

    td.int_regs.return_registers([rs1, tmp, chk])
    return out


def _build_elp_clear(pfx: str, td: TestData, cg: str, xlpe: XLPEConfig, xlen: int) -> list[str]:
    """CP_ELP_CLEAR: LPL=0 LPAD clears ELP (PELP)."""
    rs1, tmp, chk = td.int_regs.get_registers(3)
    out = [comment_banner(f"{pfx}: ELP Clear (LPL=0)")]
    out.extend(_set_lpe(xlpe, tmp, True))

    tc = _tid(pfx, "elp_clear")
    out += [
        "",
        td.add_testcase(tc, CP_ELP_CLEAR, cg),
        *_la(rs1, f"{pfx}_tgt_lpad_zero"),
        *_indirect_branch("jalr", rs1, rd_is_x7=True),
        *_read_pelp(xlpe, chk),
        write_sigupd(chk, td),
    ]

    td.int_regs.return_registers([rs1, tmp, chk])
    return out


# ═══════════════════════════════════════════════════════════════════════════
# M-MODE ONLY PASSES (Sm Covergroup)
# ═══════════════════════════════════════════════════════════════════════════


def _build_trap_entry(pfx: str, td: TestData, cg: str, xlpe: XLPEConfig, xlen: int) -> list[str]:
    """CP_PELP_ENTRY, CP_PELP_GUARDED, CP_ELP_PRESERVE (M-mode only)."""
    if xlpe.pelp_csr not in ("mstatus", "mstatush"):
        return []
    rs1, tmp, chk = td.int_regs.get_registers(3)
    out = [comment_banner(f"{pfx}: PELP Trap Entry (M-mode)")]
    out.extend(_set_lpe(xlpe, tmp, True))

    tc = _tid(pfx, "trap", "elp1")
    out += [
        "",
        td.add_testcase(tc, CP_PELP_ENTRY, cg),
        td.add_testcase(tc, CP_ELP_PRESERVE, cg),
        *_la(REP_NON_LINK, f"{pfx}_tgt_lpad_zero"),
        *_indirect_branch("jalr", REP_NON_LINK, rd_is_x7=True),
        "ecall",
        *_read_pelp(xlpe, chk),
        write_sigupd(chk, td),
    ]

    tc = _tid(pfx, "trap", "elp0_link")
    out += [
        "",
        td.add_testcase(tc, CP_PELP_GUARDED, cg),
        td.add_testcase(tc, CP_ELP_PRESERVE, cg),
        *_la(REP_LINK, f"{pfx}_tgt_lpad_zero"),
        *_indirect_branch("jalr", REP_LINK, rd_is_x7=False),
        "ecall",
        *_read_pelp(xlpe, chk),
        write_sigupd(chk, td),
    ]

    td.int_regs.return_registers([rs1, tmp, chk])
    return out


def _build_trap_return(pfx: str, td: TestData, cg: str, xlpe: XLPEConfig, xlen: int) -> list[str]:
    """CP_PELP_RET (M-mode only)."""
    if xlpe.pelp_csr not in ("mstatus", "mstatush"):
        return []
    tmp, chk = td.int_regs.get_registers(2)
    out = [comment_banner(f"{pfx}: PELP Trap Return (MRET)")]

    for lpe_en, suffix in [(True, "lpe1"), (False, "lpe0")]:
        out.extend(_set_lpe(xlpe, tmp, lpe_en))
        tc = _tid(pfx, "trapret", suffix)
        out += [
            "",
            td.add_testcase(tc, CP_PELP_RET, cg),
            "ecall",
            *_read_pelp(xlpe, chk),
            write_sigupd(chk, td),
            "mret",
        ]

    out.extend(_set_lpe(xlpe, tmp, True))
    td.int_regs.return_registers([tmp, chk])
    return out


def _build_exc_priority(pfx: str, td: TestData, cg: str, xlpe: XLPEConfig, xlen: int) -> list[str]:
    """CP_EXC_PRIORITY: ELP=1, Jump to Fault Address."""
    rd, tmp, chk = td.int_regs.get_registers(3)
    out = [comment_banner(f"{pfx}: Exception Priority")]
    out.extend(_set_lpe(xlpe, tmp, True))
    out += [
        "#ifdef RVMODEL_ACCESS_FAULT_ADDRESS",
        "",
        td.add_testcase(_tid(pfx, "exc_prio"), CP_EXC_PRIORITY, cg),
        f"LI(x{REP_NON_LINK}, RVMODEL_ACCESS_FAULT_ADDRESS)",
        *_indirect_branch("jalr", REP_NON_LINK, rd_is_x7=True),
        *_csrr(chk, "mcause"),
        write_sigupd(chk, td),
        "#endif // RVMODEL_ACCESS_FAULT_ADDRESS",
    ]
    td.int_regs.return_registers([rd, tmp, chk])
    return out


# ═══════════════════════════════════════════════════════════════════════════
# MAIN PER-MODE EMITTER
# ═══════════════════════════════════════════════════════════════════════════


def emit_mode(td: TestData, mode: str, cg: str, xlen: int, satp_mode: str = "bare") -> list[str]:
    """
    Generates the complete test sequence for a specific mode/xlen/satp_mode.
    """
    xlpe = _get_xlpe_config(mode, xlen)
    pfx = f"{mode}_{satp_mode}_rv{xlen}"

    lines = []
    if xlpe.guard:
        lines.append(xlpe.guard)
    lines += [comment_banner(f"Zicfilp {mode.upper()} Mode {satp_mode.upper()} (RV{xlen})", cg)]

    # Data & Trampolines
    lines += _data_section()
    lines += _trampoline_section(pfx)

    # Page Tables & SATP -- EXPLICIT GUARD
    is_translation_mode = satp_mode in ("sv39", "sv48", "sv57")
    if mode in ("smode", "umode", "umode_nos") and is_translation_mode:
        lines += _data_slvl_tables(satp_mode)
        lines += satp_setup(xlen, satp_mode)
    else:
        lines += satp_setup(xlen, "bare")

    # M-mode Config
    lines += [GOTO_MMODE]
    lines += _set_lpe(xlpe, 10, True)
    if mode in ("smode", "umode", "umode_nos"):
        lines += ["csrw medeleg, x0", "csrw mideleg, x0"]
        lines += [GOTO_SMODE if mode == "smode" else GOTO_UMODE]
    else:
        lines += [GOTO_MMODE]

    lines += _la(REP_NON_LINK, "zicfilp_scratch")

    # COMMON PASSES
    lines += _build_elp_update(pfx, td, cg, xlpe, xlen)
    lines += _build_bypass(pfx, td, cg, xlpe, xlen)
    lines += _build_valid(pfx, td, cg, xlpe, xlen)
    lines += _build_faults(pfx, td, cg, xlpe, xlen)
    lines += _build_disabled(pfx, td, cg, xlpe, xlen)
    lines += _build_elp_clear(pfx, td, cg, xlpe, xlen)
    lines += _build_exc_priority(pfx, td, cg, xlpe, xlen)

    # M-MODE ONLY
    if mode == "mmode":
        lines += _build_trap_entry(pfx, td, cg, xlpe, xlen)
        lines += _build_trap_return(pfx, td, cg, xlpe, xlen)

    lines += teardown_vm()
    if xlpe.guard:
        lines.append(f"#endif // {xlpe.guard.split()[-1]}")
    return lines


# ═══════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════

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
    "emit_mode",
]
