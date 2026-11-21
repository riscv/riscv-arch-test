/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef SH_DEFS_H
#define SH_DEFS_H

/* ===================================================================
 * RISC-V Hypervisor Extension CSR Definitions
 *
 * All H-extension CSR addresses (HS-level, VS-level, M-mode H-ext)
 * and associated bit-field definitions.
 *
 * Defined unconditionally (address constants only). Use ENABLE_HYP
 * in build to compile the supporting accessors / handlers.
 * Safe for both C and assembly inclusion.
 * =================================================================== */

/* ----- HS-level Hypervisor CSRs ----- */
#define CSR_HSTATUS       0x600
#define CSR_HEDELEG       0x602
#define CSR_HIDELEG       0x603
#define CSR_HIE           0x604
#define CSR_HTIMEDELTA    0x605
#define CSR_HCOUNTEREN    0x606
#define CSR_HGEIE         0x607
#define CSR_HENVCFG       0x60A
#define CSR_HENVCFGH      0x61A   /* RV32 only */
#define CSR_HTVAL         0x643
#define CSR_HIP           0x644
#define CSR_HVIP          0x645
#define CSR_HTINST        0x64A
#define CSR_HGEIP         0xE12
#define CSR_HGATP         0x680

/* ----- VS-level CSRs ----- */
#define CSR_VSSTATUS      0x200
#define CSR_VSIE          0x204
#define CSR_VSTVEC        0x205
#define CSR_VSSCRATCH     0x240
#define CSR_VSEPC         0x241
#define CSR_VSCAUSE       0x242
#define CSR_VSTVAL        0x243
#define CSR_VSIP          0x244
#define CSR_VSATP         0x280

/* ----- M-mode hypervisor-extension CSRs ----- */
#define CSR_MTVAL2         0x34B
#define CSR_MTINST         0x34A

/* ===================================================================
 * hstatus fields (RV64)
 * =================================================================== */
#define HSTATUS_VSBE       (1UL << 5)
#define HSTATUS_GVA        (1UL << 6)
#define HSTATUS_SPV        (1UL << 7)
#define HSTATUS_SPVP       (1UL << 8)
#define HSTATUS_HU         (1UL << 9)
#define HSTATUS_VGEIN_SHIFT 12
#define HSTATUS_VGEIN_MASK (0x3FUL << HSTATUS_VGEIN_SHIFT)
#define HSTATUS_VTVM       (1UL << 20)
#define HSTATUS_VTW        (1UL << 21)
#define HSTATUS_VTSR       (1UL << 22)
#define HSTATUS_VSXL_SHIFT 32
#define HSTATUS_VSXL_MASK  (3UL << HSTATUS_VSXL_SHIFT)
#define HSTATUS_HUPMM_OFF  48             /* HUPMM field offset in hstatus (RV64) */
#define HSTATUS_HUPMM_MASK (3UL << 48)   /* HUPMM field mask [49:48] (Ssnpm) */

#define HSTATUS_WRITABLE_MASK ( \
    HSTATUS_VSBE | HSTATUS_GVA | HSTATUS_SPV | HSTATUS_SPVP | \
    HSTATUS_HU | HSTATUS_VGEIN_MASK | \
    HSTATUS_VTVM | HSTATUS_VTW | HSTATUS_VTSR | HSTATUS_VSXL_MASK )

/* ===================================================================
 * vsstatus / vsie writable masks
 * =================================================================== */
#define VSSTATUS_WRITABLE_MASK ( \
    (1UL << 1)  | \
    (1UL << 5)  | \
    (1UL << 6)  | \
    (1UL << 8)  | \
    (3UL << 9)  | \
    (3UL << 13) | \
    (3UL << 15) | \
    (1UL << 18) | \
    (1UL << 19) )

#define VSIE_WRITABLE_MASK ( \
    (1UL << 1) | \
    (1UL << 5) | \
    (1UL << 9) )

/* ===================================================================
 * vstvec MODE encoding
 * =================================================================== */
#define VSTVEC_MODE_DIRECT   0
#define VSTVEC_MODE_VECTORED 1
#define VSTVEC_MODE_MASK     0x3UL
#define VSTVEC_BASE_MASK     (~0x3UL)

/* ===================================================================
 * mstatus extension fields for hypervisor (RV64)
 * =================================================================== */
#define MSTATUS_GVA        (1ULL << 38)
#define MSTATUS_MPV        (1ULL << 39)

/* ===================================================================
 * hgatp layout constants (RV64)
 * =================================================================== */
#define HGATP64_MODE_SHIFT 60
#define HGATP64_VMID_SHIFT 44
#define HGATP64_PPN_MASK   ((1ULL << 44) - 1)
#define HGATP64_VMID_MASK  ((1UL << 14) - 1)

#define HGATP_MODE_BARE    0
#define HGATP_MODE_SV39X4  8
#define HGATP_MODE_SV48X4  9
#define HGATP_MODE_SV57X4  10

/* ===================================================================
 * HENVCFG field bits
 *
 * henvcfg mirrors menvcfg for the fields that affect VS-mode.
 * LPE and SSE have the same bit positions as in menvcfg.
 * =================================================================== */
#define HENVCFG_PBMTE   (1ULL << 62)   /* Svpbmt for VS-stage */
#define HENVCFG_ADUE    (1ULL << 61)   /* Hardware A/D update for VS-stage */
#define HENVCFG_STCE    (1ULL << 63)   /* vstimecmp enable */
#define HENVCFG_LPE     (1ULL << 2)    /* Landing Pad Enable for VS-mode (Zicfilp) */
#define HENVCFG_SSE     (1ULL << 3)    /* Shadow Stack Enable for VS-mode (Zicfiss) */
#define HENVCFG_PMM_OFF  32             /* PMM field offset in henvcfg */
#define HENVCFG_PMM_MASK (3ULL << 32)   /* PMM field mask [33:32] (Ssnpm, VS-mode) */
#define HENVCFG_FIOM    (1ULL << 0)    /* FENCE.I implicit memory ordering for VS/VU (Zifencei) */

/* ===================================================================
 * vsstatus field bits (VS-mode version of sstatus)
 *
 * SPELP mirrors sstatus.SPELP (bit 23) for VS-mode trap save/restore.
 * =================================================================== */
#define VSSTATUS_SPELP_BIT  BIT(23)    /* VS-mode Previous ELP (Zicfilp) */

/* ===================================================================
 * Sstc Extension: VS-mode / Hypervisor field definitions
 * =================================================================== */
#define CSR_VSTIMECMP   0x24D
#define CSR_VSTIMECMPH  0x25D   /* RV32 only */

#define HIP_VSTIP       (1ULL << 6)
#define HVIP_VSTIP      (1ULL << 6)
#define HCOUNTEREN_TM   (1ULL << 1)

/* ===================================================================
 * Smstateen H-mode CSRs
 * =================================================================== */
#define CSR_HSTATEEN0      0x60C
#define CSR_HSTATEEN1      0x60D
#define CSR_HSTATEEN2      0x60E
#define CSR_HSTATEEN3      0x60F

/* RV32-only high-half of hstateen0 */
#ifndef CSR_HSTATEEN0H
#define CSR_HSTATEEN0H     0x61C
#endif

/* Hypervisor Context Register (Sdtrig, gated by stateen0.CONTEXT) */
#ifndef CSR_HCONTEXT
#define CSR_HCONTEXT       0x6A8
#endif

/* RV32-only high-half of hideleg (Ssaia) */
#ifndef CSR_HIDELEGH
#define CSR_HIDELEGH       0x613
#endif

/* VS indirect CSRs (Smcsrind / Sscsrind) */
#ifndef CSR_VSISELECT
#define CSR_VSISELECT      0x250
#endif
#ifndef CSR_VSIREG
#define CSR_VSIREG         0x251
#endif
#ifndef CSR_VSIREG2
#define CSR_VSIREG2        0x252
#endif
#ifndef CSR_VSIREG3
#define CSR_VSIREG3        0x253
#endif
#ifndef CSR_VSIREG4
#define CSR_VSIREG4        0x255
#endif
#ifndef CSR_VSIREG5
#define CSR_VSIREG5        0x256
#endif
#ifndef CSR_VSIREG6
#define CSR_VSIREG6        0x257
#endif

/* VS top external interrupt (Ssaia, IMSIC only) */
#ifndef CSR_VSTOPEI
#define CSR_VSTOPEI        0x25C
#endif

#endif /* SH_DEFS_H */
