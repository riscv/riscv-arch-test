##################################
# priv/extensions/pmp/HSvZicbo.py
#
# PMP HSvZicbo group: PMP on cache-block operations under two-stage address translation.
# David_Harris@hmc.edu 29 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMP HSvZicbo group: PMP on the final address of cache-block operations from VS-mode and VU-mode.

The group boots to M-mode, which programs PMP, and delegates nothing, so the M-mode handler takes every trap.  The
guest translation and CBO cases come from the Sv HZicbo group.
"""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.pmp import helpers as pmp
from testgen.priv.extensions.sv.page_tables import SV32X4, SV39X4, VS_SV32, VS_SV39, PteFlags, SvMode
from testgen.priv.extensions.sv.SvHZicbo import DATA, Chunk, case, make_chunk, mapping, vs_identity
from testgen.priv.registry import add_priv_test_generator


def _pmp_cases(test_data: TestData, c: Chunk, mode: str) -> list[str]:
    """PMP entry 0 denies the test page (XWR = 000), then allows only reads (XWR = 001), through both stages'
    kilopages.

    set_pmpaddr clobbers x5 and x6 before each case loads its registers.
    """
    lines = []
    for xwr in ("000", "001"):
        region = [
            *pmp.zero_pmp_regs(),
            *pmp.set_pmpaddr("napot", 0, DATA),
            *pmp.set_pmpcfg(0, pmp.cfg_byte(f"0{xwr}", "napot", pmp.cfg_shift(0))),
            "sfence.vma",
        ]
        expected = "store access fault" if c.family == "zicboz" or xwr == "000" else "no fault: reads are allowed"
        vs_ptes = [*region, *mapping(test_data, c.vs, 0, PteFlags(user=mode == "vu"))]
        g_ptes = [*region, *vs_identity(test_data, c, mode), *mapping(test_data, c.g, 0, PteFlags(user=True))]
        lines.extend(
            [
                *case(test_data, c, mode, f"pmp{xwr}", "cp_pmp", expected, vs_ptes, stage=c.vs, level=0),
                *case(test_data, c, mode, f"pmp{xwr}", "cp_pmp", expected, g_ptes, stage=c.g, level=0),
            ]
        )
    return [*lines, *pmp.zero_pmp_regs()]


def _make_hsvzicbo(test_data: TestData, g: SvMode, vs: SvMode, family: str) -> list[TestChunk]:
    return [
        make_chunk(
            test_data,
            family,
            g,
            vs,
            group="HSvZicbo",
            covergroup="PMP_HSvZicbo_cg",
            home="M",
            section=("pmp", "cp_pmp", "PMP denies the test page, then allows only reads", _pmp_cases),
            setup=(*pmp.napot_mask_defines(12), "RVTEST_PMP_SET_BACKGROUND x4"),
        )
    ]


# PMP entry 0 is a NAPOT region that covers the 4 KiB test page, which holds whole cache blocks; the last entry is
# the background region.
_PARAMS = [
    "NUM_PMP_ENTRIES: '>1'",
    "PMP_NAPOT_SUPPORTED: true",
    "PMP_GRANULARITY: '<=12'",
]


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sm", "H", "Zicbom"],
    extra_defines=["#define BOOT_TO_MMODE"],
    params=[*_PARAMS, "SV39X4_TRANSLATION: true", "SV39_VSMODE_TRANSLATION: true"],
)
def make_hsvzicbo_sv39x4_zicbom(test_data: TestData) -> list[TestChunk]:
    return _make_hsvzicbo(test_data, SV39X4, VS_SV39, "zicbom")


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sm", "H", "Zicboz"],
    extra_defines=["#define BOOT_TO_MMODE"],
    params=[*_PARAMS, "SV39X4_TRANSLATION: true", "SV39_VSMODE_TRANSLATION: true"],
)
def make_hsvzicbo_sv39x4_zicboz(test_data: TestData) -> list[TestChunk]:
    return _make_hsvzicbo(test_data, SV39X4, VS_SV39, "zicboz")


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sm", "H", "Zicbom"],
    extra_defines=["#define BOOT_TO_MMODE"],
    params=[*_PARAMS, "SV32X4_TRANSLATION: true", "SV32_VSMODE_TRANSLATION: true"],
)
def make_hsvzicbo_sv32x4_zicbom(test_data: TestData) -> list[TestChunk]:
    return _make_hsvzicbo(test_data, SV32X4, VS_SV32, "zicbom")


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sm", "H", "Zicboz"],
    extra_defines=["#define BOOT_TO_MMODE"],
    params=[*_PARAMS, "SV32X4_TRANSLATION: true", "SV32_VSMODE_TRANSLATION: true"],
)
def make_hsvzicbo_sv32x4_zicboz(test_data: TestData) -> list[TestChunk]:
    return _make_hsvzicbo(test_data, SV32X4, VS_SV32, "zicboz")
