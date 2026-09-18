##################################
# priv/extensions/HPT.py
#
# H two-stage page-table test generation
# wutianze@ict.ac.cn Sep 2026
# Assisted by the MLVP AI framework
# SPDX-License-Identifier: Apache-2.0
##################################
"""H two-stage page-table test generation.

Guest-memory (hlv/hlvx/hsv) and fence (hfence/sfence.vma) stimulus over
explicit two-stage page tables (hgatp G-stage + vsatp VS-stage). The
hypervisor CSR sub-suite lives in HCSR; shared scaffolding in HCommon.
"""

from collections.abc import Iterator
from itertools import product

from testgen.constants import TESTCASES_PER_PRIV_FILE
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.HCommon import (
    Case,
    finish_case,
    new_case,
)
from testgen.priv.registry import add_priv_test_generator

def fence_tests(td: TestData, cp: str, hypervisor: bool) -> Iterator[TestChunk]:
    modes = ("m", "hs") if hypervisor else ("m", "hs", "vs")
    instructions = ("hfence.vvma", "hfence.gvma") if hypervisor else ("sfence.vma",)
    for mode, inst, tvm, vtvm in product(modes, instructions, range(2), range(2)):
        case = new_case(td, cp, mode, f"{mode}_{inst}_tvm{tvm}_vtvm{vtvm}", ("hstatus",))
        case.field("mstatus", 1 << 20, tvm << 20)
        case.field("hstatus", 1 << 20, vtvm << 20)
        case.enter()
        case.instruction(f"{inst} zero, zero")
        expected = 0
        if mode == "hs" and tvm and inst != "hfence.vvma":
            expected = 2
        if mode == "vs" and vtvm:
            expected = 22
        case.recover(expected)
        yield finish_case(case)


def vm_tables(case: Case, executable: bool, spvp: int) -> str:
    """Implement the contract's explicit-access pagewalk and payload closure.

    GVA = payload PA - 0x60000000; GPA = PA - 0x40000000. A single
    aligned 64KiB block guarantees all pagewalk/payload GPAs share a lowest
    G-stage table. Only actual walk pages and payload are mapped, never host
    code/signature. All PPNs come from linked symbols.
    """
    prefix = case.label + "_"
    names = ("g_root", "g_l1", "g_l0", "vs_root", "vs_l1", "vs_l0", "payload")
    case.tc.code[1] = "# H_RESOURCE_MODE two_stage"
    case.tc.raw_data.append(".balign 65536")
    for name in names:
        case.tc.raw_data += [f"{prefix}{name}_pa:", f".zero {16384 if name == 'g_root' else 4096}"]
    for name in ("vs_root", "vs_l1", "vs_l0", "payload"):
        case.tc.raw_data.append(f".set {prefix}{name}_gpa, {prefix}{name}_pa - 0x40000000")
    case.tc.raw_data.append(f".set {prefix}payload_gva, {prefix}payload_pa - 0x60000000")
    case.emit(f"# Nonidentity symbols: {prefix}payload_gva -> {prefix}payload_gpa -> {prefix}payload_pa")

    def pte(table: str, address: str, shift: int, mask: int, target: str, flags: int, xlen: int) -> None:
        case.emit(
            f"LA(x{case.p}, {prefix}{table}_pa)",
            f"LA(x{case.t}, {prefix}{address})",
            f"srli x{case.t}, x{case.t}, {shift}",
            f"LI(x{case.a}, {mask})",
            f"and x{case.t}, x{case.t}, x{case.a}",
            f"slli x{case.t}, x{case.t}, {2 if xlen == 32 else 3}",
            f"add x{case.p}, x{case.p}, x{case.t}",
            f"LA(x{case.t}, {prefix}{target})",
            f"srli x{case.t}, x{case.t}, 12",
            f"slli x{case.t}, x{case.t}, 10",
            f"ori x{case.t}, x{case.t}, {flags}",
            f"SREG x{case.t}, 0(x{case.p})",
        )

    # These branches are the smallest UDB-supported modes reviewed in the VM
    # contract. No assumption about Sv48/Sv57 or the selected platform PA.
    for xlen in (32, 64):
        case.emit(f"#if __riscv_xlen == {xlen}")
        if xlen == 64:
            pte("g_root", "payload_gpa", 30, 2047, "g_l1_pa", 1, xlen)
            pte("g_l1", "payload_gpa", 21, 511, "g_l0_pa", 1, xlen)
            pte("vs_root", "payload_gva", 30, 511, "vs_l1_gpa", 1, xlen)
            pte("vs_l1", "payload_gva", 21, 511, "vs_l0_gpa", 1, xlen)
        else:
            pte("g_root", "payload_gpa", 22, 4095, "g_l0_pa", 1, xlen)
            pte("vs_root", "payload_gva", 22, 1023, "vs_l0_gpa", 1, xlen)
        index_mask = 1023 if xlen == 32 else 511
        for name in ("vs_root", "vs_l0") + (("vs_l1",) if xlen == 64 else ()):
            pte("g_l0", name + "_gpa", 12, index_mask, name + "_pa", 0xD7, xlen)
        permission = 0xC9 if executable else 0xC7
        pte("g_l0", "payload_gpa", 12, index_mask, "payload_pa", permission | 0x10, xlen)
        pte("vs_l0", "payload_gva", 12, index_mask, "payload_gpa", permission | (0x10 if not spvp else 0), xlen)
        case.emit(
            "fence rw, rw",
            f"LA(x{case.t}, {prefix}g_root_pa)",
            f"srli x{case.t}, x{case.t}, 12",
            f"LI(x{case.a}, {1 << 31 if xlen == 32 else 8 << 60})",
            f"or x{case.t}, x{case.t}, x{case.a}",
        )
        case.write("hgatp", case.t)
        case.emit(
            "hfence.gvma zero, zero",
            "nop",
            f"LA(x{case.t}, {prefix}vs_root_gpa)",
            f"srli x{case.t}, x{case.t}, 12",
            f"or x{case.t}, x{case.t}, x{case.a}",
        )
        case.write("vsatp", case.t)
        case.emit("hfence.vvma zero, zero", "nop", "#endif")
    case.field("vsstatus", (1 << 18) | (1 << 19), 0)
    return prefix


def memory_tests(td: TestData, cp: str, kind: str) -> Iterator[TestChunk]:
    instructions = {
        "hlv": [
            ("hlv.b", 1, True, False),
            ("hlv.bu", 1, False, False),
            ("hlv.h", 2, True, False),
            ("hlv.hu", 2, False, False),
            ("hlv.w", 4, True, False),
            ("hlv.wu", 4, False, True),
            ("hlv.d", 8, True, True),
        ],
        "hlvx": [("hlvx.hu", 2, False, False), ("hlvx.wu", 4, False, False)],
        "hsv": [
            ("hsv.b", 1, False, False),
            ("hsv.h", 2, False, False),
            ("hsv.w", 4, False, False),
            ("hsv.d", 8, False, True),
        ],
    }[kind]
    for mode in ("m", "hs", "u"):
        for (inst, width, signed, only64), hu, spvp, pattern in product(instructions, range(2), range(2), range(3)):
            if mode == "u" and not hu:
                continue
            value = (0, 0x35, -1)[pattern]
            case = new_case(
                td,
                cp,
                mode,
                f"{mode}_{inst}_hu{hu}_spvp{spvp}_p{pattern}",
                ("hstatus", "vsstatus", "vsatp", "hgatp"),
                "__riscv_xlen == 64 && defined(SV39_SUPPORTED)"
                if only64
                else "(__riscv_xlen == 32 && defined(SV32_SUPPORTED)) || (__riscv_xlen == 64 && defined(SV39_SUPPORTED))",
                virtual=True,
            )
            prefix = vm_tables(case, kind == "hlvx", spvp)
            case.field("hstatus", (1 << 9) | (1 << 8), (hu << 9) | (spvp << 8))
            case.emit(f"LA(x{case.p}, {prefix}payload_pa)", f"LI(x{case.b}, 0x5a)")
            for offset in range(16):
                case.emit(f"sb x{case.b}, {offset}(x{case.p})")
            if kind != "hsv":
                case.emit(
                    f"LI(x{case.b}, {value})",
                    f"{'sd' if width == 8 else 'sw' if width == 4 else 'sh' if width == 2 else 'sb'} x{case.b}, 8(x{case.p})",
                )
            case.emit("fence rw, rw")
            case.enter()
            # Random allocator assignments vary both address and value/result.
            case.emit(f"LA(x{case.a}, {prefix}payload_gva)", f"addi x{case.a}, x{case.a}, 8", f"LI(x{case.b}, {value})")
            operand = case.b if kind == "hsv" else case.r
            case.instruction(f"{inst} x{operand}, (x{case.a})")
            case.recover(0)
            if kind == "hsv":
                case.emit(f"LA(x{case.p}, {prefix}payload_pa)")
                for offset in range(16):
                    byte = (value >> (8 * (offset - 8))) & 255 if 8 <= offset < 8 + width else 0x5A
                    case.emit(f"lbu x{case.r}, {offset}(x{case.p})")
                    case.expect(case.r, byte)
                    case.signature(case.r)
            else:
                raw = value & ((1 << (width * 8)) - 1)
                expected = raw - (1 << (width * 8)) if signed and raw & (1 << (width * 8 - 1)) else raw
                case.expect(case.r, expected)
                case.signature(case.r)
            yield finish_case(case)


@add_priv_test_generator(
    "H",
    required_extensions=["H", "Sm", "S", "U", "Zicsr"],
    extra_defines=["#define BOOT_TO_MMODE"],
    testcases_per_file=16,
)
def make_hpt(test_data: TestData) -> list[TestChunk]:
    """Generate the H page-table sub-suite targets using native automatic splitting."""
    assert TESTCASES_PER_PRIV_FILE >= 16
    chunks: list[TestChunk] = []
    chunks.extend(memory_tests(test_data, "cp_hlv", "hlv"))
    chunks.extend(memory_tests(test_data, "cp_hlvx", "hlvx"))
    chunks.extend(memory_tests(test_data, "cp_hsv", "hsv"))
    chunks.extend(fence_tests(test_data, "cp_hfence", True))
    chunks.extend(fence_tests(test_data, "cp_sfence", False))
    return chunks
