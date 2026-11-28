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

// Match the parenthesized base operand to a register for the R-type encoding.
.macro ZILX_LOAD funct3, funct7, rd, base, index
  .set zilx_base_found, 0
  .irp base_reg, x0, x1, x2, x3, x4, x5, x6, x7, x8, x9, x10, x11, x12, x13, x14, x15, x16, x17, x18, x19, x20, x21, x22, x23, x24, x25, x26, x27, x28, x29, x30, x31, zero, ra, sp, gp, tp, t0, t1, t2, s0, fp, s1, a0, a1, a2, a3, a4, a5, a6, a7, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11, t3, t4, t5, t6
    .ifc \base, (\base_reg)
      .set zilx_base_found, 1
      .insn r 0x2f, \funct3, \funct7, \rd, \index, \base_reg
    .endif
  .endr
  .if zilx_base_found == 0
    .error "Zilx requires a parenthesized base register"
  .endif
.endm

.macro lxh rd, base, index
  ZILX_LOAD 1, 0x48, \rd, \base, \index
.endm

.macro lxw rd, base, index
  ZILX_LOAD 2, 0x48, \rd, \base, \index
.endm

.macro lxd rd, base, index
  ZILX_LOAD 3, 0x48, \rd, \base, \index
.endm

.macro lxhu rd, base, index
  ZILX_LOAD 5, 0x48, \rd, \base, \index
.endm

.macro lxwu rd, base, index
  ZILX_LOAD 6, 0x48, \rd, \base, \index
.endm

.macro lxsb rd, base, index
  ZILX_LOAD 0, 0x68, \rd, \base, \index
.endm

.macro lxsh rd, base, index
  ZILX_LOAD 1, 0x68, \rd, \base, \index
.endm

.macro lxsw rd, base, index
  ZILX_LOAD 2, 0x68, \rd, \base, \index
.endm

.macro lxsd rd, base, index
  ZILX_LOAD 3, 0x68, \rd, \base, \index
.endm

.macro lxsbu rd, base, index
  ZILX_LOAD 4, 0x68, \rd, \base, \index
.endm

.macro lxshu rd, base, index
  ZILX_LOAD 5, 0x68, \rd, \base, \index
.endm

.macro lxswu rd, base, index
  ZILX_LOAD 6, 0x68, \rd, \base, \index
.endm

.macro lxsuwb rd, base, index
  ZILX_LOAD 0, 0x78, \rd, \base, \index
.endm

.macro lxsuwh rd, base, index
  ZILX_LOAD 1, 0x78, \rd, \base, \index
.endm

.macro lxsuww rd, base, index
  ZILX_LOAD 2, 0x78, \rd, \base, \index
.endm

.macro lxsuwd rd, base, index
  ZILX_LOAD 3, 0x78, \rd, \base, \index
.endm

.macro lxsuwbu rd, base, index
  ZILX_LOAD 4, 0x78, \rd, \base, \index
.endm

.macro lxsuwhu rd, base, index
  ZILX_LOAD 5, 0x78, \rd, \base, \index
.endm

.macro lxsuwwu rd, base, index
  ZILX_LOAD 6, 0x78, \rd, \base, \index
.endm

#endif

#endif
