##################################
# priv/extensions/InterruptsSmH.py
#
# Interrupts_Sm_cg hypervisor interrupt tests that run in M-mode or need M-mode to set up delegation.
# David_Harris@hmc.edu 25 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Interrupts_Sm hypervisor interrupt test generator (from the hypervisor branch's InterruptsHSm).

The group boots to M-mode.  mideleg is zero except for the VS-level interrupts (and SGEI when GEILEN > 0),
which are always delegated to HS-mode.
"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

_CG = "Interrupts_Sm_cg"


def _mcsr_tests(test_data: TestData) -> list[str]:
    """mie and mip bits for the VS-level interrupts and SGEI, seen from M-mode."""
    tmp_reg, check_reg = test_data.int_regs.get_registers(2)
    lines = [
        comment_banner(
            "cp_mie_mip",
            "With hie = 0x444, hie = 0x1444 (if GEILEN > 0) and hvip = 0x444, read mie and the VS-level and SGEI\n"
            "bits of mip, and hip after the hvip write.  SGEIE is writable when GEILEN > 0; otherwise mideleg[12]\n"
            "and so SGEIE are implementation-defined",
        ),
        "csrw mie, zero",
        "csrw hvip, zero",
    ]
    for name, csr, value, guard in (
        ("hie_444", "hie", "MIP_VS_MASK", None),
        ("hie_1444", "hie", "MIP_HS_MASK", "UDB_NUM_EXTERNAL_GUEST_INTERRUPTS >= 1"),
        ("hvip_444", "hvip", "MIP_VS_MASK", None),
    ):
        lines.extend(
            [
                *([f"#if {guard}"] if guard else []),
                "csrw hie, zero",
                f"LI(x{tmp_reg}, {value})",
                f"csrw {csr}, x{tmp_reg}",
                f"LI(x{tmp_reg}, MIP_HS_MASK)",
                test_data.add_testcase(f"{name}_mie", "cp_mie_mip", _CG),
                f"csrr x{check_reg}, mie",
                f"and x{check_reg}, x{check_reg}, x{tmp_reg}",
                write_sigupd(check_reg, test_data),
                test_data.add_testcase(f"{name}_mip", "cp_mie_mip", _CG),
                f"csrr x{check_reg}, mip",
                f"and x{check_reg}, x{check_reg}, x{tmp_reg}",
                write_sigupd(check_reg, test_data),
                *([f"csrr x{check_reg}, hip", write_sigupd(check_reg, test_data)] if csr == "hvip" else []),
                *(["#endif"] if guard else []),
            ]
        )
    lines.extend(["csrw hie, zero", "csrw hvip, zero"])
    test_data.int_regs.return_registers([tmp_reg, check_reg])
    return lines


def _priority_level_tests(test_data: TestData, mode: str) -> list[str]:
    """Enter VS or VU mode with interrupts pending for two or three of M-mode (MSI), HS-mode (SSI, delegated by
    mideleg) and VS-mode (VSSI, delegated by hideleg).  They are taken in the order M, HS, VS."""
    coverpoint = "cp_priority_levels"
    tmp_reg = test_data.int_regs.get_register()
    levels = {
        "m": ("MSI", "MSW", "UDB_MSI_INTR_IMPL"),
        "hs": ("SSI", "SSW", "UDB_SSI_INTR_IMPL"),
        "vs": ("VSSI", "VSSW", None),
    }
    lines = [
        comment_banner(
            coverpoint,
            "With mstatus.MIE = 0, mideleg.SSI = 1, hideleg.VSSI = 1, mie.MSIE = mie.SSIE = mie.VSSIE = 1 and\n"
            f"vsstatus.SIE = 1, raise two or three of MSI, SSI and VSSI and enter {mode}-mode.  M-mode takes MSI,\n"
            "then HS-mode takes SSI, then VS-mode takes VSSI",
        ),
        "csrci mstatus, MSTATUS_MIE",
        f"LI(x{tmp_reg}, MIP_SSIP)",
        f"csrw mideleg, x{tmp_reg}",
        f"LI(x{tmp_reg}, MIP_VSSIP)",
        f"csrw hideleg, x{tmp_reg}",
        f"LI(x{tmp_reg}, SSTATUS_SIE)",
        f"csrs vsstatus, x{tmp_reg}",
    ]
    for combo in (("m", "hs"), ("m", "vs"), ("hs", "vs"), ("m", "hs", "vs")):
        guards = [levels[level][2] for level in combo if levels[level][2]]
        lines.extend(
            [
                *[f"#ifdef {guard}" for guard in guards],
                f"LI(x{tmp_reg}, MIP_MSIP | MIP_SSIP | MIP_VSSIP)",
                f"csrw mie, x{tmp_reg}",
                *[f"RVTEST_SET_{levels[level][1]}_INT_M" for level in combo],
                f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg})",
                test_data.add_testcase("_".join([mode.lower(), *combo]), coverpoint, _CG),
                f"RVTEST_TSBI_GOTO_{mode}MODE",
                f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg})",
                "RVTEST_TSBI_GOTO_MMODE",
                *[f"RVTEST_CLR_{levels[level][1]}_INT_M" for level in combo],
                "csrw mie, zero",
                *[f"#endif // {guard}" for guard in reversed(guards)],
            ]
        )
    lines.extend(["csrw mideleg, zero", "csrw hideleg, zero"])
    test_data.int_regs.return_register(tmp_reg)
    return lines


@add_priv_test_generator(
    "Interrupts",
    required_extensions=["Sm", "H"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_interrupts_sm_h(test_data: TestData) -> list[TestChunk]:
    """Interrupts_Sm tests of the hypervisor interrupt CSRs from M-mode and of interrupt levels in VS and VU modes."""
    test_chunks: list[TestChunk] = []

    tc = test_data.new_test_chunk(test_chunks, "Sm_h_mcsr")
    tc.code.extend(_mcsr_tests(test_data))

    tc = test_data.new_test_chunk(test_chunks, "Sm_h_priority_levels")
    tc.code.extend([*_priority_level_tests(test_data, "VS"), *_priority_level_tests(test_data, "VU")])

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
