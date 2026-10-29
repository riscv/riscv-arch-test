##################################
# asm/tsbi.py
#
# Assembly generation helpers for T-SBI call
# David_Harris@hmc.edu 7 July 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Assembly generation helpers for test code."""

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
    if normalized_instr.lower() == "sfence.vma":
        return f"{INDENT}RVTEST_TSBI_SFENCE_VMA # T-SBI call to execute instruction: {instr}"
    rs1 = get_rs1(normalized_instr)
    rs2 = get_rs2(normalized_instr)
    rd = get_rd(normalized_instr)
    if _CSR_INSTR_RE.fullmatch(normalized_instr):
        return _tsbi_csr_call(instr, normalized_instr, rs1, rd)
    opcode = add_opcode(normalized_instr, rs1, rs2, rd)

    preamble = []
    postscript = []
    if rs1 not in [11]:
        preamble.append(f"{INDENT}# Copy rs1 (x{rs1}) to a1 for T-SBI call\n{INDENT}mv a1, x{rs1}\n")
    if rs2 not in [12]:
        preamble.append(f"{INDENT}# Copy rs2 (x{rs2}) to a2 for T-SBI call\n{INDENT}mv a2, x{rs2}\n")
    if rd not in [0, 10]:
        postscript.append(f"{INDENT}# Copy a0 to rd (x{rd}) for T-SBI call\n{INDENT}mv x{rd}, a0\n")

    return "\n".join(
        [
            f"{INDENT}# T-SBI call to execute instruction: {instr}",
            *preamble,
            f"{INDENT}LI(a0, {opcode}) # {instr}",
            f"{INDENT}ecall # T-SBI call to execute instruction at suitable privilege level",
            *postscript,
        ]
    )


def _csr_operand(csr: str) -> str:
    """A known CSR name becomes its CSR_* macro from encoding.h. A macro or number is used as is."""
    return f"CSR_{csr.upper()}" if csr.lower() in _CSR_ALIASES else csr


def _tsbi_csr_call(instr: str, normalized_instr: str, rs1: int, rd: int) -> str:
    """T-SBI CSR call through the RVTEST_TSBI_CSR macros, which take the value in a1 and return a read in a0."""
    mnemonic, first, second = _CSR_INSTR_RE.fullmatch(normalized_instr).groups()  # type: ignore[union-attr]
    lines = [f"{INDENT}# T-SBI call to execute instruction: {instr}"]
    if mnemonic.lower() == "csrr":
        lines.append(f"{INDENT}RVTEST_TSBI_CSR_READ({_csr_operand(second)})")
        if rd not in [0, 10]:
            lines.append(f"{INDENT}mv x{rd}, a0")
    else:
        if rs1 != 11:
            lines.append(f"{INDENT}mv a1, x{rs1}")
        macro = {
            "csrw": "RVTEST_TSBI_CSR_WRITE_A1",
            "csrs": "RVTEST_TSBI_CSR_ACCESS TSBI_CSR_SET",
            "csrc": "RVTEST_TSBI_CSR_ACCESS TSBI_CSR_CLEAR",
        }[mnemonic.lower()]
        lines.append(f"{INDENT}{macro}({_csr_operand(first)})")
    return "\n".join(lines)


def _csr_level(csr: str) -> int:
    """csr[9:8] of a CSR operand: a name, a number, or a CSR_* / RVTEST_CSR_* macro."""
    try:
        return (_parse_csr(csr) >> 8) & 3
    except ValueError:
        pass
    name = csr.lower().removeprefix("rvtest_csr_").removeprefix("csr_")
    if name in _CSR_ALIASES:
        return (_CSR_ALIASES[name] >> 8) & 3
    if name.startswith("mhpm"):  # the hpm counter and event CSRs are all M-mode
        return 3
    raise ValueError(f"Unsupported CSR name: {csr}")


# Highest CSR privilege level, csr[9:8], that code in each mode may access directly. Level 2 holds the
# hypervisor and VS CSRs, which exist only with H, and S-mode is HS-mode then.
_MAX_CSR_LEVEL = {"M": 3, "S": 2, "VS": 1, "U": 0, "VU": 0}


def tsbi_call_or_direct(instr: str, mode: str) -> str:
    """
    Generate a CSR instruction that runs directly when ``mode`` may access the CSR, otherwise through T-SBI.

    Args:
      instr: csrr/csrw/csrs/csrc instruction, optionally followed by a # comment
      mode: privilege mode the code runs in: "M", "S" (HS when H is implemented), "VS", "U" or "VU"

    Returns:
      instr unchanged, or the T-SBI call that executes it
    """
    csr_match = _CSR_INSTR_RE.fullmatch(_normalize_instr(instr))
    if csr_match is None:
        raise ValueError(f"tsbi_call_or_direct takes a csrr/csrw/csrs/csrc instruction: {instr}")
    csr = csr_match.group(3) if csr_match.group(1).lower() == "csrr" else csr_match.group(2)
    return instr if _MAX_CSR_LEVEL[mode] >= _csr_level(csr) else tsbi_call(instr)


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
    "senvcfg": 0x10A,
    "sscratch": 0x140,
    "sepc": 0x141,
    "scause": 0x142,
    "stval": 0x143,
    "sip": 0x144,
    "stimecmp": 0x14D,
    "stimecmph": 0x15D,
    "satp": 0x180,
    "vsstatus": 0x200,
    "mstatus": 0x300,
    "misa": 0x301,
    "medeleg": 0x302,
    "mideleg": 0x303,
    "mie": 0x304,
    "mtvec": 0x305,
    "mcounteren": 0x306,
    "menvcfg": 0x30A,
    "mstateen0": 0x30C,
    "mstateen1": 0x30D,
    "mstateen2": 0x30E,
    "mstateen3": 0x30F,
    "menvcfgh": 0x31A,
    "mstateen0h": 0x31C,
    "mstateen1h": 0x31D,
    "mstateen2h": 0x31E,
    "mstateen3h": 0x31F,
    "mcountinhibit": 0x320,
    "mscratch": 0x340,
    "mepc": 0x341,
    "mcause": 0x342,
    "mip": 0x344,
    "scontext": 0x5A8,
    "scountovf": 0xDA0,
    "hstatus": 0x600,
    "hie": 0x604,
    "hcounteren": 0x606,
    "hip": 0x644,
    "hcontext": 0x6A8,
    "mseccfg": 0x747,
    "tselect": 0x7A0,
    "tdata1": 0x7A1,
    "tdata2": 0x7A2,
    "tdata3": 0x7A3,
    "tinfo": 0x7A4,
    "tcontrol": 0x7A5,
    "mcontext": 0x7A8,
    "mscontext": 0x7AA,
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
        tsbi_rs1 = 11

        if mnemonic == "csrr":
            csr = _parse_csr(second_arg)
            encoded = _encode_i_type(opcode, 0b010, tsbi_rd, 0, csr)
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
        tsbi_rs1 = 11
        tsbi_rs2 = 12

        if mnemonic in {"lw", "ld"}:
            funct3 = {"lw": 0b010, "ld": 0b011}[mnemonic]
            encoded = _encode_i_type(0x03, funct3, tsbi_rd, tsbi_rs1, imm12)
        else:
            funct3 = {"sw": 0b010, "sd": 0b011}[mnemonic]
            encoded = _encode_s_type(0x23, funct3, tsbi_rs1, tsbi_rs2, imm12)

        return f"0x{encoded:08x}"

    raise ValueError(f"Unsupported instruction format for opcode conversion: {normalized_instr}")
