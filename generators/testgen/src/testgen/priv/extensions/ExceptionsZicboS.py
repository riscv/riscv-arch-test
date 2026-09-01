##################################
# ExceptionsZicboS.py
#
# ExceptionsZicboS privileged extension test generator.
# ellyu@g.hmc.edu March 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Zicbo extension exception test generator."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ExceptionsZicboCommon import (
    cbo_access_fault_helper,
    cbo_config_helper,
    cbo_misaligned_helper,
)
from testgen.priv.registry import add_priv_test_generator

_CG = "ExceptionsZicboS_cg"
_MODES = ["S", "U"]  # supervisor, then user


@add_priv_test_generator(
    "ExceptionsZicboS",
    required_extensions=["S", ["Zicbom", "Zicboz", "Zicbop"]],
    march_extensions=["Zicbom", "Zicboz", "Zicbop"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_exceptionszicbos(test_data: TestData) -> list[TestChunk]:
    """Generate tests for ExceptionsZicboS coverpoints"""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()

    for mode in _MODES:
        tc.code.append(f"RVTEST_TSBI_GOTO_{mode}MODE  # enter {mode}-mode")
        tc.code.extend(
            cbo_config_helper(
                test_data,
                _CG,
                "cbie",
                description=(
                    f"Execute cbo.inval in {mode} mode with menvcfg x senvcfg.cbie crossed "
                    "over {00/01/11 x 00/01/11}, via T-SBI"
                ),
                mode=mode,
                cross_senvcfg=True,
            )
        )
        tc.code.extend(
            cbo_config_helper(
                test_data,
                _CG,
                "cbcfe",
                description=(
                    f"Execute cbo.{{clean, flush}} in {mode} mode with menvcfg x senvcfg.cbcfe "
                    "crossed over {0/1 x 0/1}, via T-SBI"
                ),
                mode=mode,
                cross_senvcfg=True,
            )
        )
        tc.code.extend(
            cbo_config_helper(
                test_data,
                _CG,
                "cbze",
                description=(
                    f"Execute cbo.zero in {mode} mode with menvcfg x senvcfg.cbze crossed over {{0/1 x 0/1}}, via T-SBI"
                ),
                mode=mode,
                cross_senvcfg=True,
            )
        )
        tc.code.extend(
            cbo_access_fault_helper(
                test_data,
                _CG,
                description=(
                    "For each supported cbo op {inval, clean, flush, zero, prefetch.{i/w/r}} "
                    f"Execute op to RVMODEL_ACCESS_FAULT_ADDRESS in {mode} mode with menvcfg "
                    "and senvcfg enabled, via T-SBI"
                ),
                mode=mode,
                cross_senvcfg=True,
            )
        )
        tc.code.extend(
            cbo_misaligned_helper(
                test_data,
                _CG,
                description=(
                    "For each supported cbo op {inval, clean, flush, zero, prefetch.{i/w/r}} "
                    f"Execute op to valid address + 1 in {mode} mode with menvcfg and senvcfg "
                    "enabled, via T-SBI"
                ),
                mode=mode,
                cross_senvcfg=True,
            )
        )

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
