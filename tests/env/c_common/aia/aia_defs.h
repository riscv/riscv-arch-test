/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef COMMON_AIA_DEFS_H
#define COMMON_AIA_DEFS_H

/* ===================================================================
 * RISC-V AIA (Advanced Interrupt Architecture) Definitions
 *
 * Single authoritative source of AIA-specific encoding constants shared
 * by the aia_* test suites (Smaia / IMSIC / APLIC / IOMMU / Hypervisor).
 *
 * CSR addresses, cause codes and stateen value bits that the privileged
 * framework already provides are NOT repeated here; including
 * "encoding.h" pulls them in from sm_defs.h / ss_defs.h / sh_defs.h /
 * cause_defs.h / encoding.h. In particular the following come from
 * common and must not be redefined:
 *   CSR_MISELECT / CSR_MIREG / CSR_MIREG2      (sm_defs.h)
 *   CSR_SISELECT / CSR_SIREG[2-6] / CSR_STOPEI / CSR_STOPI / CSR_SIPH
 *                                              (ss_defs.h)
 *   CSR_VSISELECT / CSR_VSIREG[2-6] / CSR_VSTOPEI / CSR_HSTATUS /
 *   CSR_HIDELEG / CSR_HVIP / CSR_HGEIP / CSR_HGEIE / CSR_HIDELEGH
 *                                              (sh_defs.h)
 *   CSR_MSTATEEN0 / CSR_HSTATEEN0 / CSR_SSTATEEN0
 *   STATEEN0_IMSIC / STATEEN0_AIA / STATEEN0_CSRIND   (encoding.h, values)
 *   CAUSE_VIRTUAL_INSTRUCTION / IRQ_S_TIMER / IRQ_M_TIMER (cause_defs.h)
 *   MIP_STIP                                    (sm_defs.h)
 *   HSTATUS_VGEIN_SHIFT / HSTATUS_VGEIN_MASK    (sh_defs.h)
 *   PRIV_VU (=4) / PRIV_VS (=5)                 (encoding.h, V=1 encoding)
 *
 * Reference: RISC-V AIA Specification, Version 1.0
 * =================================================================== */

#include "encoding.h"

/* ===================================================================
 * AIA Machine-level CSRs (Smaia / Smcsrind)
 *
 * Guarded with #ifndef so a future common definition takes precedence
 * without a redefinition diagnostic (values are architectural).
 * =================================================================== */
#ifndef CSR_MIREG3
#define CSR_MIREG3      0x353   /* Machine indirect register alias 3 */
#endif
#ifndef CSR_MIREG4
#define CSR_MIREG4      0x355   /* Machine indirect register alias 4 */
#endif
#ifndef CSR_MIREG5
#define CSR_MIREG5      0x356   /* Machine indirect register alias 5 */
#endif
#ifndef CSR_MIREG6
#define CSR_MIREG6      0x357   /* Machine indirect register alias 6 */
#endif
#ifndef CSR_MTOPEI
#define CSR_MTOPEI      0x35C   /* Machine top external interrupt (IMSIC) */
#endif
#ifndef CSR_MTOPI
#define CSR_MTOPI       0xFB0   /* Machine top interrupt */
#endif
#ifndef CSR_MVIEN
#define CSR_MVIEN       0x308   /* Machine virtual interrupt enables */
#endif
#ifndef CSR_MVIP
#define CSR_MVIP        0x309   /* Machine virtual interrupt pending */
#endif

/* RV32 high-half M-mode CSRs */
#ifndef CSR_MIDELEGH
#define CSR_MIDELEGH    0x313   /* Upper 32 bits of mideleg */
#endif
#ifndef CSR_MIEH
#define CSR_MIEH        0x314   /* Upper 32 bits of mie */
#endif
#ifndef CSR_MIPH
#define CSR_MIPH        0x354   /* Upper 32 bits of mip */
#endif
#ifndef CSR_MVIENH
#define CSR_MVIENH      0x318   /* Upper 32 bits of mvien */
#endif
#ifndef CSR_MVIPH
#define CSR_MVIPH       0x319   /* Upper 32 bits of mvip */
#endif

/* ===================================================================
 * AIA Supervisor-level CSRs
 * =================================================================== */
#ifndef CSR_SIEH
#define CSR_SIEH        0x114   /* Upper 32 bits of sie */
#endif

/* ===================================================================
 * AIA Hypervisor / VS-level CSRs
 * =================================================================== */
#ifndef CSR_HVIEN
#define CSR_HVIEN       0x608   /* Hypervisor virtual interrupt enables */
#endif
#ifndef CSR_HVICTL
#define CSR_HVICTL      0x609   /* Hypervisor virtual interrupt control */
#endif
#ifndef CSR_HVIPRIO1
#define CSR_HVIPRIO1    0x646   /* Hypervisor VS interrupt priority 1 */
#endif
#ifndef CSR_HVIPRIO2
#define CSR_HVIPRIO2    0x647   /* Hypervisor VS interrupt priority 2 */
#endif
#ifndef CSR_VSTOPI
#define CSR_VSTOPI      0xEB0   /* VS top interrupt */
#endif

/* RV32 high-half H / VS CSRs */
#ifndef CSR_HVIENH
#define CSR_HVIENH      0x618   /* Upper 32 bits of hvien */
#endif
#ifndef CSR_HVIPH
#define CSR_HVIPH       0x655   /* Upper 32 bits of hvip */
#endif
#ifndef CSR_HVIPRIO1H
#define CSR_HVIPRIO1H   0x656   /* Upper 32 bits of hviprio1 */
#endif
#ifndef CSR_HVIPRIO2H
#define CSR_HVIPRIO2H   0x657   /* Upper 32 bits of hviprio2 */
#endif
#ifndef CSR_VSIEH
#define CSR_VSIEH       0x214   /* Upper 32 bits of vsie */
#endif
#ifndef CSR_VSIPH
#define CSR_VSIPH       0x254   /* Upper 32 bits of vsip */
#endif

/* ===================================================================
 * mstateen0 / hstateen0 bit numbers for AIA
 *
 * The value-form macros STATEEN0_IMSIC / STATEEN0_AIA / STATEEN0_CSRIND
 * are provided by common/encoding.h; only the bit numbers live here.
 * =================================================================== */
#define STATEEN0_IMSIC_BIT      58  /* Controls IMSIC state access */
#define STATEEN0_AIA_BIT        59  /* Controls AIA CSR access */
#define STATEEN0_CSRIND_BIT     60  /* Controls indirect CSR access */

/* ===================================================================
 * IMSIC Indirect Register Numbers (accessed via *iselect / *ireg)
 * =================================================================== */

/* Interrupt file registers */
#define IMSIC_EIDELIVERY    0x70    /* External interrupt delivery enable */
#define IMSIC_EITHRESHOLD   0x72    /* External interrupt threshold */

/* External interrupt pending (eip) array: 0x80 - 0xBF */
#define IMSIC_EIP0          0x80
#define IMSIC_EIP63         0xBF
#define IMSIC_EIPn(n)       (IMSIC_EIP0 + (n))

/* External interrupt enable (eie) array: 0xC0 - 0xFF */
#define IMSIC_EIE0          0xC0
#define IMSIC_EIE63         0xFF
#define IMSIC_EIEn(n)       (IMSIC_EIE0 + (n))

/* Interrupt priority (iprio) array: 0x30 - 0x3F */
#define IMSIC_IPRIO0        0x30
#define IMSIC_IPRIO15       0x3F
#define IMSIC_IPRIOn(n)     (IMSIC_IPRIO0 + (n))

/* ===================================================================
 * IMSIC eidelivery values
 * =================================================================== */
#define EIDELIVERY_DISABLE          0
#define EIDELIVERY_ENABLE           1
#define EIDELIVERY_PLIC_COMPAT      0x40000000  /* Optional: PLIC/APLIC delivery */

/* ===================================================================
 * *topei / *topi field encodings
 * =================================================================== */

/* *topei: bits 26:16 = identity, bits 10:0 = priority (same as identity) */
#define TOPEI_ID_SHIFT      16
#define TOPEI_ID_MASK       0x7FF
#define TOPEI_PRIO_MASK     0x7FF
#define TOPEI_GET_ID(val)   (((val) >> TOPEI_ID_SHIFT) & TOPEI_ID_MASK)

/* *topi: bits 27:16 = IID, bits 7:0 = IPRIO */
#define TOPI_IID_SHIFT      16
#define TOPI_IID_MASK       0xFFF
#define TOPI_IPRIO_MASK     0xFF
#define TOPI_GET_IID(val)   (((val) >> TOPI_IID_SHIFT) & TOPI_IID_MASK)
#define TOPI_GET_IPRIO(val) ((val) & TOPI_IPRIO_MASK)

/* ===================================================================
 * hvictl field encodings
 * =================================================================== */
#define HVICTL_VTI          (1UL << 30)     /* Virtual Trap Interrupt */
#define HVICTL_IID_SHIFT    16
#define HVICTL_IID_MASK     (0xFFFUL << 16)
#define HVICTL_DPR          (1UL << 9)      /* Default Priority */
#define HVICTL_IPRIOM       (1UL << 8)      /* IPRIO Mode */
#define HVICTL_IPRIO_MASK   0xFF

/* ===================================================================
 * IMSIC Memory-mapped register offsets
 * =================================================================== */
#define IMSIC_MMIO_SETEIPNUM_LE     0x00    /* Set EIP number (little-endian) */
#define IMSIC_MMIO_SETEIPNUM_BE     0x04    /* Set EIP number (big-endian) */

/* ===================================================================
 * Interrupt cause short aliases
 *
 * common/cause_defs.h uses the long names IRQ_S_SOFTWARE / IRQ_M_SOFTWARE /
 * IRQ_S_EXTERNAL / IRQ_M_EXTERNAL (and already defines IRQ_S_TIMER /
 * IRQ_M_TIMER). AIA test code historically uses the short forms; alias
 * them here so the numeric value has a single source of truth.
 * =================================================================== */
#define IRQ_S_SOFT      IRQ_S_SOFTWARE  /* 1: Supervisor software interrupt */
#define IRQ_M_SOFT      IRQ_M_SOFTWARE  /* 3: Machine software interrupt */
#define IRQ_S_EXT       IRQ_S_EXTERNAL  /* 9: Supervisor external interrupt */
#define IRQ_M_EXT       IRQ_M_EXTERNAL  /* 11: Machine external interrupt */

/* ===================================================================
 * mip / mie bit positions
 *
 * MIP_STIP is provided by common/sm_defs.h and must not be redefined.
 * The remaining bits are expressed via the cause-code aliases above so
 * the bit index has a single source of truth.
 * =================================================================== */
#define MIP_SSIP        (1UL << IRQ_S_SOFT)
#define MIP_MSIP        (1UL << IRQ_M_SOFT)
#define MIP_MTIP        (1UL << IRQ_M_TIMER)
#define MIP_SEIP        (1UL << IRQ_S_EXT)
#define MIP_MEIP        (1UL << IRQ_M_EXT)

#endif /* COMMON_AIA_DEFS_H */
