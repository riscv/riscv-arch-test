##################################
# cp_zcmp.py
#
# SPDX-License-Identifier: Apache-2.0
##################################

"""Coverpoint generators for the Zcmp extension (cm.push/pop/popret/popretz/mva01s/mvsa01)."""

from testgen.asm.helpers import write_sigupd
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk

# s0-s7 as (asm_name, x_number) — Zcmp r1s'/r2s' 3-bit field maps 0-7 to these
_SREG = [
    ("s0", 8),
    ("s1", 9),
    ("s2", 18),
    ("s3", 19),
    ("s4", 20),
    ("s5", 21),
    ("s6", 22),
    ("s7", 23),
]

_RLIST_ASM = {
    4: "{ra}",
    5: "{ra,s0}",
    6: "{ra,s0-s1}",
    7: "{ra,s0-s2}",
    8: "{ra,s0-s3}",
    9: "{ra,s0-s4}",
    10: "{ra,s0-s5}",
    11: "{ra,s0-s6}",
    12: "{ra,s0-s7}",
    13: "{ra,s0-s8}",
    14: "{ra,s0-s9}",
    15: "{ra,s0-s11}",
}

_RLIST_XREGS = {
    4: [1],
    5: [8, 1],
    6: [9, 8, 1],
    7: [18, 9, 8, 1],
    8: [19, 18, 9, 8, 1],
    9: [20, 19, 18, 9, 8, 1],
    10: [21, 20, 19, 18, 9, 8, 1],
    11: [22, 21, 20, 19, 18, 9, 8, 1],
    12: [23, 22, 21, 20, 19, 18, 9, 8, 1],
    13: [24, 23, 22, 21, 20, 19, 18, 9, 8, 1],
    14: [25, 24, 23, 22, 21, 20, 19, 18, 9, 8, 1],
    15: [27, 26, 25, 24, 23, 22, 21, 20, 19, 18, 9, 8, 1],
}

_STACK_ADJ_RV32 = {4: 16, 5: 16, 6: 16, 7: 16, 8: 32, 9: 32, 10: 32, 11: 32, 12: 48, 13: 48, 14: 48, 15: 64}
_STACK_ADJ_RV64 = {4: 16, 5: 16, 6: 32, 7: 32, 8: 48, 9: 48, 10: 64, 11: 64, 12: 80, 13: 80, 14: 96, 15: 112}

_TEST_VALS = {
    1: 0x01010101,
    8: 0x08080808,
    9: 0x09090909,
    18: 0x12121212,
    19: 0x13131313,
    20: 0x14141414,
    21: 0x15151515,
    22: 0x16161616,
    23: 0x17171717,
    24: 0x18181818,
    25: 0x19191919,
    26: 0x1A1A1A1A,
    27: 0x1B1B1B1B,
}

_RLIST_ALL = [1, 8, 9, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27]
_PUSH_CONSUME = [2] + _RLIST_ALL

# Scratch area offset: scratch is 264 bytes; sp at scratch+240 leaves 240B below for stores
_SP_OFFSET = 240


def _setup_sp_lines(xT: int) -> list[str]:
    """Assembly lines to set x2 = scratch + _SP_OFFSET."""
    return [
        f"LA(x{xT}, scratch)",
        f"addi x2, x{xT}, {_SP_OFFSET}",
    ]


@add_coverpoint_generator("cp_zcmp_push_rlist")
def make_zcmp_push_rlist(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Test cm.push for each rlist value; verify register values stored on stack."""
    tc = test_data.begin_test_chunk()
    lines: list[str] = []

    asm = test_data.int_regs.consume_registers(_PUSH_CONSUME)
    if asm:
        lines.append(asm)

    xlen = test_data.xlen
    adj_table = _STACK_ADJ_RV32 if xlen == 32 else _STACK_ADJ_RV64
    reg_size = 4 if xlen == 32 else 8
    load_instr = "lw" if xlen == 32 else "ld"

    xT = test_data.int_regs.get_register()
    xV = test_data.int_regs.get_register()

    for rlist in range(4, 16):
        stack_adj = adj_table[rlist]
        regs = _RLIST_XREGS[rlist]

        for xreg in regs:
            lines.append(f"LI(x{xreg}, {hex(_TEST_VALS[xreg])})")

        lines.extend(_setup_sp_lines(xT))
        lines.append(test_data.add_testcase(f"rlist{rlist}", coverpoint))

        lines.append(f"cm.push {_RLIST_ASM[rlist]}, -{stack_adj}")

        for i, xreg in enumerate(regs):
            offset = stack_adj - reg_size * (i + 1)
            lines.append(f"{load_instr} x{xV}, {offset}(x2)")
            lines.append(write_sigupd(xV, test_data, "int"))

        # Undo push effect so next iteration starts clean
        lines.append(f"addi x2, x2, {stack_adj}")

    test_data.int_regs.return_registers(_PUSH_CONSUME + [xT, xV])
    tc.code = "\n".join(lines)
    return [test_data.end_test_chunk()]


@add_coverpoint_generator("cp_zcmp_pop_rlist")
def make_zcmp_pop_rlist(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Test cm.pop: use cm.push to set up stack, zero regs, pop and verify restoration."""
    tc = test_data.begin_test_chunk()
    lines: list[str] = []

    asm = test_data.int_regs.consume_registers(_PUSH_CONSUME)
    if asm:
        lines.append(asm)

    xlen = test_data.xlen
    adj_table = _STACK_ADJ_RV32 if xlen == 32 else _STACK_ADJ_RV64
    xT = test_data.int_regs.get_register()

    for rlist in range(4, 16):
        stack_adj = adj_table[rlist]
        regs = _RLIST_XREGS[rlist]

        for xreg in regs:
            lines.append(f"LI(x{xreg}, {hex(_TEST_VALS[xreg])})")
        lines.extend(_setup_sp_lines(xT))
        lines.append(f"cm.push {_RLIST_ASM[rlist]}, -{stack_adj}")

        for xreg in regs:
            lines.append(f"li x{xreg}, 0")

        lines.append(test_data.add_testcase(f"rlist{rlist}", coverpoint))
        lines.append(f"cm.pop {_RLIST_ASM[rlist]}, {stack_adj}")

        for xreg in regs:
            lines.append(write_sigupd(xreg, test_data, "int"))

    test_data.int_regs.return_registers(_PUSH_CONSUME + [xT])
    tc.code = "\n".join(lines)
    return [test_data.end_test_chunk()]


@add_coverpoint_generator("cp_zcmp_popret_rlist")
def make_zcmp_popret_rlist(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Test cm.popret: push, zero regs, popret (jumps to ra), verify s-registers restored."""
    tc = test_data.begin_test_chunk()
    lines: list[str] = []

    asm = test_data.int_regs.consume_registers(_PUSH_CONSUME)
    if asm:
        lines.append(asm)

    xlen = test_data.xlen
    adj_table = _STACK_ADJ_RV32 if xlen == 32 else _STACK_ADJ_RV64
    xT = test_data.int_regs.get_register()

    for rlist in range(4, 16):
        stack_adj = adj_table[rlist]
        regs = _RLIST_XREGS[rlist]
        s_regs = [r for r in regs if r != 1]  # exclude ra

        testcase_line = test_data.add_testcase(f"rlist{rlist}", coverpoint)
        ret_label = f"{test_data.current_testcase_label}_ret"

        lines.append(f"LA(x1, {ret_label})")

        for xreg in s_regs:
            lines.append(f"LI(x{xreg}, {hex(_TEST_VALS[xreg])})")
        lines.extend(_setup_sp_lines(xT))

        lines.append(testcase_line)
        lines.append(f"cm.push {_RLIST_ASM[rlist]}, -{stack_adj}")

        # Zero out all rlist registers
        for xreg in regs:
            lines.append(f"li x{xreg}, 0")

        # cm.popret restores regs then does jalr x0, ra, 0
        lines.append(f"cm.popret {_RLIST_ASM[rlist]}, {stack_adj}")

        lines.append(f"{ret_label}:")

        for xreg in s_regs:
            lines.append(write_sigupd(xreg, test_data, "int"))

    test_data.int_regs.return_registers(_PUSH_CONSUME + [xT])
    tc.code = "\n".join(lines)
    return [test_data.end_test_chunk()]


@add_coverpoint_generator("cp_zcmp_popretz_rlist")
def make_zcmp_popretz_rlist(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Test cm.popretz: like popret but also zeroes a0; verify s-registers and a0=0."""
    tc = test_data.begin_test_chunk()
    lines: list[str] = []

    asm = test_data.int_regs.consume_registers(_PUSH_CONSUME + [10])
    if asm:
        lines.append(asm)

    xlen = test_data.xlen
    adj_table = _STACK_ADJ_RV32 if xlen == 32 else _STACK_ADJ_RV64
    xT = test_data.int_regs.get_register()

    for rlist in range(4, 16):
        stack_adj = adj_table[rlist]
        regs = _RLIST_XREGS[rlist]
        s_regs = [r for r in regs if r != 1]

        testcase_line = test_data.add_testcase(f"rlist{rlist}", coverpoint)
        ret_label = f"{test_data.current_testcase_label}_ret"

        lines.append(f"LA(x1, {ret_label})")
        for xreg in s_regs:
            lines.append(f"LI(x{xreg}, {hex(_TEST_VALS[xreg])})")
        lines.extend(_setup_sp_lines(xT))

        lines.append(testcase_line)
        lines.append(f"cm.push {_RLIST_ASM[rlist]}, -{stack_adj}")

        for xreg in regs:
            lines.append(f"li x{xreg}, 0")

        lines.append("LI(x10, 0xDEADBEEF)")
        lines.append(f"cm.popretz {_RLIST_ASM[rlist]}, {stack_adj}")
        lines.append(f"{ret_label}:")

        for xreg in s_regs:
            lines.append(write_sigupd(xreg, test_data, "int"))

        lines.append(write_sigupd(10, test_data, "int"))

    test_data.int_regs.return_registers(_PUSH_CONSUME + [10, xT])
    tc.code = "\n".join(lines)
    return [test_data.end_test_chunk()]


@add_coverpoint_generator("cp_zcmp_mva01s")
def make_zcmp_mva01s(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Test cm.mva01s: each s-register (s0-s7) as r1s', verify a0 and a1 set correctly."""
    tc = test_data.begin_test_chunk()
    lines: list[str] = []

    all_sreg_nums = [x for _, x in _SREG]
    asm = test_data.int_regs.consume_registers([2, 10, 11] + all_sreg_nums)
    if asm:
        lines.append(asm)

    for i, (r1s_name, r1s_num) in enumerate(_SREG):
        r2s_idx = (i + 1) % len(_SREG)
        r2s_name, r2s_num = _SREG[r2s_idx]

        lines.append(f"LI(x{r1s_num}, {hex(_TEST_VALS[r1s_num])})")
        lines.append(f"LI(x{r2s_num}, {hex(_TEST_VALS[r2s_num])})")

        lines.append(test_data.add_testcase(r1s_name, coverpoint))
        lines.append(f"cm.mva01s {r1s_name}, {r2s_name}")

        # Verify a0 = r1s' value, a1 = r2s' value
        lines.append(write_sigupd(10, test_data, "int"))
        lines.append(write_sigupd(11, test_data, "int"))

    test_data.int_regs.return_registers([2, 10, 11] + all_sreg_nums)
    tc.code = "\n".join(lines)
    return [test_data.end_test_chunk()]


@add_coverpoint_generator("cp_zcmp_mvsa01")
def make_zcmp_mvsa01(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Test cm.mvsa01: a0/a1 copied to distinct s-register pairs; verify each destination."""
    tc = test_data.begin_test_chunk()
    lines: list[str] = []

    all_sreg_nums = [x for _, x in _SREG]
    asm = test_data.int_regs.consume_registers([2, 10, 11] + all_sreg_nums)
    if asm:
        lines.append(asm)

    a0_val = 0xA0A0A0A0
    a1_val = 0xA1A1A1A1

    for i, (r1s_name, r1s_num) in enumerate(_SREG):
        # r1s' and r2s' must be distinct registers
        r2s_idx = (i + 1) % len(_SREG)
        r2s_name, r2s_num = _SREG[r2s_idx]

        lines.append(f"LI(x10, {hex(a0_val)})")
        lines.append(f"LI(x11, {hex(a1_val)})")

        lines.append(test_data.add_testcase(r1s_name, coverpoint))
        lines.append(f"cm.mvsa01 {r1s_name}, {r2s_name}")

        lines.append(write_sigupd(r1s_num, test_data, "int"))
        lines.append(write_sigupd(r2s_num, test_data, "int"))

    test_data.int_regs.return_registers([2, 10, 11] + all_sreg_nums)
    tc.code = "\n".join(lines)
    return [test_data.end_test_chunk()]
