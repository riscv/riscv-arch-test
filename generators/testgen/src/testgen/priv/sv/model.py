##################################
# priv/sv/model.py
#
# Data model for the Sv* virtual-memory suite generators.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Declarative data model for the generated Sv* virtual-memory test suites."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SvMode:
    """One satp translation mode and the constants that depend on it."""

    name: str  # "sv32" | "sv39" | "sv48" | "sv57"
    xlen: int
    levels: int  # number of page-table levels; leaf levels range 0 .. levels-1
    va_data: str  # virtual address mapped to the test data region (rvtest_data_1)
    va_code: str  # virtual address mapped to the code region
    satp_setup: str  # assembly macro invocation that programs satp
    suffix: str  # PTE macro suffix: PTE_SETUP_{suffix} / SUPERPAGE_PTE_SETUP_{suffix}
    march: str
    page_names: tuple[str, ...]  # page size name per leaf level (index = level)

    @property
    def ext(self) -> str:
        """Extension name for REQUIRED_EXTENSIONS, e.g. Sv39."""
        return self.name.capitalize()


SVMODES: dict[str, SvMode] = {
    "sv32": SvMode(
        name="sv32",
        xlen=32,
        levels=2,
        va_data="0x90407000",
        va_code="0x30000000",
        satp_setup="SATP_SETUP_SV32",
        suffix="SV32",
        march="rv32i_zicsr_zifencei",
        page_names=("4KB", "4MB"),
    ),
    "sv39": SvMode(
        name="sv39",
        xlen=64,
        levels=3,
        va_data="0x140802000",
        va_code="0x180000000",
        satp_setup="SATP_SETUP_RV64(sv39)",
        suffix="SV39",
        march="rv64i_zicsr_zifencei",
        page_names=("4KB", "2MB", "1GB"),
    ),
    "sv48": SvMode(
        name="sv48",
        xlen=64,
        levels=4,
        va_data="0x028500403000",
        va_code="0x030080000000",
        satp_setup="SATP_SETUP_RV64(sv48)",
        suffix="SV48",
        march="rv64i_zicsr_zifencei",
        page_names=("4KB", "2MB", "1GB", "512GB"),
    ),
    "sv57": SvMode(
        name="sv57",
        xlen=64,
        levels=5,
        va_data="0x07028500403000",
        va_code="0x03000080000000",
        satp_setup="SATP_SETUP_RV64(sv57)",
        suffix="SV57",
        march="rv64i_zicsr_zifencei",
        page_names=("4KB", "2MB", "1GB", "512GB", "256TB"),
    ),
}


@dataclass(frozen=True)
class TestCase:
    """One structured test case: a PTE walk plus one runner invocation.

    Used by suites whose cases all follow the standard walk/leaf/runner shape
    (e.g. Svade). ``banner_result`` may contain ``{mode}``, replaced with "S" or
    "U" at render time. ``leaf_perms`` lists the PTE permission tokens for the
    leaf WITHOUT ``PTE_U``; the renderer inserts ``PTE_U`` for U-mode files.
    """

    inline_desc: str  # e.g. "PTE.D unset and PTE.A set" (inline // Test case comment)
    banner_desc: str  # e.g. "PTE.D unset, PTE.A set" (numbered banner list)
    banner_result: str  # e.g. "Then, access the page in {mode}-Mode. Expected: Store-page-fault"
    inline_result: str  # e.g. "Store page fault"
    level: int  # leaf page level
    leaf_perms: tuple[str, ...]
    faults: int  # expected trap count contribution (for banner total and TRAP_SIGUPD_COUNT)
    walk_perms: str = "PTE_V"  # permissions for the non-leaf walk PTEs
    superpage: bool = True  # use SUPERPAGE_PTE_SETUP_* for the leaf when level > 0
    pre_asm: tuple[str, ...] = ()  # extra assembly lines emitted just before the runner
    post_asm: tuple[str, ...] = ()  # extra assembly lines emitted just after the runner


@dataclass(frozen=True)
class SvCase:
    """One freeform test case for topics that don't fit the structured TestCase.

    ``banner`` lines get "// {n}. " / "//        " prefixes at render time.
    ``body`` lines are emitted verbatim (builders provide indentation and the
    concrete testcase names). ``sig_strs`` lists ``(label, message)`` pairs that
    become ``{label}_str: .string "\\"{message}\\""`` entries and are counted for
    SIGUPD_COUNT.
    """

    banner: tuple[str, ...]
    body: tuple[str, ...]
    sig_strs: tuple[tuple[str, str], ...] = ()
    faults: int = 0
    level: int | None = None  # drives the TESTS AT LEVEL / page-size comment headers
    sigupds: int | None = None  # override signature-update count (default len(sig_strs))


@dataclass(frozen=True)
class FileSpec:
    """Complete description of one generated .S test file."""

    filename: str
    required_extensions: tuple[str, ...]
    march: str
    svmode: SvMode
    priv_mode: str  # "Smode" | "Umode" (names the file and the {mode} letter)
    banner_prefix: str  # verbatim comment block (attribution etc.); may contain {mode}
    macro_blocks: tuple[str, ...] = ()  # verbatim local .macro block texts, in order
    cases: tuple[TestCase, ...] = ()  # structured cases (Svade style)
    sv_cases: tuple[SvCase, ...] = ()  # freeform cases (Sv style); mutually exclusive with cases
    setup_asm: tuple[str, ...] = ()  # extra assembly after the SATP setup (already indented)
    sig_ops: tuple[tuple[str, str], ...] = (("store", "sw"), ("load", "lw"), ("exec", "jalr"))
    code_guard: str | None = None  # wrap macros+code in #ifdef <guard> ... #endif
    code_pte_change_be: bool = False  # emit CHANGE_PTE_TO_BE after the code-region PTE setup
    sig_init: str = "  LI( a2, 0x800)              // Test signature initialization"
    va_defs: tuple[tuple[str, str], ...] | None = None  # (name, value); None -> (("va_data", svmode.va_data),)
    va_code_override: str | None = None  # code-region VA when it differs from svmode.va_code
    data_align: int = 12  # .p2align of the test data region
    data_region_body: str | None = None  # override the standard test region blob (with labels)
    extra_defines: tuple[str, ...] = ()  # extra #define lines after the count defines
    sigupd_override: int | None = None  # explicit SIGUPD_COUNT (template files)
    trap_override: int | None = None  # explicit TRAP_SIGUPD_COUNT (template files)
    emit_trap_count: bool = True
    body_template: str | None = None  # bespoke files: fully verbatim body instead of cases
    banner_body: str | None = None  # bespoke files: verbatim banner text (case list etc.)
