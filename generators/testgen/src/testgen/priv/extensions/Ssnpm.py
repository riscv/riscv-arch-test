##################################
# priv/extensions/Ssnpm.py
#
# Ssnpm privileged extension test generator.
# Author : David Harris, Umer Shahid & Ammarah Wakeel  email:ammarahwakeel9@gmail.com (UET, JULY 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZpmCommon import (
    HIGH_VA,
    LEVELS_BELOW_ROOT,
    MODE_GUARDS,
    MODES,
    PMM_CONFIGS,
    _pte_chain_asm,
    alloc_pm_regs_paired,
    build_finegrained_text_map_asm,
    csr_op,
    data_page,
    data_slvl_tables,
    free_pm_regs,
    generate_fault_address_tests,
    generate_instruction_sweep_tests,
    generate_jalr_tests,
    generate_misaligned_tests,
    generate_mxr_tests,
    generate_sign_extension_tests,
    generate_xlen_change_tests,
    jalr_pad_asm,
    satp_clear,
    satp_setup,
    set_mxr,
    set_pmm_field,
)
from testgen.priv.registry import add_priv_test_generator

COVERGROUP = "Ssnpm_cg"


@add_priv_test_generator(
    "Ssnpm",
    required_extensions=["Ssnpm"],
    march_extensions=["I", "A", "F", "D", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz"],
    extra_defines=["#define BOOT_TO_SMODE", "#define RVTEST_ALLOW_OOS_FETCH_EPC"],
)
def make_ssnpm(test_data: TestData) -> list[TestChunk]:
    # Build the fine-grained U-text/data page-table setup for every non-bare
    # mode FIRST, while the register pool is still full.
    finegrained_maps: dict[str, list[str]] = {}
    for mode in MODES:
        if mode == "bare":
            continue
        img_tables = [f"pm_img_slvl{i}_pg_tbl" for i in range(LEVELS_BELOW_ROOT[mode] - 1, -1, -1)]
        finegrained_maps[mode] = build_finegrained_text_map_asm(mode, img_tables, test_data)

    regs = alloc_pm_regs_paired(test_data)

    chunks = []
    for mode in MODES:
        tc = test_data.begin_test_chunk(split_name=mode)
        guard, is_bare = MODE_GUARDS[mode], mode == "bare"
        lines = [] if not guard else [f"#ifdef {guard}"]
        lines.extend([".pushsection .data", *data_page("pm_lo_page")])
        if not is_bare:
            lines.extend(
                [
                    *data_page("pm_hi_page"),
                    *data_slvl_tables(mode),
                    *data_slvl_tables(mode, label_prefix="pm_img_slvl"),
                ]
            )
        lines.extend(
            [
                ".popsection",
                ".p2align 12",
                "pm_utext_begin:",
                *jalr_pad_asm(regs),
                "# sstatus.SUM = 1: S-mode setup code touches the U-accessible data pages",
                *csr_op("csrs", "sstatus", "SSTATUS_SUM", regs.tmp),
            ]
        )
        if not is_bare:
            lines.extend(["", *finegrained_maps[mode], "", *_pte_chain_asm(mode, HIGH_VA[mode], "pm_hi_page")])

        # S-mode cannot fetch from the U-marked test text once satp is on, so U-mode
        # turns satp on and off itself and writes senvcfg/sstatus through T-SBI.
        lines.append("RVTEST_TSBI_GOTO_UMODE")
        if not is_bare:
            lines.extend(satp_setup(mode, regs, tsbi=True))

        for pmm, pmlen, label in PMM_CONFIGS:
            prefix = f"{label}_{mode}"
            lines.extend(
                [
                    comment_banner(f"PMM={pmm:#04b} (PMLEN={pmlen}), satp={mode.upper()}"),
                    *set_pmm_field("senvcfg", pmm, pmlen, regs.tmp, tsbi=True),
                    *set_mxr(False, regs.tmp, tsbi=True),
                    f"LA(x{regs.base}, pm_lo_page)",
                    *generate_instruction_sweep_tests(prefix, test_data, regs, COVERGROUP),
                ]
            )
            if not is_bare:
                lines.extend(generate_sign_extension_tests(prefix, mode, test_data, regs, COVERGROUP))
            lines.extend(
                [
                    *generate_misaligned_tests(prefix, test_data, regs, COVERGROUP),
                    *generate_jalr_tests(prefix, test_data, regs, COVERGROUP, mxr=0),
                    *generate_fault_address_tests(prefix, test_data, regs, COVERGROUP),
                    *generate_mxr_tests(prefix, test_data, regs, COVERGROUP, tsbi=True),
                    *generate_jalr_tests(prefix, test_data, regs, COVERGROUP, mxr=1),
                    *set_mxr(False, regs.tmp, tsbi=True),
                ]
            )

        if not is_bare:
            lines.extend(satp_clear(regs, tsbi=True))
        lines.append("RVTEST_TSBI_GOTO_SMODE")
        for pmm, pmlen, label in PMM_CONFIGS:
            prefix = f"{label}_{mode}"
            lines.extend(
                [
                    *set_pmm_field("senvcfg", pmm, pmlen, regs.tmp),
                    *generate_xlen_change_tests(
                        prefix,
                        test_data,
                        regs,
                        cp="cp_pmm_uxl_clear",
                        cg=COVERGROUP,
                        pmm_csr="senvcfg",
                        status_csr="sstatus",
                        status_shift=32,
                        ifdef_guard="UDB_UXLEN_32",
                    ),
                ]
            )

        lines.extend(
            [
                *set_pmm_field("senvcfg", 0b00, 0, regs.tmp),
                *set_mxr(False, regs.tmp),
                ".p2align 12",
                "pm_utext_end:",
            ]
        )
        if guard:
            lines.append(f"#endif // {guard}")
        tc.code = lines
        chunks.append(test_data.end_test_chunk())

    free_pm_regs(test_data, regs)
    return chunks
