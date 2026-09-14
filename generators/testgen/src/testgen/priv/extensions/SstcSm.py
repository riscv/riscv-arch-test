##################################
# priv/extensions/SstcSm.py
#
# SstcSm privileged extension test generator.
# sanarayanan@hmc.edu April 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Sstc stimecmp access test generator (machine-mode only)."""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.SstcCommon import stce_tests, tm_tests
from testgen.priv.registry import add_priv_test_generator

_CG = "SstcSm_cg"


@add_priv_test_generator(
    "SstcSm",
    required_extensions=["Sm", "S", "Sstc"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_sstcsm(test_data: TestData) -> list[TestChunk]:
    """Generate tests for SstcSm coverpoints; the suite boots to and stays in M-mode."""
    tc = test_data.begin_test_chunk()
    tc.code = [
        comment_banner("SstcSm", "Supervisor timer (Sstc) stimecmp access tests from M-mode"),
        "",
    ]
    tc.code += tm_tests(test_data, _CG, "Sm")
    tc.code += stce_tests(test_data, _CG, "Sm")
    return [test_data.end_test_chunk()]
