##################################
# HSm.py
#
# H hypervisor extension tests that run in M-mode, or that need M-mode to take their traps.
# David_Harris@hmc.edu 24 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""HSm hypervisor extension test generator.

The suite boots to M-mode and delegates nothing, so the M-mode handler takes every trap.  The
mstatus.TVM tests run in lower modes but live here because the HS-mode trap handler reads satp,
vsatp and hgatp, which trap in HS-mode when TVM = 1.
"""

from testgen.asm.csr import gen_csr_read_sigupd
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.HCommon import (
    H_HS_CSRS,
    H_M_CSRS,
    H_VS_CSRS,
    REPLICA_ATP_GATE,
    REPLICAS,
    gated,
    guest_page_fault_tests,
    hcsr_tests,
    hlv_tests,
    replica_read,
    replica_write,
    sret_tests,
)
from testgen.priv.registry import add_priv_test_generator

CSR_CG = "HSm_mcsr_cg"
TVM_CG = "HSm_tvm_cg"
INST_CG = "HSm_inst_cg"


def _replica_tests(test_data: TestData) -> list[str]:
    """Write different values to each S CSR and its VS replica, then read both back."""
    save_s, save_vs, mask_reg, val_reg = test_data.int_regs.get_registers(4)
    lines = [
        comment_banner("cp_replica", "Write different values to each S CSR and its VS replica, then read both"),
        f"LI(x{val_reg}, MIP_S_MASK)",
        f"csrw mideleg, x{val_reg}    # sie and sip show only delegated interrupts",
        f"LI(x{val_reg}, MIP_VS_MASK)",
        f"csrw hideleg, x{val_reg}    # vsie and vsip show only delegated interrupts",
    ]
    for rep in REPLICAS:
        body = [
            f"csrr x{save_s}, {rep.s}",
            f"csrr x{save_vs}, {rep.vs}",
            *([f"LI(x{mask_reg}, {rep.mask:#x})"] if rep.mask else []),
            *replica_write(test_data, rep, rep.s, rep.values[0], val_reg),
            *replica_write(test_data, rep, rep.vs, rep.values[1], val_reg),
            *replica_read(test_data, rep, rep.s, mask_reg, rep.s, CSR_CG),
            *replica_read(test_data, rep, rep.vs, mask_reg, rep.vs, CSR_CG),
            f"csrw {rep.s}, x{save_s}",
            f"csrw {rep.vs}, x{save_vs}",
        ]
        lines.extend(gated(body, REPLICA_ATP_GATE if rep.s == "satp" else None))
    # Boot delegates nothing
    lines.extend(["csrw mideleg, zero", "csrw hideleg, zero"])
    test_data.int_regs.return_registers([save_s, save_vs, mask_reg, val_reg])
    return lines


def _mtvala_tests(test_data: TestData) -> list[str]:
    """With H, mtval is not read-only zero."""
    save_reg, check_reg = test_data.int_regs.get_registers(2)
    lines = [
        comment_banner("cp_mtvala", "Write all 1s to mtval; it must not read back as zero"),
        f"csrr x{save_reg}, mtval",
        f"LI(x{check_reg}, -1)",
        test_data.add_testcase("ones", "cp_mtvala", CSR_CG),
        f"csrw mtval, x{check_reg}",
        f"csrr x{check_reg}, mtval",
        f"snez x{check_reg}, x{check_reg}",
        write_sigupd(check_reg, test_data),
        f"csrw mtval, x{save_reg}",
    ]
    test_data.int_regs.return_registers([save_reg, check_reg])
    return lines


def _tvm_tests(test_data: TestData) -> list[str]:
    """satp/hgatp accesses and fences in each mode with mstatus.TVM and hstatus.VTVM."""
    temp_reg, rd = test_data.int_regs.get_registers(2)

    def tvm_bits(tvm: int, vtvm: int | None = None) -> list[str]:
        """Write mstatus.TVM and, unless vtvm is None, hstatus.VTVM from M-mode."""
        lines = [f"LI(x{temp_reg}, MSTATUS_TVM)", f"{'csrs' if tvm else 'csrc'} mstatus, x{temp_reg}"]
        if vtvm is not None:
            lines.extend([f"LI(x{temp_reg}, HSTATUS_VTVM)", f"{'csrs' if vtvm else 'csrc'} hstatus, x{temp_reg}"])
        return lines

    lines = [
        comment_banner("cp_tvm_hs", "Read and write satp and hgatp in HS-mode with mstatus.TVM = 0, 1.  TVM = 1 traps")
    ]
    for tvm in (0, 1):
        lines.extend([*tvm_bits(tvm), "RVTEST_TSBI_GOTO_SMODE"])
        for csr in ("satp", "hgatp"):
            lines.extend(
                [
                    f"LI(x{rd}, 42)",
                    test_data.add_testcase(f"{csr}_read_tvm{tvm}", "cp_tvm_hs", TVM_CG),
                    f"csrr x{rd}, {csr}",
                    write_sigupd(rd, test_data),
                    test_data.add_testcase(f"{csr}_write_tvm{tvm}", "cp_tvm_hs", TVM_CG),
                    f"csrw {csr}, zero",
                ]
            )
        lines.append("RVTEST_TSBI_GOTO_MMODE")

    lines.append(
        comment_banner(
            "cp_tvm_vs",
            "Read and write satp in VS-mode with mstatus.TVM = 0, 1 and hstatus.VTVM = 0, 1.\n"
            "VTVM = 1 raises virtual instruction; TVM does not affect VS-mode",
        )
    )
    for tvm in (0, 1):
        for vtvm in (0, 1):
            lines.extend(
                [
                    *tvm_bits(tvm, vtvm),
                    "RVTEST_TSBI_GOTO_VSMODE",
                    f"LI(x{rd}, 42)",
                    test_data.add_testcase(f"satp_read_tvm{tvm}_vtvm{vtvm}", "cp_tvm_vs", TVM_CG),
                    f"csrr x{rd}, satp",
                    write_sigupd(rd, test_data),
                    test_data.add_testcase(f"satp_write_tvm{tvm}_vtvm{vtvm}", "cp_tvm_vs", TVM_CG),
                    "csrw satp, zero",
                    "RVTEST_TSBI_GOTO_MMODE",
                ]
            )

    lines.append(
        comment_banner(
            "cp_hfence, cp_sfence",
            "Execute hfence.vvma, hfence.gvma and sfence.vma in M, HS, VS, U and VU modes with\n"
            "mstatus.TVM = 0, 1 and hstatus.VTVM = 0, 1",
        )
    )
    for tvm in (0, 1):
        for vtvm in (0, 1):
            lines.extend(tvm_bits(tvm, vtvm))
            for mode in ("m", "s", "vs", "u", "vu"):
                suffix = f"{mode}_tvm{tvm}_vtvm{vtvm}"
                lines.extend(
                    [
                        *([] if mode == "m" else [f"RVTEST_TSBI_GOTO_{mode.upper()}MODE"]),
                        test_data.add_testcase(f"hfence_vvma_{suffix}", "cp_hfence", TVM_CG),
                        "hfence.vvma",
                        test_data.add_testcase(f"hfence_gvma_{suffix}", "cp_hfence", TVM_CG),
                        "hfence.gvma",
                        test_data.add_testcase(f"sfence_vma_{suffix}", "cp_sfence", TVM_CG),
                        "sfence.vma",
                        *([] if mode == "m" else ["RVTEST_TSBI_GOTO_MMODE"]),
                    ]
                )
    lines.extend(tvm_bits(0, 0))
    test_data.int_regs.return_registers([temp_reg, rd])
    return lines


def _mret_tests(test_data: TestData) -> list[str]:
    """mret from M-mode.  In a lower mode, a read of mscratch traps and the trap record shows the mode."""
    save_reg, save_h_reg, mpv_reg, temp_reg, rd = test_data.int_regs.get_registers(5)
    lines = [
        comment_banner(
            "cp_mret_m",
            "Execute mret with mstatus.MPP = {M, S, U}, MPV = {0, 1} and MPIE = {0, 1}.  With MPP = M, V stays 0",
        ),
        f"csrr x{save_reg}, mstatus",
        "#if __riscv_xlen == 64",
        f"LI(x{mpv_reg}, MSTATUS_MPV)",
        "#else",
        f"csrr x{save_h_reg}, mstatush",
        f"LI(x{mpv_reg}, MSTATUSH_MPV)",
        "#endif",
    ]
    for mpp, mpp_bits in ((3, "MPP_MMODE"), (1, "MPP_SMODE"), (0, None)):
        for mpv in (0, 1):
            for mpie in (0, 1):
                name = f"mpp{mpp}_mpv{mpv}_mpie{mpie}"
                bits = " | ".join(bit for bit in (mpp_bits, "MSTATUS_MPIE" if mpie else None) if bit) or "0"
                mpv_op = "csrs" if mpv else "csrc"
                lines.extend(
                    [
                        f"LI(x{temp_reg}, MSTATUS_MPP | MSTATUS_MPIE)",
                        f"csrc mstatus, x{temp_reg}",
                        f"LI(x{temp_reg}, {bits})",
                        f"csrs mstatus, x{temp_reg}",
                        "#if __riscv_xlen == 64",
                        f"{mpv_op} mstatus, x{mpv_reg}",
                        "#else",
                        f"{mpv_op} mstatush, x{mpv_reg}",
                        "#endif",
                        f"LA(x{temp_reg}, 1f)",
                        f"csrw mepc, x{temp_reg}",
                        test_data.add_testcase(name, "cp_mret_m", INST_CG),
                        "mret",
                        "1:",
                    ]
                )
                if mpp != 3:
                    lines.extend(
                        [
                            f"LI(x{rd}, 42)",
                            test_data.add_testcase(f"{name}_mode", "cp_mret_m", INST_CG),
                            f"csrr x{rd}, mscratch",
                            write_sigupd(rd, test_data),
                            "RVTEST_TSBI_GOTO_MMODE",
                        ]
                    )
                lines.extend(
                    [
                        test_data.add_testcase(f"{name}_mstatus", "cp_mret_m", INST_CG),
                        gen_csr_read_sigupd(rd, ("mstatus", None), test_data),
                        "#if __riscv_xlen == 32",
                        test_data.add_testcase(f"{name}_mstatush", "cp_mret_m", INST_CG),
                        gen_csr_read_sigupd(rd, ("mstatush", None), test_data),
                        "#endif",
                    ]
                )
    lines.extend([f"csrw mstatus, x{save_reg}", "#if __riscv_xlen == 32", f"csrw mstatush, x{save_h_reg}", "#endif"])
    test_data.int_regs.return_registers([save_reg, save_h_reg, mpv_reg, temp_reg, rd])
    return lines


@add_priv_test_generator(
    "HSm",
    required_extensions=["Sm", "H"],
    extra_defines=["#define BOOT_TO_MMODE"],
    # VS and VU traps need the visible trap handler
    params=["TIME_CSR_IMPLEMENTED: true"],
)
def make_hsm(test_data: TestData) -> list[TestChunk]:
    """Generate tests for the HSm hypervisor testsuite."""
    test_chunks: list[TestChunk] = []
    hcsr_tests(test_data, test_chunks, [*H_M_CSRS, *H_HS_CSRS, *H_VS_CSRS], CSR_CG)

    tc = test_data.new_test_chunk(test_chunks, "replica")
    tc.code.extend([*_replica_tests(test_data), *_mtvala_tests(test_data)])

    tc = test_data.new_test_chunk(test_chunks, "tvm")
    tc.code.extend(_tvm_tests(test_data))

    tc = test_data.new_test_chunk(test_chunks, "inst")
    tc.code.extend(
        [
            *hlv_tests(test_data, tc, INST_CG, ("m",)),
            *_mret_tests(test_data),
            *sret_tests(test_data, INST_CG, "cp_sret_m", "m"),
        ]
    )

    tc = test_data.new_test_chunk(test_chunks, "trap")
    tc.code.extend(
        [
            comment_banner(
                "cp_guest_page_fault",
                "In M-mode, hlv.w and hsv.w raise guest-page faults on the final translation and on an\n"
                "implicit VS-stage access; the trap records hold mtval2 and mtinst",
            ),
            *guest_page_fault_tests(test_data, INST_CG),
        ]
    )

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
