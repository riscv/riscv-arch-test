##################################
# priv/extensions/SvukteCommon.py
#
# Common utilities for the SvukteH, SvukteS and SvukteSm tests.
#
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared helpers for the Svukte test suites."""

from __future__ import annotations

from dataclasses import dataclass

from testgen.asm.helpers import write_sigupd
from testgen.data.state import TestData

SENTINEL = 0xDEADBEEF

FIRST_STORE_VALUE = 0x800
STORE_VALUE_STEP = 16

TEST_WORD_OFFSET = 20

PTE_INVALID = "0"
PTE_USER_RWX = "PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V"
PTE_USER_RX = "PTE_D | PTE_A | PTE_U | PTE_X | PTE_R | PTE_V"
PTE_SUPERVISOR_RWX = "PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V"

# The default test image enters at 0x80000000.  This address is used only for
# SvukteS, whose code must remain VA == PA while satp is enabled.
CODE_VA_IDENTITY = 0x80000000


@dataclass(frozen=True)
class SvMode:
    """One RV64 translation mode and its test addresses."""

    name: str
    level: int
    va_data: int
    va_data_super: int
    va_data_lower: int
    va_code: int

    @property
    def guard(self) -> str:
        """Preprocessor define set when the DUT implements this mode."""
        return f"{self.name.upper()}_SUPPORTED"

    @property
    def level_macro(self) -> str:
        """Framework macro naming this mode's superpage level."""
        return f"LEVEL{self.level}"

    @property
    def va_shift(self) -> int:
        """Number of address bits below a superpage at this level."""
        return self.level * 9 + 12

    def superpage_base(self, va: int) -> int:
        """Return the superpage-aligned base containing `va`."""
        return (va >> self.va_shift) << self.va_shift


SV_MODES: tuple[SvMode, ...] = (
    SvMode(
        name="sv39",
        level=2,
        va_data=0xFFFFFFC000000000,
        va_data_super=0xFFFFFFC040000000,
        va_data_lower=0x0000000040000000,
        va_code=0x0000000180000000,
    ),
    SvMode(
        name="sv48",
        level=3,
        va_data=0xFFFF800000000000,
        va_data_super=0xFFFF808000000000,
        va_data_lower=0x0000400000000000,
        va_code=0x0000030080000000,
    ),
    SvMode(
        name="sv57",
        level=4,
        va_data=0xFF00000000000000,
        va_data_super=0xFF01000000000000,
        # A level-4 leaf covers 256 TiB. VPN[4] must differ from the identity
        # mapping's index zero so lower-address cases do not replace it.
        va_data_lower=0x0001000000000000,
        va_code=0x0005000080000000,
    ),
)


@dataclass(frozen=True)
class SvukteRegs:
    """Registers held live across privilege-mode round trips."""

    store_val: int
    load_dst: int
    exec_dst: int
    va: int
    scratch: int


def allocate_regs(test_data: TestData) -> SvukteRegs:
    """Reserve the registers used by the Svukte tests."""
    store_val, load_dst, exec_dst, va, scratch = test_data.int_regs.get_registers(5)
    return SvukteRegs(
        store_val=store_val,
        load_dst=load_dst,
        exec_dst=exec_dst,
        va=va,
        scratch=scratch,
    )


def release_regs(test_data: TestData, regs: SvukteRegs) -> None:
    """Return the registers reserved by `allocate_regs`."""
    test_data.int_regs.return_registers(
        [
            regs.store_val,
            regs.load_dst,
            regs.exec_dst,
            regs.va,
            regs.scratch,
        ]
    )


def rv64_only(body: list[str]) -> list[str]:
    """Guard `body` on RV64."""
    return [
        "#if __riscv_xlen == 64",
        *body,
        "#endif // __riscv_xlen == 64",
    ]


def mode_guarded(mode: SvMode, body: list[str]) -> list[str]:
    """Guard `body` on the DUT implementing `mode`."""
    return [
        f"#ifdef {mode.guard}",
        *body,
        f"#endif // {mode.guard}",
    ]


def hypervisor_only(body: list[str]) -> list[str]:
    """Guard `body` on hypervisor support."""
    return [
        "#ifdef H_SUPPORTED",
        *body,
        "#endif // H_SUPPORTED",
    ]


def data_payload(regs: SvukteRegs) -> list[str]:
    """Emit the executable test-data page."""
    return [
        "",
        "# Target page for every Svukte access test.",
        ".pushsection .data",
        ".p2align 12",
        "rvtest_data_1:",
        "nop",
        f"addi x{regs.exec_dst}, x{regs.store_val}, 4",
        "jr ra",
        "nop",
        ".word 0xbeefcaf1",
        ".word 0xbeefcaf2",
        "nop",
        "jr ra",
        ".popsection",
        "",
    ]


def init_store_value(regs: SvukteRegs) -> list[str]:
    """Seed the running store value."""
    return [f"LI(x{regs.store_val}, {hex(FIRST_STORE_VALUE)}) # running store value, bumped per testcase"]


def target_va(
    mode: SvMode,
    va: int,
    regs: SvukteRegs,
) -> list[str]:
    """Compute the virtual address under test."""
    base = mode.superpage_base(va)
    offset_bits = 64 - mode.va_shift

    return [
        (f"# Virtual address under test: superpage {hex(base)} + rvtest_data_1's page offset"),
        f"LI(x{regs.va}, {hex(base)})",
        f"LA(x{regs.scratch}, rvtest_data_1)",
        f"slli x{regs.scratch}, x{regs.scratch}, {offset_bits}",
        f"srli x{regs.scratch}, x{regs.scratch}, {offset_bits}",
        f"add x{regs.va}, x{regs.va}, x{regs.scratch}",
        "# Seed the result registers so a faulting access leaves its sentinel in place.",
        f"LI(x{regs.load_dst}, {hex(SENTINEL)})",
        f"LI(x{regs.exec_dst}, {hex(SENTINEL)})",
    ]


def set_csr_bits(
    csr: str,
    mask: str,
    scratch: int,
    *,
    set_bits: bool,
) -> list[str]:
    """Set or clear `mask` in `csr`."""
    operation = "csrs" if set_bits else "csrc"
    return [
        f"LI(x{scratch}, ({mask}))",
        f"{operation} {csr}, x{scratch}",
    ]


def set_ukte(
    regs: SvukteRegs,
    *,
    qualified: bool,
) -> list[str]:
    """Set or clear senvcfg.UKTE."""
    return set_csr_bits(
        "senvcfg",
        "SENVCFG_UKTE",
        regs.scratch,
        set_bits=qualified,
    )


def s_stage_pte(
    mode: SvMode,
    pa_label: str,
    perms: str,
    va: int,
    *,
    fence: bool = True,
) -> list[str]:
    """Map `va` to `pa_label` in the S-stage page table."""
    lines = [(f"SUPERPAGE_PTE_SETUP_{mode.name.upper()}({pa_label}, ({perms}), {hex(va)}, {mode.level_macro})")]

    if fence:
        lines.append("sfence.vma")

    return lines


def vs_stage_pte(
    mode: SvMode,
    pa_label: str,
    perms: str,
    va: int,
    *,
    fence: bool = True,
) -> list[str]:
    """Map `va` to `pa_label` in the VS-stage page table."""
    lines = [(f"SUPERPAGE_VS_PTE_SETUP({mode.name}, {pa_label}, ({perms}), {hex(va)}, {mode.level_macro})")]

    if fence:
        lines.append("hfence.vvma")

    return lines


def enable_s_stage(
    mode: SvMode,
    *,
    code_va: int | None = None,
) -> list[str]:
    """Map the code region and enable `satp`."""
    if code_va is None:
        code_va = mode.va_code

    return [
        (f"# Map the code region so S-mode and U-mode can fetch under {mode.name}."),
        *s_stage_pte(
            mode,
            "rvtest_code_begin",
            PTE_USER_RX,
            code_va,
        ),
        ("# Point the S-mode save area's code pointer at the code region's virtual address."),
        ("# RVTEST_GOTO_LOWER_MODE relocates its return address. a0 is not allocatable,"),
        "# but SAVE_AREA_SETUP requires it and nothing switches mode in between.",
        "csrr a0, mscratch",
        (f"SAVE_AREA_SETUP({hex(code_va)}, rvtest_code_begin, code, {mode.level_macro})"),
        f"SATP_SETUP_RV64({mode.name})",
        "sfence.vma",
    ]


def disable_translation() -> list[str]:
    """Return to Bare translation."""
    return [
        "# Back to Bare translation before the next translation mode's block.",
        "csrwi satp, 0",
        "sfence.vma",
    ]


def access_test(
    test_data: TestData,
    regs: SvukteRegs,
    *,
    covergroup: str,
    coverpoint: str,
    bin_name: str,
    kind: str,
) -> tuple[list[str], str, int]:
    """Emit one access under test."""
    label_line = test_data.add_testcase(
        bin_name,
        coverpoint,
        covergroup,
    )
    label = label_line.rstrip(":")

    setup: list[str] = []

    if kind in ("hsv", "hlv", "hlvx"):
        setup = [(f"addi x{regs.scratch}, x{regs.va}, {TEST_WORD_OFFSET}")]

    instruction, check_reg = {
        "store": (
            f"sw x{regs.store_val}, {TEST_WORD_OFFSET}(x{regs.va})",
            regs.store_val,
        ),
        "load": (
            f"lw x{regs.load_dst}, {TEST_WORD_OFFSET}(x{regs.va})",
            regs.load_dst,
        ),
        "exec": (
            f"jalr ra, x{regs.va}, 0",
            regs.exec_dst,
        ),
        "hsv": (
            f"hsv.w x{regs.store_val}, (x{regs.scratch})",
            regs.store_val,
        ),
        "hlv": (
            f"hlv.w x{regs.load_dst}, (x{regs.scratch})",
            regs.load_dst,
        ),
        "hlvx": (
            f"hlvx.wu x{regs.exec_dst}, (x{regs.scratch})",
            regs.exec_dst,
        ),
    }[kind]

    return (
        [
            *setup,
            label_line,
            instruction,
            "nop",
        ],
        label,
        check_reg,
    )


def bump_store_value(regs: SvukteRegs) -> list[str]:
    """Advance the running store value."""
    return [(f"addi x{regs.store_val}, x{regs.store_val}, {STORE_VALUE_STEP}")]


def deferred_sigupds(
    test_data: TestData,
    results: list[tuple[str, int]],
) -> list[str]:
    """Emit signature updates after returning to M-mode."""
    lines = ["# Signature updates, now that we are back in M-mode."]

    for label, check_reg in results:
        lines.append(
            write_sigupd(
                check_reg,
                test_data,
                label=label,
            )
        )

    return lines
