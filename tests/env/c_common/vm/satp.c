/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#include "vm.h"
#include "test_framework.h"

/* ===================================================================
 * External dependencies from privilege.c and trap.c
 * =================================================================== */

/* Privilege level definitions are in encoding.h. */

/* From privilege.c */
extern uintptr_t run_in_priv(unsigned priv, uintptr_t (*fn)(uintptr_t),
                              uintptr_t arg);

/* From trap_asm.S */
extern void s_trap_entry(void);

/* Linker-provided S-mode stack */
extern uintptr_t __smode_stack_end;

/* From csr_accessors.c */
extern uintptr_t csr_read(uint16_t csr);
extern void csr_write(uint16_t csr, uintptr_t val);

/* ===================================================================
 * PMP helpers for VM
 *
 * When running S-mode code, PMP must allow access. If no PMP entries
 * are configured, S/U-mode accesses will fail with access faults.
 * We use a high-numbered PMP entry (entry 15) with NAPOT covering
 * the entire address space to grant RWX permissions.
 * =================================================================== */

/* PMP constants (PMP_R, PMP_W, PMP_X, PMP_A_NAPOT, PMP_RWX) are
 * defined in sm_defs.h, included via encoding.h through vm.h. */

/* PMP entry index used by VM framework */
#define VM_PMP_ENTRY    15

/**
 * vm_pmp_allow_all - Set up PMP entry to allow S/U-mode full access
 *
 * Configures PMP entry VM_PMP_ENTRY as a NAPOT region covering the
 * entire address space with RWX permissions.
 *
 * pmpaddr = all ones => covers entire address space (2^(XLEN+2) bytes)
 * pmpcfg  = A=NAPOT | R | W | X
 */
static void vm_pmp_allow_all(void) {
    /* pmpaddr15 = all 1s => NAPOT covering entire address space */
    csr_write(CSR_PMPADDR0 + VM_PMP_ENTRY, (uintptr_t)-1);

    /* Read pmpcfg, set entry 15's byte to NAPOT|RWX */
#if __riscv_xlen == 64
    /* RV64: pmpcfg2 holds entries 8-15, entry 15 is byte 7 */
    int cfg_csr = CSR_PMPCFG0 + 2;  /* pmpcfg2 */
    int byte_offset = (VM_PMP_ENTRY % 8) * 8;  /* entry 15 => byte 7 => shift 56 */
#else
    /* RV32: pmpcfg3 holds entries 12-15, entry 15 is byte 3 */
    int cfg_csr = CSR_PMPCFG0 + 3;  /* pmpcfg3 */
    int byte_offset = (VM_PMP_ENTRY % 4) * 8;  /* entry 15 => byte 3 => shift 24 */
#endif

    uintptr_t cfg_val = csr_read(cfg_csr);
    uintptr_t mask = ~((uintptr_t)0xFF << byte_offset);
    cfg_val = (cfg_val & mask) | ((uintptr_t)(PMP_A_NAPOT | PMP_RWX) << byte_offset);
    csr_write(cfg_csr, cfg_val);
}

/**
 * vm_pmp_clear - Clear the PMP entry used by VM framework
 */
static void vm_pmp_clear(void) {
    csr_write(CSR_PMPADDR0 + VM_PMP_ENTRY, 0);

#if __riscv_xlen == 64
    int cfg_csr = CSR_PMPCFG0 + 2;
    int byte_offset = (VM_PMP_ENTRY % 8) * 8;
#else
    int cfg_csr = CSR_PMPCFG0 + 3;
    int byte_offset = (VM_PMP_ENTRY % 4) * 8;
#endif

    uintptr_t cfg_val = csr_read(cfg_csr);
    uintptr_t mask = ~((uintptr_t)0xFF << byte_offset);
    cfg_val = cfg_val & mask;
    csr_write(cfg_csr, cfg_val);
}

/* ===================================================================
 * sfence.vma helpers
 * =================================================================== */

/**
 * vm_sfence_vma - Execute sfence.vma with optional address/ASID
 */
void vm_sfence_vma(uintptr_t vaddr, uintptr_t asid) {
    if (vaddr == 0 && asid == 0) {
        /* Global flush */
        asm volatile("sfence.vma" ::: "memory");
    } else if (asid == 0) {
        /* Flush by address */
        asm volatile("sfence.vma %0, zero" :: "r"(vaddr) : "memory");
    } else if (vaddr == 0) {
        /* Flush by ASID */
        asm volatile("sfence.vma zero, %0" :: "r"(asid) : "memory");
    } else {
        /* Flush by address and ASID */
        asm volatile("sfence.vma %0, %1" :: "r"(vaddr), "r"(asid) : "memory");
    }
}

/* ===================================================================
 * satp Control
 * =================================================================== */

/**
 * vm_enable - Enable virtual memory by writing satp
 */
void vm_enable(pt_context_t *ctx, unsigned asid) {
    if (!ctx || !ctx->root_pt) {
        LOG_E("vm_enable: invalid context\n");
        return;
    }

    uintptr_t root_ppn = (uintptr_t)ctx->root_pt >> PAGE_SHIFT;
    uintptr_t satp_val = MAKE_SATP(ctx->mode, asid, root_ppn);

    CSRW(satp, satp_val);
    vm_sfence_vma(0, 0);
}

/**
 * vm_disable - Disable virtual memory (set satp to Bare mode)
 */
void vm_disable(void) {
    CSRW(satp, 0);
    vm_sfence_vma(0, 0);
}

/* ===================================================================
 * Mode Switching
 * =================================================================== */

/**
 * vm_switch_mode - Switch to a different Sv mode
 *
 * Disables VM, reinitializes page tables for the new mode,
 * and rebuilds the identity mapping with the same parameters.
 */
void vm_switch_mode(pt_context_t *ctx, int new_mode) {
    /* Save current mapping parameters */
    uintptr_t saved_base  = ctx->map_base;
    uintptr_t saved_size  = ctx->map_size;
    int       saved_level = ctx->map_level;

    /* Disable VM first */
    vm_disable();

    /* Reset page table pool and reinitialize */
    pt_pool_reset();
    pt_init(ctx, new_mode);

    /* Rebuild identity mapping if one was previously set up */
    if (saved_size > 0) {
        uintptr_t flags = PTE_V | PTE_RWXAD;
        pt_setup_identity_mapping(ctx, saved_base, saved_size,
                                  flags, saved_level);
    }
}

/* ===================================================================
 * S-mode Execution with VM
 * =================================================================== */

/**
 * vm_run_in_smode - Execute a function in S-mode with VM enabled
 *
 * Flow:
 * 0. Raise to M-mode (this helper owns M-level state; see below)
 * 1. Set up PMP to allow S-mode access
 * 2. Configure trap delegation (page faults -> S-mode)
 * 3. Set stvec to s_trap_entry
 * 4. Enable virtual memory (write satp)
 * 5. Switch to S-mode and execute fn(arg) via run_in_priv()
 * 6. On return, disable VM and restore delegation
 * 7. Drop back to the privilege the caller came in at
 *
 * Callable from any privilege level.  Under the T-SBI S-mode-normal model
 * (tsbi_design_brief.md section 1) tests run in S-mode, but this helper still
 * needs M-mode authority: it programs medeleg and, above all, satp.  Writing
 * satp from S and continuing to execute there would place the helper's OWN
 * next instruction fetch under the new translation, so a deliberately broken
 * page table -- exactly what these suites install to provoke a fault -- would
 * trap on the harness instead of on the payload it is meant to observe, and
 * the fetch would keep re-faulting.  Raising first keeps satp programmed
 * where translation does not apply and enters the payload through mret, so a
 * fault always lands on fn's access, just as it did when every caller was in
 * M-mode.  A caller already in M-mode (a -DTSBI_BOOT_MODE_M suite) pays
 * nothing: goto_priv() is a no-op at the same level.
 *
 * The page table context must have identity mapping set up
 * so that code and data addresses are valid in both M and S modes.
 */
uintptr_t vm_run_in_smode(pt_context_t *ctx,
                           uintptr_t (*fn)(uintptr_t),
                           uintptr_t arg) {
    /*
     * Step 0: own the M-level setup from wherever the caller is.
     */
    unsigned caller_priv = get_current_priv();
    if (caller_priv != PRIV_M)
        goto_priv(PRIV_M);

    /*
     * Step 1: Set up PMP to allow S-mode access
     *
     * RISC-V requires PMP rules for S/U-mode access. Without any
     * matching PMP entry, all S/U-mode accesses fail with access faults.
     * We set up a catch-all NAPOT entry covering the entire address space.
     *
     * entry.S already hoists an equivalent entry 0 configuration ahead of the
     * drop to S-mode, so this is belt-and-braces rather than the only line of
     * defence; it is kept because a suite may have reprogrammed PMP itself.
     */
    vm_pmp_allow_all();

    /*
     * Step 2: Configure trap delegation
     *
     * Delegate page faults and ecalls from U-mode to S-mode.
     * This allows the S-mode trap handler to handle page faults
     * while VM is enabled.
     *
     * IMPORTANT: do NOT delegate CAUSE_ECALL_FROM_S (cause 9). The
     * framework's _run_trampoline exits S-mode via `ecall` to ask
     * M-mode to switch current_priv back to M; that exit ecall MUST
     * be intercepted by the M-mode handler. Delegating it to S-mode
     * leaves the framework's ecall to be re-delivered to S-mode,
     * which causes infinite recursion (s_trap_handler -> goto_priv(M)
     * -> do_ecall -> ECALL_FROM_S -> s_trap_handler -> ...).
     *
     * Tests that need an S-mode-installed stvec to intercept S-mode
     * ecall (e.g. Sstvecd STVEC-DIR-01 / MULTI-01) cannot be expressed
     * with the current vm_run_in_smode shape and should be marked
     * SKIP at the call site.
     */
    uintptr_t medeleg = CSRR(medeleg);
    uintptr_t new_medeleg = medeleg |
        BIT(CAUSE_INST_PAGE_FAULT)  |
        BIT(CAUSE_LOAD_PAGE_FAULT)  |
        BIT(CAUSE_STORE_PAGE_FAULT) |
        BIT(CAUSE_ECALL_FROM_U);
    CSRW(medeleg, new_medeleg);

    /*
     * Step 3: Set up S-mode trap vector
     */
    CSRW(stvec, (uintptr_t)s_trap_entry);

    /*
     * Step 4: Enable virtual memory
     */
    vm_enable(ctx, 0);

    /*
     * Step 5: Execute function in S-mode
     *
     * run_in_priv handles the M->S transition via mret and
     * the S->M return via ecall. Since we have identity mapping,
     * all addresses (code, stack, data) are valid in both modes.
     */
    uintptr_t result = run_in_priv(PRIV_S, fn, arg);

    /*
     * Step 6: Clean up
     */
    vm_disable();
    CSRW(medeleg, medeleg);  /* Restore original delegation */
    vm_pmp_clear();          /* Remove VM PMP entry */

    /*
     * Step 6: hand control back at the privilege the caller came in at.
     * run_in_priv() has already returned us to M-mode.
     */
    if (get_current_priv() != caller_priv)
        goto_priv(caller_priv);

    return result;
}

/* ===================================================================
 * U-mode Execution with VM
 * =================================================================== */

/**
 * vm_run_in_umode - Execute a function in U-mode with VM enabled
 *
 * Similar to vm_run_in_smode but targets U-mode.
 *
 * Flow:
 * 0. Raise to M-mode (satp must not be programmed under the caller's own
 *    translation - see vm_run_in_smode for the full reasoning)
 * 1. Set up PMP to allow U-mode access
 * 2. Enable virtual memory (write satp)
 * 3. Switch to U-mode via run_in_priv(PRIV_U)
 * 4. On return, disable VM and clean up
 * 5. Drop back to the privilege the caller came in at
 *
 * Callable from any privilege level.
 * The page table context must have identity mapping set up with
 * PTE_U flag on all pages that fn will access, so that U-mode
 * can read/write/execute them.
 *
 * The ecall from U-mode (cause 8) returns the payload to the framework: it
 * is delegated to the S handler by the T-SBI baseline, which forwards the
 * GOTO_MMODE request up to M.  Page faults are NOT delegated for the sake of
 * this helper; they are caught by the trap_record mechanism for assertions.
 */
uintptr_t vm_run_in_umode(pt_context_t *ctx,
                           uintptr_t (*fn)(uintptr_t),
                           uintptr_t arg) {
    /*
     * Step 0: own the M-level setup from wherever the caller is.
     */
    unsigned caller_priv = get_current_priv();
    if (caller_priv != PRIV_M)
        goto_priv(PRIV_M);

    /*
     * Step 1: Set up PMP to allow U-mode access
     */
    vm_pmp_allow_all();

    /*
     * Step 1b: route this helper's traps to M-mode.
     *
     * The caller's page table maps the whole code region -- including this
     * framework's s_trap_entry -- as U=1 so the U-mode payload can execute it.
     * The T-SBI baseline delegates ecall-from-U and page faults to the S
     * handler, but with VM enabled an S-mode instruction fetch of a U=1 page
     * always faults (mstatus.SUM governs loads/stores, not fetches), so the
     * delegated trap re-faults on the handler entry in an infinite cause-12
     * storm.  Undelegate them here so the payload's traps are taken in M-mode
     * (physical fetch, recorded by m_trap_handler via trap_record) -- the
     * behaviour this helper's contract describes.  Restored in the cleanup. */
    uintptr_t medeleg = CSRR(medeleg);
    CSRW(medeleg, medeleg & ~(
        BIT(CAUSE_ECALL_FROM_U)      |
        BIT(CAUSE_INST_PAGE_FAULT)   |
        BIT(CAUSE_LOAD_PAGE_FAULT)   |
        BIT(CAUSE_STORE_PAGE_FAULT)));

    /*
     * Step 2: Enable virtual memory
     */
    vm_enable(ctx, 0);

    /*
     * Step 3: Execute function in U-mode
     *
     * run_in_priv(PRIV_U) uses mret with MPP=0 to jump directly
     * from M-mode to U-mode. The trampoline's ecall (cause 8,
     * ECALL_FROM_U) returns to M-mode via the M-mode trap handler.
     *
     * Since we use identity mapping, all addresses are valid in
     * both M and U modes, provided PTE_U is set on the pages.
     */
    uintptr_t result = run_in_priv(PRIV_U, fn, arg);

    /*
     * Step 4: Clean up
     */
    vm_disable();
    CSRW(medeleg, medeleg);  /* restore original delegation */
    vm_pmp_clear();

    /*
     * Step 5: hand control back at the privilege the caller came in at.
     */
    if (get_current_priv() != caller_priv)
        goto_priv(caller_priv);

    return result;
}
