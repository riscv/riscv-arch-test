##################################
# sail-to-rvvi.py
#
# jcarlin@hmc.edu 9 May 2025
# SPDX-License-Identifier: Apache-2.0
#
# Convert a Sail log file into a trace format for use
# with RVVI input to riscv-arch-test
##################################

import re
from pathlib import Path

MSTATUS = "300"
SSTATUS = "100"


def _sstatus_mask(xlen: int) -> int:
    """Return the mstatus bits visible through sstatus."""
    # SIE, SPIE, UBE, SPP, VS, FS, XS, SUM, MXR, SPELP, SDT
    bits = [1, 5, 6, 8, 9, 10, 13, 14, 15, 16, 18, 19, 23, 24]
    if xlen == 64:
        bits += [32, 33]  # UXL
    bits.append(xlen - 1)  # SD
    return sum(1 << b for b in bits)


def _alias_status_writes(reg_writes: dict[tuple[str, str], str], last_mstatus: int | None) -> int | None:
    """Add the sstatus or mstatus update implied by a write to the other.

    sstatus is a view of mstatus, but Sail logs only the register named in the instruction.
    Returns the mstatus value after this instruction, or None if it is not yet known.
    """
    mstatus = reg_writes.get(("CSR", MSTATUS))
    sstatus = reg_writes.get(("CSR", SSTATUS))
    if mstatus is not None:
        xlen = len(mstatus) * 4
        value = int(mstatus, 16)
        reg_writes[("CSR", SSTATUS)] = f"{value & _sstatus_mask(xlen):0{len(mstatus)}X}"
        return value
    if sstatus is not None and last_mstatus is not None:
        xlen = len(sstatus) * 4
        mask = _sstatus_mask(xlen)
        value = (last_mstatus & ~mask) | (int(sstatus, 16) & mask)
        reg_writes[("CSR", MSTATUS)] = f"{value:0{len(sstatus)}X}"
        return value
    return last_mstatus


def sailLog2Trace(inputLogFile: Path, outputTraceFile: Path) -> None:
    # Regular expression to match instruction lines
    #                             [STEP]     [MODE]:    0xPC              (0xINSN)           DISASM
    insn_pattern = re.compile(r"\[(\d+)\] \[(HS|M|S|U)\]: 0x([0-9a-fA-F]+) \(0x([0-9a-fA-F]+)\) (.*)")

    # Regular expressions to match register updates
    reg_patterns = {
        "CSR": re.compile(r"CSR .* \(0x([0-9a-fA-F]+)\) (?:<-|->) 0x([0-9a-fA-F]+)"),
        "X": re.compile(r"x(\d+) <- 0x([0-9a-fA-F]+)"),
        "F": re.compile(r"f(\d+) <- 0x([0-9a-fA-F]+)"),
        "V": re.compile(r"v(\d+) <- 0x([0-9a-fA-F]+)"),
    }

    # Mode mapping
    mode_map = {"M": "3", "S": "1", "HS": "1", "U": "0"}

    # TODO: Add support for parsing traps, interrupts, and VM signals

    # Main parsing of log file
    with inputLogFile.open() as f, outputTraceFile.open("w") as outfile:
        lines = f.readlines()
        output_line = ""
        prev_mode_num: str | None = None
        last_mstatus: int | None = None
        for i in range(len(lines)):
            line = lines[i]

            # Check for instruction line
            insn_match = insn_pattern.search(line)
            if insn_match:
                order, prev_mode, pc, insn, _ = insn_match.groups()
                prev_mode_num = mode_map.get(prev_mode)

                # Format the beginning of the instruction line
                # mode_num is set later based on the mode for the next instruction because RVVI expects the
                # mode at the end of the instruction but Sail logs have the mode at the start of the instruction.
                next_output = f"ORDER {order} PC {pc} INSN {insn} MODE " + "{mode_num}"

                # Check for register updates until the next instruction line.  Sail logs every
                # element a vector instruction writes as a separate whole-register update, so a
                # vector load can log a register a thousand times; only the final value of each
                # register matters, so keep the last write per register in first-write order.
                reg_writes: dict[tuple[str, str], str] = {}
                j = i + 1
                while j < len(lines):
                    for reg, pattern in reg_patterns.items():
                        reg_match = pattern.search(lines[j])
                        if reg_match:
                            reg_num, reg_val = reg_match.groups()
                            reg_writes[(reg, reg_num)] = reg_val
                            break
                    if insn_pattern.search(lines[j]):
                        break
                    j += 1
                last_mstatus = _alias_status_writes(reg_writes, last_mstatus)
                for (reg_type, reg_num), reg_val in reg_writes.items():
                    next_output += f" {reg_type} {reg_num} {reg_val}"

                # Reached end of instruction
                next_output += "\n"

                # Update the previous instruction with the new privilege mode and output it to the trace file
                output_line = output_line.format(mode_num=prev_mode_num)
                outfile.write(output_line)
                output_line = next_output

        # Flush the final instruction. Sail logs mode at the start of an
        # instruction, so the trailing instruction has no "next" mode to
        # inherit from; fall back to its own start mode as the closest
        # approximation rather than dropping it from the trace.
        if output_line and prev_mode_num is not None:
            outfile.write(output_line.format(mode_num=prev_mode_num))
