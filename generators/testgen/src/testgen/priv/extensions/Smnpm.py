##################################
# priv/extensions/Smnpm.py
#
# Smnpm privileged extension test generator.
# Author : David Harris, Umer Shahid & Ammarah Wakeel email:ammarahwakeel9@gmail.com (UET, JULY 2026)
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
    PMLEN_BY_PMM,
    SPLITS,
    build_4k_image_map,
    data_page,
    data_slvl_tables,
    generate_csr_write_tests,
    generate_edge_case_tests,
    generate_instruction_sweep_tests,
    generate_mprv_lower_mode_tests,
    generate_sign_extension_tests,
    generate_zicfiss_tests,
    map_pm_hi_page,
    mprv_data_section,
    satp_clear,
    satp_setup,
    set_mxr,
    set_pmm_field,
    set_sse,
    ss_data_page,
)
from testgen.priv.registry import add_priv_test_generator

COVERGROUP_S = "Smnpm_S_cg"
COVERGROUP_SSM = "Smnpm_SSm_cg"
COVERGROUP_U = "Smnpm_U_cg"
COVERGROUP_USM = "Smnpm_USm_cg"


# ── S-mode probes from M-mode-configured pointer masking (group S) ─────────


def _smnpms_sweep(test_data: TestData, pmm: int) -> list[TestChunk]:
    """Build the chunks for one menvcfg.PMM setting, across every satp mode."""
    pmlen = PMLEN_BY_PMM[pmm]
    label = f"pmm{pmm:02b}"
    chunks = []
    for mode in MODES:
        # Each PMM setting is split into three files to keep every test under 100k instructions.
        # sweep_lowtags and sweep_hightags run every load, store, AMO, CBO and vector instruction through
        # a tagged pointer: the first with tags that leave bit 63 clear, the second with tags that set it.
        # edgecases holds the remaining checks, such as misaligned accesses, JALR, access faults and MXR.
        for split, uppers in SPLITS:
            tc = test_data.begin_test_chunk(f"S_{mode}_{label}_{split}")
            guard = MODE_GUARDS[mode]
            if guard:
                tc.raw_data.append(f"#ifdef {guard}")
            tc.raw_data.extend(data_page("pm_lo_page"))
            if mode != "bare":
                tc.raw_data.extend([*data_page("pm_hi_page"), *data_slvl_tables(mode), *ss_data_page(mode)])
            if guard:
                tc.raw_data.append(f"#endif // {guard}")
            tc.code = _smnpms_chunk(mode, pmm, pmlen, label, split, uppers, test_data)
            chunks.append(test_data.end_test_chunk())
    return chunks


# One generator per PMLEN. The header params select the file only when the config supports that PMLEN.
@add_priv_test_generator(
    "Smnpm",
    required_extensions=["Smnpm", "S"],
    march_extensions=["I", "A", "F", "D", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz", "Zicfiss"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_smnpms_pmm00(test_data: TestData) -> list[TestChunk]:
    return _smnpms_sweep(test_data, 0b00)


@add_priv_test_generator(
    "Smnpm",
    required_extensions=["Smnpm", "S"],
    march_extensions=["I", "A", "F", "D", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz", "Zicfiss"],
    extra_defines=["#define BOOT_TO_SMODE"],
    params=["SUPPORTED_PMLEN_SMNPM: 7"],
)
def make_smnpms_pmm10(test_data: TestData) -> list[TestChunk]:
    return _smnpms_sweep(test_data, 0b10)


@add_priv_test_generator(
    "Smnpm",
    required_extensions=["Smnpm", "S"],
    march_extensions=["I", "A", "F", "D", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz", "Zicfiss"],
    extra_defines=["#define BOOT_TO_SMODE"],
    params=["SUPPORTED_PMLEN_SMNPM: 16"],
)
def make_smnpms_pmm11(test_data: TestData) -> list[TestChunk]:
    return _smnpms_sweep(test_data, 0b11)


def _smnpms_chunk(
    mode: str, pmm: int, pmlen: int, label: str, split: str, uppers: list[int], test_data: TestData
) -> list[str]:
    """One satp mode, one menvcfg.PMM setting and one test split, probed from S-mode.

    The edge-case file carries the probes that are not part of the instruction sweep.
    """
    guard, is_bare = MODE_GUARDS[mode], mode == "bare"
    prefix = f"{label}_{mode}"
    lines = [] if not guard else [f"#ifdef {guard}"]
    if not is_bare:
        lines.extend(
            [
                *map_pm_hi_page(mode, user=False),
                # A shadow-stack page needs a 4 KiB leaf, so the identity superpage is split.
                "#ifdef ZICFISS_SUPPORTED",
                *build_4k_image_map(mode, IMAGE_TABLES, [], test_data, ss_page_user=False),
                "#endif // ZICFISS_SUPPORTED",
                *satp_setup(mode, test_data),
                *set_sse("menvcfg", True, test_data, tsbi=True),
            ]
        )

    lines.extend(
        [
            *set_pmm_field("menvcfg", pmm, pmlen, test_data, tsbi=True),
            *generate_instruction_sweep_tests(prefix, test_data, COVERGROUP_S, uppers),
        ]
    )
    # A shadow-stack instruction always faults with satp Bare, so pointer masking has nothing to act on.
    if not is_bare:
        lines.extend(generate_zicfiss_tests(prefix, test_data, COVERGROUP_S, uppers))
    if split == EDGE_CASES:
        if not is_bare:
            lines.extend(generate_sign_extension_tests(prefix, mode, test_data, COVERGROUP_S))
        lines.extend(
            [
                *generate_edge_case_tests(prefix, test_data, COVERGROUP_S, status_csr="sstatus"),
                *generate_csr_write_tests(prefix, pmlen, test_data, COVERGROUP_S, ["sepc", "sscratch"]),
            ]
        )
    lines.extend([*set_pmm_field("menvcfg", 0b00, 0, test_data, tsbi=True), *set_mxr(False, test_data)])
    if not is_bare:
        lines.extend([*set_sse("menvcfg", False, test_data, tsbi=True), *satp_clear()])
    if guard:
        lines.append(f"#endif // {guard}")
    return lines


# ── M-mode half of SmnpmS: MPRV=1 with MPP=S (group Sm) ─────────────────────


@add_priv_test_generator(
    "Smnpm",
    required_extensions=["Smnpm", "S", "Sm"],
    march_extensions=["I", "A", "F", "D", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_smnpmssm(test_data: TestData) -> list[TestChunk]:
    """M-mode half of Smnpm_S: MPRV=1 with MPP=S.

    The probes run in M-mode but take S-mode's effective privilege, so menvcfg.PMM --
    the CSR Smnpm adds -- decides whether the pointer is masked, and mseccfg.PMM does
    not apply. That pairing is why these cases cannot live in the Smmpm suite: a hart
    with Smmpm alone has no menvcfg.PMM to program.
    """
    tc = test_data.begin_test_chunk("SSm")
    tc.raw_data.extend(mprv_data_section())
    tc.code = [
        *generate_mprv_lower_mode_tests(
            test_data,
            COVERGROUP_SSM,
            mpp="PRV_S",
            pmm_csr="menvcfg",
            cp="cp_pm_mprv_mpp_s",
        ),
    ]
    return [test_data.end_test_chunk()]


# ── U-mode probes from M-mode-configured pointer masking, no S-mode (group U) ─


def _smnpmu_sweep(test_data: TestData, pmm: int) -> list[TestChunk]:
    """Build the chunks for one menvcfg.PMM setting, probed from U-mode."""
    pmlen = PMLEN_BY_PMM[pmm]
    label = f"pmm{pmm:02b}"
    chunks = []
    # Each PMM setting is split into three files to keep every test under 100k instructions.
    # sweep_lowtags and sweep_hightags run every load, store, AMO, CBO and vector instruction through
    # a tagged pointer: the first with tags that leave bit 63 clear, the second with tags that set it.
    # edgecases holds the remaining checks, such as misaligned accesses, JALR, access faults and MXR.
    for split, uppers in SPLITS:
        tc = test_data.begin_test_chunk(f"U_{label}_{split}")
        tc.raw_data.extend(data_page("pm_lo_page"))
        prefix = f"{label}_bare"
        lines = [
            comment_banner(f"PMM={pmm:#04b} (PMLEN={pmlen}), physical addresses, {split}"),
            *set_pmm_field("menvcfg", pmm, pmlen, test_data, tsbi=True),
            *generate_instruction_sweep_tests(prefix, test_data, COVERGROUP_U, uppers),
        ]
        if split == EDGE_CASES:
            lines.extend(generate_edge_case_tests(prefix, test_data, COVERGROUP_U))
        lines.extend(set_pmm_field("menvcfg", 0b00, 0, test_data, tsbi=True))
        tc.code = lines
        chunks.append(test_data.end_test_chunk())
    return chunks


# One generator per PMLEN. The header params select the file only when the config supports that PMLEN.
@add_priv_test_generator(
    "Smnpm",
    required_extensions=["Smnpm", "U"],
    forbidden_extensions=["S"],
    march_extensions=["I", "A", "F", "D", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz"],
)
def make_smnpmu_pmm00(test_data: TestData) -> list[TestChunk]:
    return _smnpmu_sweep(test_data, 0b00)


@add_priv_test_generator(
    "Smnpm",
    required_extensions=["Smnpm", "U"],
    forbidden_extensions=["S"],
    march_extensions=["I", "A", "F", "D", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz"],
    params=["SUPPORTED_PMLEN_SMNPM: 7"],
)
def make_smnpmu_pmm10(test_data: TestData) -> list[TestChunk]:
    return _smnpmu_sweep(test_data, 0b10)


@add_priv_test_generator(
    "Smnpm",
    required_extensions=["Smnpm", "U"],
    forbidden_extensions=["S"],
    march_extensions=["I", "A", "F", "D", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz"],
    params=["SUPPORTED_PMLEN_SMNPM: 16"],
)
def make_smnpmu_pmm11(test_data: TestData) -> list[TestChunk]:
    return _smnpmu_sweep(test_data, 0b11)


# ── M-mode half of SmnpmU: MPRV=1 with MPP=U on a hart without S-mode (group USm) ─


@add_priv_test_generator(
    "Smnpm",
    required_extensions=["Smnpm", "U", "Sm"],
    forbidden_extensions=["S"],
    march_extensions=["I", "A", "F", "D", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_smnpmusm(test_data: TestData) -> list[TestChunk]:
    """M-mode half of SmnpmU: MPRV=1 with MPP=U on a hart without S-mode.

    Without S-mode, menvcfg.PMM (Smnpm), governs U-mode, so it decides
    whether the pointer is masked, and mseccfg.PMM does not apply.
    """
    tc = test_data.begin_test_chunk("USm")
    tc.raw_data.extend(mprv_data_section())
    tc.code = [
        *generate_mprv_lower_mode_tests(
            test_data,
            COVERGROUP_USM,
            mpp="PRV_U",
            pmm_csr="menvcfg",
            cp="cp_pm_mprv_mpp_u",
            s_mode=False,
        ),
    ]
    return [test_data.end_test_chunk()]
