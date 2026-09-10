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

# CSR Bit Positions (per Spec)
_MSECCFG_MLPE_BIT = 10  # mseccfg.MLPE
_MENVCFG_LPE_BIT = 2  # menvcfg.LPE
_SENVCFG_LPE_BIT = 2  # senvcfg.LPE
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
    # True when pelp_csr isn't accessible from the privilege level the test
    # code runs at (U-mode reading sstatus/mstatus), so _read_pelp must go
    # through the T-SBI CSR-access ecall instead of a direct csrr.
    pelp_needs_elevation: bool = False
    # True to have _read_pelp additionally force-clear live ELP after
    # reading pelp_csr (see _clear_pelp). xPELP is restored into live ELP
    # on xret, so a genuine software-check fault (missing/mismatched
    # landing pad) leaves ELP armed for whatever comes next -- the next
    # instruction (not itself a jump target) fails the same check and the
    # fault cascades forward one instruction at a time until the
    # trap-signature buffer overflows. Set for "smode" and "umode", where
    # this cascade was actually observed (ZicfilpS/ZicfilpUS).
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
            pelp_bit=_MSTATUS_MPELP_BIT,
            guard="#ifndef S_SUPPORTED",
            pelp_needs_elevation=True,  # mstatus/mstatush isn't readable from U-mode
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


# CSR addresses for the T-SBI CSR-access encodings below. mseccfg isn't
# here: it's M-mode's own CSR and test code never drops below M-mode in
# that config, so it's always accessed directly.
_CSR_ADDR = {
    "menvcfg": 0x30A,
    "senvcfg": 0x10A,
    "mstatus": 0x300,
    "mstatush": 0x310,
    "sstatus": 0x100,
}

# Fixed instruction fields for RVTEST_TSBI_CSR_ACCESS encodings (opcode=SYSTEM,
# funct3 for CSRRS/CSRRC, rs1=a1 (x11), rd=x0). OR with (csr_addr << 20) to
# get the full encoding. See RVTEST_TSBI_CSR_ACCESS's own doc comment in
# rvtest_trap_handler.h for the worked example this matches.
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
        # menvcfg/senvcfg are only writable from a strictly higher privilege
        # level. By the time this runs inside a probe, test code is already
        # executing at the (lower) privilege level that requested this LPE
        # setting, so a direct csrs/csrc here would itself be illegal. Route
        # through the M-mode trap handler's T-SBI CSR dispatch instead.
        msk = 1 << xlpe.bit
        op = _TSBI_CSRRS_X0_A1 if en else _TSBI_CSRRC_X0_A1
        encoding = (_CSR_ADDR[xlpe.csr] << 20) | op
        lines += [
            f"# {xlpe.csr}.{xlpe.name} = {int(en)} (via T-SBI CSR access)",
            f"LI(a1, {hex(msk)})",
            f"RVTEST_TSBI_CSR_ACCESS {hex(encoding)}, a1",
        ]
    if guard:
        lines.append(f"#endif // {guard.split()[-1]}")
    return lines


def _clear_pelp(xlpe: XLPEConfig) -> list[str]:
    """Force-clear live ELP. See clear_live_elp on XLPEConfig for why this
    is needed: without it, a genuine software-check fault leaves ELP armed
    (restored from xPELP on xret) for whatever instruction comes next,
    which isn't itself a jump target and so fails the same check, cascading
    forward until the trap-signature buffer overflows. No-op if
    clear_live_elp isn't set.

    Executes an LPL=0 landing pad directly in sequential flow (not as a
    jump target). Per spec LPL=0 always "matches", so this unconditionally
    clears live ELP -- and is a harmless AUIPC-shaped no-op if ELP was
    already 0. This needs no CSR access, so it works the same regardless of
    mode/xlen/privilege.
    """
    if not xlpe.clear_live_elp:
        return []
    return [
        "# execute a bypass (LPL=0) landing pad to force-clear live ELP",
        f".word {hex(_lpad_encoding(0))}",
    ]


def _read_pelp(xlpe: XLPEConfig, dst: int) -> list[str]:
    """Read xPELP bit into dst."""
    guard = xlpe.guard
    lines = []
    if guard:
        lines.append(guard)
    if xlpe.pelp_needs_elevation:
        # pelp_csr isn't accessible from the current (U-mode) privilege
        # level, so read it via the M-mode trap handler's T-SBI CSR
        # dispatch instead of a direct csrr, which would trap illegal
        # instruction. The macro's contract requires rd=a0.
        encoding = (_CSR_ADDR[xlpe.pelp_csr] << 20) | _TSBI_CSRRS_A0_X0
        lines += [
            f"# read {xlpe.pelp_csr} via T-SBI CSR access (not accessible at current privilege)",
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


def _trampoline_section(pfx: str, section: str = ".text.rvtest", self_heal_elp: bool = False) -> list[str]:
    """
    Emits LPAD targets with CORRECT encoding (rs1=x7).
    Labels:
      _tgt_lpad_zero          : Label=0,     LPL=0 (0x017)
      _tgt_lpad_zero_retra    : Same as _tgt_lpad_zero, but returns via ra
                                instead of x7 -- for callers that deliberately
                                set x7 to a controlled value (e.g. 0) to cover
                                x7_label, where the jump itself must not be
                                the rd=x7 form (that would overwrite it). `jr
                                ra` (rs1 in the link-register set, rd=x0) is
                                itself return-shaped, so it doesn't require a
                                landing pad at the caller's resume point --
                                unlike `jr a0`, which would.
      _tgt_lpad_match         : Label=PC+4,  LPL=1 (0x117) -- Match occurs naturally if JALR x7 falls through
      _tgt_lpad_mismatch      : Label=0x12345, LPL=1
      _tgt_lpad_zero_nonzero  : Label=0xABCDE, LPL=0 (For sc4 bin)
      _tgt_nonlpad            : NOP

    self_heal_elp: replace each target's second instruction (a plain nop)
    with a bypass (LPL=0) landing pad. A genuine mismatch/missing fault at
    the first word is unexpected to the shared framework trap handler, so
    it just records it and resumes at faulting-instruction-address +
    instruction-length -- landing right on this second instruction, still
    inside the trampoline, without ever running the trampoline's own `jr`
    below. If ELP is still armed at that point, this second instruction
    would *also* fault (it's not a jump target, so it isn't itself
    protected), and so on for every instruction after it, forever. An LPL=0
    landing pad there unconditionally clears ELP (LPL=0 always "matches")
    so the trampoline's own `jr` below runs safely either way; it's a
    harmless AUIPC-shaped no-op in the ordinary (already-passed) case,
    same as the nop it replaces. For _tgt_nonlpad specifically, the first
    instruction is the plain nop the "missing landing pad" testcase
    deliberately jumps to -- replacing that one would remove the fault
    being tested, so only the *second* nop there is replaced.
    """
    enc_zero = _lpad_encoding(0x00000)  # LPL=0
    enc_match = _lpad_encoding(0xABCDE)  # LPL=0xABCDE
    enc_mismatch = _lpad_encoding(0x12345)  # LPL=0x12345
    enc_zero_nz = _lpad_encoding(0xABCDE)  # LPL=0xABCDE (for sc4)
    heal = f"  .word {hex(enc_zero)}" if self_heal_elp else "  nop"

    return [
        "",
        "# ── Zicfilp LPAD Targets (rs1=x7 encoded) ─────────────────",
        # Bare .text is swept into .text.rvmodel by the linker script (the
        # framework's own reserved code region), which the trap handler's
        # EPC segment-recognition logic doesn't treat as valid test content
        # -- a fault landing there aborts instead of being recorded. Modes
        # whose landing-pad exception is actually reachable need
        # .text.rvtest so a real fault there gets recorded instead of
        # aborting; see each generator's own call site for why it picks
        # one or the other.
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
        # heal must be 4-byte aligned for the CPU to recognize it as a
        # landing pad at all (the preceding nop above is compressed, 2
        # bytes, so without this the healing word would land 2-byte-aligned
        # but not 4-byte-aligned and silently fail to clear ELP).
        ".p2align 2",
        heal,
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
    # Without .pushsection .data, these .p2align'd .zero blocks land in
    # whatever section is active at the call site (.text.rvtest), silently
    # overlapping/shifting the actual test code that follows.
    lines: list[str] = [".pushsection .data"]
    for i in range(LEVELS_BELOW_ROOT[mode]):
        lines += [".p2align 12", f"rvtest_slvl{i}_pg_tbl: .zero 4096"]
    lines.append(".popsection")
    return lines


# ═══════════════════════════════════════════════════════════════════════════
# XLEN / MODE HELPERS
# ═══════════════════════════════════════════════════════════════════════════


def both_xlens(build: Callable[[int], list[str]]) -> list[str]:
    """Emit build(64) and build(32) inside XLEN guards.

    Gated on SV39_SUPPORTED/SV32_SUPPORTED: only meaningful for callers whose
    build() actually cycles through paged satp modes (sv39/sv48/sv57). For a
    bare-only body, use both_xlens_bare instead -- gating bare content behind
    a translation-support define excludes it on any DUT that doesn't also
    happen to support paging (e.g. a true no-S config), even though the body
    itself never touches satp.
    """
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

    The framework's own boot-time identity map (rvtest_identity_map in
    rvtest_setup.h) only covers rvtest_data_begin and grants RWX with PTE_U
    clear (permission byte 0xCF) -- enough for S-mode, which is why paged
    ZicfilpS tests work without any of this. True U-mode execution additionally
    needs PTE_U on the page holding the code it's about to fetch from, or the
    very first instruction fetch after switching to U-mode page-faults; with
    LPE still enabled that fault recurses into a return path that never
    resolves it, silently burning the entire trap-signature budget instead of
    failing cleanly. Mirrors rvtest_identity_map's own register-based approach
    (T1-T4, same registers) rather than the VA-templated SUPERPAGE_PTE_SETUP_SV*
    macros, since those need a compile-time '.set' VA constant and this needs a
    true identity map off rvtest_code_begin's own runtime address. Assumes
    rvtest_code_begin and rvtest_data_begin share the same superpage-aligned
    region, same as the boot map already assumes for rvtest_data_begin.
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

    # NOTE: with mseccfg.MLPE=1 (M-mode), any dest other than lpad_zero risks
    # a real elp violation (lpad_match's target label is a fixed constant
    # that x7 essentially never holds, so it only avoids faulting for
    # rs1 in LINK_REGS, which is exempt as return-shaped; nonlpad/mismatch
    # always fault). Taking any trap while MLPE=1 recurses into the shared
    # M-mode dispatcher's own unprotected indirect jump (common_Mhandler's
    # `jr T5`), which has no landing pad and faults again, forever. So skip
    # dest/rs1 combinations that would actually fault for mmode.
    # menvcfg.LPE/senvcfg.LPE (S/U-mode) don't hit this: the M-mode
    # dispatcher only self-checks against mseccfg.MLPE. Fixing this for
    # real needs a change in the shared trap handler, out of scope here.
    #
    # Not every non-lpad_zero dest actually faults though: lpad_zero and
    # lpad_match (via the explicit-x7 special case below, or the LINK_REGS
    # exemption) never fault regardless of mode, and mismatch/nonlpad only
    # fault when rs1 isn't in LINK_REGS (LINK_REGS is exempt from the elp
    # check entirely, so those jumps never reach the label check at all).
    # Only skip the genuinely unsafe combination.
    is_mmode = xlpe.csr == "mseccfg"

    def _unsafe_for_mmode(lpe: int, dest: str, rs1_val: int) -> bool:
        return bool(lpe and is_mmode and dest in ("lpad_mismatch", "nonlpad") and rs1_val not in LINK_REGS)

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
                if _unsafe_for_mmode(lpe, dest, rs1_val):
                    continue
                tc = _tid(pfx, f"lpe{lpe}", "jalr", f"rs1_{rs1_val}", dest)
                if dest == "lpad_match" and rs1_val not in LINK_REGS:
                    # A plain `jalr x7` only "matches" by accident: rs1 in
                    # LINK_REGS exempts the jump from the elp check entirely
                    # (see _build_valid), so it never actually compares
                    # against the target's label. For every other rs1 this
                    # was a genuine mismatch -- a real trap on nearly every
                    # iteration of this loop, which is what blew out the
                    # trap-signature buffer. Set x7 to the target's actual
                    # label instead, with rd != x7, and return via ra.
                    ret_label = f"{tc}_ret"
                    out += [
                        "",
                        td.add_testcase(tc, CP_ELP_UPDATE, cg),
                        f"# LPE={lpe} JALR x7 rs1=x{rs1_val} -> {dest}",
                        *_li(7, 0xABCDE000),
                        *_la(1, ret_label),
                        *_la(rs1_val, f"{pfx}_tgt_lpad_match_retra"),
                        *_indirect_branch("jalr", rs1_val, rd_is_x7=False),
                        f"{ret_label}:",
                        *_read_pelp(xlpe, chk),
                        write_sigupd(chk, td),
                    ]
                    continue
                out += [
                    "",
                    td.add_testcase(tc, CP_ELP_UPDATE, cg),
                    f"# LPE={lpe} JALR x7 rs1=x{rs1_val} -> {dest}",
                    *_la(rs1_val, tgt_label),
                    *_indirect_branch("jalr", rs1_val, rd_is_x7=True),
                    *_read_pelp(xlpe, chk),
                    write_sigupd(chk, td),
                ]

    # 2. Compressed (ZCA) - Outside outer lpe loop to prevent duplication
    out.append("#ifdef ZCA_SUPPORTED")
    for lpe in [0, 1]:
        out.extend(_set_lpe(xlpe, tmp, bool(lpe)))
        for name in ("c.jr", "c.jalr"):
            for rs1_val in COMP_REGS:
                # rs1=x7 can't be tested here: c.jr/c.jalr don't write x7
                # themselves, so x7 has to hold the jump target for the
                # instruction to encode rs1=x7 at all. That leaves no way to
                # also preload x7 with a return address below, and the
                # trampoline's `jr x7` return would just jump back to itself.
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
                        # Same reasoning as the uncompressed loop above: only
                        # rs1 in LINK_REGS is exempt from the elp check, so
                        # everything else needs a genuine label match. x7 is
                        # already spoken for as the return-address preload
                        # below for the other dests, so here it holds the
                        # label instead and ra carries the return address.
                        out += [
                            "",
                            td.add_testcase(tc, CP_ELP_UPDATE, cg),
                            f"# LPE={lpe} {name} rs1=x{rs1_val} -> {dest}",
                            *_li(7, 0xABCDE000),
                            *_la(1, ret_label),
                            *_la(rs1_val, f"{pfx}_tgt_lpad_match_retra"),
                            *_indirect_branch(name, rs1_val, rd_is_x7=False),
                            f"{ret_label}:",
                            *_read_pelp(xlpe, chk),
                            write_sigupd(chk, td),
                        ]
                        continue
                    out += [
                        "",
                        td.add_testcase(tc, CP_ELP_UPDATE, cg),
                        f"# LPE={lpe} {name} rs1=x{rs1_val} -> {dest}",
                        # c.jr/c.jalr never write x7, but the shared trampoline
                        # always returns via `jr x7`. Load the true return
                        # address into x7 ourselves so it doesn't fall back to
                        # whatever a previous jalr left there.
                        *_la(7, ret_label),
                        *_la(rs1_val, tgt_label),
                        *_indirect_branch(name, rs1_val, rd_is_x7=False),
                        f"{ret_label}:",
                        *_read_pelp(xlpe, chk),
                        write_sigupd(chk, td),
                    ]
    out.append("#endif // ZCA_SUPPORTED")

    td.int_regs.return_registers([rs1, tmp, chk])
    return out


def _build_bypass(pfx: str, td: TestData, cg: str, xlpe: XLPEConfig, xlen: int) -> list[str]:
    """CP_LPAD_BYPASS: LPL=0, ELP=1. x7_label (zero/nonzero)."""
    # ra (x1) is reserved here as the return-address register for the
    # x7-zeroing cases below, so exclude it from general allocation.
    rs1, tmp, chk = td.int_regs.get_registers(3, exclude_regs=[1])
    out = [comment_banner(f"{pfx}: LPAD LPL=0 Bypass")]
    out.extend(_set_lpe(xlpe, tmp, True))

    # Case 1: x7_label.zero (ins.prev.x_wdata[7] == 0)
    # x7 is deliberately zeroed here to cover x7_label, so the jump can't use
    # rd=x7 (that would overwrite it before the lpad even checks it) -- use
    # the _retra target instead, and preload ra with the resume address
    # ourselves. `jr a0` would also avoid clobbering x7, but a0 isn't a link
    # register, so that jump would itself require a landing pad at the
    # resume point; ra is exempt as return-shaped.
    tc = _tid(pfx, "bypass", "x7_zero")
    ret_label = f"{tc}_ret"
    out += [
        "",
        td.add_testcase(tc, CP_LPAD_BYPASS, cg),
        *_li(7, 0),
        *_la(1, ret_label),
        *_la(rs1, f"{pfx}_tgt_lpad_zero_retra"),
        *_indirect_branch("jalr", rs1, rd_is_x7=False),
        f"{ret_label}:",
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

    # Case 3: sc4 bin (LPL!=0, x7=0). Whether the target's nonzero LPL still
    # requires an exact x7 match here (i.e. whether this genuinely faults) is
    # ambiguous from the coverpoint alone, and this code doesn't handle a
    # fault if one occurs. Skip under mmode: a real trap here would recurse
    # into the shared M-mode dispatcher's own unprotected indirect jump (see
    # the note in _build_elp_update). menvcfg.LPE/senvcfg.LPE (S/U-mode)
    # don't hit that.
    if xlpe.csr != "mseccfg":
        # Same reasoning as case 1: x7 is deliberately zeroed, so preload ra
        # and return via the _retra target.
        tc = _tid(pfx, "scenario", "sc4")
        ret_label = f"{tc}_ret"
        out += [
            "",
            td.add_testcase(tc, CP_LPAD_SCENARIO, cg),
            *_li(7, 0),
            *_la(1, ret_label),
            *_la(rs1, f"{pfx}_tgt_lpad_zero_nonzero_retra"),
            *_indirect_branch("jalr", rs1, rd_is_x7=False),
            f"{ret_label}:",
            *_read_pelp(xlpe, chk),
            write_sigupd(chk, td),
        ]

    td.int_regs.return_registers([rs1, tmp, chk])
    return out


def _build_valid(pfx: str, td: TestData, cg: str, xlpe: XLPEConfig, xlen: int) -> list[str]:
    """CP_LPAD_VALID: LPL!=0, Match."""
    # ra (x1) is reserved as the return-address register below.
    rs1, tmp, chk = td.int_regs.get_registers(3, exclude_regs=[1])
    out = [comment_banner(f"{pfx}: Valid LPAD Execution (Match)")]
    out.extend(_set_lpe(xlpe, tmp, True))

    # A genuine match needs x7[31:12] == the target's encoded label (0xABCDE
    # here) at the moment the lpad executes. rd=x7 (rd_is_x7=True) can't
    # produce that reliably: it overwrites x7 with its own return address,
    # which only happens to equal 0xABCDE if rs1 is a link register (exempt
    # from the elp check entirely) -- not an actual match. Set x7 explicitly
    # instead, with rd!=x7, and return via ra (link-register exempt) since
    # x7 no longer holds a usable address.
    tc = _tid(pfx, "valid", "match")
    ret_label = f"{tc}_ret"
    out += [
        "",
        td.add_testcase(tc, CP_LPAD_VALID, cg),
        *_li(7, 0xABCDE000),
        *_la(1, ret_label),
        *_la(rs1, f"{pfx}_tgt_lpad_match_retra"),
        *_indirect_branch("jalr", rs1, rd_is_x7=False),
        f"{ret_label}:",
        *_read_pelp(xlpe, chk),
        write_sigupd(chk, td),
    ]

    td.int_regs.return_registers([rs1, tmp, chk])
    return out


def _build_faults(pfx: str, td: TestData, cg: str, xlpe: XLPEConfig, xlen: int) -> list[str]:
    """CP_LPAD_MISSING, CP_LPAD_MISMATCH, CP_EXC_DELIVERY, CP_LPAD_SCENARIO."""
    if xlpe.csr == "mseccfg":
        # Every case here deliberately traps with LPE=1. In M-mode that
        # recurses into the shared trap dispatcher's own unguarded indirect
        # jump (see the note in _build_elp_update); skip until that's fixed.
        return []
    rs1, tmp, chk = td.int_regs.get_registers(3)
    out = [comment_banner(f"{pfx}: LPAD Faults & Scenarios")]
    out.extend(_set_lpe(xlpe, tmp, True))

    # 1. Missing Instruction -> sc3_not_lpad
    # mcause/mtval aren't recorded explicitly here: this function only ever
    # runs for smode/umode/umode_nos (mmode returns above), where they're
    # M-mode-only CSRs the test can't read directly. The framework's own
    # trap-signature area already records cause/tval for every unexpected
    # trap, so that's relied on instead; read_pelp below still gives each
    # testcase a real, legally-readable signature contribution.
    tc = _tid(pfx, "fault", "missing")
    out += [
        "",
        td.add_testcase(tc, CP_LPAD_MISSING, cg),
        td.add_testcase(tc, CP_LPAD_SCENARIO, cg),
        *_la(rs1, f"{pfx}_tgt_nonlpad"),
        *_indirect_branch("jalr", rs1, rd_is_x7=True),
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
        *_read_pelp(xlpe, chk),
        write_sigupd(chk, td),
    ]

    # 3. x7=0, LPL!=0: x7==0 bypasses the label check entirely (same as
    # LPL==0 does), so this never actually faults -- confirmed by trace,
    # despite the sc4 bin's own "mismatch" framing in the coverpoint. x7 is
    # deliberately zeroed to cover that, so (like _build_bypass's x7-zero
    # cases) the jump can't use rd=x7, and return must go via ra instead of
    # the now-zeroed x7.
    td.int_regs.return_registers([rs1, tmp, chk])
    rs1, tmp, chk, rd_tmp = td.int_regs.get_registers(4, exclude_regs=[1])
    tc = _tid(pfx, "fault", "x7_zero_mismatch")
    ret_label = f"{tc}_ret"
    out += [
        "",
        td.add_testcase(tc, CP_LPAD_MISMATCH, cg),
        *_li(7, 0),
        *_la(1, ret_label),
        *_la(rs1, f"{pfx}_tgt_lpad_match_retra"),
        *_indirect_branch("jalr", rs1, rd_is_x7=False),
        f"{ret_label}:",
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
        *_read_pelp(xlpe, chk),
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
    """CP_PELP_ENTRY, CP_PELP_GUARDED, CP_ELP_PRESERVE (M-mode only).

    Disabled: every case here takes an M-mode trap (ecall) with
    mseccfg.MLPE=1, which recurses into the shared trap dispatcher's own
    unguarded indirect jump (see the note in _build_elp_update). Skip until
    that's fixed.
    """
    return []


def _build_trap_return(pfx: str, td: TestData, cg: str, xlpe: XLPEConfig, xlen: int) -> list[str]:
    """CP_PELP_RET (M-mode only).

    Disabled: takes an M-mode trap (ecall) with mseccfg.MLPE=1; see
    _build_trap_entry.
    """
    return []


def _build_exc_priority(pfx: str, td: TestData, cg: str, xlpe: XLPEConfig, xlen: int) -> list[str]:
    """CP_EXC_PRIORITY: ELP=1, Jump to Fault Address.

    Disabled for now (all modes): the framework's own instruction-access-
    fault probe (generate_instr_access_fault_tests in ExceptionsCommon.py)
    jumps to RVMODEL_ACCESS_FAULT_ADDRESS as the last thing it emits and
    never expects to resume normally afterward. This probe runs mid-
    sequence, with a lot more test code that needs to keep running
    correctly after it -- and in practice the jump doesn't cleanly resume,
    it burns through the entire trap-signature budget instead and corrupts
    everything downstream. Needs a redesign (its own isolated chunk, or
    similar) before it's safe to re-enable.
    """
    return []


# ═══════════════════════════════════════════════════════════════════════════
# MAIN PER-MODE EMITTER
# ═══════════════════════════════════════════════════════════════════════════


def emit_mode(
    td: TestData,
    mode: str,
    cg: str,
    xlen: int,
    satp_mode: str = "bare",
    trampoline_section: str = ".text.rvtest",
    skip_trampoline_fallthrough: bool = False,
) -> list[str]:
    """
    Generates the complete test sequence for a specific mode/xlen/satp_mode.

    trampoline_section: which section the LPAD-target trampolines land in.
    Each generator picks this for itself -- see the call site in
    ZicfilpU.py/ZicfilpUS.py/ZicfilpS.py/ZicfilpSm.py for the reasoning
    specific to that mode.

    skip_trampoline_fallthrough: emit an unconditional jump around the
    trampoline block below so mode-entry code doesn't fall through into it.
    Without this, execution runs off the end of the mode-entry sequence
    straight into _tgt_lpad_zero's `c.jr x7` with x7 uncontrolled; see the
    call site in ZicfilpUS.py for why that's unsafe there.
    """
    xlpe = _get_xlpe_config(mode, xlen)
    pfx = f"{mode}_{satp_mode}_rv{xlen}"

    lines = []
    if xlpe.guard:
        lines.append(xlpe.guard)
    lines += [comment_banner(f"Zicfilp {mode.upper()} Mode {satp_mode.upper()} (RV{xlen})", cg)]

    # Data (trampolines are emitted further below, not here -- see the note
    # by that call for why order matters when they land in .text.rvtest)
    lines += _data_section()

    # Page Tables & SATP -- EXPLICIT GUARD
    is_translation_mode = satp_mode in ("sv39", "sv48", "sv57")
    if mode in ("smode", "umode", "umode_nos") and is_translation_mode:
        lines += _data_slvl_tables(satp_mode)
        lines += satp_setup(xlen, satp_mode, grant_umode_access=(mode == "umode"))
    else:
        lines += satp_setup(xlen, "bare")

    # M-mode Config
    lines += [GOTO_MMODE]
    lines += _set_lpe(xlpe, 10, True)
    if mode in ("smode", "umode", "umode_nos"):
        lines += ["csrw medeleg, x0", "csrw mideleg, x0"]
        lines += [GOTO_SMODE if mode == "smode" else GOTO_UMODE]
    # mode == "mmode": already in M-mode from the GOTO_MMODE above. A second
    # GOTO_MMODE here would ecall with mseccfg.MLPE now set, which traps into
    # the shared M-mode dispatcher's own unguarded indirect jump (see the
    # note in _build_elp_update).

    lines += _la(REP_NON_LINK, "zicfilp_scratch")

    # Trampolines: emitted here, not before the mode-entry sequence above.
    # A framework-wide boot routine (canary_check) fills every register with
    # a distinctive poison pattern and then jumps to the fixed address
    # 0x80000040 -- the well-known start of real test content in
    # .text.rvtest -- expecting genuine test code there. When
    # trampoline_section is .text.rvtest and these trampolines were the
    # first thing emitted, they physically landed at that exact address:
    # canary_check would jump straight into the middle of a trampoline's
    # `c.jr x7` with x7 still holding the poison pattern (never having gone
    # through a real `jalr x7, ...`), faulting on a fetch from garbage.
    # Emitting them after the mode-entry sequence keeps real code first.
    # That alone only stops canary_check's own jump into the trampolines --
    # it doesn't stop mode-entry code from falling through into them, which
    # hits _tgt_lpad_zero's `c.jr x7` with x7 uncontrolled. Callers that hit
    # that (see skip_trampoline_fallthrough) need an explicit jump around it.
    trampoline_end = f"{pfx}_trampolines_end"
    if skip_trampoline_fallthrough:
        lines += [f"j {trampoline_end}"]
    lines += _trampoline_section(pfx, section=trampoline_section, self_heal_elp=xlpe.clear_live_elp)
    if skip_trampoline_fallthrough:
        lines += [f"{trampoline_end}:"]

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

    # teardown_vm() ecalls RVTEST_GOTO_MMODE to get back to M-mode for the
    # satp cleanup. For mode=="mmode" we're already there, so that ecall is
    # redundant -- but with mseccfg.MLPE still set from the last probe, it
    # would still trap, recursing into the shared M-mode dispatcher's own
    # unprotected indirect jump (see the note in _build_elp_update). Clear
    # LPE first so teardown is safe regardless of mode.
    lines += _set_lpe(xlpe, 10, False)
    # _set_lpe only disables *future* landing-pad checks; it doesn't clear
    # an already-armed ELP. Every testcase above clears it via _read_pelp
    # (see clear_live_elp), but nothing runs _read_pelp after this point,
    # so a fault from the very last testcase would otherwise leave ELP
    # armed straight into the framework's own teardown/cleanup code.
    lines += _clear_pelp(xlpe)
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
    "both_xlens_bare",
    "emit_mode",
]
