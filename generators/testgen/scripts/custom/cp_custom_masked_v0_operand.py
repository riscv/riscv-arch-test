# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_masked_v0_operand

Verify correct execution when an instruction is masked (vm=0) and uses
v0 as a source operand (v0 serves as both mask and source).

Template has 2 crosses:
- cp_custom_masked_vs2_v0: std_vec × mask_enabled × vs2=v0 × vd!=v0
- cp_custom_masked_vs1_v0: std_vec × mask_enabled × vs1=v0 × vd!=v0

We force vs2=v0 or vs1=v0 with masking enabled, ensuring vd != v0.
"""

from coverpoint_registry import register
import vector_testgen_common as common
from vector_testgen_common import (
    writeTest,
    randomizeVectorInstructionData,
    incrementBasetestCount,
    getBaseSuiteTestCount,
    vsAddressCount,
    vs1ins,
)

@register("cp_custom_masked_v0_operand")
def make(test, sew):
    # Part 1: masked with vs2=v0, vd != v0
    # Let the register assigner pick vd (respects EMUL alignment for LS instructions)
    description = f"cp_custom_masked_vs2_v0 ({test}, vs2=v0, masked)"
    try:
        data = randomizeVectorInstructionData(
            test, sew, getBaseSuiteTestCount(), lmul=1,
            vs2=0,
            additional_no_overlap=[['vd', 'v0']],
        )
        writeTest(description, test, data, sew=sew, lmul=1, vl=1, maskval="ones")
        incrementBasetestCount()
        vsAddressCount()
    except ValueError:
        pass  # overlap constraints unsolvable for this instruction/sew combo

    # Part 2: masked with vs1=v0, vd != v0 (only if instruction uses vs1)
    if test in vs1ins:
        description = f"cp_custom_masked_vs1_v0 ({test}, vs1=v0, masked)"
        try:
            data = randomizeVectorInstructionData(
                test, sew, getBaseSuiteTestCount(), lmul=1,
                vs1=0,
                additional_no_overlap=[['vd', 'v0']],
            )
            writeTest(description, test, data, sew=sew, lmul=1, vl=1, maskval="ones")
            incrementBasetestCount()
            vsAddressCount()
        except ValueError:
            pass  # overlap constraints unsolvable for this instruction/sew combo
