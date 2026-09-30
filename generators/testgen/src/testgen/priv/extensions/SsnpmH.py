##################################
# priv/extensions/SsnpmH.py
#
# SsnpmH pointer masking tests for VS-mode, VU-mode and the hypervisor load/store instructions.
# David_Harris@hmc.edu 29 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""SsnpmH test generator.

The suite boots to HS-mode.  Each test runs with vsatp = Bare and hgatp = Sv57x4 or Sv48x4 identity mapping the
test image, so a guest address is a guest physical address and pointer masking zero-extends it (zpm.adoc,
pm_ignore_pa).  A tagged address sets one bit that PMLEN = 7 and 16 both mask (58 for Sv57x4, 57 for Sv48x4) or
one that only PMLEN = 16 masks (48 for Sv57x4, 49 for Sv48x4).  When masking clears the tag, the access reaches
ssnpmh_data.  Otherwise the tagged guest physical address has no G-stage mapping, or is wider than hgatp allows,
and raises a guest-page fault in HS-mode, and a load leaves its destination unchanged.  Bits 58 and 49 are the top
guest physical address bits, beyond the VS-stage modes' widths, which masking clears only when vsatp = Bare
(hypervisor.adoc, "Interaction with Pointer Masking").

henvcfg.PMM applies to VS-mode and senvcfg.PMM to VU-mode.  An HLV or HSV from HS-mode takes henvcfg.PMM when
hstatus.SPVP = 1 and senvcfg.PMM when SPVP = 0; from U-mode with hstatus.HU = 1 it takes henvcfg.PMM when SPVP = 1
and hstatus.HUPMM when SPVP = 0.  In each case the other PMM fields hold a different value.  HLVX is never masked,
and nor is an access with vsstatus.MXR = 1.  A PMM value selects PMLEN = 7 (10) or 16 (11) only when the
configuration supports that PMLEN.
"""

from collections.abc import Sequence

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.sv.generate import guest_translation_setup, guest_translation_teardown
from testgen.priv.extensions.sv.page_tables import SV48X4, SV57X4, SvMode
from testgen.priv.registry import add_priv_test_generator

_CG = "SsnpmH_cg"
_DATA = "ssnpmh_data"
_LOAD_VALUE = 0x0123456789ABCDEF
_STORE_VALUE = 0x0F1E2D3C4B5A6978
# PMM encodings, the PMLEN each selects and the configuration guard for it
_PMM = {"00": (0, None), "10": (7, "UDB_SUPPORTED_PMLEN_SSNPM_7"), "11": (16, "UDB_SUPPORTED_PMLEN_SSNPM_16")}
# PMM value, defined in the test, that the fields a case does not use hold: enabled when the case's field is 00
_OTHER_ON = "SSNPMH_PMM_ON"
_PMM_ON_DEFINE = [
    "#ifdef UDB_SUPPORTED_PMLEN_SSNPM_16",
    f"#define {_OTHER_ON} 3",
    "#else",
    f"#define {_OTHER_ON} 2",
    "#endif",
]
# The PMM field of each CSR and its position
_PMM_FIELDS = {"henvcfg": ("HENVCFG_PMM", 32), "senvcfg": ("SENVCFG_PMM", 32), "hstatus": ("HSTATUS_HUPMM", 48)}
_OPS = {
    "ld": "ld x{rd}, 0(x{addr})",
    "sd": "sd x{rd}, 0(x{addr})",
    "hlv.d": "hlv.d x{rd}, (x{addr})",
    "hsv.d": "hsv.d x{rd}, (x{addr})",
    "hlvx.wu": "hlvx.wu x{rd}, (x{addr})",
}
_STORES = ("sd", "hsv.d")


def _tags(g: SvMode) -> tuple[int, int]:
    """Address bits a test tags: one that PMLEN = 7 and 16 both mask (bits 63:57) and one that only PMLEN = 16
    masks (bits 56:48).  Each is the top guest physical address bit when that lies in its range."""
    top = g.levels - 1
    msb = g.page_offset_bits(top) + g.index_bits(top) - 1
    return (max(msb, 57), msb if 48 <= msb < 57 else 48)


def _set_pmm(csr: str, value: str, reg: int) -> list[str]:
    """Write ``value`` (a PMM encoding or _OTHER_ON) to the PMM field of ``csr``."""
    mask, shift = _PMM_FIELDS[csr]
    field = int(value, 2) if value in _PMM else value
    return [f"LI(x{reg}, {mask})", f"csrc {csr}, x{reg}", f"LI(x{reg}, ({field}) << {shift})", f"csrs {csr}, x{reg}"]


def _access(test_data: TestData, name: str, coverpoint: str, op: str, tag: int, mode: str) -> list[str]:
    """``op`` in ``mode`` (VS, VU, U, or S for HS) at ssnpmh_data with bit ``tag`` set, checked back in HS-mode.

    A load's destination starts at -1 and a store writes _STORE_VALUE over _LOAD_VALUE, so the check shows whether
    the access reached ssnpmh_data.
    """
    addr, rd, tmp = test_data.int_regs.get_registers(3)
    store = op in _STORES
    lines = [
        f"LA(x{addr}, {_DATA})",
        f"LI(x{tmp}, {1 << tag:#x})  # tag bit {tag}",
        f"or x{addr}, x{addr}, x{tmp}",
        f"LI(x{rd}, {_STORE_VALUE:#x})" if store else f"LI(x{rd}, -1)",
        *([] if mode == "S" else [f"RVTEST_TSBI_GOTO_{mode}MODE"]),
        test_data.add_testcase(name, coverpoint, _CG),
        _OPS[op].format(rd=rd, addr=addr),
        *([] if mode == "S" else ["RVTEST_TSBI_GOTO_SMODE"]),
    ]
    if store:
        lines.extend(
            [
                f"LA(x{addr}, {_DATA})",
                f"ld x{rd}, 0(x{addr})",
                write_sigupd(rd, test_data),
                "# Restore ssnpmh_data",
                f"LI(x{rd}, {_LOAD_VALUE:#x})",
                f"sd x{rd}, 0(x{addr})",
            ]
        )
    else:
        lines.append(write_sigupd(rd, test_data))
    test_data.int_regs.return_registers([addr, rd, tmp])
    return lines


def _pmm_cases(
    test_data: TestData,
    g: SvMode,
    coverpoint: str,
    mode: str,
    ops: tuple[str, ...],
    field: str,
    others: tuple[str, ...],
    setup: Sequence[str] = (),
) -> list[str]:
    """``ops`` in ``mode`` for each PMM value of ``field``, with the ``others`` fields enabled when it is 00."""
    reg = test_data.int_regs.get_register()
    lines = []
    for value, (pmlen, guard) in _PMM.items():
        body = [f"# {field} PMM = {value} (PMLEN = {pmlen})", *setup, *_set_pmm(field, value, reg)]
        for other in others:
            body.extend(_set_pmm(other, _OTHER_ON if value == "00" else "00", reg))
        for op in ops:
            for tag in _tags(g):
                body.extend(_access(test_data, f"{g.name}_{op}_{field}{value}_bit{tag}", coverpoint, op, tag, mode))
        lines.extend([f"#ifdef {guard}", *body, "#endif"] if guard else body)
    lines.extend(_set_pmm(field, "00", reg))
    lines.extend(line for other in others for line in _set_pmm(other, "00", reg))
    test_data.int_regs.return_register(reg)
    return lines


def _spvp(value: int, reg: int) -> list[str]:
    return [f"LI(x{reg}, HSTATUS_SPVP)", f"{'csrs' if value else 'csrc'} hstatus, x{reg}"]


def _make_ssnpmh(test_data: TestData, g: SvMode) -> list[TestChunk]:
    reg = test_data.int_regs.get_register()
    chunks = []

    def begin(name: str, title: str, description: str) -> TestChunk:
        tc = test_data.begin_test_chunk(f"{g.name}_{name}")
        tc.section_header = comment_banner(title, description)
        tc.code.extend([*_PMM_ON_DEFINE, *guest_translation_setup(test_data, g, None, "VSmode")])
        tc.raw_data.extend([".p2align 3", f"{_DATA}:", f".8byte {_LOAD_VALUE:#x}"])
        return tc

    def end(tc: TestChunk) -> None:
        tc.code.extend(guest_translation_teardown(test_data))
        chunks.append(test_data.end_test_chunk())

    tc = begin(
        "guest",
        "cp_vs_pmm, cp_vu_pmm",
        f"ld and sd in VS-mode for each henvcfg.PMM and in VU-mode for each senvcfg.PMM, at tagged addresses,\n"
        f"with vsatp = Bare and hgatp = {g.extension}.  The other of the two fields is enabled when the one that\n"
        "applies is 00",
    )
    tc.code.extend(_pmm_cases(test_data, g, "cp_vs_pmm", "VS", ("ld", "sd"), "henvcfg", ("senvcfg",)))
    tc.code.extend(_pmm_cases(test_data, g, "cp_vu_pmm", "VU", ("ld", "sd"), "senvcfg", ("henvcfg",)))
    end(tc)

    tc = begin(
        "hlv",
        "cp_hlv_hs_pmm, cp_hlv_u_pmm",
        "hlv.d and hsv.d at tagged addresses from HS-mode and from U-mode with hstatus.HU = 1, for hstatus.SPVP = 0\n"
        "and 1 and each value of the PMM field that applies: henvcfg.PMM for SPVP = 1, senvcfg.PMM from HS-mode\n"
        "and hstatus.HUPMM from U-mode for SPVP = 0.  The other fields are enabled when that one is 00",
    )
    ops = ("hlv.d", "hsv.d")
    tc.code.extend(
        [
            *_pmm_cases(test_data, g, "cp_hlv_hs_pmm", "S", ops, "henvcfg", ("senvcfg", "hstatus"), _spvp(1, reg)),
            *_pmm_cases(test_data, g, "cp_hlv_hs_pmm", "S", ops, "senvcfg", ("henvcfg", "hstatus"), _spvp(0, reg)),
            f"LI(x{reg}, HSTATUS_HU)",
            f"csrs hstatus, x{reg}",
            *_pmm_cases(test_data, g, "cp_hlv_u_pmm", "U", ops, "henvcfg", ("senvcfg", "hstatus"), _spvp(1, reg)),
            *_pmm_cases(test_data, g, "cp_hlv_u_pmm", "U", ops, "hstatus", ("henvcfg", "senvcfg"), _spvp(0, reg)),
            f"LI(x{reg}, HSTATUS_HU)",
            f"csrc hstatus, x{reg}",
        ]
    )
    end(tc)

    tc = begin(
        "unmasked",
        "cp_hlvx_pmm, cp_mxr_pmm",
        "With the PMM field that applies enabled, hlvx.wu from HS-mode and from U-mode with hstatus.HU = 1, and\n"
        "ld in VS-mode and VU-mode with vsstatus.MXR = 1, at tagged addresses.  Neither is masked, so each raises\n"
        "a guest-page fault",
    )
    lines = []
    for mode, spvp, field in (("S", 1, "henvcfg"), ("S", 0, "senvcfg"), ("U", 1, "henvcfg"), ("U", 0, "hstatus")):
        lines.extend([*_spvp(spvp, reg), *_set_pmm(field, _OTHER_ON, reg)])
        if mode == "U":
            lines.extend([f"LI(x{reg}, HSTATUS_HU)", f"csrs hstatus, x{reg}"])
        tag = "hs" if mode == "S" else "u"
        for bit in _tags(g):
            lines.extend(
                _access(test_data, f"{g.name}_{tag}_spvp{spvp}_{field}_bit{bit}", "cp_hlvx_pmm", "hlvx.wu", bit, mode)
            )
        if mode == "U":
            lines.extend([f"LI(x{reg}, HSTATUS_HU)", f"csrc hstatus, x{reg}"])
        lines.extend(_set_pmm(field, "00", reg))
    lines.extend([f"LI(x{reg}, SSTATUS_MXR)", f"csrs vsstatus, x{reg}"])
    for mode, field in (("VS", "henvcfg"), ("VU", "senvcfg")):
        lines.extend(_set_pmm(field, _OTHER_ON, reg))
        for bit in _tags(g):
            lines.extend(_access(test_data, f"{g.name}_{mode.lower()}_{field}_bit{bit}", "cp_mxr_pmm", "ld", bit, mode))
        lines.extend(_set_pmm(field, "00", reg))
    lines.extend([f"LI(x{reg}, SSTATUS_MXR)", f"csrc vsstatus, x{reg}"])
    tc.code.extend(lines)
    end(tc)

    test_data.int_regs.return_register(reg)
    return chunks


@add_priv_test_generator(
    "SsnpmH",
    required_extensions=["H", "Ssnpm"],
    extra_defines=["#define BOOT_TO_SMODE"],
    params=["SV57X4_TRANSLATION: true"],
)
def make_ssnpmh_sv57x4(test_data: TestData) -> list[TestChunk]:
    return _make_ssnpmh(test_data, SV57X4)


@add_priv_test_generator(
    "SsnpmH",
    required_extensions=["H", "Ssnpm"],
    extra_defines=["#define BOOT_TO_SMODE"],
    params=["SV48X4_TRANSLATION: true"],
)
def make_ssnpmh_sv48x4(test_data: TestData) -> list[TestChunk]:
    return _make_ssnpmh(test_data, SV48X4)
