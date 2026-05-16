"""Priv coverpoint handler for cp_vectorfp_mstatus_fs_state_affecting_csr.

This coverpoint is intentionally empty in coverage SV (see the matching
template) because the spec permits a legal always-Dirty mstatus.FS
implementation, making the FS transition unobservable in pure functional
coverage. The test sequence is still emitted here so that a transitioning
model can be cross-checked against an always-Dirty model via signature
comparison.

We exercise the row's instruction at mstatus.FS=Initial (1) and FS=Clean (2)
with VS=Dirty.
"""

from __future__ import annotations

from random import seed as set_seed

import vector_testgen_common as common
from priv_coverpoint_registry import register

from ._mstatus_helpers import run_under_fs_vs

CP = "cp_vectorfp_mstatus_fs_state_affecting_csr"


@register(CP)
def make_vectorfp_mstatus_fs_state_affecting_csr(instruction: str) -> None:
    set_seed(common.myhash(instruction + CP))
    for fs, name in ((1, "initial"), (2, "clean")):
        run_under_fs_vs(instruction, CP, fs=fs, vs=3, skip_sigupd=False, sub_label=f"FS={name}")
