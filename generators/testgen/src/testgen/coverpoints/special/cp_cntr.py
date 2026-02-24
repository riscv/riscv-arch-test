##################################
# cp_cntr.py
#
# David_Harris@hmc.edu 6 Jan 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_cntr coverpoint generator."""

from testgen.asm.helpers import write_sigupd
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData


@add_coverpoint_generator("cp_cntr")
def make_cntr(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for counter coverpoints."""
    test_lines: list[str] = []

    # Allocate some registers for testing.
    r1, r2, r3 = test_data.int_regs.get_registers(3, exclude_regs=[0])

    if coverpoint == "cp_cntr":
        test_lines.extend(
            [
                gen_cntr_test(instr_name, "cycle", r1, r2, r3, test_data),
                "#if TIME_CSR_IMPLEMENTED\n",
                gen_cntr_test(instr_name, "time", r1, r2, r3, test_data),
                "#endif\n",
                gen_cntr_test(instr_name, "instret", r1, r2, r3, test_data),
                "#if __riscv_xlen == 32\n",
                gen_cntr_test(instr_name, "cycleh", r1, r2, r3, test_data),
                "#if TIME_CSR_IMPLEMENTED\n",
                gen_cntr_test(instr_name, "timeh", r1, r2, r3, test_data),
                "#endif\n",
                gen_cntr_test(instr_name, "instreth", r1, r2, r3, test_data),
                "#endif\n",
            ]
        )
    elif coverpoint == "cp_cntr_hpm":
        for hpm in range(3, 32):  # hpmcounter3 through hpmcounter31
            test_lines.append(gen_cntr_test(instr_name, f"hpmcounter{hpm}", r1, r2, r3, test_data))
        test_lines.append("#if __riscv_xlen == 32\n")
        for hpm in range(3, 32):  # hpmcounter3h through hpmcounter31h
            test_lines.append(gen_cntr_test(instr_name, f"hpmcounter{hpm}h", r1, r2, r3, test_data))
        test_lines.append("#endif\n")
    else:
        raise ValueError(f"Unknown cp_cntr coverpoint variant: {coverpoint} for {instr_name}")

    test_data.int_regs.return_registers([r1, r2, r3])

    return test_lines


def gen_cntr_test(instr_name: str, cntr: str, r1: int, r2: int, r3: int, test_data: TestData) -> str:
    """Generate counter test snippet."""
    mindiff = 1 if cntr in ["instret", "cycle", "time"] else 0  # h registers unlikely to increment
    if cntr != "instret" and not cntr.endswith("h"):
        slt = f"slti x{r1}, x{r1}, {mindiff} # set fail code if difference < {mindiff}"
    else:
        slt = ""  # for minstret, the difference should be exact.  High counters should be exactly zero.
    lines = [
        test_data.add_testcase(cntr, "cp_cntr"),
        f"# Testcase: cp_cntr ({cntr})",
    ]
    if cntr == "time":
        lines.extend(
            [
                "# Loop until time increments, or fail if it does not",
                f"{instr_name} x{r1}, {cntr}, x0 # read {cntr} initial value",
                f"li x{r3}, 2000 # timeout counter to prevent infinite loop if counter doesn't increment",
                f"test_{test_data.test_count}:",
                f"1: {instr_name} x{r2}, {cntr}, x0 # read {cntr} new value",
                f"addi x{r3}, x{r3}, -1 # decrement timeout counter",
                f"beqz x{r3}, 2f # if timeout counter reaches zero, fail",
                f"beq x{r1}, x{r2}, 1b # keep waiting if counter has not incremented",
                "2: # counter incremented or timeout reached",
            ]
        )
    else:
        lines.extend(
            [
                "#  Read two consecutive times to check if counter increments",
                f"{instr_name} x{r1}, {cntr}, x0",
                f"addi x{r2}, x{r1}, 1 # delay a bit",
                f"addi x{r2}, x{r2}, 1 # delay a bit",
                f"addi x{r2}, x{r2}, 1 # delay a bit",
                f"addi x{r2}, x{r2}, 1 # delay a bit",
                f"addi x{r2}, x{r2}, 1 # delay a bit",
                f"addi x{r2}, x{r2}, 1 # delay a bit",
                f"{instr_name} x{r2}, {cntr}, x0",
                f"test_{test_data.test_count}:",
                f"{instr_name} x{r2}, {cntr}, x0 # read again to increase delay a bit more",
            ]
        )
    lines.extend(
        [
            f"sub x{r1}, x{r2}, x{r1} # compute difference",
            f"{slt}",
            write_sigupd(r1, test_data, "int"),  # record difference as signature
            "",
        ]
    )
    return "\n".join(lines)
