# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_indexed_emul_data_only

Verify EMUL*NFIELDS <= 8 constraint applies to data register group only.
Test at data LMUL*NFIELDS = 8 boundary.

Template has a single cross: std_vec × nf_lmul_at_boundary.
The nf_lmul_at_boundary coverpoint checks a combined condition:
  NF=2 at LMUL=4, NF=4 at LMUL=2, or NF=8 at LMUL=1.
"""

from coverpoint_registry import register
import vector_testgen_common as common
from vector_testgen_common import (
    writeTest,
    randomizeVectorInstructionData,
    incrementBasetestCount,
    getBaseSuiteTestCount,
    vsAddressCount,
    eew8_ins,
    eew16_ins,
    eew32_ins,
    eew64_ins,
)

import re


def _get_nfields(instruction: str) -> int:
    """Extract NFIELDS from segmented instruction name (e.g., vluxseg4ei8.v → 4)."""
    m = re.search(r'seg(\d+)', instruction)
    return int(m.group(1)) if m else 1


def _get_index_eew(instruction: str) -> int | None:
    """Get the index element width from the instruction name."""
    if instruction in eew64_ins:
        return 64
    if instruction in eew32_ins:
        return 32
    if instruction in eew16_ins:
        return 16
    if instruction in eew8_ins:
        return 8
    return None


def _make(test: str, sew: int, min_sew: int = 0) -> None:
    # Gate for _sew_ge{N} variants: CSV framework appends e.g. "sew_ge16" to the
    # column name, producing cp_custom_indexed_emul_data_only_sew_ge16. The
    # coverage generator strips the suffix from the covergroup template, but the
    # testgen registry sees the full name — so one handler per variant gates SEW.
    if sew < min_sew:
        return

    nf = _get_nfields(test)
    targets = {8: 1, 4: 2, 2: 4}  # nf → required lmul

    if nf not in targets:
        return

    lmul = targets[nf]

    # Check index EMUL legality at the required LMUL
    index_eew = _get_index_eew(test)
    if index_eew is not None:
        index_emul = index_eew * lmul // sew
        if index_emul > 8:
            return

    description = f"cp_custom_indexed_emul_data_only ({test}, lmul={lmul}, nf={nf})"
    try:
        data = randomizeVectorInstructionData(
            test, sew, getBaseSuiteTestCount(), lmul=lmul,
        )
    except ValueError:
        return
    writeTest(description, test, data, sew=sew, lmul=lmul, vl=1)
    incrementBasetestCount()
    vsAddressCount()


register("cp_custom_indexed_emul_data_only")(lambda test, sew: _make(test, sew))
for _min in (16, 32, 64):
    register(f"cp_custom_indexed_emul_data_only_sew_ge{_min}")(
        (lambda m: lambda test, sew: _make(test, sew, min_sew=m))(_min)
    )
