##################################
# priv/pmp/suites/PMPSm.py
#
# PMPSm: machine-mode PMP configuration and enforcement.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMPSm suite: pmpcfg/pmpaddr WARL behaviour and M-mode PMP enforcement."""

from __future__ import annotations

from testgen.priv.pmp import add_pmp_suite
from testgen.priv.pmp.macros import (
    EXIT,
    GRANULE_WORDS,
    LOCKED_LXWR_CASES,
    NAPOT_MASK_DEFINES,
    NUM_PMP_ENTRIES_PARAM,
    QUALCOMM,
    REGION_BLOBS,
    RETURN_TRAMPOLINE,
    VERIFICATION_SECTION,
    amode_params,
    banner,
    cfg_byte,
    cfg_csr,
    cfg_shift,
    csr_write,
    entry_walk,
    lxwr_walk_body,
    probes,
    run_case,
    set_pmpaddr,
    set_pmpcfg,
    sig_strs,
    sigupd_count,
    zero_pmp_regs,
)
from testgen.priv.pmp.model import XLENS, PmpFile, Xlen

_CARLIN = ("Umer Shahid, Allen Baum, David Harris", "Muhammad Abdullah, Hamza Ali, Muhammad Zain", "Jordan Carlin")


#####################################################################
# pmpcfg_walk: WARL readback of every pmpcfg CSR bit
#####################################################################

_MAX_PMP_ENTRIES = 64

#: Within each configuration byte, bit 1 (W without R) is reserved and bit 4 selects NA4.
_SKIPPED_BITS = {1, 4}


def _walk_banner(test_cases: str) -> str:
    return banner(
        "cp_pmpcfg_walk for PMPSm is partially covered in this test file.",
        test_cases,
        title="PMP configuration CSR walk verification",
        description="This test verifies WARL-safe writes to PMP configuration CSRs.",
        authors=_CARLIN,
    )


def _csr_walk(xlen: Xlen, value: str, label: str) -> list[str]:
    """Write ``value`` to every implemented pmpcfg CSR and check the readback."""
    return [
        "    .set pmpcfgi, CSR_PMPCFG0",
        f"    .rept {xlen.cfg_rept}",
        f"1:  LI(t2, {value})",
        f"    RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, {label}_str)",
        f"    .set pmpcfgi, pmpcfgi+{xlen.cfg_step}",
        "    .endr",
    ]


def _walk_spec(xlen: Xlen, number: int, test_cases: str, body: list[str], sig_strs: list[tuple[str, str]]) -> PmpFile:
    reps = _MAX_PMP_ENTRIES // xlen.cfgs_per_reg
    return PmpFile(
        filename=f"pmpsm_pmpcfg_walk-{number:02d}.S",
        xlen=xlen,
        copyright=QUALCOMM,
        banner=_walk_banner(test_cases),
        required_extensions=("Sm",),
        params=(NUM_PMP_ENTRIES_PARAM,),
        sigupd=sigupd_count(len(sig_strs) * reps),
        body=tuple(body),
        sig_strs=tuple(sig_strs),
    )


def _zero_file(xlen: Xlen) -> PmpFile:
    body = ["// Test Case: 1 : write zero to every pmpcfg CSR", *_csr_walk(xlen, "0", "test_1")]
    return _walk_spec(
        xlen,
        1,
        "Write zero to every pmpcfg CSR and check the readback.",
        body,
        [("test_1", "test: 1; cp: cp_pmpcfg_walk_zero")],
    )


def _walk_file(xlen: Xlen, number: int, byte: int) -> PmpFile:
    """Walk a one through the legal bits of configuration byte ``byte`` of every pmpcfg CSR."""
    body: list[str] = []
    sig_strs: list[tuple[str, str]] = []
    for bit in range(8 * byte, 8 * byte + 8):
        if bit % 8 in _SKIPPED_BITS:
            continue
        n = len(sig_strs) + 1
        body.extend(
            [
                "",
                f"// Test Case: {n} : write 1 << {bit} to every pmpcfg CSR",
                *_csr_walk(xlen, f"1 << {bit}", f"test_{n}"),
            ]
        )
        sig_strs.append((f"test_{n}", f"test: {n}; cp: cp_pmpcfg_walk_bit{bit}"))
    return _walk_spec(
        xlen,
        number,
        f"Write a walking one through bits {8 * byte}..{8 * byte + 7} of every pmpcfg CSR and check\n"
        "the readback, skipping the reserved R=0/W=1 encoding and the A=NA4 bit.",
        body[1:],
        sig_strs,
    )


def build_walk_files() -> list[PmpFile]:
    """Every ``pmpsm_pmpcfg_walk-*`` file of the PMPSm suite, for both XLENs."""
    specs: list[PmpFile] = []
    for xlen in XLENS.values():
        specs.append(_zero_file(xlen))
        specs.extend(_walk_file(xlen, byte + 2, byte) for byte in range(xlen.bits // 8))
    return specs


#####################################################################
# cfg_*: pmpcfg A/L/XWR enforcement
#####################################################################

#: The 15 PMP entries below the background entry of a 16-entry PMP, lowest priority first.
_ENTRIES = tuple(range(14, -1, -1))


def _cfg_file(
    xlen: Xlen,
    name: str,
    coverpoint: str,
    test_cases: str,
    body: list[str],
    *,
    sigupd: int,
    sig_strs: tuple[tuple[str, str], ...] = (),
    params: tuple[str, ...] | None = None,
    data: tuple[str, ...] = (),
    extra_defines: tuple[str, ...] = (),
    holders: tuple[str, ...] = (),
    banner_text: str | None = None,
) -> PmpFile:
    return PmpFile(
        filename=f"pmpsm_cfg_{name}.S",
        xlen=xlen,
        banner=banner_text or banner(f"{coverpoint} for PMPSm is fully covered in this test file.", test_cases),
        required_extensions=("Sm",),
        params=params or amode_params(None),
        sigupd=sigupd,
        body=tuple(body),
        sig_strs=sig_strs,
        data=data,
        extra_defines=extra_defines,
        copyright=holders,
    )


# ---------------------------------------------------------------------------
# cfg_A_all: pmpcfg.A is writable in every region
# ---------------------------------------------------------------------------

_A_MODES = (("NA4", "PMP_NA4"), ("NAPOT", "PMP_NAPOT"), ("TOR", "PMP_TOR"), ("OFF", None))


def _a_all_file(xlen: Xlen) -> PmpFile:
    csrs = [i * xlen.cfg_step for i in range(16 // xlen.cfg_step)]
    present = 16 // xlen.cfgs_per_reg  # pmpcfg CSRs of a 16-entry PMP
    body = [*zero_pmp_regs(xlen), "", "    RVTEST_PMP_SET_BACKGROUND x4", "", VERIFICATION_SECTION]
    n = 0
    for index, (name, const) in enumerate(_A_MODES, start=1):
        body.extend(["", f"// Test Case: {index} : write A = {name} to every byte of every pmpcfg CSR"])
        if const:
            bytes_ = "|".join(f"(({const}&0xFF) << PMP{i}_CFG_SHIFT)" for i in range(xlen.cfgs_per_reg))
            body.append(f"    LI(x4, {bytes_})")
        for i, csr in enumerate(csrs):
            if i == present:
                body.append(".if UDB_NUM_PMP_ENTRIES == 64")
            n += 1
            body.extend(csr_write(f"pmpcfg{csr}", "x4" if const else "x0", n, f"test_{index}"))
        body.append(".endif")
    return _cfg_file(
        xlen,
        "A_all",
        "cp_cfg_A_all",
        "Write A = NA4, NAPOT, TOR and OFF into every byte of every pmpcfg CSR and read it back.",
        body,
        sigupd=sigupd_count(n),
        sig_strs=tuple((f"test_{i}", f"test: {i}; cp: cp_cfg_A_all_{name}") for i, (name, _) in enumerate(_A_MODES, 1)),
    )


# ---------------------------------------------------------------------------
# cfg_A_off_all: A=OFF never matches
# ---------------------------------------------------------------------------


def _a_off_all_file(xlen: Xlen) -> PmpFile:
    body = [
        *zero_pmp_regs(xlen),
        "",
        "#define REGIONSTART TEST_FOR_EXECUTION",
        *NAPOT_MASK_DEFINES,
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        VERIFICATION_SECTION,
        *entry_walk(
            xlen, _ENTRIES, "napot", lambda e: f"({cfg_byte('1000', 'off', '0')} << {cfg_shift(xlen, e)})", "RWX"
        ),
        *EXIT,
    ]
    return _cfg_file(
        xlen,
        "A_off_all",
        "cp_cfg_A_off_all",
        "{jalr, sw, lw} at a region whose entry has L = 1, A = OFF, XWR = 000, for every entry; all succeed.",
        body,
        sigupd=sigupd_count(len(_ENTRIES) * 3),
        sig_strs=sig_strs("RWX", xlen, "pmpsm_cfg_A_off_all"),
        data=tuple(REGION_BLOBS["napot_pad"]),
    )


# ---------------------------------------------------------------------------
# cfg_A_tor_bot: region 1 extends from pmpaddr0 to pmpaddr1
# ---------------------------------------------------------------------------


def _a_tor_bot_file(xlen: Xlen) -> PmpFile:
    body = [
        *zero_pmp_regs(xlen),
        "",
        f"#define PMPREGION_UPPER_BOUND {cfg_byte('1101', 'tor', 'PMP1_CFG_SHIFT')}",
        f"#define PMPREGION_LOWER_BOUND {cfg_byte('1000', 'off', 'PMP0_CFG_SHIFT')}",
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        *set_pmpaddr("tor", 1, "TEST_FOR_EXECUTION"),
        "",
        VERIFICATION_SECTION,
        "",
        "// Test Case: 1 : pmpcfg1 = L, TOR, XR; pmpcfg0 = OFF, unlocked",
        *set_pmpcfg(xlen, 0, "PMPREGION_UPPER_BOUND"),
        *run_case("RWX_TOR_BOT", 1),
        "",
        "// Test Case: 2 : pmpcfg1 = L, TOR, XR; pmpcfg0 = OFF, locked",
        *set_pmpcfg(xlen, 0, "PMPREGION_UPPER_BOUND|PMPREGION_LOWER_BOUND"),
        *run_case("RWX_TOR_BOT", 2),
        *EXIT,
    ]
    return _cfg_file(
        xlen,
        "A_tor_bot",
        "cp_cfg_A_tor_bot",
        "{sw, lw, jalr} at pmpaddr0-4, pmpaddr0, pmpaddr1-4 and pmpaddr1 with entry 1 = L, TOR, XR and entry 0 = OFF, unlocked then locked.",
        body,
        params=amode_params("tor"),
        sigupd=sigupd_count(2 * len(probes("RWX_TOR_BOT", xlen))),
        sig_strs=sig_strs("RWX_TOR_BOT", xlen, "pmpsm_cfg_A_tor_bot"),
        data=tuple(REGION_BLOBS["tor"]),
    )


# ---------------------------------------------------------------------------
# cfg_A_tor_zero: region 0 extends from address 0 to pmpaddr0
# ---------------------------------------------------------------------------


def _a_tor_zero_file(xlen: Xlen) -> PmpFile:
    body = [
        *zero_pmp_regs(xlen),
        "",
        f"#define PMPREGION_TOR {cfg_byte('1111', 'tor', 'PMP0_CFG_SHIFT')}",
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        "    LA(x5, TEST_FOR_EXECUTION)",
        "    srl x5, x5, PMP_SHIFT",
        "    csrw pmpaddr0, x5",
        "",
        VERIFICATION_SECTION,
        "",
        "// Test Case: 1 : pmpcfg0 = L, TOR, XWR: region 0 spans [0, TEST_FOR_EXECUTION)",
        *set_pmpcfg(xlen, 0, "PMPREGION_TOR"),
        *run_case("RWX_TOR_ZERO", 1),
        *EXIT,
    ]
    return _cfg_file(
        xlen,
        "A_tor_zero",
        "cp_cfg_A_tor0",
        "{sw, lw, jalr} at pmpaddr0, pmpaddr0-4 and 0 with entry 0 = L, TOR, XWR.",
        body,
        params=amode_params("tor"),
        extra_defines=("#define SKIP_MTVAL",),
        sigupd=sigupd_count(len(probes("RWX_TOR_ZERO", xlen))),
        sig_strs=sig_strs("RWX_TOR_ZERO", xlen, "pmpsm_cfg_A_tor_zero"),
        data=tuple(REGION_BLOBS["off"]),
    )


# ---------------------------------------------------------------------------
# cfg_L_access_all: L=0 never restricts M-mode
# ---------------------------------------------------------------------------


def _l_access_all_file(xlen: Xlen) -> PmpFile:
    body = [
        *zero_pmp_regs(xlen),
        "",
        "#define REGIONSTART TEST_FOR_EXECUTION",
        *NAPOT_MASK_DEFINES,
        "",
        VERIFICATION_SECTION,
        "",
        "// Test Case: 0 : M-mode access succeeds when every PMP entry is off",
        *run_case("RWX", 0),
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        *entry_walk(
            xlen, _ENTRIES, "napot", lambda e: f"({cfg_byte('0000', 'napot', '0')} << {cfg_shift(xlen, e)})", "RWX"
        ),
        *EXIT,
    ]
    return _cfg_file(
        xlen,
        "L_access_all",
        "cp_cfg_L_access_all and cp_none",
        "{jalr, sw, lw} with every PMP entry off, then at a region whose entry has L = 0, A = NAPOT, XWR = 000, for every entry; all succeed.",
        body,
        sigupd=sigupd_count((len(_ENTRIES) + 1) * 3),
        sig_strs=sig_strs("RWX", xlen, "pmpsm_cfg_L_access_all"),
        data=tuple(REGION_BLOBS["napot_pad"]),
    )


# ---------------------------------------------------------------------------
# cfg_L_modify_{off,tor,napot}: locked entries reject writes
# ---------------------------------------------------------------------------

#: (name, setup lines with {cfg} = the entry-1 configuration, CSR, source register)
_L_MODIFY_STEPS = (
    ("write_pmpaddr1", "    addi x4, x0, 0x100", "pmpaddr1", "x4"),
    ("write_pmpcfg0", "    LI(x4, {cfg})", "pmpcfg0", "x4"),
    ("modify_pmpcfg0", "    addi x5, x4, 7", "pmpcfg0", "x5"),
    ("modify_pmpaddr0", "    addi x4, x0, -1", "pmpaddr0", "x4"),
    ("clear_pmpaddr1", "", "pmpaddr1", "x0"),
    ("clear_pmpcfg0", "", "pmpcfg0", "x0"),
)
_L_MODIFY_RESET = (("reset_pmpaddr0", "", "pmpaddr0", "x0"), ("reset_pmpcfg0", "", "pmpcfg0", "x0"))


def _l_modify_file(xlen: Xlen, amode: str) -> PmpFile:
    body = [*zero_pmp_regs(xlen), "", "    RVTEST_PMP_SET_BACKGROUND x4", "", VERIFICATION_SECTION]
    names: list[str] = []
    for lock in (0, 1):
        body.extend(
            ["", f"// Test Case {lock + 1} : entry 1 = {amode.upper()}, L = {lock}, XWR = {lock}111, pmpaddr1 = 0x100"]
        )
        steps = [*_L_MODIFY_STEPS, *(_L_MODIFY_RESET if lock == 0 else [])]
        for step, setup, csr, src in steps:
            names.append(f"L{lock}_{step}")
            body.extend(setup.format(cfg=cfg_byte(f"{lock}111", amode, "PMP1_CFG_SHIFT")).splitlines())
            body.extend(csr_write(csr, src, len(names), f"test_{len(names)}"))
    return _cfg_file(
        xlen,
        f"L_modify_{amode}",
        "cp_cfg_L_modify",
        f"Write and read back pmpaddr1/pmpcfg0 with entry 1 = {amode.upper()}, L = {{0, 1}}: locked entries and, for TOR, "
        "the preceding pmpaddr reject writes.",
        body,
        params=amode_params(None if amode == "off" else amode),
        sigupd=sigupd_count(len(names)),
        sig_strs=tuple((f"test_{n}", f"test: {n}; cp: cp_cfg_L_modify_{name}") for n, name in enumerate(names, 1)),
    )


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


def _xwr_all_file(xlen: Xlen, part: int) -> PmpFile:
    codes = _XWR_ROLL[part - 1].split()
    body = [
        *zero_pmp_regs(xlen),
        "",
        *(f"#define PMPREGION_XWR_{xwr} {cfg_byte(f'1{xwr}', 'napot', '0')}" for xwr in sorted(set(codes))),
        "#define REGIONSTART TEST_FOR_EXECUTION",
        *NAPOT_MASK_DEFINES,
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        "    // Every entry covers the region; only its permissions vary below.",
        *set_pmpaddr("napot", 0)[:-1],
        "    .set pmpaddri, CSR_PMPADDR0",
        "    .rept UDB_NUM_PMP_ENTRIES",
        "    csrw pmpaddri, x5",
        "    .set pmpaddri, pmpaddri+1",
        "    .endr",
        "",
        VERIFICATION_SECTION,
    ]
    first = 15 * (part - 1) + 1
    for n, (entry, xwr) in enumerate(zip(_ENTRIES, codes, strict=True), start=first):
        body.extend(["", f"// Test Case: {n} : L -> 1 and XWR -> {xwr} on PMP entry {entry}"])
        body.extend(set_pmpcfg(xlen, entry, f"(PMPREGION_XWR_{xwr} << {cfg_shift(xlen, entry)})"))
        body.extend(run_case("RWX_ALL", n))
    body.extend(EXIT)
    return _cfg_file(
        xlen,
        f"XWR_all-{part:02d}",
        "cp_cfg_X0_all, cp_cfg_X1_all, cp_cfg_RW00_all, cp_cfg_RW10_all and cp_cfg_RW11_all",
        "Every load and store width plus a jalr at a locked NAPOT region, rolling the six legal XWR over entries 14..0.",
        body,
        sigupd=sigupd_count(len(codes) * len(probes("RWX_ALL", xlen))),
        sig_strs=sig_strs("RWX_ALL", xlen, "pmpsm_cfg_XWR_all"),
        data=tuple(REGION_BLOBS["napot_pad"]),
    )


# ---------------------------------------------------------------------------
# cfg_na4_all / cfg_napot_all: A=NA4 / A=NAPOT works in every region
# ---------------------------------------------------------------------------


def _amode_all_file(xlen: Xlen, amode: str) -> PmpFile:
    beyond = "4" if amode == "na4" else "PMP_NAPOT_REGION_BYTES"
    body = [
        *zero_pmp_regs(xlen),
        "",
        "#define REGIONSTART TEST_FOR_EXECUTION",
        *(NAPOT_MASK_DEFINES if amode == "napot" else []),
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        VERIFICATION_SECTION,
    ]
    body.extend(
        entry_walk(
            xlen,
            _ENTRIES,
            amode,
            lambda e: cfg_byte("1000", amode, cfg_shift(xlen, e)),
            "LW_BOUNDS",
            extra=f", {beyond}",
        )
    )
    body.extend(EXIT)
    return _cfg_file(
        xlen,
        f"{amode}_all",
        f"cp_cfg_A_{amode}_all",
        f"lw at, 4 below and just beyond a locked no-permission {amode.upper()} region, for every entry.",
        body,
        params=amode_params(amode),
        sigupd=sigupd_count(len(_ENTRIES) * 3),
        sig_strs=sig_strs("LW_BOUNDS", xlen, f"pmpsm_cfg_{amode}_all"),
        data=tuple(REGION_BLOBS["off" if amode == "na4" else "napot_pad"]),
    )


# ---------------------------------------------------------------------------
# cfg_tor_all: A=TOR works in every region
# ---------------------------------------------------------------------------


def _tor_all_file(xlen: Xlen) -> PmpFile:
    per = xlen.cfgs_per_reg
    body = [
        *zero_pmp_regs(xlen),
        "",
        f"#define DEFAULT_TOR_REGION {cfg_byte('1111', 'tor', 'PMP0_CFG_SHIFT')}",
        *(
            f"#define PMPREGION{i}_XWR_{'001' if i % 2 else '000'} {cfg_byte('1001' if i % 2 else '1000', 'tor', f'PMP{i}_CFG_SHIFT')}"
            for i in range(per)
        ),
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        "    // pmpaddr_i = TEST_FOR_EXECUTION_i, so TOR region i+1 is [TEST_FOR_EXECUTION_i, TEST_FOR_EXECUTION_i+1)",
    ]
    for entry in range(15):
        body.extend(
            [f"    LA(x5, TEST_FOR_EXECUTION_{entry})", "    srl x5, x5, PMP_SHIFT", f"    csrw pmpaddr{entry}, x5"]
        )
    body.extend(
        [
            "",
            VERIFICATION_SECTION,
            "",
            "// Test Case: 1 : every region L -> 1, A -> TOR, XWR -> 00(i%2); lw at the start of each region",
        ]
    )
    for csr_index in range(16 // per):
        top = min(per, 15 - csr_index * per)
        slots = [f"PMPREGION{i}_XWR_{'001' if i % 2 else '000'}" for i in range(top - 1, 0, -1)]
        slots.append("DEFAULT_TOR_REGION" if csr_index == 0 else "PMPREGION0_XWR_000")
        body.extend([f"    LI(x4, ({'|'.join(slots)}))", f"    csrw pmpcfg{csr_index * xlen.cfg_step}, x4"])
    body.append("    RVTEST_SFENCE_VMA_IF_SUPPORTED")
    for n in range(1, 16):
        body.append(f"    PMP_VERIFICATION_LW    TEST_FOR_EXECUTION_{n - 1}, test_{n}")
    body.extend(EXIT)
    data = [
        ".p2align 12",
        ".p2align (UDB_PMP_GRANULARITY)",
        "TEST_FOR_EXECUTION_X:",
        f"    .rept {GRANULE_WORDS}",
        "    jr ra",
        "    .endr",
    ]
    for i in range(15):
        data.extend(
            [f"TEST_FOR_EXECUTION_{i}:", f"    .rept ({i + 1} * (PMP_TOR_REGION_BYTES / 4))", "    nop", "    .endr"]
        )
    data.extend(RETURN_TRAMPOLINE)
    return _cfg_file(
        xlen,
        "tor_all",
        "cp_cfg_A_tor_all",
        "Fifteen locked TOR regions of increasing size with XWR = 00(i%2); lw at the start of each.",
        body,
        params=amode_params("tor"),
        sigupd=sigupd_count(15),
        sig_strs=sig_strs("LW", xlen, "pmpsm_cfg_tor_all"),
        data=tuple(data),
    )


# ---------------------------------------------------------------------------
# cfg_tor_check: a TOR region with pmpaddr0 >= pmpaddr1 never matches
# ---------------------------------------------------------------------------

_TOR_CHECK_CASES = (
    ("pmpaddr0 = pmpaddr1", ["    csrw pmpaddr0, x5"]),
    (
        "pmpaddr0 = pmpaddr1 + g",
        ["    LI(x6, PMP_TOR_REGION_BYTES >> PMP_SHIFT)", "    add x6, x5, x6", "    csrw pmpaddr0, x6"],
    ),
    ("pmpaddr0 = all ones", ["    LI(x6, -1)", "    csrw pmpaddr0, x6"]),
)


def _tor_check_file(xlen: Xlen, part: int) -> PmpFile:
    case, addr0 = _TOR_CHECK_CASES[part - 1]
    body = [
        *zero_pmp_regs(xlen),
        "",
        f"#define PMPREGION_UPPER_BOUND {cfg_byte('1000', 'tor', 'PMP1_CFG_SHIFT')}",
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        "    LA(x5, TEST_FOR_EXECUTION)",
        "    srl x5, x5, PMP_SHIFT",
        "    csrw pmpaddr1, x5",
        *addr0,
        "",
        VERIFICATION_SECTION,
        "",
        f"// Test Case: 1 : pmpcfg1 = L, TOR, no permissions; {case}",
        *set_pmpcfg(xlen, 0, "PMPREGION_UPPER_BOUND"),
        *run_case("RWX_NA4", 1),
        *EXIT,
    ]
    return _cfg_file(
        xlen,
        f"tor_check-{part:02d}",
        f"cp_cfg_A_tor_non-overlap test case {part}",
        f"{{jalr, sw, lw}} around a locked TOR entry 1 with no permissions while {case}; no match, so all succeed.",
        body,
        params=amode_params("tor"),
        sigupd=sigupd_count(len(probes("RWX_NA4", xlen))),
        sig_strs=sig_strs("RWX_NA4", xlen, f"pmpsm_cfg_tor_check{part}"),
        data=tuple(REGION_BLOBS["off"]),
    )


def build_cfg_files() -> list[PmpFile]:
    """Every ``pmpsm_cfg_*`` file of the PMPSm suite, for both XLENs."""
    files: list[PmpFile] = []
    for xlen in XLENS.values():
        files.append(_a_all_file(xlen))
        files.append(_a_off_all_file(xlen))
        files.append(_a_tor_bot_file(xlen))
        files.append(_a_tor_zero_file(xlen))
        files.append(_l_access_all_file(xlen))
        files.extend(_l_modify_file(xlen, amode) for amode in ("off", "tor", "napot"))
        files.extend(_xwr_all_file(xlen, part) for part in range(1, 5))
        files.extend(_amode_all_file(xlen, amode) for amode in ("na4", "napot"))
        files.append(_tor_all_file(xlen))
        files.extend(_tor_check_file(xlen, part) for part in (1, 2, 3))
    return files


def _misc_file(
    xlen: Xlen,
    name: str,
    coverpoint: str,
    test_cases: str,
    body: list[str],
    *,
    sigupd: int,
    sig_strs: tuple[tuple[str, str], ...] = (),
    params: tuple[str, ...] | None = None,
    data: tuple[str, ...] = (),
    extra_defines: tuple[str, ...] = (),
    holders: tuple[str, ...] = (),
    banner_text: str | None = None,
) -> PmpFile:
    return PmpFile(
        filename=f"pmpsm_{name}.S",
        xlen=xlen,
        banner=banner_text or banner(f"{coverpoint} for PMPSm is fully covered in this test file.", test_cases),
        required_extensions=("Sm",),
        params=params or amode_params(None),
        sigupd=sigupd,
        body=tuple(body),
        sig_strs=sig_strs,
        data=data,
        extra_defines=extra_defines,
        copyright=holders,
    )


#####################################################################
# pmpsm_grain / pmpsm_grain_check: pmpaddr readback versus the grain
#####################################################################

_GRAIN_PATTERNS = (("zeros", "0"), ("ones", "-1"), ("checkerboard", "CHECKERBOARD"))
_GRAIN_MODES = ("OFF", "NAPOT", "TOR")


def _grain_file(xlen: Xlen) -> PmpFile:
    body = [
        *zero_pmp_regs(xlen),
        "",
        *(f"#define PMPREGION_{mode} {cfg_byte('0111', mode.lower(), 'PMP0_CFG_SHIFT')}" for mode in _GRAIN_MODES),
        "#define PMP_GRAIN_MASK ((1 << (UDB_PMP_GRANULARITY - 2)) - 1)",
        f"#define CHECKERBOARD 0x{'AA' * (xlen.bits // 8)}",
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        "    LI(t3, PMP_GRAIN_MASK)",
        "",
        VERIFICATION_SECTION,
    ]
    strs = []
    n = 0
    for pattern, value in _GRAIN_PATTERNS:
        for write_mode in ("NAPOT", "OFF"):
            for read_mode in _GRAIN_MODES:
                n += 1
                strs.append((f"test_{n}", f"test: {n}; cp: cp_grain_{pattern}_write_{write_mode}_read_{read_mode}"))
                block = [
                    "",
                    f"// Test Case: {n} : write {pattern} to pmpaddr0 with A = {write_mode}, read back with A = {read_mode}",
                    f"    LI(x6, PMPREGION_{write_mode})",
                    "    csrw pmpcfg0, x6",
                    f"    LI(x6, {value})",
                    "    csrw pmpaddr0, x6",
                    f"    LI(x6, PMPREGION_{read_mode})",
                    "    csrw pmpcfg0, x6",
                    f"    test_{n}:",
                    "        csrr x7, pmpaddr0",
                    "        and x7, x7, t3",
                    f"        RVTEST_SIGUPD(x2, x5, x4, x7, test_{n}, test_{n}_str)",
                ]
                if read_mode == "TOR":
                    block = ["#ifdef UDB_PMP_TOR_SUPPORTED", *block, "#endif"]
                body.extend(block)
    return _misc_file(
        xlen,
        "grain",
        "cp_grain",
        "Write zeros, ones and a checkerboard to pmpaddr0 with A = NAPOT and OFF; read back with A = OFF, NAPOT and TOR.",
        body,
        holders=QUALCOMM,
        banner_text=banner(
            "cp_grain for PMPSm is fully covered in this test file.",
            "See the test case comments.",
            title="PMP address grain readback verification",
            description="This test verifies PMP address grain readback behavior.",
            authors=_CARLIN,
        ),
        sigupd=sigupd_count(n),
        sig_strs=tuple(strs),
    )


def _grain_check_file(xlen: Xlen) -> PmpFile:
    body = [
        *zero_pmp_regs(xlen),
        "",
        "#define PMP_GRAIN_CHECK_MASK ((1 << (UDB_PMP_GRANULARITY - 1)) - 1)",
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        VERIFICATION_SECTION,
        "",
        "// Test Case: 1 : write 0 to pmpcfg0 and all ones to pmpaddr0, read back pmpaddr0",
        "    csrw pmpcfg0, x0",
        "    LI(x6, -1)",
        "    csrw pmpaddr0, x6",
        "    LI(t3, PMP_GRAIN_CHECK_MASK)",
        "    test_1:",
        "        csrr x7, pmpaddr0",
        "        and x7, x7, t3",
        "        RVTEST_SIGUPD(x2, x5, x4, x7, test_1, test_1_str)",
    ]
    return _misc_file(
        xlen,
        "grain_check",
        "cp_grain_check",
        "",
        body,
        holders=QUALCOMM,
        banner_text=banner(
            "cp_grain_check for PMPSm is fully covered in this test file.",
            "Write all ones to pmpaddr0 with pmpcfg0 = 0 and read it back; the lowest set bit gives the grain.",
            title="PMP address grain discovery verification",
            description="This test verifies PMP address grain discovery.",
            authors=_CARLIN,
        ),
        sigupd=sigupd_count(1),
        sig_strs=(("test_1", "test: 1; cp: cp_grain_check"),),
    )


#####################################################################
# pmpsm_pmpaddr_upper: the architecturally zero high pmpaddr bits
#####################################################################


def _pmpaddr_upper_file() -> PmpFile:
    body = [
        "",
        "// Test Case: 1 : write ones to every pmpaddr CSR and check bits 63:54 read back as zero",
        "    LI(t0, -1)",
        "    LI(t1, 0xFFC0000000000000)",
        "    .set pmpaddri, CSR_PMPADDR0",
        "    .rept UDB_NUM_PMP_ENTRIES",
        "1:  csrw pmpaddri, t0",
        "    csrr t2, pmpaddri",
        "    and t2, t2, t1",
        "    RVTEST_SIGUPD(x2, x5, x4, t2, 1b, test_1_str)",
        "    .set pmpaddri, pmpaddri+1",
        "    .endr",
    ]
    return _misc_file(
        XLENS[64],
        "pmpaddr_upper",
        "cp_pmpaddr_upper_zero",
        "",
        body,
        holders=QUALCOMM,
        banner_text=banner(
            "cp_pmpaddr_upper_zero for PMPSm is fully covered in this test file.",
            "Write ones to pmpaddr CSRs and check bits 63:54 read back as zero.",
            title="PMP address upper-bits verification",
            description="This test verifies the architecturally fixed upper bits of RV64 pmpaddr CSRs.",
            authors=_CARLIN,
        ),
        sigupd=sigupd_count(64),
        sig_strs=(("test_1", "test: 1; cp: cp_pmpaddr_upper_zero"),),
    )


#####################################################################
# pmpsm_{na4,napot,tor}_legal_lxwr: every legal locked LXWR against
# one region in each address mode
#####################################################################


_LEGAL_MACROS = {"na4": "RWX_NA4", "napot": "RWX_NAPOT", "tor": "RWX_LEGAL"}

_TOR_ENTRIES = ((11, 9, 7), (5, 3, 1))


def _legal_file(xlen: Xlen, amode: str, part: int | None = None) -> PmpFile:
    macro = _LEGAL_MACROS[amode]
    if part is None:
        cases, first, name = LOCKED_LXWR_CASES, 1, f"{amode}_legal_lxwr"
    else:
        cases = LOCKED_LXWR_CASES[3 * (part - 1) : 3 * part]
        if amode == "tor":
            cases = list(zip([lxwr for lxwr, _ in cases], _TOR_ENTRIES[part - 1], strict=True))
        first, name = 3 * (part - 1) + 1, f"{amode}_legal_lxwr-{part:02d}"
    return _misc_file(
        xlen,
        name,
        f"cp_cfg_A_{amode}",
        f"{{jalr, sw, lw}} in M mode at and around a locked {amode.upper()} region, each legal XWR.",
        lxwr_walk_body(xlen, cases, amode, macro, first=first),
        params=amode_params(amode),
        sigupd=sigupd_count(len(cases) * len(probes(macro, xlen))),
        sig_strs=sig_strs(macro, xlen, f"pmpsm_{amode}"),
        data=tuple(REGION_BLOBS[amode]),
    )


#####################################################################
# pmpsm_priority / pmpsm_priority_off: overlapping regions
#####################################################################

#: LXWR code of each of the seven nested NAPOT regions, smallest (highest priority) first.
_PRIORITY_CODES = ("1000", "1101", "1011", "1100", "1001", "1111", "1000")


def _priority_file(xlen: Xlen) -> PmpFile:
    body = [
        *zero_pmp_regs(xlen),
        "",
        *(
            f"#define PMPREGION{e}_LXWR_{lxwr} {cfg_byte(lxwr, 'napot', cfg_shift(xlen, e))}"
            for e, lxwr in enumerate(_PRIORITY_CODES)
        ),
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        "    // Seven overlapping NAPOT regions based at TEST_FOR_EXECUTION, of sizes",
        "    // PMP_NAPOT_REGION_BYTES times 1, 2, 4, ..., 64: pmpaddr_i = (base >> 2) | (2^i * bytes/8 - 1)",
        "    LA(x5, TEST_FOR_EXECUTION)",
        "    srl x5, x5, PMP_SHIFT",
        "    .set i, 0",
        "    .set pmpaddri, CSR_PMPADDR0",
        "    .rept 7",
        "    LI(x6, (1 << i) * (PMP_NAPOT_REGION_BYTES / 8) - 1)",
        "    or x6, x5, x6",
        "    csrw pmpaddri, x6",
        "    .set i, i+1",
        "    .set pmpaddri, pmpaddri+1",
        "    .endr",
    ]
    for csr in sorted({cfg_csr(xlen, e) for e in range(7)}):
        names = [f"PMPREGION{e}_LXWR_{lxwr}" for e, lxwr in enumerate(_PRIORITY_CODES) if cfg_csr(xlen, e) == csr]
        body.extend([f"    LI(x4, ({'|'.join(names)}))", f"    csrw {csr}, x4"])
    body.extend(["    RVTEST_SFENCE_VMA_IF_SUPPORTED", "", VERIFICATION_SECTION])
    for n, lxwr in enumerate(_PRIORITY_CODES, start=1):
        size = 1 << (n - 1)
        body.extend(
            [
                "",
                f"// Test Case: {n} : access the last word of region {n - 1} (size {size}x), permissions {lxwr}",
                f"    PMP_VERIFICATION_RWX    (TEST_FOR_EXECUTION + {size} * PMP_NAPOT_REGION_BYTES - 4), test_{n}",
            ]
        )
    body.extend(EXIT)
    data = [
        ".p2align 12",
        "TEST_FOR_EXECUTION_0:",
        "    jr ra",
        ".p2align (UDB_PMP_GRANULARITY + 7)",
        "TEST_FOR_EXECUTION:",
        "    .rept (16 * PMP_NAPOT_REGION_BYTES)",
        "    nop",
        "    .endr",
        *RETURN_TRAMPOLINE,
    ]
    return _misc_file(
        xlen,
        "priority",
        "cp_priority",
        "{jalr, sw, lw} at the last word of each of seven nested NAPOT regions cycling the six legal XWR; the smallest matching region decides.",
        body,
        params=amode_params("napot"),
        sigupd=sigupd_count(7 * 3),
        sig_strs=sig_strs("RWX", xlen, "pmpsm_priority"),
        data=tuple(data),
    )


def _priority_off_file(xlen: Xlen) -> PmpFile:
    codes = (("1000", "off"), ("1101", "napot"), ("1000", "off"), ("1111", "napot"))
    body = [
        *zero_pmp_regs(xlen),
        "",
        *(
            f"#define PMPREGION{e}_LXWR_{lxwr} {cfg_byte(lxwr, amode, cfg_shift(xlen, e))}"
            for e, (lxwr, amode) in enumerate(codes)
        ),
        "#define REGIONSTART TEST_FOR_EXECUTION",
        *NAPOT_MASK_DEFINES,
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        "    // pmpaddr0 and pmpaddr2: OFF regions; pmpaddr1 and pmpaddr3: NAPOT regions at REGIONSTART",
        *set_pmpaddr("na4", 0),
        "    csrw pmpaddr2, x5",
        *set_pmpaddr("napot", 1),
        "    csrw pmpaddr3, x5",
        "",
        VERIFICATION_SECTION,
        "",
        "// Test Case: 1 : an OFF region does not match, and the first matching region takes priority",
        *set_pmpcfg(xlen, 0, "|".join(f"PMPREGION{e}_LXWR_{lxwr}" for e, (lxwr, _) in enumerate(codes))),
        "    RVTEST_SFENCE_VMA_IF_SUPPORTED",
        "    PMP_VERIFICATION_RWX    TEST_FOR_EXECUTION, test_1",
        *EXIT,
    ]
    return _misc_file(
        xlen,
        "priority_off",
        "cp_priority_off",
        "{jalr, sw, lw} at a region covered by entries 0..3 = OFF, NAPOT XR, OFF, NAPOT XWR; entry 1 decides.",
        body,
        params=amode_params("napot"),
        sigupd=sigupd_count(3),
        sig_strs=sig_strs("RWX", xlen, "pmpsm_priority_off"),
        data=tuple(REGION_BLOBS["napot_pad"]),
    )


#####################################################################
# pmpsm_all_entries_check: every PMP entry enforces load/store access
#####################################################################


def _all_entries_file(xlen: Xlen) -> PmpFile:
    def _all_entries_cfg(entry: int) -> str:
        return f"(PMP_REGION_CFG << {cfg_shift(xlen, entry)})"

    body = [
        *zero_pmp_regs(xlen),
        "",
        f"#define PMP_REGION_CFG {cfg_byte('1101', 'napot', '0')}",
        "#define REGIONSTART TEST_FOR_EXECUTION",
        *NAPOT_MASK_DEFINES,
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        VERIFICATION_SECTION,
        "",
        "// Every entry below the background entry, lowest priority first.",
        "#if UDB_NUM_PMP_ENTRIES == 64",
        *entry_walk(xlen, range(62, -1, -1), "napot", _all_entries_cfg, "RWX"),
        "#else",
        *entry_walk(xlen, range(14, -1, -1), "napot", _all_entries_cfg, "RWX"),
        "#endif",
        *EXIT,
    ]
    return _misc_file(
        xlen,
        "all_entries_check",
        "cp_pmp64",
        "{jalr, sw, lw} at a locked NAPOT XR region, for every entry below the background entry (16 or 64 entries).",
        body,
        params=amode_params("napot"),
        sigupd=sigupd_count(63 * 3),
        sig_strs=sig_strs("RWX", xlen, "pmpsm_all_entries_check"),
        data=tuple(REGION_BLOBS["napot_pad"]),
    )


#####################################################################


def build_misc_files() -> list[PmpFile]:
    """Every PMPSm file outside the cfg_* and pmpcfg_walk families, for both XLENs."""
    specs: list[PmpFile] = []
    for xlen in XLENS.values():
        specs.append(_all_entries_file(xlen))
        specs.append(_grain_file(xlen))
        specs.append(_grain_check_file(xlen))
        specs.append(_legal_file(xlen, "na4"))
        specs.extend(_legal_file(xlen, amode, part) for amode in ("napot", "tor") for part in (1, 2))
        specs.append(_priority_file(xlen))
        specs.append(_priority_off_file(xlen))
    specs.append(_pmpaddr_upper_file())
    return specs


@add_pmp_suite("PMPSm")
def build() -> list[PmpFile]:
    return [*build_walk_files(), *build_cfg_files(), *build_misc_files()]
