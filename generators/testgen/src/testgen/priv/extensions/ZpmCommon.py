##################################
# priv/extensions/ZpmCommon.py
#
# Pointer masking (Ssnpm/Smmpm/Smnpm) shared test generators.
# Author :  David Harris, Umer Shahid & Ammarah Wakeel  email:ammarahwakeel9@gmail.com (UET, JULY 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared pointer-masking extension test infrastructure.
Common code for Ssnpm (S->U), Smmpm (M-mode), SmnpmS (M->S), SmnpmU (M->U)
test generators.
"""

from testgen.asm.csr import gen_csr_write_sigupd
from testgen.asm.helpers import arch_block, comment_banner, write_sigupd
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData
from testgen.priv.extensions.sv.page_tables import RV64_SV_MODES, SV39, PteFlags, create_page_mapping

# ── Constants ──────────────────────────────────────────────────────────────

UPPER_PATTERNS = [
    0x0000,  # no tag: masking is a no-op, the control case
    0x0001,  # bit 48   -- stripped by PMLEN=16 only
    0x0100,  # bit 56   -- stripped by PMLEN=16 only
    0x0200,  # bit 57   -- stripped by PMLEN=16 and PMLEN=7
    0x8000,  # bit 63   -- stripped by PMLEN=16 and PMLEN=7
    0xFFFF,  # bits 63:48 -- fully stripped by PMLEN=16, partially by PMLEN=7
    0xFE00,  # bits 63:57 -- exactly the PMLEN=7 window
    0xFF00,  # bits 63:56 -- fully stripped by PMLEN=16, partially by PMLEN=7
]

PMM_CONFIGS = [
    (0b00, 0, "pmm00"),
    (0b10, 7, "pmm10"),
    (0b11, 16, "pmm11"),
]

VALUE_OLD = 0xABCD_1234_ABCD_1234
VALUE_NEW = 0xA5A5_A5A5_A5A5_A5A5
SENTINEL = 0x1BAD_0BAD_1BAD_0BAD

CP_MASKING = "cp_pmlen_masking"

READS = ["lb", "lbu", "lh", "lhu", "lw", "lwu", "ld"]
WRITES = [("sb", "lbu"), ("sh", "lhu"), ("sw", "lwu"), ("sd", "ld")]
AMO_OPS = ["swap", "add", "xor", "and", "or", "min", "max", "minu", "maxu"]
RV64A_AMOS = [(f"amo{op}.{size}", readback) for op in AMO_OPS for size, readback in (("w", "lw"), ("d", "ld"))]
ZABHA_AMOS = [(f"amo{op}.{size}", readback) for op in AMO_OPS for size, readback in (("b", "lbu"), ("h", "lhu"))]
ZACAS_AMOS = ["amocas.w", "amocas.d", "amocas.q"]
FP_READS = [
    ("flw", "F_SUPPORTED", "fmv.w.x"),
    ("fld", "D_SUPPORTED", "fmv.d.x"),
]  # TODO :Add flq & fsq when Q is supported.
FP_WRITES = [
    ("fsw", "lw", "F_SUPPORTED", "fmv.w.x"),
    ("fsd", "ld", "D_SUPPORTED", "fmv.d.x"),
]
ZCA_READS_CL = ["c.lw", "c.ld"]
ZCA_WRITES_CS = [("c.sw", "lw"), ("c.sd", "ld")]
ZCA_READS_SP = ["c.lwsp", "c.ldsp"]
ZCA_WRITES_SP = [("c.swsp", "lw"), ("c.sdsp", "ld")]

ZICBOM_OPS = ["cbo.clean", "cbo.flush", "cbo.inval"]
ZICBOP_OPS = ["prefetch.r", "prefetch.w", "prefetch.i"]
ZICFISS_AMOS: list[
    tuple[str, str]
] = []  # TODO : Add all zicfiss instructions including amo and push, pop instructions.

VEC_READS = [
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
VEC_WRITES = [
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

SV_MODES = {sv.name: sv for sv in RV64_SV_MODES}
_MPRV_TABLE_LABEL = "rvtest_mprv_slvl{}_pg_tbl_"
_COMPRESSED_REGS = list(range(8, 16))  # registers encodable in 3-bit compressed fields

HIGH_VA = {
    "sv39": 0xFFFF_FFC0_0000_0000,
    "sv48": 0xFFFF_8000_0000_0000,
    # sv57 reuses sv48's boundary rather than its own tighter one (bit 56
    # only, 0xFF00...) because that value leaves bit 47 = 0, breaking the
    # PMLEN=16 round trip; this one keeps bits 63:47 all set to 1.
    "sv57": 0xFFFF_8000_0000_0000,
}

MODES = ["bare", "sv39", "sv48", "sv57"]
MODE_GUARDS = {m: None if m == "bare" else f"{m.upper()}_SUPPORTED" for m in MODES}

# PMM field bit position (common across mseccfg/menvcfg/senvcfg)
_PMM_SHIFT = 32

# Limited upper patterns for MPRV testing (per testplan)
_MPRV_UPPER_PATTERNS = [0x0000, 0x0001, 0x0200]


# ── Assembly Helpers ───────────────────────────────────────────────────────


def _binname(prefix: str, upper: int, mnemonic: str) -> str:
    return f"{prefix}_up{upper:04X}_{mnemonic.replace('.', '_')}"


def _tagged_address(base_reg: int, addr_reg: int, base: str | int, upper: int, offset: int = 0) -> list[str]:
    """Point *base_reg* at *base* (a label or an address) and *addr_reg* at the same address with bits 63:48
    XORed with *upper*.

    XOR equals OR for pm_lo_page, whose bits 63:48 are zero. For an upper-half base it makes
    the pointer non-canonical, so only a sign-extending mask recovers the base.
    """
    lines = [
        f"LA(x{base_reg}, {base})" if isinstance(base, str) else f"LI(x{base_reg}, {hex(base)})",
        f"LI(x{addr_reg}, {hex(upper << 48)})",
        f"xor x{addr_reg}, x{addr_reg}, x{base_reg}   # tagged pointer: bits 63:48 ^= 0x{upper:04X}",
    ]
    if offset:
        lines.append(f"addi x{addr_reg}, x{addr_reg}, {offset}   # force a misaligned effective address")
    return lines


def _seed(base_reg: int, scratch: int) -> list[str]:
    return [f"LI(x{scratch}, {hex(VALUE_OLD)})", f"sd x{scratch}, 0(x{base_reg})"]


# ── Factoring helpers (CSR fields / satp / data pages) ─────────────────────


def csr_op(op: str, csr: str, value: str, test_data: TestData, tsbi: bool = False) -> list[str]:
    """csrs/csrc/csrw *csr* with *value* (an assembler expression), directly or through a T-SBI call."""
    tmp = test_data.int_regs.get_register()
    instr = f"{op} {csr}, x{tmp}"
    lines = [f"LI(x{tmp}, {value})", tsbi_call(instr) if tsbi else instr]
    test_data.int_regs.return_register(tmp)
    return lines


def set_pmm_field(csr: str, val: int, pmlen: int, test_data: TestData, tsbi: bool = False) -> list[str]:
    """Clear then set the 2-bit PMM field in *csr*."""
    lines = [f"# {csr}.PMM={val:#04b} PMLEN={pmlen}", *csr_op("csrc", csr, f"{csr.upper()}_PMM", test_data, tsbi)]
    if val:
        lines.extend(csr_op("csrs", csr, hex(val << _PMM_SHIFT), test_data, tsbi))
    return lines


def set_mxr(enable: bool, test_data: TestData, status_csr: str = "sstatus", tsbi: bool = False) -> list[str]:
    """MXR gates pointer masking off entirely when set in priv modes below M"""
    op = "csrs" if enable else "csrc"
    return [
        f"# {status_csr}.MXR = {int(enable)}",
        *csr_op(op, status_csr, f"{status_csr.upper()}_MXR", test_data, tsbi),
    ]


def satp_setup(mode: str, test_data: TestData, tsbi: bool = False) -> list[str]:
    """Point satp at the framework root table in *mode*, from S-mode directly or from U-mode through T-SBI."""
    if not tsbi:
        return ["sfence.vma", SV_MODES[mode].satp_setup, "sfence.vma"]
    satp, mode_bits = test_data.int_regs.get_registers(2)
    lines = [
        f"LA(x{satp}, rvtest_Sroot_pg_tbl)",
        f"srli x{satp}, x{satp}, 12",
        f"LI(x{mode_bits}, (SATP64_MODE) & (SATP_MODE_{SV_MODES[mode].suffix} << 60))",
        f"or x{satp}, x{satp}, x{mode_bits}",
        tsbi_call("sfence.vma"),
        tsbi_call(f"csrw satp, x{satp}"),
        tsbi_call("sfence.vma"),
    ]
    test_data.int_regs.return_registers([satp, mode_bits])
    return lines


def satp_clear(tsbi: bool = False) -> list[str]:
    if not tsbi:
        return ["csrwi satp, 0", "sfence.vma"]
    return [tsbi_call("csrw satp, x0"), tsbi_call("sfence.vma")]


def data_page(label: str, value: int = VALUE_OLD) -> list[str]:
    """One 4 KiB page containing a single dword seed."""
    return [
        ".p2align 12",
        f"{label}: .dword {hex(value)}",
        ".zero 4088",
    ]


def data_slvl_tables(mode: str, table_label: str = "rvtest_slvl{}_pg_tbl") -> list[str]:
    """Zero-filled page-table pages below the root for *mode*, named by *table_label*."""
    lines: list[str] = []
    for level in range(SV_MODES[mode].levels - 1):
        lines.extend([".p2align 12", f"{table_label.format(level)}: .zero 4096"])
    return lines


# ── Page tables and MPRV data (Smmpm / Ssnpm) ───────────────────────────


def mprv_data_section() -> list[str]:
    lines = [
        ".pushsection .data",
        *data_page("pm_lo_page"),
        *data_page("mprv_page"),
    ]
    for mode in SV_MODES:
        guard = f"{mode.upper()}_SUPPORTED"
        lines.extend([f"#ifdef {guard}", *data_slvl_tables(mode, _MPRV_TABLE_LABEL + mode), f"#endif // {guard}"])
    lines.append(".popsection")
    return lines


def build_4k_image_map(
    mode: str, table_label: str, user_ranges: list[tuple[str, str | int]], test_data: TestData
) -> list[str]:
    """Map the 2 MiB region containing rvtest_code_begin as 512 identity 4 KiB leaves.

    The walk goes from the framework root through the tables named by *table_label*. A page gets
    PTE_U when it lies inside one of *user_ranges*, each a (begin label, end label or byte size)
    pair; everything else, such as the S-mode trap handler, stays supervisor-only.
    Only six integer registers are free, so the range bounds are reloaded on each iteration.
    """
    tables = [table_label.format(level) for level in SV_MODES[mode].levels_desc[1:]]
    (r0,) = test_data.int_regs.get_registers(1)
    lines = [
        f"# {mode.upper()}: 4 KiB mapping of the test image; PTE_U on {', '.join(b for b, _ in user_ranges)}",
        f"LA(x{r0}, rvtest_code_begin)",
        *_walk_asm(mode, tables, f"x{r0}", test_data),
    ]
    r1, count, perms, s1, s2 = test_data.int_regs.get_registers(5)
    lines.extend(
        [
            f"srli x{r0}, x{r0}, 21",
            f"slli x{r0}, x{r0}, 21                  # x{r0} = 2 MiB-aligned base of the image",
            f"LA(x{r1}, {tables[-1]})",
            f"li   x{count}, 512",
            "1:",
            f"li   x{perms}, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V)",
        ]
    )
    for begin, end in user_ranges:
        size = [f"LA(x{s2}, {end})", f"sub  x{s2}, x{s2}, x{s1}"] if isinstance(end, str) else [f"li   x{s2}, {end}"]
        lines.extend(
            [
                f"LA(x{s1}, {begin})",
                *size,
                f"sub  x{s1}, x{r0}, x{s1}",
                f"bltu x{s1}, x{s2}, 2f                # inside {begin} -> U-accessible",
            ]
        )
    lines.extend(
        [
            "j    3f",
            "2:",
            f"ori  x{perms}, x{perms}, PTE_U",
            "3:",
            f"srli x{s1}, x{r0}, 12",
            f"slli x{s1}, x{s1}, 10",
            f"or   x{s1}, x{s1}, x{perms}",
            f"sd   x{s1}, 0(x{r1})",
            f"addi x{r1}, x{r1}, 8",
            f"lui  x{s1}, 1",
            f"add  x{r0}, x{r0}, x{s1}",
            f"addi x{count}, x{count}, -1",
            f"bnez x{count}, 1b",
        ]
    )
    test_data.int_regs.return_registers([r0, r1, count, perms, s1, s2])
    return lines


def map_pm_hi_page(mode: str, *, user: bool) -> list[str]:
    """Map HIGH_VA[mode] to pm_hi_page with a 4 KiB read/write leaf."""
    va = HIGH_VA[mode]
    return [
        f"# {mode.upper()}: map {hex(va)} -> pm_hi_page",
        *create_page_mapping(
            SV_MODES[mode],
            leaf_level=0,
            leaf_flags=PteFlags(execute=False, user=user),
            virtual_address=hex(va),
            physical_address="pm_hi_page",
        ),
    ]


def _nonleaf_asm(parent: str, child: str, shift: int, va_reg: str, test_data: TestData) -> list[str]:
    """parent[VPN(va, shift)] = child, valid but not a leaf."""
    t1, t2, t3 = test_data.int_regs.get_registers(3)
    lines = [
        f"srli x{t1}, {va_reg}, {shift}",
        f"andi x{t1}, x{t1}, 0x1FF",
        f"slli x{t1}, x{t1}, 3",
        f"LA(x{t2}, {parent})",
        f"add  x{t2}, x{t2}, x{t1}",
        f"LA(x{t3}, {child})",
        f"srli x{t3}, x{t3}, 12",
        f"slli x{t3}, x{t3}, 10",
        f"ori  x{t3}, x{t3}, ({PteFlags.nonleaf()})",
        f"sd   x{t3}, 0(x{t2})",
    ]
    test_data.int_regs.return_registers([t1, t2, t3])
    return lines


def _walk_asm(mode: str, tables: list[str], va_reg: str, test_data: TestData) -> list[str]:
    """Install non-leaf entries from the framework root down to tables[0]."""
    sv = SV_MODES[mode]
    shifts = [sv.page_offset_bits(level) for level in sv.levels_desc[:-1]]
    chain = ["rvtest_Sroot_pg_tbl", *tables]
    lines: list[str] = []
    for parent, child, shift in zip(chain, chain[1:], shifts):
        lines.extend(_nonleaf_asm(parent, child, shift, va_reg, test_data))
    return lines


# ── Probe Primitives ───────────────────────────────────────────────────────
# Each probe reserves its own registers, points them at *base* tagged with *upper*,
# runs one access, and releases the registers. *cg* is the caller's covergroup.


def _with_arch(instr: str, arch: tuple[str, ...]) -> list[str]:
    """Enable *arch* extensions around *instr* only when it needs them."""
    return arch_block([instr], *arch) if arch else [instr]


def _access(
    instr: str, addr: int, binname: str, test_data: TestData, cp: str, cg: str, via_sp: bool, arch: tuple[str, ...]
) -> list[str]:
    """Emit the testcase label and ``instr, 0(addr)``, addressed through sp for c.*sp forms."""
    if not via_sp:
        return [test_data.add_testcase(binname, cp, cg), *_with_arch(f"{instr}, 0(x{addr})", arch)]
    sp_save = test_data.int_regs.get_register()
    lines = [
        f"mv x{sp_save}, sp",
        f"mv sp, x{addr}",
        test_data.add_testcase(binname, cp, cg),
        *_with_arch(f"{instr}, 0(sp)", arch),
        f"mv sp, x{sp_save}",
    ]
    test_data.int_regs.return_register(sp_save)
    return lines


def _probe_load(
    mn: str,
    upper: int,
    binname: str,
    test_data: TestData,
    cg: str,
    *,
    cp: str = CP_MASKING,
    base: str | int = "pm_lo_page",
    offset: int = 0,
    compressed: bool = False,
    via_sp: bool = False,
    fp_move: str | None = None,
    arch: tuple[str, ...] = (),
) -> list[str]:
    """Load through a tagged pointer into a SENTINEL-poisoned destination and record it.

    compressed: c.lw/c.ld only encode x8-x15. via_sp: c.*sp forms take their address from sp.
    fp_move: fmv.w.x or fmv.d.x to route the value through an FP destination.
    """
    a, chk = test_data.int_regs.get_registers(2, reg_range=_COMPRESSED_REGS if compressed else None)
    b = test_data.int_regs.get_register()
    fp = test_data.float_regs.get_register() if fp_move else None
    dest = f"f{fp}" if fp_move else f"x{chk}"
    lines = [*_tagged_address(b, a, base, upper, offset), *_seed(b, chk), f"LI(x{chk}, {hex(SENTINEL)})"]
    if fp_move:
        lines.append(f"{fp_move} {dest}, x{chk}   # poison the FP destination")
    lines.extend(_access(f"{mn} {dest}", a, binname, test_data, cp, cg, via_sp, arch))
    if fp_move:
        lines.append(f"fmv.x.{fp_move.split('.')[1]} x{chk}, {dest}")
    lines.append(write_sigupd(chk, test_data))
    test_data.int_regs.return_registers([a, chk, b])
    if fp is not None:
        test_data.float_regs.return_register(fp)
    return lines


def _probe_store(
    mn: str,
    readback: str,
    upper: int,
    binname: str,
    test_data: TestData,
    cg: str,
    *,
    cp: str = CP_MASKING,
    base: str | int = "pm_lo_page",
    offset: int = 0,
    compressed: bool = False,
    via_sp: bool = False,
    fp_move: str | None = None,
    arch: tuple[str, ...] = (),
) -> list[str]:
    """Store VALUE_NEW through a tagged pointer, then read the untagged base back with *readback*.

    The options match _probe_load.
    """
    a, data = test_data.int_regs.get_registers(2, reg_range=_COMPRESSED_REGS if compressed else None)
    b = test_data.int_regs.get_register()
    fp = test_data.float_regs.get_register() if fp_move else None
    src = f"f{fp}" if fp_move else f"x{data}"
    lines = [*_tagged_address(b, a, base, upper, offset), *_seed(b, data), f"LI(x{data}, {hex(VALUE_NEW)})"]
    if fp_move:
        lines.append(f"{fp_move} {src}, x{data}")
    lines.extend(_access(f"{mn} {src}", a, binname, test_data, cp, cg, via_sp, arch))
    lines.extend([f"{readback} x{data}, 0(x{b})", write_sigupd(data, test_data)])
    test_data.int_regs.return_registers([a, data, b])
    if fp is not None:
        test_data.float_regs.return_register(fp)
    return lines


def _probe_amo(
    mn: str, readback: str, upper: int, binname: str, test_data: TestData, cg: str, arch: tuple[str, ...] = ()
) -> list[str]:
    """AMO (or Zicfiss SSAMOSWAP) through a tagged pointer: record rd, then the memory readback."""
    b, a, data, chk = test_data.int_regs.get_registers(4)
    lines = [
        *_tagged_address(b, a, "pm_lo_page", upper),
        *_seed(b, data),
        f"LI(x{data}, {hex(VALUE_NEW)})",
        f"LI(x{chk}, {hex(SENTINEL)})",
        test_data.add_testcase(binname, CP_MASKING, cg),
        *_with_arch(f"{mn} x{chk}, x{data}, (x{a})", arch),
        write_sigupd(chk, test_data),
        f"{readback} x{chk}, 0(x{b})",
        write_sigupd(chk, test_data),
    ]
    test_data.int_regs.return_registers([b, a, data, chk])
    return lines


def _probe_zacas(mn: str, upper: int, binname: str, test_data: TestData, cg: str) -> list[str]:
    """ZACAS probe: amocas.w/d use single registers, amocas.q uses even/odd register pairs."""
    if mn == "amocas.q":
        # Take the pairs first: only a few even/odd pairs are free.
        dest, src = test_data.int_regs.get_register_pair(), test_data.int_regs.get_register_pair()
        b, a = test_data.int_regs.get_registers(2)
        lines = [
            *_tagged_address(b, a, "pm_lo_page", upper),
            *_seed(b, dest),
            f"sd x0, 8(x{b})   # seed high dword of the 128-bit comparand",
            f"LI(x{dest}, {hex(VALUE_OLD)})   # comparand.lo matches the seeded value",
            f"LI(x{dest + 1}, 0)                  # comparand.hi matches the seeded value",
            f"LI(x{src}, {hex(VALUE_NEW)})",
            f"LI(x{src + 1}, {hex(VALUE_NEW)})",
            test_data.add_testcase(binname, CP_MASKING, cg),
            f"{mn} x{dest}, x{src}, (x{a})",
            f"ld x{dest}, 0(x{b})",
            f"ld x{dest + 1}, 8(x{b})",
            write_sigupd(dest, test_data),
            write_sigupd(dest + 1, test_data),
        ]
        test_data.int_regs.return_register_pair(dest)
        test_data.int_regs.return_register_pair(src)
        test_data.int_regs.return_registers([b, a])
        return lines

    b, a, dest, src = test_data.int_regs.get_registers(4)
    lines = [
        *_tagged_address(b, a, "pm_lo_page", upper),
        *_seed(b, dest),
        f"LI(x{dest}, {hex(VALUE_OLD)})   # comparand matches the seeded value",
        f"LI(x{src}, {hex(VALUE_NEW)})",
        test_data.add_testcase(binname, CP_MASKING, cg),
        f"{mn} x{dest}, x{src}, (x{a})",
        f"ld x{dest}, 0(x{b})",
        write_sigupd(dest, test_data),
    ]
    test_data.int_regs.return_registers([b, a, dest, src])
    return lines


def _probe_cbo(mn: str, upper: int, binname: str, test_data: TestData, cg: str) -> list[str]:
    b, a, data = test_data.int_regs.get_registers(3)
    lines = [
        *_tagged_address(b, a, "pm_lo_page", upper),
        *_seed(b, data),
        test_data.add_testcase(binname, CP_MASKING, cg),
        f"{mn} 0(x{a})",
        f"ld x{data}, 0(x{b})",
        write_sigupd(data, test_data),
    ]
    test_data.int_regs.return_registers([b, a, data])
    return lines


def _probe_vec(
    sew: int, template: str, readback: str | None, upper: int, binname: str, test_data: TestData, cg: str
) -> list[str]:
    """Vector load (*readback* None) or store through a tagged pointer, two elements at *sew*."""
    b, a, value = test_data.int_regs.get_registers(3)
    lines = [
        *_tagged_address(b, a, "pm_lo_page", upper),
        *_seed(b, value),
        f"LI(x{value}, {hex(SENTINEL if readback is None else VALUE_NEW)})",
        "csrw vstart, x0",
        f"vsetivli x0, 2, e{sew}, m1, ta, ma",
        "vmv.v.i v4, 0   # zero index vector: indexed probes address the base itself",
        f"vmv.v.x v2, x{value}",
        test_data.add_testcase(binname, CP_MASKING, cg),
        template.format(a=a),
    ]
    if readback is None:
        lines.extend([f"vmv.x.s x{value}, v2", "csrw vstart, x0"])
    else:
        lines.extend(["csrw vstart, x0", f"{readback} x{value}, 0(x{b})"])
    lines.append(write_sigupd(value, test_data))
    test_data.int_regs.return_registers([b, a, value])
    return lines


# ── Common Test Generators ─────────────────────────────────────────────────


def generate_instruction_sweep_tests(prefix: str, test_data: TestData, cg: str) -> list[str]:
    lines = []
    for upper in UPPER_PATTERNS:
        lines.append(comment_banner(f"{prefix} {CP_MASKING}: tag 0x{upper:04X} -- full instruction sweep"))
        for mn in READS:
            lines.extend(_probe_load(mn, upper, _binname(prefix, upper, mn), test_data, cg))
        for mn, rb in WRITES:
            lines.extend(_probe_store(mn, rb, upper, _binname(prefix, upper, mn), test_data, cg))

        lines.append("#ifdef ZAAMO_SUPPORTED")
        for mn, rb in RV64A_AMOS:
            lines.extend(_probe_amo(mn, rb, upper, _binname(prefix, upper, mn), test_data, cg))
        lines.append("#ifdef ZABHA_SUPPORTED")
        for mn, rb in ZABHA_AMOS:
            lines.extend(_probe_amo(mn, rb, upper, _binname(prefix, upper, mn), test_data, cg))
        lines.extend(["#endif // ZABHA_SUPPORTED", "#ifdef ZACAS_SUPPORTED"])
        for mn in ZACAS_AMOS:
            lines.extend(_probe_zacas(mn, upper, _binname(prefix, upper, mn), test_data, cg))
        lines.extend(["#endif // ZACAS_SUPPORTED", "#endif // ZAAMO_SUPPORTED"])

        for mn, guard, mv in FP_READS:
            lines.extend(
                [
                    f"#ifdef {guard}",
                    *_probe_load(mn, upper, _binname(prefix, upper, mn), test_data, cg, fp_move=mv),
                    f"#endif // {guard}",
                ]
            )
        for mn, rb, guard, mv in FP_WRITES:
            lines.extend(
                [
                    f"#ifdef {guard}",
                    *_probe_store(mn, rb, upper, _binname(prefix, upper, mn), test_data, cg, fp_move=mv),
                    f"#endif // {guard}",
                ]
            )

        zca = ("zca",)
        lines.append("#ifdef ZCA_SUPPORTED")
        for mn in ZCA_READS_CL:
            lines.extend(_probe_load(mn, upper, _binname(prefix, upper, mn), test_data, cg, compressed=True, arch=zca))
        for mn, rb in ZCA_WRITES_CS:
            lines.extend(
                _probe_store(mn, rb, upper, _binname(prefix, upper, mn), test_data, cg, compressed=True, arch=zca)
            )
        for mn in ZCA_READS_SP:
            lines.extend(_probe_load(mn, upper, _binname(prefix, upper, mn), test_data, cg, via_sp=True, arch=zca))
        for mn, rb in ZCA_WRITES_SP:
            lines.extend(_probe_store(mn, rb, upper, _binname(prefix, upper, mn), test_data, cg, via_sp=True, arch=zca))
        zcd = {"via_sp": True, "fp_move": "fmv.d.x", "arch": ("zca", "zcd")}
        lines.extend(
            [
                "#ifdef ZCD_SUPPORTED",
                *_probe_load("c.fldsp", upper, _binname(prefix, upper, "c.fldsp"), test_data, cg, **zcd),
                *_probe_store("c.fsdsp", "ld", upper, _binname(prefix, upper, "c.fsdsp"), test_data, cg, **zcd),
                "#endif // ZCD_SUPPORTED",
                "#endif // ZCA_SUPPORTED",
            ]
        )

        lines.append("#ifdef ZICFISS_SUPPORTED")
        for mn, rb in ZICFISS_AMOS:
            lines.extend(_probe_amo(mn, rb, upper, _binname(prefix, upper, mn), test_data, cg, arch=("zicfiss",)))
        lines.append("#endif // ZICFISS_SUPPORTED")

        for guard, ops in (("ZICBOZ", ["cbo.zero"]), ("ZICBOM", ZICBOM_OPS), ("ZICBOP", ZICBOP_OPS)):
            lines.append(f"#ifdef {guard}_SUPPORTED")
            for mn in ops:
                lines.extend(_probe_cbo(mn, upper, _binname(prefix, upper, mn), test_data, cg))
            lines.append(f"#endif // {guard}_SUPPORTED")

        # EEW <= 32 needs only Zve32x (ZVL32B marks any vector support); EEW = 64 needs Zve64x.
        for guard, wide in (("ZVL32B", False), ("ZVE64X", True)):
            lines.append(f"#ifdef {guard}_SUPPORTED")
            for mn, sew, template in VEC_READS:
                if (sew > 32) == wide:
                    lines.extend(_probe_vec(sew, template, None, upper, _binname(prefix, upper, mn), test_data, cg))
            for mn, sew, template, rb in VEC_WRITES:
                if (sew > 32) == wide:
                    lines.extend(_probe_vec(sew, template, rb, upper, _binname(prefix, upper, mn), test_data, cg))
            lines.append(f"#endif // {guard}_SUPPORTED")

    return lines


def _load_store_sweep(
    prefix: str,
    load: str,
    store: str,
    readback: str,
    test_data: TestData,
    cp: str,
    cg: str,
    *,
    base: str | int = "pm_lo_page",
    offset: int = 0,
) -> list[str]:
    """One load and one store through each tag in UPPER_PATTERNS."""
    lines = []
    for upper in UPPER_PATTERNS:
        lines.extend(
            [
                *_probe_load(
                    load, upper, _binname(prefix, upper, load), test_data, cg, cp=cp, base=base, offset=offset
                ),
                *_probe_store(
                    store,
                    readback,
                    upper,
                    _binname(prefix, upper, store),
                    test_data,
                    cg,
                    cp=cp,
                    base=base,
                    offset=offset,
                ),
            ]
        )
    return lines


def generate_misaligned_tests(prefix: str, test_data: TestData, cg: str) -> list[str]:
    return [
        comment_banner(f"{prefix}: misaligned word accesses through a tagged pointer"),
        *_load_store_sweep(f"{prefix}_mis", "lw", "sw", "lw", test_data, "cp_pmlen_misaligned_word", cg, offset=1),
    ]


def generate_mxr_tests(
    prefix: str,
    test_data: TestData,
    cg: str,
    status_csr: str = "sstatus",
    tsbi: bool = False,
) -> list[str]:
    """sw/lw with MXR set. MXR suppresses masking, so tagged pointers must fault."""
    return [
        comment_banner(f"{prefix}: {status_csr}.MXR=1 suppresses pointer masking"),
        *set_mxr(True, test_data, status_csr, tsbi),
        *_load_store_sweep(f"{prefix}_mxr", "lw", "sw", "lw", test_data, "cp_pmm_mxr", cg),
    ]


def generate_jalr_tests(prefix: str, test_data: TestData, cg: str, mxr: int = 0) -> list[str]:
    """JALR to a tagged pointer at a local pad. Fetches are never masked, so only an untagged target reaches it."""
    base, a, chk = test_data.int_regs.get_registers(3)
    pad = f"{prefix}_mxr{mxr}_jalr_pad"
    lines = [
        comment_banner(f"{prefix}: JALR through a tagged pointer, MXR={mxr} (fetch is never masked)"),
        f"j {pad}_end",
        f"{pad}:",
        f"addi x{chk}, x{chk}, 1   # reached only if the fetch succeeded",
        "jr ra",
        f"{pad}_end:",
        f"LA(x{base}, {pad})",
    ]
    for upper in UPPER_PATTERNS:
        lines.extend(
            [
                f"LI(x{a}, {hex(upper << 48)})",
                f"xor x{a}, x{a}, x{base}",
                f"li x{chk}, 0",
                test_data.add_testcase(_binname(f"{prefix}_mxr{mxr}", upper, "jalr"), "cp_pmm_jalr", cg),
                f"jalr ra, 0(x{a})",
                write_sigupd(chk, test_data),
            ]
        )
    test_data.int_regs.return_registers([base, a, chk])
    return lines


def generate_fault_address_tests(prefix: str, test_data: TestData, cg: str) -> list[str]:
    cp = "cp_hardware_csr_writes_fault"
    base, a, data, chk = test_data.int_regs.get_registers(4)
    lines = [
        comment_banner(f"{prefix}: masked address resolves to the model's access-fault address"),
        "#ifdef RVMODEL_ACCESS_FAULT_ADDRESS",
        f"LI(x{base}, RVMODEL_ACCESS_FAULT_ADDRESS)",
    ]
    for upper in UPPER_PATTERNS:
        lines.extend(
            [
                f"LI(x{a}, {hex(upper << 48)})",
                f"xor x{a}, x{a}, x{base}",
                f"LI(x{chk}, {hex(SENTINEL)})",
                test_data.add_testcase(_binname(f"{prefix}_flt", upper, "lw"), cp, cg),
                f"lw x{chk}, 0(x{a})",
                write_sigupd(chk, test_data),
                f"LI(x{data}, {hex(VALUE_NEW)})",
                f"LI(x{chk}, {hex(SENTINEL)})",
                test_data.add_testcase(_binname(f"{prefix}_flt", upper, "sw"), cp, cg),
                f"sw x{data}, 0(x{a})",
                write_sigupd(chk, test_data),
            ]
        )
    lines.append("#endif // RVMODEL_ACCESS_FAULT_ADDRESS")
    test_data.int_regs.return_registers([base, a, data, chk])
    return lines


def generate_sign_extension_tests(prefix: str, mode: str, test_data: TestData, cg: str) -> list[str]:
    """ld/sd against an upper-half VA: only sign extension reproduces the base.

    For Sv39/Sv48/Sv57 modes where translation applies sign-extension instead
    of zero-extension to masked bits. Shared between Ssnpm and SmnpmS.
    """
    base = HIGH_VA[mode]
    return [
        comment_banner(f"{prefix}: upper-half VA {hex(base)} -- masking must sign extend, not zero extend"),
        *_load_store_sweep(f"{prefix}_hi", "ld", "sd", "ld", test_data, CP_MASKING, cg, base=base),
    ]


def generate_csr_write_tests(prefix: str, pmlen: int, test_data: TestData, cg: str, csrs: list[str]) -> list[str]:
    """CSR writes must not be pointer-masked (shared by Smmpm / SmnpmS)."""
    save, chk = test_data.int_regs.get_registers(2)
    lines = [comment_banner(f"{prefix}: CSR writes must not be pointer-masked")]
    pattern = ((1 << pmlen) - 1) << (64 - pmlen) | 0x1234_5678
    for csr in csrs:
        lines.extend(
            [
                f"csrr x{save}, {csr} # save the csr's value before clobbering it",
                f"LI(x{chk}, {hex(pattern)})",
                test_data.add_testcase(f"{prefix}_csrw_{csr}", "cp_pm_csr_software_access", cg),
                gen_csr_write_sigupd(chk, csr, test_data),
                f"csrw {csr}, x{save} # restore before any later trap needs this CSR",
            ]
        )
    test_data.int_regs.return_registers([save, chk])
    return lines


def generate_xlen_change_tests(
    prefix: str,
    test_data: TestData,
    *,
    cp: str,
    cg: str,
    pmm_csr: str,
    status_csr: str,
    status_shift: int,
    rv32_val: int = 0b01,
    rv64_val: int = 0b10,
    ifdef_guard: str | None = None,
) -> list[str]:
    """Setting status_csr's 2-bit field to 01 (RV32) must clear pmm_csr.PMM to 00.

    ifdef_guard names the UDB define (UDB_UXLEN_32 / UDB_SXLEN_32) that says the mode
    can actually be switched to RV32; on a fixed-XLEN-64 config the write is a WARL
    no-op and the pass is skipped (the matching coverpoint is guarded the same way).

    Runs in a mode whose own XLEN is unaffected (M in Smmpm, S in Ssnpm): the
    affected mode could neither execute the RV64 test code that follows nor see
    bits 33:32 of a CSR value returned by a T-SBI read.
    """
    chk, tmp = test_data.int_regs.get_registers(2)
    mask = 0b11 << status_shift
    lines = [""]
    if ifdef_guard:
        lines.append(f"#ifdef {ifdef_guard}")
    lines.extend(
        [
            comment_banner(f"{prefix}: {status_csr} field=01 must clear {pmm_csr}.PMM"),
            "",
            f"csrr x{chk}, {pmm_csr}",
            f"srli x{chk}, x{chk}, {_PMM_SHIFT}",
            f"andi x{chk}, x{chk}, 0x3",
            test_data.add_testcase(f"{prefix}_before", cp, cg),
            write_sigupd(chk, test_data),
            "",
            f"LI(x{tmp}, {hex(mask)})",
            f"csrc {status_csr}, x{tmp}",
            f"LI(x{tmp}, {hex(rv32_val << status_shift)})",
            f"csrs {status_csr}, x{tmp}",
            "",
            f"csrr x{chk}, {pmm_csr}",
            f"srli x{chk}, x{chk}, {_PMM_SHIFT}",
            f"andi x{chk}, x{chk}, 0x3",
            test_data.add_testcase(f"{prefix}_after", cp, cg),
            write_sigupd(chk, test_data),
            "",
            f"LI(x{tmp}, {hex(mask)})",
            f"csrc {status_csr}, x{tmp}",
            f"LI(x{tmp}, {hex(rv64_val << status_shift)})",
            f"csrs {status_csr}, x{tmp}",
        ]
    )
    if ifdef_guard:
        lines.append(f"#endif // {ifdef_guard}")
    test_data.int_regs.return_registers([chk, tmp])
    return lines


# ── MPRV Nested Loop Pass (Smmpm-specific) ────────────────────────────────


def set_mprv(enable: bool, test_data: TestData, mpp: str = "PRV_M") -> list[str]:
    """Set MPRV=1 with MPP=*mpp* (a PRV_* name), or clear MPRV. mstatus.MPP is bits 12:11."""
    if not enable:
        return csr_op("csrc", "mstatus", "MSTATUS_MPRV", test_data)
    return [
        *csr_op("csrc", "mstatus", "MSTATUS_MPP", test_data),
        *csr_op("csrs", "mstatus", f"MSTATUS_MPRV | ({mpp} << 11)", test_data),
    ]


def _mprv_lw_sw_probe(mpp: str, cp: str, prefix: str, test_data: TestData, cg: str) -> list[str]:
    """lw/sw through a pointer with MPRV=1/MPP=mpp, swept over _MPRV_UPPER_PATTERNS.
    MPRV stays set between accesses and is cleared once the sweep is done.
    """
    b, a, data, chk = test_data.int_regs.get_registers(4)
    lines = []
    for upper in _MPRV_UPPER_PATTERNS:
        lines.extend(
            [
                *_tagged_address(b, a, "pm_lo_page", upper),
                *_seed(b, data),
                f"LI(x{chk}, {hex(SENTINEL)})",
                *set_mprv(True, test_data, mpp),
                test_data.add_testcase(_binname(prefix, upper, "lw"), cp, cg),
                f"lw x{chk}, 0(x{a})",
                write_sigupd(chk, test_data),
                *_seed(b, data),
                f"LI(x{data}, {hex(VALUE_NEW)})",
                *set_mprv(True, test_data, mpp),
                test_data.add_testcase(_binname(prefix, upper, "sw"), cp, cg),
                f"sw x{data}, 0(x{a})",
                *set_mprv(True, test_data, mpp),
                f"lw x{chk}, 0(x{b})",
                write_sigupd(chk, test_data),
            ]
        )
    test_data.int_regs.return_registers([b, a, data, chk])
    lines.extend(set_mprv(False, test_data))
    return lines


def _mprv_satp_loop(
    mpp: str,
    mpp_name: str,
    cp: str,
    mxr_val: int,
    mseccfg_pmm: int,
    menvcfg_pmm: int,
    test_data: TestData,
    cg: str,
) -> list[str]:
    """Shared between MPP=U (S_SUPPORTED) and MPP=S,
    which loop identically and share the same coverpoint
    (cp_pm_mprv_mpp_u_s). The U-accessible data map is built once by the
    caller before entering the mxr/pmm loops.
    """
    lines = []
    for senvcfg_pmm, senvcfg_pmlen, _ in PMM_CONFIGS:
        lines.extend(set_pmm_field("senvcfg", senvcfg_pmm, senvcfg_pmlen, test_data))

        for satp_mode in ["bare", "sv39"]:
            prefix = (
                f"mprv_mxr{mxr_val}_mseccfg{mseccfg_pmm:02b}_"
                f"menvcfg{menvcfg_pmm:02b}_senvcfg{senvcfg_pmm:02b}_"
                f"{satp_mode}_{mpp_name}"
            )
            if satp_mode != "bare":
                lines.extend([SV39.satp_setup, "sfence.vma"])
            lines.extend(_mprv_lw_sw_probe(mpp, cp, prefix, test_data, cg))
            if satp_mode != "bare":
                lines.extend(["csrwi satp, 0", "sfence.vma"])
    return lines


def generate_mprv_tests(test_data: TestData, cg: str) -> list[str]:
    """MPRV=1 test with nested loops over MXR, mseccfg.PMM, menvcfg.PMM, senvcfg.PMM, MPP, satp.MODE, upper patterns.

    Uses only Bare and Sv39 modes (not Sv48/Sv57).
    senvcfg.PMM is only programmed when S_SUPPORTED (CSR does not exist otherwise).
    MPP=M: no SATP at all (satp is an S-mode register); no S-mode required.
    MPP=U: no S-mode guard required; SATP used only when S_SUPPORTED. Under
    sv39, pm_lo_page's default PTE has no PTE_U, so the MPP=U probes remap
    the data range with build_4k_image_map before enabling SATP --
    without this, every mppu/sv39 access would page-fault regardless of
    tag/PMLEN and the masking behavior would never actually be exercised.
    MPP=S (S_SUPPORTED only): loops satp.MODE in {Bare, Sv39}.
    The MPP=U remap already put PTE_U on the data pages, so SUM must be
    set for S-mode accesses to succeed.  No further remap is done here.

    mstatus.MPRV, .MXR and .SUM are all explicitly cleared at the end rather
    than snapshotted/restored
    """
    lines = [
        comment_banner(
            "Smmpm MPRV: pointer masking with MPRV=1 uses effective MPP's PMM settings",
            "MPRV=1 causes effective privilege = MPP, so mseccfg.PMM is ignored."
            "MPP=M: no SATP. MPP=U: no S guard. MPP=S and senvcfg: S_SUPPORTED only.",
        ),
        "",
        "#ifdef S_SUPPORTED",
        "#ifdef SV39_SUPPORTED",
        "# Build the U-accessible data map once; the page tables never change",
        *build_4k_image_map(
            "sv39",
            _MPRV_TABLE_LABEL + "sv39",
            [("pm_lo_page", 4096), ("mprv_page", 4096), ("rvtest_data_begin", "end_signature")],
            test_data,
        ),
        "sfence.vma",
        "#endif // SV39_SUPPORTED",
        # Enable SUM so we can access user-space pages from S-mode (only when S exists)
        "# mstatus.SUM = 1",
        *csr_op("csrs", "mstatus", "MSTATUS_SUM", test_data),
        "#endif // S_SUPPORTED",
    ]

    # Loop over MXR settings (only meaningful when S-mode exists)
    for mxr_val in [0, 1]:
        lines.extend(["#ifdef S_SUPPORTED", *set_mxr(mxr_val != 0, test_data, "mstatus"), "#endif // S_SUPPORTED"])

        # Loop over mseccfg.PMM (M-mode setting)
        for mseccfg_pmm, mseccfg_pmlen, _ in PMM_CONFIGS:
            lines.extend(set_pmm_field("mseccfg", mseccfg_pmm, mseccfg_pmlen, test_data))

            # Loop over menvcfg.PMM
            for menvcfg_pmm, menvcfg_pmlen, _ in PMM_CONFIGS:
                prefix_m = f"mprv_mxr{mxr_val}_mseccfg{mseccfg_pmm:02b}_menvcfg{menvcfg_pmm:02b}_senvcfg00_nosatp_mppm"
                prefix_u_nos = (
                    f"mprv_mxr{mxr_val}_mseccfg{mseccfg_pmm:02b}_menvcfg{menvcfg_pmm:02b}_senvcfg00_nosatp_mppu"
                )
                lines.extend(
                    [
                        *set_pmm_field("menvcfg", menvcfg_pmm, menvcfg_pmlen, test_data),
                        # MPP=M: always runs, no SATP at all (satp is S-mode CSR)
                        *_mprv_lw_sw_probe("PRV_M", "cp_pm_mprv_mpp_m", prefix_m, test_data, cg),
                        # MPP=U: no S_SUPPORTED guard on the MPP itself.
                        # senvcfg only exists / is programmed when S_SUPPORTED.
                        # SATP only when S_SUPPORTED. Map was already built once above.
                        "#ifdef S_SUPPORTED",
                        *_mprv_satp_loop(
                            "PRV_U", "mppu", "cp_pm_mprv_mpp_u_s", mxr_val, mseccfg_pmm, menvcfg_pmm, test_data, cg
                        ),
                        "#endif // S_SUPPORTED",
                        # MPP=U when S is NOT supported: no senvcfg, no SATP
                        "#ifndef S_SUPPORTED",
                        *_mprv_lw_sw_probe("PRV_U", "cp_pm_mprv_mpp_u_no_s", prefix_u_nos, test_data, cg),
                        "#endif // !S_SUPPORTED",
                        # MPP=S: only when S_SUPPORTED; SATP in {Bare, Sv39}
                        "#ifdef S_SUPPORTED",
                        *_mprv_satp_loop(
                            "PRV_S", "mpps", "cp_pm_mprv_mpp_u_s", mxr_val, mseccfg_pmm, menvcfg_pmm, test_data, cg
                        ),
                        "#endif // S_SUPPORTED",
                    ]
                )

    lines.extend(
        [
            *set_pmm_field("mseccfg", 0b00, 0, test_data),
            *set_pmm_field("menvcfg", 0b00, 0, test_data),
            "#ifdef S_SUPPORTED",
            *set_pmm_field("senvcfg", 0b00, 0, test_data),
            *set_mxr(False, test_data, "mstatus"),
            "# mstatus.SUM = 0",
            *csr_op("csrc", "mstatus", "MSTATUS_SUM", test_data),
            "#endif // S_SUPPORTED",
            *set_mprv(False, test_data),
            "# restore mstatus.MPP = M; set_mprv(False, ...) only clears MPRV",
            *csr_op("csrs", "mstatus", "MSTATUS_MPP", test_data),
        ]
    )

    return lines
