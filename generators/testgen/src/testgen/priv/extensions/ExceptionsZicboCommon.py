##################################
# priv/extensions/ExceptionsZicboCommon.py
#
# Shared Zicbo extension exception test generation.
# aman.murad@10xengineers.ai August 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared helpers for generating Zicbo (cache-block operation) exception tests
across different privilege-modes."""

from testgen.asm.helpers import comment_banner
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData

CBO_INSTRS = ["inval", "clean", "flush", "zero"]
PREFETCH_INSTRS = ["i", "r", "w"]


def _csrw(csr: str, reg: int, use_tsbi: bool) -> str:
    """Return a csrw instruction, routed through T-SBI when required."""
    instr = f"csrw  {csr}, x{reg}"
    return tsbi_call(instr) if use_tsbi else instr


def _goto_mode(mode: str) -> str:
    """Return the T-SBI hop into the given mode tag (``"1"`` = S, ``"0"`` = U)."""
    if mode == "0":
        return "RVTEST_TSBI_GOTO_UMODE  # Run tests in user mode"
    return "RVTEST_TSBI_GOTO_SMODE  # Run tests in supervisor mode"


def cbo_config_helper(
    test_data: TestData,
    covergroup: str,
    *,
    coverpoint: str,
    tag: str,
    shift: int,
    bins: list[str],
    instrs: list[str],
    guard: str,
    description: str,
    use_tsbi: bool,
    modes: list[str] | None = None,
    cross_senvcfg: bool = False,
) -> list[str]:
    """Generate the cbie/cbcfe/cbze-style tests: execute ``instrs`` with menvcfg
    (optionally crossed with senvcfg, optionally per mode) walked over ``bins``.
    """
    addr_reg, cfg_reg = test_data.int_regs.get_registers(2)

    lines = [comment_banner(coverpoint, description), "", f"#ifdef {guard}"]

    for mode in modes or [None]:
        if mode is not None:
            lines.append(_goto_mode(mode))
        mode_tag = f"_mode{mode}" if mode is not None else ""

        for m_val in bins:
            for s_val in bins if cross_senvcfg else [None]:
                senvcfg_tag = f"_senvcfg.{tag}{s_val}" if cross_senvcfg else ""

                lines.extend(
                    [
                        f"LA(x{addr_reg}, scratch)",
                        f"LI(x{cfg_reg}, {int(m_val, 2) << shift})",
                        _csrw("menvcfg", cfg_reg, use_tsbi),
                    ]
                )

                if cross_senvcfg:
                    assert s_val is not None
                    lines.extend(
                        [
                            f"LI(x{cfg_reg}, {int(s_val, 2) << shift})",
                            _csrw("senvcfg", cfg_reg, use_tsbi),
                        ]
                    )
                lines.append("nop")

                for instr in instrs:
                    name = f"{instr}{mode_tag}_menvcfg.{tag}{m_val}{senvcfg_tag}"
                    lines.extend(
                        [
                            test_data.add_testcase(name, coverpoint, covergroup),
                            f"{instr}    (x{addr_reg})",
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
    use_tsbi: bool,
    modes: list[str] | None = None,
    cross_senvcfg: bool = False,
) -> list[str]:
    """Generate cbo/prefetch access-fault tests against RVMODEL_ACCESS_FAULT_ADDRESS."""
    coverpoint = "cp_cbo_access_fault"
    addr_reg, cfg_reg = test_data.int_regs.get_registers(2)

    lines = ["#ifdef RVMODEL_ACCESS_FAULT_ADDRESS", comment_banner(coverpoint, description), ""]

    for mode in modes or [None]:
        if mode is not None:
            lines.append(_goto_mode(mode))
        mode_tag = f"_mode{mode}" if mode is not None else ""

        for cbo in CBO_INSTRS:
            lines.append("#ifdef ZICBOZ_SUPPORTED" if cbo == "zero" else "#ifdef ZICBOM_SUPPORTED")
            lines.extend(
                [
                    f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
                    f"LI(x{cfg_reg}, 240)",  # setting all relevant bits in menvcfg to 1
                    _csrw("menvcfg", cfg_reg, use_tsbi),
                ]
            )
            if cross_senvcfg:
                lines.append(_csrw("senvcfg", cfg_reg, use_tsbi))
            lines.extend(
                [
                    "nop",
                    test_data.add_testcase(f"cbo.{cbo}{mode_tag}_access_fault_0", coverpoint, covergroup),
                    f"cbo.{cbo}    0(x{addr_reg})",
                    f"addi x{addr_reg}, x{addr_reg}, 1  # attempt access again with misalignment, check misaligned address is reported in mtval if applicable",
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
                    _csrw("menvcfg", cfg_reg, use_tsbi),
                ]
            )
            if cross_senvcfg:
                lines.append(_csrw("senvcfg", cfg_reg, use_tsbi))
            lines.extend(
                [
                    "nop",
                    "# No need to gate prefetch instructions with ZICBOP_SUPPORTED because they are hints that fall back to defined behavior",
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
    use_tsbi: bool,
    modes: list[str] | None = None,
    cross_senvcfg: bool = False,
) -> list[str]:
    """Generate cbo/prefetch misaligned-address trap tests."""
    coverpoint = "cp_cbo_address_misaligned"
    addr_reg, cfg_reg = test_data.int_regs.get_registers(2)

    lines = [comment_banner(coverpoint, description), ""]

    for mode in modes or [None]:
        if mode is not None:
            lines.append(_goto_mode(mode))
        mode_tag = f"_mode{mode}" if mode is not None else ""

        for cbo in CBO_INSTRS:
            lines.append("#ifdef ZICBOZ_SUPPORTED" if cbo == "zero" else "#ifdef ZICBOM_SUPPORTED")
            lines.extend(
                [
                    f"LA(x{addr_reg}, scratch)",
                    f"addi x{addr_reg}, x{addr_reg}, 1",
                    f"LI(x{cfg_reg}, 240)",  # setting all relevant bits in menvcfg to 1
                    _csrw("menvcfg", cfg_reg, use_tsbi),
                ]
            )
            if cross_senvcfg:
                lines.append(_csrw("senvcfg", cfg_reg, use_tsbi))
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
                    _csrw("menvcfg", cfg_reg, use_tsbi),
                ]
            )
            if cross_senvcfg:
                lines.append(_csrw("senvcfg", cfg_reg, use_tsbi))
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
