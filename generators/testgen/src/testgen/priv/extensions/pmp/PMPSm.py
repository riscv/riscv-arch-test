##################################
# priv/extensions/pmp/PMPSm.py
#
# PMPSm: machine-mode PMP configuration and enforcement.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMPSm suite: pmpcfg/pmpaddr WARL behaviour and M-mode PMP enforcement."""

from testgen.asm.csr import gen_csr_write_sigupd
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.pmp.helpers import (
    LOCKED_LXWR_CASES,
    NAPOT_MASK_DEFINES,
    REGION_BLOBS,
    RETURN_TRAMPOLINE,
    TOR_ENTRIES,
    TOR_REGION_WORDS,
    cfg_byte,
    cfg_shift,
    entry_walk,
    lxwr_walk_body,
    set_pmpaddr,
    set_pmpcfg,
    zero_pmp_regs,
)
from testgen.priv.extensions.pmp.probes import (
    gen_lw_bounds,
    gen_rwx,
    gen_rwx_all,
    gen_rwx_legal,
    gen_rwx_na4,
    gen_rwx_napot,
    gen_rwx_tor_bot,
    gen_rwx_tor_zero,
)
from testgen.priv.registry import add_priv_test_generator

#####################################################################
# pmpcfg_walk: WARL readback of every pmpcfg CSR bit
#####################################################################

_MAX_PMP_ENTRIES = 64


def _packed_pmpcfg_writes(values: list[str], xlen: int) -> list[str]:
    """Pack entry values into the legal pmpcfg CSRs for one XLEN."""
    entries_per_csr = xlen // 8
    csr_step = xlen // 32
    lines = []
    for base in range(0, len(values), entries_per_csr):
        packed = "|".join(values[base : base + entries_per_csr])
        lines.extend([f"LI(x4, ({packed}))", f"csrw pmpcfg{(base // entries_per_csr) * csr_step}, x4"])
    return lines


def _csr_walk(value: str, label: str) -> list[str]:
    """Write ``value`` to every implemented pmpcfg CSR and check the readback."""
    return [
        ".set pmpcfgi, CSR_PMPCFG0",
        ".rept UDB_NUM_PMP_ENTRIES / (UDB_MXLEN / 8)",
        f"1:  LI(t2, {value})",
        f"RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, {label}_str)",
        ".set pmpcfgi, pmpcfgi + (UDB_MXLEN / 32)",
        ".endr",
    ]


def _make_zero_walk_chunk(test_data: TestData) -> TestChunk:
    chunk = test_data.begin_test_chunk("pmpcfg_walk_01")
    chunk.section_header = comment_banner("cp_pmpcfg_walk", "Write zero to every pmpcfg CSR and check the readback.")
    chunk.code.extend(
        [
            test_data.add_testcase("zero", "cp_pmpcfg_walk", "PMPSm"),
            "// Write zero to every pmpcfg CSR",
            *_csr_walk("0", test_data.current_testcase_label),
        ]
    )
    chunk.sigupd_count = _MAX_PMP_ENTRIES // 4
    return test_data.end_test_chunk()


def _make_pmpcfg_walk_chunk(test_data: TestData, number: int, byte: int) -> TestChunk:
    """Walk a one through the legal bits of configuration byte ``byte`` of every pmpcfg CSR."""
    chunk = test_data.begin_test_chunk(f"pmpcfg_walk_{number:02d}")
    chunk.section_header = comment_banner(
        "cp_pmpcfg_walk",
        f"Write a walking one through bits {8 * byte}..{8 * byte + 7} of every pmpcfg CSR and check\n"
        "the readback, skipping the reserved R=0/W=1 encoding and the A=NA4 bit.",
    )
    cases = 0
    for bit in range(8 * byte, 8 * byte + 8):
        if bit % 8 in (1, 4):  # W without R is reserved; A=NA4 is optional.
            continue
        if chunk.code:
            chunk.code.append("")
        chunk.code.extend(
            [
                test_data.add_testcase(f"bit{bit}", "cp_pmpcfg_walk", "PMPSm"),
                f"// Write 1 << {bit} to every pmpcfg CSR",
                *_csr_walk(f"1 << {bit}", test_data.current_testcase_label),
            ]
        )
        cases += 1
    chunk.sigupd_count = cases * (_MAX_PMP_ENTRIES // 4)
    return test_data.end_test_chunk()


#####################################################################
# cfg_*: pmpcfg A/L/XWR enforcement
#####################################################################

#: The 15 PMP entries below the background entry of a 16-entry PMP, lowest priority first.
_ENTRIES = tuple(range(14, -1, -1))


# ---------------------------------------------------------------------------
# cfg_A_all: pmpcfg.A is writable in every region
# ---------------------------------------------------------------------------


def _make_a_all_chunk(test_data: TestData) -> TestChunk:
    chunk = test_data.begin_test_chunk("cfg_A_all")
    chunk.section_header = comment_banner(
        "cp_cfg_A_all", "Write A = NA4, NAPOT, TOR and OFF into every byte of every pmpcfg CSR and read it back."
    )
    chunk.code.extend([*zero_pmp_regs(), "", "RVTEST_PMP_SET_BACKGROUND x4"])

    def add_csr_checks(name: str, const: str | None, csrs: tuple[int, ...]) -> None:
        for csr in csrs:
            chunk.code.extend(
                [
                    test_data.add_testcase(f"{name}_pmpcfg{csr}", "cp_cfg_A_all", "PMPSm"),
                    gen_csr_write_sigupd(4 if const else 0, f"pmpcfg{csr}", test_data),
                ]
            )

    for name, const in (("NA4", "PMP_NA4"), ("NAPOT", "PMP_NAPOT"), ("TOR", "PMP_TOR"), ("OFF", None)):
        chunk.code.extend(["", f"// PMP configuration: write A = {name} to every byte of every pmpcfg CSR"])
        if const:
            rv32_bytes = "|".join(f"(({const}&0xFF) << PMP{i}_CFG_SHIFT)" for i in range(4))
            rv64_bytes = "|".join(f"(({const}&0xFF) << PMP{i}_CFG_SHIFT)" for i in range(8))
            chunk.code.extend(
                [
                    "#if __riscv_xlen == 64",
                    f"LI(x4, {rv64_bytes})",
                    "#else",
                    f"LI(x4, {rv32_bytes})",
                    "#endif",
                ]
            )
        add_csr_checks(name, const, (0, 2))
        chunk.code.append("#if __riscv_xlen == 32")
        add_csr_checks(name, const, (1, 3))
        chunk.code.extend(["#endif", "#if UDB_NUM_PMP_ENTRIES == 64"])
        add_csr_checks(name, const, (4, 6, 8, 10, 12, 14))
        chunk.code.extend(["#endif", "#if UDB_NUM_PMP_ENTRIES == 64 && __riscv_xlen == 32"])
        add_csr_checks(name, const, (5, 7, 9, 11, 13, 15))
        chunk.code.append("#endif")
    return test_data.end_test_chunk()


# ---------------------------------------------------------------------------
# cfg_A_off_all: A=OFF never matches
# ---------------------------------------------------------------------------


def _make_a_off_all_chunk(test_data: TestData) -> TestChunk:
    chunk = test_data.begin_test_chunk("cfg_A_off_all")
    body = [
        *zero_pmp_regs(),
        "",
        "#define REGIONSTART TEST_FOR_EXECUTION",
        *NAPOT_MASK_DEFINES,
        "",
        "RVTEST_PMP_SET_BACKGROUND x4",
        "",
        *entry_walk(
            test_data,
            _ENTRIES,
            "napot",
            lambda e: f"({cfg_byte('1000', 'off', '0')} << {cfg_shift(e)})",
            gen_rwx,
            "cp_cfg_A_off_all",
        ),
    ]
    chunk.section_header = comment_banner(
        "cp_cfg_A_off_all",
        "{jalr, sw, lw} at a region whose entry has L = 1, A = OFF, XWR = 000, for every entry; all succeed.",
    )
    chunk.code.extend(body)
    chunk.raw_data.extend(tuple(REGION_BLOBS["napot_pad"]))
    return test_data.end_test_chunk()


# ---------------------------------------------------------------------------
# cfg_A_tor_bot: region 1 extends from pmpaddr0 to pmpaddr1
# ---------------------------------------------------------------------------


def _make_a_tor_bot_chunk(test_data: TestData) -> TestChunk:
    chunk = test_data.begin_test_chunk("cfg_A_tor_bot")
    body = [
        *zero_pmp_regs(),
        "",
        f"#define PMPREGION_UPPER_BOUND {cfg_byte('1101', 'tor', 'PMP1_CFG_SHIFT')}",
        f"#define PMPREGION_LOWER_BOUND {cfg_byte('1000', 'off', 'PMP0_CFG_SHIFT')}",
        "",
        "RVTEST_PMP_SET_BACKGROUND x4",
        "",
        *set_pmpaddr("tor", 1, "TEST_FOR_EXECUTION"),
        "",
        "// PMP configuration 1: pmpcfg1 = L, TOR, XR; pmpcfg0 = OFF, unlocked",
        *set_pmpcfg(0, "PMPREGION_UPPER_BOUND"),
        "RVTEST_SFENCE_VMA_IF_SUPPORTED",
        *gen_rwx_tor_bot(test_data, "unlocked", "cp_cfg_A_tor_bot"),
        "",
        "// PMP configuration 2: pmpcfg1 = L, TOR, XR; pmpcfg0 = OFF, locked",
        *set_pmpcfg(0, "PMPREGION_UPPER_BOUND|PMPREGION_LOWER_BOUND"),
        "RVTEST_SFENCE_VMA_IF_SUPPORTED",
        *gen_rwx_tor_bot(test_data, "locked", "cp_cfg_A_tor_bot"),
    ]
    chunk.section_header = comment_banner(
        "cp_cfg_A_tor_bot",
        "{sw, lw, jalr} at pmpaddr0-4, pmpaddr0, pmpaddr1-4 and pmpaddr1 with entry 1 = L, TOR, XR and entry 0 = OFF, unlocked then locked.",
    )
    chunk.code.extend(body)
    chunk.raw_data.extend(tuple(REGION_BLOBS["tor"]))
    return test_data.end_test_chunk()


# ---------------------------------------------------------------------------
# cfg_A_tor_zero: region 0 extends from address 0 to pmpaddr0
# ---------------------------------------------------------------------------


def _make_a_tor_zero_chunk(test_data: TestData) -> TestChunk:
    chunk = test_data.begin_test_chunk("cfg_A_tor_zero")
    body = [
        *zero_pmp_regs(),
        "",
        f"#define PMPREGION_TOR {cfg_byte('1111', 'tor', 'PMP0_CFG_SHIFT')}",
        "",
        "RVTEST_PMP_SET_BACKGROUND x4",
        "",
        "LA(x5, TEST_FOR_EXECUTION)",
        "srl x5, x5, PMP_SHIFT",
        "csrw pmpaddr0, x5",
        "",
        "// PMP configuration 1: pmpcfg0 = L, TOR, XWR: region 0 spans [0, TEST_FOR_EXECUTION)",
        *set_pmpcfg(0, "PMPREGION_TOR"),
        "RVTEST_SFENCE_VMA_IF_SUPPORTED",
        *gen_rwx_tor_zero(test_data, "region0", "cp_cfg_A_tor0"),
    ]
    chunk.section_header = comment_banner(
        "cp_cfg_A_tor0", "{sw, lw, jalr} at pmpaddr0, pmpaddr0-4 and 0 with entry 0 = L, TOR, XWR."
    )
    chunk.code.extend(body)
    chunk.raw_data.extend(tuple(REGION_BLOBS["off"]))
    return test_data.end_test_chunk()


# ---------------------------------------------------------------------------
# cfg_L_access_all: L=0 never restricts M-mode
# ---------------------------------------------------------------------------


def _make_l_access_all_chunk(test_data: TestData) -> TestChunk:
    chunk = test_data.begin_test_chunk("cfg_L_access_all")
    body = [
        *zero_pmp_regs(),
        "",
        "#define REGIONSTART TEST_FOR_EXECUTION",
        *NAPOT_MASK_DEFINES,
        "",
        "// PMP configuration 0: M-mode access succeeds when every PMP entry is off",
        "RVTEST_SFENCE_VMA_IF_SUPPORTED",
        *gen_rwx(test_data, "all_off", "cp_none"),
        "",
        "RVTEST_PMP_SET_BACKGROUND x4",
        *entry_walk(
            test_data,
            _ENTRIES,
            "napot",
            lambda e: f"({cfg_byte('0000', 'napot', '0')} << {cfg_shift(e)})",
            gen_rwx,
            "cp_cfg_L_access_all",
        ),
    ]
    chunk.section_header = comment_banner(
        "cp_cfg_L_access_all and cp_none",
        "{jalr, sw, lw} with every PMP entry off, then at a region whose entry has L = 0, A = NAPOT, XWR = 000, for every entry; all succeed.",
    )
    chunk.code.extend(body)
    chunk.raw_data.extend(tuple(REGION_BLOBS["napot_pad"]))
    return test_data.end_test_chunk()


# ---------------------------------------------------------------------------
# cfg_L_modify_{off,tor,napot}: locked entries reject writes
# ---------------------------------------------------------------------------

#: (name, setup lines with {cfg} = the entry-1 configuration, CSR, source register)
_L_MODIFY_STEPS = (
    ("write_pmpaddr1", "addi x4, x0, 0x100", "pmpaddr1", 4),
    ("write_pmpcfg0", "LI(x4, {cfg})", "pmpcfg0", 4),
    ("modify_pmpcfg0", "addi x5, x4, 7", "pmpcfg0", 5),
    ("modify_pmpaddr0", "addi x4, x0, -1", "pmpaddr0", 4),
    ("clear_pmpaddr1", "", "pmpaddr1", 0),
    ("clear_pmpcfg0", "", "pmpcfg0", 0),
)
_L_MODIFY_RESET = (("reset_pmpaddr0", "", "pmpaddr0", 0), ("reset_pmpcfg0", "", "pmpcfg0", 0))


def _make_l_modify_chunk(test_data: TestData, amode: str) -> TestChunk:
    chunk = test_data.begin_test_chunk(f"cfg_L_modify_{amode}")
    chunk.section_header = comment_banner(
        "cp_cfg_L_modify",
        f"Write and read back pmpaddr1/pmpcfg0 with entry 1 = {amode.upper()}, L = {{0, 1}}: locked entries and, for TOR, "
        "the preceding pmpaddr reject writes.",
    )
    chunk.code.extend([*zero_pmp_regs(), "", "RVTEST_PMP_SET_BACKGROUND x4"])
    for lock in (0, 1):
        chunk.code.extend(
            [
                "",
                f"// PMP configuration {lock + 1}: entry 1 = {amode.upper()}, L = {lock}, XWR = {lock}111, pmpaddr1 = 0x100",
            ]
        )
        steps = [*_L_MODIFY_STEPS, *(_L_MODIFY_RESET if lock == 0 else [])]
        for step, setup, csr, src in steps:
            chunk.code.extend(setup.format(cfg=cfg_byte(f"{lock}111", amode, "PMP1_CFG_SHIFT")).splitlines())
            chunk.code.extend(
                [
                    f"{test_data.add_testcase(f'L{lock}_{step}', 'cp_cfg_L_modify', 'PMPSm')}",
                    gen_csr_write_sigupd(src, csr, test_data),
                ]
            )
    return test_data.end_test_chunk()


# ---------------------------------------------------------------------------
# cfg_XWR_all: every legal XWR encoding in every region
# ---------------------------------------------------------------------------

#: The XWR code written to each region, lowest priority first, across the four files.
_XWR_ROLL = (
    "000 100 001 101 011 111 000 100 001 101 011 111 000 100 001",
    "101 011 111 000 100 001 101 011 111 000 100 001 101 011 111",
    "111 001 101 001 100 000 111 001 101 001 101 000 111 001 101",
    "001 100 000 111 001 101 001 100 000 111 011 101 001 100 000",
)


def _make_xwr_all_chunk(test_data: TestData, part: int) -> TestChunk:
    chunk = test_data.begin_test_chunk(f"cfg_XWR_all-{part:02d}")
    codes = _XWR_ROLL[part - 1].split()
    body = [
        *zero_pmp_regs(),
        "",
        *(f"#define PMPREGION_XWR_{xwr} {cfg_byte(f'1{xwr}', 'napot', '0')}" for xwr in sorted(set(codes))),
        "#define REGIONSTART TEST_FOR_EXECUTION",
        *NAPOT_MASK_DEFINES,
        "",
        "RVTEST_PMP_SET_BACKGROUND x4",
        "",
        "// Every entry covers the region; only its permissions vary below.",
        *set_pmpaddr("napot", 0)[:-1],
        ".set pmpaddri, CSR_PMPADDR0",
        ".rept UDB_NUM_PMP_ENTRIES",
        "csrw pmpaddri, x5",
        ".set pmpaddri, pmpaddri+1",
        ".endr",
        "",
    ]
    first = 15 * (part - 1) + 1
    for n, (entry, xwr) in enumerate(zip(_ENTRIES, codes, strict=True), start=first):
        body.extend(["", f"// PMP configuration {n}: L = 1 and XWR = {xwr} on PMP entry {entry}"])
        body.extend(set_pmpcfg(entry, f"(PMPREGION_XWR_{xwr} << {cfg_shift(entry)})"))
        body.extend(["RVTEST_SFENCE_VMA_IF_SUPPORTED", *gen_rwx_all(test_data, f"entry{entry}_lxwr{xwr}", "cp_cfg_RW")])
    chunk.section_header = comment_banner(
        "cp_cfg_X0_all, cp_cfg_X1_all, cp_cfg_RW00_all, cp_cfg_RW10_all and cp_cfg_RW11_all",
        "Every load and store width plus a jalr at a locked NAPOT region, rolling the six legal XWR over entries 14..0.",
    )
    chunk.code.extend(body)
    chunk.raw_data.extend(tuple(REGION_BLOBS["napot_pad"]))
    return test_data.end_test_chunk()


# ---------------------------------------------------------------------------
# cfg_na4_all / cfg_napot_all: A=NA4 / A=NAPOT works in every region
# ---------------------------------------------------------------------------


def _make_amode_all_chunk(test_data: TestData, amode: str) -> TestChunk:
    chunk = test_data.begin_test_chunk(f"cfg_{amode}_all")
    beyond = "4" if amode == "na4" else "PMP_NAPOT_REGION_BYTES"
    body = [
        *zero_pmp_regs(),
        "",
        "#define REGIONSTART TEST_FOR_EXECUTION",
        *(NAPOT_MASK_DEFINES if amode == "napot" else []),
        "",
        "RVTEST_PMP_SET_BACKGROUND x4",
        "",
    ]
    body.extend(
        entry_walk(
            test_data,
            _ENTRIES,
            amode,
            lambda e: cfg_byte("1000", amode, cfg_shift(e)),
            lambda data, case, coverpoint, region: gen_lw_bounds(data, case, coverpoint, region, beyond),
            f"cp_cfg_A_{amode}_all",
        )
    )
    chunk.section_header = comment_banner(
        f"cp_cfg_A_{amode}_all",
        f"lw at, 4 below and just beyond a locked no-permission {amode.upper()} region, for every entry.",
    )
    chunk.code.extend(body)
    chunk.raw_data.extend(tuple(REGION_BLOBS["off" if amode == "na4" else "napot_pad"]))
    return test_data.end_test_chunk()


# ---------------------------------------------------------------------------
# cfg_tor_all: A=TOR works in every region
# ---------------------------------------------------------------------------


def _make_tor_all_chunk(test_data: TestData) -> TestChunk:
    chunk = test_data.begin_test_chunk("cfg_tor_all")
    body = [
        *zero_pmp_regs(),
        "",
        *(
            f"#define PMPREGION{i}_XWR_{'111' if i == 0 else ('001' if i % 2 else '000')} "
            f"{cfg_byte('1111' if i == 0 else ('1001' if i % 2 else '1000'), 'tor', cfg_shift(i))}"
            for i in range(15)
        ),
        "",
        "RVTEST_PMP_SET_BACKGROUND x4",
        "",
        "// pmpaddr_i = TEST_FOR_EXECUTION_i, so TOR region i+1 is [TEST_FOR_EXECUTION_i, TEST_FOR_EXECUTION_i+1)",
    ]
    for entry in range(15):
        body.extend([f"LA(x5, TEST_FOR_EXECUTION_{entry})", "srl x5, x5, PMP_SHIFT", f"csrw pmpaddr{entry}, x5"])
    body.extend(
        [
            "",
            "// PMP configuration 1: every region L = 1, A -> TOR, XWR = 00(i%2); lw at the start of each region",
        ]
    )
    cfg_values = [
        f"PMPREGION{entry}_XWR_{'111' if entry == 0 else ('001' if entry % 2 else '000')}" for entry in range(15)
    ]
    body.extend(
        [
            "#if __riscv_xlen == 64",
            *_packed_pmpcfg_writes(cfg_values, 64),
            "#else",
            *_packed_pmpcfg_writes(cfg_values, 32),
            "#endif",
        ]
    )
    body.append("RVTEST_SFENCE_VMA_IF_SUPPORTED")
    for n in range(1, 16):
        body.extend(
            [
                "RVTEST_SFENCE_VMA_IF_SUPPORTED",
                "",
                f"LA(a5, TEST_FOR_EXECUTION_{n - 1})",
                test_data.add_testcase(f"entry{n}_1_lw", "cp_cfg_A_tor_all", "PMPSm"),
                "lw a4, 0(a5)",
                write_sigupd(14, test_data),
            ]
        )
    data = [
        ".p2align 12",
        ".p2align (UDB_PMP_GRANULARITY)",
        "TEST_FOR_EXECUTION_X:",
        f".rept {TOR_REGION_WORDS}",
        "jr ra",
        ".endr",
    ]
    for i in range(15):
        data.extend([f"TEST_FOR_EXECUTION_{i}:", f".rept ({i + 1} * (PMP_TOR_REGION_BYTES / 4))", "nop", ".endr"])
    data.extend(RETURN_TRAMPOLINE)
    chunk.section_header = comment_banner(
        "cp_cfg_A_tor_all", "Fifteen locked TOR regions of increasing size with XWR = 00(i%2); lw at the start of each."
    )
    chunk.code.extend(body)
    chunk.raw_data.extend(tuple(data))
    return test_data.end_test_chunk()


# ---------------------------------------------------------------------------
# cfg_tor_check: a TOR region with pmpaddr0 >= pmpaddr1 never matches
# ---------------------------------------------------------------------------

_TOR_CHECK_CASES = (
    ("pmpaddr0 = pmpaddr1", ["csrw pmpaddr0, x5"]),
    (
        "pmpaddr0 = pmpaddr1 + g",
        ["LI(x6, PMP_TOR_REGION_BYTES >> PMP_SHIFT)", "add x6, x5, x6", "csrw pmpaddr0, x6"],
    ),
    ("pmpaddr0 = all ones", ["LI(x6, -1)", "csrw pmpaddr0, x6"]),
)


def _make_tor_check_chunk(test_data: TestData, part: int) -> TestChunk:
    chunk = test_data.begin_test_chunk(f"cfg_tor_check-{part:02d}")
    case, addr0 = _TOR_CHECK_CASES[part - 1]
    body = [
        *zero_pmp_regs(),
        "",
        f"#define PMPREGION_UPPER_BOUND {cfg_byte('1000', 'tor', 'PMP1_CFG_SHIFT')}",
        "",
        "RVTEST_PMP_SET_BACKGROUND x4",
        "",
        "LA(x5, TEST_FOR_EXECUTION)",
        "srl x5, x5, PMP_SHIFT",
        "csrw pmpaddr1, x5",
        *addr0,
        "",
        f"// PMP configuration 1: pmpcfg1 = L, TOR, no permissions; {case}",
        *set_pmpcfg(0, "PMPREGION_UPPER_BOUND"),
        "RVTEST_SFENCE_VMA_IF_SUPPORTED",
        *gen_rwx_na4(test_data, f"non_overlap{part}", "cp_cfg_A_tor_non_overlap"),
    ]
    chunk.section_header = comment_banner(
        f"cp_cfg_A_tor_non-overlap test case {part}",
        f"{{jalr, sw, lw}} around a locked TOR entry 1 with no permissions while {case}; no match, so all succeed.",
    )
    chunk.code.extend(body)
    chunk.raw_data.extend(tuple(REGION_BLOBS["off"]))
    return test_data.end_test_chunk()


#####################################################################
# pmpsm_grain / pmpsm_grain_check: pmpaddr readback versus the grain
#####################################################################


def _make_grain_chunk(test_data: TestData) -> TestChunk:
    chunk = test_data.begin_test_chunk("grain")
    chunk.section_header = comment_banner(
        "cp_grain",
        "Write zeros, ones and a checkerboard to pmpaddr0 with A = NAPOT and OFF; read back with A = OFF, NAPOT and TOR.",
    )
    chunk.code.extend(
        [
            *zero_pmp_regs(),
            "",
            *(
                f"#define PMPREGION_{mode} {cfg_byte('0111', mode.lower(), 'PMP0_CFG_SHIFT')}"
                for mode in ("OFF", "NAPOT", "TOR")
            ),
            "#define PMP_GRAIN_MASK ((1 << (UDB_PMP_GRANULARITY - 2)) - 1)",
            "#if __riscv_xlen == 64",
            "#define CHECKERBOARD 0xAAAAAAAAAAAAAAAA",
            "#else",
            "#define CHECKERBOARD 0xAAAAAAAA",
            "#endif",
            "",
            "RVTEST_PMP_SET_BACKGROUND x4",
            "",
            "LI(t3, PMP_GRAIN_MASK)",
            "",
        ]
    )
    for pattern, value in (("zeros", "0"), ("ones", "-1"), ("checkerboard", "CHECKERBOARD")):
        for write_mode in ("NAPOT", "OFF"):
            for read_mode in ("OFF", "NAPOT", "TOR"):
                block = [
                    "",
                    test_data.add_testcase(f"{pattern}_write_{write_mode}_read_{read_mode}", "cp_grain", "PMPSm"),
                    f"// Write {pattern} to pmpaddr0 with A = {write_mode}, read back with A = {read_mode}",
                    f"LI(x6, PMPREGION_{write_mode})",
                    "csrw pmpcfg0, x6",
                    f"LI(x6, {value})",
                    "csrw pmpaddr0, x6",
                    f"LI(x6, PMPREGION_{read_mode})",
                    "csrw pmpcfg0, x6",
                    "csrr x7, pmpaddr0",
                    "and x7, x7, t3",
                    write_sigupd(7, test_data),
                ]
                if read_mode == "TOR":
                    block = ["#ifdef UDB_PMP_TOR_SUPPORTED", *block, "#endif"]
                chunk.code.extend(block)
    return test_data.end_test_chunk()


def _make_grain_check_chunk(test_data: TestData) -> TestChunk:
    chunk = test_data.begin_test_chunk("grain_check")
    chunk.section_header = comment_banner(
        "cp_grain_check",
        "Write all ones to pmpaddr0 with pmpcfg0 = 0 and read it back; the lowest set bit gives the grain.",
    )
    chunk.code.extend(
        [
            *zero_pmp_regs(),
            "",
            "#define PMP_GRAIN_CHECK_MASK ((1 << (UDB_PMP_GRANULARITY - 1)) - 1)",
            "",
            "RVTEST_PMP_SET_BACKGROUND x4",
            "",
            test_data.add_testcase("readback", "cp_grain_check", "PMPSm"),
            "// Write 0 to pmpcfg0 and all ones to pmpaddr0, then read back pmpaddr0",
            "csrw pmpcfg0, x0",
            "LI(x6, -1)",
            "csrw pmpaddr0, x6",
            "LI(t3, PMP_GRAIN_CHECK_MASK)",
            "csrr x7, pmpaddr0",
            "and x7, x7, t3",
            write_sigupd(7, test_data),
        ]
    )
    return test_data.end_test_chunk()


#####################################################################
# pmpsm_pmpaddr_upper: the architecturally zero high pmpaddr bits
#####################################################################


def _make_pmpaddr_upper_chunk(test_data: TestData) -> TestChunk:
    chunk = test_data.begin_test_chunk("pmpaddr_upper")
    chunk.section_header = comment_banner(
        "cp_pmpaddr_upper_zero", "Write ones to pmpaddr CSRs and check bits 63:54 read back as zero."
    )
    chunk.code.extend(
        [
            test_data.add_testcase("all_ones", "cp_pmpaddr_upper_zero", "PMPSm"),
            "// Write ones to every pmpaddr CSR and check bits 63:54 read back as zero",
            "LI(t0, -1)",
            "LI(t1, 0xFFC0000000000000)",
            ".set pmpaddri, CSR_PMPADDR0",
            ".rept UDB_NUM_PMP_ENTRIES",
            "1:  csrw pmpaddri, t0",
            "csrr t2, pmpaddri",
            "and t2, t2, t1",
            f"RVTEST_SIGUPD(x2, x5, x4, x7, 1b, {test_data.current_testcase_label}_str)",
            ".set pmpaddri, pmpaddri+1",
            ".endr",
        ]
    )
    chunk.sigupd_count += 64
    return test_data.end_test_chunk()


#####################################################################
# pmpsm_{na4,napot,tor}_legal_lxwr: every legal locked LXWR against
# one region in each address mode
#####################################################################


def _make_legal_chunk(test_data: TestData, amode: str, part: int | None = None) -> TestChunk:
    generator = {"na4": gen_rwx_na4, "napot": gen_rwx_napot, "tor": gen_rwx_legal}[amode]
    if part is None:
        cases, first, name = LOCKED_LXWR_CASES, 1, f"{amode}_legal_lxwr"
    else:
        cases = LOCKED_LXWR_CASES[3 * (part - 1) : 3 * part]
        if amode == "tor":
            cases = list(zip([lxwr for lxwr, _ in cases], TOR_ENTRIES[part - 1], strict=True))
        first, name = 3 * (part - 1) + 1, f"{amode}_legal_lxwr-{part:02d}"
    chunk = test_data.begin_test_chunk(name)
    chunk.section_header = comment_banner(
        f"cp_cfg_A_{amode}",
        f"{{jalr, sw, lw}} in M mode at and around a locked {amode.upper()} region, each legal XWR.",
    )
    chunk.code.extend(lxwr_walk_body(test_data, cases, amode, generator, f"cp_cfg_A_{amode}", first=first))
    chunk.raw_data.extend(tuple(REGION_BLOBS[amode]))
    return test_data.end_test_chunk()


#####################################################################
# pmpsm_priority / pmpsm_priority_off: overlapping regions
#####################################################################

#: LXWR code of each of the seven nested NAPOT regions, smallest (highest priority) first.
_PRIORITY_CODES = ("1000", "1101", "1011", "1100", "1001", "1111", "1000")


def _make_priority_chunk(test_data: TestData) -> TestChunk:
    chunk = test_data.begin_test_chunk("priority")
    body = [
        *zero_pmp_regs(),
        "",
        *(
            f"#define PMPREGION{e}_LXWR_{lxwr} {cfg_byte(lxwr, 'napot', cfg_shift(e))}"
            for e, lxwr in enumerate(_PRIORITY_CODES)
        ),
        "",
        "RVTEST_PMP_SET_BACKGROUND x4",
        "",
        "// Seven overlapping NAPOT regions based at TEST_FOR_EXECUTION, of sizes",
        "// PMP_NAPOT_REGION_BYTES times 1, 2, 4, ..., 64: pmpaddr_i = (base >> 2) | (2^i * bytes/8 - 1)",
        "LA(x5, TEST_FOR_EXECUTION)",
        "srl x5, x5, PMP_SHIFT",
        ".set i, 0",
        ".set pmpaddri, CSR_PMPADDR0",
        ".rept 7",
        "LI(x6, (1 << i) * (PMP_NAPOT_REGION_BYTES / 8) - 1)",
        "or x6, x5, x6",
        "csrw pmpaddri, x6",
        ".set i, i+1",
        ".set pmpaddri, pmpaddri+1",
        ".endr",
    ]
    cfg_values = [f"PMPREGION{entry}_LXWR_{lxwr}" for entry, lxwr in enumerate(_PRIORITY_CODES)]
    body.extend(
        [
            "#if __riscv_xlen == 64",
            *_packed_pmpcfg_writes(cfg_values, 64),
            "#else",
            *_packed_pmpcfg_writes(cfg_values, 32),
            "#endif",
        ]
    )
    body.extend(["RVTEST_SFENCE_VMA_IF_SUPPORTED"])
    for n, lxwr in enumerate(_PRIORITY_CODES, start=1):
        size = 1 << (n - 1)
        body.extend(
            [
                "",
                f"// PMP configuration {n}: access the last word of region {n - 1} (size {size}x), permissions {lxwr}",
                "RVTEST_SFENCE_VMA_IF_SUPPORTED",
                *gen_rwx(
                    test_data,
                    f"region{n - 1}_lxwr{lxwr}",
                    "cp_priority",
                    f"(TEST_FOR_EXECUTION + {size} * PMP_NAPOT_REGION_BYTES - 4)",
                ),
            ]
        )
    data = [
        ".p2align 12",
        "TEST_FOR_EXECUTION_0:",
        "jr ra",
        ".p2align (UDB_PMP_GRANULARITY + 7)",
        "TEST_FOR_EXECUTION:",
        ".rept (16 * PMP_NAPOT_REGION_BYTES)",
        "nop",
        ".endr",
        *RETURN_TRAMPOLINE,
    ]
    chunk.section_header = comment_banner(
        "cp_priority",
        "{jalr, sw, lw} at the last word of each of seven nested NAPOT regions cycling the six legal XWR; the smallest matching region decides.",
    )
    chunk.code.extend(body)
    chunk.raw_data.extend(tuple(data))
    return test_data.end_test_chunk()


def _make_priority_off_chunk(test_data: TestData) -> TestChunk:
    chunk = test_data.begin_test_chunk("priority_off")
    codes = (("1000", "off"), ("1101", "napot"), ("1000", "off"), ("1111", "napot"))
    body = [
        *zero_pmp_regs(),
        "",
        *(
            f"#define PMPREGION{e}_LXWR_{lxwr} {cfg_byte(lxwr, amode, cfg_shift(e))}"
            for e, (lxwr, amode) in enumerate(codes)
        ),
        "#define REGIONSTART TEST_FOR_EXECUTION",
        *NAPOT_MASK_DEFINES,
        "",
        "RVTEST_PMP_SET_BACKGROUND x4",
        "",
        "// pmpaddr0 and pmpaddr2: OFF regions; pmpaddr1 and pmpaddr3: NAPOT regions at REGIONSTART",
        *set_pmpaddr("na4", 0),
        "csrw pmpaddr2, x5",
        *set_pmpaddr("napot", 1),
        "csrw pmpaddr3, x5",
        "",
        "// PMP configuration 1: an OFF region does not match, and the first matching region takes priority",
        *set_pmpcfg(0, "|".join(f"PMPREGION{e}_LXWR_{lxwr}" for e, (lxwr, _) in enumerate(codes))),
        "RVTEST_SFENCE_VMA_IF_SUPPORTED",
        *gen_rwx(test_data, "entry1", "cp_priority_off"),
    ]
    chunk.section_header = comment_banner(
        "cp_priority_off",
        "{jalr, sw, lw} at a region covered by entries 0..3 = OFF, NAPOT XR, OFF, NAPOT XWR; entry 1 decides.",
    )
    chunk.code.extend(body)
    chunk.raw_data.extend(tuple(REGION_BLOBS["napot_pad"]))
    return test_data.end_test_chunk()


#####################################################################
# pmpsm_all_entries_check: every PMP entry enforces load/store access
#####################################################################


def _make_all_entries_chunk(test_data: TestData) -> TestChunk:
    chunk = test_data.begin_test_chunk("all_entries_check")

    def _all_entries_cfg(entry: int) -> str:
        return f"(PMP_REGION_CFG << {cfg_shift(entry)})"

    body = [
        *zero_pmp_regs(),
        "",
        f"#define PMP_REGION_CFG {cfg_byte('1101', 'napot', '0')}",
        "#define REGIONSTART TEST_FOR_EXECUTION",
        *NAPOT_MASK_DEFINES,
        "",
        "RVTEST_PMP_SET_BACKGROUND x4",
        "",
        "// Every entry below the background entry, lowest priority first.",
        "#if UDB_NUM_PMP_ENTRIES == 64",
        *entry_walk(
            test_data,
            range(62, -1, -1),
            "napot",
            _all_entries_cfg,
            gen_rwx,
            "cp_pmp64",
            case_prefix="pmp64_entry",
        ),
        "#else",
        *entry_walk(
            test_data,
            range(14, -1, -1),
            "napot",
            _all_entries_cfg,
            gen_rwx,
            "cp_pmp64",
            case_prefix="pmp16_entry",
        ),
        "#endif",
    ]
    chunk.section_header = comment_banner(
        "cp_pmp64",
        "{jalr, sw, lw} at a locked NAPOT XR region, for every entry below the background entry (16 or 64 entries).",
    )
    chunk.code.extend(body)
    chunk.raw_data.extend(tuple(REGION_BLOBS["napot_pad"]))
    return test_data.end_test_chunk()


#####################################################################


@add_priv_test_generator(
    "PMPSm",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Sm"],
    params=["NUM_PMP_ENTRIES: '>0'"],
)
def make_pmpsm_base(test_data: TestData) -> list[TestChunk]:
    return [
        _make_zero_walk_chunk(test_data),
        *(_make_pmpcfg_walk_chunk(test_data, byte + 2, byte) for byte in range(4)),
        _make_a_all_chunk(test_data),
        _make_a_off_all_chunk(test_data),
        _make_l_access_all_chunk(test_data),
        _make_l_modify_chunk(test_data, "off"),
        *(_make_xwr_all_chunk(test_data, part) for part in range(1, 5)),
        _make_grain_chunk(test_data),
        _make_grain_check_chunk(test_data),
    ]


@add_priv_test_generator(
    "PMPSm",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Sm"],
    params=["MXLEN: 64", "NUM_PMP_ENTRIES: '>0'"],
)
def make_pmpsm_rv64(test_data: TestData) -> list[TestChunk]:
    return [
        *(_make_pmpcfg_walk_chunk(test_data, byte + 2, byte) for byte in range(4, 8)),
        _make_pmpaddr_upper_chunk(test_data),
    ]


@add_priv_test_generator(
    "PMPSm",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Sm"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_NA4_SUPPORTED: true"],
)
def make_pmpsm_na4(test_data: TestData) -> list[TestChunk]:
    return [_make_amode_all_chunk(test_data, "na4"), _make_legal_chunk(test_data, "na4")]


@add_priv_test_generator(
    "PMPSm",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Sm"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_NAPOT_SUPPORTED: true"],
)
def make_pmpsm_napot(test_data: TestData) -> list[TestChunk]:
    return [
        _make_l_modify_chunk(test_data, "napot"),
        _make_amode_all_chunk(test_data, "napot"),
        *(_make_legal_chunk(test_data, "napot", part) for part in (1, 2)),
        _make_priority_chunk(test_data),
        _make_priority_off_chunk(test_data),
        _make_all_entries_chunk(test_data),
    ]


@add_priv_test_generator(
    "PMPSm",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Sm"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_TOR_SUPPORTED: true"],
)
def make_pmpsm_tor(test_data: TestData) -> list[TestChunk]:
    return [
        _make_a_tor_bot_chunk(test_data),
        _make_a_tor_zero_chunk(test_data),
        _make_l_modify_chunk(test_data, "tor"),
        _make_tor_all_chunk(test_data),
        *(_make_tor_check_chunk(test_data, part) for part in (1, 2, 3)),
        *(_make_legal_chunk(test_data, "tor", part) for part in (1, 2)),
    ]
