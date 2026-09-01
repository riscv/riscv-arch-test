##################################
# ExceptionsZicboU.py
#
# ExceptionsZicboU privileged extension test generator.
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

_CG = "ExceptionsZicboU_cg"
_MODE = "U"


@add_priv_test_generator(
    "ExceptionsZicboU",
    required_extensions=["U", ["Zicbom", "Zicboz", "Zicbop"]],
    march_extensions=["Zicbom", "Zicboz", "Zicbop"],
)
def make_exceptionszicbou(test_data: TestData) -> list[TestChunk]:
    """Generate tests for ExceptionsZicboU coverpoints"""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()

    tc.code.extend(
        cbo_config_helper(
            test_data,
            _CG,
            "cbie",
            description="Execute cbo.inval in user mode with menvcfg.cbie = {00/01/11}, via T-SBI",
            mode=_MODE,
        )
    )
    tc.code.extend(
        cbo_config_helper(
            test_data,
            _CG,
            "cbcfe",
            description="Execute cbo.{clean, flush} in user mode with menvcfg.cbcfe = {0/1}, via T-SBI",
            mode=_MODE,
        )
    )
    tc.code.extend(
        cbo_config_helper(
            test_data,
            _CG,
            "cbze",
            description="Execute cbo.zero in user mode with menvcfg.cbze = {0/1}, via T-SBI",
            mode=_MODE,
        )
    )
    tc.code.extend(
        cbo_access_fault_helper(
            test_data,
            _CG,
            description=(
                "For each supported cbo op {inval, clean, flush, zero, prefetch.{i/w/r}} "
                "Execute op to ACCESS_FAULT_ADDR with menvcfg enabled"
            ),
            mode=_MODE,
        )
    )
    tc.code.extend(
        cbo_misaligned_helper(
            test_data,
            _CG,
            description=(
                "For each supported cbo op {inval, clean, flush, zero, prefetch.{i/w/r}} "
                "Execute op to valid address + 1 with menvcfg enabled"
            ),
            mode=_MODE,
        )
    )

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
