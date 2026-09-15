##################################
# cp_custom_fflags_accrue.py
#
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_custom_fflags_accrue coverpoint generator."""

from testgen.asm.helpers import load_float_reg, write_sigupd
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.instructions.params import generate_random_params

# Pre-set flags, all disjoint from the NV the comparison raises, so a set bit
# afterwards can only have been carried in.
PRESET_FFLAGS = (0b00001, 0b00010, 0b00100, 0b01000, 0b01111)

# Signaling NaN raises NV in every comparison; the second operand is 1.0.
SNAN = {"single": 0x7F800001, "double": 0x7FF0000000000001}
ONE = {"single": 0x3F800000, "double": 0x3FF0000000000000}


@add_coverpoint_generator("cp_custom_fflags_accrue")
def make_custom_fflags_accrue(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """Generate tests showing fflags accrues rather than being overwritten."""
    if instr_type != "FC":
        raise ValueError(
            f"cp_custom_fflags_accrue only supports FC-type comparisons, got {instr_type} for {instr_name}."
        )
    fmt = "double" if coverpoint.endswith("_D") else "single"

    test_chunks: list[TestChunk] = []
    for preset in PRESET_FFLAGS:
        params = generate_random_params(test_data, instr_type, exclude_regs=[0], fs1val=SNAN[fmt], fs2val=ONE[fmt])
        assert params.fs1 is not None and params.fs2 is not None and params.rd is not None

        tc = test_data.begin_test_chunk()
        tc.code.append(f"# Testcase {coverpoint} (fflags pre-set to {preset:#07b}, operation raises NV)")
        label_line = test_data.add_testcase(f"preset_{preset:05b}", coverpoint)
        tc.code.extend(
            [
                load_float_reg("fs1", params.fs1, SNAN[fmt], test_data, params.fp_load_type),
                load_float_reg("fs2", params.fs2, ONE[fmt], test_data, params.fp_load_type),
                f"fsflagsi {preset:#07b} # pre-set fflags with flags the operation cannot raise",
                label_line,
                f"{instr_name} x{params.rd}, f{params.fs1}, f{params.fs2} # raises NV, must accrue onto the pre-set flags",
                write_sigupd(params.rd, test_data, "int"),
                write_sigupd(None, test_data, "fflags"),
            ]
        )
        test_chunks.append(test_data.end_test_chunk())
        return_testcase_registers(test_data, params)

    return test_chunks
