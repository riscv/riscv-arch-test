##################################
# priv/extensions/HCSR.py
#
# H CSR test generation
# wutianze@ict.ac.cn Sep 2026
# Assisted by the MLVP AI framework
# SPDX-License-Identifier: Apache-2.0
##################################
"""H CSR test generation.

Access, WARL walk, replica, denied, high-half and WLRL scalar stimulus
for the hypervisor CSR sub-suite. The guest-memory (hlv/hlvx/hsv), fence
and return families are contributed as follow-up donations.
"""

from collections.abc import Iterator
from itertools import product

from testgen.constants import TESTCASES_PER_PRIV_FILE
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.HCommon import (
    CSR,
    M_CSRS,
    OPS,
    S_CSRS,
    VS_CSRS,
    Case,
    csr_inventory,
    finish_case,
    new_case,
)
from testgen.priv.registry import add_priv_test_generator


def legal_mask(csr: str) -> str:
    """Restrict WLRL values and translation MODE while preserving useful WARL tests."""
    if csr in ("satp", "vsatp", "hgatp"):
        return "0xfffff"  # Bare, small PPN field: never changes instruction translation.
    fixed = {
        "hedeleg": 0xB1FF,
        "hedelegh": 0,
        "hideleg": 0x444,
        "hie": 0x1444,
        "hip": 4,
        "hvip": 0x444,
        "hcounteren": 0xFFFFFFFF,
        "henvcfg": 1,
        "henvcfgh": 0,
        "vsie": 0x222,
        "vsip": 2,
        "sie": 0x222,
        "sip": 2,
        "scounteren": 0xFFFFFFFF,
        "senvcfg": 1,
    }
    if csr in fixed:
        return str(fixed[csr])
    if csr == "hgeie":
        return "((1 << UDB_NUM_EXTERNAL_GUEST_INTERRUPTS) - 1) << 1"
    if csr in ("scause", "vscause"):
        return "2"  # Illegal instruction is a supported WLRL cause.
    if csr == "hstatus":
        return "0x700380"  # SPV/SPVP/HU/VTVM/VTW/VTSR, no reserved VGEIN/VSXL.
    if csr in ("sstatus", "vsstatus"):
        return "0xc6722"  # SIE/SPIE/SPP/VS/FS/SUM/MXR, excludes WPRI/UXL.
    if csr in ("stvec", "vstvec", "sepc", "vsepc"):
        return "0x7fc"  # Direct vector/aligned EPC, no reserved vector mode.
    return "-1"


def csr_instruction(case: Case, csr: str, op: str, value: str | int | None = None) -> str:
    """Exact CSR operation under test; capture rd and defer signature to M."""
    # Numeric encodings permit intentional accesses to RV32-only CSRs on RV64.
    csr_operand = f"CSR_{csr.upper()}" if csr in ("hedelegh", "henvcfgh", "htimedeltah", "vstimecmph") else csr
    if op == "read":
        return f"csrrs x{case.r}, {csr_operand}, zero"
    operand = "0" if op == "write_zero" else legal_mask(csr) if value is None else str(value)
    case.emit(f"LI(x{case.b}, {operand})")
    saved_csr = "v" + csr if case.mode == "vs" and csr in S_CSRS else csr
    if op.startswith("write") and saved_csr in case.saved:
        # Writes preserve WPRI/untested fields from an independent old-value
        # slot. Set/clear already supply a mask and leave all other bits alone.
        case.emit(
            f"LI(x{case.t}, {legal_mask(csr)})",
            f"and x{case.b}, x{case.b}, x{case.t}",
            f"not x{case.t}, x{case.t}",
            f"LA(x{case.p}, {case.base})",
            f"LREG x{case.a}, {case.saved.index(saved_csr) * 8}(x{case.p})",
            f"and x{case.a}, x{case.a}, x{case.t}",
            f"or x{case.b}, x{case.b}, x{case.a}",
        )
    mnemonic = "csrrs" if op == "set" else "csrrc" if op == "clear" else "csrrw"
    return f"{mnemonic} x{case.r}, {csr_operand}, x{case.b}"


def csr_case(
    td: TestData,
    cp: str,
    mode: str,
    csr: CSR,
    op: str,
    expected: int = 0,
    value: int | str | None = None,
    tag: str = "",
    tvm: int = 0,
    vtvm: int = 0,
) -> TestChunk:
    name = f"{mode}_{csr.name}_{op}{tag}"
    changed = (csr.name,) if expected == 0 and csr.name != "hgeip" else ()
    changed += ("hstatus",) if tvm or vtvm or cp.endswith("tvm") else ()
    timer_access = csr.name in ("vstimecmp", "vstimecmph")
    if timer_access:
        changed += ("menvcfg", "mcounteren")
    case = new_case(td, cp, mode, name, changed, csr.guard)
    if mode != "m" and csr.name in ("henvcfg", "henvcfgh", "senvcfg", "hedelegh"):
        case.enable_stateen(csr.name)
    if timer_access:
        case.timer_access = True
        case.emit("#if __riscv_xlen == 32")
        case.read(case.t, "menvcfgh")
        case.store_slot(case.t, 5)
        case.field("menvcfgh", "(1 << 31)", "(1 << 31)")
        case.emit("#else")
        case.field("menvcfg", "(1 << 63)", "(1 << 63)")
        case.emit("#endif")
        case.field("mcounteren", 2, 2)
    case.field("mstatus", 1 << 20, tvm << 20)
    if "hstatus" in case.saved:
        case.field("hstatus", 1 << 20, vtvm << 20)
    # HS/VS test controls must be set before mode entry. Operand preparation is
    # privilege independent and does not overwrite the mode helper's saved state.
    case.enter()
    inst = csr_instruction(case, csr.name, op, value)
    case.instruction(inst)
    case.recover(expected)
    if expected == 0:
        case.signature(case.r)
        if csr.name != "hgeip":
            readback = "v" + csr.name if mode == "vs" and csr.name in S_CSRS else csr.name
            case.read(case.r, readback)
            case.signature(case.r)
    return finish_case(case)


def access_tests(td: TestData, cp: str, mode: str) -> Iterator[TestChunk]:
    for csr in csr_inventory(machine=mode == "m"):
        for op in OPS:
            expected = 2 if csr.name == "hgeip" and op != "read" else 0
            yield csr_case(td, cp, mode, csr, op, expected)


def denied_tests(td: TestData, cp: str, mode: str, scope: str) -> Iterator[TestChunk]:
    if scope == "machine":
        csrs = [CSR(name) for name in M_CSRS]
    elif scope == "supervisor":
        csrs = csr_inventory(supervisor=True) + [CSR("senvcfg"), CSR("scounteren")]
    else:
        csrs = csr_inventory(machine=scope == "all")
    for csr, op in product(csrs, OPS):
        expected = 2 if mode == "u" or csr.name in M_CSRS or (csr.name == "hgeip" and op != "read") else 22
        yield csr_case(td, cp, mode, csr, op, expected)


def walk_tests(td: TestData, cp: str, mode: str) -> Iterator[TestChunk]:
    csrs = (
        [CSR(s) for s in M_CSRS]
        if mode == "m"
        else [csr for csr in csr_inventory() if csr.name not in ("hstatus", "vsstatus", "hgeip", "vscause")]
    )
    for csr in csrs:
        masks = {
            "hedeleg": 0xB1FF,
            "hedelegh": 0,
            "hideleg": 0x444,
            "hie": 0x1444,
            "hip": 4,
            "hvip": 0x444,
            "hcounteren": 0xFFFFFFFF,
            "henvcfg": 1,
            "henvcfgh": 0,
            "vsie": 0x222,
            "vsip": 2,
        }
        for bit in range(csr.access_bits or 64):
            if csr.name in masks and not (masks[csr.name] & (1 << bit)):
                continue
            # Bare translation roots use legal non-MODE bits. Other WARL masks
            # can coerce individual bits and their readbacks are recorded.
            if csr.name in ("vsatp", "hgatp") and bit >= 20:
                continue
            if csr.name == "vstvec" and bit < 2:
                continue
            guard = csr.guard
            if csr.name == "hgeie":
                if bit == 0:
                    continue
                guard = f"UDB_NUM_EXTERNAL_GUEST_INTERRUPTS >= {bit}"
            if bit >= 32:
                guard = f"({guard}) && __riscv_xlen == 64" if guard else "__riscv_xlen == 64"
            for op in ("set", "clear"):
                yield csr_case(td, cp, mode, CSR(csr.name, guard), op, value=1 << bit, tag=f"_bit{bit}")
    if mode == "hs":
        # WLRL vscause cannot be swept with reserved exception/interrupt codes.
        # Each selected bit has an explicitly legal set and clear result.
        for bit in (0, 1, 2, 3, 31, 63):
            guard = f"__riscv_xlen == {32 if bit == 31 else 64}" if bit >= 31 else None
            for op in ("set", "clear"):
                case = new_case(td, cp, mode, f"hs_vscause_{op}_bit{bit}", ("vscause",), guard)
                initial = (1 if bit >= 31 else 2) | ((1 << bit) if op == "clear" else 0)
                case.emit(f"LI(x{case.b}, {initial})")
                case.write("vscause", case.b)
                case.enter()
                case.instruction(csr_instruction(case, "vscause", op, 1 << bit))
                case.recover(0)
                case.read(case.r, "vscause")
                case.signature(case.r)
                yield finish_case(case)


def replica_tests(td: TestData, cp: str, mode: str) -> Iterator[TestChunk]:
    for host, guest in zip(S_CSRS, VS_CSRS):
        selected = (host,) if mode == "vs" else (host, guest)
        for csr, op in product(selected, OPS):
            case = new_case(td, cp, mode, f"{mode}_{csr}_{op}", (host, guest))
            peer = host if mode == "vs" or csr == guest else guest
            case.read(case.r, peer)
            case.store_slot(case.r, 5)
            case.enter()
            case.instruction(csr_instruction(case, csr, op))
            case.recover(0)
            case.read(case.r, peer)
            case.load_slot(case.b, 5)
            case.emit(f"xor x{case.r}, x{case.r}, x{case.b}")
            case.expect(case.r, 0)
            case.signature(case.r)
            case.read(case.r, guest if mode == "vs" else csr)
            case.signature(case.r)
            yield finish_case(case)


def high_half_tests(td: TestData, cp: str, mode: str) -> Iterator[TestChunk]:
    for name, gate in (
        ("hedelegh", None),
        ("henvcfgh", None),
        ("htimedeltah", "ZICNTR_SUPPORTED"),
        ("vstimecmph", "SSTC_SUPPORTED"),
    ):
        guard = "__riscv_xlen == 64" + (f" && defined({gate})" if gate else "")
        for op in OPS:
            yield csr_case(td, cp, mode, CSR(name, guard), op, 2)


def scalar_tests(td: TestData, cp: str, kind: str) -> Iterator[TestChunk]:
    if kind == "mtval":
        case = new_case(td, cp, "m", "mtval_nonzero", ("mtval",))
        case.emit(f"LA(x{case.b}, {case.base})")
        case.write("mtval", case.b)
        case.instruction(f"csrr x{case.r}, mtval")
        case.recover(0)
        case.emit(f"snez x{case.r}, x{case.r}")
        case.expect(case.r, 1)
        case.signature(case.r)
        yield finish_case(case)
    elif kind == "vscause":
        values = [str(x) for x in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 20, 21, 22, 23)]
        values += [f"(1 << (__riscv_xlen - 1)) | {x}" for x in (1, 5, 9)]
        for index, value in enumerate(values):
            case = new_case(td, cp, "hs", f"vscause_{index}", ("vscause",))
            case.enter()
            case.emit(f"LI(x{case.b}, {value})")
            case.instruction(f"csrrw x{case.r}, vscause, x{case.b}")
            case.read(case.r, "vscause")
            case.recover(0)
            case.expect(case.r, value)
            case.signature(case.r)
            yield finish_case(case)
    elif kind == "sd":
        for fs, vs, sd, host_fs in product(range(4), range(4), range(2), (0, 3)):
            case = new_case(
                td,
                cp,
                "vs",
                f"fs{fs}_vs{vs}_sd{sd}_hostfs{host_fs}",
                ("sstatus", "vsstatus"),
                "defined(F_SUPPORTED) && defined(V_SUPPORTED)",
            )
            case.field("mstatus", 3 << 13, host_fs << 13)
            case.enter()
            case.emit(f"LI(x{case.b}, ({fs} << 13) | ({vs} << 9) | ({sd} << (__riscv_xlen-1)))")
            case.instruction(f"csrrw x{case.r}, sstatus, x{case.b}")
            case.read(case.r, "sstatus")
            case.emit(f"srli x{case.r}, x{case.r}, (__riscv_xlen-1)")
            case.recover(0)
            case.expect(case.r, int(fs == 3 or vs == 3))
            case.signature(case.r)
            yield finish_case(case)


@add_priv_test_generator(
    "H",
    required_extensions=["H", "Sm", "S", "U", "Zicsr"],
    extra_defines=["#define BOOT_TO_MMODE"],
    testcases_per_file=16,
)
def make_h(test_data: TestData) -> list[TestChunk]:
    """Generate the H CSR sub-suite targets using native automatic splitting."""
    assert TESTCASES_PER_PRIV_FILE >= 16
    chunks: list[TestChunk] = []
    chunks.extend(access_tests(test_data, "cp_m_hcsr_access", "m"))
    chunks.extend(walk_tests(test_data, "cp_m_hcsr_walk", "m"))
    chunks.extend(replica_tests(test_data, "cp_m_replica", "m"))
    chunks.extend(scalar_tests(test_data, "cp_m_mtval", "mtval"))
    chunks.extend(access_tests(test_data, "cp_hs_hcsr_access", "hs"))
    chunks.extend(walk_tests(test_data, "cp_hs_hcsr_walk", "hs"))
    chunks.extend(denied_tests(test_data, "cp_hs_mcsr_denied", "hs", "machine"))
    chunks.extend(replica_tests(test_data, "cp_hs_replica", "hs"))
    chunks.extend(scalar_tests(test_data, "cp_hs_vscause", "vscause"))
    chunks.extend(denied_tests(test_data, "cp_vs_mcsr_denied", "vs", "machine"))
    chunks.extend(high_half_tests(test_data, "cp_vs_high_half", "vs"))
    chunks.extend(replica_tests(test_data, "cp_vs_replica", "vs"))
    for csr, op in product((CSR("senvcfg"), CSR("scounteren")), OPS):
        chunks.append(csr_case(test_data, "cp_vs_nonreplica", "vs", csr, op))
    chunks.extend(scalar_tests(test_data, "cp_vs_sd", "sd"))
    chunks.extend(denied_tests(test_data, "cp_u_hcsr_denied", "u", "all"))
    chunks.extend(high_half_tests(test_data, "cp_u_high_half", "u"))
    chunks.extend(denied_tests(test_data, "cp_vu_csr_denied", "vu", "all"))
    chunks.extend(high_half_tests(test_data, "cp_vu_high_half", "vu"))
    return chunks
