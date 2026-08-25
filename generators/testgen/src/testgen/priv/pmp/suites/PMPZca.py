##################################
# priv/pmp/suites/PMPZca.py
#
# PMPZca: PMP enforcement of compressed instruction fetches.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMPZca suite: PMP region boundaries versus 16-bit and misaligned 32-bit fetches."""

from __future__ import annotations

from testgen.priv.pmp import add_pmp_suite
from testgen.priv.pmp.macros import (
    EXIT,
    GRANULE_WORDS,
    LOCKED_LXWR_CASES,
    NAPOT_MASK_DEFINES,
    NAPOT_REGION_WORDS,
    RETURN_TRAMPOLINE,
    VERIFICATION_SECTION,
    amode_params,
    banner,
    cfg_byte,
    cfg_shift,
    exec_region,
    set_pmpaddr,
    set_pmpcfg,
    sigupd_count,
    walk_file,
    zero_pmp_regs,
)
from testgen.priv.pmp.model import XLENS, PmpFile, Xlen

_JALR = "    jalr x0, x1, 0"

#: Bytes in the smallest region of each address mode.
_REGION_BYTES = {
    "na4": "4",
    "napot": "PMP_NAPOT_REGION_BYTES",
    "off": "PMP_NAPOT_REGION_BYTES",
    "tor": "PMP_TOR_REGION_BYTES",
}


def _extensions(xlen: Xlen) -> tuple[str, ...]:
    return ("Zca", "Sm")


def _march(xlen: Xlen, *extra: str) -> str:
    return "_".join((f"rv{xlen.bits}i", "zicsr", "zifencei", "zca", *extra))


def _zca_file(
    xlen: Xlen,
    name: str,
    coverpoint: str,
    test_cases: str,
    amode: str | None,
    *,
    sigupd: int,
    body: list[str],
    sig_strs: tuple[tuple[str, str], ...],
    data: tuple[str, ...],
) -> PmpFile:
    return PmpFile(
        filename=f"pmpzca_{name}.S",
        xlen=xlen,
        banner=banner(f"{coverpoint} for PMPZca is fully covered in this test file.", test_cases),
        required_extensions=_extensions(xlen),
        params=amode_params(amode),
        march=_march(xlen),
        sigupd=sigupd,
        body=tuple(body),
        sig_strs=sig_strs,
        data=data,
    )


#####################################################################
# cret_{na4,napot,tor}: four c.ret around one region boundary
#####################################################################


def _cret_body(xlen: Xlen, amode: str) -> list[str]:
    entry = 1 if amode == "tor" else 0
    lines = [
        *zero_pmp_regs(xlen),
        "",
        f"#define PMPCFG {cfg_byte('1111', amode, cfg_shift(xlen, entry))}",
        "#define REGIONSTART TEST_FOR_EXECUTION_1",
        *(NAPOT_MASK_DEFINES if amode == "napot" else []),
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        VERIFICATION_SECTION,
        "",
        f"// Test Case: {amode.upper()} region with L -> 1 and XWR -> 111, c.ret just below, at the bottom, at the top and just above it",
        *set_pmpaddr(amode, entry),
        *set_pmpcfg(xlen, entry, "PMPCFG"),
        "    RVTEST_SFENCE_VMA_IF_SUPPORTED",
    ]
    for n in range(4):
        lines.extend(["", f"    PMP_VERIFICATION_X_C TEST_FOR_EXECUTION_{n}, test{n + 1}"])
    lines.extend(EXIT)
    return lines


def _cret_data(xlen: Xlen, amode: str) -> list[str]:
    """Four c.ret instructions: just below, at the start, at the top and just above the region."""
    lines = [
        f".p2align {11 if xlen.bits == 32 else 10}",
        f".skip {'0x806' if amode == 'napot' else '0x802'}",
        "TEST_FOR_EXECUTION_0:",
        "    ret",
        "TEST_FOR_EXECUTION_1:",
        "    ret",
    ]
    if amode != "na4":
        lines.extend([f"    .rept (({_REGION_BYTES[amode]} - 4) / 2)", "    c.nop", "    .endr"])
    lines.extend(["TEST_FOR_EXECUTION_2:", "    ret", "TEST_FOR_EXECUTION_3:", "    ret", *RETURN_TRAMPOLINE])
    return lines


def _cret_file(xlen: Xlen, amode: str) -> PmpFile:
    return _zca_file(
        xlen,
        f"cret_{amode}",
        f"cp_cret_{amode}",
        f"""\
Checking that 16-bit fetches adjacent to a {amode.upper()} PMP boundary succeed.
Set up a standard {amode.upper()} PMP region with L=1, XWR = 111. Placing four
c.ret = c.jr ra statements just below, at bottom, at top, and just
above PMP region, half of which are on 16-bit boundaries.
Attempt jalr to each c.ret.""",
        amode,
        sigupd=sigupd_count(4),
        body=_cret_body(xlen, amode),
        sig_strs=(("test_1", f"test: 1; cp: pmpzca_cret_{amode}_execute"),),
        data=tuple(_cret_data(xlen, amode)),
    )


#####################################################################
# aligned_* / misaligned_*: three consecutive regions, the third locked
# without permissions, and uncompressed jalr inside them (aligned) or
# straddling their boundaries (misaligned)
#####################################################################


def _region_body(xlen: Xlen, amode: str, misaligned: bool) -> list[str]:
    size = _REGION_BYTES[amode]
    entries = (1, 2, 3) if amode == "tor" else (0, 1, 2)
    lines = [*zero_pmp_regs(xlen), ""]
    for entry, lxwr in zip(entries, ("1111", "1111", "1111" if amode == "off" else "1000"), strict=True):
        lines.append(f"#define PMP{entry}CFG {cfg_byte(lxwr, amode, cfg_shift(xlen, entry))}")
    region = "TEST_FOR_EXECUTION_0" if (amode == "na4" and misaligned) else "TEST_FOR_EXECUTION_1"
    lines.extend(["", f"#define REGIONSTART {region}", f"#define REGION_SIZE {size}"])
    if amode == "napot":
        lines.extend(NAPOT_MASK_DEFINES)
    lines.extend(["", "    RVTEST_PMP_SET_BACKGROUND x4", "", VERIFICATION_SECTION, ""])
    lines.append(f"// Test Case: three consecutive {amode.upper()} regions, the third locked with XWR = 000")
    if amode == "tor":
        lines.extend(["    LA(x5, REGIONSTART)", "    srl x5, x5, PMP_SHIFT", "    csrw pmpaddr0, x5"])
    for i, entry in enumerate(entries):
        lines.extend(
            [
                "    LA(x5, REGIONSTART)",
                f"    LI(x6, {i + 1 if amode == 'tor' else i} * REGION_SIZE)",
                "    add x5, x5, x6",
                "    srl x5, x5, PMP_SHIFT",
            ]
        )
        if amode == "napot":
            lines.extend(
                ["    LI(x6, PMP_MASK)", "    and x5, x5, x6", "    LI(x6, PMP_REGION_SIZE)", "    or x5, x5, x6"]
            )
        lines.append(f"    csrw pmpaddr{entry}, x5")
    lines.extend(set_pmpcfg(xlen, entries[0], "|".join(f"PMP{entry}CFG" for entry in entries)))
    lines.append("    RVTEST_SFENCE_VMA_IF_SUPPORTED")
    calls = (
        ["TEST_FOR_EXECUTION_2", "TEST_FOR_EXECUTION_4"]
        if misaligned and amode != "na4"
        else ["TEST_FOR_EXECUTION_1", "TEST_FOR_EXECUTION_2"]
    )
    if misaligned and amode == "napot":
        calls += ["REGIONSTART", "REGIONSTART + REGION_SIZE"]
    for n, target in enumerate(calls, start=1):
        lines.extend(["", f"    PMP_VERIFICATION_X_C {target}, test_{n}"])
    lines.extend(EXIT)
    return lines


_GRAIN_ALIGN = ".p2align (UDB_PMP_GRANULARITY)"
_STRADDLE_NOTE = (
    "// No alignment before these labels: the c.nop offsets above make the jalr straddle the region boundary"
)


def _filler(count: str, insn: str = "nop") -> list[str]:
    return [f"    .rept {count}", f"    {insn}", "    .endr"]


def _aligned_data(amode: str) -> list[str]:
    """One uncompressed jalr inside each of the first two regions."""
    lines = [".p2align 12", _GRAIN_ALIGN]
    if amode == "off":
        lines.extend(["TEST_FOR_EXECUTION_0:", *_filler(NAPOT_REGION_WORDS, "jalr x0, x1, 0")])
    else:
        lines.extend(["TEST_FOR_EXECUTION_0:", _JALR])
    for n in (1, 2):
        lines.extend([_GRAIN_ALIGN, f"TEST_FOR_EXECUTION_{n}:", _JALR])
        if amode != "na4":
            lines.extend(_filler("((REGION_SIZE - 4) / 2)"))
    if amode != "na4":
        lines.extend([_GRAIN_ALIGN, "TEST_FOR_EXECUTION_3:", *_filler("(REGION_SIZE / 2)")])
    lines.extend(RETURN_TRAMPOLINE)
    return lines


def _misaligned_data(amode: str) -> list[str]:
    """An uncompressed jalr straddling the start and the end of the second region."""
    lines = [".p2align 12", _GRAIN_ALIGN]
    if amode == "na4":
        lines.extend(
            [
                "TEST_FOR_EXECUTION_X:",
                _JALR,
                _GRAIN_ALIGN,
                "TEST_FOR_EXECUTION_0:",
                "    c.nop",
                _STRADDLE_NOTE,
                "TEST_FOR_EXECUTION_1:",
                _JALR,
                "TEST_FOR_EXECUTION_2:",
                _JALR,
            ]
        )
    else:
        if amode == "off":
            lines.extend(["TEST_FOR_EXECUTION_0:", *_filler(NAPOT_REGION_WORDS, "jalr x0, x1, 0")])
        elif amode == "napot":
            lines.extend(["TEST_FOR_EXECUTION_0:", _JALR, "    nop", _GRAIN_ALIGN])
        else:
            lines.extend(["TEST_FOR_EXECUTION_0:", _JALR, _GRAIN_ALIGN])
        lines.extend(
            [
                "TEST_FOR_EXECUTION_1:",
                *_filler("((REGION_SIZE / 2) - 1)", "c.nop"),
                _STRADDLE_NOTE,
                "TEST_FOR_EXECUTION_2:",
                _JALR,
                "TEST_FOR_EXECUTION_3:",
                *_filler("((REGION_SIZE / 2) - 2)", "c.nop"),
                "TEST_FOR_EXECUTION_4:",
                _JALR,
                _GRAIN_ALIGN,
                "TEST_FOR_EXECUTION_5:",
                *_filler("(REGION_SIZE / 2)"),
            ]
        )
    lines.extend(RETURN_TRAMPOLINE)
    return lines


def _region_file(xlen: Xlen, amode: str, misaligned: bool) -> PmpFile:
    prefix = "misaligned" if misaligned else "aligned"
    if misaligned:
        test_cases = f"An uncompressed jalr straddling the start and the end of the second of three consecutive {amode.upper()} regions."
    else:
        test_cases = f"An uncompressed jalr inside each of the first two of three consecutive {amode.upper()} regions, the third locked with XWR = 000."
    return _zca_file(
        xlen,
        f"{prefix}_{amode}",
        f"cp_{prefix}_{amode}",
        test_cases,
        amode if amode != "off" else None,
        sigupd=sigupd_count(4 if misaligned and amode == "napot" else 2),
        body=_region_body(xlen, amode, misaligned),
        sig_strs=(("test_1", f"test: 1; cp: pmpzca_{prefix}_{amode}_execute"),),
        data=tuple(_misaligned_data(amode) if misaligned else _aligned_data(amode)),
    )


#####################################################################
# legal_lwrx and the Zcb/Zcd/Zcf walks: every legal locked LXWR against
# compressed loads, stores and jumps
#####################################################################

_LEGAL_TEST_CASES = "Compressed loads, stores and a c.jalr against a locked NAPOT region with each legal XWR."


def _legal_file(xlen: Xlen) -> PmpFile:
    return walk_file(
        xlen,
        "pmpzca_legal_lwrx.S",
        "ZCA",
        LOCKED_LXWR_CASES,
        "napot",
        banner=banner("cp_cfg_RW for PMPZca is fully covered in this test file.", _LEGAL_TEST_CASES),
        prefix="pmpzca_legal_lxwr",
        required_extensions=_extensions(xlen),
        march=_march(xlen),
        data=exec_region((GRANULE_WORDS, "c.nop\n    c.nop")),
    )


def _zc_file(xlen: Xlen, subset: str) -> PmpFile:
    return walk_file(
        xlen,
        f"pmp{subset}_legal_lxwr.S",
        subset.upper(),
        LOCKED_LXWR_CASES,
        "napot",
        banner=banner("cp_cfg_RW for PMPZca is fully covered in this test file.", _LEGAL_TEST_CASES),
        prefix=f"pmp{subset}_cfg_wr",
        required_extensions=(subset.capitalize(), "Sm"),
        march=_march(xlen, subset),
        data=exec_region(),
    )


@add_pmp_suite("PMPZca")
def build() -> list[PmpFile]:
    specs: list[PmpFile] = []
    for xlen in XLENS.values():
        specs.extend(_cret_file(xlen, amode) for amode in ("na4", "napot", "tor"))
        specs.extend(
            _region_file(xlen, amode, misaligned)
            for misaligned in (False, True)
            for amode in ("na4", "napot", "off", "tor")
        )
        specs.append(_legal_file(xlen))
        specs.extend(_zc_file(xlen, subset) for subset in ("zcb", "zcd"))
    specs.append(_zc_file(XLENS[32], "zcf"))
    return specs
