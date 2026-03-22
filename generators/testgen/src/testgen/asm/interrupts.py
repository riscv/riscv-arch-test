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
        "# Cause machine timer interrupt",
        f"LA(x{r_mtime}, RVMODEL_MTIME_ADDRESS)",
        f"LA(x{r_mtimecmp}, RVMODEL_MTIMECMP_ADDRESS)",
        "#if __riscv_xlen == 64",
        f"LREG x{r_temp}, 0(x{r_mtime})",
        f"SREG x{r_temp}, 0(x{r_mtimecmp})",
        "#elif __riscv_xlen == 32",
        # Per RISC-V Priv Spec
        f"lw x{r_temp2}, 4(x{r_mtime}) # Read high word first",
        f"lw x{r_temp}, 0(x{r_mtime}) # Read low word",
        f"lw x{r_temp2}, 4(x{r_mtime}) # Re-read high word",
        # Now write to mtimecmp
        f"sw x{r_temp}, 0(x{r_mtimecmp}) # Write low word",
        f"sw x{r_temp2}, 4(x{r_mtimecmp}) # Write high word",
        "#endif",
    ]


def clr_mtimer_int(r_temp: int, r_mtimecmp: int) -> list[str]:
    """Generate assembly to clear machine timer interrupt (mtimecmp = -1).


    Args:
        r_temp: Register number for -1 value
        r_mtimecmp: Register number to hold MTIMECMP address
    """
    return [
        "# Clear machine timer interrupt",
        f"LI(x{r_temp}, -1)",
        f"LA(x{r_mtimecmp}, RVMODEL_MTIMECMP_ADDRESS)",
        f"SREG x{r_temp}, 0(x{r_mtimecmp})",
        "#if __riscv_xlen == 32",
        f"sw x{r_temp}, 4(x{r_mtimecmp})",
        "#endif",
    ]


def set_mtimer_int_soon(
    r_mtime: int, r_mtimecmp: int, r_temp1: int, r_temp2: int, r_temp3: int, r_temp4: int
) -> list[str]:
    return [
        "# Cause machine timer interrupt soon",
        f"LA(x{r_mtime}, RVMODEL_MTIME_ADDRESS)",
        f"LA(x{r_mtimecmp}, RVMODEL_MTIMECMP_ADDRESS)",
        "#if __riscv_xlen == 64",
        # Set mtimecmp to max value first to prevent spurious interrupt.
        # If mtimecmp < mtime from a previous test,
        # mip.MTIP would be set immediately when we enable MTIE, causing
        # an unexpected trap before we're ready.
        f"LI(x{r_temp1}, -1)",
        f"sd x{r_temp1}, 0(x{r_mtimecmp})",
        f"{INDENT}# Read current time",
        f"ld x{r_temp1}, 0(x{r_mtime})",
        f"addi x{r_temp1}, x{r_temp1}, RVMODEL_TIMER_INT_SOON_DELAY",
        f"sd x{r_temp1}, 0(x{r_mtimecmp})",
        "#elif __riscv_xlen == 32",
        f"{INDENT}# Disable comparator first",
        f"LI(x{r_temp1}, -1)",
        f"sw x{r_temp1}, 0(x{r_mtimecmp})",
        f"sw x{r_temp1}, 4(x{r_mtimecmp})",
        f"{INDENT}# Read current time",
        f"lw x{r_temp1}, 0(x{r_mtime})",
        f"lw x{r_temp2}, 4(x{r_mtime})",
        f"addi x{r_temp3}, x{r_temp1}, RVMODEL_TIMER_INT_SOON_DELAY",
        f"sltu x{r_temp4}, x{r_temp3}, x{r_temp1}",
        f"add x{r_temp2}, x{r_temp2}, x{r_temp4}",
        f"sw x{r_temp3}, 0(x{r_mtimecmp})",
        f"sw x{r_temp2}, 4(x{r_mtimecmp})",
        "#endif",
    ]


def set_stimer_int(r_mtime: int, r_temp: int, r_temp2: int, r_scratch: int) -> list[str]:
    """Set supervisor timer interrupt.

    Checks menvcfg.STCE at runtime:
    - If STCE=1: Use Sstc method (write stimecmp from S-mode)
    - If STCE=0: Use legacy method (write mip.STIP from M-mode)
    """
    return [
        "# Set supervisor timer interrupt",
        f"{INDENT}# Check if Sstc is enabled",
        f"CSRR x{r_scratch}, menvcfg",
        "#if __riscv_xlen == 64",
        f"SRLI x{r_scratch}, x{r_scratch}, 63",  # STCE is bit 63
        "#else",
        f"SRLI x{r_scratch}, x{r_scratch}, 31",  # STCE is bit 31 on RV32
        "#endif",
        f"ANDI x{r_scratch}, x{r_scratch}, 0x1",
        f"BEQZ x{r_scratch}, 1f # If STCE=0, use non sstc method",
        "",
        "# Sstc method: Write stimecmp",
        f"LA(x{r_mtime}, RVMODEL_MTIME_ADDRESS)",
        f"LREG x{r_temp}, 0(x{r_mtime})",
        f"csrw stimecmp, x{r_temp}",
        "nop",
        "#if __riscv_xlen == 32",
        f"LI(x{r_temp}, -1)",
        f"csrw stimecmp, x{r_temp}",
        f"lw x{r_temp2}, 4(x{r_mtime})",
        f"lw x{r_temp}, 0(x{r_mtime})",
        f"csrw stimecmph, x{r_temp2}",
        f"csrw stimecmp, x{r_temp}",
        "nop",
        "#endif",
        "j 2f",
        "",
        "1: # Legacy method: Set mip.STIP from M-mode",
        f"LI(x{r_temp}, 0x20)",  # STIP = bit 5
        f"csrrs x{r_temp}, mip, x{r_temp}",
        "",
        "2: # Continue",
    ]


def clr_stimer_int(r_temp: int, r_stimecmp: int, r_scratch: int) -> list[str]:
    """Clear supervisor timer interrupt.

    Checks menvcfg.STCE at runtime:
    - If STCE=1: Use Sstc method (write stimecmp = -1)
    - If STCE=0: Use legacy method (clear mip.STIP from M-mode)
    """
    return [
        "# Clear supervisor timer interrupt",
        f"{INDENT}# Check if Sstc is enabled",
        f"CSRR x{r_scratch}, menvcfg",
        "#if __riscv_xlen == 64",
        f"SRLI x{r_scratch}, x{r_scratch}, 63",  # STCE is bit 63
        "#else",
        f"SRLI x{r_scratch}, x{r_scratch}, 31",  # STCE is bit 31 on RV32
        "#endif",
        f"ANDI x{r_scratch}, x{r_scratch}, 0x1",
        f"BEQZ x{r_scratch}, 1f # If STCE=0, use non sstc method",
        "",
        "# Sstc method: Write stimecmp = -1 (max value)",
        f"LI(x{r_temp}, -1)",
        f"csrw stimecmp, x{r_temp}",
        "#if __riscv_xlen == 32",
        f"csrw stimecmph, x{r_temp}",  # Also clear high word
        "#endif",
        "j 2f",
        "",
        "1: # Legacy method: Clear mip.STIP from M-mode",
        f"LI(x{r_temp}, 0x20)",  # STIP = bit 5
        f"csrrc x{r_temp}, mip, x{r_temp}",
        "",
        "2: # Continue",
    ]


def set_stimer_int_soon_sstc(r_mtime: int, r_temp1: int, r_temp2: int, r_temp3: int, r_temp4: int) -> list[str]:
    """Set supervisor timer interrupt to fire soon WITH Sstc extension.


    Uses stimecmp CSR (not MTIMECMP memory). Otherwise identical to set_mtimer_int_soon.
    """
    return [
        "# Set supervisor timer interrupt to fire soon with Sstc extension",
        f"LA(x{r_mtime}, RVMODEL_MTIME_ADDRESS)",
        "#if __riscv_xlen == 64",
        "# Disable comparator first",
        f"LI(x{r_temp1}, -1)",
        f"csrw stimecmp, x{r_temp1}",
        "# Read current time and add delay",
        f"ld x{r_temp1}, 0(x{r_mtime})",
        f"addi x{r_temp1}, x{r_temp1}, RVMODEL_TIMER_INT_SOON_DELAY",
        f"csrw stimecmp, x{r_temp1}",
        "#elif __riscv_xlen == 32",
        "# Disable comparator first --> set to high value to prevent early firing",
        f"LI(x{r_temp1}, -1)",
        f"csrw stimecmp, x{r_temp1}",
        f"csrw stimecmph, x{r_temp1}",
        "# Read current time",
        f"lw x{r_temp1}, 0(x{r_mtime})",
        f"lw x{r_temp2}, 4(x{r_mtime})",
        f"addi x{r_temp3}, x{r_temp1}, RVMODEL_TIMER_INT_SOON_DELAY",
        f"sltu x{r_temp4}, x{r_temp3}, x{r_temp1}",
        f"add x{r_temp2}, x{r_temp2}, x{r_temp4}",
        f"csrw stimecmp, x{r_temp3}",
        f"csrw stimecmph, x{r_temp2}",
        "#endif",
    ]
