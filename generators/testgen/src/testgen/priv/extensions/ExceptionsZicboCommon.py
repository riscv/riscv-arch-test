##################################
# priv/extensions/ExceptionsZicboCommon.py
#
# Shared Zicbo extension exception test generation.
# aman.murad@10xengineers.ai August 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared helpers for generating Zicbo (cache-block operation) exception tests
across different privilege-modes."""

from typing import NamedTuple

from testgen.asm.helpers import comment_banner
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData

CBO_INSTRS = ["inval", "clean", "flush", "zero"]
PREFETCH_INSTRS = ["i", "r", "w"]

class _CboField(NamedTuple):
    """One cbie/cbcfe/cbze binned config test: bit position, values walked, the
    instruction(s) executed, and the feature #ifdef guarding the block."""

    shift: int
    bins: list[str]
    instrs: list[str]
    guard: str

_CBO_FIELDS: dict[str, _CboField] = {
    "cbie": _CboField(
        shift=4, bins=["00", "01", "11"], instrs=["cbo.inval"], guard="ZICBOM_SUPPORTED"
    ),
    "cbcfe": _CboField(
        shift=6,
        bins=["0", "1"],
        instrs=["cbo.clean", "cbo.flush"],
        guard="ZICBOM_SUPPORTED",
    ),
    "cbze": _CboField(
        shift=7, bins=["0", "1"], instrs=["cbo.zero"], guard="ZICBOZ_SUPPORTED"
    ),
}


def _csrw(csr: str, reg: int, mode: str) -> str:
    """Return a csrw instruction: direct in M-mode, routed through T-SBI otherwise."""
    instr = f"csrw  {csr}, x{reg}"
    return instr if mode == "Sm" else tsbi_call(instr)


def goto_mode(mode: str) -> str:
    """Return the T-SBI hop into ``mode`` ("S" or "U")."""
    if mode == "S":
        return "RVTEST_TSBI_GOTO_SMODE  # Run tests in supervisor mode"
    if mode == "U":
        return "RVTEST_TSBI_GOTO_UMODE  # Run tests in user mode"
    raise ValueError(f"no T-SBI hop for mode {mode!r}")


def _mode_tag(mode: str, cross_senvcfg: bool) -> str:
    """Test-name mode suffix."""
    if not cross_senvcfg:
        return ""
    return f"_mode{'1' if mode == 'S' else '0'}"


def cbo_config_helper(
    test_data: TestData,
    covergroup: str,
    field: str,  # "cbie" | "cbcfe" | "cbze" -- looked up in _CBO_FIELDS
    *,
    description: str,
    mode: str,  # "Sm" | "S" | "U"
    cross_senvcfg: bool = False,
) -> list[str]:
    """Generate the cbie/cbcfe/cbze-style tests: execute ``field``'s instructions
    with menvcfg (optionally crossed with senvcfg) walked over ``field``'s bins,
    for a single ``mode``."""

    assert not (mode == "Sm" and cross_senvcfg), "senvcfg is not applicable in M-mode"
    cfg = _CBO_FIELDS[field]
    coverpoint = f"cp_{field}"
    shift, bins, instrs, guard = cfg["shift"], cfg["bins"], cfg["instrs"], cfg["guard"]

    addr_reg, cfg_reg = test_data.int_regs.get_registers(2)
    mode_tag = _mode_tag(mode, cross_senvcfg)

    lines = [comment_banner(coverpoint, description), "", f"#ifdef {guard}"]

    for m_val in bins:
        for s_val in bins if cross_senvcfg else [None]:
            senvcfg_tag = f"_senvcfg.{field}{s_val}" if cross_senvcfg else ""

            lines.extend(
                [
                    f"LA(x{addr_reg}, scratch)",
                    f"LI(x{cfg_reg}, {int(m_val, 2) << shift})",
                    _csrw("menvcfg", cfg_reg, mode),
                ]
            )
            if cross_senvcfg:
                lines.extend(
                    [
                        f"LI(x{cfg_reg}, {int(s_val, 2) << shift})",
                        _csrw("senvcfg", cfg_reg, mode),
                    ]
                )
            lines.append("nop")

            for instr in instrs:
                name = f"{instr}{mode_tag}_menvcfg.{field}{m_val}{senvcfg_tag}"
                lines.extend(
                    [
                        test_data.add_testcase(name, coverpoint, covergroup),
                        f"{instr}    0(x{addr_reg})",
                    ]
                )
    lines.append("#endif")

    test_data.int_regs.return_registers([addr_reg, cfg_reg])
    return lines


def cbo_access_fault_helper(
    test_data: TestData,
    covergroup: str,
    *,
    description: str,
    mode: str,
    cross_senvcfg: bool = False,
) -> list[str]:
    """Generate cbo/prefetch access-fault tests against RVMODEL_ACCESS_FAULT_ADDRESS."""
    assert not (mode == "Sm" and cross_senvcfg), "senvcfg is not applicable in M-mode"
    coverpoint = "cp_cbo_access_fault"
    addr_reg, cfg_reg = test_data.int_regs.get_registers(2)
    mode_tag = _mode_tag(mode, cross_senvcfg)

    lines = ["#ifdef RVMODEL_ACCESS_FAULT_ADDRESS", comment_banner(coverpoint, description), ""]

    for cbo in CBO_INSTRS:
        lines.append("#ifdef ZICBOZ_SUPPORTED" if cbo == "zero" else "#ifdef ZICBOM_SUPPORTED")
        lines.extend(
            [
                f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
                f"LI(x{cfg_reg}, 240)",  # setting all relevant bits in menvcfg to 1
                _csrw("menvcfg", cfg_reg, mode),
            ]
        )
        if cross_senvcfg:
            lines.append(_csrw("senvcfg", cfg_reg, mode))
        lines.extend(
            [
                "nop",
                test_data.add_testcase(f"cbo.{cbo}{mode_tag}_access_fault_0", coverpoint, covergroup),
                f"cbo.{cbo}    0(x{addr_reg})",
                f"addi x{addr_reg}, x{addr_reg}, 1  # attempt access again with misalignment",
                test_data.add_testcase(f"cbo.{cbo}{mode_tag}_access_fault_1", coverpoint, covergroup),
                f"cbo.{cbo}    0(x{addr_reg})",
                "#endif",
            ]
        )

    for prefetch in PREFETCH_INSTRS:
        lines.extend(
            [
                f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
                f"LI(x{cfg_reg}, 240)",  # setting all relevant bits in menvcfg to 1
                _csrw("menvcfg", cfg_reg, mode),
            ]
        )
        if cross_senvcfg:
            lines.append(_csrw("senvcfg", cfg_reg, mode))
        lines.extend(
            [
                "nop",
                test_data.add_testcase(f"prefetch.{prefetch}{mode_tag}_access_fault_0", coverpoint, covergroup),
                f"prefetch.{prefetch}    0(x{addr_reg})",
                f"addi x{addr_reg}, x{addr_reg}, 1  # attempt access again with misalignment",
                test_data.add_testcase(f"prefetch.{prefetch}{mode_tag}_access_fault_1", coverpoint, covergroup),
                f"prefetch.{prefetch}    0(x{addr_reg})",
            ]
        )

    lines.append("#endif")

    test_data.int_regs.return_registers([addr_reg, cfg_reg])
    return lines


def cbo_misaligned_helper(
    test_data: TestData,
    covergroup: str,
    *,
    description: str,
    mode: str,
    cross_senvcfg: bool = False,
) -> list[str]:
    """Generate cbo/prefetch misaligned-address trap tests."""
    assert not (mode == "Sm" and cross_senvcfg), "senvcfg is not applicable in M-mode"
    coverpoint = "cp_cbo_address_misaligned"
    addr_reg, cfg_reg = test_data.int_regs.get_registers(2)
    mode_tag = _mode_tag(mode, cross_senvcfg)

    lines = [comment_banner(coverpoint, description), ""]

    for cbo in CBO_INSTRS:
        lines.append("#ifdef ZICBOZ_SUPPORTED" if cbo == "zero" else "#ifdef ZICBOM_SUPPORTED")
        lines.extend(
            [
                f"LA(x{addr_reg}, scratch)",
                f"addi x{addr_reg}, x{addr_reg}, 1",
                f"LI(x{cfg_reg}, 240)",  # setting all relevant bits in menvcfg to 1
                _csrw("menvcfg", cfg_reg, mode),
            ]
        )
        if cross_senvcfg:
            lines.append(_csrw("senvcfg", cfg_reg, mode))
        lines.extend(
            [
                "nop",
                test_data.add_testcase(f"cbo.{cbo}{mode_tag}_misaligned", coverpoint, covergroup),
                f"cbo.{cbo}    0(x{addr_reg})",
                "#endif",
            ]
        )

    for prefetch in PREFETCH_INSTRS:
        lines.extend(
            [
                f"LA(x{addr_reg}, scratch)",
                f"addi x{addr_reg}, x{addr_reg}, 1",
                f"LI(x{cfg_reg}, 240)",  # setting all relevant bits in menvcfg to 1
                _csrw("menvcfg", cfg_reg, mode),
            ]
        )
        if cross_senvcfg:
            lines.append(_csrw("senvcfg", cfg_reg, mode))
        lines.extend(
            [
                "nop",
                "# No need to gate prefetch instructions with ZICBOP_SUPPORTED because they are hints that fall back to defined behavior",
                test_data.add_testcase(f"prefetch.{prefetch}{mode_tag}_misaligned", coverpoint, covergroup),
                f"prefetch.{prefetch}    0(x{addr_reg})",
            ]
        )

    test_data.int_regs.return_registers([addr_reg, cfg_reg])
    return lines
