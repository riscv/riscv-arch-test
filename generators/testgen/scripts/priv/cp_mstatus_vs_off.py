"""Priv coverpoint handler for cp_mstatus_vs_off.

Emits a single test of the row's vector-FP instruction with mstatus.VS = Off
and mstatus.FS = Dirty. The instruction must trap with illegal-instruction;
the data SIGUPD is skipped because the test always traps -- the trap-handler
signature is what proves the coverpoint hit on cross-model comparison.
"""

from __future__ import annotations

from random import seed as set_seed

import vector_testgen_common as common
from priv_coverpoint_registry import register

from ._mstatus_helpers import run_under_fs_vs

CP = "cp_mstatus_vs_off"


@register(CP)
def make_mstatus_vs_off(instruction: str) -> None:
    set_seed(common.myhash(instruction + CP))
    run_under_fs_vs(instruction, CP, fs=3, vs=0, skip_sigupd=True)
