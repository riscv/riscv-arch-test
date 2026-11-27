/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#include "types.h"
#include "iopmp_cfg.h"
#include "iopmp_access.h"

/* ===================================================================
 * Capability Detection
 * =================================================================== */

uint32_t iopmp_get_hwcfg0(uintptr_t base)
{
    return iopmp_read(base, IOPMP_HWCFG0);
}

uint32_t iopmp_get_hwcfg1(uintptr_t base)
{
    return iopmp_read(base, IOPMP_HWCFG1);
}

uint32_t iopmp_get_hwcfg2(uintptr_t base)
{
    return iopmp_read(base, IOPMP_HWCFG2);
}

uint32_t iopmp_get_entry_offset_raw(uintptr_t base)
{
    return iopmp_read(base, IOPMP_ENTRYOFFSET);
}

unsigned int iopmp_get_rrid_num(uintptr_t base)
{
    return (unsigned int)(iopmp_get_hwcfg1(base) & HWCFG1_RRID_NUM_MASK);
}

unsigned int iopmp_get_entry_num(uintptr_t base)
{
    return (unsigned int)((iopmp_get_hwcfg1(base) & HWCFG1_ENTRY_NUM_MASK)
                          >> HWCFG1_ENTRY_NUM_SHIFT);
}

unsigned int iopmp_get_md_num(uintptr_t base)
{
    return (unsigned int)((iopmp_get_hwcfg0(base) & HWCFG0_MD_NUM_MASK)
                          >> HWCFG0_MD_NUM_SHIFT);
}

unsigned int iopmp_get_prio_entry(uintptr_t base)
{
    return (unsigned int)(iopmp_get_hwcfg2(base) & HWCFG2_PRIO_ENTRY_MASK);
}

uint8_t iopmp_get_mdcfg_fmt(uintptr_t base)
{
    return (uint8_t)((iopmp_get_hwcfg0(base) & HWCFG0_MDCFG_FMT_MASK)
                     >> HWCFG0_MDCFG_FMT_SHIFT);
}

uint8_t iopmp_get_srcmd_fmt(uintptr_t base)
{
    return (uint8_t)((iopmp_get_hwcfg0(base) & HWCFG0_SRCMD_FMT_MASK)
                     >> HWCFG0_SRCMD_FMT_SHIFT);
}

uint8_t iopmp_get_md_entry_num(uintptr_t base)
{
    return (uint8_t)((iopmp_get_hwcfg0(base) & HWCFG0_MD_ENTRY_NUM_MASK)
                     >> HWCFG0_MD_ENTRY_NUM_SHIFT);
}

bool iopmp_is_tor_supported(uintptr_t base)
{
    return (iopmp_get_hwcfg0(base) & HWCFG0_TOR_EN) != 0;
}

bool iopmp_is_sps_enabled(uintptr_t base)
{
    return (iopmp_get_hwcfg0(base) & HWCFG0_SPS_EN) != 0;
}

bool iopmp_is_user_cfg_enabled(uintptr_t base)
{
    return (iopmp_get_hwcfg0(base) & HWCFG0_USER_CFG_EN) != 0;
}

bool iopmp_is_chk_x(uintptr_t base)
{
    return (iopmp_get_hwcfg0(base) & HWCFG0_CHK_X) != 0;
}

bool iopmp_is_no_x(uintptr_t base)
{
    return (iopmp_get_hwcfg0(base) & HWCFG0_NO_X) != 0;
}

bool iopmp_is_no_w(uintptr_t base)
{
    return (iopmp_get_hwcfg0(base) & HWCFG0_NO_W) != 0;
}

bool iopmp_is_stall_en(uintptr_t base)
{
    return (iopmp_get_hwcfg0(base) & HWCFG0_STALL_EN) != 0;
}

bool iopmp_is_peis(uintptr_t base)
{
    return (iopmp_get_hwcfg0(base) & HWCFG0_PEIS) != 0;
}

bool iopmp_is_pees(uintptr_t base)
{
    return (iopmp_get_hwcfg0(base) & HWCFG0_PEES) != 0;
}

bool iopmp_is_mfr_en(uintptr_t base)
{
    return (iopmp_get_hwcfg0(base) & HWCFG0_MFR_EN) != 0;
}

bool iopmp_is_addrh_en(uintptr_t base)
{
    return (iopmp_get_hwcfg0(base) & HWCFG0_ADDRH_EN) != 0;
}

bool iopmp_is_enable(uintptr_t base)
{
    return (iopmp_get_hwcfg0(base) & HWCFG0_ENABLE) != 0;
}

bool iopmp_is_prient_prog(uintptr_t base)
{
    return (iopmp_get_hwcfg0(base) & HWCFG0_PRIENT_PROG) != 0;
}

/* ===================================================================
 * IOPMP Enable
 * =================================================================== */

void iopmp_enable(uintptr_t base)
{
    uint32_t hwcfg0 = iopmp_get_hwcfg0(base);
    hwcfg0 |= HWCFG0_ENABLE;
    iopmp_write(base, IOPMP_HWCFG0, hwcfg0);
}

/* ===================================================================
 * Entry Configuration Helpers
 * =================================================================== */

uint32_t iopmp_build_entry_cfg(bool r, bool w, bool x, uint8_t mode)
{
    uint32_t cfg = 0;
    if (r) cfg |= ENTRY_CFG_R;
    if (w) cfg |= ENTRY_CFG_W;
    if (x) cfg |= ENTRY_CFG_X;
    cfg |= ((uint32_t)mode << ENTRY_CFG_A_SHIFT);
    return cfg;
}

void iopmp_set_entry_off(uintptr_t base, uint32_t entry_offset, unsigned int i)
{
    iopmp_write_entry_cfg(base, entry_offset, i, 0);
    iopmp_write_entry_addr(base, entry_offset, i, 0);
}

void iopmp_set_entry_na4(uintptr_t base, uint32_t entry_offset, unsigned int i,
                         uintptr_t region_addr, bool r, bool w, bool x)
{
    /* NA4: addr = region_addr >> 2 */
    uint32_t addr = (uint32_t)((region_addr >> 2) & 0xFFFFFFFFU);
    uint32_t cfg = iopmp_build_entry_cfg(r, w, x, IOPMP_A_NA4);
    iopmp_write_entry_addr(base, entry_offset, i, addr);
    iopmp_write_entry_cfg(base, entry_offset, i, cfg);
}

void iopmp_set_entry_tor(uintptr_t base, uint32_t entry_offset, unsigned int i,
                         uintptr_t top_addr, bool r, bool w, bool x)
{
    /* TOR: addr = top_addr >> 2 */
    uint32_t addr = (uint32_t)((top_addr >> 2) & 0xFFFFFFFFU);
    uint32_t cfg = iopmp_build_entry_cfg(r, w, x, IOPMP_A_TOR);
    iopmp_write_entry_addr(base, entry_offset, i, addr);
    iopmp_write_entry_cfg(base, entry_offset, i, cfg);
}

void iopmp_set_entry_napot(uintptr_t base, uint32_t entry_offset, unsigned int i,
                           uintptr_t base_addr, unsigned int order,
                           bool r, bool w, bool x)
{
    /* NAPOT: for a region of size 2^order starting at base_addr,
     * the encoded address = (base_addr >> 2) | ((1 << (order-3)) - 1)
     * For order >= 3 (minimum 8 bytes for NAPOT) */
    uint32_t napot_addr;
    if (order < 3) {
        /* NAPOT needs at least 8 bytes, fall back to NA4 equivalent */
        napot_addr = (uint32_t)((base_addr >> 2) & 0xFFFFFFFFU);
    } else {
        uint32_t mask = (1U << (order - 3)) - 1;
        napot_addr = (uint32_t)((base_addr >> 2) & 0xFFFFFFFFU) | mask;
    }
    uint32_t cfg = iopmp_build_entry_cfg(r, w, x, IOPMP_A_NAPOT);
    iopmp_write_entry_addr(base, entry_offset, i, napot_addr);
    iopmp_write_entry_cfg(base, entry_offset, i, cfg);
}

void iopmp_set_entry(uintptr_t base, uint32_t entry_offset, unsigned int i,
                     uint32_t addr, uint32_t cfg)
{
    iopmp_write_entry_addr(base, entry_offset, i, addr);
    iopmp_write_entry_cfg(base, entry_offset, i, cfg);
}

void iopmp_set_entry_suppress(uintptr_t base, uint32_t entry_offset, unsigned int i,
                              bool sire, bool siwe, bool sixe,
                              bool sere, bool sewe, bool sexe)
{
    uint32_t cfg = iopmp_read_entry_cfg(base, entry_offset, i);
    if (sire) cfg |= ENTRY_CFG_SIRE;
    if (siwe) cfg |= ENTRY_CFG_SIWE;
    if (sixe) cfg |= ENTRY_CFG_SIXE;
    if (sere) cfg |= ENTRY_CFG_SERE;
    if (sewe) cfg |= ENTRY_CFG_SEWE;
    if (sexe) cfg |= ENTRY_CFG_SEXE;
    iopmp_write_entry_cfg(base, entry_offset, i, cfg);
}

/* ===================================================================
 * SRCMD Table Helpers (Format 0)
 * =================================================================== */

void iopmp_set_srcmd_en(uintptr_t base, unsigned int s, uint32_t md_bits,
                        bool lock)
{
    uint32_t val = (md_bits << 1) & MDLCK_MD_MASK;
    if (lock) val |= SRCMD_EN_L;
    iopmp_write_srcmd_en(base, s, val);
}

uint32_t iopmp_get_srcmd_en(uintptr_t base, unsigned int s)
{
    return iopmp_read_srcmd_en(base, s);
}

void iopmp_set_srcmd_r(uintptr_t base, unsigned int s, uint32_t md_bits)
{
    iopmp_write_srcmd_r(base, s, (md_bits << 1) & MDLCK_MD_MASK);
}

void iopmp_set_srcmd_w(uintptr_t base, unsigned int s, uint32_t md_bits)
{
    iopmp_write_srcmd_w(base, s, (md_bits << 1) & MDLCK_MD_MASK);
}

/* ===================================================================
 * SRCMD Table Helpers (Format 2)
 * =================================================================== */

void iopmp_set_srcmd_perm(uintptr_t base, unsigned int m, unsigned int s,
                          bool r, bool w)
{
    /* In Format 2, bit 2*s = read, bit 2*s+1 = write */
    uint32_t perm = iopmp_read_srcmd_perm(base, m);
    if (s < 16) {
        uint32_t bit_r = 1U << (2 * s);
        uint32_t bit_w = 1U << (2 * s + 1);
        perm &= ~(bit_r | bit_w);
        if (r) perm |= bit_r;
        if (w) perm |= bit_w;
        iopmp_write_srcmd_perm(base, m, perm);
    } else {
        uint32_t permh = iopmp_read_srcmd_permh(base, m);
        uint32_t bit_r = 1U << (2 * (s - 16));
        uint32_t bit_w = 1U << (2 * (s - 16) + 1);
        permh &= ~(bit_r | bit_w);
        if (r) permh |= bit_r;
        if (w) permh |= bit_w;
        iopmp_write_srcmd_permh(base, m, permh);
    }
}

/* ===================================================================
 * MDCFG Table Helpers (Format 0)
 * =================================================================== */

void iopmp_set_mdcfg(uintptr_t base, unsigned int m, uint16_t top_index)
{
    iopmp_write_mdcfg(base, m, (uint32_t)top_index);
}

uint32_t iopmp_get_mdcfg(uintptr_t base, unsigned int m)
{
    return iopmp_read_mdcfg(base, m);
}

/* ===================================================================
 * Error Configuration and Status
 * =================================================================== */

void iopmp_set_err_cfg(uintptr_t base, bool ie, bool rs, bool stall_violation_en)
{
    uint32_t val = 0;
    if (ie) val |= ERR_CFG_IE;
    if (rs) val |= ERR_CFG_RS;
    if (stall_violation_en) val |= ERR_CFG_STALL_VIOLATION_EN;
    iopmp_write(base, IOPMP_ERR_CFG, val);
}

uint32_t iopmp_get_err_info(uintptr_t base)
{
    return iopmp_read(base, IOPMP_ERR_INFO);
}

void iopmp_clear_err_info(uintptr_t base)
{
    iopmp_write(base, IOPMP_ERR_INFO, ERR_INFO_V);
}

uint32_t iopmp_get_err_reqid(uintptr_t base)
{
    return iopmp_read(base, IOPMP_ERR_REQID);
}

uint32_t iopmp_get_err_reqaddr(uintptr_t base)
{
    return iopmp_read(base, IOPMP_ERR_REQADDR);
}

uint32_t iopmp_get_err_reqaddrh(uintptr_t base)
{
    return iopmp_read(base, IOPMP_ERR_REQADDRH);
}

uint8_t iopmp_get_etype(uintptr_t base)
{
    return (uint8_t)((iopmp_get_err_info(base) & ERR_INFO_ETYPE_MASK)
                     >> ERR_INFO_ETYPE_SHIFT);
}

uint8_t iopmp_get_ttype(uintptr_t base)
{
    return (uint8_t)((iopmp_get_err_info(base) & ERR_INFO_TTYPE_MASK)
                     >> ERR_INFO_TTYPE_SHIFT);
}

/* ===================================================================
 * Stall Control
 * =================================================================== */

/* Detect which MD bits are implemented in MDSTALL.md field */
uint32_t iopmp_stall_detect_md_mask(uintptr_t base)
{
    /* Save original MDSTALL value to restore after probe */
    uint32_t saved = iopmp_read(base, IOPMP_MDSTALL);

    /* Write all 1s to md bits (bits [31:1]) */
    iopmp_write(base, IOPMP_MDSTALL, MDSTALL_MD_MASK);
    uint32_t val = iopmp_read(base, IOPMP_MDSTALL);
    /* Clear is_stalled bit, keep only md bits */
    val &= MDSTALL_MD_MASK;

    /* Restore original md bits (without exempt/is_stalled bit)
     * to avoid losing the caller's stall configuration */
    iopmp_write(base, IOPMP_MDSTALL, saved & MDSTALL_MD_MASK);
    return val;
}

void iopmp_stall_begin(uintptr_t base, bool exempt, uint32_t md_bits)
{
    uint32_t val = (md_bits << 1) & MDSTALL_MD_MASK;
    if (exempt) val |= MDSTALL_EXEMPT;
    iopmp_write(base, IOPMP_MDSTALL, val);
}

void iopmp_stall_add_rrid(uintptr_t base, unsigned int rrid, bool stall)
{
    uint32_t op = stall ? RRIDSCP_OP_STALL : RRIDSCP_OP_UNSTALL;
    uint32_t val = (rrid & RRIDSCP_RRID_MASK) | (op << RRIDSCP_OP_SHIFT);
    iopmp_write(base, IOPMP_RRIDSCP, val);
}

void iopmp_stall_wait(uintptr_t base)
{
    /* Poll until is_stalled == 1, with short timeout to prevent infinite hang.
     * Each iteration does a MMIO read which is slow on real hardware.
     * 10000 iterations should be more than enough for any compliant hardware. */
    volatile uint32_t timeout = 0;
    while ((iopmp_read(base, IOPMP_MDSTALL) & MDSTALL_IS_STALLED) == 0) {
        timeout++;
        if (timeout > 10000U) {
            /* Timeout: hardware did not assert is_stalled within
             * reasonable time. This indicates non-compliance. */
            break;
        }
    }
}

void iopmp_stall_resume(uintptr_t base)
{
    iopmp_write(base, IOPMP_MDSTALL, 0);
}

bool iopmp_stall_is_stalled(uintptr_t base)
{
    return (iopmp_read(base, IOPMP_MDSTALL) & MDSTALL_IS_STALLED) != 0;
}

uint32_t iopmp_stall_query_rrid(uintptr_t base, unsigned int rrid)
{
    /* op=0 (query), then read back stat field */
    uint32_t val = (rrid & RRIDSCP_RRID_MASK);
    iopmp_write(base, IOPMP_RRIDSCP, val);
    return (iopmp_read(base, IOPMP_RRIDSCP) & RRIDSCP_STAT_MASK)
           >> RRIDSCP_STAT_SHIFT;
}

/* ===================================================================
 * Lock Control
 * =================================================================== */

void iopmp_set_mdlck(uintptr_t base, uint32_t md_bits)
{
    uint32_t val = (md_bits << 1) & MDLCK_MD_MASK;
    iopmp_write(base, IOPMP_MDLCK, val);
}

void iopmp_set_mdcfglck(uintptr_t base, uint8_t f, bool lock)
{
    uint32_t val = ((uint32_t)f << MDCFGLCK_F_SHIFT) & MDCFGLCK_F_MASK;
    if (lock) val |= MDCFGLCK_L;
    iopmp_write(base, IOPMP_MDCFGLCK, val);
}

void iopmp_set_entrylck(uintptr_t base, uint16_t f, bool lock)
{
    uint32_t val = ((uint32_t)f << ENTRYLCK_F_SHIFT) & ENTRYLCK_F_MASK;
    if (lock) val |= ENTRYLCK_L;
    iopmp_write(base, IOPMP_ENTRYLCK, val);
}

/* ===================================================================
 * Capability Detection (cached)
 * =================================================================== */

void iopmp_detect_caps(uintptr_t base, iopmp_caps_t *caps)
{
    if (!caps) return;

    caps->hwcfg0 = iopmp_get_hwcfg0(base);
    caps->hwcfg1 = iopmp_get_hwcfg1(base);
    caps->hwcfg2 = iopmp_get_hwcfg2(base);
    caps->entry_offset = iopmp_get_entry_offset_raw(base);

    caps->rrid_num = iopmp_get_rrid_num(base);
    caps->entry_num = iopmp_get_entry_num(base);
    caps->md_num = iopmp_get_md_num(base);
    caps->prio_entry = iopmp_get_prio_entry(base);
    caps->mdcfg_fmt = iopmp_get_mdcfg_fmt(base);
    caps->srcmd_fmt = iopmp_get_srcmd_fmt(base);
    caps->md_entry_num = iopmp_get_md_entry_num(base);

    caps->tor_en = (caps->hwcfg0 & HWCFG0_TOR_EN) != 0;
    caps->sps_en = (caps->hwcfg0 & HWCFG0_SPS_EN) != 0;
    caps->user_cfg_en = (caps->hwcfg0 & HWCFG0_USER_CFG_EN) != 0;
    caps->chk_x = (caps->hwcfg0 & HWCFG0_CHK_X) != 0;
    caps->no_x = (caps->hwcfg0 & HWCFG0_NO_X) != 0;
    caps->no_w = (caps->hwcfg0 & HWCFG0_NO_W) != 0;
    caps->stall_en = (caps->hwcfg0 & HWCFG0_STALL_EN) != 0;
    caps->peis = (caps->hwcfg0 & HWCFG0_PEIS) != 0;
    caps->pees = (caps->hwcfg0 & HWCFG0_PEES) != 0;
    caps->mfr_en = (caps->hwcfg0 & HWCFG0_MFR_EN) != 0;
    caps->addrh_en = (caps->hwcfg0 & HWCFG0_ADDRH_EN) != 0;
    caps->enable = (caps->hwcfg0 & HWCFG0_ENABLE) != 0;
}
