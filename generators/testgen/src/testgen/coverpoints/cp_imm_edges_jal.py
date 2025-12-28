##################################
# cp_imm_edges_jal.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################


"""cp_imm_edges_jal coverpoint generators."""

from testgen.coverpoints.coverpoints import add_coverpoint_generator
from testgen.data.test_data import TestData
from testgen.utils.common import return_test_regs
from testgen.utils.param_generator import generate_random_params


@add_coverpoint_generator("cp_imm_edges_jal", "cp_imm_edges_c_jal")
def make_cp_imm_edges_jal(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for JAL immediate edge values.

    Coverage bins are based on immediate value ranges (powers of 2):
    - b_4: offset 2-3 (impossible for 4-byte jal)
    - b_8: offset 4-7
    - b_16: offset 8-15
    - ... up to b_4096: offset 2048-4095
    - b_m4: offset -4 to -3
    - b_m8: offset -8 to -5
    - ... up to b_m4096: offset -4096 to -2049
    """
    test_lines: list[str] = []

    if instr_name == "c.jal":
        # TODO: implement c.jal - needs CJAL instruction formatter first
        return []
    elif instr_name == "c.j":
        params = generate_random_params(test_data, instr_type)
        params.rd = 0  # c.j always uses x0
        instr_size = 2
    else:  # jal
        params = generate_random_params(test_data, instr_type)
        instr_size = 4

    assert params.temp_reg is not None and params.rd is not None

    # Label prefix to avoid conflicts with other coverpoints
    lbl = f"{coverpoint}_"

    # Coverage bins map to alignment levels:
    # b_8 (4-7): align 2 (4 bytes) - but jal is 4 bytes, so offset = 4
    # b_16 (8-15): align 3 (8 bytes)
    # b_32 (16-31): align 4 (16 bytes)
    # ... up to b_4096: align 11 (2048 bytes)
    #
    # For jal (4 bytes): start at align N, jal takes 4 bytes, .align N-1 gives offset 2^(N-1)
    # Example: .align 4 puts us at 16-byte boundary
    #          jal (4 bytes) -> now at offset 4
    #          .align 3 pads to 8-byte boundary -> adds 4 bytes
    #          target at offset 8, hits b_16

    # Alignment levels to test (maps to bin boundaries)
    # align_level N means target at 2^(N-1) bytes from jal
    # jal: can't hit b_4 (need 2-3 byte offset, but jal is 4 bytes)
    # c.j: can hit b_4 with offset 2
    align_levels = list(range(2, 13)) if instr_size == 4 else list(range(1, 13))

    # Forward jumps: .align N positions jal, then .align N positions target 2^N bytes later
    # Example for b_16 (N=4):
    #   .align 4  -> at 16-byte boundary (offset 0)
    #   jal       -> 4 bytes, now at offset 4
    #   .align 4  -> pads 12 bytes to next 16-byte boundary
    #   target:   -> at offset 16 from jal, hits b_16
    for align in align_levels:
        bin_name = f"b_{1 << align}"  # 2^align
        test_data.add_testcase_string(coverpoint)

        test_lines.extend(
            [
                "",
                f"# Forward jump for {bin_name}",
                f".align {align}",
            ]
        )

        if instr_name == "jal":
            test_lines.append(f"jal x{params.rd}, {lbl}fwd_{bin_name}")
        else:
            test_lines.append(f"{instr_name} {lbl}fwd_{bin_name}")

        test_lines.extend(
            [
                f".align {align}",
                f"{lbl}fwd_{bin_name}:",
            ]
        )

    # Backward jumps: place target and source at consecutive alignment boundaries
    # Example for b_m16 (N=4):
    #   .align 5  -> at 32-byte boundary
    #   jal skip  -> skip over target (4 bytes)
    #   .align 4  -> target at 16-byte boundary (next one after the jal)
    #   target:
    #   jal after -> escape (4 bytes)
    #   skip:     -> at offset 8 from .align 5
    #   .align 5  -> pad to next 32-byte boundary
    #   jal target -> at 32-byte boundary, target at 16-byte, offset = 16-32 = -16
    #   after:

    for align in align_levels:
        bin_name = f"b_m{1 << align}"  # negative 2^align
        test_data.add_testcase_string(coverpoint)

        test_lines.extend(
            [
                "",
                f"# Backward jump for {bin_name}",
                f".align {align + 1}",
            ]
        )

        # Jump over the target
        if instr_name == "jal":
            test_lines.append(f"jal x{params.rd}, {lbl}skip_{bin_name}")
        else:
            test_lines.append(f"{instr_name} {lbl}skip_{bin_name}")

        # Align target to 2^align boundary
        test_lines.append(f".align {align}")

        # Target label (when backward jump lands here, escape forward)
        test_lines.append(f"{lbl}bwd_{bin_name}:")
        if instr_name == "jal":
            test_lines.append(f"jal x{params.rd}, {lbl}after_{bin_name}")
        else:
            test_lines.append(f"{instr_name} {lbl}after_{bin_name}")

        # Skip point
        test_lines.append(f"{lbl}skip_{bin_name}:")

        # Align source to 2^(align+1) boundary for backward jump
        test_lines.append(f".align {align + 1}")

        # Backward jump
        if instr_name == "jal":
            test_lines.append(f"jal x{params.rd}, {lbl}bwd_{bin_name}")
        else:
            test_lines.append(f"{instr_name} {lbl}bwd_{bin_name}")

        test_lines.append(f"{lbl}after_{bin_name}:")

    return_test_regs(test_data, params)
    return test_lines
