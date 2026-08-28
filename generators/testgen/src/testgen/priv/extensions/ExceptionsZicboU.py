##################################
# ExceptionsZicboU.py
#
# ExceptionsZicboU privileged extension test generator.
# ellyu@g.hmc.edu March 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Zicbo extension exception test generator."""

from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ExceptionsZicboCommon import (
    cbo_access_fault_helper,
    cbo_config_helper,
    cbo_misaligned_helper,
)
from testgen.priv.registry import add_priv_test_generator

_CG = "ExceptionsZicboU_cg"


@add_priv_test_generator(
    "ExceptionsZicboU",
    required_extensions=["U"],
    march_extensions=["Zicbom", "Zicboz", "Zicbop"],
    extra_defines=["#define BOOT_TO_UMODE"],
)
def make_exceptionszicbou(test_data: TestData) -> list[TestChunk]:
    """Generate tests for ExceptionsZicboU coverpoints"""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()

    senvcfg_reg = test_data.int_regs.get_registers(1)[0]
    tc.code.extend(
        [
            "#ifdef S_SUPPORTED",
            f"LI(x{senvcfg_reg}, -1)",
            tsbi_call(f"csrw senvcfg, x{senvcfg_reg}"),
            "#endif",
        ]
    )
    test_data.int_regs.return_registers([senvcfg_reg])

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
            description="Execute cbo.inval in user mode with menvcfg.cbie = {00/01/11}, via T-SBI",
            use_tsbi=True,
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
            description="Execute cbo.{clean, flush} in user mode with menvcfg.cbcfe = {0/1}, via T-SBI",
            use_tsbi=True,
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
            description="Execute cbo.zero in user mode with menvcfg.cbze = {0/1}, via T-SBI",
            use_tsbi=True,
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
            use_tsbi=True,
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
            use_tsbi=True,
        )
    )

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
