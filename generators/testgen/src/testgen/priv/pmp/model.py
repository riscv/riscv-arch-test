##################################
# priv/pmp/model.py
#
# Data model for the pure (non-virtual-memory) PMP suite generators.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Declarative data model for the generated ``tests/priv/pmp`` test suites.

These suites are machine-mode PMP tests with no page tables, so they share
nothing with the Sv* model in :mod:`testgen.priv.sv.model` beyond the general
"describe the file, render it" shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Xlen:
    """The XLEN-dependent constants a PMP test needs."""

    bits: int  # 32 | 64
    outdir: str  # "pmp32" | "pmp64"
    march: str
    cfgs_per_reg: int  # PMP entries described by one pmpcfg CSR
    cfg_step: int  # CSR-number step between consecutive legal pmpcfg CSRs

    @property
    def cfg_rept(self) -> str:
        """`.rept` count that walks every legal pmpcfg CSR."""
        return f"UDB_NUM_PMP_ENTRIES/{self.cfgs_per_reg}"


XLENS: dict[int, Xlen] = {
    32: Xlen(bits=32, outdir="pmp32", march="rv32i_zicsr_zifencei", cfgs_per_reg=4, cfg_step=1),
    64: Xlen(bits=64, outdir="pmp64", march="rv64i_zicsr_zifencei", cfgs_per_reg=8, cfg_step=2),
}


@dataclass(frozen=True)
class PmpFile:
    """Complete description of one generated PMP .S test file."""

    filename: str
    xlen: Xlen
    banner: str  # verbatim comment block: Title/Authors/Description/Coverpoints/Test Cases
    required_extensions: tuple[str, ...]
    sigupd: int
    body: tuple[str, ...]  # assembly between `main:` and RVTEST_CODE_END
    params: tuple[str, ...] = ()  # YAML '# params:' entries; MXLEN is added automatically
    march: str | None = None  # defaults to xlen.march
    trap_sigupd: int | None = None
    priv_test: bool = True  # emit `#define RVTEST_PRIV_TEST`
    extra_defines: tuple[str, ...] = ()  # extra #defines before the framework #include
    post_include_defines: tuple[str, ...] = ()  # #defines that depend on riscv_arch_test.h
    macro_blocks: tuple[str, ...] = ()  # verbatim local .macro blocks, emitted after RVTEST_BEGIN
    data: tuple[str, ...] = ()  # lines between RVTEST_DATA_BEGIN and RVTEST_DATA_END
    sig_strs: tuple[tuple[str, str], ...] = ()  # (label, message) -> `<label>_str: .string "\"<msg>\""`
    data_align: int | None = None  # `.p2align N` emitted at the top of the data section
    copyright: tuple[str, ...] = field(default_factory=tuple)  # extra copyright lines above the title
