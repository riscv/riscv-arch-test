/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef HYP_VS_TRAP_H
#define HYP_VS_TRAP_H

/* ===================================================================
 * VS-mode custom trap entry configuration
 *
 * Required by:
 *   - shvstvecd: testing vectored VS interrupt delivery
 *   - shvstvala: verifying vstval population on VS trap entry
 *
 * Provides utilities to:
 *   1. Configure vstvec from HS/M-mode before entering VS-mode
 *   2. Generate vectored trap handler tables for VS-mode
 *   3. Record trap information captured by VS-mode handlers
 *   4. Delegate specific exceptions to VS-mode and verify delivery
 *
 * Architecture:
 *   HS/M-mode sets up vstvec (Direct or Vectored) and delegates
 *   desired exceptions via hedeleg/hideleg. When VS-mode takes a
 *   trap, the custom VS handler records trap info, then returns
 *   to HS via ecall. HS-mode retrieves the record for assertions.
 * =================================================================== */

#include "types.h"
#include "encoding.h"

/* ===================================================================
 * VS trap record — captured by VS-mode trap handler
 * =================================================================== */

typedef struct {
    uintptr_t vs_cause;     /* vscause value at VS trap entry */
    uintptr_t vs_epc;       /* vsepc value at VS trap entry */
    uintptr_t vs_tval;      /* vstval value at VS trap entry */
    uintptr_t vs_tvec;      /* vstvec value (for vectored index check) */
    int       entry_idx;    /* vectored entry index (-1 = Direct mode) */
    bool      triggered;    /* whether VS trap was actually taken */
} vs_trap_record_t;

/* ===================================================================
 * VS trap handler configuration
 * =================================================================== */

typedef struct {
    uintptr_t handler_base;  /* base address of handler (must be in GPA
                              * identity-mapped region accessible by VS) */
    int       mode;          /* VSTVEC_MODE_DIRECT or VSTVEC_MODE_VECTORED */
    int       num_entries;   /* number of vectored entries (mode=Vectored) */
} vs_trap_config_t;

/**
 * vs_trap_setup - Configure VS-mode trap entry from HS/M-mode.
 *
 * Writes the vstvec CSR with (handler_base | mode).
 * For Vectored mode, handler_base must be aligned to at least
 * (num_entries * 4) bytes as per the trap vector table layout.
 *
 * Call this BEFORE entering VS-mode (before run_in_vs_mode or
 * two_stage_run_in_vs).
 */
void vs_trap_setup(vs_trap_config_t *cfg);

/**
 * vs_trap_setup_direct - Shorthand: configure Direct mode handler.
 */
void vs_trap_setup_direct(uintptr_t handler_addr);

/**
 * vs_trap_setup_framework - Install the framework's own VS-mode entry.
 *
 * Opt-in alternative to handing vs_trap_setup_direct() a suite-local stub.
 * The framework entry builds a full trap frame and runs the T-SBI dispatch
 * layer, so a VU/VS requester can use tsbi_ecall_test() and the S-level CSR
 * proxy from inside the guest, with everything above VS's authority forwarded
 * up the VS->HS->M chain.  The trap it does NOT serve is recorded exactly as
 * before and readable through vs_trap_get_last().
 *
 * Requires a valid VS-mode stack (the suites' flat identity map provides one).
 * Call from HS/M-mode before entering VS, same as vs_trap_setup().
 */
void vs_trap_setup_framework(void);

/**
 * vs_trap_handler - C body of the framework VS entry; called from assembly.
 *
 * FRAMEWORK-INTERNAL.  Declared here only so the definition is checked against
 * a prototype; test code has no reason to call it.
 */
void vs_trap_handler(uintptr_t *frame);

/* ===================================================================
 * VS-mode trap record access
 * =================================================================== */

/**
 * vs_trap_get_last - Retrieve the last VS trap record.
 *
 * Returns pointer to the internal record. Valid until the next
 * VS trap or vs_trap_clear() call.
 */
vs_trap_record_t *vs_trap_get_last(void);

/**
 * vs_trap_clear - Reset the VS trap record.
 */
void vs_trap_clear(void);

/**
 * vs_trap_was_triggered - Check if a VS trap was captured.
 */
bool vs_trap_was_triggered(void);

/* Scalar views of the last VS trap, used by trap.c's generic accessors to
 * merge a VS-delegated stimulus into trap_was_triggered()/trap_get_cause()/
 * trap_get_epc()/trap_get_tval(). trap.c declares these locally (it cannot
 * include this header without a circular dependency). */
uintptr_t vs_trap_get_cause(void);
uintptr_t vs_trap_get_epc(void);
uintptr_t vs_trap_get_tval(void);

/* ===================================================================
 * VS-mode trap verification support (shvstvecd specific)
 * =================================================================== */

/**
 * vstvec_supports_vectored - Probe if vstvec Vectored mode is supported.
 *
 * Writes MODE=1, reads back. Returns true if MODE reads back as 1.
 */
bool vstvec_supports_vectored(void);

#endif /* HYP_VS_TRAP_H */
