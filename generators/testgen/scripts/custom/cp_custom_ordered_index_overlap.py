# SPDX-License-Identifier: Apache-2.0

from coverpoint_registry import register
import vector_testgen_common as common

@register("cp_custom_ordered_index_overlap")
def make(test: str, sew: int):
    common.registerCustomData("custom_index_overlap", [0], sew)
    instruction_data  = common.randomizeVectorInstructionData(test, sew, common.getLengthSuiteTestCount(), suite="length", vs2_val_pointer="custom_index_overlap")

    cp = "cp_custom_ordered_index_overlap"
    description = "cp_custom_ordered_index_overlap (Data Overlap of Indices)"
    common.writeTest(description, test, cp, instruction_data, sew=sew, vl="vlmax", suite="length")
    common.incrementLengthtestCount()
