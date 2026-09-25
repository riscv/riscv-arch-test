##################################
# priv/extensions/SstcS.py
#
# SstcS privileged extension test generator.
# sanarayanan@hmc.edu April 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Sstc stimecmp access test generator (supervisor and user modes)."""

from testgen.asm.helpers import comment_banner
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.SstcCommon import stce_tests, tm_tests
from testgen.priv.registry import add_priv_test_generator

_CG = "SstcS_cg"
_MODES = ["S", "U"]


def _tsbi_stimecmp_max(reg: int) -> list[str]:
    """stimecmp = -1 through T-SBI, for use while STCE=0 makes stimecmp inaccessible below M-mode."""
    return [
        f"LI(x{reg}, -1)",
        "#if __riscv_xlen == 32",
        tsbi_call(f"csrw stimecmph, x{reg}"),
        "#endif",
        tsbi_call(f"csrw stimecmp, x{reg}"),
    ]


def emit_lower_tests(test_data: TestData, covergroup: str, mode: str) -> list[TestChunk]:
    """All Sstc tests for one lower mode as one chunk; starts and ends in S-mode."""
    tc = test_data.begin_test_chunk()
    r_scratch = test_data.int_regs.get_register()
    tc.code = [
        comment_banner("SstcS", f"Supervisor timer (Sstc) stimecmp access tests from {mode}-mode"),
        "",
        "# Boot state: mcounteren=-1, scounteren=-1, STCE=0, so S-mode can access stimecmp once",
        "# STCE=1 and only mcounteren.TM/STCE gate U-mode reads. stimecmp has no reset value, so",
        "# park it at -1 before any test sets STCE.",
        *_tsbi_stimecmp_max(r_scratch),
        "",
    ]
    test_data.int_regs.return_registers([r_scratch])
    tc.code += tm_tests(test_data, covergroup, mode)
    tc.code += stce_tests(test_data, covergroup, mode)
    return [test_data.end_test_chunk()]


@add_priv_test_generator(
    "SstcS",
    required_extensions=["S", "Sstc"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_sstcs(test_data: TestData) -> list[TestChunk]:
    """Generate tests for SstcS coverpoints."""
    test_chunks: list[TestChunk] = []
    for mode in _MODES:
        test_chunks.extend(emit_lower_tests(test_data, _CG, mode))
    return test_chunks
