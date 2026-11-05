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

// Zvabd funct6: vabd=0x15, vabdu=0x16, vwabda=0x3D, vwabdau=0x3E.
// Zvabd funct3: OPMVV=2 and OPMVX=6 for vabd/vabdu, OPIVV=0 and OPIVX=4 for vwabda/vwabdau.
// Operand order is vd, vs2, vs1/rs1, with an optional trailing v0.t that clears vm.
// `.insn r` rejects vector register names for OP-V, so resolve each operand to its
// 5-bit field value and emit the encoding directly.
.macro ZVABD_VREG out, r
  .set \out, -1
  .irp i,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31
    .ifc "\r","v\i"
      .set \out, \i
    .endif
  .endr
  .if \out < 0
    .error "Zvabd: expected a vector register, got \r"
  .endif
.endm

.macro ZVABD_XREG out, r
  .set \out, -1
  .irp i,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31
    .ifc "\r","x\i"
      .set \out, \i
    .endif
  .endr
  .if \out < 0
    .error "Zvabd: expected an integer register, got \r"
  .endif
.endm

.macro ZVABD_VM out, m
  .set \out, 1
  .ifc "\m","v0.t"
    .set \out, 0
  .endif
.endm

.macro ZVABD_WORD funct6, funct3, vd, vs2, op1, vm
  .word ((\funct6) << 26) | ((\vm) << 25) | ((\vs2) << 20) | ((\op1) << 15) | ((\funct3) << 12) | ((\vd) << 7) | 0x57
.endm

.macro vabd.vv vd, vs2, vs1, m=
  ZVABD_VREG _zvabd_vd, \vd
  ZVABD_VREG _zvabd_vs2, \vs2
  ZVABD_VREG _zvabd_op1, \vs1
  ZVABD_VM _zvabd_vm, \m
  ZVABD_WORD 0x15, 2, _zvabd_vd, _zvabd_vs2, _zvabd_op1, _zvabd_vm
.endm

.macro vabd.vx vd, vs2, rs1, m=
  ZVABD_VREG _zvabd_vd, \vd
  ZVABD_VREG _zvabd_vs2, \vs2
  ZVABD_XREG _zvabd_op1, \rs1
  ZVABD_VM _zvabd_vm, \m
  ZVABD_WORD 0x15, 6, _zvabd_vd, _zvabd_vs2, _zvabd_op1, _zvabd_vm
.endm

.macro vabdu.vv vd, vs2, vs1, m=
  ZVABD_VREG _zvabd_vd, \vd
  ZVABD_VREG _zvabd_vs2, \vs2
  ZVABD_VREG _zvabd_op1, \vs1
  ZVABD_VM _zvabd_vm, \m
  ZVABD_WORD 0x16, 2, _zvabd_vd, _zvabd_vs2, _zvabd_op1, _zvabd_vm
.endm

.macro vabdu.vx vd, vs2, rs1, m=
  ZVABD_VREG _zvabd_vd, \vd
  ZVABD_VREG _zvabd_vs2, \vs2
  ZVABD_XREG _zvabd_op1, \rs1
  ZVABD_VM _zvabd_vm, \m
  ZVABD_WORD 0x16, 6, _zvabd_vd, _zvabd_vs2, _zvabd_op1, _zvabd_vm
.endm

.macro vwabda.vv vd, vs2, vs1, m=
  ZVABD_VREG _zvabd_vd, \vd
  ZVABD_VREG _zvabd_vs2, \vs2
  ZVABD_VREG _zvabd_op1, \vs1
  ZVABD_VM _zvabd_vm, \m
  ZVABD_WORD 0x3D, 0, _zvabd_vd, _zvabd_vs2, _zvabd_op1, _zvabd_vm
.endm

.macro vwabda.vx vd, vs2, rs1, m=
  ZVABD_VREG _zvabd_vd, \vd
  ZVABD_VREG _zvabd_vs2, \vs2
  ZVABD_XREG _zvabd_op1, \rs1
  ZVABD_VM _zvabd_vm, \m
  ZVABD_WORD 0x3D, 4, _zvabd_vd, _zvabd_vs2, _zvabd_op1, _zvabd_vm
.endm

.macro vwabdau.vv vd, vs2, vs1, m=
  ZVABD_VREG _zvabd_vd, \vd
  ZVABD_VREG _zvabd_vs2, \vs2
  ZVABD_VREG _zvabd_op1, \vs1
  ZVABD_VM _zvabd_vm, \m
  ZVABD_WORD 0x3E, 0, _zvabd_vd, _zvabd_vs2, _zvabd_op1, _zvabd_vm
.endm

.macro vwabdau.vx vd, vs2, rs1, m=
  ZVABD_VREG _zvabd_vd, \vd
  ZVABD_VREG _zvabd_vs2, \vs2
  ZVABD_XREG _zvabd_op1, \rs1
  ZVABD_VM _zvabd_vm, \m
  ZVABD_WORD 0x3E, 4, _zvabd_vd, _zvabd_vs2, _zvabd_op1, _zvabd_vm
.endm

#endif

#endif
