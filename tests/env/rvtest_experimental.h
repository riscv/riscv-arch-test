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

#endif

#endif
