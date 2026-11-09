##################################
# priv/extensions/Ssdbltrp.py
#
# Ssdbltrp H group: vsstatus.SDT across SRET from HS-mode and from VS-mode.
# David_Harris@hmc.edu 8 November 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Ssdbltrp H group test generator.

The group boots to HS-mode with menvcfg.DTE = henvcfg.DTE = 1, so sstatus.SDT and vsstatus.SDT are writable.
An SRET in HS-mode clears sstatus.SDT, and also vsstatus.SDT when it returns to VU-mode; an SRET in VS-mode clears
vsstatus.SDT.  An SRET from HS-mode to VS-mode or HS-mode leaves vsstatus.SDT alone.  After each SRET the test
returns to HS-mode and records vsstatus.SDT and sstatus.SDT.
"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

_CG = "Ssdbltrp_H_cg"

_DTE_ON = [
    "#if __riscv_xlen == 64",
    "RVTEST_TSBI_CSR_SET(CSR_MENVCFG, MENVCFG_DTE)",
    "#else",
    "RVTEST_TSBI_CSR_SET(CSR_MENVCFGH, MENVCFGH_DTE)",
    "#endif",
]
_DTE_OFF = [line.replace("_SET(", "_CLEAR(") for line in _DTE_ON]


def _henvcfg_dte(op: str, reg: int) -> list[str]:
    return [
        "#if __riscv_xlen == 64",
        f"LI(x{reg}, HENVCFG_DTE)",
        f"{op} henvcfg, x{reg}",
        "#else",
        f"LI(x{reg}, HENVCFGH_DTE)",
        f"{op} henvcfgh, x{reg}",
        "#endif",
    ]


def _record_sdt(test_data: TestData, rd: int, mask_reg: int, name: str, coverpoint: str) -> list[str]:
    """In HS-mode, record vsstatus.SDT and sstatus.SDT."""
    lines = []
    for csr in ("vsstatus", "sstatus"):
        lines.extend(
            [
                test_data.add_testcase(f"{name}_{csr}", coverpoint, _CG),
                f"csrr x{rd}, {csr}",
                f"and x{rd}, x{rd}, x{mask_reg}",
                write_sigupd(rd, test_data),
            ]
        )
    return lines


def _sret_sdt_tests(test_data: TestData) -> list[str]:
    temp_reg, rd, mask_reg = test_data.int_regs.get_registers(3)
    lines = [
        comment_banner(
            "cp_hs_sret_vsstatus_sdt, cp_vs_sret_vsstatus_sdt",
            "With menvcfg.DTE = henvcfg.DTE = 1 and vsstatus.SDT = 1, SRET from HS-mode to VU-mode, VS-mode and\n"
            "HS-mode, and SRET in VS-mode to VU-mode and VS-mode.  Back in HS-mode, read vsstatus.SDT and sstatus.SDT.\n"
            "Only SRET to VU-mode from HS-mode and SRET in VS-mode clear vsstatus.SDT",
        ),
        *_DTE_ON,
        *_henvcfg_dte("csrs", temp_reg),
        f"LI(x{mask_reg}, SSTATUS_SDT)",
    ]
    # SRET from HS-mode: (target, hstatus.SPV, sstatus.SPP)
    for target, spv, spp in (("vu", 1, 0), ("vs", 1, 1), ("hs", 0, 1)):
        name = f"hs_to_{target}"
        lines.extend(
            [
                "",
                f"# SRET from HS-mode to {target.upper()}-mode with vsstatus.SDT = 1 and sstatus.SDT = 1",
                f"csrs vsstatus, x{mask_reg}",
                f"LI(x{temp_reg}, HSTATUS_SPV)",
                f"{'csrs' if spv else 'csrc'} hstatus, x{temp_reg}",
                f"LI(x{temp_reg}, SSTATUS_SPP)",
                f"{'csrs' if spp else 'csrc'} sstatus, x{temp_reg}",
                f"csrs sstatus, x{mask_reg}",
                f"LA(x{temp_reg}, 1f)",
                f"csrw sepc, x{temp_reg}",
                test_data.add_testcase(name, "cp_hs_sret_vsstatus_sdt", _CG),
                "sret",
                "1:",
                *([] if target == "hs" else ["RVTEST_TSBI_GOTO_SMODE"]),
                *_record_sdt(test_data, rd, mask_reg, name, "cp_hs_sret_vsstatus_sdt"),
            ]
        )
    lines.extend([f"LI(x{temp_reg}, HSTATUS_SPV)", f"csrc hstatus, x{temp_reg}"])
    # SRET in VS-mode: vsstatus.SPP selects VU-mode or VS-mode
    for target, spp in (("vu", 0), ("vs", 1)):
        name = f"vs_to_{target}"
        lines.extend(
            [
                "",
                f"# SRET in VS-mode to {target.upper()}-mode with vsstatus.SDT = 1",
                f"csrs vsstatus, x{mask_reg}",
                f"LI(x{temp_reg}, SSTATUS_SPP)",
                f"{'csrs' if spp else 'csrc'} vsstatus, x{temp_reg}",
                "RVTEST_TSBI_GOTO_VSMODE",
                f"LA(x{temp_reg}, 1f)",
                f"csrw sepc, x{temp_reg}",
                test_data.add_testcase(name, "cp_vs_sret_vsstatus_sdt", _CG),
                "sret",
                "1:",
                "RVTEST_TSBI_GOTO_SMODE",
                *_record_sdt(test_data, rd, mask_reg, name, "cp_vs_sret_vsstatus_sdt"),
            ]
        )
    lines.extend(
        [
            f"csrc vsstatus, x{mask_reg}",
            f"csrc sstatus, x{mask_reg}",
            *_henvcfg_dte("csrc", temp_reg),
            *_DTE_OFF,
        ]
    )
    test_data.int_regs.return_registers([temp_reg, rd, mask_reg])
    return lines


@add_priv_test_generator(
    "Ssdbltrp",
    required_extensions=["Ssdbltrp", "H"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_ssdbltrph(test_data: TestData) -> list[TestChunk]:
    """Generate the Ssdbltrp_H tests: vsstatus.SDT across SRET."""
    tc = test_data.begin_test_chunk("H")
    tc.code.extend(_sret_sdt_tests(test_data))
    return [test_data.end_test_chunk()]
