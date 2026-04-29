"""Priv coverpoint handler for cp_mstatus_fs_off.

Emits a single test of the row's vector-FP instruction with mstatus.FS = Off
and mstatus.VS = Dirty. The instruction must trap with illegal-instruction;
the data SIGUPD is skipped because the test always traps -- the trap-handler
signature is what proves the coverpoint hit on cross-model comparison.
"""

from __future__ import annotations

from random import seed as set_seed

import vector_testgen_common as common
from priv_coverpoint_registry import register

from ._mstatus_helpers import run_under_fs_vs

CP = "cp_mstatus_fs_off"


@register(CP)
def make_mstatus_fs_off(instruction: str) -> None:
    set_seed(common.myhash(instruction + CP))
    run_under_fs_vs(instruction, CP, fs=0, vs=3, skip_sigupd=True)
