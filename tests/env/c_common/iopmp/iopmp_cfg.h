/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef IOPMP_CFG_H
#define IOPMP_CFG_H

#include "types.h"
#include "iopmp_regs.h"

/* ===================================================================
 * IOPMP Capability Detection
 * =================================================================== */

uint32_t iopmp_get_hwcfg0(uintptr_t base);
uint32_t iopmp_get_hwcfg1(uintptr_t base);
uint32_t iopmp_get_hwcfg2(uintptr_t base);
uint32_t iopmp_get_entry_offset_raw(uintptr_t base);

unsigned int iopmp_get_rrid_num(uintptr_t base);
unsigned int iopmp_get_entry_num(uintptr_t base);
unsigned int iopmp_get_md_num(uintptr_t base);
unsigned int iopmp_get_prio_entry(uintptr_t base);
uint8_t iopmp_get_mdcfg_fmt(uintptr_t base);
uint8_t iopmp_get_srcmd_fmt(uintptr_t base);
uint8_t iopmp_get_md_entry_num(uintptr_t base);

bool iopmp_is_tor_supported(uintptr_t base);
bool iopmp_is_sps_enabled(uintptr_t base);
bool iopmp_is_user_cfg_enabled(uintptr_t base);
bool iopmp_is_chk_x(uintptr_t base);
bool iopmp_is_no_x(uintptr_t base);
bool iopmp_is_no_w(uintptr_t base);
bool iopmp_is_stall_en(uintptr_t base);
bool iopmp_is_peis(uintptr_t base);
bool iopmp_is_pees(uintptr_t base);
bool iopmp_is_mfr_en(uintptr_t base);
bool iopmp_is_addrh_en(uintptr_t base);
bool iopmp_is_enable(uintptr_t base);
bool iopmp_is_prient_prog(uintptr_t base);

/* ===================================================================
 * IOPMP Enable / Disable
 * =================================================================== */

void iopmp_enable(uintptr_t base);

/* ===================================================================
 * Entry Configuration Helpers
 * =================================================================== */

/* Build ENTRY_CFG value from permission and mode bits */
uint32_t iopmp_build_entry_cfg(bool r, bool w, bool x, uint8_t mode);

/* Set entry to OFF mode (disable) */
void iopmp_set_entry_off(uintptr_t base, uint32_t entry_offset, unsigned int i);

/* Set entry with NA4 address mode */
void iopmp_set_entry_na4(uintptr_t base, uint32_t entry_offset, unsigned int i,
                         uintptr_t region_addr, bool r, bool w, bool x);

/* Set entry with TOR address mode (requires tor_en=1) */
void iopmp_set_entry_tor(uintptr_t base, uint32_t entry_offset, unsigned int i,
                         uintptr_t top_addr, bool r, bool w, bool x);

/* Set entry with NAPOT address mode */
void iopmp_set_entry_napot(uintptr_t base, uint32_t entry_offset, unsigned int i,
                           uintptr_t base_addr, unsigned int order,
                           bool r, bool w, bool x);

/* Generic entry configuration */
void iopmp_set_entry(uintptr_t base, uint32_t entry_offset, unsigned int i,
                     uint32_t addr, uint32_t cfg);

/* Set interrupt/error suppression bits on an entry */
void iopmp_set_entry_suppress(uintptr_t base, uint32_t entry_offset, unsigned int i,
                              bool sire, bool siwe, bool sixe,
                              bool sere, bool sewe, bool sexe);

/* ===================================================================
 * SRCMD Table Helpers (Format 0)
 * =================================================================== */

void iopmp_set_srcmd_en(uintptr_t base, unsigned int s, uint32_t md_bits,
                        bool lock);
uint32_t iopmp_get_srcmd_en(uintptr_t base, unsigned int s);
void iopmp_set_srcmd_r(uintptr_t base, unsigned int s, uint32_t md_bits);
void iopmp_set_srcmd_w(uintptr_t base, unsigned int s, uint32_t md_bits);

/* ===================================================================
 * SRCMD Table Helpers (Format 2)
 * =================================================================== */

void iopmp_set_srcmd_perm(uintptr_t base, unsigned int m, unsigned int s,
                          bool r, bool w);

/* ===================================================================
 * MDCFG Table Helpers (Format 0)
 * =================================================================== */

void iopmp_set_mdcfg(uintptr_t base, unsigned int m, uint16_t top_index);
uint32_t iopmp_get_mdcfg(uintptr_t base, unsigned int m);

/* ===================================================================
 * Error Configuration and Status
 * =================================================================== */

void iopmp_set_err_cfg(uintptr_t base, bool ie, bool rs, bool stall_violation_en);
uint32_t iopmp_get_err_info(uintptr_t base);
void iopmp_clear_err_info(uintptr_t base);
uint32_t iopmp_get_err_reqid(uintptr_t base);
uint32_t iopmp_get_err_reqaddr(uintptr_t base);
uint32_t iopmp_get_err_reqaddrh(uintptr_t base);
uint8_t iopmp_get_etype(uintptr_t base);
uint8_t iopmp_get_ttype(uintptr_t base);

/* ===================================================================
 * Stall Control
 * =================================================================== */

/* Detect which MD bits are implemented in MDSTALL.md field.
 * Writes all 1s and reads back to determine implemented bits. */
uint32_t iopmp_stall_detect_md_mask(uintptr_t base);

void iopmp_stall_begin(uintptr_t base, bool exempt, uint32_t md_bits);
void iopmp_stall_add_rrid(uintptr_t base, unsigned int rrid, bool stall);
void iopmp_stall_wait(uintptr_t base);
void iopmp_stall_resume(uintptr_t base);
bool iopmp_stall_is_stalled(uintptr_t base);
uint32_t iopmp_stall_query_rrid(uintptr_t base, unsigned int rrid);

/* ===================================================================
 * Lock Control
 * =================================================================== */

void iopmp_set_mdlck(uintptr_t base, uint32_t md_bits);
void iopmp_set_mdcfglck(uintptr_t base, uint8_t f, bool lock);
void iopmp_set_entrylck(uintptr_t base, uint16_t f, bool lock);

/* ===================================================================
 * Reset and Initialization
 * =================================================================== */

void iopmp_reset(uintptr_t base);

/* Cached capability structure for convenience */
typedef struct {
    uint32_t hwcfg0;
    uint32_t hwcfg1;
    uint32_t hwcfg2;
    uint32_t entry_offset;
    unsigned int rrid_num;
    unsigned int entry_num;
    unsigned int md_num;
    unsigned int prio_entry;
    uint8_t mdcfg_fmt;
    uint8_t srcmd_fmt;
    uint8_t md_entry_num;
    bool tor_en;
    bool sps_en;
    bool user_cfg_en;
    bool chk_x;
    bool no_x;
    bool no_w;
    bool stall_en;
    bool peis;
    bool pees;
    bool mfr_en;
    bool addrh_en;
    bool enable;
} iopmp_caps_t;

void iopmp_detect_caps(uintptr_t base, iopmp_caps_t *caps);

#endif /* IOPMP_CFG_H */
