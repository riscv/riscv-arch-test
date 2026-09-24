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

    # Page-table walks (Sail --trace-ptw): one "PTW: Step" per level, ending in "PTW: Success" or "PTW: failed".
    # The last step holds the PTE the walk stopped on. A data walk belongs to the instruction being logged;
    # an instruction fetch walk (access_type X) is logged just before the instruction it fetches.
    ptw_start_pattern = re.compile(r"PTW: Start, vpn=0x([0-9a-fA-F]+), access_type=(\S+),")
    ptw_step_pattern = re.compile(r"PTW: Step, level=\d+, pte=0x([0-9a-fA-F]+)")
    ptw_end_pattern = re.compile(r"PTW: (Success, final_ppn=0x([0-9a-fA-F]+)|failed)")
    # Sail caches successful walks in its TLB, so a repeated access to a page logs no walk. The leaf PTE of
    # each walk is kept until the next TLB flush so that TLB hits still report their PTE: by physical page
    # for accesses that reach memory, and by virtual page for accesses that fault before reaching it.
    # An access that spans pages reports the last page it touched.
    mem_pattern = re.compile(r"mem\[([A-Za-z.]+),0x([0-9a-fA-F]+)\]")
    tlb_flush_pattern = re.compile(r"(?:sfence|sinval|hfence|hinval)\.")
    satp_pattern = re.compile(r"CSR satp \(0x180\) (?:<-|->) 0x([0-9a-fA-F]+)")

    # Exceptions log "trapping from"; interrupts log "Handling interrupt" first. A fetch fault is logged in the
    # record of the instruction before it, which did retire.
    trap_pattern = re.compile(r"trapping from \S+ to \S+ to handle (\S+)")
    exc_pattern = re.compile(r"handling exc#(?:load|store/amo)-(?:access|page)-fault .* tval=0x([0-9a-fA-F]+)")
    interrupt_pattern = re.compile(r"Handling interrupt")
    fetch_faults = ("fetch-access-fault", "fetch-page-fault", "fetch-guest-page-fault")

    # Mode mapping
    mode_map = {"M": "3", "S": "1", "HS": "1", "U": "0"}

    # TODO: Add support for parsing interrupts and the remaining VM signals

    # Main parsing of log file
    with inputLogFile.open() as f, outputTraceFile.open("w") as outfile:
        lines = f.readlines()
        output_line = ""
        prev_mode_num: str | None = None
        walk_access = ""
        walk_pte: str | None = None
        next_pte_i: str | None = None
        next_fetch_ppn: int | None = None
        tlb: dict[int, str | None] = {}
        tlb_va: dict[int, str] = {}
        walk_vpn = 0
        translating = False
        for i in range(len(lines)):
            line = lines[i]

            # Check for instruction line
            insn_match = insn_pattern.search(line)
            if insn_match:
                order, prev_mode, pc, insn, disasm = insn_match.groups()
                prev_mode_num = mode_map.get(prev_mode)
                translated = translating and prev_mode != "M"

                # Format the beginning of the instruction line
                # mode_num is set later based on the mode for the next instruction because RVVI expects the
                # mode at the end of the instruction but Sail logs have the mode at the start of the instruction.
                next_output = f"ORDER {order} PC {pc} INSN {insn} MODE " + "{mode_num}"
                pte_i, next_pte_i = next_pte_i, None
                if pte_i is None and translated and next_fetch_ppn is not None:
                    pte_i = tlb.get(next_fetch_ppn)
                next_fetch_ppn = None
                pte_d: str | None = None
                trap = False
                interrupt = False
                if tlb_flush_pattern.match(disasm):
                    tlb.clear()
                    tlb_va.clear()

                # Check for register updates until the next instruction line.  Sail logs every
                # element a vector instruction writes as a separate whole-register update, so a
                # vector load can log a register a thousand times; only the final value of each
                # register matters, so keep the last write per register in first-write order.
                reg_writes: dict[tuple[str, str], str] = {}
                j = i + 1
                while j < len(lines):
                    if insn_pattern.search(lines[j]):
                        break
                    if ptw_start := ptw_start_pattern.search(lines[j]):
                        walk_vpn = int(ptw_start.group(1), 16)
                        walk_access = ptw_start.group(2)
                        walk_pte = walk_pte or ""
                    elif ptw_step := ptw_step_pattern.search(lines[j]):
                        walk_pte = ptw_step.group(1)
                    elif (ptw_end := ptw_end_pattern.search(lines[j])) and walk_pte is not None:
                        if walk_pte:
                            if walk_access.startswith("X"):
                                next_pte_i = walk_pte
                            else:
                                pte_d = walk_pte
                            if ptw_end.group(2):
                                ppn = int(ptw_end.group(2), 16)
                                # A page reached through two different PTEs cannot be attributed on a TLB hit
                                tlb[ppn] = walk_pte if tlb.get(ppn, walk_pte) == walk_pte else None
                                tlb_va[walk_vpn] = walk_pte
                            else:
                                tlb_va.pop(walk_vpn, None)
                        walk_pte = None
                    elif walk_pte is not None:
                        pass
                    elif mem := mem_pattern.search(lines[j]):
                        ppn = int(mem.group(2), 16) >> 12
                        if mem.group(1) == "X":
                            next_fetch_ppn = ppn
                        elif translated and tlb.get(ppn) is not None:
                            pte_d = tlb[ppn]
                    elif trap_match := trap_pattern.search(lines[j]):
                        trap = trap or not (interrupt or trap_match.group(1) in fetch_faults)
                        next_pte_i = None
                        next_fetch_ppn = None
                    elif exc := exc_pattern.search(lines[j]):
                        vpn = int(exc.group(1), 16) >> 12
                        if translated and vpn in tlb_va:
                            pte_d = tlb_va[vpn]
                    elif interrupt_pattern.search(lines[j]):
                        interrupt = True
                    else:
                        if satp := satp_pattern.search(lines[j]):
                            satp_val = satp.group(1)
                            translating = int(satp_val, 16) >> (60 if len(satp_val) > 8 else 31) != 0
                        for reg, pattern in reg_patterns.items():
                            reg_match = pattern.search(lines[j])
                            if reg_match:
                                reg_num, reg_val = reg_match.groups()
                                reg_writes[(reg, reg_num)] = reg_val
                                break
                    j += 1
                for (reg_type, reg_num), reg_val in reg_writes.items():
                    next_output += f" {reg_type} {reg_num} {reg_val}"
                if trap:
                    next_output += " TRAP 1"
                if pte_i is not None:
                    next_output += f" PTE_I {pte_i}"
                if pte_d is not None:
                    next_output += f" PTE_D {pte_d}"

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
