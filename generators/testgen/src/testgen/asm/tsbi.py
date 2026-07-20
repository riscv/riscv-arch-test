##################################
# asm/tsbi.py
#
# Assembly generation helpers for T-SBI call
# David_Harris@hmc.edu 7 July 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Assembly generation helpers for test code."""

from __future__ import annotations

import re

from testgen.constants import INDENT

_CSR_INSTR_RE = re.compile(r"(?i)(csrr|csrw|csrs|csrc)\s+([^,\s]+)\s*,\s*([^,\s]+)")
_MEM_INSTR_RE = re.compile(r"(?i)(lw|ld|sw|sd)\s+([^,\s]+)\s*,\s*([-+]?(?:0x[0-9a-f]+|\d+))\s*\(\s*([^\)\s]+)\s*\)")


def tsbi_call(instr: str) -> str:
    """
    Generate assembly for a T-SBI call

    Args:
      instr: the instruction to be executed in the T-SBI call

    Returns:
      A string containing the assembly code for the T-SBI call
    """

    normalized_instr = _normalize_instr(instr)
    rs1 = get_rs1(normalized_instr)
    rs2 = get_rs2(normalized_instr)
    rd = get_rd(normalized_instr)

    preamble = []
    postscript = []
    if rs1 not in [0, 11]:
        preamble.append(f"{INDENT}# Copy rs1 (x{rs1}) to a1 for T-SBI call\n{INDENT}mv a1, x{rs1}\n")
    if rs2 not in [0, 12]:
        preamble.append(f"{INDENT}# Copy rs2 (x{rs2}) to a2 for T-SBI call\n{INDENT}mv a2, x{rs2}\n")
    if rd not in [0, 10]:
        postscript.append(f"{INDENT}# Copy a0 to rd (x{rd}) for T-SBI call\n{INDENT}mv x{rd}, a0\n")

    return "\n".join(
        [
            f"{INDENT}# T-SBI call to execute instruction: {instr}",
            *preamble,
            f"{INDENT}LI(a0, {add_opcode(normalized_instr, rs1, rs2, rd)}) # {instr}",
            f"{INDENT}ecall # T-SBI call to execute instruction at suitable privilege level",
            *postscript,
        ]
    )


_REGISTER_ALIASES = {
    "zero": 0,
    "ra": 1,
    "sp": 2,
    "gp": 3,
    "tp": 4,
    "t0": 5,
    "t1": 6,
    "t2": 7,
    "s0": 8,
    "fp": 8,
    "s1": 9,
    "a0": 10,
    "a1": 11,
    "a2": 12,
    "a3": 13,
    "a4": 14,
    "a5": 15,
    "a6": 16,
    "a7": 17,
    "s2": 18,
    "s3": 19,
    "s4": 20,
    "s5": 21,
    "s6": 22,
    "s7": 23,
    "s8": 24,
    "s9": 25,
    "s10": 26,
    "s11": 27,
    "t3": 28,
    "t4": 29,
    "t5": 30,
    "t6": 31,
}

_CSR_ALIASES = {
    "sstatus": 0x100,
    "sie": 0x104,
    "stvec": 0x105,
    "scounteren": 0x106,
    "sscratch": 0x140,
    "sepc": 0x141,
    "scause": 0x142,
    "sip": 0x144,
    "senvcfg": 0x10A,
    "satp": 0x180,
    "mstatus": 0x300,
    "misa": 0x301,
    "medeleg": 0x302,
    "mideleg": 0x303,
    "mie": 0x304,
    "mtvec": 0x305,
    "mcounteren": 0x306,
    "mscratch": 0x340,
    "mepc": 0x341,
    "mcause": 0x342,
    "mip": 0x344,
    "menvcfg": 0x30A,
    "menvcfgh": 0x31A,
    "stimecmp": 0x14D,
    "stimecmph": 0x15D,
}


def _parse_register(reg: str) -> int:
    reg_name = reg.strip().lower()
    if match := re.fullmatch(r"x([0-9]|[12][0-9]|3[01])", reg_name):
        return int(match.group(1))
    if reg_name in _REGISTER_ALIASES:
        return _REGISTER_ALIASES[reg_name]
    raise ValueError(f"Unsupported register name: {reg}")


def _parse_csr(csr: str) -> int:
    csr_name = csr.strip().lower()
    if csr_name in _CSR_ALIASES:
        return _CSR_ALIASES[csr_name]
    try:
        csr_num = int(csr_name, 0)
    except ValueError as exc:
        raise ValueError(f"Unsupported CSR name: {csr}") from exc
    if not 0 <= csr_num <= 0xFFF:
        raise ValueError(f"CSR out of 12-bit range: {csr}")
    return csr_num


def _parse_imm12(imm: str) -> int:
    try:
        imm_val = int(imm, 0)
    except ValueError as exc:
        raise ValueError(f"Unsupported immediate value: {imm}") from exc
    if not -(1 << 11) <= imm_val < (1 << 11):
        raise ValueError(f"Immediate out of 12-bit signed range: {imm}")
    return imm_val & 0xFFF


def _normalize_instr(instr: str) -> str:
    return instr.split("#", 1)[0].strip()


def get_rd(normalized_instr: str) -> int:
    if csr_match := _CSR_INSTR_RE.fullmatch(normalized_instr):
        mnemonic = csr_match.group(1).lower()
        if mnemonic == "csrr":
            return _parse_register(csr_match.group(2))
        return 0

    if mem_match := _MEM_INSTR_RE.fullmatch(normalized_instr):
        mnemonic = mem_match.group(1).lower()
        if mnemonic in {"lw", "ld"}:
            return _parse_register(mem_match.group(2))
        return 0

    raise ValueError(f"Unsupported instruction format for register extraction: {normalized_instr}")


def get_rs1(normalized_instr: str) -> int:
    if csr_match := _CSR_INSTR_RE.fullmatch(normalized_instr):
        mnemonic = csr_match.group(1).lower()
        if mnemonic == "csrr":
            return 0
        return _parse_register(csr_match.group(3))

    if mem_match := _MEM_INSTR_RE.fullmatch(normalized_instr):
        return _parse_register(mem_match.group(4))

    raise ValueError(f"Unsupported instruction format for register extraction: {normalized_instr}")


def get_rs2(normalized_instr: str) -> int:
    if csr_match := _CSR_INSTR_RE.fullmatch(normalized_instr):
        mnemonic = csr_match.group(1).lower()
        if mnemonic in {"csrr", "csrw", "csrs", "csrc"}:
            return 0

    if mem_match := _MEM_INSTR_RE.fullmatch(normalized_instr):
        mnemonic = mem_match.group(1).lower()
        if mnemonic in {"sw", "sd"}:
            return _parse_register(mem_match.group(2))
        return 0

    raise ValueError(f"Unsupported instruction format for register extraction: {normalized_instr}")


def _tsbi_rd_reg(rd: int) -> int:
    return rd if rd in {0, 10} else 10


def _tsbi_rs1_reg(rs1: int) -> int:
    return rs1 if rs1 in {0, 11} else 11


def _tsbi_rs2_reg(rs2: int) -> int:
    return rs2 if rs2 in {0, 12} else 12


def _encode_i_type(opcode: int, funct3: int, rd: int, rs1: int, imm12: int) -> int:
    return (
        ((imm12 & 0xFFF) << 20) | ((rs1 & 0x1F) << 15) | ((funct3 & 0x7) << 12) | ((rd & 0x1F) << 7) | (opcode & 0x7F)
    )


def _encode_s_type(opcode: int, funct3: int, rs1: int, rs2: int, imm12: int) -> int:
    return (
        (((imm12 >> 5) & 0x7F) << 25)
        | ((rs2 & 0x1F) << 20)
        | ((rs1 & 0x1F) << 15)
        | ((funct3 & 0x7) << 12)
        | ((imm12 & 0x1F) << 7)
        | (opcode & 0x7F)
    )


def add_opcode(normalized_instr: str, rs1: int, rs2: int, rd: int) -> str:
    """Return the 32-bit opcode encoding for a supported assembly instruction."""
    csr_match = _CSR_INSTR_RE.fullmatch(normalized_instr)
    if csr_match:
        mnemonic = csr_match.group(1).lower()
        first_arg = csr_match.group(2)
        second_arg = csr_match.group(3)
        opcode = 0x73
        tsbi_rd = _tsbi_rd_reg(rd)
        tsbi_rs1 = _tsbi_rs1_reg(rs1)

        if mnemonic == "csrr":
            csr = _parse_csr(second_arg)
            encoded = _encode_i_type(opcode, 0b010, tsbi_rd, tsbi_rs1, csr)
        else:
            csr = _parse_csr(first_arg)
            funct3 = {"csrw": 0b001, "csrs": 0b010, "csrc": 0b011}[mnemonic]
            encoded = _encode_i_type(opcode, funct3, tsbi_rd, tsbi_rs1, csr)

        return f"0x{encoded:08x}"

    mem_match = _MEM_INSTR_RE.fullmatch(normalized_instr)
    if mem_match:
        mnemonic = mem_match.group(1).lower()
        imm12 = _parse_imm12(mem_match.group(3))
        tsbi_rd = _tsbi_rd_reg(rd)
        tsbi_rs1 = _tsbi_rs1_reg(rs1)
        tsbi_rs2 = _tsbi_rs2_reg(rs2)

        if mnemonic in {"lw", "ld"}:
            funct3 = {"lw": 0b010, "ld": 0b011}[mnemonic]
            encoded = _encode_i_type(0x03, funct3, tsbi_rd, tsbi_rs1, imm12)
        else:
            funct3 = {"sw": 0b010, "sd": 0b011}[mnemonic]
            encoded = _encode_s_type(0x23, funct3, tsbi_rs1, tsbi_rs2, imm12)

        return f"0x{encoded:08x}"

    raise ValueError(f"Unsupported instruction format for opcode conversion: {normalized_instr}")
