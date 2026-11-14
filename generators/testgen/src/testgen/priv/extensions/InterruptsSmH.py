##################################
# priv/extensions/InterruptsSmH.py
#
# Interrupts_Sm_cg hypervisor interrupt tests that run in M-mode or need M-mode to set up delegation.
# David_Harris@hmc.edu 25 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Interrupts_Sm hypervisor interrupt test generator.

The group boots to M-mode.  mideleg is zero except for the VS-level interrupts (and SGEI when GEILEN > 0),
which are always delegated to HS-mode.
"""

from itertools import product

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.InterruptsCommon import ALIAS_OPS, IE_CSRS, IP_CSRS, alias_readback, alias_write_tests
from testgen.priv.extensions.InterruptsSm import COVERGROUP as _CG
from testgen.priv.registry import add_priv_test_generator


def _mcsr_tests(test_data: TestData) -> list[str]:
    """The VS-level and SGEI bits of mip, hvip, hip, vsip, mie, hie and vsie, written and read from M-mode."""
    ip_readers = ("mip", "hip", "hvip", "vsip", "sip")
    ie_readers = ("mie", "hie", "vsie", "sie")
    lines = [
        comment_banner(
            "cp_mie_mip",
            "With hideleg = 0x444, csrw, csrs and csrc each VS-level interrupt bit, and all three, in each of mip,\n"
            "hvip, hip and vsip, starting with the bits clear and set in hvip, and read back mip, hip, hvip, vsip\n"
            "and sip.  Only hvip and the VSSIP aliases are writable, and sip never shows the VS-level bits.\n"
            "Likewise write mie, hie and vsie, starting from hie, and read back mie, hie, vsie and sie",
        ),
        "csrw mie, zero",
        *alias_write_tests(test_data, _CG, "cp_mie_mip", IP_CSRS, "hvip", ip_readers, "M", (("", 0x444),)),
        *alias_write_tests(test_data, _CG, "cp_mie_mip", IE_CSRS, "hie", ie_readers, "M", (("", 0x444),)),
    ]
    # SGEIP is read-only in mip and hip and read-only zero in hvip.  SGEIE is writable in mie and hie when
    # GEILEN > 0; otherwise mideleg[12] and so SGEIE are implementation-defined
    val_reg, check_reg, mask_reg = test_data.int_regs.get_registers(3, exclude_regs=[10, 11])
    lines.extend(
        [
            comment_banner(
                "cp_mie_mip_sgei",
                "With GEILEN > 0 and hgeie = 0, csrw, csrs and csrc bit 12 in mip, hvip, hip, mie and hie, and read\n"
                "back mip, hip, hvip, mie and hie.  Only mie.SGEIE and hie.SGEIE are writable",
            ),
            "#ifdef RVTEST_SGEI_INTR_IMPL",
            "csrw hgeie, zero",
        ]
    )
    for csr, op in product(("mip", "hvip", "hip", "mie", "hie"), ALIAS_OPS):
        lines.extend(
            [
                "csrw hvip, zero",
                "csrw hie, zero",
                f"LI(x{val_reg}, MIP_SGEIP)",
                test_data.add_testcase(f"{csr}_{op}_sgei", "cp_mie_mip_sgei", _CG),
                f"{op} {csr}, x{val_reg}",
                *alias_readback(test_data, ("mip", "hip", "hvip", "mie", "hie"), check_reg, mask_reg, "M"),
            ]
        )
    lines.extend(["csrw hie, zero", "#endif"])
    test_data.int_regs.return_registers([val_reg, check_reg, mask_reg])
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
