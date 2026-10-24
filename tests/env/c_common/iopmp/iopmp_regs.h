/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef IOPMP_REGS_H
#define IOPMP_REGS_H

#include "types.h"

/* ===================================================================
 * IOPMP Register Offsets (from IOPMP base address)
 * Based on RISC-V IOPMP 0.7 Specification, Chapter 5
 * =================================================================== */

/* INFO registers */
#define IOPMP_VERSION         0x0000U
#define IOPMP_IMPLEMENTATION  0x0004U
#define IOPMP_HWCFG0          0x0008U
#define IOPMP_HWCFG1          0x000CU
#define IOPMP_HWCFG2          0x0010U
#define IOPMP_ENTRYOFFSET     0x0014U
#define IOPMP_HWCFG_USER      0x002CU

/* Programming Protection registers */
#define IOPMP_MDSTALL         0x0030U
#define IOPMP_MDSTALLH        0x0034U
#define IOPMP_RRIDSCP         0x0038U

/* Configuration Protection registers */
#define IOPMP_MDLCK           0x0040U
#define IOPMP_MDLCKH          0x0044U
#define IOPMP_MDCFGLCK        0x0048U
#define IOPMP_ENTRYLCK        0x004CU

/* Error Reporting registers */
#define IOPMP_ERR_CFG         0x0060U
#define IOPMP_ERR_INFO        0x0064U
#define IOPMP_ERR_REQADDR     0x0068U
#define IOPMP_ERR_REQADDRH    0x006CU
#define IOPMP_ERR_REQID       0x0070U
#define IOPMP_ERR_MFR         0x0074U
#define IOPMP_ERR_MSIADDR     0x0078U
#define IOPMP_ERR_MSIADDRH    0x007CU
#define IOPMP_ERR_USER_BASE   0x0080U

/* MDCFG Table base (Format 0 only, m = 0..md_num-1) */
#define IOPMP_MDCFG_BASE      0x0800U
#define IOPMP_MDCFG_STRIDE    4U

/* SRCMD Table base (Format 0: s = 0..rrid_num-1; Format 2: m = 0..md_num-1) */
#define IOPMP_SRCMD_BASE      0x1000U
#define IOPMP_SRCMD_STRIDE    32U

/* Entry array stride (each entry = 16 bytes: addr, addrh, cfg, user_cfg) */
#define IOPMP_ENTRY_STRIDE    16U
#define IOPMP_ENTRY_ADDR_OFF  0U
#define IOPMP_ENTRY_ADDRH_OFF 4U
#define IOPMP_ENTRY_CFG_OFF   8U
#define IOPMP_ENTRY_USER_OFF  12U

/* ===================================================================
 * HWCFG0 Field Definitions
 * =================================================================== */

#define HWCFG0_MDCFG_FMT_MASK     0x00000003U
#define HWCFG0_MDCFG_FMT_SHIFT    0
#define HWCFG0_SRCMD_FMT_MASK     0x0000000CU
#define HWCFG0_SRCMD_FMT_SHIFT    2
#define HWCFG0_TOR_EN             (1U << 4)
#define HWCFG0_SPS_EN             (1U << 5)
#define HWCFG0_USER_CFG_EN        (1U << 6)
#define HWCFG0_PRIENT_PROG        (1U << 7)
#define HWCFG0_RRID_TRANSL_EN    (1U << 8)
#define HWCFG0_RRID_TRANSL_PROG  (1U << 9)
#define HWCFG0_CHK_X              (1U << 10)
#define HWCFG0_NO_X               (1U << 11)
#define HWCFG0_NO_W               (1U << 12)
#define HWCFG0_STALL_EN           (1U << 13)
#define HWCFG0_PEIS                (1U << 14)
#define HWCFG0_PEES                (1U << 15)
#define HWCFG0_MFR_EN              (1U << 16)
#define HWCFG0_MD_ENTRY_NUM_MASK   0x007F0000U
#define HWCFG0_MD_ENTRY_NUM_SHIFT  17
#define HWCFG0_MD_NUM_MASK         0x3F000000U
#define HWCFG0_MD_NUM_SHIFT        24
#define HWCFG0_ADDRH_EN           (1U << 30)
#define HWCFG0_ENABLE             (1U << 31)

/* ===================================================================
 * HWCFG1 Field Definitions
 * =================================================================== */

#define HWCFG1_RRID_NUM_MASK    0x0000FFFFU
#define HWCFG1_ENTRY_NUM_MASK   0xFFFF0000U
#define HWCFG1_ENTRY_NUM_SHIFT  16

/* ===================================================================
 * HWCFG2 Field Definitions
 * =================================================================== */

#define HWCFG2_PRIO_ENTRY_MASK     0x0000FFFFU
#define HWCFG2_RRID_TRANSL_MASK    0xFFFF0000U
#define HWCFG2_RRID_TRANSL_SHIFT   16

/* ===================================================================
 * ENTRY_CFG Field Definitions
 * =================================================================== */

#define ENTRY_CFG_R        (1U << 0)
#define ENTRY_CFG_W        (1U << 1)
#define ENTRY_CFG_X        (1U << 2)
#define ENTRY_CFG_A_MASK   0x00000018U
#define ENTRY_CFG_A_SHIFT  3
#define ENTRY_CFG_SIRE     (1U << 5)
#define ENTRY_CFG_SIWE     (1U << 6)
#define ENTRY_CFG_SIXE     (1U << 7)
#define ENTRY_CFG_SERE     (1U << 8)
#define ENTRY_CFG_SEWE     (1U << 9)
#define ENTRY_CFG_SEXE     (1U << 10)

/* ===================================================================
 * ERR_CFG Field Definitions
 * =================================================================== */

#define ERR_CFG_L                   (1U << 0)
#define ERR_CFG_IE                  (1U << 1)
#define ERR_CFG_RS                  (1U << 2)
#define ERR_CFG_MSI_EN              (1U << 3)
#define ERR_CFG_STALL_VIOLATION_EN  (1U << 4)
#define ERR_CFG_MSIDATA_MASK        0x0007FF00U
#define ERR_CFG_MSIDATA_SHIFT       8

/* ===================================================================
 * ERR_INFO Field Definitions
 * =================================================================== */

#define ERR_INFO_V          (1U << 0)
#define ERR_INFO_TTYPE_MASK 0x00000006U
#define ERR_INFO_TTYPE_SHIFT 1
#define ERR_INFO_MSI_WERR   (1U << 3)
#define ERR_INFO_ETYPE_MASK  0x000000F0U
#define ERR_INFO_ETYPE_SHIFT 4
#define ERR_INFO_SVC         (1U << 8)

/* ===================================================================
 * ERR_REQID Field Definitions
 * =================================================================== */

#define ERR_REQID_RRID_MASK  0x0000FFFFU
#define ERR_REQID_EID_MASK   0xFFFF0000U
#define ERR_REQID_EID_SHIFT  16

/* ===================================================================
 * MDSTALL Field Definitions
 * =================================================================== */

#define MDSTALL_EXEMPT      (1U << 0)
#define MDSTALL_IS_STALLED  (1U << 0)  /* same bit, read side */
#define MDSTALL_MD_MASK     0xFFFFFFFEU
#define MDSTALL_MD_SHIFT    1

/* ===================================================================
 * RRIDSCP Field Definitions
 * =================================================================== */

#define RRIDSCP_RRID_MASK    0x0000FFFFU
#define RRIDSCP_OP_MASK      0xC0000000U
#define RRIDSCP_OP_SHIFT     30
#define RRIDSCP_STAT_MASK    0xC0000000U
#define RRIDSCP_STAT_SHIFT   30

#define RRIDSCP_OP_QUERY     0
#define RRIDSCP_OP_STALL     1
#define RRIDSCP_OP_UNSTALL   2
#define RRIDSCP_OP_RESERVED  3

#define RRIDSCP_STAT_NOT_IMPL  0
#define RRIDSCP_STAT_STALLED   1
#define RRIDSCP_STAT_NOT_STALL 2
#define RRIDSCP_STAT_UNIMPL    3

/* ===================================================================
 * MDLCK Field Definitions
 * =================================================================== */

#define MDLCK_L          (1U << 0)
#define MDLCK_MD_MASK    0xFFFFFFFEU
#define MDLCK_MD_SHIFT   1

/* ===================================================================
 * MDCFGLCK Field Definitions
 * =================================================================== */

#define MDCFGLCK_L       (1U << 0)
#define MDCFGLCK_F_MASK  0x0000007EU
#define MDCFGLCK_F_SHIFT 1

/* ===================================================================
 * ENTRYLCK Field Definitions
 * =================================================================== */

#define ENTRYLCK_L       (1U << 0)
#define ENTRYLCK_F_MASK  0x0001FFFEU
#define ENTRYLCK_F_SHIFT 1

/* ===================================================================
 * Error Type Definitions
 * =================================================================== */

#define IOPMP_ETYPE_NONE            0x00U
#define IOPMP_ETYPE_ILLEGAL_READ    0x01U
#define IOPMP_ETYPE_ILLEGAL_WRITE   0x02U
#define IOPMP_ETYPE_ILLEGAL_IFETCH  0x03U
#define IOPMP_ETYPE_PARTIAL_HIT    0x04U
#define IOPMP_ETYPE_NOT_HIT         0x05U
#define IOPMP_ETYPE_UNKNOWN_RRID   0x06U
#define IOPMP_ETYPE_STALL_ERR      0x07U

/* Transaction type definitions */
#define IOPMP_TTYPE_NONE    0x00U
#define IOPMP_TTYPE_READ    0x01U
#define IOPMP_TTYPE_WRITE   0x02U
#define IOPMP_TTYPE_IFETCH  0x03U

/* ===================================================================
 * Address Mode Encodings (same as RISC-V PMP)
 * =================================================================== */

#define IOPMP_A_OFF    0U
#define IOPMP_A_TOR    1U
#define IOPMP_A_NA4    2U
#define IOPMP_A_NAPOT  3U

/* ===================================================================
 * SRCMD Table Format Constants
 * =================================================================== */

#define SRCMD_FMT0  0U
#define SRCMD_FMT1  1U
#define SRCMD_FMT2  2U

/* MDCFG Table Format Constants */
#define MDCFG_FMT0  0U
#define MDCFG_FMT1  1U
#define MDCFG_FMT2  2U

/* SRCMD_EN(s).l bit */
#define SRCMD_EN_L  (1U << 0)

#endif /* IOPMP_REGS_H */
