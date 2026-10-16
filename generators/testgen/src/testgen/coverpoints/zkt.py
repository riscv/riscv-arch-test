##################################
# zkt.py
#
# David_Harris@hmc.edu 11 Oct 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Zkt data-independent execution latency coverpoint generators (cp_zkt_*).

Zkt requires the listed instructions to take the same time for any operand data. Each testcase
times one instruction with RVTEST_CYCLE_CSR, which utils.h defines as cycle when Zicntr is supported
and as mcycle otherwise. The mcycle tests boot to M-mode; the cycle tests boot to the lowest mode.

    LI(runs, 2)
  1: load the operands
    xor start, rs1, rs2            # drain: the loads complete before timing starts
    .balign 64
    csrr start, RVTEST_CYCLE_CSR
    sltu dep, start, x0            # dep = 0, but it is ready only after the first cycle read
    or src, src, dep               # src keeps its value and now depends on the first cycle read
    <instruction under test>       # reads src
    csrr end, RVTEST_CYCLE_CSR
    addi runs, runs, -1
    bnez runs, 1b                  # run twice and time the second run

Run twice: the first run fills the instruction cache and corrects the branch predictor. A tagless
BTB can hold an entry from unrelated code at the same index and mispredict an instruction in the
window. Only the warm second run is timed.

.balign 64: an instruction-cache miss on the line after the window stalls fetch, and in a simple
pipeline the stall delays the second cycle read. Starting the window at a 64-byte boundary keeps
the window and the instructions after it in one line.

Dependency: without it, an out-of-order core could execute the instruction under test before the
first cycle read and hide its latency. sltu and or are themselves Zkt instructions, so they add a
constant time that cancels below. One source carries the dependency; the instruction cannot start
until it is ready. Instructions without data operands (cp_zkt_pc) have nothing to depend on.

The second read cannot take a dependency: csrrs with rs1 != x0 writes the CSR. Writing cycle
raises an illegal-instruction exception, and writing mcycle changes the count. The method therefore
assumes that CSR reads execute in order at commit, as is typical. A core that reads the counter
early loses sensitivity but does not fail falsely. FENCE does not order CSR reads against
arithmetic instructions, so it is not used.

Signature: reference models count one cycle per instruction, while real cores differ, so a raw
cycle count is not portable. The first testcase's latency is the baseline, and every testcase
writes latency - baseline, which is 0 on any implementation whose latency does not depend on the
data. Registers and immediates are part of the encoding and may legally affect latency, so they are
fixed for each instruction and only the data varies.
"""

from dataclasses import replace

from testgen.asm.helpers import write_sigupd
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.edges import get_general_edges
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_instruction
from testgen.instructions.params import generate_random_params


@add_coverpoint_generator("cp_zkt_rs1_rs2", "cp_zkt_rs1", "cp_zkt_rs2", "cp_zkt_pc")
def make_cp_zkt(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Time the instruction with cycle or mcycle across edge values of its source operands."""
    tc = test_data.begin_test_chunk()
    start, end, baseline, runs, dep = test_data.int_regs.get_registers(5, exclude_regs=[0])
    # x0 is excluded because rd=x0 forms are HINTs, which Zkt does not cover
    params = generate_random_params(test_data, instr_type, exclude_regs=[0])
    if params.immval == 0:
        params.immval = 1  # a zero immediate makes c.addi a HINT
    # Registers loaded by the setup code, which must finish before timing starts
    loaded_regs = [reg for reg in (params.rs1, params.rs2) if reg is not None]

    # dep_src is the source that carries the dependency on the first cycle read
    edges = get_general_edges(test_data.xlen)
    if coverpoint == "cp_zkt_rs1_rs2":
        operand_values = [{"rs1val": rs1val, "rs2val": rs2val} for rs1val in edges for rs2val in edges]
        dep_src = params.rs1
    elif coverpoint == "cp_zkt_rs1":
        operand_values = [{"rs1val": rs1val} for rs1val in edges]
        dep_src = params.rs1
    elif coverpoint == "cp_zkt_rs2":
        operand_values = [{"rs2val": rs2val} for rs2val in edges]
        dep_src = params.rs2  # c.mv, whose only source is rs2
    elif coverpoint == "cp_zkt_pc":
        operand_values = [{}]  # no data operands; only the pc varies
        dep_src = None
    else:
        raise ValueError(f"Unknown cp_zkt coverpoint variant: {coverpoint} for {instr_name}")
    data_reg = test_data.int_regs.data_reg
    tc.code.extend(
        [
            "# Each testcase times the instruction twice, counted down in",
            f"# x{runs}, and writes the second run's latency (x{end} - x{start}) minus the",
            f"# first testcase's (x{baseline}), which must be 0. See the Zkt section of the CTP.",
            "",
        ]
    )

    for case, values in enumerate(operand_values):
        case_params = replace(params, **values)
        bin_name = ", ".join(f"{name}={value:#x}" for name, value in values.items()) or "timed"
        if case:
            tc.code.append("")
        tc.code.append(f"# Testcase {coverpoint} ({bin_name})")
        label_line = test_data.add_testcase(bin_name, coverpoint)
        data_count = len(tc.data_values)
        setup, test, check = format_instruction(instr_name, instr_type, test_data, case_params)
        data_bytes = f"{len(tc.data_values) - data_count}*SIG_STRIDE"
        # Run twice and time the second run (see the module docstring)
        tc.code.extend([f"LI(x{runs}, 2)", "1:"])
        if setup:
            # Rewind the data pointer so the second run loads the same values
            tc.code.extend([setup, f"addi x{data_reg}, x{data_reg}, -{data_bytes}"])
        if loaded_regs:
            tc.code.append(f"xor x{start}, x{loaded_regs[0]}, x{loaded_regs[-1]}")  # drain the loads
        tc.code.extend([".balign 64", f"csrr x{start}, RVTEST_CYCLE_CSR"])
        if dep_src is not None:
            # Zero-valued dependency on the first cycle read
            tc.code.extend([f"sltu x{dep}, x{start}, x0", f"or x{dep_src}, x{dep_src}, x{dep}"])
        tc.code.extend(
            [
                label_line,
                test,
                f"csrr x{end}, RVTEST_CYCLE_CSR",
                f"addi x{runs}, x{runs}, -1",
                f"bnez x{runs}, 1b",
            ]
        )
        if setup:
            tc.code.append(f"addi x{data_reg}, x{data_reg}, {data_bytes}")
        tc.code.append(f"sub x{end}, x{end}, x{start}")
        if case == 0:
            tc.code.append(f"mv x{baseline}, x{end}")
        tc.code.append(f"sub x{end}, x{end}, x{baseline}")
        if check:
            tc.code.append(check)
        tc.code.append(write_sigupd(end, test_data, "int"))

    return_testcase_registers(test_data, params)
    test_data.int_regs.return_registers([start, end, baseline, runs, dep])
    return [test_data.end_test_chunk()]
