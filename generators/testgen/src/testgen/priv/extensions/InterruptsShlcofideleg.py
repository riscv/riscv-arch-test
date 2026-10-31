##################################
# priv/extensions/InterruptsShlcofideleg.py
#
# Interrupts_Shlcofideleg and Interrupts_SmShlcofideleg groups: delegation of LCOFI to VS-mode.
# David_Harris@hmc.edu 25 October 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Interrupts test generator for Shlcofideleg, which makes hideleg[13] writable so LCOFI can be delegated to VS-mode.

Interrupts_Shlcofideleg boots to HS-mode, where mideleg delegates LCOFI.  With hideleg[13] = 1, LCOFI goes to
VS-mode: HS-mode and U-mode never take it, VS-mode takes it (as cause 13) when vsstatus.SIE = 1 and VU-mode always
does.  vsip.LCOFIP and vsie.LCOFIE are aliases of sip.LCOFIP and sie.LCOFIE, and read zero when hideleg[13] = 0.

Interrupts_SmShlcofideleg boots to M-mode with mideleg[13] = 0, which makes hideleg[13] read-only zero, so LCOFI
goes to M-mode from every mode.
"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.InterruptsCommon import goto_mode
from testgen.priv.registry import add_priv_test_generator

_CG = "Interrupts_Shlcofideleg_cg"
_CG_SM = "Interrupts_SmShlcofideleg_cg"


def _trigger_tests(test_data: TestData) -> list[str]:
    """Raise LCOFI with hideleg[13] = 1 in each mode below M, with vsstatus.SIE = 0/1."""
    tmp_reg = test_data.int_regs.get_register()
    lines = [
        comment_banner(
            "cp_trigger_lcofi_vs",
            "With hideleg[13] = 1, sie.LCOFIE = 1 and vsstatus.SIE = 0/1, raise LCOFI in HS, U, VS or VU mode.\n"
            "HS-mode and U-mode never take it; VS-mode takes cause 13 when vsstatus.SIE = 1 and VU-mode always does",
        ),
        "csrci sstatus, SSTATUS_SIE",
    ]
    for mode, goto in goto_mode.items():
        flavor = "S" if mode == "HS" else "U"
        for sie in (0, 1):
            lines.extend(
                [
                    f"LI(x{tmp_reg}, MIP_LCOFIP)",
                    f"csrw hideleg, x{tmp_reg} # hideleg delegates LCOFI to VS-mode",
                    f"csrw sie, x{tmp_reg} # sie.LCOFIE = 1",
                    f"LI(x{tmp_reg}, SSTATUS_SIE)",
                    f"csr{'s' if sie else 'c'} vsstatus, x{tmp_reg} # vsstatus.SIE = {sie}",
                    test_data.add_testcase(f"{mode.lower()}_vsstatus_sie{sie}", "cp_trigger_lcofi_vs", _CG),
                    *([] if mode == "HS" else [f"RVTEST_TSBI_GOTO_{goto}MODE"]),
                    f"RVTEST_SET_LCOFI_INT_{flavor}",
                    f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg})",
                    f"RVTEST_CLR_LCOFI_INT_{flavor}",
                    *([] if mode == "HS" else ["RVTEST_TSBI_GOTO_SMODE"]),
                    f"csrr x{tmp_reg}, sie # LCOFIE is cleared only if VS-mode took LCOFI",
                    write_sigupd(tmp_reg, test_data),
                ]
            )
    lines.extend(
        [
            "csrw sie, zero",
            "csrw hideleg, zero",
            f"LI(x{tmp_reg}, SSTATUS_SIE)",
            f"csrc vsstatus, x{tmp_reg}",
        ]
    )
    test_data.int_regs.return_register(tmp_reg)
    return lines


def _alias_tests(test_data: TestData) -> list[str]:
    """vsip.LCOFIP and vsie.LCOFIE alias sip.LCOFIP and sie.LCOFIE when hideleg[13] = 1 and read zero otherwise."""
    tmp_reg = test_data.int_regs.get_register()
    lines = [
        comment_banner(
            "cp_vsip_vsie_lcofi",
            "With hideleg[13] = 0/1 and sip.LCOFIP = sie.LCOFIE = 1, read vsie and vsip, then write vsie = 0 and\n"
            "read sie, and write vsip = 0 and read sip.  The writes clear the bits only when hideleg[13] = 1",
        ),
        "csrci sstatus, SSTATUS_SIE",
    ]
    for deleg in (0, 1):
        lines.extend(
            [
                f"LI(x{tmp_reg}, {deleg << 13:#x})",
                f"csrw hideleg, x{tmp_reg}",
                f"LI(x{tmp_reg}, MIP_LCOFIP)",
                f"csrs sie, x{tmp_reg}",
                f"csrs sip, x{tmp_reg}",
                test_data.add_testcase(f"hideleg{deleg}_csrr_vsie", "cp_vsip_vsie_lcofi", _CG),
                f"csrr x{tmp_reg}, vsie",
                write_sigupd(tmp_reg, test_data),
                test_data.add_testcase(f"hideleg{deleg}_csrr_vsip", "cp_vsip_vsie_lcofi", _CG),
                f"csrr x{tmp_reg}, vsip",
                write_sigupd(tmp_reg, test_data),
                test_data.add_testcase(f"hideleg{deleg}_csrw_vsie", "cp_vsip_vsie_lcofi", _CG),
                "csrw vsie, zero",
                f"csrr x{tmp_reg}, sie",
                write_sigupd(tmp_reg, test_data),
                test_data.add_testcase(f"hideleg{deleg}_csrw_vsip", "cp_vsip_vsie_lcofi", _CG),
                "csrw vsip, zero",
                f"csrr x{tmp_reg}, sip",
                write_sigupd(tmp_reg, test_data),
                f"LI(x{tmp_reg}, MIP_LCOFIP)",
                f"csrc sip, x{tmp_reg}",
                f"csrc sie, x{tmp_reg}",
            ]
        )
    lines.append("csrw hideleg, zero")
    test_data.int_regs.return_register(tmp_reg)
    return lines


def _trigger_sm_tests(test_data: TestData) -> list[str]:
    """With mideleg[13] = 0, writing hideleg[13] = 1 has no effect and LCOFI goes to M-mode from every mode."""
    tmp_reg, check_reg = test_data.int_regs.get_registers(2)
    lines = [
        comment_banner(
            "cp_trigger_lcofi_m",
            "With mideleg = 0, write hideleg[13] = 1 (it reads 0) and set mie.LCOFIE = 1 and vsstatus.SIE = 1.\n"
            "Raise LCOFI in M-mode with mstatus.MIE = 0/1, or with MIE = 0 and then enter HS, U, VS or VU mode.\n"
            "M-mode takes it when MIE = 1 and on the mret into every other mode.  VS-mode reads vsip.LCOFIP = 0",
        ),
        "csrw mideleg, zero",
    ]
    # M-mode takes LCOFI as it is raised when mstatus.MIE = 1; the other modes take it on the mret into the mode
    for mode, mie in [("M", 0), ("M", 1), *[(mode, 0) for mode in goto_mode]]:
        name = f"m_mie{mie}" if mode == "M" else mode.lower()
        if mode == "M":
            enter = []
        else:
            enter = [
                f"RVTEST_TSBI_GOTO_{goto_mode[mode]}MODE",
                f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg})",
                *(
                    [f"csrr x{check_reg}, sip # vsip.LCOFIP reads 0", write_sigupd(check_reg, test_data)]
                    if mode == "VS"
                    else []
                ),
                "RVTEST_TSBI_GOTO_MMODE",
            ]
        lines.extend(
            [
                test_data.add_testcase(name, "cp_trigger_lcofi_m", _CG_SM),
                f"LI(x{tmp_reg}, MIP_LCOFIP)",
                f"csrw hideleg, x{tmp_reg} # read-only zero because mideleg[13] = 0",
                f"csrr x{check_reg}, hideleg",
                write_sigupd(check_reg, test_data),
                f"csrw mie, x{tmp_reg} # mie.LCOFIE = 1",
                f"LI(x{tmp_reg}, SSTATUS_SIE)",
                f"csrs vsstatus, x{tmp_reg} # vsstatus.SIE = 1",
                f"csr{'s' if mie else 'c'}i mstatus, MSTATUS_MIE",
                "RVTEST_SET_LCOFI_INT_M",
                f"RVTEST_IDLE_FOR_INTERRUPT(x{tmp_reg})",
                "csrci mstatus, MSTATUS_MIE",
                *enter,
                "RVTEST_CLR_LCOFI_INT_M",
                f"csrr x{check_reg}, mie # LCOFIE is cleared when M-mode took LCOFI",
                write_sigupd(check_reg, test_data),
                "csrw mie, zero",
            ]
        )
    lines.extend(["csrw hideleg, zero", f"LI(x{tmp_reg}, SSTATUS_SIE)", f"csrc vsstatus, x{tmp_reg}"])
    test_data.int_regs.return_registers([tmp_reg, check_reg])
    return lines


@add_priv_test_generator(
    "Interrupts",
    required_extensions=["H", "Sscofpmf", "Shlcofideleg"],
    # The toolchain does not know Shlcofideleg, which adds no instructions
    march_extensions=["H", "Sscofpmf"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_interrupts_shlcofideleg(test_data: TestData) -> list[TestChunk]:
    """Interrupts_Shlcofideleg tests of LCOFI delegated to VS-mode."""
    test_chunks: list[TestChunk] = []

    tc = test_data.new_test_chunk(test_chunks, "Shlcofideleg")
    tc.code.extend([*_trigger_tests(test_data), *_alias_tests(test_data)])

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks


@add_priv_test_generator(
    "Interrupts",
    required_extensions=["Sm", "H", "Sscofpmf", "Shlcofideleg"],
    # The toolchain does not know Shlcofideleg, which adds no instructions
    march_extensions=["H", "Sscofpmf"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_interrupts_smshlcofideleg(test_data: TestData) -> list[TestChunk]:
    """Interrupts_SmShlcofideleg tests of LCOFI with mideleg[13] = 0."""
    test_chunks: list[TestChunk] = []

    tc = test_data.new_test_chunk(test_chunks, "SmShlcofideleg")
    tc.code.extend(_trigger_sm_tests(test_data))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
