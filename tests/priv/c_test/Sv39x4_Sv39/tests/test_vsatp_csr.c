/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/tests_2stage/test_group02_vsatp_csr.c
 *
 * Group 2: vsatp CSR semantics (TS-VSATP-01..07)
 *
 * vsatp (CSR 0x280) is the VS-stage address-translation register. It
 * is accessible from HS/M-mode (V=0) without trapping; from VS-mode
 * (V=1) the unprivileged access is fine but TVM/STVEC interactions
 * are out-of-scope here. These tests cover only the HS/M-mode WARL
 * behavior of vsatp itself, plus its independence from satp.
 *
 * Cases:
 *   TS-VSATP-01  V=1: VS-mode csrr satp reads vsatp (alias)
 *   TS-VSATP-02  V=1: VS-mode csrw satp writes vsatp (alias)
 *   TS-VSATP-03  V=1: write unsupported MODE via satp is ignored
 *   TS-VSATP-04  V=0: write unsupported MODE to vsatp -> WARL/ignored
 *   TS-VSATP-05  vsatp.PPN field is writable and reads back
 *   TS-VSATP-06  vsatp.ASID field obeys ASIDLEN (mask matches platform)
 *   TS-VSATP-07  hstatus.VTVM=1: VS-mode satp access -> virtual-inst (22)
 *
 * Source-included by per-suite test_register.c. Runs entirely from
 * M-mode using csr_accessors; does not require two_stage_helpers.
 * =================================================================== */

#include "two_stage_helpers.h"

/* ===================================================================
 * VS-mode helpers for satp alias tests.
 * When V=1, satp is an alias for vsatp.
 *
 * vs_read_satp() from common/hyp/hyp_test_helpers.h.
 * vs_satp_write_fn is local because it adds sfence.vma after the
 * write (TLB flush required for subsequent instruction fetches).
 * =================================================================== */

static uintptr_t vs_satp_write_fn(uintptr_t new_val) {
    CSRW(CSR_SATP, new_val);
    /* Flush TLB so subsequent instructions use the new mappings. */
    asm volatile ("sfence.vma" ::: "memory");
    return 0;
}

/* ===================================================================
 * TS-VSATP-01: V=1 — VS-mode csrr satp reads vsatp.
 *
 * Spec (norm:vsatp_sz_acc_op): When V=1, satp substitutes for vsatp.
 * From VS-mode, reading satp must return the vsatp value.
 * =================================================================== */
TEST_REGISTER(test_ts_vsatp_01_v1_satp_reads_vsatp);
bool test_ts_vsatp_01_v1_satp_reads_vsatp(void)
{
    TEST_BEGIN("TS-VSATP-01: V=1 csrr satp reads vsatp");
    REQUIRE_VSATP_MODE(SATP_MODE_SV39);

    uintptr_t saved = vsatp_read();

    /* Setup two-stage context (builds page tables in memory). */
    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SATP_MODE_SV39, HGATP_MODE_BARE);

    /* Activate two-stage (writes vsatp/hgatp CSRs). */
    two_stage_enable(&ctx, /*vmid=*/0);

    /* Read vsatp AFTER activation — this is what VS-mode should see. */
    uintptr_t expected = vsatp_read();

    /* Enter VS-mode (V=1) and read satp; should return vsatp. */
    uintptr_t got = run_in_vs_mode(vs_read_satp, 0);

    /* Manual cleanup (avoid double-cleanup from ts2_finish which
     * would zero vsatp before we can verify). */
    gpt_disable();
    CSRW(CSR_VSATP, 0);  /* vsatp = 0 */
    hyp_reset_state();

    TEST_ASSERT_EQ("V=1: csrr satp == vsatp", got, expected);

    vsatp_write(saved);
    asm volatile ("sfence.vma" ::: "memory");
    HYP_TEST_END();
}

/* ===================================================================
 * TS-VSATP-02: V=1 — VS-mode csrw satp writes vsatp.
 *
 * Spec (norm:vsatp_sz_acc_op): When V=1, writing satp actually
 * writes vsatp. Verify by reading vsatp from HS/M-mode afterward.
 * =================================================================== */
TEST_REGISTER(test_ts_vsatp_02_v1_satp_writes_vsatp);
bool test_ts_vsatp_02_v1_satp_writes_vsatp(void)
{
    TEST_BEGIN("TS-VSATP-02: V=1 csrw satp writes vsatp");
    REQUIRE_VSATP_MODE(SATP_MODE_SV39);

    uintptr_t saved = vsatp_read();

    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SATP_MODE_SV39, HGATP_MODE_BARE);

    /* Activate two-stage so vsatp has a valid root PPN. */
    two_stage_enable(&ctx, /*vmid=*/0);
    uintptr_t current_vsatp = vsatp_read();
    uintptr_t current_ppn = current_vsatp & ((1UL << 44) - 1);
    uintptr_t test_val = MAKE_VSATP(SATP_MODE_SV39, 0x55, current_ppn);

    /* VS-mode writes satp (=vsatp) with new ASID, same PPN. */
    (void)run_in_vs_mode(vs_satp_write_fn, test_val);

    /* Read vsatp BEFORE cleanup (cleanup would zero it). */
    uintptr_t got = vsatp_read();

    /* Manual cleanup. */
    gpt_disable();
    CSRW(CSR_VSATP, 0);  /* vsatp = 0 */
    hyp_reset_state();

    TEST_ASSERT_EQ("V=1: vsatp was written via satp", got, test_val);

    vsatp_write(saved);
    asm volatile ("sfence.vma" ::: "memory");
    HYP_TEST_END();
}

/* ===================================================================
 * TS-VSATP-03: V=1 — write unsupported MODE via satp is ignored.
 *
 * Spec (norm:vsatp_mode_unsupported_v1):
 *   "when V=1, a write to satp with an unsupported MODE value is
 *    ignored and no write to vsatp is effected."
 *
 * This differs from V=0 (TS-VSATP-04) where WARL is permitted.
 * =================================================================== */
TEST_REGISTER(test_ts_vsatp_03_v1_unsupported_mode_ignored);
bool test_ts_vsatp_03_v1_unsupported_mode_ignored(void)
{
    TEST_BEGIN("TS-VSATP-03: V=1 satp unsupported MODE ignored");
    REQUIRE_VSATP_MODE(SATP_MODE_SV39);

    uintptr_t saved = vsatp_read();

    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SATP_MODE_SV39, HGATP_MODE_BARE);

    /* Activate two-stage so vsatp has the actual VS root PPN. */
    two_stage_enable(&ctx, /*vmid=*/0);

    /* Read vsatp AFTER activation — this is the value that should
     * remain unchanged if the V=1 unsupported-MODE write is ignored. */
    uintptr_t pre_val = vsatp_read();

    /* VS-mode tries to write satp with reserved MODE=7. */
    uintptr_t bad_val = MAKE_VSATP(7, 0, 0x2000);
    (void)run_in_vs_mode(vs_satp_write_fn, bad_val);

    /* Read vsatp BEFORE cleanup. */
    uintptr_t got = vsatp_read();

    /* Manual cleanup. */
    gpt_disable();
    CSRW(CSR_VSATP, 0);
    hyp_reset_state();

    TEST_ASSERT_EQ("V=1: vsatp unchanged after unsupported MODE write via satp",
                   got, pre_val);

    vsatp_write(saved);
    asm volatile ("sfence.vma" ::: "memory");
    HYP_TEST_END();
}

/* ===================================================================
 * TS-VSATP-04: Writing an unsupported MODE to vsatp (V=0).
 *
 * Spec (norm:vsatp_mode_unsupported_v0):
 *   "When V=0, a write to vsatp with an unsupported MODE value is
 *    either ignored as it is for satp, or the fields of vsatp are
 *    treated as WARL in the normal way."
 *
 * We use a *reserved* MODE encoding (7) which is guaranteed unsupported
 * on all platforms, so the test never needs to skip.
 *
 * Two valid outcomes:
 *   (a) Write ignored (satp-like): vsatp unchanged from saved value.
 *   (b) WARL processed: MODE field becomes a legal value (0/8/9/10).
 * =================================================================== */
TEST_REGISTER(test_ts_vsatp_04_warl_unsupported_mode);
bool test_ts_vsatp_04_warl_unsupported_mode(void)
{
    TEST_BEGIN("TS-VSATP-04: vsatp reserved MODE -> ignored or WARL");

    uintptr_t saved = vsatp_read();

    /* MODE=7 is reserved (not Bare/Sv39/Sv48/Sv57), always unsupported. */
    const unsigned reserved_mode = 7;
    uintptr_t probe = MAKE_VSATP(reserved_mode, 0, 0);
    vsatp_write(probe);
    uintptr_t got = vsatp_read();

    /* Restore immediately. */
    vsatp_write(saved);

    unsigned got_mode = (unsigned)SATP_GET_MODE(got);

    /* Outcome (a): entire write ignored, vsatp == saved. */
    bool ignored = (got == saved);

    /* Outcome (b): WARL processed, MODE is a legal encoding. */
    bool legal_mode = (got_mode == SATP_MODE_BARE) ||
                      (got_mode == SATP_MODE_SV39) ||
                      (got_mode == SATP_MODE_SV48) ||
                      (got_mode == SATP_MODE_SV57);

    TEST_ASSERT("reserved MODE must NOT persist in vsatp",
                got_mode != reserved_mode);
    TEST_ASSERT("write ignored (satp-like) OR MODE is legal (WARL)",
                ignored || legal_mode);

    HYP_TEST_END();
}

/* ===================================================================
 * TS-VSATP-05: vsatp.PPN is writable
 * =================================================================== */
TEST_REGISTER(test_ts_vsatp_05_ppn_writeback);
bool test_ts_vsatp_05_ppn_writeback(void)
{
    TEST_BEGIN("TS-VSATP-05: vsatp.PPN writeback");
    REQUIRE_VSATP_MODE(SATP_MODE_SV39);

    uintptr_t saved = vsatp_read();
    /* Use a benign PPN; it will not be walked because we restore
     * vsatp before any access. */
    uintptr_t test_ppn = 0xABCDEUL;  /* 20 bits, well within 44-bit PPN */
    vsatp_write(MAKE_VSATP(SATP_MODE_SV39, 0, test_ppn));
    uintptr_t got = vsatp_read();
    /* PPN field: bits [43:0]. Extract by shift-then-mask. */
    uintptr_t got_ppn = got & ((1UL << 44) - 1);
    TEST_ASSERT_EQ("vsatp.PPN reads back", got_ppn, test_ppn);

    vsatp_write(saved);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-VSATP-06: vsatp.ASID obeys ASIDLEN
 *
 * The platform's effective ASIDLEN may be 0..16 bits. We write all-1s
 * to the ASID field and read back; only the supported low bits should
 * remain set. The test asserts that the read-back is a contiguous
 * low-bit mask (i.e. ASIDLEN is well-defined) without prescribing its
 * exact width.
 * =================================================================== */
TEST_REGISTER(test_ts_vsatp_06_asid_warl);
bool test_ts_vsatp_06_asid_warl(void)
{
    TEST_BEGIN("TS-VSATP-06: vsatp.ASID WARL contiguous low bits");
    REQUIRE_VSATP_MODE(SATP_MODE_SV39);

    uintptr_t saved = vsatp_read();
    /* Write all-ones into ASID (16 bits per spec). */
    uintptr_t all_asid = (1UL << 16) - 1;
    vsatp_write(MAKE_VSATP(SATP_MODE_SV39, all_asid, 0));
    uintptr_t got = vsatp_read();
    uintptr_t got_asid = (got >> 44) & ((1UL << 16) - 1);

    /* Check that got_asid is of the form (1 << n) - 1, i.e. a
     * contiguous run of 1s starting from bit 0. */
    bool contiguous = ((got_asid + 1) & got_asid) == 0;
    TEST_ASSERT("ASID readback is contiguous low-bit mask", contiguous);

    vsatp_write(saved);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-VSATP-07: hstatus.VTVM=1 -> VS-mode satp access traps as
 *              virtual-instruction exception (cause=22).
 *
 * Spec: hstatus.VTVM=1 causes VS-mode attempts to access satp
 * (or execute SFENCE.VMA / SINVAL.VMA) to raise a virtual-instruction
 * exception.
 * =================================================================== */
TEST_REGISTER(test_ts_vsatp_07_vtvm_traps_satp);
bool test_ts_vsatp_07_vtvm_traps_satp(void)
{
    TEST_BEGIN("TS-VSATP-07: VTVM=1 + VS satp access -> virt-inst (22)");
    REQUIRE_VSATP_MODE(SATP_MODE_SV39);

    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SATP_MODE_SV39, HGATP_MODE_BARE);

    /* Set hstatus.VTVM=1 (bit 20). */
    CSRS(CSR_HSTATUS, (uintptr_t)HSTATUS_VTVM);

    /* VS-mode reads satp -> should trap as virtual-instruction. */
    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, vs_read_satp, 0);
    bool fired = trap_was_triggered();
    uintptr_t cause = fired ? trap_get_cause() : 0;
    trap_expect_end();

    /* Restore hstatus.VTVM=0. */
    CSRC(CSR_HSTATUS, (uintptr_t)HSTATUS_VTVM);
    ts2_finish(&ctx);

    TEST_ASSERT("trap fired on VS-mode satp access with VTVM=1", fired);
    TEST_ASSERT_EQ("cause = virtual-instruction (22)",
                   cause, (uintptr_t)CAUSE_VIRTUAL_INSTRUCTION);
    HYP_TEST_END();
}
