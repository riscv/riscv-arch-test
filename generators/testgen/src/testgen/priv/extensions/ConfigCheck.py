##################################
# priv/extensions/ConfigCheck.py
#
# ConfigCheck suite: does the DUT match its UDB config?
# SPDX-License-Identifier: Apache-2.0
##################################

"""Checks that the DUT matches its UDB config.

Run after Hello and before the certification suites. Each testcase reads one value
the config describes from the hart -- a misa bit, the mtvec modes, the number of
usable PMP entries, a satp mode, the writable medeleg bits, VLEN, whether an
extension's instruction executes -- and compares it with the value the config
implies, through RVTEST_CONFIG_CHECK. The testcase is named after the UDB parameter
or extension it checks.

The expected values come from the UDB defines when the test is assembled, not from
the reference model, so the same code checks sail.json on the reference model and the
DUT on the DUT. A mismatch prints both values and the test carries on, so one run
lists every disagreement. The suite claims no functional coverage.

Only parameters the reference model also takes from its config are checked; the others
would make the reference run fail on every config whose sail.json leaves them at the
default.
"""

from collections.abc import Callable

from testgen.asm.helpers import arch_block, comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

_CG = "ConfigCheck_cg"

# misa bits with a defined meaning. X (non-standard extensions) can't be derived from
# the config, the reserved letters are left to the Sm suite, and Q is left out because
# the reference model doesn't implement it.
_MISA_LETTERS = "ABCDEFHIMSUV"

# (name, MODE value, extension define) for the satp probes, per XLEN.
_SATP_MODES = {
    32: (("Sv32", 1, "SV32_SUPPORTED"),),
    64: (("Sv39", 8, "SV39_SUPPORTED"), ("Sv48", 9, "SV48_SUPPORTED"), ("Sv57", 10, "SV57_SUPPORTED")),
}
_SATP_MODE_SHIFT = {32: 31, 64: 60}
_SV_FOR_ASID = "(__riscv_xlen == 64 && defined(SV39_SUPPORTED)) || (__riscv_xlen == 32 && defined(SV32_SUPPORTED))"

# One instruction per extension: (bin, preprocessor condition, extensions to enable, instruction).
# {d} is a scratch destination, {a} holds the address of `scratch`, {b} a second source.
# The instruction must be 4 bytes, so the probe trap handler can skip it.
_EXTENSION_PROBES: tuple[tuple[str, str, tuple[str, ...], str], ...] = (
    ("Zifencei", "defined(ZIFENCEI_SUPPORTED)", ("zifencei",), "fence.i"),
    ("Zmmul", "defined(ZMMUL_SUPPORTED)", ("zmmul",), "mul x{d}, x{a}, x{b}"),
    ("Zba", "defined(ZBA_SUPPORTED)", ("zba",), "sh1add x{d}, x{a}, x{b}"),
    ("Zbb", "defined(ZBB_SUPPORTED)", ("zbb",), "andn x{d}, x{a}, x{b}"),
    ("Zbc", "defined(ZBC_SUPPORTED)", ("zbc",), "clmul x{d}, x{a}, x{b}"),
    ("Zbs", "defined(ZBS_SUPPORTED)", ("zbs",), "bset x{d}, x{a}, x{b}"),
    ("Zbkb", "defined(ZBKB_SUPPORTED)", ("zbkb",), "pack x{d}, x{a}, x{b}"),
    ("Zbkc", "defined(ZBKC_SUPPORTED)", ("zbkc",), "clmulh x{d}, x{a}, x{b}"),
    ("Zbkx", "defined(ZBKX_SUPPORTED)", ("zbkx",), "xperm8 x{d}, x{a}, x{b}"),
    ("Zicond", "defined(ZICOND_SUPPORTED)", ("zicond",), "czero.eqz x{d}, x{a}, x{b}"),
    ("Zimop", "defined(ZIMOP_SUPPORTED)", ("zimop",), "mop.r.0 x{d}, x{a}"),
    ("Zknh", "defined(ZKNH_SUPPORTED)", ("zknh",), "sha256sum0 x{d}, x{a}"),
    ("Zksh", "defined(ZKSH_SUPPORTED)", ("zksh",), "sm3p0 x{d}, x{a}"),
    ("Zksed", "defined(ZKSED_SUPPORTED)", ("zksed",), "sm4ed x{d}, x{a}, x{b}, 0"),
    ("Zkne", "defined(ZKNE_SUPPORTED) && __riscv_xlen == 64", ("zkne",), "aes64es x{d}, x{a}, x{b}"),
    ("Zkne_rv32", "defined(ZKNE_SUPPORTED) && __riscv_xlen == 32", ("zkne",), "aes32esi x{d}, x{a}, x{b}, 0"),
    ("Zknd", "defined(ZKND_SUPPORTED) && __riscv_xlen == 64", ("zknd",), "aes64ds x{d}, x{a}, x{b}"),
    ("Zknd_rv32", "defined(ZKND_SUPPORTED) && __riscv_xlen == 32", ("zknd",), "aes32dsi x{d}, x{a}, x{b}, 0"),
    ("Zaamo", "defined(ZAAMO_SUPPORTED)", ("zaamo",), "amoadd.w x{d}, x{b}, (x{a})"),
    ("Zalrsc", "defined(ZALRSC_SUPPORTED)", ("zalrsc",), "lr.w x{d}, (x{a})"),
    ("Zabha", "defined(ZABHA_SUPPORTED)", ("zaamo", "zabha"), "amoadd.b x{d}, x{b}, (x{a})"),
    ("Zacas", "defined(ZACAS_SUPPORTED)", ("zaamo", "zacas"), "amocas.w x{d}, x{b}, (x{a})"),
    ("Zicbom", "defined(ZICBOM_SUPPORTED)", ("zicbom",), "cbo.clean (x{a})"),
    # cbo.zero clears one cache block of `scratch`, which is 256-byte aligned and longer.
    (
        "Zicboz",
        "defined(ZICBOZ_SUPPORTED) && defined(UDB_CACHE_BLOCK_SIZE) && UDB_CACHE_BLOCK_SIZE <= 256",
        ("zicboz",),
        "cbo.zero (x{a})",
    ),
    ("Svinval", "defined(SVINVAL_SUPPORTED)", ("svinval",), "sinval.vma x0, x0"),
    ("Zfinx", "defined(ZFINX_SUPPORTED)", ("zfinx",), "fadd.s x{d}, x{a}, x{b}"),
    ("Zhinx", "defined(ZHINX_SUPPORTED)", ("zhinx",), "fadd.h x{d}, x{a}, x{b}"),
    ("Zhinxmin", "defined(ZHINXMIN_SUPPORTED)", ("zhinxmin",), "fcvt.s.h x{d}, x{a}"),
    # On RV32, Zdinx operands are even register pairs, which the allocator can't promise.
    ("Zdinx", "defined(ZDINX_SUPPORTED) && __riscv_xlen == 64", ("zdinx",), "fadd.d x{d}, x{a}, x{b}"),
    # The F-based probes run with mstatus.FS enabled (see _extensions).
    ("Zfh", "defined(ZFH_SUPPORTED)", ("zfh",), "fadd.h f1, f2, f3"),
    ("Zfhmin", "defined(ZFHMIN_SUPPORTED)", ("zfhmin",), "fcvt.s.h f1, f2"),
    ("Zfa", "defined(ZFA_SUPPORTED)", ("zfa",), "fminm.s f1, f2, f3"),
    ("Zfbfmin", "defined(ZFBFMIN_SUPPORTED)", ("zfbfmin",), "fcvt.s.bf16 f1, f2"),
    # Extensions recognised by the CSRs they add. M-mode can access all of them. Extensions
    # the reference model doesn't implement (Smaia, Smcsrind, Smctr, Smrnmi, ...) are left out.
    ("Zicntr", "defined(ZICNTR_SUPPORTED)", (), "csrr x{d}, CSR_CYCLE"),
    (
        "TIME_CSR_IMPLEMENTED",
        "defined(ZICNTR_SUPPORTED) && defined(UDB_TIME_CSR_IMPLEMENTED)",
        (),
        "csrr x{d}, CSR_TIME",
    ),
    ("Zihpm", "defined(ZIHPM_SUPPORTED)", (), "csrr x{d}, CSR_HPMCOUNTER3"),
    ("Zkr", "defined(ZKR_SUPPORTED)", (), "csrrw x{d}, CSR_SEED, x0"),
    ("Sstc", "defined(SSTC_SUPPORTED)", (), "csrr x{d}, CSR_STIMECMP"),
    ("Smstateen", "defined(SMSTATEEN_SUPPORTED)", (), "csrr x{d}, CSR_MSTATEEN0"),
    ("Sscofpmf", "defined(SSCOFPMF_SUPPORTED)", (), "csrr x{d}, CSR_SCOUNTOVF"),
    ("Smcntrpmf", "defined(SMCNTRPMF_SUPPORTED)", (), "csrr x{d}, CSR_MCYCLECFG"),
    ("Sdtrig", "defined(SDTRIG_SUPPORTED)", (), "csrr x{d}, CSR_TSELECT"),
)

_FP_PROBES = frozenset({"Zfh", "Zfhmin", "Zfa", "Zfbfmin"})

# 16-bit probes: (bin, condition, encoding for rd' = x8). Each is followed by c.nop so the
# pair fills the 4 bytes the probe trap handler skips. c.zext.b writes rd' (x8-x15).
_COMPRESSED_PROBES: tuple[tuple[str, str, int, bool], ...] = (
    ("Zcb", "defined(ZCB_SUPPORTED)", 0x9C61, True),  # c.zext.b rd'
    ("Zcmop", "defined(ZCMOP_SUPPORTED)", 0x6081, False),  # c.mop.1
)
_C_NOP = 0x0001

# Extensions recognised by the xenvcfg bit they add: (bin, condition, menvcfg bit). The
# privileged spec makes an unimplemented field read-only zero, so the bit must read back
# as written exactly when the config lists the extension.
_ENVCFG_BITS: tuple[tuple[str, str, int], ...] = (
    ("Zicfilp", "defined(ZICFILP_SUPPORTED)", 2),  # LPE
    ("Zicfiss", "defined(ZICFISS_SUPPORTED)", 3),  # SSE
    ("Ssdbltrp", "defined(SSDBLTRP_SUPPORTED)", 59),  # DTE
    ("Svadu", "defined(SVADU_SUPPORTED)", 61),  # ADUE
    ("Svpbmt", "defined(SVPBMT_SUPPORTED)", 62),  # PBMTE
)


def _li_cfg(reg: int, cases: list[tuple[str, str]], default: str) -> list[str]:
    """LI(reg, value) for the first preprocessor condition that holds, else the default."""
    lines: list[str] = []
    for i, (cond, value) in enumerate(cases):
        lines += [f"#{'if' if i == 0 else 'elif'} {cond}", f"LI(x{reg}, {value})"]
    return [*lines, "#else", f"LI(x{reg}, {default})", "#endif"]


def _check(test_data: TestData, obs: int, cfg: int) -> str:
    """Compare x{obs} with x{cfg}, the value the config implies (cfg 0 is x0)."""
    return f"RVTEST_CONFIG_CHECK(x{obs}, x{cfg}, {test_data.current_testcase_label}_str)"


def _done(test_data: TestData, marker: int) -> list[str]:
    """One signature word, so the file self-checks that it reached the end."""
    reg = test_data.int_regs.get_registers(1)[0]
    lines = [f"LI(x{reg}, {hex(marker)})", write_sigupd(reg, test_data)]
    test_data.int_regs.return_registers([reg])
    return lines


def _misa(test_data: TestData) -> list[str]:
    """MXL and one misa bit per single-letter extension.

    Catches an extension missing from implemented_extensions as well as one listed
    that the hart doesn't have. Skipped when MISA_CSR_IMPLEMENTED is false: the
    reference model always implements misa, so it can't check that misa reads zero.
    """
    misa, obs, cfg = test_data.int_regs.get_registers(3)
    lines = [
        comment_banner("ConfigCheck: misa", "MXL and the single-letter extensions in implemented_extensions"),
        "#ifdef UDB_MISA_CSR_IMPLEMENTED",
        f"csrr x{misa}, CSR_MISA",
        "#endif",
        test_data.add_testcase("MXLEN", "cp_misa", _CG),
        "#ifdef UDB_MISA_CSR_IMPLEMENTED",
        f"srli x{obs}, x{misa}, UDB_MXLEN-2",
        *_li_cfg(cfg, [("UDB_MXLEN == 64", "2")], "1"),
        _check(test_data, obs, cfg),
        "#endif",
    ]
    for letter in _MISA_LETTERS:
        lines += [
            test_data.add_testcase(letter, "cp_misa", _CG),
            "#ifdef UDB_MISA_CSR_IMPLEMENTED",
            f"srli x{obs}, x{misa}, {ord(letter) - ord('A')}",
            f"andi x{obs}, x{obs}, 1",
            *_li_cfg(cfg, [(f"defined({letter}_SUPPORTED)", "1")], "0"),
            _check(test_data, obs, cfg),
            "#endif",
        ]
    test_data.int_regs.return_registers([misa, obs, cfg])
    return [*lines, *_done(test_data, 0xC0F16001)]


def _probed(lines: list[str]) -> list[str]:
    """Run lines under the probe trap handler (see RVTEST_CONFIG_PROBE_BEGIN)."""
    return [
        "#ifdef UDB_MTVEC_ACCESS_RW",
        "RVTEST_CONFIG_PROBE_BEGIN",
        "#endif",
        *lines,
        "#ifdef UDB_MTVEC_ACCESS_RW",
        "RVTEST_CONFIG_PROBE_END",
        "#endif",
    ]


def _tvec_modes(test_data: TestData, csr: str, param: str, guard: str) -> list[str]:
    """Which xtvec modes the hart accepts: bit 0 = direct, bit 1 = vectored.

    rvtest_config_probe_trap is aligned for both modes, so a mode the hart supports
    reads back as written; an unsupported one reads back as the other mode.
    """
    save, base, tmp, obs, cfg = test_data.int_regs.get_registers(5)
    lines = [
        test_data.add_testcase(param, f"cp_{csr.lower()}", _CG),
        f"#if {guard}",
        f"csrr x{save}, CSR_{csr}",
        f"LA(x{base}, rvtest_config_probe_trap)",
        f"ori x{tmp}, x{base}, 1",
        f"csrw CSR_{csr}, x{tmp}      # vectored",
        f"LI(x{tmp}, 0)",
        f"csrr x{tmp}, CSR_{csr}",
        f"andi x{tmp}, x{tmp}, 3",
        f"addi x{tmp}, x{tmp}, -1",
        f"seqz x{obs}, x{tmp}",
        f"slli x{obs}, x{obs}, 1",
        f"csrw CSR_{csr}, x{base}     # direct",
        f"LI(x{tmp}, 1)",
        f"csrr x{tmp}, CSR_{csr}",
        f"andi x{tmp}, x{tmp}, 3",
        f"seqz x{tmp}, x{tmp}",
        f"or x{obs}, x{obs}, x{tmp}",
        f"csrw CSR_{csr}, x{save}",
        *_li_cfg(
            cfg,
            [
                (f"defined(UDB_{param}_0) && defined(UDB_{param}_1)", "3"),
                (f"defined(UDB_{param}_1)", "2"),
            ],
            "1",
        ),
        _check(test_data, obs, cfg),
        f"#endif // {guard}",
    ]
    test_data.int_regs.return_registers([save, base, tmp, obs, cfg])
    return lines


def _tvec_alignment(test_data: TestData, csr: str, mode: int, param: str, mode_define: str) -> list[str]:
    """The smallest xtvec base alignment the hart accepts in one mode.

    Writes bases 64 KiB down to 4 bytes past a 128 KiB boundary near the current
    value; the smallest that reads back unchanged is the alignment.
    """
    save, base, wr, rd, obs, cfg = test_data.int_regs.get_registers(6)
    guard = f"defined(UDB_MTVEC_ACCESS_RW) && defined({mode_define}) && defined(UDB_{param}) && UDB_{param} <= 0x10000"
    lines = [
        test_data.add_testcase(param, f"cp_{csr.lower()}", _CG),
        f"#if {guard}",
        f"csrr x{save}, CSR_{csr}",
        f"LI(x{base}, -0x20000)",
        f"and x{base}, x{save}, x{base}",
        f"LI(x{obs}, 0)",
    ]
    for k in range(16, 1, -1):
        lines += [
            f"LI(x{wr}, {hex((1 << k) | mode)})",
            f"or x{wr}, x{wr}, x{base}",
            f"csrw CSR_{csr}, x{wr}",
            f"csrr x{rd}, CSR_{csr}",
            f"bne x{rd}, x{wr}, 1f",
            f"LI(x{obs}, {hex(1 << k)})",
            "1:",
        ]
    lines += [
        f"csrw CSR_{csr}, x{save}",
        f"LI(x{cfg}, UDB_{param})",
        _check(test_data, obs, cfg),
        "#endif",
    ]
    test_data.int_regs.return_registers([save, base, wr, rd, obs, cfg])
    return lines


def _tvec(test_data: TestData) -> list[str]:
    """mtvec and stvec modes and base alignments.

    The trap handler is installed through these, so a wrong value here breaks every
    test that takes a trap. stvec is probed under the probe handler, in case the hart
    has no S-mode.
    """
    stvec_guard = "defined(UDB_STVEC_MODES_0) || defined(UDB_STVEC_MODES_1)"
    return [
        comment_banner("ConfigCheck: trap vectors", "mtvec/stvec modes and base alignments"),
        *_tvec_modes(test_data, "MTVEC", "MTVEC_MODES", "defined(UDB_MTVEC_ACCESS_RW)"),
        *_tvec_alignment(test_data, "MTVEC", 0, "MTVEC_BASE_ALIGNMENT_DIRECT", "UDB_MTVEC_MODES_0"),
        *_tvec_alignment(test_data, "MTVEC", 1, "MTVEC_BASE_ALIGNMENT_VECTORED", "UDB_MTVEC_MODES_1"),
        *_probed(
            [
                *_tvec_modes(test_data, "STVEC", "STVEC_MODES", stvec_guard),
                *_tvec_alignment(test_data, "STVEC", 1, "STVEC_BASE_ALIGNMENT_VECTORED", "UDB_STVEC_MODES_1"),
            ]
        ),
        *_done(test_data, 0xC0F16002),
    ]


def _pmpcfg(i: int, xlen: int) -> tuple[str, int]:
    """The pmpcfg CSR holding entry i, and the entry's byte within it."""
    per_csr = xlen // 8
    return f"pmpcfg{(i // per_csr) * (per_csr // 4)}", i % per_csr


def _pmp_entry_off(i: int, scfg: int, tmp: int) -> list[str]:
    """Save the pmpcfg CSR holding entry i in x{scfg}, then turn entry i off."""
    (csr64, byte64), (csr32, byte32) = _pmpcfg(i, 64), _pmpcfg(i, 32)
    return [
        "#if __riscv_xlen == 64",
        f"csrr x{scfg}, {csr64}",
        f"LI(x{tmp}, {hex(0xFF << (8 * byte64))})",
        f"csrc {csr64}, x{tmp}",
        "#else",
        f"csrr x{scfg}, {csr32}",
        f"LI(x{tmp}, {hex(0xFF << (8 * byte32))})",
        f"csrc {csr32}, x{tmp}",
        "#endif",
    ]


def _pmp_entry_restore(i: int, scfg: int) -> list[str]:
    """Restore the pmpcfg CSR holding entry i from x{scfg}."""
    return [
        "#if __riscv_xlen == 64",
        f"csrw {_pmpcfg(i, 64)[0]}, x{scfg}",
        "#else",
        f"csrw {_pmpcfg(i, 32)[0]}, x{scfg}",
        "#endif",
    ]


def _pmp_write_ones(i: int, scfg: int, saddr: int, tmp: int, rd: int) -> list[str]:
    """Turn entry i off, write its pmpaddr with all ones, read it into x{rd} and restore.

    x{rd} is cleared first, so a pmpaddr the hart doesn't have reads as zero.
    """
    return [
        *_pmp_entry_off(i, scfg, tmp),
        f"csrr x{saddr}, pmpaddr{i}",
        f"LI(x{tmp}, -1)",
        f"csrw pmpaddr{i}, x{tmp}",
        f"LI(x{rd}, 0)",
        f"csrr x{rd}, pmpaddr{i}",
        f"csrw pmpaddr{i}, x{saddr}",
        *_pmp_entry_restore(i, scfg),
    ]


def _pmp(test_data: TestData) -> list[str]:
    """Usable PMP entries, PMP granularity and physical address width.

    The entries the config says exist are probed; the rest may trap. With an entry off,
    its pmpaddr reads back the writable bits: the lowest is 2^G and the highest is
    bit PHYS_ADDR_WIDTH-3.
    """
    scfg, saddr, tmp, rd, cnt, obs = test_data.int_regs.get_registers(6)
    lines = [
        test_data.add_testcase("NUM_USABLE_PMP_ENTRIES", "cp_pmp", _CG),
        "#if UDB_NUM_PMP_ENTRIES > 0",
        f"LI(x{cnt}, 0)",
    ]
    for i in range(64):
        lines += [
            f"#if UDB_NUM_PMP_ENTRIES > {i}",
            *_pmp_write_ones(i, scfg, saddr, tmp, rd),
            f"snez x{rd}, x{rd}",
            f"add x{cnt}, x{cnt}, x{rd}",
            "#endif",
        ]
    lines += [
        *_li_cfg(tmp, [("defined(UDB_NUM_USABLE_PMP_ENTRIES)", "UDB_NUM_USABLE_PMP_ENTRIES")], "UDB_NUM_PMP_ENTRIES"),
        _check(test_data, cnt, tmp),
        "#endif",
    ]

    low = cnt
    entry0 = (
        "UDB_NUM_PMP_ENTRIES > 0 && defined(UDB_PMP_GRANULARITY) && "
        "(!defined(UDB_NUM_USABLE_PMP_ENTRIES) || UDB_NUM_USABLE_PMP_ENTRIES > 0)"
    )
    lines += [
        test_data.add_testcase("PMP_GRANULARITY", "cp_pmp", _CG),
        f"#if {entry0}",
        *_pmp_write_ones(0, scfg, saddr, tmp, rd),
        f"neg x{low}, x{rd}",
        f"and x{low}, x{low}, x{rd}      # lowest writable bit, 2^G",
        f"slli x{obs}, x{low}, 2         # granule in bytes, 2^(G+2)",
        f"LI(x{tmp}, 1 << UDB_PMP_GRANULARITY)",
        _check(test_data, obs, tmp),
        "#endif",
        test_data.add_testcase("PHYS_ADDR_WIDTH", "cp_pmp", _CG),
        # Without Sv32, UDB caps an RV32 PHYS_ADDR_WIDTH at 32, but harts commonly keep
        # pmpaddr[31:30] writable, which no valid config can describe.
        f"#if {entry0} && (__riscv_xlen == 64 || defined(SV32_SUPPORTED))",
        f"addi x{low}, x{low}, -1",
        f"or x{obs}, x{rd}, x{low}         # pmpaddr with every address bit set",
        f"LI(x{tmp}, (1 << (UDB_PHYS_ADDR_WIDTH - 2)) - 1)",
        _check(test_data, obs, tmp),
        "#endif",
    ]
    test_data.int_regs.return_registers([scfg, saddr, tmp, rd, cnt, obs])
    return [
        comment_banner("ConfigCheck: PMP", "Usable entries, granularity and physical address width"),
        *_probed(lines),
        *_done(test_data, 0xC0F16003),
    ]


def _satp(test_data: TestData) -> list[str]:
    """Which satp modes the hart accepts, and ASID_WIDTH.

    A write with an unsupported MODE has no effect, so the mode reads back as written
    only if the hart supports it. M-mode does not translate, so satp can be changed
    here without an sfence.vma.
    """
    save, wr, rd, obs, cfg = test_data.int_regs.get_registers(5)
    lines = [
        "#ifdef S_SUPPORTED",
        f"LI(x{save}, 0)",
        f"csrr x{save}, CSR_SATP",
        "#endif",
    ]
    for xlen, modes in _SATP_MODES.items():
        shift = _SATP_MODE_SHIFT[xlen]
        for name, mode, define in modes:
            lines += [
                test_data.add_testcase(name, "cp_satp", _CG),
                f"#if defined(S_SUPPORTED) && __riscv_xlen == {xlen}",
                f"LI(x{wr}, {hex(mode << shift)})",
                f"csrw CSR_SATP, x{wr}",
                f"LI(x{rd}, 0)",
                f"csrr x{rd}, CSR_SATP",
                f"csrw CSR_SATP, x{save}",
                f"srli x{rd}, x{rd}, {shift}",
                f"addi x{rd}, x{rd}, -{mode}",
                f"seqz x{obs}, x{rd}",
                *_li_cfg(cfg, [(f"defined({define})", "1")], "0"),
                _check(test_data, obs, cfg),
                "#endif",
            ]
    lines += [
        test_data.add_testcase("ASID_WIDTH", "cp_satp", _CG),
        f"#if defined(S_SUPPORTED) && defined(UDB_ASID_WIDTH) && ({_SV_FOR_ASID})",
        "#if __riscv_xlen == 64",
        f"LI(x{wr}, (8 << 60) | (0xFFFF << 44))    # Sv39, every ASID bit set",
        f"csrw CSR_SATP, x{wr}",
        f"LI(x{rd}, 0)",
        f"csrr x{rd}, CSR_SATP",
        f"csrw CSR_SATP, x{save}",
        f"srli x{rd}, x{rd}, 44",
        f"LI(x{wr}, 0xFFFF)",
        f"and x{obs}, x{rd}, x{wr}",
        "#else",
        f"LI(x{wr}, (1 << 31) | (0x1FF << 22))     # Sv32, every ASID bit set",
        f"csrw CSR_SATP, x{wr}",
        f"LI(x{rd}, 0)",
        f"csrr x{rd}, CSR_SATP",
        f"csrw CSR_SATP, x{save}",
        f"srli x{rd}, x{rd}, 22",
        f"andi x{obs}, x{rd}, 0x1FF",
        "#endif",
        f"LI(x{cfg}, (1 << UDB_ASID_WIDTH) - 1)",
        _check(test_data, obs, cfg),
        "#endif",
    ]
    test_data.int_regs.return_registers([save, wr, rd, obs, cfg])
    return [
        comment_banner("ConfigCheck: satp", "Translation modes and ASID width"),
        *_probed(lines),
        *_done(test_data, 0xC0F16004),
    ]


def _probe(
    test_data: TestData,
    bin_name: str,
    coverpoint: str,
    guard: str,
    instr: list[str],
    obs: int,
    expected: Callable[[int], list[str]] | None = None,
) -> list[str]:
    """Execute instr under the probe trap handler and check the cause it raised.

    expected(reg) returns the lines that load the cause the config implies into x{reg};
    by default the instruction must not trap (cause 0).
    """
    cfg = test_data.int_regs.get_registers(1)[0] if expected else 0
    lines = [
        test_data.add_testcase(bin_name, coverpoint, _CG),
        f"#if defined(UDB_MTVEC_ACCESS_RW) && {guard}",
        "csrw CSR_MCAUSE, zero",
        ".option push",
        ".option norvc",
        *instr,
        ".option pop",
        f"csrr x{obs}, CSR_MCAUSE",
        *(expected(cfg) if expected else []),
        _check(test_data, obs, cfg),
        "#endif",
    ]
    if expected:
        test_data.int_regs.return_registers([cfg])
    return lines


def _misaligned(test_data: TestData) -> list[str]:
    """MISALIGNED_LDST: a misaligned load or store completes, or raises the misaligned exception."""
    addr, data, obs = test_data.int_regs.get_registers(3)
    lines = [f"LA(x{addr}, scratch)", f"addi x{addr}, x{addr}, 1"]
    for kind, instr, cause in (
        ("load", f"lw x{data}, 0(x{addr})", "CAUSE_MISALIGNED_LOAD"),
        ("store", f"sw x{data}, 0(x{addr})", "CAUSE_MISALIGNED_STORE"),
    ):
        lines += _probe(
            test_data,
            f"MISALIGNED_LDST_{kind}",
            "cp_misaligned",
            "1",
            [instr],
            obs,
            lambda reg, cause=cause: _li_cfg(reg, [("defined(UDB_MISALIGNED_LDST)", "0")], cause),
        )
    test_data.int_regs.return_registers([addr, data, obs])
    return [
        comment_banner("ConfigCheck: misaligned accesses", "A misaligned load and store complete, or trap"),
        *_probed(lines),
        *_done(test_data, 0xC0F16005),
    ]


def _envcfg_bit(test_data: TestData, bin_name: str, guard: str, bit: int, save: int, tmp: int, obs: int) -> list[str]:
    """Set one menvcfg bit, read it back and restore menvcfg; the bit must stick iff guard holds."""

    def read_back(csr: str, pos: int) -> list[str]:
        return [
            f"csrr x{save}, {csr}",
            f"LI(x{tmp}, {hex(1 << pos)})",
            f"csrs {csr}, x{tmp}",
            f"LI(x{obs}, 0)",
            f"csrr x{obs}, {csr}",
            f"csrw {csr}, x{save}",
            f"srli x{obs}, x{obs}, {pos}",
        ]

    lines = [
        test_data.add_testcase(bin_name, "cp_envcfg", _CG),
        "#if defined(U_SUPPORTED) && defined(UDB_MTVEC_ACCESS_RW)",
        "#if __riscv_xlen == 64",
        *read_back("CSR_MENVCFG", bit),
        "#else",
        *read_back("CSR_MENVCFGH" if bit >= 32 else "CSR_MENVCFG", bit % 32),
        "#endif",
        f"andi x{obs}, x{obs}, 1",
        *_li_cfg(tmp, [(guard, "1")], "0"),
        _check(test_data, obs, tmp),
        "#endif",
    ]
    return lines


def _extensions(test_data: TestData) -> list[str]:
    """One instruction or CSR read per extension the config lists; none may trap.

    Extensions the config omits are not probed: their encodings are reserved, so a
    hart may implement them anyway. misa covers the single-letter extensions. An
    extension that adds a menvcfg field is checked both ways, because an unimplemented
    field must read as zero.
    """
    # d must be one of x8-x15 for the compressed probes.
    d = test_data.int_regs.get_registers(1, reg_range=list(range(8, 16)))[0]
    mstatus, a, b, obs = test_data.int_regs.get_registers(4)
    lines = [
        f"LA(x{a}, scratch)",
        f"LI(x{b}, 1)",
        "#ifdef F_SUPPORTED",
        f"csrr x{mstatus}, CSR_MSTATUS",
        f"LI(x{d}, MSTATUS_FS)",
        f"csrs CSR_MSTATUS, x{d}",
        "#endif",
    ]
    for bin_name, guard, exts, instr in _EXTENSION_PROBES:
        if bin_name in _FP_PROBES:
            guard = f"defined(F_SUPPORTED) && {guard}"
        body = arch_block([instr.format(d=d, a=a, b=b)], *exts)
        lines += _probe(test_data, bin_name, "cp_extensions", guard, body, obs)
    for bin_name, guard, encoding, writes_rd in _COMPRESSED_PROBES:
        enc = encoding | ((d - 8) << 7) if writes_rd else encoding
        body = [f".2byte {hex(enc)}", f".2byte {hex(_C_NOP)}"]
        lines += _probe(test_data, bin_name, "cp_extensions", guard, body, obs)
    lines += ["#ifdef F_SUPPORTED", f"csrw CSR_MSTATUS, x{mstatus}", "#endif"]
    for bin_name, guard, bit in _ENVCFG_BITS:
        lines += _envcfg_bit(test_data, bin_name, guard, bit, a, b, obs)
    test_data.int_regs.return_registers([mstatus, d, a, b, obs])
    return [
        comment_banner("ConfigCheck: extensions", "Each listed extension's instruction executes without a trap"),
        *_probed(lines),
        *_done(test_data, 0xC0F16006),
    ]


def _write_ones_read(test_data: TestData, csr: str, save: int, obs: int) -> list[str]:
    """Write all ones to a CSR, read it into x{obs}, and restore it."""
    return [
        f"csrr x{save}, {csr}",
        f"LI(x{obs}, -1)",
        f"csrw {csr}, x{obs}",
        f"LI(x{obs}, 0)",
        f"csrr x{obs}, {csr}",
        f"csrw {csr}, x{save}",
    ]


def _deleg(test_data: TestData) -> list[str]:
    """The medeleg and mideleg bits that can be set: which traps can go to S-mode.

    Writing all ones and reading back gives the delegatable bits plus any read-only-one
    bits (VS-level interrupts with H), which is what the UDB masks list. Only the standard
    cause codes are compared: a hart may make the custom-use bits (medeleg 24-31,
    mideleg 16 and up) writable, and the config has no way to say so.
    """
    save, obs, cfg = test_data.int_regs.get_registers(3)
    lines = [comment_banner("ConfigCheck: trap delegation", "Writable medeleg and mideleg bits")]
    for csr, param, standard in (
        ("CSR_MEDELEG", "MEDELEG_DELEGATABLE", 0x00FFFFFF),
        ("CSR_MIDELEG", "MIDELEG_DELEGATABLE", 0x0000FFFF),
    ):
        lines += [
            test_data.add_testcase(param, "cp_deleg", _CG),
            f"#if defined(S_SUPPORTED) && defined(UDB_{param}_MASK)",
            *_write_ones_read(test_data, csr, save, obs),
            f"LI(x{cfg}, {hex(standard)})",
            f"and x{obs}, x{obs}, x{cfg}",
            f"LI(x{cfg}, (UDB_{param}_MASK) & {hex(standard)})",
            _check(test_data, obs, cfg),
            "#endif",
        ]
    test_data.int_regs.return_registers([save, obs, cfg])
    return [*_probed(lines), *_done(test_data, 0xC0F16007)]


def _tval_probe(
    test_data: TestData, bin_name: str, guard: str, body: list[str], cause: str, expected: list[str]
) -> list[str]:
    """Run body under the probe handler and check what mtval holds after the trap.

    expected loads the mtval the config implies into x{cfg}. If body does not raise
    cause, the observed value is all ones, which no config implies.
    """
    obs, tmp = test_data.int_regs.get_registers(2)
    lines = [
        test_data.add_testcase(bin_name, "cp_tval", _CG),
        f"#if defined(UDB_MTVEC_ACCESS_RW) && {guard}",
        "csrw CSR_MCAUSE, zero",
        "csrw CSR_MTVAL, zero",
        ".option push",
        ".option norvc",
        *body,
        ".option pop",
        f"csrr x{obs}, CSR_MTVAL",
        f"csrr x{tmp}, CSR_MCAUSE",
        f"addi x{tmp}, x{tmp}, -{cause}",
        f"beqz x{tmp}, 2f",
        f"LI(x{obs}, -1)",
        "2:",
        *[ln.format(cfg=tmp) for ln in expected],
        _check(test_data, obs, tmp),
        "#endif",
    ]
    test_data.int_regs.return_registers([obs, tmp])
    return lines


def _tval(test_data: TestData) -> list[str]:
    """What mtval holds for the exceptions whose mtval the config describes.

    Illegal instruction: csrrw to mvendorid, which is read-only on every hart, so the
    encoding is fixed. Breakpoint: ebreak. Misaligned and access-fault loads and stores:
    scratch + 1 when misaligned accesses trap, and the dut_environment fault addresses.
    """
    addr, n = test_data.int_regs.get_registers(2)
    ebreak = "rvtest_config_ebreak"
    illegal = 0xF1101073  # csrrw x0, mvendorid, x0

    def va(param: str, reg: int) -> list[str]:
        """x{cfg} = x{reg} if the config reports the address in mtval, else 0."""
        return [f"#ifdef UDB_{param}", f"mv x{{cfg}}, x{reg}", "#else", "LI(x{cfg}, 0)", "#endif"]

    lines = [comment_banner("ConfigCheck: trap values", "mtval for the exceptions the config describes")]
    lines += _tval_probe(
        test_data,
        "REPORT_ENCODING_IN_MTVAL_ON_ILLEGAL_INSTRUCTION",
        "1",
        [f".4byte {hex(illegal)}"],
        "CAUSE_ILLEGAL_INSTRUCTION",
        [
            "#ifdef UDB_REPORT_ENCODING_IN_MTVAL_ON_ILLEGAL_INSTRUCTION",
            f"LI(x{{cfg}}, {hex(illegal)})",
            "#else",
            "LI(x{cfg}, 0)",
            "#endif",
        ],
    )
    lines += _tval_probe(
        test_data,
        "REPORT_VA_IN_MTVAL_ON_BREAKPOINT",
        "1",
        [f"LA(x{addr}, {ebreak})", f"{ebreak}:", "ebreak"],
        "CAUSE_BREAKPOINT",
        va("REPORT_VA_IN_MTVAL_ON_BREAKPOINT", addr),
    )
    for op, cause, param in (
        (f"lw x{n}, 0(x{addr})", "CAUSE_MISALIGNED_LOAD", "REPORT_VA_IN_MTVAL_ON_LOAD_MISALIGNED"),
        (f"sw x{n}, 0(x{addr})", "CAUSE_MISALIGNED_STORE", "REPORT_VA_IN_MTVAL_ON_STORE_AMO_MISALIGNED"),
    ):
        lines += _tval_probe(
            test_data,
            param,
            "!defined(UDB_MISALIGNED_LDST)",
            [f"LA(x{addr}, scratch)", f"addi x{addr}, x{addr}, 1", op],
            cause,
            va(param, addr),
        )
    for kind, op, cause, param in (
        ("LOAD", f"lw x{n}, 0(x{addr})", "CAUSE_LOAD_ACCESS", "REPORT_VA_IN_MTVAL_ON_LOAD_ACCESS_FAULT"),
        ("STORE", f"sw x{n}, 0(x{addr})", "CAUSE_STORE_ACCESS", "REPORT_VA_IN_MTVAL_ON_STORE_AMO_ACCESS_FAULT"),
    ):
        lines += _tval_probe(
            test_data,
            param,
            f"defined(RVMODEL_ACCESS_FAULT_ADDRESS_{kind})",
            [f"LI_FIXED_LEN(x{addr}, RVMODEL_ACCESS_FAULT_ADDRESS_{kind})", op],
            cause,
            va(param, addr),
        )
    test_data.int_regs.return_registers([addr, n])
    return [*_probed(lines), *_done(test_data, 0xC0F16008)]


def _counters(test_data: TestData) -> list[str]:
    """The writable bits of the counter-enable CSRs and of mcountinhibit.

    UDB lets a counter-enable bit be writable only for a counter the config has: CY, TM
    and IR with Zicntr, the HPM counters with Zihpm. A hart may still make the others
    writable, so only the bits the config can describe are compared.
    """
    save, obs, cfg, mask = test_data.int_regs.get_registers(4)
    lines = [comment_banner("ConfigCheck: counters", "Counter-enable and counter-inhibit bits")]
    for csr, param, guard, describable in (
        ("CSR_MCOUNTEREN", "MCOUNTENABLE_EN", "defined(U_SUPPORTED)", True),
        ("CSR_SCOUNTEREN", "SCOUNTENABLE_EN", "defined(S_SUPPORTED)", True),
        ("CSR_HCOUNTEREN", "HCOUNTENABLE_EN", "defined(H_SUPPORTED)", True),
        ("CSR_MCOUNTINHIBIT", "COUNTINHIBIT_EN", "defined(UDB_MCOUNTINHIBIT_IMPLEMENTED)", False),
    ):
        compare = (
            _li_cfg(
                mask,
                [
                    ("defined(ZICNTR_SUPPORTED) && defined(ZIHPM_SUPPORTED)", "0xFFFFFFFF"),
                    ("defined(ZICNTR_SUPPORTED)", "0x7"),
                    ("defined(ZIHPM_SUPPORTED)", "0xFFFFFFF8"),
                ],
                "0",
            )
            if describable
            else [f"LI(x{mask}, 0xFFFFFFFF)"]
        )
        lines += [
            test_data.add_testcase(param, "cp_counters", _CG),
            f"#if {guard} && defined(UDB_{param}_MASK)",
            *_write_ones_read(test_data, csr, save, obs),
            *compare,
            f"and x{obs}, x{obs}, x{mask}",
            f"LI(x{cfg}, UDB_{param}_MASK)",
            f"and x{cfg}, x{cfg}, x{mask}",
            _check(test_data, obs, cfg),
            "#endif",
        ]
    test_data.int_regs.return_registers([save, obs, cfg, mask])
    return [*_probed(lines), *_done(test_data, 0xC0F16009)]


# One instruction per vector extension: (bin, condition, extensions to enable, vsetivli, instruction).
# Element-group instructions run with LMUL = 4, so vl is a whole number of groups and the
# group width fits on any VLEN the extension allows.
_VECTOR_PROBES: tuple[tuple[str, str, tuple[str, ...], str, str], ...] = (
    ("Zvbb", "defined(ZVBB_SUPPORTED)", ("zvbb",), "vsetivli x0, 4, e8, m1, ta, ma", "vbrev.v v8, v16"),
    ("Zvkb", "defined(ZVKB_SUPPORTED)", ("zvkb",), "vsetivli x0, 4, e8, m1, ta, ma", "vandn.vv v8, v16, v24"),
    ("Zvbc", "defined(ZVBC_SUPPORTED)", ("zvbc",), "vsetivli x0, 2, e64, m1, ta, ma", "vclmul.vv v8, v16, v24"),
    ("Zvkg", "defined(ZVKG_SUPPORTED)", ("zvkg",), "vsetivli x0, 4, e32, m4, ta, ma", "vghsh.vv v8, v12, v16"),
    ("Zvkned", "defined(ZVKNED_SUPPORTED)", ("zvkned",), "vsetivli x0, 4, e32, m4, ta, ma", "vaesef.vv v8, v12"),
    ("Zvknha", "defined(ZVKNHA_SUPPORTED)", ("zvknha",), "vsetivli x0, 4, e32, m4, ta, ma", "vsha2ms.vv v8, v12, v16"),
    ("Zvknhb", "defined(ZVKNHB_SUPPORTED)", ("zvknhb",), "vsetivli x0, 4, e64, m4, ta, ma", "vsha2ms.vv v8, v12, v16"),
    ("Zvksed", "defined(ZVKSED_SUPPORTED)", ("zvksed",), "vsetivli x0, 4, e32, m4, ta, ma", "vsm4r.vv v8, v12"),
    ("Zvksh", "defined(ZVKSH_SUPPORTED)", ("zvksh",), "vsetivli x0, 8, e32, m4, ta, ma", "vsm3me.vv v8, v12, v16"),
    ("Zvfh", "defined(ZVFH_SUPPORTED)", ("zvfh",), "vsetivli x0, 1, e16, m1, ta, ma", "vfadd.vv v8, v16, v24"),
    ("Zvfhmin", "defined(ZVFHMIN_SUPPORTED)", ("zvfhmin",), "vsetivli x0, 1, e16, m1, ta, ma", "vfwcvt.f.f.v v8, v16"),
    (
        "Zvfbfmin",
        "defined(ZVFBFMIN_SUPPORTED)",
        ("zvfbfmin",),
        "vsetivli x0, 1, e16, m1, ta, ma",
        "vfwcvtbf16.f.f.v v8, v16",
    ),
    (
        "Zvfbfwma",
        "defined(ZVFBFWMA_SUPPORTED)",
        ("zvfbfwma",),
        "vsetivli x0, 1, e16, m1, ta, ma",
        "vfwmaccbf16.vv v8, v16, v24",
    ),
)
_VECTOR = "(defined(V_SUPPORTED) || defined(ZVE32X_SUPPORTED))"


def _vector(test_data: TestData) -> list[str]:
    """VLEN, ELEN, and one instruction per vector extension the config lists.

    vsetvli with AVL = x0 returns VLMAX, which is VLEN / 8 at SEW = 8 and LMUL = 1.
    vtype.vill is set by a vsetvli asking for SEW = 64 exactly when ELEN is 32.
    """
    mstatus, tmp, obs, cfg = test_data.int_regs.get_registers(4)
    lines = [
        f"#if {_VECTOR}",
        f"csrr x{mstatus}, CSR_MSTATUS",
        f"LI(x{tmp}, MSTATUS_VS | MSTATUS_FS)",
        f"csrs CSR_MSTATUS, x{tmp}",
        "#endif",
        test_data.add_testcase("VLEN", "cp_vector", _CG),
        f"#if {_VECTOR} && defined(UDB_VLEN)",
        *arch_block([f"vsetvli x{obs}, x0, e8, m1, ta, ma"], "v"),
        f"slli x{obs}, x{obs}, 3",
        f"LI(x{cfg}, UDB_VLEN)",
        _check(test_data, obs, cfg),
        "#endif",
        test_data.add_testcase("ELEN", "cp_vector", _CG),
        f"#if {_VECTOR} && defined(UDB_ELEN)",
        *arch_block([f"vsetvli x{tmp}, x0, e64, m1, ta, ma"], "v"),
        f"csrr x{tmp}, CSR_VTYPE",
        f"srli x{tmp}, x{tmp}, __riscv_xlen - 1",
        f"LI(x{obs}, 64)",
        f"beqz x{tmp}, 1f",
        f"LI(x{obs}, 32)",
        "1:",
        f"LI(x{cfg}, UDB_ELEN)",
        _check(test_data, obs, cfg),
        "#endif",
    ]
    for bin_name, guard, exts, vset, instr in _VECTOR_PROBES:
        lines += [
            f"#if {_VECTOR} && {guard}",
            *arch_block([vset], "v"),
            "#endif",
            *_probe(test_data, bin_name, "cp_vector", f"{_VECTOR} && {guard}", arch_block([instr], "v", *exts), obs),
        ]
    lines += [f"#if {_VECTOR}", f"csrw CSR_MSTATUS, x{mstatus}", "#endif"]
    test_data.int_regs.return_registers([mstatus, tmp, obs, cfg])
    return [
        comment_banner("ConfigCheck: vector", "VLEN, ELEN and one instruction per vector extension"),
        *_probed(lines),
        *_done(test_data, 0xC0F1600A),
    ]


def _cache(test_data: TestData) -> list[str]:
    """CACHE_BLOCK_SIZE, measured with cbo.zero.

    scratch is 256-byte aligned and longer than 256 bytes. After filling it with ones,
    cbo.zero clears one block from its start; the first byte that is still nonzero is
    at offset CACHE_BLOCK_SIZE.
    """
    base, tmp, obs, cfg = test_data.int_regs.get_registers(4)
    guard = "defined(ZICBOZ_SUPPORTED) && defined(UDB_CACHE_BLOCK_SIZE) && UDB_CACHE_BLOCK_SIZE <= 256"
    lines = [
        test_data.add_testcase("CACHE_BLOCK_SIZE", "cp_cache", _CG),
        f"#if defined(UDB_MTVEC_ACCESS_RW) && {guard}",
        f"LA(x{base}, scratch)",
        f"LI(x{tmp}, -1)",
        *[f"sw x{tmp}, {off}(x{base})" for off in range(0, 264, 4)],
        *arch_block([f"cbo.zero (x{base})"], "zicboz"),
        f"LI(x{obs}, 512)",
    ]
    for size in (256, 128, 64, 32, 16, 8, 4):
        lines += [f"lbu x{tmp}, {size}(x{base})", f"beqz x{tmp}, 1f", f"LI(x{obs}, {size})", "1:"]
    lines += [f"LI(x{cfg}, UDB_CACHE_BLOCK_SIZE)", _check(test_data, obs, cfg), "#endif"]
    test_data.int_regs.return_registers([base, tmp, obs, cfg])
    return [
        comment_banner("ConfigCheck: cache block", "CACHE_BLOCK_SIZE from the bytes cbo.zero clears"),
        *_probed(lines),
        *_done(test_data, 0xC0F1600B),
    ]


# hgatp: (bin, MODE value, UDB define) per XLEN, and where VMID sits.
_HGATP_MODES = {
    32: (("Sv32x4", 1, "UDB_SV32X4_TRANSLATION"),),
    64: (
        ("Sv39x4", 8, "UDB_SV39X4_TRANSLATION"),
        ("Sv48x4", 9, "UDB_SV48X4_TRANSLATION"),
        ("Sv57x4", 10, "UDB_SV57X4_TRANSLATION"),
    ),
}
_HGATP_VMID = {32: (22, 0x7F, 1 << 31), 64: (44, 0x3FFF, 8 << 60)}  # shift, field mask, a mode to write with


def _hypervisor(test_data: TestData) -> list[str]:
    """GEILEN, VMID width and the G-stage translation modes.

    hgeie has a writable bit for each guest external interrupt, bits 1 to GEILEN. Unlike
    satp, hgatp fields are WARL, so an unsupported MODE reads back as some other mode.
    """
    save, wr, rd, obs, cfg = test_data.int_regs.get_registers(5)
    lines = [
        test_data.add_testcase("NUM_EXTERNAL_GUEST_INTERRUPTS", "cp_hypervisor", _CG),
        "#if defined(H_SUPPORTED) && defined(UDB_NUM_EXTERNAL_GUEST_INTERRUPTS)",
        *_write_ones_read(test_data, "CSR_HGEIE", save, obs),
        "#if UDB_NUM_EXTERNAL_GUEST_INTERRUPTS > 0",
        f"LI(x{cfg}, -1)",
        f"srli x{cfg}, x{cfg}, __riscv_xlen - UDB_NUM_EXTERNAL_GUEST_INTERRUPTS",
        f"slli x{cfg}, x{cfg}, 1",
        "#else",
        f"LI(x{cfg}, 0)",
        "#endif",
        _check(test_data, obs, cfg),
        "#endif",
        "#ifdef H_SUPPORTED",
        f"csrr x{save}, CSR_HGATP",
        "#endif",
    ]
    for xlen, modes in _HGATP_MODES.items():
        for name, mode, define in modes:
            shift = 60 if xlen == 64 else 31
            lines += [
                test_data.add_testcase(name, "cp_hypervisor", _CG),
                f"#if defined(H_SUPPORTED) && __riscv_xlen == {xlen}",
                f"LI(x{wr}, {hex(mode << shift)})",
                f"csrw CSR_HGATP, x{wr}",
                f"LI(x{rd}, 0)",
                f"csrr x{rd}, CSR_HGATP",
                f"csrw CSR_HGATP, x{save}",
                f"srli x{rd}, x{rd}, {shift}",
                f"addi x{rd}, x{rd}, -{mode}",
                f"seqz x{obs}, x{rd}",
                *_li_cfg(cfg, [(f"defined({define})", "1")], "0"),
                _check(test_data, obs, cfg),
                "#endif",
            ]
    lines += [test_data.add_testcase("VMID_WIDTH", "cp_hypervisor", _CG)]
    for xlen, (shift, field, mode_bits) in _HGATP_VMID.items():
        first = xlen == 32
        lines += [
            f"#{'if' if first else 'elif'} defined(H_SUPPORTED) && defined(UDB_VMID_WIDTH) && __riscv_xlen == {xlen}",
            f"LI(x{wr}, {hex(mode_bits | (field << shift))})    # a supported mode, every VMID bit set",
            f"csrw CSR_HGATP, x{wr}",
            f"LI(x{rd}, 0)",
            f"csrr x{rd}, CSR_HGATP",
            f"csrw CSR_HGATP, x{save}",
            f"srli x{rd}, x{rd}, {shift}",
            f"LI(x{wr}, {hex(field)})",
            f"and x{obs}, x{rd}, x{wr}",
            f"LI(x{cfg}, (1 << UDB_VMID_WIDTH) - 1)",
            _check(test_data, obs, cfg),
        ]
    lines += ["#endif"]
    test_data.int_regs.return_registers([save, wr, rd, obs, cfg])
    return [
        comment_banner("ConfigCheck: hypervisor", "GEILEN, VMID width and the hgatp modes"),
        *_probed(lines),
        *_done(test_data, 0xC0F1600C),
    ]


_MAX_TRIGGERS = 32


def _sdtrig(test_data: TestData) -> list[str]:
    """SDTRIG_NUM_TRIGGERS: tselect reads back as written only for an implemented trigger.

    Selects triggers 0 to SDTRIG_NUM_TRIGGERS, one past the last, and counts those that
    read back, so a hart with more triggers than the config says is caught too.
    """
    save, rd, cnt, cfg = test_data.int_regs.get_registers(4)
    lines = [
        test_data.add_testcase("SDTRIG_NUM_TRIGGERS", "cp_sdtrig", _CG),
        f"#if defined(SDTRIG_SUPPORTED) && defined(UDB_SDTRIG_NUM_TRIGGERS) && UDB_SDTRIG_NUM_TRIGGERS < {_MAX_TRIGGERS}",
        f"csrr x{save}, CSR_TSELECT",
        f"LI(x{cnt}, 0)",
    ]
    for i in range(_MAX_TRIGGERS + 1):
        lines += [
            f"#if UDB_SDTRIG_NUM_TRIGGERS >= {i}",
            f"LI(x{rd}, {i})",
            f"csrw CSR_TSELECT, x{rd}",
            f"csrr x{cfg}, CSR_TSELECT",
            f"bne x{cfg}, x{rd}, 1f",
            f"addi x{cnt}, x{cnt}, 1",
            "1:",
            "#endif",
        ]
    lines += [
        f"csrw CSR_TSELECT, x{save}",
        f"LI(x{cfg}, UDB_SDTRIG_NUM_TRIGGERS)",
        _check(test_data, cnt, cfg),
        "#endif",
    ]
    test_data.int_regs.return_registers([save, rd, cnt, cfg])
    return [
        comment_banner("ConfigCheck: triggers", "The number of triggers tselect can select"),
        *_probed(lines),
        *_done(test_data, 0xC0F1600D),
    ]


# Pointer masking: (extension, CSR holding its PMM field). PMM is bits 33:32 on RV64;
# PMM = 2 selects PMLEN 7 and PMM = 3 selects PMLEN 16.
_PMM_CSRS = (("SMMPM", "CSR_MSECCFG"), ("SMNPM", "CSR_MENVCFG"), ("SSNPM", "CSR_SENVCFG"))


def _pmlen(test_data: TestData) -> list[str]:
    """Which pointer-masking lengths each extension's PMM field accepts (RV64 only)."""
    save, wr, obs, cfg = test_data.int_regs.get_registers(4)
    lines = []
    for ext, csr in _PMM_CSRS:
        for pmm, pmlen in ((2, 7), (3, 16)):
            param = f"SUPPORTED_PMLEN_{ext}_{pmlen}"
            lines += [
                test_data.add_testcase(param, "cp_pmlen", _CG),
                f"#if defined({ext}_SUPPORTED) && __riscv_xlen == 64",
                f"csrr x{save}, {csr}",
                f"LI(x{wr}, 3 << 32)",
                f"not x{wr}, x{wr}",
                f"and x{wr}, x{save}, x{wr}",
                f"LI(x{obs}, {pmm} << 32)",
                f"or x{wr}, x{wr}, x{obs}",
                f"csrw {csr}, x{wr}",
                f"csrr x{obs}, {csr}",
                f"csrw {csr}, x{save}",
                f"srli x{obs}, x{obs}, 32",
                f"andi x{obs}, x{obs}, 3",
                f"addi x{obs}, x{obs}, -{pmm}",
                f"seqz x{obs}, x{obs}",
                *_li_cfg(cfg, [(f"defined(UDB_{param})", "1")], "0"),
                _check(test_data, obs, cfg),
                "#endif",
            ]
    test_data.int_regs.return_registers([save, wr, obs, cfg])
    return [
        comment_banner("ConfigCheck: pointer masking", "The PMLEN values each PMM field accepts"),
        *_probed(lines),
        *_done(test_data, 0xC0F1600E),
    ]


def _qos(test_data: TestData) -> list[str]:
    """RCID_WIDTH and MCID_WIDTH: the writable bits of srmcfg (Ssqosid)."""
    save, obs, tmp, cfg = test_data.int_regs.get_registers(4)
    lines = []
    for param, shift in (("RCID_WIDTH", 0), ("MCID_WIDTH", 16)):
        lines += [
            test_data.add_testcase(param, "cp_qos", _CG),
            f"#if defined(SSQOSID_SUPPORTED) && defined(UDB_{param})",
            *_write_ones_read(test_data, "CSR_SRMCFG", save, obs),
            f"srli x{obs}, x{obs}, {shift}",
            f"LI(x{tmp}, 0xFFF)",
            f"and x{obs}, x{obs}, x{tmp}",
            f"LI(x{cfg}, (1 << UDB_{param}) - 1)",
            _check(test_data, obs, cfg),
            "#endif",
        ]
    test_data.int_regs.return_registers([save, obs, tmp, cfg])
    return [
        comment_banner("ConfigCheck: QoS identifiers", "srmcfg RCID and MCID widths"),
        *_probed(lines),
        *_done(test_data, 0xC0F1600F),
    ]


@add_priv_test_generator(
    "ConfigCheck",
    required_extensions=["Sm"],
    extra_defines=["#define BOOT_TO_MMODE", "#define RVTEST_CONFIG_CHECKS"],
)
def make_config_check(test_data: TestData) -> list[TestChunk]:
    """One file per area of the config."""
    chunks: list[TestChunk] = []
    for name, body in (
        ("misa", _misa),
        ("tvec", _tvec),
        ("deleg", _deleg),
        ("tval", _tval),
        ("pmp", _pmp),
        ("satp", _satp),
        ("misaligned", _misaligned),
        ("counters", _counters),
        ("extensions", _extensions),
        ("vector", _vector),
        ("cache", _cache),
        ("hypervisor", _hypervisor),
        ("sdtrig", _sdtrig),
        ("pmlen", _pmlen),
        ("qos", _qos),
    ):
        tc = test_data.begin_test_chunk(split_name=name)
        tc.code = body(test_data)
        chunks.append(test_data.end_test_chunk())
    return chunks
