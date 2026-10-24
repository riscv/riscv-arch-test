/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef VM_DEFS_H
#define VM_DEFS_H

/* ===================================================================
 * RISC-V Virtual Memory Definitions
 *
 * Constants for Sv39/Sv48/Sv57 page-based virtual memory systems.
 * =================================================================== */

#include "types.h"

/* ===================================================================
 * satp MODE field values and MAKE_SATP are defined in ss_defs.h
 * (included via encoding.h). They are not redefined here to avoid
 * duplication.
 *
 * SATP_MODE_SHIFT / SATP_ASID_SHIFT / SATP_PPN_MASK below are
 * alternative names (without the "64" prefix) used by some test
 * code. They are kept here with #ifndef guards so that projects
 * needing RV32-specific values (e.g. Svbare) can override them.
 * =================================================================== */
#ifndef SATP_MODE_SHIFT
#define SATP_MODE_SHIFT     60
#endif
#ifndef SATP_ASID_SHIFT
#define SATP_ASID_SHIFT     44
#endif
#ifndef SATP_PPN_MASK
#define SATP_PPN_MASK       ((1ULL << 44) - 1)
#endif

/* ===================================================================
 * Page sizes
 * =================================================================== */
#define PAGE_SHIFT_4K   12
#define PAGE_SHIFT_2M   21
#define PAGE_SHIFT_4M   22      /* Sv32 megapage (RV32 only) */
#define PAGE_SHIFT_1G   30
#define PAGE_SHIFT_512G 39      /* Sv48/Sv57 level-1 huge page */
#define PAGE_SHIFT_256T 48      /* Sv57 level-1 huge page */

#define PAGE_SIZE_4K    (1UL << PAGE_SHIFT_4K)   /* 4 KB   = 0x1000     */
#define PAGE_SIZE_2M    (1UL << PAGE_SHIFT_2M)   /* 2 MB   = 0x200000   */
#define PAGE_SIZE_4M    (1UL << PAGE_SHIFT_4M)   /* 4 MB   = 0x400000   (Sv32 megapage) */
#define PAGE_SIZE_1G    (1UL << PAGE_SHIFT_1G)   /* 1 GB   = 0x40000000 */
#define PAGE_SIZE_512G  (1UL << PAGE_SHIFT_512G) /* 512 GB (Sv48/Sv57)  */
#define PAGE_SIZE_256T  (1UL << PAGE_SHIFT_256T) /* 256 TB (Sv57)       */

#define PAGE_SIZE       PAGE_SIZE_4K
#define PAGE_SHIFT      PAGE_SHIFT_4K

/* ===================================================================
 * Page Table Entry (PTE) bit definitions
 * =================================================================== */
#define PTE_V   BIT(0)   /* Valid */
#define PTE_R   BIT(1)   /* Read */
#define PTE_W   BIT(2)   /* Write */
#define PTE_X   BIT(3)   /* Execute */
#define PTE_U   BIT(4)   /* User-accessible */
#define PTE_G   BIT(5)   /* Global */
#define PTE_A   BIT(6)   /* Accessed */
#define PTE_D   BIT(7)   /* Dirty */
#define PTE_N   BIT(63)  /* NAPOT translation contiguity (Svnapot, RV64) */

/* PBMT field in PTE bits 62-61 (Svpbmt extension) */
#define PTE_PBMT_SHIFT  61
#define PTE_PBMT_MASK   (3UL << PTE_PBMT_SHIFT)

#define PBMT_PMA        (0UL << PTE_PBMT_SHIFT)  /* 00: Use underlying PMA */
#define PBMT_NC         (1UL << PTE_PBMT_SHIFT)  /* 01: Non-cacheable, idempotent, RVWMO */
#define PBMT_IO         (2UL << PTE_PBMT_SHIFT)  /* 10: Non-cacheable, non-idempotent, I/O ordering */
#define PBMT_RSVD       (3UL << PTE_PBMT_SHIFT)  /* 11: Reserved (triggers page-fault) */

/* Extract PBMT field from a PTE */
#define PTE_PBMT(pte)   (((pte) & PTE_PBMT_MASK) >> PTE_PBMT_SHIFT)

/* Shadow Stack page encoding: R=0, W=1, X=0 (xwr=010) per Zicfiss */
#define PTE_SS      (PTE_V | PTE_W)

/* Common permission combinations */
#define PTE_RWX     (PTE_R | PTE_W | PTE_X)
#define PTE_RWXU    (PTE_R | PTE_W | PTE_X | PTE_U)
#define PTE_RWXAD   (PTE_R | PTE_W | PTE_X | PTE_A | PTE_D)

/* ===================================================================
 * Page table level definitions
 *
 * Level 0 = leaf at 4KB granularity (lowest level)
 * Level 1 = leaf at 2MB granularity (megapage)
 * Level 2 = leaf at 1GB granularity (gigapage)
 * Level 3 = leaf at 512GB granularity (Sv48/Sv57 only)
 * Level 4 = leaf at 256TB granularity (Sv57 only)
 * =================================================================== */
#define PT_LEVEL_4K     0
#define PT_LEVEL_2M     1
#define PT_LEVEL_1G     2
#define PT_LEVEL_512G   3
#define PT_LEVEL_256T   4

/* Number of PTEs per page table page */
#define PT_ENTRIES      512
#define PT_INDEX_BITS   9

/* Number of page table levels for each mode */
#define SV39_LEVELS     3
#define SV48_LEVELS     4
#define SV57_LEVELS     5

/* ===================================================================
 * PTE field extraction and construction macros
 * =================================================================== */

/* PTE flags are in bits [7:0], RSW in [9:8], PPN in [53:10] */
#define PTE_FLAGS_MASK  0x3FFUL
#define PTE_PPN_SHIFT   10

/* Extract flags from a PTE */
#define PTE_FLAGS(pte)      ((pte) & PTE_FLAGS_MASK)

/* 44-bit PPN mask (bits 53:10 of PTE, after right-shift by 10 = bits 43:0) */
#define PTE_PPN_MASK    ((1ULL << 44) - 1)

/* Extract PPN from a PTE (physical page number) */
#define PTE_PPN(pte)        ((((pte) >> PTE_PPN_SHIFT)) & PTE_PPN_MASK)

/* Convert a physical address to PTE PPN field */
#define PA_TO_PTE(pa)       (((uintptr_t)(pa) >> PAGE_SHIFT) << PTE_PPN_SHIFT)

/* Convert PTE PPN field back to physical address */
#define PTE_TO_PA(pte)      ((uintptr_t)((PTE_PPN(pte)) << PAGE_SHIFT))

/* Check if PTE is a leaf (has R, W, or X set) */
#define PTE_IS_LEAF(pte)    (((pte) & (PTE_R | PTE_W | PTE_X)) != 0)

/* ===================================================================
 * Virtual address VPN field extraction
 *
 * Sv39: VA[38:12] = VPN[2] | VPN[1] | VPN[0]
 * Sv48: VA[47:12] = VPN[3] | VPN[2] | VPN[1] | VPN[0]
 * Sv57: VA[56:12] = VPN[4] | VPN[3] | VPN[2] | VPN[1] | VPN[0]
 *
 * Each VPN field is 9 bits.
 * =================================================================== */
#define VA_VPN_MASK     0x1FFUL  /* 9-bit mask */

#define VA_VPN0(va)     (((uintptr_t)(va) >> 12) & VA_VPN_MASK)
#define VA_VPN1(va)     (((uintptr_t)(va) >> 21) & VA_VPN_MASK)
#define VA_VPN2(va)     (((uintptr_t)(va) >> 30) & VA_VPN_MASK)
#define VA_VPN3(va)     (((uintptr_t)(va) >> 39) & VA_VPN_MASK)
#define VA_VPN4(va)     (((uintptr_t)(va) >> 48) & VA_VPN_MASK)

/* Extract VPN at a given level */
#define VA_VPN(va, level)   (((uintptr_t)(va) >> (12 + 9 * (level))) & VA_VPN_MASK)

/* ===================================================================
 * Page table pool configuration
 * =================================================================== */
#define PT_POOL_PAGES   64                          /* Number of 4KB pages in pool */
#define PT_POOL_SIZE    (PT_POOL_PAGES * PAGE_SIZE) /* 256 KB total */

/* ===================================================================
 * Shared test-data magic constants
 *
 * Authoritative values used by the VM test suites to tag written data
 * and verify translation/readback. Do NOT redefine these locally.
 * =================================================================== */
#define MAGIC_WRITE     0xDEADBEEF12345678UL
#define MAGIC_READ      0xCAFEBABE87654321UL

#endif /* VM_DEFS_H */
