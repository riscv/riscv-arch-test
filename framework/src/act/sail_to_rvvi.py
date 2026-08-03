##################################
# sail-to-rvvi.py
#
# jcarlin@hmc.edu 9 May 2025
# SPDX-License-Identifier: Apache-2.0
#
# Turn a Sail verbose log (*.trace) into the short Tracefile (*.rvvi) that the
# ACT4 coverage testbench actually reads.
#
#   Sail --trace  →  *.trace  →  sailLog2Trace()  →  *.rvvi  →  testbench.sv
#
# One retired instruction becomes one .rvvi line, space-separated KEY VALUE:
#   ORDER <n> PC <hex> INSN <hex> MODE <0|1|3> MODE_VIRT <0|1>
#     [X|F|V|CSR <id> <val>]…
#     READ_ACCESS <0|1> WRITE_ACCESS <0|1> EXECUTE_ACCESS 1
#     [PTE_I|PTE_D|VS_PTE_*|G_PTE_* <hex>]…
#
# The original converter only emitted ORDER/PC/INSN/MODE plus X/F/V/CSR.
# SvH covergroups also need MODE_VIRT, access flags, and stage-tagged PTEs,
# so this file adds those without changing the basic one-insn-one-line shape.
##################################

import re
from pathlib import Path


def sailLog2Trace(inputLogFile: Path, outputTraceFile: Path) -> None:
    # Instruction line. Example:
    #   [568] [VS]: 0x900002A4 (0x00460613) addi x12, x12, 0x4
    # MODE is any [A-Z]+ so VS/VU/HS match (older code only allowed [MSU]).
    insn_pattern = re.compile(r"\[(\d+)\] \[([A-Z]+)\]: 0x([0-9a-fA-F]+) \(0x([0-9a-fA-F]+)\) (.*)")

    # Memory read during a page walk or load. We only keep the value:
    #   mem[R,0x08000C100] -> 0x20001801
    mem_r_pattern = re.compile(r"mem\[R,0x[0-9a-fA-F]+\] -> 0x([0-9a-fA-F]+)")

    # CSR writes only (<-). We use these to know whether satp/vsatp/hgatp
    # translation is on. Reads (->) must not flip that state.
    #   CSR vsatp (0x280) <- 0x80000000
    csr_wr_pattern = re.compile(r"CSR .* \(0x([0-9a-fA-F]+)\) <- 0x([0-9a-fA-F]+)")

    # Side effects that go onto the .rvvi line after the insn.
    # CSR matches both write (<-) and read (->); X/F/V are writes only.
    reg_patterns = {
        "CSR": re.compile(r"CSR .* \(0x([0-9a-fA-F]+)\) (?:<-|->) 0x([0-9a-fA-F]+)"),
        "X"  : re.compile(r"x(\d+) <- 0x([0-9a-fA-F]+)"),
        "F"  : re.compile(r"f(\d+) <- 0x([0-9a-fA-F]+)"),
        "V"  : re.compile(r"v(\d+) <- 0x([0-9a-fA-F]+)"),
    }

    # Sail privilege tag → (MODE, MODE_VIRT) as the TB samples them.
    # Coverpoints cross {mode_virt, mode}; e.g. HS and S both look like mode=1.
    mode_map = {
        "M": ("3", "0"),   # machine
        "S": ("1", "0"),   # supervisor (no H)
        "HS": ("1", "0"),  # hypervisor-extended S; same MODE bits as S
        "U": ("0", "0"),   # user
        "VS": ("1", "1"),  # virtual supervisor
        "VU": ("0", "1"),  # virtual user
    }

    # Translation enabled? Checked from the last CSR write to each satp-family
    # register. MODE≠Bare means "on":
    #   RV32 → bit 31; RV64 → bits [63:60].
    # Addresses: satp=0x180, vsatp=0x280, hgatp=0x680.
    satp_on = False
    vsatp_on = False
    hgatp_on = False

    with inputLogFile.open() as f, outputTraceFile.open("w") as outfile:
        lines = f.readlines()
        output_line = ""
        prev_mode: str | None = None
        prev_mode_virt = "0"  # only needed when flushing the last insn

        for i in range(len(lines)):
            line = lines[i]

            # Keep satp/vsatp/hgatp MODE state up to date even on non-insn lines.
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

            # Everything below is per retired instruction.
            insn_match = insn_pattern.search(line)
            if not insn_match:
                continue

            order, mode_tag, pc, insn, _ = insn_match.groups()
            mode, mode_virt = mode_map.get(mode_tag, ("3", "0"))
            insn_val = int(insn, 16)
            prev_mode = mode

            # MODE / MODE_VIRT start as placeholders. We fill them later from
            # the *next* insn's start mode, which is this insn's end mode.
            # (Sail prints mode at insn start; RVVI coverpoints want end mode.)
            next_output = (
                f"ORDER {order} PC {pc} INSN {insn} "
                f"MODE {{mode}} MODE_VIRT {{mode_virt}}"
            )

            # ---- Instruction fetch page walk (above this insn in the log) ----
            # Sail typically prints:
            #   mem[R] -> PTE          ← walk
            #   mem[R] -> PTE
            #   mem[X] -> insn bytes   ← marks "this is ifetch"
            #   [n] [VS]: …            ← we are here
            # Walk backward until the previous insn. Stop at mem[W] so we do
            # not pick up the previous store's data-side PTEs (that used to
            # inflate I-side cover bins).
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
                        # Keep V=1 walks, and also V=0 leaves that still have
                        # R/W/X or A/D set — invalid-PTE cover bins need them.
                        if (val & 1) or ((val & 0xE) and (val & 0xC0)):
                            ifetch_ptes.append(val)
                k -= 1
            ifetch_ptes.reverse()  # root → leaf

            # ---- After the insn: CSR/reg updates + data-side page walk ----
            # Store example:
            #   [n] [VS]: … sw …
            #   mem[R] -> PTE          ← data walk (collect)
            #   mem[W] -> store data   ← stop; this is the payload, not a PTE
            #   [n+1] …
            # Also stop at the next mem[X] (next insn's ifetch starting).
            data_ptes: list[int] = []
            stop_ptes = False
            saw_store = False
            j = i + 1
            while j < len(lines):
                if insn_pattern.search(lines[j]):
                    break

                if "mem[W," in lines[j]:
                    saw_store = True
                    stop_ptes = True  # store data is never a PTE
                elif "mem[X," in lines[j]:
                    stop_ptes = True  # next ifetch begins

                # Still in the walk: keep mem[R] values that look like PTEs.
                if not stop_ptes:
                    mr = mem_r_pattern.search(lines[j])
                    if mr:
                        val = int(mr.group(1), 16)
                        if (val & 1) or ((val & 0xE) and (val & 0xC0)):
                            # On a load/HLV, Sail also prints the loaded word
                            # as mem[R]. Cap how many PTEs we keep so that
                            # payload never gets labeled as a leaf PTE.
                            # Two-stage walks are longer (VS + G), so allow 8.
                            max_walk = 8 if (vsatp_on and hgatp_on) else 2
                            f7 = (insn_val >> 25) & 0x7F
                            f3 = (insn_val >> 12) & 0x7
                            is_data_load = (insn_val & 0x7F) == 0x03 or (
                                (insn_val & 0x7F) == 0x73 and f3 == 0b100 and f7 in (0x34, 0x36)
                            )
                            if not (is_data_load and len(data_ptes) >= max_walk):
                                data_ptes.append(val)

                # Same as the original converter: append X / F / V / CSR updates.
                for reg, pattern in reg_patterns.items():
                    reg_match = pattern.search(lines[j])
                    if reg_match:
                        reg_num, reg_val = reg_match.groups()
                        next_output += f" {reg} {reg_num} {reg_val}"
                        break
                j += 1

            # ---- Access flags (SvH crosses key off these) ----
            # Ordinary LOAD (opcode 0x03) / STORE (0x23), plus HLV/HSV.
            # HLV and HSV are SYSTEM (0x73); funct7 tells them apart:
            #   HLV  → funct7 0x34 / 0x36
            #   HSV  → funct7 0x35
            # Without mapping HLV→READ and HSV→WRITE, MPRV×HLV cover bins stay 0.
            is_load = (insn_val & 0x7F) == 0x03
            is_store = (insn_val & 0x7F) == 0x23 or saw_store
            is_hlv = False
            is_hsv = False
            if (insn_val & 0x7F) == 0x73:
                f7 = (insn_val >> 25) & 0x7F
                f3 = (insn_val >> 12) & 0x7
                if f3 == 0b100 and f7 in (0x34, 0x36):
                    is_hlv = True
                if f3 == 0b100 and f7 == 0x35:
                    is_hsv = True
            read_a = "1" if is_load or is_hlv else "0"
            write_a = "1" if is_store or is_hsv else "0"
            next_output += f" READ_ACCESS {read_a} WRITE_ACCESS {write_a} EXECUTE_ACCESS 1"

            # ---- Decide which leaf belongs to VS-stage vs G-stage ----
            #   vsatp only  → last leaf is VS
            #   hgatp only  → last leaf is G
            #   both on     → normally last-but-one = VS, last = G
            # A "leaf" here means R/W/X set (PTE bits [3:1]).
            #
            # One catch for two-stage faults (e.g. X-only PTE with MXR=0):
            # Sail may never finish a G data leaf. Then the last leaf is the
            # VS data PTE, and the leaf before it is often G's map of that
            # VS PTE itself (R+W, no X). Swap in that case so VS_PTE_* gets
            # the X-only page and G_PTE_* gets the PT map.
            def stage(ptes: list[int]) -> tuple[int, int]:
                leaves = [p for p in ptes if (p & 0xE) != 0]
                if not leaves:
                    return 0, 0
                if vsatp_on and hgatp_on and len(leaves) >= 2:
                    vs_leaf, g_leaf = leaves[-2], leaves[-1]
                    xonly = lambda p: (p & 0xE) == 0x8   # X only
                    pt_map = lambda p: (p & 0xE) == 0x6  # R+W, typical PT map
                    if xonly(g_leaf) and pt_map(vs_leaf):
                        return g_leaf, vs_leaf  # VS data leaf, G-of-VS-PT
                    return vs_leaf, g_leaf
                if vsatp_on and not hgatp_on:
                    return leaves[-1], 0
                return 0, leaves[-1]

            vs_i, g_i = stage(ifetch_ptes)
            vs_d, g_d = stage(data_ptes)

            # Emit PTE keys for the translation that is actually on.
            #   classic satp only  → PTE_I / PTE_D
            #   vsatp and/or hgatp → VS_PTE_* / G_PTE_*
            #   nothing on         → no PTE keys (avoids labeling lw data as PTEs)
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

            # Write the *previous* insn now that we know this insn's start
            # mode (= previous insn's end mode). Coverpoints sample
            # ins.prev.mode / ins.prev.mode_virt.
            if output_line:
                outfile.write(output_line.format(mode=prev_mode, mode_virt=mode_virt))
            output_line = next_output
            prev_mode_virt = mode_virt

        # Last insn has no "next" mode to inherit. Use its own start mode —
        # close enough, and better than dropping it from the trace.
        if output_line and prev_mode is not None:
            outfile.write(output_line.format(mode=prev_mode, mode_virt=prev_mode_virt))
