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
    EDGE_CASES,
    IMAGE_TABLES,
    MODE_GUARDS,
    MODES,
    PMM_CONFIGS,
    SPLITS,
    build_4k_image_map,
    csr_op,
    data_page,
    data_slvl_tables,
    generate_edge_case_tests,
    generate_instruction_sweep_tests,
    generate_sign_extension_tests,
    generate_xlen_change_tests,
    generate_zicfiss_tests,
    map_pm_hi_page,
    satp_clear,
    satp_setup,
    set_mxr,
    set_pmm_field,
    set_sse,
    ss_data_page,
)
from testgen.priv.registry import add_priv_test_generator

COVERGROUP = "Ssnpm_cg"


@add_priv_test_generator(
    "Ssnpm",
    required_extensions=["Ssnpm"],
    march_extensions=["I", "A", "F", "D", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz", "Zicfiss"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_ssnpm(test_data: TestData) -> list[TestChunk]:
    chunks = []
    for mode in MODES:
        for pmm, pmlen, label in PMM_CONFIGS:
            # Each PMM setting is split into three files to keep every test under 100k instructions.
            # sweep_lowtags and sweep_hightags run every load, store, AMO, CBO and vector instruction through
            # a tagged pointer: the first with tags that leave bit 63 clear, the second with tags that set it.
            # edgecases holds the remaining checks, such as misaligned accesses, JALR, access faults and MXR.
            for split, uppers in SPLITS:
                tc = test_data.begin_test_chunk(split_name=f"{mode}_{label}_{split}")
                guard = MODE_GUARDS[mode]
                if guard:
                    tc.raw_data.append(f"#ifdef {guard}")
                tc.raw_data.extend(data_page("pm_lo_page"))
                if mode != "bare":
                    tc.raw_data.extend(
                        [
                            *data_page("pm_hi_page"),
                            *data_slvl_tables(mode),
                            *data_slvl_tables(mode, IMAGE_TABLES),
                            *ss_data_page(),
                        ]
                    )
                if guard:
                    tc.raw_data.append(f"#endif // {guard}")
                tc.code = _ssnpm_chunk(mode, pmm, pmlen, label, split, uppers, test_data)
                chunks.append(test_data.end_test_chunk())
    return chunks


def _ssnpm_chunk(
    mode: str, pmm: int, pmlen: int, label: str, split: str, uppers: list[int], test_data: TestData
) -> list[str]:
    """One satp mode, one senvcfg.PMM setting and one test split, probed from U-mode.

    The edge-case file carries the probes that are not part of the instruction sweep.
    """
    guard, is_bare = MODE_GUARDS[mode], mode == "bare"
    prefix = f"{label}_{mode}"
    lines = [] if not guard else [f"#ifdef {guard}"]
    lines.extend(
        [
            ".p2align 12",
            "pm_utext_begin:",
            "# sstatus.SUM = 1: S-mode setup code touches the U-accessible data pages",
            *csr_op("csrs", "sstatus", "SSTATUS_SUM", test_data),
        ]
    )
    if not is_bare:
        lines.extend(
            [
                *set_sse("menvcfg", True, test_data, tsbi=True),
                *set_sse("senvcfg", True, test_data),
                "",
                *build_4k_image_map(
                    mode,
                    IMAGE_TABLES,
                    [
                        ("pm_utext_begin", "pm_utext_end"),
                        ("pm_lo_page", 4096),
                        ("pm_hi_page", 4096),
                        ("rvtest_data_begin", "end_signature"),
                    ],
                    test_data,
                    ss_page_user=True,
                ),
                "",
                *map_pm_hi_page(mode, user=True),
            ]
        )

    # S-mode cannot fetch from the U-marked test text once satp is on, so U-mode
    # turns satp on and off itself and writes senvcfg/sstatus through T-SBI.
    lines.append("RVTEST_TSBI_GOTO_UMODE")
    if not is_bare:
        lines.extend(satp_setup(mode, test_data, tsbi=True))

    lines.extend(
        [
            comment_banner(f"PMM={pmm:#04b} (PMLEN={pmlen}), satp={mode.upper()}, {split}"),
            *set_pmm_field("senvcfg", pmm, pmlen, test_data, tsbi=True),
            *set_mxr(False, test_data, tsbi=True),
            *generate_instruction_sweep_tests(prefix, test_data, COVERGROUP, uppers),
        ]
    )
    # A shadow-stack instruction always faults with satp Bare, so pointer masking has nothing to act on.
    if not is_bare:
        lines.extend(generate_zicfiss_tests(prefix, test_data, COVERGROUP, uppers))
    if split == EDGE_CASES:
        if not is_bare:
            lines.extend(generate_sign_extension_tests(prefix, mode, test_data, COVERGROUP))
        lines.extend(
            generate_edge_case_tests(
                prefix,
                test_data,
                COVERGROUP,
                status_csr="sstatus",
                tsbi=True,
            )
        )

    if not is_bare:
        lines.extend(satp_clear(tsbi=True))
    lines.append("RVTEST_TSBI_GOTO_SMODE")
    if split == EDGE_CASES:
        lines.extend(
            [
                *set_pmm_field("senvcfg", pmm, pmlen, test_data),
                *generate_xlen_change_tests(
                    prefix,
                    test_data,
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
            *set_pmm_field("senvcfg", 0b00, 0, test_data),
            *set_mxr(False, test_data),
        ]
    )
    if not is_bare:
        lines.extend([*set_sse("senvcfg", False, test_data), *set_sse("menvcfg", False, test_data, tsbi=True)])
    lines.extend([".p2align 12", "pm_utext_end:"])
    if guard:
        lines.append(f"#endif // {guard}")
    return lines
