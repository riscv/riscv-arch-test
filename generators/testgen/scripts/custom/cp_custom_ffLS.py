# SPDX-License-Identifier: BSD-3-Clause
"""Custom coverpoint: cp_custom_ffLS

Template cross: std_vec × ffLS_vtype_lmul_2 × ffLS_vl_max × ffLS_mask_enabled
                × ffLS_v0_eq_2 × ffLS_rs1_at_fault_addr

Requires: LMUL=2, vl=VLMAX, masking enabled (vm=0), v0=2,
rs1 = RVMODEL_ACCESS_FAULT_ADDRESS (0x0).

Fault-only-first load with rs1 pointing to a known faulting address.
Element 0 is masked OFF (v0 bit 0 = 0), element 1 is active (v0 bit 1 = 1).
Per V spec §7.7: element 0 doesn't access memory (masked), element 1+ faults
at the fault address → vl is trimmed to 1 rather than trapping.
"""

from __future__ import annotations

import re

from coverpoint_registry import register
from vector_testgen_common import (
    getBaseSuiteTestCount,
    getLmulFlag,
    incrementBasetestCount,
    randomizeVectorInstructionData,
    vsAddressCount,
    writeTest,
)

FAULT_ADDRESS = 0  # matches RVMODEL_ACCESS_FAULT_ADDRESS in config


def _get_eew(instruction: str) -> int | None:
    """Get EEW from instruction name (e.g., vlseg3e64ff.v → 64)."""
    m = re.search(r"e(\d+)", instruction.split("seg")[-1] if "seg" in instruction else instruction)
    return int(m.group(1)) if m else None


def _get_nf(instruction: str) -> int:
    """Get nfields from segmented instruction name. Returns 1 if not segmented."""
    m = re.search(r"seg(\d+)", instruction)
    return int(m.group(1)) if m else 1


@register("cp_custom_ffLS")
def make(test: str, sew: int) -> None:
    lmul = 2

    eew = _get_eew(test)
    emul = (eew * lmul // sew) if eew is not None else lmul
    nf = _get_nf(test)
    if emul * nf > 8:
        return

    description = f"cp_custom_ffLS ({test}, lmul=2, vl=vlmax, masked, v0=2, rs1=fault_addr)"
    try:
        data = randomizeVectorInstructionData(
            test,
            sew,
            getBaseSuiteTestCount(),
            lmul=lmul,
            additional_no_overlap=[["vd", "v0"]],
        )
        rs1 = int(data[1]["rs1"]["reg"])

        lmulflag = getLmulFlag(lmul)
        # Set v0=2 (bit 0=0 masks element 0, bit 1=1 activates element 1)
        # This ensures element 0 does NOT access the fault address (no trap),
        # while element 1+ are active and fault → vl trimmed.
        # {s0} is allocated by writeTest via pre_test_scratch_regs (centralized
        # allocation avoids collision with a switched sigReg).
        pre_lines = [
            "vsetivli x0, 1, e8, m1, tu, mu",
            "vmv.v.i v0, 2",
            f"vsetvli x{{s0}}, x0, e{sew}, m{lmulflag}, tu, mu",
        ]
        pre_inst_lines = [
            f"li x{rs1}, {FAULT_ADDRESS}",
        ]
        writeTest(
            description, test, data,
            sew=sew, lmul=lmul, vl="vlmax",
            maskval="zeroes", pre_test_lines=pre_lines,
            pre_instruction_lines=pre_inst_lines,
            pre_test_scratch_regs=1,
        )
        incrementBasetestCount()
        vsAddressCount()
    except ValueError:
        pass
