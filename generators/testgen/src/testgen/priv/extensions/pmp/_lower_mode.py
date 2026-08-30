##################################
# priv/extensions/pmp/_lower_mode.py
#
# PMPS and PMPU: PMP configured in M mode and probed from S or U mode.
# SPDX-License-Identifier: Apache-2.0
##################################

"""The PMPS and PMPU suites, which differ only in the mode the probes run from."""

from dataclasses import dataclass

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.pmp.helpers import (
    LOCKED_LXWR_CASES,
    NAPOT_MASK_DEFINES,
    REGION_BLOBS,
    TOR_ENTRIES,
    UNLOCKED_LXWR_CASES,
    cfg_byte,
    cfg_shift,
    lxwr_walk_body,
    set_pmpaddr,
    set_pmpcfg,
    zero_pmp_regs,
)
from testgen.priv.extensions.pmp.probes import (
    gen_rwx,
    gen_rwx_all,
    gen_rwx_legal,
    gen_rwx_mprv,
    gen_rwx_na4,
    gen_rwx_napot,
)


@dataclass(frozen=True)
class Mode:
    """The lower privilege mode a suite probes from."""

    letter: str  # "S" | "U"
    mpp: str  # mstatus.MPP encoding of the mode

    @property
    def prefix(self) -> str:
        return f"pmp{self.letter.lower()}"

    @property
    def suite(self) -> str:
        return f"PMP{self.letter}"


S_MODE = Mode("S", "(1 << 11)")
U_MODE = Mode("U", "0")


def _make_cfg_a_off_chunk(test_data: TestData, mode: Mode) -> TestChunk:
    chunk = test_data.begin_test_chunk("cfg_A_off")
    body = [
        *zero_pmp_regs(),
        "",
        "RVTEST_PMP_SET_BACKGROUND x4",
        "",
        "// PMP configuration 1: L = 0, A = OFF and no permissions given to PMP entry 0, pmpaddr0 = all ones",
        "LI(x5, -1)",
        "csrw pmpaddr0, x5",
        "csrw pmpcfg0, x0",
        "RVTEST_SFENCE_VMA_IF_SUPPORTED",
        f"RVTEST_TSBI_GOTO_{mode.letter}MODE",
        *gen_rwx(test_data, "off", "cp_cfg_A_off"),
        "RVTEST_TSBI_GOTO_MMODE",
    ]
    chunk.section_header = comment_banner(
        f"{mode.suite} cp_cfg_A_off",
        f"{{jalr, sw, lw}} from {mode.letter} mode at a region whose entry has A = OFF, XWR = 000 and pmpaddr = all ones; all succeed.",
    )
    chunk.code.extend(body)
    chunk.raw_data.extend(REGION_BLOBS["off"])
    return test_data.end_test_chunk()


def _make_cfg_xwr_chunk(test_data: TestData, mode: Mode, *, locked: bool) -> TestChunk:
    name = "cfg_XWR" if locked else "cfg_XWR_unlocked"
    cases = LOCKED_LXWR_CASES if locked else UNLOCKED_LXWR_CASES
    chunk = test_data.begin_test_chunk(name)
    chunk.section_header = comment_banner(
        f"{mode.suite} cp_cfg_X and cp_cfg_RW",
        f"Every load and store width plus a jalr from {mode.letter} mode at the start of a NAPOT region, "
        f"L = {int(locked)}, each legal XWR.",
    )
    chunk.code.extend(lxwr_walk_body(test_data, cases, "napot", gen_rwx_all, "cp_cfg_RW", lower_mode=mode.letter))
    chunk.raw_data.extend(REGION_BLOBS["off"])
    return test_data.end_test_chunk()


def _csr_walk(symbol: str, first: str, count: int, string_label: str, mode: Mode) -> list[str]:
    """Write all ones to every CSR of one bank from the lower mode, checking each trap."""
    return [
        f".set {symbol}, {first}",
        f".rept {count}",
        f"RVTEST_TSBI_GOTO_{mode.letter}MODE",
        "99:",
        f"RVTEST_SIGUPD_CSR_WRITE({symbol}, x4, 99b, {string_label}_str)",
        "nop",
        "RVTEST_TSBI_GOTO_MMODE",
        f".set {symbol}, {symbol}+1",
        ".endr",
    ]


def _make_csr_access_chunk(test_data: TestData, mode: Mode) -> TestChunk:
    low = mode.letter.lower()
    chunk = test_data.begin_test_chunk("csr_access")
    chunk.section_header = comment_banner(
        f"{mode.suite} cp_pmpaddr_access_{low} and cp_pmpcfg_access_{low}",
        f"Write every pmpaddr and pmpcfg CSR from {mode.letter} mode; each traps with an illegal instruction.",
    )
    chunk.code.extend(
        [
            "RVTEST_PMP_SET_BACKGROUND x4",
            "",
            test_data.add_testcase("write_all", f"cp_pmpaddr_access_{low}", mode.suite),
            f"// Write all ones to every pmpaddr CSR from {mode.letter} mode",
            "LI(x4, -1)",
            *_csr_walk("pmpaddri", "CSR_PMPADDR0", 64, test_data.current_testcase_label, mode),
            "",
            test_data.add_testcase("write_all", f"cp_pmpcfg_access_{low}", mode.suite),
            f"// Write all ones to every pmpcfg CSR from {mode.letter} mode",
            *_csr_walk("pmpcfgi", "CSR_PMPCFG0", 16, test_data.current_testcase_label, mode),
        ]
    )
    chunk.sigupd_count = 80
    return test_data.end_test_chunk()


def _make_mprv_chunk(test_data: TestData, mode: Mode, part: int) -> TestChunk:
    chunk = test_data.begin_test_chunk(f"mprv_check-0{part}")
    xwr = "000" if part == 1 else "111"
    body = [
        *zero_pmp_regs(),
        "",
        f"#define PMPREGION_LXWR_0{xwr} {cfg_byte(f'0{xwr}', 'napot', cfg_shift(0))}",
        f"#define PMPREGION_LXWR_1{xwr} {cfg_byte(f'1{xwr}', 'napot', cfg_shift(0))}",
        "#define MPRV       (1 << 17)",
        "#define MPP        (3 << 11)",
        f"#define MPP_LOWER  {mode.mpp}",
        "#define REGIONSTART TEST_FOR_EXECUTION",
        *NAPOT_MASK_DEFINES,
        "",
        "RVTEST_PMP_SET_BACKGROUND x4",
        "",
    ]
    n = 0
    for lock in (0, 1):
        body.extend(["", *set_pmpaddr("napot", 0), *set_pmpcfg(0, f"PMPREGION_LXWR_{lock}{xwr}")])
        body.append("RVTEST_SFENCE_VMA_IF_SUPPORTED")
        for mprv in (0, 1):
            n += 1
            bits = "MPP_LOWER|MPRV" if mprv else "MPP_LOWER"
            body.extend(
                [
                    "",
                    f"// PMP configuration {n}: mstatus.MPRV = {mprv}, mstatus.MPP = {mode.letter} mode, L = {lock}, XWR = {xwr}",
                    *gen_rwx_mprv(test_data, f"lock{lock}_mprv{mprv}", "cp_mprv", bits),
                ]
            )
    chunk.section_header = comment_banner(
        f"{mode.suite} cp_mprv",
        f"{{jalr, sw, lw}} from M mode with mstatus.MPRV = {{0, 1}} and MPP = {mode.letter}, region L = {{0, 1}}, XWR = {xwr}.",
    )
    chunk.code.extend(body)
    chunk.raw_data.extend(REGION_BLOBS["napot_pad"])
    return test_data.end_test_chunk()


def _make_legal_chunk(test_data: TestData, mode: Mode, amode: str, part: int | None = None) -> TestChunk:
    """The six unlocked XWR encodings against one NA4, NAPOT or TOR region, from the lower mode."""
    cases = UNLOCKED_LXWR_CASES if part is None else UNLOCKED_LXWR_CASES[3 * (part - 1) : 3 * part]
    if amode == "tor":
        cases = [(lxwr, entry) for (lxwr, _), entry in zip(cases, TOR_ENTRIES[part - 1 if part else 0], strict=True)]
    name = f"{amode}_legal_lxwr" + ("" if part is None else f"-0{part}")
    generator = {"na4": gen_rwx_na4, "napot": gen_rwx_napot, "tor": gen_rwx_legal}[amode]
    chunk = test_data.begin_test_chunk(name)
    chunk.section_header = comment_banner(
        f"{mode.suite} cp_cfg_A_{amode}",
        f"{{jalr, sw, lw}} from {mode.letter} mode at and around a {amode.upper()} region, L = 0, each legal XWR.",
    )
    chunk.code.extend(
        lxwr_walk_body(
            test_data,
            cases,
            amode,
            generator,
            f"cp_cfg_A_{amode}",
            first=1 if part is None else 3 * (part - 1) + 1,
            lower_mode=mode.letter,
        )
    )
    chunk.raw_data.extend(REGION_BLOBS[amode])
    return test_data.end_test_chunk()


def make_lower_mode_base(test_data: TestData, mode: Mode) -> list[TestChunk]:
    """Build lower-mode PMP tests without an address-mode constraint."""
    chunks = [_make_cfg_a_off_chunk(test_data, mode)]
    chunks.extend(_make_cfg_xwr_chunk(test_data, mode, locked=locked) for locked in (True, False))
    chunks.append(_make_csr_access_chunk(test_data, mode))
    chunks.extend(_make_mprv_chunk(test_data, mode, part) for part in (1, 2))
    return chunks


def make_lower_mode_amode(test_data: TestData, mode: Mode, amode: str) -> list[TestChunk]:
    """Build lower-mode PMP tests for one PMP address mode."""
    if amode == "na4":
        return [_make_legal_chunk(test_data, mode, amode)]
    return [_make_legal_chunk(test_data, mode, amode, part) for part in (1, 2)]
