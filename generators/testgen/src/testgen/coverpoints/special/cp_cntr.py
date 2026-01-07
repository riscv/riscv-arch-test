##################################
# cp_cntr.py
#
# David_Harris@hmc.edu 6 Jan 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_cntr coverpoint generator."""

from testgen.coverpoints.coverpoints import add_coverpoint_generator
from testgen.data.test_data import TestData
from testgen.utils.common import write_sigupd


@add_coverpoint_generator("cp_cntr")
def make_cntr(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for counter coverpoints."""
    test_lines: list[str] = []

    # Allocate some registers for testing.  Restrict them to [8,15] in case the registers are used for compressed instructions
    r1, r2 = test_data.int_regs.get_registers(2, exclude_regs=[0])

    if coverpoint == "cp_cntr":
        test_lines.extend(
            [
                gen_cntr_test("cycle", r1, r2, test_data),
                gen_cntr_test("time", r1, r2, test_data),
                gen_cntr_test("instret", r1, r2, test_data),
                "#if __riscv_xlen == 32\n",
                gen_cntr_test("cycleh", r1, r2, test_data),
                gen_cntr_test("timeh", r1, r2, test_data),
                gen_cntr_test("instreth", r1, r2, test_data),
                "#endif\n",
            ]
        )
    elif coverpoint == "cp_cntr_hpm":
        for hpm in range(3, 32):  # hpmcounter3 through hpmcounter31
            test_lines.append(gen_cntr_test(f"hpmcounter{hpm}", r1, r2, test_data))
        test_lines.append("#if __riscv_xlen == 32\n")
        for hpm in range(3, 32):  # hpmcounter3h through hpmcounter31h
            test_lines.append(gen_cntr_test(f"hpmcounter{hpm}h", r1, r2, test_data))
        test_lines.append("#endif\n")
    else:
        raise ValueError(f"Unknown cp_cntr coverpoint variant: {coverpoint} for {instr_name}")

    test_data.int_regs.return_registers([r1, r2])

    return test_lines


def gen_cntr_test(cntr: str, r1: int, r2: int, test_data: TestData) -> str:
    """Generate counter test snippet."""
    mindiff = 1 if cntr in ["instret", "cycle"] else 0  # instret and cycle increment quickly; others may not
    lines = [
        test_data.add_testcase("cp_cntr"),
        f"# Testcase: cp_cntr ({cntr})",
        "#  Read two consecutive times to check if counter increments",
        f"csrr x{r1}, {cntr}",
        "nop",
        "nop",
        "nop",
        "nop",
        "nop",
        "nop",
        f"csrr x{r2}, {cntr}",
        f"sub x{r1}, x{r2}, x{r1} # compute difference",
        f"slti x{r1}, x{r1}, {mindiff} # set fail code if difference < {mindiff}",
        write_sigupd(r1, test_data, "int"),  # record difference as signature
        "",
    ]
    return "\n".join(lines)
