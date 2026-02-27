##################################
# asm/csr.py
#
# CSR test utilities for privileged test generation.
#
# SPDX-License-Identifier: Apache-2.0
##################################

"""CSR test utilities for privileged test generation."""

from testgen.data.state import TestData


def gen_csr_read_sigupd(check_reg: int, csr_name: str, test_data: TestData) -> str:
    """
    Generate assembly for CSR read SIGUPD and increment sigupd_count.

    This function behaves like write_sigupd - it only generates the SIGUPD line.
    Call add_testcase separately before this to create the label.

    Args:
        check_reg: Register to read CSR into
        csr_name: Name of the CSR to read
        test_data: TestData object to track signature updates

    Returns:
        Assembly line for the CSR read SIGUPD
    """
    test_data.sigupd_count += 1
    return (
        f"\t# Read {csr_name} into x{check_reg} and check against expected.\n"
        f"\tRVTEST_SIGUPD_CSR_READ({csr_name}, x{check_reg}, test_{test_data.test_count}, test_{test_data.test_count}_str) "
    )


def gen_csr_write_sigupd(check_reg: int, csr_name: str, test_data: TestData) -> str:
    """
    Generate assembly for CSR write SIGUPD and increment sigupd_count.

    This function behaves like write_sigupd - it only generates the SIGUPD line.
    Call add_testcase separately before this to create the label.

    Args:
        check_reg: Register containing value to write to CSR
        csr_name: Name of the CSR to write
        test_data: TestData object to track signature updates

    Returns:
        Assembly line for the CSR write SIGUPD
    """
    test_data.sigupd_count += 1
    return (
        f"\t# Write x{check_reg} to {csr_name}, read back and check against expected.\n"
        f"\tRVTEST_SIGUPD_CSR_WRITE({csr_name}, x{check_reg}, test_{test_data.test_count}, test_{test_data.test_count}_str) "
    )


def csr_access_test(test_data: TestData, csr_name: str, covergroup: str, coverpoint: str) -> list[str]:
    """
    Generate a CSR access test: write all 1s, write all 0s, set all, clear all.

    Args:
        test_data: TestData object to track signature updates
        csr_name: Name of the CSR to test
        covergroup: Covergroup name for testcase strings
        coverpoint: Coverpoint name for testcase strings

    Returns:
        List of assembly lines for the access test
    """
    save_reg, temp_reg, check_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    lines = [
        f"\n# CSR Access Tests for {csr_name}",
        f"\tCSRR(x{save_reg}, {csr_name})    # Save CSR",
        f"\tli x{temp_reg}, -1           # x{temp_reg} = all 1s",
        test_data.add_testcase(f"{csr_name}_csrrw0", coverpoint, covergroup),
        f"\tCSRW({csr_name}, x{temp_reg})    # Write all 1s to CSR",
        f"test_{test_data.test_count}:",
        gen_csr_read_sigupd(check_reg, csr_name, test_data),
        test_data.add_testcase(f"{csr_name}_csrrw1", coverpoint, covergroup),
        f"\tCSRW({csr_name}, zero)   # Write all 0s to CSR",
        f"test_{test_data.test_count}:",
        gen_csr_read_sigupd(check_reg, csr_name, test_data),
        test_data.add_testcase(f"{csr_name}_csrs_all", coverpoint, covergroup),
        f"\tCSRS({csr_name}, x{temp_reg})    # Set all CSR bits",
        f"test_{test_data.test_count}:",
        gen_csr_read_sigupd(check_reg, csr_name, test_data),
        test_data.add_testcase(f"{csr_name}_csrrc_all", coverpoint, covergroup),
        f"\tCSRC({csr_name}, x{temp_reg})    # Clear all CSR bits",
        f"test_{test_data.test_count}:",
        gen_csr_read_sigupd(check_reg, csr_name, test_data),
        f"\tCSRW({csr_name}, x{save_reg})       # Restore CSR",
    ]
    test_data.int_regs.return_registers([save_reg, temp_reg, check_reg])
    return lines


def csr_walk_test(test_data: TestData, csr_name: str, covergroup: str, coverpoint: str) -> list[str]:
    """
    Generate a CSR walking ones test: set and clear each bit individually.

    Args:
        test_data: TestData object to track signature updates
        csr_name: Name of the CSR to test
        covergroup: Covergroup name for testcase strings
        coverpoint: Coverpoint name for testcase strings

    Returns:
        List of assembly lines for the walk test
    """
    save_reg, temp_reg, walk_reg, check_reg = test_data.int_regs.get_registers(4, exclude_regs=[0])

    lines = [
        f"    CSRR(x{save_reg}, {csr_name})      # Save CSR",
        f"    li x{temp_reg}, -1             # x{temp_reg} = all 1s",
        f"    li x{walk_reg}, 1            # 1 in lsb",
    ]

    # don't test MODE bit of satp
    if csr_name == "satp":
        r1 = range(31)
        r2 = range(31, 60)
    else:
        r1 = range(32)
        r2 = range(32, 64)

    # Set each bit 0-31
    for i in r1:
        lines.extend(
            [
                f"    CSRW({csr_name}, zero)    # clear all bits",
                f"    CSRS({csr_name}, x{walk_reg})      # set walking 1 in column {i}",
                test_data.add_testcase(f"{csr_name}_set_bit_{i}", coverpoint, covergroup),
                f"test_{test_data.test_count}:",
                gen_csr_read_sigupd(check_reg, csr_name, test_data),
                f"    slli x{walk_reg}, x{walk_reg}, 1      # walk the 1",
            ]
        )

    # Set bits 32-63 (RV64 only)
    lines.append("\n#if __riscv_xlen == 64")
    for i in r2:
        lines.extend(
            [
                f"    CSRW({csr_name}, zero)    # clear all bits",
                f"    CSRS({csr_name}, x{walk_reg})      # set walking 1 in column {i}",
                test_data.add_testcase(f"{csr_name}_set_bit_{i}", coverpoint, covergroup),
                f"test_{test_data.test_count}:",
                gen_csr_read_sigupd(check_reg, csr_name, test_data),
                f"    slli x{walk_reg}, x{walk_reg}, 1      # walk the 1",
            ]
        )
    lines.append("#endif\n")

    # Clear each bit 0-31
    lines.append(f"    li x{walk_reg}, 1            # 1 in lsb")
    for i in r1:
        lines.extend(
            [
                f"    CSRW({csr_name}, x{temp_reg})      # set all bits",
                f"    CSRC({csr_name}, x{walk_reg})      # clear walking 1 in column {i}",
                test_data.add_testcase(f"{csr_name}_clr_bit_{i}", coverpoint, covergroup),
                f"test_{test_data.test_count}:",
                gen_csr_read_sigupd(check_reg, csr_name, test_data),
                f"    slli x{walk_reg}, x{walk_reg}, 1      # walk the 1",
            ]
        )

    # Clear bits 32-63 (RV64 only)
    lines.append("\n#if __riscv_xlen == 64")
    for i in r2:
        lines.extend(
            [
                f"    CSRW({csr_name}, x{temp_reg})    # set all bits",
                f"    CSRC({csr_name}, x{walk_reg})    # clear walking 1 in column {i}",
                test_data.add_testcase(f"{csr_name}_clr_bit_{i}", coverpoint, covergroup),
                f"test_{test_data.test_count}:",
                gen_csr_read_sigupd(check_reg, csr_name, test_data),
                f"    slli x{walk_reg}, x{walk_reg}, 1      # walk the 1",
            ]
        )
    lines.append("#endif\n")

    lines.append(f"    CSRW({csr_name}, x{save_reg})            # restore CSR")
    test_data.int_regs.return_registers([save_reg, temp_reg, walk_reg, check_reg])
    return lines
