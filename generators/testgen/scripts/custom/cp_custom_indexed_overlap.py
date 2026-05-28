# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_indexed_overlap_eew{8,16,32,64}

Covers legal vd/vs2 (load) or vs3/vs2 (store) register-group overlap for
NON-SEGMENT indexed loads/stores per V-spec §5.2:
  (a) EEW_dest == EEW_src                -> any overlap legal
  (b) EEW_dest <  EEW_src                -> overlap in LOWEST part of source group
  (c) EEW_dest >  EEW_src, EMUL_src >= 1 -> overlap in HIGHEST part of dest group

Indexed loads: dest = vd (EEW=SEW), src = vs2 (EEW=index EEW).
Indexed stores: vs3 and vs2 are both sources, so vs3 == vs2 is only legal
when SEW == index EEW (else a single register would be read at two EEWs).

V-spec norm:vector_ls_seg_indexed_vreg_rsv reserves any vd/vs2 overlap for
indexed SEGMENT loads, so those are excluded here.
"""

import math
from functools import partial

from coverpoint_registry import register
from vector_testgen_common import (
    getBaseSuiteTestCount,
    getInstructionEEW,
    incrementBasetestCount,
    indexed_loads,
    indexed_stores,
    randomizeVectorInstructionData,
    segment_loads,
    vreg_count,
    vsAddressCount,
    writeTest,
)


def _aligned_bases(align: int, footprint: int):
    """All multiples of *align* such that base..base+footprint-1 fits in vreg_count."""
    max_start = vreg_count - footprint
    if max_start < 0:
        raise ValueError("footprint exceeds register file")
    return range(0, max_start + 1, align)


def _emit(test: str, sew: int, lmul: int, label: str, **reg_overrides) -> None:
    pretty = ", ".join(f"{k}=v{v}" for k, v in reg_overrides.items())
    description = f"{label} ({test}, sew={sew}, lmul={lmul}, {pretty})"
    try:
        data = randomizeVectorInstructionData(
            test,
            sew,
            getBaseSuiteTestCount(),
            lmul=lmul,
            **reg_overrides,
        )
    except (ValueError, KeyError):
        return
    writeTest(description, test, data, sew=sew, lmul=lmul, vl=1)
    incrementBasetestCount()
    vsAddressCount()


def _make(test: str, sew: int, expected_eew: int) -> None:
    K = getInstructionEEW(test)
    if K is None or K != expected_eew:
        return
    if test in segment_loads:
        return
    if test not in indexed_loads and test not in indexed_stores:
        return

    N = sew
    is_store = test in indexed_stores

    for lmul in (1, 2, 4, 8):
        data_emul = lmul  # non-segment indexed: data EMUL == LMUL
        if K * lmul > 8 * N:
            continue  # index EMUL > 8 not allowed

        if K == N:
            # Rule (a): full overlap legal.
            for base in _aligned_bases(lmul, lmul):
                if is_store:
                    _emit(test, sew, lmul, "cp_custom_indexed_overlap_ruleA",
                          vs3=base, vs2=base)
                else:
                    _emit(test, sew, lmul, "cp_custom_indexed_overlap_ruleA",
                          vd=base, vs2=base)

        elif K > N:
            # Rule (b): dest at LOWEST of source group -> vd == vs2.
            # Stores: vs3 != vs2 required when K != N.
            if is_store:
                continue
            src_emul = (K * lmul) // N
            align = math.lcm(src_emul, data_emul)
            try:
                bases = _aligned_bases(align, src_emul)
            except ValueError:
                continue
            for base in bases:
                _emit(test, sew, lmul, "cp_custom_indexed_overlap_ruleB",
                      vd=base, vs2=base)

        else:  # K < N
            # Rule (c): src at HIGHEST of dest group. EMUL_src must be >= 1.
            if is_store:
                continue
            if K * lmul < N:
                continue
            src_emul = (K * lmul) // N
            vs2_offset = data_emul - src_emul
            if vs2_offset <= 0 or vs2_offset % src_emul != 0:
                continue
            try:
                bases = _aligned_bases(data_emul, data_emul)
            except ValueError:
                continue
            for base in bases:
                _emit(test, sew, lmul, "cp_custom_indexed_overlap_ruleC",
                      vd=base, vs2=base + vs2_offset)


for _K in (8, 16, 32, 64):
    register(f"cp_custom_indexed_overlap_eew{_K}")(partial(_make, expected_eew=_K))
