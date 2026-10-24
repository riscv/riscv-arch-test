/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef PM_CFG_H
#define PM_CFG_H

/* ===================================================================
 * Pointer Masking (PM) Configuration API
 *
 * Provides per-privilege-mode PM enable/disable/detect helpers.
 *
 * Each privilege mode's PM is controlled by the *next-higher* mode's
 * CSR (spec: norm:pm_config_next_higher):
 *   - U-mode PM  -> senvcfg.PMM   (Ssnpm)
 *   - S-mode PM  -> menvcfg.PMM   (Smnpm)
 *   - M-mode PM  -> mseccfg.PMM   (Smmpm)
 *
 * All functions assume execution in M-mode unless noted otherwise.
 * =================================================================== */

#include "types.h"
#include "encoding.h"

/* ===================================================================
 * Per-mode PM control
 * =================================================================== */

/* senvcfg.PMM -> controls U-mode PM (Ssnpm) */
void     pm_set_umode(unsigned pmm);
unsigned pm_get_umode(void);

/* menvcfg.PMM -> controls S-mode PM (Smnpm) */
void     pm_set_smode(unsigned pmm);
unsigned pm_get_smode(void);

/* mseccfg.PMM -> controls M-mode PM (Smmpm) */
void     pm_set_mmode(unsigned pmm);
unsigned pm_get_mmode(void);

/* henvcfg.PMM -> controls VS-mode PM (Ssnpm, requires H ext) */
void     pm_set_vsmode(unsigned pmm);
unsigned pm_get_vsmode(void);

/* hstatus.HUPMM -> controls PM for HLV/HSV in U-mode as VU (Ssnpm, H ext) */
void     pm_set_hupmm(unsigned pmm);
unsigned pm_get_hupmm(void);

/* ===================================================================
 * Extension detection
 *
 * Each function tries to write a non-zero PMM value and reads back.
 * Returns true if the PMM field is writable (extension implemented).
 * Uses trap_expect_begin/end to handle cases where the CSR itself
 * does not exist.
 * =================================================================== */

bool detect_ssnpm(void);   /* senvcfg.PMM writable? */
bool detect_smnpm(void);   /* menvcfg.PMM writable? */
bool detect_smmpm(void);   /* mseccfg.PMM writable? */
bool detect_ssnpm_hyp(void); /* henvcfg.PMM + hstatus.HUPMM writable? (H ext) */

/* ===================================================================
 * PMLEN helpers
 * =================================================================== */

/* Convert PMM encoding to PMLEN value */
static inline unsigned pmm_to_pmlen(unsigned pmm) {
    switch (pmm) {
    case PMM_PMLEN7:  return 7;
    case PMM_PMLEN16: return 16;
    default:          return 0;
    }
}

/* Get the supported PMLEN values for a given detection function.
 * Returns a bitmask: bit 0 = PMLEN7 supported, bit 1 = PMLEN16 supported */
unsigned pm_detect_supported_pmlen(bool (*detect_fn)(void),
                                   void (*set_fn)(unsigned),
                                   unsigned (*get_fn)(void));

/* Non-destructive PMLEN detection for M-mode (mseccfg).
 * Avoids writing PMLEN16 to prevent sticky bit pollution.
 * Returns same bitmask as pm_detect_supported_pmlen. */
unsigned pm_detect_supported_pmlen_mmode(void);

#endif /* PM_CFG_H */
