"""cp_ssstrictv_masking_vd_eq_v0: vd=v0 with mask enabled (vm=0) at LMUL=1.

Cross: ``std_trap_vec, vtype_lmul_1, vd_is_v0_meqv0(=v0), mask_enabled(vm=0)``.
The instruction need not actually trap; the cross only requires the encoding
bits and the trap-eligible vtype/vstart/vl/mstatus pre-state.

Round-robins SEW across {8,16,32,64} so the inherited ``vtype_all_sew_supported``
coverpoint also fires for sixteen/thirtytwo/sixtyfour bins.
"""

from __future__ import annotations

import vector_testgen_common as common
from priv_coverpoint_registry import register
from ._ssstrictv_helpers import issue_simple_test, make_dest_zero_overrides

CP = "cp_ssstrictv_masking_vd_eq_v0"


@register(CP)
def make(instruction: str) -> None:
    eew = common.getInstructionEEW(instruction)
    sews = [eew] if eew else [8, 16, 32, 64]
    for sew in sews:
        issue_simple_test(instruction, CP, sew=sew, lmul=1, maskval="v0.t",
                          skip_sigupd=True, **make_dest_zero_overrides(instruction))

    # Auxiliary: fire the auto-included encoding-overlap helper coverpoints
    # vd_eq_vs1 / vd_eq_vs2 / vs2_eq_vs1 (defined in
    # coverpoints/general/RISCV_coverage_ssstrictv_helpers.svh). These sample
    # purely on the instruction-word register fields, so a single trap-eligible
    # encoding per overlap pattern is enough. v8 is divisible by 8 so it stays
    # aligned for every supported LMUL.
    sew = eew if eew else 8
    issue_simple_test(instruction, CP, sew=sew, lmul=1, maskval=None,
                      override_vd=8, override_vs1=8, override_vs2=16, override_vs3=8,
                      skip_sigupd=True)
    issue_simple_test(instruction, CP, sew=sew, lmul=1, maskval=None,
                      override_vd=8, override_vs1=16, override_vs2=8, override_vs3=8,
                      skip_sigupd=True)
    issue_simple_test(instruction, CP, sew=sew, lmul=1, maskval=None,
                      override_vd=24, override_vs1=8, override_vs2=8, override_vs3=24,
                      skip_sigupd=True)
