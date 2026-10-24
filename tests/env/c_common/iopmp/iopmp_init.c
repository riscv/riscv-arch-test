/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#include "types.h"
#include "iopmp_cfg.h"
#include "iopmp_access.h"

/* ===================================================================
 * IOPMP Reset
 *
 * Clears all entries to OFF, clears error records, resets SRCMD/MDCFG
 * tables. Does NOT clear locked entries or pre-locked configurations.
 * =================================================================== */

void iopmp_reset(uintptr_t base)
{
    uint32_t hwcfg0 = iopmp_get_hwcfg0(base);
    uint32_t hwcfg1 = iopmp_get_hwcfg1(base);
    uint32_t entry_offset = iopmp_get_entry_offset_raw(base);
    unsigned int entry_num = (hwcfg1 & HWCFG1_ENTRY_NUM_MASK)
                             >> HWCFG1_ENTRY_NUM_SHIFT;
    unsigned int rrid_num = hwcfg1 & HWCFG1_RRID_NUM_MASK;
    unsigned int md_num = (hwcfg0 & HWCFG0_MD_NUM_MASK)
                          >> HWCFG0_MD_NUM_SHIFT;
    uint8_t mdcfg_fmt = (hwcfg0 & HWCFG0_MDCFG_FMT_MASK)
                        >> HWCFG0_MDCFG_FMT_SHIFT;
    uint8_t srcmd_fmt = (hwcfg0 & HWCFG0_SRCMD_FMT_MASK)
                        >> HWCFG0_SRCMD_FMT_SHIFT;

    /* Clear error info (write 1 to ERR_INFO.v) */
    iopmp_write(base, IOPMP_ERR_INFO, ERR_INFO_V);

    /* Clear ERR_CFG to default (ie=0, rs=0) */
    /* Do not touch if locked */
    uint32_t err_cfg = iopmp_read(base, IOPMP_ERR_CFG);
    if ((err_cfg & ERR_CFG_L) == 0) {
        iopmp_write(base, IOPMP_ERR_CFG, 0);
    }

    /* Clear all entries to OFF (skip locked entries) */
    uint32_t entrylck = iopmp_read(base, IOPMP_ENTRYLCK);
    unsigned int locked_entries = (entrylck & ENTRYLCK_F_MASK)
                                  >> ENTRYLCK_F_SHIFT;

    for (unsigned int i = locked_entries; i < entry_num; i++) {
        iopmp_write_entry_cfg(base, entry_offset, i, 0);
        iopmp_write_entry_addr(base, entry_offset, i, 0);
    }

    /* Clear MDCFG table (Format 0 only, skip locked) */
    if (mdcfg_fmt == MDCFG_FMT0) {
        uint32_t mdcfglck = iopmp_read(base, IOPMP_MDCFGLCK);
        unsigned int locked_mdcfg = (mdcfglck & MDCFGLCK_F_MASK)
                                    >> MDCFGLCK_F_SHIFT;
        for (unsigned int m = locked_mdcfg; m < md_num; m++) {
            iopmp_write_mdcfg(base, m, 0);
        }
    }

    /* Clear SRCMD table (Format 0 only) */
    if (srcmd_fmt == SRCMD_FMT0) {
        for (unsigned int s = 0; s < rrid_num; s++) {
            uint32_t srcmd_en = iopmp_read_srcmd_en(base, s);
            /* Skip if locked by SRCMD_EN(s).l */
            if (srcmd_en & SRCMD_EN_L) continue;

            iopmp_write_srcmd_en(base, s, 0);

            /* Clear SRCMD_R/W if SPS is enabled */
            if (hwcfg0 & HWCFG0_SPS_EN) {
                iopmp_write_srcmd_r(base, s, 0);
                iopmp_write_srcmd_w(base, s, 0);
            }
        }
    }

    /* Clear SRCMD table (Format 2) */
    if (srcmd_fmt == SRCMD_FMT2) {
        for (unsigned int m = 0; m < md_num; m++) {
            iopmp_write_srcmd_perm(base, m, 0);
            iopmp_write_srcmd_permh(base, m, 0);
        }
    }
}
