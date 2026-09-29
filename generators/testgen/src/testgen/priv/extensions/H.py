##################################
# H.py
#
# H hypervisor extension tests that run in HS, VS, U and VU modes.
# David_Harris@hmc.edu 24 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""H hypervisor extension test generator.

The suite boots to HS-mode.  The HS-mode handler takes traps from U, VS and VU (hedeleg = 0).
Tests that need mstatus.TVM = 1 are in HSm.
"""

from testgen.asm.csr import csr_access_test, gen_csr_read_sigupd
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.HCommon import (
    H_HS_CSRS,
    H_M_CSRS,
    H_VS_CSRS,
    HSTATUS_MASK,
    REPLICA_ATP_GATE,
    REPLICAS,
    HCsr,
    gated,
    guest_page_fault_tests,
    hcsr_tests,
    hlv_tests,
    replica_read,
    replica_write,
    sret_tests,
)
from testgen.priv.extensions.S import scause_write_tests, sstatus_sd_tests
from testgen.priv.registry import add_priv_test_generator

HS_CG = "H_hscsr_cg"
VS_CG = "H_vscsr_cg"
U_CG = "H_ucsr_cg"
INST_CG = "H_inst_cg"

# The accesses of csraccesses: csrrw all 1s, csrrw 0s, csrrs all 1s, csrrc all 1s, csrr
CSR_OPS = [
    ("csrrw1", "csrrw x{rd}, {csr}, x{ones}"),
    ("csrrw0", "csrrw x{rd}, {csr}, x0"),
    ("csrrs_all", "csrrs x{rd}, {csr}, x{ones}"),
    ("csrrc_all", "csrrc x{rd}, {csr}, x{ones}"),
    ("csrr", "csrr x{rd}, {csr}"),
]

# HS and VS H CSRs, which VS-mode and VU-mode cannot access
HS_VS_CSRS = [*H_HS_CSRS, HCsr("hgeip"), *H_VS_CSRS, HCsr("vscause")]
# High halves of H CSRs, illegal on RV64, where the assembler knows only their numbers
H_UPPER_CSRS = [
    HCsr(f"CSR_{name}", gate="__riscv_xlen == 64") for name in ("HEDELEGH", "HTIMEDELTAH", "HENVCFGH", "VSTIMECMPH")
]
S_REPLICATED_CSRS = [
    HCsr(name) for name in ("sstatus", "sie", "stvec", "sscratch", "sepc", "scause", "stval", "sip", "satp")
]
S_UNREPLICATED_CSRS = [
    HCsr("scounteren"),
    HCsr("senvcfg", gate="defined(S1P12P0_OR_LATER_SUPPORTED)"),
    HCsr("scountinhibit", gate="defined(SSCCFG_SUPPORTED)"),
]


def _csr_trap_ops(test_data: TestData, csr: HCsr, covergroup: str, coverpoint: str) -> list[str]:
    """Perform each CSR_OPS access to a CSR that is expected to trap; rd must keep its known value."""
    ones, rd = test_data.int_regs.get_registers(2)
    lines = [*csr.setup, f"LI(x{ones}, -1)"]
    for op, fmt in CSR_OPS:
        lines.extend(
            [
                f"LI(x{rd}, 42)",
                test_data.add_testcase(f"{csr.name}_{op}", coverpoint, covergroup),
                fmt.format(rd=rd, csr=csr.name, ones=ones),
                write_sigupd(rd, test_data),
            ]
        )
    test_data.int_regs.return_registers([ones, rd])
    return gated([*lines, *csr.restore], csr.gate)


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


def _replica_tests(test_data: TestData) -> list[str]:
    """S CSRs and their VS replicas accessed from HS-mode and from VS-mode, and read back in M-mode."""
    save_s, save_vs, mask_reg, val_reg = test_data.int_regs.get_registers(4)
    lines = [
        comment_banner(
            "cp_replica (HS-mode)",
            "M-mode writes different values to an S CSR and its VS replica.  HS-mode reads both, writes new\n"
            "values and reads them back.  M-mode reads both again",
        )
    ]
    for rep in REPLICAS:
        mask = [f"LI(x{mask_reg}, {rep.mask:#x})"] if rep.mask else []
        body = [
            "RVTEST_TSBI_GOTO_MMODE",
            f"LI(x{val_reg}, MIP_VS_MASK)",
            f"csrw hideleg, x{val_reg}",
            f"csrr x{save_s}, {rep.s}",
            f"csrr x{save_vs}, {rep.vs}",
            *replica_write(test_data, rep, rep.s, rep.values[0], val_reg),
            *replica_write(test_data, rep, rep.vs, rep.values[1], val_reg),
            *mask,
            "RVTEST_TSBI_GOTO_SMODE",
            *replica_read(test_data, rep, rep.s, mask_reg, f"hs_{rep.s}_init", HS_CG),
            *replica_read(test_data, rep, rep.vs, mask_reg, f"hs_{rep.vs}_init", HS_CG),
            *replica_write(test_data, rep, rep.s, rep.values[2], val_reg),
            *replica_write(test_data, rep, rep.vs, rep.values[3], val_reg),
            *replica_read(test_data, rep, rep.s, mask_reg, f"hs_{rep.s}", HS_CG),
            *replica_read(test_data, rep, rep.vs, mask_reg, f"hs_{rep.vs}", HS_CG),
            "RVTEST_TSBI_GOTO_MMODE",
            *replica_read(test_data, rep, rep.s, mask_reg, f"hs_{rep.s}_m", HS_CG),
            *replica_read(test_data, rep, rep.vs, mask_reg, f"hs_{rep.vs}_m", HS_CG),
            f"csrw {rep.s}, x{save_s}",
            f"csrw {rep.vs}, x{save_vs}",
            "csrw hideleg, zero",
            "RVTEST_TSBI_GOTO_SMODE",
        ]
        lines.extend(gated(body, REPLICA_ATP_GATE) if rep.s == "satp" else body)

    lines.append(
        comment_banner(
            "cp_replica (VS-mode)",
            "M-mode writes different values to an S CSR and its VS replica.  VS-mode reads the S CSR name,\n"
            "writes a new value and reads it back, which reaches the replica.  M-mode reads both.  VS-mode\n"
            "ecalls go to M-mode so that no trap into HS-mode changes sepc, scause, stval or sstatus",
        )
    )
    for rep in REPLICAS:
        # vsatp stays Bare while VS-mode runs
        values = (
            ("rvtest_Sroot_pg_tbl", None, None) if rep.s == "satp" else (rep.values[0], rep.values[1], rep.values[3])
        )
        s_init, vs_init, vs_new = values
        body = [
            "RVTEST_TSBI_GOTO_MMODE",
            f"LI(x{val_reg}, 1 << CAUSE_VIRTUAL_SUPERVISOR_ECALL)",
            f"csrc medeleg, x{val_reg}",
            f"LI(x{val_reg}, MIP_VS_MASK)",
            f"csrw hideleg, x{val_reg}",
            f"csrr x{save_s}, {rep.s}",
            f"csrr x{save_vs}, {rep.vs}",
            *replica_write(test_data, rep, rep.s, s_init, val_reg),
            *replica_write(test_data, rep, rep.vs, vs_init, val_reg),
            *([f"LI(x{mask_reg}, {rep.mask:#x})"] if rep.mask else []),
            "RVTEST_TSBI_GOTO_VSMODE",
            *replica_read(test_data, rep, rep.s, mask_reg, f"vs_{rep.s}_init", VS_CG),
            *replica_write(test_data, rep, rep.s, vs_new, val_reg),
            *replica_read(test_data, rep, rep.s, mask_reg, f"vs_{rep.s}", VS_CG),
            "RVTEST_TSBI_GOTO_MMODE",
            *replica_read(test_data, rep, rep.s, mask_reg, f"vs_{rep.s}_m", VS_CG),
            *replica_read(test_data, rep, rep.vs, mask_reg, f"vs_{rep.vs}_m", VS_CG),
            f"csrw {rep.s}, x{save_s}",
            f"csrw {rep.vs}, x{save_vs}",
            "csrw hideleg, zero",
            f"LI(x{val_reg}, 1 << CAUSE_VIRTUAL_SUPERVISOR_ECALL)",
            f"csrs medeleg, x{val_reg}",
            "RVTEST_TSBI_GOTO_SMODE",
        ]
        lines.extend(gated(body, REPLICA_ATP_GATE) if rep.s == "satp" else body)

    test_data.int_regs.return_registers([save_s, save_vs, mask_reg, val_reg])
    return lines


def _vs_csr_tests(test_data: TestData, test_chunks: list[TestChunk]) -> None:
    """CSR accesses from VS-mode."""
    tc = test_data.new_test_chunk(test_chunks, "vscsr")
    tc.section_header = comment_banner(
        "cp_hcsr_inaccessible, cp_hcsr_virtualinstructionfault, cp_illegalupper",
        "In VS-mode, access each Machine-level H CSR (illegal instruction), each HS and VS H CSR (virtual\n"
        "instruction when the access is legal in HS-mode), and on RV64 each high-half H CSR (illegal)",
    )
    tc.code.append("RVTEST_TSBI_GOTO_VSMODE")
    for csr in H_M_CSRS:
        tc.code.extend(_csr_trap_ops(test_data, csr, VS_CG, "cp_hcsr_inaccessible"))
    for csr in HS_VS_CSRS:
        tc.code.extend(_csr_trap_ops(test_data, csr, VS_CG, "cp_hcsr_virtualinstructionfault"))
    for csr in H_UPPER_CSRS:
        tc.code.extend(_csr_trap_ops(test_data, csr, VS_CG, "cp_illegalupper"))
    tc.code.append("RVTEST_TSBI_GOTO_SMODE")

    tc = test_data.new_test_chunk(test_chunks)
    tc.section_header = comment_banner("cp_nonreplica", "In VS-mode, access each S CSR that has no VS replica")
    tc.code.append("RVTEST_TSBI_GOTO_VSMODE")
    for csr in S_UNREPLICATED_CSRS:
        tc.code.extend(gated(csr_access_test(test_data, (csr.name, csr.mask), VS_CG, "cp_nonreplica"), csr.gate))
    tc.code.extend([*sstatus_sd_tests(test_data, VS_CG, "cp_vsstatus_sd_write", uxl=False), "RVTEST_TSBI_GOTO_SMODE"])


def _user_csr_tests(test_data: TestData, test_chunks: list[TestChunk], mode: str) -> None:
    """Every H CSR and S CSR access traps from U-mode and VU-mode."""
    tc = test_data.new_test_chunk(test_chunks, f"{mode}csr")
    tc.section_header = comment_banner(
        "cp_hcsr_inaccessible, cp_hcsr_inaccessible_u, cp_hcsr_virtualinstructionfault, cp_illegalupper, cp_scsr",
        f"In {mode.upper()}-mode, access each H CSR, each S CSR, and on RV64 each high-half H CSR.  Each\n"
        "access raises illegal instruction, or virtual instruction from VU-mode when HS-mode could perform it",
    )
    tc.code.append(f"RVTEST_TSBI_GOTO_{mode.upper()}MODE")
    for csr in H_M_CSRS:
        tc.code.extend(_csr_trap_ops(test_data, csr, U_CG, "cp_hcsr_inaccessible"))
    for csr in HS_VS_CSRS:
        coverpoint = "cp_hcsr_virtualinstructionfault" if mode == "vu" else "cp_hcsr_inaccessible_u"
        tc.code.extend(_csr_trap_ops(test_data, csr, U_CG, coverpoint))
    for csr in H_UPPER_CSRS:
        tc.code.extend(_csr_trap_ops(test_data, csr, U_CG, "cp_illegalupper"))
    for csr in [*S_REPLICATED_CSRS, *S_UNREPLICATED_CSRS]:
        tc.code.extend(_csr_trap_ops(test_data, csr, U_CG, "cp_scsr"))
    tc.code.append("RVTEST_TSBI_GOTO_SMODE")


def _xret_tests(test_data: TestData) -> list[str]:
    """Illegal mret and sret, and sret from HS-mode and VS-mode.

    After each sret, a read of mscratch traps into HS-mode and the trap record shows the mode reached.
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


@add_priv_test_generator(
    "H",
    required_extensions=["H"],
    extra_defines=["#define BOOT_TO_SMODE"],
    # VS and VU traps need the visible trap handler
    params=["TIME_CSR_IMPLEMENTED: true"],
)
def make_h(test_data: TestData) -> list[TestChunk]:
    """Generate tests for the H hypervisor testsuite."""
    test_chunks: list[TestChunk] = []
    hcsr_tests(test_data, test_chunks, [*H_HS_CSRS, *H_VS_CSRS], HS_CG)

    tc = test_data.new_test_chunk(test_chunks)
    tc.section_header = comment_banner(
        "cp_hcsr_inaccessible", "Access each Machine-level H CSR from HS-mode; each raises illegal instruction"
    )
    for csr in H_M_CSRS:
        tc.code.extend(_csr_trap_ops(test_data, csr, HS_CG, "cp_hcsr_inaccessible"))

    tc = test_data.new_test_chunk(test_chunks, "hscsr_fields")
    tc.code.extend([*_vgein_tests(test_data), *scause_write_tests(test_data, "vscause", HS_CG)])

    tc = test_data.new_test_chunk(test_chunks, "replica")
    tc.code.extend(_replica_tests(test_data))

    _vs_csr_tests(test_data, test_chunks)
    _user_csr_tests(test_data, test_chunks, "u")
    _user_csr_tests(test_data, test_chunks, "vu")

    tc = test_data.new_test_chunk(test_chunks, "inst")
    tc.code.extend([*hlv_tests(test_data, tc, INST_CG, ("hs", "u")), *_xret_tests(test_data)])

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
