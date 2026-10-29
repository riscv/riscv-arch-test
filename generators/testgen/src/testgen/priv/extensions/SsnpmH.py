##################################
# priv/extensions/SsnpmH.py
#
# Ssnpm H group: pointer masking tests for VS-mode, VU-mode and the hypervisor load/store instructions.
# David_Harris@hmc.edu 29 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Ssnpm H group test generator.

The group boots to HS-mode.  Each test runs with vsatp = Bare and hgatp = Sv57x4 or Sv48x4 identity mapping the
test image, so a guest address is a guest physical address and pointer masking zero-extends it (zpm.adoc,
pm_ignore_pa).  A tagged address sets one bit that PMLEN = 7 and 16 both mask (58 for Sv57x4, 57 for Sv48x4) or
one that only PMLEN = 16 masks (48 for Sv57x4, 49 for Sv48x4).  When masking clears the tag, the access reaches
the test data.  Otherwise the tagged guest physical address has no G-stage mapping, or is wider than hgatp allows,
and raises a guest-page fault in HS-mode, and a load leaves its destination unchanged.  Bits 58 and 49 are the top
guest physical address bits, beyond the VS-stage modes' widths, which masking clears only when vsatp = Bare
(hypervisor.adoc, "Interaction with Pointer Masking").

henvcfg.PMM applies to VS-mode and senvcfg.PMM to VU-mode.  An HLV or HSV from HS-mode takes henvcfg.PMM when
hstatus.SPVP = 1 and senvcfg.PMM when SPVP = 0; from U-mode with hstatus.HU = 1 it takes henvcfg.PMM when SPVP = 1
and hstatus.HUPMM when SPVP = 0.  In each case the other PMM fields hold a different value.  HLVX is never masked,
and nor is an access with vsstatus.MXR = 1; those cases enable every PMM field.  A PMM value selects PMLEN = 7 (10)
or 16 (11) only when the configuration supports that PMLEN.
"""

from collections.abc import Sequence

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.sv.generate import guest_translation_setup, guest_translation_teardown
from testgen.priv.extensions.sv.page_tables import SV48X4, SV57X4, SvMode
from testgen.priv.extensions.ZpmCommon import (
    PMM_CONFIGS,
    csr_op,
    data_page,
    pmm_ifdef,
    probe_load,
    probe_store,
    set_pmm_field,
)
from testgen.priv.registry import add_priv_test_generator

_CG = "Ssnpm_H_cg"
# PMM value, defined in the test, that the fields a case does not use hold: enabled when the case's field is 00
_OTHER_ON = "SSNPMH_PMM_ON"
_PMM_ON_DEFINE = [
    "#ifdef UDB_SUPPORTED_PMLEN_SSNPM_16",
    f"#define {_OTHER_ON} 3",
    "#else",
    f"#define {_OTHER_ON} 2",
    "#endif",
]
_PMM_CSRS = ("henvcfg", "senvcfg", "hstatus")
# Store mnemonic and the load that reads its data back
_STORES = {"sd": "ld", "hsv.d": "ld"}


def _tags(g: SvMode) -> tuple[int, int]:
    """Address bits a test tags: one that PMLEN = 7 and 16 both mask (bits 63:57) and one that only PMLEN = 16
    masks (bits 56:48).  Each is the top guest physical address bit when that lies in its range."""
    top = g.levels - 1
    msb = g.page_offset_bits(top) + g.index_bits(top) - 1
    return (max(msb, 57), msb if 48 <= msb < 57 else 48)


def _probe(test_data: TestData, name: str, coverpoint: str, op: str, tag: int, mode: str) -> list[str]:
    """``op`` in ``mode`` (VS, VU, U, or S for HS) at pm_lo_page with bit ``tag`` set, checked back in HS-mode."""
    run_mode = None if mode == "S" else mode
    upper_tag = 1 << (tag - 48)
    if op in _STORES:
        return probe_store(op, _STORES[op], upper_tag, name, test_data, _CG, coverpoint=coverpoint, mode=run_mode)
    return probe_load(op, upper_tag, name, test_data, _CG, coverpoint=coverpoint, mode=run_mode)


def _pmm_cases(
    test_data: TestData,
    g: SvMode,
    coverpoint: str,
    mode: str,
    ops: tuple[str, ...],
    field: str,
    setup: Sequence[str] = (),
) -> list[str]:
    """``ops`` in ``mode`` for each PMM value of ``field``, with the other PMM fields enabled when it is 00."""
    others = [other for other in _PMM_CSRS if other != field]
    lines = []
    for pmm, pmlen, label in PMM_CONFIGS:
        body = [*setup, *set_pmm_field(field, pmm, pmlen, test_data)]
        for other in others:
            body.extend(
                set_pmm_field(other, _OTHER_ON, None, test_data) if pmm == 0 else set_pmm_field(other, 0, 0, test_data)
            )
        for op in ops:
            for tag in _tags(g):
                body.extend(_probe(test_data, f"{g.name}_{op}_{field}_{label}_bit{tag}", coverpoint, op, tag, mode))
        lines.extend(pmm_ifdef(field, pmlen, body))
    lines.extend(_set_all_pmm(test_data, 0))
    return lines


def _set_all_pmm(test_data: TestData, value: int | str) -> list[str]:
    pmlen = None if isinstance(value, str) else 0
    return [line for csr in _PMM_CSRS for line in set_pmm_field(csr, value, pmlen, test_data)]


def _make_ssnpmh(test_data: TestData, g: SvMode) -> list[TestChunk]:
    chunks = []

    def begin(name: str, title: str, description: str) -> TestChunk:
        tc = test_data.begin_test_chunk(f"H_{g.name}_{name}")
        tc.section_header = comment_banner(title, description)
        tc.code.extend([*_PMM_ON_DEFINE, *guest_translation_setup(test_data, g, None, "VSmode")])
        tc.raw_data.extend(data_page("pm_lo_page"))
        return tc

    def end(tc: TestChunk) -> None:
        tc.code.extend(guest_translation_teardown(test_data))
        chunks.append(test_data.end_test_chunk())

    spvp = {value: csr_op("csrs" if value else "csrc", "hstatus", "HSTATUS_SPVP", test_data) for value in (0, 1)}
    hu = {value: csr_op("csrs" if value else "csrc", "hstatus", "HSTATUS_HU", test_data) for value in (0, 1)}

    tc = begin(
        "guest",
        "cp_vs_pmm, cp_vu_pmm",
        f"ld and sd in VS-mode for each henvcfg.PMM and in VU-mode for each senvcfg.PMM, at tagged addresses,\n"
        f"with vsatp = Bare and hgatp = {g.extension}.  The other PMM fields are enabled when the one that\n"
        "applies is 00",
    )
    tc.code.extend(_pmm_cases(test_data, g, "cp_vs_pmm", "VS", ("ld", "sd"), "henvcfg"))
    tc.code.extend(_pmm_cases(test_data, g, "cp_vu_pmm", "VU", ("ld", "sd"), "senvcfg"))
    end(tc)

    tc = begin(
        "hlv",
        "cp_hlv_hs_spvp1_pmm, cp_hlv_hs_spvp0_pmm, cp_hlv_u_spvp1_pmm, cp_hlv_u_spvp0_pmm",
        "hlv.d and hsv.d at tagged addresses from HS-mode and from U-mode with hstatus.HU = 1, for hstatus.SPVP = 0\n"
        "and 1 and each value of the PMM field that applies: henvcfg.PMM for SPVP = 1, senvcfg.PMM from HS-mode\n"
        "and hstatus.HUPMM from U-mode for SPVP = 0.  The other fields are enabled when that one is 00",
    )
    ops = ("hlv.d", "hsv.d")
    tc.code.extend(
        [
            *_pmm_cases(test_data, g, "cp_hlv_hs_spvp1_pmm", "S", ops, "henvcfg", spvp[1]),
            *_pmm_cases(test_data, g, "cp_hlv_hs_spvp0_pmm", "S", ops, "senvcfg", spvp[0]),
            *hu[1],
            *_pmm_cases(test_data, g, "cp_hlv_u_spvp1_pmm", "U", ops, "henvcfg", spvp[1]),
            *_pmm_cases(test_data, g, "cp_hlv_u_spvp0_pmm", "U", ops, "hstatus", spvp[0]),
            *hu[0],
        ]
    )
    end(tc)

    tc = begin(
        "unmasked",
        "cp_hlvx_hs_pmm, cp_hlvx_u_pmm, cp_mxr_pmm",
        "With every PMM field enabled, hlvx.wu from HS-mode and from U-mode with hstatus.HU = 1 for hstatus.SPVP\n"
        "= 0 and 1, and ld in VS-mode and VU-mode with vsstatus.MXR = 1, at tagged addresses.  Neither is masked,\n"
        "so each raises a guest-page fault",
    )
    lines = _set_all_pmm(test_data, _OTHER_ON)
    for mode, coverpoint in (("S", "cp_hlvx_hs_pmm"), ("U", "cp_hlvx_u_pmm")):
        lines.extend(hu[mode == "U"])
        for value in (0, 1):
            lines.extend(spvp[value])
            for bit in _tags(g):
                lines.extend(_probe(test_data, f"{g.name}_spvp{value}_bit{bit}", coverpoint, "hlvx.wu", bit, mode))
    lines.extend([*hu[0], *csr_op("csrs", "vsstatus", "SSTATUS_MXR", test_data)])
    for mode in ("VS", "VU"):
        for bit in _tags(g):
            lines.extend(_probe(test_data, f"{g.name}_{mode.lower()}_bit{bit}", "cp_mxr_pmm", "ld", bit, mode))
    lines.extend([*csr_op("csrc", "vsstatus", "SSTATUS_MXR", test_data), *_set_all_pmm(test_data, 0)])
    tc.code.extend(lines)
    end(tc)

    return chunks


@add_priv_test_generator(
    "Ssnpm",
    required_extensions=["H", "Ssnpm"],
    extra_defines=["#define BOOT_TO_SMODE"],
    params=["SV57X4_TRANSLATION: true"],
)
def make_ssnpmh_sv57x4(test_data: TestData) -> list[TestChunk]:
    return _make_ssnpmh(test_data, SV57X4)


@add_priv_test_generator(
    "Ssnpm",
    required_extensions=["H", "Ssnpm"],
    extra_defines=["#define BOOT_TO_SMODE"],
    params=["SV48X4_TRANSLATION: true"],
)
def make_ssnpmh_sv48x4(test_data: TestData) -> list[TestChunk]:
    return _make_ssnpmh(test_data, SV48X4)
