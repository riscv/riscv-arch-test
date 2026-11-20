##################################
# cp_custom_fence_i.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_custom_fence_i coverpoint generator."""

from testgen.asm.helpers import load_int_reg, write_sigupd
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk

# The coverpoint bins are fixed encodings: nonzero rs1 is x2 and nonzero rd is x1.
FENCEI_RD = 1
FENCEI_RS1 = 2
RD_SENTINEL = "0x5A5A5A5A"
RS1_VALUE = "0x0F0F0F0F"
# Alignment of each patched instruction, so the four word cases and the Zca
# halfword case occupy different cache lines of up to 128 bytes.
PATCH_ALIGN = 128
# c.li immediate used by the Zca sh case. It must differ from 3+1, the result
# of the original c.addi, so a stale fetch fails the second signature.
C_LI_IMM = 17


def encode_addi(rd: int, rs1: int, imm: int) -> int:
    """Encode addi instruction."""
    return (imm << 20) | (rs1 << 15) | (0 << 12) | (rd << 7) | 0x13


def encode_fence_i(rd: int = 0, rs1: int = 0, imm: int = 0) -> int:
    """Encode fence.i with the given (reserved) rd, rs1 and imm fields."""
    return (imm << 20) | (rs1 << 15) | (0b001 << 12) | (rd << 7) | 0x0F


def encode_c_addi(rd: int, imm: int) -> int:
    """Encode c.addi rd, imm for a positive immediate that fits in imm[4:0]."""
    if not 1 <= imm <= 31:
        raise ValueError(f"c.addi immediate {imm} is outside 1..31")
    return (rd << 7) | (imm << 2) | 0x1


def encode_c_li(rd: int, imm: int) -> int:
    """Encode c.li rd, imm for an immediate that fits in imm[4:0]."""
    if not 0 <= imm <= 31:
        raise ValueError(f"c.li immediate {imm} is outside 0..31")
    return (0b010 << 13) | (rd << 7) | (imm << 2) | 0x1


@add_coverpoint_generator("cp_custom_fencei")
def make_custom_fence_i(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for fence.i coverpoints.

    Each testcase calls the original instruction, records 3+1, stores a new
    instruction, executes fence.i, calls the same address again, and records the
    new result. rd, rs1 and imm are reserved and must be ignored (norm:fence_i_rsv),
    so the nonzero-rd case also checks that rd is not written. Two word testcases
    read the instruction as data before the store, so that the store finds the line
    in any data cache; the other two store without a prior read. Each patched
    instruction starts a 128-byte block, so one testcase's fetch or read cannot
    bring another's line in. A Zca hart also stores a c.li with sh.
    """
    if instr_name != "fence.i":
        raise ValueError(f"cp_custom_fencei generator only supports fence.i instruction, got {instr_name}")

    tc = test_data.begin_test_chunk()

    # Take x1 and x2 for the fixed encodings; this moves the signature pointer off x2.
    asm = test_data.int_regs.consume_registers([FENCEI_RD, FENCEI_RS1])
    if asm:
        tc.code.append(asm)

    # (bin name, description, fence.i encoding or None for the plain opcode,
    #  store kind, patched immediate, read the line as data before the store, ifdef)
    cases: list[tuple[str, str, int | None, str, int, bool, str | None]] = [
        ("fencei", "normal fence.i", None, "sw", 5, True, None),
        ("fencei_nonzerors1", "fence.i with nonzero rs1", encode_fence_i(rs1=FENCEI_RS1), "sw", 7, False, None),
        ("fencei_nonzerord", "fence.i with nonzero rd", encode_fence_i(rd=FENCEI_RD), "sw", 9, False, None),
        ("fencei_nonzerof12", "fence.i with nonzero funct12", encode_fence_i(imm=1), "sw", 13, True, None),
        ("fencei_zca_sh", "sh of c.li before fence.i", None, "sh", C_LI_IMM, True, "ZCA_SUPPORTED"),
    ]

    link = test_data.int_regs.link_reg
    for bin_name, desc, fence_encoding, store_kind, imm, read_first, ifdef in cases:
        reg1, reg2, reg3 = test_data.int_regs.get_registers(3, exclude_regs=[0])
        label = f"selfmodify_{test_data.test_count}"
        after_label = f"after_{label}"
        fence_instr = "fence.i" if fence_encoding is None else f".insn {fence_encoding:#010x}"
        if store_kind == "sw":
            old_insn = f"addi x{reg1}, x{reg1}, 1 # original code"
            new_instr = encode_addi(reg1, reg1, imm)
            new_name = f"addi x{reg1}, x{reg1}, {imm}"
            store = f"sw x{reg2}, 0(x{reg3})"
        elif store_kind == "sh":
            old_insn = f".half {encode_c_addi(reg1, 1):#06x} # original c.addi x{reg1}, 1"
            new_instr = encode_c_li(reg1, imm)
            new_name = f"c.li x{reg1}, {imm}"
            store = f"sh x{reg2}, 0(x{reg3})"
        else:
            raise ValueError(f"Unsupported store kind: {store_kind}")

        if ifdef:
            tc.code.append(f"#ifdef {ifdef}")
        tc.code.append(f"# Testcase {bin_name}: {desc}")
        if bin_name == "fencei_nonzerors1":
            tc.code.append(f"LI(x{FENCEI_RS1}, {RS1_VALUE}) # nonzero value in the ignored rs1")
        if bin_name == "fencei_nonzerord":
            tc.code.append(f"LI(x{FENCEI_RD}, {RD_SENTINEL}) # fence.i must not write the ignored rd")
        # Fetch and execute the old instruction before the store, then record 3+1.
        # add_testcase names the signature label; the label itself is placed on fence.i.
        tc.code.extend([f"LI(x{reg1}, 3)", f"LA(x{reg3}, {label})", f"jal x{link}, {label}"])
        testcase_label = test_data.add_testcase(bin_name, "cp_custom_fencei")
        tc.code.append(write_sigupd(reg1, test_data))
        tc.code.append(f"LI(x{reg1}, 3) # replay the patched instruction from the same input")
        if read_first:
            tc.code.append(f"lw x{reg2}, 0(x{reg3}) # read the instruction as data before the store")
        tc.code.extend(
            [
                load_int_reg(new_name, reg2, new_instr, test_data),
                store,
                testcase_label,
                f"{fence_instr} # {desc}",
                f"jalr x{link}, x{reg3}, 0",
                write_sigupd(reg1, test_data),
            ]
        )
        if bin_name == "fencei_nonzerord":
            tc.code.append(write_sigupd(FENCEI_RD, test_data))
        tc.code.extend(
            [
                f"jal x0, {after_label}",
                f".balign {PATCH_ALIGN} # keep this patched instruction in its own cache line",
                f"{label}:",
                old_insn,
                f"jalr x0, x{link}, 0",
                f"{after_label}:",
                "",
            ]
        )
        if ifdef:
            tc.code.append(f"#endif // {ifdef}")
            tc.code.append("")
        test_data.int_regs.return_registers([reg1, reg2, reg3])

    test_data.int_regs.return_registers([FENCEI_RD, FENCEI_RS1])
    return [test_data.end_test_chunk()]
