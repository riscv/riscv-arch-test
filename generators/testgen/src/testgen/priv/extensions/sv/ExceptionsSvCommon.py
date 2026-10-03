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
from testgen.priv.extensions.sv.generate import SvRegs, begin_sv_test, end_sv_test, sv_data
from testgen.priv.extensions.sv.page_tables import PTE_SETUP_ADDR_REG, PteFlags, SvMode, create_page_mapping
from testgen.priv.extensions.sv.Sv import mprv_cleanup, mstatus_setup

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

    def setup(self, scratch: int) -> tuple[str, ...]:
        return mstatus_setup(f"mprv_{self.effective_mode[0].lower()}", scratch) if self.mprv else ()

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
    regs: SvRegs,
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
    setup = target.setup(regs.scratch)
    value, addr, load = (f"x{reg}" for reg in (regs.value, regs.addr, regs.load))
    lines = [*address, *enter, *setup, f"addi {value}, {value}, 1", ""]
    if target.operation == "Zaamo":
        lines.extend([f"{labels['amoadd']}:", f"amoadd.w {load}, {value}, ({addr})", "nop"])
        results = ((regs.load, labels["amoadd"]),)
    else:
        lr = [f"{labels['lr']}:", f"lr.w {load}, ({addr})", "nop"]
        sc = [f"{labels['sc']}:", f"sc.w x{regs.result}, {value}, ({addr})"]
        if faults:
            # A trap taken in M-mode changes mstatus.MPP, so set up MPRV again before the SC.
            lines.extend([*lr, *setup, *sc])
        else:
            # regs.scratch is free here: the MPRV setup above and the cleanup below only use it as a temporary.
            retry_start, retry_end = lrsc_retry_loop(labels["sc"], regs.scratch, regs.result)
            lines.extend([*retry_start, *lr, *sc, *retry_end])
        lines.append("nop")
        results = ((regs.load, labels["lr"]), (regs.result, labels["sc"]))
    if target.mprv:
        lines.extend(["", *mprv_cleanup(regs.scratch)])
    lines.extend(["", *leave, "", *(write_sigupd(reg, test_data, label=label) for reg, label in results)])
    return lines


def _add_access(
    test_data: TestData,
    sv: SvMode,
    regs: SvRegs,
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
        destination=regs.addr,
        scratch=regs.scratch,
        physical_address=physical_address,
        physical_address_is_label=physical_address == "rvtest_data_1",
    )
    if misaligned:
        address.append(f"addi x{regs.addr}, x{regs.addr}, 2")
    coverpoints = target.coverpoints(medeleg=medeleg, misaligned=misaligned)
    if target.operation == "rwx":
        access = add_rwx_test(
            test_data,
            sv,
            regs,
            target.mode,
            va,
            level,
            f"test{number}",
            driver_mode=target.driver_mode,
            address=address,
            setup=target.setup(regs.scratch),
            cleanup=mprv_cleanup(regs.scratch) if target.mprv else (),
            repeat_setup=target.mprv,
            physical_fetch=target.mprv,
            coverpoints=coverpoints,
            covergroup=f"{target.suite}_cg",
        )
    else:
        faults = not valid or misaligned or physical_address != "rvtest_data_1"
        access = _atomic_access(test_data, regs, target, f"test{number}", address, coverpoints, faults=faults)
    return [
        *create_page_mapping(
            sv, virtual_address=va, physical_address=physical_address, leaf_level=level, leaf_flags=permissions
        ),
        "sfence.vma",
        "",
        *access,
        "",
    ]


def _make_mode_test(
    test_data: TestData, sv: SvMode, target: _Target, *, base_cases: bool, medeleg_cases: bool
) -> TestChunk:
    operation_name = "" if target.operation == "rwx" else f"_{target.operation}"
    mode_name = f"mprv_{target.effective_mode[0]}_Mmode" if target.mprv else target.mode
    topic = "exceptions" if base_cases else "medeleg"

    setup_asm: tuple[str, ...] = ()
    saved_medeleg = 0
    if medeleg_cases:
        # Allocated before the chunk's registers so it is never x6, which the page-table macros clobber.
        saved_medeleg = test_data.int_regs.get_register(exclude_regs=[0, PTE_SETUP_ADDR_REG])
        setup_asm = (f"csrr x{saved_medeleg}, medeleg",)
    regs = SvRegs.allocate(test_data)
    if target.mprv and target.operation == "rwx":
        # MPRV does not affect instruction fetches. If it did, fetching the target routine
        # through its invalid identity PTE would fault.
        identity = PteFlags(valid=False, user=target.effective_mode == "Umode")
        level = sv.levels - 1
        # regs.value is free here: begin_sv_test initializes it after setup_asm.
        pa, perms, temp, table, va = (
            f"x{reg}" for reg in (regs.addr, regs.load, regs.value, regs.result, regs.scratch)
        )
        setup_asm = (
            *setup_asm,
            f"LA({pa}, rvtest_data_1)",
            f"LI({perms}, {identity})",
            f"LA({table}, {sv.page_table_label(level)})",
            f"LA({va}, rvtest_data_1)",
            f"PTE_SETUP_COMMON({pa}, {perms}, {temp}, {table}, {va}, LEVEL{level})",
        )
        setup_asm = (*setup_asm, "sfence.vma")

    suffix = target.mode[0].lower()
    if not base_cases:
        banner = f"cp_medeleg_{suffix}"
    elif target.operation == "rwx":
        banner = f"cp_instr_page_fault_{suffix}"
    else:
        banner = f"cp_misaligned_priority_{suffix}"
    chunk = begin_sv_test(
        test_data,
        regs,
        sv,
        target.effective_mode,
        f"{sv.name}_{topic}{operation_name}_{mode_name}",
        coverpoint=banner,
        va_defs=(("va_data", sv.data_va), ("va_data_invalid", _INVALID_VA[sv.name])),
        setup_asm=setup_asm,
    )

    number = 1
    if base_cases:
        for valid, physical_address, misaligned in _BASE_CASES:
            guarded = physical_address == "RVMODEL_ACCESS_FAULT_ADDRESS"
            access = _add_access(
                test_data,
                sv,
                regs,
                target,
                number,
                valid=valid,
                physical_address=physical_address,
                misaligned=misaligned,
            )
            chunk.code.extend(["#ifdef RVMODEL_ACCESS_FAULT_ADDRESS", *access, "#endif", ""] if guarded else access)
            number += 1

    if medeleg_cases:
        for medeleg in _MEDELEG_VALUES:
            chunk.code.extend(
                [
                    f"LI(x{regs.scratch}, {medeleg:#x})",
                    f"csrw medeleg, x{regs.scratch}",
                    *_add_access(test_data, sv, regs, target, number, medeleg=True),
                    *_add_access(
                        test_data, sv, regs, target, number + 1, va="va_data_invalid", valid=False, medeleg=True
                    ),
                ]
            )
            number += 2
        chunk.code.append(f"csrw medeleg, x{saved_medeleg}")

    chunk.raw_data.extend(sv_data(sv, regs))
    chunk.trap_sigupd_count = trap_sigupd_count(200)
    tc = end_sv_test(test_data, regs)
    if medeleg_cases:
        test_data.int_regs.return_register(saved_medeleg)
    return tc


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
