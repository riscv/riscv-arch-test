"""Shared helpers for ExceptionsVf priv coverpoints that manipulate mstatus.{FS,VS}.

The vector floating-point ExceptionsVf coverpoints all share the same
boilerplate: prepare valid vtype/vd/vs2/vs1, set mstatus.FS and mstatus.VS to
specific values, then run the row's instruction. The instruction may or may
not trap depending on the FS/VS pattern under test.

This module factors out the FS/VS manipulation and the per-instruction
testline construction (taken from cp_exceptionsv_LS) so each coverpoint
script is just a thin wrapper that picks an FS/VS pattern.
"""

from __future__ import annotations

import vector_testgen_common as common

from .cp_exceptionsv_LS import _build_testline, _emit_setup, _sig_params

_FS_MASK = 3 << 13  # mstatus.FS = bits [14:13]
_VS_MASK = 3 << 9   # mstatus.VS = bits [10:9]


def emit_set_fs_vs(fs: int, vs: int, scratch: int) -> None:
    """Force mstatus.FS=fs (0..3) and mstatus.VS=vs (0..3) using `scratch`."""
    common.writeLine(f"li x{scratch}, {_FS_MASK | _VS_MASK}", "# clear-mask FS|VS")
    common.writeLine(f"csrc mstatus, x{scratch}", "# clear FS and VS")
    common.writeLine(f"li x{scratch}, {(fs << 13) | (vs << 9)}", f"# set FS={fs} VS={vs}")
    common.writeLine(f"csrs mstatus, x{scratch}", "# write FS|VS into mstatus")


def emit_seed_misa(scratch: int) -> None:
    """Sail only emits misa to rvvi when an instruction touches it."""
    common.writeLine(f"csrr x{scratch}, misa", "# seed misa into rvvi trace")


def run_under_fs_vs(
    instruction: str,
    cp: str,
    fs: int,
    vs: int,
    *,
    skip_sigupd: bool,
    sub_label: str | None = None,
) -> None:
    """Emit one priv test of `instruction` under mstatus.FS=fs, mstatus.VS=vs.

    Setup is performed at FS=Dirty/VS=Dirty (so the vle/vfp init is legal),
    then mstatus is reprogrammed to the requested (fs, vs) just before the
    test instruction is emitted by writeVecTest. `skip_sigupd` should be
    True for cases that always trap (VS=Off, FS=Off): the trap-handler
    signature still records the trap event for cross-model comparison.
    """
    eew = common.getInstructionEEW(instruction) or common.minSEW_MIN
    sew = eew

    instruction_data = common.randomizeVectorInstructionData(
        instruction, sew, common.getBaseSuiteTestCount(),
        vd_val_pointer="vector_random",
        vs2_val_pointer="vector_random",
        vs1_val_pointer="vector_random",
    )
    common.remapPrivScalarRegs(instruction_data, instruction)

    label = cp if sub_label is None else f"{cp} ({sub_label})"
    common.writeLine(f"\n# Testcase {label}")

    # Setup needs FS=Dirty + VS=Dirty so vle/vfp init never trap.
    scratch = common.pickPrivScratch(instruction_data[1])
    emit_set_fs_vs(fs=3, vs=3, scratch=scratch)
    _emit_setup(instruction, instruction_data, sew)

    # Re-pick scratch in case _emit_setup consumed/clobbered ours.
    scratch = common.pickPrivScratch(instruction_data[1])
    emit_set_fs_vs(fs=fs, vs=vs, scratch=scratch)
    emit_seed_misa(scratch)

    testline, vd, rd = _build_testline(instruction, instruction_data)
    sig_lmul, sig_wr = _sig_params(instruction, instruction_data)
    fp_data = instruction_data[2]
    fd = fp_data["fd"]["reg"] if "fd" in fp_data else None

    # After the test instruction (which may trap and leave mstatus.{FS,VS} in a
    # state that itself traps on `csrr fcsr` / vector SIGUPD ops), restore both
    # fields to Dirty so writeVecTest's post-test fcsr save and SIGUPD blocks
    # always run cleanly.
    restore_scratch = common.pickPrivScratch(instruction_data[1])
    post_lines = [
        f"li x{restore_scratch}, {(_FS_MASK | _VS_MASK)}  # restore FS|VS = Dirty",
        f"csrs mstatus, x{restore_scratch}",
    ]

    common.add_testcase_string(cp, instruction)
    common.writeVecTest(
        instruction, cp, vd, sew, testline,
        test=instruction, rd=rd, fd=fd, vl=1, sig_lmul=sig_lmul,
        sig_whole_register_store=sig_wr, priv=True, skip_sigupd=skip_sigupd,
        post_instruction_lines=post_lines,
    )
