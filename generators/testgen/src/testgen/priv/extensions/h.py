##################################
# priv/extensions/h.py
#
# H privileged extension test generator.
# nchulani@g.hmc.edu Feb 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""H privileged extension test generator."""

from testgen.asm.csr import gen_csr_read_sigupd, gen_csr_write_sigupd
from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _emit_cp_hcsr_access_writeall1s(
    test_data: TestData,
    csrs: list[str],
    description: str,
) -> list[str]:
    """Emit cp_hcsr_access write-all-1s/readback checks for a list of CSRs."""
    covergroup = "H_mcsr_cg"
    coverpoint = "cp_hcsr_access"

    save_reg, write_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])
    lines = [comment_banner("cp_hcsr_access", description)]

    for csr in csrs:
        lines.extend(
            [
                f"\tCSRR(x{save_reg}, {csr})      # save {csr}",
                f"\tLI(x{write_reg}, -1)          # all 1s",
                test_data.add_testcase(f"{csr}_writeall1s", coverpoint, covergroup),
                f"test_{test_data.test_count}:",
                gen_csr_write_sigupd(write_reg, csr, test_data),
                f"\tCSRW({csr}, x{save_reg})      # restore {csr}",
                "",
            ]
        )

    test_data.int_regs.return_registers([save_reg, write_reg])
    return lines


def _generate_cp_hcsr_access_machine_csr_reads(test_data: TestData) -> list[str]:
    """Generate cp_hcsr_access machine H-CSR read checks (mtinst/mtval2)."""
    covergroup = "H_mcsr_cg"
    coverpoint = "cp_hcsr_access"
    csrs = ["mtinst", "mtval2"]

    lines = [
        comment_banner(
            "cp_hcsr_access",
            "Tests executed in M-mode: machine H-extension CSRs (mtinst/mtval2) read checks",
        )
    ]

    check_reg = test_data.int_regs.get_register(exclude_regs=[0])
    for csr in csrs:
        lines.extend(
            [
                test_data.add_testcase(f"{csr}_read", coverpoint, covergroup),
                f"test_{test_data.test_count}:",
                gen_csr_read_sigupd(check_reg, csr, test_data),
            ]
        )
    test_data.int_regs.return_registers([check_reg])
    return lines


def _generate_cp_hcsr_access_hs_vs_writable(test_data: TestData) -> list[str]:
    """Generate cp_hcsr_access write-all-1s/readback checks for writable HS/VS CSRs."""
    csrs = [
        "hstatus",
        "hedeleg",
        "hideleg",
        "hie",
        "hcounteren",
        "hgeie",
        "henvcfg",
        "hgatp",
        "hvip",
        "htinst",
        "htimedelta",
        "htval",
        "vsstatus",
        "vsie",
        "vsip",
        "vstvec",
        "vsscratch",
        "vsepc",
        "vscause",
        "vstval",
        "vsatp",
    ]
    return _emit_cp_hcsr_access_writeall1s(
        test_data,
        csrs,
        "Tests executed in M-mode: HS/VS H-extension CSRs write-all-1s/readback checks",
    )


def _generate_cp_hcsr_access_readonly_reads(test_data: TestData) -> list[str]:
    """Generate cp_hcsr_access read-only checks for HIP/HGEIP."""
    covergroup = "H_mcsr_cg"
    coverpoint = "cp_hcsr_access"
    csrs = ["hip", "hgeip"]

    lines = [
        comment_banner(
            "cp_hcsr_access",
            "Tests executed in M-mode: read-only H-extension CSR checks (hip/hgeip)",
        )
    ]

    check_reg = test_data.int_regs.get_register(exclude_regs=[0])
    for csr in csrs:
        lines.extend(
            [
                test_data.add_testcase(f"{csr}_read", coverpoint, covergroup),
                f"test_{test_data.test_count}:",
                gen_csr_read_sigupd(check_reg, csr, test_data),
            ]
        )

    test_data.int_regs.return_registers([check_reg])
    return lines


def _generate_cp_hcsr_access_rv32_highhalf(test_data: TestData) -> list[str]:
    """Generate cp_hcsr_access RV32 high-half H-CSR write-all-1s/readback checks."""
    csrs = ["htimedeltah", "henvcfgh"]
    lines = [
        comment_banner(
            "cp_hcsr_access",
            "Tests executed in M-mode: RV32-only high-half HS H-extension CSRs",
        ),
        "#if __riscv_xlen == 32",
    ]
    lines.extend(
        _emit_cp_hcsr_access_writeall1s(
            test_data,
            csrs,
            "RV32 high-half write-all-1s/readback checks",
        )
    )
    lines.append("#endif")
    return lines


@add_priv_test_generator("H", required_extensions=["H"])
def make_h(test_data: TestData) -> list[str]:
    """Generate tests for H hypervisor extension."""
    lines: list[str] = []

    # Hypervisor - H - US.csv
    # Tests executed in M-mode (H_mcsr_cg)
    lines.extend(_generate_cp_hcsr_access_machine_csr_reads(test_data))
    lines.extend(_generate_cp_hcsr_access_hs_vs_writable(test_data))
    lines.extend(_generate_cp_hcsr_access_readonly_reads(test_data))
    lines.extend(_generate_cp_hcsr_access_rv32_highhalf(test_data))

    return lines
