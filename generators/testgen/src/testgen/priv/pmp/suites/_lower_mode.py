##################################
# priv/pmp/suites/_lower_mode.py
#
# PMPS and PMPU: PMP configured in M mode and probed from S or U mode.
# SPDX-License-Identifier: Apache-2.0
##################################

"""The PMPS and PMPU suites, which differ only in the mode the probes run from."""

from __future__ import annotations

from dataclasses import dataclass

from testgen.priv.pmp.macros import (
    EXIT,
    LOCKED_LXWR_CASES,
    NAPOT_MASK_DEFINES,
    REGION_BLOBS,
    UNLOCKED_LXWR_CASES,
    VERIFICATION_SECTION,
    amode_params,
    banner,
    cfg_byte,
    cfg_shift,
    probes,
    run_case,
    set_pmpaddr,
    set_pmpcfg,
    sigupd_count,
    walk_file,
    zero_pmp_regs,
)
from testgen.priv.pmp.macros import (
    sig_strs as macros_sig_strs,
)
from testgen.priv.pmp.model import XLENS, PmpFile, Xlen


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


MODES = {"S": Mode("S", "(1 << 11)"), "U": Mode("U", "0")}

#: TOR regions need two pmpaddr CSRs, so the six cases use every other entry, on the
#: entries the cfg_A_tor coverpoint expects.
_TOR_ENTRIES = ((11, 9, 7), (5, 3, 1))

_LEGAL_MACROS = {"na4": "RWX_NA4", "napot": "RWX_NAPOT", "tor": "RWX_LEGAL"}


def _file(
    mode: Mode,
    xlen: Xlen,
    name: str,
    macro: str,
    cases: int,
    body: list[str],
    *,
    banner: str,
    params: tuple[str, ...] | None = None,
    sig_strs: tuple[tuple[str, str], ...] | None = None,
    data: tuple[str, ...] = (),
) -> PmpFile:
    return PmpFile(
        filename=f"{mode.prefix}_{name}.S",
        xlen=xlen,
        banner=banner,
        required_extensions=(mode.letter,),
        params=params or amode_params(None),
        sigupd=sigupd_count(cases * len(probes(macro, xlen))),
        body=tuple(body),
        sig_strs=sig_strs or macros_sig_strs(macro, xlen, f"{mode.prefix}_{name.split('-')[0]}"),
        data=data,
    )


def _cfg_a_off(mode: Mode, xlen: Xlen) -> PmpFile:
    body = [
        *zero_pmp_regs(xlen),
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        VERIFICATION_SECTION,
        "",
        "// Test Case: 1 : L -> 0, A = OFF and No Permissions given to PMP entry 0, pmpaddr0 = all ones",
        "    LI(x5, -1)",
        "    csrw pmpaddr0, x5",
        "    csrw pmpcfg0, x0",
        *run_case("RWX", 1, lower_mode=mode.letter),
        *EXIT,
    ]
    return _file(
        mode,
        xlen,
        "cfg_A_off",
        "RWX",
        1,
        body,
        banner=banner(
            f"cp_cfg_A_off for {mode.suite} is fully covered in this test file.",
            f"{{jalr, sw, lw}} from {mode.letter} mode at a region whose entry has A = OFF, XWR = 000 and pmpaddr = all ones; all succeed.",
        ),
        data=tuple(REGION_BLOBS["off"]),
    )


def _cfg_xwr(mode: Mode, xlen: Xlen, *, locked: bool) -> PmpFile:
    name = "cfg_XWR" if locked else "cfg_XWR_unlocked"
    return walk_file(
        xlen,
        f"{mode.prefix}_{name}.S",
        "RWX_ALL",
        LOCKED_LXWR_CASES if locked else UNLOCKED_LXWR_CASES,
        "napot",
        banner=banner(
            f"cp_cfg_X and cp_cfg_RW from {mode.suite} are partially covered in this test file.",
            f"Every load and store width plus a jalr from {mode.letter} mode at the start of a NAPOT region, "
            f"L = {int(locked)}, each legal XWR.",
        ),
        prefix=f"{mode.prefix}_{name}",
        required_extensions=(mode.letter,),
        lower_mode=mode.letter,
        data=REGION_BLOBS["off"],
    )


def _csr_walk(symbol: str, first: str, count: int, index: int, mode: Mode) -> list[str]:
    """Write all ones to every CSR of one bank from the lower mode, checking each trap."""
    return [
        f"    .set {symbol}, {first}",
        f"    .rept {count}",
        f"    RVTEST_GOTO_LOWER_MODE    {mode.letter}mode",
        "    99:",
        f"    RVTEST_SIGUPD_CSR_WRITE({symbol}, x4, 99b, test_{index}_str)",
        "    nop",
        "    RVTEST_GOTO_MMODE",
        f"    .set {symbol}, {symbol}+1",
        "    .endr",
    ]


def _csr_access(mode: Mode, xlen: Xlen) -> PmpFile:
    low = mode.letter.lower()
    body = [
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        VERIFICATION_SECTION,
        "",
        f"// Test Case: 1 : write all ones to every pmpaddr CSR from {mode.letter} mode",
        "    LI(x4, -1)",
        *_csr_walk("pmpaddri", "CSR_PMPADDR0", 64, 1, mode),
        "",
        f"// Test Case: 2 : write all ones to every pmpcfg CSR from {mode.letter} mode",
        *_csr_walk("pmpcfgi", "CSR_PMPCFG0", 16, 2, mode),
        *EXIT,
    ]
    return PmpFile(
        filename=f"{mode.prefix}_csr_access.S",
        xlen=xlen,
        banner=banner(
            f"cp_pmpaddr_access_{low} and cp_pmpcfg_access_{low} are fully covered in this test file.",
            f"Write every pmpaddr and pmpcfg CSR from {mode.letter} mode; each traps with an illegal instruction.",
        ),
        required_extensions=(mode.letter,),
        params=amode_params(None),
        sigupd=sigupd_count(64 + 16),
        body=tuple(body),
        sig_strs=(
            ("test_1", f"test: 1; cp: cp_pmpaddr_access_{low}"),
            ("test_2", f"test: 2; cp: cp_pmpcfg_access_{low}"),
        ),
    )


def _mprv(mode: Mode, xlen: Xlen, part: int) -> PmpFile:
    xwr = "000" if part == 1 else "111"
    body = [
        *zero_pmp_regs(xlen),
        "",
        f"#define PMPREGION_LXWR_0{xwr} {cfg_byte(f'0{xwr}', 'napot', cfg_shift(xlen, 0))}",
        f"#define PMPREGION_LXWR_1{xwr} {cfg_byte(f'1{xwr}', 'napot', cfg_shift(xlen, 0))}",
        "#define MPRV       (1 << 17)",
        "#define MPP        (3 << 11)",
        f"#define MPP_LOWER  {mode.mpp}",
        "#define REGIONSTART TEST_FOR_EXECUTION",
        *NAPOT_MASK_DEFINES,
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        VERIFICATION_SECTION,
    ]
    n = 0
    for lock in (0, 1):
        body.extend(["", *set_pmpaddr("napot", 0), *set_pmpcfg(xlen, 0, f"PMPREGION_LXWR_{lock}{xwr}")])
        body.append("    RVTEST_SFENCE_VMA_IF_SUPPORTED")
        for mprv in (0, 1):
            n += 1
            bits = "MPP_LOWER|MPRV" if mprv else "MPP_LOWER"
            body.extend(
                [
                    "",
                    f"// Test Case: {n} : mstatus.MPRV = {mprv}, mstatus.MPP = {mode.letter} mode, L = {lock}, XWR = {xwr}",
                    f"    PMP_VERIFICATION_RWX_MPRV    TEST_FOR_EXECUTION, test_{n}, {bits}",
                ]
            )
    body.extend(EXIT)
    return _file(
        mode,
        xlen,
        f"mprv_check-0{part}",
        "RWX",
        4,
        body,
        banner=banner(
            f"cp_mprv for {mode.suite} is partially covered in this file.",
            f"{{jalr, sw, lw}} from M mode with mstatus.MPRV = {{0, 1}} and MPP = {mode.letter}, region L = {{0, 1}}, XWR = {xwr}.",
        ),
        data=tuple(REGION_BLOBS["napot_pad"]),
    )


def _legal(mode: Mode, xlen: Xlen, amode: str, part: int | None = None) -> PmpFile:
    """The six unlocked XWR encodings against one NA4, NAPOT or TOR region, from the lower mode."""
    cases = UNLOCKED_LXWR_CASES if part is None else UNLOCKED_LXWR_CASES[3 * (part - 1) : 3 * part]
    if amode == "tor":
        cases = [(lxwr, entry) for (lxwr, _), entry in zip(cases, _TOR_ENTRIES[part - 1 if part else 0], strict=True)]
    name = f"{amode}_legal_lxwr" + ("" if part is None else f"-0{part}")
    return walk_file(
        xlen,
        f"{mode.prefix}_{name}.S",
        _LEGAL_MACROS[amode],
        cases,
        amode,
        banner=banner(
            f"cp_cfg_A_{amode} for {mode.suite} is {'fully' if part is None else 'partially'} covered in this test file.",
            f"{{jalr, sw, lw}} from {mode.letter} mode at and around a {amode.upper()} region, L = 0, each legal XWR.",
        ),
        prefix=f"{mode.prefix}_{amode}_legal_lxwr",
        required_extensions=(mode.letter,),
        params=amode_params(amode),
        first=1 if part is None else 3 * (part - 1) + 1,
        lower_mode=mode.letter,
    )


def build_lower_mode_suite(mode: Mode) -> list[PmpFile]:
    """Every file of the PMPS or PMPU suite, for both XLENs."""
    files: list[PmpFile] = []
    for xlen in XLENS.values():
        files.append(_cfg_a_off(mode, xlen))
        files.extend(_cfg_xwr(mode, xlen, locked=locked) for locked in (True, False))
        files.append(_csr_access(mode, xlen))
        files.extend(_mprv(mode, xlen, part) for part in (1, 2))
        files.append(_legal(mode, xlen, "na4"))
        files.extend(_legal(mode, xlen, amode, part) for amode in ("napot", "tor") for part in (1, 2))
    return files
