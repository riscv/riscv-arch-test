##################################
# sail-to-rvvi.py
#
# jcarlin@hmc.edu 9 May 2025
# SPDX-License-Identifier: Apache-2.0
#
# Convert a Sail log file (*.trace) into a short Tracefile (*.rvvi) for the
# ACT4 coverage testbench (RVVI).
#
# Pipeline:
#   Sail --trace → *.trace  →  sailLog2Trace()  →  *.rvvi  →  testbench.sv
#
# Output format (one retired insn per line, space-separated KEY VALUE):
#   ORDER <n> PC <hex> INSN <hex> MODE <0|1|3> MODE_VIRT <0|1>
#     [X|F|V|CSR <id> <val>]…
#     READ_ACCESS <0|1> WRITE_ACCESS <0|1> EXECUTE_ACCESS 1
#     [PTE_I|PTE_D|VS_PTE_*|G_PTE_* <hex>]…
#
# Original behavior (unchanged idea):
#   One Sail insn → one .rvvi line with ORDER / PC / INSN / MODE + X/F/V/CSR.
#
# Extensions for SvH (coverpoints need these; old converter left them 0):
#   1) MODE_VIRT + accept Sail tags VS / VU / HS
#   2) READ / WRITE / EXECUTE_ACCESS from opcode (and mem[W] for hsv.w)
#   3) VS_PTE_* / G_PTE_* from page-walk mem[R], labeled via vsatp/hgatp MODE
##################################

import re
from pathlib import Path


def sailLog2Trace(inputLogFile: Path, outputTraceFile: Path) -> None:
    # Regular expression to match instruction lines
    # Sail example:  [568]  [VS]:   0x900002A4 (0x00460613) addi x12, x12, 0x4
    #               [STEP]  [MODE]: 0xPC       (0xINSN)     DISASM
    # MODE is [A-Z]+ so VS/VU/HS match too (old file only allowed [MSU]).
    insn_pattern = re.compile(r"\[(\d+)\] \[([A-Z]+)\]: 0x([0-9a-fA-F]+) \(0x([0-9a-fA-F]+)\) (.*)")

    # Page-table (or data) reads during a walk / load
    # Sail example:  mem[R,0x08000C100]   ->     0x20001801
    #                address ignored            captured PTE/data value
    mem_r_pattern = re.compile(r"mem\[R,0x[0-9a-fA-F]+\] -> 0x([0-9a-fA-F]+)")

    # CSR *writes* only (<-). Used to track vsatp/hgatp MODE.
    # Sail example:  CSR vsatp    (0x280) <-     0x80000000
    #                             ADDR           VALUE
    # Reads (->) must not flip vsatp_on / hgatp_on.
    csr_wr_pattern = re.compile(r"CSR .* \(0x([0-9a-fA-F]+)\) <- 0x([0-9a-fA-F]+)")

    # Regular expressions to match register / CSR updates (emitted into .rvvi)
    # CSR:  CSR mstatus (0x300) <- 0x80006680   or   … -> 0x…
    # X:    x12 <- 0x257A0005
    # F/V:  same shape for float / vector regs
    reg_patterns = {
        "CSR": re.compile(r"CSR .* \(0x([0-9a-fA-F]+)\) (?:<-|->) 0x([0-9a-fA-F]+)"),
        "X"  : re.compile(r"x(\d+) <- 0x([0-9a-fA-F]+)"),
        "F"  : re.compile(r"f(\d+) <- 0x([0-9a-fA-F]+)"),
        "V"  : re.compile(r"v(\d+) <- 0x([0-9a-fA-F]+)"),
    }

    # Privilege mapping: Sail tag → (MODE, MODE_VIRT) Tracefile values.
    # Same names as TB/SV: mode (0/1/3), mode_virt (0/1).
    # Coverpoints use {ins.*.mode_virt, ins.*.mode}, e.g. HS = 3'b001.
    mode_map = {
        "M": ("3", "0"),   # 3'b011
        "S": ("1", "0"),   # 3'b001
        "HS": ("1", "0"),  # 3'b001  (same as S; H makes it HS)
        "U": ("0", "0"),   # 3'b000
        "VS": ("1", "1"),  # 3'b101
        "VU": ("0", "1"),  # 3'b100
    }

    # Track whether translation is enabled (RV32 MODE = bit 31).
    # satp 0x180 = classic Sv; vsatp 0x280 / hgatp 0x680 = hypervisor.
    satp_on = False
    vsatp_on = False
    hgatp_on = False

    # Main parsing of log file
    with inputLogFile.open() as f, outputTraceFile.open("w") as outfile:
        lines = f.readlines()
        output_line = ""
        prev_mode: str | None = None
        prev_mode_virt = "0"   # used only when flushing the last insn

        for i in range(len(lines)):
            line = lines[i]

            # --- Always: update satp MODE from CSR writes (even between insns) ---
            # RV32: MODE = bit 31.  RV64: MODE = bits [63:60] (Bare=0).
            csr_wr = csr_wr_pattern.search(line)
            if csr_wr:
                addr = int(csr_wr.group(1), 16)
                val = int(csr_wr.group(2), 16)
                mode_on = ((val >> 60) & 0xF) != 0 or (val & (1 << 31)) != 0
                if addr == 0x180:
                    satp_on = mode_on
                elif addr == 0x280:
                    vsatp_on = mode_on
                elif addr == 0x680:
                    hgatp_on = mode_on

            # --- Only act on instruction lines; skip chatter ---
            insn_match = insn_pattern.search(line)
            if not insn_match:
                continue

            order, mode_tag, pc, insn, _ = insn_match.groups()
            # Locals named like SV fields: mode / mode_virt
            # Tracefile keys stay MODE / MODE_VIRT (parsed by testbench.sv).
            mode, mode_virt = mode_map.get(mode_tag, ("3", "0"))
            insn_val = int(insn, 16)
            prev_mode = mode

            # Start of this insn's .rvvi line.
            # MODE / MODE_VIRT are placeholders: filled from the *next* insn's
            # start mode (Sail prints start-of-insn mode; RVVI wants end-of-insn).
            next_output = (
                f"ORDER {order} PC {pc} INSN {insn} "
                f"MODE {{mode}} MODE_VIRT {{mode_virt}}"
            )

            # --- Ifetch page walk sits *above* this insn in the Sail log ---
            #   mem[R] -> PTE          ← collect these (after seeing mem[X])
            #   mem[R] -> PTE
            #   mem[X] -> insn bytes   ← marks start of ifetch
            #   [n] [VS]: …            ← we are here (index i)
            # Walk backward until previous insn (or mem[W]). Do not reuse the
            # previous store's data PTEs — that inflated I-side cover bins.
            ifetch_ptes: list[int] = []
            k = i - 1
            seen_x = False
            while k >= 0 and not insn_pattern.search(lines[k]):
                if "mem[W," in lines[k]:
                    break
                if "mem[X," in lines[k]:
                    seen_x = True
                elif seen_x:
                    mr = mem_r_pattern.search(lines[k])
                    if mr:
                        val = int(mr.group(1), 16)
                        # Keep V=1 walks, and V=0 invalid leaves (A/D + R/W/X)
                        # so invalid-PTE cover bins can still see them.
                        if (val & 1) or ((val & 0xE) and (val & 0xC0)):
                            ifetch_ptes.append(val)
                k -= 1
            ifetch_ptes.reverse()  # root → leaf order

            # --- After this insn: register updates + data-side page walk ---
            # Sail layout for a store:
            #   [n] [VS]: … sw …
            #   mem[R] -> PTE          ← data walk
            #   mem[W] -> store data   ← stop PTE collection (payload ≠ PTE)
            #   [n+1] …
            # Stop PTE collection also at next mem[X] (next insn's ifetch). After the store, the next instruction must be fetched.
            data_ptes: list[int] = []
            stop_ptes = False #Should I keep collecting PTEs?
            saw_store = False #Did this instruction actually perform a store?
            j = i + 1
            while j < len(lines):
                if insn_pattern.search(lines[j]):
                    break

                if "mem[W," in lines[j]:
                    saw_store = True
                    stop_ptes = True  # store data — not a PTE
                elif "mem[X," in lines[j]:
                    stop_ptes = True  # next insn's ifetch starts here

                # If we are still inside the page-table walk, look for memory reads (mem[R]), check if the value looks like a PTE, and save it.
                if not stop_ptes:
                    mr = mem_r_pattern.search(lines[j])
                    if mr:
                        val = int(mr.group(1), 16)
                        if (val & 1) or ((val & 0xE) and (val & 0xC0)):
                            # For loads, later mem[R] is often the loaded word —
                            # cap walk length so we don't treat payload as PTEs.
                            max_walk = 8 if (vsatp_on and hgatp_on) else 2
                            #if instruction is a LOAD (lw)
                            if not ((insn_val & 0x7F) == 0x03 and len(data_ptes) >= max_walk):
                                data_ptes.append(val)

                # Same as original: append X / F / V / CSR updates to the line
                for reg, pattern in reg_patterns.items():
                    reg_match = pattern.search(lines[j])
                    if reg_match:
                        reg_num, reg_val = reg_match.groups()
                        next_output += f" {reg} {reg_num} {reg_val}"
                        break
                j += 1

            # --- Access flags for SvH cover crosses ---
            # LOAD opcode 0x03 → READ; STORE 0x23 or any mem[W] → WRITE (hsv.w).
            # EXECUTE_ACCESS is always 1 on a retired-insn line.
           # Did a two-stage translation happen for a READ? or WRITE?
            read_a = "1" if (insn_val & 0x7F) == 0x03 else "0"
            write_a = "1" if (insn_val & 0x7F) == 0x23 or saw_store else "0"
            next_output += f" READ_ACCESS {read_a} WRITE_ACCESS {write_a} EXECUTE_ACCESS 1"

            # --- Split walk leaves into VS-stage vs G-stage ---
            #   vsatp only  → VS_PTE_*
            #   hgatp only  → G_PTE_*
            #   both on     → last leaf = G, previous leaf = VS (two-stage)
            # Leaf heuristic: any of R/W/X set (bits [3:1]).
            # "These PTEs belong to VS page table or G page table?"
            def stage(ptes: list[int]) -> tuple[int, int]:
                leaves = [p for p in ptes if (p & 0xE) != 0]
                if not leaves:
                    return 0, 0
                if vsatp_on and hgatp_on and len(leaves) >= 2:
                    return leaves[-2], leaves[-1]
                if vsatp_on and not hgatp_on:
                    return leaves[-1], 0
                return 0, leaves[-1]

            vs_i, g_i = stage(ifetch_ptes)
            vs_d, g_d = stage(data_ptes)

            # Emit PTE keys by translation kind (no redundant overlap):
            #   • satp MODE on, H off → legacy PTE_I/PTE_D (Svnapot/Svpbmt/…)
            #   • vsatp/hgatp MODE on → VS_PTE_* / G_PTE_* (SvH)
            #   • all MODE off → no PTE keys (avoids mistaking lw data for PTEs)
            hypervisor = vsatp_on or hgatp_on
            if satp_on and not hypervisor:
                leaf_i = vs_i or g_i
                leaf_d = vs_d or g_d
                if leaf_i:
                    next_output += f" PTE_I {leaf_i:x}"
                if leaf_d:
                    next_output += f" PTE_D {leaf_d:x}"
            elif hypervisor:
                if vs_i:
                    next_output += f" VS_PTE_I {vs_i:x}"
                if vs_d:
                    next_output += f" VS_PTE_D {vs_d:x}"
                if g_i:
                    next_output += f" G_PTE_I {g_i:x}"
                if g_d:
                    next_output += f" G_PTE_D {g_d:x}"

            next_output += "\n"

            # Delayed write: fill PREVIOUS insn's MODE/MODE_VIRT with THIS
            # insn's start mode (= previous insn's end mode).
            # Coverpoints sample ins.prev.mode / ins.prev.mode_virt.
            if output_line:
                outfile.write(output_line.format(mode=prev_mode, mode_virt=mode_virt))
            output_line = next_output
            prev_mode_virt = mode_virt   # remember for the last-insn flush below

        # Flush the final instruction. Sail logs mode at the start of an
        # instruction, so the trailing instruction has no "next" mode to
        # inherit from; fall back to its own start mode as the closest
        # approximation rather than dropping it from the trace.
        if output_line and prev_mode is not None:
            outfile.write(output_line.format(mode=prev_mode, mode_virt=prev_mode_virt))
