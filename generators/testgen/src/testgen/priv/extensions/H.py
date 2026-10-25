##################################
# H.py
#
# H hypervisor extension tests that run in HS, VS, U and VU modes.
# David_Harris@hmc.edu 24 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""H hypervisor extension test generator.

The suite boots to HS-mode.  The HS-mode handler takes traps from U, VS and VU (hedeleg = 0).
Tests that need mstatus.TVM = 1 are in the Sm suite's Sm_H group.
"""

from testgen.asm.csr import csr_access_test, gen_csr_read_sigupd
from testgen.asm.helpers import comment_banner, gated, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.FCommon import gen_fcsr_tests
from testgen.priv.extensions.HCommon import (
    H_HS_CSRS,
    H_VS_CSRS,
    HSTATUS_MASK,
    REPLICA_ATP_GATE,
    REPLICAS,
    HCsr,
    guest_page_fault_tests,
    hcsr_tests,
    hlv_tests,
    replica_read,
    replica_rw_tests,
    replica_write,
    sret_tests,
)
from testgen.priv.extensions.PrivCommon import (
    csr_insufficient_priv_tests,
    csr_ro_write_tests,
    xcause_write_tests,
    xstatus_sd_tests,
    xtval_value_tests,
)
from testgen.priv.extensions.VCommon import gen_v_tests
from testgen.priv.extensions.VFCommon import gen_vf_tests
from testgen.priv.extensions.ZicntrCommon import Counteren, Mode, counteren_walk_tests, htimedelta_tests
from testgen.priv.registry import add_priv_test_generator

HS_CG = "H_hscsr_cg"
VSCAUSE_CG = "H_vscause_cg"
VS_CG = "H_vscsr_cg"
VSSTATUS_CG = "H_vsstatus_cg"
VU_CG = "H_vucsr_cg"
INST_CG = "H_inst_cg"

# The CSR numbers of the M-mode CSRs, which VS-mode cannot access, as in S (cp_csr_insufficient_priv)
M_CSR_RANGES = [
    range(0x300, 0x400),
    range(0x700, 0x7AA),  # exclude 0x7AA mscontext, which is accessible from S-mode
    range(0x7AB, 0x800),
    range(0xB00, 0xC00),
    range(0xF00, 0x1000),
]
# The CSR numbers that are not user CSRs, and the user read-only CSRs, as in U (cp_csr_insufficient_priv, cp_csr_ro).
# 0x7AA mscontext is left out as in S, because it may be accessible from S-mode and so raise virtual instruction.
NONUSER_CSR_RANGES = [
    range(0x100, 0x400),
    range(0x500, 0x7AA),
    range(0x7AB, 0x800),
    range(0x900, 0xC00),
    range(0xD00, 0x1000),
]
USER_RO_CSR_RANGES = [range(0xC00, 0xD00)]
# Each VS-mode and VU-mode chunk of the CSR sweeps enters the mode once
CSRS_PER_CHUNK = 16

# HS and VS H CSRs, which VS-mode and VU-mode cannot access
HS_VS_CSRS = [*H_HS_CSRS, HCsr("hgeip"), *H_VS_CSRS, HCsr("vscause")]
# High halves of H CSRs, illegal on RV64, where the assembler knows only their numbers
H_UPPER_CSRS = [
    HCsr(f"CSR_{name}", gate="__riscv_xlen == 64") for name in ("HEDELEGH", "HTIMEDELTAH", "HENVCFGH", "VSTIMECMPH")
]
S_UNREPLICATED_CSRS = [
    HCsr("scounteren"),
    HCsr("senvcfg", gate="defined(S1P12P0_OR_LATER_SUPPORTED)"),
]
# scountinhibit raises illegal instruction with menvcfg.CDE = 0, as boot leaves it, and virtual instruction in
# VS-mode and VU-mode with CDE = 1
SCOUNTINHIBIT = HCsr("scountinhibit", gate="defined(SSCCFG_SUPPORTED)")


def _csr_trap_test(test_data: TestData, csr: HCsr, covergroup: str, coverpoint: str) -> list[str]:
    """Access a CSR that traps in the current mode, as csr_access_test does a CSR that does not."""
    lines = csr_access_test(test_data, (csr.operand, None), covergroup, coverpoint)
    return gated([*csr.setup, *lines, *csr.restore], csr.gate)


def _vgein_tests(test_data: TestData) -> list[str]:
    """hstatus.VGEIN holds each value from 0 through GEILEN; larger values are WLRL, so they are not written."""
    save_reg, val_reg, mask_reg, check_reg = test_data.int_regs.get_registers(4)
    mask = HSTATUS_MASK | (0x3F << 12)
    lines = [
        comment_banner("cp_hstatus_vgein", "Write hstatus.VGEIN = 0, 1, GEILEN-1 and GEILEN"),
        f"csrr x{save_reg}, hstatus",
        f"LI(x{mask_reg}, {HSTATUS_MASK:#x} | HSTATUS_VGEIN)",
    ]
    for name, value in (
        ("zero", "0"),
        ("one", "1"),
        ("geilen_m1", "(UDB_NUM_EXTERNAL_GUEST_INTERRUPTS - 1)"),
        ("geilen", "UDB_NUM_EXTERNAL_GUEST_INTERRUPTS"),
    ):
        body = [
            f"LI(x{val_reg}, HSTATUS_VGEIN)",
            f"csrc hstatus, x{val_reg}",
            f"csrr x{val_reg}, hstatus",
            *([] if value == "0" else [f"LI(x{check_reg}, {value} << 12)", f"or x{val_reg}, x{val_reg}, x{check_reg}"]),
            test_data.add_testcase(name, "cp_hstatus_vgein", HS_CG),
            f"csrw hstatus, x{val_reg}",
            gen_csr_read_sigupd(check_reg, ("hstatus", mask), test_data, mask_reg),
        ]
        lines.extend(body if name == "zero" else gated(body, "UDB_NUM_EXTERNAL_GUEST_INTERRUPTS >= 1"))
    lines.append(f"csrw hstatus, x{save_reg}")
    test_data.int_regs.return_registers([save_reg, val_reg, mask_reg, check_reg])
    return lines


# S CSRs that the HS-mode trap handler needs (stvec, sscratch) or that a trap into HS-mode rewrites
TRAP_HANDLER_S_CSRS = ("stvec", "sscratch", "sepc", "scause", "stval")


def _replica_tests(test_data: TestData) -> list[str]:
    """S CSRs and their VS replicas accessed from HS-mode and from VS-mode, and read back in HS-mode."""
    val_reg = test_data.int_regs.get_register()
    lines = [
        comment_banner(
            "cp_replica (HS-mode)",
            "HS-mode writes different values to an S CSR and its VS replica, reads both, writes new values and\n"
            "reads them back",
        ),
        f"LI(x{val_reg}, MIP_VS_MASK)",
        f"csrw hideleg, x{val_reg}",
    ]
    test_data.int_regs.return_register(val_reg)
    lines.extend(
        [*replica_rw_tests(test_data, HS_CG, ((0, 1, "hs_{csr}_init"), (2, 3, "hs_{csr}"))), "csrw hideleg, zero"]
    )

    lines.append(
        comment_banner(
            "cp_replica (VS-mode)",
            "HS-mode writes different values to an S CSR and its VS replica.  VS-mode reads the S CSR name,\n"
            "writes a new value and reads it back, which reaches the replica.  HS-mode reads both.  The return\n"
            "to HS-mode is a trap, which needs stvec and sscratch and rewrites sepc, scause and stval: HS-mode\n"
            "leaves those S CSRs alone and checks only their replicas.  satp and vsatp stay Bare, because\n"
            "the HS-mode and VS-mode code is not mapped",
        )
    )
    save_s, save_vs, mask_reg, val_reg = test_data.int_regs.get_registers(4)
    for rep in REPLICAS:
        satp = rep.s == "satp"
        s_checked = rep.s not in TRAP_HANDLER_S_CSRS
        s_init, vs_init, vs_new = (None, None, None) if satp else (rep.values[0], rep.values[1], rep.values[3])
        body = [f"LI(x{val_reg}, MIP_VS_MASK)", f"csrw hideleg, x{val_reg}"]
        if s_checked:
            body.extend([f"csrr x{save_s}, {rep.s}", *replica_write(test_data, rep, rep.s, s_init, val_reg)])
        body.extend(
            [
                f"csrr x{save_vs}, {rep.vs}",
                *replica_write(test_data, rep, rep.vs, vs_init, val_reg),
                *([f"LI(x{mask_reg}, {rep.mask:#x})"] if rep.mask else []),
                "RVTEST_TSBI_GOTO_VSMODE",
                *replica_read(test_data, rep, rep.s, mask_reg, f"vs_{rep.s}_init", VS_CG),
                *replica_write(test_data, rep, rep.s, vs_new, val_reg),
                *replica_read(test_data, rep, rep.s, mask_reg, f"vs_{rep.s}", VS_CG),
                "RVTEST_TSBI_GOTO_SMODE",
            ]
        )
        if s_checked:
            body.extend(
                [
                    *replica_read(test_data, rep, rep.s, mask_reg, f"vs_{rep.s}_hs", VS_CG),
                    f"csrw {rep.s}, x{save_s}",
                ]
            )
        body.extend(
            [
                *replica_read(test_data, rep, rep.vs, mask_reg, f"vs_{rep.vs}_hs", VS_CG),
                f"csrw {rep.vs}, x{save_vs}",
                "csrw hideleg, zero",
            ]
        )
        lines.extend(gated(body, REPLICA_ATP_GATE) if satp else body)

    test_data.int_regs.return_registers([save_s, save_vs, mask_reg, val_reg])
    return lines


def _vs_csr_tests(test_data: TestData, test_chunks: list[TestChunk]) -> None:
    """CSR accesses from VS-mode."""
    csr_insufficient_priv_tests(
        test_data,
        test_chunks,
        VS_CG,
        M_CSR_RANGES,
        "vscsr",
        "In VS-mode, attempt to read each M-mode CSR.  Should throw illegal instruction",
        mode="VS",
        csrs_per_chunk=CSRS_PER_CHUNK,
    )

    tc = test_data.new_test_chunk(test_chunks)
    tc.section_header = comment_banner(
        "cp_hcsr_virtualinstructionfault, cp_illegalupper",
        "In VS-mode, access each HS and VS H CSR (virtual instruction when the access is legal in HS-mode),\n"
        "and on RV64 each high-half H CSR (illegal instruction)",
    )
    tc.code.append("RVTEST_TSBI_GOTO_VSMODE")
    for csr in HS_VS_CSRS:
        tc.code.extend(_csr_trap_test(test_data, csr, VS_CG, "cp_hcsr_virtualinstructionfault"))
    for csr in H_UPPER_CSRS:
        tc.code.extend(_csr_trap_test(test_data, csr, VS_CG, "cp_illegalupper"))
    tc.code.append("RVTEST_TSBI_GOTO_SMODE")

    tc = test_data.new_test_chunk(test_chunks)
    tc.section_header = comment_banner("cp_nonreplica", "In VS-mode, access each S CSR that has no VS replica")
    tc.code.append("RVTEST_TSBI_GOTO_VSMODE")
    for csr in S_UNREPLICATED_CSRS:
        tc.code.extend(gated(csr_access_test(test_data, (csr.operand, csr.mask), VS_CG, "cp_nonreplica"), csr.gate))
    tc.code.extend(
        [
            *xstatus_sd_tests(test_data, "sstatus", VSSTATUS_CG, "cp_vsstatus_sd_write"),
            "RVTEST_TSBI_GOTO_SMODE",
        ]
    )

    # TODO: also access scountinhibit with menvcfg.CDE = 1 (virtual instruction) once Sail implements menvcfg.CDE
    tc = test_data.new_test_chunk(test_chunks)
    tc.section_header = comment_banner(
        "cp_scountinhibit_vs", "In VS-mode, access scountinhibit with menvcfg.CDE = 0 (illegal instruction)"
    )
    tc.code.extend(
        [
            "RVTEST_TSBI_GOTO_VSMODE",
            *_csr_trap_test(test_data, SCOUNTINHIBIT, VS_CG, "cp_scountinhibit_vs"),
            "RVTEST_TSBI_GOTO_SMODE",
        ]
    )


def _vu_csr_tests(test_data: TestData, test_chunks: list[TestChunk]) -> None:
    """CSR accesses from VU-mode, as the U suite's from U-mode."""
    csr_insufficient_priv_tests(
        test_data,
        test_chunks,
        VU_CG,
        NONUSER_CSR_RANGES,
        "vucsr",
        "In VU-mode, attempt to read each CSR that is not a user CSR.  Should throw illegal or virtual instruction",
        mode="VU",
        csrs_per_chunk=CSRS_PER_CHUNK,
    )
    csr_ro_write_tests(
        test_data, test_chunks, VU_CG, USER_RO_CSR_RANGES, "vucsr_ro", mode="VU", csrs_per_chunk=CSRS_PER_CHUNK
    )


def _xret_tests(test_data: TestData) -> list[str]:
    """Illegal mret and sret, and sret from HS-mode and VS-mode.

    After each sret, a read of mscratch traps and the trap record shows the mode reached.
    """
    lines = [
        comment_banner("cp_mret_illegal, cp_sret_illegal", "Execute mret in HS, VS and VU modes and sret in VU-mode"),
        test_data.add_testcase("hs", "cp_mret_illegal", INST_CG),
        "mret",
        "RVTEST_TSBI_GOTO_VSMODE",
        test_data.add_testcase("vs", "cp_mret_illegal", INST_CG),
        "mret",
        "RVTEST_TSBI_GOTO_VUMODE",
        test_data.add_testcase("vu", "cp_mret_illegal", INST_CG),
        "mret",
        test_data.add_testcase("vu", "cp_sret_illegal", INST_CG),
        "sret",
        "RVTEST_TSBI_GOTO_SMODE",
        *sret_tests(test_data, INST_CG, "cp_sret_hs", "s"),
    ]
    save_reg, temp_reg, rd = test_data.int_regs.get_registers(3)
    lines.extend(
        [
            comment_banner(
                "cp_sret_vs",
                "Execute sret in VS-mode with vsstatus.SPP = {0, 1}, vsstatus.SPIE = {0, 1} and\n"
                "hstatus.VTSR = {0, 1}.  VTSR = 1 raises virtual instruction",
            ),
            "RVTEST_TSBI_GOTO_VSMODE",
            f"csrr x{save_reg}, sstatus",
        ]
    )
    for vtsr in (0, 1):
        lines.append(f"RVTEST_TSBI_CSR_{'SET' if vtsr else 'CLEAR'}(CSR_HSTATUS, HSTATUS_VTSR)")
        for spp in (0, 1):
            for spie in (0, 1):
                name = f"spp{spp}_spie{spie}_vtsr{vtsr}"
                bits = " | ".join(bit for bit, on in (("SSTATUS_SPP", spp), ("SSTATUS_SPIE", spie)) if on) or "0"
                lines.extend(
                    [
                        f"LI(x{temp_reg}, SSTATUS_SPP | SSTATUS_SPIE)",
                        f"csrc sstatus, x{temp_reg}",
                        f"LI(x{temp_reg}, {bits})",
                        f"csrs sstatus, x{temp_reg}",
                        f"LA(x{temp_reg}, 1f)",
                        f"csrw sepc, x{temp_reg}",
                        test_data.add_testcase(name, "cp_sret_vs", INST_CG),
                        "sret",
                        "1:",
                        f"LI(x{rd}, 42)",
                        test_data.add_testcase(f"{name}_mode", "cp_sret_vs", INST_CG),
                        f"csrr x{rd}, mscratch",
                        write_sigupd(rd, test_data),
                        "RVTEST_TSBI_GOTO_VSMODE",
                        f"LI(x{temp_reg}, SSTATUS_SPP | SSTATUS_SPIE | SSTATUS_SIE)",
                        test_data.add_testcase(f"{name}_vsstatus", "cp_sret_vs", INST_CG),
                        f"csrr x{rd}, sstatus",
                        f"and x{rd}, x{rd}, x{temp_reg}",
                        write_sigupd(rd, test_data),
                    ]
                )
    lines.extend(
        [
            "RVTEST_TSBI_CSR_CLEAR(CSR_HSTATUS, HSTATUS_VTSR)",
            f"csrw sstatus, x{save_reg}",
            "RVTEST_TSBI_GOTO_SMODE",
        ]
    )
    test_data.int_regs.return_registers([save_reg, temp_reg, rd])
    return lines


def _hfence_tests(test_data: TestData) -> list[str]:
    """hfence.vvma and hfence.gvma in each mode the suite reaches, with mstatus.TVM = 0 and hstatus.VTVM = 0."""
    lines = [
        comment_banner(
            "cp_hfence",
            "Execute hfence.vvma and hfence.gvma in HS-mode (no trap), VS-mode and VU-mode (virtual instruction)\n"
            "and U-mode (illegal instruction)",
        )
    ]
    for mode in ("hs", "vs", "vu", "u"):
        if mode != "hs":
            lines.append(f"RVTEST_TSBI_GOTO_{mode.upper()}MODE")
        for instr in ("hfence.vvma", "hfence.gvma"):
            lines.extend([test_data.add_testcase(f"{mode}_{instr.replace('.', '_')}", "cp_hfence", INST_CG), instr])
    lines.append("RVTEST_TSBI_GOTO_SMODE")
    return lines


def _vtvm_tests(test_data: TestData) -> list[str]:
    """hstatus.VTVM = {0, 1}: sfence.vma and satp accesses in VS-mode, and hfence.vvma in HS-mode.

    VTVM = 1 makes the VS-mode accesses raise virtual instruction, but does not trap hfence.vvma.  vsatp stays Bare.
    """
    rd = test_data.int_regs.get_register()
    lines = [
        comment_banner(
            "cp_vtvm_sfence, cp_vtvm_satp, cp_vtvm_hfence_vvma",
            "With hstatus.VTVM = {0, 1}, execute hfence.vvma in HS-mode, and sfence.vma, csrr satp and csrw satp\n"
            "in VS-mode.  VTVM = 1 raises virtual instruction for the VS-mode instructions only",
        )
    ]
    for vtvm in (0, 1):
        lines.extend(
            [
                f"LI(x{rd}, HSTATUS_VTVM)",
                f"{'csrs' if vtvm else 'csrc'} hstatus, x{rd}",
                test_data.add_testcase(f"hs_hfence_vvma_vtvm{vtvm}", "cp_vtvm_hfence_vvma", INST_CG),
                "hfence.vvma",
                "RVTEST_TSBI_GOTO_VSMODE",
                test_data.add_testcase(f"vs_sfence_vma_vtvm{vtvm}", "cp_vtvm_sfence", INST_CG),
                "sfence.vma",
                f"LI(x{rd}, 42)",
                test_data.add_testcase(f"vs_csrr_satp_vtvm{vtvm}", "cp_vtvm_satp", INST_CG),
                f"csrr x{rd}, satp",
                write_sigupd(rd, test_data),
                test_data.add_testcase(f"vs_csrw_satp_vtvm{vtvm}", "cp_vtvm_satp", INST_CG),
                "csrw satp, zero",
                "RVTEST_TSBI_GOTO_SMODE",
            ]
        )
    lines.extend([f"LI(x{rd}, HSTATUS_VTVM)", f"csrc hstatus, x{rd}"])
    test_data.int_regs.return_register(rd)
    return lines


@add_priv_test_generator(
    "H",
    required_extensions=["H"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_h(test_data: TestData) -> list[TestChunk]:
    """Generate tests for the H hypervisor testsuite."""
    test_chunks: list[TestChunk] = []
    hcsr_tests(test_data, test_chunks, [*H_HS_CSRS, *H_VS_CSRS], HS_CG)

    tc = test_data.new_test_chunk(test_chunks, "hscsr_fields")
    tc.code.extend(
        [
            *_vgein_tests(test_data),
            *xcause_write_tests(test_data, "vscause", VSCAUSE_CG),
            *xtval_value_tests(test_data, "vstval", HS_CG),
        ]
    )

    tc = test_data.new_test_chunk(test_chunks, "replica")
    tc.code.extend(_replica_tests(test_data))

    _vs_csr_tests(test_data, test_chunks)
    _vu_csr_tests(test_data, test_chunks)

    tc = test_data.new_test_chunk(test_chunks, "inst")
    tc.code.extend(
        [
            *hlv_tests(test_data, tc, INST_CG, ("hs", "u")),
            *_xret_tests(test_data),
            *_hfence_tests(test_data),
            *_vtvm_tests(test_data),
        ]
    )

    tc = test_data.new_test_chunk(test_chunks, "trap")
    tc.code.extend(
        [
            comment_banner(
                "cp_guest_page_fault",
                "In HS-mode, hlv.w and hsv.w raise guest-page faults on the final translation and on an\n"
                "implicit VS-stage access; the trap records hold htval and htinst",
            ),
            *guest_page_fault_tests(test_data, INST_CG),
        ]
    )

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks


_ZICNTR_CG = "H_Zicntr_cg"

# (coverpoint, mode, CSR walked, mcounteren, hcounteren, scounteren)
_ZICNTR_WALKS: list[tuple[str, Mode, str, Counteren | None, Counteren | None, Counteren | None]] = [
    ("cp_scounteren_access_hs", "S", "scounteren", "ones", "zeros", None),
    ("cp_mcounteren_access_vs", "VS", "mcounteren", None, "ones", "zeros"),
    ("cp_mcounteren_access_vs_h0", "VS", "mcounteren", None, "zeros", "zeros"),
    ("cp_hcounteren_access_vs", "VS", "hcounteren", "ones", None, "zeros"),
    ("cp_scounteren_access_u", "U", "scounteren", "ones", "zeros", None),
    ("cp_mcounteren_access_vu", "VU", "mcounteren", None, "ones", "ones"),
    ("cp_mcounteren_access_vu_hs0", "VU", "mcounteren", None, "zeros", "zeros"),
    ("cp_hcounteren_access_vu", "VU", "hcounteren", "ones", None, "ones"),
    ("cp_scounteren_access_vu", "VU", "scounteren", "ones", "ones", None),
]


@add_priv_test_generator(
    "H",
    required_extensions=["H", "Zicntr"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_h_zicntr(test_data: TestData) -> list[TestChunk]:
    """Generate tests for H_Zicntr coverpoints: counter access and htimedelta in HS, VS, U and VU modes.

    The HS-mode handler takes the illegal- and virtual-instruction traps from U, VS and VU (hedeleg = 0).  A counter
    read in VS or VU raises illegal instruction when its mcounteren bit is 0, whatever hcounteren and scounteren hold,
    and virtual instruction when only hcounteren (or, in VU, scounteren) forbids it.
    """
    test_chunks: list[TestChunk] = []
    for index, (coverpoint, mode, csr, mcounteren, hcounteren, scounteren) in enumerate(_ZICNTR_WALKS):
        presets = ", ".join(
            f"{name} = all {setting}"
            for name, setting in (("mcounteren", mcounteren), ("hcounteren", hcounteren), ("scounteren", scounteren))
            if setting
        )
        tc = test_data.new_test_chunk(test_chunks, "Zicntr" if index == 0 else None)
        tc.code.extend(
            [
                *([f"RVTEST_TSBI_GOTO_{mode}MODE"] if mode != "S" else []),
                *counteren_walk_tests(
                    test_data,
                    _ZICNTR_CG,
                    coverpoint,
                    f"Write walking 1s and 0s to {csr} with {presets}.  Read from corresponding counter and\n"
                    f"counterh in {'HS' if mode == 'S' else mode}-mode",
                    csrs=[csr],
                    mode=mode,
                    mcounteren=mcounteren,
                    hcounteren=hcounteren,
                    scounteren=scounteren,
                ),
                *(["RVTEST_TSBI_GOTO_SMODE"] if mode != "S" else []),
            ]
        )

    tc = test_data.new_test_chunk(test_chunks)
    ones_reg = test_data.int_regs.get_register()
    tc.code.extend(
        [
            "RVTEST_TSBI_CSR_WRITE(CSR_MCOUNTEREN, -1)",
            f"LI(x{ones_reg}, -1)",
            f"csrw hcounteren, x{ones_reg}",
            f"csrw scounteren, x{ones_reg}",
        ]
    )
    test_data.int_regs.return_register(ones_reg)
    modes: tuple[Mode, ...] = ("S", "VS", "U", "VU")
    for mode in modes:
        tc.code.extend(htimedelta_tests(test_data, _ZICNTR_CG, mode))
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks


@add_priv_test_generator(
    "H",
    required_extensions=["H", "F"],
    march_extensions=["F", "D", "Zfa"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_h_f(test_data: TestData) -> list[TestChunk]:
    """Generate H_F tests: the floating-point CSRs and instructions in VS and VU modes against vsstatus.FS and sstatus.FS."""

    test_chunks: list[TestChunk] = []

    tc = test_data.begin_test_chunk("F_vs")
    tc.code.extend(
        [
            "RVTEST_TSBI_GOTO_VSMODE",
            *gen_fcsr_tests(test_data, "VS", "H_F_cg"),
            "RVTEST_TSBI_GOTO_SMODE",
        ]
    )
    test_chunks.append(test_data.end_test_chunk())

    tc = test_data.begin_test_chunk("F_vu")
    tc.code.extend(
        [
            "RVTEST_TSBI_GOTO_VUMODE",
            *gen_fcsr_tests(test_data, "VU", "H_F_cg"),
            "RVTEST_TSBI_GOTO_SMODE",
        ]
    )
    test_chunks.append(test_data.end_test_chunk())

    return test_chunks


@add_priv_test_generator(
    "H",
    required_extensions=["H", "Zve32x"],
    extra_defines=[
        "#define RVTEST_VECTOR",
        "#define RVTEST_SEW 0",
        "#define VDSEW 0",
        "#define BOOT_TO_SMODE",
    ],
)
def make_h_v(test_data: TestData) -> list[TestChunk]:
    """Generate H_V tests: vector CSRs, vset* behavior, vill, vstart and vsstatus.VS/sstatus.VS in VS and VU modes."""
    test_chunks: list[TestChunk] = []

    for tc in gen_v_tests(test_data, "VS", "H_V_cg"):
        tc.code = ["RVTEST_TSBI_GOTO_VSMODE", *tc.code, "RVTEST_TSBI_GOTO_SMODE"]
        test_chunks.append(tc)

    for tc in gen_v_tests(test_data, "VU", "H_V_cg"):
        tc.code = ["RVTEST_TSBI_GOTO_VUMODE", *tc.code, "RVTEST_TSBI_GOTO_SMODE"]
        test_chunks.append(tc)

    return test_chunks


@add_priv_test_generator(
    "H",
    required_extensions=["H", "Zve32f"],
    extra_defines=[
        "#define RVTEST_VECTOR",
        "#define RVTEST_SEW 0",
        "#define VDSEW 0",
        "#define BOOT_TO_SMODE",
    ],
)
def make_h_vf(test_data: TestData) -> list[TestChunk]:
    """Generate H_VF tests: vector floating-point instructions against vsstatus.FS and sstatus.FS in VS and VU modes."""
    test_chunks: list[TestChunk] = []

    for tc in gen_vf_tests(test_data, "VS", "H_VF_cg"):
        tc.code = ["RVTEST_TSBI_GOTO_VSMODE", *tc.code, "RVTEST_TSBI_GOTO_SMODE"]
        test_chunks.append(tc)

    for tc in gen_vf_tests(test_data, "VU", "H_VF_cg"):
        tc.code = ["RVTEST_TSBI_GOTO_VUMODE", *tc.code, "RVTEST_TSBI_GOTO_SMODE"]
        test_chunks.append(tc)

    return test_chunks
