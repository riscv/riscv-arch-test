/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef SS_DEFS_H
#define SS_DEFS_H

/* ===================================================================
 * RISC-V Supervisor-mode CSR Definitions
 *
 * All S-mode CSR addresses and associated bit-field definitions.
 * Safe for both C and assembly inclusion (plain integer constants).
 * =================================================================== */

/* ----- Supervisor-level CSRs ----- */
#define CSR_SSTATUS     0x100
#define CSR_SIE         0x104
#define CSR_STVEC       0x105
#define CSR_SCOUNTEREN  0x106
#define CSR_SSCRATCH    0x140
#define CSR_SEPC        0x141
#define CSR_SCAUSE      0x142
#define CSR_STVAL       0x143
#define CSR_SIP         0x144
#define CSR_SATP        0x180

/* ----- sstatus field bits ----- */
#define SSTATUS_SIE_BIT  BIT(1)   /* Supervisor Interrupt Enable (== mstatus.SIE) */
#define SSTATUS_SUM_BIT  BIT(18)  /* Permit Supervisory User Accesses (== mstatus.SUM) */
#define SSTATUS_MXR_BIT  BIT(19)  /* Make eXecutable Readable (== mstatus.MXR) */
#define SSTATUS_SD_BIT   BIT(63)  /* State Dirty summary (FS!=0 or VS!=0 or XS!=0) */
#define SSTATUS_SDT_BIT  BIT(24)  /* S-mode Double Trap enable (Ssdbltrp) */

/* sstatus.VS field [10:9] - vector context state (Off/Initial/Clean/Dirty) */
#define SSTATUS_VS_SHIFT    9
#define SSTATUS_VS_MASK     (3UL << SSTATUS_VS_SHIFT)
#define SSTATUS_VS_OFF      (0UL << SSTATUS_VS_SHIFT)
#define SSTATUS_VS_INITIAL  (1UL << SSTATUS_VS_SHIFT)
#define SSTATUS_VS_CLEAN    (2UL << SSTATUS_VS_SHIFT)
#define SSTATUS_VS_DIRTY    (3UL << SSTATUS_VS_SHIFT)

/* sstatus.FS field [14:13] - float context state (Off/Initial/Clean/Dirty) */
#define SSTATUS_FS_SHIFT    13
#define SSTATUS_FS_MASK     (3UL << SSTATUS_FS_SHIFT)
#define SSTATUS_FS_OFF      (0UL << SSTATUS_FS_SHIFT)
#define SSTATUS_FS_INITIAL  (1UL << SSTATUS_FS_SHIFT)
#define SSTATUS_FS_CLEAN    (2UL << SSTATUS_FS_SHIFT)
#define SSTATUS_FS_DIRTY    (3UL << SSTATUS_FS_SHIFT)

/* sstatus.UXL field [33:32] - U-mode effective XLEN (RV64) */
#define SSTATUS_UXL_SHIFT   32
#define SSTATUS_UXL_MASK    (3UL << SSTATUS_UXL_SHIFT)

/* ----- stvec field layout (Sstvecd) -----
 * Authoritative source; suites must not redefine these locally. */
#define STVEC_MODE_MASK      0x3UL               /* MODE field [1:0] */
#define STVEC_MODE_DIRECT    0x0UL               /* MODE=0: Direct mode */
#define STVEC_MODE_VECTORED  0x1UL               /* MODE=1: Vectored mode */
#define STVEC_BASE_MASK      (~STVEC_MODE_MASK)  /* BASE field [XLEN-1:2] */

/* Supervisor Counter Inhibit (Ssccfg) */
#ifndef CSR_SCOUNTINHIBIT
#define CSR_SCOUNTINHIBIT 0x120
#endif

/* RV32-only high-half of sie */
#ifndef CSR_SIEH
#define CSR_SIEH        0x114
#endif

/* ----- Supervisor Environment Configuration ----- */
#define CSR_SENVCFG     0x10A
#define CSR_SENVCFGH    0x11A   /* RV32 only */

#define SENVCFG_LPE     (1ULL << 2)    /* Landing Pad Enable for U-mode (Zicfilp) */
#define SENVCFG_SSE     (1ULL << 3)    /* Shadow Stack Enable for U-mode (Zicfiss) */
#define SENVCFG_CBIE_SHIFT  4            /* CBIE field offset (Zicbom) */
#define SENVCFG_CBIE_MASK   (3ULL << 4)  /* CBIE field mask [5:4] (Zicbom) */
#define SENVCFG_CBCFE   (1ULL << 6)     /* Cache-Block Clean/Flush Enable (Zicbom) */
#define SENVCFG_CBZE    (1ULL << 7)     /* Cache-Block Zero Enable (Zicboz) */
#define SENVCFG_PMM_OFF  32             /* PMM field offset in senvcfg */
#define SENVCFG_PMM_MASK (3ULL << 32)   /* PMM field mask [33:32] (Ssnpm) */
#define SENVCFG_FIOM    (1ULL << 0)     /* FENCE.I implicit memory ordering (Zifencei) */

/* ===================================================================
 * satp layout constants
 *
 * RV32 (Sv32): [31] MODE | [30:22] ASID | [21:0] PPN
 * RV64 (Sv39+): [63:60] MODE | [59:44] ASID | [43:0] PPN
 * =================================================================== */

/* RV64 layout */
#ifndef SATP64_MODE_SHIFT
#define SATP64_MODE_SHIFT  60
#endif
#ifndef SATP64_ASID_SHIFT
#define SATP64_ASID_SHIFT  44
#endif
#ifndef SATP64_PPN_MASK
#define SATP64_PPN_MASK    ((1ULL << 44) - 1)
#endif
#define SATP64_ASID_MASK   ((1ULL << 16) - 1)

/* RV32 layout (Sv32) */
#define SATP32_MODE_SHIFT  31
#define SATP32_ASID_SHIFT  22
#define SATP32_PPN_MASK    ((1UL << 22) - 1)
#define SATP32_ASID_MASK   ((1UL << 9) - 1)

/* XLEN-aware generic names.
 * ss_defs.h is the authoritative source for these macros.
 * Use #undef to suppress redefinition warnings when vm_defs.h
 * (which has #ifndef fallbacks) happens to be included first. */
#undef SATP_MODE_SHIFT
#undef SATP_ASID_SHIFT
#undef SATP_PPN_MASK
#undef SATP_ASID_MASK
#undef SATP_MODE_BITS
#if __riscv_xlen == 32
#define SATP_MODE_SHIFT    SATP32_MODE_SHIFT
#define SATP_ASID_SHIFT    SATP32_ASID_SHIFT
#define SATP_PPN_MASK      SATP32_PPN_MASK
#define SATP_ASID_MASK     SATP32_ASID_MASK
#define SATP_MODE_BITS     1
#else
#define SATP_MODE_SHIFT    SATP64_MODE_SHIFT
#define SATP_ASID_SHIFT    SATP64_ASID_SHIFT
#define SATP_PPN_MASK      SATP64_PPN_MASK
#define SATP_ASID_MASK     SATP64_ASID_MASK
#define SATP_MODE_BITS     4
#endif

/* SATP MODE field values */
#ifndef SATP_MODE_BARE
#define SATP_MODE_BARE     0
#define SATP_MODE_SV32     1
#define SATP_MODE_SV39     8
#define SATP_MODE_SV48     9
#define SATP_MODE_SV57     10
#endif

#ifndef MAKE_SATP
#define MAKE_SATP(mode, asid, ppn) \
    ((uintptr_t)( \
    (((uintptr_t)(mode) << SATP_MODE_SHIFT) | \
     (((uintptr_t)(asid) & SATP_ASID_MASK) << SATP_ASID_SHIFT) | \
     ((uintptr_t)(ppn) & SATP_PPN_MASK))))
#endif

/* vsatp has the same layout as satp; alias for two-stage (Hypervisor) tests. */
#ifndef MAKE_VSATP
#define MAKE_VSATP(mode, asid, ppn)  MAKE_SATP((mode), (asid), (ppn))
#endif

#define SATP_GET_MODE(v)   (((uintptr_t)(v) >> SATP_MODE_SHIFT) & ((1UL << SATP_MODE_BITS) - 1))
#define SATP_GET_ASID(v)   (((uintptr_t)(v) >> SATP_ASID_SHIFT) & SATP_ASID_MASK)
#define SATP_GET_PPN(v)    ((uintptr_t)(v) & SATP_PPN_MASK)

/* ===================================================================
 * Sstc Extension: S-mode CSRs and field definitions
 * =================================================================== */
#define CSR_STIMECMP    0x14D
#define CSR_STIMECMPH   0x15D   /* RV32 only */

#define SIP_STIP        (1ULL << 5)
#define SIE_STIE        (1ULL << 5)

/* ===================================================================
 * Supervisor Count Overflow (Sscofpmf)
 * =================================================================== */
#define CSR_SCOUNTOVF     0xDA0

/* RV32-only high-half of sip */
#ifndef CSR_SIPH
#define CSR_SIPH          0x154
#endif

/* Supervisor indirect CSRs (Smcsrind / Sscsrind) */
#ifndef CSR_SISELECT
#define CSR_SISELECT      0x150
#endif
#ifndef CSR_SIREG
#define CSR_SIREG         0x151
#endif
#ifndef CSR_SIREG2
#define CSR_SIREG2        0x152
#endif
#ifndef CSR_SIREG3
#define CSR_SIREG3        0x153
#endif
#ifndef CSR_SIREG4
#define CSR_SIREG4        0x155
#endif
#ifndef CSR_SIREG5
#define CSR_SIREG5        0x156
#endif
#ifndef CSR_SIREG6
#define CSR_SIREG6        0x157
#endif

/* Supervisor top external interrupt (Ssaia, IMSIC only) */
#ifndef CSR_STOPEI
#define CSR_STOPEI        0x15C
#endif

/* Supervisor top interrupt (Ssaia, read-only) */
#ifndef CSR_STOPI
#define CSR_STOPI         0xDB0
#endif

/* Supervisor QoS resource configuration (Ssqosid) */
#ifndef CSR_SRMCFG
#define CSR_SRMCFG        0x181
#endif

/* srmcfg field layout (Ssqosid): [11:0] RCID, [27:16] MCID (both WARL) */
#ifndef SRMCFG_RCID_MASK
#define SRMCFG_RCID_MASK  0xFFFUL
#endif
#ifndef SRMCFG_RCID_SHIFT
#define SRMCFG_RCID_SHIFT 0
#endif
#ifndef SRMCFG_MCID_MASK
#define SRMCFG_MCID_MASK  0xFFFUL
#endif
#ifndef SRMCFG_MCID_SHIFT
#define SRMCFG_MCID_SHIFT 16
#endif

/* ===================================================================
 * Smstateen S-mode CSRs
 * =================================================================== */
#define CSR_SSTATEEN0      0x10C
#define CSR_SSTATEEN1      0x10D
#define CSR_SSTATEEN2      0x10E
#define CSR_SSTATEEN3      0x10F

/* ===================================================================
 * Ssctr: sctrctl field aliases (same layout as mctrctl; sctrctl.M
 * (bit 2) and sctrctl.MTE (bit 9) are read-only zero per SPEC)
 * =================================================================== */
#define SCTRCTL_U           CTRCTL_U
#define SCTRCTL_S           CTRCTL_S
#define SCTRCTL_RASEMU      CTRCTL_RASEMU
#define SCTRCTL_STE         CTRCTL_STE
#define SCTRCTL_BPFRZ       CTRCTL_BPFRZ
#define SCTRCTL_LCOFIFRZ    CTRCTL_LCOFIFRZ
#define SCTRCTL_EXCINH      CTRCTL_EXCINH
#define SCTRCTL_INTRINH     CTRCTL_INTRINH
#define SCTRCTL_TRETINH     CTRCTL_TRETINH
#define SCTRCTL_NTBREN      CTRCTL_NTBREN
#define SCTRCTL_TKBRINH     CTRCTL_TKBRINH
#define SCTRCTL_INDCALLINH  CTRCTL_INDCALLINH
#define SCTRCTL_DIRCALLINH  CTRCTL_DIRCALLINH
#define SCTRCTL_INDJMPINH   CTRCTL_INDJMPINH
#define SCTRCTL_DIRJMPINH   CTRCTL_DIRJMPINH
#define SCTRCTL_CORSWAPINH  CTRCTL_CORSWAPINH
#define SCTRCTL_RETINH      CTRCTL_RETINH
#define SCTRCTL_INDLJMPINH  CTRCTL_INDLJMPINH
#define SCTRCTL_DIRLJMPINH  CTRCTL_DIRLJMPINH
#define SCTRCTL_CUSTOM_MASK CTRCTL_CUSTOM_MASK

/* ===================================================================
 * sstatus.SDT (S-mode Double Trap enable, Ssdbltrp) accessors.
 * Authoritative source; suites must not redefine these locally.
 * =================================================================== */
#ifndef __ASSEMBLER__
#include "types.h"

/** Read sstatus.SDT as a boolean. */
static inline bool get_sdt(void)
{
    uintptr_t sstatus;
    asm volatile ("csrr %0, sstatus" : "=r"(sstatus));
    return (sstatus & SSTATUS_SDT_BIT) != 0;
}

/** Set sstatus.SDT. */
static inline void set_sdt(void)
{
    asm volatile ("csrs sstatus, %0" :: "r"(SSTATUS_SDT_BIT));
}

/** Clear sstatus.SDT. */
static inline void clear_sdt(void)
{
    asm volatile ("csrc sstatus, %0" :: "r"(SSTATUS_SDT_BIT));
}
#endif /* __ASSEMBLER__ */

#endif /* SS_DEFS_H */
