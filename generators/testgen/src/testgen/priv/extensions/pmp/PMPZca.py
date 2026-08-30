##################################
# priv/extensions/pmp/PMPZca.py
#
# PMPZca: PMP enforcement of compressed instruction fetches.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMP tests for compressed instructions and misaligned 32-bit instruction fetches."""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.pmp.helpers import (
    LOCKED_LXWR_CASES,
    NAPOT_MASK_DEFINES,
    NAPOT_REGION_WORDS,
    RETURN_TRAMPOLINE,
    TOR_REGION_WORDS,
    cfg_byte,
    cfg_shift,
    lxwr_walk_body,
    make_exec_region,
    set_pmpaddr,
    set_pmpcfg,
    zero_pmp_regs,
)
from testgen.priv.extensions.pmp.probes import (
    gen_compressed_execute,
    gen_zca,
    gen_zcb,
    gen_zcd,
    gen_zcf,
)
from testgen.priv.registry import add_priv_test_generator

_JALR = "jalr x0, x1, 0"

#: Bytes in the smallest region of each address mode.
_REGION_BYTES = {
    "na4": "4",
    "napot": "PMP_NAPOT_REGION_BYTES",
    "off": "PMP_NAPOT_REGION_BYTES",
    "tor": "PMP_TOR_REGION_BYTES",
}


#####################################################################
# cret_{na4,napot,tor}: four c.ret around one region boundary
#####################################################################


def _cret_body(test_data: TestData, amode: str) -> list[str]:
    entry = 1 if amode == "tor" else 0
    lines = [
        *zero_pmp_regs(),
        "",
        f"#define PMPCFG {cfg_byte('1111', amode, cfg_shift(entry))}",
        "#define REGIONSTART TEST_FOR_EXECUTION_1",
        *(NAPOT_MASK_DEFINES if amode == "napot" else []),
        "",
        "RVTEST_PMP_SET_BACKGROUND x4",
        "",
        f"// PMP configuration: {amode.upper()} region with L = 1 and XWR = 111, c.ret just below, at the bottom, at the top and just above it",
        *set_pmpaddr(amode, entry),
        *set_pmpcfg(entry, "PMPCFG"),
        "RVTEST_SFENCE_VMA_IF_SUPPORTED",
    ]
    for n in range(4):
        lines.extend(gen_compressed_execute(test_data, f"boundary{n}", f"cp_cret_{amode}", f"TEST_FOR_EXECUTION_{n}"))
    return lines


def _cret_data(amode: str) -> list[str]:
    """Four c.ret instructions: just below, at the start, at the top and just above the region."""
    lines = [
        "#if __riscv_xlen == 32",
        ".p2align 11",
        "#else",
        ".p2align 10",
        "#endif",
        f".skip {'0x806' if amode == 'napot' else '0x802'}",
        "TEST_FOR_EXECUTION_0:",
        "ret",
        "TEST_FOR_EXECUTION_1:",
        "ret",
    ]
    if amode != "na4":
        lines.extend([f".rept (({_REGION_BYTES[amode]} - 4) / 2)", "c.nop", ".endr"])
    lines.extend(["TEST_FOR_EXECUTION_2:", "ret", "TEST_FOR_EXECUTION_3:", "ret", *RETURN_TRAMPOLINE])
    return lines


def _make_cret_chunk(test_data: TestData, amode: str) -> TestChunk:
    test_cases = f"""\
Checking that 16-bit fetches adjacent to a {amode.upper()} PMP boundary succeed.
Set up a standard {amode.upper()} PMP region with L=1, XWR = 111. Placing four
c.ret = c.jr ra statements just below, at bottom, at top, and just
above PMP region, half of which are on 16-bit boundaries.
Attempt jalr to each c.ret."""
    chunk = test_data.begin_test_chunk(f"cret_{amode}")
    chunk.section_header = comment_banner(f"cp_cret_{amode}", test_cases)
    chunk.code.extend(_cret_body(test_data, amode))
    chunk.raw_data.extend(_cret_data(amode))
    return test_data.end_test_chunk()


#####################################################################
# aligned_* / misaligned_*: three consecutive regions, the third locked
# without permissions, and uncompressed jalr inside them (aligned) or
# straddling their boundaries (misaligned)
#####################################################################


def _region_body(test_data: TestData, amode: str, misaligned: bool) -> list[str]:
    size = _REGION_BYTES[amode]
    entries = (1, 2, 3) if amode == "tor" else (0, 1, 2)
    lines = [*zero_pmp_regs(), ""]
    for entry, lxwr in zip(entries, ("1111", "1111", "1111" if amode == "off" else "1000"), strict=True):
        lines.append(f"#define PMP{entry}CFG {cfg_byte(lxwr, amode, cfg_shift(entry))}")
    region = "TEST_FOR_EXECUTION_0" if (amode == "na4" and misaligned) else "TEST_FOR_EXECUTION_1"
    lines.extend(["", f"#define REGIONSTART {region}", f"#define REGION_SIZE {size}"])
    if amode == "napot":
        lines.extend(NAPOT_MASK_DEFINES)
    lines.extend(["", "RVTEST_PMP_SET_BACKGROUND x4"])
    lines.append(f"// PMP configuration: three consecutive {amode.upper()} regions, the third locked with XWR = 000")
    if amode == "tor":
        lines.extend(["LA(x5, REGIONSTART)", "srl x5, x5, PMP_SHIFT", "csrw pmpaddr0, x5"])
    for i, entry in enumerate(entries):
        lines.extend(
            [
                "LA(x5, REGIONSTART)",
                f"LI(x6, {i + 1 if amode == 'tor' else i} * REGION_SIZE)",
                "add x5, x5, x6",
                "srl x5, x5, PMP_SHIFT",
            ]
        )
        if amode == "napot":
            lines.extend(["LI(x6, PMP_MASK)", "and x5, x5, x6", "LI(x6, PMP_REGION_SIZE)", "or x5, x5, x6"])
        lines.append(f"csrw pmpaddr{entry}, x5")
    lines.extend(set_pmpcfg(entries[0], "|".join(f"PMP{entry}CFG" for entry in entries)))
    lines.append("RVTEST_SFENCE_VMA_IF_SUPPORTED")
    calls = (
        ["TEST_FOR_EXECUTION_2", "TEST_FOR_EXECUTION_4"]
        if misaligned and amode != "na4"
        else ["TEST_FOR_EXECUTION_1", "TEST_FOR_EXECUTION_2"]
    )
    if misaligned and amode == "napot":
        calls += ["REGIONSTART", "REGIONSTART + REGION_SIZE"]
    prefix = "misaligned" if misaligned else "aligned"
    for n, target in enumerate(calls, start=1):
        lines.extend(gen_compressed_execute(test_data, f"region{n}", f"cp_{prefix}_{amode}", target))
    return lines


_GRAIN_ALIGN = ".p2align (UDB_PMP_GRANULARITY)"
_STRADDLE_NOTE = (
    "// No alignment before these labels: the c.nop offsets above make the jalr straddle the region boundary"
)


def _filler(count: str, insn: str = "nop") -> list[str]:
    return [f".rept {count}", insn, ".endr"]


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
                "c.nop",
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
            lines.extend(["TEST_FOR_EXECUTION_0:", _JALR, "nop", _GRAIN_ALIGN])
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


def _make_region_chunk(test_data: TestData, amode: str, misaligned: bool) -> TestChunk:
    prefix = "misaligned" if misaligned else "aligned"
    if misaligned:
        test_cases = f"An uncompressed jalr straddling the start and the end of the second of three consecutive {amode.upper()} regions."
    else:
        test_cases = f"An uncompressed jalr inside each of the first two of three consecutive {amode.upper()} regions, the third locked with XWR = 000."
    chunk = test_data.begin_test_chunk(f"{prefix}_{amode}")
    chunk.section_header = comment_banner(f"cp_{prefix}_{amode}", test_cases)
    chunk.code.extend(_region_body(test_data, amode, misaligned))
    chunk.raw_data.extend(_misaligned_data(amode) if misaligned else _aligned_data(amode))
    return test_data.end_test_chunk()


#####################################################################
# legal_lwrx and the Zcb/Zcd/Zcf walks: every legal locked LXWR against
# compressed loads, stores and jumps
#####################################################################

_ZCA_LEGAL_TEST_CASES = (
    "Compressed integer loads, stores, stack-pointer accesses, and c.jalr against a locked NAPOT region "
    "with each legal XWR."
)
_ZC_TEST_CASES = {
    "zcb": "Compressed byte and halfword loads and stores against a locked NAPOT region with each legal XWR.",
    "zcd": "Compressed double-precision floating-point loads and stores against a locked NAPOT region with each legal XWR.",
    "zcf": "Compressed single-precision floating-point loads and stores against a locked NAPOT region with each legal XWR.",
}


def _make_legal_chunk(test_data: TestData) -> TestChunk:
    chunk = test_data.begin_test_chunk("legal_lwrx")
    chunk.section_header = comment_banner("cp_cfg_RW", _ZCA_LEGAL_TEST_CASES)
    chunk.code.extend(lxwr_walk_body(test_data, LOCKED_LXWR_CASES, "napot", gen_zca, "cp_cfg_RW"))
    chunk.raw_data.extend(make_exec_region((TOR_REGION_WORDS, "c.nop\nc.nop")))
    return test_data.end_test_chunk()


def _make_zc_chunk(test_data: TestData, subset: str) -> TestChunk:
    chunk = test_data.begin_test_chunk(f"{subset}_legal_lxwr")
    chunk.section_header = comment_banner("cp_cfg_RW", _ZC_TEST_CASES[subset])
    generator = {"zcb": gen_zcb, "zcd": gen_zcd, "zcf": gen_zcf}[subset]
    chunk.code.extend(lxwr_walk_body(test_data, LOCKED_LXWR_CASES, "napot", generator, "cp_cfg_RW"))
    chunk.raw_data.extend(make_exec_region())
    return test_data.end_test_chunk()


@add_priv_test_generator(
    "PMPZca",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Zca", "Sm"],
    params=["NUM_PMP_ENTRIES: '>0'"],
)
def make_pmpzca_off(test_data: TestData) -> list[TestChunk]:
    return [_make_region_chunk(test_data, "off", misaligned) for misaligned in (False, True)]


@add_priv_test_generator(
    "PMPZca",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Zca", "Sm"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_NA4_SUPPORTED: true"],
)
def make_pmpzca_na4(test_data: TestData) -> list[TestChunk]:
    return [
        _make_cret_chunk(test_data, "na4"),
        *(_make_region_chunk(test_data, "na4", misaligned) for misaligned in (False, True)),
    ]


@add_priv_test_generator(
    "PMPZca",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Zca", "Sm"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_NAPOT_SUPPORTED: true"],
)
def make_pmpzca_napot(test_data: TestData) -> list[TestChunk]:
    return [
        _make_cret_chunk(test_data, "napot"),
        *(_make_region_chunk(test_data, "napot", misaligned) for misaligned in (False, True)),
    ]


@add_priv_test_generator(
    "PMPZca",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Zca", "Sm"],
    params=["NUM_PMP_ENTRIES: '>0'"],
)
def make_pmpzca_legal(test_data: TestData) -> list[TestChunk]:
    return [_make_legal_chunk(test_data)]


@add_priv_test_generator(
    "PMPZca",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Zca", "Sm"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_TOR_SUPPORTED: true"],
)
def make_pmpzca_tor(test_data: TestData) -> list[TestChunk]:
    return [
        _make_cret_chunk(test_data, "tor"),
        *(_make_region_chunk(test_data, "tor", misaligned) for misaligned in (False, True)),
    ]


@add_priv_test_generator(
    "PMPZca",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Zcb", "Sm"],
    march_extensions=["Zca", "Zcb"],
    params=["NUM_PMP_ENTRIES: '>0'"],
)
def make_pmpzca_zcb(test_data: TestData) -> list[TestChunk]:
    return [_make_zc_chunk(test_data, "zcb")]


@add_priv_test_generator(
    "PMPZca",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Zcd", "Sm"],
    march_extensions=["Zca", "Zcd"],
    params=["NUM_PMP_ENTRIES: '>0'"],
)
def make_pmpzca_zcd(test_data: TestData) -> list[TestChunk]:
    return [_make_zc_chunk(test_data, "zcd")]


@add_priv_test_generator(
    "PMPZca",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Zcf", "Sm"],
    march_extensions=["Zca", "Zcf"],
    params=["MXLEN: 32", "NUM_PMP_ENTRIES: '>0'"],
)
def make_pmpzca_zcf(test_data: TestData) -> list[TestChunk]:
    return [_make_zc_chunk(test_data, "zcf")]
