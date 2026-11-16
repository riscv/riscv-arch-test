##################################
# priv/extensions/sv/Svvptc.py
#
# Svvptc invalid-to-valid PTE visibility tests.
# David_Harris@hmc.edu October 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate Svvptc tests: a store that sets PTE.V reaches later accesses without SFENCE.VMA."""

from testgen.asm.helpers import write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk, trap_sigupd_count
from testgen.priv.extensions.sv.access import mode_switch, virtual_address
from testgen.priv.extensions.sv.generate import SvRegs, begin_sv_test, end_sv_test, sv_data
from testgen.priv.extensions.sv.page_tables import (
    SV32,
    SV39,
    SV48,
    SV57,
    PteFlags,
    SvMode,
    create_leaf_pte,
    create_nonleaf_pte,
    create_page_mapping,
)
from testgen.priv.registry import add_priv_test_generator

# Svvptc bounds the time until the PTE store reaches implicit accesses but does not fix it. The test waits
# 4096 loop iterations (about 8K instructions) before retrying, longer than any reasonable eviction timer,
# so a hart without Svvptc fails the retry instead of hanging.
_DELAY_ITERATIONS = 4096

# Offset of the word that the load and store accesses use in the data page.
_DATA_OFFSET = 20


def _data_region(value_reg: int, result_reg: int) -> str:
    """Return the data page: a fetch payload that writes result_reg, and the word the loads and stores use.

    The framework returns a fetch page fault to ra, so the payload returns through ra as well.
    """
    return f"""\
.p2align 12
rvtest_data_1:
nop
addi x{result_reg}, x{value_reg}, 4
jr ra
nop
.word 0xbeefcaf1
.word 0xbeefcaf2
"""


def _accesses(addr_reg: int, value_reg: int, result_reg: int) -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    """Return (access, faulting instruction, retry instructions); each retry leaves its result in result_reg."""
    load = f"lw x{result_reg}, {_DATA_OFFSET}(x{addr_reg})"
    store = f"sw x{value_reg}, {_DATA_OFFSET}(x{addr_reg})"
    fetch = f"jalr ra, x{addr_reg}, 0"
    return (("load", load, (load,)), ("store", store, (store, load)), ("fetch", fetch, (fetch,)))


def _retry_after_valid(
    test_data: TestData,
    mode: str,
    number: int,
    sv_regs: SvRegs,
    accesses: tuple[tuple[str, str, tuple[str, ...]], ...],
    invalid: list[str],
    valid: str,
    address: list[str],
) -> list[str]:
    """Return one testcase per access: fault on the invalid PTE, store the valid PTE, wait, and retry.

    Args:
        test_data: Test generation state.
        mode: Privilege mode of the accesses, "Smode" or "Umode".
        number: Test case number for labels.
        sv_regs: Registers for the address, store value, result and delay counter.
        accesses: Access kinds from _accesses().
        invalid: Page-table setup with V=0 in the PTE under test.
        valid: Store of the same PTE with V=1.
        address: Code that builds the virtual address in the address register.
    """
    value_reg, result_reg, delay_reg = sv_regs.value, sv_regs.result, sv_regs.load
    enter, leave = mode_switch(mode, "Smode")
    lines = []
    for access, fault, retry in accesses:
        label = test_data.add_testcase(f"test{number}_{access}", f"cp_{access}", f"{test_data.testsuite}_cg")
        lines.extend(
            [
                f"// {access.capitalize()}: page fault on V=0, then retry after setting V=1 without SFENCE.VMA",
                *invalid,
                "sfence.vma",
                *address,
                f"addi x{value_reg}, x{value_reg}, 16",
                *enter,
                fault,
                *leave,
                valid,
                f"LI(x{delay_reg}, {_DELAY_ITERATIONS})",
                "1:",
                f"addi x{delay_reg}, x{delay_reg}, -1",
                f"bnez x{delay_reg}, 1b",
                f"LI(x{result_reg}, 0)",
                *enter,
                label,
                *retry,
                *leave,
                write_sigupd(result_reg, test_data),
                "",
            ]
        )
    return lines


def _make_svvptc_mode(test_data: TestData, sv: SvMode, mode: str) -> TestChunk:
    sv_regs = SvRegs.allocate(test_data)
    chunk = begin_sv_test(
        test_data, sv_regs, sv, mode, f"{sv.name}_{mode}", coverpoint="cp_load, cp_store, cp_fetch", sig_init=""
    )
    umode = mode == "Umode"
    leaf = PteFlags(user=umode)
    chunk.code.append(f"LI(x{sv_regs.value}, 0x800) // Value for the stores")

    # Each case is (description, V=0 page-table setup, V=1 PTE store, level of the accessed address).
    cases = [
        (
            f"{sv.page_names[level]} page, leaf PTE at level {level}",
            create_page_mapping(sv, leaf_level=level, leaf_flags=PteFlags(valid=False, user=umode)),
            create_leaf_pte(sv, level=level, flags=leaf),
            level,
        )
        for level in sv.levels_desc
    ] + [
        (
            f"4KB page, non-leaf PTE at level {level}",
            create_page_mapping(sv, leaf_level=0, leaf_flags=leaf, walk_overrides={level: "0"}),
            create_nonleaf_pte(sv, level=level, flags=PteFlags.nonleaf()),
            0,
        )
        for level in range(sv.levels - 1, 0, -1)
    ]

    accesses = _accesses(sv_regs.addr, sv_regs.value, sv_regs.result)
    for number, (description, invalid, valid, level) in enumerate(cases, 1):
        # The scratch register builds the address and is not live across a PTE_SETUP macro.
        address = virtual_address(sv, "va_data", level, destination=sv_regs.addr, scratch=sv_regs.scratch)
        chunk.code.extend(
            [
                "",
                f"// Test case {number}: {description} changes from V=0 to V=1",
                *_retry_after_valid(test_data, mode, number, sv_regs, accesses, invalid, valid, address),
            ]
        )

    chunk.raw_data.extend(sv_data(sv, sv_regs, data_region_body=_data_region(sv_regs.value, sv_regs.result)))
    chunk.trap_sigupd_count = trap_sigupd_count(len(cases) * len(accesses))
    return end_sv_test(test_data, sv_regs)


@add_priv_test_generator(
    "Svvptc",
    required_extensions=["Sv32", "Svvptc"],
    march_extensions=["Svvptc"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svvptc_sv32(test_data: TestData) -> list[TestChunk]:
    return [_make_svvptc_mode(test_data, SV32, mode) for mode in ("Smode", "Umode")]


@add_priv_test_generator(
    "Svvptc",
    required_extensions=["Sv39", "Svvptc"],
    march_extensions=["Svvptc"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svvptc_sv39(test_data: TestData) -> list[TestChunk]:
    return [_make_svvptc_mode(test_data, SV39, mode) for mode in ("Smode", "Umode")]


@add_priv_test_generator(
    "Svvptc",
    required_extensions=["Sv48", "Svvptc"],
    march_extensions=["Svvptc"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svvptc_sv48(test_data: TestData) -> list[TestChunk]:
    return [_make_svvptc_mode(test_data, SV48, mode) for mode in ("Smode", "Umode")]


@add_priv_test_generator(
    "Svvptc",
    required_extensions=["Sv57", "Svvptc"],
    march_extensions=["Svvptc"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svvptc_sv57(test_data: TestData) -> list[TestChunk]:
    return [_make_svvptc_mode(test_data, SV57, mode) for mode in ("Smode", "Umode")]
