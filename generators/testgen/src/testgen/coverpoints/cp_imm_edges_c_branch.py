##################################
# cp_imm_edges_c_branch.py
#
# David_Harris@hmc.edu Sep 2026
# SPDX-License-Identifier: Apache-2.0
##################################


"""cp_imm_edges_c_branch coverpoint generator."""

from testgen.asm.helpers import write_sigupd
from testgen.constants import INDENT
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.instructions.params import generate_random_params

MAX_FWD_ALIGN = 7  # +128; the largest positive offset is +254
MAX_BWD_ALIGN = 8  # -256, the most negative offset


@add_coverpoint_generator("cp_imm_edges_c_branch")
def make_cp_imm_edges_c_branch(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """Generate taken c.beqz / c.bnez branches with power-of-two offsets from +2 to +128 and -2 to -256."""
    if instr_name not in ("c.beqz", "c.bnez"):
        raise ValueError(f"Unsupported instruction for {coverpoint}: {instr_name}")

    tc = test_data.begin_test_chunk()
    params = generate_random_params(test_data, instr_type, exclude_regs=[0])
    assert params.rs1 is not None and params.temp_reg is not None
    rs1 = params.rs1
    temp = params.temp_reg

    # Every halfword between the branch and its target is c.li temp, 7. A branch that is not taken or that
    # lands on any other halfword of the gap records the failure code; only the correct target records 1.
    # A +2 branch goes to the next halfword either way, so it cannot be checked.
    def gap(num_bytes: int) -> list[str]:
        if num_bytes == 0:
            return [f"{INDENT}# no gap to check"]
        return [f"c.li x{temp}, 7 # wrong target or not taken" for _ in range(num_bytes // 2)]

    tc.code.append(f"LI(x{rs1}, {0 if instr_name == 'c.beqz' else 1}) # branch is taken")

    for align in range(1, MAX_FWD_ALIGN + 1):
        offset = 1 << align
        target = f"{coverpoint}_fwd_b_{offset}"
        tc.code.extend(
            [
                "",
                f"# {coverpoint}: forward branch by {offset}",
                f"c.li x{temp}, 1 # success code",
                test_data.add_testcase(f"b_{offset}", coverpoint),
                f"{instr_name} x{rs1}, {target}",
                *gap(offset - 2),
                f"{target}:",
                write_sigupd(temp, test_data),
            ]
        )

    for align in range(1, MAX_BWD_ALIGN + 1):
        offset = 1 << align
        branch = f"{coverpoint}_bwd_src_b_m{offset}"
        target = f"{coverpoint}_bwd_b_m{offset}"
        done = f"{coverpoint}_bwd_done_b_m{offset}"
        tc.code.extend(
            [
                "",
                f"# {coverpoint}: backward branch by -{offset}",
                f"c.li x{temp}, 1 # success code",
                f"c.j {branch}",
                f"{target}:",
                f"c.j {done} # correct target",
                *gap(offset - 2),
                f"{branch}:",
                test_data.add_testcase(f"b_m{offset}", coverpoint),
                f"{instr_name} x{rs1}, {target}",
                f"c.li x{temp}, 7 # branch not taken",
                f"{done}:",
                write_sigupd(temp, test_data),
            ]
        )

    return_testcase_registers(test_data, params)
    return [test_data.end_test_chunk()]
