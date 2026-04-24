##################################
# asm/interrupts.py
#
# Interrupt helper functions for generating timer interrupt assembly code.
# sanarayanan@hmc.edu February 2026
# SPDX-License-Identifier: Apache-2.0
##################################


from testgen.constants import INDENT


def set_mtimer_int(r_mtime: int, r_mtimecmp: int, r_temp: int, r_temp2: int) -> list[str]:
    """Generate assembly to set machine timer interrupt (mtimecmp = mtime).

    Args:
        r_mtime: Register number to hold MTIME address
        r_mtimecmp: Register number to hold MTIMECMP address
        r_temp: Temp register number for values
        r_temp2: Second temp register number for RV32
    """
    return [
        f"{INDENT}# Cause machine timer interrupt if supported",
        "#ifdef RVMODEL_MTIME_ADDRESS",
        f"LA(x{r_mtime}, RVMODEL_MTIME_ADDRESS)",
        f"LA(x{r_mtimecmp}, RVMODEL_MTIMECMP_ADDRESS)",
        "#if __riscv_xlen == 64",
        f"LREG x{r_temp}, 0(x{r_mtime})",
        f"SREG x{r_temp}, 0(x{r_mtimecmp})",
        "#elif __riscv_xlen == 32",
        "# Write sequence to prevent spurious interrupts",
        "# Read mtime (new comparand will be in temp2:temp)",
        f"lw x{r_temp}, 0(x{r_mtime}) # mtime[31:0] -> low word",
        f"lw x{r_temp2}, 4(x{r_mtime}) # mtime[63:32] -> high word",
        "# 3-step write sequence (new comparand is in temp2:temp)",
        f"LI(x{r_mtime}, -1) # Reuse r_mtime for -1",
        f"sw x{r_mtime}, 0(x{r_mtimecmp}) # Step 1: Write -1 to low (no smaller than old)",
        f"sw x{r_temp2}, 4(x{r_mtimecmp}) # Step 2: Write high word (no smaller than new)",
        f"sw x{r_temp}, 0(x{r_mtimecmp}) # Step 3: Write low word (new value)",
        # Write sequence to prevent spurious interrupts
        # Read mtime (new comparand will be in temp2:temp)
        f"lw x{r_temp}, 0(x{r_mtime})",  # mtime[31:0] -> low word
        f"lw x{r_temp2}, 4(x{r_mtime})",  # mtime[63:32] -> high word
        # 3-step write sequence (new comparand is in temp2:temp)
        f"LI(x{r_mtime}, -1)",  # Reuse r_mtime for -1
        f"sw x{r_mtime}, 0(x{r_mtimecmp})",  # Step 1: Write -1 to low (no smaller than old)
        f"sw x{r_temp2}, 4(x{r_mtimecmp})",  # Step 2: Write high word (no smaller than new)
        f"sw x{r_temp}, 0(x{r_mtimecmp})",  # Step 3: Write low word (new value)
        "#endif",
        "#endif",
    ]


def clr_mtimer_int(r_temp: int, r_mtimecmp: int) -> list[str]:
    """Generate assembly to clear machine timer interrupt (mtimecmp = -1).

    Args:
        r_temp: Register number for -1 value
        r_mtimecmp: Register number to hold MTIMECMP address
    """
    return [
        f"{INDENT}# Clear machine timer interrupt",
        f"LI(x{r_temp}, -1)",
        "// skip clearing interrupt if RVMODEL_MTIMECMP_ADDRESS is not defined",
        "#ifdef RVMODEL_MTIMECMP_ADDRESS",
        f"LA(x{r_mtimecmp}, RVMODEL_MTIMECMP_ADDRESS)",
        f"SREG x{r_temp}, 0(x{r_mtimecmp})",
        "#if __riscv_xlen == 32",
        f"sw x{r_temp}, 4(x{r_mtimecmp})",
        "#endif",
        "#endif",
    ]


def set_mtimer_int_soon(
    r_mtime: int, r_mtimecmp: int, r_temp1: int, r_temp2: int, r_temp3: int, r_temp4: int
) -> list[str]:
    """Generate assembly to set timer to fire soon (mtimecmp = mtime + DELAY).

    Uses LI + add to handle delays > 2047 (addi 12-bit immediate limit).

    Args:
        r_mtime: Register for MTIME address
        r_mtimecmp: Register for MTIMECMP address
        r_temp1, r_temp2, r_temp3, r_temp4: Temp registers for calculations
    """
    return [
        f"{INDENT}# Cause machine timer interrupt soon if supported",
        "#ifdef RVMODEL_MTIME_ADDRESS",
        f"LA(x{r_mtime}, RVMODEL_MTIME_ADDRESS)",
        f"LA(x{r_mtimecmp}, RVMODEL_MTIMECMP_ADDRESS)",
        "#if __riscv_xlen == 64",
        "# Read current time and add delay",
        f"LI(x{r_temp2}, RVMODEL_TIMER_INT_SOON_DELAY)",
        f"LREG x{r_temp1}, 0(x{r_mtime})",  # Use LREG macro
        f"add x{r_temp1}, x{r_temp1}, x{r_temp2}",
        f"SREG x{r_temp1}, 0(x{r_mtimecmp})",  # Use SREG macro
        "#elif __riscv_xlen == 32",
        f"LI(x{r_temp4}, RVMODEL_TIMER_INT_SOON_DELAY)",
        "# Read current time (64-bit on RV32)",
        f"lw x{r_temp1}, 0(x{r_mtime})",
        f"lw x{r_temp2}, 4(x{r_mtime})",
        "# Add delay to 64-bit value",
        f"add x{r_temp3}, x{r_temp1}, x{r_temp4}",
        f"sltu x{r_temp4}, x{r_temp3}, x{r_temp1}",
        f"add x{r_temp2}, x{r_temp2}, x{r_temp4}",
        "# Per RISC-V Spec 3.2.1: Write sequence to prevent spurious interrupt",
        f"LI(x{r_temp1}, -1)",
        f"sw x{r_temp1}, 0(x{r_mtimecmp})",
        f"sw x{r_temp2}, 4(x{r_mtimecmp})",
        f"sw x{r_temp3}, 0(x{r_mtimecmp})",
        "#endif",
        "#endif",
    ]


def set_stimer_int(r_mtime: int, r_temp: int, r_temp2: int, r_scratch: int, r_stce: int) -> list[str]:
    """Set supervisor timer interrupt.

    Args:
        r_stce: Optional - register containing pre-read menvcfg.STCE value (0 or 1)
                If None, will read menvcfg in M-mode

    If STCE=1: Use Sstc method (write stimecmp - works in S-mode)
    If STCE=0: Use legacy method (write mip.STIP - requires M-mode)
    """
    lines = [
        f"{INDENT}# Set supervisor timer interrupt",
    ]

    # If STCE not pre-read, read menvcfg (assumes M-mode)
    if r_stce is None:
        lines.extend(
            [
                f"{INDENT}# Check if Sstc is enabled",
                f"CSRR x{r_scratch}, menvcfg",
                "#if __riscv_xlen == 64",
                f"SRLI x{r_scratch}, x{r_scratch}, 63",  # STCE is bit 63
                "#else",
                f"SRLI x{r_scratch}, x{r_scratch}, 31",  # STCE is bit 31
                "#endif",
                f"ANDI x{r_scratch}, x{r_scratch}, 0x1",
            ]
        )
        check_reg = r_scratch
    else:
        check_reg = r_stce

    lines.extend(
        [
            f"BEQZ x{check_reg}, 1f # If STCE=0, use legacy method",
            "",
            f"{INDENT}# Sstc method: Write stimecmp (works in S-mode)",
            f"LA(x{r_mtime}, RVMODEL_MTIME_ADDRESS)",
            f"LREG x{r_temp}, 0(x{r_mtime})",
            f"addi x{r_temp}, x{r_temp}, 100",  # Add 100 cycle delay
            f"csrw stimecmp, x{r_temp}",
            "nop",
            "#if __riscv_xlen == 32",
            f"LI(x{r_temp}, -1)",
            f"csrw stimecmp, x{r_temp}",
            f"lw x{r_temp2}, 4(x{r_mtime})",
            f"lw x{r_temp}, 0(x{r_mtime})",
            f"addi x{r_temp}, x{r_temp}, 100",  # Add 100 cycle delay to low word
            f"sltu x{r_scratch}, x{r_temp}, x{r_temp}",  # Check for overflow
            f"add x{r_temp2}, x{r_temp2}, x{r_scratch}",  # Add carry to high word
            f"csrw stimecmph, x{r_temp2}",
            f"csrw stimecmp, x{r_temp}",
            "nop",
            "#endif",
            "j 2f",
            "",
            "1: # Legacy method: Set mip.STIP (requires M-mode)",
            "RVTEST_GOTO_MMODE",
            f"LI(x{r_temp}, 0x20)",  # STIP bit
            f"csrrs x{r_temp}, mip, x{r_temp}",
            "# Clear MPIE to prevent MIE=1 after mret back to S-mode",
            f"LI(x{r_temp}, 0x80)",  # MPIE bit (bit 7)
            f"csrc mstatus, x{r_temp}",
            "RVTEST_GOTO_LOWER_MODE Smode",
            "",
            "2: # Continue",
        ]
    )

    return lines


def clr_stimer_int(r_temp: int, r_stimecmp: int, r_scratch: int, r_stce: int) -> list[str]:
    """Clear supervisor timer interrupt.

    Args:
        r_stce: Optional - register containing pre-read menvcfg.STCE value (0 or 1)
                If None, will read menvcfg (assumes M-mode)

    If STCE=1: Use Sstc method (write stimecmp = -1)
    If STCE=0: Use legacy method (clear mip.STIP - requires M-mode)
    """
    lines = [
        f"{INDENT}# Clear supervisor timer interrupt",
    ]

    # If STCE not pre-read, read menvcfg (assumes M-mode)
    if r_stce is None:
        lines.extend(
            [
                f"{INDENT}# Check if Sstc is enabled",
                f"CSRR x{r_scratch}, menvcfg",
                "#if __riscv_xlen == 64",
                f"SRLI x{r_scratch}, x{r_scratch}, 63",  # STCE is bit 63
                "#else",
                f"SRLI x{r_scratch}, x{r_scratch}, 31",  # STCE is bit 31
                "#endif",
                f"ANDI x{r_scratch}, x{r_scratch}, 0x1",
            ]
        )
        check_reg = r_scratch
    else:
        check_reg = r_stce

    lines.extend(
        [
            f"BEQZ x{check_reg}, 1f # If STCE=0, use legacy method",
            "",
            f"{INDENT}# Sstc method: Write stimecmp = -1 (max value)",
            f"LI(x{r_temp}, -1)",
            f"csrw stimecmp, x{r_temp}",
            "#if __riscv_xlen == 32",
            f"csrw stimecmph, x{r_temp}",  # Also clear high word
            "#endif",
            "j 2f",
            "",
            "1: # Legacy method: Clear mip.STIP (must be in M-mode)",
            f"LI(x{r_temp}, 0x20)",  # STIP = bit 5
            f"csrrc x{r_temp}, mip, x{r_temp}",
            "",
            "2: # Continue",
        ]
    )

    return lines


def set_stimer_int_soon_sstc(r_mtime: int, r_temp1: int, r_temp2: int, r_temp3: int, r_temp4: int) -> list[str]:
    """Set supervisor timer interrupt to fire soon WITH Sstc extension.


    Uses stimecmp CSR (not MTIMECMP memory). Otherwise identical to set_mtimer_int_soon.
    """
    return [
        f"{INDENT}# Set supervisor timer interrupt to fire soon with Sstc extension",
        f"LA(x{r_mtime}, RVMODEL_MTIME_ADDRESS)  # NOTE: This will need to be replaced by a SBI call because MTIME might not exist or be accessible",
        "#if __riscv_xlen == 64",
        f"{INDENT}# Disable comparator first",
        f"LI(x{r_temp1}, -1)",
        f"csrw stimecmp, x{r_temp1}",
        f"{INDENT}# Read current time and add delay",
        f"ld x{r_temp1}, 0(x{r_mtime})",
        f"addi x{r_temp1}, x{r_temp1}, RVMODEL_TIMER_INT_SOON_DELAY",
        f"csrw stimecmp, x{r_temp1}",
        "#elif __riscv_xlen == 32",
        f"{INDENT}# Disable comparator first --> set to high value to prevent early firing",
        f"LI(x{r_temp1}, -1)",
        f"csrw stimecmp, x{r_temp1}",
        f"csrw stimecmph, x{r_temp1}",
        f"{INDENT}# Read current time",
        f"lw x{r_temp1}, 0(x{r_mtime})",
        f"lw x{r_temp2}, 4(x{r_mtime})",
        f"addi x{r_temp3}, x{r_temp1}, RVMODEL_TIMER_INT_SOON_DELAY",
        f"sltu x{r_temp4}, x{r_temp3}, x{r_temp1}",
        f"add x{r_temp2}, x{r_temp2}, x{r_temp4}",
        f"csrw stimecmp, x{r_temp3}",
        f"csrw stimecmph, x{r_temp2}",
        "#endif",
    ]


def set_stimer_mmode(r_scratch: int) -> list[str]:
    """Set supervisor timer interrupt in M-mode (direct mip write).

    This function directly writes mip.STIP without mode transitions.
    Must be called from M-mode.

    Args:
        r_scratch: Scratch register for loading immediate

    Returns:
        List of assembly instructions
    """
    return [
        f"{INDENT}# Set supervisor timer interrupt (M-mode direct)",
        f"LI(x{r_scratch}, 0x20)",  # STIP bit (bit 5)
        f"CSRS(mip, x{r_scratch})",
        "nop",
    ]


def clr_stimer_mmode(r_scratch: int) -> list[str]:
    """Clear supervisor timer interrupt in M-mode (direct mip write).

    This function directly clears mip.STIP without mode transitions.
    Must be called from M-mode.

    Args:
        r_scratch: Scratch register for loading immediate

    Returns:
        List of assembly instructions
    """
    return [
        f"{INDENT}# Clear supervisor timer interrupt (M-mode direct)",
        f"LI(x{r_scratch}, 0x20)",  # STIP bit (bit 5)
        f"CSRC(mip, x{r_scratch})",
        "nop",
    ]


def set_menvcfg_stce(r_scratch: int, enable: bool) -> list[str]:
    """Set or clear menvcfg.STCE (bit 63 on RV64, bit 31 of menvcfgh on RV32).

    Must be called from M-mode.

    Args:
        r_scratch: Scratch register
        enable: True to set STCE=1, False to clear STCE=0
    """
    op = "CSRS" if enable else "CSRC"
    return [
        f"{INDENT}# {'Enable' if enable else 'Disable'} menvcfg.STCE",
        "#if __riscv_xlen == 64",
        f"    LI(x{r_scratch}, 1)",
        f"    slli x{r_scratch}, x{r_scratch}, 63",
        f"    {op}(menvcfg, x{r_scratch})",
        "#else",
        f"    LI(x{r_scratch}, 0x80000000)",
        f"    {op}(menvcfgh, x{r_scratch})",
        "#endif",
    ]


def set_stimecmp_max(r_scratch: int) -> list[str]:
    """Write stimecmp = -1 (max) to disable Sstc timer interrupt. M-mode only."""
    return [
        f"{INDENT}# Disable Sstc timer: stimecmp = -1",
        f"LI(x{r_scratch}, -1)",
        f"CSRW(stimecmp, x{r_scratch})",
        "#if __riscv_xlen == 32",
        f"    CSRW(stimecmph, x{r_scratch})",
        "#endif",
    ]


def set_stimecmp_zero() -> list[str]:
    """Write stimecmp = 0 to immediately assert Sstc timer interrupt.

    stimecmp=0 guarantees mtime > stimecmp (mtime is always > 0 after reset).
    This can serve as the coverage sample instruction: the write makes
    ins.current.csr[stimecmp]=0 visible to the coverage model, while the
    interrupt fires at the NEXT instruction boundary, not before.
    """
    return [
        f"{INDENT}# Assert Sstc timer: stimecmp = 0  (interrupt fires at next boundary)",
        "CSRW(stimecmp, zero)",
    ]


def set_stimecmp_soon(r_scratch: int, r_time: int, r_hi: int) -> list[str]:
    """Write stimecmp = TIME + 500 from M-mode so the interrupt fires after entering U-mode.

    Disables stimecmp first (-1) to prevent a spurious interrupt during
    the read-modify-write sequence.  Falls back to stimecmp=0 if
    RVMODEL_MTIME_ADDRESS is not defined.

    Args:
        r_scratch: scratch register (clobbered)
        r_time:    scratch for MTIME address / RV32 new_lo (clobbered)
        r_hi:      scratch for RV32 old_hi / new_hi (clobbered; unused on RV64)
    """
    return [
        f"{INDENT}# stimecmp = TIME + 500: interrupt fires after entering U-mode",
        *set_stimecmp_max(r_scratch),
        "#ifdef RVMODEL_MTIME_ADDRESS",
        "    #if __riscv_xlen == 64",
        f"        LA(x{r_time}, RVMODEL_MTIME_ADDRESS)",
        f"        LREG x{r_scratch}, 0(x{r_time})",
        f"        addi x{r_scratch}, x{r_scratch}, 500",
        f"        CSRW(stimecmp, x{r_scratch})",
        "    #else",
        f"        LA(x{r_time}, RVMODEL_MTIME_ADDRESS)",
        f"        lw x{r_scratch}, 0(x{r_time})",  # old_lo
        f"        lw x{r_hi}, 4(x{r_time})",  # old_hi
        f"        addi x{r_time}, x{r_scratch}, 500",  # new_lo (reuse r_time)
        f"        sltu x{r_scratch}, x{r_time}, x{r_scratch}",  # carry
        f"        add x{r_hi}, x{r_hi}, x{r_scratch}",  # new_hi
        f"        CSRW(stimecmph, x{r_hi})",
        f"        CSRW(stimecmp, x{r_time})",
        "    #endif",
        "#else",
        "    CSRW(stimecmp, zero)",
        "#endif",
    ]


def set_mpie(r_scratch: int, enable: bool) -> list[str]:
    """Set or clear mstatus.MPIE (bit 7) to control MIE after the next mret.

    Must be called from M-mode before RVTEST_GOTO_LOWER_MODE.
    After mret: MIE = old MPIE.
    Uses csrrs/csrrc with a register because bit 7 exceeds the 5-bit CSRxI immediate limit.

    Args:
        r_scratch: Scratch register to hold the MPIE bitmask
        enable: True → MPIE=1 (MIE=1 in lower mode), False → MPIE=0 (MIE=0)
    """
    op = "CSRS" if enable else "CSRC"
    comment = "MPIE=1 -> MIE=1 after mret" if enable else "MPIE=0 -> MIE=0 after mret"
    return [
        f"LI(x{r_scratch}, 0x80)  # {comment}",
        f"{op}(mstatus, x{r_scratch})",
    ]


def mmode_sti_setup(r_scratch: int, r_stce: int, mideleg_sti: int, mie_stie: int) -> list[str]:
    """Common M-mode setup for Sstc STI tests: disable interrupts, set mideleg/mie/STCE, stimecmp=max.

    Leaves interrupts globally disabled (MIE=0, SIE=0) with stimecmp=-1 (no pending STI).
    Caller must enable MIE/SIE as needed for the specific test.

    Args:
        r_scratch: Scratch register
        r_stce: Register for STCE bit manipulation
        mideleg_sti: 1 to delegate STI to S-mode, 0 for M-mode handling
        mie_stie: 1 to enable STIE in mie, 0 to disable
    """
    lines = [
        "RVTEST_GOTO_MMODE",
        "CSRW(mie, zero)",
        "csrci mstatus, 8",  # MIE=0
        "csrci mstatus, 2",  # SIE=0
        f"LI(x{r_scratch}, 0x20)",
        f"CSRC(mip, x{r_scratch})",  # clear any pending STIP
        *set_stimecmp_max(r_scratch),
        *set_menvcfg_stce(r_stce, True),  # STCE=1
    ]
    # mideleg
    if mideleg_sti:
        lines += [f"LI(x{r_scratch}, 0x20)", f"CSRW(mideleg, x{r_scratch})"]
    else:
        lines.append("CSRW(mideleg, zero)")
    # mie.STIE
    if mie_stie:
        lines += [f"LI(x{r_scratch}, 0x20)", f"CSRW(mie, x{r_scratch})"]
    else:
        lines.append("CSRW(mie, zero)")
    return lines


def mmode_sti_cleanup(r_scratch: int, r_stce: int) -> list[str]:
    """Restore M-mode state after an Sstc STI test."""
    return [
        "RVTEST_GOTO_MMODE",
        "csrci mstatus, 8",
        "csrci mstatus, 2",
        "CSRW(mideleg, zero)",
        "CSRW(mie, zero)",
        *set_stimecmp_max(r_scratch),
        f"LI(x{r_scratch}, 0x20)",
        f"CSRC(mip, x{r_scratch})",
        *set_menvcfg_stce(r_stce, False),  # STCE=0
    ]
