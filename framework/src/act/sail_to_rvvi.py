##################################
# sail_to_rvvi.py
#
# jcarlin@hmc.edu 9 May 2025
# SPDX-License-Identifier: Apache-2.0
#
# Job of this file:
#   Sail prints a long log (*.trace). The coverage TB reads a short file
#   (*.rvvi). This code converts one into the other.
#
# Pipeline:
#   Sail --trace  -->  *.trace  -->  sailLog2Trace()  -->  *.rvvi  -->  TB
#
# One retired instruction = one .rvvi line of KEY VALUE pairs, e.g.:
#   ORDER 12 PC 80000100 INSN 0007a703 MODE 3 MODE_VIRT 0
#     X 14 257a0141 READ_ACCESS 1 WRITE_ACCESS 0 EXECUTE_ACCESS 1
#     VS_PTE_D 200024c7
#
# Extra keys beyond ORDER/PC/INSN/MODE (MODE_VIRT, READ/WRITE_ACCESS,
# VS_PTE_*/G_PTE_*) are required for SvH covergroups to hit.
##################################

import re                                                       # regular expressions to parse Sail log lines
from pathlib import Path                                        # Path type for input/output file names


def sailLog2Trace(inputLogFile: Path, outputTraceFile: Path) -> None:
    """Read one Sail *.trace and write the matching short *.rvvi file."""

    # Match a Sail instruction line like:
    #   [568] [VS]: 0x900002A4 (0x00460613) addi x12, x12, 0x4
    # Groups: order, privilege tag, PC, encoding, rest of text
    insn_pattern = re.compile(
        r"\[(\d+)\] \[([A-Z]+)\]: 0x([0-9a-fA-F]+) \(0x([0-9a-fA-F]+)\) (.*)"
    )

    # Match a memory read value: mem[R,0x...] -> 0xVALUE
    # Used for page-table walks and for the word a load returns
    mem_r_pattern = re.compile(r"mem\[R,0x[0-9a-fA-F]+\] -> 0x([0-9a-fA-F]+)")

    # Match a CSR *write* only (arrow left <-). Reads (->) are ignored here.
    # Example: CSR vsatp (0x280) <- 0x80000000
    csr_wr_pattern = re.compile(r"CSR .* \(0x([0-9a-fA-F]+)\) <- 0x([0-9a-fA-F]+)")

    # Patterns for side effects we append onto the .rvvi line
    reg_patterns = {
        "CSR": re.compile(r"CSR .* \(0x([0-9a-fA-F]+)\) (?:<-|->) 0x([0-9a-fA-F]+)"),  # CSR write or read
        "X": re.compile(r"x(\d+) <- 0x([0-9a-fA-F]+)"),                               # integer reg write
        "F": re.compile(r"f(\d+) <- 0x([0-9a-fA-F]+)"),                               # float reg write
        "V": re.compile(r"v(\d+) <- 0x([0-9a-fA-F]+)"),                               # vector reg write
    }

    # Sail privilege name -> (MODE, MODE_VIRT) numbers the testbench expects
    mode_map = {
        "M": ("3", "0"),                                        # machine, not virtual
        "S": ("1", "0"),                                        # supervisor, not virtual
        "HS": ("1", "0"),                                       # HS looks like S for MODE bits
        "U": ("0", "0"),                                        # user, not virtual
        "VS": ("1", "1"),                                       # virtual supervisor
        "VU": ("0", "1"),                                       # virtual user
    }

    # These flags track "is paging turned on?" as we scan the log top to bottom
    satp_on = False                                             # ordinary satp MODE != Bare?
    vsatp_on = False                                            # guest vsatp MODE != Bare?
    hgatp_on = False                                            # hypervisor hgatp MODE != Bare?

    with inputLogFile.open() as f, outputTraceFile.open("w") as outfile:  # open Sail log in, rvvi out
        lines = f.readlines()                                   # load whole Sail log into memory
        output_line = ""                                        # holds previous insn's rvvi text until we know its end mode
        prev_mode: str | None = None                            # MODE of the instruction we just finished parsing
        prev_mode_virt = "0"                                    # MODE_VIRT of that same instruction

        for i in range(len(lines)):                             # walk every line of the Sail log
            line = lines[i]                                     # current log line text

            # --- Keep satp/vsatp/hgatp "paging on?" flags up to date ---
            csr_wr = csr_wr_pattern.search(line)                # is this line a CSR write?
            if csr_wr:                                          # yes: update paging flags
                addr = int(csr_wr.group(1), 16)                 # CSR address (e.g. 0x280 = vsatp)
                val = int(csr_wr.group(2), 16)                  # value written into that CSR
                # MODE != Bare: RV64 uses bits [63:60], RV32 uses bit 31
                mode_on = ((val >> 60) & 0xF) != 0 or (val & (1 << 31)) != 0
                if addr == 0x180:                               # satp
                    satp_on = mode_on
                elif addr == 0x280:                             # vsatp
                    vsatp_on = mode_on
                elif addr == 0x680:                             # hgatp
                    hgatp_on = mode_on

            insn_match = insn_pattern.search(line)              # is this line a retired instruction?
            if not insn_match:                                  # no: skip (mtime, blank lines, etc.)
                continue

            order, mode_tag, pc, insn, _ = insn_match.groups()  # pull fields out of the Sail insn line
            mode, mode_virt = mode_map.get(mode_tag, ("3", "0"))  # map "VS"/"M"/... to MODE numbers
            insn_val = int(insn, 16)                            # instruction encoding as an integer
            prev_mode = mode                                    # remember MODE for the delayed write below

            # Build this insn's rvvi text. MODE/MODE_VIRT use {placeholders}
            # filled later from the *next* insn (Sail prints start mode; TB
            # wants end mode of the previous insn).
            next_output = (
                f"ORDER {order} PC {pc} INSN {insn} "           # order, PC, encoding
                f"MODE {{mode}} MODE_VIRT {{mode_virt}}"        # filled when next insn arrives
            )

            # ============================================================
            # I-FETCH page walk: look at log lines ABOVE this instruction
            # ============================================================
            # Sail usually prints:
            #   mem[R] PTE
            #   mem[R] PTE
            #   mem[X] fetched instruction bytes
            #   [n] [VS]: ...          <-- we are here
            ifetch_ptes: list[int] = []                         # PTEs from the instruction-fetch walk
            k = i - 1                                           # start one line above the insn
            seen_x = False                                      # have we hit mem[X] yet while scanning up?
            while k >= 0 and not insn_pattern.search(lines[k]):  # stop at previous insn or start of file
                if "mem[W," in lines[k]:                        # store data: not part of ifetch walk
                    break
                if "mem[X," in lines[k]:                        # instruction-byte fetch
                    seen_x = True                               # from here upward, mem[R]s are ifetch PTEs
                elif seen_x:                                    # above mem[X]: collect walk reads
                    mr = mem_r_pattern.search(lines[k])         # mem[R] -> value?
                    if mr:
                        val = int(mr.group(1), 16)              # the PTE (or similar) value
                        # Keep V=1, or V=0 leaves that still have R/W/X or A/D
                        if (val & 1) or ((val & 0xE) and (val & 0xC0)):
                            ifetch_ptes.append(val)             # save this walk entry
                k -= 1                                          # move one line further up
            ifetch_ptes.reverse()                               # put root first, leaf last

            # ============================================================
            # DATA page walk + reg/CSR updates: look at lines AFTER insn
            # ============================================================
            # Store example:
            #   sw
            #   mem[R] PTE(s)
            #   mem[W] store data      <-- stop PTE collection
            #
            # Load / HLV (Sv39, one stage) example:
            #   lw
            #   mem[R] non-leaf
            #   mem[R] non-leaf
            #   mem[R] leaf            <-- keep (coverpoints need this)
            #   mem[R] loaded word     <-- do NOT keep (can look like V=1)
            #
            # Old code stopped after 2 mem[R]s (fine for Sv32, wrong for Sv39).
            # Now stop after enough *leaf* PTEs (bits [3:1] = R/W/X non-zero):
            #   one stage  -> need 1 leaf
            #   two-stage  -> need 2 leaves
            data_ptes: list[int] = []                           # PTEs from the data-access walk
            stop_ptes = False                                   # True = do not collect more PTEs
            saw_store = False                                   # True = we saw mem[W] after this insn
            j = i + 1                                           # start one line below the insn
            while j < len(lines):                               # scan forward until next insn / end
                if insn_pattern.search(lines[j]):               # next retired instruction starts
                    break

                if "mem[W," in lines[j]:                        # store payload written to memory
                    saw_store = True                            # this insn was (or did) a store
                    stop_ptes = True                            # store data is never a PTE
                elif "mem[X," in lines[j]:                      # next insn's ifetch beginning
                    stop_ptes = True                            # leave data-walk collection

                if not stop_ptes:                               # still inside the data walk
                    mr = mem_r_pattern.search(lines[j])         # mem[R] -> value?
                    if mr:
                        val = int(mr.group(1), 16)              # walk PTE or load result
                        # Value "looks like" a PTE candidate?
                        if (val & 1) or ((val & 0xE) and (val & 0xC0)):
                            f7 = (insn_val >> 25) & 0x7F        # funct7 field of the instruction
                            f3 = (insn_val >> 12) & 0x7         # funct3 field of the instruction
                            # Is this a normal load (opcode 0x03) or HLV?
                            is_data_load = (insn_val & 0x7F) == 0x03 or (
                                (insn_val & 0x7F) == 0x73       # SYSTEM opcode
                                and f3 == 0b100                 # HLV/HSV funct3
                                and f7 in (0x34, 0x36)          # HLV funct7 values
                            )
                            if is_data_load:                    # load/HLV: protect against payload
                                # Count leaf PTEs already kept (R/W/X bits set)
                                leaves = sum(1 for p in data_ptes if (p & 0xE) != 0)
                                # Two-stage needs VS leaf + G leaf; else one leaf
                                need = 2 if (vsatp_on and hgatp_on) else 1
                                if leaves < need:               # still missing leaf PTE(s)
                                    data_ptes.append(val)       # keep this walk entry
                                # else: already have leaf(s); this mem[R] is load data — skip
                            else:                               # not a load/HLV (e.g. other cases)
                                data_ptes.append(val)           # keep the mem[R] value

                # Also grab X/F/V/CSR updates printed after the instruction
                for reg, pattern in reg_patterns.items():       # try CSR, then X, then F, then V
                    reg_match = pattern.search(lines[j])        # does this line match?
                    if reg_match:
                        reg_num, reg_val = reg_match.groups()   # register id and new value
                        next_output += f" {reg} {reg_num} {reg_val}"  # append onto rvvi line
                        break                                   # one match per log line is enough
                j += 1                                          # next log line

            # ============================================================
            # Access flags: was this a read, a write, or both?
            # ============================================================
            is_load = (insn_val & 0x7F) == 0x03                 # LOAD opcode
            is_store = (insn_val & 0x7F) == 0x23 or saw_store    # STORE opcode, or we saw mem[W]
            is_hlv = False                                      # hypervisor load virtual?
            is_hsv = False                                      # hypervisor store virtual?
            if (insn_val & 0x7F) == 0x73:                       # SYSTEM opcode family
                f7 = (insn_val >> 25) & 0x7F                    # funct7
                f3 = (insn_val >> 12) & 0x7                     # funct3
                if f3 == 0b100 and f7 in (0x34, 0x36):          # HLV encodings
                    is_hlv = True
                if f3 == 0b100 and f7 == 0x35:                   # HSV encoding
                    is_hsv = True
            read_a = "1" if is_load or is_hlv else "0"          # mark READ_ACCESS for load/HLV
            write_a = "1" if is_store or is_hsv else "0"        # mark WRITE_ACCESS for store/HSV
            next_output += (
                f" READ_ACCESS {read_a} WRITE_ACCESS {write_a} EXECUTE_ACCESS 1"
            )

            # ============================================================
            # Decide which leaf is VS-stage and which is G-stage
            # ============================================================
            # A "leaf" has R/W/X bits [3:1] non-zero.
            #   vsatp only  -> last leaf is VS
            #   hgatp only  -> last leaf is G
            #   both on     -> normally 2nd-to-last = VS, last = G
            #
            # Fault quirk: sometimes Sail never walks a G data leaf. Then the
            # last leaf may be the VS data page (e.g. X-only) and the one before
            # it is G's map of that VS PTE (R+W). Swap so labels stay correct.
            def stage(ptes: list[int]) -> tuple[int, int]:
                leaves = [p for p in ptes if (p & 0xE) != 0]    # keep only leaf PTEs
                if not leaves:                                  # no leaf found
                    return 0, 0                                 # (vs=0, g=0)
                if vsatp_on and hgatp_on and len(leaves) >= 2:  # two-stage walk
                    vs_leaf, g_leaf = leaves[-2], leaves[-1]    # assume VS then G
                    xonly = lambda p: (p & 0xE) == 0x8          # X only (no R/W)
                    pt_map = lambda p: (p & 0xE) == 0x6         # R+W (typical PT map)
                    if xonly(g_leaf) and pt_map(vs_leaf):       # order was swapped by fault path
                        return g_leaf, vs_leaf                  # return (VS data, G-of-PT)
                    return vs_leaf, g_leaf                      # normal VS then G
                if vsatp_on and not hgatp_on:                   # VS-stage only
                    return leaves[-1], 0                        # (VS leaf, no G)
                return 0, leaves[-1]                            # G-stage only (or satp via g slot)

            vs_i, g_i = stage(ifetch_ptes)                      # ifetch: VS leaf, G leaf
            vs_d, g_d = stage(data_ptes)                        # data:   VS leaf, G leaf

            # ============================================================
            # Emit PTE keys only if that translation is actually on
            # ============================================================
            # If nothing is paged, print no PTE_* keys (avoids calling a load
            # result a "PTE").
            hypervisor = vsatp_on or hgatp_on                   # any H-stage / VS paging?
            if satp_on and not hypervisor:                      # classic satp only
                leaf_i = vs_i or g_i                            # ifetch leaf (either slot)
                leaf_d = vs_d or g_d                            # data leaf (either slot)
                if leaf_i:
                    next_output += f" PTE_I {leaf_i:x}"         # ifetch PTE for satp
                if leaf_d:
                    next_output += f" PTE_D {leaf_d:x}"         # data PTE for satp
            elif hypervisor:                                    # vsatp and/or hgatp
                if vs_i:
                    next_output += f" VS_PTE_I {vs_i:x}"        # VS ifetch leaf
                if vs_d:
                    next_output += f" VS_PTE_D {vs_d:x}"        # VS data leaf
                if g_i:
                    next_output += f" G_PTE_I {g_i:x}"          # G ifetch leaf
                if g_d:
                    next_output += f" G_PTE_D {g_d:x}"          # G data leaf

            next_output += "\n"                                 # end of this insn's rvvi line

            # Write the *previous* insn now: this insn's start mode is that
            # previous insn's end mode (what coverpoints sample as prev.*).
            if output_line:                                     # there is a pending previous line
                outfile.write(
                    output_line.format(mode=prev_mode, mode_virt=mode_virt)
                )
            output_line = next_output                           # current insn becomes the new "pending"
            prev_mode_virt = mode_virt                          # save MODE_VIRT for last-insn flush

        # Last instruction in the file has no follower — use its own start mode
        if output_line and prev_mode is not None:
            outfile.write(
                output_line.format(mode=prev_mode, mode_virt=prev_mode_virt)
            )
