/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef HYP_DEFS_H
#define HYP_DEFS_H

/* ===================================================================
 * RISC-V Hypervisor Extension common definitions for G-stage tests
 *
 * Pulls together hgatp encoding, page-table layout (Sv-x4) and
 * page-table pool sizing used by common/hyp and the sv39x4
 * test suite.
 *
 * NOTE: hgatp / hstatus / cause-code numeric constants live in
 *       common/encoding.h to keep them available to inline asm
 *       and assembly code.  This header layers higher-level
 *       compile-time helpers on top of those constants.
 * =================================================================== */

#include "types.h"
#include "encoding.h"
#include "vm/vm_defs.h"

/* ===================================================================
 * hgatp construction macro (RV64 / HSXLEN=64)
 *
 *   bits [63:60]  MODE (4 bits, see HGATP_MODE_*)
 *   bits [59:44]  VMID (up to 14 bits used; VMIDLEN is impl-defined)
 *   bits [43:0]   PPN  (low 2 bits forced to 0 in Sv*x4 modes)
 * =================================================================== */
#define MAKE_HGATP(mode, vmid, ppn) \
    ((uintptr_t)( \
    (((uint64_t)(mode) << HGATP64_MODE_SHIFT) | \
     (((uint64_t)(vmid) & HGATP64_VMID_MASK) << HGATP64_VMID_SHIFT) | \
     ((uint64_t)(ppn)  & HGATP64_PPN_MASK))))

/* Convenience masks for extracting hgatp fields (read-back). */
#define HGATP_PPN_MASK   HGATP64_PPN_MASK
#define HGATP_VMID_MASK  (HGATP64_VMID_MASK << HGATP64_VMID_SHIFT)
#define HGATP_MODE_MASK  (0xFUL << HGATP64_MODE_SHIFT)

#define HGATP_GET_PPN(v)   ((uintptr_t)(v) & HGATP_PPN_MASK)
#define HGATP_GET_VMID(v)  (((uint64_t)(v) >> HGATP64_VMID_SHIFT) & HGATP64_VMID_MASK)
#define HGATP_GET_MODE(v)  (((uint64_t)(v) >> HGATP64_MODE_SHIFT) & 0xFUL)

/* ===================================================================
 * G-stage root page table layout
 *
 * Per the H-extension spec (norm:hgatp_mode_x4), the Sv*x4 root
 * page table is 16KB (4 contiguous 4KB pages) and must be 16KB
 * aligned. The top-level VPN field is 11 bits (2 wider than the
 * corresponding Sv* mode).
 * =================================================================== */
#define GPT_ROOT_PAGES      4
#define GPT_ROOT_SIZE       (GPT_ROOT_PAGES * PAGE_SIZE_4K)   /* 16KB */
#define GPT_ROOT_ALIGN      GPT_ROOT_SIZE                      /* 16KB */
#define GPT_ROOT_ENTRIES    (GPT_ROOT_SIZE / sizeof(uintptr_t)) /* 2048 */

/* Top-level VPN width: 11 bits (vs 9 bits for non-G-stage). */
#define GPA_VPN_TOP_BITS    11
#define GPA_VPN_TOP_MASK    ((1UL << GPA_VPN_TOP_BITS) - 1)    /* 0x7FF */

/* Number of levels per Sv*x4 mode (same as Sv* counterpart). */
#define SV39X4_LEVELS       3
#define SV48X4_LEVELS       4
#define SV57X4_LEVELS       5

/* Maximum supported GPA bit-width per mode. */
#define SV39X4_GPA_BITS     41
#define SV48X4_GPA_BITS     50
#define SV57X4_GPA_BITS     59

/* ===================================================================
 * G-stage page table pool
 *
 * Allocated from a dedicated 16KB-aligned linker section
 * `.gpt_page_tables`.  The first 4 pages of the pool are reserved
 * for the root table (so the root is guaranteed 16KB-aligned).
 * =================================================================== */
#define GPT_POOL_PAGES      64
#define GPT_POOL_SIZE       (GPT_POOL_PAGES * PAGE_SIZE_4K)    /* 256KB */

/* ===================================================================
 * Misc helpers
 * =================================================================== */

/* "Magic" value used by the VS-mode read/write helper for read-back. */
#define HYP_TEST_MAGIC      0xCAFEBEEFDEADF00DUL

#endif /* HYP_DEFS_H */
