##################################
# priv/extensions/ConfigCheck.py
#
# ConfigCheck suite: does the DUT match its UDB config?
# SPDX-License-Identifier: Apache-2.0
##################################

"""Checks that the DUT matches its UDB config.

Run after Hello and before the certification suites. Each testcase reads one value
the config describes from the hart -- a misa bit, the mtvec modes, the number of
usable PMP entries, a satp mode, whether an extension's instruction executes -- and
compares it with the value the config implies, through RVTEST_CONFIG_CHECK. The
testcase is named after the UDB parameter or extension it checks.

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
    that the hart doesn't have. MISA_CSR_IMPLEMENTED false means misa reads zero.
    """
    misa, obs, cfg = test_data.int_regs.get_registers(3)
    lines = [
        comment_banner("ConfigCheck: misa", "MXL and the single-letter extensions in implemented_extensions"),
        f"csrr x{misa}, CSR_MISA",
        test_data.add_testcase("MXLEN", "cp_misa", _CG),
        f"srli x{obs}, x{misa}, UDB_MXLEN-2",
        *_li_cfg(cfg, [("!defined(UDB_MISA_CSR_IMPLEMENTED)", "0"), ("UDB_MXLEN == 64", "2")], "1"),
        _check(test_data, obs, cfg),
    ]
    for letter in _MISA_LETTERS:
        lines += [
            test_data.add_testcase(letter, "cp_misa", _CG),
            f"srli x{obs}, x{misa}, {ord(letter) - ord('A')}",
            f"andi x{obs}, x{obs}, 1",
            *_li_cfg(cfg, [(f"defined(UDB_MISA_CSR_IMPLEMENTED) && defined({letter}_SUPPORTED)", "1")], "0"),
            _check(test_data, obs, cfg),
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


def _mtvec_alignment(test_data: TestData, mode: int, param: str, mode_define: str) -> list[str]:
    """The smallest mtvec base alignment the hart accepts in one mode.

    Writes bases 64 KiB down to 4 bytes past a 128 KiB boundary near the test's own
    handler; the smallest that reads back unchanged is the alignment.
    """
    save, base, wr, rd, obs, cfg = test_data.int_regs.get_registers(6)
    guard = f"defined(UDB_MTVEC_ACCESS_RW) && defined({mode_define}) && defined(UDB_{param}) && UDB_{param} <= 0x10000"
    lines = [
        test_data.add_testcase(param, "cp_mtvec", _CG),
        f"#if {guard}",
        f"csrr x{save}, CSR_MTVEC",
        f"LI(x{base}, -0x20000)",
        f"and x{base}, x{save}, x{base}",
        f"LI(x{obs}, 0)",
    ]
    for k in range(16, 1, -1):
        lines += [
            f"LI(x{wr}, {hex((1 << k) | mode)})",
            f"or x{wr}, x{wr}, x{base}",
            f"csrw CSR_MTVEC, x{wr}",
            f"csrr x{rd}, CSR_MTVEC",
            f"bne x{rd}, x{wr}, 1f",
            f"LI(x{obs}, {hex(1 << k)})",
            "1:",
        ]
    lines += [
        f"csrw CSR_MTVEC, x{save}",
        f"LI(x{cfg}, UDB_{param})",
        _check(test_data, obs, cfg),
        "#endif",
    ]
    test_data.int_regs.return_registers([save, base, wr, rd, obs, cfg])
    return lines


def _tvec(test_data: TestData) -> list[str]:
    """mtvec and stvec modes, and mtvec base alignment.

    The trap handler is installed through these, so a wrong value here breaks every
    test that takes a trap. stvec is probed under the probe handler, in case the hart
    has no S-mode.
    """
    stvec_guard = "defined(UDB_STVEC_MODES_0) || defined(UDB_STVEC_MODES_1)"
    return [
        comment_banner("ConfigCheck: trap vectors", "mtvec/stvec modes and mtvec base alignment"),
        *_tvec_modes(test_data, "MTVEC", "MTVEC_MODES", "defined(UDB_MTVEC_ACCESS_RW)"),
        *_mtvec_alignment(test_data, 0, "MTVEC_BASE_ALIGNMENT_DIRECT", "UDB_MTVEC_MODES_0"),
        *_mtvec_alignment(test_data, 1, "MTVEC_BASE_ALIGNMENT_VECTORED", "UDB_MTVEC_MODES_1"),
        *_probed(_tvec_modes(test_data, "STVEC", "STVEC_MODES", stvec_guard)),
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


def _extensions(test_data: TestData) -> list[str]:
    """One instruction or CSR read per extension the config lists; none may trap.

    Extensions the config omits are not probed: their encodings are reserved, so a
    hart may implement them anyway. misa covers the single-letter extensions.
    """
    mstatus, d, a, b, obs = test_data.int_regs.get_registers(5)
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
    lines += ["#ifdef F_SUPPORTED", f"csrw CSR_MSTATUS, x{mstatus}", "#endif"]
    test_data.int_regs.return_registers([mstatus, d, a, b, obs])
    return [
        comment_banner("ConfigCheck: extensions", "Each listed extension's instruction executes without a trap"),
        *_probed(lines),
        *_done(test_data, 0xC0F16006),
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
        ("pmp", _pmp),
        ("satp", _satp),
        ("misaligned", _misaligned),
        ("extensions", _extensions),
    ):
        tc = test_data.begin_test_chunk(split_name=name)
        tc.code = body(test_data)
        chunks.append(test_data.end_test_chunk())
    return chunks
