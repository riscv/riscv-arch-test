##################################
# priv/extensions/sv/ExceptionsSvCommon.py
#
# Common virtual-memory exception test generation.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate common virtual-memory exception tests."""

from dataclasses import dataclass

from testgen.asm.helpers import lrsc_retry_loop, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk, trap_sigupd_count
from testgen.priv.extensions.sv.access import add_rwx_test, mode_switch, virtual_address
from testgen.priv.extensions.sv.generate import begin_sv_test, sv_data
from testgen.priv.extensions.sv.page_tables import PteFlags, SvMode, create_leaf_pte, create_page_mapping
from testgen.priv.extensions.sv.Sv import MPRV_CLEANUP, mstatus_setup

# medeleg[9] would delegate the S-mode ecall that T-SBI uses to enter M-mode.
_MEDELEG_VALUES = (*(1 << bit for bit in range(9)), 1 << 12, 1 << 13, 1 << 15, 0xB1FF)
_INVALID_VA = {"sv32": "0x90807000", "sv39": "0x1c0802000"}
_BASE_CASES = (
    (True, "rvtest_data_1", False),
    (True, "rvtest_data_1", True),
    (True, "RVMODEL_ACCESS_FAULT_ADDRESS", False),
    (True, "RVMODEL_ACCESS_FAULT_ADDRESS", True),
    (False, "rvtest_data_1", False),
    (False, "rvtest_data_1", True),
    (False, "RVMODEL_ACCESS_FAULT_ADDRESS", False),
    (False, "RVMODEL_ACCESS_FAULT_ADDRESS", True),
)
# Two physical pages holding a 4-byte instruction that starts in the last halfword of the first page
_CROSSING_DATA = (
    "// Two pages that a misaligned access spans",
    ".p2align 12",
    "rvtest_cross_page:",
    ".skip 4096 - 2",
    ".option push",
    ".option norvc",
    "jr ra",
    ".option pop",
    ".skip 4096 - 2",
)


@dataclass(frozen=True)
class _Target:
    """Where one exception test runs its accesses.

    ``mode`` executes the accesses. When it is M-mode, mstatus.MPRV makes them use ``effective_mode``.
    """

    suite: str
    operation: str
    mode: str
    effective_mode: str
    driver_mode: str

    @property
    def mprv(self) -> bool:
        return self.mode == "Mmode"

    @property
    def setup(self) -> tuple[str, ...]:
        return mstatus_setup(f"mprv_{self.effective_mode[0].lower()}") if self.mprv else ()

    def coverpoints(self, *, medeleg: bool, misaligned: bool) -> dict[str, str]:
        suffix = self.mode[0].lower()
        if self.operation != "rwx":
            coverpoint = f"cp_medeleg_{suffix}" if medeleg else f"cp_misaligned_priority_{suffix}"
            operations = ("amoadd",) if self.operation == "Zaamo" else ("lr", "sc")
            return dict.fromkeys(operations, coverpoint)
        if medeleg:
            return {
                "store": f"cp_medeleg_{suffix}",
                "load": f"cp_medeleg_{suffix}",
                "exec": f"cp_medeleg_fetch_{suffix}",
            }
        if misaligned:
            return dict.fromkeys(("store", "load"), f"cp_misaligned_priority_{suffix}") | {
                "exec": f"cp_misaligned_priority_fetch_{suffix}"
            }
        return {
            "store": f"cp_store_page_fault_{suffix}",
            "load": f"cp_load_page_fault_{suffix}",
            "exec": f"cp_instr_page_fault_{suffix}",
        }


def _atomic_access(
    test_data: TestData,
    target: _Target,
    name: str,
    address: list[str],
    coverpoints: dict[str, str],
    *,
    faults: bool,
) -> list[str]:
    covergroup = f"{target.suite}_cg"
    labels = {
        op: test_data.add_testcase(f"{name}_{op}", coverpoint, covergroup).removesuffix(":")
        for op, coverpoint in coverpoints.items()
    }
    enter, leave = mode_switch(target.mode, target.driver_mode)
    lines = [*address, *enter, *target.setup, "addi a2, a2, 1", ""]
    if target.operation == "Zaamo":
        lines.extend([f"{labels['amoadd']}:", "amoadd.w a3, a2, (a5)", "nop"])
        results = ((13, labels["amoadd"]),)
    else:
        lr = [f"{labels['lr']}:", "lr.w a3, (a5)", "nop"]
        sc = [f"{labels['sc']}:", "sc.w a4, a2, (a5)"]
        if faults:
            # A trap taken in M-mode changes mstatus.MPP, so set up MPRV again before the SC.
            lines.extend([*lr, *target.setup, *sc])
        else:
            retry_reg = test_data.int_regs.get_register(exclude_regs=[13, 14, 15])  # a3-a5 hold the operands
            retry_start, retry_end = lrsc_retry_loop(labels["sc"], retry_reg, 14)
            test_data.int_regs.return_register(retry_reg)
            lines.extend([*retry_start, *lr, *sc, *retry_end])
        lines.append("nop")
        results = ((13, labels["lr"]), (14, labels["sc"]))
    if target.mprv:
        lines.extend(["", *MPRV_CLEANUP])
    lines.extend(["", *leave, "", *(write_sigupd(reg, test_data, label=label) for reg, label in results)])
    return lines


def _add_access(
    test_data: TestData,
    sv: SvMode,
    target: _Target,
    number: int,
    *,
    va: str = "va_data",
    valid: bool = True,
    physical_address: str = "rvtest_data_1",
    misaligned: bool = False,
    medeleg: bool = False,
) -> list[str]:
    level = sv.levels - 1
    permissions = PteFlags(user=target.effective_mode == "Umode", valid=valid)
    address = virtual_address(
        sv,
        va,
        level,
        physical_address=physical_address,
        physical_address_is_label=physical_address == "rvtest_data_1",
    )
    if misaligned:
        address.append("addi a5, a5, 2")
    coverpoints = target.coverpoints(medeleg=medeleg, misaligned=misaligned)
    if target.operation == "rwx":
        access = add_rwx_test(
            test_data,
            sv,
            target.mode,
            va,
            level,
            f"test{number}",
            driver_mode=target.driver_mode,
            address=address,
            setup=target.setup,
            cleanup=MPRV_CLEANUP if target.mprv else (),
            repeat_setup=target.mprv,
            physical_fetch=target.mprv,
            coverpoints=coverpoints,
            covergroup=f"{target.suite}_cg",
        )
    else:
        faults = not valid or misaligned or physical_address != "rvtest_data_1"
        access = _atomic_access(test_data, target, f"test{number}", address, coverpoints, faults=faults)
    return [
        *create_page_mapping(
            sv, virtual_address=va, physical_address=physical_address, leaf_level=level, leaf_flags=permissions
        ),
        "sfence.vma",
        "",
        *access,
        "",
    ]


# The word that spans the two pages: jr ra (jalr x0, 0(ra)), which the fetch cases execute
_CROSSING_WORD = 0x00008067
# Each page passes (RWX = 111) or fails (zero PTE): (name, first page passes, second page passes)
_CROSSING_COMBINATIONS = (
    ("neither", True, True),
    ("first", False, True),
    ("second", True, False),
    ("both", False, False),
)


def _page_crossing_cases(test_data: TestData, sv: SvMode) -> list[str]:
    """Fetch, load and store across the boundary of two kilopages, for each combination of the pages passing or failing.

    A page passes with RWX = 111 and fails with a zero PTE. A jalr to a 4-byte instruction, a lw and a sw each start
    at the last halfword of the first page. The stores write back the word already there, so a store that faults
    after writing the part in one page leaves memory unchanged. When neither page faults, the store first writes a
    different word and a load reads it back.
    """
    covergroup = "ExceptionsSv_cg"
    # PTE_SETUP clobbers t0 and t1 (a0 and a1 are not in the privileged register pool)
    addr, word, load = test_data.int_regs.get_registers(3, exclude_regs=[5, 6])
    lines = [f"LI(x{word}, {_CROSSING_WORD:#x}) # jr ra, the word that spans the two pages"]
    for name, first_passes, second_passes in _CROSSING_COMBINATIONS:
        labels = {
            op: test_data.add_testcase(f"cross_{name}_fails_{op}", coverpoint, covergroup).removesuffix(":")
            for op, coverpoint in (
                ("exec", "cp_misaligned_instr_page_fault_s"),
                ("load", "cp_misaligned_load_page_fault_s"),
                ("store", "cp_misaligned_store_page_fault_s"),
            )
        }
        lines.extend(
            [
                "",
                f"// Page crossing: {name} of the two pages {'fail' if name == 'both' else 'fails'}",
                *create_page_mapping(
                    sv,
                    virtual_address="va_cross_1",
                    physical_address="rvtest_cross_page",
                    leaf_level=0,
                    leaf_flags=PteFlags() if first_passes else "0",
                ),
                create_leaf_pte(
                    sv,
                    level=0,
                    flags=PteFlags() if second_passes else "0",
                    virtual_address="va_cross_2",
                    physical_address="rvtest_cross_page + 4096",
                ),
                "sfence.vma",
                f"LI(x{addr}, va_cross_2 - 2)",
                f"{labels['exec']}:",
                f"jalr ra, x{addr}, 0",
                "nop",
                f"{labels['load']}:",
                f"lw x{load}, 0(x{addr})",
                "nop",
                write_sigupd(load, test_data, label=labels["load"]),
            ]
        )
        if first_passes and second_passes:
            lines.extend(
                [
                    f"not x{load}, x{word} # a different word, read back after the store",
                    f"{labels['store']}:",
                    f"sw x{load}, 0(x{addr})",
                    "nop",
                    f"lw x{load}, 0(x{addr})",
                    write_sigupd(load, test_data, label=labels["store"]),
                    f"sw x{word}, 0(x{addr}) # restore jr ra",
                ]
            )
        else:
            lines.extend([f"{labels['store']}:", f"sw x{word}, 0(x{addr})", "nop"])
    test_data.int_regs.return_registers([addr, word, load])
    return lines


def _make_mode_test(
    test_data: TestData, sv: SvMode, target: _Target, *, base_cases: bool, medeleg_cases: bool
) -> TestChunk:
    operation_name = "" if target.operation == "rwx" else f"_{target.operation}"
    mode_name = f"mprv_{target.effective_mode[0]}_Mmode" if target.mprv else target.mode
    topic = "exceptions" if base_cases else "medeleg"

    setup_asm: tuple[str, ...] = ()
    saved_medeleg = medeleg_value = 0
    if medeleg_cases:
        saved_medeleg, medeleg_value = test_data.int_regs.get_registers(2, reg_range=[8, 9])
        setup_asm = (f"csrr x{saved_medeleg}, medeleg",)
    if target.mprv and target.operation == "rwx":
        # MPRV does not affect instruction fetches. If it did, fetching the target routine
        # through its invalid identity PTE would fault.
        identity = PteFlags(valid=False, user=target.effective_mode == "Umode")
        level = sv.levels - 1
        setup_asm = (
            *setup_asm,
            "LA(a0, rvtest_data_1)",
            f"LI(a1, {identity})",
            f"LA(t1, {sv.page_table_label(level)})",
            "LA(a3, rvtest_data_1)",
            f"PTE_SETUP_COMMON(a0, a1, t0, t1, a3, LEVEL{level})",
        )
        setup_asm = (*setup_asm, "sfence.vma")

    crossing = base_cases and target.operation == "rwx" and target.mode == "Smode"
    va_defs = (("va_data", sv.data_va), ("va_data_invalid", _INVALID_VA[sv.name]))
    if crossing:
        va_defs = (*va_defs, ("va_cross_1", sv.data_va), ("va_cross_2", "va_cross_1 + 0x1000"))

    suffix = target.mode[0].lower()
    if not base_cases:
        banner = f"cp_medeleg_{suffix}"
    elif target.operation == "rwx":
        banner = f"cp_instr_page_fault_{suffix}"
    else:
        banner = f"cp_misaligned_priority_{suffix}"
    chunk = begin_sv_test(
        test_data,
        sv,
        target.effective_mode,
        f"{sv.name}_{topic}{operation_name}_{mode_name}",
        coverpoint=banner,
        va_defs=va_defs,
        setup_asm=setup_asm,
    )

    number = 1
    if base_cases:
        for valid, physical_address, misaligned in _BASE_CASES:
            guarded = physical_address == "RVMODEL_ACCESS_FAULT_ADDRESS"
            access = _add_access(
                test_data,
                sv,
                target,
                number,
                valid=valid,
                physical_address=physical_address,
                misaligned=misaligned,
            )
            chunk.code.extend(["#ifdef RVMODEL_ACCESS_FAULT_ADDRESS", *access, "#endif", ""] if guarded else access)
            number += 1
    if crossing:
        chunk.code.extend(_page_crossing_cases(test_data, sv))

    if medeleg_cases:
        for medeleg in _MEDELEG_VALUES:
            chunk.code.extend(
                [
                    f"LI(x{medeleg_value}, {medeleg:#x})",
                    f"csrw medeleg, x{medeleg_value}",
                    *_add_access(test_data, sv, target, number, medeleg=True),
                    *_add_access(test_data, sv, target, number + 1, va="va_data_invalid", valid=False, medeleg=True),
                ]
            )
            number += 2
        chunk.code.append(f"csrw medeleg, x{saved_medeleg}")
        test_data.int_regs.return_registers([saved_medeleg, medeleg_value])

    chunk.raw_data.extend(sv_data(sv))
    if crossing:
        chunk.raw_data.extend(_CROSSING_DATA)
    chunk.trap_sigupd_count = trap_sigupd_count(200)
    return test_data.end_test_chunk()


def make_exception_suite(
    test_data: TestData, sv: SvMode, *, suite: str, operation: str, machine_state: bool
) -> list[TestChunk]:
    """Generate the virtual-memory exception tests for one suite.

    Suites without ``machine_state`` run the base cases from S-mode and U-mode. Suites with it add the medeleg
    walk to each mode and run the base cases in M-mode with mstatus.MPRV set.
    """
    if not machine_state:
        return [
            _make_mode_test(
                test_data, sv, _Target(suite, operation, mode, mode, "Smode"), base_cases=True, medeleg_cases=False
            )
            for mode in ("Smode", "Umode")
        ]
    modes = [("Smode", "Smode", False), ("Umode", "Umode", False), ("Mmode", "Smode", True)]
    if operation == "rwx":
        modes.append(("Mmode", "Umode", True))
    return [
        _make_mode_test(
            test_data,
            sv,
            _Target(suite, operation, mode, effective_mode, "Mmode"),
            base_cases=base_cases,
            medeleg_cases=True,
        )
        for mode, effective_mode, base_cases in modes
    ]
