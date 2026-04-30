##################################
# priv/extensions/Ssnpm.py
#
# Ssnpm pointer masking extension test generator.
# ammarahwakeel9@gmail.com (UET) March 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Ssnpm pointer masking extension test generator."""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.constants import INDENT
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator

READ_OPS = ["lb", "lbu", "lh", "lhu", "lw", "lwu", "ld"]
WRITE_OPS = ["sb", "sh", "sw", "sd"]
SATP_MODES = ["bare", "sv39", "sv48", "sv57"]
SATP_VA_MODES = ["sv39", "sv48", "sv57"]  # bare excluded for VA tests
SATP_MODE_ENCODINGS = {"bare": 0, "sv39": 8, "sv48": 9, "sv57": 10}

# senvcfg.PMM bits [33:32] — PMM=10 gives PMLEN=7, PMM=11 gives PMLEN=16
PMM_CONFIGS = [
    (0b10, 7),
    (0b11, 16),
]


def _set_pmm(pmm_val: int, pmm_reg: int, pmm_tmp: int) -> list[str]:
    """Set senvcfg.PMM = pmm_val via read-modify-write from S-mode."""

    return [
        f"CSRR(x{pmm_tmp}, senvcfg)",
        f"LI(x{pmm_reg}, 0x3)",
        f"slli x{pmm_reg}, x{pmm_reg}, 32",
        f"not x{pmm_reg}, x{pmm_reg}",
        f"and x{pmm_tmp}, x{pmm_tmp}, x{pmm_reg}",
        f"LI(x{pmm_reg}, {pmm_val})",
        f"slli x{pmm_reg}, x{pmm_reg}, 32",
        f"or x{pmm_tmp}, x{pmm_tmp}, x{pmm_reg}",
        f"CSRW(senvcfg, x{pmm_tmp})",
    ]


def _set_satp_mode(mode: str, reg: int) -> list[str]:
    """Set satp to the requested paging mode from S-mode."""

    mode_val = SATP_MODE_ENCODINGS[mode]
    if mode == "bare":
        return [
            "CSRW(satp, zero)",
        ]
    return [
        f"LI(x{reg}, {mode_val})",
        f"slli x{reg}, x{reg}, 60",
        f"CSRW(satp, x{reg})",
        "sfence.vma",
    ]


def _asm_ifdef_guard_open(mode: str) -> str:
    guards = {"sv39": "#ifdef SV39", "sv48": "#ifdef SV48", "sv57": "#ifdef SV57"}
    return guards.get(mode, "")


def _asm_ifdef_guard_close(mode: str) -> str:
    return "#endif" if mode in ("sv39", "sv48", "sv57") else ""


PAGE_SIZE = 4096


def _setup_address_regions(addr_a: int, addr_b: int, addr_c: int, tmp: int) -> list[str]:
    """Set addr_a=scratch, addr_b=scratch+4KB, addr_c=scratch+8KB."""
    return [
        "",
        f"LA(x{addr_a}, scratch)",
        f"LI(x{tmp}, {PAGE_SIZE})",
        f"add x{addr_b}, x{addr_a}, x{tmp}",
        f"slli x{tmp}, x{tmp}, 1",
        f"add x{addr_c}, x{addr_a}, x{tmp}",
        "",
    ]


def _generate_pmlen_masking_tests(test_data: TestData) -> list[str]:
    covergroup = "Ssnpm_cg"
    cp_write = "cp_pmlen_masking_write"
    cp_read = "cp_pmlen_masking_read"

    addr_reg, masked_reg, data_reg, tmp_reg, pmm_tmp = test_data.int_regs.get_registers(5, exclude_regs=[0, 2])

    lines = [
        comment_banner(cp_write, " store data to address A"),
        comment_banner(cp_read, " load data from A_masked"),
        "",
    ]

    for pmm_val, pmlen in PMM_CONFIGS:
        upper_mask = ((1 << pmlen) - 1) << (64 - pmlen)

        for satp_mode in SATP_MODES:
            lines.append(_asm_ifdef_guard_open(satp_mode))

            # S-mode setup
            lines.extend(_set_pmm(pmm_val, tmp_reg, pmm_tmp))
            lines.extend(_set_satp_mode(satp_mode, tmp_reg))

            # Enter U-mode
            lines.append("RVTEST_GOTO_LOWER_MODE Umode")

            lines.extend(
                [
                    f"LA(x{addr_reg}, scratch)",
                    f"LI(x{masked_reg}, {upper_mask:#018x})",
                    f"xor x{masked_reg}, x{addr_reg}, x{masked_reg} # A_masked = A with upper bits flipped",
                ]
            )

            for winstr in WRITE_OPS:
                binname = f"pmm_{pmm_val:02b}_{satp_mode}_{winstr}"
                lines.extend(
                    [
                        test_data.add_testcase(binname, cp_write, covergroup),
                        f"LI(x{data_reg}, 0xAB)",
                        f"{winstr} x{data_reg}, 0(x{addr_reg})",
                        "nop",
                    ]
                )

            for rinstr in READ_OPS:
                binname = f"pmm_{pmm_val:02b}_{satp_mode}_{rinstr}"
                lines.extend(
                    [
                        test_data.add_testcase(binname, cp_read, covergroup),
                        f"{rinstr} x{data_reg}, 0(x{masked_reg})        # load from A_masked",
                        "nop",
                        write_sigupd(data_reg, test_data),
                    ]
                )

            lines.extend(
                [
                    "RVTEST_GOTO_MMODE",
                    "RVTEST_GOTO_LOWER_MODE Smode",
                ]
            )
            lines.append(_asm_ifdef_guard_close(satp_mode))
            lines.append("")

    test_data.int_regs.return_registers([addr_reg, masked_reg, data_reg, tmp_reg, pmm_tmp])
    return lines


def _generate_effective_address_tests(test_data: TestData) -> list[str]:
    """Generate cp_effective_address_explicit_write and cp_effective_address_fetch."""
    covergroup = "Ssnpm_cg"
    cp_amo = "cp_effective_address_explicit_write"
    cp_fetch = "cp_effective_address_fetch"

    addr_reg, masked_reg, dest_reg, src_reg, tmp_reg, pmm_tmp = test_data.int_regs.get_registers(6, exclude_regs=[0, 2])

    K = 0x1234

    lines = [
        comment_banner(cp_amo, "Write K=0x1234 to A; AMO on A_masked; verify dest==K and memory updated"),
        comment_banner(cp_fetch, "Fetch: PA_low succeeds; PA_high (masking not applied) faults at PMP"),
        "",
    ]

    amo_word_ops = ["amoadd.w", "amoswap.w", "amoxor.w"]
    amo_double_ops = ["amoadd.d", "amoswap.d", "amoxor.d"]

    amo_word_operands = {
        "amoadd.w": 0x0001,
        "amoswap.w": 0x5678,
        "amoxor.w": 0xFFFF,
    }
    amo_double_operands = {
        "amoadd.d": 0x0001,
        "amoswap.d": 0x5678ABCD,
        "amoxor.d": 0xFFFFFFFF,
    }

    lines.append("#ifdef ZAAMO_SUPPORTED")
    lines.append("")

    for pmm_val, pmlen in PMM_CONFIGS:
        upper_mask = ((1 << pmlen) - 1) << (64 - pmlen)

        for satp_mode in SATP_MODES:
            lines.append(_asm_ifdef_guard_open(satp_mode))

            # S-mode setup
            lines.extend(_set_pmm(pmm_val, tmp_reg, pmm_tmp))
            lines.extend(_set_satp_mode(satp_mode, tmp_reg))
            lines.append("RVTEST_GOTO_LOWER_MODE Umode")

            # Build A and A_masked
            lines.extend(
                [
                    f"LA(x{addr_reg}, scratch)",
                    f"LI(x{masked_reg}, {upper_mask:#018x})",
                    f"xor x{masked_reg}, x{addr_reg}, x{masked_reg}",
                ]
            )

            for amo in amo_word_ops:
                amo_label = amo.replace(".", "_")
                binname = f"pmm_{pmm_val:02b}_{satp_mode}_{amo_label}"
                V = amo_word_operands[amo]

                lines.extend(
                    [
                        test_data.add_testcase(binname, cp_amo, covergroup),
                        f"LI(x{src_reg}, {K})",
                        f"sw x{src_reg}, 0(x{addr_reg})",
                        "nop",
                        f"LI(x{src_reg}, {V})",
                        f"{amo} x{dest_reg}, x{src_reg}, (x{masked_reg})",
                        "nop",
                        write_sigupd(dest_reg, test_data),
                        f"lw x{dest_reg}, 0(x{masked_reg})",
                        "nop",
                        write_sigupd(dest_reg, test_data),
                    ]
                )

            for amo in amo_double_ops:
                amo_label = amo.replace(".", "_")
                binname = f"pmm_{pmm_val:02b}_{satp_mode}_{amo_label}"
                V = amo_double_operands[amo]

                lines.extend(
                    [
                        test_data.add_testcase(binname, cp_amo, covergroup),
                        f"LI(x{src_reg}, {K})",
                        f"sd x{src_reg}, 0(x{addr_reg})",
                        "nop",
                        f"LI(x{src_reg}, {V})",
                        f"{amo} x{dest_reg}, x{src_reg}, (x{masked_reg})",
                        "nop",
                        write_sigupd(dest_reg, test_data),
                        f"ld x{dest_reg}, 0(x{masked_reg})",
                        "nop",
                        write_sigupd(dest_reg, test_data),
                    ]
                )

            lines.extend(
                [
                    "RVTEST_GOTO_MMODE",
                    "RVTEST_GOTO_LOWER_MODE Smode",
                ]
            )
            lines.append(_asm_ifdef_guard_close(satp_mode))
            lines.append("")

    lines.append("#endif  // ZAAMO_SUPPORTED")
    lines.append("")

    for pmm_val, pmlen in PMM_CONFIGS:
        upper_mask = ((1 << pmlen) - 1) << (64 - pmlen)
        lbl = f"pmm{pmm_val:02b}_pmlen{pmlen}"

        lines.extend(_set_pmm(pmm_val, tmp_reg, pmm_tmp))
        lines.extend(_set_satp_mode("bare", tmp_reg))
        lines.append("RVTEST_GOTO_LOWER_MODE Umode")

        binname_jal_low = f"pmm_{pmm_val:02b}_bare_jal_pa_low"
        lines.extend(
            [
                test_data.add_testcase(binname_jal_low, cp_fetch, covergroup),
                f"jal x0, fetch_jal_low_{lbl}",
                "nop",
                f"fetch_jal_low_{lbl}:",
                "",
            ]
        )

        binname_jalr_low = f"pmm_{pmm_val:02b}_bare_jalr_pa_low"
        lines.extend(
            [
                test_data.add_testcase(binname_jalr_low, cp_fetch, covergroup),
                f"LA(x{addr_reg}, fetch_jalr_low_{lbl})",
                f"jalr x0, 0(x{addr_reg})",
                "nop",
                f"fetch_jalr_low_{lbl}:",
                "",
            ]
        )

        binname_jalr_high = f"pmm_{pmm_val:02b}_bare_jalr_pa_high"
        lines.extend(
            [
                test_data.add_testcase(binname_jalr_high, cp_fetch, covergroup),
                f"LA(x{addr_reg}, fetch_jalr_high_{lbl})",
                f"LI(x{masked_reg}, {upper_mask:#018x})",
                f"or x{addr_reg}, x{addr_reg}, x{masked_reg}",
                f"jalr x0, 0(x{addr_reg})",
                "nop",
                f"fetch_jalr_high_{lbl}:",
                "",
            ]
        )

        lines.extend(
            [
                "RVTEST_GOTO_MMODE",
                "RVTEST_GOTO_LOWER_MODE Smode",
                "",
            ]
        )

    test_data.int_regs.return_registers([addr_reg, masked_reg, dest_reg, src_reg, tmp_reg, pmm_tmp])
    return lines


def _generate_va_sign_extension_tests(test_data: TestData) -> list[str]:
    """cp_virtual_address_sign_extension_write/read: masking sign-extends bit(XLEN-PMLEN-1)."""

    covergroup = "Ssnpm_cg"
    cp_write = "cp_virtual_address_sign_extension_write"
    cp_read = "cp_virtual_address_sign_extension_read"

    sign_ext_masks = {
        "sv39": 0xFFFFFF8000000000,
        "sv48": 0xFFFF000000000000,
        "sv57": 0xFF00000000000000,
    }

    addr_reg, masked_reg, data_reg, tmp_reg, pmm_tmp = test_data.int_regs.get_registers(5, exclude_regs=[0, 2])

    lines = [
        comment_banner(cp_write, "Write to canonical A (sign_val=0: low-half; sign_val=1: high-half)"),
        comment_banner(cp_read, "Read from non-canonical A_masked; masking restores A"),
        "",
    ]

    for pmm_val, pmlen in PMM_CONFIGS:
        upper_mask = ((1 << pmlen) - 1) << (64 - pmlen)

        for satp_mode in SATP_VA_MODES:
            lines.append(_asm_ifdef_guard_open(satp_mode))

            lines.extend(_set_pmm(pmm_val, tmp_reg, pmm_tmp))
            lines.extend(_set_satp_mode(satp_mode, tmp_reg))
            lines.append("RVTEST_GOTO_LOWER_MODE Umode")

            # sign_val = 0: low-half canonical VA
            lines.extend(
                [
                    f"LA(x{addr_reg}, scratch)",
                    f"LI(x{masked_reg}, {upper_mask:#018x})",
                    f"xor x{masked_reg}, x{addr_reg}, x{masked_reg}",
                ]
            )

            for winstr in WRITE_OPS:
                binname = f"pmm_{pmm_val:02b}_{satp_mode}_sign0_{winstr}"
                lines.extend(
                    [
                        test_data.add_testcase(binname, cp_write, covergroup),
                        f"LI(x{data_reg}, 0xCD)",
                        f"{winstr} x{data_reg}, 0(x{addr_reg})",
                        "nop",
                    ]
                )

            for rinstr in READ_OPS:
                binname = f"pmm_{pmm_val:02b}_{satp_mode}_sign0_{rinstr}"
                lines.extend(
                    [
                        test_data.add_testcase(binname, cp_read, covergroup),
                        f"{rinstr} x{data_reg}, 0(x{masked_reg})         # read from A_masked (non-canonical); masking -> A",
                        "nop",
                        write_sigupd(data_reg, test_data),
                    ]
                )

            # sign_val = 1: high-half canonical VA
            se_mask = sign_ext_masks[satp_mode]
            lines.extend(
                [
                    f"LA(x{addr_reg}, scratch)",
                    f"LI(x{tmp_reg}, {se_mask:#018x})",
                    f"or x{addr_reg}, x{addr_reg}, x{tmp_reg}",
                    f"LI(x{masked_reg}, {upper_mask:#018x})",
                    f"xor x{masked_reg}, x{addr_reg}, x{masked_reg}",
                ]
            )

            for winstr in WRITE_OPS:
                binname = f"pmm_{pmm_val:02b}_{satp_mode}_sign1_{winstr}"
                lines.extend(
                    [
                        test_data.add_testcase(binname, cp_write, covergroup),
                        f"LI(x{data_reg}, 0xCD)",
                        f"{winstr} x{data_reg}, 0(x{addr_reg})",
                        "nop",
                    ]
                )

            for rinstr in READ_OPS:
                binname = f"pmm_{pmm_val:02b}_{satp_mode}_sign1_{rinstr}"
                lines.extend(
                    [
                        test_data.add_testcase(binname, cp_read, covergroup),
                        f"{rinstr} x{data_reg}, 0(x{masked_reg})",
                        "nop",
                        write_sigupd(data_reg, test_data),
                    ]
                )

            lines.extend(
                [
                    "RVTEST_GOTO_MMODE",
                    "RVTEST_GOTO_LOWER_MODE Smode",
                ]
            )

            lines.append(_asm_ifdef_guard_close(satp_mode))
            lines.append("")

    test_data.int_regs.return_registers([addr_reg, masked_reg, data_reg, tmp_reg, pmm_tmp])
    return lines


def _generate_pa_zero_extension_tests(test_data: TestData) -> list[str]:
    """cp_physical_address_zero_extension_write/read: bare mode forces upper PMLEN bits to zero."""
    covergroup = "Ssnpm_cg"
    cp_write = "cp_physical_address_zero_extension_write"
    cp_read = "cp_physical_address_zero_extension_read"

    addr_reg, masked_reg, data_reg, tmp_reg, pmm_tmp = test_data.int_regs.get_registers(5, exclude_regs=[0, 2])

    lines = [
        comment_banner(cp_write, "Write to A (upper PMLEN bits = 0) in bare mode"),
        comment_banner(cp_read, "Read from A_masked (upper bits set); zero-extension restores A"),
        "",
    ]

    for pmm_val, pmlen in PMM_CONFIGS:
        upper_mask = ((1 << pmlen) - 1) << (64 - pmlen)

        lines.extend(_set_pmm(pmm_val, tmp_reg, pmm_tmp))
        lines.extend(_set_satp_mode("bare", tmp_reg))
        lines.append("RVTEST_GOTO_LOWER_MODE Umode")

        lines.extend(
            [
                f"LA(x{addr_reg}, scratch)",
                f"LI(x{masked_reg}, {upper_mask:#018x})",
                f"xor x{masked_reg}, x{addr_reg}, x{masked_reg}",
            ]
        )

        for winstr in WRITE_OPS:
            binname = f"pmm_{pmm_val:02b}_bare_{winstr}"
            lines.extend(
                [
                    test_data.add_testcase(binname, cp_write, covergroup),
                    f"LI(x{data_reg}, 0xEF)",
                    f"{winstr} x{data_reg}, 0(x{addr_reg})",
                    "nop",
                ]
            )

        for rinstr in READ_OPS:
            binname = f"pmm_{pmm_val:02b}_bare_{rinstr}"
            lines.extend(
                [
                    test_data.add_testcase(binname, cp_read, covergroup),
                    f"{rinstr} x{data_reg}, 0(x{masked_reg})",
                    "nop ",
                    write_sigupd(data_reg, test_data),
                ]
            )

        lines.extend(
            [
                "RVTEST_GOTO_MMODE",
                "RVTEST_GOTO_LOWER_MODE Smode",
                "",
            ]
        )

    test_data.int_regs.return_registers([addr_reg, masked_reg, data_reg, tmp_reg, pmm_tmp])
    return lines


def _generate_mask_priv_mode_only_tests(test_data: TestData) -> list[str]:

    covergroup = "Ssnpm_cg"
    cp_write = "cp_mask_priv_mode_only_write"
    cp_read = "cp_mask_priv_mode_only_read"

    addr_a, addr_b, addr_c, masked_reg, data_reg, tmp_reg, pmm_tmp = test_data.int_regs.get_registers(
        7, exclude_regs=[0, 2]
    )

    lines = [
        comment_banner(cp_write, "Masking depends only on U-mode privilege, not address value"),
        comment_banner(cp_read, "Three address patterns A/B/C on different VPNs"),
        "",
    ]

    for pmm_val, pmlen in PMM_CONFIGS:
        upper_mask = ((1 << pmlen) - 1) << (64 - pmlen)

        for satp_mode in SATP_MODES:
            lines.append(_asm_ifdef_guard_open(satp_mode))

            lines.extend(_set_pmm(pmm_val, tmp_reg, pmm_tmp))
            lines.extend(_set_satp_mode(satp_mode, tmp_reg))
            lines.append("RVTEST_GOTO_LOWER_MODE Umode")

            lines.extend(_setup_address_regions(addr_a, addr_b, addr_c, tmp_reg))

            for pat_label, pat_reg in [("A", addr_a), ("B", addr_b), ("C", addr_c)]:
                lines.extend(
                    [
                        f"{INDENT}# Pattern {pat_label} — different VPN, masking must apply uniformly",
                        f"LI(x{masked_reg}, {upper_mask:#018x})",
                        f"xor x{masked_reg}, x{pat_reg}, x{masked_reg}",
                    ]
                )

                for winstr in WRITE_OPS:
                    binname = f"pmm_{pmm_val:02b}_{satp_mode}_{pat_label}_{winstr}"
                    lines.extend(
                        [
                            test_data.add_testcase(binname, cp_write, covergroup),
                            f"LI(x{data_reg}, 0x12)",
                            f"{winstr} x{data_reg}, 0(x{pat_reg})",
                            "nop",
                        ]
                    )

                for rinstr in READ_OPS:
                    binname = f"pmm_{pmm_val:02b}_{satp_mode}_{pat_label}_{rinstr}"
                    lines.extend(
                        [
                            test_data.add_testcase(binname, cp_read, covergroup),
                            f"{rinstr} x{data_reg}, 0(x{masked_reg})",
                            "nop",
                            write_sigupd(data_reg, test_data),
                        ]
                    )

            lines.extend(
                [
                    "RVTEST_GOTO_MMODE",
                    "RVTEST_GOTO_LOWER_MODE Smode",
                ]
            )
            lines.append(_asm_ifdef_guard_close(satp_mode))
            lines.append("")

    test_data.int_regs.return_registers([addr_a, addr_b, addr_c, masked_reg, data_reg, tmp_reg, pmm_tmp])
    return lines


def _generate_mxr_disable_tests(test_data: TestData) -> list[str]:
    """cp_pm_mxr_disable_write/read: MXR=1 suppresses pointer masking."""

    covergroup = "Ssnpm_cg"
    cp_write = "cp_pm_mxr_disable_write"
    cp_read = "cp_pm_mxr_disable_read"

    addr_reg, masked_reg, data_reg, tmp_reg, pmm_tmp = test_data.int_regs.get_registers(5, exclude_regs=[0, 2])

    lines = [
        comment_banner(
            cp_write,
            "Write 0x34 to canonical A; MXR=1 active",
        ),
        comment_banner(cp_read, "Load from A_masked with MXR=1: no masking results page fault; sentinel 0xBAD stays"),
        "",
    ]

    for pmm_val, pmlen in PMM_CONFIGS:
        upper_mask = ((1 << pmlen) - 1) << (64 - pmlen)

        for satp_mode in SATP_VA_MODES:
            lines.append(_asm_ifdef_guard_open(satp_mode))

            lines.extend(_set_pmm(pmm_val, tmp_reg, pmm_tmp))

            lines.extend(
                [
                    f"LI(x{tmp_reg}, {1 << 19})",
                    f"CSRS(sstatus, x{tmp_reg})   # set sstatus.MXR = 1",
                ]
            )

            lines.extend(_set_satp_mode(satp_mode, tmp_reg))
            lines.append("RVTEST_GOTO_LOWER_MODE Umode")

            lines.extend(
                [
                    f"LA(x{addr_reg}, scratch)",
                    f"LI(x{masked_reg}, {upper_mask:#018x})",
                    f"xor x{masked_reg}, x{addr_reg}, x{masked_reg}",
                ]
            )

            for winstr in WRITE_OPS:
                binname = f"pmm_{pmm_val:02b}_{satp_mode}_mxr1_{winstr}"
                lines.extend(
                    [
                        test_data.add_testcase(binname, cp_write, covergroup),
                        f"LI(x{data_reg}, 0x34)",
                        f"{winstr} x{data_reg}, 0(x{addr_reg})",
                        "nop",
                    ]
                )

            for rinstr in READ_OPS:
                binname = f"pmm_{pmm_val:02b}_{satp_mode}_mxr1_{rinstr}"
                lines.extend(
                    [
                        test_data.add_testcase(binname, cp_read, covergroup),
                        f"LI(x{data_reg}, 0xBAD)",
                        f"{rinstr} x{data_reg}, 0(x{masked_reg})",
                        "nop",
                        write_sigupd(data_reg, test_data),
                    ]
                )

            lines.extend(
                [
                    "RVTEST_GOTO_MMODE",
                    f"LI(x{tmp_reg}, {1 << 19})",
                    f"CSRC(sstatus, x{tmp_reg})   # clear sstatus.MXR",
                    "RVTEST_GOTO_LOWER_MODE Smode",
                ]
            )

            lines.append(_asm_ifdef_guard_close(satp_mode))
            lines.append("")

    test_data.int_regs.return_registers([addr_reg, masked_reg, data_reg, tmp_reg, pmm_tmp])
    return lines


def _generate_misaligned_tests(test_data: TestData) -> list[str]:
    """cp_pm_misaligned_half/word/double write/read.
    Each offset uses distinct write pattern (0x56+offset).
    Two sig slots per read: value from A_masked, then from A directly."""

    covergroup = "Ssnpm_cg"

    misalign_cases = [
        (
            "cp_pm_misaligned_half_write",
            "cp_pm_misaligned_half_read",
            ["sh"],
            ["lh", "lhu"],
            [0, 1],
            "half",
        ),
        (
            "cp_pm_misaligned_word_write",
            "cp_pm_misaligned_word_read",
            ["sw"],
            ["lw", "lwu"],
            [0, 1, 2, 3],
            "word",
        ),
        (
            "cp_pm_misaligned_double_write",
            "cp_pm_misaligned_double_read",
            ["sd"],
            ["ld"],
            list(range(8)),
            "double",
        ),
    ]

    addr_reg, masked_reg, data_reg, ref_reg, tmp_reg, pmm_tmp = test_data.int_regs.get_registers(6, exclude_regs=[0, 2])

    lines = [
        comment_banner("Masking applies to aligned and misaligned accesses; distinct patterns prevent false positives"),
        "",
        "#ifdef ZICCLSM_SUPPORTED",
        "",
    ]

    for cp_write, cp_read, write_ops, read_ops, offsets, size_label in misalign_cases:
        lines.extend(
            [
                comment_banner(
                    f"cp_pm_misaligned_{size_label}_write / cp_pm_misaligned_{size_label}_read",
                    f"Size={size_label}: offsets={offsets}",
                ),
                "",
            ]
        )

        for pmm_val, pmlen in PMM_CONFIGS:
            upper_mask = ((1 << pmlen) - 1) << (64 - pmlen)

            for satp_mode in SATP_MODES:
                lines.append(_asm_ifdef_guard_open(satp_mode))

                lines.extend(_set_pmm(pmm_val, tmp_reg, pmm_tmp))
                lines.extend(_set_satp_mode(satp_mode, tmp_reg))
                lines.append("RVTEST_GOTO_LOWER_MODE Umode")

                lines.extend(
                    [
                        f"LA(x{addr_reg}, scratch)",
                        f"LI(x{masked_reg}, {upper_mask:#018x})",
                        f"xor x{masked_reg}, x{addr_reg}, x{masked_reg}",
                    ]
                )

                for offset in offsets:
                    align_label = "aligned" if offset == 0 else "misaligned"
                    write_pattern = 0x56 + offset

                    for winstr in write_ops:
                        binname = f"pmm_{pmm_val:02b}_{satp_mode}_{size_label}_{align_label}_off{offset}_{winstr}"
                        lines.extend(
                            [
                                test_data.add_testcase(binname, cp_write, covergroup),
                                f"LI(x{data_reg}, {write_pattern:#04x})",
                                f"{winstr} x{data_reg}, {offset}(x{addr_reg})",
                                "nop",
                            ]
                        )

                    for rinstr in read_ops:
                        binname = f"pmm_{pmm_val:02b}_{satp_mode}_{size_label}_{align_label}_off{offset}_{rinstr}"
                        lines.extend(
                            [
                                test_data.add_testcase(binname, cp_read, covergroup),
                                f"{rinstr} x{data_reg}, {offset}(x{masked_reg})",
                                "nop",
                                write_sigupd(data_reg, test_data),
                                f"{rinstr} x{ref_reg}, {offset}(x{addr_reg})",
                                "nop",
                                write_sigupd(ref_reg, test_data),
                            ]
                        )

                lines.extend(
                    [
                        "RVTEST_GOTO_MMODE",
                        "RVTEST_GOTO_LOWER_MODE Smode",
                    ]
                )

                lines.append(_asm_ifdef_guard_close(satp_mode))
                lines.append("")

    lines.append("#endif  // ZICCLSM_SUPPORTED")
    lines.append("")

    test_data.int_regs.return_registers([addr_reg, masked_reg, data_reg, ref_reg, tmp_reg, pmm_tmp])
    return lines


@add_priv_test_generator(
    "Ssnpm",
    required_extensions=["Ssnpm", "S", "Zicsr"],
    march_extensions=["Zicsr"],
)
def make_ssnpm(test_data: TestData) -> list[str]:
    """Generate tests for the Ssnpm supervisor pointer-masking extension."""

    lines: list[str] = []

    # Wrapped entire test in RV64 guard so RV32 targets skip cleanly.
    lines.append("#if __riscv_xlen == 64")

    init_addr, init_data, stride_reg = test_data.int_regs.get_registers(3, exclude_regs=[0, 2])
    lines.extend(
        [
            f"LA(x{init_addr}, test_data_region)",
            f"LI(x{init_data}, 0)",
            f"LI(x{stride_reg}, 4096)",
            f"sd x{init_data}, 0(x{init_addr})",
            f"add x{init_addr}, x{init_addr}, x{stride_reg}",
            f"sd x{init_data}, 0(x{init_addr})",
            f"add x{init_addr}, x{init_addr}, x{stride_reg}",
            f"sd x{init_data}, 0(x{init_addr})",
            "",
        ]
    )
    test_data.int_regs.return_registers([init_addr, init_data, stride_reg])

    lines.append("RVTEST_GOTO_LOWER_MODE Smode")

    lines.extend(_generate_pmlen_masking_tests(test_data))
    lines.extend(_generate_effective_address_tests(test_data))
    lines.extend(_generate_va_sign_extension_tests(test_data))
    lines.extend(_generate_pa_zero_extension_tests(test_data))
    lines.extend(_generate_mask_priv_mode_only_tests(test_data))
    lines.extend(_generate_mxr_disable_tests(test_data))
    lines.extend(_generate_misaligned_tests(test_data))

    lines.append("RVTEST_GOTO_MMODE")

    lines.append("#endif  // __riscv_xlen == 64")

    return lines
