##################################
# cp_misalign.py
#
# David_Harris@hmc.edu 2 Jan 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_misalign coverpoint generator."""

from testgen.coverpoints.coverpoints import add_coverpoint_generator
from testgen.data.test_data import TestData
from testgen.utils.common import load_int_reg, write_sigupd


@add_coverpoint_generator("cp_misalign")
def make_misalign(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for alignment coverpoints."""
    if coverpoint == "cp_misalign":
        alignments = [0, 1, 2, 3, 4, 5, 6, 7]
    else:
        raise ValueError(f"Unknown cp_misalign coverpoint variant: {coverpoint} for {instr_name}")

    test_lines: list[str] = []

    # Allocate some registers for testing.  Restrict them to [8,15] in case the registers are used for compressed instructions
    r1, r2 = test_data.int_regs.get_registers(2, exclude_regs=[0], reg_range=range(8, 16))

    if instr_type == "L" or instr_type == "FL" or instr_type == "CL" or instr_type == "CILS":
        test_lines.extend(
            [
                "# Start by placing 0x01234567_89ABCDEF_00112233_44556677 into 16 bytes starting at scratch address to facilitate misaligned load tests",
                f"LA(x{r1}, scratch) # load base address",
                load_int_reg("testdata_0", r2, 0x44556677, test_data),
                f"sw x{r2}, 0(x{r1}) # store at offset 0",
                load_int_reg("testdata_1", r2, 0x00112233, test_data),
                f"sw x{r2}, 4(x{r1}) # store at offset 4",
                load_int_reg("testdata_2", r2, 0x89ABCDEF, test_data),
                f"sw x{r2}, 8(x{r1}) # store at offset 8",
                load_int_reg("testdata_3", r2, 0x01234567, test_data),
                f"sw x{r2}, 12(x{r1}) # store at offset 12",
                "",
            ]
        )

    for alignment in alignments:
        test_lines.append(test_data.add_testcase(coverpoint))
        if instr_type == "L":
            test_lines.extend(
                [
                    f"# Testcase: {coverpoint} (imm[2:0] = {alignment:03b})",
                    f"LA(x{r1}, scratch) # load base address",
                    f"{instr_name} x{r2}, {alignment}(x{r1}) # perform load",
                    write_sigupd(r2, test_data, "int"),
                    "",
                ]
            )
        elif instr_type == "FL":
            test_lines.extend(
                [
                    f"# Testcase: {coverpoint} (imm[2:0] = {alignment:03b})",
                    f"LA(x{r1}, scratch) # load base address",
                    f"{instr_name} f{r2}, {alignment}(x{r1}) # perform load",
                    write_sigupd(r2, test_data, "float"),
                    "",
                ]
            )
        elif instr_type == "CL":
            test_lines.extend(
                [
                    f"# Testcase: {coverpoint} (addr[2:0] = {alignment:03b})",
                    f"LA(x{r1}, scratch) # load base address",
                    f"addi x{r1}, x{r1}, {alignment} # adjust for alignment",
                    f"{instr_name} x{r2}, 0(x{r1}) # perform load",
                    write_sigupd(r2, test_data, "int"),
                    "",
                ]
            )
        elif instr_type == "CILS":
            test_lines.extend(
                [
                    f"# Testcase: {coverpoint} (imm[2:0] = {alignment:03b})",
                    test_data.int_regs.consume_registers([2]),
                    "LA(sp, scratch) # load base address",
                    f"addi sp, sp, {alignment} # adjust for alignment",
                    f"{instr_name} x{r2}, 0(sp) # perform load",
                    write_sigupd(r2, test_data, "int"),
                    "",
                ]
            )
            test_data.int_regs.return_registers([2])
        elif instr_type == "S" or instr_type == "FS" or instr_type == "CS" or instr_type == "CSS":
            val = (
                0x0F1E2D3C if test_data.xlen == 32 else 0x0F1E2D3C4B5A6978
            )  # bytes to store all differ from values placed in scratch
            test_lines.extend(
                [
                    f"# Testcase: {coverpoint} (imm[2:0] = {alignment:03b})",
                    "# Start by placing 0x01234567_89ABCDEF_00112233_44556677 into 16 bytes starting at scratch address to facilitate misaligned load tests",
                    f"LA(x{r1}, scratch) # load base address",
                    load_int_reg("testdata_0", r2, 0x44556677, test_data),
                    f"sw x{r2}, 0(x{r1}) # store at offset 0",
                    load_int_reg("testdata_0", r2, 0x00112233, test_data),
                    f"sw x{r2}, 4(x{r1}) # store at offset 4",
                    load_int_reg("testdata_0", r2, 0x89ABCDEF, test_data),
                    f"sw x{r2}, 8(x{r1}) # store at offset 8",
                    load_int_reg("testdata_0", r2, 0x01234567, test_data),
                    f"sw x{r2}, 12(x{r1}) # store at offset 12",
                    load_int_reg("rs2", r2, val, test_data),
                ]
            )
            if instr_type == "S":
                test_lines.append(f"{instr_name} x{r2}, {alignment}(x{r1}) # perform store to scratch memory")
            elif instr_type == "FS":
                test_lines.append(f"{instr_name} f{r2}, {alignment}(x{r1}) # perform store to scratch memory")
            elif instr_type == "CS":
                test_lines.extend(
                    [
                        f"addi x{r1}, x{r1}, {alignment} # adjust for alignment",
                        f"{instr_name} x{r2}, 0(x{r1}) # perform store",
                        f"addi x{r1}, x{r1}, {-alignment} # restore base address",
                    ]
                )
            elif instr_type == "CSS":
                test_lines.extend(
                    [
                        test_data.int_regs.consume_registers([2]),
                        "LA(sp, scratch) # load base address",
                        f"addi sp, sp, {alignment} # adjust for alignment",
                        f"{instr_name} x{r2}, 0(sp) # perform store",
                    ]
                )
                test_data.int_regs.return_registers([2])
            if test_data.xlen == 32:
                test_lines.extend(
                    [
                        f"# Check all 16 bytes as signatureLREG x{r2}, 0(x{r1})",
                        write_sigupd(r2, test_data, "int"),
                        f"LREG x{r2}, 4(x{r1})",
                        write_sigupd(r2, test_data, "int"),
                        f"LREG x{r2}, 8(x{r1})",
                        write_sigupd(r2, test_data, "int"),
                        f"LREG x{r2}, 12(x{r1})",
                    ]
                )
            else:  # RV64
                test_lines.extend(
                    [
                        f"# Check all 16 bytes as signatureLREG x{r2}, 0(x{r1})",
                        write_sigupd(r2, test_data, "int"),
                        f"LREG x{r2}, 8(x{r1})",
                        write_sigupd(r2, test_data, "int"),
                    ]
                )
        else:
            raise ValueError(f"Unknown instruction type: {instr_type} for cp_misalign.")

    test_data.int_regs.return_registers([r1, r2])

    return test_lines
