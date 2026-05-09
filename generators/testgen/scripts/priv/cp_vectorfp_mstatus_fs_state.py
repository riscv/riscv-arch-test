"""Priv coverpoint handler for cp_vectorfp_mstatus_fs_state.

Emits three sub-tests of the row's vector-FP instruction, one for each
non-Off mstatus.FS state (Initial=1, Clean=2, Dirty=3) with mstatus.VS=Dirty.
Each sub-test runs to completion (no expected trap) so the data SIGUPD is
preserved.
"""

from __future__ import annotations

from random import seed as set_seed

import vector_testgen_common as common
from priv_coverpoint_registry import register

from ._mstatus_helpers import run_under_fs_vs

CP = "cp_vectorfp_mstatus_fs_state"

_FS_NAMES = {1: "initial", 2: "clean", 3: "dirty"}


@register(CP)
def make_vectorfp_mstatus_fs_state(instruction: str) -> None:
    set_seed(common.myhash(instruction + CP))
    for fs, name in _FS_NAMES.items():
        run_under_fs_vs(instruction, CP, fs=fs, vs=3, skip_sigupd=False, sub_label=f"FS={name}")
