/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef COMMON_CMO_CMO_H
#define COMMON_CMO_CMO_H

/* ===================================================================
 * RISC-V CMO (Cache Management Operations) Definitions
 *
 * Provides:
 *   - envcfg CBIE/CBCFE/CBZE field definitions
 *   - CBO instruction inline assembly macros
 *   - Prefetch instruction inline assembly macros
 *   - Cache block size discovery helpers
 *
 * Reference: SPEC/riscv-isa-manual/src/unpriv/cmo.adoc
 * =================================================================== */

#include "types.h"
#include "sm_defs.h"
#include "ss_defs.h"
#include "tsbi/tsbi.h"   /* tsbi_csr_*: menvcfg is M-level */

/* ===================================================================
 * envcfg CMO field definitions
 *
 * menvcfg/senvcfg/henvcfg share the same bit positions for CMO fields:
 *   CBIE  [5:4]  - cbo.inval control (2-bit WARL)
 *   CBCFE [6]    - cbo.clean/cbo.flush enable
 *   CBZE  [7]    - cbo.zero enable
 * =================================================================== */

#define ENVCFG_CBIE_SHIFT   4
#define ENVCFG_CBIE_MASK    (3ULL << ENVCFG_CBIE_SHIFT)  /* bits [5:4] */
#define ENVCFG_CBCFE        (1ULL << 6)                   /* bit [6] */
#define ENVCFG_CBZE         (1ULL << 7)                   /* bit [7] */

/* CBIE encoding values */
#define CBIE_DISABLE        0   /* 00: raise exception */
#define CBIE_FLUSH          1   /* 01: perform flush instead of invalidate */
#define CBIE_RESERVED       2   /* 10: reserved */
#define CBIE_INVAL          3   /* 11: perform invalidate */

/* ===================================================================
 * CBO Instruction Encodings
 *
 * All Zicbom/Zicboz instructions use MISC-MEM opcode (0x0F):
 *   [6:0]   = 0x0F (MISC-MEM)
 *   [11:7]  = 0x00 (rd=0)
 *   [14:12] = 0x2  (funct3=CBO)
 *   [19:15] = rs1  (base address)
 *   [31:20] = operation
 *
 * Operation encodings:
 *   cbo.inval = 0x000
 *   cbo.clean = 0x001
 *   cbo.flush = 0x002
 *   cbo.zero  = 0x004
 * =================================================================== */

#define CBO_OPCODE    0x0F
#define CBO_FUNCT3    0x2
#define CBO_OP_INVAL  0x000
#define CBO_OP_CLEAN  0x001
#define CBO_OP_FLUSH  0x002
#define CBO_OP_ZERO   0x004

/* Construct a CBO instruction word */
#define CBO_INSN(op, rs1_num) \
    ((uint32_t)(CBO_OPCODE) | \
     ((uint32_t)(CBO_FUNCT3) << 12) | \
     ((uint32_t)(rs1_num) << 15) | \
     ((uint32_t)(op) << 20))

/* ===================================================================
 * Prefetch Instruction Encodings (Zicbop)
 *
 * Encoded as ORI with rd=0:
 *   [6:0]   = 0x13 (OP-IMM)
 *   [11:7]  = 0x00 (rd=0, also imm[4:0]=0)
 *   [14:12] = 0x6  (funct3=ORI)
 *   [19:15] = rs1  (base address)
 *   [31:20] = imm[11:0] where imm[11:5] encodes prefetch type
 *
 * Prefetch type (imm[11:5]):
 *   prefetch.i = 0x00
 *   prefetch.r = 0x01
 *   prefetch.w = 0x03
 * =================================================================== */

#define PREFETCH_OPCODE   0x13
#define PREFETCH_FUNCT3   0x6
#define PREFETCH_TYPE_I   0x00
#define PREFETCH_TYPE_R   0x01
#define PREFETCH_TYPE_W   0x03

/* ===================================================================
 * CBO Instruction Macros (inline assembly)
 *
 * These macros emit the actual CBO instructions using .insn
 * directive to avoid assembler version dependencies.
 * =================================================================== */

/**
 * cbo.inval - Invalidate cache block containing address in rs1
 *
 * Encoding: 0x0000200F | (rs1 << 15)
 */
#define CBO_INVAL(addr) ({ \
    register uintptr_t __rs1 asm("a0") = (uintptr_t)(addr); \
    asm volatile(".insn i 0x0F, 0x2, x0, %0, 0x000" :: "r"(__rs1) : "memory"); \
})

/**
 * cbo.clean - Clean cache block containing address in rs1
 *
 * Encoding: 0x0010200F | (rs1 << 15)
 */
#define CBO_CLEAN(addr) ({ \
    register uintptr_t __rs1 asm("a0") = (uintptr_t)(addr); \
    asm volatile(".insn i 0x0F, 0x2, x0, %0, 0x001" :: "r"(__rs1) : "memory"); \
})

/**
 * cbo.flush - Flush cache block containing address in rs1
 *
 * Encoding: 0x0020200F | (rs1 << 15)
 */
#define CBO_FLUSH(addr) ({ \
    register uintptr_t __rs1 asm("a0") = (uintptr_t)(addr); \
    asm volatile(".insn i 0x0F, 0x2, x0, %0, 0x002" :: "r"(__rs1) : "memory"); \
})

/**
 * cbo.zero - Zero cache block containing address in rs1
 *
 * Encoding: 0x0040200F | (rs1 << 15)
 */
#define CBO_ZERO(addr) ({ \
    register uintptr_t __rs1 asm("a0") = (uintptr_t)(addr); \
    asm volatile(".insn i 0x0F, 0x2, x0, %0, 0x004" :: "r"(__rs1) : "memory"); \
})

/* ===================================================================
 * Prefetch Instruction Macros (Zicbop)
 *
 * prefetch.{r,w,i} offset(base)
 * Encoded as ORI with rd=0, imm = (type << 5) | (offset & 0xFE0)
 * =================================================================== */

/**
 * prefetch.r - Prefetch for data read
 */
#define PREFETCH_R(addr) ({ \
    register uintptr_t __rs1 asm("a0") = (uintptr_t)(addr); \
    asm volatile(".insn i 0x13, 0x6, x0, %0, 0x020" :: "r"(__rs1) : "memory"); \
})

/**
 * prefetch.w - Prefetch for data write
 */
#define PREFETCH_W(addr) ({ \
    register uintptr_t __rs1 asm("a0") = (uintptr_t)(addr); \
    asm volatile(".insn i 0x13, 0x6, x0, %0, 0x060" :: "r"(__rs1) : "memory"); \
})

/**
 * prefetch.i - Prefetch for instruction fetch
 */
#define PREFETCH_I(addr) ({ \
    register uintptr_t __rs1 asm("a0") = (uintptr_t)(addr); \
    asm volatile(".insn i 0x13, 0x6, x0, %0, 0x000" :: "r"(__rs1) : "memory"); \
})

/* ===================================================================
 * envcfg CMO field access helpers
 *
 * menvcfg is M-level. Under the S-mode-normal (T-SBI) execution model the
 * suites run in S/HS-mode, where a bare csrr/csrw menvcfg raises
 * illegal-instruction, so the menvcfg_* helpers go through the tsbi_csr_*
 * proxy. senvcfg/henvcfg are S/HS-level and stay direct (they are gated by
 * Smstateen ENVCFG, which the suites open via hyp_enable_envcfg_access()).
 * =================================================================== */

static inline uintptr_t menvcfg_get_cbie(void)
{
    uintptr_t val = tsbi_csr_read(CSR_MENVCFG);
    return (val & ENVCFG_CBIE_MASK) >> ENVCFG_CBIE_SHIFT;
}

static inline void menvcfg_set_cbie(unsigned cbie)
{
    uintptr_t val = tsbi_csr_read(CSR_MENVCFG);
    val = (val & ~ENVCFG_CBIE_MASK) | ((uintptr_t)cbie << ENVCFG_CBIE_SHIFT);
    tsbi_csr_write(CSR_MENVCFG, val);
}

static inline uintptr_t menvcfg_get_cbcfe(void)
{
    uintptr_t val = tsbi_csr_read(CSR_MENVCFG);
    return (val & ENVCFG_CBCFE) ? 1 : 0;
}

static inline void menvcfg_set_cbcfe(unsigned en)
{
    if (en)
        tsbi_csr_set(CSR_MENVCFG, ENVCFG_CBCFE);
    else
        tsbi_csr_clear(CSR_MENVCFG, ENVCFG_CBCFE);
}

static inline uintptr_t menvcfg_get_cbze(void)
{
    uintptr_t val = tsbi_csr_read(CSR_MENVCFG);
    return (val & ENVCFG_CBZE) ? 1 : 0;
}

static inline void menvcfg_set_cbze(unsigned en)
{
    if (en)
        tsbi_csr_set(CSR_MENVCFG, ENVCFG_CBZE);
    else
        tsbi_csr_clear(CSR_MENVCFG, ENVCFG_CBZE);
}

static inline uintptr_t senvcfg_get_cbie(void)
{
    uintptr_t val;
    asm volatile("csrr %0, 0x10A" : "=r"(val));
    return (val & ENVCFG_CBIE_MASK) >> ENVCFG_CBIE_SHIFT;
}

static inline void senvcfg_set_cbie(unsigned cbie)
{
    uintptr_t val;
    asm volatile("csrr %0, 0x10A" : "=r"(val));
    val = (val & ~ENVCFG_CBIE_MASK) | ((uintptr_t)cbie << ENVCFG_CBIE_SHIFT);
    asm volatile("csrw 0x10A, %0" :: "r"(val));
}

static inline uintptr_t senvcfg_get_cbcfe(void)
{
    uintptr_t val;
    asm volatile("csrr %0, 0x10A" : "=r"(val));
    return (val & ENVCFG_CBCFE) ? 1 : 0;
}

static inline void senvcfg_set_cbcfe(unsigned en)
{
    if (en)
        asm volatile("csrs 0x10A, %0" :: "r"(ENVCFG_CBCFE));
    else
        asm volatile("csrc 0x10A, %0" :: "r"(ENVCFG_CBCFE));
}

static inline uintptr_t senvcfg_get_cbze(void)
{
    uintptr_t val;
    asm volatile("csrr %0, 0x10A" : "=r"(val));
    return (val & ENVCFG_CBZE) ? 1 : 0;
}

static inline void senvcfg_set_cbze(unsigned en)
{
    if (en)
        asm volatile("csrs 0x10A, %0" :: "r"(ENVCFG_CBZE));
    else
        asm volatile("csrc 0x10A, %0" :: "r"(ENVCFG_CBZE));
}

/* henvcfg (CSR 0x60A) - Hypervisor envcfg; same CBIE/CBCFE/CBZE layout.
 * Completes the menvcfg/senvcfg/henvcfg accessor triple so Hypervisor
 * CMO suites (Zicbom/Zicbop/Zicboz) need not redefine them locally. */
static inline uintptr_t henvcfg_get_cbie(void)
{
    uintptr_t val;
    asm volatile("csrr %0, 0x60A" : "=r"(val));
    return (val & ENVCFG_CBIE_MASK) >> ENVCFG_CBIE_SHIFT;
}

static inline void henvcfg_set_cbie(unsigned cbie)
{
    uintptr_t val;
    asm volatile("csrr %0, 0x60A" : "=r"(val));
    val = (val & ~ENVCFG_CBIE_MASK) | ((uintptr_t)cbie << ENVCFG_CBIE_SHIFT);
    asm volatile("csrw 0x60A, %0" :: "r"(val));
}

static inline uintptr_t henvcfg_get_cbcfe(void)
{
    uintptr_t val;
    asm volatile("csrr %0, 0x60A" : "=r"(val));
    return (val & ENVCFG_CBCFE) ? 1 : 0;
}

static inline void henvcfg_set_cbcfe(unsigned en)
{
    if (en)
        asm volatile("csrs 0x60A, %0" :: "r"(ENVCFG_CBCFE));
    else
        asm volatile("csrc 0x60A, %0" :: "r"(ENVCFG_CBCFE));
}

static inline uintptr_t henvcfg_get_cbze(void)
{
    uintptr_t val;
    asm volatile("csrr %0, 0x60A" : "=r"(val));
    return (val & ENVCFG_CBZE) ? 1 : 0;
}

static inline void henvcfg_set_cbze(unsigned en)
{
    if (en)
        asm volatile("csrs 0x60A, %0" :: "r"(ENVCFG_CBZE));
    else
        asm volatile("csrc 0x60A, %0" :: "r"(ENVCFG_CBZE));
}

/* ===================================================================
 * CBO instruction decode from stval / htinst
 *
 * Per SPEC, a CBO virtual-instruction trap writes stval as either 0 or
 * the faulting instruction encoding. When non-zero, verify the encoding
 * matches a cbo.* instruction of the given operation:
 *   bits [6:0]  = 0x0F (MISC-MEM opcode)
 *   bits [14:12] = 2    (funct3)
 *   bits [31:20] = operation (CBO_OP_INVAL/CLEAN/FLUSH/ZERO)
 * Returns true when stval==0 (implementation writes no encoding).
 * =================================================================== */
static inline bool stval_is_cbo_insn(uintptr_t stval, uint32_t operation)
{
    if (stval == 0)
        return true;
    uint32_t expected = (operation << 20) | (2 << 12) | 0x0F;
    uint32_t mask = (0xFFF << 20) | (7 << 12) | 0x7F; /* op+funct3+opcode */
    return (stval & mask) == expected;
}

/* ===================================================================
 * Cache block size
 *
 * The cache block size is implementation-specific. On most platforms
 * it is 64 bytes. This default can be overridden by platform config.
 * =================================================================== */

#ifndef CMO_CACHE_BLOCK_SIZE
#define CMO_CACHE_BLOCK_SIZE  64
#endif

/* Align address down to cache block boundary */
#define CBO_ALIGN_DOWN(addr) \
    ((uintptr_t)(addr) & ~((uintptr_t)CMO_CACHE_BLOCK_SIZE - 1))

/* Align address up to cache block boundary */
#define CBO_ALIGN_UP(addr) \
    (((uintptr_t)(addr) + CMO_CACHE_BLOCK_SIZE - 1) & ~((uintptr_t)CMO_CACHE_BLOCK_SIZE - 1))

#endif /* COMMON_CMO_CMO_H */
