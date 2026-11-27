/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef SMMTT_INSN_H
#define SMMTT_INSN_H

/* ===================================================================
 * Smsd -- MFENCE.PA / MINVAL.PA instruction encoding macros
 *
 * Source: SPEC/riscv-smmtt/chapter3.adoc.
 *
 * Both instructions share the R-type SYSTEM encoding:
 *   opcode = SYSTEM (0x73), funct3 = PRIV (0), rd = x0,
 *   rs1 = PADDR, rs2 = SDID, funct7 = <instruction>.
 *
 * This header is the single encoding authority for the whole SMMTT
 * family (Smsd / Smmpt / Smsdia / I-O MPT suites).
 *
 * ------------------------------------------------------------------
 * !!! UNCONFIRMED FUNCT7 ENCODING !!!
 *
 * chapter3.adoc draws MFENCE.PA / MINVAL.PA only as wavedrom field
 * diagrams; it labels the funct7 field with the instruction NAME but
 * does NOT give a numeric funct7 value, and the upstream spec renders
 * the same way. Per project rules the encoding must NOT be guessed.
 *
 * The funct7 defaults below are PLACEHOLDERS. They are chosen to avoid
 * colliding with allocated SYSTEM/funct3=0 encodings (ECALL 0x00,
 * EBREAK 0x01, SFENCE.VMA 0x09, SINVAL.VMA 0x0B, SFENCE.W.INVAL /
 * SFENCE.INVAL.IR 0x0C, HFENCE.VVMA 0x11, HFENCE.GVMA 0x31), so they
 * are safe to assemble but are architecturally meaningless.
 *
 * To exercise the instruction-dependent cases (e.g. Smsd test plan
 * Groups 4/5/6) on a real DUT:
 *   1. Fill in the official funct7 values, either by editing the
 *      defaults below or by building with
 *        make EXTRA_CFLAGS='-DMFENCE_PA_FUNC7=0xNN -DMINVAL_PA_FUNC7=0xMM'
 *   2. Build with -DSMSD_INSN_ENCODING_CONFIRMED so the tests stop
 *      skipping (SMSD_INSN_ENCODING_READY becomes 1).
 *
 * Until then every case that actually executes MFENCE.PA / MINVAL.PA
 * is gated on SMSD_INSN_ENCODING_READY and reports SKIP, so a wrong
 * placeholder can never masquerade as a DUT failure. Suites that only
 * issue the fence as part of MPT activation on a SMMTT-capable DUT
 * (mpt_activate) are gated by their own <EXT>_AVAILABLE capability.
 * ------------------------------------------------------------------
 * =================================================================== */

#include "smmtt_defs.h"

#ifndef MFENCE_PA_FUNC7
#define MFENCE_PA_FUNC7 0x7D   /* UNCONFIRMED placeholder -- see above */
#endif

#ifndef MINVAL_PA_FUNC7
#define MINVAL_PA_FUNC7 0x7E   /* UNCONFIRMED placeholder -- see above */
#endif

/* 1 only once the official funct7 values are supplied AND the builder
 * opts in with -DSMSD_INSN_ENCODING_CONFIRMED. */
#ifdef SMSD_INSN_ENCODING_CONFIRMED
#define SMSD_INSN_ENCODING_READY 1
#else
#define SMSD_INSN_ENCODING_READY 0
#endif

#ifndef __ASSEMBLER__

#include "types.h"

#define _SMMTT_STR(x)  #x
#define SMMTT_STR(x)   _SMMTT_STR(x)

/* Statement-expression form so the macros work inside PRIV_DO(...) and
 * EXPECT_NO_TRAP(...). "x0" is written literally for the rs1/rs2 = x0
 * cases: a general register holding 0 would mean rs!=x0 (a specific
 * PA/SDID of 0), which is a DIFFERENT architectural case. */

/* ---- MFENCE.PA: four rs1/rs2 combinations (norm:mfence_pa_cases) ---- */

/* rs1=x0, rs2=x0 : all levels of the MPTs for all supervisor domains */
#define MFENCE_PA_GG() \
    ({ asm volatile(".insn r 0x73, 0, " SMMTT_STR(MFENCE_PA_FUNC7) \
                    ", x0, x0, x0" ::: "memory"); })

/* rs1=PA, rs2=x0 : leaf MPT entries for PA, all supervisor domains */
#define MFENCE_PA_PA(pa) \
    ({ asm volatile(".insn r 0x73, 0, " SMMTT_STR(MFENCE_PA_FUNC7) \
                    ", x0, %0, x0" :: "r"((uintptr_t)(pa)) : "memory"); })

/* rs1=x0, rs2=SDID : all levels of the MPT for one supervisor domain */
#define MFENCE_PA_SDID(sdid) \
    ({ asm volatile(".insn r 0x73, 0, " SMMTT_STR(MFENCE_PA_FUNC7) \
                    ", x0, x0, %0" :: "r"((uintptr_t)(sdid)) : "memory"); })

/* rs1=PA, rs2=SDID : leaf MPT entries for PA of one supervisor domain */
#define MFENCE_PA_PA_SDID(pa, sdid) \
    ({ asm volatile(".insn r 0x73, 0, " SMMTT_STR(MFENCE_PA_FUNC7) \
                    ", x0, %0, %1" \
                    :: "r"((uintptr_t)(pa)), "r"((uintptr_t)(sdid)) : "memory"); })

/* ---- MINVAL.PA: same operand forms, batched invalidation ---- */

#define MINVAL_PA_GG() \
    ({ asm volatile(".insn r 0x73, 0, " SMMTT_STR(MINVAL_PA_FUNC7) \
                    ", x0, x0, x0" ::: "memory"); })

#define MINVAL_PA_PA(pa) \
    ({ asm volatile(".insn r 0x73, 0, " SMMTT_STR(MINVAL_PA_FUNC7) \
                    ", x0, %0, x0" :: "r"((uintptr_t)(pa)) : "memory"); })

#define MINVAL_PA_SDID(sdid) \
    ({ asm volatile(".insn r 0x73, 0, " SMMTT_STR(MINVAL_PA_FUNC7) \
                    ", x0, x0, %0" :: "r"((uintptr_t)(sdid)) : "memory"); })

#define MINVAL_PA_PA_SDID(pa, sdid) \
    ({ asm volatile(".insn r 0x73, 0, " SMMTT_STR(MINVAL_PA_FUNC7) \
                    ", x0, %0, %1" \
                    :: "r"((uintptr_t)(pa)), "r"((uintptr_t)(sdid)) : "memory"); })

#endif /* __ASSEMBLER__ */

#endif /* SMMTT_INSN_H */
