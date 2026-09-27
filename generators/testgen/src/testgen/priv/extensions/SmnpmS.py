##################################
# priv/extensions/SmnpmS.py
#
# SmnpmS privileged extension test generator.
# Author : David Harris, Umer Shahid & Ammarah Wakeel email:ammarahwakeel9@gmail.com (UET, JULY 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZpmCommon import (
    _LEAF_PERMS_S,
    HIGH_VA,
    MODE_GUARDS,
    MODES,
    PMM_CONFIGS,
    _pte_chain_asm,
    data_page,
    data_slvl_tables,
    generate_csr_write_tests,
    generate_fault_address_tests,
    generate_instruction_sweep_tests,
    generate_jalr_tests,
    generate_misaligned_tests,
    generate_mxr_tests,
    generate_sign_extension_tests,
    satp_clear,
    satp_setup,
    set_mxr,
    set_pmm_field,
)
from testgen.priv.registry import add_priv_test_generator

COVERGROUP = "SmnpmS_cg"


@add_priv_test_generator(
    "SmnpmS",
    required_extensions=["Smnpm", "S"],
    march_extensions=["I", "A", "F", "D", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz"],
    extra_defines=["#define BOOT_TO_SMODE", "#define RVTEST_ALLOW_OOS_FETCH_EPC"],
)
def make_smnpms(test_data: TestData) -> list[TestChunk]:
    chunks = []
    for mode in MODES:
        tc = test_data.begin_test_chunk(split_name=mode)
        guard, is_bare = MODE_GUARDS[mode], mode == "bare"
        lines = [] if not guard else [f"#ifdef {guard}"]
        lines.extend([".pushsection .data", *data_page("pm_lo_page")])
        if not is_bare:
            lines.extend([*data_page("pm_hi_page"), *data_slvl_tables(mode)])
        lines.extend(
            [
                ".popsection",
            ]
        )
        if not is_bare:
            lines.extend(
                [
                    *_pte_chain_asm(mode, HIGH_VA[mode], "pm_hi_page", _LEAF_PERMS_S),
                    *satp_setup(mode, test_data),
                ]
            )

        for pmm, pmlen, label in PMM_CONFIGS:
            prefix = f"{label}_{mode}"
            lines.extend(
                [
                    *set_pmm_field("menvcfg", pmm, pmlen, test_data, tsbi=True),
                    *generate_instruction_sweep_tests(prefix, test_data, COVERGROUP),
                ]
            )
            if not is_bare:
                lines.extend(generate_sign_extension_tests(prefix, mode, test_data, COVERGROUP))
            lines.extend(
                [
                    *generate_misaligned_tests(prefix, test_data, COVERGROUP),
                    *generate_jalr_tests(prefix, test_data, COVERGROUP, mxr=0),
                    *generate_fault_address_tests(prefix, test_data, COVERGROUP),
                    *generate_mxr_tests(prefix, test_data, COVERGROUP),
                    *generate_jalr_tests(prefix, test_data, COVERGROUP, mxr=1),
                    *set_mxr(False, test_data),
                    *generate_csr_write_tests(prefix, pmlen, test_data, COVERGROUP, ["sepc", "sscratch"]),
                ]
            )

        lines.extend(
            [
                *set_pmm_field("menvcfg", 0b00, 0, test_data, tsbi=True),
                *set_mxr(False, test_data),
            ]
        )
        if not is_bare:
            lines.extend(satp_clear())
        if guard:
            lines.append(f"#endif // {guard}")
        tc.code = lines
        chunks.append(test_data.end_test_chunk())
    return chunks
