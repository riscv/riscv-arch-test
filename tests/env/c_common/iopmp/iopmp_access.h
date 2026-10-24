/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef IOPMP_ACCESS_H
#define IOPMP_ACCESS_H

#include "types.h"
#include "mem_ops.h"
#include "iopmp_regs.h"

/* ===================================================================
 * IOPMP MMIO Register Access Wrappers
 *
 * IOPMP registers are 32-bit MMIO. All accesses use mem_load32/mem_store32
 * to ensure correct bus transaction width.
 * =================================================================== */

static inline uint32_t iopmp_read(uintptr_t base, uint32_t offset)
{
    return mem_load32(base + offset);
}

static inline void iopmp_write(uintptr_t base, uint32_t offset, uint32_t val)
{
    mem_store32(base + offset, val);
}

/* ===================================================================
 * Entry Array Register Access
 *
 * Entry array is at base + ENTRYOFFSET (signed offset from VERSION).
 * Each entry occupies 16 bytes: addr(0), addrh(4), cfg(8), user_cfg(12).
 * =================================================================== */

static inline uint32_t iopmp_read_entry_addr(uintptr_t base, uint32_t entry_offset,
                                              unsigned int i)
{
    return iopmp_read(base, entry_offset + i * IOPMP_ENTRY_STRIDE +
                      IOPMP_ENTRY_ADDR_OFF);
}

static inline void iopmp_write_entry_addr(uintptr_t base, uint32_t entry_offset,
                                          unsigned int i, uint32_t val)
{
    iopmp_write(base, entry_offset + i * IOPMP_ENTRY_STRIDE +
                IOPMP_ENTRY_ADDR_OFF, val);
}

static inline uint32_t iopmp_read_entry_addrh(uintptr_t base, uint32_t entry_offset,
                                               unsigned int i)
{
    return iopmp_read(base, entry_offset + i * IOPMP_ENTRY_STRIDE +
                      IOPMP_ENTRY_ADDRH_OFF);
}

static inline void iopmp_write_entry_addrh(uintptr_t base, uint32_t entry_offset,
                                           unsigned int i, uint32_t val)
{
    iopmp_write(base, entry_offset + i * IOPMP_ENTRY_STRIDE +
                IOPMP_ENTRY_ADDRH_OFF, val);
}

static inline uint32_t iopmp_read_entry_cfg(uintptr_t base, uint32_t entry_offset,
                                             unsigned int i)
{
    return iopmp_read(base, entry_offset + i * IOPMP_ENTRY_STRIDE +
                      IOPMP_ENTRY_CFG_OFF);
}

static inline void iopmp_write_entry_cfg(uintptr_t base, uint32_t entry_offset,
                                         unsigned int i, uint32_t val)
{
    iopmp_write(base, entry_offset + i * IOPMP_ENTRY_STRIDE +
                IOPMP_ENTRY_CFG_OFF, val);
}

static inline uint32_t iopmp_read_entry_user_cfg(uintptr_t base,
                                                  uint32_t entry_offset,
                                                  unsigned int i)
{
    return iopmp_read(base, entry_offset + i * IOPMP_ENTRY_STRIDE +
                      IOPMP_ENTRY_USER_OFF);
}

static inline void iopmp_write_entry_user_cfg(uintptr_t base, uint32_t entry_offset,
                                              unsigned int i, uint32_t val)
{
    iopmp_write(base, entry_offset + i * IOPMP_ENTRY_STRIDE +
                IOPMP_ENTRY_USER_OFF, val);
}

/* ===================================================================
 * MDCFG Table Register Access (Format 0 only)
 * MDCFG(m) at base + 0x0800 + m * 4
 * =================================================================== */

static inline uint32_t iopmp_read_mdcfg(uintptr_t base, unsigned int m)
{
    return iopmp_read(base, IOPMP_MDCFG_BASE + m * IOPMP_MDCFG_STRIDE);
}

static inline void iopmp_write_mdcfg(uintptr_t base, unsigned int m, uint32_t val)
{
    iopmp_write(base, IOPMP_MDCFG_BASE + m * IOPMP_MDCFG_STRIDE, val);
}

/* ===================================================================
 * SRCMD Table Register Access (Format 0: indexed by RRID s)
 *
 * SRCMD_EN(s)   at base + 0x1000 + s * 32
 * SRCMD_ENH(s)  at base + 0x1004 + s * 32
 * SRCMD_R(s)    at base + 0x1008 + s * 32
 * SRCMD_RH(s)   at base + 0x100C + s * 32
 * SRCMD_W(s)    at base + 0x1010 + s * 32
 * SRCMD_WH(s)   at base + 0x1014 + s * 32
 * =================================================================== */

static inline uint32_t iopmp_read_srcmd_en(uintptr_t base, unsigned int s)
{
    return iopmp_read(base, IOPMP_SRCMD_BASE + s * IOPMP_SRCMD_STRIDE);
}

static inline void iopmp_write_srcmd_en(uintptr_t base, unsigned int s, uint32_t val)
{
    iopmp_write(base, IOPMP_SRCMD_BASE + s * IOPMP_SRCMD_STRIDE, val);
}

static inline uint32_t iopmp_read_srcmd_enh(uintptr_t base, unsigned int s)
{
    return iopmp_read(base, IOPMP_SRCMD_BASE + s * IOPMP_SRCMD_STRIDE + 4);
}

static inline void iopmp_write_srcmd_enh(uintptr_t base, unsigned int s, uint32_t val)
{
    iopmp_write(base, IOPMP_SRCMD_BASE + s * IOPMP_SRCMD_STRIDE + 4, val);
}

static inline uint32_t iopmp_read_srcmd_r(uintptr_t base, unsigned int s)
{
    return iopmp_read(base, IOPMP_SRCMD_BASE + s * IOPMP_SRCMD_STRIDE + 8);
}

static inline void iopmp_write_srcmd_r(uintptr_t base, unsigned int s, uint32_t val)
{
    iopmp_write(base, IOPMP_SRCMD_BASE + s * IOPMP_SRCMD_STRIDE + 8, val);
}

static inline uint32_t iopmp_read_srcmd_w(uintptr_t base, unsigned int s)
{
    return iopmp_read(base, IOPMP_SRCMD_BASE + s * IOPMP_SRCMD_STRIDE + 0x10);
}

static inline void iopmp_write_srcmd_w(uintptr_t base, unsigned int s, uint32_t val)
{
    iopmp_write(base, IOPMP_SRCMD_BASE + s * IOPMP_SRCMD_STRIDE + 0x10, val);
}

/* ===================================================================
 * SRCMD Table Register Access (Format 2: indexed by MD m)
 *
 * SRCMD_PERM(m)  at base + 0x1000 + m * 32
 * SRCMD_PERMH(m) at base + 0x1004 + m * 32
 * =================================================================== */

static inline uint32_t iopmp_read_srcmd_perm(uintptr_t base, unsigned int m)
{
    return iopmp_read(base, IOPMP_SRCMD_BASE + m * IOPMP_SRCMD_STRIDE);
}

static inline void iopmp_write_srcmd_perm(uintptr_t base, unsigned int m, uint32_t val)
{
    iopmp_write(base, IOPMP_SRCMD_BASE + m * IOPMP_SRCMD_STRIDE, val);
}

static inline uint32_t iopmp_read_srcmd_permh(uintptr_t base, unsigned int m)
{
    return iopmp_read(base, IOPMP_SRCMD_BASE + m * IOPMP_SRCMD_STRIDE + 4);
}

static inline void iopmp_write_srcmd_permh(uintptr_t base, unsigned int m, uint32_t val)
{
    iopmp_write(base, IOPMP_SRCMD_BASE + m * IOPMP_SRCMD_STRIDE + 4, val);
}

#endif /* IOPMP_ACCESS_H */
