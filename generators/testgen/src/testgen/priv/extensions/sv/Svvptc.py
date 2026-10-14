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
from testgen.priv.extensions.sv.generate import begin_sv_test, sv_data
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
    regs: tuple[int, int, int, int],
    invalid: list[str],
    valid: str,
    address: list[str],
) -> list[str]:
    """Return one testcase per access: fault on the invalid PTE, store the valid PTE, wait, and retry.

    Args:
        test_data: Test generation state.
        mode: Privilege mode of the accesses, "Smode" or "Umode".
        number: Test case number for labels.
        regs: Address, store value, result and delay registers.
        invalid: Page-table setup with V=0 in the PTE under test.
        valid: Store of the same PTE with V=1.
        address: Code that builds the virtual address in the address register.
    """
    addr_reg, value_reg, result_reg, delay_reg = regs
    enter, leave = mode_switch(mode, "Smode")
    lines = []
    for access, fault, retry in _accesses(addr_reg, value_reg, result_reg):
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
    chunk = begin_sv_test(
        test_data, sv, mode, f"{sv.name}_{mode}", coverpoint="cp_load, cp_store, cp_fetch", sig_init=""
    )
    # The PTE_SETUP macros clobber t0 and t1. The result register also builds the address, before each access.
    addr_reg, value_reg, result_reg, delay_reg = test_data.int_regs.get_registers(4, exclude_regs=[5, 6])
    regs = (addr_reg, value_reg, result_reg, delay_reg)
    umode = mode == "Umode"
    leaf = PteFlags(user=umode)
    number = 0
    chunk.code.append(f"LI(x{value_reg}, 0x800) // Value for the stores")

    def address(level: int) -> list[str]:
        return virtual_address(sv, "va_data", level, destination=f"x{addr_reg}", scratch=f"x{result_reg}")

    for level in sv.levels_desc:
        number += 1
        chunk.code.extend(
            [
                "",
                f"// Test case {number}: {sv.page_names[level]} page, leaf PTE at level {level} changes from V=0 to V=1",
                *_retry_after_valid(
                    test_data,
                    mode,
                    number,
                    regs,
                    create_page_mapping(sv, leaf_level=level, leaf_flags=PteFlags(valid=False, user=umode)),
                    create_leaf_pte(sv, level=level, flags=leaf),
                    address(level),
                ),
            ]
        )

    for level in range(sv.levels - 1, 0, -1):
        number += 1
        chunk.code.extend(
            [
                "",
                f"// Test case {number}: 4KB page, non-leaf PTE at level {level} changes from V=0 to V=1",
                *_retry_after_valid(
                    test_data,
                    mode,
                    number,
                    regs,
                    create_page_mapping(sv, leaf_level=0, leaf_flags=leaf, walk_overrides={level: "0"}),
                    create_nonleaf_pte(sv, level=level, flags=PteFlags.nonleaf()),
                    address(0),
                ),
            ]
        )

    test_data.int_regs.return_registers(list(regs))
    chunk.raw_data.extend(sv_data(sv, data_region_body=_data_region(value_reg, result_reg)))
    chunk.trap_sigupd_count = trap_sigupd_count(number * len(_accesses(addr_reg, value_reg, result_reg)))
    return test_data.end_test_chunk()


def _make_svvptc(test_data: TestData, sv: SvMode) -> list[TestChunk]:
    return [_make_svvptc_mode(test_data, sv, mode) for mode in ("Smode", "Umode")]


@add_priv_test_generator(
    "Svvptc",
    required_extensions=["Sv32", "Svvptc"],
    march_extensions=["Svvptc"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svvptc_sv32(test_data: TestData) -> list[TestChunk]:
    return _make_svvptc(test_data, SV32)


@add_priv_test_generator(
    "Svvptc",
    required_extensions=["Sv39", "Svvptc"],
    march_extensions=["Svvptc"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svvptc_sv39(test_data: TestData) -> list[TestChunk]:
    return _make_svvptc(test_data, SV39)


@add_priv_test_generator(
    "Svvptc",
    required_extensions=["Sv48", "Svvptc"],
    march_extensions=["Svvptc"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svvptc_sv48(test_data: TestData) -> list[TestChunk]:
    return _make_svvptc(test_data, SV48)


@add_priv_test_generator(
    "Svvptc",
    required_extensions=["Sv57", "Svvptc"],
    march_extensions=["Svvptc"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svvptc_sv57(test_data: TestData) -> list[TestChunk]:
    return _make_svvptc(test_data, SV57)
