##################################
# priv/extensions/SsnpmH.py
#
# Ssnpm H group: pointer masking tests for VS-mode, VU-mode and the hypervisor load/store instructions.
# David_Harris@hmc.edu 29 September 2026
# Marco Bartoli marco.bartoli.dev@gmail.com 10 November 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Ssnpm H group test generator (testplans/priv/Ssnpm_H.yaml).

The group boots to HS-mode.  Guest accesses run in VS-mode or VU-mode, entered through T-SBI, and HLV, HSV and HLVX
run in HS-mode or in U-mode with hstatus.HU = 1.  Where a case makes several accesses in one mode, they and their
checks run in one T-SBI entry (_stint); otherwise each access runs alone and is checked back in HS-mode.  henvcfg.PMM
masks VS-mode, senvcfg.PMM masks VU-mode, and an HLV or HSV takes henvcfg.PMM with hstatus.SPVP = 1, and senvcfg.PMM
from HS-mode or hstatus.HUPMM from U-mode with SPVP = 0.  The PMM fields a case does not test hold a different
value: the largest one their extension supports when the field under test is 00, else 00.  menvcfg.PMM and
mseccfg.PMM take a T-SBI call, which HS-mode skips when the value does not change.  HLVX and accesses with MXR in
effect are never masked, and those cases enable every field.

The test page pm_lo_page is identity mapped in both stages, so a tag that masking clears reaches it.  A tag that
masking keeps is non-canonical or unmapped in the VS stage when vsatp is paged, and wider than the G stage or unmapped
in it when hgatp is paged, so the access faults, except where a case maps it to pm_gpa_alias_page on purpose: the
HFENCE cases in the G stage and the no-HFENCE case with vsatp = Sv57 in the VS stage.  With (vsatp, hgatp) =
(Bare, Bare) a kept tag is a physical address bit, and the address faults only when its highest kept bit is at or
above the physical address width, at most 56 bits.  So tag 0x0002 (bit 49), when masking keeps it, is used there only
with a physical address of at most 49 bits.

pm_lo_page has bits 47 and 56 clear, where sign extension (vsatp paged) and zero extension (vsatp = Bare) of the
masked bits give the same address.  So cp_vs_pmm, cp_vu_pmm and the HLV cases also reach it through an address with
bit 63 - PMLEN set, which only the right extension leaves mapped: _HIGH_VA in a paged VS stage, and _UPPER_GPA in a
G stage wide enough to hold it.  Their *_upper coverpoints sample these accesses.

Each supported (vsatp, hgatp) pair has a file with cp_vs_pmm, cp_vu_pmm and the cases tied to that pair.  The other
coverpoints use BARE_PAIR and PAGED_PAIR, the widest supported pairs with vsatp = Bare and with vsatp paged, which
the files pick with the preprocessor exactly as pair_chosen does.  Those files are split by the PMM value under test.
BARE_PAIR exists only when vsatp = Bare is supported and PAGED_PAIR only with a paged pair, so the VS-mode writers of
cp_vu_pmm_writer_vs and cp_pmm_vsuxl_clear run on both.  hgatp = Bare is optional when an x4 mode is supported, and
BARE_PAIR uses it only without one.

The test image must lie below 255 GiB, so that it is outside the root entries of _SPARE_VA and _GPF_GPA.  The
access-fault cases identity map RVMODEL_ACCESS_FAULT_ADDRESS_* and run only where it fits (_fault_fits).
"""

from collections.abc import Callable
from dataclasses import dataclass
from itertools import groupby
from typing import NamedTuple

from testgen.asm.helpers import arch_block, comment_banner, gated, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.sv.generate import guest_translation_setup, guest_translation_teardown, identity_map_image
from testgen.priv.extensions.sv.page_tables import (
    SV39X4,
    SV48X4,
    SV57X4,
    VS_SV39,
    VS_SV48,
    VS_SV57,
    PteFlags,
    SvMode,
    create_page_mapping,
    lower_table_data,
    write_pte,
)
from testgen.priv.extensions.ZpmCommon import (
    PMM_CONFIGS,
    SENTINEL,
    VALUE_NEW,
    VALUE_OLD,
    HeldAddress,
    csr_op,
    data_page,
    pmm_ifdef,
    probe_amo,
    probe_cbo,
    probe_load,
    probe_store,
    probe_vec,
    probe_zacas,
    set_pmm_field,
    set_sse,
)
from testgen.priv.registry import add_priv_test_generator

_CG = "Ssnpm_H_cg"
_BOOT = ["#define BOOT_TO_SMODE"]
_EXTENSIONS: list[str | list[str]] = ["H", "Ssnpm"]
_MARCH = ["I", "A", "F", "D", "V", "H", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz", "Zicfiss"]
# VS-mode, VU-mode and the HLV and HSV accesses run as RV64
_XLEN64 = ["VSXLEN: 64", "VUXLEN: 64"]

# Bits 63:48 of the address (tag5, tag3), and the untagged control with the tags each PMLEN masks in full (pmm_tag_h)
_TAGS = (0x0000, 0x0002, 0x0400, 0xFF00, 0xFFFF)
_SWEEP_TAGS = (0x0000, 0x0400, 0xFFFF)
_FULL_TAGS = {0b10: (0x0000, 0x0400), 0b11: (0x0000, 0xFFFF)}
_PMLEN = {0b00: 0, 0b10: 7, 0b11: 16}
# (vsstatus.MXR, sstatus.MXR) with MXR in effect (mxr_pair)
_MXR = ((0, 1), (1, 0), (1, 1))

_ALIAS = "pm_gpa_alias_page"
_VALUE_ALIAS = 0x5A5A_A11A_5A5A_A11A
_SS_PAGE = "pm_ss_page"
_IMAGE = ("rvtest_code_begin", "rvtest_data_begin", "rvtest_sig_end")
# An upper-half guest virtual address, which masking with either PMLEN leaves unchanged, in a VS-stage root entry of
# its own.  cp_vs_gstage_no_pmm and the upper-half probes of a paged VS stage map it.
_HIGH_VA = 0xFFFF_FFFF_C000_0000
# For vsatp = Bare, a guest physical address with bit 63 - PMLEN set for each PMM, which the G stage maps to pm_lo_page
# for the upper-half probes.  Under a split Sv57x4 root, the level-3 index of the PMLEN 16 one, 0x100, is not the test
# image's.
_UPPER_GPA = {0b10: 0x0140_8000_0000_0000, 0b11: 0x0000_8000_0000_0000}
# The tags of the upper-half probes: one keeps bits 63:48, the other flips every bit that masking replaces
_UPPER_TAGS = {0b10: (0x0000, 0xFE00), 0b11: (0x0000, 0xFFFF)}
# A guest physical address inside every G-stage width that the G stage never maps: its Sv39x4 and Sv48x4 root entries
# (0x5FF, 2) and, once _split_root splits the test image's Sv57x4 root entry, its level-3 entry (2) hold no mapping.
# Bits 63:47 are zero, so masking leaves it unchanged and its tags are the tag bins.
_GPF_GPA = 0x17F_C000_0000
# A guest virtual address of each VS-stage mode with bits 63:47 zero, which a root superpage maps to _GPF_GPA for
# Sv39 and Sv48 (root entry 0xFF).  For Sv57 it is in the test image's root entry, whose identity map reaches
# _GPF_GPA, and _split_root makes its level-3 entry free.  It holds the shadow stack page.
_SPARE_VA = {"sv39": 0x3F_C000_0000, "sv48": 0x7FFF_C000_0000, "sv57": _GPF_GPA}

_FIELDS = ("henvcfg", "senvcfg", "hstatus")  # hstatus is HUPMM
_M_FIELDS = (("menvcfg", "SMNPM"), ("mseccfg", "SMMPM"))
# HS-mode keeps the last value written to menvcfg.PMM and mseccfg.PMM here, -1 before the first write
_M_SHADOW = "ssnpmh_m_pmm"


@dataclass(frozen=True)
class _Pair:
    """A (vsatp.MODE, hgatp.MODE) pair, None for Bare."""

    vs: SvMode | None
    g: SvMode | None

    @property
    def name(self) -> str:
        return f"{self.vs.name if self.vs else 'bare'}_{self.g.name if self.g else 'bare'}"

    @property
    def params(self) -> list[str]:
        vs = f"{self.vs.name.upper()}_VSMODE_TRANSLATION: true" if self.vs else "VSSTAGE_MODE_BARE: true"
        g = f"{self.g.name.upper()}_TRANSLATION: true" if self.g else "GSTAGE_MODE_BARE: true"
        return [vs, g, *_XLEN64]


_BARE_BARE = _Pair(None, None)
_BARE_SV39X4 = _Pair(None, SV39X4)
_BARE_SV48X4 = _Pair(None, SV48X4)
_BARE_SV57X4 = _Pair(None, SV57X4)
_SV39_SV39X4 = _Pair(VS_SV39, SV39X4)
_SV48_SV48X4 = _Pair(VS_SV48, SV48X4)
_SV57_SV57X4 = _Pair(VS_SV57, SV57X4)

# BARE_PAIR and PAGED_PAIR: (macro, [(hgatp.MODE, pair)]) in the order pair_chosen prefers them.  The macro holds
# hgatp.MODE of the chosen pair, and 0 for (Bare, Bare) or no paged pair.  BARE_PAIR is used only with vsatp = Bare.
_ROLES = {
    "bare": ("SSNPMH_BARE_PAIR", ((10, _BARE_SV57X4), (9, _BARE_SV48X4), (8, _BARE_SV39X4), (0, _BARE_BARE))),
    "paged": ("SSNPMH_PAGED_PAIR", ((10, _SV57_SV57X4), (9, _SV48_SV48X4), (8, _SV39_SV39X4))),
}
_Target = _Pair | str  # a pair, or "bare" or "paged" for BARE_PAIR or PAGED_PAIR


def _support(pair: _Pair) -> str:
    """The preprocessor condition for pair's modes."""
    return " && ".join(
        f"defined(UDB_{mode.name.upper()}{'_VSMODE' if mode.stage == 'vs' else ''}_TRANSLATION)"
        for mode in (pair.vs, pair.g)
        if mode is not None
    )


def _role_defines() -> list[str]:
    lines = ["// BARE_PAIR and PAGED_PAIR: hgatp.MODE of the widest supported pairs, as in pair_chosen"]
    for macro, candidates in _ROLES.values():
        for index, (value, pair) in enumerate(candidates):
            lines.append(f"{'#if' if index == 0 else '#elif'} {_support(pair)}" if pair.g else "#else")
            lines.append(f"#define {macro} {value}")
        if macro == "SSNPMH_PAGED_PAIR":
            lines.extend(["#else", f"#define {macro} 0"])
        lines.append("#endif")
    return lines


def _on_defines(ext: str) -> list[str]:
    return [
        f"#if defined(UDB_SUPPORTED_PMLEN_{ext}_16)",
        f"#define SSNPMH_{ext}_ON 3",
        f"#elif defined(UDB_SUPPORTED_PMLEN_{ext}_7)",
        f"#define SSNPMH_{ext}_ON 2",
        "#else",
        f"#define SSNPMH_{ext}_ON 0",
        "#endif",
    ]


_DEFINES = [
    *_role_defines(),
    "// _SPARE_VA of the VS-stage mode of PAGED_PAIR",
    "#if SSNPMH_PAGED_PAIR == 8",
    f"#define SSNPMH_SPARE_VA {_SPARE_VA['sv39']:#x}",
    "#elif SSNPMH_PAGED_PAIR == 9",
    f"#define SSNPMH_SPARE_VA {_SPARE_VA['sv48']:#x}",
    "#else",
    f"#define SSNPMH_SPARE_VA {_SPARE_VA['sv57']:#x}",
    "#endif",
    "// The largest PMM each extension supports (00 if only PMLEN 0), which the fields not under test hold when the",
    "// tested one is 00",
    *_on_defines("SSNPM"),
    *_on_defines("SMNPM"),
    *_on_defines("SMMPM"),
]
# A chunk that does not start a file uses the defines of the one that does
_NEED_DEFINES = [
    "#ifndef SSNPMH_BARE_PAIR",
    '#error "Ssnpm H: the SSNPMH_* defines must come from the first chunk of the file"',
    "#endif",
]


# ── Translation ────────────────────────────────────────────────────────────


def _setup(test_data: TestData, pair: _Pair, user: bool) -> list[str]:
    """Turn on pair's translation with the test image identity mapped in both stages.

    user sets PTE.U in the VS-stage leaves, for VU-mode and for HLV, HSV and HLVX as VU (hstatus.SPVP = 0).
    """
    if pair.vs is None and pair.g is None:
        return ["csrw hgatp, zero", "csrw vsatp, zero", "hfence.gvma", "hfence.vvma"]
    lines = guest_translation_setup(test_data, pair.g, pair.vs, "VUmode" if user else "VSmode")
    if user and pair.vs is not None:
        pte, addr, tmp = test_data.int_regs.get_registers(3)
        lines.extend(
            [
                "// User VS-stage leaves for the test image",
                *identity_map_image(((pair.vs, PteFlags(user=True)),), (pte, addr, tmp)),
                "hfence.vvma",
            ]
        )
        test_data.int_regs.return_registers([pte, addr, tmp])
    return lines


def _split_root(test_data: TestData, mode: SvMode, flags: PteFlags) -> list[str]:
    """Map the test image with leaves one level below mode's root, so that the rest of its root entry can map other
    pages.  Sv57 and Sv57x4 need it for an address below 2^48 outside the image.  _map_image undoes it."""
    pte, addr, tmp = test_data.int_regs.get_registers(3)
    regs = (pte, addr, tmp)
    level = mode.levels - 2
    lines = identity_map_image(((mode, flags),), regs, level=level)
    for label in _IMAGE:
        lines.extend(
            write_pte(
                mode,
                level=level + 1,
                flags=PteFlags.nonleaf(),
                virtual_address=label,
                physical_address=mode.page_table_label(level),
                regs=regs,
                va_is_label=True,
            )
        )
    test_data.int_regs.return_registers([pte, addr, tmp])
    return lines


def _map_image(test_data: TestData, *stages: tuple[SvMode | None, PteFlags]) -> list[str]:
    """Map the test image at the root of each (mode, leaf flags) again, as _setup leaves it.  This undoes _split_root
    and restores a root entry that a removed mapping shared with the image."""
    pte, addr, tmp = test_data.int_regs.get_registers(3)
    lines = identity_map_image(stages, (pte, addr, tmp))
    test_data.int_regs.return_registers([pte, addr, tmp])
    return lines


def _needs_split(mode: SvMode) -> bool:
    """A root entry of mode spans 2^48 bytes, so the test image's holds every address below 2^48."""
    return mode.page_offset_bits(mode.levels - 1) >= 48


def _per_pair(
    target: _Target, build: Callable[[_Pair], list[str]], keep: Callable[[_Pair], bool] = lambda _: True
) -> list[str]:
    """build(pair) for a pair, or for BARE_PAIR or PAGED_PAIR an #if branch on its macro for each candidate pair that
    keep accepts."""
    if isinstance(target, _Pair):
        return build(target) if keep(target) else []
    macro, candidates = _ROLES[target]
    lines = []
    for value, pair in candidates:
        if keep(pair):
            lines.extend([f"{'#elif' if lines else '#if'} {macro} == {value}", *build(pair)])
    return [*lines, f"#endif // {macro}"] if lines else []


def _on(
    test_data: TestData, target: _Target, user: bool, extra: Callable[[_Pair], list[str]] | None = None
) -> list[str]:
    """Turn on the translation of target, choosing BARE_PAIR or PAGED_PAIR with the preprocessor, then add extra."""
    return _per_pair(target, lambda pair: [*_setup(test_data, pair, user), *(extra(pair) if extra else [])])


def _wrap(target: _Target, lines: list[str]) -> list[str]:
    """Run lines only when target exists: BARE_PAIR needs vsatp = Bare, and PAGED_PAIR a paged pair."""
    if target == "bare":
        return gated(lines, "defined(UDB_VSSTAGE_MODE_BARE)")
    return gated(lines, "SSNPMH_PAGED_PAIR") if target == "paged" else lines


def _name(target: _Target) -> str:
    return target.name if isinstance(target, _Pair) else f"{target}_pair"


def _tag_gate(target: _Target, tag: int, pmlen: int) -> str | None:
    """The condition for using tag with (vsatp, hgatp) = (Bare, Bare), where it is a physical address.

    The highest bit that masking with pmlen keeps must be at or above the physical address width, so that the address
    faults instead of reaching memory.  An RV64 physical address has at most 56 bits, so a bit from 56 up always is.
    """
    if target not in (_BARE_BARE, "bare"):
        return None
    top = ((tag << 48) & ((1 << (64 - pmlen)) - 1)).bit_length() - 1
    if not 0 <= top < 56:
        return None
    gate = f"UDB_PHYS_ADDR_WIDTH <= {top}"
    return gate if target == _BARE_BARE else f"SSNPMH_BARE_PAIR != 0 || {gate}"


def _map_page(test_data: TestData, mode: SvMode, va: int, pa: int, flags: PteFlags) -> list[str]:
    """Map the 4 KiB page at the address in x{va} to the one in x{pa} through mode's tables below the root."""
    pte, slot, tmp = test_data.int_regs.get_registers(3)
    lines = create_page_mapping(mode, leaf_level=0, leaf_flags=flags, regs=(pte, slot, tmp), va_reg=va, pa_reg=pa)
    test_data.int_regs.return_registers([pte, slot, tmp])
    return lines


def _unmap(test_data: TestData, mode: SvMode, va: int, level: int | None = None) -> list[str]:
    """Clear the PTE at level (default: the root) of mode's tables that maps the address in x{va}."""
    level = mode.levels - 1 if level is None else level
    slot, tmp = test_data.int_regs.get_registers(2)
    top = mode.xlen - mode.index_bits(level)
    lines = [
        f"srli x{slot}, x{va}, {mode.page_offset_bits(level)}",
        f"slli x{slot}, x{slot}, {top}",
        f"srli x{slot}, x{slot}, {top - 3}",
        f"LA(x{tmp}, {mode.page_table_label(level)})",
        f"add x{slot}, x{slot}, x{tmp}",
        f"SREG x0, 0(x{slot})",
    ]
    test_data.int_regs.return_registers([slot, tmp])
    return lines


def _tagged_lo_page(reg: int, tmp: int, tag: int) -> list[str]:
    """x{reg} = pm_lo_page with bits 63:48 = tag."""
    return [f"LA(x{reg}, pm_lo_page)", f"LI(x{tmp}, {tag << 48:#x})", f"or x{reg}, x{reg}, x{tmp}"]


def _alias_tags(test_data: TestData, mode: SvMode, tags: tuple[int, ...], flags: PteFlags, unmap: bool) -> list[str]:
    """Map pm_lo_page tagged with each of tags to the alias page in mode's stage, or unmap it.

    The tags differ only in the root index, so the mappings share the tables below the root.
    """
    va, pa = test_data.int_regs.get_registers(2)
    lines = []
    for tag in tags:
        lines.extend(_tagged_lo_page(va, pa, tag))
        if unmap:
            lines.extend(_unmap(test_data, mode, va))
        else:
            lines.extend([f"LA(x{pa}, {_ALIAS})", *_map_page(test_data, mode, va, pa, flags)])
    test_data.int_regs.return_registers([va, pa])
    return [*lines, "hfence.gvma", "hfence.vvma"]


def _check_alias(test_data: TestData) -> list[str]:
    """Record the alias page, then restore it."""
    addr, value = test_data.int_regs.get_registers(2)
    lines = [
        f"LA(x{addr}, {_ALIAS})",
        f"ld x{value}, 0(x{addr})",
        write_sigupd(value, test_data),
        f"LI(x{value}, {_VALUE_ALIAS:#x})",
        f"sd x{value}, 0(x{addr})",
    ]
    test_data.int_regs.return_registers([addr, value])
    return lines


# ── CSR fields ─────────────────────────────────────────────────────────────


def _m_field(test_data: TestData, csr: str, ext: str, value: int | str, gate: str = "") -> list[str]:
    """Write menvcfg.PMM or mseccfg.PMM through T-SBI when the extension that has it is implemented.  Each T-SBI call
    is costly and the value often does not change, so HS-mode skips the write when _M_SHADOW holds the same value."""
    pmlen = None if isinstance(value, str) else _PMLEN[value]
    offset = 8 * [field for field, _ in _M_FIELDS].index(csr)
    shadow, old, new = test_data.int_regs.get_registers(3)
    check = [
        f"LA(x{shadow}, {_M_SHADOW})",
        f"ld x{old}, {offset}(x{shadow})",
        f"LI(x{new}, {value})",
        f"beq x{old}, x{new}, 1f   # {csr}.PMM already holds the value",
        f"sd x{new}, {offset}(x{shadow})",
    ]
    test_data.int_regs.return_registers([shadow, old, new])
    write = set_pmm_field(csr, value, pmlen, test_data, tsbi=True)
    return gated([*check, *write, "1:"], f"defined({ext}_SUPPORTED){gate}")


def _pmm_case(test_data: TestData, field: str, pmm: int, value: int | str | None = None) -> list[str]:
    """field = pmm, or value when given.  The other PMM fields hold the largest value their extension supports when
    pmm is 00, else 00."""
    value = pmm if value is None else value
    lines = set_pmm_field(field, value, _PMLEN[value] if isinstance(value, int) else None, test_data)
    for other in _FIELDS:
        if other != field:
            lines.extend(
                set_pmm_field(other, 0, 0, test_data)
                if pmm
                else set_pmm_field(other, "SSNPMH_SSNPM_ON", None, test_data)
            )
    for csr, ext in _M_FIELDS:
        lines.extend(_m_field(test_data, csr, ext, 0 if pmm else f"SSNPMH_{ext}_ON"))
    return [*lines, "hfence.gvma", "hfence.vvma"]


def _all_pmm(test_data: TestData, pmm: int) -> list[str]:
    """Every PMM field = pmm, menvcfg.PMM and mseccfg.PMM only when their extension supports its PMLEN."""
    pmlen = _PMLEN[pmm]
    lines = [line for field in _FIELDS for line in set_pmm_field(field, pmm, pmlen, test_data)]
    for csr, ext in _M_FIELDS:
        lines.extend(_m_field(test_data, csr, ext, pmm, f" && defined(UDB_SUPPORTED_PMLEN_{ext}_{pmlen})"))
    return [*lines, "hfence.gvma", "hfence.vvma"]


def _clear_pmm(test_data: TestData) -> list[str]:
    lines = [line for field in _FIELDS for line in set_pmm_field(field, 0, 0, test_data)]
    for csr, ext in _M_FIELDS:
        lines.extend(_m_field(test_data, csr, ext, 0))
    return [*lines, "hfence.gvma", "hfence.vvma"]


def _csrw_field(test_data: TestData, csr: str, mask: str, value: int, label: str | None = None) -> list[str]:
    """Write the field mask of csr with value (in position) by a csrw, which label marks."""
    reg, tmp = test_data.int_regs.get_registers(2)
    lines = [
        f"csrr x{reg}, {csr}",
        f"LI(x{tmp}, {mask})",
        f"not x{tmp}, x{tmp}",
        f"and x{reg}, x{reg}, x{tmp}",
        f"LI(x{tmp}, {value:#x})",
        f"or x{reg}, x{reg}, x{tmp}",
        *([label] if label else []),
        f"csrw {csr}, x{reg}",
    ]
    test_data.int_regs.return_registers([reg, tmp])
    return lines


def _hstatus(test_data: TestData, spvp: int, hu: int) -> list[str]:
    return [
        *csr_op("csrs" if spvp else "csrc", "hstatus", "HSTATUS_SPVP", test_data),
        *csr_op("csrs" if hu else "csrc", "hstatus", "HSTATUS_HU", test_data),
    ]


def _mxr(test_data: TestData, vs_mxr: int, s_mxr: int) -> list[str]:
    return [
        *csr_op("csrs" if vs_mxr else "csrc", "vsstatus", "SSTATUS_MXR", test_data),
        *csr_op("csrs" if s_mxr else "csrc", "sstatus", "SSTATUS_MXR", test_data),
    ]


# ── Probes ─────────────────────────────────────────────────────────────────


def _stint(test_data: TestData, mode: str, build: Callable[[str | HeldAddress], list[str]]) -> list[str]:
    """build's lines, given the address of pm_lo_page, run in mode (VS, VU or U) in one T-SBI entry, or in place in
    HS-mode.  A fault traps to HS-mode, which records it and resumes at the next instruction in mode.  Code in mode runs
    at the code alias, so HS-mode loads pm_lo_page into a register for it."""
    if mode == "HS":
        return build("pm_lo_page")
    held = test_data.int_regs.get_register()
    lines = build(HeldAddress(held))
    test_data.int_regs.return_register(held)
    if not lines:
        return []
    return [f"LA(x{held}, pm_lo_page)", f"RVTEST_TSBI_GOTO_{mode}MODE", *lines, "RVTEST_TSBI_GOTO_SMODE"]


def _probe(
    test_data: TestData,
    cp: str,
    name: str,
    op: str,
    tag: int,
    mode: str,
    offset: int = 0,
    base: str | HeldAddress = "pm_lo_page",
) -> list[str]:
    """op at base + offset tagged with tag, run in mode (VS, VU or U) and checked in HS-mode, or in place when mode
    is HS."""
    run = None if mode == "HS" else mode
    if op in ("sd", "sw", "hsv.d"):
        return probe_store(
            op, "ld", tag, name, test_data, _CG, coverpoint=cp, base_address=base, offset=offset, mode=run
        )
    return probe_load(op, tag, name, test_data, _CG, coverpoint=cp, base_address=base, offset=offset, mode=run)


def _tag_probes(
    test_data: TestData,
    target: _Target,
    cp: str,
    prefix: str,
    ops: tuple[str, ...],
    tags: tuple[int, ...],
    mode: str,
    pmlen: int,
) -> list[str]:
    """Each op at pm_lo_page with each tag, which masking with pmlen keeps or clears, in one stint in mode."""

    def build(base: str | HeldAddress) -> list[str]:
        lines = []
        for tag in tags:
            probes = [
                line
                for op in ops
                for line in _probe(test_data, cp, f"{prefix}_{op}_t{tag:04x}", op, tag, "HS", base=base)
            ]
            lines.extend(gated(probes, _tag_gate(target, tag, pmlen)))
        return lines

    return _stint(test_data, mode, build)


def _guest_op(test_data: TestData, cp: str, name: str, mode: str, op: str, addr: int) -> list[str]:
    """A ld (checked in HS-mode) or a sd of VALUE_NEW in mode at the address in x{addr}."""
    data = test_data.int_regs.get_register()
    lines = [
        f"LI(x{data}, {SENTINEL if op == 'ld' else VALUE_NEW:#x})",
        f"RVTEST_TSBI_GOTO_{mode}MODE",
        test_data.add_testcase(name, cp, _CG),
        f"{op} x{data}, 0(x{addr})",
        "RVTEST_TSBI_GOTO_SMODE",
    ]
    if op == "ld":
        lines.append(write_sigupd(data, test_data))
    test_data.int_regs.return_register(data)
    return lines


# ── Upper-half addresses ───────────────────────────────────────────────────


def _upper_ok(pair: _Pair, pmm: int) -> bool:
    """Whether pair has an upper-half address for pmm: _HIGH_VA in a paged VS stage, else _UPPER_GPA[pmm] when the G
    stage is wide enough to hold it."""
    if pair.vs is not None:
        return True
    return pair.g is not None and _UPPER_GPA[pmm] >> pair.g.va_bits == 0


def _page_map(
    test_data: TestData, mode: SvMode, address: int, page: str, flags: PteFlags, image: PteFlags, unmap: bool
) -> list[str]:
    """Map the 4 KiB page at address in mode's stage to page, or unmap it.  Under Sv57 and Sv57x4 an address below 2^48
    is in the test image's root entry, which _split_root splits first, with the image's leaf flags; unmapping clears
    the entry below the root and maps the image at the root again."""
    inside = _needs_split(mode) and address >> 48 == 0
    lines = _split_root(test_data, mode, image) if inside and not unmap else []
    va = test_data.int_regs.get_register()
    lines.append(f"LI(x{va}, {address:#x})")
    if unmap:
        lines.extend(_unmap(test_data, mode, va, mode.levels - 2 if inside else None))
        if inside:
            lines.extend(_map_image(test_data, (mode, image)))
    else:
        pa = test_data.int_regs.get_register()
        lines.extend([f"LA(x{pa}, {page})", *_map_page(test_data, mode, va, pa, flags)])
        test_data.int_regs.return_register(pa)
    test_data.int_regs.return_register(va)
    return lines


def _upper_map(test_data: TestData, pair: _Pair, pmm: int, user: bool, unmap: bool) -> list[str]:
    """Map pair's upper-half address for pmm to pm_lo_page, or unmap it."""
    if pair.vs is not None:
        mode, address, flags = pair.vs, _HIGH_VA, PteFlags(user=user)
    else:
        assert pair.g is not None
        mode, address, flags = pair.g, _UPPER_GPA[pmm], PteFlags(user=True)
    return [*_page_map(test_data, mode, address, "pm_lo_page", flags, flags, unmap), "hfence.gvma", "hfence.vvma"]


def _upper_probe(test_data: TestData, cp: str, name: str, op: str, address: int, base: str | HeldAddress) -> list[str]:
    """op at address, an upper-half address that masking turns into one mapped to pm_lo_page, which the probe seeds and
    checks through base, its identity-mapped address."""
    phys, addr, data = test_data.int_regs.get_registers(3)
    store = op in ("sd", "hsv.d")
    lines = [
        f"mv x{phys}, x{base.reg}" if isinstance(base, HeldAddress) else f"LA(x{phys}, {base})",
        f"LI(x{data}, {VALUE_OLD:#x})",
        f"sd x{data}, 0(x{phys})",
        f"LI(x{addr}, {address:#x})",
        f"LI(x{data}, {VALUE_NEW if store else SENTINEL:#x})",
        test_data.add_testcase(name, cp, _CG),
        f"{op} x{data}, 0(x{addr})",
        *([f"ld x{data}, 0(x{phys})"] if store else []),
        write_sigupd(data, test_data),
    ]
    test_data.int_regs.return_registers([phys, addr, data])
    return lines


def _upper(
    test_data: TestData, target: _Target, cp: str, prefix: str, ops: tuple[str, ...], pmm: int, mode: str, user: bool
) -> list[str]:
    """Each op at target's upper-half address for pmm with bits 63:48 XORed with each _UPPER_TAGS tag, where target
    has one, for {cp}_upper.  Masking reaches pm_lo_page only by sign-extending a guest virtual address and
    zero-extending a guest physical one, so these accesses fail with the wrong extension, which pm_lo_page itself does
    not show."""
    if pmm not in _UPPER_TAGS:
        return []

    def keep(pair: _Pair) -> bool:
        return _upper_ok(pair, pmm)

    def build(unmap: bool) -> list[str]:
        return _per_pair(target, lambda pair: _upper_map(test_data, pair, pmm, user, unmap), keep)

    maps = build(unmap=False)
    if not maps:
        return []
    paged = target == "paged" or (isinstance(target, _Pair) and target.vs is not None)
    base = _HIGH_VA if paged else _UPPER_GPA[pmm]
    probes = _stint(
        test_data,
        mode,
        lambda held: [
            line
            for op in ops
            for tag in _UPPER_TAGS[pmm]
            for line in _upper_probe(
                test_data, f"{cp}_upper", f"{prefix}_{op}_t{tag:04x}", op, base ^ (tag << 48), held
            )
        ],
    )
    gate = None
    if isinstance(target, str):
        macro, candidates = _ROLES[target]
        values = [value for value, pair in candidates if keep(pair)]
        gate = None if len(values) == len(candidates) else " || ".join(f"{macro} == {value}" for value in values)
    return gated([*maps, *probes, *build(unmap=True)], gate)


# ── cp_vs_pmm, cp_vu_pmm and the cases tied to one pair ───────────────────


def _ldsd(test_data: TestData, pair: _Pair, mode: str) -> list[str]:
    field, cp = ("henvcfg", "cp_vs_pmm") if mode == "VS" else ("senvcfg", "cp_vu_pmm")
    user = mode == "VU"
    lines = [
        comment_banner(f"{cp}: ld and sd in {mode}-mode for each {field}.PMM"),
        *_setup(test_data, pair, user),
    ]
    for pmm, pmlen, label in PMM_CONFIGS:
        prefix = f"{pair.name}_{label}"
        body = [
            *_pmm_case(test_data, field, pmm),
            *_tag_probes(test_data, pair, cp, prefix, ("ld", "sd"), _TAGS, mode, pmlen),
            *_upper(test_data, pair, cp, prefix, ("ld", "sd"), pmm, mode, user),
        ]
        lines.extend(pmm_ifdef(field, pmlen, body))
    return [*lines, *_clear_pmm(test_data), *guest_translation_teardown(test_data)]


def _writer_vs(test_data: TestData, target: _Target, pmm: int) -> list[str]:
    """cp_vu_pmm_writer_vs: VS-mode writes senvcfg.PMM = pmm, a value HS-mode did not set, and VU-mode follows it.
    VS-mode cannot execute the user pages that VU-mode needs, so HS-mode sets PTE.U in a paged VS stage after the
    write."""
    label = f"pmm{pmm:02b}"
    check = test_data.int_regs.get_register()
    body = [
        comment_banner(f"cp_vu_pmm_writer_vs: senvcfg PMM {pmm:02b}, {_name(target)}"),
        *_on(test_data, target, user=False),
        *_pmm_case(test_data, "senvcfg", pmm, value=0 if pmm else "SSNPMH_SSNPM_ON"),
        "RVTEST_TSBI_GOTO_VSMODE",
        *_csrw_field(
            test_data,
            "senvcfg",
            "SENVCFG_PMM",
            pmm << 32,
            test_data.add_testcase(f"vs_{_name(target)}_{label}", "cp_vu_pmm_writer_vs", _CG),
        ),
        f"csrr x{check}, senvcfg",
        "RVTEST_TSBI_GOTO_SMODE",
        write_sigupd(check, test_data),
        "hfence.gvma",
        "hfence.vvma",
        *_per_pair(target, lambda pair: _setup(test_data, pair, user=True), lambda pair: pair.vs is not None),
    ]
    test_data.int_regs.return_register(check)
    prefix = f"{_name(target)}_vs_writer_{label}"
    body.extend(_tag_probes(test_data, target, "cp_vu_pmm", prefix, ("ld", "sd"), (0x0400,), "VU", _PMLEN[pmm]))
    return [*_wrap(target, [*body, *guest_translation_teardown(test_data)]), *_clear_pmm(test_data)]


# hgatp: (coverpoint suffix, [(old PMM, new PMM, tags)]) of cp_henvcfg_pmm_change_hfence and cp_hupmm_change_hfence
_HFENCE = {
    "sv57x4": (
        "",
        (
            (0b00, 0b10, (0x0400,)),
            (0b10, 0b00, (0x0400,)),
            (0b00, 0b11, (0x0002, 0x0400)),
            (0b11, 0b00, (0x0002, 0x0400)),
            (0b10, 0b11, (0x0002,)),
            (0b11, 0b10, (0x0002,)),
        ),
    ),
    "sv48x4": ("_sv48x4", ((0b00, 0b11, (0x0002,)), (0b11, 0b00, (0x0002,)))),
}


def _pmm_change_steps(
    test_data: TestData,
    pair: _Pair,
    *,
    csr: str,
    mask: str,
    shift: int,
    old: int,
    new: int,
    tags: tuple[int, ...],
    mode: str,
    load: str,
    store: str,
    cp: str,
    name: str,
    fence: bool,
    alias: bool,
) -> list[str]:
    """The steps of the PMM change cases: loads with the old value, the change, then loads and stores with the new.

    With fence, HFENCE.GVMA x0, x0 follows each change at once.  Without it, nothing fences the change.
    """
    lines = [
        comment_banner(f"{cp}: {csr} PMM {old:02b} -> {new:02b}"),
        *set_pmm_field(csr, old, _PMLEN[old], test_data),
        *(["hfence.gvma x0, x0"] if fence else ["hfence.gvma x0, x0", "hfence.vvma"]),
        *_tag_probes(test_data, pair, cp, f"{name}_old", (load,), tags, mode, 0),
        *_csrw_field(test_data, csr, mask, new << shift, test_data.add_testcase(name, cp, _CG)),
        "hfence.gvma x0, x0" if fence else "// Nothing fences the change",
        *_tag_probes(test_data, pair, cp, f"{name}_new", (load,), tags, mode, 0),
    ]
    for tag in tags:
        lines.extend(_probe(test_data, cp, f"{name}_new_{store}_t{tag:04x}", store, tag, mode))
        if alias:
            lines.extend(_check_alias(test_data))
    for pmm in sorted({old, new} - {0}):
        lines = pmm_ifdef(csr, _PMLEN[pmm], lines)
    return lines


def _hfence(test_data: TestData, g: SvMode) -> list[str]:
    """cp_henvcfg_pmm_change_hfence and cp_hupmm_change_hfence: each tag maps to the alias page in the G stage, and
    after a PMM change and HFENCE.GVMA x0, x0 the accesses follow the new PMM."""
    suffix, cases = _HFENCE[g.name]
    tags = tuple(sorted({tag for _, _, case_tags in cases for tag in case_tags}))
    lines = [
        *_setup(test_data, _Pair(None, g), user=False),
        *_alias_tags(test_data, g, tags, PteFlags(user=True), unmap=False),
        *_clear_pmm(test_data),
    ]
    for csr, mask, shift, mode, load, store, cp in (
        ("henvcfg", "HENVCFG_PMM", 32, "VS", "ld", "sd", f"cp_henvcfg_pmm_change_hfence{suffix}"),
        ("hstatus", "HSTATUS_HUPMM", 48, "U", "hlv.d", "hsv.d", f"cp_hupmm_change_hfence{suffix}"),
    ):
        if mode == "U":
            lines.extend(_hstatus(test_data, spvp=0, hu=1))
        for old, new, case_tags in cases:
            lines.extend(
                _pmm_change_steps(
                    test_data,
                    _Pair(None, g),
                    csr=csr,
                    mask=mask,
                    shift=shift,
                    old=old,
                    new=new,
                    tags=case_tags,
                    mode=mode,
                    load=load,
                    store=store,
                    cp=cp,
                    name=f"{g.name}_{csr}_{old:02b}to{new:02b}",
                    fence=True,
                    alias=True,
                )
            )
        lines.extend(set_pmm_field(csr, 0, 0, test_data))
    return [
        *lines,
        *_hstatus(test_data, spvp=0, hu=0),
        *_alias_tags(test_data, g, tags, PteFlags(user=True), unmap=True),
        *guest_translation_teardown(test_data),
    ]


# pair: [(PMM, tags)] of cp_henvcfg_pmm_change_no_hfence.  With vsatp = Sv57 the VS stage maps the canonical tag 0x0002
# to the alias page.
_NO_HFENCE = {
    "bare_sv39x4": ((0b10, (0x0400,)), (0b11, (0x0002, 0x0400))),
    "bare_sv48x4": ((0b10, (0x0400,)),),
    "sv57_sv57x4": ((0b10, (0x0400,)), (0b11, (0x0002, 0x0400))),
}


def _no_hfence(test_data: TestData, pair: _Pair) -> list[str]:
    """cp_henvcfg_pmm_change_no_hfence: with no G-stage bit masked, a henvcfg.PMM change needs no HFENCE."""
    alias = pair.vs is not None
    lines = [*_setup(test_data, pair, user=False), *_clear_pmm(test_data)]
    if pair.vs is not None:
        lines.extend(_alias_tags(test_data, pair.vs, (0x0002,), PteFlags(), unmap=False))
    for pmm, tags in _NO_HFENCE[pair.name]:
        for old, new in ((0b00, pmm), (pmm, 0b00)):
            lines.extend(
                _pmm_change_steps(
                    test_data,
                    pair,
                    csr="henvcfg",
                    mask="HENVCFG_PMM",
                    shift=32,
                    old=old,
                    new=new,
                    tags=tags,
                    mode="VS",
                    load="ld",
                    store="sd",
                    cp="cp_henvcfg_pmm_change_no_hfence",
                    name=f"{pair.name}_{old:02b}to{new:02b}",
                    fence=False,
                    alias=alias,
                )
            )
    if pair.vs is not None:
        lines.extend(_alias_tags(test_data, pair.vs, (0x0002,), PteFlags(), unmap=True))
    return [*lines, *_clear_pmm(test_data), *guest_translation_teardown(test_data)]


# pair: GPA bit b of cp_vs_gstage_no_pmm.  b is the top GPA bit of Sv48x4, and for Sv57x4 the top bit a VS-stage PTE can
# hold (its PPN ends at address bit 55).  Only PMLEN 16 masks either, so the case uses PMM 11.
_GSTAGE_NO_PMM = {"sv48_sv48x4": 49, "sv57_sv57x4": 55}


def _gstage_no_pmm(test_data: TestData, pair: _Pair) -> list[str]:
    """cp_vs_gstage_no_pmm: the VS stage maps _HIGH_VA to G, the GPA of pm_lo_page with bit b set, which the G stage
    maps to the alias page.  Masking that cleared bit b of G would reach pm_lo_page instead."""
    assert pair.vs is not None and pair.g is not None
    va, gpa, tmp = test_data.int_regs.get_registers(3)
    lines = [
        *_setup(test_data, pair, user=False),
        f"LI(x{va}, {_HIGH_VA:#x})",
        f"LA(x{gpa}, pm_lo_page)",
        f"LI(x{tmp}, {1 << _GSTAGE_NO_PMM[pair.name]:#x})",
        f"or x{gpa}, x{gpa}, x{tmp}",
        *_map_page(test_data, pair.vs, va, gpa, PteFlags()),
        f"LA(x{tmp}, {_ALIAS})",
        *_map_page(test_data, pair.g, gpa, tmp, PteFlags(user=True)),
        "hfence.gvma",
        "hfence.vvma",
    ]
    label = f"{pair.name}_pmm11"
    body = [
        *_pmm_case(test_data, "henvcfg", 0b11),
        *_guest_op(test_data, "cp_vs_gstage_no_pmm", f"{label}_ld", "VS", "ld", va),
        *_guest_op(test_data, "cp_vs_gstage_no_pmm", f"{label}_sd", "VS", "sd", va),
        f"LA(x{tmp}, pm_lo_page)",
        f"ld x{tmp}, 0(x{tmp})",
        write_sigupd(tmp, test_data),
        *_check_alias(test_data),
    ]
    lines.extend(
        [*pmm_ifdef("henvcfg", _PMLEN[0b11], body), *_unmap(test_data, pair.vs, va), *_unmap(test_data, pair.g, gpa)]
    )
    test_data.int_regs.return_registers([va, gpa, tmp])
    return [*lines, *_clear_pmm(test_data), *guest_translation_teardown(test_data)]


# ── Coverpoints on BARE_PAIR and PAGED_PAIR ────────────────────────────────

# (coverpoint, mode, hstatus.SPVP, PMM field) of the HLV and HSV cases
_HLV = (
    ("cp_hlv_hs_spvp1_pmm", "HS", 1, "henvcfg"),
    ("cp_hlv_hs_spvp0_pmm", "HS", 0, "senvcfg"),
    ("cp_hlv_u_spvp1_pmm", "U", 1, "henvcfg"),
    ("cp_hlv_u_spvp0_pmm", "U", 0, "hstatus"),
)


def _hlv(test_data: TestData, target: _Target, pmm: int) -> list[str]:
    lines = []
    ops = ("hlv.d", "hsv.d")
    for cp, mode, spvp, field in _HLV:
        body = [
            comment_banner(f"{cp}: {field} PMM {pmm:02b}, {_name(target)}"),
            *_on(test_data, target, user=not spvp),
            *_hstatus(test_data, spvp=spvp, hu=int(mode == "U")),
            *_pmm_case(test_data, field, pmm),
            *_tag_probes(test_data, target, cp, _name(target), ops, _TAGS, mode, _PMLEN[pmm]),
            *_upper(test_data, target, cp, _name(target), ops, pmm, mode, user=not spvp),
            *_hstatus(test_data, spvp=0, hu=0),
            *guest_translation_teardown(test_data),
        ]
        lines.extend(_wrap(target, body))
    return [*lines, *_clear_pmm(test_data)]


def _hlvx(test_data: TestData, target: _Target, pmm: int) -> list[str]:
    lines = []
    for mode, cp in (("HS", "cp_hlvx_hs_pmm"), ("U", "cp_hlvx_u_pmm")):
        for spvp in (0, 1):
            body = [
                comment_banner(f"{cp}: every PMM field {pmm:02b}, SPVP = {spvp}, {_name(target)}"),
                *_on(test_data, target, user=not spvp),
                *_hstatus(test_data, spvp=spvp, hu=int(mode == "U")),
                *_all_pmm(test_data, pmm),
                *_tag_probes(test_data, target, cp, f"{_name(target)}_spvp{spvp}", ("hlvx.wu",), _TAGS, mode, 0),
                *_hstatus(test_data, spvp=0, hu=0),
                *guest_translation_teardown(test_data),
            ]
            lines.extend(_wrap(target, body))
    return [*lines, *_clear_pmm(test_data)]


def _mxr_cases(test_data: TestData, target: _Target, pmm: int, cp: str, mode: str, ops: tuple[str, ...]) -> list[str]:
    """ops in mode with every PMM field = pmm and each MXR combination in effect, which turns masking off."""
    lines = []
    for vs_mxr, s_mxr in _MXR:
        prefix = f"{_name(target)}_vsmxr{vs_mxr}_smxr{s_mxr}"
        lines.extend(
            [
                *_mxr(test_data, vs_mxr, s_mxr),
                *_tag_probes(test_data, target, cp, prefix, ops, _FULL_TAGS[pmm], mode, 0),
            ]
        )
    return [*lines, *_mxr(test_data, 0, 0)]


def _hlv_mxr(test_data: TestData, target: _Target, pmm: int) -> list[str]:
    lines = []
    for spvp in (1, 0):
        cp = f"cp_hlv_hs_spvp{spvp}_mxr_pmm"
        body = [
            comment_banner(f"{cp}: every PMM field {pmm:02b}, {_name(target)}"),
            *_on(test_data, target, user=not spvp),
            *_hstatus(test_data, spvp=spvp, hu=0),
            *_all_pmm(test_data, pmm),
            *_mxr_cases(test_data, target, pmm, cp, "HS", ("hlv.d", "hsv.d")),
            *_hstatus(test_data, spvp=0, hu=0),
            *guest_translation_teardown(test_data),
        ]
        lines.extend(_wrap(target, body))
    return [*lines, *_clear_pmm(test_data)]


def _guest_mxr(test_data: TestData, target: _Target, pmm: int) -> list[str]:
    lines = []
    for mode in ("VS", "VU"):
        cp = f"cp_{mode.lower()}_mxr_pmm"
        body = [
            comment_banner(f"{cp}: every PMM field {pmm:02b}, {_name(target)}"),
            *_on(test_data, target, user=mode == "VU"),
            *_all_pmm(test_data, pmm),
            *_mxr_cases(test_data, target, pmm, cp, mode, ("ld", "sd")),
            *guest_translation_teardown(test_data),
        ]
        lines.extend(_wrap(target, body))
    return [*lines, *_clear_pmm(test_data)]


def _jalr(test_data: TestData, target: _Target, pmm: int) -> list[str]:
    """cp_vs_pmm_jalr, cp_vu_pmm_jalr: a jalr to a tagged pointer at a pad.  Fetches are never masked, so only the
    untagged one reaches the pad, and the trap handler returns from a fetch fault to ra."""
    base, addr, check = test_data.int_regs.get_registers(3)
    pad = f"{_name(target)}_pmm{pmm:02b}_jalr_pad"
    lines = [
        f"j {pad}_end",
        f"{pad}:",
        f"addi x{check}, x{check}, 1   # reached only through an untagged pointer",
        "jr ra",
        f"{pad}_end:",
    ]
    for mode, field in (("VS", "henvcfg"), ("VU", "senvcfg")):
        cp = f"cp_{mode.lower()}_pmm_jalr"
        body = [
            comment_banner(f"{cp}: {field} PMM {pmm:02b}, {_name(target)}"),
            *_on(test_data, target, user=mode == "VU"),
            *_pmm_case(test_data, field, pmm),
        ]
        for tag in _TAGS:
            probe = [
                f"LA(x{base}, {pad})",
                f"LI(x{addr}, {tag << 48:#x})",
                f"xor x{addr}, x{addr}, x{base}",
                f"LI(x{check}, 0)",
                f"RVTEST_TSBI_GOTO_{mode}MODE",
                test_data.add_testcase(f"{_name(target)}_pmm{pmm:02b}_t{tag:04x}", cp, _CG),
                f"jalr ra, 0(x{addr})",
                "RVTEST_TSBI_GOTO_SMODE",
                write_sigupd(check, test_data),
            ]
            body.extend(gated(probe, _tag_gate(target, tag, 0)))
        lines.extend(_wrap(target, [*body, *guest_translation_teardown(test_data)]))
    test_data.int_regs.return_registers([base, addr, check])
    return [*lines, *_clear_pmm(test_data)]


def _misaligned(test_data: TestData, target: _Target, pmm: int) -> list[str]:
    lines = []
    for mode, field in (("VS", "henvcfg"), ("VU", "senvcfg")):
        cp = f"cp_{mode.lower()}_pmlen_misaligned_word"
        body = [
            comment_banner(f"{cp}: {field} PMM {pmm:02b}, {_name(target)}"),
            *_on(test_data, target, user=mode == "VU"),
            *_pmm_case(test_data, field, pmm),
        ]

        def build(base: str | HeldAddress, cp: str = cp) -> list[str]:
            return [
                line
                for tag in _FULL_TAGS[pmm]
                for op in ("lw", "sw")
                for line in _probe(
                    test_data, cp, f"{_name(target)}_pmm{pmm:02b}_{op}_t{tag:04x}", op, tag, "HS", offset=1, base=base
                )
            ]

        body.extend(_stint(test_data, mode, build))
        lines.extend(_wrap(target, [*body, *guest_translation_teardown(test_data)]))
    return [*lines, *_clear_pmm(test_data)]


def _fault_fits(pair: _Pair, fault: str, pmlen: int) -> str:
    """The condition for using fault, an RVMODEL_ACCESS_FAULT_ADDRESS_* macro, on pair with masking by pmlen and
    _fault_maps: it is defined, unchanged by masking (bits 63:63 - pmlen clear when vsatp is paged, which
    sign-extends, and bits 63:64 - pmlen when vsatp = Bare, which zero-extends), inside each stage's width (a low-half
    address of a VS stage), and outside the root entries (the level-3 entry under a split Sv57x4 root) that hold the
    guest code alias, _GPF_GPA and, where it is not identity mapped, _SPARE_VA."""
    width = 63 - pmlen if pair.vs is not None else 64 - pmlen
    taken: list[tuple[int, int]] = []
    for mode in (pair.g, pair.vs):
        if mode is None:
            continue
        split = mode.stage == "g" and _needs_split(mode)
        if split:
            width = min(width, 48)
        elif mode.stage == "vs":
            width = min(width, mode.va_bits - 1)
        else:
            width = min(width, mode.va_bits)
        shift = mode.page_offset_bits(mode.levels - 2 if split else mode.levels - 1)
        taken.append((shift, int(mode.code_va, 16)))
        if mode.stage == "g":
            taken.append((shift, _GPF_GPA))
        elif not _needs_split(mode):
            taken.append((shift, _SPARE_VA[mode.name]))
    conds = [f"defined({fault})", f"({fault}) >> {width} == 0"]
    conds.extend(
        dict.fromkeys(f"({fault}) >> {shift} != {a >> shift:#x}" for shift, a in sorted(taken) if a >> width == 0)
    )
    return " && ".join(conds)


def _fault_gate(target: _Target, kind: str, pmlen: int) -> tuple[list[str], str]:
    """The defines and the condition for using RVMODEL_ACCESS_FAULT_ADDRESS_{kind} on target with masking by pmlen:
    _fault_fits of a pair, or for BARE_PAIR or PAGED_PAIR a macro that holds it for the pair the preprocessor
    chooses."""
    fault = f"RVMODEL_ACCESS_FAULT_ADDRESS_{kind}"
    if isinstance(target, _Pair):
        return [], _fault_fits(target, fault, pmlen)
    macro, candidates = _ROLES[target]
    name = f"SSNPMH_{target.upper()}_FAULT_{kind}"
    lines = []
    for value, pair in candidates:
        cond = f"{macro} == {value} && {_fault_fits(pair, fault, pmlen)}"
        lines.extend([f"{'#elif' if lines else '#if'} {cond}", f"#define {name} 1"])
    return [*lines, "#else", f"#define {name} 0", "#endif"], name


def _fault_maps(test_data: TestData, pair: _Pair, user: bool, gates: dict[str, str]) -> list[str]:
    """Identity map the access-fault address of each kind in both stages under its condition in gates, and map
    _SPARE_VA to _GPF_GPA in a paged VS stage.  _fault_unmaps removes them.

    The test image's Sv57x4 root entry would also map _GPF_GPA, so _split_root splits it.  _SPARE_VA of Sv57 is in
    the image's VS-stage root entry, which maps it to _GPF_GPA.
    """
    pte, addr, tmp = test_data.int_regs.get_registers(3)
    regs = (pte, addr, tmp)
    vs_flags, g_flags = PteFlags(user=user), PteFlags(user=True)
    split = pair.g is not None and _needs_split(pair.g)
    lines = _split_root(test_data, pair.g, g_flags) if split and pair.g is not None else []
    for kind, gate in gates.items():
        fault = f"RVMODEL_ACCESS_FAULT_ADDRESS_{kind}"
        body = []
        for mode, flags in ((pair.vs, vs_flags), (pair.g, g_flags)):
            if mode is None:
                continue
            level = mode.levels - 1
            if split and mode is pair.g:
                table = mode.page_table_label(level - 1)
                body.extend(
                    write_pte(
                        mode,
                        level=level,
                        flags=PteFlags.nonleaf(),
                        virtual_address=fault,
                        physical_address=table,
                        regs=regs,
                    )
                )
                level -= 1
            body.extend(
                write_pte(
                    mode,
                    level=level,
                    flags=flags,
                    virtual_address=fault,
                    physical_address=fault,
                    regs=regs,
                    pa_is_label=False,
                    superpage=True,
                )
            )
        if body:
            lines.extend(gated(body, gate))
    if pair.vs is not None and not _needs_split(pair.vs):
        lines.extend(
            write_pte(
                pair.vs,
                level=pair.vs.levels - 1,
                flags=vs_flags,
                virtual_address=hex(_SPARE_VA[pair.vs.name]),
                physical_address=hex(_GPF_GPA),
                regs=regs,
                pa_is_label=False,
                superpage=True,
            )
        )
    test_data.int_regs.return_registers([pte, addr, tmp])
    return [*lines, "hfence.gvma", "hfence.vvma"]


def _fault_unmaps(test_data: TestData, pair: _Pair, user: bool, gates: dict[str, str]) -> list[str]:
    """Remove the mappings of _fault_maps, then map the test image at the root again: that undoes the split of an
    Sv57x4 root, and an access-fault address can share a root entry with the image."""
    split = pair.g is not None and _needs_split(pair.g)
    va = test_data.int_regs.get_register()
    lines = []
    for kind, gate in gates.items():
        body = []
        for mode in (pair.vs, pair.g):
            if mode is not None:
                body.extend(_unmap(test_data, mode, va, mode.levels - 2 if split and mode is pair.g else None))
        if body:
            lines.extend(gated([f"LI_FIXED_LEN(x{va}, RVMODEL_ACCESS_FAULT_ADDRESS_{kind})", *body], gate))
    if pair.vs is not None and not _needs_split(pair.vs):
        lines.extend([f"LI(x{va}, {_SPARE_VA[pair.vs.name]:#x})", *_unmap(test_data, pair.vs, va)])
    test_data.int_regs.return_register(va)
    image = _map_image(test_data, (pair.g, PteFlags(user=True)), (pair.vs, PteFlags(user=user)))
    return [*lines, *image, "hfence.gvma", "hfence.vvma"]


def _gpf_base(target: _Target) -> str:
    """The LI line format for an address of target whose guest physical address has no G-stage mapping."""
    return f"LI(x{{}}, {_GPF_GPA:#x})" if target == "bare" else "LI(x{}, SSNPMH_SPARE_VA)"


def _fault_probe(test_data: TestData, cp: str, name: str, mode: str, op: str, base: str, tag: int) -> list[str]:
    """op in mode at base (an LI line format) tagged with tag.  It traps to HS-mode, whose trap record holds scause,
    stval and htval."""
    base_reg, addr, data = test_data.int_regs.get_registers(3)
    lines = [
        base.format(base_reg),
        f"LI(x{addr}, {tag << 48:#x})",
        f"xor x{addr}, x{addr}, x{base_reg}",
        f"LI(x{data}, {SENTINEL:#x})",
        f"RVTEST_TSBI_GOTO_{mode}MODE",
        test_data.add_testcase(name, cp, _CG),
        f"{op} x{data}, 0(x{addr})",
        "RVTEST_TSBI_GOTO_SMODE",
        write_sigupd(data, test_data),
    ]
    test_data.int_regs.return_registers([base_reg, addr, data])
    return lines


def _faults(test_data: TestData, target: _Target, pmm: int) -> list[str]:
    """cp_*_hardware_csr_writes_fault_*: lw and sw at an access-fault address and at an address with no G-stage
    mapping, untagged and with tags that masking clears.  stval holds the masked address and htval the GPA of a
    guest-page fault, or zero."""
    lines: list[str] = []
    gates: dict[str, str] = {}
    for kind in ("LOAD", "STORE"):
        defines, gates[kind] = _fault_gate(target, kind, _PMLEN[pmm])
        lines.extend(defines)
    for mode, field in (("VS", "henvcfg"), ("VU", "senvcfg")):
        user = mode == "VU"
        body = [
            comment_banner(f"cp_{mode.lower()}_hardware_csr_writes_fault_*: {field} PMM {pmm:02b}, {_name(target)}"),
            *_on(test_data, target, user, lambda pair, user=user: _fault_maps(test_data, pair, user, gates)),
            *_pmm_case(test_data, field, pmm),
        ]
        for tag in _FULL_TAGS[pmm]:
            for op, kind in (("lw", "LOAD"), ("sw", "STORE")):
                cp = f"cp_{mode.lower()}_hardware_csr_writes_fault_{kind.lower()}"
                fault = f"LI_FIXED_LEN(x{{}}, RVMODEL_ACCESS_FAULT_ADDRESS_{kind})"
                name = f"{_name(target)}_pmm{pmm:02b}_t{tag:04x}"
                access = _fault_probe(test_data, cp, f"{name}_access", mode, op, fault, tag)
                body.extend(gated(access, gates[kind]))
                gpf = _fault_probe(test_data, cp, f"{name}_gpf", mode, op, _gpf_base(target), tag)
                body.extend(gated(gpf, "SSNPMH_BARE_PAIR != 0" if target == "bare" else None))
        unmaps = _per_pair(
            target,
            lambda pair, user=user: _fault_unmaps(test_data, pair, user, gates),
            lambda pair: pair != _BARE_BARE,
        )
        lines.extend(_wrap(target, [*body, *unmaps, *guest_translation_teardown(test_data)]))
    return [*lines, *_clear_pmm(test_data)]


class _Insn(NamedTuple):
    """A pm_h_insn access other than RVV: its probe (load, store, amo, cas or cbo), the condition it needs, the
    readback of a store or AMO, and its probe options."""

    probe: str
    mnemonic: str
    gate: str | None = None
    readback: str = "ld"
    compressed: bool = False
    via_sp: bool = False
    fp: bool = False
    arch: tuple[str, ...] = ()


_ZCA = "defined(ZCA_SUPPORTED)"
_ZCD = "defined(ZCA_SUPPORTED) && defined(ZCD_SUPPORTED)"
_SWEEP = (
    _Insn("amo", "amoadd.d", "defined(ZAAMO_SUPPORTED)"),
    _Insn("cas", "amocas.d", "defined(ZACAS_SUPPORTED)"),
    _Insn("amo", "amoadd.h", "defined(ZABHA_SUPPORTED)", readback="lhu"),
    _Insn("load", "fld", "defined(D_SUPPORTED)", fp=True),
    _Insn("store", "fsd", "defined(D_SUPPORTED)", fp=True),
    _Insn("load", "c.ld", _ZCA, compressed=True, arch=("zca",)),
    _Insn("store", "c.sd", _ZCA, compressed=True, arch=("zca",)),
    _Insn("load", "c.ldsp", _ZCA, via_sp=True, arch=("zca",)),
    _Insn("store", "c.sdsp", _ZCA, via_sp=True, arch=("zca",)),
    _Insn("load", "c.fldsp", _ZCD, via_sp=True, fp=True, arch=("zca", "zcd")),
    _Insn("store", "c.fsdsp", _ZCD, via_sp=True, fp=True, arch=("zca", "zcd")),
    _Insn("cbo", "cbo.zero", "defined(ZICBOZ_SUPPORTED)"),
    _Insn("cbo", "cbo.clean", "defined(ZICBOM_SUPPORTED)"),
    # A hint on every hart: the readback shows that it changed nothing
    _Insn("cbo", "prefetch.w"),
)
# RVV pm_h_insn: (mnemonic, template, readback after a store)
_VECTOR = (
    ("vle64.v", "vle64.v v2, (x{a})", None),
    ("vlse64.v", "vlse64.v v2, (x{a}), x0", None),
    ("vluxei64.v", "vluxei64.v v2, (x{a}), v4", None),
    ("vloxei64.v", "vloxei64.v v2, (x{a}), v4", None),
    ("vlseg2e64.v", "vlseg2e64.v v2, (x{a})", None),
    ("vl1re64.v", "vl1re64.v v2, (x{a})", None),
    ("vle64ff.v", "vle64ff.v v2, (x{a})", None),
    ("vse64.v", "vse64.v v2, (x{a})", "ld"),
    ("vsse64.v", "vsse64.v v2, (x{a}), x0", "ld"),
    ("vsuxei64.v", "vsuxei64.v v2, (x{a}), v4", "ld"),
    ("vsoxei64.v", "vsoxei64.v v2, (x{a}), v4", "ld"),
    ("vsseg2e64.v", "vsseg2e64.v v2, (x{a})", "ld"),
    ("vs1r.v", "vs1r.v v2, (x{a})", "ld"),
)


def _sweep_probe(test_data: TestData, insn: _Insn, cp: str, name: str, tag: int, base: str | HeldAddress) -> list[str]:
    if insn.probe == "amo":
        return probe_amo(insn.mnemonic, insn.readback, tag, name, test_data, _CG, coverpoint=cp, base_address=base)
    if insn.probe == "cas":
        return probe_zacas(insn.mnemonic, tag, name, test_data, _CG, coverpoint=cp, base_address=base)
    if insn.probe == "cbo":
        return probe_cbo(insn.mnemonic, tag, name, test_data, _CG, coverpoint=cp, base_address=base)
    if insn.probe == "load":
        return probe_load(
            insn.mnemonic,
            tag,
            name,
            test_data,
            _CG,
            coverpoint=cp,
            compressed=insn.compressed,
            via_sp=insn.via_sp,
            float_load=insn.fp,
            arch_extensions=insn.arch,
            base_address=base,
        )
    return probe_store(
        insn.mnemonic,
        insn.readback,
        tag,
        name,
        test_data,
        _CG,
        coverpoint=cp,
        compressed=insn.compressed,
        via_sp=insn.via_sp,
        fp_move_mnemonic="fmv.d.x" if insn.fp else None,
        arch_extensions=insn.arch,
        base_address=base,
    )


def _sweep(test_data: TestData, cp: str, prefix: str, tag: int, base: str | HeldAddress) -> list[str]:
    """One access of each pm_h_insn group at base tagged with tag."""

    def name(mnemonic: str) -> str:
        return f"{prefix}_{mnemonic}_t{tag:04x}"

    lines = []
    for gate, insns in groupby(_SWEEP, key=lambda insn: insn.gate):
        probes = [line for insn in insns for line in _sweep_probe(test_data, insn, cp, name(insn.mnemonic), tag, base)]
        lines.extend(gated(probes, gate))
    vector = [
        line
        for mnemonic, template, readback in _VECTOR
        for line in probe_vec(
            64, template, readback, tag, name(mnemonic), test_data, _CG, coverpoint=cp, base_address=base
        )
    ]
    return [*lines, *gated(vector, "defined(ZVE64X_SUPPORTED)")]


def _masking(test_data: TestData, target: _Target, pmm: int, mode: str) -> list[str]:
    field = "henvcfg" if mode == "VS" else "senvcfg"
    cp = f"cp_{mode.lower()}_pmlen_masking"
    body = [
        comment_banner(f"{cp}: {field} PMM {pmm:02b}, {_name(target)}"),
        *_on(test_data, target, user=mode == "VU"),
        *_pmm_case(test_data, field, pmm),
    ]
    prefix = f"{_name(target)}_pmm{pmm:02b}"

    def build(base: str | HeldAddress) -> list[str]:
        lines = []
        for tag in _SWEEP_TAGS:
            lines.extend(gated(_sweep(test_data, cp, prefix, tag, base), _tag_gate(target, tag, _PMLEN[pmm])))
        return lines

    body.extend(_stint(test_data, mode, build))
    return [*_wrap(target, [*body, *guest_translation_teardown(test_data)]), *_clear_pmm(test_data)]


def _ss_page(test_data: TestData, pair: _Pair, user: bool, unmap: bool = False) -> list[str]:
    """Map _SPARE_VA to the shadow stack page (PTE.xwr = 010) in a paged VS stage, or unmap it."""
    assert pair.vs is not None
    flags = PteFlags(read=False, write=True, execute=False, user=user)
    page = _page_map(test_data, pair.vs, _SPARE_VA[pair.vs.name], _SS_PAGE, flags, PteFlags(user=user), unmap)
    return [*page, "hfence.vvma"]


def _ss_address(reg: int, tmp: int, tag: int, offset: int = 0) -> list[str]:
    """x{reg} = the shadow stack page's guest virtual address with bits 63:48 = tag, plus offset."""
    lines = [f"LI(x{reg}, SSNPMH_SPARE_VA)", f"LI(x{tmp}, {tag << 48:#x})", f"xor x{reg}, x{reg}, x{tmp}"]
    return [*lines, f"addi x{reg}, x{reg}, {offset}"] if offset else lines


def _seed_ss(base: int, value: int, seed: int) -> list[str]:
    """Write seed to the shadow stack page through its physical address, which HS-mode accesses with satp = Bare."""
    return [f"LA(x{base}, {_SS_PAGE})", f"LI(x{value}, {seed:#x})", f"sd x{value}, 0(x{base})"]


def _ssamoswap(test_data: TestData, cp: str, name: str, mode: str, mnemonic: str, readback: str, tag: int) -> list[str]:
    base, addr, value, result = test_data.int_regs.get_registers(4)
    lines = [
        *_seed_ss(base, value, VALUE_OLD),
        *_ss_address(addr, value, tag),
        f"LI(x{value}, {VALUE_NEW:#x})",
        f"LI(x{result}, {SENTINEL:#x})",
        f"RVTEST_TSBI_GOTO_{mode}MODE",
        test_data.add_testcase(name, cp, _CG),
        f"{mnemonic} x{result}, x{value}, (x{addr})",
        "RVTEST_TSBI_GOTO_SMODE",
        write_sigupd(result, test_data),
        f"{readback} x{result}, 0(x{base})",
        write_sigupd(result, test_data),
    ]
    test_data.int_regs.return_registers([base, addr, value, result])
    return lines


def _ss_push_pop(
    test_data: TestData, cp: str, name: str, mode: str, mnemonic: str, link: int, compressed: bool, tag: int
) -> list[str]:
    """A push writes the link register at ssp - 8 and a pop checks it against ssp.  HS-mode sets ssp to the tagged
    address and checks ssp and, after a push, the shadow stack page."""
    push = "push" in mnemonic
    base, addr, value = test_data.int_regs.get_registers(3)
    lines = [
        *_seed_ss(base, value, VALUE_OLD),
        *_ss_address(addr, value, tag, 8 if push else 0),
        f"csrw CSR_SSP, x{addr}",
        f"LI(x{link}, {VALUE_NEW if push else VALUE_OLD:#x})",
        f"RVTEST_TSBI_GOTO_{mode}MODE",
        test_data.add_testcase(name, cp, _CG),
        *arch_block([f"{mnemonic} x{link}"], *(("zca", "zcmop") if compressed else ())),
        "RVTEST_TSBI_GOTO_SMODE",
        f"csrr x{value}, CSR_SSP",
        write_sigupd(value, test_data),
    ]
    if push:
        lines.extend([f"ld x{value}, 0(x{base})", write_sigupd(value, test_data)])
    test_data.int_regs.return_registers([base, addr, value])
    return gated(lines, "defined(ZCMOP_SUPPORTED)") if compressed else lines


def _zicfiss(test_data: TestData, pmm: int, mode: str) -> list[str]:
    """cp_*_pmlen_zicfiss_amo and _ssp on PAGED_PAIR, where _SPARE_VA maps to a shadow stack page."""
    user = mode == "VU"
    field = "senvcfg" if user else "henvcfg"
    prefix = f"paged_pair_pmm{pmm:02b}"
    amo_cp, ssp_cp = f"cp_{mode.lower()}_pmlen_zicfiss_amo", f"cp_{mode.lower()}_pmlen_zicfiss_ssp"
    body = [
        comment_banner(f"{amo_cp}, {ssp_cp}: {field} PMM {pmm:02b}, paged_pair"),
        *_on(test_data, "paged", user, lambda pair: _ss_page(test_data, pair, user)),
        *set_sse("menvcfg", True, test_data, tsbi=True),
        *set_sse("henvcfg", True, test_data),
        *(set_sse("senvcfg", True, test_data) if user else []),
        *_pmm_case(test_data, field, pmm),
    ]
    for tag in _SWEEP_TAGS:
        for mnemonic, readback in (("ssamoswap.w", "lw"), ("ssamoswap.d", "ld")):
            body.extend(_ssamoswap(test_data, amo_cp, f"{prefix}_{mnemonic}_t{tag:04x}", mode, mnemonic, readback, tag))
        for mnemonic, link, compressed in (
            ("sspush", 1, False),
            ("sspush", 5, False),
            ("c.sspush", 1, True),
            ("sspopchk", 1, False),
            ("sspopchk", 5, False),
            ("c.sspopchk", 5, True),
        ):
            name = f"{prefix}_{mnemonic}_x{link}_t{tag:04x}"
            body.extend(_ss_push_pop(test_data, ssp_cp, name, mode, mnemonic, link, compressed, tag))
    body.extend(
        [
            *(set_sse("senvcfg", False, test_data) if user else []),
            *set_sse("henvcfg", False, test_data),
            *set_sse("menvcfg", False, test_data, tsbi=True),
            *_per_pair("paged", lambda pair: _ss_page(test_data, pair, user, unmap=True)),
            *guest_translation_teardown(test_data),
            *_clear_pmm(test_data),
        ]
    )
    return _wrap("paged", gated(body, "defined(ZICFISS_SUPPORTED)"))


# ── Chunks ─────────────────────────────────────────────────────────────────


def _chunk(
    test_data: TestData, split: str | None, title: str, description: str, build: Callable[[], list[str]]
) -> TestChunk:
    """A chunk of build's code, with the data every Ssnpm H file needs.  A chunk that starts a file (split) also has
    the defines, which the later chunks of the file share.  .ifndef keeps one copy of the data."""
    tc = test_data.begin_test_chunk(split_name=split)
    tc.section_header = comment_banner(title, description)
    tc.code.extend([*(_DEFINES if split else _NEED_DEFINES), *build()])
    for label, value in (("pm_lo_page", VALUE_OLD), (_ALIAS, _VALUE_ALIAS), (_SS_PAGE, 0)):
        tc.raw_data.extend([f".ifndef {label}", *data_page(label, value), ".endif"])
    tc.raw_data.extend([f".ifndef {_M_SHADOW}", ".p2align 3", f"{_M_SHADOW}:", ".dword -1, -1", ".endif"])
    tc.raw_data.extend(lower_table_data(SV57X4, VS_SV57))
    return test_data.end_test_chunk()


def _make_pair(test_data: TestData, pair: _Pair) -> list[TestChunk]:
    """cp_vs_pmm and cp_vu_pmm with pair, and the cases that need it."""
    chunks = [
        _chunk(
            test_data,
            f"H_{pair.name}",
            f"cp_vs_pmm, cp_vu_pmm: (vsatp, hgatp) = {pair.name}",
            "ld and sd at each tag in VS-mode for each henvcfg.PMM and in VU-mode for each senvcfg.PMM",
            lambda: [*_ldsd(test_data, pair, "VS"), *_ldsd(test_data, pair, "VU")],
        )
    ]
    g = pair.g
    if pair.vs is None and g is not None and g.name in _HFENCE:
        suffix = _HFENCE[g.name][0]
        chunks.append(
            _chunk(
                test_data,
                None,
                f"cp_henvcfg_pmm_change_hfence{suffix}, cp_hupmm_change_hfence{suffix}",
                "henvcfg.PMM (VS-mode ld and sd) and hstatus.HUPMM (U-mode hlv.d and hsv.d) change, followed at once\n"
                "by HFENCE.GVMA x0, x0, with each tag mapped to the alias page in the G stage",
                lambda: _hfence(test_data, g),
            )
        )
    if pair.name in _NO_HFENCE:
        chunks.append(
            _chunk(
                test_data,
                None,
                "cp_henvcfg_pmm_change_no_hfence",
                "henvcfg.PMM changes with nothing to fence it, where no masked bit is a guest physical address bit",
                lambda: _no_hfence(test_data, pair),
            )
        )
    if pair.name in _GSTAGE_NO_PMM:
        chunks.append(
            _chunk(
                test_data,
                None,
                "cp_vs_gstage_no_pmm",
                "henvcfg.PMM never masks the guest physical address that the VS stage produces",
                lambda: _gstage_no_pmm(test_data, pair),
            )
        )
    return chunks


def _roles(build: Callable[[TestData, _Target, int], list[str]], test_data: TestData, pmm: int) -> list[str]:
    return [line for role in ("bare", "paged") for line in build(test_data, role, pmm)]


def _make_chosen(test_data: TestData, pmm: int) -> list[TestChunk]:
    """The coverpoints on BARE_PAIR and PAGED_PAIR, for PMM value pmm of the field under test."""
    label = f"pmm{pmm:02b}"
    chunks = [
        _chunk(
            test_data,
            f"H_{label}_hlv",
            f"cp_hlv_*_pmm: PMM {pmm:02b}",
            "hlv.d and hsv.d from HS-mode and from U-mode (hstatus.HU = 1) with each hstatus.SPVP",
            lambda: _roles(_hlv, test_data, pmm),
        )
    ]
    if pmm:
        chunks.append(
            _chunk(
                test_data,
                None,
                f"cp_hlvx_*_pmm, cp_hlv_hs_spvp*_mxr_pmm: PMM {pmm:02b}",
                "hlvx.wu, and hlv.d and hsv.d with MXR in effect, are never masked",
                lambda: [*_roles(_hlvx, test_data, pmm), *_roles(_hlv_mxr, test_data, pmm)],
            )
        )
    chunks.append(
        _chunk(
            test_data,
            f"H_{label}_guest",
            f"cp_vu_pmm_writer_vs: PMM {pmm:02b}",
            "VS-mode writes senvcfg.PMM with a csrw, and the VU-mode accesses follow it",
            lambda: _roles(_writer_vs, test_data, pmm),
        )
    )
    chunks.append(
        _chunk(
            test_data,
            None,
            f"cp_vs_pmm_jalr, cp_vu_pmm_jalr: PMM {pmm:02b}",
            "Instruction fetches are never masked",
            lambda: _roles(_jalr, test_data, pmm),
        )
    )
    if pmm:
        chunks.append(
            _chunk(
                test_data,
                None,
                f"cp_*_pmlen_misaligned_word, cp_*_hardware_csr_writes_fault_*, cp_*_mxr_pmm: PMM {pmm:02b}",
                "Masking applies to misaligned accesses and to the stval of a fault, and not with MXR in effect",
                lambda: [
                    *_roles(_misaligned, test_data, pmm),
                    *_roles(_faults, test_data, pmm),
                    *_roles(_guest_mxr, test_data, pmm),
                ],
            )
        )
    for mode in ("VS", "VU"):
        prefix = f"cp_{mode.lower()}_pmlen"
        chunks.append(
            _chunk(
                test_data,
                f"H_{label}_{mode.lower()}_masking",
                f"{prefix}_masking: PMM {pmm:02b}",
                f"One instruction of each kind that accesses memory, in {mode}-mode at each tag",
                lambda mode=mode: [line for role in ("bare", "paged") for line in _masking(test_data, role, pmm, mode)],
            )
        )
        chunks.append(
            _chunk(
                test_data,
                None,
                f"{prefix}_zicfiss_amo, {prefix}_zicfiss_ssp: PMM {pmm:02b}",
                f"Shadow stack accesses in {mode}-mode on PAGED_PAIR",
                lambda mode=mode: _zicfiss(test_data, pmm, mode),
            )
        )
    return chunks


def _xl_clear(test_data: TestData, cp: str) -> list[str]:
    """hstatus.VSXL = 01 clears henvcfg.PMM (cp_pmm_vsxl_clear), and vsstatus.UXL = 01, written from HS-mode or
    VS-mode, clears senvcfg.PMM (cp_pmm_vsuxl_clear).  Setting the field back to 10 leaves PMM at 00.  The VS-mode
    writer runs on BARE_PAIR and on PAGED_PAIR."""
    vsxl = cp == "cp_pmm_vsxl_clear"
    pmm_csr, csr, mask = ("henvcfg", "hstatus", "HSTATUS_VSXL") if vsxl else ("senvcfg", "vsstatus", "SSTATUS_UXL")
    check = test_data.int_regs.get_register()

    def read(name: str) -> list[str]:
        return [
            f"csrr x{check}, {pmm_csr}",
            f"srli x{check}, x{check}, 32",
            f"andi x{check}, x{check}, 3",
            test_data.add_testcase(name, cp, _CG),
            write_sigupd(check, test_data),
        ]

    def cases(writer: str, suffix: str = "") -> list[str]:
        lines = []
        for pmm, pmlen, label in PMM_CONFIGS[1:]:
            name = f"{label}_{writer.lower()}{suffix}"
            body = [*set_pmm_field(pmm_csr, pmm, pmlen, test_data), *read(f"{name}_before")]
            write = _csrw_field(
                test_data,
                csr if writer == "HS" else "sstatus",
                mask,
                1 << 32,
                test_data.add_testcase(f"{name}_write", cp, _CG),
            )
            body.extend(write if writer == "HS" else ["RVTEST_TSBI_GOTO_VSMODE", *write, "RVTEST_TSBI_GOTO_SMODE"])
            body.extend([*read(f"{name}_rv32"), *_csrw_field(test_data, csr, mask, 2 << 32), *read(f"{name}_rv64")])
            lines.extend(pmm_ifdef(pmm_csr, pmlen, body))
        return lines

    lines = cases("HS")
    if not vsxl:
        for role in ("bare", "paged"):
            on = _on(test_data, role, user=False)
            body = [*on, *cases("VS", f"_{_name(role)}"), *guest_translation_teardown(test_data)]
            lines.extend(_wrap(role, body))
    test_data.int_regs.return_register(check)
    return [*lines, *set_pmm_field(pmm_csr, 0, 0, test_data)]


def _make_xl(test_data: TestData, cp: str) -> list[TestChunk]:
    return [
        _chunk(
            test_data, f"H_{cp.removeprefix('cp_pmm_')}", cp, _xl_clear.__doc__ or "", lambda: _xl_clear(test_data, cp)
        )
    ]


# ── Generators ─────────────────────────────────────────────────────────────


@add_priv_test_generator(
    "Ssnpm", required_extensions=_EXTENSIONS, march_extensions=_MARCH, extra_defines=_BOOT, params=_BARE_BARE.params
)
def make_ssnpmh_bare_bare(test_data: TestData) -> list[TestChunk]:
    return _make_pair(test_data, _BARE_BARE)


@add_priv_test_generator(
    "Ssnpm", required_extensions=_EXTENSIONS, march_extensions=_MARCH, extra_defines=_BOOT, params=_BARE_SV39X4.params
)
def make_ssnpmh_bare_sv39x4(test_data: TestData) -> list[TestChunk]:
    return _make_pair(test_data, _BARE_SV39X4)


@add_priv_test_generator(
    "Ssnpm", required_extensions=_EXTENSIONS, march_extensions=_MARCH, extra_defines=_BOOT, params=_BARE_SV48X4.params
)
def make_ssnpmh_bare_sv48x4(test_data: TestData) -> list[TestChunk]:
    return _make_pair(test_data, _BARE_SV48X4)


@add_priv_test_generator(
    "Ssnpm", required_extensions=_EXTENSIONS, march_extensions=_MARCH, extra_defines=_BOOT, params=_BARE_SV57X4.params
)
def make_ssnpmh_bare_sv57x4(test_data: TestData) -> list[TestChunk]:
    return _make_pair(test_data, _BARE_SV57X4)


@add_priv_test_generator(
    "Ssnpm", required_extensions=_EXTENSIONS, march_extensions=_MARCH, extra_defines=_BOOT, params=_SV39_SV39X4.params
)
def make_ssnpmh_sv39_sv39x4(test_data: TestData) -> list[TestChunk]:
    return _make_pair(test_data, _SV39_SV39X4)


@add_priv_test_generator(
    "Ssnpm", required_extensions=_EXTENSIONS, march_extensions=_MARCH, extra_defines=_BOOT, params=_SV48_SV48X4.params
)
def make_ssnpmh_sv48_sv48x4(test_data: TestData) -> list[TestChunk]:
    return _make_pair(test_data, _SV48_SV48X4)


@add_priv_test_generator(
    "Ssnpm", required_extensions=_EXTENSIONS, march_extensions=_MARCH, extra_defines=_BOOT, params=_SV57_SV57X4.params
)
def make_ssnpmh_sv57_sv57x4(test_data: TestData) -> list[TestChunk]:
    return _make_pair(test_data, _SV57_SV57X4)


@add_priv_test_generator(
    "Ssnpm", required_extensions=_EXTENSIONS, march_extensions=_MARCH, extra_defines=_BOOT, params=_XLEN64
)
def make_ssnpmh_pmm00(test_data: TestData) -> list[TestChunk]:
    return _make_chosen(test_data, 0b00)


@add_priv_test_generator(
    "Ssnpm",
    required_extensions=_EXTENSIONS,
    march_extensions=_MARCH,
    extra_defines=_BOOT,
    params=[*_XLEN64, "SUPPORTED_PMLEN_SSNPM: 7"],
)
def make_ssnpmh_pmm10(test_data: TestData) -> list[TestChunk]:
    return _make_chosen(test_data, 0b10)


@add_priv_test_generator(
    "Ssnpm",
    required_extensions=_EXTENSIONS,
    march_extensions=_MARCH,
    extra_defines=_BOOT,
    params=[*_XLEN64, "SUPPORTED_PMLEN_SSNPM: 16"],
)
def make_ssnpmh_pmm11(test_data: TestData) -> list[TestChunk]:
    return _make_chosen(test_data, 0b11)


# TODO: Register make_ssnpmh_vsxl and make_ssnpmh_vsuxl again for full coverage once Sail supports mixed XLEN.  Sail
# ignores writes to hstatus.VSXL and vsstatus.UXL, so its signatures keep henvcfg.PMM and senvcfg.PMM, which a hart
# with VSXLEN or VUXLEN 32 must clear.  Until then such a hart misses cp_pmm_vsxl_clear and cp_pmm_vsuxl_clear, and an
# RV64-only hart has neither coverpoint.
# @add_priv_test_generator(
#     "Ssnpm", required_extensions=_EXTENSIONS, march_extensions=_MARCH, extra_defines=_BOOT, params=["VSXLEN: 32"]
# )
def make_ssnpmh_vsxl(test_data: TestData) -> list[TestChunk]:
    return _make_xl(test_data, "cp_pmm_vsxl_clear")


# @add_priv_test_generator(
#     "Ssnpm",
#     required_extensions=_EXTENSIONS,
#     march_extensions=_MARCH,
#     extra_defines=_BOOT,
#     params=["VSXLEN: 64", "VUXLEN: 32"],
# )
def make_ssnpmh_vsuxl(test_data: TestData) -> list[TestChunk]:
    return _make_xl(test_data, "cp_pmm_vsuxl_clear")
