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

    # Mode mapping
    mode_map = {"M": "3", "S": "1", "HS": "1", "U": "0"}

    # sip and sie are restricted views of mip and mie through mideleg, and Sail logs only the view
    # that was accessed. A csrrs to sip therefore leaves the mip the covergroups read unchanged, so
    # an interrupt S-mode raised for itself is invisible to any coverpoint keyed on mip. Mirror the
    # S view back into the M register: the delegated bits take the logged value and the rest keep
    # what mip/mie already held. A read mirrors to the same value it already has, so it costs
    # nothing and resynchronises after a write this converter did not see.
    SIP, MIP, SIE, MIE, MIDELEG = 0x144, 0x344, 0x104, 0x304, 0x303
    s_view_of = {SIP: MIP, SIE: MIE}
    csr_state: dict[int, int] = {}

    # TODO: Add support for parsing traps, interrupts, and VM signals

    # Main parsing of log file
    with inputLogFile.open() as f, outputTraceFile.open("w") as outfile:
        lines = f.readlines()
        output_line = ""
        prev_mode_num: str | None = None
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
                            if reg == "CSR":
                                csr_num, csr_val = int(reg_num, 16), int(reg_val, 16)
                                csr_state[csr_num] = csr_val
                                m_num = s_view_of.get(csr_num)
                                if m_num is not None:
                                    mideleg = csr_state.get(MIDELEG, 0)
                                    m_val = (csr_state.get(m_num, 0) & ~mideleg) | (csr_val & mideleg)
                                    csr_state[m_num] = m_val
                                    reg_writes[("CSR", f"{m_num:x}")] = f"{m_val:016x}"
                            break
                    if insn_pattern.search(lines[j]):
                        break
                    j += 1
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
