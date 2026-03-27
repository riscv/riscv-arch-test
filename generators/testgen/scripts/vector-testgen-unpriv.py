#!/usr/bin/env python3

##################################
# vector-testgen-unpriv.py
#
# James Kaden Cassidy jacassidy@g.hmc.edu June 26 2025
# SPDX-License-Identifier: Apache-2.0
#
# Generate directed tests for functional coverage
##################################

##################################
# libraries
##################################
import filecmp
import math
import os
import re
from random import randint, seed

import vector_testgen_common as common
from vector_testgen_common import (
  ARCH_VERIF,
  fedges,
  fedgesD,
  fedgesH,
  flen,
  freg_count,
  frmList,
  genVtestdata,
  getBaseLmul,
  getBaseSuiteTestCount,
  getInstructionEEW,
  getLegalVlmul,
  getLengthLmul,
  getLengthSuiteTestCount,
  getSigSpace,
  imm_31,
  incrementBasetestCount,
  incrementLengthtestCount,
  indexed_loads,
  indexed_stores,
  insertTemplate,
  maxELEN,
  minSEW_MIN,
  mmins,
  myhash,
  narrowins,
  newInstruction,
  randomizeMask,
  randomizeOngroupVectorRegister,
  randomizeVectorInstructionData,
  readTestplans,
  setExtension,
  setFlen,
  setXlen,
  v_edges_ls,
  vedgeseew1,
  vedgesemul1,
  vedgesemul2,
  vedgesemul4,
  vedgesemul8,
  vedgesemulf2,
  vedgesemulf4,
  vedgesemulf8,
  vd_widen_ins,
  vector_loads,
  vector_ls_ins,
  vector_stores,
  vextins,
  vfedgesemul1,
  vfedgesemul2,
  vfloattypes,
  vmlogicalins,
  vreg_count,
  vs1ins,
  vs2_widen_ins,
  vsAddressCount,
  vxrmList,
  writeTest,
  wvsins,
  wwvins,
  xreg_count,
  xvmtype,
  xvtype,
)

unsupported_tests = [ # conflicting signatures between sail and spike, open PRs listed below
  # "vnclip.wi",      # Sail issue 1071
  # "vnclipu.wi",     # Sail issue 1071
  # "vnsra.wi",       # Sail issue 1071
  # "vnsrl.wi",       # Sail issue 1071
  # "vslideup.vi",    # Sail issue 1071
  # "vslidedown.vi",  # Sail issue 1071
  # "vrgather.vi",    # Sail issue 1071
  "vlseg3e32ff.v",
  "vlseg3e32.v",
  "vlseg4e32.v",
  "vsseg3e64.v",
  "vsseg3e32.v"

]

def writeLine(argument: str, comment = ""):
  comment_distance = 50
  tab_size = 4

  argument = (" " * tab_size * common.tab_count) + str(argument)

  if comment != "":
    padding = max(0, comment_distance - len(argument))
    comment = " " * padding + str(comment)

  f.write(argument + comment +"\n")

def make_custom(test, xlen):
    insertTemplate(test, 0, f"{test}.S")

def make_vd(instruction, sew, rng, lmul = 1):

  for v in rng:
    description = "cp_vd (Test destination vd = v" + str(v) + ")"
    instruction_data = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), lmul = lmul, vd = v)

    writeTest(description, instruction, instruction_data, sew=sew, lmul = lmul)
    incrementBasetestCount()
    vsAddressCount()

def make_vl_0(instruction, sew, lmul = 1):
  description = "cr_vl_0 (Test vl = 0)"
  instruction_data  = randomizeVectorInstructionData(instruction, sew, getLengthSuiteTestCount(), suite="length", lmul = lmul)

  writeTest(description, instruction, instruction_data, sew=sew, lmul=lmul, vl=0)
  incrementLengthtestCount()
  vsAddressCount("length")

def make_vs3(instruction, sew, rng, lmul = 1):

  for v in rng:
    description = "cp_vs2 (Test source vs3 = v" + str(v) + ")"
    instruction_data = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), lmul = lmul, vs3 = v)

    writeTest(description, instruction, instruction_data, sew=sew, lmul = lmul)
    incrementBasetestCount()
    vsAddressCount()

def make_vs2(instruction, sew, rng, lmul = 1):

  for v in rng:
    description = "cp_vs2 (Test source vs2 = v" + str(v) + ")"
    instruction_data = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), lmul = lmul, vs2 = v)

    writeTest(description, instruction, instruction_data, sew=sew, lmul = lmul)
    incrementBasetestCount()
    vsAddressCount()

def make_vs1(instruction, sew, rng):

  for v in rng:
    description       = "cp_vs1 (Test source vs1 = v" + str(v) + ")"
    instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), vs1 = v)

    writeTest(description, instruction, instruction_data, sew=sew)
    incrementBasetestCount()
    vsAddressCount()

def make_vd_vs2(instruction, sew, rng, lmul = 1):

  for v in rng:
    description = f"cmp_vd_vs2 (Test vd = vs2 = v{v})"
    instruction_data = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), lmul = lmul, vd = v, vs2 = v)

    writeTest(description, instruction, instruction_data, sew=sew, lmul = lmul)
    incrementBasetestCount()
    vsAddressCount()

def make_vd_vs1(instruction, sew, rng):

  for v in rng:
    description       = "cmp_vd_vs1 (Test vd = vs1 = v" + str(v) + ")"
    instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), vd = v, vs1 = v)

    writeTest(description, instruction, instruction_data, sew=sew)
    incrementBasetestCount()
    vsAddressCount()

def make_vd_vs1_vs2(instruction, sew, rng):

  for v in rng:
    description       = "cmp_vd_vs1_vs2 (Test vd = vs1 = vs2 = v" + str(v) + ")"
    instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), vd = v, vs1 = v, vs2 = v)

    writeTest(description, instruction, instruction_data, sew=sew)
    incrementBasetestCount()
    vsAddressCount()

def make_vs1_vs2(instruction, sew, rng):

  for v in rng:
    description       = "cmp_vs1_vs2 (Test vs1 = vs2 = v" + str(v) + ")"
    instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), vs1 = v, vs2 = v)

    writeTest(description, instruction, instruction_data, sew=sew)
    incrementBasetestCount()
    vsAddressCount()

def make_vs3_vs2(instruction, sew, rng, lmul = 1):

  for v in rng:
    description       = "cmp_vs3_vs2 (Test vs3 = vs2 = v" + str(v) + ")"
    instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), lmul = lmul, vs3 = v, vs2 = v)

    writeTest(description, instruction, instruction_data, sew=sew, lmul = lmul)
    incrementBasetestCount()
    vsAddressCount()

def make_rs1_v(instruction, sew, rng, lmul = 1):

  for r in rng:
    description       = "cp_rs1 (Test rs1 = x" + str(r) + ")"
    instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), lmul = lmul, rs1 = r)

    writeTest(description, instruction, instruction_data, sew=sew, lmul = lmul)
    incrementBasetestCount()

def make_rs2_v(instruction, sew, rng, lmul = 1):

  for r in rng:
    description       = "cp_rs2 (Test rs2 = x" + str(r) + ")"
    instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), lmul = lmul, rs2 = r)

    writeTest(description, instruction, instruction_data, sew=sew, lmul = lmul)
    incrementBasetestCount()

def make_rs2_edges_v(instruction, sew, redges, lmul=1):
  vlvals = ["vlmax"]
  for vl in vlvals:
    for r in redges:
      description       = f"cp_rs2_edges (Test rs2 corner val = {r})"
      instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), lmul = lmul, rs2_val = r)

      writeTest(description, instruction, instruction_data, sew=sew, vl=vl, lmul = lmul)
      incrementBasetestCount()

def make_rs1_rs2_v(instruction, sew, rng, lmul = 1):

  for r in rng:
    description       = "cmp_rs1_rs2 (Test rs1 = rs2 = x" + str(r) + ")"
    instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), lmul = lmul, rs1 = r, rs2 = r)

    writeTest(description, instruction, instruction_data, sew=sew, lmul = lmul)
    incrementBasetestCount()

def make_fs1_v(instruction, sew, rng, lmul = 1):

  for f in rng:
    description       = "cp_fs1 (Test fs1 = f" + str(f) + ")"
    instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), lmul = lmul, fs1 = f)

    writeTest(description, instruction, instruction_data, sew=sew, lmul = lmul)
    incrementBasetestCount()

def make_imm_v(instruction, sew):

  if (test in imm_31):
    for uimm in range(0,32):
      description       = "cp_imm_5bit_u (Test uimm = " + str(uimm) + ")"
      instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), imm = uimm)

      writeTest(description, instruction, instruction_data, sew=sew)
      incrementBasetestCount()
  else:
    for imm in range(-16,16):
      description       = "cp_imm_5bit (Test imm = " + str(imm) + ")"
      instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), imm = imm)

      writeTest(description, instruction, instruction_data, sew=sew)
      incrementBasetestCount()

def make_rdv(instruction, sew, rng):

  for r in rng:
    description       = "cp_rd (Test rd = x" + str(r) + ")"
    instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), rd = r)

    writeTest(description, instruction, instruction_data, sew=sew)
    incrementBasetestCount()
    vsAddressCount()

def make_fdv(instruction, sew, rng):

  for f in rng:
    description       = "cp_fd (Test fd = f" + str(f) + ")"
    instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), fd = f)

    writeTest(description, instruction, instruction_data, sew=sew)
    incrementBasetestCount()
    vsAddressCount()

def make_vs2_edges(instruction, sew, vedges, vl=1, lmul = 1):

  for v in vedges:
    description       = "cp_vs2_edges (Test source vs2 value = " + v + ")"
    instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), lmul = lmul, vs2_val_pointer = v)

    writeTest(description, instruction, instruction_data, sew=sew, vl=vl, lmul = lmul)
    incrementBasetestCount()

def make_vs1_edges(instruction, sew, vedges, vl=1):

  for v in vedges:
    description       = "cp_vs1_edges (Test source vs1 value = " + v + ")"
    instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), vs1_val_pointer = v)

    writeTest(description, instruction, instruction_data, sew=sew, vl=vl)
    incrementBasetestCount()

def make_rs1_edges_v(instruction, sew, redgesv):

  for rcorner in redgesv:
    description       = "cp_rs1_edges (Test source rs1 value = " + hex(rcorner) + ")"
    instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), rs1_val = rcorner)

    writeTest(description, instruction, instruction_data, sew=sew)
    incrementBasetestCount()

def make_fs1_edges_v(instruction, sew):
  if sew == 64:
    fedgesv = fedgesD
  elif sew == 16:
    fedgesv = fedgesH
  else:
    fedgesv = fedges

  for fcorner in fedgesv:
    fcorner_val       = fedgesv[fcorner]
    description       = "cp_fs1_edges (Test source fs1 value = " + fcorner + ")"
    instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), fs1_val = fcorner_val)

    writeTest(description, instruction, instruction_data, sew=sew)
    incrementBasetestCount()

def make_vs2_vs1_edges(instruction, sew, vs2edges, vs1edges, vl=1):
  for v1 in vs1edges:
    for v2 in vs2edges:
      description = "cr_vs2_vs1_edges"
      instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), vs1_val_pointer = v1, vs2_val_pointer = v2, additional_no_overlap=[['vs1', 'vs2']])

      writeTest(description, instruction, instruction_data, sew=sew, vl=vl)

def make_vs2_rs1_edges(instruction, sew, vs2edges):
  for r1 in redgesv:
    for v2 in vs2edges:
      description = "cr_vs2_rs1_edges"
      instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), vs2_val_pointer = v2, rs1_val = r1)

      writeTest(description, instruction, instruction_data, sew=sew)

def make_vs2_fs1_edges(instruction, sew, vs2edges):
  if sew == 64:
    fedgesv = fedgesD
  elif sew == 16:
    fedgesv = fedgesH
  else:
    fedgesv = fedges

  for f1 in fedgesv:
    for v2 in vs2edges:
      f1_val = fedgesv[f1]
      description = "cr_vs2_rs1_edges"
      instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), vs2_val_pointer = v2, fs1_val = f1_val)

      writeTest(description, instruction, instruction_data, sew=sew)

def make_vs2_imm_edges(instruction, sew, vs2edges):
  for imm in immedgesv:
    for v2 in vs2edges:
      description = "cr_vs2_imm_edges"
      instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), vs2_val_pointer = v2, imm = imm)

      writeTest(description, instruction, instruction_data, sew=sew)

def make_vxrm_vs2_vs1_edges(instruction, sew, vs2edges, vs1edges):
  for vxrm in vxrmList:
    for v1 in vs1edges:
      for v2 in vs2edges:
        description = "cr_vxrm_vs2_vs1_edges (Test vxrm = " + vxrm + ")"
        instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), vs2_val_pointer = v2, vs1_val_pointer = v1, additional_no_overlap=[['vs1','vs2']])

        writeTest(description, instruction, instruction_data, sew=sew, vxrm=vxrm)

def make_vxrm_vs2_rs1_edges(instruction, sew, vs2edges):
  for vxrm in vxrmList:
    for r1 in redgesv:
      for v2 in vs2edges:
        description = "cr_vxrm_vs2_rs1_edges (Test vxrm = " + vxrm + ")"
        instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), vs2_val_pointer = v2, rs1_val = r1)

        writeTest(description, instruction, instruction_data, sew=sew, vxrm=vxrm)

def make_vxrm_vs2_imm_edges(instruction, sew, vs2edges):
  for vxrm in vxrmList:
    for imm in immedgesv:
      for v2 in vs2edges:
        description = "cr_vxrm_vs2_imm_edges (Test vxrm = " + vxrm + ")" + str(imm)
        instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), vs2_val_pointer = v2, imm = imm)

        writeTest(description, instruction, instruction_data, sew=sew, vxrm=vxrm)

def make_frm(instruction, sew):
  for frm in frmList:
    for i in range(10):
      description = f"cp_csr_frm (Test frm = {frm}, Test number {i+1})"
      instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount())

      writeTest(description, instruction, instruction_data, sew=sew, frm=frm)
      incrementBasetestCount()

##################################### length suite (vl!=1) test generation #####################################

def getMaxlmul(sew, eew, maxemul):
  if eew is None:
    return maxemul

  lmulMultiplier = eew/sew

  if lmulMultiplier > 1:
    return maxemul / lmulMultiplier

  return maxemul

def make_vl_lmul(instruction, sew, maxemul=8, eew = None, preset_emul = None):
  global legalvlmuls

  numlmul = int(math.log2(getMaxlmul(sew, eew, maxemul)))
  minlmul = min(legalvlmuls)

  for l in range(minlmul, numlmul+1):
    for k in range(3):
      lmul = 2 ** l # creating lmul first

      vlval = ["vlmax", 1, "random"]
      vl = vlval[k]
      vta = randint(0,1)
      vma = randint(0,1)

      if preset_emul is not None:
        emul = preset_emul
      else:
        emul = lmul

      maskval = randomizeMask(test)
      no_overlap = [['vs1', 'v0'], ['vs2', 'v0'], ['vd', 'v0']] if maskval is not None else None

      description = f"cr_vl_lmul (Test lmul = {lmul}, vl = {vl})"
      instruction_data  = randomizeVectorInstructionData(instruction, sew, getLengthSuiteTestCount(), suite="length", lmul = emul, additional_no_overlap=no_overlap)

      writeTest(description, instruction, instruction_data, sew=sew, lmul=lmul, vl=vl, maskval=maskval, vta=vta, vma=vma)
      incrementLengthtestCount()
      vsAddressCount("length")

def make_mask_edges(instruction, sew, lmul = 1):
  vma = randint(0,1)
  cp_masking_edges_data = ["ones", "zeroes", "vlmaxm1_ones", "vlmaxd2p1_ones", "cp_mask_random"]

  for m in cp_masking_edges_data:
    vma = randint(0,1)

    description = f"cp_masking_edges (Test v0 = {m})"
    instruction_data  = randomizeVectorInstructionData(instruction, sew, getLengthSuiteTestCount(), lmul=lmul, suite="length", additional_no_overlap=[['vs1', 'v0'], ['vs2', 'v0'], ['vd', 'v0'], ['vs3', 'v0']])

    writeTest(description, instruction, instruction_data, sew=sew, lmul=lmul, vl="vlmax", maskval=m, vma=vma)
    incrementLengthtestCount()
    vsAddressCount("length")

def make_vtype_agnostic(instruction, sew, maxemul=8, eew = None, preset_emul = None):
  global legalvlmuls

  vlmulmax = int(math.log2(getMaxlmul(sew, eew, maxemul)))
  minlmul = min(legalvlmuls)

  for t in [0,1]:
    for m in [0,1]:

      lmul = 2 ** randint(minlmul, vlmulmax) # pick random integer LMUL to ensure that coverpoints are hit

      if preset_emul is not None:
        emul = preset_emul
      else:
        emul = lmul

      maskval = randomizeMask(instruction, always_masked=True)
      no_overlap = [['vs1', 'v0'], ['vs2', 'v0'], ['vd', 'v0']] if maskval is not None else None
      vta = t
      vma = m

      description = f"cr_vtype_agnostic (Test vta = {vta}, vma = {vma})"
      instruction_data  = randomizeVectorInstructionData(instruction, sew, getLengthSuiteTestCount(), suite="length", lmul = emul, additional_no_overlap=no_overlap)

      writeTest(description, instruction, instruction_data, sew=sew, lmul=lmul, vl="random", maskval=maskval, vta=vta, vma=vma)
      incrementLengthtestCount()
      vsAddressCount("length")


#####################################         custom test generation       #####################################

def make_custom_vmask_write_lmulge1(instruction, sew):
  for lmul in [1, 2, 4, 8]:
    description = f"cp_custom_vmask_write_lmulge1 (Test lmul = {lmul})"
    instruction_data  = randomizeVectorInstructionData(instruction, sew, getLengthSuiteTestCount(), suite="length", lmul = lmul)

    writeTest(description, instruction, instruction_data, sew=sew, lmul=lmul, vl="vlmax")
    incrementLengthtestCount()
    vsAddressCount("length")

def make_custom_vmask_write_v0_masked(instruction, sew):
  maskval = randomizeMask(instruction, always_masked = True)  # set always_masked true since this cp will only be tested for instr with mask available
  no_overlap = [['vs1', 'v0'], ['vs2', 'v0']]

  description = "cp_custom_vmask_write_v0_masked"
  instruction_data  = randomizeVectorInstructionData(instruction, sew, getLengthSuiteTestCount(), vd = 0, suite="length", additional_no_overlap=no_overlap)

  writeTest(description, instruction, instruction_data, sew=sew, vl="vlmax", maskval=maskval)
  incrementLengthtestCount()
  vsAddressCount("length")

def make_custom_voffgroup_vr(instruction, sew, lmul, vr):
  for v in range(0, vreg_count):
    if (v % lmul == 0):
      pass
    else:
      description = f"cp_custom_voffgroup_{vr}_lmul{lmul} (Test lmul = {lmul}, {vr} = {v})"
      if vr == "vs1":
        vd  = randomizeOngroupVectorRegister(instruction, v, lmul=lmul)
        if (instruction in wvsins):
          vs2 = randomizeOngroupVectorRegister(instruction, v, vd, math.floor(v/lmul) * lmul, lmul=lmul)
        else:
          vs2 = randomizeOngroupVectorRegister(instruction, v, vd, lmul=lmul)
        instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), vd = vd, vs2 = vs2, vs1 = v, suite="base", lmul = lmul)
      elif vr == "vs2":
        vd  = randomizeOngroupVectorRegister(instruction, v, lmul=lmul)
        vs1 = randomizeOngroupVectorRegister(instruction, v, vd, lmul=lmul)
        instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), vd = vd, vs2 = v, vs1 = vs1, suite="base", lmul = lmul)
      else: # vd
        vs2 = randomizeOngroupVectorRegister(instruction, v, lmul=lmul)
        vs1 = randomizeOngroupVectorRegister(instruction, v, vs2, lmul=lmul)
        instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), vd = v, vs2 = vs2, vs1 = vs1, suite="base", lmul = lmul)

      writeTest(description, instruction, instruction_data, sew=sew, lmul=lmul)
      incrementBasetestCount()
      vsAddressCount()

def make_custom_gprWriting_vstart_eq_vl(instruction, sew):
  description = "cp_custom_gprWriting_vstart_eq_vl"
  instruction_data  = randomizeVectorInstructionData(instruction, sew, getLengthSuiteTestCount(), suite="length")

  writeTest(description, instruction, instruction_data, sew=sew, vl=0, vstart=0)
  incrementLengthtestCount()
  vsAddressCount("length")

def make_custom_vext_overlapping_vd_vs2(instruction, sew, vext_ins):
  # vext is the suffix of the extension, e.g. "f2" of vsext.vf2
  # Generate tests for multiple LMUL values depending on the suffix:
  #  - "f2" -> LMULs 2, 4, 8
  #  - "f4" -> LMULs 4, 8
  #  - "f8" -> LMUL 8
  if vext_ins == "f2":
    lmul_list = [2, 4, 8]
  elif vext_ins == "f4":
    lmul_list = [4, 8]
  elif vext_ins == "f8":
    lmul_list = [8]
  else:
    lmul_list = [int(vext_ins[1])]

  vext = int(vext_ins[1])

  for lmul in lmul_list:
    vd = randint(0, math.floor((vreg_count-1)/lmul)) * lmul   # ensure that vd is on group with the given lmul
    vs2 = vd + (lmul - int(lmul/vext))                                 # force vs2 to overlap with the top of vd
    vs1 = randomizeOngroupVectorRegister(instruction, vs2, vd, lmul=lmul)

    description = f"cp_custom_vext{vext}_overlapping_vd_vs2 (lmul = {lmul})"
    instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), vd = vd, vs2 = vs2, vs1 = vs1, suite="base", lmul = lmul)

    writeTest(description, instruction, instruction_data, sew=sew, lmul=lmul)
    incrementBasetestCount()
    vsAddressCount()

def make_custom_vdOverlapTopVs1_vd_vs1(instruction, sew, lmul):
  emul = 2 * lmul
  vd = randint(0, math.floor((vreg_count-1)/emul)) * emul   # ensure that vd is on group with the given lmul
  vs1 = vd + lmul                                           # force vs1 to overlap with the top of vd, for widening so the overlap is simply the top half
  if instruction in vs2_widen_ins:
    vs2 = randomizeOngroupVectorRegister(instruction, vs1, vd, lmul=emul)
  else:
    vs2 = randomizeOngroupVectorRegister(instruction, vs1, vd, lmul=lmul)

  description = f"cp_custom_vdOverlapTopVs1_vd_vs1_lmul{lmul}"
  instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), vd = vd, vs2 = vs2, vs1 = vs1, suite="base", lmul = lmul)

  writeTest(description, instruction, instruction_data, sew=sew, lmul=lmul)
  incrementBasetestCount()
  vsAddressCount()

def make_custom_vdOverlapTopVs2_vd_vs2(instruction, sew, lmul):
  emul = 2 * lmul
  vd = randint(0, math.floor((vreg_count-1)/emul)) * emul   # ensure that vd is on group with the given lmul
  vs2 = vd + lmul                                           # force vs2 to overlap with the top of vd, for widening so the overlap is simply the top half
  vs1 = randomizeOngroupVectorRegister(instruction, vs2, vd, lmul=lmul)

  description = f"cp_custom_vdOverlapTopVs2_vd_vs2_lmul{lmul}"
  instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), vd = vd, vs2 = vs2, vs1 = vs1, suite="base", lmul = lmul)

  writeTest(description, instruction, instruction_data, sew=sew, lmul=lmul)
  incrementBasetestCount()
  vsAddressCount()

def make_custom_vdOverlapBtmVs2_vd_vs2(instruction, sew, lmul):
  emul = 2 * lmul
  vd = randint(0, math.floor((vreg_count-1)/emul)) * emul   # ensure that vd is on group with the given lmul
  vs2 = vd                                                  # force vs2 to overlap with the bottom of vd

  description = f"cp_custom_vdOverlapBtmVs2_vd_vs2_lmul{lmul}"
  instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), vd = vd, vs2 = vs2, suite="base", lmul = lmul)

  writeTest(description, instruction, instruction_data, sew=sew, lmul=lmul)
  incrementBasetestCount()
  vsAddressCount()

def make_custom_allVdOverlapTopVs2_vd_vs2(instruction, sew, lmul):
  emul = 2 * lmul
  for v in range(0, vreg_count):
    if (v % emul == 0):
      vd  = v             # ensure that vd is on group with the given lmul
      vs2 = vd + lmul     # force vs2 to overlap with the top of vd, for widening so the overlap is simply the top half
      vs1 = randomizeOngroupVectorRegister(instruction, vs2, vd, lmul=lmul)

      description = f"cp_custom_allVdOverlapTopVs2_vd_vs2_lmul{lmul} (Test vd = {v}, vs2 = {vs2})"
      instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), vd = vd, vs2 = vs2, vs1 = vs1, suite="base", lmul = lmul)

      writeTest(description, instruction, instruction_data, sew=sew, lmul=lmul)
      incrementBasetestCount()
      vsAddressCount()
    else:
      pass

def make_custom_allVdOverlapTopVs1_vd_vs1(instruction, sew, lmul):
  emul = 2 * lmul
  for v in range(0, vreg_count):
    if (v % emul == 0):
      vd  = v             # ensure that vd is on group with the given lmul
      vs1 = vd + lmul     # force vs2 to overlap with the top of vd, for widening so the overlap is simply the top half
      if (instruction in wwvins):
        vs2 = randomizeOngroupVectorRegister(instruction, vs1, vd, lmul=emul)
      else:
        vs2 = randomizeOngroupVectorRegister(instruction, vs1, vd, lmul=lmul)

      description = f"cp_custom_allVdOverlapTopVs1_vd_vs1_lmul{lmul} (Test vd = {v}, vs1 = {vs1})"
      instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), vd = vd, vs2 = vs2, vs1 = vs1, suite="base", lmul = lmul)

      writeTest(description, instruction, instruction_data, sew=sew, lmul=lmul)
      incrementBasetestCount()
      vsAddressCount()
    else:
      pass

def make_custom_vreductionw_vd_vs1_emul_16(instruction, sew):
  description = "cp_custom_vreductionw_vd_vs1_emul_16"
  instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), suite="base", lmul = 8) # requires lmul = 8

  writeTest(description, instruction, instruction_data, sew=sew, lmul=8)
  incrementBasetestCount()
  vsAddressCount()

def make_custom_element0Masked(instruction, sew):
  no_overlap = [['vd', 'vs1'], ['vd', 'v0'], ['vs1', 'v0'], ['vs2', 'v0']]

  description = "cp_custom_element0Masked"
  instruction_data  = randomizeVectorInstructionData(instruction, sew, getLengthSuiteTestCount(), suite="base", additional_no_overlap=no_overlap)

  writeTest(description, instruction, instruction_data, sew=sew, vl="vlmax", maskval="ones")
  incrementBasetestCount()
  vsAddressCount()

def make_custom_vshift_upperbits_r1_ones(instruction, sew, r1, narrow=False):
  def top_bits_mask(xlen, sew):
    top = xlen - 1
    bottom = int(math.log2(sew))
    width = top - bottom + 1
    mask = ((1 << width) - 1) << bottom
    return mask

  if (narrow):
    r1_val = hex(top_bits_mask(xlen, 2 * sew))
  else:
    r1_val = hex(top_bits_mask(xlen, sew))

  description = f"cp_custom_vshift{narrow}_upperbits_{r1}_ones"
  if r1 == "rs1":
    instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), suite="base", rs1_val=r1_val)
  else:
    instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), suite="base", vs1_val=r1_val)

  writeTest(description, instruction, instruction_data, sew=sew)
  incrementBasetestCount()
  vsAddressCount()

def make_custom_vindexedges_index_ge_vlmax(instruction, sew):
  description = "cp_custom_vindexedges_index_ge_vlmax"
  instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), suite="base", vs1_val=-1)

  writeTest(description, instruction, instruction_data, sew=sew)
  incrementBasetestCount()
  vsAddressCount()

def make_custom_vindexedges_index_gt_vl_lt_vlmax(instruction, sew):
  description = "cp_custom_vindexedges_index_gt_vl_lt_vlmax"
  instruction_data  = randomizeVectorInstructionData(instruction, sew, getBaseSuiteTestCount(), suite="base", lmul=2, vs1_val=2)

  writeTest(description, instruction, instruction_data, sew=sew, lmul=2)
  incrementBasetestCount()
  vsAddressCount()

#####################################           test generation           #####################################

def makeTest(coverpoints, test, sew=None):
  global NaNBox_tests
  # default vl and lmul settings for base suite
  for coverpoint in coverpoints:
    # produce a deterministic seed for repeatable random numbers distinct for each instruction and coverpoint
    testname = test + coverpoint
    hashval = myhash(testname)
    # hashval = hash(testname) # doesn't work because of Python hash randomization
    seed(hashval)
    # print(f"\ncoverpoint: {coverpoint}")
    # print(f"instruction: {test}")
    #seed(hash(test + coverpoint))
    ############################# base suite #############################
    if   ((coverpoint in ['RV32', 'RV64', 'EFFEW8', 'EFFEW16', 'EFFEW32', 'EFFEW64']) or
          ("sample" in coverpoint))                   : pass
    if   coverpoint == "cp_asm_count"                 : pass
    elif coverpoint == "cp_fd"                        : make_fdv(test, sew, range(freg_count))
    elif coverpoint == "cp_fs1"                       : make_fs1_v(test, sew, range(freg_count))
    elif coverpoint == "cp_rd"                        : make_rdv(test, sew, range(xreg_count))
    elif coverpoint == "cp_rs1"                       : make_rs1_v(test, sew, range(xreg_count))
    elif coverpoint == "cp_rs1_nx0"                   : make_rs1_v(test, sew, range(1, xreg_count), getBaseLmul(test, sew))
    elif coverpoint == "cp_rs2"                       : make_rs2_v(test, sew, range(xreg_count), getBaseLmul(test, sew))
    elif coverpoint == "cp_rs2_edges_ls_e8"         : make_rs2_edges_v(test, sew, redges_ls_e8, lmul = getBaseLmul(test, sew))
    elif coverpoint == "cp_rs2_edges_ls_e16"        : make_rs2_edges_v(test, sew, redges_ls_e16, lmul = getBaseLmul(test, sew))
    elif coverpoint == "cp_rs2_edges_ls_e32"        : make_rs2_edges_v(test, sew, redges_ls_e32, lmul = getBaseLmul(test, sew))
    elif coverpoint == "cp_rs2_edges_ls_e64"        : make_rs2_edges_v(test, sew, redges_ls_e64, lmul = getBaseLmul(test, sew))
    elif coverpoint == "cp_rs1_edges"               : make_rs1_edges_v(test, sew, redgesv)
    elif coverpoint == "cp_fs1_edges_v"             : make_fs1_edges_v(test, sew)
    elif coverpoint == "cmp_rs1_rs2"                  : make_rs1_rs2_v(test, sew, range(xreg_count))
    elif coverpoint == "cp_imm_5bit"                  : make_imm_v(test, sew)
    elif coverpoint == "cp_imm_5bit_u"                : make_imm_v(test, sew)
    elif coverpoint == "cp_vd"                        : make_vd(test, sew, range(vreg_count),   getBaseLmul(test, sew))
    elif coverpoint == "cp_vd_lte30"                  : make_vd(test, sew, range(vreg_count-1), getBaseLmul(test, sew))
    elif coverpoint == "cp_vd_lte29"                  : make_vd(test, sew, range(vreg_count-2), getBaseLmul(test, sew))
    elif coverpoint == "cp_vd_lte28"                  : make_vd(test, sew, range(vreg_count-3), getBaseLmul(test, sew))
    elif coverpoint == "cp_vd_lte27"                  : make_vd(test, sew, range(vreg_count-4), getBaseLmul(test, sew))
    elif coverpoint == "cp_vd_lte26"                  : make_vd(test, sew, range(vreg_count-5), getBaseLmul(test, sew))
    elif coverpoint == "cp_vd_lte25"                  : make_vd(test, sew, range(vreg_count-6), getBaseLmul(test, sew))
    elif coverpoint == "cp_vd_lte24"                  : make_vd(test, sew, range(vreg_count-7), getBaseLmul(test, sew))
    elif coverpoint == "cp_vd_nv0"                    : make_vd(test, sew, range(1,vreg_count))
    elif coverpoint == "cp_vd_emul2"                  : make_vd(test, sew, range(0,vreg_count,2), getBaseLmul(test, sew))
    elif coverpoint == "cp_vd_emul4"                  : make_vd(test, sew, range(0,vreg_count,4), getBaseLmul(test, sew))
    elif coverpoint == "cp_vd_emul8"                  : make_vd(test, sew, range(0,vreg_count,8), getBaseLmul(test, sew))
    elif coverpoint == "cp_vs3"                       : make_vs3(test, sew, range(vreg_count),   getBaseLmul(test, sew))
    elif coverpoint == "cp_vs3_lte30"                 : make_vs3(test, sew, range(vreg_count-1), getBaseLmul(test, sew))
    elif coverpoint == "cp_vs3_lte29"                 : make_vs3(test, sew, range(vreg_count-2), getBaseLmul(test, sew))
    elif coverpoint == "cp_vs3_lte28"                 : make_vs3(test, sew, range(vreg_count-3), getBaseLmul(test, sew))
    elif coverpoint == "cp_vs3_lte27"                 : make_vs3(test, sew, range(vreg_count-4), getBaseLmul(test, sew))
    elif coverpoint == "cp_vs3_lte26"                 : make_vs3(test, sew, range(vreg_count-5), getBaseLmul(test, sew))
    elif coverpoint == "cp_vs3_lte25"                 : make_vs3(test, sew, range(vreg_count-6), getBaseLmul(test, sew))
    elif coverpoint == "cp_vs3_lte24"                 : make_vs3(test, sew, range(vreg_count-7), getBaseLmul(test, sew))
    elif coverpoint == "cp_vs3_emul2"                 : make_vs3(test, sew, range(0,vreg_count,2), getBaseLmul(test, sew))
    elif coverpoint == "cp_vs3_emul4"                 : make_vs3(test, sew, range(0,vreg_count,4), getBaseLmul(test, sew))
    elif coverpoint == "cp_vs3_emul8"                 : make_vs3(test, sew, range(0,vreg_count,8), getBaseLmul(test, sew))
    elif coverpoint == "cp_vs2"                       : make_vs2(test, sew, range(vreg_count), getBaseLmul(test, sew))
    elif coverpoint == "cp_vs2_nv0"                   : make_vs2(test, sew, range(1,vreg_count))
    elif coverpoint == "cp_vs2_emul2"                 : make_vs2(test, sew, range(0,vreg_count,2), getBaseLmul(test, sew))
    elif coverpoint == "cp_vs2_emul4"                 : make_vs2(test, sew, range(0,vreg_count,4), getBaseLmul(test, sew))
    elif coverpoint == "cp_vs2_emul8"                 : make_vs2(test, sew, range(0,vreg_count,8), getBaseLmul(test, sew))
    elif coverpoint == "cp_vs1"                       : make_vs1(test, sew, range(vreg_count))
    elif coverpoint == "cp_vs1_nv0"                   : make_vs1(test, sew, range(1,vreg_count))
    elif coverpoint == "cp_vs1_emul2"                 : make_vs1(test, sew, range(0,vreg_count,2))
    elif coverpoint == "cmp_vd_vs2"                   : make_vd_vs2(test, sew, range(vreg_count), getBaseLmul(test, sew))
    elif coverpoint == "cmp_vd_vs2_nv0"               : make_vd_vs2(test, sew, range(1,vreg_count), getBaseLmul(test, sew))
    elif coverpoint == "cmp_vd_vs2_emul2"             : make_vd_vs2(test, sew, range(0,vreg_count,2), getBaseLmul(test, sew))
    elif coverpoint == "cmp_vd_vs2_emul4"             : make_vd_vs2(test, sew, range(0,vreg_count,4), getBaseLmul(test, sew))
    elif coverpoint == "cmp_vd_vs2_emul8"             : make_vd_vs2(test, sew, range(0,vreg_count,8), getBaseLmul(test, sew))
    elif coverpoint == "cmp_vd_vs1"                   : make_vd_vs1(test, sew, range(vreg_count))
    elif coverpoint == "cmp_vd_vs1_nv0"               : make_vd_vs1(test, sew, range(1,vreg_count))
    elif coverpoint == "cmp_vd_vs1_emul2"             : make_vd_vs1(test, sew, range(0,vreg_count,2))
    elif coverpoint == "cmp_vs1_vs2"                  : make_vs1_vs2(test, sew, range(vreg_count))
    elif coverpoint == "cmp_vs1_vs2_nv0"              : make_vs1_vs2(test, sew, range(1,vreg_count))
    elif coverpoint == "cmp_vd_vs1_vs2"               : make_vd_vs1_vs2(test, sew, range(vreg_count))
    elif coverpoint == "cmp_vd_vs1_vs2_nv0"           : make_vd_vs1_vs2(test, sew, range(1,vreg_count))
    elif coverpoint == "cmp_vs3_vs2"                  : make_vs3_vs2(test, sew, range(vreg_count), getBaseLmul(test, sew))
    elif coverpoint == "cmp_vs3_vs2_lte30"            : make_vs3_vs2(test, sew, range(vreg_count-1), getBaseLmul(test, sew))
    elif coverpoint == "cmp_vs3_vs2_lte29"            : make_vs3_vs2(test, sew, range(vreg_count-2), getBaseLmul(test, sew))
    elif coverpoint == "cmp_vs3_vs2_lte28"            : make_vs3_vs2(test, sew, range(vreg_count-3), getBaseLmul(test, sew))
    elif coverpoint == "cmp_vs3_vs2_lte27"            : make_vs3_vs2(test, sew, range(vreg_count-4), getBaseLmul(test, sew))
    elif coverpoint == "cmp_vs3_vs2_lte26"            : make_vs3_vs2(test, sew, range(vreg_count-5), getBaseLmul(test, sew))
    elif coverpoint == "cmp_vs3_vs2_lte25"            : make_vs3_vs2(test, sew, range(vreg_count-6), getBaseLmul(test, sew))
    elif coverpoint == "cmp_vs3_vs2_lte24"            : make_vs3_vs2(test, sew, range(vreg_count-7), getBaseLmul(test, sew))
    elif coverpoint == "cp_vs2_edges"               : make_vs2_edges(test, sew, vedgesemul1)
    elif coverpoint == "cp_vs2_edges_emul2"         : make_vs2_edges(test, sew, vedgesemul2)
    elif coverpoint == "cp_vs2_edges_emul4"         : make_vs2_edges(test, sew, vedgesemul4)
    elif coverpoint == "cp_vs2_edges_emul8"         : make_vs2_edges(test, sew, vedgesemul8)
    elif coverpoint == "cp_vs2_edges_emulf2"        : make_vs2_edges(test, sew, vedgesemulf2)
    elif coverpoint == "cp_vs2_edges_emulf4"        : make_vs2_edges(test, sew, vedgesemulf4)
    elif coverpoint == "cp_vs2_edges_emulf8"        : make_vs2_edges(test, sew, vedgesemulf8)
    elif coverpoint == "cp_vs2_edges_eew1"          : make_vs2_edges(test, sew, vedgeseew1, vl=8)  # assume vl = 8 for mask logical instr
    elif coverpoint == "cp_vs2_edges_ls"            : make_vs2_edges(test, sew, v_edges_ls, lmul=getBaseLmul(test, sew))
    elif coverpoint == "cp_vs2_edges_f"             : make_vs2_edges(test, sew, vfedgesemul1)
    elif coverpoint == "cp_vs2_edges_f_emul2"       : make_vs2_edges(test, sew, vfedgesemul2)
    elif coverpoint == "cp_vs1_edges"               : make_vs1_edges(test, sew, vedgesemul1)
    elif coverpoint == "cp_vs1_edges_emul2"         : make_vs1_edges(test, sew, vedgesemul2)
    elif coverpoint == "cp_vs1_edges_eew1"          : make_vs1_edges(test, sew, vedgeseew1, vl=8)  # assume vl = 8 for mask logical instr
    elif coverpoint == "cp_vs1_edges_f"             : make_vs1_edges(test, sew, vfedgesemul1)
    elif coverpoint == "cp_vs1_edges_f_emul2"       : make_vs1_edges(test, sew, vfedgesemul2)
    elif coverpoint == "cr_vs2_vs1_edges"           : make_vs2_vs1_edges(test, sew, vedgesemul1, vedgesemul1)
    elif coverpoint == "cr_vs2_vs1_edges_wv"        : make_vs2_vs1_edges(test, sew, vedgesemul2, vedgesemul1)
    elif coverpoint == "cr_vs2_vs1_edges_wred"      : make_vs2_vs1_edges(test, sew, vedgesemul1, vedgesemul2)
    elif coverpoint == "cr_vs2_vs1_edges_mm"        : make_vs2_vs1_edges(test, sew, vedgeseew1, vedgeseew1, vl=8)
    elif coverpoint == "cr_vs2_vs1_edges_f"         : make_vs2_vs1_edges(test, sew, vfedgesemul1, vfedgesemul1)
    elif coverpoint == "cr_vs2_vs1_edges_fwv"       : make_vs2_vs1_edges(test, sew, vfedgesemul2, vfedgesemul1)
    elif coverpoint == "cr_vs2_vs1_edges_fwred"     : make_vs2_vs1_edges(test, sew, vfedgesemul1, vfedgesemul2)
    elif coverpoint == "cr_vs2_rs1_edges"           : make_vs2_rs1_edges(test, sew, vedgesemul1)
    elif coverpoint == "cr_vs2_rs1_edges_wx"        : make_vs2_rs1_edges(test, sew, vedgesemul2)
    elif coverpoint == "cr_vs2_fs1_edges"           : make_vs2_fs1_edges(test, sew, vfedgesemul1)
    elif coverpoint == "cr_vs2_fs1_edges_wf"        : make_vs2_fs1_edges(test, sew, vfedgesemul2)
    elif coverpoint == "cr_vs2_imm_edges"           : make_vs2_imm_edges(test, sew, vedgesemul1)
    elif coverpoint == "cr_vs2_imm_edges_u"         : make_vs2_imm_edges(test, sew, vedgesemul1)
    elif coverpoint == "cr_vs2_imm_edges_wi"        : make_vs2_imm_edges(test, sew, vedgesemul2)
    elif coverpoint == "cr_vs2_imm_edges_wiu"       : make_vs2_imm_edges(test, sew, vedgesemul2)
    elif coverpoint == "cr_vxrm_vs2_vs1_edges"      : make_vxrm_vs2_vs1_edges(test, sew, vedgesemul1, vedgesemul1)
    elif coverpoint == "cr_vxrm_vs2_vs1_edges_wv"   : make_vxrm_vs2_vs1_edges(test, sew, vedgesemul2, vedgesemul1)
    elif coverpoint == "cr_vxrm_vs2_rs1_edges"      : make_vxrm_vs2_rs1_edges(test, sew, vedgesemul1)
    elif coverpoint == "cr_vxrm_vs2_rs1_edges_wx"   : make_vxrm_vs2_rs1_edges(test, sew, vedgesemul2)
    elif coverpoint == "cr_vxrm_vs2_imm_edges"      : make_vxrm_vs2_imm_edges(test, sew, vedgesemul1)
    elif coverpoint == "cr_vxrm_vs2_imm_edges_wi"   : make_vxrm_vs2_imm_edges(test, sew, vedgesemul2)
    elif coverpoint == "cp_csr_frm_v"                 : make_frm(test, sew)
    elif "cp_csr_fflags" in coverpoint                : pass # flags are expected to be raised by edge values of input
    elif coverpoint == "cp_imm_edges_5bit"          : pass # already tested in cp_imm_5bit but needed for cr_vs2_imm_edges
    elif coverpoint == "cp_imm_edges_5bit_u"        : pass # already tested in cp_imm_5bit but needed for cr_vs2_imm_edges
    elif coverpoint == "cp_csr_vxrm"                  : pass # already tested in cross coverpoints with vs2 and vs1/rs1/imm
    ############################ length suite ############################
    elif coverpoint == "cp_masking_edges"             : make_mask_edges(test, sew, getBaseLmul(test, sew))
    elif coverpoint == "cp_vl_0"                        : make_vl_0(test, sew, lmul = getBaseLmul(test, sew))
    elif "cr_vl_lmul_lmul4max"      in coverpoint       : make_vl_lmul(test, sew, maxemul=4) # includes tests for legal LMUL up to 4
    elif "cr_vl_lmul_lmul2max"      in coverpoint       : make_vl_lmul(test, sew, maxemul=2) # includes tests for legal LMUL up to 4
    elif "cr_vl_lmul_lmul1max"      in coverpoint       : make_vl_lmul(test, sew, maxemul=1) # includes tests for legal LMUL up to 4
    elif "cr_vl_lmul_e8_emul4max"   in coverpoint       : make_vl_lmul(test, sew, eew = 8,  maxemul=4)
    elif "cr_vl_lmul_e16_emul4max"  in coverpoint       : make_vl_lmul(test, sew, eew = 16, maxemul=4)
    elif "cr_vl_lmul_e32_emul4max"  in coverpoint       : make_vl_lmul(test, sew, eew = 32, maxemul=4)
    elif "cr_vl_lmul_e64_emul4max"  in coverpoint       : make_vl_lmul(test, sew, eew = 64, maxemul=4)
    elif "cr_vl_lmul_e8_emul2max"   in coverpoint       : make_vl_lmul(test, sew, eew = 8,  maxemul=2)
    elif "cr_vl_lmul_e16_emul2max"  in coverpoint       : make_vl_lmul(test, sew, eew = 16, maxemul=2)
    elif "cr_vl_lmul_e32_emul2max"  in coverpoint       : make_vl_lmul(test, sew, eew = 32, maxemul=2)
    elif "cr_vl_lmul_e64_emul2max"  in coverpoint       : make_vl_lmul(test, sew, eew = 64, maxemul=2)
    elif "cr_vl_lmul_e8_emul1max"   in coverpoint       : make_vl_lmul(test, sew, eew = 8,  maxemul=1)
    elif "cr_vl_lmul_e16_emul1max"  in coverpoint       : make_vl_lmul(test, sew, eew = 16, maxemul=1)
    elif "cr_vl_lmul_e32_emul1max"  in coverpoint       : make_vl_lmul(test, sew, eew = 32, maxemul=1)
    elif "cr_vl_lmul_e64_emul1max"  in coverpoint       : make_vl_lmul(test, sew, eew = 64, maxemul=1)
    elif "cr_vl_lmul_e8"            in coverpoint       : make_vl_lmul(test, sew, eew = 8 )
    elif "cr_vl_lmul_e16"           in coverpoint       : make_vl_lmul(test, sew, eew = 16)
    elif "cr_vl_lmul_e32"           in coverpoint       : make_vl_lmul(test, sew, eew = 32)
    elif "cr_vl_lmul_e64"           in coverpoint       : make_vl_lmul(test, sew, eew = 64)
    elif "cr_vl_lmul"               in coverpoint       : make_vl_lmul(test, sew, preset_emul = getLengthLmul(test)) # includes tests for legal LMUL up to 8
    elif coverpoint in ["cr_vtype_agnostic", "cr_vtype_agnostic_nomask"]              : make_vtype_agnostic(test, sew, preset_emul=getLengthLmul(test))
    elif coverpoint == "cr_vtype_agnostic_lmul4max"     : make_vtype_agnostic(test, sew, maxemul=4)
    elif coverpoint == "cr_vtype_agnostic_lmul2max"     : make_vtype_agnostic(test, sew, maxemul=2)
    elif coverpoint == "cr_vtype_agnostic_lmul1max"     : make_vtype_agnostic(test, sew, maxemul=1)
    elif coverpoint == "cr_vtype_agnostic_e8"           : make_vtype_agnostic(test, sew, eew = 8 )
    elif coverpoint == "cr_vtype_agnostic_e16"          : make_vtype_agnostic(test, sew, eew = 16)
    elif coverpoint == "cr_vtype_agnostic_e32"          : make_vtype_agnostic(test, sew, eew = 32)
    elif coverpoint == "cr_vtype_agnostic_e64"          : make_vtype_agnostic(test, sew, eew = 64)
    elif coverpoint == "cr_vtype_agnostic_e8_emul4max"  : make_vtype_agnostic(test, sew, eew = 8,  maxemul=4)
    elif coverpoint == "cr_vtype_agnostic_e16_emul4max" : make_vtype_agnostic(test, sew, eew = 16, maxemul=4)
    elif coverpoint == "cr_vtype_agnostic_e32_emul4max" : make_vtype_agnostic(test, sew, eew = 32, maxemul=4)
    elif coverpoint == "cr_vtype_agnostic_e64_emul4max" : make_vtype_agnostic(test, sew, eew = 64, maxemul=4)
    elif coverpoint == "cr_vtype_agnostic_e8_emul2max"  : make_vtype_agnostic(test, sew, eew = 8,  maxemul=2)
    elif coverpoint == "cr_vtype_agnostic_e16_emul2max" : make_vtype_agnostic(test, sew, eew = 16, maxemul=2)
    elif coverpoint == "cr_vtype_agnostic_e32_emul2max" : make_vtype_agnostic(test, sew, eew = 32, maxemul=2)
    elif coverpoint == "cr_vtype_agnostic_e64_emul2max" : make_vtype_agnostic(test, sew, eew = 64, maxemul=2)
    elif coverpoint == "cr_vtype_agnostic_e8_emul1max"  : make_vtype_agnostic(test, sew, eew = 8,  maxemul=1)
    elif coverpoint == "cr_vtype_agnostic_e16_emul1max" : make_vtype_agnostic(test, sew, eew = 16, maxemul=1)
    elif coverpoint == "cr_vtype_agnostic_e32_emul1max" : make_vtype_agnostic(test, sew, eew = 32, maxemul=1)
    elif coverpoint == "cr_vtype_agnostic_e64_emul1max" : make_vtype_agnostic(test, sew, eew = 64, maxemul=1)
    ############################  cp_custom   ############################
    elif coverpoint == "cp_custom_vmask_write_lmulge1"                : make_custom_vmask_write_lmulge1(test, sew)
    elif coverpoint == "cp_custom_vmask_write_v0_masked"              : make_custom_vmask_write_v0_masked(test, sew)
    elif (coverpoint in ["cp_custom_voffgroup_vd_lmul2", "cp_custom_voffgroup_vd_lmul4", "cp_custom_voffgroup_vd_lmul8"]):
      lmul = int(coverpoint[-1])
      make_custom_voffgroup_vr(test, sew, lmul, "vd")
    elif (coverpoint in ["cp_custom_voffgroup_vs2_lmul2", "cp_custom_voffgroup_vs2_lmul4", "cp_custom_voffgroup_vs2_lmul8"]):
      lmul = int(coverpoint[-1])
      make_custom_voffgroup_vr(test, sew, lmul, "vs2")
    elif (coverpoint in ["cp_custom_voffgroup_vs1_lmul2", "cp_custom_voffgroup_vs1_lmul4", "cp_custom_voffgroup_vs1_lmul8"]):
      lmul = int(coverpoint[-1])
      make_custom_voffgroup_vr(test, sew, lmul, "vs1")
    elif coverpoint == "cp_custom_gprWriting_vstart_eq_vl"            : make_custom_gprWriting_vstart_eq_vl(test, sew)
    elif (coverpoint in ["cp_custom_vext2_overlapping_vd_vs2", "cp_custom_vext4_overlapping_vd_vs2", "cp_custom_vext8_overlapping_vd_vs2"]):
      vext = test[-2:]  # "f2" of vsext.vf2
      make_custom_vext_overlapping_vd_vs2(test, sew, vext)
    elif (coverpoint in ["cp_custom_vdOverlapTopVs1_vd_vs1_lmul1", "cp_custom_vdOverlapTopVs1_vd_vs1_lmul2", "cp_custom_vdOverlapTopVs1_vd_vs1_lmul4"]):
      lmul = int(coverpoint[-1])
      make_custom_vdOverlapTopVs1_vd_vs1(test, sew, lmul)
    elif (coverpoint in ["cp_custom_vdOverlapTopVs2_vd_vs2_lmul1", "cp_custom_vdOverlapTopVs2_vd_vs2_lmul2", "cp_custom_vdOverlapTopVs2_vd_vs2_lmul4"]):
      lmul = int(coverpoint[-1])
      make_custom_vdOverlapTopVs2_vd_vs2(test, sew, lmul)
    elif (coverpoint in ["cp_custom_allVdOverlapTopVs1_vd_vs1_lmul1", "cp_custom_allVdOverlapTopVs1_vd_vs1_lmul2", "cp_custom_allVdOverlapTopVs1_vd_vs1_lmul4"]):
      lmul = int(coverpoint[-1])
      make_custom_allVdOverlapTopVs1_vd_vs1(test, sew, lmul)
    elif (coverpoint in ["cp_custom_allVdOverlapTopVs2_vd_vs2_lmul1", "cp_custom_allVdOverlapTopVs2_vd_vs2_lmul2", "cp_custom_allVdOverlapTopVs2_vd_vs2_lmul4"]):
      lmul = int(coverpoint[-1])
      make_custom_allVdOverlapTopVs2_vd_vs2(test, sew, lmul)
    elif (coverpoint in ["cp_custom_vdOverlapBtmVs2_vd_vs2_lmul1", "cp_custom_vdOverlapBtmVs2_vd_vs2_lmul2", "cp_custom_vdOverlapBtmVs2_vd_vs2_lmul4"]):
      lmul = int(coverpoint[-1])
      make_custom_vdOverlapBtmVs2_vd_vs2(test, sew, lmul)
    elif coverpoint == "cp_custom_vreductionw_vd_vs1_emul_16"         : make_custom_vreductionw_vd_vs1_emul_16(test, sew)
    elif coverpoint == "cp_custom_element0Masked"                     : make_custom_element0Masked(test, sew)
    elif coverpoint == "cp_custom_vshift_upperbits_vs1_ones"          : make_custom_vshift_upperbits_r1_ones(test, sew, "vs1")
    elif coverpoint == "cp_custom_vshift_upperbits_rs1_ones"          : make_custom_vshift_upperbits_r1_ones(test, sew, "rs1")
    elif coverpoint == "cp_custom_vshiftn_upperbits_vs1_ones"         : make_custom_vshift_upperbits_r1_ones(test, sew, "vs1", narrow=True)
    elif coverpoint == "cp_custom_vshiftn_upperbits_rs1_ones"         : make_custom_vshift_upperbits_r1_ones(test, sew, "rs1", narrow=True)
    elif coverpoint == "cp_custom_vindexedges_index_ge_vlmax"       : make_custom_vindexedges_index_ge_vlmax(test, sew)
    elif coverpoint == "cp_custom_vindexedges_index_gt_vl_lt_vlmax" : make_custom_vindexedges_index_gt_vl_lt_vlmax(test, sew)
    elif coverpoint[:2] != "cp"                                       : pass # skip all the helper coverpoints
    else:
      print("Warning: " + coverpoint + " not implemented yet for " + test)

def coverpointInclusions(coverpoints):
  applicable_coverpoints = coverpoints
  for coverpoint in coverpoints:
    if ((coverpoint in ['RV32', 'RV64', 'EFFEW8', 'EFFEW16', 'EFFEW32', 'EFFEW64']) or
        ("sample" in coverpoint))                                  : applicable_coverpoints.remove(coverpoint)
    elif coverpoint[:3] not in ["cp_", "cmp", "cr_"]               : applicable_coverpoints.remove(coverpoint) # skip all the helper coverpoints
    elif coverpoint == "cp_custom_wvv":
      applicable_coverpoints.remove(coverpoint)
      applicable_coverpoints.append("cp_custom_vdOverlapTopVs2_vd_vs2_lmul1")
      applicable_coverpoints.append("cp_custom_vdOverlapTopVs1_vd_vs1_lmul1")
      applicable_coverpoints.append("cp_custom_vdOverlapTopVs2_vd_vs2_lmul2")
      applicable_coverpoints.append("cp_custom_vdOverlapTopVs1_vd_vs1_lmul2")
      applicable_coverpoints.append("cp_custom_vdOverlapTopVs2_vd_vs2_lmul4")
      applicable_coverpoints.append("cp_custom_vdOverlapTopVs1_vd_vs1_lmul4")
    elif coverpoint == "cp_custom_wvv_all":
      applicable_coverpoints.remove(coverpoint)
      applicable_coverpoints.append("cp_custom_allVdOverlapTopVs2_vd_vs2_lmul1")
      applicable_coverpoints.append("cp_custom_allVdOverlapTopVs2_vd_vs2_lmul2")
      applicable_coverpoints.append("cp_custom_allVdOverlapTopVs2_vd_vs2_lmul4")
      applicable_coverpoints.append("cp_custom_allVdOverlapTopVs1_vd_vs1_lmul1")
      applicable_coverpoints.append("cp_custom_allVdOverlapTopVs1_vd_vs1_lmul2")
      applicable_coverpoints.append("cp_custom_allVdOverlapTopVs1_vd_vs1_lmul4")
    elif coverpoint == "cp_custom_wwv_all":
      applicable_coverpoints.remove(coverpoint)
      applicable_coverpoints.append("cp_custom_allVdOverlapTopVs1_vd_vs1_lmul1")
      applicable_coverpoints.append("cp_custom_allVdOverlapTopVs1_vd_vs1_lmul2")
      applicable_coverpoints.append("cp_custom_allVdOverlapTopVs1_vd_vs1_lmul4")
    elif coverpoint == "cp_custom_wvx_all":
      applicable_coverpoints.remove(coverpoint)
      applicable_coverpoints.append("cp_custom_allVdOverlapTopVs2_vd_vs2_lmul1")
      applicable_coverpoints.append("cp_custom_allVdOverlapTopVs2_vd_vs2_lmul2")
      applicable_coverpoints.append("cp_custom_allVdOverlapTopVs2_vd_vs2_lmul4")
    elif coverpoint == "cp_custom_wvx":
      applicable_coverpoints.remove(coverpoint)
      applicable_coverpoints.append("cp_custom_vdOverlapTopVs2_vd_vs2_lmul1")
      applicable_coverpoints.append("cp_custom_vdOverlapTopVs2_vd_vs2_lmul2")
      applicable_coverpoints.append("cp_custom_vdOverlapTopVs2_vd_vs2_lmul4")
    elif coverpoint == "cp_custom_wwv":
      applicable_coverpoints.remove(coverpoint)
      applicable_coverpoints.append("cp_custom_vdOverlapTopVs1_vd_vs1_lmul1")
      applicable_coverpoints.append("cp_custom_vdOverlapTopVs1_vd_vs1_lmul2")
      applicable_coverpoints.append("cp_custom_vdOverlapTopVs1_vd_vs1_lmul4")
    elif (coverpoint in ["cp_custom_vext2", "cp_custom_vext4", "cp_custom_vext8"]):
      applicable_coverpoints.remove(coverpoint)
      vext = coverpoint[-1]
      applicable_coverpoints.append(f"cp_custom_vext{vext}_overlapping_vd_vs2")
    elif coverpoint == "cp_custom_maskwrite_masked":
      applicable_coverpoints.remove(coverpoint)
      applicable_coverpoints.append("cp_custom_vmask_write_lmulge1")
      applicable_coverpoints.append("cp_custom_vmask_write_v0_masked")
    elif coverpoint == "cp_custom_maskwrite_unmasked":
      applicable_coverpoints.remove(coverpoint)
      applicable_coverpoints.append("cp_custom_vmask_write_lmulge1")
    elif coverpoint == "cp_custom_shift_vv":
      applicable_coverpoints.remove(coverpoint)
      applicable_coverpoints.append("cp_custom_vshift_upperbits_vs1_ones")
    elif coverpoint == "cp_custom_shift_vx":
      applicable_coverpoints.remove(coverpoint)
      applicable_coverpoints.append("cp_custom_vshift_upperbits_rs1_ones")
    elif coverpoint == "cp_custom_shift_wv":
      applicable_coverpoints.remove(coverpoint)
      applicable_coverpoints.append("cp_custom_vdOverlapBtmVs2_vd_vs2_lmul1")
      applicable_coverpoints.append("cp_custom_vdOverlapBtmVs2_vd_vs2_lmul2")
      applicable_coverpoints.append("cp_custom_vdOverlapBtmVs2_vd_vs2_lmul4")
      applicable_coverpoints.append("cp_custom_vshiftn_upperbits_vs1_ones")
    elif coverpoint == "cp_custom_shift_wx":
      applicable_coverpoints.remove(coverpoint)
      applicable_coverpoints.append("cp_custom_vdOverlapBtmVs2_vd_vs2_lmul1")
      applicable_coverpoints.append("cp_custom_vdOverlapBtmVs2_vd_vs2_lmul2")
      applicable_coverpoints.append("cp_custom_vdOverlapBtmVs2_vd_vs2_lmul4")
      applicable_coverpoints.append("cp_custom_vshiftn_upperbits_rs1_ones")
    elif coverpoint == "cp_custom_shift_wi":
      applicable_coverpoints.remove(coverpoint)
      applicable_coverpoints.append("cp_custom_vdOverlapBtmVs2_vd_vs2_lmul1")
      applicable_coverpoints.append("cp_custom_vdOverlapBtmVs2_vd_vs2_lmul2")
      applicable_coverpoints.append("cp_custom_vdOverlapBtmVs2_vd_vs2_lmul4")
    elif coverpoint == "cp_custom_shift_wi_all":
      applicable_coverpoints.remove(coverpoint)
      applicable_coverpoints.append("cp_custom_allVdOverlapBtmVs2_vd_vs2_lmul1")
      applicable_coverpoints.append("cp_custom_allVdOverlapBtmVs2_vd_vs2_lmul2")
      applicable_coverpoints.append("cp_custom_allVdOverlapBtmVs2_vd_vs2_lmul4")
    elif coverpoint in ["cp_custom_red", "cp_custom_wred"]:
      applicable_coverpoints.remove(coverpoint)
      applicable_coverpoints.append("cp_custom_element0Masked")
      applicable_coverpoints.append("cp_custom_vmask_write_v0_masked")
      if coverpoint[-4] == "w":
        lmuls = ["2", "4"]
        applicable_coverpoints.append("cp_custom_vreductionw_vd_vs1_emul_16")
      else:
        lmuls = ["2", "4", "8"]
      for lmul in lmuls:
        applicable_coverpoints.append(f"cp_custom_voffgroup_vd_lmul{lmul}")
        applicable_coverpoints.append(f"cp_custom_voffgroup_vs1_lmul{lmul}")
    elif coverpoint == "cp_custom_gprwrite":
      applicable_coverpoints.remove(coverpoint)
      applicable_coverpoints.append("cp_custom_gprWriting_vstart_eq_vl")
    elif coverpoint == "cp_custom_vmv_s_x":
      applicable_coverpoints.remove(coverpoint)
      for lmul in ["2", "4", "8"]:
        applicable_coverpoints.append(f"cp_custom_voffgroup_vd_lmul{lmul}")
    elif coverpoint == "cp_custom_vmv_x_s":
      applicable_coverpoints.remove(coverpoint)
      applicable_coverpoints.append("cp_custom_gprWriting_vstart_eq_vl")
      for lmul in ["2", "4", "8"]:
        applicable_coverpoints.append(f"cp_custom_voffgroup_vs2_lmul{lmul}")
    elif coverpoint == "cp_custom_vindexVV":
      applicable_coverpoints.remove(coverpoint)
      applicable_coverpoints.append("cp_custom_vindexedges_index_ge_vlmax")
      applicable_coverpoints.append("cp_custom_vindexedges_index_gt_vl_lt_vlmax")
    elif coverpoint == "cp_custom_vindexVX":
      applicable_coverpoints.remove(coverpoint)
      # cp_custom_vindexVX_rs1_not_truncated_32, cp_custom_vindexVX_rs1_not_truncated_64 are covered with cp_rs1_edges
  return applicable_coverpoints

#####################################               rewrite               #####################################


# TODO replace with better common functions
def getcovergroups(coverdefdir, coverfiles, xlen):
  coverpoints = {}
  curinstr = ""
  mode = "both"
  ingroup = False
  for coverfile in coverfiles:
    coverfile = coverdefdir + "/" + coverfile + "_coverage.svh"
    f = open(coverfile)
    for line in f:
      if (re.search("covergroup .* with", line)):
        ingroup = True
      if (re.search("endgroup", line)):
        ingroup = False
      if ((not ingroup) and re.search('`ifdef XLEN32', line)):
        mode = 32
      if ((not ingroup) and re.search('`ifdef XLEN64', line)):
        mode = 64
      # only look for coverpoints if we are of the proper xlen
      #print("mode: " + str(mode) + " xlen: " + str(xlen) + " " + line)
      if (mode == "both" or mode == xlen):
        m = re.search(r'covergroup.*?_(.*?)_cg', line)
        if (m):
          curinstr = m.group(1).replace("_", ".")
          # print(f'instr is: {curinstr}')
          coverpoints[curinstr] = []
        m = re.search(r"\s*(\S+) :", line)
        if (m):
          # print(f'coverpoint: {m.group(1)}')
          coverpoints[curinstr].append(m.group(1))
    f.close()
    return coverpoints

def getExtensions():
  extensions = []
  path = ARCH_VERIF+"/fcov/unpriv"
  for (dirpath, dirnames, filenames) in os.walk(path):
    for filename in filenames:
      m = re.search("(.*)_coverage.svh", filename)
      if (m is not None):
        ext = m.group(1)
        if 'V' in ext or 'v' in ext:
          extensions.append(ext)
  return extensions

if __name__ == '__main__':
  common.writeLine        = writeLine

  # TODO: auipc missing, check whatelse is missing in ^these^ types

  author = "kacassidy@g.hmc.edu"
  xlens = [32, 64]
  numrand = 3
  edges = []

  # setup
  seed(0) # make tests reproducible

  # generate files for each test
  for xlen in xlens:
    # extensions = getExtensions() # find all extensions in
    testplans = readTestplans()
    extensions = list(testplans.keys())
    maxreg = 31 # I uses registers x0-x31

    for extension in extensions:
      setExtension(extension)
      setXlen(xlen)

      coverdefdir = f"{ARCH_VERIF}/fcov/unpriv"
      coverfiles = [extension]
      #coverpoints = getcovergroups(coverdefdir, coverfiles, xlen)
      pathname = f"{ARCH_VERIF}/tests/rv{xlen}i/{extension}"

      print("Generating tests for " + pathname)

      if (xlen == 32):
        storecmd = "sw"
        wordsize = 4
      else:
        storecmd = "sd"
        wordsize = 8

      redgesv = [0, 1, 2, 2**xlen-1, 2**xlen-2, 2**(xlen-1), 2**(xlen-1)+1, 2**(xlen-1)-1, 2**(xlen-1)-2, sum(1 << i for i in range(xlen) if i % 2 == 0), sum(1 << i for i in range(xlen) if i % 2 == 1)]
      if (xlen == 32):
        redgesv = redgesv + [0b01011011101111001000100001110010, 0b10101010101010101010101010101010, 0b01010101010101010101010101010101]
      else:
        redgesv = redgesv + [0b0101101110111100100010000111011101100011101011101000011011110010, # random
                            0b1010101010101010101010101010101010101010101010101010101010101010, # walking odd
                            0b0101010101010101010101010101010101010101010101010101010101010101, # walking even
                            0b0000000000000000000000000000000011111111111111111111111111111111, # Wmax
                            0b0000000000000000000000000000000011111111111111111111111111111110, # Wmaxm1
                            0b0000000000000000000000000000000100000000000000000000000000000000, # Wmaxp1
                            0b0000000000000000000000000000000100000000000000000000000000000001] # Wmaxp2

      redges_ls_e8  = [-2, -1, 0, 1, 2]
      redges_ls_e16 = [-4, -2, 0, 2, 4]
      redges_ls_e32 = [-8, -4, 0, 4, 8]
      redges_ls_e64 = [-16,-8, 0, 8,16]

      # global NaNBox_tests
      NaNBox_tests = False

      # cmd = "mkdir -p " + pathname + " ; rm -f " + pathname + "/*" # make directory and remove old tests in dir
      cmd = "mkdir -p " + pathname # make directory
      os.system(cmd)
      basepathname = pathname
      includeVData = " "

      for pattern in [r'/Vx(\d+)$', r'/Vls(\d+)$', r'/Vf(\d+)$', r'/Zvbb(\d+)$', r'/Zvkb(\d+)$', r'/Zvbc(\d+)$']:
        match = re.search(pattern, pathname)
        if match:
            sew = int(match.group(1))
            break
      else:
        sew = 8

      instructions = list(testplans[extension].keys())
      applicable_instructions = list(testplans[extension].keys())
      effewcp = "EFFEW" + str(sew)
      for test in instructions:
        if effewcp not in list(testplans[extension][test]):
          applicable_instructions.remove(test)

      for test in applicable_instructions:
      # print("Generating test for ", test, " with entries: ", coverpoints[test])

        newInstruction()

        if (test in imm_31):
          immedgesv = [0, 1, 2, 15, 16, 30, 31]
        else:
          immedgesv = [0, 1, 2, 14, 15, -1, -2, -15, -16]

        basename = extension + "-" + test
        fname = pathname + "/" + basename + ".S"
        tempfname = pathname + "/" + basename + "_temp.S"

        vdsew = sew * (2 if (test in vd_widen_ins) else 1)

        # print custom header part
        f = open(tempfname, "w")
        line = "///////////////////////////////////////////\n"
        f.write(line)
        line="// "+fname+ "\n// " + author + "\n"
        f.write(line)
        # Don't print creation date because this forces rebuild of files that are otherwise identical
        #line ="// Created " + str(datetime.now()) + "\n"
        #f.write(line)

        # insert generic header
        insertTemplate(test, getSigSpace(xlen,flen), "testgen_header.S", sew=sew, vdsew=vdsew)

        # add assembly lines to enable fp where needed
        if test in vfloattypes:
          float_en = "\n# set mstatus.FS to 10 to enable fp\nli t0,0x4000\ncsrs mstatus, t0\n\n"
          f.write(float_en)

        for pattern in [r'/Vx(\d+)$', r'/Vls(\d+)$', r'/Vf(\d+)$']:
          sew_match = re.search(pattern, pathname)
          if sew_match:
              sew = int(sew_match.group(1))
              break
        else:
          sew = 8

        setFlen(32)

        legalvlmuls = getLegalVlmul(maxELEN, minSEW_MIN, sew)

        # include ifdefs for widening/narrowing instr, which doesn't exist in the ELEN suite
        if (test in vd_widen_ins) or (test in vs2_widen_ins):
          if (sew == 8):
            f.write("#if ELEN > 8\n")
          elif (sew == 16):
            f.write("#if ELEN > 16\n")
          elif (sew == 32):
            f.write("#if ELEN > 32\n")
          elif (sew == 64):
            f.write("#if ELEN > 64\n")

        coverpoints = list(testplans[extension][test])
        applicable_coverpoints = coverpointInclusions(coverpoints)
        if test not in unsupported_tests:
          makeTest(applicable_coverpoints, test, sew=sew)

        if (test in vd_widen_ins) or (test in vs2_widen_ins):
          f.write("#endif\n")

        test_data = genVtestdata(test, sew)

        # print footer
        signatureWords = getSigSpace(xlen, flen) #figure out how many words are needed for signature
        insertTemplate(test, signatureWords, "testgen_footer.S", test_data=test_data)

        # Finish
        f.close()
        # if new file is different from old file, replace old file with new file
        if os.path.exists(fname):
          if filecmp.cmp(fname, tempfname): # files are the same
            os.system(f"rm {tempfname}") # remove temp file
          else:
            os.system(f"mv {tempfname} {fname}")
            print("Updated " + fname)
        else:
          os.system(f"mv {tempfname} {fname}")
