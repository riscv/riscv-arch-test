##################################
# priv/extensions/InterruptsHSm.py
#
# Hypervisor interrupt tests that run in M-mode or need M-mode to set up delegation.
# David_Harris@hmc.edu 25 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""InterruptsHSm hypervisor interrupt test generator.

The suite boots to M-mode.  mideleg is zero except for the VS-level interrupts (and SGEI when GEILEN > 0),
which are always delegated to HS-mode.
"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.InterruptsCommon import (
    REG_TRIGGER_DEFINES,
    guard_symbol,
    int_macro,
    interrupt_xtinst_tests,
)
from testgen.priv.registry import add_priv_test_generator

_CG = "InterruptsHSm_m_cg"


def _mcsr_tests(test_data: TestData) -> list[str]:
    """mideleg, mie and mip bits for the VS-level interrupts and SGEI, seen from M-mode."""
    tmp_reg, check_reg = test_data.int_regs.get_registers(2)
    lines = [
        comment_banner(
            "cp_mideleg",
            "Write mideleg = 0.  Bits 10, 6 and 2 read 1, and bit 12 reads 1 when GEILEN > 0.  GEILEN > 0\n"
            "exactly when some hgeie bit is writable; bit 12 is unspecified otherwise, so it is not checked",
        ),
        f"LI(x{tmp_reg}, -1)",
        f"csrw hgeie, x{tmp_reg}",
        f"csrr x{tmp_reg}, hgeie",
        "csrw hgeie, zero",
        f"snez x{tmp_reg}, x{tmp_reg}",
        f"slli x{tmp_reg}, x{tmp_reg}, 12",
        f"ori x{tmp_reg}, x{tmp_reg}, MIP_VS_MASK",
        test_data.add_testcase("zeros", "cp_mideleg", _CG),
        "csrw mideleg, zero",
        f"csrr x{check_reg}, mideleg",
        f"and x{check_reg}, x{check_reg}, x{tmp_reg}",
        write_sigupd(check_reg, test_data),
        comment_banner("cp_mie", "With hie = 0x444, read mie"),
        "csrw mie, zero",
        f"LI(x{tmp_reg}, MIP_VS_MASK)",
        f"csrw hie, x{tmp_reg}",
        test_data.add_testcase("hie_444", "cp_mie", _CG),
        f"csrr x{check_reg}, mie",
        write_sigupd(check_reg, test_data),
        comment_banner(
            "cp_mie_gilen", "With hie = 0x1444, read mie.  SGEIE is writable if GEILEN > 0 and read-only 0 otherwise"
        ),
        f"LI(x{tmp_reg}, MIP_HS_MASK)",
        f"csrw hie, x{tmp_reg}",
        test_data.add_testcase("hie_1444", "cp_mie_gilen", _CG),
        f"csrr x{check_reg}, mie",
        write_sigupd(check_reg, test_data),
        "csrw hie, zero",
        comment_banner("cp_mip", "With hvip = 0x444, read the VS-level and SGEI bits of mip, and hip"),
        f"LI(x{tmp_reg}, MIP_VS_MASK)",
        f"csrw hvip, x{tmp_reg}",
        f"LI(x{tmp_reg}, MIP_HS_MASK)",
        test_data.add_testcase("hvip_444", "cp_mip", _CG),
        f"csrr x{check_reg}, mip",
        f"and x{check_reg}, x{check_reg}, x{tmp_reg}",
        write_sigupd(check_reg, test_data),
        f"csrr x{check_reg}, hip",
        write_sigupd(check_reg, test_data),
        comment_banner(
            "cp_nohint_m",
            "With hvip = mie = 0x444, hideleg = 0 and mstatus.MIE = 1, M-mode takes no interrupt: the VS-level\n"
            "interrupts are always delegated to HS-mode",
        ),
        "csrw hideleg, zero",
        f"LI(x{tmp_reg}, MIP_VS_MASK)",
        f"csrw hvip, x{tmp_reg}",
        f"csrw mie, x{tmp_reg}",
        test_data.add_testcase("mie_444", "cp_nohint_m", _CG),
        "csrsi mstatus, MSTATUS_MIE",
        f"RVTEST_IDLE_FOR_INTERRUPT(x{check_reg})",
        "csrci mstatus, MSTATUS_MIE",
        f"csrr x{check_reg}, hip",
        write_sigupd(check_reg, test_data),
        "csrw hvip, zero",
        "csrw mie, zero",
    ]
    test_data.int_regs.return_registers([tmp_reg, check_reg])
    return lines


def _mideleg_mip_tests(test_data: TestData, mode: str) -> list[str]:
    """With mideleg = 0 or 1s, enter VS or VU mode with one M-level or S-level interrupt pending.

    M-mode takes the M-level interrupts, and the S-level ones unless mideleg delegates them, in which case
    HS-mode takes them.
    """
    coverpoint = f"cp_mideleg_mip_{mode.lower()}"
    tmp_reg = test_data.int_regs.get_register()
    lines = [
        comment_banner(
            coverpoint,
            f"With mstatus.MIE = 0, mie = 1s and mideleg = 0/1s, raise MEI, MTI, MSI, SEI, STI or SSI and enter\n"
            f"{mode}-mode.  M-mode takes the interrupt, or HS-mode when mideleg delegates it",
        ),
        "csrci mstatus, MSTATUS_MIE",
    ]
    for deleg in (0, -1):
        for int_type in ["MEI", "MTI", "MSI", "SEI", "STI", "SSI"]:
            macro = int_macro[int_type]
            guard = guard_symbol(int_type)
            lines.extend(
                [
                    f"#ifdef {guard}",
                    f"LI(x{tmp_reg}, {deleg})",
                    f"csrw mideleg, x{tmp_reg}",
                    f"LI(x{tmp_reg}, -1)",
                    f"csrw mie, x{tmp_reg}",
                    f"RVTEST_SET_{macro}_INT_M",
                    f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg})",
                    test_data.add_testcase(
                        f"mideleg_{'ones' if deleg else 'zeros'}_{int_type.lower()}", coverpoint, _CG
                    ),
                    f"RVTEST_TSBI_GOTO_{mode}MODE",
                    f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg})",
                    "RVTEST_TSBI_GOTO_MMODE",
                    f"RVTEST_CLR_{macro}_INT_M",
                    "csrw mie, zero",
                    f"#endif // {guard}",
                ]
            )
    lines.append("csrw mideleg, zero")
    test_data.int_regs.return_register(tmp_reg)
    return lines


@add_priv_test_generator(
    "InterruptsHSm",
    required_extensions=["Sm", "H"],
    extra_defines=[*REG_TRIGGER_DEFINES, "#define BOOT_TO_MMODE"],
    # VS and VU traps need the visible trap handler
    params=["TIME_CSR_IMPLEMENTED: true"],
)
def make_interruptshsm(test_data: TestData) -> list[TestChunk]:
    """Generate tests for the InterruptsHSm hypervisor interrupt suite."""
    test_chunks: list[TestChunk] = []

    tc = test_data.new_test_chunk(test_chunks, "mcsr")
    tc.code.extend([*_mcsr_tests(test_data), *interrupt_xtinst_tests(test_data, _CG, "M")])

    tc = test_data.new_test_chunk(test_chunks, "mideleg_mip")
    tc.code.extend([*_mideleg_mip_tests(test_data, "VS"), *_mideleg_mip_tests(test_data, "VU")])

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
