##################################
# ExceptionsZicboSm.py
#
# ExceptionsZicboSm privileged extension test generator.
# aman.murad@10xengineers.ai August 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Zicbo extension exception test generator (machine-mode only)."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ExceptionsZicboCommon import (
    cbo_access_fault_helper,
    cbo_config_helper,
    cbo_misaligned_helper,
)
from testgen.priv.registry import add_priv_test_generator

_CG = "ExceptionsZicboSm_cg"


@add_priv_test_generator(
    "ExceptionsZicboSm",
    required_extensions=["Sm", ["Zicbom", "Zicboz", "Zicbop"]],
    march_extensions=["Zicbom", "Zicboz", "Zicbop"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_exceptionszicbosm(test_data: TestData) -> list[TestChunk]:
    """Generate tests for ExceptionsZicboSm coverpoints"""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()

    tc.code.extend(
        cbo_config_helper(
            test_data,
            _CG,
            coverpoint="cp_cbie",
            tag="cbie",
            shift=4,
            bins=["00", "01", "11"],
            instrs=["cbo.inval"],
            guard="ZICBOM_SUPPORTED",
            description="Execute cbo.inval in machine mode with menvcfg.cbie = {00/01/11}",
            use_tsbi=False,
        )
    )
    tc.code.extend(
        cbo_config_helper(
            test_data,
            _CG,
            coverpoint="cp_cbcfe",
            tag="cbcfe",
            shift=6,
            bins=["0", "1"],
            instrs=["cbo.clean", "cbo.flush"],
            guard="ZICBOM_SUPPORTED",
            description="Execute cbo.{clean, flush} in machine mode with menvcfg.cbcfe = {0/1}",
            use_tsbi=False,
        )
    )
    tc.code.extend(
        cbo_config_helper(
            test_data,
            _CG,
            coverpoint="cp_cbze",
            tag="cbze",
            shift=7,
            bins=["0", "1"],
            instrs=["cbo.zero"],
            guard="ZICBOZ_SUPPORTED",
            description="Execute cbo.zero in machine mode with menvcfg.cbze = {0/1}",
            use_tsbi=False,
        )
    )
    tc.code.extend(
        cbo_access_fault_helper(
            test_data,
            _CG,
            description=(
                "For each supported cbo op {inval, clean, flush, zero, prefetch.{i/w/r}} "
                "Execute op to ACCESS_FAULT_ADDR in machine mode with menvcfg enabled"
            ),
            use_tsbi=False,
        )
    )
    tc.code.extend(
        cbo_misaligned_helper(
            test_data,
            _CG,
            description=(
                "For each supported cbo op {inval, clean, flush, zero, prefetch.{i/w/r}} "
                "Execute op to valid address + 1 in machine mode with menvcfg enabled"
            ),
            use_tsbi=False,
        )
    )

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
