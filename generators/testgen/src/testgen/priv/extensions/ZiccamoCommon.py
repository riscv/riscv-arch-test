##################################
# priv/extensions/ZiccamoCommon.py
#
# Shared AMO tests for the Ziccamoa and Ziccamoc main-memory atomics test generators.
# David_Harris@hmc.edu 22 October 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared AMO tests for Ziccamoa and Ziccamoc.

Each AMO operates on scratch, which is first written with a known pattern, and the test records the value the AMO
returns and the value it leaves in memory. The pattern's low word and low byte are negative and the source operand
is positive, so the signed and unsigned minimum and maximum give different results. A compare-and-swap compares
against the value scratch holds, so it swaps. AMO atomicity is only observable with another hart or agent, so a
single-hart test cannot check it.
"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData

# Scratch pattern, as words from the lowest address
_SCRATCH_WORDS = [0x876543A1, 0xFEDCBA98, 0x0F1E2D3C, 0x4B5A6978]
_SCRATCH = b"".join(w.to_bytes(4, "little") for w in _SCRATCH_WORDS)
# Value each AMO writes or combines with memory: (low word, high word) for doubleword pairs on RV32,
# and the doublewords of the source pair of amocas.q
_SRC_LO, _SRC_HI = 0x12345678, 0x9ABCDEF0

_RV64 = "#if __riscv_xlen == 64"
_ZABHA = "#ifdef ZABHA_SUPPORTED"
_LOADS = {1: "lb", 2: "lh", 4: "lw", 8: "ld"}

# (mnemonic, access size in bytes, guard) for the AMOArithmetic-level AMOs, grouped by guard
_AMO_OPS = ["swap", "add", "and", "or", "xor", "min", "max", "minu", "maxu"]
AMO_ARITHMETIC: list[tuple[str, int, str | None]] = [
    *[(f"amo{op}.w", 4, None) for op in _AMO_OPS],
    *[(f"amo{op}.d", 8, _RV64) for op in _AMO_OPS],
    *[(f"amo{op}.h", 2, _ZABHA) for op in _AMO_OPS],
    *[(f"amo{op}.b", 1, _ZABHA) for op in _AMO_OPS],
]
# The compare-and-swap AMOs added at the AMOCASW, AMOCASD and AMOCASQ levels, with their Zabha forms
AMO_CAS: list[tuple[str, int, str | None]] = [
    ("amocas.w", 4, None),
    ("amocas.d", 8, None),
    ("amocas.q", 16, _RV64),
    ("amocas.b", 1, _ZABHA),
    ("amocas.h", 2, _ZABHA),
]


def _signed(size: int) -> int:
    """The scratch value of the given size at offset 0, sign-extended as an AMO returns it."""
    value = int.from_bytes(_SCRATCH[:size], "little")
    return value - (1 << (8 * size)) if value >> (8 * size - 1) else value


def _init_scratch(base: int, tmp: int) -> list[str]:
    lines = [f"LA(x{base}, scratch)"]
    for i, word in enumerate(_SCRATCH_WORDS):
        lines += [f"LI(x{tmp}, {word:#x})", f"sw x{tmp}, {4 * i}(x{base})"]
    return lines


def _cas_operands(mnemonic: str, size: int, rd: int, rs2: int) -> list[str]:
    """Set the compare value (rd) to what scratch holds and the swap value (rs2)."""
    lo, hi = (int.from_bytes(_SCRATCH[i : i + 8], "little") for i in (0, 8))
    if size == 16:  # amocas.q (RV64): register pairs of doublewords
        return [
            f"LI(x{rd}, {lo:#x})",
            f"LI(x{rd + 1}, {hi:#x})",
            f"LI(x{rs2}, {_SRC_LO:#x})",
            f"LI(x{rs2 + 1}, {_SRC_HI:#x})",
        ]
    if size == 8:  # amocas.d: register pairs of words on RV32
        return [
            "#if __riscv_xlen == 32",
            f"LI(x{rd}, {_SCRATCH_WORDS[0]:#x})",
            f"LI(x{rd + 1}, {_SCRATCH_WORDS[1]:#x})",
            f"LI(x{rs2}, {_SRC_LO:#x})",
            f"LI(x{rs2 + 1}, {_SRC_HI:#x})",
            "#else",
            f"LI(x{rd}, {lo:#x})",
            f"LI(x{rs2}, {(_SRC_HI << 32) | _SRC_LO:#x})",
            "#endif",
        ]
    return [f"LI(x{rd}, {_signed(size)})  # sign-extended {mnemonic} compare value", f"LI(x{rs2}, {_SRC_LO:#x})"]


def _readback(size: int, base: int, chk: int, test_data: TestData) -> list[str]:
    """Record the memory the AMO wrote."""
    if size == 16:
        return [
            f"ld x{chk}, 0(x{base})",
            write_sigupd(chk, test_data),
            f"ld x{chk}, 8(x{base})",
            write_sigupd(chk, test_data),
        ]
    if size == 8:
        return [
            "#if __riscv_xlen == 32",
            f"lw x{chk}, 0(x{base})",
            write_sigupd(chk, test_data),
            f"lw x{chk}, 4(x{base})",
            write_sigupd(chk, test_data),
            "#else",
            f"ld x{chk}, 0(x{base})",
            write_sigupd(chk, test_data),
            "#endif",
        ]
    return [f"{_LOADS[size]} x{chk}, 0(x{base})", write_sigupd(chk, test_data)]


def amo_tests(
    test_data: TestData, ops: list[tuple[str, int, str | None]], coverpoint: str, covergroup: str
) -> list[str]:
    """Run each AMO in ops once on scratch and record the value it returns and the memory it leaves."""
    # amocas.d on RV32 and amocas.q take register pairs, so rd and rs2 are the even registers of pairs
    rd = test_data.int_regs.get_register_pair()
    rs2 = test_data.int_regs.get_register_pair()
    base, chk = test_data.int_regs.get_registers(2)
    lines = [comment_banner(coverpoint, "Each AMO on scratch: record the value it returns and the memory it leaves")]
    guard = None
    for mnemonic, size, op_guard in ops:
        if op_guard != guard:
            if guard is not None:
                lines.append("#endif")
            if op_guard is not None:
                lines.append(op_guard)
            guard = op_guard
        cas = mnemonic.startswith("amocas")
        lines += [
            "",
            *_init_scratch(base, chk),
            *(_cas_operands(mnemonic, size, rd, rs2) if cas else [f"LI(x{rs2}, {_SRC_LO:#x})"]),
            test_data.add_testcase(mnemonic.replace(".", "_"), coverpoint, covergroup),
            f"{mnemonic} x{rd}, x{rs2}, (x{base})",
            write_sigupd(rd, test_data),
        ]
        if size == 16:
            lines.append(write_sigupd(rd + 1, test_data))
        elif size == 8 and cas:
            lines += ["#if __riscv_xlen == 32", write_sigupd(rd + 1, test_data), "#endif"]
        lines += _readback(size, base, chk, test_data)
    if guard is not None:
        lines.append("#endif")
    test_data.int_regs.return_registers([base, chk])
    test_data.int_regs.return_register_pair(rd)
    test_data.int_regs.return_register_pair(rs2)
    return lines
