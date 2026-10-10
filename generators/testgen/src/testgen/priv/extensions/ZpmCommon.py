##################################
# priv/extensions/ZpmCommon.py
#
# Pointer masking (Ssnpm/Smmpm/Smnpm) shared test generators.
# Author :  David Harris, Umer Shahid & Ammarah Wakeel  email:ammarahwakeel9@gmail.com (UET, JULY 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

"""
Shared pointer-masking extension test infrastructure.
Common code for Ssnpm (S->U), Smmpm (M-mode), SmnpmS (M->S), SmnpmU (M->U)
test generators.
"""

from testgen.asm.csr import gen_csr_write_sigupd
from testgen.asm.helpers import arch_block, comment_banner, write_sigupd
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData
from testgen.priv.extensions.sv.page_tables import RV64_SV_MODES, SV39, PteFlags, create_page_mapping

# ── Constants ──────────────────────────────────────────────────────────────

# Values for the address tag in bits 63:48. _tagged_address shifts each value left by 48.
# PMM=10 masks bits 63:57; PMM=11 masks bits 63:48. The set covers both boundaries.
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

# Each PMM setting is split into three files to keep tests under 100k instructions:
#   sweep_lowtags  -- instruction sweep, tags with bit 63 clear (none, or bit 48, 56 or 57)
#   sweep_hightags -- instruction sweep, tags with bit 63 set
#   edgecases      -- misaligned, JALR, fault-address, MXR and the other non-sweep probes
EDGE_CASES = "edgecases"
SPLITS = [
    ("sweep_lowtags", UPPER_PATTERNS[:4]),
    ("sweep_hightags", UPPER_PATTERNS[4:]),
    (EDGE_CASES, []),
]

# (PMM encoding, PMLEN, filename label) for the supported pointer masks.
PMM_CONFIGS = [
    (0b00, 0, "pmm00"),
    (0b10, 7, "pmm10"),
    (0b11, 16, "pmm11"),
]

# Values used to seed memory, write new data, and detect an unexpected load result.
VALUE_OLD = 0xABCD_1234_ABCD_1234
VALUE_NEW = 0xA5A5_A5A5_A5A5_A5A5
SENTINEL = 0x1BAD_0BAD_1BAD_0BAD

# Shared coverage point for normal pointer-masking accesses.
CP_MASKING = "cp_pmlen_masking"

# Scalar loads and stores. Store entries are (store mnemonic, readback load).
READS = ["lb", "lbu", "lh", "lhu", "lw", "lwu", "ld"]
WRITES = [("sb", "lbu"), ("sh", "lhu"), ("sw", "lwu"), ("sd", "ld")]
AMO_OPS = ["swap", "add", "xor", "and", "or", "min", "max", "minu", "maxu"]
# AMO tables contain (mnemonic, readback instruction).
RV64A_AMOS = [(f"amo{op}.{size}", readback) for op in AMO_OPS for size, readback in (("w", "lw"), ("d", "ld"))]
ZABHA_AMOS = [(f"amo{op}.{size}", readback) for op in AMO_OPS for size, readback in (("b", "lbu"), ("h", "lhu"))]
ZACAS_AMOS = ["amocas.w", "amocas.d", "amocas.q"]
# Floating-point load entries contain (instruction, feature guard).
# TODO: Add flq and fsq when Q is supported.
FP_READS = [
    ("flw", "F_SUPPORTED"),
    ("fld", "D_SUPPORTED"),
]
FP_WRITES = [
    ("fsw", "lw", "F_SUPPORTED", "fmv.w.x"),
    ("fsd", "ld", "D_SUPPORTED", "fmv.d.x"),
]
# Compressed operations split into register-register and stack-pointer forms.
ZCA_READS_CL = ["c.lw", "c.ld"]
ZCA_WRITES_CS = [("c.sw", "lw"), ("c.sd", "ld")]
ZCA_READS_SP = ["c.lwsp", "c.ldsp"]
ZCA_WRITES_SP = [("c.swsp", "lw"), ("c.sdsp", "ld")]

# Cache-block and prefetch operations use rs1 as their address.
ZICBOM_OPS = ["cbo.clean", "cbo.flush", "cbo.inval"]
ZICBOP_OPS = ["prefetch.r", "prefetch.w", "prefetch.i"]
# Zicfiss instructions target SS_PAGE , used only by the suites
# that probe below M-mode under S-mode (Ssnpm, SmnpmS``). AMO entries contain (mnemonic, readback instruction).
ZICFISS_AMOS = [("ssamoswap.w", "lw"), ("ssamoswap.d", "ld")]
# Push and pop entries contain (mnemonic, link register, is compressed). They address memory through ssp.
ZICFISS_PUSHES = [("sspush", 1, False), ("sspush", 5, False), ("c.sspush", 1, True)]
ZICFISS_POPS = [("sspopchk", 1, False), ("sspopchk", 5, False), ("c.sspopchk", 5, True)]
SS_PAGE = "pm_ss_page"
# Tables of the 4 KiB identity map of the test image, which holds the SS_PAGE leaf.
IMAGE_TABLES = "pm_img_slvl{}_pg_tbl"

# Vector entries contain (instruction, SEW, assembly template).
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

# SATP mode descriptors and the page-table label pattern.
SV_MODES = {sv.name: sv for sv in RV64_SV_MODES}
_MPRV_TABLE_LABEL = "rvtest_mprv_slvl{}_pg_tbl_"
_COMPRESSED_REGS = list(range(8, 16))  # registers encodable in 3-bit compressed fields

# Upper-half virtual addresses used to verify sign extension after masking.
HIGH_VA = {
    "sv39": 0xFFFF_FFC0_0000_0000,
    "sv48": 0xFFFF_8000_0000_0000,
    # sv57 reuses sv48's boundary rather than its own tighter one (bit 56
    # only, 0xFF00...) because that value leaves bit 47 = 0, breaking the
    # PMLEN=16 round trip; this one keeps bits 63:47 all set to 1.
    "sv57": 0xFFFF_8000_0000_0000,
}

# Translation modes and their compile-time support guards.
MODES = ["bare", "sv39", "sv48", "sv57"]
MODE_GUARDS = {m: None if m == "bare" else f"{m.upper()}_SUPPORTED" for m in MODES}

# PMM field bit position (common across mseccfg/menvcfg/senvcfg)
_PMM_SHIFT = 32

# Smaller tag set used by the MPRV coverage points.
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
    return [
        f"LI(x{scratch}, {hex(VALUE_OLD)})",
        f"sd x{scratch}, 0(x{base_reg})",
    ]


# ── CSR, satp, and data-section helpers ───────────────────────────────────


def csr_op(op: str, csr: str, value: str, test_data: TestData, tsbi: bool = False) -> list[str]:
    """csrs/csrc/csrw *csr* with *value* (an assembler expression), directly or through a T-SBI call."""
    tmp = test_data.int_regs.get_register()
    instr = f"{op} {csr}, x{tmp}"
    lines = [f"LI(x{tmp}, {value})", tsbi_call(instr) if tsbi else instr]
    test_data.int_regs.return_register(tmp)
    return lines


def set_pmm_field(csr: str, val: int, pmlen: int, test_data: TestData, tsbi: bool = False) -> list[str]:
    """Clear then set the 2-bit PMM field in *csr*."""
    lines = [
        f"# {csr}.PMM={val:#04b} PMLEN={pmlen}",
        *csr_op("csrc", csr, f"{csr.upper()}_PMM", test_data, tsbi),
    ]
    if val:
        lines.extend(csr_op("csrs", csr, hex(val << _PMM_SHIFT), test_data, tsbi))
    return lines


def set_mxr(enable: bool, test_data: TestData, status_csr: str = "sstatus", tsbi: bool = False) -> list[str]:
    """Set or clear MXR, which disables pointer masking below M-mode."""
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
    """Clear satp directly or through T-SBI."""
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


def ss_data_page(image_mode: str | None = None) -> list[str]:
    """The page probed by the Zicfiss instructions, plus the IMAGE_TABLES pages for *image_mode*."""
    tables = data_slvl_tables(image_mode, IMAGE_TABLES) if image_mode else []
    return _ifdef("ZICFISS_SUPPORTED", [*data_page(SS_PAGE), *tables])


def set_sse(csr: str, enable: bool, test_data: TestData, tsbi: bool = False) -> list[str]:
    """Set or clear the shadow-stack enable (SSE) in menvcfg or senvcfg."""
    op = "csrs" if enable else "csrc"
    return _ifdef(
        "ZICFISS_SUPPORTED",
        [f"# {csr}.SSE = {int(enable)}", *csr_op(op, csr, f"{csr.upper()}_SSE", test_data, tsbi)],
    )


def data_slvl_tables(mode: str, table_label: str = "rvtest_slvl{}_pg_tbl") -> list[str]:
    """Zero-filled page-table pages below the root for *mode*, named by *table_label*."""
    lines: list[str] = []
    for level in range(SV_MODES[mode].levels - 1):
        lines.extend([".p2align 12", f"{table_label.format(level)}: .zero 4096"])
    return lines


# ── Page tables and MPRV data (Smmpm / Ssnpm) ───────────────────────────


def mprv_data_section() -> list[str]:
    """Return data pages and optional lower-level tables for MPRV probes."""
    lines = [*data_page("pm_lo_page"), *data_page("mprv_page")]
    for mode in SV_MODES:
        guard = f"{mode.upper()}_SUPPORTED"
        lines.extend(_ifdef(guard, data_slvl_tables(mode, _MPRV_TABLE_LABEL + mode)))
    return lines


def build_4k_image_map(
    mode: str,
    table_label: str,
    user_ranges: list[tuple[str, str | int]],
    test_data: TestData,
    *,
    ss_page_user: bool | None = None,
) -> list[str]:
    """Map the 2 MiB region containing rvtest_code_begin as 512 identity 4 KiB leaves.

    The walk goes from the framework root through the tables named by *table_label*. A page gets
    PTE_U when its base lies inside one of *user_ranges*, each a (begin label, end label or byte size)
    pair; everything else, such as the S-mode trap handler, stays supervisor-only.
    All 512 leaves are written supervisor-only first; a second pass sets PTE_U on each range's pages.
    With Zicfiss, *ss_page_user* also makes SS_PAGE a shadow-stack page (xwr=010), with PTE_U if true.
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
            f"LI(x{count}, 512)",
            f"LI(x{perms}, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V))",
            f"mv   x{s2}, x{r0}",
            "1:",
            f"srli x{s1}, x{s2}, 12",
            f"slli x{s1}, x{s1}, 10",
            f"or   x{s1}, x{s1}, x{perms}",
            f"sd   x{s1}, 0(x{r1})",
            f"addi x{r1}, x{r1}, 8",
            f"lui  x{s1}, 1",
            f"add  x{s2}, x{s2}, x{s1}",
            f"addi x{count}, x{count}, -1",
            f"bnez x{count}, 1b",
            f"LA(x{r1}, {tables[-1]})",
        ]
    )
    for begin, end in user_ranges:
        bound = [f"LA(x{s2}, {end})"] if isinstance(end, str) else [f"LI(x{s2}, {end})", f"add  x{s2}, x{s2}, x{s1}"]
        lines.extend(
            [
                f"# PTE_U on pages based in [{begin}, {end if isinstance(end, str) else f'{begin} + {end}'})",
                f"LA(x{s1}, {begin})",
                *bound,
                f"addi x{s1}, x{s1}, -1",
                f"srli x{s1}, x{s1}, 12",
                f"addi x{s1}, x{s1}, 1",
                f"slli x{s1}, x{s1}, 12                  # first page base at or above {begin}",
                "j    3f",
                "2:",
                f"sub  x{count}, x{s1}, x{r0}",
                f"srli x{perms}, x{count}, 21",
                f"bnez x{perms}, 4f                      # page outside the 2 MiB image",
                f"srli x{count}, x{count}, 9             # leaf offset = page index * 8",
                f"add  x{count}, x{count}, x{r1}",
                f"ld   x{perms}, 0(x{count})",
                f"ori  x{perms}, x{perms}, PTE_U",
                f"sd   x{perms}, 0(x{count})",
                "4:",
                f"lui  x{count}, 1",
                f"add  x{s1}, x{s1}, x{count}",
                "3:",
                f"bltu x{s1}, x{s2}, 2b",
            ]
        )
    if ss_page_user is not None:
        ss_leaf = [
            f"# {SS_PAGE}: shadow-stack leaf (xwr=010)",
            f"LA(x{s1}, {SS_PAGE})",
            f"sub  x{count}, x{s1}, x{r0}",
            f"srli x{count}, x{count}, 9             # leaf offset = page index * 8",
            f"add  x{count}, x{count}, x{r1}",
            f"srli x{s1}, x{s1}, 12",
            f"slli x{s1}, x{s1}, 10",
            f"ori  x{s1}, x{s1}, ({PteFlags(read=False, execute=False, user=ss_page_user)})",
            f"sd   x{s1}, 0(x{count})",
        ]
        lines.extend(_ifdef("ZICFISS_SUPPORTED", ss_leaf))
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


# ── Probe helpers ──────────────────────────────────────────────────────────
# Each probe allocates and releases its own registers. *cg* is the caller's covergroup.


def _ifdef(guard: str, body: list[str]) -> list[str]:
    """Wrap assembly lines in a preprocessor feature guard."""
    return [f"#ifdef {guard}", *body, f"#endif // {guard}"]


def _access(
    instr: str,
    addr: int,
    bin_name: str,
    test_data: TestData,
    coverpoint: str,
    covergroup: str,
    via_sp: bool,
    arch_extensions: tuple[str, ...],
) -> list[str]:
    """Emit the testcase label and ``instr, 0(addr)``, addressed through sp for c.*sp forms."""
    if not via_sp:
        return [
            test_data.add_testcase(bin_name, coverpoint, covergroup),
            *arch_block([f"{instr}, 0(x{addr})"], *arch_extensions),
        ]
    sp_save = test_data.int_regs.get_register()
    lines = [
        f"mv x{sp_save}, sp",
        f"mv sp, x{addr}",
        test_data.add_testcase(bin_name, coverpoint, covergroup),
        *arch_block([f"{instr}, 0(sp)"], *arch_extensions),
        f"mv sp, x{sp_save}",
    ]
    test_data.int_regs.return_register(sp_save)
    return lines


def _probe_load(
    mnemonic: str,
    upper_tag: int,
    bin_name: str,
    test_data: TestData,
    covergroup: str,
    *,
    coverpoint: str = CP_MASKING,
    base_address: str | int = "pm_lo_page",
    offset: int = 0,
    compressed: bool = False,
    via_sp: bool = False,
    float_load: bool = False,
    arch_extensions: tuple[str, ...] = (),
) -> list[str]:
    """Generate one load probe and record the loaded value.

    ``compressed`` restricts address and result registers to x8-x15.
    ``via_sp`` uses the stack pointer as the address register.
    ``float_load`` records the result with the floating-point signature helper.
    """
    reg_range = _COMPRESSED_REGS if compressed else None
    addr, scratch = test_data.int_regs.get_registers(2, reg_range=reg_range)
    base_reg = test_data.int_regs.get_register()
    if float_load:
        result = test_data.float_regs.get_register()
        destination = f"f{result}"
    else:
        result = scratch
        destination = f"x{result}"

    lines = [*_tagged_address(base_reg, addr, base_address, upper_tag, offset), *_seed(base_reg, scratch)]
    if not float_load:
        lines.append(f"LI(x{result}, {hex(SENTINEL)})")
    lines.extend(
        _access(f"{mnemonic} {destination}", addr, bin_name, test_data, coverpoint, covergroup, via_sp, arch_extensions)
    )
    lines.append(write_sigupd(result, test_data, sig_type="float" if float_load else "int"))

    test_data.int_regs.return_registers([addr, scratch, base_reg])
    if float_load:
        test_data.float_regs.return_register(result)
    return lines


def _probe_store(
    mnemonic: str,
    readback_mnemonic: str,
    upper_tag: int,
    bin_name: str,
    test_data: TestData,
    covergroup: str,
    *,
    coverpoint: str = CP_MASKING,
    base_address: str | int = "pm_lo_page",
    offset: int = 0,
    compressed: bool = False,
    via_sp: bool = False,
    fp_move_mnemonic: str | None = None,
    arch_extensions: tuple[str, ...] = (),
) -> list[str]:
    """Generate one store probe, then read the untagged address back."""
    reg_range = _COMPRESSED_REGS if compressed else None
    addr, value = test_data.int_regs.get_registers(2, reg_range=reg_range)
    base_reg = test_data.int_regs.get_register()
    fp_reg = test_data.float_regs.get_register() if fp_move_mnemonic is not None else None
    source = f"f{fp_reg}" if fp_reg is not None else f"x{value}"

    lines = [
        *_tagged_address(base_reg, addr, base_address, upper_tag, offset),
        *_seed(base_reg, value),
        f"LI(x{value}, {hex(VALUE_NEW)})",
    ]
    if fp_move_mnemonic is not None:
        lines.append(f"{fp_move_mnemonic} {source}, x{value}")
    lines.extend(
        _access(f"{mnemonic} {source}", addr, bin_name, test_data, coverpoint, covergroup, via_sp, arch_extensions)
    )
    lines.extend([f"{readback_mnemonic} x{value}, 0(x{base_reg})", write_sigupd(value, test_data)])

    test_data.int_regs.return_registers([addr, value, base_reg])
    if fp_reg is not None:
        test_data.float_regs.return_register(fp_reg)
    return lines


def _probe_amo(
    mnemonic: str,
    readback_mnemonic: str,
    upper_tag: int,
    bin_name: str,
    test_data: TestData,
    covergroup: str,
    arch_extensions: tuple[str, ...] = (),
) -> list[str]:
    """Generate one AMO probe and record both its result and memory value."""
    base_reg, addr, value, result = test_data.int_regs.get_registers(4)
    lines = [
        *_tagged_address(base_reg, addr, "pm_lo_page", upper_tag),
        *_seed(base_reg, value),
        f"LI(x{value}, {hex(VALUE_NEW)})",
        f"LI(x{result}, {hex(SENTINEL)})",
        test_data.add_testcase(bin_name, CP_MASKING, covergroup),
        *arch_block([f"{mnemonic} x{result}, x{value}, (x{addr})"], *arch_extensions),
        write_sigupd(result, test_data),
        f"{readback_mnemonic} x{result}, 0(x{base_reg})",
        write_sigupd(result, test_data),
    ]
    test_data.int_regs.return_registers([base_reg, addr, value, result])
    return lines


def _probe_ssamoswap(
    mnemonic: str, readback_mnemonic: str, upper_tag: int, bin_name: str, test_data: TestData, covergroup: str
) -> list[str]:
    """Generate one SSAMOSWAP probe on SS_PAGE and record both its result and memory value.

    An ordinary store to a shadow-stack page faults, so the page is seeded with SSAMOSWAP.D
    through the untagged address.
    """
    base_reg, addr, value, result = test_data.int_regs.get_registers(4)
    lines = [
        *_tagged_address(base_reg, addr, SS_PAGE, upper_tag),
        f"LI(x{value}, {hex(VALUE_OLD)})",
        f"ssamoswap.d x0, x{value}, (x{base_reg})",
        f"LI(x{value}, {hex(VALUE_NEW)})",
        f"LI(x{result}, {hex(SENTINEL)})",
        test_data.add_testcase(bin_name, "cp_pmlen_zicfiss_amo", covergroup),
        f"{mnemonic} x{result}, x{value}, (x{addr})",
        write_sigupd(result, test_data),
        f"{readback_mnemonic} x{result}, 0(x{base_reg})",
        write_sigupd(result, test_data),
    ]
    test_data.int_regs.return_registers([base_reg, addr, value, result])
    return lines


def _probe_ssp(
    mnemonic: str, link: int, compressed: bool, push: bool, upper_tag: int, bin_name: str, test_data: TestData, cg: str
) -> list[str]:
    """Generates a shadow-stack push or pop probe using a tagged ssp, with SSPUSH storing the link register at ssp-8
    and SSPOPCHK loading and validating it from ssp.
    Records the resulting ssp on successful access and the memory value for pushes, using x1 or x5 as the link register.
    """
    base_reg, addr, value = test_data.int_regs.get_registers(3)
    lines = [
        *_tagged_address(base_reg, addr, SS_PAGE, upper_tag),
        f"LI(x{value}, {hex(VALUE_OLD)})",
        f"ssamoswap.d x0, x{value}, (x{base_reg})",
        *([f"addi x{addr}, x{addr}, 8"] if push else []),
        f"csrw CSR_SSP, x{addr}",
        f"LI(x{link}, {hex(VALUE_NEW if push else VALUE_OLD)})",
        test_data.add_testcase(bin_name, "cp_pmlen_zicfiss_ssp", cg),
        *arch_block([f"{mnemonic} x{link}"], *(("zca", "zcmop") if compressed else ())),
        f"csrr x{value}, CSR_SSP",
        write_sigupd(value, test_data),
    ]
    if push:
        lines.extend([f"ld x{value}, 0(x{base_reg})", write_sigupd(value, test_data)])
    test_data.int_regs.return_registers([base_reg, addr, value])
    return _ifdef("ZCMOP_SUPPORTED", lines) if compressed else lines


def _probe_zacas(mnemonic: str, upper_tag: int, bin_name: str, test_data: TestData, covergroup: str) -> list[str]:
    """Generate an AMOCAS probe, using register pairs for AMOCAS.Q."""
    if mnemonic == "amocas.q":
        comparand = test_data.int_regs.get_register_pair()
        replacement = test_data.int_regs.get_register_pair()
        base_reg, addr = test_data.int_regs.get_registers(2)
        lines = [
            *_tagged_address(base_reg, addr, "pm_lo_page", upper_tag),
            *_seed(base_reg, comparand),
            f"sd x0, 8(x{base_reg})   # seed high dword of the 128-bit comparand",
            f"LI(x{comparand}, {hex(VALUE_OLD)})   # comparand.lo matches the seeded value",
            f"LI(x{comparand + 1}, 0)                  # comparand.hi matches the seeded value",
            f"LI(x{replacement}, {hex(VALUE_NEW)})",
            f"LI(x{replacement + 1}, {hex(VALUE_NEW)})",
            test_data.add_testcase(bin_name, CP_MASKING, covergroup),
            f"{mnemonic} x{comparand}, x{replacement}, (x{addr})",
            f"ld x{comparand}, 0(x{base_reg})",
            f"ld x{comparand + 1}, 8(x{base_reg})",
            write_sigupd(comparand, test_data),
            write_sigupd(comparand + 1, test_data),
        ]
        test_data.int_regs.return_register_pair(comparand)
        test_data.int_regs.return_register_pair(replacement)
        test_data.int_regs.return_registers([base_reg, addr])
        return lines

    base_reg, addr, comparand, replacement = test_data.int_regs.get_registers(4)
    lines = [
        *_tagged_address(base_reg, addr, "pm_lo_page", upper_tag),
        *_seed(base_reg, comparand),
        f"LI(x{comparand}, {hex(VALUE_OLD)})   # comparand matches the seeded value",
        f"LI(x{replacement}, {hex(VALUE_NEW)})",
        test_data.add_testcase(bin_name, CP_MASKING, covergroup),
        f"{mnemonic} x{comparand}, x{replacement}, (x{addr})",
        f"ld x{comparand}, 0(x{base_reg})",
        write_sigupd(comparand, test_data),
    ]
    test_data.int_regs.return_registers([base_reg, addr, comparand, replacement])
    return lines


def _probe_cbo(mnemonic: str, upper_tag: int, bin_name: str, test_data: TestData, covergroup: str) -> list[str]:
    """Generate one cache-block operation probe.

    CBO.INVAL has no reliable readback, so only its trap signature is checked.
    """
    base_reg, addr, readback_reg = test_data.int_regs.get_registers(3)
    lines = [
        *_tagged_address(base_reg, addr, "pm_lo_page", upper_tag),
        *_seed(base_reg, readback_reg),
        test_data.add_testcase(bin_name, CP_MASKING, covergroup),
        f"{mnemonic} 0(x{addr})",
    ]
    if mnemonic != "cbo.inval":
        lines.extend([f"ld x{readback_reg}, 0(x{base_reg})", write_sigupd(readback_reg, test_data)])
    test_data.int_regs.return_registers([base_reg, addr, readback_reg])
    return lines


def _probe_vec(
    sew: int,
    instruction_template: str,
    readback_mnemonic: str | None,
    upper_tag: int,
    bin_name: str,
    test_data: TestData,
    covergroup: str,
) -> list[str]:
    """Generate a two-element vector load or store probe."""
    base_reg, addr, value = test_data.int_regs.get_registers(3)
    is_load = readback_mnemonic is None
    initial_value = SENTINEL if is_load else VALUE_NEW
    lines = [
        *_tagged_address(base_reg, addr, "pm_lo_page", upper_tag),
        *_seed(base_reg, value),
        f"LI(x{value}, {hex(initial_value)})",
        "csrw vstart, x0",
        f"vsetivli x0, 2, e{sew}, m1, ta, ma",
        "vmv.v.i v4, 0   # zero index vector: indexed probes address the base itself",
        f"vmv.v.x v2, x{value}",
        test_data.add_testcase(bin_name, CP_MASKING, covergroup),
        instruction_template.format(a=addr),
    ]
    if is_load:
        lines.extend([f"vmv.x.s x{value}, v2", "csrw vstart, x0"])
    else:
        lines.extend(["csrw vstart, x0", f"{readback_mnemonic} x{value}, 0(x{base_reg})"])
    lines.append(write_sigupd(value, test_data))
    test_data.int_regs.return_registers([base_reg, addr, value])
    return lines


# ── Common Test Generators ─────────────────────────────────────────────────


def generate_instruction_sweep_tests(
    prefix: str, test_data: TestData, cg: str, uppers: list[int] = UPPER_PATTERNS
) -> list[str]:
    """Exercise supported memory-access instructions through each tagged address pattern."""
    lines = []
    for upper in uppers:
        lines.append(comment_banner(f"{prefix} {CP_MASKING}: tag 0x{upper:04X} -- full instruction sweep"))
        for mn in READS:
            lines.extend(_probe_load(mn, upper, _binname(prefix, upper, mn), test_data, cg))
        for mn, rb in WRITES:
            lines.extend(_probe_store(mn, rb, upper, _binname(prefix, upper, mn), test_data, cg))

        amos = []
        for mn, rb in RV64A_AMOS:
            amos.extend(_probe_amo(mn, rb, upper, _binname(prefix, upper, mn), test_data, cg))
        zabha = []
        for mn, rb in ZABHA_AMOS:
            zabha.extend(_probe_amo(mn, rb, upper, _binname(prefix, upper, mn), test_data, cg))
        zacas = []
        for mn in ZACAS_AMOS:
            zacas.extend(_probe_zacas(mn, upper, _binname(prefix, upper, mn), test_data, cg))
        lines.extend(
            [
                *_ifdef("ZAAMO_SUPPORTED", amos),
                *_ifdef("ZABHA_SUPPORTED", zabha),
                *_ifdef("ZACAS_SUPPORTED", zacas),
            ]
        )

        for mn, guard in FP_READS:
            lines.extend(
                _ifdef(
                    guard,
                    [*_probe_load(mn, upper, _binname(prefix, upper, mn), test_data, cg, float_load=True)],
                )
            )
        for mn, rb, guard, mv in FP_WRITES:
            lines.extend(
                _ifdef(
                    guard,
                    [*_probe_store(mn, rb, upper, _binname(prefix, upper, mn), test_data, cg, fp_move_mnemonic=mv)],
                )
            )

        zca = ("zca",)
        zca_lines = []
        for mn in ZCA_READS_CL:
            zca_lines.extend(
                _probe_load(
                    mn,
                    upper,
                    _binname(prefix, upper, mn),
                    test_data,
                    cg,
                    compressed=True,
                    arch_extensions=zca,
                )
            )
        for mn, rb in ZCA_WRITES_CS:
            zca_lines.extend(
                _probe_store(
                    mn,
                    rb,
                    upper,
                    _binname(prefix, upper, mn),
                    test_data,
                    cg,
                    compressed=True,
                    arch_extensions=zca,
                )
            )
        for mn in ZCA_READS_SP:
            zca_lines.extend(
                _probe_load(
                    mn,
                    upper,
                    _binname(prefix, upper, mn),
                    test_data,
                    cg,
                    via_sp=True,
                    arch_extensions=zca,
                )
            )
        for mn, rb in ZCA_WRITES_SP:
            zca_lines.extend(
                _probe_store(
                    mn,
                    rb,
                    upper,
                    _binname(prefix, upper, mn),
                    test_data,
                    cg,
                    via_sp=True,
                    arch_extensions=zca,
                )
            )
        zcd_load = {"via_sp": True, "float_load": True, "arch_extensions": ("zca", "zcd")}
        zcd_store = {"via_sp": True, "fp_move_mnemonic": "fmv.d.x", "arch_extensions": ("zca", "zcd")}
        zca_lines.extend(
            _ifdef(
                "ZCD_SUPPORTED",
                [
                    *_probe_load("c.fldsp", upper, _binname(prefix, upper, "c.fldsp"), test_data, cg, **zcd_load),
                    *_probe_store(
                        "c.fsdsp", "ld", upper, _binname(prefix, upper, "c.fsdsp"), test_data, cg, **zcd_store
                    ),
                ],
            )
        )
        lines.extend(_ifdef("ZCA_SUPPORTED", zca_lines))

        for guard, ops in (("ZICBOZ", ["cbo.zero"]), ("ZICBOM", ZICBOM_OPS), ("ZICBOP", ZICBOP_OPS)):
            cbo = []
            for mn in ops:
                cbo.extend(_probe_cbo(mn, upper, _binname(prefix, upper, mn), test_data, cg))
            lines.extend(_ifdef(f"{guard}_SUPPORTED", cbo))

        # EEW <= 32 needs only Zve32x (ZVL32B marks any vector support); EEW = 64 needs Zve64x.
        for guard, wide in (("ZVL32B", False), ("ZVE64X", True)):
            vector = []
            for mn, sew, template in VEC_READS:
                if (sew > 32) == wide:
                    vector.extend(_probe_vec(sew, template, None, upper, _binname(prefix, upper, mn), test_data, cg))
            for mn, sew, template, rb in VEC_WRITES:
                if (sew > 32) == wide:
                    vector.extend(_probe_vec(sew, template, rb, upper, _binname(prefix, upper, mn), test_data, cg))
            lines.extend(_ifdef(f"{guard}_SUPPORTED", vector))

    return lines


def generate_zicfiss_tests(prefix: str, test_data: TestData, cg: str, uppers: list[int]) -> list[str]:
    """Exercise the Zicfiss shadow-stack instructions through each tagged address pattern.

    They access memory only below M-mode with S-mode implemented, shadow stacks enabled by set_sse,
    and SS_PAGE mapped as a shadow-stack page.
    """
    lines = []
    for upper in uppers:
        lines.append(comment_banner(f"{prefix} Zicfiss shadow-stack instructions: tag 0x{upper:04X}"))
        for mn, rb in ZICFISS_AMOS:
            lines.extend(_probe_ssamoswap(mn, rb, upper, _binname(prefix, upper, mn), test_data, cg))
        for push, forms in ((True, ZICFISS_PUSHES), (False, ZICFISS_POPS)):
            for mn, link, compressed in forms:
                bin_name = _binname(prefix, upper, f"{mn}_x{link}")
                lines.extend(_probe_ssp(mn, link, compressed, push, upper, bin_name, test_data, cg))
    return _ifdef("ZICFISS_SUPPORTED", lines) if lines else []


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
                    load,
                    upper,
                    _binname(prefix, upper, load),
                    test_data,
                    cg,
                    coverpoint=cp,
                    base_address=base,
                    offset=offset,
                ),
                *_probe_store(
                    store,
                    readback,
                    upper,
                    _binname(prefix, upper, store),
                    test_data,
                    cg,
                    coverpoint=cp,
                    base_address=base,
                    offset=offset,
                ),
            ]
        )
    return lines


def generate_misaligned_tests(prefix: str, test_data: TestData, cg: str) -> list[str]:
    """Check tagged word accesses with a misaligned effective address."""
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


def generate_edge_case_tests(
    prefix: str,
    test_data: TestData,
    cg: str,
    *,
    status_csr: str | None = None,
    status_guard: str | None = None,
    tsbi: bool = False,
) -> list[str]:
    """Generate the edge probes shared by the pointer-masking suites.

    ``status_csr`` adds the MXR probes. ``status_guard`` wraps them when the
    status CSR exists only with a supported lower privilege mode.
    """
    lines = [
        *generate_misaligned_tests(prefix, test_data, cg),
        *generate_jalr_tests(prefix, test_data, cg, mxr=0),
        *generate_fault_address_tests(prefix, test_data, cg),
    ]
    if status_csr is None:
        return lines

    mxr_lines = [
        *generate_mxr_tests(prefix, test_data, cg, status_csr, tsbi),
        *generate_jalr_tests(prefix, test_data, cg, mxr=1),
        *set_mxr(False, test_data, status_csr, tsbi),
    ]
    if status_guard is not None:
        lines.extend([f"#ifdef {status_guard}", *mxr_lines, f"#endif // {status_guard}"])
    else:
        lines.extend(mxr_lines)
    return lines


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
                f"LI(x{chk}, 0)",
                test_data.add_testcase(_binname(f"{prefix}_mxr{mxr}", upper, "jalr"), "cp_pmm_jalr", cg),
                f"jalr ra, 0(x{a})",
                write_sigupd(chk, test_data),
            ]
        )
    test_data.int_regs.return_registers([base, a, chk])
    return lines


def generate_fault_address_tests(prefix: str, test_data: TestData, cg: str) -> list[str]:
    """Check that masking also applies before the model access-fault address is used."""
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
    """Check that changing a lower mode to RV32 clears its PMM field.

    ``ifdef_guard`` skips the test when the lower mode cannot use RV32. The
    test runs from an unaffected higher mode because the lower mode cannot
    execute the remaining RV64 code or read CSR bits 33:32 through T-SBI.
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


# ── MPRV (Smmpm, SsnpmSm, SmnpmSSm, SmnpmUSm) ─────────────────────────────


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


def mprv_setup(test_data: TestData) -> list[str]:
    """Build the U-accessible Sv39 map and enable SUM for MPRV probes.

    MPP=U accesses need PTE_U on the data pages. SUM lets the setup code in
    S- or M-mode reach those pages.
    """
    return [
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
        "# mstatus.SUM = 1",
        *csr_op("csrs", "mstatus", "MSTATUS_SUM", test_data),
    ]


def mprv_teardown(test_data: TestData, *, sum_bit: bool, mxr: bool = True) -> list[str]:
    """Restore status bits after an MPRV sweep, including MPP=M.

    ``set_mprv(False)`` clears MPRV but does not restore MPP.
    """
    lines = set_mxr(False, test_data, "mstatus") if mxr else []
    if sum_bit:
        lines.extend(["# mstatus.SUM = 0", *csr_op("csrc", "mstatus", "MSTATUS_SUM", test_data)])
    lines.extend(
        [
            *set_mprv(False, test_data),
            "# restore mstatus.MPP = M; set_mprv(False, ...) only clears MPRV",
            *csr_op("csrs", "mstatus", "MSTATUS_MPP", test_data),
        ]
    )
    return lines


def generate_mprv_mpp_m_tests(test_data: TestData, cg: str) -> list[str]:
    """MPRV=1 with MPP=M: the effective privilege stays M, so mseccfg.PMM governs.

    This is the only MPRV case that belongs to Smmpm. satp is an S-mode register and
    plays no part when the effective privilege is M, so there is no satp loop here.
    """
    lines = [
        comment_banner(
            "Smmpm MPRV, MPP=M: the effective privilege is M, so mseccfg.PMM governs",
            "No satp loop: satp does not apply to M-mode accesses.",
        ),
        "",
    ]
    for mseccfg_pmm, mseccfg_pmlen, _ in PMM_CONFIGS:
        prefix = f"mprv_mseccfg{mseccfg_pmm:02b}_nosatp_mppm"
        lines.extend(
            [
                *set_pmm_field("mseccfg", mseccfg_pmm, mseccfg_pmlen, test_data),
                *_mprv_lw_sw_probe("PRV_M", "cp_pm_mprv_mpp_m", prefix, test_data, cg),
            ]
        )
    lines.extend([*set_pmm_field("mseccfg", 0b00, 0, test_data), *mprv_teardown(test_data, sum_bit=False)])
    return lines


def generate_mprv_lower_mode_tests(
    test_data: TestData,
    cg: str,
    *,
    mpp: str,
    pmm_csr: str,
    cp: str,
    s_mode: bool = True,
) -> list[str]:
    """MPRV=1 with MPP below M: the effective privilege is *mpp*, so the PMM field of
    that mode's envcfg -- *pmm_csr* -- governs, not mseccfg.PMM.

    mseccfg.PMM is swept alongside it (when Smmpm is implemented) precisely to show
    that it is ignored once the effective privilege drops below M. MXR and satp.MODE
    are swept because both apply at the effective privilege.

    *s_mode* False is the hart without S-mode (SmnpmUSm): MXR and SUM are read-only 0
    and there is no satp, so only Bare is swept and no page tables are built.
    """
    mpp_name = {"PRV_U": "mppu", "PRV_S": "mpps"}[mpp]
    lines = [
        comment_banner(
            f"MPRV, MPP={mpp_name[-1].upper()}: the effective privilege is {mpp_name[-1].upper()},"
            f" so {pmm_csr}.PMM governs",
            "mseccfg.PMM is swept with it to show it no longer applies.",
        ),
        "",
        *(mprv_setup(test_data) if s_mode else []),
    ]

    for mxr_val in [0, 1] if s_mode else [0]:
        if s_mode:
            lines.extend(set_mxr(mxr_val != 0, test_data, "mstatus"))

        # mseccfg.PMM only exists with Smmpm; without it the sweep collapses to one pass.
        for mseccfg_pmm, mseccfg_pmlen, _ in PMM_CONFIGS:
            lines.extend(_ifdef("SMMPM_SUPPORTED", set_pmm_field("mseccfg", mseccfg_pmm, mseccfg_pmlen, test_data)))

            for pmm, pmlen, _ in PMM_CONFIGS:
                lines.extend(set_pmm_field(pmm_csr, pmm, pmlen, test_data))

                for satp_mode in ["bare", "sv39"] if s_mode else ["bare"]:
                    cfg = f"mseccfg{mseccfg_pmm:02b}_{pmm_csr}{pmm:02b}"
                    prefix = f"mprv_mxr{mxr_val}_{cfg}_{satp_mode}_{mpp_name}" if s_mode else f"mprv_{cfg}_{mpp_name}"
                    probe = _mprv_lw_sw_probe(mpp, cp, prefix, test_data, cg)
                    if satp_mode != "bare":
                        probe = _ifdef(
                            "SV39_SUPPORTED", [SV39.satp_setup, "sfence.vma", *probe, "csrwi satp, 0", "sfence.vma"]
                        )
                    lines.extend(probe)

    lines.extend(
        [
            *_ifdef("SMMPM_SUPPORTED", set_pmm_field("mseccfg", 0b00, 0, test_data)),
            *set_pmm_field(pmm_csr, 0b00, 0, test_data),
            *mprv_teardown(test_data, sum_bit=s_mode, mxr=s_mode),
        ]
    )
    return lines
