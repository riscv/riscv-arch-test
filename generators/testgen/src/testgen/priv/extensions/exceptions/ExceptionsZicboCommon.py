##################################
# priv/extensions/exceptions/ExceptionsZicboCommon.py
#
# Shared Zicbo extension exception test generation.
# aman.murad@10xengineers.ai August 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared helpers for generating Zicbo (cache-block operation) exception tests
across different privilege-modes."""

import itertools
from collections.abc import Callable
from typing import NamedTuple

from testgen.asm.helpers import comment_banner, gated, write_sigupd
from testgen.asm.tsbi import tsbi_call_or_direct
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk

CBO_INSTRS = ["inval", "clean", "flush", "zero"]
PREFETCH_INSTRS = ["i", "r", "w"]

_ENVCFG_ALL_ENABLE = 0b11110000  # [7:4] = cbze,cbcfe,cbie: enable all cbo ops

_CBCFE_BIT = 1 << 6
_CBIE_ENABLED_BINS = ["01", "11"]  # 00 makes cbo.inval illegal and 10 is reserved

# Words of the cache block checked one at a time. scratch is 256 byte aligned and
# 264 bytes long, so it holds a whole block of up to _MAX_CHECKED_BLOCK bytes plus
# the first word of the next block.
_MAX_CHECKED_BLOCK = 256
_OLD_PATTERN_BASE = 0x5A5A0000
_BEYOND_PATTERN_BASE = 0x3C3C0000


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


def _cbo_test(
    instr: str,
    name: str,
    coverpoint: str,
    covergroup: str,
    addr_reg: int,
    val_reg: int,
    test_data: TestData,
) -> list[str]:
    lines = []
    if instr == "cbo.zero":
        lines.extend(
            [
                "# Store a nonzero value so the test can check cbo.zero",
                f"LI(x{val_reg}, {0x0C0B0000:#x})",
                f"sw x{val_reg}, 0(x{addr_reg})",
            ]
        )
    lines.extend(
        [
            test_data.add_testcase(name, coverpoint, covergroup),
            f"{instr}    0(x{addr_reg})",
        ]
    )
    if instr == "cbo.zero":
        lines.extend(
            [
                f"lw x{val_reg}, 0(x{addr_reg})",
                write_sigupd(val_reg, test_data),
            ]
        )
    return lines


def _csr_op(op: str, csr: str, reg: int, mode: str) -> str:
    """Return a CSR instruction (csrs/csrc/csrw on ``csr`` using ``reg``),
    issued directly when ``mode`` has direct access to ``csr``, and routed
    through T-SBI otherwise."""
    instr = f"{op}  {csr}, x{reg}"
    return tsbi_call_or_direct(instr, "M" if mode == "Sm" else mode)


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
    bins: list[str] | None = None,
    extra_set: int = 0,
    case: Callable[[str, str, str | None, int, int], list[str]] | None = None,
) -> list[str]:
    """Generate the cbie/cbcfe/cbze-style tests: execute ``field``'s instructions
    with menvcfg (optionally crossed with senvcfg) walked over ``field``'s bins,
    for a single ``mode``. ``bins`` overrides the values walked and ``extra_set``
    gives envcfg bits to keep set. ``case(tag, m_val, s_val, addr_reg, val_reg)``
    replaces the per-instruction tests; ``s_val`` is None when senvcfg is not set."""
    assert not (mode == "Sm" and cross_senvcfg), "senvcfg is not applicable in M-mode"
    cfg = _CBO_FIELDS[field]
    coverpoint = f"cp_{field}"
    shift, instrs, guard = cfg.shift, cfg.instrs, cfg.guard
    bins = bins or cfg.bins
    width = len(bins[0])
    field_mask = ((1 << width) - 1) << shift | extra_set
    mask_bits = field_mask.bit_length()
    mode_tag = _mode_tag(mode, cross_senvcfg)

    description = f"Exercise {', '.join(instrs)} across menvcfg.{field}"

    addr_reg, cfg_reg, mask_reg, val_reg = test_data.int_regs.get_registers(4)

    def tests(tag: str, m_val: str, s_val: str | None) -> list[str]:
        if case:
            return case(tag, m_val, s_val, addr_reg, val_reg)
        return [
            line
            for instr in instrs
            for line in _cbo_test(instr, f"{instr}{tag}", coverpoint, covergroup, addr_reg, val_reg, test_data)
        ]

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
        if int(m_val, 2) or extra_set:
            lines.extend(
                [
                    f"LI(x{cfg_reg}, 0b{int(m_val, 2) << shift | extra_set:0{mask_bits}b})",
                    _csr_op("csrs", "menvcfg", cfg_reg, mode),
                ]
            )

        if not cross_senvcfg:
            lines.extend(tests(f"{mode_tag}_menvcfg.{field}{m_val}", m_val, None))
        else:
            lines.append("#ifdef S1P12P0_OR_LATER_SUPPORTED")
            for s_val in bins:
                senvcfg_tag = f"_senvcfg.{field}{s_val}"
                lines.append(_csr_op("csrc", "senvcfg", mask_reg, mode))
                if int(s_val, 2) or extra_set:
                    lines.extend(
                        [
                            f"LI(x{cfg_reg}, 0b{int(s_val, 2) << shift | extra_set:0{mask_bits}b})",
                            _csr_op("csrs", "senvcfg", cfg_reg, mode),
                        ]
                    )
                lines.extend(tests(f"{mode_tag}_menvcfg.{field}{m_val}{senvcfg_tag}", m_val, s_val))
            lines.append("#else")
            lines.extend(tests(f"{mode_tag}_menvcfg.{field}{m_val}", m_val, None))
            lines.append("#endif // S1P12P0_OR_LATER_SUPPORTED")

    lines.append("#endif")
    if mode == "Sm":
        lines.append("#endif // U_SUPPORTED")
    lines.append("#endif // SM1P12P0_OR_LATER_SUPPORTED")

    test_data.int_regs.return_registers([addr_reg, cfg_reg, mask_reg, val_reg])
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
    """Generate cbo/prefetch tests showing a misaligned address does not trap."""
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


def _block_gate(off: int) -> str | None:
    """Gate that assembles code only when the cache block reaches ``off``."""
    return f"UDB_CACHE_BLOCK_SIZE > {off}" if off else None


def _fill_block(test_data: TestData, addr_reg: int, base: int) -> list[str]:
    """Write ``base``, ``base+2``, ``base+4`` ... over the words of the cache block, so
    every word holds a different value. The step of 2 leaves bit 0 of each word free:
    filling once from an even ``base`` and again from ``base + 1`` gives each word an
    old and a new value that differ only in bit 0."""
    pat_reg = test_data.int_regs.get_register()
    lines = [f"LI(x{pat_reg}, {base:#x})"]
    for off in range(0, _MAX_CHECKED_BLOCK, 4):
        step = [] if off == 0 else [f"addi x{pat_reg}, x{pat_reg}, 2"]
        lines.extend(gated([*step, f"sw   x{pat_reg}, {off}(x{addr_reg})"], _block_gate(off)))
    test_data.int_regs.return_register(pat_reg)
    return lines


def cbo_inval_data_helper(
    test_data: TestData,
    covergroup: str,
    *,
    mode: str,  # "Sm" | "S" | "U"
) -> list[str]:
    """Generate the cbo.inval data tests: clean a known pattern out to memory, dirty
    the block with a pattern differing in one bit per word, then cbo.inval and check
    the whole block plus the word beyond it, for each enabled xenvcfg.CBIE setting."""
    coverpoint = "cp_cbo_inval_data"
    case_index = itertools.count()  # makes each case use its own pattern

    def case(tag: str, m_val: str, s_val: str | None, addr_reg: int, val_reg: int) -> list[str]:
        # cbo.inval really invalidates unless an xenvcfg.CBIE of 01 turns it into a flush.
        # M-mode has no xenvcfg.CBIE, so it may do either.
        real_inval = mode == "Sm" or (m_val == "11" and not (mode == "U" and s_val == "01"))
        old_base = _OLD_PATTERN_BASE + (next(case_index) << 8)
        lines = [
            f"# Write the old pattern ({old_base:#x}, +2 per word) and clean it out to memory",
            *_fill_block(test_data, addr_reg, old_base),
            f"cbo.clean   0(x{addr_reg})",
            "# Dirty the block with the new pattern, which differs from the old one only in bit 0",
            *_fill_block(test_data, addr_reg, old_base + 1),
            "# Dirty the first word of the next block, which cbo.inval must leave alone",
            f"LI(x{val_reg}, {_BEYOND_PATTERN_BASE:#x})",
            f"sw   x{val_reg}, UDB_CACHE_BLOCK_SIZE(x{addr_reg})",
            test_data.add_testcase(f"cbo.inval_data{tag}", coverpoint, covergroup),
            f"cbo.inval   0(x{addr_reg})",
            f"lw   x{val_reg}, UDB_CACHE_BLOCK_SIZE(x{addr_reg})",
            write_sigupd(val_reg, test_data),
            "# Each word reads back its old or new value (bit 0 masked)"
            if real_inval
            else "# cbo.inval flushed the block, so each word must read back its new value",
        ]
        for off in range(0, _MAX_CHECKED_BLOCK, 4):
            check = [f"lw   x{val_reg}, {off}(x{addr_reg})"]
            if real_inval:
                check.append(f"andi x{val_reg}, x{val_reg}, -2")
            check.append(write_sigupd(val_reg, test_data))
            lines.extend(gated(check, _block_gate(off)))
        return lines

    if mode == "Sm":
        addr_reg, val_reg = test_data.int_regs.get_registers(2)
        body = [f"LA(x{addr_reg}, scratch)", *case("_m", "", None, addr_reg, val_reg)]
        test_data.int_regs.return_registers([addr_reg, val_reg])
        return ["#ifdef ZICBOM_SUPPORTED", "#ifdef UDB_CACHE_BLOCK_SIZE", *body, "#endif", "#endif"]

    # cbo.clean needs cbcfe set. Cross senvcfg in U-mode too, since it gates cbo.inval there.
    body = cbo_config_helper(
        test_data,
        covergroup,
        "cbie",
        mode=mode,
        cross_senvcfg=True,
        bins=_CBIE_ENABLED_BINS,
        extra_set=_CBCFE_BIT,
        case=case,
    )
    return ["#ifdef UDB_CACHE_BLOCK_SIZE", *body, "#endif"]


def emit_suite(
    test_data: TestData,
    covergroup: str,
    mode: str,  # "Sm" | "S" | "U"
    group: str,
    cross_senvcfg: bool = False,
    mode_entry: bool = False,
) -> list[TestChunk]:
    """Generate the cbie/cbcfe/cbze + access-fault + misaligned + cbo.inval data tests."""

    tc = test_data.begin_test_chunk(group)
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

    chunks = [test_data.end_test_chunk()]

    tc = test_data.begin_test_chunk()
    if mode_entry:
        tc.code.append(f"RVTEST_TSBI_GOTO_{mode}MODE  # enter {mode}-mode")
    tc.code.extend(cbo_inval_data_helper(test_data, covergroup, mode=mode))
    chunks.append(test_data.end_test_chunk())

    return chunks
