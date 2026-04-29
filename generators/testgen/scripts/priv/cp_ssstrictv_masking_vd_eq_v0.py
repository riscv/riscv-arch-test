"""cp_ssstrictv_masking_vd_eq_v0: vd=v0 with mask enabled (vm=0) at LMUL=1.

Cross: ``std_trap_vec, vtype_lmul_1, vd_is_v0_meqv0(=v0), mask_enabled(vm=0)``.
The instruction need not actually trap; the cross only requires the encoding
bits and the trap-eligible vtype/vstart/vl/mstatus pre-state.
"""

from __future__ import annotations

from priv_coverpoint_registry import register
from ._ssstrictv_helpers import issue_simple_test

CP = "cp_ssstrictv_masking_vd_eq_v0"


@register(CP)
def make(instruction: str) -> None:
    issue_simple_test(instruction, CP, lmul=1, override_vd=0, maskval="v0.t",
                      skip_sigupd=True)
