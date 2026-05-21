#!/usr/bin/env python3
##################################
# vector-testgen-priv.py
#
# Georgia Tai ytai@hmc.edu 26 June 2025
# SPDX-License-Identifier: Apache-2.0
#
# Generate directed privileged tests for functional coverage of the vector extension
##################################

##################################
# libraries
##################################
import filecmp
import math
import os
import pathlib
import re
from random import randint, seed

import priv  # priv coverpoint generator scripts
import vector_testgen_common as common
from priv_coverpoint_registry import PRIV_REGISTRY, import_all_modules
##################################
# SsstrictV skip table
##################################
# The (coverpoint-column, instruction) pairs that the SsstrictV pipeline
# intentionally OMITS due to simulator failures or missing generator support
# live in `ssstrictv_skip_combinations.SKIP_COMBINATIONS`.
#
# Single source of truth: generators/testgen/scripts/ssstrictv_skip_combinations.py
# That table is consumed by:
#   * the priv test generator (this file) to suppress test emission, and
#   * the coverage generator (covergroupgen/generate.py) to suppress the
#     corresponding covergroup bins so they are not counted as missing.
#
# To audit / extend the skip list, edit that module directly. Keep entries
# justified (sail issue 1104, unimplemented coverpoint, etc.).
from ssstrictv_skip_combinations import SKIP_COMBINATIONS as SSSTRICTV_SKIP_COMBINATIONS
from vector_testgen_common import (
  ARCH_VERIF,
  add_testcase_string,
  eew8_ins,
  eew16_ins,
  eew32_ins,
  eew64_ins,
  encodeIndexedLSAsInsn,
  finalizeSigupdCount,
  flen,
  genRandomVectorLS,
  genVMaskedges,
  getBaseSuiteTestCount,
  getInstructionArguments,
  getInstructionSegments,
  getLengthLmul,
  getLengthSuiteTestCount,
  getSigSpace,
  handleSignaturePointerConflict,
  indexed_ls_ins,
  insertTemplate,
  loadScalarReg,
  loadScalarAddress,
  maxVLEN,
  minSEW_MIN,
  myhash,
  narrowins,
  newInstruction,
  pickPrivScratch,
  prepVstart,
  randomizeMask,
  randomizeVectorInstructionData,
  readTestplans,
  setExtension,
  setFlen,
  setXlen,
  vd_widen_ins,
  vector_ls_ins,
  vector_stores,
  vstart_zero_required,
  whole_register_ls,
  whole_register_move,
  writeVecTest,
)


def _eew_for_instruction(instruction: str) -> int | None:
    """Return the explicit EEW (in bits) of an EEW-suffixed load/store, else None."""
    if instruction in eew64_ins:
        return 64
    if instruction in eew32_ins:
        return 32
    if instruction in eew16_ins:
        return 16
    if instruction in eew8_ins:
        return 8
    return None


def _eff_sew_for_instruction(instruction: str) -> int:
    """Effective vsetvli SEW for the priv test execution of `instruction`.

    For EEW-suffixed loads/stores we set SEW = EEW so that the data-register
    size_multiplier collapses to 1 and EMUL_eff = LMUL * NFIELDS stays small
    enough to remain architecturally legal at our randomized LMUL choices.
    All other instructions execute at SEWMIN.
    """
    eew = _eew_for_instruction(instruction)
    if eew is not None:
        return max(minSEW_MIN, eew)
    return minSEW_MIN


def _max_lmul_for_instruction(instruction: str) -> int:
    """Cap test-time LMUL so that EMUL = LMUL * size_mult * segments <= 8.

    With eff_sew = EEW for EEW-suffixed loads, the data register's
    size_multiplier collapses to 1, so EMUL_eff = LMUL * NFIELDS. Segmented
    variants are the binding case. Whole-register load/store ignore vtype LMUL
    and are pinned at 1.
    """
    if instruction in whole_register_ls:
        return 1
    segs = getInstructionSegments(instruction)
    return max(1, 8 // segs)


# Framework-reserved scalar X-registers that sigReg must NEVER be relocated into
# in the privileged vector flow. RVTEST_CODE_END's check_trap_sig_offset uses x2
# as the signature pointer and T1..T6 (x6..x11) as scratch; tempReg=x4, linkReg=x5,
# gp=x3, ra=x1, zero=x0 are also reserved. If sigReg ends up in any of these,
# either the cleanup epilog stores through a stale x2, or the cleanup's own
# T-register usage clobbers the live signature pointer.
_PRIV_RESERVED_SIGREG_FORBIDDEN = (0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11)


def resolveScalarSigConflict(instruction_arguments, scalar_register_data):
  """Priv-aware version of common.resolveScalarSigConflict.

  In addition to the test's own scalar operand registers, also force sigReg
  away from framework-reserved registers (T1..T6, tempReg, linkReg, gp, ra)
  so that the trap handler / RVTEST_CODE_END epilog does not collide with a
  live signature pointer.
  """
  scalar_regs_used = [
    scalar_register_data[a]['reg']
    for a in instruction_arguments
    if a and a[0] == 'r' and a in scalar_register_data
  ]
  handleSignaturePointerConflict(*scalar_regs_used, *_PRIV_RESERVED_SIGREG_FORBIDDEN)
  return scalar_regs_used


def writeLine(argument: str, comment = ""):
  comment_distance = 50
  tab_size = 4

  argument = (" " * tab_size * common.tab_count) + str(argument)

  if comment != "":
    padding = max(0, comment_distance - len(argument))
    comment = " " * padding + str(comment)

  f.write(argument + comment +"\n")

#####################################       test for each coverpoint      #####################################

def make_vill(instruction):
    # ============================================================
    # SPIKE-VS-SAIL DISAGREEMENT — cp_vill SKIP FOR vmv<nr>r.v
    # ------------------------------------------------------------
    # Per V-spec §16.6, the whole-register-move family vmv<nr>r.v
    # still observes vill: Spike correctly traps after we install an
    # illegal vtype, but Sail does not.
    #
    # TO RE-ENABLE cp_vill FOR vmv<nr>r.v (once Sail honors vill):
    #   Delete the `if instruction in (...): return` block below.
    # ============================================================
    if instruction in ("vmv1r.v", "vmv2r.v", "vmv4r.v", "vmv8r.v"):
        return  # noqa: cp_vill disabled for vmv<nr>r.v — see banner above
    description = "cp_vill"
    sew = _eff_sew_for_instruction(instruction)
    instruction_data = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(),
                                                      vd_val_pointer = "vector_random", vs2_val_pointer = "vector_random", vs1_val_pointer = "vector_random")

    scratch = pickPrivScratch(instruction_data[1])
    vtype_reg = pickPrivScratch(instruction_data[1], exclude=(scratch,))
    writePrivTestPrep(description, instruction, instruction_data, sew=sew, scratch=scratch)
    # Set vtype.vill by loading an explicitly-illegal vtype value (all bits
    # set, including the vill bit at XLEN-1 plus reserved fields) into a
    # register and applying it via vsetvl. Per the V spec, supplying any
    # unsupported vtype causes the implementation to set vill=1 and zero the
    # remaining vtype bits, which is well-defined for both Spike and Sail.
    # Avoid `vsetivli ..., e64, mf8` style triggers: that combination uses
    # fractional LMUL with LMUL < SEW/ELEN, which the two reference models
    # currently disagree on for follow-up instructions.
    writeLine(f"li        x{vtype_reg}, -1",                                  "# all-ones vtype, vill bit set, all other fields reserved")
    writeLine(f"vsetvl    x{scratch}, x0, x{vtype_reg}",                      "# install illegal vtype -> vill = 1")
    writePrivTestLine(instruction, instruction_data, cp="cp_vill", sew=sew)


def make_vstart(instruction, maxlmul = 8):
    # Cap LMUL for widening/narrowing instructions (EMUL = 2*LMUL must be ≤ 8)
    if instruction in vd_widen_ins or instruction in narrowins:
        maxlmul = min(maxlmul, 4)
    # Further cap for EEW-driven load/store and segmented variants so that
    # EMUL of every operand stays ≤ 8 (LMUL * size_mult * segments ≤ 8).
    maxlmul = min(maxlmul, _max_lmul_for_instruction(instruction))
    # Whole-register move (vmv<nr>r.v) is reserved when vstart >= evl, where
    # evl = NREG * VLEN/SEW. cp_vstart picks vstart in [1, vlmax) and
    # vlmax = LMUL * VLEN/SEW. Cap LMUL <= NREG so vlmax <= evl, guaranteeing
    # vstart < evl and the instruction is never reserved (testable).
    if instruction in whole_register_move:
        maxlmul = min(maxlmul, int(instruction[3]))
    vstartvals = ["one", "vlmaxm1", "vlmaxd2", "random"]
    for vstartval in vstartvals:
        if maxlmul <= 1:
            lmul = 1
        else:
            lmul = 2 ** randint(1, int(math.log2(maxlmul))) # pick random integer LMUL to ensure that coverpoints are hit

        maskval = randomizeMask(instruction)
        no_overlap = [['vs1', 'v0'], ['vs2', 'v0'], ['vd', 'v0']] if maskval is not None else None

        description = f"cp_vstart (vstart = {vstartval})"
        sew = _eff_sew_for_instruction(instruction)
        instruction_data = randomizeVectorInstructionData(instruction, sew, getLengthSuiteTestCount(), suite = "length", lmul = lmul,
                                                          vd_val_pointer = "vector_random", vs2_val_pointer = "vector_random", vs1_val_pointer = "vector_random",
                                                          additional_no_overlap=no_overlap)

        scratch = pickPrivScratch(instruction_data[1])
        scratch2 = pickPrivScratch(instruction_data[1], exclude=(scratch,))
        writePrivTestPrep(description, instruction, instruction_data, lmul = lmul, vl = "vlmax", sew=sew, scratch=scratch)
        prepVstart(vstartval, scratch=scratch, scratch2=scratch2)
        writePrivTestLine(instruction, instruction_data, cp="cp_vstart", lmul = lmul, vl = "vlmax", sew=sew, maskval = maskval)

def make_vstart_gt_vl(instruction):
    randvl = randint(1, maxVLEN)
    randvstart = randint(1, maxVLEN)
    description = "cp_vstart_gt_vl"
    sew = _eff_sew_for_instruction(instruction)
    # Cap LMUL by EMUL constraints (EEW-driven loads/stores, segmented variants).
    # Must be picked BEFORE randomizeVectorInstructionData so register selection
    # uses the correct alignment (e.g. NF=3 segmented EEW LS at lmul=2 needs even vd).
    lmul = min(4, _max_lmul_for_instruction(instruction))
    if instruction in vd_widen_ins or instruction in narrowins:
        lmul = min(lmul, 4)
    instruction_data = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), lmul = lmul,
                                                      vd_val_pointer = "vector_random", vs2_val_pointer = "vector_random", vs1_val_pointer = "vector_random")

    # a0 (x10) and a1 (x11) are used by the cp_vstart_gt_vl_setup helper for vl/vstart
    # inputs and are clobbered on return; exclude them from the scratch candidate set.
    # Note: sigReg is also kept out of x10/x11 by the priv resolveScalarSigConflict
    # forbidden-set, so no extra save/restore around the helper call is needed.
    scratch = pickPrivScratch(instruction_data[1], exclude=(10, 11))
    scratch2 = pickPrivScratch(instruction_data[1], exclude=(10, 11, scratch))
    scratch3 = pickPrivScratch(instruction_data[1], exclude=(10, 11, scratch, scratch2))
    writePrivTestPrep(description, instruction, instruction_data, lmul = lmul, vl = "vlmax", vstart = True, sew=sew, scratch=scratch)

    # Inline vstart > vl > 0 setup using the test's eff_sew/lmul so VLMAX > vstart > vl > 0
    # holds with the test's vtype (the shared cp_vstart_gt_vl_setup helper hardcodes
    # e8/m4 and a follow-up vsetvli can clip vl such that vstart >= VLMAX, breaking
    # cp_vstart_gt_vl which requires VLMAX > vstart). Algorithm:
    #   VLMAX = vsetvli(e{sew}, m{lmul})
    #   vl     = (rand_vl mod (VLMAX-2)) + 1                  in [1, VLMAX-2]
    #   vstart = vl + 1 + (rand_vstart mod (VLMAX-vl-1))      in [vl+1, VLMAX-1]
    # Requires VLMAX >= 3 (true for all supported VLEN/SEW/LMUL combos here since
    # VLEN >= 128 and the largest binding case is sew=64 lmul=1 NF=5 → VLMAX=2 only on
    # VLEN=128, but our configs use VLEN=1024).
    writeLine(f"vsetvli x{scratch}, x0, e{sew}, m{lmul}, tu, mu",       f"# x{scratch} = VLMAX at test vtype (e{sew}/m{lmul})")
    writeLine(f"li x{scratch2}, {randvl}",                              "# rand_vl")
    writeLine(f"addi x{scratch3}, x{scratch}, -2",                      f"# x{scratch3} = VLMAX-2")
    writeLine(f"remu x{scratch2}, x{scratch2}, x{scratch3}",            "# rand_vl mod (VLMAX-2)")
    writeLine(f"addi x{scratch2}, x{scratch2}, 1",                      f"# vl = x{scratch2} in [1, VLMAX-2]")
    writeLine(f"li a1, {randvstart}",                                   "# rand_vstart")
    writeLine(f"sub x{scratch3}, x{scratch}, x{scratch2}",              f"# x{scratch3} = VLMAX - vl")
    writeLine(f"addi x{scratch3}, x{scratch3}, -1",                     f"# x{scratch3} = VLMAX - vl - 1 (>= 1)")
    writeLine(f"remu a1, a1, x{scratch3}",                              "# rand_vstart mod (VLMAX-vl-1)")
    writeLine(f"add a1, a1, x{scratch2}",                               "# a1 = vl + (rand mod (VLMAX-vl-1))")
    writeLine("addi a1, a1, 1",                                         "# vstart = a1+1 in [vl+1, VLMAX-1]")
    writeLine(f"vsetvli x{scratch}, x{scratch2}, e{sew}, m{lmul}, tu, mu", "# set vl")
    writeLine("csrw vstart, a1",                                        "# set vstart > vl, < VLMAX")

    writePrivTestLine(instruction, instruction_data, cp="cp_vstart_gt_vl", vl = "vlmax", lmul = lmul, sew=sew)

#####################################           test generation           #####################################

def makeTest(coverpoints, instruction):
    writeLine("\n")
    writeLine("///////////////////////////////////////////")
    writeLine(f"// ExceptionsV tests for {instruction}")
    writeLine("///////////////////////////////////////////")
    for coverpoint in coverpoints:
        # Skip simulator-failure / unimplemented combinations curated in the
        # SsstrictV skip table (see ssstrictv_skip_combinations.py).
        if instruction in SSSTRICTV_SKIP_COMBINATIONS.get(coverpoint, ()):
            continue
        # produce a deterministic seed for repeatable random numbers distinct for each instruction and coverpoint
        testname = instruction + coverpoint
        hashval = myhash(testname)
        seed(hashval)

        if   ((coverpoint in ['RV32', 'RV64', 'EFFEW8', 'EFFEW16', 'EFFEW32', 'EFFEW64']) or
              ("sample" in coverpoint))                      : pass
        elif (coverpoint == "cp_vill")                       : make_vill(instruction)
        elif (coverpoint == "cp_vstart")                     : make_vstart(instruction)
        elif (coverpoint == "cp_vstart_gt_vl")               : make_vstart_gt_vl(instruction)
        elif coverpoint in PRIV_REGISTRY                     : PRIV_REGISTRY[coverpoint](instruction)
        else:
            print("Warning: " + coverpoint + " not implemented yet for " + instruction)

def _emul_lmul_str(group_size):
    # Convert an EMUL group size (number of architectural vregs) to the LMUL
    # field encoding string used by vsetvli (e.g. 1 -> "m1", 2 -> "m2", 8 -> "m8").
    # Group sizes that are not powers of two (segment NF=3,5,6,7) are clamped to
    # the smallest legal LMUL ≥ group_size so the init load covers all
    # constituent registers.
    if group_size <= 1:
        return "m1"
    if group_size <= 2:
        return "m2"
    if group_size <= 4:
        return "m4"
    return "m8"


def writePrivTestPrep(description, instruction, instruction_data=None, lmul = 1, vl = 1, vstart = False, sew = None, scratch=None):
    instruction_arguments = getInstructionArguments(instruction)
    if sew is None:
        sew = minSEW_MIN

    writeLine("\n# Testcase " + str(description))

    if (vstart):
        writeLine("csrw vstart, 0",                        "# initialize vstart  = 0 for preparing")

    if instruction_data is not None:
        if scratch is None:
            scratch = pickPrivScratch(instruction_data[1])
        vec_data = instruction_data[0]
        vd_reg  = vec_data['vd']['reg']
        vs2_reg = vec_data['vs2']['reg']
        vs1_reg = vec_data['vs1']['reg']
        # vd's SIGUPD_V_LEN comparison runs at sig_lmul (= getLengthLmul for
        # whole-register moves, otherwise = test lmul, otherwise = 1 for mask/scalar).
        # The init must cover at least sig_lmul regs of vd so the data-vector
        # comparison reads/writes hit fully-initialized state — otherwise stale
        # upper-LMUL regs differ between the SIGRUN and SELFCHECK builds (which
        # emit different vector ops in the SIGUPD_V slot), causing spurious
        # mismatches in tests that trap (cp_vill, cp_vstart_gt_vl) where the test
        # never actually runs.
        if vec_data['vd']['reg_type'] in ("mask", "scalar"):
            vd_sig_lmul = 1
        elif instruction in whole_register_move:
            vd_sig_lmul = getLengthLmul(instruction) or 1
        else:
            vd_sig_lmul = lmul if isinstance(lmul, int) else 1
        vd_emul  = max(1, int(lmul * vec_data['vd' ].get('size_multiplier', 1) * vec_data['vd' ].get('segments', 1)), vd_sig_lmul)
        vs2_emul = max(1, int(lmul * vec_data['vs2'].get('size_multiplier', 1) * vec_data['vs2'].get('segments', 1)))
        vs1_emul = max(1, int(lmul * vec_data['vs1'].get('size_multiplier', 1) * vec_data['vs1'].get('segments', 1)))
    else:
        # Backwards-compatible legacy path (should not be used by new code).
        if scratch is None:
            scratch = 8
        vd_reg, vs2_reg, vs1_reg = 8, 16, 24
        vd_emul = vs2_emul = vs1_emul = 1

    # Init each constituent vector register of every operand at LMUL=1 vl=VLMAX.
    # This fully initializes every architectural vreg the test instruction will
    # read or write, so the SIGRUN and SELFCHECK runs enter the test in
    # bit-identical state. (Initializing the operand at its full EMUL would be
    # cheaper but is unsafe in the priv flow because randomizeVectorInstructionData
    # does not always pick LMUL-aligned vector regs — e.g. widening vwadd.vv with
    # vd EMUL=8 may pick vd=v22, which is not aligned to 8 and would trap on the
    # init load.) Constituent regs that would extend past v31 are skipped — the
    # test instruction itself is also architecturally invalid in that case, and
    # we don't want the init load to emit an out-of-range vreg.
    def _emit_init(arg_name, base_reg, emul):
        if arg_name not in instruction_arguments:
            return
        writeLine(f"vsetvli x{scratch}, x0, SEWSIZE, m1, tu, mu",  f"# {arg_name} init: LMUL=1 vl=VLMAX, will iterate {emul} reg(s)")
        for i in range(emul):
            if base_reg + i > 31:
                break
            writeLine(f"la x{scratch}, random_mask_0",       "# load random vector base")
            writeLine(f"VLESEWMIN v{base_reg + i}, (x{scratch})",  f"# load to initialize {arg_name} reg #{i} (v{base_reg + i})")

    _emit_init("vd",  vd_reg,  vd_emul)
    _emit_init("vs2", vs2_reg, vs2_emul)
    _emit_init("vs1", vs1_reg, vs1_emul)

    # Restore the requested test-time vl/lmul after the init loads.
    if (vl == "vlmax"):
      writeLine(f"vsetvli x{scratch}, x0, e{sew}, m{lmul}, tu, mu",  f"# restore test vtype: vl=VLMAX, LMUL={lmul}, SEW={sew}")
    else:
      writeLine(f"vsetivli x{scratch}, {vl}, e{sew}, m{lmul}, tu, mu",  f"# restore test vtype: vl={vl}, LMUL={lmul}, SEW={sew}")

def writePrivTestLine(instruction, instruction_data, cp="cp_vill", vl=1, lmul=1, sew=None, maskval=None):
    if sew is None:
        sew = minSEW_MIN
    instruction_arguments = getInstructionArguments(instruction)
    [vector_register_data, scalar_register_data, floating_point_register_data, imm_val] = instruction_data

    # Relocate sigReg before any `li x{rd}, ...` is emitted. Without this,
    # GPR-writing vector ops (vcpop.m, vfirst.m, vmv.x.s, ...) can land on x2
    # and produce a self-colliding RVTEST_SIGUPD(x2, ..., x2).
    resolveScalarSigConflict(instruction_arguments, scalar_register_data)

    testline = instruction + " "

    for argument in instruction_arguments:
        if   argument == 'vm':
            if maskval is not None:
                testline = testline + "v0.t"
            else:
                testline = testline[:-2] # remove the ", " since there's no argument
        elif argument == 'v0':
            testline = testline + "v0"
        elif argument == 'imm':
            testline = testline + f"{imm_val}"
        elif argument[0] == 'v':
            testline = testline + f"v{vector_register_data[argument]['reg']}"
        elif argument[0] == 'r':
            if argument == "rs1" and instruction in vector_ls_ins:
                loadScalarAddress(argument, scalar_register_data)
                testline = testline + f"(x{scalar_register_data[argument]['reg']})"
            else:
                loadScalarReg(argument, scalar_register_data)
                testline = testline + f"x{scalar_register_data[argument]['reg']}"
        elif argument[0] == 'f':
            testline = testline + f"f{floating_point_register_data[argument]['reg']}"
        else:
            raise TypeError(f"Instruction Argument type not supported: '{argument}'")

        testline = testline + ", "

    testline = testline[:-2] # remove the ", " at the end of the test

    # clang's RV32 frontend rejects indexed-segment ei{32,64} mnemonics
    # ("requires RV64I"); emit raw `.insn` encoding to force assembly.
    if instruction in indexed_ls_ins:
        testline = encodeIndexedLSAsInsn(instruction, instruction_data,
                                         masked=(maskval is not None))

    if vector_register_data['vd']['reg_type'] == "mask" or vector_register_data['vd']['reg_type'] == "scalar":
        sig_whole_register_store = True
        sig_lmul = 1
    elif instruction in whole_register_move:
        sig_whole_register_store = True
        sig_lmul= getLengthLmul(instruction) # will return <nf> for whole register moves
    else:
        sig_whole_register_store = False
        sig_lmul = lmul


    vd = vector_register_data ['vd'] ['reg']
    rd = scalar_register_data ['rd'] ['reg']
    fd = floating_point_register_data['fd']['reg'] if 'fd' in floating_point_register_data else None

    add_testcase_string(cp, instruction)
    # The data-vector SIGUPD_V is meaningless and actively harmful for tests
    # that *always* trap, because:
    #   1. The test instruction never executes, so vd contents are irrelevant.
    #   2. The SIGUPD_V macro itself emits different vector ops in SIGRUN vs
    #      SELFCHECK builds (vse vs vle+vmsne+blt). When vd is unaligned to
    #      sig_lmul, those vector ops trap on different instructions in the
    #      two builds, producing different mepc/mcause values and a spurious
    #      trap_signature mismatch.
    # The trap handler's TRAP_SIGUPD emissions (mvect/mcause/mepc/mtval) still
    # run regardless of skip_sigupd, so we still verify trap correctness —
    # which is the entire coverage goal for these always-trapping cases.
    #
    # Always-trapping cases:
    #   - cp_vill: vill=1 forces illegal-instruction on every test.
    #   - cp_vstart_gt_vl: vstart > vl is reserved → illegal.
    #   - cp_vstart on vstart_zero_required: spec marks vstart!=0 reserved.
    #   - cp_vstart on vector_stores: stores have no architectural vd; the
    #     SIGUPD_V vd is a random unused reg, comparison non-deterministic.
    # whole_register_move (vmv<nr>r.v): per V spec reserved only when
    # vstart >= evl (= NREG*VLEN/SEW). make_vstart caps LMUL <= NREG so
    # vlmax <= evl and the cp_vstart picks (vstart < vlmax) always satisfy
    # vstart < evl -- the instruction executes legally and SIGUPD_V is valid.
    skip_sigupd = (
        cp in ("cp_vill", "cp_vstart_gt_vl")
        or (cp == "cp_vstart" and instruction in vector_stores)
        or (cp == "cp_vstart" and instruction in vstart_zero_required)
    )
    writeVecTest(instruction, cp, vd, sew, testline, test=instruction, rd=rd, fd=fd, vl=vl, lmul=lmul, sig_lmul=sig_lmul, sig_whole_register_store=sig_whole_register_store, priv=True, force_vill=(cp == "cp_vill"), skip_sigupd=skip_sigupd)



#####################################                main                 #####################################

if __name__ == '__main__':
    common.writeLine        = writeLine
    common.mtrap_sig_count  = 2000  # TODO: check if hard code
    signatureWords          = 10000  # TODO: check if hard code


    author = "David_Harris@hmc.edu"
    xlens = [32, 64]
    maxXLEN = 64
    numrand = 3
    corners = []
    fcorners = []

    # setup
    seed(0) # make tests reproducible

    import_all_modules(priv)

    testplans = readTestplans(priv=True)
    extensions = list(testplans.keys())

    for xlen in xlens:
      for extension in extensions:
        setExtension(extension)
        setXlen(xlen)

        # Filter instructions to only those marked for this xlen
        all_instructions = list(testplans[extension].keys())
        instructions = [inst for inst in all_instructions if f"RV{xlen}" in testplans[extension][inst]]

        # Per-SEW filtering for vector-FP test suites. Mirrors the unpriv driver:
        # ExceptionsVf{16,32,64} share one ExceptionsVf.csv; the driver filters
        # to instructions marked EFFEW{N}. ExceptionsVfmin runs at SEW=16 (the
        # only SEW where vfwcvt.f.f.v / vfncvt.f.f.w exercise the Zvfhmin
        # FP16<->FP32 conversion). SEW=8 is reserved for vector FP and is
        # excluded by the absence of EFFEW8 marks in the CSVs.
        sew_match = re.search(r"ExceptionsVf(\d+)$", extension)
        if sew_match:
            file_sew = int(sew_match.group(1))
        elif extension == "ExceptionsVfmin":
            file_sew = 16
        else:
            file_sew = None
        if file_sew is not None:
            effewcp = f"EFFEW{file_sew}"
            instructions = [inst for inst in instructions if effewcp in testplans[extension][inst]]
        common.setPrivFpSew(file_sew)
        # Initialize flen so loadFloatReg / FP value formatting work correctly
        # when priv coverpoints (e.g. cp_vectorfp_mstatus_fs_state) need to
        # preload a scalar-FP source. Without this, flen=0 makes the random
        # FP value 0 and the hex format string empty. Mirror the unpriv
        # vfloat path: scalar FLEN is 32 by default and only widens to 64
        # when SEW=64 selects FD; SEW (16/32) does not narrow FLEN.
        if file_sew is not None:
          setFlen(file_sew if file_sew > 32 else 32)
        else:
          setFlen(xlen)

        if not instructions:
            continue

        basename = extension
        pathname = f"{ARCH_VERIF}/tests/priv/{basename}"

        cmd = "mkdir -p " + pathname # make directory
        os.system(cmd)
        fname = pathname + "/" + basename + f"_rv{xlen}.S"
        tempfname = pathname + "/" + basename + f"_rv{xlen}_temp.S"

        # Split SsstrictV across multiple .S files so each ELF stays under the
        # ±1MiB JAL relocation range. The framework's `tests_dir.rglob("*.S")`
        # picks up every chunk independently, each with its own RVTEST_BEGIN/END
        # wrapper, signature region, and SIGUPD_COUNT. Other priv arches keep a
        # single file (CHUNK_SIZE >= len(instructions)).
        if extension.startswith("SsstrictV"):
            CHUNK_SIZE = 25
        else:
            CHUNK_SIZE = max(len(instructions), 1)

        chunks = [instructions[i:i + CHUNK_SIZE] for i in range(0, len(instructions), CHUNK_SIZE)]
        # Discover existing chunk files so stale outputs from a larger split
        # don't leak into the build (e.g. switching from 6 chunks to 4).
        for stale in pathlib.Path(pathname).glob(f"{basename}_rv{xlen}*.S"):
            os.system(f"rm -f {stale}")

        for chunk_idx, chunk_instructions in enumerate(chunks):
            # Reset per-file generator state (sigupd_count, testcase_count, sigReg, ...)
            # so each chunk starts clean and signature counts / label numbering
            # don't accumulate across chunks.
            newInstruction()

            # Single-chunk extensions keep the historical filename so other
            # tooling that searches for "<ext>_rv<xlen>.S" continues to work.
            if len(chunks) == 1:
                chunk_basename = basename
                fname = pathname + f"/{basename}_rv{xlen}.S"
                tempfname = pathname + f"/{basename}_rv{xlen}_temp.S"
            else:
                chunk_basename = f"{basename}_p{chunk_idx}"
                fname = pathname + f"/{basename}_rv{xlen}_p{chunk_idx}.S"
                tempfname = pathname + f"/{basename}_rv{xlen}_p{chunk_idx}_temp.S"

            print(f"Generating rv{xlen} tests for " + fname)

            ############################### starting test file ###############################
            # print custom header part
            f = pathlib.Path(tempfname).open("w")
            line = "///////////////////////////////////////////\n"
            f.write(line)
            line = "// "+fname+ "\n// " + author + "\n"
            f.write(line)

            # insert generic header
            insertTemplate(chunk_basename, 0, "testgen_header.S", priv=True)

            ###############################     test body      ###############################
            for instruction in chunk_instructions:
                coverpoints = list(testplans[extension][instruction])
                makeTest(coverpoints, instruction)

            insertTemplate(chunk_basename, 0, "cp_vstart_gt_vl_setup.S")

            # The framework's RVTEST_CODE_END (tests/env/rvtest_setup.h) hardcodes x2
            # as the signature pointer for its final check_trap_sig_offset SIGUPD.
            # If our test relocated sigReg away from x2 (handleSignaturePointerConflict),
            # x2 now holds stale data and the cleanup epilog would store through a
            # bogus pointer (typical symptom: trap loop with MEPC inside
            # check_trap_sig_offset). Restore x2 = sigReg here so the cleanup works.
            if common.sigReg != 2:
                writeLine(f"mv x2, x{common.sigReg}", "# restore sigReg into x2 for RVTEST_CODE_END cleanup epilog")

            ###############################  ending test file  ###############################
            # generate vector data (random and corners)
            test_data = genVMaskedges() # TODO: change to generate a good random (vector_random)
            test_data += genRandomVectorLS()

            # print footer with test data and signature
            signatureWords = getSigSpace(xlen, flen)
            insertTemplate(chunk_basename, signatureWords, "testgen_footer.S", test_data=test_data)

            # Finish
            f.close()
            # Replace the @SIGUPD_COUNT_FROM_TESTGEN@ placeholder using the dynamic
            # sigupd_count tally maintained by writeSIGUPD / writeSIGUPD_V (same path
            # used by vector-testgen-unpriv.py). PR #1353 dropped the _OFFSET arg from
            # RVTEST_SIGUPD_V/_V_LEN, so the previous regex-based byte counter no longer
            # works.
            finalizeSigupdCount(tempfname, xlen, flen)
            # if new file is different from old file, replace old file with new file
            if pathlib.Path(fname).exists():
                if filecmp.cmp(fname, tempfname): # files are the same
                    os.system(f"rm {tempfname}") # remove temp file
                else:
                    os.system(f"mv {tempfname} {fname}")
                    print("Updated " + fname)
            else:
                os.system(f"mv {tempfname} {fname}")
