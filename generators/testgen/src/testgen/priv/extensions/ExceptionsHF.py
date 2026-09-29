##################################
# priv/extensions/ExceptionsHF.py
#
# ExceptionsHF hypervisor floating-point exception tests: mstatus.FS and vsstatus.FS in each mode.
# David_Harris@hmc.edu 24 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ExceptionsHF test generator.

Boots to HS-mode; illegal instructions trap to HS-mode (hedeleg = 0).
"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ExceptionsHCommon import xstatus_tests
from testgen.priv.registry import add_priv_test_generator

CG = "ExceptionsHF_cg"


@add_priv_test_generator(
    "ExceptionsHF",
    required_extensions=["H", "F"],
    extra_defines=["#define BOOT_TO_SMODE"],
    # VS and VU traps need the visible trap handler
    params=["TIME_CSR_IMPLEMENTED: true"],
)
def make_exceptionshf(test_data: TestData) -> list[TestChunk]:
    """Generate tests for the ExceptionsHF hypervisor floating-point exception testsuite."""
    test_chunks: list[TestChunk] = []
    tc = test_data.new_test_chunk(test_chunks)
    temp_reg = test_data.int_regs.get_register()
    fd, fs1, fs2 = test_data.float_regs.get_registers(3)

    def body(suffix: str, rd: int) -> list[str]:
        """Read fcsr and execute fadd.s; each is illegal when either FS field in effect is Off."""
        return [
            f"LI(x{rd}, 42)",
            test_data.add_testcase(f"csrr_fcsr_{suffix}", "cp_exceptionsHF_fs", CG),
            f"csrr x{rd}, fcsr",
            write_sigupd(rd, test_data),
            test_data.add_testcase(f"fadd_{suffix}", "cp_exceptionsHF_fs", CG),
            f"fadd.s f{fd}, f{fs1}, f{fs2}",
        ]

    def check(rd: int) -> list[str]:
        """With FS enabled, check the fadd.s result, then clear it for the next test."""
        return [
            "RVTEST_TSBI_CSR_SET(CSR_MSTATUS, MSTATUS_FS)",
            f"fmv.x.w x{rd}, f{fd}",
            write_sigupd(rd, test_data),
            f"fmv.w.x f{fd}, x0",
        ]

    tc.code.extend(
        [
            comment_banner(
                "cp_exceptionsHF_fs",
                "In HS, VS, U and VU modes with mstatus.FS = 0-3 and vsstatus.FS = 0-3, read fcsr and execute\n"
                "fadd.s.  Each raises illegal instruction if mstatus.FS = Off, or if V = 1 and vsstatus.FS = Off.\n"
                "Otherwise fadd.s sets mstatus.FS, and vsstatus.FS when V = 1, to Dirty",
            ),
            "RVTEST_TSBI_CSR_SET(CSR_MSTATUS, MSTATUS_FS)",
            "csrw fcsr, zero",
            f"LI(x{temp_reg}, 1)",
            f"fcvt.s.w f{fs1}, x{temp_reg}",
            f"LI(x{temp_reg}, 2)",
            f"fcvt.s.w f{fs2}, x{temp_reg}",
            f"fmv.w.x f{fd}, x0",
            *xstatus_tests(test_data, "FS", body, check),
        ]
    )
    test_data.int_regs.return_register(temp_reg)
    test_data.float_regs.return_registers([fd, fs1, fs2])
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
