##################################
# priv/extensions/ExceptionsHV.py
#
# ExceptionsHV hypervisor vector exception tests: mstatus.VS and vsstatus.VS in each mode.
# David_Harris@hmc.edu 24 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ExceptionsHV test generator.

Boots to HS-mode; illegal instructions trap to HS-mode (hedeleg = 0).
"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ExceptionsHCommon import xstatus_tests
from testgen.priv.registry import add_priv_test_generator

CG = "ExceptionsHV_cg"


@add_priv_test_generator(
    "ExceptionsHV",
    required_extensions=["H", "V"],
    extra_defines=["#define BOOT_TO_SMODE", "#define RVTEST_VECTOR", "#define RVTEST_SEW 0", "#define VDSEW 0"],
    # VS and VU traps need the visible trap handler
    params=["TIME_CSR_IMPLEMENTED: true"],
)
def make_exceptionshv(test_data: TestData) -> list[TestChunk]:
    """Generate tests for the ExceptionsHV hypervisor vector exception testsuite."""
    test_chunks: list[TestChunk] = []
    tc = test_data.new_test_chunk(test_chunks)

    def read_add(suffix: str, rd: int) -> list[str]:
        """Read vl, which leaves vector state unchanged, and increment v1 with vadd.vv."""
        return [
            f"LI(x{rd}, 42)",
            test_data.add_testcase(f"csrr_vl_{suffix}", "cp_exceptionsHV_vs", CG),
            f"csrr x{rd}, vl",
            write_sigupd(rd, test_data),
            test_data.add_testcase(f"vadd_{suffix}", "cp_exceptionsHV_vs", CG),
            "vadd.vv v1, v1, v2",
        ]

    def check_add(rd: int) -> list[str]:
        """With VS enabled, record v1, which counts the vadd.vv instructions that executed."""
        return ["RVTEST_TSBI_CSR_SET(CSR_MSTATUS, MSTATUS_VS)", f"vmv.x.s x{rd}, v1", write_sigupd(rd, test_data)]

    def set_vl(suffix: str, rd: int) -> list[str]:
        """Change vl from 1 to 2 with vsetvli."""
        return [
            f"LI(x{rd}, 2)",
            test_data.add_testcase(f"vsetvli_{suffix}", "cp_exceptionsHV_vs", CG),
            f"vsetvli x0, x{rd}, e32, m1, tu, mu",
        ]

    def check_vl(rd: int) -> list[str]:
        """With VS enabled, record vl, then set it back to 1."""
        return [
            "RVTEST_TSBI_CSR_SET(CSR_MSTATUS, MSTATUS_VS)",
            f"csrr x{rd}, vl",
            write_sigupd(rd, test_data),
            "vsetivli x0, 1, e32, m1, tu, mu",
        ]

    tc.code.extend(
        [
            comment_banner(
                "cp_exceptionsHV_vs, cp_vsstatus_vs_set_dirty_arithmetic, cp_vsstatus_vs_set_dirty_csr",
                "In HS, VS, U and VU modes with mstatus.VS = 0-3 and vsstatus.VS = 0-3, read vl and increment v1\n"
                "with vadd.vv, then separately change vl from 1 to 2 with vsetvli.  Each raises illegal instruction\n"
                "if mstatus.VS = Off, or if V = 1 and vsstatus.VS = Off.  Otherwise vadd.vv and vsetvli change\n"
                "vector state, so they set mstatus.VS, and vsstatus.VS when V = 1, to Dirty",
            ),
            "RVTEST_TSBI_CSR_SET(CSR_MSTATUS, MSTATUS_VS)",
            "vsetivli x0, 1, e32, m1, tu, mu",
            "vmv.v.i v1, 0",
            "vmv.v.i v2, 1",
            *xstatus_tests(test_data, "VS", read_add, check_add),
            *xstatus_tests(test_data, "VS", set_vl, check_vl),
        ]
    )
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
