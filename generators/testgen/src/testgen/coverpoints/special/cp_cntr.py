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
from testgen.data.test_chunk import TestChunk


@add_coverpoint_generator("cp_cntr")
def make_cntr(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for counter coverpoints."""
    tc = test_data.begin_test_chunk()

    # Allocate some registers for testing.
    r1, r2, r3 = test_data.int_regs.get_registers(3, exclude_regs=[0])

    if coverpoint == "cp_cntr":
        # With U-mode, a counter is readable only if mcounteren (and scounteren with S-mode) can
        # delegate it, so only those counters are read.
        counters = ["cycle", "time", "instret"]
        for bit, cntr in enumerate(counters):
            tc.code.extend(
                [
                    f"#if {cntr_readable(bit)}\n",
                    gen_cntr_test(instr_name, cntr, r1, r2, r3, coverpoint, test_data),
                    "#endif\n",
                ]
            )
        tc.code.append("#if __riscv_xlen == 32\n")
        for bit, cntr in enumerate(counters):
            tc.code.extend(
                [
                    f"#if {cntr_readable(bit)}\n",
                    gen_cntr_test(instr_name, f"{cntr}h", r1, r2, r3, coverpoint, test_data),
                    "#endif\n",
                ]
            )
        tc.code.append("#endif\n")
    elif coverpoint == "cp_cntr_hpm":
        # hpmcounter3 through hpmcounter31, each read only if the configuration implements it and
        # the test's mode can access it. Accessing an unimplemented counter may trap or return a
        # constant (norm:hpm_unimplemented_counter_access), so no single signature covers it.
        for hpm in range(3, 32):
            tc.code.append(f"#if defined(UDB_HPM_COUNTER_EN_{hpm}) && {cntr_readable(hpm)}\n")
            tc.code.append(gen_cntr_test(instr_name, f"hpmcounter{hpm}", r1, r2, r3, coverpoint, test_data))
            tc.code.append("#endif\n")
        tc.code.append("#if __riscv_xlen == 32\n")
        # hpmcounter3h through hpmcounter31h
        for hpm in range(3, 32):
            tc.code.append(f"#if defined(UDB_HPM_COUNTER_EN_{hpm}) && {cntr_readable(hpm)}\n")
            tc.code.append(gen_cntr_test(instr_name, f"hpmcounter{hpm}h", r1, r2, r3, coverpoint, test_data))
            tc.code.append("#endif\n")
        tc.code.append("#endif\n")
    else:
        raise ValueError(f"Unknown cp_cntr coverpoint variant: {coverpoint} for {instr_name}")

    test_data.int_regs.return_registers([r1, r2, r3])

    return [test_data.end_test_chunk()]


def cntr_readable(bit: int) -> str:
    """Preprocessor condition that counter `bit` is readable from the mode unprivileged tests run in."""
    return (
        f"(!defined(U_SUPPORTED) || (defined(UDB_MCOUNTENABLE_EN_{bit}) && "
        f"(!defined(S_SUPPORTED) || defined(UDB_SCOUNTENABLE_EN_{bit}))))"
    )


def gen_cntr_test(instr_name: str, cntr: str, r1: int, r2: int, r3: int, coverpoint: str, test_data: TestData) -> str:
    """Generate counter test snippet."""
    mindiff = 1 if cntr in ["instret", "cycle", "time"] else 0  # h registers unlikely to increment
    if cntr != "instret" and not cntr.endswith("h"):
        slt = f"slti x{r1}, x{r1}, {mindiff} # set fail code if difference < {mindiff}"
    else:
        slt = ""  # for minstret, the difference should be exact.  High counters should be exactly zero.
    lines = [f"# Testcase: {coverpoint} ({cntr})"]
    if cntr == "time":
        lines.extend(
            [
                "# Loop until time increments, or fail if it does not",
                f"{instr_name} x{r1}, {cntr}, x0 # read {cntr} initial value",
                f"LI(x{r3}, 2000) # timeout counter to prevent infinite loop if counter doesn't increment",
                test_data.add_testcase(cntr, coverpoint),
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
                "# Read two consecutive times to check if counter increments",
                f"{instr_name} x{r1}, {cntr}, x0",
                f"addi x{r2}, x{r1}, 1 # delay a bit",
                f"addi x{r2}, x{r2}, 1 # delay a bit",
                f"addi x{r2}, x{r2}, 1 # delay a bit",
                f"addi x{r2}, x{r2}, 1 # delay a bit",
                f"addi x{r2}, x{r2}, 1 # delay a bit",
                f"addi x{r2}, x{r2}, 1 # delay a bit",
                f"{instr_name} x{r2}, {cntr}, x0",
                test_data.add_testcase(cntr, coverpoint),
                f"{instr_name} x{r2}, {cntr}, x0 # read again to increase delay a bit more",
            ]
        )
    lines.append(f"sub x{r1}, x{r2}, x{r1} # compute difference")
    if slt:
        lines.append(slt)
    lines.extend(
        [
            write_sigupd(r1, test_data, "int"),  # record difference as signature
            "",
        ]
    )
    return "\n".join(lines)
