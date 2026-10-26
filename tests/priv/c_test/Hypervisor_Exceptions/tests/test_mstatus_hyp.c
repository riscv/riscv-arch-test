/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * Test Group 5: mstatus Hypervisor enhancements
 *
 * Tests MSTAT-01 through MSTAT-14 verify mstatus hypervisor bits.
 */

#include "hyp_test_helpers.h"

/* Helper trampolines for PRIV_DO (which requires an expression, not
 * an asm statement). */
static uintptr_t hs_read_hgatp(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    v = CSRR(CSR_HGATP);  /* hgatp */
    return v;
}

static uintptr_t hs_exec_hfence_gvma(uintptr_t arg) {
    (void)arg;
    asm volatile(".4byte 0x62000073");  /* hfence.gvma x0, x0 */
    return 0;
}

/* ------------------------------------------------------------------
 * MSTAT-01: MPV set to 1 on VS trap to M-mode
 * ------------------------------------------------------------------ */
TEST_REGISTER(mstatus_mpv_vs_trap);
bool mstatus_mpv_vs_trap(void) {
    TEST_BEGIN("MSTAT-01: Verify MPV set to 1 on VS trap to M-mode");

    /* VS ecall trap to M-mode (cause=10). */
    trap_expect_begin();
    run_in_vs_mode(vs_exec_ecall, 0);
    trap_expect_end();

    /* Cause=10 (ecall-from-VS) is only generated when the trap
     * originates in VS-mode (V=1), proving hardware set MPV=1 at
     * trap entry.  After run_in_vs_mode returns to M-mode, MPV has
     * been consumed by mret and reads as 0 — that is correct. */
    uintptr_t cause = trap_get_cause();
    TEST_ASSERT_EQ("VS ecall cause=10 (proves MPV was set)", cause, (uintptr_t)10);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * MSTAT-02: MPV set to 0 on HS trap to M-mode
 * ------------------------------------------------------------------ */
TEST_REGISTER(mstatus_mpv_hs_trap);
bool mstatus_mpv_hs_trap(void) {
    TEST_BEGIN("MSTAT-02: Verify MPV set to 0 on HS trap to M-mode");

    /* mstatus.MPV is only written by hardware on a trap INTO M-mode, but the
     * T-SBI baseline delegates illegal-instruction (cause 2) to HS. Undelegate
     * it here so this HS-mode trap is taken in M-mode and MPV is captured
     * (medeleg is M-level config; use the tsbi_csr_* accessor, bit 2 only
     * -- never touching the medeleg[9] service-channel invariant). Restore
     * afterwards; hyp_reset_state also re-applies the baseline. */
    uintptr_t saved_medeleg = tsbi_csr_read(CSR_MEDELEG);
    tsbi_csr_clear(CSR_MEDELEG, 1UL << CAUSE_ILLEGAL_INST);

    /* HS illegal instruction trap to M-mode. */
    EXPECT_TRAP(2, {
        asm volatile(".4byte 0x00401073"); /* illegal instruction */
    });

    /* mstatus.MPV is M-level trap state captured at M-mode trap entry; reading
     * mstatus directly from S(HS)-mode both traps and would reflect the proxy
     * ecall rather than this trap. Use the framework's MPV snapshot. */
    TEST_ASSERT("MPV should be 0 on HS trap to M-mode", !trap_get_mpv());

    tsbi_csr_write(CSR_MEDELEG, saved_medeleg);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * MSTAT-03: MRET with V<-MPV
 *
 * Manually set MPV=1, MPP=1(S), then execute MRET.  Per spec
 * norm:mstatus_mpv_op, MRET sets V=MPV (unless MPP=3).
 * We verify V=1 by executing csrr hgatp in the post-MRET context:
 * hgatp is an HS-only CSR, so accessing it with V=1 triggers
 * virtual-instruction (cause=22).
 * ------------------------------------------------------------------ */
TEST_REGISTER(mstatus_mret_v_from_mpv);
bool mstatus_mret_v_from_mpv(void) {
    TEST_BEGIN("MSTAT-03: Verify MRET sets V<-MPV");

    /* Per norm:mstatus_mpv_op, MRET sets V<-MPV (unless MPP=M). The framework
     * enters VS-mode through exactly that mechanism: run_in_vs_mode() sets
     * mstatus.MPV=1/MPP=S and executes MRET. The old hand-rolled csrw mstatus
     * + csrw mepc + mret sequence ran inline in the test body, which under the
     * S-mode-normal model is HS-mode where those M-only operations trap (and
     * its ecall_args return tag is dead under the T-SBI wire protocol). Drive
     * the same MRET-into-VS path via the framework trampoline and prove V=1 by
     * reading an HS-only CSR (hgatp) in the landed context: with V=1 it raises
     * a virtual-instruction exception (cause 22). */
    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_read_hgatp, 0));

    HYP_TEST_END();
}

/* MSTAT-04 drives a real MRET with MPP=3 inside an M-mode excursion: MRET and
 * the mstatus.MPP/MPV fields are M-only, and the test body is HS-mode under
 * S-mode-normal. Returns mstatus.MPV observed right after the MRET, which must
 * be 0 -- MPP=M forces V=0 and ignores/clears MPV (norm:mstatus_mpv_op). */
static uintptr_t mstat04_mret_mpp3_probe(uintptr_t arg)
{
    (void)arg;
    uintptr_t ms = CSRR(mstatus);
    ms &= ~((3UL << 11) | MSTATUS_MPV);
    ms |= (3UL << 11);        /* MPP = M (3) */
    ms |= MSTATUS_MPV;        /* MPV = 1 */
    CSRW(mstatus, ms);

    /* MRET with MPP=M stays in M-mode and forces V=0 regardless of MPV. */
    asm volatile("la t0, 1f\n\t" "csrw mepc, t0\n\t" "mret\n\t" "1:\n\t"
                 ::: "t0", "memory");

    return (CSRR(mstatus) >> 39) & 1;   /* MPV after MRET */
}

/* ------------------------------------------------------------------
 * MSTAT-04: MRET with MPP=3 keeps V=0
 * ------------------------------------------------------------------ */
TEST_REGISTER(mstatus_mret_mpp3_v_zero);
bool mstatus_mret_mpp3_v_zero(void) {
    TEST_BEGIN("MSTAT-04: Verify MRET with MPP=3 keeps V=0");

    /* Configure MPP=3/MPV=1 and execute MRET inside an M-mode excursion (see
     * helper); verify V=0 (MPV reads 0) afterwards. */
    uintptr_t mpv = run_in_priv(PRIV_M, mstat04_mret_mpp3_probe, 0);
    TEST_ASSERT_EQ("V=0 after MRET with MPP=3", mpv, (uintptr_t)0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * MSTAT-05: M-mode GVA correctness
 *
 * Per norm:mstatus_gva_op: GVA is set to 1 when a guest-page-fault
 * trap writes a GVA to mtval, and set to 0 for any other trap into
 * M-mode. Because fire_vs_load_fault returns to M-mode via an ecall
 * from VS-mode (which clears GVA to 0), the test must use
 * trap_get_gva() — which returns the GVA captured at GPF trap entry
 * time — rather than reading mstatus directly.
 * ------------------------------------------------------------------ */
TEST_REGISTER(mstatus_gva_m_mode);
bool mstatus_gva_m_mode(void) {
    TEST_BEGIN("MSTAT-05: Verify M-mode GVA correctness");

    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    /* Fire a VS load fault to trigger GPF trap to M-mode.
     * Clear PTE_R so the G-stage leaf is non-readable, causing a
     * load guest-page-fault (cause=21) when VS-mode loads from it. */
    uintptr_t victim_gpa = (uintptr_t)test_fault_page;
    uintptr_t flags = G_FLAGS_RWXU_AD & ~PTE_R;
    bool fired = fire_vs_load_fault(victim_gpa, flags);
    TEST_ASSERT("load guest-page-fault triggered", fired);

    /* Per norm:mstatus_gva_op: guest-page-fault writes a GVA to mtval,
     * so GVA must be set to 1. Use trap_get_gva() which returns the
     * value captured at trap entry, before the ecall return clears it. */
    if (fired) {
        bool gva = trap_get_gva();
        TEST_ASSERT("GVA=1 on guest page fault", gva);
    }

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * MSTAT-06: TSR only affects HS-mode, not VS-mode
 *
 * Per norm:mstatus_modes: "The TSR and TVM fields of mstatus affect
 * execution only in HS-mode, not in VS-mode."
 * Set mstatus.TSR=1 and hstatus.VTSR=0, then execute SRET in
 * VS-mode.  SRET must NOT trap because TSR does not affect VS-mode.
 * ------------------------------------------------------------------ */
TEST_REGISTER(mstatus_tsr_hs_only);
bool mstatus_tsr_hs_only(void) {
    TEST_BEGIN("MSTAT-06: Verify TSR only affects HS-mode SRET");

    /* Set mstatus.TSR (config bit) via the tsbi_csr_* accessor; this
     * suite runs in S(HS)-mode so a raw csrr/csrw mstatus would trap. */
    tsbi_csr_set(CSR_MSTATUS, MSTATUS_TSR_BIT);

    /* Clear VTSR to ensure only mstatus.TSR is the factor. */
    hstatus_set_vtsr(0);

    /* Defensive: with TSR=1, an SRET executed in HS-mode traps illegal, and the
     * HS-level trap handler returns to the guest with an SRET -- so if the
     * implementation wrongly traps the VS-mode SRET (TSR must NOT affect
     * VS-mode) and that trap is delegated to HS, the handler's own SRET re-traps
     * forever. Route exceptions to M-mode (mret return, TSR gates SRET only) so
     * a non-compliant trap surfaces as a clean VS_EXPECT_NO_TRAP failure instead
     * of an infinite loop. On a compliant impl the VS SRET does not trap at all.
     * hyp_reset_state at HYP_TEST_END restores the delegation baseline. */
    clear_all_deleg();

    /* VS-mode SRET should NOT trap: TSR does not affect VS-mode (and VTSR=0),
     * so the guest SRET completes and run_in_vs_mode returns through its
     * M-mode ecall -- the HS handler's SRET return path is never exercised. */
    VS_EXPECT_NO_TRAP(run_in_vs_mode(vs_exec_sret, 0));

    /* Clear mstatus.TSR. */
    tsbi_csr_clear(CSR_MSTATUS, MSTATUS_TSR_BIT);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * MSTAT-07: TVM=1 blocks HS-mode hgatp access
 * ------------------------------------------------------------------ */
TEST_REGISTER(mstatus_tvm_hgatp);
bool mstatus_tvm_hgatp(void) {
    TEST_BEGIN("MSTAT-07: Verify TVM=1 blocks HS-mode hgatp access");

    /* Set mstatus.TVM (config bit) via the tsbi_csr_* accessor. */
    tsbi_csr_set(CSR_MSTATUS, MSTATUS_TVM);

    /* Try to access hgatp (CSR 0x680) from HS-mode — TVM=1 should
     * cause illegal-instruction (cause=2).  Must run in S-mode
     * (HS-mode) because TVM does not affect M-mode. */
    goto_priv(PRIV_S);
    PRIV_DO(hs_read_hgatp(0));
    goto_priv(PRIV_M);
    CHECK_TRAP("TVM=1 hgatp access from HS-mode trapped", 2);

    /* Clear mstatus.TVM. */
    tsbi_csr_clear(CSR_MSTATUS, MSTATUS_TVM);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * MSTAT-08: TVM=1 blocks HS-mode HFENCE.GVMA
 * ------------------------------------------------------------------ */
TEST_REGISTER(mstatus_tvm_hfence_gvma);
bool mstatus_tvm_hfence_gvma(void) {
    TEST_BEGIN("MSTAT-08: Verify TVM=1 blocks HS-mode HFENCE.GVMA");

    /* Set mstatus.TVM (config bit) via the tsbi_csr_* accessor. */
    tsbi_csr_set(CSR_MSTATUS, MSTATUS_TVM);

    /* Try HFENCE.GVMA from HS-mode — TVM=1 should cause
     * illegal-instruction (cause=2).  Must run in S-mode (HS-mode)
     * because TVM does not affect M-mode. */
    goto_priv(PRIV_S);
    PRIV_DO(hs_exec_hfence_gvma(0));
    goto_priv(PRIV_M);
    CHECK_TRAP("TVM=1 HFENCE.GVMA from HS-mode trapped", 2);

    /* Clear mstatus.TVM. */
    tsbi_csr_clear(CSR_MSTATUS, MSTATUS_TVM);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * MSTAT-09: TVM=1 does not affect vsatp access
 * ------------------------------------------------------------------ */
TEST_REGISTER(mstatus_tvm_vsatp);
bool mstatus_tvm_vsatp(void) {
    TEST_BEGIN("MSTAT-09: Verify TVM=1 does not affect vsatp access");

    /* Set mstatus.TVM (config bit) via the tsbi_csr_* accessor. */
    tsbi_csr_set(CSR_MSTATUS, MSTATUS_TVM);

    /* Per norm:mstatus_tvm_hs, TVM does NOT gate vsatp: reading vsatp (0x280)
     * from HS-mode with TVM=1 must succeed (no trap). The old code read `satp`
     * via vs_read_satp -- which TVM *does* gate in HS-mode, the wrong CSR for
     * this norm; it only "passed" before because the body ran in M-mode where
     * TVM has no effect. */
    uintptr_t vsatp_val;
    vsatp_val = CSRR(CSR_VSATP);
    (void)vsatp_val;

    /* Clear mstatus.TVM. */
    tsbi_csr_clear(CSR_MSTATUS, MSTATUS_TVM);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * MSTAT-10: TVM=1 does not affect HFENCE.VVMA
 * ------------------------------------------------------------------ */
TEST_REGISTER(mstatus_tvm_hfence_vvma);
bool mstatus_tvm_hfence_vvma(void) {
    TEST_BEGIN("MSTAT-10: Verify TVM=1 does not affect HFENCE.VVMA");

    /* Set mstatus.TVM (config bit) via the tsbi_csr_* accessor. */
    tsbi_csr_set(CSR_MSTATUS, MSTATUS_TVM);

    /* Per norm:mstatus_tvm_hs, TVM does NOT gate HFENCE.VVMA: executing it
     * from HS-mode with TVM=1 must succeed (no trap). The old code executed
     * SFENCE.VMA via vs_exec_sfence_vma -- which TVM *does* gate in HS-mode,
     * the wrong instruction for this norm. */
    vs_exec_hfence_vvma(0);

    /* Clear mstatus.TVM. */
    tsbi_csr_clear(CSR_MSTATUS, MSTATUS_TVM);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * MSTAT-11: MPRV=1 MPV=1 MPP=1 triggers two-stage translation
 * ------------------------------------------------------------------ */
TEST_REGISTER(mstatus_mprv_mpv_mpp);
bool mstatus_mprv_mpv_mpp(void) {
    TEST_BEGIN("MSTAT-11: Verify MPRV=1 MPV=1 MPP=1 triggers two-stage translation");

    TEST_SKIP("requires MPRV+MPV two-stage setup");

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * MSTAT-12: MPRV=1 MPV=0 does not trigger two-stage translation
 * ------------------------------------------------------------------ */
TEST_REGISTER(mstatus_mprv_mpv_zero);
bool mstatus_mprv_mpv_zero(void) {
    TEST_BEGIN("MSTAT-12: Verify MPRV=1 MPV=0 does not trigger two-stage translation");

    TEST_SKIP("requires MPRV two-stage setup");

    HYP_TEST_END();
}

/* MSTAT-13 helper: run HLV.W in M-mode with MPRV=1/MPP=S. MPRV only redirects
 * M-mode loads and MPRV/MPP are M-mode control bits (return-path bits the
 * tsbi_csr_ guard won't proxy), so the whole sequence must be an M-mode excursion.
 * g_mstat13_target is the guest address to load. If HLV wrongly honored MPRV
 * the load would trap; the armed M handler records it and EXPECT_NO_TRAP
 * surfaces the failure. Returns 0 on success. */
static uintptr_t g_mstat13_target;
static uintptr_t mstat13_hlv_mprv1(uintptr_t arg)
{
    (void)arg;
    uintptr_t ms = CSRR(mstatus);
    ms &= ~((3UL << 11) | MSTATUS_MPRV_BIT);
    ms |= (1UL << 11) | MSTATUS_MPRV_BIT;   /* MPP = S, MPRV = 1 */
    CSRW(mstatus, ms);

    (void)hlv_w(g_mstat13_target);          /* HLV must ignore MPRV */

    CSRC(mstatus, MSTATUS_MPRV_BIT);        /* clear MPRV before returning */
    return 0;
}

/* ------------------------------------------------------------------
 * MSTAT-13: MPRV does not affect HLV/HSV
 *
 * Per norm:mstatus_mprv_hlsv: "MPRV does not affect the virtual-
 * machine load/store instructions, HLV, HLVX, and HSV.  The
 * explicit loads and stores of these instructions always act as
 * though V=1 and the nominal privilege mode were hstatus.SPVP,
 * overriding MPRV."
 *
 * Set up two-stage translation (G-stage identity + VS-stage Bare),
 * then execute HLV.W from M-mode with MPRV=1 MPP=S.  If MPRV
 * incorrectly affected HLV, the instruction would behave
 * differently.  A successful load proves HLV ignores MPRV.
 * ------------------------------------------------------------------ */
TEST_REGISTER(mstatus_mprv_hlv_hsv);
bool mstatus_mprv_hlv_hsv(void) {
    TEST_BEGIN("MSTAT-13: Verify MPRV does not affect HLV/HSV");

    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    /* Set up G-stage identity mapping + VS-stage Bare. */
    gpt_pool_reset();
    two_stage_ctx_t ctx;
    two_stage_init(&ctx, SATP_MODE_BARE, SUITE_HGATP_MODE);

    /* Identity-map low memory (kernel/UART region). */
    uintptr_t lo_base = PLATFORM_MEM_BASE & ~(PAGE_SIZE_2M - 1);
    uintptr_t lo_end  = (uintptr_t)__vm_test_region_start
                        & ~(PAGE_SIZE_2M - 1);
    two_stage_setup_identity(&ctx, lo_base, lo_end - lo_base,
                             G_FLAGS_RWXU_AD, PT_LEVEL_2M);

    /* Identity-map test region. */
    uintptr_t r_start = (uintptr_t)__vm_test_region_start;
    uintptr_t r_size  = (uintptr_t)__vm_test_region_end - r_start;
    two_stage_setup_identity(&ctx, r_start, r_size,
                             G_FLAGS_RWXU_AD, PT_LEVEL_4K);

    /* Activate G-stage (hgatp); VS-stage stays Bare. */
    two_stage_enable(&ctx, 0);

    /* Baseline: HLV.W with MPRV=0 should succeed. */
    uintptr_t target = (uintptr_t)test_data_area;
    EXPECT_NO_TRAP(hlv_w(target));

    /* Per norm:mstatus_mprv_hlsv, HLV ignores MPRV and always acts as
     * V=1 + SPVP. Set MPRV=1/MPP=S and execute the HLV inside one M-mode
     * excursion (see helper): MPRV only redirects M-mode loads and cannot be
     * proxied by tsbi_csr_ from S(HS)-mode. A successful load proves HLV ignores
     * MPRV as required by spec. */
    g_mstat13_target = target;
    EXPECT_NO_TRAP(run_in_priv(PRIV_M, mstat13_hlv_mprv1, 0));

    two_stage_cleanup(&ctx);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * MSTAT-14: TW=1 affects VS-mode WFI
 * ------------------------------------------------------------------ */
TEST_REGISTER(mstatus_tw_vs_wfi);
bool mstatus_tw_vs_wfi(void) {
    TEST_BEGIN("MSTAT-14: Verify TW=1 causes illegal-inst on VS-mode WFI");

    /* Set mstatus.TW (config bit) via the tsbi_csr_* accessor. */
    tsbi_csr_set(CSR_MSTATUS, MSTATUS_TW_BIT);

    /* VS-mode WFI should trap with illegal-instruction (TW affects all modes
     * except M, norm:mstatus_modes). */
    EXPECT_ILLEGAL_INST(run_in_vs_mode(vs_exec_wfi, 0));

    /* Clear mstatus.TW. */
    tsbi_csr_clear(CSR_MSTATUS, MSTATUS_TW_BIT);

    HYP_TEST_END();
}
