##################################
# cp_misalign.py
#
# David_Harris@hmc.edu 2 Jan 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_misalign coverpoint generator."""

from testgen.asm.helpers import load_float_reg, load_int_reg, write_sigupd
from testgen.constants import INDENT
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk

# 16 distinct bytes placed in the test window, as four little-endian words at offsets 0, 4, 8, 12.
# Bytes 0-7 all have bit 7 clear, so the complement pass (bytes 88 99 aa bb cc dd ee ff 10 32 54 76 98 ba dc fe,
# still all distinct) is needed for every (width, offset) to see a set sign bit as well as a clear one.
_PATTERN = (0x44556677, 0x00112233, 0x89ABCDEF, 0x01234567)
_PATTERN_INV = tuple(~w & 0xFFFFFFFF for w in _PATTERN)

# Window base offsets from scratch (256-byte aligned, 264 bytes long; see RVTEST_DATA_BEGIN).
# cp_misalign uses scratch+0. cp_misalign_cross64_{hword,word,double} use scratch+56, so the 16-byte window
# [56, 72) spans scratch+64 and misaligned accesses there cross a 16/32/64-byte cache-line or bus-beat boundary.
_CROSS64 = {"cp_misalign_cross64_hword": 2, "cp_misalign_cross64_word": 4, "cp_misalign_cross64_double": 8}

# Byte offsets tested within the window; 8 is not strictly required by cp_misalign, but shows wrapping works.
_OFFSETS = range(9)


def _access_bytes(instr_name: str) -> int:
    """Return the access size in bytes of a scalar load/store mnemonic (lh, lwu, fld, c.sdsp, ...)."""
    core = instr_name.removeprefix("c.").removesuffix("sp").removeprefix("f")[1:]  # drop l/s
    return {"h": 2, "hu": 2, "w": 4, "wu": 4, "d": 8}[core]


def _fill_window(r1: int, r2: int, words: tuple[int, ...], test_data: TestData) -> list[str]:
    """Write the four pattern words into the 16-byte window at x{r1}."""
    lines = [
        f"{INDENT}# Place 0x{words[3]:08X}_{words[2]:08X}_{words[1]:08X}_{words[0]:08X} into the 16-byte window at x{r1}",
    ]
    for i, w in enumerate(words):
        lines.append(load_int_reg(f"testdata_{i}", r2, w, test_data))
        lines.append(f"sw x{r2}, {4 * i}(x{r1}) # store at offset {4 * i}")
    return lines


@add_coverpoint_generator("cp_misalign")
def make_misalign(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for misalignment coverpoints."""
    tc = test_data.begin_test_chunk()
    size = _access_bytes(instr_name)
    if coverpoint in _CROSS64:
        if _CROSS64[coverpoint] != size:
            raise ValueError(f"{coverpoint} does not match the {size}-byte access of {instr_name}")
        base = 56
    elif coverpoint == "cp_misalign":
        base = 0
    else:
        raise ValueError(f"Unknown cp_misalign coverpoint variant: {coverpoint} for {instr_name}")

    def bin_name(offset: int, suffix: str = "") -> str:
        if coverpoint in _CROSS64:
            start = base + offset
            name = f"{'yes' if start < 64 < start + size else 'no'}_{offset}"  # does the access straddle scratch+64?
        else:
            name = "8_wrap" if offset == 8 else f"{offset}"  # offset 8 is bin 0 of addr[2:0]
        return name + suffix

    def set_base(reg: str, extra: int = 0) -> list[str]:
        lines = [f"LA({reg}, scratch) # load base address"]
        if base + extra:
            where = f"scratch+{base} window" + (f" + offset {extra}" if extra else "")
            lines.append(f"addi {reg}, {reg}, {base + extra} # {where}")
        return lines

    # Allocate some registers for testing.  Restrict them to [8,15] in case the registers are used for compressed instructions
    r1, r2 = test_data.int_regs.get_registers(2, exclude_regs=[0], reg_range=list(range(8, 16)))

    if instr_type in {"L", "FL", "CL", "CILS"}:
        # Two passes: the pattern, then its complement, so each misaligned load sees both sign-bit values
        for words, suffix in ((_PATTERN, ""), (_PATTERN_INV, "_inv")):
            tc.code.extend([*set_base(f"x{r1}"), *_fill_window(r1, r2, words, test_data), ""])
            for alignment in _OFFSETS:
                tc.code.append(f"# Testcase: {coverpoint} (scratch+{base} window, offset {alignment}{suffix})")
                if instr_type in {"L", "FL"}:
                    reg, sig = (f"x{r2}", "int") if instr_type == "L" else (f"f{r2}", "float")
                    tc.code.extend(
                        [
                            *set_base(f"x{r1}"),
                            test_data.add_testcase(bin_name(alignment, suffix), coverpoint),
                            f"{instr_name} {reg}, {alignment}(x{r1}) # perform load",
                            write_sigupd(r2, test_data, sig),
                            "",
                        ]
                    )
                elif instr_type == "CL":
                    tc.code.extend(
                        [
                            *set_base(f"x{r1}", alignment),
                            test_data.add_testcase(bin_name(alignment, suffix), coverpoint),
                            f"{instr_name} x{r2}, 0(x{r1}) # perform load",
                            write_sigupd(r2, test_data, "int"),
                            "",
                        ]
                    )
                else:  # CILS
                    asm = test_data.int_regs.consume_registers([2])
                    if asm:
                        tc.code.append(asm)
                    tc.code.extend(
                        [
                            *set_base("sp", alignment),
                            test_data.add_testcase(bin_name(alignment, suffix), coverpoint),
                            f"{instr_name} x{r2}, 0(sp) # perform load",
                            write_sigupd(r2, test_data, "int"),
                            "",
                        ]
                    )
                    test_data.int_regs.return_registers([2])
    elif instr_type in {"S", "FS", "CS", "CSS"}:
        # bytes to store all differ from values placed in the window.  A store's result does not depend
        # on the sign of the bytes it overwrites, so stores need only the one pattern.
        val = 0x0F1E2D3C4B5A6978 if max(test_data.xlen, test_data.flen) == 64 else 0x0F1E2D3C
        for alignment in _OFFSETS:
            tc.code.extend(
                [
                    f"# Testcase: {coverpoint} (scratch+{base} window, offset {alignment})",
                    *set_base(f"x{r1}"),
                    *_fill_window(r1, r2, _PATTERN, test_data),
                ]
            )
            if instr_type == "S":
                tc.code.extend(
                    [
                        load_int_reg("rs2", r2, val, test_data),
                        test_data.add_testcase(bin_name(alignment), coverpoint),
                        f"{instr_name} x{r2}, {alignment}(x{r1}) # perform store to scratch memory",
                    ]
                )
            elif instr_type == "FS":
                tc.code.extend(
                    [
                        load_float_reg("fs2", r2, val, test_data),
                        test_data.add_testcase(bin_name(alignment), coverpoint),
                        f"{instr_name} f{r2}, {alignment}(x{r1}) # perform store to scratch memory",
                    ]
                )
            elif instr_type == "CS":
                tc.code.extend(
                    [
                        load_int_reg("rs2", r2, val, test_data),
                        f"addi x{r1}, x{r1}, {alignment} # adjust for alignment",
                        test_data.add_testcase(bin_name(alignment), coverpoint),
                        f"{instr_name} x{r2}, 0(x{r1}) # perform store",
                        f"addi x{r1}, x{r1}, {-alignment} # restore base address",
                    ]
                )
            else:  # CSS
                asm = test_data.int_regs.consume_registers([2])
                if asm:
                    tc.code.append(asm)
                tc.code.extend(
                    [
                        load_int_reg("rs2", r2, val, test_data),
                        *set_base("sp", alignment),
                        test_data.add_testcase(bin_name(alignment), coverpoint),
                        f"{instr_name} x{r2}, 0(sp) # perform store",
                    ]
                )
                test_data.int_regs.return_registers([2])
            tc.code.append(f"{INDENT}# Check all 16 bytes of the window as signature")
            for off in range(0, 16, test_data.xlen // 8):
                tc.code.extend([f"LREG x{r2}, {off}(x{r1})", write_sigupd(r2, test_data, "int")])
            tc.code.append("")
    else:
        raise ValueError(f"Unknown instruction type: {instr_type} for cp_misalign.")

    test_data.int_regs.return_registers([r1, r2])

    return [test_data.end_test_chunk()]
