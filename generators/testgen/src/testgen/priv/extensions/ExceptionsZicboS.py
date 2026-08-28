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
_MODES = ["1", "0"]  # supervisor, then user


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
            description=(
                "Execute cbo.inval in {supervisor/user} mode with {menvcfg x senvcfg}.cbie = "
                "{00/01/11 x 00/01/11}, via T-SBI"
            ),
            use_tsbi=True,
            modes=_MODES,
            cross_senvcfg=True,
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
            description=(
                "Execute cbo.{clean, flush} in {supervisor/user} mode with {menvcfg x senvcfg}.cbcfe = "
                "{0/1 x 0/1}, via T-SBI"
            ),
            use_tsbi=True,
            modes=_MODES,
            cross_senvcfg=True,
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
            description=(
                "Execute cbo.zero in {supervisor/user} mode with {menvcfg x senvcfg}.cbze = {0/1 x 0/1}, via T-SBI"
            ),
            use_tsbi=True,
            modes=_MODES,
            cross_senvcfg=True,
        )
    )
    tc.code.extend(
        cbo_access_fault_helper(
            test_data,
            _CG,
            description=(
                "For each supported cbo op {inval, clean, flush, zero, prefetch.{i/w/r}} "
                "Execute op to RVMODEL_ACCESS_FAULT_ADDRESS in {supervisor/user} mode with menvcfg "
                "and senvcfg enabled, via T-SBI"
            ),
            use_tsbi=True,
            modes=_MODES,
            cross_senvcfg=True,
        )
    )
    tc.code.extend(
        cbo_misaligned_helper(
            test_data,
            _CG,
            description=(
                "For each supported cbo op {inval, clean, flush, zero, prefetch.{i/w/r}} "
                "Execute op to valid address + 1 in {supervisor/user} mode with menvcfg and senvcfg "
                "enabled, via T-SBI"
            ),
            use_tsbi=True,
            modes=_MODES,
            cross_senvcfg=True,
        )
    )

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
