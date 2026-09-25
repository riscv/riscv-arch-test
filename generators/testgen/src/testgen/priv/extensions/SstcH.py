##################################
# priv/extensions/SstcH.py
#
# Sstc hypervisor tests that run in HS, VS, VU and U modes.
# David_Harris@hmc.edu 25 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""SstcH test generator.

The suite boots to HS-mode and writes menvcfg and mcounteren through T-SBI.  An access that menvcfg.STCE or
mcounteren.TM forbids raises illegal instruction; one that only henvcfg.STCE or hcounteren.TM forbids raises
virtual instruction.  Both are taken in HS-mode.
"""

from testgen.asm.csr import csr_access_test
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.PrivCommon import write64
from testgen.priv.extensions.SstcCommon import access_cross, rv32_only, stce_tm, vstimecmp_int_tests
from testgen.priv.registry import add_priv_test_generator

_HS_CG = "SstcH_hs_cg"
_VS_CG = "SstcH_vs_cg"
_VU_CG = "SstcH_vu_cg"
_U_CG = "SstcH_u_cg"
# Distinct values in the future for stimecmp and vstimecmp, and one VS-mode writes through stimecmp
STIMECMP = 0xAAAAAAAAAAAAAAAA
VSTIMECMP = 0x5555555555555555
VS_STIMECMP = 0x3333333333333333


def _setup_timecmps(test_data: TestData) -> list[str]:
    """Give stimecmp and vstimecmp distinct values; needs menvcfg.STCE = mcounteren.TM = 1 for the HS-mode writes."""
    tmp_reg = test_data.int_regs.get_register()
    lines = [
        *stce_tm(test_data, 1, 1, 1, 1, "supervisor"),
        *write64("stimecmp", STIMECMP, tmp_reg),
        *write64("vstimecmp", VSTIMECMP, tmp_reg),
    ]
    test_data.int_regs.return_register(tmp_reg)
    return lines


def _hs_tests(test_data: TestData) -> list[str]:
    """vstimecmp from HS-mode: access control by menvcfg.STCE and mcounteren.TM, and every access type.

    H cp_hcsrwalk walks vstimecmp.
    """
    lines = [
        comment_banner(
            "cp_hs_vstimecmp_accessible",
            "Read vstimecmp (and vstimecmph) for each value of menvcfg.STCE, henvcfg.STCE, mcounteren.TM and\n"
            "hcounteren.TM.  Illegal instruction when menvcfg.STCE = 0 or mcounteren.TM = 0",
        ),
        *_setup_timecmps(test_data),
        *access_cross(test_data, "cp_hs_vstimecmp_accessible", _HS_CG, "hs", ["vstimecmp", "vstimecmph"]),
        comment_banner(
            "cp_hs_vstimecmp_accesses",
            "With menvcfg.STCE = mcounteren.TM = 1 and henvcfg.STCE = hcounteren.TM = 0, write 1s and 0s to, set and\n"
            "clear vstimecmp (and vstimecmph)",
        ),
        *stce_tm(test_data, 1, 0, 1, 0, "supervisor"),
        *csr_access_test(test_data, ("vstimecmp", None), _HS_CG, "cp_hs_vstimecmp_accesses"),
        *rv32_only("vstimecmph", csr_access_test(test_data, ("vstimecmph", None), _HS_CG, "cp_hs_vstimecmp_accesses")),
        *stce_tm(test_data, 0, 0, 1, 1, "supervisor"),
    ]
    return lines


def _vs_tests(test_data: TestData) -> list[str]:
    """stimecmp in VS-mode is vstimecmp; vstimecmp by its own name is not accessible there."""
    tmp_reg, rd = test_data.int_regs.get_registers(2)
    lines = [
        comment_banner(
            "cp_vs_stimecmp_accessible",
            "With stimecmp and vstimecmp holding different values, read stimecmp (and stimecmph) in VS-mode for each\n"
            "value of menvcfg.STCE, henvcfg.STCE, mcounteren.TM and hcounteren.TM.  Illegal instruction when\n"
            "menvcfg.STCE = 0 or mcounteren.TM = 0, else virtual instruction when henvcfg.STCE = 0 or\n"
            "hcounteren.TM = 0, else the read returns vstimecmp",
        ),
        *_setup_timecmps(test_data),
        *access_cross(test_data, "cp_vs_stimecmp_accessible", _VS_CG, "vs", ["stimecmp", "stimecmph"]),
        comment_banner(
            "cp_vs_vstimecmp_inaccessible",
            "Read vstimecmp (and vstimecmph) in VS-mode for each value of menvcfg.STCE, henvcfg.STCE, mcounteren.TM\n"
            "and hcounteren.TM.  Illegal instruction when HS-mode could not access it, else virtual instruction",
        ),
        *access_cross(test_data, "cp_vs_vstimecmp_inaccessible", _VS_CG, "vs", ["vstimecmp", "vstimecmph"]),
        comment_banner(
            "cp_vs_stimecmp_accesses",
            "With menvcfg.STCE = henvcfg.STCE = mcounteren.TM = hcounteren.TM = 1, write 1s and 0s to, set and clear\n"
            "stimecmp (and stimecmph) in VS-mode, then write it and check from HS-mode that vstimecmp changed and\n"
            "stimecmp did not",
        ),
        *stce_tm(test_data, 1, 1, 1, 1, "supervisor"),
        "RVTEST_TSBI_GOTO_VSMODE",
        *csr_access_test(test_data, ("stimecmp", None), _VS_CG, "cp_vs_stimecmp_accesses"),
        *rv32_only("stimecmph", csr_access_test(test_data, ("stimecmph", None), _VS_CG, "cp_vs_stimecmp_accesses")),
        test_data.add_testcase("write_then_read_from_hs", "cp_vs_stimecmp_accesses", _VS_CG),
        *write64("stimecmp", VS_STIMECMP, tmp_reg),
        "RVTEST_TSBI_GOTO_SMODE",
    ]
    for csr in ("vstimecmp", "vstimecmph", "stimecmp", "stimecmph"):
        lines.extend(rv32_only(csr, [f"csrr x{rd}, {csr}", write_sigupd(rd, test_data)]))
    lines.extend(stce_tm(test_data, 0, 0, 1, 1, "supervisor"))
    test_data.int_regs.return_registers([tmp_reg, rd])
    return lines


def _user_tests(test_data: TestData) -> list[str]:
    """stimecmp and vstimecmp are never accessible from VU-mode or U-mode."""
    csrs = ["stimecmp", "stimecmph", "vstimecmp", "vstimecmph"]
    return [
        comment_banner(
            "cp_vu_timecmp_inaccessible",
            "Read stimecmp and vstimecmp (and the upper halves) in VU-mode for each value of menvcfg.STCE,\n"
            "henvcfg.STCE, mcounteren.TM and hcounteren.TM.  Illegal instruction when HS-mode could not access\n"
            "them, else virtual instruction",
        ),
        *_setup_timecmps(test_data),
        *access_cross(test_data, "cp_vu_timecmp_inaccessible", _VU_CG, "vu", csrs),
        comment_banner(
            "cp_u_timecmp_inaccessible",
            "Read stimecmp and vstimecmp (and the upper halves) in U-mode for each value of menvcfg.STCE,\n"
            "henvcfg.STCE, mcounteren.TM and hcounteren.TM.  Always illegal instruction",
        ),
        *access_cross(test_data, "cp_u_timecmp_inaccessible", _U_CG, "u", csrs),
    ]


@add_priv_test_generator(
    "SstcH",
    required_extensions=["H", "Sstc"],
    extra_defines=["#define BOOT_TO_SMODE"],
    # VS and VU traps need the visible trap handler
    params=["TIME_CSR_IMPLEMENTED: true"],
)
def make_sstch(test_data: TestData) -> list[TestChunk]:
    """Generate tests for the SstcH suite."""
    test_chunks: list[TestChunk] = []

    tc = test_data.new_test_chunk(test_chunks, "hs")
    tc.code.extend([*_hs_tests(test_data), *vstimecmp_int_tests(test_data, _HS_CG, "supervisor")])

    tc = test_data.new_test_chunk(test_chunks, "vs")
    tc.code.extend(_vs_tests(test_data))

    tc = test_data.new_test_chunk(test_chunks, "vu")
    tc.code.extend(_user_tests(test_data))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
