##################################
# priv/extensions/ZpmCommon.py
#
# Pointer masking (Ssnpm/Smmpm/Smnpm) shared test generators.
# Author :  Umer Shahid & Ammarah Wakeel  email:ammarahwakeel9@gmail.com (UET, JULY 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared pointer-masking extension test infrastructure.
Common code for Ssnpm (S->U), Smmpm (M-mode), SmnpmS (M->S), SmnpmU (M->U)
test generators.
"""

from __future__ import annotations

from dataclasses import dataclass

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData

# ── Constants ──────────────────────────────────────────────────────────────

UPPER_PATTERNS: list[int] = [
    0x0000,  # no tag: masking is a no-op, the control case
    0x0001,  # bit 48   -- stripped by PMLEN=16 only
    0x0100,  # bit 56   -- stripped by PMLEN=16 only
    0x0200,  # bit 57   -- stripped by PMLEN=16 and PMLEN=7
    0x8000,  # bit 63   -- stripped by PMLEN=16 and PMLEN=7
    0xFFFF,  # bits 63:48 -- fully stripped by PMLEN=16, partially by PMLEN=7
    0xFE00,  # bits 63:57 -- exactly the PMLEN=7 window
    0xFF00,  # bits 63:56 -- fully stripped by PMLEN=16, partially by PMLEN=7
]

PMM_CONFIGS: list[tuple[int, int, str]] = [
    (0b00, 0, "pmm00"),
    (0b10, 7, "pmm10"),
    (0b11, 16, "pmm11"),
]

VALUE_OLD: int = 0xABCD_1234_ABCD_1234
VALUE_NEW: int = 0xA5A5_A5A5_A5A5_A5A5
SENTINEL: int = 0x1BAD_0BAD_1BAD_0BAD

_MSTATUS_MXR = 1 << 19

CP_MASKING = "cp_pmlen_masking"
CP_MISALIGN = "cp_pmlen_misaligned_word"
CP_MXR = "cp_pmm_mxr"
CP_JALR = "cp_pmm_jalr"
CP_FAULT = "cp_hardware_csr_writes_fault"
CP_CSR = "cp_pm_csr_software_access"
CP_UXL_CLEAR = "cp_pmm_uxl_clear"
CP_SXL_CLEAR = "cp_pmm_sxl_clear"
CP_MPRV = "cp_pm_mprv"

# envcfg (menvcfg/senvcfg) field positions shared by every mode-entry prelude
# that needs to grant cbo.*/prefetch.*/Zicfiss permission to the next lower
# privilege level. Same bit positions regardless of which *envcfg CSR is used.
_ENVCFG_CBIE_SHIFT = 4
_ENVCFG_CBCFE_SHIFT = 6
_ENVCFG_CBZE_SHIFT = 7
_ENVCFG_SSE_BIT = 1 << 3

READS: list[str] = ["lb", "lbu", "lh", "lhu", "lw", "lwu", "ld"]
WRITES: list[tuple[str, str]] = [("sb", "lbu"), ("sh", "lhu"), ("sw", "lw"), ("sd", "ld")]
AMO_OPS = ["swap", "add", "xor", "and", "or", "min", "max", "minu", "maxu"]
RV64A_AMOS: list[tuple[str, str]] = [(f"amo{op}.{w}", "lw" if w == "w" else "ld") for op in AMO_OPS for w in ("w", "d")]
ZABHA_AMOS: list[tuple[str, str]] = [
    (f"amo{op}.{w}", "lbu" if w == "b" else "lhu") for op in AMO_OPS for w in ("b", "h")
]
ZACAS_AMOS: list[str] = ["amocas.w", "amocas.d"]
FP_READS: list[tuple[str, str, str]] = [("flw", "F_SUPPORTED", "fmv.w.x"), ("fld", "D_SUPPORTED", "fmv.d.x")]
FP_WRITES: list[tuple[str, str, str, str]] = [
    ("fsw", "lw", "F_SUPPORTED", "fmv.w.x"),
    ("fsd", "ld", "D_SUPPORTED", "fmv.d.x"),
]
ZCA_READS_CL: list[str] = ["c.lw", "c.ld"]
ZCA_WRITES_CS: list[tuple[str, str]] = [("c.sw", "lw"), ("c.sd", "ld")]
ZCA_READS_SP: list[str] = ["c.lwsp", "c.ldsp"]
ZCA_WRITES_SP: list[tuple[str, str]] = [("c.swsp", "lw"), ("c.sdsp", "ld")]

ZICBOM_OPS: list[str] = ["cbo.clean", "cbo.flush", "cbo.inval"]
ZICBOP_OPS: list[str] = ["prefetch.r", "prefetch.w", "prefetch.i"]
ZICFISS_AMOS: list[tuple[str, str, int]] = []

VEC_READS: list[tuple[str, int, str]] = [
    ("vle8.v", 8, "vle8.v v2, (x{a})"),
    ("vle16.v", 16, "vle16.v v2, (x{a})"),
    ("vle32.v", 32, "vle32.v v2, (x{a})"),
    ("vle64.v", 64, "vle64.v v2, (x{a})"),
    ("vle8ff.v", 8, "vle8ff.v v2, (x{a})"),
    ("vle16ff.v", 16, "vle16ff.v v2, (x{a})"),
    ("vle32ff.v", 32, "vle32ff.v v2, (x{a})"),
    ("vle64ff.v", 64, "vle64ff.v v2, (x{a})"),
    ("vlse32.v", 32, "vlse32.v v2, (x{a}), x0"),
    ("vlse64.v", 64, "vlse64.v v2, (x{a}), x0"),
    ("vluxei32.v", 32, "vluxei32.v v2, (x{a}), v4"),
    ("vluxei64.v", 64, "vluxei64.v v2, (x{a}), v4"),
    ("vloxei32.v", 32, "vloxei32.v v2, (x{a}), v4"),
    ("vloxei64.v", 64, "vloxei64.v v2, (x{a}), v4"),
    ("vl1r.v", 64, "vl1r.v v2, (x{a})"),
    ("vlseg2e32.v", 32, "vlseg2e32.v v2, (x{a})"),
]
VEC_WRITES: list[tuple[str, int, str, str]] = [
    ("vse8.v", 8, "vse8.v v2, (x{a})", "lbu"),
    ("vse16.v", 16, "vse16.v v2, (x{a})", "lhu"),
    ("vse32.v", 32, "vse32.v v2, (x{a})", "lw"),
    ("vse64.v", 64, "vse64.v v2, (x{a})", "ld"),
    ("vsse32.v", 32, "vsse32.v v2, (x{a}), x0", "lw"),
    ("vsse64.v", 64, "vsse64.v v2, (x{a}), x0", "ld"),
    ("vsuxei32.v", 32, "vsuxei32.v v2, (x{a}), v4", "lw"),
    ("vsuxei64.v", 64, "vsuxei64.v v2, (x{a}), v4", "ld"),
    ("vsoxei32.v", 32, "vsoxei32.v v2, (x{a}), v4", "lw"),
    ("vsoxei64.v", 64, "vsoxei64.v v2, (x{a}), v4", "ld"),
    ("vs1r.v", 64, "vs1r.v v2, (x{a})", "ld"),
    ("vsseg2e32.v", 32, "vsseg2e32.v v2, (x{a})", "lw"),
]

# ── Page-table constants (Sv39/Sv48/Sv57) ─────────────────────────────────

_NONLEAF_PERMS = "PTE_V"  # non-leaf PTEs must have ONLY V set
_LEAF_PERMS_U = "PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V"  # U-accessible data page
_LEAF_PERMS_S = "PTE_D | PTE_A | PTE_W | PTE_R | PTE_V"  # S-accessible only (no U)

LEVELS_BELOW_ROOT: dict[str, int] = {"sv39": 2, "sv48": 3, "sv57": 4}

IDENTITY_VPN_SHIFT: dict[str, int] = {"sv39": 30, "sv48": 39, "sv57": 48}

HIGH_VA: dict[str, int] = {
    "sv39": 0xFFFF_FFC0_0000_0000,
    "sv48": 0xFFFF_8000_0000_0000,
    "sv57": 0xFFFF_8000_0000_0000,
}

# ── Config / Regs ──────────────────────────────────────────────────────────


@dataclass
class Regs:
    base: int
    a: int
    data: int
    chk: int
    tmp: int
    tmp2: int
    fp: int
    fp_c: int


# ── Assembly Helpers ───────────────────────────────────────────────────────


def _li(reg: int, val: int) -> str:
    return f"LI(x{reg}, {hex(val)})"


def _fixed(instr: str) -> list[str]:
    return [".option push", ".option norvc", instr, ".option pop"]


def _compressed(instr: str) -> list[str]:
    return [".option push", ".option rvc", instr, ".option pop"]


def _fixed_block(body: list[str]) -> list[str]:
    return [".option push", ".option norvc", *body, ".option pop"]


def _guard_open(macro: str | None) -> list[str]:
    return [f"#ifdef {macro}"] if macro else []


def _guard_close(macro: str | None) -> list[str]:
    return [f"#endif // {macro}"] if macro else []


def _tid(prefix: str, upper: int, mnemonic: str) -> str:
    return f"{prefix}_up{upper:04X}_{mnemonic.replace('.', '_')}"


# ── envcfg (menvcfg/senvcfg) setup helper ──────────────────────────────────


def enable_envcfg_cbo_sse(regs: Regs, csr: str = "menvcfg") -> list[str]:
    """Grant the next-lower privilege level permission to run cbo.*/
    prefetch.* and the Zicfiss shadow-stack atomics.

    Pass the *envcfg CSR that actually gates the mode the probes run in:
    - "menvcfg" when the probes run in S-mode with no lower level to cascade
      through (SmnpmS, and M-mode-only Smmpm doesn't need this at all).
    - "senvcfg" when the probes run in U-mode; the caller is responsible for
      first cascading the same fields through menvcfg down to senvcfg
      (Ssnpm, SmnpmU).
    """
    cbo_fields = (0b11 << _ENVCFG_CBIE_SHIFT) | (1 << _ENVCFG_CBCFE_SHIFT) | (1 << _ENVCFG_CBZE_SHIFT) | _ENVCFG_SSE_BIT
    return [
        f"# {csr}: let the probes run cbo.*/prefetch.* (CBIE=11, CBCFE=1, CBZE=1)",
        "# and the Zicfiss shadow-stack atomics (SSE=1)",
        _li(regs.tmp, _ENVCFG_SSE_BIT),
        f"csrs {csr}, x{regs.tmp}",
        _li(regs.tmp, cbo_fields),
        f"csrc {csr}, x{regs.tmp}",
        _li(regs.tmp, cbo_fields),
        f"csrs {csr}, x{regs.tmp}",
    ]


def enable_cascaded_envcfg_cbo_sse(regs: Regs) -> list[str]:
    """Grant U-mode permission to run cbo.*/prefetch.* and the Zicfiss
    shadow-stack atomics, cascading the grant through menvcfg down to senvcfg.

    Used when the probes run in U-mode under an M-mode-configured PMM
    ( SmnpmU) -- menvcfg gates whether S-mode's own senvcfg settings
    take effect at all, so menvcfg.SSE must be set.
    """
    cbo_fields = (0b11 << _ENVCFG_CBIE_SHIFT) | (1 << _ENVCFG_CBCFE_SHIFT) | (1 << _ENVCFG_CBZE_SHIFT) | _ENVCFG_SSE_BIT
    return [
        "# Let U-mode run cbo.*/prefetch.* (CBIE=11, CBCFE=1, CBZE=1) and the Zicfiss",
        "# shadow-stack atomics (SSE=1). menvcfg gates senvcfg, so both are written.",
        _li(regs.tmp, _ENVCFG_SSE_BIT),
        f"csrs menvcfg, x{regs.tmp}",
        _li(regs.tmp, cbo_fields),
        f"csrc senvcfg, x{regs.tmp}",
        _li(regs.tmp, cbo_fields),
        f"csrs senvcfg, x{regs.tmp}",
    ]


# ── Page-table helpers (ported verbatim, previously missing from ZpmCommon) ─


def _pte_chain_asm(mode: str, va: int, leaf_label: str, leaf_perms: str = _LEAF_PERMS_U) -> list[str]:
    """Walk a fresh chain from the root down to a 4 KiB leaf mapping ``va``.
    This walks root -> slvl(top-1) -> ... -> slvl0 -> leaf across multiple PTE_SETUP calls
    """
    top = LEVELS_BELOW_ROOT[mode]
    macro = f"PTE_SETUP_{mode.upper()}"
    lines = [f"# {mode.upper()}: map {hex(va)} -> {leaf_label}"]
    for level in range(top, 0, -1):
        lines.append(f"{macro}(rvtest_slvl{level - 1}_pg_tbl, ({_NONLEAF_PERMS}), {hex(va)}, LEVEL{level})")
    lines.append(f"{macro}({leaf_label}, ({leaf_perms}), {hex(va)}, LEVEL0)")
    return lines


def _grant_umode_access_to_identity_map_asm(mode: str, regs: Regs | None = None) -> list[str]:
    """OR PTE_U into the boot-time identity leaf so U-mode can run from it."""
    shift = IDENTITY_VPN_SHIFT[mode]
    return [
        f"# {mode.upper()}: make the boot identity superpage U-accessible (leaf stays a leaf)",
        "LA(a1, rvtest_data_begin)",
        f"srli a1, a1, {shift}",
        "andi a1, a1, 0x1FF",
        "slli a1, a1, 3",
        "LA(a0, rvtest_Sroot_pg_tbl)",
        "add  a0, a0, a1",
        "ld   t0, 0(a0)",
        "li   t1, PTE_U",
        "or   t0, t0, t1",
        "sd   t0, 0(a0)",
    ]


# ── Probe Primitives ───────────────────────────────────────────────────────
# Every probe below takes an explicit `cg` (covergroup) argument. Callers
# must pass their own extension's covergroup name.


def _seed(regs: Regs) -> list[str]:
    return [_li(regs.data, VALUE_OLD), f"sd x{regs.data}, 0(x{regs.base})"]


def _sentinel(regs: Regs) -> list[str]:
    return [_li(regs.chk, SENTINEL)]


def _probe_load(mn: str, tid: str, td: TestData, regs: Regs, cp: str, cg: str) -> list[str]:
    return [
        *_seed(regs),
        *_sentinel(regs),
        td.add_testcase(tid, cp, cg),
        *_fixed(f"{mn} x{regs.chk}, 0(x{regs.a})"),
        write_sigupd(regs.chk, td),
    ]


def _probe_store(mn: str, readback: str, tid: str, td: TestData, regs: Regs, cp: str, cg: str) -> list[str]:
    return [
        *_seed(regs),
        _li(regs.data, VALUE_NEW),
        td.add_testcase(tid, cp, cg),
        *_fixed(f"{mn} x{regs.data}, 0(x{regs.a})"),
        *_fixed(f"{readback} x{regs.chk}, 0(x{regs.base})"),
        write_sigupd(regs.chk, td),
    ]


def _probe_amo(mn: str, readback: str, tid: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    return [
        *_seed(regs),
        _li(regs.data, VALUE_NEW),
        td.add_testcase(tid, CP_MASKING, cg),
        *_fixed(f"{mn} x0, x{regs.data}, (x{regs.a})"),
        *_fixed(f"{readback} x{regs.chk}, 0(x{regs.base})"),
        write_sigupd(regs.chk, td),
    ]


def _probe_zacas(mn: str, tid: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    return [
        *_seed(regs),
        f"{_li(regs.chk, VALUE_OLD)}   # comparand matches the seeded value",
        _li(regs.data, VALUE_NEW),
        td.add_testcase(tid, CP_MASKING, cg),
        *_fixed(f"{mn} x{regs.chk}, x{regs.data}, (x{regs.a})"),
        *_fixed(f"ld x{regs.chk}, 0(x{regs.base})"),
        write_sigupd(regs.chk, td),
    ]


def _probe_fp_load(mn: str, mv: str, tid: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    return [
        *_seed(regs),
        *_sentinel(regs),
        f"{mv} f{regs.fp}, x{regs.chk}   # poison the FP destination",
        td.add_testcase(tid, CP_MASKING, cg),
        *_fixed(f"{mn} f{regs.fp}, 0(x{regs.a})"),
        write_sigupd(regs.fp, td, "float"),
    ]


def _probe_fp_store(mn: str, readback: str, mv: str, tid: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    return [
        *_seed(regs),
        _li(regs.data, VALUE_NEW),
        f"{mv} f{regs.fp}, x{regs.data}",
        td.add_testcase(tid, CP_MASKING, cg),
        *_fixed(f"{mn} f{regs.fp}, 0(x{regs.a})"),
        *_fixed(f"{readback} x{regs.chk}, 0(x{regs.base})"),
        write_sigupd(regs.chk, td),
    ]


def _probe_c_load_cl(mn: str, tid: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    return [
        *_seed(regs),
        *_sentinel(regs),
        td.add_testcase(tid, CP_MASKING, cg),
        *_compressed(f"{mn} x{regs.chk}, 0(x{regs.a})"),
        write_sigupd(regs.chk, td),
    ]


def _probe_c_store_cs(mn: str, readback: str, tid: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    return [
        *_seed(regs),
        _li(regs.data, VALUE_NEW),
        td.add_testcase(tid, CP_MASKING, cg),
        *_compressed(f"{mn} x{regs.data}, 0(x{regs.a})"),
        *_fixed(f"{readback} x{regs.chk}, 0(x{regs.base})"),
        write_sigupd(regs.chk, td),
    ]


def _probe_c_load_sp(mn: str, tid: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    return [
        *_seed(regs),
        *_sentinel(regs),
        f"mv x{regs.tmp}, sp",
        f"mv sp, x{regs.a}",
        td.add_testcase(tid, CP_MASKING, cg),
        *_compressed(f"{mn} x{regs.chk}, 0(sp)"),
        f"mv sp, x{regs.tmp}",
        write_sigupd(regs.chk, td),
    ]


def _probe_c_store_sp(mn: str, readback: str, tid: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    return [
        *_seed(regs),
        _li(regs.data, VALUE_NEW),
        f"mv x{regs.tmp}, sp",
        f"mv sp, x{regs.a}",
        td.add_testcase(tid, CP_MASKING, cg),
        *_compressed(f"{mn} x{regs.data}, 0(sp)"),
        f"mv sp, x{regs.tmp}",
        *_fixed(f"{readback} x{regs.chk}, 0(x{regs.base})"),
        write_sigupd(regs.chk, td),
    ]


def _probe_cd_load_sp(tid: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    return [
        *_seed(regs),
        *_sentinel(regs),
        f"fmv.d.x f{regs.fp_c}, x{regs.chk}",
        f"mv x{regs.tmp}, sp",
        f"mv sp, x{regs.a}",
        td.add_testcase(tid, CP_MASKING, cg),
        *_compressed(f"c.fldsp f{regs.fp_c}, 0(sp)"),
        f"mv sp, x{regs.tmp}",
        write_sigupd(regs.fp_c, td, "float"),
    ]


def _probe_cd_store_sp(tid: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    return [
        *_seed(regs),
        _li(regs.data, VALUE_NEW),
        f"fmv.d.x f{regs.fp_c}, x{regs.data}",
        f"mv x{regs.tmp}, sp",
        f"mv sp, x{regs.a}",
        td.add_testcase(tid, CP_MASKING, cg),
        *_compressed(f"c.fsdsp f{regs.fp_c}, 0(sp)"),
        f"mv sp, x{regs.tmp}",
        *_fixed(f"ld x{regs.chk}, 0(x{regs.base})"),
        write_sigupd(regs.chk, td),
    ]


def _probe_cbo(mn: str, tid: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    return [
        *_seed(regs),
        td.add_testcase(tid, CP_MASKING, cg),
        *_fixed(f"{mn} 0(x{regs.a})"),
        *_fixed(f"ld x{regs.chk}, 0(x{regs.base})"),
        write_sigupd(regs.chk, td),
    ]


def _vset(sew: int, regs: Regs) -> list[str]:
    return [
        "csrw vstart, x0",
        f"vsetivli x{regs.tmp}, 2, e{sew}, m1, ta, ma",
        "vmv.v.i v4, 0   # zero index vector: indexed probes address the base itself",
    ]


def _probe_vec_load(mn: str, sew: int, template: str, tid: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    return [
        *_seed(regs),
        *_sentinel(regs),
        *_fixed_block(
            [
                *_vset(sew, regs),
                f"vmv.v.x v2, x{regs.chk}   # poison the destination vector",
                td.add_testcase(tid, CP_MASKING, cg),
                template.format(a=regs.a),
                f"vmv.x.s x{regs.chk}, v2",
                "csrw vstart, x0",
            ]
        ),
        write_sigupd(regs.chk, td),
    ]


def _probe_vec_store(
    mn: str, sew: int, template: str, readback: str, tid: str, td: TestData, regs: Regs, cg: str
) -> list[str]:
    return [
        *_seed(regs),
        _li(regs.data, VALUE_NEW),
        *_fixed_block(
            [
                *_vset(sew, regs),
                f"vmv.v.x v2, x{regs.data}",
                td.add_testcase(tid, CP_MASKING, cg),
                template.format(a=regs.a),
                "csrw vstart, x0",
            ]
        ),
        *_fixed(f"{readback} x{regs.chk}, 0(x{regs.base})"),
        write_sigupd(regs.chk, td),
    ]


def _probe_zicfiss(mn: str, readback: str, funct3: int, tid: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    """Zicfiss shadow-stack AMO through a tagged pointer (kept for parity;
    ZICFISS_AMOS is currently empty across all four extensions -- see their
    module docstrings for why)."""
    return [
        *_seed(regs),
        _li(regs.data, VALUE_NEW),
        *_sentinel(regs),
        td.add_testcase(tid, CP_MASKING, cg),
        *_fixed(
            f".insn r 0x2f, {funct3:#x}, 0x24, x{regs.chk}, x{regs.a}, x{regs.data}"
            f"   # {mn} x{regs.chk}, x{regs.data}, (x{regs.a})"
        ),
        *_fixed(f"{readback} x{regs.chk}, 0(x{regs.base})"),
        write_sigupd(regs.chk, td),
    ]


# ── Mode-specific address loading helpers ──────────────────────────────────


def _load_base(mode: str, region: str, regs: Regs) -> list[str]:
    if region == "hi":
        return [
            f"# upper-half VA base: masking must sign extend to reproduce {hex(HIGH_VA[mode])}",
            _li(regs.base, HIGH_VA[mode]),
        ]
    return [f"LA(x{regs.base}, pm_lo_page)"]


def _tag_address(upper: int, regs: Regs, byte_offset: int = 0) -> list[str]:
    lines = [
        f"# tagged pointer: bits 63:48 = 0x{upper:04X}",
        _li(regs.tmp, upper << 48),
        f"or x{regs.a}, x{regs.base}, x{regs.tmp}",
    ]
    if byte_offset:
        lines.append(f"addi x{regs.a}, x{regs.a}, {byte_offset}   # force a misaligned effective address")
    return lines


# ── Common Pass Implementations ────────────────────────────────────────────


def pass_a_all_instructions(cfg: object | None, prefix: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    lines = []
    for upper in UPPER_PATTERNS:
        lines.append(comment_banner(f"{prefix}: tag 0x{upper:04X} -- full instruction sweep"))
        lines += [_li(regs.tmp, upper << 48), f"or x{regs.a}, x{regs.base}, x{regs.tmp}"]

        for mn in READS:
            lines += _probe_load(mn, _tid(prefix, upper, mn), td, regs, CP_MASKING, cg)
        for mn, rb in WRITES:
            lines += _probe_store(mn, rb, _tid(prefix, upper, mn), td, regs, CP_MASKING, cg)

        lines += _guard_open("ZAAMO_SUPPORTED")
        for mn, rb in RV64A_AMOS:
            lines += _probe_amo(mn, rb, _tid(prefix, upper, mn), td, regs, cg)
        lines += _guard_open("ZABHA_SUPPORTED")
        for mn, rb in ZABHA_AMOS:
            lines += _probe_amo(mn, rb, _tid(prefix, upper, mn), td, regs, cg)
        lines += _guard_close("ZABHA_SUPPORTED")
        lines += _guard_open("ZACAS_SUPPORTED")
        for mn in ZACAS_AMOS:
            lines += _probe_zacas(mn, _tid(prefix, upper, mn), td, regs, cg)
        lines += _guard_close("ZACAS_SUPPORTED")
        lines += _guard_close("ZAAMO_SUPPORTED")

        for mn, guard, mv in FP_READS:
            lines += _guard_open(guard)
            lines += _probe_fp_load(mn, mv, _tid(prefix, upper, mn), td, regs, cg)
            lines += _guard_close(guard)
        for mn, rb, guard, mv in FP_WRITES:
            lines += _guard_open(guard)
            lines += _probe_fp_store(mn, rb, mv, _tid(prefix, upper, mn), td, regs, cg)
            lines += _guard_close(guard)

        lines += _guard_open("ZCA_SUPPORTED")
        for mn in ZCA_READS_CL:
            lines += _probe_c_load_cl(mn, _tid(prefix, upper, mn), td, regs, cg)
        for mn, rb in ZCA_WRITES_CS:
            lines += _probe_c_store_cs(mn, rb, _tid(prefix, upper, mn), td, regs, cg)
        for mn in ZCA_READS_SP:
            lines += _probe_c_load_sp(mn, _tid(prefix, upper, mn), td, regs, cg)
        for mn, rb in ZCA_WRITES_SP:
            lines += _probe_c_store_sp(mn, rb, _tid(prefix, upper, mn), td, regs, cg)
        lines += _guard_open("ZCD_SUPPORTED")
        lines += _probe_cd_load_sp(_tid(prefix, upper, "c.fldsp"), td, regs, cg)
        lines += _probe_cd_store_sp(_tid(prefix, upper, "c.fsdsp"), td, regs, cg)
        lines += _guard_close("ZCD_SUPPORTED")
        lines += _guard_close("ZCA_SUPPORTED")

        lines += _guard_open("ZICFISS_SUPPORTED")
        for mn, rb, f3 in ZICFISS_AMOS:
            lines += _probe_zicfiss(mn, rb, f3, _tid(prefix, upper, mn), td, regs, cg)
        lines += _guard_close("ZICFISS_SUPPORTED")

        lines += _guard_open("ZICBOZ_SUPPORTED")
        lines += _probe_cbo("cbo.zero", _tid(prefix, upper, "cbo.zero"), td, regs, cg)
        lines += _guard_close("ZICBOZ_SUPPORTED")

        lines += _guard_open("ZICBOM_SUPPORTED")
        for mn in ZICBOM_OPS:
            lines += _probe_cbo(mn, _tid(prefix, upper, mn), td, regs, cg)
        lines += _guard_close("ZICBOM_SUPPORTED")

        lines += _guard_open("ZICBOP_SUPPORTED")
        for mn in ZICBOP_OPS:
            lines += _probe_cbo(mn, _tid(prefix, upper, mn), td, regs, cg)
        lines += _guard_close("ZICBOP_SUPPORTED")

        lines += _guard_open("ZVL32B_SUPPORTED")
        for mn, sew, template in VEC_READS:
            lines += _probe_vec_load(mn, sew, template, _tid(prefix, upper, mn), td, regs, cg)
        for mn, sew, template, rb in VEC_WRITES:
            lines += _probe_vec_store(mn, sew, template, rb, _tid(prefix, upper, mn), td, regs, cg)
        lines += _guard_close("ZVL32B_SUPPORTED")
    return lines


def pass_c_misaligned(cfg: object | None, prefix: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    lines = [comment_banner(f"{prefix}: misaligned word accesses through a tagged pointer")]
    for upper in UPPER_PATTERNS:
        lines += [
            _li(regs.tmp, upper << 48),
            f"or x{regs.a}, x{regs.base}, x{regs.tmp}",
            f"addi x{regs.a}, x{regs.a}, 1   # force a misaligned effective address",
        ]
        lines += _probe_load("lw", _tid(f"{prefix}_mis", upper, "lw"), td, regs, CP_MISALIGN, cg)
        lines += _probe_store("sw", "lw", _tid(f"{prefix}_mis", upper, "sw"), td, regs, CP_MISALIGN, cg)
    return lines


def set_mxr(enable: bool, tmp: int, status_csr: str = "sstatus") -> list[str]:
    """MXR gates pointer masking off entirely when set.

    `status_csr` must match whatever CSR the caller's _cg mxr_bit coverpoint
    actually samples:
    - Ssnpm samples the sstatus shadow (probes run in U-mode under an
      S-mode-configured PMM) -> status_csr="sstatus" (the default).
    - Smmpm and SmnpmS sample mstatus directly (no shadow-register concern)
      -> status_csr="mstatus".
    """
    op = "csrs" if enable else "csrc"
    return [f"# {status_csr}.MXR = {int(enable)}", _li(tmp, _MSTATUS_MXR), f"{op} {status_csr}, x{tmp}"]


def pass_d_mxr(
    cfg: object | None,
    prefix: str,
    td: TestData,
    regs: Regs,
    cg: str,
    goto_target_mode: str = "RVTEST_TSBI_GOTO_UMODE",
    status_csr: str = "sstatus",
) -> list[str]:
    """sw/lw with MXR set. MXR suppresses masking, so tagged pointers must fault.

    `goto_target_mode` is whatever privilege-transition macro puts the hart
    where the probes should run (U-mode for Ssnpm, S-mode for SmnpmS, or
    omitted/no-op for Smmpm which never leaves M-mode -- pass "" in that case).
    `status_csr` is forwarded to set_mxr; see its docstring.
    """
    lines = [comment_banner(f"{prefix}: {status_csr}.MXR=1 suppresses pointer masking")]
    lines += ["RVTEST_GOTO_MMODE", *set_mxr(True, regs.tmp, status_csr)]
    if goto_target_mode:
        lines.append(goto_target_mode)
    lines += [f"LA(x{regs.base}, pm_lo_page)"]
    for upper in UPPER_PATTERNS:
        lines += [_li(regs.tmp, upper << 48), f"or x{regs.a}, x{regs.base}, x{regs.tmp}"]
        lines += _probe_load("lw", _tid(f"{prefix}_mxr", upper, "lw"), td, regs, CP_MXR, cg)
        lines += _probe_store("sw", "lw", _tid(f"{prefix}_mxr", upper, "sw"), td, regs, CP_MXR, cg)
    return lines


def pass_e_jalr(cfg: object | None, prefix: str, td: TestData, regs: Regs, cg: str, mxr: int = 0) -> list[str]:
    lines = [comment_banner(f"{prefix}: JALR through a tagged pointer, MXR={mxr} (fetch is never masked)")]
    lines.append(f"LA(x{regs.base}, pm_jalr_pad)")
    for upper in UPPER_PATTERNS:
        lines += [_li(regs.tmp, upper << 48), f"or x{regs.a}, x{regs.base}, x{regs.tmp}"]
        lines += [
            f"li x{regs.chk}, 0   # the pad sets this to 1 if the fetch succeeded",
            td.add_testcase(_tid(f"{prefix}_mxr{mxr}", upper, "jalr"), CP_JALR, cg),
            *_fixed(f"jalr ra, 0(x{regs.a})"),
            write_sigupd(regs.chk, td),
        ]
    lines += [f"LA(x{regs.base}, pm_lo_page)"]
    return lines


def pass_f_fault_address(cfg: object | None, prefix: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    lines = [
        comment_banner(f"{prefix}: masked address resolves to the model's access-fault address"),
        "#ifdef RVMODEL_ACCESS_FAULT_ADDRESS",
        f"LI(x{regs.base}, RVMODEL_ACCESS_FAULT_ADDRESS)",
    ]
    for upper in UPPER_PATTERNS:
        lines += [
            _li(regs.tmp, upper << 48),
            f"or x{regs.a}, x{regs.base}, x{regs.tmp}",
            *_sentinel(regs),
            td.add_testcase(_tid(f"{prefix}_flt", upper, "lw"), CP_FAULT, cg),
            *_fixed(f"lw x{regs.chk}, 0(x{regs.a})"),
            write_sigupd(regs.chk, td),
            _li(regs.data, VALUE_NEW),
            *_sentinel(regs),
            td.add_testcase(_tid(f"{prefix}_flt", upper, "sw"), CP_FAULT, cg),
            *_fixed(f"sw x{regs.data}, 0(x{regs.a})"),
            write_sigupd(regs.chk, td),
        ]
    lines += ["#endif // RVMODEL_ACCESS_FAULT_ADDRESS", f"LA(x{regs.base}, pm_lo_page)"]
    return lines


def pass_b_sign_extension(cfg: object | None, prefix: str, mode: str, td: TestData, regs: Regs, cg: str) -> list[str]:
    """ld/sd against an upper-half VA: only sign extension reproduces the base.

    For Sv39/Sv48/Sv57 modes where translation applies sign-extension instead
    of zero-extension to masked bits. Shared between Ssnpm and SmnpmS.
    """
    lines = [comment_banner(f"{prefix}: upper-half VA -- masking must sign extend, not zero extend")]
    lines += _load_base(mode, "hi", regs)
    for upper in UPPER_PATTERNS:
        lines += _tag_address(upper, regs)
        lines += _probe_load("ld", _tid(f"{prefix}_hi", upper, "ld"), td, regs, CP_MASKING, cg)
        lines += _probe_store("sd", "ld", _tid(f"{prefix}_hi", upper, "sd"), td, regs, CP_MASKING, cg)
    lines += _load_base(mode, "lo", regs)
    return lines


def pass_clear_on_xlen_change(
    cfg: object | None,
    prefix: str,
    td: TestData,
    regs: Regs,
    *,
    cp: str,
    cg: str,
    pmm_csr: str,
    pmm_shift: int,
    status_csr: str,
    status_shift: int,
    rv32_val: int = 0b01,
    rv64_val: int = 0b10,
    ifdef_guard: str | None = None,
) -> list[str]:
    """Setting status_csr's 2-bit field to 01 (RV32) must clear pmm_csr.PMM to 00.

    Generalizes Ssnpm's, SmnpmU's UXL-clear pass and SmnpmS's SXL-clear pass -- same
    clear-then-set-both-bits logic, just parameterized on which CSR/shift.
    """
    lines = [""]
    if ifdef_guard:
        lines.append(f"#ifndef {ifdef_guard}")
    lines += [
        comment_banner(f"{prefix}: {status_csr} field=01 must clear {pmm_csr}.PMM"),
        "RVTEST_GOTO_MMODE",
        "",
        f"csrr x{regs.chk}, {pmm_csr}",
        f"srli x{regs.chk}, x{regs.chk}, {pmm_shift}",
        f"andi x{regs.chk}, x{regs.chk}, 0x3",
        td.add_testcase(f"{prefix}_before", cp, cg),
        write_sigupd(regs.chk, td),
        "",
    ]
    mask = 0b11 << status_shift
    lines += [
        _li(regs.tmp, mask),
        f"csrc {status_csr}, x{regs.tmp}",
        _li(regs.tmp, rv32_val << status_shift),
        f"csrs {status_csr}, x{regs.tmp}",
        "",
    ]
    lines += [
        f"csrr x{regs.chk}, {pmm_csr}",
        f"srli x{regs.chk}, x{regs.chk}, {pmm_shift}",
        f"andi x{regs.chk}, x{regs.chk}, 0x3",
        td.add_testcase(f"{prefix}_after", cp, cg),
        write_sigupd(regs.chk, td),
        "",
    ]
    lines += [
        _li(regs.tmp, mask),
        f"csrc {status_csr}, x{regs.tmp}",
        _li(regs.tmp, rv64_val << status_shift),
        f"csrs {status_csr}, x{regs.tmp}",
    ]
    if ifdef_guard:
        lines.append(f"#endif // {ifdef_guard}")
    return lines
