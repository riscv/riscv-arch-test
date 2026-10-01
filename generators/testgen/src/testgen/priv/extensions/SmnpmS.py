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
    MODE_GUARDS,
    MODES,
    PMM_CONFIGS,
    TAG_GROUPS,
    data_page,
    data_slvl_tables,
    generate_csr_write_tests,
    generate_fault_address_tests,
    generate_instruction_sweep_tests,
    generate_jalr_tests,
    generate_misaligned_tests,
    generate_mxr_tests,
    generate_sign_extension_tests,
    map_pm_hi_page,
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
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_smnpms(test_data: TestData) -> list[TestChunk]:
    chunks = []
    for mode in MODES:
        for pmm, pmlen, label in PMM_CONFIGS:
            for part, uppers in enumerate(TAG_GROUPS, 1):
                tc = test_data.begin_test_chunk(split_name=f"{mode}_{label}_part{part}")
                tc.code = _smnpms_chunk(mode, pmm, pmlen, label, part, uppers, test_data)
                chunks.append(test_data.end_test_chunk())
    return chunks


def _smnpms_chunk(
    mode: str, pmm: int, pmlen: int, label: str, part: int, uppers: list[int], test_data: TestData
) -> list[str]:
    """One satp mode, one menvcfg.PMM setting and one tag group, probed from S-mode.

    Part 1 also carries the probes that are not part of the instruction sweep.
    """
    guard, is_bare = MODE_GUARDS[mode], mode == "bare"
    prefix = f"{label}_{mode}"
    lines = [] if not guard else [f"#ifdef {guard}"]
    lines.extend([".pushsection .data", *data_page("pm_lo_page")])
    if not is_bare:
        lines.extend([*data_page("pm_hi_page"), *data_slvl_tables(mode)])
    lines.append(".popsection")
    if not is_bare:
        lines.extend([*map_pm_hi_page(mode, user=False), *satp_setup(mode, test_data)])

    lines.extend(
        [
            *set_pmm_field("menvcfg", pmm, pmlen, test_data, tsbi=True),
            *generate_instruction_sweep_tests(prefix, test_data, COVERGROUP, uppers),
        ]
    )
    if part == 1:
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
    lines.extend([*set_pmm_field("menvcfg", 0b00, 0, test_data, tsbi=True), *set_mxr(False, test_data)])
    if not is_bare:
        lines.extend(satp_clear())
    if guard:
        lines.append(f"#endif // {guard}")
    return lines
