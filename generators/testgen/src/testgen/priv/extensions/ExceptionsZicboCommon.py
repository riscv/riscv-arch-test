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
from testgen.data.test_chunk import TestChunk

CBO_INSTRS = ["inval", "clean", "flush", "zero"]
PREFETCH_INSTRS = ["i", "r", "w"]

_ENVCFG_ALL_ENABLE = 0b11110000  # [7:4] = cbze,cbcfe,cbie: enable all cbo ops


class _CboField(NamedTuple):
    """One cbie/cbcfe/cbze binned config test: bit position, values walked, the
    instruction(s) executed, and the feature #ifdef guarding the block."""

    shift: int
    bins: list[str]
    instrs: list[str]
    guard: str


_CBO_FIELDS: dict[str, _CboField] = {
    "cbie": _CboField(shift=4, bins=["00", "01", "11"], instrs=["cbo.inval"], guard="ZICBOM_SUPPORTED"),
    "cbcfe": _CboField(
        shift=6,
        bins=["0", "1"],
        instrs=["cbo.clean", "cbo.flush"],
        guard="ZICBOM_SUPPORTED",
    ),
    "cbze": _CboField(shift=7, bins=["0", "1"], instrs=["cbo.zero"], guard="ZICBOZ_SUPPORTED"),
}


def _csr_op(op: str, csr: str, reg: int, mode: str) -> str:
    """Return a CSR instruction (csrs/csrc/csrw on ``csr`` using ``reg``),
    issued directly when ``mode`` has direct access to ``csr``, and routed
    through T-SBI otherwise."""
    instr = f"{op}  {csr}, x{reg}"
    needs_tsbi = (mode == "U") if csr == "senvcfg" else (mode != "Sm")
    return tsbi_call(instr) if needs_tsbi else instr


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
    mode: str,  # "Sm" | "S" | "U"
    cross_senvcfg: bool = False,
) -> list[str]:
    """Generate the cbie/cbcfe/cbze-style tests: execute ``field``'s instructions
    with menvcfg (optionally crossed with senvcfg) walked over ``field``'s bins,
    for a single ``mode``."""
    assert not (mode == "Sm" and cross_senvcfg), "senvcfg is not applicable in M-mode"
    cfg = _CBO_FIELDS[field]
    coverpoint = f"cp_{field}"
    shift, bins, instrs, guard = cfg.shift, cfg.bins, cfg.instrs, cfg.guard
    width = len(bins[0])
    field_mask = ((1 << width) - 1) << shift
    mask_bits = shift + width
    mode_tag = _mode_tag(mode, cross_senvcfg)

    description = f"Exercise {', '.join(instrs)} across menvcfg.{field}"

    addr_reg, cfg_reg, mask_reg = test_data.int_regs.get_registers(3)

    lines = [
        comment_banner(coverpoint, description),
        "",
        "#ifdef SM1P12P0_OR_LATER_SUPPORTED",
    ]
    if mode == "Sm":
        lines.append("#ifdef U_SUPPORTED")
    lines.extend(
        [
            f"#ifdef {guard}",
            f"LA(x{addr_reg}, scratch)",
            f"LI(x{mask_reg}, 0b{field_mask:0{mask_bits}b})  # {field} field mask",
        ]
    )

    for m_val in bins:
        lines.extend(
            [
                "",
                f"# menvcfg.{field} = {m_val}",
                _csr_op("csrc", "menvcfg", mask_reg, mode),
            ]
        )
        if int(m_val, 2):
            lines.extend(
                [
                    f"LI(x{cfg_reg}, 0b{int(m_val, 2) << shift:0{mask_bits}b})",
                    _csr_op("csrs", "menvcfg", cfg_reg, mode),
                ]
            )

        if not cross_senvcfg:
            for instr in instrs:
                name = f"{instr}{mode_tag}_menvcfg.{field}{m_val}"
                lines.extend(
                    [
                        test_data.add_testcase(name, coverpoint, covergroup),
                        f"{instr}    0(x{addr_reg})",
                    ]
                )
        else:
            lines.append("#ifdef S1P12P0_OR_LATER_SUPPORTED")
            for s_val in bins:
                senvcfg_tag = f"_senvcfg.{field}{s_val}"
                lines.append(_csr_op("csrc", "senvcfg", mask_reg, mode))
                if int(s_val, 2):
                    lines.extend(
                        [
                            f"LI(x{cfg_reg}, 0b{int(s_val, 2) << shift:0{mask_bits}b})",
                            _csr_op("csrs", "senvcfg", cfg_reg, mode),
                        ]
                    )
                for instr in instrs:
                    name = f"{instr}{mode_tag}_menvcfg.{field}{m_val}{senvcfg_tag}"
                    lines.extend(
                        [
                            test_data.add_testcase(name, coverpoint, covergroup),
                            f"{instr}    0(x{addr_reg})",
                        ]
                    )
            lines.append("#else")
            for instr in instrs:
                name = f"{instr}{mode_tag}_menvcfg.{field}{m_val}"
                lines.extend(
                    [
                        test_data.add_testcase(name, coverpoint, covergroup),
                        f"{instr}    0(x{addr_reg})",
                    ]
                )
            lines.append("#endif // S1P12P0_OR_LATER_SUPPORTED")

    lines.append("#endif")
    if mode == "Sm":
        lines.append("#endif // U_SUPPORTED")
    lines.append("#endif // SM1P12P0_OR_LATER_SUPPORTED")

    test_data.int_regs.return_registers([addr_reg, cfg_reg, mask_reg])
    return lines


def cbo_access_fault_helper(
    test_data: TestData,
    covergroup: str,
    *,
    mode: str,
    cross_senvcfg: bool = False,
) -> list[str]:
    """Generate cbo/prefetch access-fault tests against RVMODEL_ACCESS_FAULT_ADDRESS."""
    assert not (mode == "Sm" and cross_senvcfg), "senvcfg is not applicable in M-mode."
    coverpoint = "cp_cbo_access_fault"
    addr_reg, cfg_reg = test_data.int_regs.get_registers(2)
    mode_tag = _mode_tag(mode, cross_senvcfg)

    lines = [
        "#ifdef RVMODEL_ACCESS_FAULT_ADDRESS",
        comment_banner(
            coverpoint,
            "cbo.{inval,clean,flush,zero} and prefetch.{i,r,w} to\nRVMODEL_ACCESS_FAULT_ADDRESS raise an access fault",
        ),
        "",
        "#ifdef SM1P12P0_OR_LATER_SUPPORTED",
    ]
    if mode == "Sm":
        lines.append("#ifdef U_SUPPORTED")
    lines.extend(
        [
            f"LI(x{cfg_reg}, 0b{_ENVCFG_ALL_ENABLE:08b})  # enable cbie/cbcfe/cbze",
            _csr_op("csrs", "menvcfg", cfg_reg, mode),
        ]
    )
    if mode == "Sm":
        lines.append("#endif // U_SUPPORTED")
    lines.append("#endif // SM1P12P0_OR_LATER_SUPPORTED")

    if cross_senvcfg:
        lines.extend(
            [
                "#ifdef S1P12P0_OR_LATER_SUPPORTED",
                f"LI(x{cfg_reg}, 0b{_ENVCFG_ALL_ENABLE:08b})  # enable cbie/cbcfe/cbze",
                _csr_op("csrs", "senvcfg", cfg_reg, mode),
                "#endif // S1P12P0_OR_LATER_SUPPORTED",
            ]
        )

    for cbo in CBO_INSTRS:
        lines.append("#ifdef ZICBOZ_SUPPORTED" if cbo == "zero" else "#ifdef ZICBOM_SUPPORTED")
        lines.extend(
            [
                f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
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
                test_data.add_testcase(f"prefetch.{prefetch}{mode_tag}_access_fault_0", coverpoint, covergroup),
                f"prefetch.{prefetch}    0(x{addr_reg})",
                f"addi x{addr_reg}, x{addr_reg}, 1  # attempt access again with misalignment",
                test_data.add_testcase(f"prefetch.{prefetch}{mode_tag}_access_fault_1", coverpoint, covergroup),
                f"prefetch.{prefetch}    0(x{addr_reg})",
            ]
        )

    lines.append("#endif // RVMODEL_ACCESS_FAULT_ADDRESS")

    test_data.int_regs.return_registers([addr_reg, cfg_reg])
    return lines


def cbo_misaligned_helper(
    test_data: TestData,
    covergroup: str,
    *,
    mode: str,
    cross_senvcfg: bool = False,
) -> list[str]:
    """Generate cbo/prefetch misaligned-address trap tests."""
    assert not (mode == "Sm" and cross_senvcfg), "senvcfg is not applicable in M-mode"
    coverpoint = "cp_cbo_address_misaligned"
    addr_reg, cfg_reg = test_data.int_regs.get_registers(2)
    mode_tag = _mode_tag(mode, cross_senvcfg)

    lines = [
        comment_banner(
            coverpoint,
            "cbo.{inval,clean,flush,zero} and prefetch.{i,r,w}\nto a misaligned address do not trap",
        ),
        "",
        "#ifdef SM1P12P0_OR_LATER_SUPPORTED",
    ]
    if mode == "Sm":
        lines.append("#ifdef U_SUPPORTED")
    lines.extend(
        [
            f"LI(x{cfg_reg}, 0b{_ENVCFG_ALL_ENABLE:08b})  # enable cbie/cbcfe/cbze",
            _csr_op("csrs", "menvcfg", cfg_reg, mode),
        ]
    )
    if mode == "Sm":
        lines.append("#endif // U_SUPPORTED")
    lines.append("#endif // SM1P12P0_OR_LATER_SUPPORTED")

    if cross_senvcfg:
        lines.extend(
            [
                "#ifdef S1P12P0_OR_LATER_SUPPORTED",
                f"LI(x{cfg_reg}, 0b{_ENVCFG_ALL_ENABLE:08b})  # enable cbie/cbcfe/cbze",
                _csr_op("csrs", "senvcfg", cfg_reg, mode),
                "#endif // S1P12P0_OR_LATER_SUPPORTED",
            ]
        )

    for cbo in CBO_INSTRS:
        lines.append("#ifdef ZICBOZ_SUPPORTED" if cbo == "zero" else "#ifdef ZICBOM_SUPPORTED")
        lines.extend(
            [
                f"LA(x{addr_reg}, scratch)",
                f"addi x{addr_reg}, x{addr_reg}, 1",
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
                "# No need to gate prefetch instructions with ZICBOP_SUPPORTED because they are hints that fall back to defined behavior",
                test_data.add_testcase(f"prefetch.{prefetch}{mode_tag}_misaligned", coverpoint, covergroup),
                f"prefetch.{prefetch}    0(x{addr_reg})",
            ]
        )

    test_data.int_regs.return_registers([addr_reg, cfg_reg])
    return lines


def emit_suite(
    test_data: TestData,
    covergroup: str,
    mode: str,  # "Sm" | "S" | "U"
    cross_senvcfg: bool = False,
    mode_entry: bool = False,
) -> list[TestChunk]:
    """Generate the cbie/cbcfe/cbze + access-fault + misaligned tests."""

    tc = test_data.begin_test_chunk()
    lines = tc.code

    if mode_entry:
        lines.append(f"RVTEST_TSBI_GOTO_{mode}MODE  # enter {mode}-mode")

    for field in ("cbie", "cbcfe", "cbze"):
        lines.extend(
            cbo_config_helper(
                test_data,
                covergroup,
                field,
                mode=mode,
                cross_senvcfg=cross_senvcfg,
            )
        )

    lines.extend(
        cbo_access_fault_helper(
            test_data,
            covergroup,
            mode=mode,
            cross_senvcfg=cross_senvcfg,
        )
    )

    lines.extend(
        cbo_misaligned_helper(
            test_data,
            covergroup,
            mode=mode,
            cross_senvcfg=cross_senvcfg,
        )
    )

    return [test_data.end_test_chunk()]
