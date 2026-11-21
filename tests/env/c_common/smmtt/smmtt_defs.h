/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef SMMTT_DEFS_H
#define SMMTT_DEFS_H

/* ===================================================================
 * SMMTT (Supervisor Domain Access Protection) common definitions
 *
 * Covers the Smsd `mmpt` / `msdcfg` CSR field layouts, the `mmpt`
 * MODE encodings, and the Smmpt Memory Protection Table (MPT) entry
 * (MPTE) bit layouts, per-mode radix parameters, XWR permission-tuple
 * encodings and NAPOT leaf rules.
 *
 * Source of truth:
 *   SPEC/riscv-smmtt/chapter3.adoc  (Smsd: mmpt/msdcfg CSRs, SDID,
 *                                    MFENCE.PA/MINVAL.PA)
 *   SPEC/riscv-smmtt/chapter4.adoc  (Smmpt: MPT lookup, MPTE formats)
 *
 * The `mmpt`/`msdcfg` CSR *addresses* live in sm_defs.h (M-mode CSR
 * address convention, pulled in via encoding.h). This header holds the
 * SMMTT-family field and MPTE layout details shared by the Smmpt /
 * Smsd / Smsdia / I-O MPT suites. The MFENCE.PA / MINVAL.PA instruction
 * encodings live in smmtt_insn.h.
 * =================================================================== */

#include "types.h"
#include "encoding.h"

/* ===================================================================
 * mmpt field layout and MODE values (chapter3, mpt-32 / mpt-64 tables)
 *
 * MXLEN=64: PPN[43:0] | NZR[51:44] | SDID[57:52] | NZR[59:58] | MODE[63:60]
 * MXLEN=32: PPN[21:0] | SDID[27:22] | NZR[29:28] | MODE[31:30]
 *
 * NZR = "0 (reserved)": must be zeroed by software, reads as zero.
 * The MODE field position differs by MXLEN, so the field masks are
 * defined per XLEN. The numeric MODE values are:
 *   MXLEN=32: 0=Bare, 1=Smmpt34, 2=reserved, 3=custom
 *   MXLEN=64: 0=Bare, 1=Smmpt43, 2=Smmpt52, 3=Smmpt64,
 *             4-13=reserved, 14-15=custom
 * =================================================================== */

#define MMPT_MODE_BARE          0

/* Standard-mode names are defined for both XLENs so XLEN-agnostic
 * probe cases compile anywhere; each case still SKIPs at runtime for
 * the inapplicable MXLEN (Smmpt34 is RV32-only, Smmpt43/52/64 are
 * RV64-only). */
#define MMPT_MODE_SMMPT34       1
#define MMPT_MODE_SMMPT43       1
#define MMPT_MODE_SMMPT52       2
#define MMPT_MODE_SMMPT64       3

/* Maximum implemented SDID bits (SDIDMAX, chapter3). */
#define SDIDMAX                 6
#define MMPT_SDID_WIDTH         6

#if __riscv_xlen == 64

#define MMPT_MODE_SHIFT         60
#define MMPT_MODE_MASK          (0xFUL << MMPT_MODE_SHIFT)
#define MMPT_PPN_SHIFT          0
#define MMPT_PPN_MASK           ((1UL << 44) - 1)   /* PPN = bits[43:0]  */
#define MMPT_SDID_SHIFT         52                   /* SDID = bits[57:52] */
#define MMPT_SDID_MASK          (0x3FUL << MMPT_SDID_SHIFT)
/* NZR: bits 51:44 (8 bits) and bits 59:58 (2 bits) */
#define MMPT_NZR_MASK           ((0xFFUL << 44) | (0x3UL << 58))

#define MMPT_MODE_RSVD_LO       4
#define MMPT_MODE_RSVD_HI       13
#define MMPT_MODE_CUSTOM_LO     14
#define MMPT_MODE_CUSTOM_HI     15
#define MMPT_MODE_STD_LO        MMPT_MODE_SMMPT43
#define MMPT_MODE_STD_HI        MMPT_MODE_SMMPT64

/* Default RV64 MPT mode exercised by the suite. */
#define SMMPT_MODE_DEFAULT      MMPT_MODE_SMMPT43

#else /* __riscv_xlen == 32 */

#define MMPT_MODE_SHIFT         30
#define MMPT_MODE_MASK          (0x3UL << MMPT_MODE_SHIFT)
#define MMPT_PPN_SHIFT          0
#define MMPT_PPN_MASK           ((1UL << 22) - 1)   /* PPN = bits[21:0]  */
#define MMPT_SDID_SHIFT         22                   /* SDID = bits[27:22] */
#define MMPT_SDID_MASK          (0x3FUL << MMPT_SDID_SHIFT)
/* NZR: bits 29:28 (2 bits) */
#define MMPT_NZR_MASK           (0x3UL << 28)

#define MMPT_MODE_RSVD_LO       2
#define MMPT_MODE_RSVD_HI       2
#define MMPT_MODE_CUSTOM_LO     3
#define MMPT_MODE_CUSTOM_HI     3
#define MMPT_MODE_STD_LO        MMPT_MODE_SMMPT34
#define MMPT_MODE_STD_HI        MMPT_MODE_SMMPT34

#define SMMPT_MODE_DEFAULT      MMPT_MODE_SMMPT34

#endif /* __riscv_xlen */

/* Build an `mmpt` value from its MODE, SDID and PPN fields. PPN holds
 * a page number (root_table_pa >> 12, PAGESIZE = 4 KiB), NOT a byte
 * address. */
#define MMPT_MAKE(mode, sdid, ppn) \
    ((uintptr_t)((((uintptr_t)(mode)) << MMPT_MODE_SHIFT) | \
                 (((uintptr_t)(sdid)) << MMPT_SDID_SHIFT) | \
                 (((uintptr_t)(ppn))  << MMPT_PPN_SHIFT)))

/* mmpt field extraction helpers. */
#define MMPT_GET_MODE(v)    (unsigned)(((v) & MMPT_MODE_MASK) >> MMPT_MODE_SHIFT)
#define MMPT_GET_SDID(v)    (unsigned)(((v) & MMPT_SDID_MASK) >> MMPT_SDID_SHIFT)
#define MMPT_GET_PPN(v)     ((uintptr_t)(((v) & MMPT_PPN_MASK) >> MMPT_PPN_SHIFT))

/* Smmpt64: mmpt.PPN bits 2:0 always read zero (32 KiB root alignment). */
#define MMPT_PPN_SMMPT64_RZERO  0x7UL

/* ===================================================================
 * msdcfg field layout (chapter3; low 32 bits, register is MXLEN wide)
 *
 * SIDN[5:0] | NZR[21:6] | SSRM[22] | SSMM[23] | SRL[27:24] | SML[31:28]
 *
 * Smsdia    -> SIDN  (supervisor interrupt domain)
 * Smsdqosid -> SRL, SML, SSRM, SSMM (supervisor-domain QoS IDs)
 * Bits 21:6 are reserved (NZR): zeroed by software, read as zero.
 * =================================================================== */
#define MSDCFG_SIDN_SHIFT       0
#define MSDCFG_SIDN_WIDTH       6
#define MSDCFG_SIDN_MASK        (0x3FUL << MSDCFG_SIDN_SHIFT)   /* bits 5:0 */
#define MSDCFG_SIDN_MAX         0x3FUL   /* 6-bit field, up to 64 domains */
#define MSDCFG_NZR_MASK         (0xFFFFUL << 6)   /* bits 21:6 (16 bits) */
#define MSDCFG_SSRM_BIT         (1UL << 22)
#define MSDCFG_SSMM_BIT         (1UL << 23)
#define MSDCFG_SRL_SHIFT        24
#define MSDCFG_SRL_MASK         (0xFUL << 24)     /* 4 bits */
#define MSDCFG_SML_SHIFT        28
#define MSDCFG_SML_MASK         (0xFUL << 28)     /* 4 bits */

/* Union of all architecturally-defined (non-NZR) msdcfg fields in bits 31:0. */
#define MSDCFG_FIELDS_MASK      (MSDCFG_SIDN_MASK | MSDCFG_SSRM_BIT | \
                                 MSDCFG_SSMM_BIT | MSDCFG_SRL_MASK | \
                                 MSDCFG_SML_MASK)

/* Bits above 31 (present when MXLEN=64) are not defined by chapter3 and
 * are expected to read as zero. */
#if __riscv_xlen == 64
#define MSDCFG_UPPER_MASK       (0xFFFFFFFFUL << 32)
#else
#define MSDCFG_UPPER_MASK       0
#endif

/* ===================================================================
 * MPTE bit layout (chapter4)
 *
 * The V/L/N bit positions, the non-leaf PPN field position, the
 * non-NAPOT leaf XWR tuple base and the NAPOT leaf G field position
 * are identical across Smmpt34 (RV32) and Smmpt43/52/64 (RV64); only
 * the entry width (MPTESIZE) and the extent of the reserved fields
 * differ. A single set of shift macros therefore serves all modes.
 * =================================================================== */

#define MPTE_V                  ((uintptr_t)1 << 0)   /* Valid          */
#define MPTE_L                  ((uintptr_t)1 << 1)   /* 1 = leaf       */
#define MPTE_N                  ((uintptr_t)1 << 2)   /* 1 = NAPOT leaf */

/* Non-leaf MPTE: PPN of the next-level table, at bits[..:10].
 * PPN value = next_table_pa >> 12 (PAGESIZE = 4 KiB). */
#define MPTE_PPN_SHIFT          10
#define MPTE_NONLEAF(next_pa)   (MPTE_V | \
    ((((uintptr_t)(next_pa) >> 12)) << MPTE_PPN_SHIFT))

/* Non-NAPOT leaf MPTE: XWR[k] is a 3-bit tuple at bit (8 + 3k). */
#define MPTE_XWR_BASE           8
#define MPTE_XWR_FIELD(k, v)    (((uintptr_t)(v) & 0x7) << (MPTE_XWR_BASE + 3 * (k)))

/* NAPOT leaf MPTE: single XWR tuple at bit 8, reserved bit 11,
 * G field at bits[15:12]. */
#define MPTE_NAPOT_XWR(v)       MPTE_XWR_FIELD(0, (v))
#define MPTE_NAPOT_RSVD_BIT     ((uintptr_t)1 << 11)
#define MPTE_NAPOT_G_SHIFT      12
#define MPTE_NAPOT_G(g)         (((uintptr_t)(g) & 0xF) << MPTE_NAPOT_G_SHIFT)
#define MPTE_NAPOT_LEAF(xwr, g) (MPTE_V | MPTE_L | MPTE_N | \
    MPTE_NAPOT_XWR(xwr) | MPTE_NAPOT_G(g))

/* ===================================================================
 * XWR permission-tuple encodings (chapter4, Smmpt-xwr-encoding)
 * =================================================================== */

#define MPT_XWR_NONE            0   /* 000: no access                 */
#define MPT_XWR_R               1   /* 001: read-only                 */
#define MPT_XWR_RSVD_010        2   /* 010: reserved for future use   */
#define MPT_XWR_RW              3   /* 011: read-write                */
#define MPT_XWR_X               4   /* 100: execute-only              */
#define MPT_XWR_RX              5   /* 101: read-execute              */
#define MPT_XWR_RSVD_110        6   /* 110: reserved for future use   */
#define MPT_XWR_RWX             7   /* 111: read-write-execute        */

/* Maximum XWR tuples per leaf MPTE (16 for the RV64 modes, 8 for
 * Smmpt34). Used to size tuple arrays passed to the builder. */
#define MPT_MAX_TUPLES          16

/* ===================================================================
 * NAPOT leaf G-field encodings (chapter4)
 *
 *   Smmpt34:        only G=6 is defined (4 MiB range); 0-5,7-15 reserved
 *   Smmpt43/52/64:  only G=4 is defined (2 MiB / 1 GiB); 0-3,5-15 reserved
 * A NAPOT range spans 2^(G+1) MPTEs whose L/N/XWR/V bits are identical.
 * =================================================================== */

#define MPT_NAPOT_G_SMMPT34     6
#define MPT_NAPOT_G_RV64        4

/* ===================================================================
 * Reserved-bit masks within a *valid* MPTE (chapter4, norm:mpte_v_res)
 *
 * Any reserved bit set in a V=1 MPTE must raise an access-fault. These
 * masks are used by the walk/validity tests to inject a reserved bit.
 * =================================================================== */

#if __riscv_xlen == 64
/* Non-leaf: Reserved = bits[9:2] and bits[63:54]. */
#define MPTE_NONLEAF_RSVD_MASK  (((uintptr_t)0xFF << 2) | ((uintptr_t)0x3FF << 54))
/* Non-NAPOT leaf: Reserved = bits[7:3] and bits[63:56]. */
#define MPTE_LEAF_RSVD_MASK     (((uintptr_t)0x1F << 3) | ((uintptr_t)0xFF << 56))
/* NAPOT leaf: Reserved = bits[7:3], bit 11, bits[63:16]. */
#define MPTE_NAPOT_RSVD_MASK    (((uintptr_t)0x1F << 3) | ((uintptr_t)1 << 11) | \
                                 ((uintptr_t)0xFFFFFFFFFFFFUL << 16))
#define MPTE_WIDTH              64
#else
/* Smmpt34 non-leaf: Reserved = bits[9:2]. */
#define MPTE_NONLEAF_RSVD_MASK  ((uintptr_t)0xFF << 2)
/* Smmpt34 non-NAPOT leaf: Reserved = bits[7:3]. */
#define MPTE_LEAF_RSVD_MASK     ((uintptr_t)0x1F << 3)
/* Smmpt34 NAPOT leaf: Reserved = bits[7:3], bit 11, bits[31:16]. */
#define MPTE_NAPOT_RSVD_MASK    (((uintptr_t)0x1F << 3) | ((uintptr_t)1 << 11) | \
                                 ((uintptr_t)0xFFFF << 16))
#define MPTE_WIDTH              32
#endif

/* ===================================================================
 * Per-mode radix parameters (chapter4, MPT_ACC_LKUP)
 *
 *   mode      LEVELS  MPTESIZE  NUMPGINRANGE  PAGESIZE  range-offset bits
 *   Smmpt34     2        4          3          4 KiB        15
 *   Smmpt43     3        8          4          4 KiB        16
 *   Smmpt52     4        8          4          4 KiB        16
 *   Smmpt64     5        8          4          4 KiB        16
 *
 * pn[i] field location (bit shift / width) per level i (0 = lowest):
 *   Smmpt34:      pn[0] = bits[24:15] (10), pn[1] = bits[33:25] (9)
 *   Smmpt43/52:   pn[i] = bits[16+9i+8 : 16+9i] (9)
 *   Smmpt64:      pn[0..3] width 9; pn[4] = bits[63:52] (12)
 * =================================================================== */

#define MPT_PAGESIZE            0x1000UL    /* 4 KiB */
#define MPT_PAGESHIFT           12

typedef struct {
    int mode;               /* MMPT_MODE_SMMPT* value                    */
    int levels;             /* radix depth (root level = levels-1)       */
    int mpte_size;          /* bytes per MPTE (4 or 8)                   */
    int numpginrange;       /* bits selecting a page inside a leaf range */
    int npg_tuples;         /* 2^numpginrange XWR tuples per leaf        */
    uintptr_t offset_bits;  /* width of the range-offset field           */
    uintptr_t spa_bits;     /* supervisor physical address width         */
} mpt_mode_info_t;

/* Fill @info for @mode. Returns 0 on success, -1 for an unknown mode. */
int mpt_mode_info(int mode, mpt_mode_info_t *info);

/* Bit shift / width of the pn[i] field for @mode (level 0 = lowest). */
int mpt_pn_shift(int mode, int level);
int mpt_pn_width(int mode, int level);

/* Extract pn[level] from a physical address; also the entry count of
 * the table at that level (2^width). */
uintptr_t mpt_pn(int mode, uintptr_t pa, int level);
uintptr_t mpt_level_entries(int mode, int level);

/* Most-significant @numpginrange bits of the range offset (level 0
 * leaf) or of pn[level-1] (higher leaf) select the XWR tuple index. */
uintptr_t mpt_page_index(const mpt_mode_info_t *info, uintptr_t pa, int leaf_level);

/* ===================================================================
 * C-only mmpt / msdcfg accessor macros
 *
 * mmpt / msdcfg are M-mode CSRs whose addresses (sm_defs.h) are not
 * known to the assembler by name, so CSRR/CSRW stringify the numeric
 * CSR address. The statement-expression form lets these be used inside
 * PRIV_DO(...) and EXPECT_NO_TRAP(...).
 * =================================================================== */

#ifndef __ASSEMBLER__

#define MMPT_READ()     ((uintptr_t)CSRR(CSR_MMPT))
#define MMPT_WRITE(v)   CSRW(CSR_MMPT, (uintptr_t)(v))
#define MSDCFG_READ()   ((uintptr_t)CSRR(CSR_MSDCFG))
#define MSDCFG_WRITE(v) CSRW(CSR_MSDCFG, (uintptr_t)(v))

#endif /* __ASSEMBLER__ */

#endif /* SMMTT_DEFS_H */
