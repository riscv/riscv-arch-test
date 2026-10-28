##################################
# zkt.py
#
# David_Harris@hmc.edu 11 Oct 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Zkt data-independent execution latency coverpoint generators (cp_zkt_*).

The timing method and its assumptions are described in the Zkt Principle of Operation
(docs/ctp/src/k.adoc, zkt-principle-of-operation).
"""

from dataclasses import replace

from testgen.asm.helpers import write_sigupd
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.edges import get_general_edges
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_instruction
from testgen.instructions.params import generate_random_params


@add_coverpoint_generator("cp_zkt")
def make_cp_zkt(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Time the instruction with cycle or mcycle across edge values of its source operands."""
    tc = test_data.begin_test_chunk()
    start, end, baseline, runs, dep = test_data.int_regs.get_registers(5, exclude_regs=[0])
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
            "# The first run warms the instruction cache and branch predictor. Only the second run is timed.",
            "# A dependency on the first cycle read stops the instruction from starting early.",
            "# .balign 64 keeps the timed window in one cache line.",
            "# The second cycle read has no dependency. Writing cycle or mcycle is illegal or changes the count.",
        ]
    )

    for case, values in enumerate(operand_values):
        case_params = replace(params, **values)
        bin_name = ", ".join(f"{name}={value:#x}" for name, value in values.items()) or "timed"
        tc.code.append(f"\n# Testcase {coverpoint} ({bin_name})")
        label_line = test_data.add_testcase(bin_name, coverpoint)
        data_count = len(tc.data_values)
        setup, test, check = format_instruction(instr_name, instr_type, test_data, case_params)
        data_bytes = f"{len(tc.data_values) - data_count}*SIG_STRIDE"
        # Run twice and time the second run (see the CTP)
        tc.code.extend([f"LI(x{runs}, 2)  # two runs; the second is timed", "1:"])
        if setup:
            tc.code.extend(
                [
                    setup,
                    f"addi x{data_reg}, x{data_reg}, -{data_bytes}    # rewind data for the second run",
                ]
            )
        if loaded_regs:
            tc.code.append(f"xor x{start}, x{loaded_regs[0]}, x{loaded_regs[-1]}           # drain: loads finish first")
        # Zero-valued dependency on the first cycle read
        tc.code.extend(
            [
                ".balign 64                  # keep the timed window in one cache line",
                f"csrr x{start}, RVTEST_CYCLE_CSR  # first cycle read",
            ]
        )
        if dep_src is not None:
            tc.code.extend(
                [
                    f"sltu x{dep}, x{start}, x0           # dep = 0, ready after the first cycle read",
                    f"or x{dep_src}, x{dep_src}, x{dep}            # operand depends on the first cycle read",
                ]
            )
        tc.code.extend(
            [
                label_line,
                test,
                f"csrr x{end}, RVTEST_CYCLE_CSR  # second cycle read",
                f"addi x{runs}, x{runs}, -1",
                f"bnez x{runs}, 1b",
            ]
        )
        if setup:
            tc.code.append(f"addi x{data_reg}, x{data_reg}, {data_bytes}   # advance past this testcase's data")
        tc.code.append(f"sub x{end}, x{end}, x{start}           # latency of the second run")
        if case == 0:
            tc.code.append(f"mv x{baseline}, x{end}                 # first testcase sets the baseline")
        tc.code.append(f"sub x{end}, x{end}, x{baseline}           # 0 on data-independent hardware")
        if check:
            tc.code.append(check)
        tc.code.append(write_sigupd(end, test_data, "int"))

    return_testcase_registers(test_data, params)
    test_data.int_regs.return_registers([start, end, baseline, runs, dep])
    return [test_data.end_test_chunk()]
