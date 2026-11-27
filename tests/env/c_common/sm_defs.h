/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef SM_DEFS_H
#define SM_DEFS_H

/* ===================================================================
 * RISC-V Machine-mode CSR Definitions
 *
 * All M-mode CSR addresses and associated bit-field definitions.
 * Safe for both C and assembly inclusion (plain integer constants).
 * =================================================================== */

/* ----- Machine-level CSRs ----- */
#define CSR_MSTATUS     0x300
#define CSR_MSTATUSH    0x310   /* RV32 only: upper 32 bits of mstatus */
#define CSR_MISA        0x301
#define CSR_MEDELEG     0x302
#define CSR_MIDELEG     0x303
#define CSR_MIE         0x304
#define CSR_MTVEC       0x305
#define CSR_MCOUNTEREN  0x306

/* Machine indirect CSR access (Smcsrind) */
#ifndef CSR_MISELECT
#define CSR_MISELECT    0x350
#endif
#ifndef CSR_MIREG
#define CSR_MIREG       0x351
#endif
#ifndef CSR_MIREG2
#define CSR_MIREG2      0x352
#endif
#ifndef CSR_MIREG3
#define CSR_MIREG3      0x353
#endif
#ifndef CSR_MIREG4
#define CSR_MIREG4      0x355
#endif
#ifndef CSR_MIREG5
#define CSR_MIREG5      0x356
#endif
#ifndef CSR_MIREG6
#define CSR_MIREG6      0x357
#endif

#define CSR_MSCRATCH    0x340
#define CSR_MEPC        0x341
#define CSR_MCAUSE      0x342
#define CSR_MTVAL       0x343
#define CSR_MIP         0x344
#define CSR_MHARTID     0xF14
#define CSR_MVENDORID   0xF11

/* RV32-only high-half of medeleg */
#ifndef CSR_MEDELEGH
#define CSR_MEDELEGH    0x312
#endif

/* ----- Machine Environment Configuration ----- */
#define CSR_MENVCFG     0x30A
#define CSR_MENVCFGH    0x31A   /* RV32 only */

#define MENVCFG_PBMTE   (1ULL << 62)    /* Page-Based Memory Types Enable (Svpbmt) */
#define MENVCFG_ADUE    (1ULL << 61)    /* A/D Update Enable (Svadu) */
#define MENVCFG_LPE     (1ULL << 2)    /* Landing Pad Enable for S-mode (Zicfilp) */
#define MENVCFG_SSE     (1ULL << 3)    /* Shadow Stack Enable for S-mode (Zicfiss) */
#define MENVCFG_PMM_OFF  32             /* PMM field offset in menvcfg */
#define MENVCFG_PMM_MASK (3ULL << 32)   /* PMM field mask [33:32] (Smnpm) */
#define MENVCFG_STCE    (1ULL << 63)    /* Sstc enable */
#define MENVCFG_CBIE_SHIFT  4            /* CBIE field offset (Zicbom) */
#define MENVCFG_CBIE_MASK   (3ULL << 4)  /* CBIE field mask [5:4] (Zicbom) */
#define MENVCFG_CBCFE   (1ULL << 6)     /* Cache-Block Clean/Flush Enable (Zicbom) */
#define MENVCFG_CBZE    (1ULL << 7)     /* Cache-Block Zero Enable (Zicboz) */
#define MENVCFG_FIOM    (1ULL << 0)     /* FENCE.I implicit memory ordering (Zifencei) */

/* ----- Machine Security Configuration ----- */
#define CSR_MSECCFG     0x747
#define CSR_MSECCFGH    0x757   /* RV32 only */

#define MSECCFG_MML     (1ULL << 0)     /* Machine Mode Lockdown */
#define MSECCFG_MMWP    (1ULL << 1)     /* Machine Mode Allowlist Policy */
#define MSECCFG_RLB     (1ULL << 2)     /* Rule Locking Bypass */
#define MSECCFG_MLPE    (1ULL << 10)    /* M-mode Landing Pad Enable (Zicfilp) */
#define MSECCFG_USEED   (1ULL << 8)     /* U-mode seed access enable (Zkr) */
#define MSECCFG_SSEED   (1ULL << 9)     /* S-mode seed access enable (Zkr) */
#define MSECCFG_PMM_OFF  32             /* PMM field offset in mseccfg */
#define MSECCFG_PMM_MASK (3ULL << 32)   /* PMM field mask [33:32] (Smmpm) */

/* ----- SMMTT / Supervisor Domain Access Protection (Smsd) -----
 * mmpt: M-mode Memory Protection Table configuration (SDID/PPN/MODE).
 * msdcfg: M-mode supervisor-domain configuration (Smsdia/Smsdqosid).
 * Field layouts, MODE encodings and MPTE formats are in smmtt/smmtt_defs.h. */
#ifndef CSR_MMPT
#define CSR_MMPT        0x382
#endif
#ifndef CSR_MSDCFG
#define CSR_MSDCFG      0x74E
#endif

/* ===================================================================
 * mstatus field offsets and masks
 * =================================================================== */
#define MSTATUS_SIE_BIT     BIT(1)
#define MSTATUS_MIE_BIT     BIT(3)
#define MSTATUS_SPIE_BIT    BIT(5)
#define MSTATUS_MPIE_BIT    BIT(7)
#define MSTATUS_SPP_OFF     8
#define MSTATUS_SPP_BIT     BIT(8)
#define MSTATUS_MPP_OFF     11
#define MSTATUS_MPP_MASK    BIT_MASK(11, 2)
#define MSTATUS_MPRV_BIT    BIT(17)
#define MSTATUS_SUM_BIT     BIT(18)
#define MSTATUS_MXR_BIT     BIT(19)
#define MSTATUS_TVM_BIT     BIT(20)
#define MSTATUS_TW_BIT      BIT(21)
#define MSTATUS_TSR_BIT     BIT(22)
#define MSTATUS_SPELP_BIT   BIT(23)    /* S-mode Previous ELP (Zicfilp) */
#define MSTATUS_MPELP_BIT   BIT(41)    /* M-mode Previous ELP (Zicfilp) */

/* Legacy alias for MSTATUS_TVM_BIT (used by Hypervisor test code) */
#ifndef MSTATUS_TVM
#define MSTATUS_TVM        MSTATUS_TVM_BIT
#endif

/* ===================================================================
 * PMP Configuration CSRs
 * =================================================================== */
#define CSR_PMPCFG0     0x3A0
#define CSR_PMPCFG1     0x3A1   /* RV32 only */
#define CSR_PMPCFG2     0x3A2
#define CSR_PMPCFG3     0x3A3   /* RV32 only */
#define CSR_PMPCFG4     0x3A4
#define CSR_PMPCFG5     0x3A5   /* RV32 only */
#define CSR_PMPCFG6     0x3A6
#define CSR_PMPCFG7     0x3A7   /* RV32 only */
#define CSR_PMPCFG8     0x3A8
#define CSR_PMPCFG9     0x3A9   /* RV32 only */
#define CSR_PMPCFG10    0x3AA
#define CSR_PMPCFG11    0x3AB   /* RV32 only */
#define CSR_PMPCFG12    0x3AC
#define CSR_PMPCFG13    0x3AD   /* RV32 only */
#define CSR_PMPCFG14    0x3AE
#define CSR_PMPCFG15    0x3AF   /* RV32 only */

#define CSR_PMPADDR0    0x3B0
#define CSR_PMPADDR1    0x3B1
#define CSR_PMPADDR2    0x3B2
#define CSR_PMPADDR3    0x3B3
#define CSR_PMPADDR4    0x3B4
#define CSR_PMPADDR5    0x3B5
#define CSR_PMPADDR6    0x3B6
#define CSR_PMPADDR7    0x3B7
#define CSR_PMPADDR8    0x3B8
#define CSR_PMPADDR9    0x3B9
#define CSR_PMPADDR10   0x3BA
#define CSR_PMPADDR11   0x3BB
#define CSR_PMPADDR12   0x3BC
#define CSR_PMPADDR13   0x3BD
#define CSR_PMPADDR14   0x3BE
#define CSR_PMPADDR15   0x3BF
#define CSR_PMPADDR16   0x3C0
#define CSR_PMPADDR17   0x3C1
#define CSR_PMPADDR18   0x3C2
#define CSR_PMPADDR19   0x3C3
#define CSR_PMPADDR20   0x3C4
#define CSR_PMPADDR21   0x3C5
#define CSR_PMPADDR22   0x3C6
#define CSR_PMPADDR23   0x3C7
#define CSR_PMPADDR24   0x3C8
#define CSR_PMPADDR25   0x3C9
#define CSR_PMPADDR26   0x3CA
#define CSR_PMPADDR27   0x3CB
#define CSR_PMPADDR28   0x3CC
#define CSR_PMPADDR29   0x3CD
#define CSR_PMPADDR30   0x3CE
#define CSR_PMPADDR31   0x3CF
#define CSR_PMPADDR32   0x3D0
#define CSR_PMPADDR33   0x3D1
#define CSR_PMPADDR34   0x3D2
#define CSR_PMPADDR35   0x3D3
#define CSR_PMPADDR36   0x3D4
#define CSR_PMPADDR37   0x3D5
#define CSR_PMPADDR38   0x3D6
#define CSR_PMPADDR39   0x3D7
#define CSR_PMPADDR40   0x3D8
#define CSR_PMPADDR41   0x3D9
#define CSR_PMPADDR42   0x3DA
#define CSR_PMPADDR43   0x3DB
#define CSR_PMPADDR44   0x3DC
#define CSR_PMPADDR45   0x3DD
#define CSR_PMPADDR46   0x3DE
#define CSR_PMPADDR47   0x3DF
#define CSR_PMPADDR48   0x3E0
#define CSR_PMPADDR49   0x3E1
#define CSR_PMPADDR50   0x3E2
#define CSR_PMPADDR51   0x3E3
#define CSR_PMPADDR52   0x3E4
#define CSR_PMPADDR53   0x3E5
#define CSR_PMPADDR54   0x3E6
#define CSR_PMPADDR55   0x3E7
#define CSR_PMPADDR56   0x3E8
#define CSR_PMPADDR57   0x3E9
#define CSR_PMPADDR58   0x3EA
#define CSR_PMPADDR59   0x3EB
#define CSR_PMPADDR60   0x3EC
#define CSR_PMPADDR61   0x3ED
#define CSR_PMPADDR62   0x3EE
#define CSR_PMPADDR63   0x3EF

/* ===================================================================
 * PMP configuration field bit definitions
 *
 * Each PMP entry has an 8-bit configuration register:
 *   [7]   L   - Lock
 *   [6:5] 00  - Reserved (WARL, reads as 0)
 *   [4:3] A   - Address matching mode
 *   [2]   X   - Execute permission
 *   [1]   W   - Write permission
 *   [0]   R   - Read permission
 * =================================================================== */

/* Permission bits */
#define PMP_R           (1U << 0)
#define PMP_W           (1U << 1)
#define PMP_X           (1U << 2)
#define PMP_RW          (PMP_R | PMP_W)
#define PMP_RX          (PMP_R | PMP_X)
#define PMP_WX          (PMP_W | PMP_X)
#define PMP_RWX         (PMP_R | PMP_W | PMP_X)

/* Address matching modes */
#define PMP_A_OFF       (0U << 3)   /* Disabled (no match) */
#define PMP_A_TOR       (1U << 3)   /* Top of Range */
#define PMP_A_NA4       (2U << 3)   /* Naturally Aligned 4-byte */
#define PMP_A_NAPOT     (3U << 3)   /* Naturally Aligned Power-of-Two */

/* Lock bit */
#define PMP_L           (1U << 7)

/* ===================================================================
 * Smstateen M-mode CSRs
 * =================================================================== */
#define CSR_MSTATEEN0      0x30C
#define CSR_MSTATEEN1      0x30D
#define CSR_MSTATEEN2      0x30E
#define CSR_MSTATEEN3      0x30F

/* RV32-only high-half of mstateen0 */
#ifndef CSR_MSTATEEN0H
#define CSR_MSTATEEN0H     0x31C
#endif

/* mstateen0 functional bit definitions (M-mode specific) */
#define MSTATEEN0_C         (1ULL << 0)
#define MSTATEEN0_FCSR      (1ULL << 1)
#define MSTATEEN0_JVT       (1ULL << 2)
#define MSTATEEN0_SRMCFG    (1ULL << 55)
#define MSTATEEN0_P1P13     (1ULL << 56)
#define MSTATEEN0_CONTEXT   (1ULL << 57)
#define MSTATEEN0_IMSIC     (1ULL << 58)
#define MSTATEEN0_AIA       (1ULL << 59)
#define MSTATEEN0_CSRIND    (1ULL << 60)
#define MSTATEEN0_ENVCFG    (1ULL << 62)
#define MSTATEEN0_SE0       (1ULL << 63)

/* WPRI mask: bits [53:3] in mstateen0 are reserved */
#define MSTATEEN0_WPRI_MASK 0x003FFFFFFFFFFFF8ULL

/* ===================================================================
 * Base Counter CSRs (M-mode read/write)
 * =================================================================== */
#define CSR_MCYCLE      0xB00
#define CSR_MINSTRET    0xB02

/* HPM Counter CSRs (M-mode read/write) */
#define CSR_MHPMCOUNTER3   0xB03
#define CSR_MHPMCOUNTER4   0xB04
#define CSR_MHPMCOUNTER5   0xB05
#define CSR_MHPMCOUNTER6   0xB06
#define CSR_MHPMCOUNTER7   0xB07
#define CSR_MHPMCOUNTER8   0xB08
#define CSR_MHPMCOUNTER9   0xB09
#define CSR_MHPMCOUNTER10  0xB0A
#define CSR_MHPMCOUNTER11  0xB0B
#define CSR_MHPMCOUNTER12  0xB0C
#define CSR_MHPMCOUNTER13  0xB0D
#define CSR_MHPMCOUNTER14  0xB0E
#define CSR_MHPMCOUNTER15  0xB0F
#define CSR_MHPMCOUNTER16  0xB10
#define CSR_MHPMCOUNTER17  0xB11
#define CSR_MHPMCOUNTER18  0xB12
#define CSR_MHPMCOUNTER19  0xB13
#define CSR_MHPMCOUNTER20  0xB14
#define CSR_MHPMCOUNTER21  0xB15
#define CSR_MHPMCOUNTER22  0xB16
#define CSR_MHPMCOUNTER23  0xB17
#define CSR_MHPMCOUNTER24  0xB18
#define CSR_MHPMCOUNTER25  0xB19
#define CSR_MHPMCOUNTER26  0xB1A
#define CSR_MHPMCOUNTER27  0xB1B
#define CSR_MHPMCOUNTER28  0xB1C
#define CSR_MHPMCOUNTER29  0xB1D
#define CSR_MHPMCOUNTER30  0xB1E
#define CSR_MHPMCOUNTER31  0xB1F

/* Parametric M-mode HPM counter CSR address by index n (3..31) */
#define CSR_MHPMCOUNTER(n)  (CSR_MHPMCOUNTER3 + ((n) - 3))

/* HPM Event CSRs (mhpmevent3-31) */
#define CSR_MHPMEVENT3   0x323
#define CSR_MHPMEVENT4   0x324
#define CSR_MHPMEVENT5   0x325
#define CSR_MHPMEVENT6   0x326
#define CSR_MHPMEVENT7   0x327
#define CSR_MHPMEVENT8   0x328
#define CSR_MHPMEVENT9   0x329
#define CSR_MHPMEVENT10  0x32A
#define CSR_MHPMEVENT11  0x32B
#define CSR_MHPMEVENT12  0x32C
#define CSR_MHPMEVENT13  0x32D
#define CSR_MHPMEVENT14  0x32E
#define CSR_MHPMEVENT15  0x32F
#define CSR_MHPMEVENT16  0x330
#define CSR_MHPMEVENT17  0x331
#define CSR_MHPMEVENT18  0x332
#define CSR_MHPMEVENT19  0x333
#define CSR_MHPMEVENT20  0x334
#define CSR_MHPMEVENT21  0x335
#define CSR_MHPMEVENT22  0x336
#define CSR_MHPMEVENT23  0x337
#define CSR_MHPMEVENT24  0x338
#define CSR_MHPMEVENT25  0x339
#define CSR_MHPMEVENT26  0x33A
#define CSR_MHPMEVENT27  0x33B
#define CSR_MHPMEVENT28  0x33C
#define CSR_MHPMEVENT29  0x33D
#define CSR_MHPMEVENT30  0x33E
#define CSR_MHPMEVENT31  0x33F

/* Parametric M-mode HPM event CSR address by index n (3..31) */
#define CSR_MHPMEVENT(n)    (CSR_MHPMEVENT3 + ((n) - 3))

/* Machine Counter Inhibit */
#define CSR_MCOUNTINHIBIT 0x320

/* ===================================================================
 * Sscofpmf: HPM field masks
 * =================================================================== */
#define MHPMEVENT_OF      (1ULL << 63)
#define MHPMEVENT_MINH    (1ULL << 62)
#define MHPMEVENT_SINH    (1ULL << 61)
#define MHPMEVENT_UINH    (1ULL << 60)
#define MHPMEVENT_VSINH   (1ULL << 59)
#define MHPMEVENT_VUINH   (1ULL << 58)

/* ===================================================================
 * Sstc Extension: M-mode field definitions
 * =================================================================== */
#define MIP_STIP        (1ULL << 5)
#define MIE_STIE        (1ULL << 5)
#define MIDELEG_STIP    (1ULL << 5)
#define MCOUNTEREN_TM   (1ULL << 1)

/* ===================================================================
 * mstatus.MPP field encodings (shifted to field position)
 * =================================================================== */
#define MSTATUS_MPP_U   (0UL << MSTATUS_MPP_OFF)
#define MSTATUS_MPP_S   (1UL << MSTATUS_MPP_OFF)
#define MSTATUS_MPP_M   (3UL << MSTATUS_MPP_OFF)

/* ===================================================================
 * Smrnmi CSRs and fields
 * =================================================================== */
#define CSR_MNSCRATCH   0x740
#define CSR_MNEPC       0x741
#define CSR_MNCAUSE     0x742
#define CSR_MNSTATUS    0x744

/* mnstatus fields */
#define MNSTATUS_NMIE_BIT       BIT(3)
#define MNSTATUS_MNPP_OFF       11
#define MNSTATUS_MNPP_MASK      BIT_MASK(11, 2)
#define MNSTATUS_MNPV_BIT       BIT(7)
#define MNSTATUS_MNPELP_BIT     BIT(9)   /* Zicfilp previous ELP */

/* mnstatus.MNPP privilege encodings (same as mstatus.MPP) */
#define MNPP_U  0
#define MNPP_S  1
#define MNPP_M  3

/* MNRET instruction encoding:
 * 0111000 00010 00000 000 00000 1110011 */
#define INSN_MNRET              0x70200073

#ifndef __ASSEMBLER__
#define MNCAUSE_INTERRUPT_BIT   (1UL << (__riscv_xlen - 1))
#endif

/* ===================================================================
 * Smctr / Ssctr: CTR CSRs and shared field layout
 * (mctrctl and sctrctl share the field layout; sctrctl.M and
 * sctrctl.MTE are read-only zero per SPEC smctr.adoc)
 * =================================================================== */
#define CSR_MCTRCTL     0x34E
#define CSR_SCTRCTL     0x14E
#define CSR_SCTRSTATUS  0x14F
#define CSR_SCTRDEPTH   0x15F

/* ctrctl bit definitions per SPEC smctr.adoc */
#define CTRCTL_U            (1ULL << 0)
#define CTRCTL_S            (1ULL << 1)
#define CTRCTL_M            (1ULL << 2)
#define CTRCTL_RASEMU       (1ULL << 7)
#define CTRCTL_STE          (1ULL << 8)
#define CTRCTL_MTE          (1ULL << 9)
#define CTRCTL_BPFRZ        (1ULL << 11)
#define CTRCTL_LCOFIFRZ     (1ULL << 12)
#define CTRCTL_EXCINH       (1ULL << 33)
#define CTRCTL_INTRINH      (1ULL << 34)
#define CTRCTL_TRETINH      (1ULL << 35)
#define CTRCTL_NTBREN       (1ULL << 36)
#define CTRCTL_TKBRINH      (1ULL << 37)
#define CTRCTL_INDCALLINH   (1ULL << 40)
#define CTRCTL_DIRCALLINH   (1ULL << 41)
#define CTRCTL_INDJMPINH    (1ULL << 42)
#define CTRCTL_DIRJMPINH    (1ULL << 43)
#define CTRCTL_CORSWAPINH   (1ULL << 44)
#define CTRCTL_RETINH       (1ULL << 45)
#define CTRCTL_INDLJMPINH   (1ULL << 46)
#define CTRCTL_DIRLJMPINH   (1ULL << 47)
#define CTRCTL_CUSTOM_MASK  (0xFULL << 60)

/* ctrsource field */
#define CTRSOURCE_V_BIT         (1ULL << 0)

/* ctrdata fields */
#define CTRDATA_TYPE_MASK       0xFULL
#define CTRDATA_TYPE_EXCEPTION  1
#define CTRDATA_TYPE_INTERRUPT  2
#define CTRDATA_TYPE_TRAPRET    3
#define CTRDATA_TYPE_NTBRANCH   4
#define CTRDATA_TYPE_TKBRANCH   5
#define CTRDATA_TYPE_INDCALL    8
#define CTRDATA_TYPE_DIRCALL    9
#define CTRDATA_TYPE_INDJMP     10
#define CTRDATA_TYPE_DIRJMP     11
#define CTRDATA_TYPE_CORSWAP    12
#define CTRDATA_TYPE_RET        13
#define CTRDATA_TYPE_INDLJMP    14
#define CTRDATA_TYPE_DIRLJMP    15
#define CTRDATA_CCV_BIT         (1ULL << 15)
#define CTRDATA_CC_MASK         (0xFFFFULL << 16)
#define CTRDATA_CCE_SHIFT       28  /* CC[15:12] = CCE */
#define CTRDATA_CCM_MASK        0xFFFULL  /* CC[11:0] = CCM */

/* ===================================================================
 * RV32 high-half M-mode CSRs
 * =================================================================== */
#if __riscv_xlen == 32
#define CSR_MHPMEVENTH3   0x723
#define CSR_MHPMEVENTH4   0x724
#define CSR_MHPMEVENTH5   0x725
#define CSR_MHPMEVENTH6   0x726
#define CSR_MHPMEVENTH7   0x727
#define CSR_MHPMEVENTH8   0x728
#define CSR_MHPMEVENTH9   0x729
#define CSR_MHPMEVENTH10  0x72A
#define CSR_MHPMEVENTH11  0x72B
#define CSR_MHPMEVENTH12  0x72C
#define CSR_MHPMEVENTH13  0x72D
#define CSR_MHPMEVENTH14  0x72E
#define CSR_MHPMEVENTH15  0x72F
#define CSR_MHPMEVENTH16  0x730
#define CSR_MHPMEVENTH17  0x731
#define CSR_MHPMEVENTH18  0x732
#define CSR_MHPMEVENTH19  0x733
#define CSR_MHPMEVENTH20  0x734
#define CSR_MHPMEVENTH21  0x735
#define CSR_MHPMEVENTH22  0x736
#define CSR_MHPMEVENTH23  0x737
#define CSR_MHPMEVENTH24  0x738
#define CSR_MHPMEVENTH25  0x739
#define CSR_MHPMEVENTH26  0x73A
#define CSR_MHPMEVENTH27  0x73B
#define CSR_MHPMEVENTH28  0x73C
#define CSR_MHPMEVENTH29  0x73D
#define CSR_MHPMEVENTH30  0x73E
#define CSR_MHPMEVENTH31  0x73F

#define CSR_MCYCLEH       0xB80
#define CSR_MINSTRETH     0xB82

#define CSR_MHPMCOUNTERH3  0xB83
#define CSR_MHPMCOUNTERH4  0xB84
#define CSR_MHPMCOUNTERH5  0xB85
#define CSR_MHPMCOUNTERH6  0xB86
#define CSR_MHPMCOUNTERH7  0xB87
#define CSR_MHPMCOUNTERH8  0xB88
#define CSR_MHPMCOUNTERH9  0xB89
#define CSR_MHPMCOUNTERH10 0xB8A
#define CSR_MHPMCOUNTERH11 0xB8B
#define CSR_MHPMCOUNTERH12 0xB8C
#define CSR_MHPMCOUNTERH13 0xB8D
#define CSR_MHPMCOUNTERH14 0xB8E
#define CSR_MHPMCOUNTERH15 0xB8F
#define CSR_MHPMCOUNTERH16 0xB90
#define CSR_MHPMCOUNTERH17 0xB91
#define CSR_MHPMCOUNTERH18 0xB92
#define CSR_MHPMCOUNTERH19 0xB93
#define CSR_MHPMCOUNTERH20 0xB94
#define CSR_MHPMCOUNTERH21 0xB95
#define CSR_MHPMCOUNTERH22 0xB96
#define CSR_MHPMCOUNTERH23 0xB97
#define CSR_MHPMCOUNTERH24 0xB98
#define CSR_MHPMCOUNTERH25 0xB99
#define CSR_MHPMCOUNTERH26 0xB9A
#define CSR_MHPMCOUNTERH27 0xB9B
#define CSR_MHPMCOUNTERH28 0xB9C
#define CSR_MHPMCOUNTERH29 0xB9D
#define CSR_MHPMCOUNTERH30 0xB9E
#define CSR_MHPMCOUNTERH31 0xB9F

/* Parametric RV32 high-half addresses by index n (3..31). Note the two
 * families sit at different offsets from their low halves: mhpmevent is
 * +0x400 (0x323 -> 0x723) while mhpmcounter is +0x80 (0xB03 -> 0xB83). */
#define CSR_MHPMEVENTH(n)    (CSR_MHPMEVENTH3   + ((n) - 3))
#define CSR_MHPMCOUNTERH(n)  (CSR_MHPMCOUNTERH3 + ((n) - 3))
#endif

#endif /* SM_DEFS_H */
