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

    # Memory operand in the disassembly, such as "0x4(x9)" in "lw x13, 0x4(x9)" or "(x6)" in "amoadd.w x8, x14, (x6)"
    mem_operand_pattern = re.compile(r"(-?0x[0-9a-fA-F]+)?\(x(\d+)\)")

    # Mode mapping
    mode_map = {"M": "3", "S": "1", "HS": "1", "U": "0"}

    # TODO: Add support for parsing traps, interrupts, and the remaining VM signals

    # Main parsing of log file
    with inputLogFile.open() as f, outputTraceFile.open("w") as outfile:
        lines = f.readlines()
        output_line = ""
        prev_mode_num: str | None = None
        # Integer register values, tracked from the logged writes, to compute effective addresses
        xregs = [0] * 32
        for i in range(len(lines)):
            line = lines[i]

            # Check for instruction line
            insn_match = insn_pattern.search(line)
            if insn_match:
                order, prev_mode, pc, insn, disasm = insn_match.groups()
                prev_mode_num = mode_map.get(prev_mode)

                # Format the beginning of the instruction line
                # mode_num is set later based on the mode for the next instruction because RVVI expects the
                # mode at the end of the instruction but Sail logs have the mode at the start of the instruction.
                next_output = f"ORDER {order} PC {pc} INSN {insn} MODE " + "{mode_num}"

                # VIRT_ADR_I is the PC. VIRT_ADR_D is the effective address of a scalar load, store, AMO, or CMO,
                # whether or not the access faults. jalr names a jump target, prefetch does not access memory, and
                # a vector access has an address per element, so they get no VIRT_ADR_D.
                # Sail prints the PC with XLEN/4 hex digits.
                next_output += f" VIRT_ADR_I {pc}"
                mnemonic = disasm.partition(" ")[0]
                mem_match = mem_operand_pattern.search(disasm)
                if mem_match and mnemonic != "jalr" and not mnemonic.startswith(("prefetch.", "v")):
                    offset, base = mem_match.groups()
                    vaddr = (xregs[int(base)] + int(offset or "0", 16)) & ((1 << (4 * len(pc))) - 1)
                    next_output += f" VIRT_ADR_D {vaddr:0{len(pc)}X}"

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
                for (reg_type, reg_num), reg_val in reg_writes.items():
                    next_output += f" {reg_type} {reg_num} {reg_val}"
                    if reg_type == "X":
                        xregs[int(reg_num)] = int(reg_val, 16)

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
