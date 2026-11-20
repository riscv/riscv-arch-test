##################################
# priv/extensions/pmp/Zicbo.py
#
# PMP Zicbo: PMP behavior of cache-block and prefetch instructions.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMP Zicbo group: cache-block and prefetch instructions checked against PMP."""

from functools import partial

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.pmp.helpers import (
    LOCKED_LXWR_CASES,
    cfg_byte,
    cfg_shift,
    lxwr_walk_body,
    make_exec_region,
    napot_mask_defines,
    set_pmpaddr,
    set_pmpcfg,
    zero_pmp_regs,
)
from testgen.priv.extensions.pmp.probes import (
    ProbeGenerator,
    gen_cbo,
    gen_prefetch,
)
from testgen.priv.registry import add_priv_test_generator

# The locked NAPOT region is max(page, grain) bytes from TEST_FOR_EXECUTION; pad to its end so that
# nothing the trap handler writes (e.g. the trap signature) shares it at grains above a page.
_PAGE_REGION = [*make_exec_region(("1024", "nop"), pad=None), ".p2align 12", ".p2align (UDB_PMP_GRANULARITY)"]

#: The region under test followed by a region of the same size that a locked entry covers in
#: cp_none_cbo, so nothing else the test uses lies there.
_NONE_REGIONS = [
    ".p2align 12",
    ".p2align (UDB_PMP_GRANULARITY)",
    "TEST_FOR_EXECUTION:",
    ".space (1 << PMP_REGION_SHIFT)",
    "PMPZICBO_ABOVE:",
    ".space (1 << PMP_REGION_SHIFT)",
]


def _make_unlocked_chunk(test_data: TestData, name: str, probe: ProbeGenerator, label: str) -> TestChunk:
    chunk = test_data.begin_test_chunk(f"Zicbo_{name}_unlocked")
    chunk.section_header = comment_banner(
        "cp_cfg_L_access_cbo",
        f"{label} against an unlocked page-sized NAPOT region with XWR = 000 and 001; never faults.",
    )
    chunk.code.extend(
        lxwr_walk_body(
            test_data,
            [("0000", 0), ("0001", 0)],
            "napot",
            probe,
            lambda instruction: f"cp_cfg_L_access_cbo_{instruction.removeprefix('cbo.')}",
            napot_mask=napot_mask_defines(12),
        )
    )
    chunk.raw_data.extend(_PAGE_REGION)
    return test_data.end_test_chunk()


def _none_cbo(instruction: str) -> str:
    return f"cp_none_cbo_{instruction.removeprefix('cbo.')}"


def _make_none_chunk(test_data: TestData, name: str, probe: ProbeGenerator, label: str) -> TestChunk:
    chunk = test_data.begin_test_chunk(f"Zicbo_{name}_none")
    chunk.section_header = comment_banner(
        "cp_none_cbo",
        f"{label} at a page-sized region that no PMP entry matches, with every entry off and then\n"
        "with a locked entry just above it and an unlocked entry just below it; never faults.",
    )
    neighbors = f"({cfg_byte('1000', 'napot', cfg_shift(0))} | {cfg_byte('0000', 'napot', cfg_shift(1))})"
    chunk.code.extend(
        [
            *zero_pmp_regs(),
            "",
            *napot_mask_defines(12),
            "RVTEST_SFENCE_VMA_IF_SUPPORTED",
            "",
            "// PMP configuration 1: every entry off",
            *probe(test_data, "off", _none_cbo, "TEST_FOR_EXECUTION"),
            "",
            "// PMP configuration 2: entry 0 = L=1, XWR=000 just above the region; entry 1 = L=0, XWR=000 just below it",
            *set_pmpaddr("napot", 0, "PMPZICBO_ABOVE"),
            *set_pmpaddr("napot", 1, "TEST_FOR_EXECUTION - (1 << PMP_REGION_SHIFT)"),
            *set_pmpcfg(0, neighbors),
            "RVTEST_SFENCE_VMA_IF_SUPPORTED",
            *probe(test_data, "active", _none_cbo, "TEST_FOR_EXECUTION"),
        ]
    )
    chunk.raw_data.extend(_NONE_REGIONS)
    return test_data.end_test_chunk()


def _make_cbo_chunks(test_data: TestData, name: str, instructions: tuple[str, ...]) -> list[TestChunk]:
    """The locked, unlocked and no-match PMP chunks for the cache-block instructions of one extension.
    In the unlocked and no-match chunks, which never fault, cbo.zero is checked by reading the block back."""
    probe = partial(gen_cbo, instructions=instructions)
    readback_probe = partial(gen_cbo, instructions=instructions, readback="cbo.zero" in instructions)
    label = "cbo." + "/".join(instruction.removeprefix("cbo.") for instruction in instructions)
    names = [f"cp_cbo_{instruction.removeprefix('cbo.')}" for instruction in instructions]
    coverpoints = " and ".join([", ".join(names[:-1]), names[-1]] if len(names) > 1 else names)
    chunks = []
    for number, lxwr in ((1, "1000"), (2, "1001"), (3, "1011")):
        chunk = test_data.begin_test_chunk(f"Zicbo_{name}_wr_{number:02d}")
        chunk.section_header = comment_banner(
            coverpoints,
            f"{label} against a locked page-sized NAPOT region with WR = {lxwr[2:]}.",
        )
        chunk.code.extend(
            lxwr_walk_body(
                test_data,
                [(lxwr, 0)],
                "napot",
                probe,
                lambda instruction: f"cp_cbo_{instruction.removeprefix('cbo.')}",
                first=number,
                napot_mask=napot_mask_defines(12),
            )
        )
        chunk.raw_data.extend(_PAGE_REGION)
        chunks.append(test_data.end_test_chunk())
    chunks.append(_make_unlocked_chunk(test_data, name, readback_probe, label))
    chunks.append(_make_none_chunk(test_data, name, readback_probe, label))
    return chunks


@add_priv_test_generator(
    "PMP",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Sm", "Zicbom"],
    params=["NUM_PMP_ENTRIES: '>0'"],
)
def make_pmpzicbo_cbom(test_data: TestData) -> list[TestChunk]:
    return _make_cbo_chunks(test_data, "cbom", ("cbo.clean", "cbo.flush", "cbo.inval"))


@add_priv_test_generator(
    "PMP",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Sm", "Zicboz"],
    params=["NUM_PMP_ENTRIES: '>0'"],
)
def make_pmpzicbo_cboz(test_data: TestData) -> list[TestChunk]:
    return _make_cbo_chunks(test_data, "cboz", ("cbo.zero",))


@add_priv_test_generator(
    "PMP",
    extra_defines=["#define BOOT_TO_MMODE"],
    # prefetch.i/r/w are HINTs (ORI with rd = x0), so the test runs with or without Zicbop
    required_extensions=["Sm"],
    march_extensions=["Zicbop"],
    params=["NUM_PMP_ENTRIES: '>0'"],
)
def make_pmpzicbo_prefetch(test_data: TestData) -> list[TestChunk]:
    chunk = test_data.begin_test_chunk("Zicbo_prefetch")
    chunk.section_header = comment_banner(
        "cp_prefetch_i, cp_prefetch_r and cp_prefetch_w",
        "prefetch.i/r/w against a locked page-sized NAPOT region with each legal XWR; never faults.",
    )
    chunk.code.extend(
        lxwr_walk_body(
            test_data,
            LOCKED_LXWR_CASES,
            "napot",
            gen_prefetch,
            lambda instruction: f"cp_prefetch_{instruction.removeprefix('prefetch.')}",
            napot_mask=napot_mask_defines(12),
        )
    )
    chunk.raw_data.extend(_PAGE_REGION)
    return [test_data.end_test_chunk()]
