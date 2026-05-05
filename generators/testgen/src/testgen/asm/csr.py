##################################
# asm/csr.py
#
# CSR test utilities for privileged test generation.
#
# SPDX-License-Identifier: Apache-2.0
##################################

"""CSR test utilities for privileged test generation."""

from __future__ import annotations

from testgen.asm.helpers import write_sigupd
from testgen.constants import INDENT
from testgen.data.state import TestData


def gen_csr_read_sigupd(check_reg: int, csr: tuple, test_data: TestData, mask_reg: int | None = None) -> str:
    """
    Generate assembly for CSR read SIGUPD and increment sigupd_count.

    This function behaves like write_sigupd - it only generates the SIGUPD line.
    Call add_testcase separately before this to create the label.

    Args:
        check_reg: Register to read CSR into
        csr: Tuple of (csr_name, mask) where csr_name is the CSR name string and
             mask is either None or an integer representing a binary mask of bits to keep
        test_data: TestData object to track signature updates
        mask_reg: Register pre-loaded with the mask, required
                  when csr mask is not None. Supports masks of any bit width.

    Returns:
        Assembly line(s) for the CSR read SIGUPD
    """
    csr_name, mask = csr
    assert test_data.test_chunk is not None, "No active test chunk — call begin_test_chunk() first"
    if mask is None:
        test_data.test_chunk.sigupd_count += 1
        return (
            f"{INDENT}# Read {csr_name} into x{check_reg} and check against expected.\n"
            f"RVTEST_SIGUPD_CSR_READ({csr_name}, x{check_reg}, {test_data.current_testcase_label}, {test_data.current_testcase_label}_str)"
        )
    else:
        assert mask_reg is not None, "mask_reg must be provided when csr mask is not None"
        return (
            f"{INDENT}# Read {csr_name} into x{check_reg}, keep only bits specified by mask ({mask:#x}), and check against expected.\n"
            f"CSRR(x{check_reg}, {csr_name})    # Read CSR\n"
            f"and x{check_reg}, x{check_reg}, x{mask_reg}    # AND with {mask:#x} to keep only masked bits\n"
            + write_sigupd(check_reg, test_data)
        )


def gen_csr_write_sigupd(check_reg: int, csr_name: str, test_data: TestData) -> str:
    """
    Generate assembly to write CSR, read it back, and check against expected.

    This function behaves like write_sigupd - it only generates the SIGUPD line.
    Call add_testcase separately before this to create the label.

    Args:
        check_reg: Register containing value to write to CSR
        csr_name: Name of the CSR to write
        test_data: TestData object to track signature updates

    Returns:
        Assembly line for the CSR write SIGUPD
    """
    assert test_data.test_chunk is not None, "No active test chunk — call begin_test_chunk() first"
    test_data.test_chunk.sigupd_count += 1
    return (
        f"{INDENT}# Write x{check_reg} to {csr_name}, read back and check against expected.\n"
        f"RVTEST_SIGUPD_CSR_WRITE({csr_name}, x{check_reg}, {test_data.current_testcase_label}, {test_data.current_testcase_label}_str)"
    )


def csr_access_test(test_data: TestData, csr: tuple, covergroup: str, coverpoint: str) -> list[str]:
    """
    Generate a CSR access test: write all 1s, write all 0s, set all, clear all.

    Args:
        test_data: TestData object to track signature updates
        csr: Tuple of (csr_name, mask) where csr_name is the CSR name string and
             mask is either None or an integer representing a binary mask of bits to keep
        covergroup: Covergroup name for testcase strings
        coverpoint: Coverpoint name for testcase strings

    Returns:
        List of assembly lines for the access test
    """
    csr_name, mask = csr
    if mask is not None:
        save_reg, temp_reg, check_reg, mask_reg = test_data.int_regs.get_registers(4)
    else:
        save_reg, temp_reg, check_reg = test_data.int_regs.get_registers(3)
        mask_reg = None

    lines = [
        "",
        f"# CSR Access Tests for {csr_name}",
        f"CSRR(x{save_reg}, {csr_name})    # Save CSR",
        f"LI(x{temp_reg}, -1)          # x{temp_reg} = all 1s",
    ]
    if mask is not None:
        lines.append(f"LI(x{mask_reg}, {mask})    # Load mask ({mask:#x})")
    lines.extend(
        [
            test_data.add_testcase(f"{csr_name}_csrrw1", coverpoint, covergroup),
            f"CSRW({csr_name}, x{temp_reg})    # Write all 1s to CSR",
            gen_csr_read_sigupd(check_reg, csr, test_data, mask_reg),
            "",
            test_data.add_testcase(f"{csr_name}_csrrw0", coverpoint, covergroup),
            f"CSRW({csr_name}, zero)   # Write all 0s to CSR",
            gen_csr_read_sigupd(check_reg, csr, test_data, mask_reg),
            "",
            test_data.add_testcase(f"{csr_name}_csrs_all", coverpoint, covergroup),
            f"CSRS({csr_name}, x{temp_reg})    # Set all CSR bits",
            gen_csr_read_sigupd(check_reg, csr, test_data, mask_reg),
            "",
            test_data.add_testcase(f"{csr_name}_csrrc_all", coverpoint, covergroup),
            f"CSRC({csr_name}, x{temp_reg})    # Clear all CSR bits",
            gen_csr_read_sigupd(check_reg, csr, test_data, mask_reg),
            f"CSRW({csr_name}, x{save_reg})       # Restore CSR",
        ]
    )
    regs = [save_reg, temp_reg, check_reg]
    if mask_reg is not None:
        regs.append(mask_reg)
    test_data.int_regs.return_registers(regs)
    return lines


def csr_walk_test(
    test_data: TestData, csr: tuple, covergroup: str, coverpoint: str, *, start_bit: int = 0, walk_zeros: bool = True
) -> list[str]:
    """
    Generate a CSR walking-ones test: set and (optionally) clear each bit individually.

    Args:
        test_data: TestData object to track signature updates
        csr: Tuple of (csr_name, mask) where csr_name is the CSR name string and
             mask is either None or an integer representing a binary mask of bits to keep
        covergroup: Covergroup name for testcase strings
        coverpoint: Coverpoint name for testcase strings
        start_bit: First bit position to walk; must be in 0..31 so the initial LI
            constant is representable on RV32 (bits 32..63 are guarded by #if __riscv_xlen == 64)
        walk_zeros: If True, follow the walking-1s pass with a walking-0s pass
    """
    assert 0 <= start_bit < 32, f"start_bit must be in 0..31, got {start_bit}"
    csr_name, mask = csr
    if mask is not None:
        save_reg, temp_reg, walk_reg, check_reg, mask_reg = test_data.int_regs.get_registers(5)
    else:
        save_reg, temp_reg, walk_reg, check_reg = test_data.int_regs.get_registers(4)
        mask_reg = None

    lines = [
        "",
        f"# CSR Walk Tests for {csr_name}",
        f"CSRR(x{save_reg}, {csr_name})      # Save CSR",
        f"LI(x{walk_reg}, {1 << start_bit})              # 1 in bit {start_bit}",
    ]
    if mask is not None:
        lines.append(f"LI(x{mask_reg}, {mask})    # Load mask ({mask:#x})")
    if walk_zeros:
        lines.append(f"LI(x{temp_reg}, -1)             # x{temp_reg} = all 1s")

    need_endif = False

    # Walking 1s
    for i in range(start_bit, 64):
        if i == 32:
            lines.append("\n#if __riscv_xlen == 64")
            need_endif = True
        lines.extend(
            [
                "",
                f"CSRW({csr_name}, zero)    # clear all bits",
                f"CSRS({csr_name}, x{walk_reg})     # set walking 1 in column {i}",
                test_data.add_testcase(f"{csr_name}_set_bit_{i}", coverpoint, covergroup),
                gen_csr_read_sigupd(check_reg, csr, test_data, mask_reg),
                f"slli x{walk_reg}, x{walk_reg}, 1      # walk the 1",
            ]
        )
    if need_endif:
        lines.append("#endif\n")
        need_endif = False

    # Walking 0s
    if walk_zeros:
        lines.append(f"LI(x{walk_reg}, {1 << start_bit})            # 1 in bit {start_bit}")
        for i in range(start_bit, 64):
            if i == 32:
                lines.append("\n#if __riscv_xlen == 64")
                need_endif = True
            lines.extend(
                [
                    "",
                    f"CSRW({csr_name}, x{temp_reg})      # set all bits",
                    f"CSRC({csr_name}, x{walk_reg})      # clear walking 1 in column {i}",
                    test_data.add_testcase(f"{csr_name}_clr_bit_{i}", coverpoint, covergroup),
                    gen_csr_read_sigupd(check_reg, csr, test_data, mask_reg),
                    f"slli x{walk_reg}, x{walk_reg}, 1      # walk the 1",
                ]
            )
        if need_endif:
            lines.append("#endif\n")
            need_endif = False

    lines.append(f"CSRW({csr_name}, x{save_reg})            # restore CSR")
    regs = [save_reg, temp_reg, walk_reg, check_reg]
    if mask_reg is not None:
        regs.append(mask_reg)
    test_data.int_regs.return_registers(regs)
    return lines


def cntr_access_test(test_data: TestData, csr: tuple, covergroup: str, coverpoint: str) -> list[str]:
    """
    Generate a counter access test: write nonzero, write all 0s, set nonzero, clear all.
    Readback checks that the read value is within 0x7FF of the written value to account for counter increments.

    Args:
        test_data: TestData object to track signature updates
        csr: Tuple of (csr_name, mask) where csr_name is the CSR name string and
             mask is either None or an integer representing a binary mask of bits to ignore (presently not used)
        covergroup: Covergroup name for testcase strings
        coverpoint: Coverpoint name for testcase strings

    Returns:
        List of assembly lines for the access test
    """
    csr_name, _mask = csr
    save_reg, temp_reg, check_reg = test_data.int_regs.get_registers(3)

    lines = [
        "",
        f"# Counter Access Tests for {csr_name}",
        f"CSRR(x{save_reg}, {csr_name})    # Save CSR",
        "#if __riscv_xlen == 64",
        f"LI(x{temp_reg}, 0x123456789ABCFFFF)   # x{temp_reg} = 64-bit pattern",
        "#else",
        f"LI(x{temp_reg}, 0x1234FFFF)           # x{temp_reg} = 32-bit pattern",
        "#endif",
        test_data.add_testcase(f"{csr_name}_csrrw_some", coverpoint, covergroup),
        f"CSRW({csr_name}, x{temp_reg})     # Write nonzero to CSR",
        f"CSRR(x{check_reg}, {csr_name})    # Read back CSR to check",
        f"sub x{check_reg}, x{check_reg}, x{temp_reg}   # Difference between read value and written value",
        f"sltiu x{check_reg}, x{check_reg}, 0x000007FF  # Check difference < 0x7FF to allow for counter increments",
        write_sigupd(check_reg, test_data),
        "",
        test_data.add_testcase(f"{csr_name}_csrrw0", coverpoint, covergroup),
        f"CSRW({csr_name}, zero)   # Write all 0s to CSR",
        f"CSRR(x{check_reg}, {csr_name})    # Read back CSR to check",
        f"sltiu x{check_reg}, x{check_reg}, 0x000007FF  # Check value < 0x7FF to allow for counter increments",
        write_sigupd(check_reg, test_data),
        "",
        test_data.add_testcase(f"{csr_name}_csrs_some", coverpoint, covergroup),
        f"CSRS({csr_name}, x{temp_reg})    # Set some CSR bits",
        f"CSRR(x{check_reg}, {csr_name})    # Read back CSR to check",
        f"sub x{check_reg}, x{check_reg}, x{temp_reg}   # Difference between read value and written value",
        f"sltiu x{check_reg}, x{check_reg}, 0x000007FF  # Check difference < 0x7FF to allow for counter increments",
        write_sigupd(check_reg, test_data),
        "",
        test_data.add_testcase(f"{csr_name}_csrrc_all", coverpoint, covergroup),
        f"LI(x{temp_reg}, -1)              # all 1s",
        f"CSRC({csr_name}, x{temp_reg})    # Clear all CSR bits",
        f"CSRR(x{check_reg}, {csr_name})    # Read back CSR to check",
        f"sltiu x{check_reg}, x{check_reg}, 0x000007FF  # Check value < 0x7FF to allow for counter increments",
        write_sigupd(check_reg, test_data),
        "",
        f"CSRW({csr_name}, x{save_reg})       # Restore CSR",
    ]
    test_data.int_regs.return_registers([save_reg, temp_reg, check_reg])
    return lines
