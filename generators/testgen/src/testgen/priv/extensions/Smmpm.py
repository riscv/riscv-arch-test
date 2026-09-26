##################################
# priv/extensions/Smmpm.py
#
# Smmpm privileged extension test generator.
# Author : Umer Shahid & Ammarah Wakeel email:ammarahwakeel9@gmail.com (UET, JULY 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZpmCommon import (
    PMM_CONFIGS,
    _mprv_img_tables,
    alloc_pm_regs_paired,
    build_data_only_u_map_asm,
    free_pm_regs,
    generate_csr_write_tests,
    generate_fault_address_tests,
    generate_instruction_sweep_tests,
    generate_jalr_tests,
    generate_misaligned_tests,
    generate_mprv_tests,
    generate_mxr_tests,
    generate_xlen_change_tests,
    jalr_pad_asm,
    mprv_data_section,
    set_mxr,
    set_pmm_field,
)
from testgen.priv.registry import add_priv_test_generator

COVERGROUP = "Smmpm_cg"
_CSR_TARGETS = ["mepc", "mscratch"]
_MSTATUS_UXL_SHIFT = 32
_MSTATUS_SXL_SHIFT = 34


@add_priv_test_generator(
    "Smmpm",
    required_extensions=["Smmpm"],
    march_extensions=["I", "A", "F", "D", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz"],
    extra_defines=["#define BOOT_TO_MMODE", "#define RVTEST_ALLOW_OOS_FETCH_EPC"],
)
def make_smmpm(test_data: TestData) -> list[TestChunk]:
    # Build the sv39 data-only U-map ASM once, before regs claims the whole
    # register pool, so building it here avoids the register exhaustion.
    sv39_data_map = build_data_only_u_map_asm("sv39", _mprv_img_tables("sv39"), test_data)

    regs = alloc_pm_regs_paired(test_data)
    tc = test_data.begin_test_chunk()
    lines = [
        *mprv_data_section(),
        comment_banner(
            "Smmpm pointer masking -- M-mode only",
            "mseccfg.PMM is programmed from M-mode; every probe also runs in M-mode.",
        ),
        "",
        *jalr_pad_asm(regs),
    ]
    for pmm, pmlen, label in PMM_CONFIGS:
        prefix = f"{label}_mmode"
        lines.extend(
            [
                comment_banner(f"PMM={pmm:#04b} (PMLEN={pmlen}), M-mode"),
                *set_pmm_field("mseccfg", pmm, pmlen, regs.tmp),
                "#ifdef S_SUPPORTED",
                *set_mxr(False, regs.tmp, "mstatus"),
                "#endif // S_SUPPORTED",
                f"LA(x{regs.base}, pm_lo_page)",
                *generate_instruction_sweep_tests(prefix, test_data, regs, COVERGROUP),
                *generate_misaligned_tests(prefix, test_data, regs, COVERGROUP),
                *generate_jalr_tests(prefix, test_data, regs, COVERGROUP),
                *generate_fault_address_tests(prefix, test_data, regs, COVERGROUP),
                "#ifdef S_SUPPORTED",
                *generate_mxr_tests(prefix, test_data, regs, COVERGROUP, status_csr="mstatus"),
                *set_mxr(False, regs.tmp, "mstatus"),
                "#endif // S_SUPPORTED",
                *generate_csr_write_tests(prefix, pmlen, test_data, regs, COVERGROUP, _CSR_TARGETS),
            ]
        )

    # Writing SXL or UXL to 32 must clear menvcfg.PMM, which governs S (SXL) or U without S (UXL).
    checks = [
        ("#ifdef S_SUPPORTED", "UDB_SXLEN_32", "sxl", "cp_pmm_sxl_clear", "menvcfg", _MSTATUS_SXL_SHIFT),
        ("#ifndef S_SUPPORTED", "UDB_UXLEN_32", "uxl", "cp_pmm_uxl_clear", "menvcfg", _MSTATUS_UXL_SHIFT),
    ]
    for mode_guard, xlen_guard, tag, cp, pmm_csr, status_shift in checks:
        lines.extend(["#ifdef U_SUPPORTED", mode_guard, f"#ifdef {xlen_guard}"])
        for pmm, pmlen, label in PMM_CONFIGS:
            lines.extend(
                [
                    *set_pmm_field(pmm_csr, pmm, pmlen, regs.tmp),
                    *generate_xlen_change_tests(
                        f"{label}_{tag}",
                        test_data,
                        regs,
                        cp=cp,
                        cg=COVERGROUP,
                        pmm_csr=pmm_csr,
                        status_csr="mstatus",
                        status_shift=status_shift,
                    ),
                ]
            )
        lines.extend(
            [
                *set_pmm_field(pmm_csr, 0b00, 0, regs.tmp),
                f"#endif // {xlen_guard}",
                f"#endif // {mode_guard.split()[1]}",
                "#endif // U_SUPPORTED",
            ]
        )

    lines.extend(
        [
            # MPRV test using nested loop structure from testplan
            # Only tests Bare and Sv39 modes with limited upper bit patterns
            *generate_mprv_tests(test_data, regs, COVERGROUP, sv39_data_map),
            *set_pmm_field("mseccfg", 0b00, 0, regs.tmp),
            "#ifdef S_SUPPORTED",
            *set_mxr(False, regs.tmp, "mstatus"),
            "#endif // S_SUPPORTED",
        ]
    )
    tc.code = lines
    chunks = [test_data.end_test_chunk()]
    free_pm_regs(test_data, regs)
    return chunks
