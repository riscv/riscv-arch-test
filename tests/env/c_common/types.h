/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef COMMON_TYPES_H
#define COMMON_TYPES_H

#ifndef __ASSEMBLER__

/* ===== Basic integer types ===== */
typedef signed char        int8_t;
typedef unsigned char      uint8_t;
typedef short              int16_t;
typedef unsigned short     uint16_t;
typedef int                int32_t;
typedef unsigned int       uint32_t;
typedef long long          int64_t;
typedef unsigned long long uint64_t;

/* ===== Pointer-width types (adapts to RV32/RV64) ===== */
#if __riscv_xlen == 64
typedef unsigned long long size_t;
typedef long long          ssize_t;
typedef unsigned long long uintptr_t;
typedef long long          intptr_t;
#define XLEN 64
#define PRIxPTR "llx"
#else
typedef unsigned int       size_t;
typedef int                ssize_t;
typedef unsigned int       uintptr_t;
typedef int                intptr_t;
#define XLEN 32
#define PRIxPTR "x"
#endif

/* ===== Boolean ===== */
#define bool  _Bool
#define true  ((_Bool)+1u)
#define false ((_Bool)+0u)

/* ===== NULL ===== */
#ifndef NULL
#define NULL ((void *)0)
#endif

/* ===== Bit manipulation helpers =====
 *
 * All macros cast to uintptr_t so results are XLEN-width:
 *   - On RV64, uintptr_t is 64-bit: full value preserved.
 *   - On RV32, uintptr_t is 32-bit: high bits truncate to 0,
 *     which is correct for single-CSR access (high-half bits
 *     are accessed via separate mstatush/envcfgh etc.).
 */
#define BIT(n)              ((uintptr_t)(1ULL << (n)))
#define BIT_MASK(off, len)  ((uintptr_t)(((1ULL << (len)) - 1) << (off)))
#define EXTRACT_FIELD(val, off, len) \
    (((uintptr_t)(val) >> (off)) & ((uintptr_t)(1ULL << (len)) - 1))
#define INSERT_FIELD(val, off, len, field) \
    (((uintptr_t)(val) & ~BIT_MASK(off, len)) | (((uintptr_t)(field) << (off)) & BIT_MASK(off, len)))

/* Sign-extension of a narrow value to XLEN, matching the RISC-V
 * LoadSignExtend semantics that load-reserved / load-acquire and the
 * byte/half/word AMO and CAS results obey (norm:lr_sc_rv64,
 * norm:zalasr_sign_extend, norm:Zacas_amocas_*). The value is first
 * narrowed to the signed type of the operand width, then widened to
 * intptr_t and reinterpreted as uintptr_t so the result is XLEN-wide:
 *   SEXT_B - 8-bit  operand (int8_t)
 *   SEXT_H - 16-bit operand (int16_t)
 *   SEXT_W - 32-bit operand (int32_t)
 * These are the single authoritative definitions; atomic-extension
 * suites must reuse them instead of redefining suite-local copies. */
#define SEXT_B(v)           ((uintptr_t)(intptr_t)(int8_t)(v))
#define SEXT_H(v)           ((uintptr_t)(intptr_t)(int16_t)(v))
#define SEXT_W(v)           ((uintptr_t)(intptr_t)(int32_t)(v))

/* Snapshot of a trap record (see trap_snapshot() in trap.c): saved by
 * flows where one hardware event can produce multiple handler records
 * (e.g. Ssdbltrp double-trap escalation on broken implementations). */
typedef struct {
    bool      triggered;
    unsigned  priv_level;
    uintptr_t cause;
    uintptr_t epc;
    uintptr_t tval;
    uintptr_t status_snap;
} trap_snapshot_t;

#endif /* __ASSEMBLER__ */

#endif /* COMMON_TYPES_H */
