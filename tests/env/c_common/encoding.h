/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef COMMON_ENCODING_H
#define COMMON_ENCODING_H

/* ===================================================================
 * RISC-V Encoding — Umbrella Header
 *
 * This header provides the full set of RISC-V privileged encoding
 * constants and inline CSR access macros. It is the single include
 * point for all C and assembly source files in the framework.
 *
 * Contents are split into focused sub-headers by privilege level:
 *   sm_defs.h     — M-mode CSR addresses and bit fields
 *   ss_defs.h     — S-mode CSR addresses and bit fields
 *   sh_defs.h     — Hypervisor CSR addresses and bit fields
 *   cause_defs.h  — Exception / interrupt cause codes
 *
 * This file retains: CSR access macros (including the RV32 split-pair
 * 64-bit logical view), privilege level constants, unprivileged CSRs,
 * PM common constants, shared stateen bits, and cross-level utility macros.
 * =================================================================== */

#include "types.h"
#include "sm_defs.h"
#include "ss_defs.h"
#include "sh_defs.h"
#include "cause_defs.h"

/* ===================================================================
 * Inline CSR access macros (compile-time CSR name)
 *
 * These macros generate csrr/csrw/csrs/csrc instructions with
 * compile-time constant CSR addresses. For runtime CSR address
 * access, use csr_read()/csr_write() from csr_accessors.c.
 *
 * Guarded by __ASSEMBLER__ — not available in assembly files.
 * =================================================================== */
#ifndef __ASSEMBLER__

#ifndef _CSR_STR
#define _CSR_STR(s) #s
#endif
#ifndef CSR_STR
#define CSR_STR(s)  _CSR_STR(s)
#endif

#if __riscv_xlen == 64
#define CSRR(csr) ({ \
    uint64_t _v; \
    asm volatile("csrr %0, " CSR_STR(csr) : "=r"(_v) :: "memory"); \
    _v; \
})
#else
#define CSRR(csr) ({ \
    uint32_t _v; \
    asm volatile("csrr %0, " CSR_STR(csr) : "=r"(_v) :: "memory"); \
    _v; \
})
#endif

#define CSRW(csr, val) \
    asm volatile("csrw " CSR_STR(csr) ", %0" :: "rK"(val) : "memory")

#define CSRS(csr, val) \
    asm volatile("csrs " CSR_STR(csr) ", %0" :: "rK"(val) : "memory")

#define CSRC(csr, val) \
    asm volatile("csrc " CSR_STR(csr) ", %0" :: "rK"(val) : "memory")

/* -------------------------------------------------------------------
 * 64-bit logical view of a split CSR pair
 *
 * On RV32 many architectural 64-bit CSRs are split into a low half and a
 * separate high-half register.  These macros present the pair as one
 * uint64_t so test code never needs `#if __riscv_xlen == 32`; on RV64 they
 * collapse to a single access and csr_hi is ignored.
 *
 * THE HIGH HALF IS NOT DERIVABLE FROM THE LOW HALF -- the offset differs by
 * register family, so callers must pass both addresses:
 *   +0x80   counters         cycle 0xC00 -> cycleh 0xC80, mcycle 0xB00 -> 0xB80
 *   +0x10   config           menvcfg 0x30A -> menvcfgh 0x31A, stimecmp 0x14D -> 0x15D
 *   +0x400  event selectors  mhpmevent3 0x323 -> mhpmeventh3 0x723
 * The macro NAME is not derivable either: counters and config append "H"
 * (CSR_MCYCLEH) while mhpmevent inflects it (CSR_MHPMEVENTH3).
 *
 * NOT ATOMIC ON RV32.  CSR_READ64 is two independent accesses, so it MUST NOT
 * be used on a register that changes by itself (cycle / time / instret /
 * mhpmcounterN): a carry out of the low half between the two reads yields a
 * value that never existed, and only ever on RV32.  Use CSR_READ64_ATOMIC for
 * live counters and CSR_READ64 for STATIC config pairs (menvcfg, mstateen0,
 * stimecmp, ...).  On RV64 the two are identical.
 *
 * Bit masks need the same XLEN treatment as the addresses: a bit-63 mask is
 * meaningless on RV32, where that bit lives at position 31 of the high half.
 * ------------------------------------------------------------------- */
#if __riscv_xlen == 32

#define CSR_READ64(csr_lo, csr_hi) ({ \
    uint32_t _lo = CSRR(csr_lo); \
    uint32_t _hi = CSRR(csr_hi); \
    ((uint64_t)_hi << 32) | (uint64_t)_lo; \
})

/* Same result as CSR_READ64, but safe for a register that increments by
 * itself (cycle / time / instret / mcycle / minstret / mhpmcounterN): the low
 * half can carry into the high half between the two reads, so the high half is
 * re-read and the sequence retried until it is stable.  This is the ordering
 * the privileged spec recommends.  Use CSR_READ64 for static config pairs and
 * this one for live counters -- on RV64 they are identical. */
#define CSR_READ64_ATOMIC(csr_lo, csr_hi) ({ \
    uint32_t _hi, _lo, _hi2; \
    do { \
        _hi  = CSRR(csr_hi); \
        _lo  = CSRR(csr_lo); \
        _hi2 = CSRR(csr_hi); \
    } while (_hi != _hi2); \
    ((uint64_t)_hi << 32) | (uint64_t)_lo; \
})

#define CSR_WRITE64(csr_lo, csr_hi, val64) ({ \
    CSRW(csr_lo, (uint32_t)(val64)); \
    CSRW(csr_hi, (uint32_t)((uint64_t)(val64) >> 32)); \
})

/* bits_lo / bits_hi select which half each bit lands in; on RV64 bits_hi is
 * unused because everything is in the single register. */
#define CSR_SET64(csr_lo, csr_hi, bits_lo, bits_hi) ({ \
    CSRS(csr_lo, bits_lo); \
    CSRS(csr_hi, bits_hi); \
})

#define CSR_CLEAR64(csr_lo, csr_hi, bits_lo, bits_hi) ({ \
    CSRC(csr_lo, bits_lo); \
    CSRC(csr_hi, bits_hi); \
})

#else /* __riscv_xlen == 64 */

#define CSR_READ64(csr_lo, csr_hi) ({ \
    (uint64_t)CSRR(csr_lo); \
})

/* A single RV64 read is already atomic, so the two variants coincide. */
#define CSR_READ64_ATOMIC(csr_lo, csr_hi) CSR_READ64(csr_lo, csr_hi)

#define CSR_WRITE64(csr_lo, csr_hi, val64) ({ \
    CSRW(csr_lo, (uintptr_t)(val64)); \
})

#define CSR_SET64(csr_lo, csr_hi, bits, _bits_hi_unused) ({ \
    CSRS(csr_lo, (uintptr_t)(bits)); \
})

#define CSR_CLEAR64(csr_lo, csr_hi, bits, _bits_hi_unused) ({ \
    CSRC(csr_lo, (uintptr_t)(bits)); \
})

#endif /* __riscv_xlen */

/* SFENCE.VMA */
static inline void sfence_vma(void) {
    asm volatile("sfence.vma" ::: "memory");
}

#endif /* __ASSEMBLER__ */

/* ===================================================================
 * Privilege Level Definitions
 *
 * Encoding:
 *   PRIV_U  = 0   User mode
 *   PRIV_S  = 1   Supervisor mode
 *   PRIV_M  = 3   Machine mode
 *
 * Virtualized privilege levels (V=1) — used by hypervisor (H ext) tests.
 * The high bit (bit 2) marks V=1; low 2 bits hold the nominal privilege.
 *   PRIV_VU = 4   V=1, nominal U
 *   PRIV_VS = 5   V=1, nominal S
 * =================================================================== */

#define PRIV_U  0
#define PRIV_S  1
#define PRIV_M  3

#define PRIV_VU 4
#define PRIV_VS 5

/* ===================================================================
 * Ecall protocol for privilege switching (goto_priv)
 *
 * When goto_priv() needs to switch to a higher privilege level,
 * it issues an ecall with a0 = ECALL_GOTO_PRIV and a1 = target priv.
 * The trap handler checks ecall_args[0] to distinguish this from
 * test-triggered ecalls.
 * =================================================================== */
#define ECALL_GOTO_PRIV  1

/* ===================================================================
 * Unprivileged CSRs (U-mode read-only)
 * =================================================================== */

/* Floating-point Control and Status Register (F extension) */
#ifndef CSR_FCSR
#define CSR_FCSR        0x003
#endif

/* Entropy Source Register (Zkr) */
#ifndef CSR_SEED
#define CSR_SEED        0x015
#endif

/* seed CSR field definitions (Zkr) */
#define SEED_OPST_SHIFT     30
#define SEED_OPST_MASK      (0x3UL << SEED_OPST_SHIFT)
#define SEED_OPST_BIST      (0x0UL << SEED_OPST_SHIFT)  /* 00 */
#define SEED_OPST_WAIT      (0x1UL << SEED_OPST_SHIFT)  /* 01 */
#define SEED_OPST_ES16      (0x2UL << SEED_OPST_SHIFT)  /* 10 */
#define SEED_OPST_DEAD      (0x3UL << SEED_OPST_SHIFT)  /* 11 */
#define SEED_ENTROPY_MASK   0xFFFFUL
#define SEED_RESERVED_MASK  (0x3FUL << 24)

/* Supervisor Context Register (Sdtrig, gated by stateen0.CONTEXT) */
#ifndef CSR_SCONTEXT
#define CSR_SCONTEXT    0x5A8
#endif

/* Machine Context Register (Sdtrig, gated by mstateen0.CONTEXT) */
#ifndef CSR_MCONTEXT
#define CSR_MCONTEXT    0x7A8
#endif

/* Trigger Module CSRs (Sdtrig) */
#define CSR_TSELECT     0x7A0
#define CSR_TDATA1      0x7A1
#define CSR_TDATA2      0x7A2
#define CSR_TDATA3      0x7A3
#define CSR_TINFO       0x7A4
#define CSR_TCONTROL    0x7A5

/* Shadow Stack Pointer (Zicfiss) */
#define CSR_SSP         0x011

/* Base Counter CSRs (S/U-mode read-only) */
#define CSR_CYCLE       0xC00
#define CSR_TIME        0xC01
#define CSR_INSTRET     0xC02
/* Upper 32-bit halves (RV32 only; absent on RV64) */
#define CSR_CYCLEH      0xC80
#define CSR_TIMEH       0xC81
#define CSR_INSTRETH    0xC82

/* HPM Counter CSRs (S/U-mode read-only shadow) */
#define CSR_HPMCOUNTER3   0xC03
#define CSR_HPMCOUNTER4   0xC04
#define CSR_HPMCOUNTER5   0xC05
#define CSR_HPMCOUNTER6   0xC06
#define CSR_HPMCOUNTER7   0xC07
#define CSR_HPMCOUNTER8   0xC08
#define CSR_HPMCOUNTER9   0xC09
#define CSR_HPMCOUNTER10  0xC0A
#define CSR_HPMCOUNTER11  0xC0B
#define CSR_HPMCOUNTER12  0xC0C
#define CSR_HPMCOUNTER13  0xC0D
#define CSR_HPMCOUNTER14  0xC0E
#define CSR_HPMCOUNTER15  0xC0F
#define CSR_HPMCOUNTER16  0xC10
#define CSR_HPMCOUNTER17  0xC11
#define CSR_HPMCOUNTER18  0xC12
#define CSR_HPMCOUNTER19  0xC13
#define CSR_HPMCOUNTER20  0xC14
#define CSR_HPMCOUNTER21  0xC15
#define CSR_HPMCOUNTER22  0xC16
#define CSR_HPMCOUNTER23  0xC17
#define CSR_HPMCOUNTER24  0xC18
#define CSR_HPMCOUNTER25  0xC19
#define CSR_HPMCOUNTER26  0xC1A
#define CSR_HPMCOUNTER27  0xC1B
#define CSR_HPMCOUNTER28  0xC1C
#define CSR_HPMCOUNTER29  0xC1D
#define CSR_HPMCOUNTER30  0xC1E
#define CSR_HPMCOUNTER31  0xC1F

/* Parametric HPM counter CSR address by index n (3..31), S/U-mode read-only shadow */
#define CSR_HPMCOUNTER(n)   (CSR_HPMCOUNTER3 + ((n) - 3))

/* ===================================================================
 * Pointer Masking (PM) common constants
 * =================================================================== */
#define PMM_DISABLED    0   /* Pointer masking disabled (PMLEN=0) */
#define PMM_RESERVED    1   /* Reserved */
#define PMM_PMLEN7      2   /* PMLEN = XLEN-57 = 7 on RV64 */
#define PMM_PMLEN16     3   /* PMLEN = XLEN-48 = 16 on RV64 */

/* ===================================================================
 * Stateen shared bit definitions (common to M/H/S levels)
 * =================================================================== */

/* Cast to uintptr_t: on RV64 preserves full value; on RV32 the
 * high bits are 0 (high-half register access needed for bits >= 32). */
#define STATEEN_BIT63      ((uintptr_t)(1ULL << 63))
#define STATEEN_BIT58      ((uintptr_t)(1ULL << 58))

/* stateen0 shared bit definitions */
#define STATEEN0_C         ((uintptr_t)(1ULL << 0))
#define STATEEN0_FCSR      ((uintptr_t)(1ULL << 1))
#define STATEEN0_JVT       ((uintptr_t)(1ULL << 2))
#define STATEEN0_CONTEXT   ((uintptr_t)(1ULL << 57))
#define STATEEN0_IMSIC     ((uintptr_t)(1ULL << 58))
#define STATEEN0_AIA       ((uintptr_t)(1ULL << 59))
#define STATEEN0_CSRIND    ((uintptr_t)(1ULL << 60))
#define STATEEN0_ENVCFG    ((uintptr_t)(1ULL << 62))
#define STATEEN0_SE0       STATEEN_BIT63

/* ===================================================================
 * Cross-level utility macros
 * =================================================================== */

/* HGATP mode matches SATP mode numerically */
#define HGATP_MODE_FOR_SATP(satp_mode) (satp_mode)

/* ===================================================================
 * Instruction field extraction macros
 *
 * Standard RISC-V instruction-word field decoders, shared by suites
 * that inspect fetched/trapped instruction encodings (e.g. mtval or
 * htinst read-back). Argument i is a 32-bit instruction word.
 * =================================================================== */
#define INST_OPCODE(i)      ((i) & 0x7FUL)
#define INST_RD(i)          (((i) >> 7) & 0x1FUL)
#define INST_FUNCT3(i)      (((i) >> 12) & 0x7UL)
#define INST_RS1(i)         (((i) >> 15) & 0x1FUL)
#define INST_RS2(i)         (((i) >> 20) & 0x1FUL)
#define INST_FUNCT7(i)      (((i) >> 25) & 0x7FUL)
#define INST_IMM12(i)       (((i) >> 20) & 0xFFFUL)

#endif /* COMMON_ENCODING_H */
