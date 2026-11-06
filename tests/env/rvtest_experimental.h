// Experimental RISC-V extensions header
// Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
// SPDX-License-Identifier: Apache-2.0
// Contains a macro for each instruction from an unratified RISC-V extension
// so tests can be compiled without requiring the experimental extensions to
// be implemented in the compiler


#ifndef RISCV_ARCH_TEST_EXPERIMENTAL_H
#define RISCV_ARCH_TEST_EXPERIMENTAL_H

#if defined(__ASSEMBLER__) && defined(ENABLE_EXPERIMENTAL_EXTENSIONS)

.macro beqi rs1, cimm, target
  .if \cimm == -1
    .insn b 0x63, 2, \rs1, x0, \target
  .else
    .insn b 0x63, 2, \rs1, x\cimm, \target
  .endif
.endm

.macro bnei rs1, cimm, target
  .if \cimm == -1
    .insn b 0x63, 3, \rs1, x0, \target
  .else
    .insn b 0x63, 3, \rs1, x\cimm, \target
  .endif
.endm

// Zvdot4a8i: assemble from the instruction fields so tests build without assembler support.
.macro RVTEST_REGNUM out, reg, pfx
  .irp i, 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31
    .ifc \reg, \pfx\i
      \out = \i
    .endif
  .endr
.endm

.macro RVTEST_VDOT4A funct3, funct6, vd, vs2, src1, src1_pfx, vm
  RVTEST_REGNUM .Lvdot4a_vd, \vd, v
  RVTEST_REGNUM .Lvdot4a_vs2, \vs2, v
  RVTEST_REGNUM .Lvdot4a_src1, \src1, \src1_pfx
  .insn 4, 0x57 | (.Lvdot4a_vd << 7) | (\funct3 << 12) | (.Lvdot4a_src1 << 15) | (.Lvdot4a_vs2 << 20) | (\vm << 25) | (\funct6 << 26)
.endm

.macro vdot4a.vv vd, vs2, src1, mask=
  .ifb \mask
    RVTEST_VDOT4A 2, 0x2c, \vd, \vs2, \src1, v, 1
  .else
    RVTEST_VDOT4A 2, 0x2c, \vd, \vs2, \src1, v, 0
  .endif
.endm

.macro vdot4a.vx vd, vs2, src1, mask=
  .ifb \mask
    RVTEST_VDOT4A 6, 0x2c, \vd, \vs2, \src1, x, 1
  .else
    RVTEST_VDOT4A 6, 0x2c, \vd, \vs2, \src1, x, 0
  .endif
.endm

.macro vdot4au.vv vd, vs2, src1, mask=
  .ifb \mask
    RVTEST_VDOT4A 2, 0x28, \vd, \vs2, \src1, v, 1
  .else
    RVTEST_VDOT4A 2, 0x28, \vd, \vs2, \src1, v, 0
  .endif
.endm

.macro vdot4au.vx vd, vs2, src1, mask=
  .ifb \mask
    RVTEST_VDOT4A 6, 0x28, \vd, \vs2, \src1, x, 1
  .else
    RVTEST_VDOT4A 6, 0x28, \vd, \vs2, \src1, x, 0
  .endif
.endm

.macro vdot4asu.vv vd, vs2, src1, mask=
  .ifb \mask
    RVTEST_VDOT4A 2, 0x2a, \vd, \vs2, \src1, v, 1
  .else
    RVTEST_VDOT4A 2, 0x2a, \vd, \vs2, \src1, v, 0
  .endif
.endm

.macro vdot4asu.vx vd, vs2, src1, mask=
  .ifb \mask
    RVTEST_VDOT4A 6, 0x2a, \vd, \vs2, \src1, x, 1
  .else
    RVTEST_VDOT4A 6, 0x2a, \vd, \vs2, \src1, x, 0
  .endif
.endm

.macro vdot4aus.vx vd, vs2, src1, mask=
  .ifb \mask
    RVTEST_VDOT4A 6, 0x2e, \vd, \vs2, \src1, x, 1
  .else
    RVTEST_VDOT4A 6, 0x2e, \vd, \vs2, \src1, x, 0
  .endif
.endm

#endif

#endif
