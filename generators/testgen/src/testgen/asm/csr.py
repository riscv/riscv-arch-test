##################################
# asm/csr.py
#
# CSR test utilities for privileged test generation.
#
# SPDX-License-Identifier: Apache-2.0
##################################

"""CSR test utilities for privileged test generation."""

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
            f"{INDENT}# Read {csr_name} into x{check_reg}, keep only bits specified by mask, and check against expected.\n"
            f"csrr x{check_reg}, {csr_name}    # Read CSR\n"
            f"and x{check_reg}, x{check_reg}, x{mask_reg}    # keep only masked bits {mask:#x}\n"
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


def csr_access_test(
    test_data: TestData, csr: tuple, covergroup: str, coverpoint: str, maskedwrites: bool = False
) -> list[str]:
    """
    Generate a CSR access test: write all 1s, write all 0s, set all, clear all.

    Args:
        test_data: TestData object to track signature updates
        csr: Tuple of (csr_name, mask) where csr_name is the CSR name string and
             mask is either None or an integer representing a binary mask of bits to keep
        covergroup: Covergroup name for testcase strings
        coverpoint: Coverpoint name for testcase strings
        maskedwrites: If True, the CSR is written with a mask applied to the value being written.

    Returns:
        List of assembly lines for the access test
    """
    csr_name, mask = csr
    if maskedwrites:
        assert mask is not None, f"maskedwrites requires a csr mask (got None for {csr_name})"
    if mask is not None:
        save_reg, temp_reg, check_reg, mask_reg = test_data.int_regs.get_registers(4)
    else:
        save_reg, temp_reg, check_reg = test_data.int_regs.get_registers(3)
        mask_reg = None

    lines = [
        "",
        f"# CSR Access Tests for {csr_name}",
        f"csrr x{save_reg}, {csr_name}    # Save CSR",
    ]
    if mask is not None:
        mask32 = mask & 0xFFFFFFFF
        if mask32 != mask:
            lines.extend(
                [
                    "#if __riscv_xlen == 64",
                    f"LI(x{mask_reg}, {mask:#x})    # Load 64-bit mask",
                    "#else",
                    f"LI(x{mask_reg}, {mask32:#x})   # Load 32-bit mask (upper bits of {mask:#x} are ignored)",
                    "#endif",
                ]
            )
        else:
            lines.append(f"LI(x{mask_reg}, {mask})    # Load mask ({mask:#x})")
    if maskedwrites:
        valstr = "mask"
        lines.append(f"mv x{temp_reg}, x{mask_reg}    # Apply {valstr} to value being written")
    else:
        valstr = "all 1s"
        lines.append(f"LI(x{temp_reg}, -1)             # write {valstr}")
    lines.extend(
        [
            test_data.add_testcase(f"{csr_name}_csrrw1", coverpoint, covergroup),
            f"csrw {csr_name}, x{temp_reg}    # Write {valstr} to CSR",
            gen_csr_read_sigupd(check_reg, csr, test_data, mask_reg),
            "",
            test_data.add_testcase(f"{csr_name}_csrrw0", coverpoint, covergroup),
            f"csrw {csr_name}, zero   # Write all 0s to CSR",
            gen_csr_read_sigupd(check_reg, csr, test_data, mask_reg),
            "",
            test_data.add_testcase(f"{csr_name}_csrs_all", coverpoint, covergroup),
            f"csrs {csr_name}, x{temp_reg}    # Set {valstr}",
            gen_csr_read_sigupd(check_reg, csr, test_data, mask_reg),
            "",
            test_data.add_testcase(f"{csr_name}_csrrc_all", coverpoint, covergroup),
            f"csrc {csr_name}, x{temp_reg}    # Clear {valstr}",
            gen_csr_read_sigupd(check_reg, csr, test_data, mask_reg),
            f"csrw {csr_name}, x{save_reg}       # Restore CSR",
        ]
    )
    regs = [save_reg, temp_reg, check_reg]
    if mask_reg is not None:
        regs.append(mask_reg)
    test_data.int_regs.return_registers(regs)
    return lines


def _warl_reserved_check(
    test_data: TestData,
    csr_name: str,
    bin_name: str,
    covergroup: str,
    coverpoint: str,
    reserved_fields: list[tuple],
    check_reg: int,
    warl_mask_reg: int,
    warl_mask: int,
) -> list[str]:
    """
    Generate the readback for a walk iteration that wrote reserved values to WARL fields.

    Implementations may legalize a reserved value to any legal value, so such fields cannot
    be exact-compared against the reference model. Check the non-field bits exactly, then
    emit a separate testcase and SIGUPD per field checking only that it does not read back
    as the reserved value, making a failure easy to identify in the test log.

    Args:
        test_data: TestData object to track signature updates
        csr_name: Name of the CSR containing the fields
        bin_name: Bin name of the walk readback this replaces (legality checks append the field name)
        covergroup: Covergroup name for testcase strings
        coverpoint: Coverpoint name for testcase strings
        reserved_fields: (field_name, lsb, width, reserved_value[, gate_define]) tuples of the
            fields that were written with a value that is reserved in this context (a gate_define,
            if present, was handled by the caller: this check is only assembled when the define is
            absent and the value therefore reserved)
        check_reg: Scratch register for the readback
        warl_mask_reg: Scratch register for the mask
        warl_mask: CSR mask with the reserved fields' bits excluded
    """
    field_list = ", ".join(f[0].upper() for f in reserved_fields)
    lines = [
        f"{INDENT}# {field_list} written with a reserved value; legalization is implementation-defined,",
        f"{INDENT}# so check the other bits exactly and only check {field_list} for a legal (non-reserved) value.",
        f"LI(x{warl_mask_reg}, {warl_mask:#x})    # Load mask excluding {field_list}",
        test_data.add_testcase(bin_name, coverpoint, covergroup),
        gen_csr_read_sigupd(check_reg, (csr_name, warl_mask), test_data, warl_mask_reg),
    ]
    for field_name, lsb, width, reserved in (f[:4] for f in reserved_fields):
        lines.extend(
            [
                test_data.add_testcase(f"{bin_name}_{field_name}_legal", coverpoint, covergroup),
                f"csrr x{check_reg}, {csr_name}    # Re-read CSR to check {field_name.upper()}",
                f"srli x{check_reg}, x{check_reg}, {lsb}",
                f"andi x{check_reg}, x{check_reg}, {(1 << width) - 1}    # extract {field_name.upper()} (bits {lsb + width - 1}:{lsb})",
                f"xori x{check_reg}, x{check_reg}, {reserved}",
                f"snez x{check_reg}, x{check_reg}    # 1 if {field_name.upper()} is not the reserved value {reserved:#b}",
                write_sigupd(check_reg, test_data),
            ]
        )
    return lines


def csr_walk_test(
    test_data: TestData,
    csr: tuple,
    covergroup: str,
    coverpoint: str,
    *,
    start_bit: int = 0,
    walk_zeros: bool = True,
    warl_fields: list[tuple] | None = None,
    maskedwrites: bool = False,
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
        warl_fields: Optional list of WARL field entries. (field_name, lsb, width, reserved_value)
            marks a value that is always reserved. (field_name, lsb, width, value, gate_define)
            marks a value that is legal only when gate_define is #defined for the config and
            reserved otherwise; the readback is emitted under #ifdef gate_define / #else so one
            generated test serves both kinds of config. Example: ("mpp", 11, 2, 0b01, "S_SUPPORTED")
            (MPP=S is legal only with S-mode); the same shape will gate menvcfg/mseccfg PMM
            encodings on pointer-masking parameters. A field may appear in several entries
            whose legalization of the reserved value is implementation-defined. Iterations that
            write the reserved value to such a field skip the exact-match check for the field's
            bits and instead check that the field holds a legal (non-reserved) value; all
            other iterations check the field exactly as usual (see _warl_reserved_check).
        maskedwrites: If True, the CSR is written with a mask applied to the value being written.
    """
    assert 0 <= start_bit < 32, f"start_bit must be in 0..31, got {start_bit}"
    csr_name, mask = csr
    if maskedwrites:
        assert mask is not None, f"maskedwrites requires a csr mask (got None for {csr_name})"
    if mask is not None:
        save_reg, temp_reg, walk_reg, check_reg, mask_reg = test_data.int_regs.get_registers(5)
    else:
        save_reg, temp_reg, walk_reg, check_reg = test_data.int_regs.get_registers(4)
        mask_reg = None
    warl_mask_reg = test_data.int_regs.get_register() if warl_fields else None

    def field_value_written(field: tuple, i: int, *, walking_ones: bool) -> int:
        """Value the walk writes to the WARL field when setting/clearing bit i."""
        lsb, width = field[1], field[2]
        if lsb <= i < lsb + width:
            walked_bit = 1 << (i - lsb)
            return walked_bit if walking_ones else ((1 << width) - 1) & ~walked_bit
        return 0 if walking_ones else (1 << width) - 1

    def reserved_fields_written(i: int, *, walking_ones: bool) -> list[tuple]:
        """WARL entries whose (possibly gate-conditional) reserved value the walk writes at bit i."""
        if not warl_fields:
            return []
        return [f for f in warl_fields if field_value_written(f, i, walking_ones=walking_ones) == f[3]]

    def warl_mask_for(reserved_fields: list[tuple]) -> int:
        """CSR mask with the given fields' bits excluded."""
        warl_mask = (1 << 64) - 1 if mask is None else mask
        for f in reserved_fields:
            lsb, width = f[1], f[2]
            warl_mask &= ~(((1 << width) - 1) << lsb)
        return warl_mask

    def readback_lines(bin_name: str, matched: list[tuple]) -> list[str]:
        """
        Readback + signature check for one walk iteration.  `matched` holds the WARL entries whose
        value was written this iteration.  Unconditional entries always take the legality check;
        gated entries branch on their gate define: exact check when it is defined (the value is
        legal there), legality check otherwise.  With several distinct gates this nests, emitting
        one branch per combination; only one branch is assembled for any given config.
        """
        uncond = [f for f in matched if len(f) == 4]
        gates = list(dict.fromkeys(f[4] for f in matched if len(f) == 5))

        def branch(name: str, reserved: list[tuple], remaining: list[str]) -> list[str]:
            # Each branch needs a distinct testcase name: the debug-string symbols emitted by
            # add_testcase are not confined to the preprocessor arm the testcase sits in.
            if not remaining:
                if not reserved:
                    return [
                        test_data.add_testcase(name, coverpoint, covergroup),
                        gen_csr_read_sigupd(check_reg, csr, test_data, mask_reg),
                    ]
                assert warl_mask_reg is not None
                return _warl_reserved_check(
                    test_data,
                    csr_name,
                    name,
                    covergroup,
                    coverpoint,
                    reserved,
                    check_reg,
                    warl_mask_reg,
                    warl_mask_for(reserved),
                )
            gate, rest = remaining[0], remaining[1:]
            gated = [f for f in matched if len(f) == 5 and f[4] == gate]
            gated_names = ", ".join(f[0].upper() for f in gated)
            return [
                f"#ifdef {gate}",
                *branch(name, reserved, rest),
                f"#else // no {gate}: the value written to {gated_names} is reserved",
                *branch(f"{name}_no{gate.lower()}", reserved + gated, rest),
                f"#endif // {gate}",
            ]

        return branch(bin_name, uncond, gates)

    lines = [
        "",
        f"# CSR Walk Tests for {csr_name}",
        f"csrr x{save_reg}, {csr_name}      # Save CSR",
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
        lines.append(f"csrw {csr_name}, zero    # clear all bits")
        if maskedwrites:
            lines.append(f"and x{check_reg}, x{walk_reg}, x{mask_reg} # mask walking 1")
            lines.append(f"csrs {csr_name}, x{check_reg}     # set walking 1 in column {i}")
        else:
            lines.append(f"csrs {csr_name}, x{walk_reg}     # set walking 1 in column {i}")
        lines.extend(readback_lines(f"{csr_name}_set_bit_{i}", reserved_fields_written(i, walking_ones=True)))
        lines.append(f"slli x{walk_reg}, x{walk_reg}, 1      # walk the 1")
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
            lines.append(
                f"csrw {csr_name}, x{mask_reg if maskedwrites else temp_reg}   # set all (possibly masked) bits"
            )
            if maskedwrites:
                lines.append(f"and x{check_reg}, x{walk_reg}, x{mask_reg} # mask walking 1")
                lines.append(f"csrc {csr_name}, x{check_reg}     # clear walking 0 in column {i}")
            else:
                lines.append(f"csrc {csr_name}, x{walk_reg}     # clear walking 0 in column {i}")
            lines.extend(readback_lines(f"{csr_name}_clr_bit_{i}", reserved_fields_written(i, walking_ones=False)))
            lines.append(f"slli x{walk_reg}, x{walk_reg}, 1      # walk the 1")
        if need_endif:
            lines.append("#endif\n")
            need_endif = False

    lines.append(f"csrw {csr_name}, x{save_reg}            # restore CSR")
    regs = [save_reg, temp_reg, walk_reg, check_reg]
    if mask_reg is not None:
        regs.append(mask_reg)
    if warl_mask_reg is not None:
        regs.append(warl_mask_reg)
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
        f"csrr x{save_reg}, {csr_name}    # Save CSR",
        "#if __riscv_xlen == 64",
        f"LI(x{temp_reg}, 0x123456789ABCFFFF)   # x{temp_reg} = 64-bit pattern",
        "#else",
        f"LI(x{temp_reg}, 0x1234FFFF)           # x{temp_reg} = 32-bit pattern",
        "#endif",
        test_data.add_testcase(f"{csr_name}_csrrw_some", coverpoint, covergroup),
        f"csrw {csr_name}, x{temp_reg}     # Write nonzero to CSR",
        f"csrr x{check_reg}, {csr_name}    # Read back CSR to check",
        f"sub x{check_reg}, x{check_reg}, x{temp_reg}   # Difference between read value and written value",
        f"sltiu x{check_reg}, x{check_reg}, 0x000007FF  # Check difference < 0x7FF to allow for counter increments",
        write_sigupd(check_reg, test_data),
        "",
        test_data.add_testcase(f"{csr_name}_csrrw0", coverpoint, covergroup),
        f"csrw {csr_name}, zero   # Write all 0s to CSR",
        f"csrr x{check_reg}, {csr_name}    # Read back CSR to check",
        f"sltiu x{check_reg}, x{check_reg}, 0x000007FF  # Check value < 0x7FF to allow for counter increments",
        write_sigupd(check_reg, test_data),
        "",
        test_data.add_testcase(f"{csr_name}_csrs_some", coverpoint, covergroup),
        f"csrs {csr_name}, x{temp_reg}    # Set some CSR bits",
        f"csrr x{check_reg}, {csr_name}    # Read back CSR to check",
        f"sub x{check_reg}, x{check_reg}, x{temp_reg}   # Difference between read value and written value",
        f"sltiu x{check_reg}, x{check_reg}, 0x000007FF  # Check difference < 0x7FF to allow for counter increments",
        write_sigupd(check_reg, test_data),
        "",
        test_data.add_testcase(f"{csr_name}_csrrc_all", coverpoint, covergroup),
        f"LI(x{temp_reg}, -1)              # all 1s",
        f"csrc {csr_name}, x{temp_reg}    # Clear all CSR bits",
        f"csrr x{check_reg}, {csr_name}    # Read back CSR to check",
        f"sltiu x{check_reg}, x{check_reg}, 0x000007FF  # Check value < 0x7FF to allow for counter increments",
        write_sigupd(check_reg, test_data),
        "",
        f"csrw {csr_name}, x{save_reg}       # Restore CSR",
    ]
    test_data.int_regs.return_registers([save_reg, temp_reg, check_reg])
    return lines
