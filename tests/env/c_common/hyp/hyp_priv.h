/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef HYP_PRIV_H
#define HYP_PRIV_H

/* ===================================================================
 * Hypervisor virtualized-privilege execution helpers
 *
 * Provides run_in_vs_mode() / run_in_vu_mode() so that tests can
 * execute a function in the VS / VU virtualized privilege levels
 * (V=1) and have it return back to M-mode for assertion/cleanup.
 *
 * The helpers cooperate with the goto_priv() / T-SBI GOTO protocol
 * machinery in common/trap.c + common/privilege.c, which has been
 * extended (under ENABLE_HYP) to set mstatus.MPV when the target
 * privilege has bit 2 (PRIV_VU=4 / PRIV_VS=5).
 * =================================================================== */

#include "types.h"
#include "test_framework.h"   /* for PRIV_VS / PRIV_VU */

/* Run fn(arg) in VS-mode (V=1, nominal S). Returns fn's return value. */
uintptr_t run_in_vs_mode(uintptr_t (*fn)(uintptr_t), uintptr_t arg);

/* Run fn(arg) in VU-mode (V=1, nominal U). Returns fn's return value. */
uintptr_t run_in_vu_mode(uintptr_t (*fn)(uintptr_t), uintptr_t arg);

/* ===================================================================
 * Direct privilege-level switching
 *
 * These provide finer-grained control compared to run_in_vs/vu_mode.
 * They switch privilege but do NOT automatically return — the caller
 * must arrange a return path (e.g., ecall → return_to_hs_mode).
 * =================================================================== */

/**
 * goto_vs_mode - Switch from HS-mode to VS-mode
 *
 * Sets hstatus.SPV=1, sstatus.SPP=1, then executes sret.
 * Must be called from HS-mode (i.e., current_priv == PRIV_S).
 * The caller must set sepc to the desired entry point before calling.
 */
void goto_vs_mode(void) __attribute__((noreturn));

/**
 * goto_vu_mode - Switch from VS-mode to VU-mode
 *
 * Sets sstatus.SPP=0 (actually vsstatus.SPP in V=1), then sret.
 * Must be called from VS-mode. The caller must set sepc (vsepc).
 */
void goto_vu_mode(void) __attribute__((noreturn));

/**
 * return_to_hs_mode - Return from VS/VU-mode to HS-mode
 *
 * Issues ecall. Assumes ecall is NOT delegated to VS-mode (hedeleg
 * bit for ecall-from-VS is clear), so it traps to M-mode which
 * bounces back to HS-mode (or directly if medeleg is set).
 */
void return_to_hs_mode(void);

/**
 * get_virt_priv - Get current virtualization-aware privilege level
 *
 * Returns: PRIV_M / PRIV_S (HS) / PRIV_U / PRIV_VS / PRIV_VU
 */
unsigned get_virt_priv(void);

#endif /* HYP_PRIV_H */
