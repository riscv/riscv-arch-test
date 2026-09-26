##################################
# priv/extensions/HCommon.py
#
# Shared test generation for the hypervisor suites.
# David_Harris@hmc.edu 24 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared definitions and test generation for the hypervisor suites."""

from collections.abc import Callable
from dataclasses import dataclass

from testgen.asm.csr import csr_access_test, csr_walk_test, gen_csr_read_sigupd, gen_csr_write_sigupd
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.random import random_int
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.PrivCommon import S_SSTATUS_MASK
from testgen.priv.extensions.sv.generate import guest_translation_setup, guest_translation_teardown, per_xlen
from testgen.priv.extensions.sv.page_tables import SV_MODES, PteFlags, SvMode, write_pte


@dataclass(frozen=True)
class HCsr:
    """A hypervisor CSR and how the access and walk tests treat it.

    mask: bits whose readback is checked (None checks all bits)
    masked: write only the mask bits, because other bits are WLRL or otherwise unsafe to write
    zero: the CSR need only hold zero, so the access test checks the readback only after writing zero and after
        clearing every bit, and the walk test skips it
    gate: preprocessor condition under which the CSR exists
    warl_fields: WARL fields with reserved encodings, as for csr_walk_test
    setup, restore: lines before and after the test that make the CSR accessible or its value visible
    """

    name: str
    mask: int | None = None
    masked: bool = False
    zero: bool = False
    gate: str | None = None
    warl_fields: tuple[tuple, ...] = ()
    setup: tuple[str, ...] = ()
    restore: tuple[str, ...] = ()


# hstatus fields checked by the access and walk tests.  VSBE is left out like UBE, because Sail has no
# big-endian support; VGEIN is WLRL (cp_hstatus_vgein); VSXL is WARL.
HSTATUS_MASK = (
    (1 << 6)  # GVA
    | (1 << 7)  # SPV
    | (1 << 8)  # SPVP
    | (1 << 9)  # HU
    | (1 << 20)  # VTVM
    | (1 << 21)  # VTW
    | (1 << 22)  # VTSR
)

# hedeleg bits the spec requires to be writable (1-8, 12, 13, 15, 18, 19) or read-only zero
# (9-11, 16, 20-23).  Bit 0 depends on IALIGN.
HEDELEG_MASK = 0xFDBFFE
# hideleg: VS-level interrupts 2, 6 and 10 are writable; 1, 5, 9 and 12 are read-only zero.
HIDELEG_MASK = 0x1666
# The VS-level interrupts (MIP_VS_MASK).  hie.SGEIE is left out: it is writable only if GEILEN > 0 (hie_acc).
VS_INTERRUPTS = 0x444
# hip also has the read-only SGEIP, which is zero while no guest external interrupt is pending (MIP_HS_MASK)
HIP_MASK = 0x1444
# henvcfg fields, as for menvcfg in Sm
HENVCFG_MASK = (
    (1 << 0)  # FIOM
    | (1 << 2)  # LPE
    | (1 << 3)  # SSE
    | (3 << 4)  # CBIE
    | (1 << 6)  # CBCFE
    | (1 << 7)  # CBZE
    | (3 << 32)  # PMM
    | (1 << 61)  # ADUE
    | (1 << 62)  # PBMTE
    | (1 << 63)  # STCE
)
HENVCFG_WARL = (("cbie", 4, 2, 0b10), ("pmm", 32, 2, 0b01))

# vsie and vsip show only interrupts delegated by hideleg.  vstimecmp is accessible below M-mode
# only with menvcfg.STCE = 1, and hedelegh only with mstateen0.P1P13 = 1.
HIDELEG_ON = ("RVTEST_TSBI_CSR_WRITE(CSR_HIDELEG, MIP_VS_MASK)",)
HIDELEG_OFF = ("RVTEST_TSBI_CSR_WRITE(CSR_HIDELEG, 0)",)
STCE_ON = (
    "#if __riscv_xlen == 64",
    "RVTEST_TSBI_CSR_SET(CSR_MENVCFG, MENVCFG_STCE)",
    "#else",
    "RVTEST_TSBI_CSR_SET(CSR_MENVCFGH, MENVCFGH_STCE)",
    "#endif",
)
STCE_OFF = tuple(line.replace("_SET(", "_CLEAR(") for line in STCE_ON)
P1P13_ON = ("#ifdef SMSTATEEN_SUPPORTED", "RVTEST_TSBI_CSR_SET(CSR_MSTATEEN0H, MSTATEEN0H_PRIV113)", "#endif")
P1P13_OFF = ("#ifdef SMSTATEEN_SUPPORTED", "RVTEST_TSBI_CSR_CLEAR(CSR_MSTATEEN0H, MSTATEEN0H_PRIV113)", "#endif")

# mtval2 and htval must hold zero (mtval2_val, htval_val), and mtinst and htinst must hold the zero that a trap
# may write (mtinst_val, htinst_val).  hgatp, vsatp and hedelegh hold zero, and their other bits are WARL.
H_M_CSRS = [HCsr("mtval2", zero=True), HCsr("mtinst", zero=True)]

H_HS_CSRS = [
    HCsr("hstatus", HSTATUS_MASK, masked=True),
    HCsr("hedeleg", HEDELEG_MASK),
    HCsr("hideleg", HIDELEG_MASK),
    HCsr("hie", VS_INTERRUPTS),
    HCsr("hcounteren"),
    HCsr("hgeie"),
    HCsr("henvcfg", HENVCFG_MASK, masked=True, warl_fields=HENVCFG_WARL),
    HCsr("htval", zero=True),
    HCsr("hip", HIP_MASK),
    HCsr("hvip", VS_INTERRUPTS),
    HCsr("htinst", zero=True),
    HCsr("hgatp", zero=True),
    HCsr("htimedelta", gate="defined(ZICNTR_SUPPORTED)"),
    # RV32-only high halves
    HCsr(
        "hedelegh",
        zero=True,
        gate="__riscv_xlen == 32 && defined(SM1P13P0_OR_LATER_SUPPORTED)",
        setup=P1P13_ON,
        restore=P1P13_OFF,
    ),
    HCsr("htimedeltah", gate="__riscv_xlen == 32 && defined(ZICNTR_SUPPORTED)"),
    HCsr("henvcfgh", HENVCFG_MASK >> 32, masked=True, gate="__riscv_xlen == 32"),
]

# vscause is WLRL, so it is written only with legal values (cp_vscause_write_*)
H_VS_CSRS = [
    HCsr("vsstatus", S_SSTATUS_MASK),
    HCsr("vsie", 0xFFFF, setup=HIDELEG_ON, restore=HIDELEG_OFF),
    HCsr("vstval"),
    HCsr("vsip", 0xFFFF, setup=HIDELEG_ON, restore=HIDELEG_OFF),
    HCsr("vstvec", 0b10),  # as stvec: legal BASE values are implementation-defined
    HCsr("vsscratch"),
    HCsr("vsepc"),
    HCsr("vsatp", zero=True),
    HCsr("vstimecmp", gate="defined(SSTC_SUPPORTED)", setup=STCE_ON, restore=STCE_OFF),
    HCsr("vstimecmph", gate="__riscv_xlen == 32 && defined(SSTC_SUPPORTED)", setup=STCE_ON, restore=STCE_OFF),
]

# Configs where Sv39/Sv39x4 (RV64) or Sv32/Sv32x4 (RV32) can be selected
ATP_GATE = {
    "satp": "(__riscv_xlen == 64 && defined(SV39_SUPPORTED)) || (__riscv_xlen == 32 && defined(SV32_SUPPORTED))",
    "vsatp": "(__riscv_xlen == 64 && defined(UDB_SV39_VSMODE_TRANSLATION)) || "
    "(__riscv_xlen == 32 && defined(UDB_SV32_VSMODE_TRANSLATION))",
    "hgatp": "(__riscv_xlen == 64 && defined(UDB_SV39X4_TRANSLATION)) || "
    "(__riscv_xlen == 32 && defined(UDB_SV32X4_TRANSLATION))",
}
TWO_STAGE_GATE = f"({ATP_GATE['vsatp']}) && ({ATP_GATE['hgatp']})"
REPLICA_ATP_GATE = f"({ATP_GATE['satp']}) && ({ATP_GATE['vsatp']})"


def gated(lines: list[str], gate: str | None) -> list[str]:
    """Wrap lines in #if gate."""
    if gate is None:
        return lines
    return [f"#if {gate}", *lines, f"#endif // {gate}"]


def hcsr_tests(test_data: TestData, test_chunks: list[TestChunk], csrs: list[HCsr], covergroup: str) -> None:
    """Access and walk each H CSR in csrs, access the read-only hgeip, and walk hgatp and vsatp with a paged MODE."""
    tc = test_data.new_test_chunk(test_chunks, "hcsr_access")
    tc.section_header = comment_banner(
        "cp_hcsr_access",
        "Read, write all 1s, write all 0s, set all 1s, clear all 1s and restore each H CSR.  hgeip is read-only,\n"
        "so its writes raise illegal instruction",
    )
    for csr in csrs:
        tc = test_data.new_test_chunk(test_chunks)
        if csr.zero:
            coverpoint = "cp_hcsr_access_zero"
            save_reg, ones_reg, check_reg = test_data.int_regs.get_registers(3)
            lines = [
                f"csrr x{save_reg}, {csr.name}",
                f"LI(x{ones_reg}, -1)",
                test_data.add_testcase(f"{csr.name}_csrrw1", coverpoint, covergroup),
                f"csrw {csr.name}, x{ones_reg}",
                test_data.add_testcase(f"{csr.name}_csrrw0", coverpoint, covergroup),
                f"csrw {csr.name}, zero",
                gen_csr_read_sigupd(check_reg, (csr.name, None), test_data),
                test_data.add_testcase(f"{csr.name}_csrs_all", coverpoint, covergroup),
                f"csrs {csr.name}, x{ones_reg}",
                test_data.add_testcase(f"{csr.name}_csrrc_all", coverpoint, covergroup),
                f"csrc {csr.name}, x{ones_reg}",
                gen_csr_read_sigupd(check_reg, (csr.name, None), test_data),
                f"csrw {csr.name}, x{save_reg}",
            ]
            test_data.int_regs.return_registers([save_reg, ones_reg, check_reg])
        else:
            coverpoint = "cp_hcsr_access_masked" if csr.masked else "cp_hcsr_access"
            lines = csr_access_test(test_data, (csr.name, csr.mask), covergroup, coverpoint, maskedwrites=csr.masked)
        tc.code.extend(gated([*csr.setup, *lines, *csr.restore], csr.gate))
    tc = test_data.new_test_chunk(test_chunks)
    tc.code.extend(csr_access_test(test_data, ("hgeip", None), covergroup, "cp_hcsr_access_ro"))

    tc = test_data.new_test_chunk(test_chunks, "hcsr_walk")
    tc.section_header = comment_banner("cp_hcsrwalk", "Set and clear each bit of each H CSR that holds more than zero")
    for csr in csrs:
        if not csr.zero:
            tc = test_data.new_test_chunk(test_chunks)
            coverpoint = "cp_hcsrwalk_masked" if csr.masked else "cp_hcsrwalk"
            lines = csr_walk_test(
                test_data,
                (csr.name, csr.mask),
                covergroup,
                coverpoint,
                warl_fields=list(csr.warl_fields) or None,
                maskedwrites=csr.masked,
            )
            tc.code.extend(gated([*csr.setup, *lines, *csr.restore], csr.gate))

    tc = test_data.new_test_chunk(test_chunks)
    tc.section_header = comment_banner(
        "cp_atpwalk1, cp_atpwalk0", "Walk a 1 and a 0 through the non-MODE bits of hgatp and vsatp"
    )
    for csr in ("hgatp", "vsatp"):
        tc = test_data.new_test_chunk(test_chunks)
        tc.code.extend(_atp_walk_test(test_data, csr, covergroup))


def _atp_walk_test(test_data: TestData, csr: str, covergroup: str) -> list[str]:
    """Walk a 1 and a 0 through the non-MODE bits of hgatp or vsatp with MODE = Sv39(x4) or Sv32(x4).

    MODE = Bare with other bits nonzero is UNSPECIFIED, and unsupported MODEs are legalized in an
    implementation-defined way, so MODE is held at a paged mode.  The PPN need not hold page numbers beyond the
    physical address width, so the readback leaves out PPN bits UDB_PHYS_ADDR_WIDTH-12 and up.
    """
    save_reg, mode_reg, val_reg, check_reg, mask_reg = test_data.int_regs.get_registers(5)

    def mode_and_mask(g: SvMode, vs: SvMode) -> list[str]:
        ppn = f"SATP{vs.xlen}_PPN"
        return [
            f"LI(x{mode_reg}, {(g if csr == 'hgatp' else vs).atp_mode:#x})",
            f"LI(x{mask_reg}, (~{ppn} | ((1 << (UDB_PHYS_ADDR_WIDTH - 12)) - 1)))",
        ]

    lines = [f"#if {ATP_GATE[csr]}", f"csrr x{save_reg}, {csr}", *per_xlen(mode_and_mask)]
    for walking_ones in (True, False):
        if not walking_ones:
            lines.extend(per_xlen(lambda g, _: [f"LI(x{val_reg}, {(1 << (60 if g.xlen == 64 else 31)) - 1:#x})"]))
            lines.append(f"or x{mode_reg}, x{mode_reg}, x{val_reg}    # MODE with every other bit set")
        for bit in range(60):
            if bit == 31:
                lines.append("#if __riscv_xlen == 64")
            lines.extend(
                [
                    f"LI(x{val_reg}, {1 << bit:#x})",
                    f"{'or' if walking_ones else 'xor'} x{val_reg}, x{val_reg}, x{mode_reg}",
                    test_data.add_testcase(f"{csr}_{bit}", f"cp_atpwalk{int(walking_ones)}", covergroup),
                    f"csrw {csr}, x{val_reg}",
                    f"csrr x{check_reg}, {csr}",
                    f"and x{check_reg}, x{check_reg}, x{mask_reg}",
                    write_sigupd(check_reg, test_data),
                ]
            )
        lines.append("#endif // __riscv_xlen == 64")
    lines.extend([f"csrw {csr}, x{save_reg}", f"#endif // {ATP_GATE[csr]}"])
    test_data.int_regs.return_registers([save_reg, mode_reg, val_reg, check_reg, mask_reg])
    return lines


def atp_mode_test(test_data: TestData, csr: str, covergroup: str, coverpoint: str) -> list[str]:
    """Write vsatp or hgatp with MODE = Bare and with each paged MODE that satp supports, and read it back.

    The other fields are zero, because MODE = Bare with nonzero fields is UNSPECIFIED.
    """
    suffix = "x4" if csr == "hgatp" else ""
    save_reg, val_reg = test_data.int_regs.get_registers(2)
    lines = [
        comment_banner(
            coverpoint,
            f"Write {csr} with MODE = Bare and with each of Sv32{suffix}, Sv39{suffix}, Sv48{suffix} and Sv57{suffix}\n"
            "whose satp MODE is supported.  The other fields are zero",
        ),
        f"csrr x{save_reg}, {csr}",
    ]
    modes: list[tuple[str, int, str | None]] = [("bare", 0, None)]
    modes.extend(
        (f"{sv.name}{suffix}", sv.atp_mode, f"__riscv_xlen == {sv.xlen} && defined({sv.suffix}_SUPPORTED)")
        for sv in SV_MODES
    )
    for name, value, gate in modes:
        body = [
            f"LI(x{val_reg}, {value:#x})",
            test_data.add_testcase(name, coverpoint, covergroup),
            gen_csr_write_sigupd(val_reg, csr, test_data),
        ]
        lines.extend(gated(body, gate))
    lines.append(f"csrw {csr}, x{save_reg}")
    test_data.int_regs.return_registers([save_reg, val_reg])
    return lines


###########################
# Hypervisor load and store instructions and guest-page faults
###########################

# (mnemonic, RV64 only)
HLV_INSTRS = [
    ("hlv.b", False),
    ("hlv.bu", False),
    ("hlv.h", False),
    ("hlv.hu", False),
    ("hlv.w", False),
    ("hlv.wu", True),
    ("hlv.d", True),
]
HLVX_INSTRS = [("hlvx.hu", False), ("hlvx.wu", False)]
HSV_INSTRS = [("hsv.b", False), ("hsv.h", False), ("hsv.w", False), ("hsv.d", True)]

# The sign bit of every access size is set, so sign and zero extension differ
HLV_DATA = 0x8BADF00DFEEDC0DE


def hlv_tests(test_data: TestData, tc: TestChunk, covergroup: str, modes: tuple[str, ...]) -> list[str]:
    """hlv, hlvx and hsv from each of modes ("m", "hs" or "u") through non-identity two-stage translation.

    The VS-stage maps the superpage at vs.data_va to the guest physical superpage at g.data_va, which the G-stage
    maps to the superpage of H_hlv_data.  U-mode runs with hstatus.HU = 1.  H_hlv_data is written and checked
    through its physical address.
    """
    tc.raw_data.extend([".p2align 3", "H_hlv_data:", "  .dword 0"])
    va_reg = test_data.int_regs.get_register()

    def mappings(g: SvMode, vs: SvMode) -> list[str]:
        pte, addr, tmp = test_data.int_regs.get_registers(3)
        top = vs.levels - 1
        shift = vs.page_offset_bits(top)
        lines = [
            *write_pte(
                vs,
                level=top,
                flags=PteFlags(user=True),
                virtual_address=vs.data_va,
                physical_address=g.data_va,
                regs=(pte, addr, tmp),
                pa_is_label=False,
                superpage=True,
            ),
            *write_pte(
                g,
                level=top,
                flags=PteFlags(user=True),
                virtual_address=g.data_va,
                physical_address="H_hlv_data",
                regs=(pte, addr, tmp),
                superpage=True,
            ),
            f"LA(x{va_reg}, H_hlv_data)",
            f"slli x{va_reg}, x{va_reg}, {vs.xlen - shift}",
            f"srli x{va_reg}, x{va_reg}, {vs.xlen - shift}",
            f"LI(x{tmp}, (({vs.data_va}) >> {shift}) << {shift})",
            f"or x{va_reg}, x{va_reg}, x{tmp}    # guest virtual address of H_hlv_data",
        ]
        test_data.int_regs.return_registers([pte, addr, tmp])
        return [*lines, *guest_translation_setup(test_data, g, vs, "VSmode")]

    lines = [
        comment_banner(
            "cp_hlv, cp_hlvx, cp_hsv",
            f"Load and store through two-stage translation from {' and '.join(f'{m.upper()}-mode' for m in modes)}",
        ),
        f"#if {TWO_STAGE_GATE}",
        *per_xlen(mappings),
    ]
    pa_reg, val_reg, rd = test_data.int_regs.get_registers(3)
    load_data = [
        "#if __riscv_xlen == 64",
        f"LI(x{val_reg}, {HLV_DATA:#x})",
        "#else",
        f"LI(x{val_reg}, {HLV_DATA & 0xFFFFFFFF:#x})",
        "#endif",
    ]
    for mode in modes:
        if mode == "u":
            lines.extend([f"LI(x{pa_reg}, HSTATUS_HU)", f"csrs hstatus, x{pa_reg}", "RVTEST_TSBI_GOTO_UMODE"])
        lines.append(f"LA(x{pa_reg}, H_hlv_data)")
        for instrs, coverpoint in ((HLV_INSTRS, "cp_hlv"), (HLVX_INSTRS, "cp_hlvx")):
            for instr, rv64 in instrs:
                body = [
                    *load_data,
                    f"SREG x{val_reg}, 0(x{pa_reg})",
                    test_data.add_testcase(f"{mode}_{instr}", coverpoint, covergroup),
                    f"{instr} x{rd}, (x{va_reg})",
                    write_sigupd(rd, test_data),
                ]
                lines.extend(gated(body, "__riscv_xlen == 64" if rv64 else None))
        for instr, rv64 in HSV_INSTRS:
            body = [
                f"SREG x0, 0(x{pa_reg})",
                *load_data,
                test_data.add_testcase(f"{mode}_{instr}", "cp_hsv", covergroup),
                f"{instr} x{val_reg}, (x{va_reg})",
                f"LREG x{rd}, 0(x{pa_reg})",
                write_sigupd(rd, test_data),
            ]
            lines.extend(gated(body, "__riscv_xlen == 64" if rv64 else None))
        if mode == "u":
            lines.extend(["RVTEST_TSBI_GOTO_SMODE", f"LI(x{pa_reg}, HSTATUS_HU)", f"csrc hstatus, x{pa_reg}"])
    test_data.int_regs.return_registers([va_reg, pa_reg, val_reg, rd])
    return [*lines, *guest_translation_teardown(test_data), f"#endif // {TWO_STAGE_GATE}"]


# Guest physical addresses that no G-stage leaf maps: the page accessed and the VS-stage root table
GPF_GPA = 0x1000
GPF_VS_ROOT_GPA = 0x2000


def guest_page_fault_tests(test_data: TestData, covergroup: str) -> list[str]:
    """hlv.w and hsv.w that raise guest-page faults, whose trap records hold mtval2/htval and mtinst/htinst.

    With vsatp = Bare the fault is on the final translation, where xtinst may be zero.  With the VS-stage root table
    at an unmapped guest physical address the fault is on an implicit access, where xtinst holds a pseudoinstruction
    if mtval2/htval is nonzero.  Runs in M-mode or HS-mode with an empty G-stage root table.
    """
    mode_reg, va_reg, rd = test_data.int_regs.get_registers(3)
    lines = [
        f"#if {TWO_STAGE_GATE}",
        f"SET_MSB(x{mode_reg})    # Sv39x4/Sv39 or Sv32x4/Sv32",
        f"LA(x{va_reg}, rvtest_Hroot_pg_tbl)",
        f"srli x{va_reg}, x{va_reg}, 12",
        f"or x{va_reg}, x{va_reg}, x{mode_reg}",
        f"csrw hgatp, x{va_reg}",
        "csrw vsatp, zero",
        "hfence.gvma",
        f"LI(x{va_reg}, {GPF_GPA:#x})",
    ]
    for vsatp in ("bare", "paged"):
        if vsatp == "paged":
            lines.extend(
                [
                    f"LI(x{rd}, {GPF_VS_ROOT_GPA >> 12:#x})",
                    f"or x{rd}, x{rd}, x{mode_reg}",
                    f"csrw vsatp, x{rd}",
                    "hfence.vvma",
                ]
            )
        lines.extend(
            [
                f"LI(x{rd}, 42)",
                test_data.add_testcase(f"hlv_w_{vsatp}", "cp_guest_page_fault", covergroup),
                f"hlv.w x{rd}, (x{va_reg})",
                write_sigupd(rd, test_data),
                test_data.add_testcase(f"hsv_w_{vsatp}", "cp_guest_page_fault", covergroup),
                f"hsv.w x{rd}, (x{va_reg})",
            ]
        )
    lines.extend(["csrw vsatp, zero", "csrw hgatp, zero", "hfence.gvma", "hfence.vvma", f"#endif // {TWO_STAGE_GATE}"])
    test_data.int_regs.return_registers([mode_reg, va_reg, rd])
    return lines


# (bin, coverpoint, instruction, guest virtual address for a VS-stage mode) of a fault taken by guest_fault_tests
GuestFault = tuple[str, str, str, Callable[[SvMode], int]]


def guest_fault_tests(
    test_data: TestData,
    covergroup: str,
    tval_csr: str,
    leaves: Callable[[SvMode, SvMode, bool, tuple[int, int, int]], list[str]],
    faults: list[GuestFault],
) -> list[str]:
    """Take each fault from VS-mode and from VU-mode under two-stage translation, after writing tval_csr randomly.

    leaves(g, vs, user, regs) writes the faulting VS-stage PTEs with three scratch registers.  Faulting loads leave
    rd unchanged, which HS-mode checks because VU-mode cannot write the signature through the supervisor-only
    identity map.
    """
    addr_reg, rd = test_data.int_regs.get_registers(2)
    lines = [f"#if {TWO_STAGE_GATE}"]
    for mode in ("vs", "vu"):

        def mappings(g: SvMode, vs: SvMode, user: bool = mode == "vu") -> list[str]:
            pte, addr, tmp = test_data.int_regs.get_registers(3)
            ptes = leaves(g, vs, user, (pte, addr, tmp))
            test_data.int_regs.return_registers([pte, addr, tmp])
            return [*ptes, *guest_translation_setup(test_data, g, vs, "VUmode" if user else "VSmode")]

        lines.extend([*per_xlen(mappings), f"LI(x{rd}, 42)", f"RVTEST_TSBI_GOTO_{mode.upper()}MODE"])
        for bin_name, coverpoint, instr, address in faults:
            lines.extend(
                [
                    *per_xlen(lambda _, vs, va=address: [f"LI(x{addr_reg}, {va(vs):#x})"]),
                    f"RVTEST_TSBI_CSR_WRITE(CSR_{tval_csr.upper()}, {random_int(32, signed=False):#x})",
                    test_data.add_testcase(f"{mode}_{bin_name}", coverpoint, covergroup),
                    f"jalr x1, 0(x{addr_reg})" if instr == "jalr" else f"{instr} x{rd}, 0(x{addr_reg})",
                ]
            )
        lines.extend(["RVTEST_TSBI_GOTO_SMODE", write_sigupd(rd, test_data)])
    test_data.int_regs.return_registers([addr_reg, rd])
    return [*lines, *guest_translation_teardown(test_data), f"#endif // {TWO_STAGE_GATE}"]


###########################
# sret from M-mode and HS-mode
###########################


def sret_tests(test_data: TestData, covergroup: str, coverpoint: str, home: str) -> list[str]:
    """Execute sret in home ("m" or "s") with each SPP, SPIE and hstatus.SPV.

    home writes SPP and SPIE through its own status CSR, which the coverage samples.  After each sret, a read of
    mscratch traps and the trap record shows the mode reached.  home then checks SPP, SPIE, SIE and hstatus.SPV.
    """
    status = "mstatus" if home == "m" else "sstatus"
    save_reg, save_h_reg, temp_reg, rd = test_data.int_regs.get_registers(4)
    lines = [
        comment_banner(
            coverpoint, f"Execute sret with {status}.SPP = {{0, 1}}, SPIE = {{0, 1}} and hstatus.SPV = {{0, 1}}"
        ),
        f"csrr x{save_reg}, {status}",
        f"csrr x{save_h_reg}, hstatus",
    ]
    for spp in (0, 1):
        for spie in (0, 1):
            for spv in (0, 1):
                name = f"spp{spp}_spie{spie}_spv{spv}"
                bits = " | ".join(bit for bit, on in (("SSTATUS_SPP", spp), ("SSTATUS_SPIE", spie)) if on) or "0"
                lines.extend(
                    [
                        f"LI(x{temp_reg}, SSTATUS_SPP | SSTATUS_SPIE)",
                        f"csrc {status}, x{temp_reg}",
                        f"LI(x{temp_reg}, {bits})",
                        f"csrs {status}, x{temp_reg}",
                        f"LI(x{temp_reg}, HSTATUS_SPV)",
                        f"{'csrs' if spv else 'csrc'} hstatus, x{temp_reg}",
                        f"LA(x{temp_reg}, 1f)",
                        f"csrw sepc, x{temp_reg}",
                        test_data.add_testcase(name, coverpoint, covergroup),
                        "sret",
                        "1:",
                        f"LI(x{rd}, 42)",
                        test_data.add_testcase(f"{name}_mode", coverpoint, covergroup),
                        f"csrr x{rd}, mscratch",
                        write_sigupd(rd, test_data),
                        f"RVTEST_TSBI_GOTO_{home.upper()}MODE",
                        f"LI(x{temp_reg}, SSTATUS_SPP | SSTATUS_SPIE | SSTATUS_SIE)",
                        test_data.add_testcase(f"{name}_{status}", coverpoint, covergroup),
                        f"csrr x{rd}, {status}",
                        f"and x{rd}, x{rd}, x{temp_reg}",
                        write_sigupd(rd, test_data),
                        f"LI(x{temp_reg}, HSTATUS_SPV)",
                        test_data.add_testcase(f"{name}_hstatus", coverpoint, covergroup),
                        f"csrr x{rd}, hstatus",
                        f"and x{rd}, x{rd}, x{temp_reg}",
                        write_sigupd(rd, test_data),
                    ]
                )
    lines.extend([f"csrw {status}, x{save_reg}", f"csrw hstatus, x{save_h_reg}"])
    test_data.int_regs.return_registers([save_reg, save_h_reg, temp_reg, rd])
    return lines


###########################
# Replicated S/VS CSRs
###########################

# sstatus fields the replica tests change.  SIE stays 0 so no interrupt is taken.
REPLICA_SSTATUS_MASK = (1 << 5) | (1 << 8) | (1 << 18) | (1 << 19)  # SPIE, SPP, SUM, MXR


@dataclass(frozen=True)
class Replica:
    """An S CSR, its VS replica, the bits checked, and the values written by each step.

    values are (S initial, VS initial, S new, VS new).  For stvec a value is an offset in 256-byte
    units into the code region; for satp it names the page table that the Sv39/Sv32 value points
    to, or None for Bare.  Enabled and pending interrupt bits never coincide, so no interrupt is taken.
    """

    s: str
    vs: str
    mask: int | None
    values: tuple


REPLICAS = [
    Replica("sstatus", "vsstatus", REPLICA_SSTATUS_MASK, (0x40020, 0x80100, 0x80020, 0x40100)),
    Replica("sie", "vsie", 0x222, (0x200, 0x000, 0x000, 0x200)),
    Replica("stvec", "vstvec", None, (1, 2, 3, 4)),
    Replica("sscratch", "vsscratch", None, (0x1D2C3B4A, 0x5E6F7081, 0x2468ACE0, 0x13579BDF)),
    Replica("sepc", "vsepc", None, (0x1A2B3C4C, 0x7E8F9AA8, 0x55AA55A4, 0x0F0F0F00)),
    Replica("scause", "vscause", None, (2, 13, 5, 7)),
    Replica("stval", "vstval", None, (0x6B5A4938, 0x3C4D5E6F, 0x7A7A0101, 0x10203040)),
    Replica("sip", "vsip", 0x222, (0x002, 0x000, 0x000, 0x002)),
    # satp stays Bare while HS-mode runs
    Replica("satp", "vsatp", None, (None, "rvtest_Vroot_pg_tbl", None, "rvtest_Hroot_pg_tbl")),
]


def replica_write(test_data: TestData, rep: Replica, csr: str, value: int | str | None, reg: int) -> list[str]:
    """Write one replica test value to csr, ending with the csrw that cp_replica samples."""
    tmp = test_data.int_regs.get_register()
    if rep.s == "sstatus":
        lines = [
            f"csrr x{reg}, {csr}",
            f"LI(x{tmp}, {REPLICA_SSTATUS_MASK:#x})",
            f"or x{reg}, x{reg}, x{tmp}",
            f"xor x{reg}, x{reg}, x{tmp}",
            f"LI(x{tmp}, {value:#x})",
            f"or x{reg}, x{reg}, x{tmp}",
        ]
    elif rep.s == "stvec":
        lines = [
            f"LA(x{reg}, rvtest_code_begin)",
            f"srli x{reg}, x{reg}, 8",
            f"addi x{reg}, x{reg}, {value}",
            f"slli x{reg}, x{reg}, 8",
        ]
    elif rep.s == "satp" and value is not None:
        lines = [
            f"LA(x{reg}, {value})",
            f"srli x{reg}, x{reg}, 12",
            *per_xlen(lambda _, vs: [f"LI(x{tmp}, {vs.atp_mode:#x})"]),
            f"or x{reg}, x{reg}, x{tmp}",
        ]
    else:
        lines = [f"LI(x{reg}, {value or 0:#x})"]
    test_data.int_regs.return_register(tmp)
    return [*lines, f"csrw {csr}, x{reg}"]


def replica_read(
    test_data: TestData, rep: Replica, csr: str, mask_reg: int, bin_name: str, covergroup: str
) -> list[str]:
    """Read csr and check the replica test's bits.  mask_reg already holds rep.mask if there is one."""
    check = test_data.int_regs.get_register()
    lines = [
        test_data.add_testcase(bin_name, "cp_replica", covergroup),
        gen_csr_read_sigupd(check, (csr, rep.mask), test_data, mask_reg if rep.mask is not None else None),
    ]
    test_data.int_regs.return_register(check)
    return lines
