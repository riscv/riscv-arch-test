"""Priv coverpoint handler for cp_exceptionsv_LS.

Generates tests that execute vector load/store instructions under standard
trap-valid conditions (vill=0, vstart=0, vl>0, mstatus.vs!=0).
"""

from __future__ import annotations

from random import randrange, seed as set_seed

import vector_testgen_common as common
from priv_coverpoint_registry import register

CP = "cp_exceptionsv_LS"


def _build_testline(instruction: str, instruction_data: list, maskval: str | None = None) -> tuple[str, int, int]:
    """Build the assembly test line and return (testline, vd_reg, rd_reg)."""
    args = common.getInstructionArguments(instruction)
    vec_data, scalar_data, fp_data, imm_val = instruction_data

    testline = instruction + " "
    for arg in args:
        if arg == "vm":
            if maskval is not None:
                testline += "v0.t"
            else:
                testline = testline[:-2]
        elif arg == "v0":
            testline += "v0"
        elif arg == "imm":
            testline += f"{imm_val}"
        elif arg[0] == "v":
            testline += f"v{vec_data[arg]['reg']}"
        elif arg[0] == "r":
            if arg == "rs1" and instruction in common.vector_ls_ins:
                # Use random_mask_0 as valid address (vector_ls_random_base
                # isn't available in priv tests). The randomly chosen rs1
                # holds the address.
                reg = scalar_data[arg]["reg"]
                common.writeLine(f"la x{reg}, random_mask_0", "# rs1 = valid memory address")
                testline += f"(x{reg})"
            else:
                common.loadScalarReg(arg, scalar_data)
                testline += f"x{scalar_data[arg]['reg']}"
        elif arg[0] == "f":
            testline += f"f{fp_data[arg]['reg']}"
        else:
            raise TypeError(f"Unsupported argument type: '{arg}'")
        testline += ", "

    testline = testline[:-2]  # strip trailing ", "

    # clang's RV32 frontend rejects indexed-segment ei{32,64} mnemonics
    # ("requires RV64I"); emit raw `.insn` encoding to force assembly.
    if instruction in common.indexed_ls_ins:
        testline = common.encodeIndexedLSAsInsn(instruction, instruction_data,
                                                masked=(maskval is not None))

    vd = vec_data["vd"]["reg"]
    rd = scalar_data["rd"]["reg"]
    return testline, vd, rd


def _sig_params(instruction: str, instruction_data: list, lmul: int = 1) -> tuple[int, bool]:
    """Determine sig_lmul and sig_whole_register_store."""
    vec_data = instruction_data[0]
    if vec_data["vd"]["reg_type"] in ("mask", "scalar"):
        return 1, True
    if instruction in common.whole_register_move:
        return common.getLengthLmul(instruction), True
    return lmul, False


def _emit_setup(instruction: str, instruction_data: list, sew: int) -> int:
    """Emit vsetivli + vd/vs2/vs3 initialization. Returns scratch reg used.

    Also initializes any scalar-FP source operand (fs1) so that downstream
    flows (e.g. mstatus.FS state tests) that call this helper while FS=Dirty
    leave the scalar FP source holding the generator-expected bit pattern
    before FS is reprogrammed. Without this, a vfX.vf row reads an
    uninitialized f-reg whose value disagrees with the golden signature.
    """
    vec_data, scalar_data, fp_data, _ = instruction_data
    scratch = common.pickPrivScratch(scalar_data)
    args = common.getInstructionArguments(instruction)
    vd_reg  = vec_data["vd"]["reg"]
    vs2_reg = vec_data["vs2"]["reg"]
    vs3_reg = vec_data["vs3"]["reg"]
    vs1_reg = vec_data["vs1"]["reg"] if "vs1" in vec_data else None
    # For widening instructions vd EEW = 2*SEW. Initialize vd at that EEW so the
    # destination element is fully written by the load (otherwise the upper half
    # of vd holds whatever boot-time garbage the model left there, producing
    # non-deterministic signature values when the test instruction itself
    # traps and leaves vd unchanged).
    vd_sew = sew * 2 if instruction in common.vd_widen_ins else sew
    vs2_sew = sew * 2 if instruction in common.vs2_widen_ins else sew
    # Widening reductions (wvsins / fwvsins) read vs1[0] at 2*SEW (the widened
    # accumulator). Initialize vs1 at that EEW so the upper half is not boot-time
    # garbage — otherwise the signature differs from the generator's expected value.
    vs1_sew = sew * 2 if instruction in common.wvsins else sew
    common.writeLine(f"la x{scratch}, random_mask_0", "# valid data address")
    if "vd" in args:
        common.writeLine(f"vsetivli x0, 1, e{vd_sew}, m1, tu, mu", "# init vd at vd EEW")
        common.writeLine(f"vle{vd_sew}.v v{vd_reg}, (x{scratch})", f"# initialize vd (v{vd_reg})")
    if "vs2" in args:
        common.writeLine(f"vsetivli x0, 1, e{vs2_sew}, m1, tu, mu", "# init vs2 at vs2 EEW")
        common.writeLine(f"vle{vs2_sew}.v v{vs2_reg}, (x{scratch})", f"# initialize vs2 (v{vs2_reg})")
    if "vs1" in args and vs1_reg is not None and vs1_sew != sew:
        common.writeLine(f"vsetivli x0, 1, e{vs1_sew}, m1, tu, mu", "# init vs1 at vs1 EEW")
        common.writeLine(f"vle{vs1_sew}.v v{vs1_reg}, (x{scratch})", f"# initialize vs1 (v{vs1_reg})")
    common.writeLine(f"vsetivli x0, 1, e{sew}, m1, tu, mu", "# vill=0, vstart=0, vl=1")
    if "vs3" in args:
        common.writeLine(f"vle{sew}.v v{vs3_reg}, (x{scratch})", f"# initialize vs3 (v{vs3_reg})")
    if "vs1" in args and vs1_reg is not None and vs1_sew == sew:
        common.writeLine(f"vle{sew}.v v{vs1_reg}, (x{scratch})", f"# initialize vs1 (v{vs1_reg})")
    # Indexed LS: vs2 holds byte offsets from rs1 (random_mask_0). The vle above
    # left vs2 holding random data, which produces huge byte offsets that land
    # outside mapped memory and trap as load/store access fault. Replace vs2[0]
    # with a small sew-aligned random offset so the access stays inside the
    # random_mask data region. Mirrors the (-2*vlmax, 2*vlmax) sew-aligned
    # bound that unpriv applies via vand/vrem on the loaded indices. vl=1 here,
    # so vmv.v.x writes only vs2[0] (the only element the test reads).
    if "vs2" in args and instruction in common.indexed_ls_ins:
        sew_bytes = max(sew // 8, 1)
        small_idx = randrange(0, 8) * sew_bytes
        common.writeLine(f"li x{scratch}, {small_idx}", "# small sew-aligned index offset")
        common.writeLine(f"vmv.v.x v{vs2_reg}, x{scratch}", f"# vs2[0] = small index into random_mask_0")
    # Initialize scalar-FP source operands (fs1) so the test instruction
    # reads a known bit pattern. Must run while mstatus.FS is writable
    # (Dirty); the FS-state runner sets FS=Dirty before calling us.
    # Pass the priv framework's reserved scalar regs (sigReg/x2, SIGUPD
    # temp/x4, SIGUPD link/x5, gp/x3, ra/x1) plus any X-operand registers so
    # loadFloatReg's scratch picks never clobber them. Without this, the
    # scratch picker would happily pick x2 (sigReg) and emit `LA(x2, scratch)`,
    # corrupting the signature pointer for the rest of the test file.
    operand_regs = [
        scalar_data[k]["reg"]
        for k in ("rd", "rs1", "rs2")
        if scalar_data.get(k) and scalar_data[k].get("reg") is not None
    ]
    reserved_for_fp = list(common.PRIV_RESERVED_SCALAR_REGS) + operand_regs
    # FP scalar precision comes from the priv suite's FP SEW (e.g. ExceptionsVf16=16),
    # not the vector SEW: arithmetic FP instructions have no eew_ins entry, so the
    # caller's `sew` falls back to minSEW_MIN=8, which has no flh/flw/fld mapping.
    fp_sew = common.getPrivFpSew() or sew
    for fp_arg in ("fs1", "fs2", "fs3"):
        if fp_arg in args and fp_arg in fp_data and fp_data[fp_arg].get("reg") is not None:
            common.loadFloatReg(fp_sew, fp_arg, fp_data, *reserved_for_fp)
    return scratch


@register(CP)
def make_exceptionsv_LS(instruction: str) -> None:
    """Execute LS instruction normally under std_trap_vec conditions."""
    set_seed(common.myhash(instruction + CP))

    # Use SEW=EEW so EMUL=LMUL=1, avoiding register overlap issues
    eew = common.getInstructionEEW(instruction) or common.minSEW_MIN
    sew = eew

    instruction_data = common.randomizeVectorInstructionData(
        instruction, sew, common.getBaseSuiteTestCount(),
        vd_val_pointer="vector_random",
        vs2_val_pointer="vector_random",
        vs1_val_pointer="vector_random",
    )
    common.remapPrivScalarRegs(instruction_data, instruction)

    common.writeLine(f"\n# Testcase {CP}")
    _emit_setup(instruction, instruction_data, sew)

    testline, vd, rd = _build_testline(instruction, instruction_data)
    sig_lmul, sig_wr = _sig_params(instruction, instruction_data)

    # Stores have no architectural vd to compare; the vd used for SIGUPD here is
    # a random unused vector register and would fail comparison non-deterministically.
    # Skip the per-test data SIGUPD for stores -- the trap-handler signature still
    # records trap-vs-no-trap behavior cross-model.
    skip = instruction in common.vector_stores
    common.add_testcase_string(CP, instruction)
    common.writeVecTest(
        instruction, CP, vd, sew, testline,
        test=instruction, rd=rd, vl=1, sig_lmul=sig_lmul,
        sig_whole_register_store=sig_wr, priv=True, skip_sigupd=skip,
    )
