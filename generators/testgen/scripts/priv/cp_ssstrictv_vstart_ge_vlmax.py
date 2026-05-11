"""cp_ssstrictv_vstart_ge_vlmax: vstart >= VLMAX is reserved.

Cross requires (after fix from ins.trap → mcause==2):
``vstart_ge_vlmax``, ``vtype_valid``, ``trap_occurred(mcause==2)``.

We set up vill=0 with a small VLMAX, force vstart >= VLMAX, then issue the
instruction. The illegal-instruction trap is detected via mcause.
"""

from __future__ import annotations

from random import seed as set_seed

import vector_testgen_common as common
from priv_coverpoint_registry import register
from ._ssstrictv_helpers import (build_testline, init_operand_regs, lmul_flag,
                                 sig_params)

CP = "cp_ssstrictv_vstart_ge_vlmax"


@register(CP)
def make(instruction: str) -> None:
    from ._ssstrictv_helpers import SKIP_COVERPOINTS
    if CP in SKIP_COVERPOINTS:
        # See simulator-issues/003-vstart-ge-vlmax-no-trap.md
        return
    set_seed(common.myhash(instruction + CP))
    sew = common.getInstructionEEW(instruction) or common.minSEW_MIN
    lmul = 1

    instruction_data = common.randomizeVectorInstructionData(
        instruction, sew, common.getBaseSuiteTestCount(),
        vd_val_pointer="vector_random",
        vs2_val_pointer="vector_random",
        vs1_val_pointer="vector_random",
    )
    common.remapPrivScalarRegs(instruction_data, instruction)

    common.writeLine(f"\n# Testcase {CP}")
    scratch = common.pickPrivScratch(instruction_data[1])
    # Establish a known small VLMAX (vl=1, eSEW, m1) and initialize operands.
    common.writeLine(f"vsetivli x{scratch}, 1, e{sew}, {lmul_flag(lmul)}, tu, mu",
                     "# vill=0, vstart=0, vl=1, m1")
    init_operand_regs(instruction, instruction_data[0], sew, scratch)
    # Re-emit vsetivli RIGHT BEFORE writing vstart so SAMPLE_BEFORE on the
    # test instruction picks up the (vtype, vl, vstart) we just configured.
    common.writeLine(f"vsetivli x{scratch}, 1, e{sew}, {lmul_flag(lmul)}, tu, mu",
                     "# repeat: ensure prior-insn snapshot has vill=0, vl=1")
    # Force vstart >= VLMAX. Use 0x7FF (2047): wider than any plausible VLMAX
    # for the configured vtype, but not a power-of-two boundary that would
    # alias to 0 when masked to vstart's actual width (e.g. for VLEN=1024
    # vstart is 10 bits and writing 0x800 aliases to 0).
    common.writeLine(f"li x{scratch}, 0x7FF", "# very large vstart, >= VLMAX")
    common.writeLine(f"csrw vstart, x{scratch}", "# vstart >= VLMAX (reserved)")

    testline, vd, rd = build_testline(instruction, instruction_data)
    sig_lmul, sig_wr = sig_params(instruction, instruction_data, lmul=lmul)

    common.add_testcase_string(CP, instruction)
    common.writeVecTest(
        instruction, CP, vd, sew, testline,
        test=instruction, rd=rd, vl=1, lmul=lmul,
        sig_lmul=sig_lmul, sig_whole_register_store=sig_wr,
        priv=True, skip_sigupd=True,
    )
