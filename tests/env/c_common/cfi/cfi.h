/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef COMMON_CFI_CFI_H
#define COMMON_CFI_CFI_H

/* ===================================================================
 * CFI (Zicfilp) instruction encodings and code-emission helpers
 *
 * Single authoritative source shared by the Zicfilp test suites
 * (cfi.Zicfilp and Hypervisor_Zicfilp), which dynamically build test
 * code sequences in a writable/executable region and need to emit
 * LPAD / RET / NOP instructions by writing raw instruction words.
 *
 * Self-contained (types.h only) and non-gated: usable by both HYP and
 * non-HYP suites. Include as "cfi/cfi.h" (resolved via the
 * framework-wide -I../common).
 * =================================================================== */

#include "types.h"

/* ===================================================================
 * Instruction encodings
 * =================================================================== */

/* LPAD is encoded as AUIPC x0, imm (opcode 0x17, rd=x0).
 * Full 32-bit: imm[31:12] | 00000 | 0010111. With label=0: 0x00000017. */
#define LPAD_INSN_WORD  0x00000017  /* LPAD with label=0 */

/* RET = jalr x0, ra, 0 */
#define RET_INSN_WORD   0x00008067

/* NOP = addi x0, x0, 0 */
#define NOP_INSN_WORD   0x00000013

/* ===================================================================
 * Emission helpers: write a raw instruction word at the given address
 * =================================================================== */

static inline void emit_lpad(void *addr)
{
    *(volatile uint32_t *)addr = LPAD_INSN_WORD;
}

static inline void emit_ret(void *addr)
{
    *(volatile uint32_t *)addr = RET_INSN_WORD;
}

static inline void emit_nop(void *addr)
{
    *(volatile uint32_t *)addr = NOP_INSN_WORD;
}

#endif /* COMMON_CFI_CFI_H */
