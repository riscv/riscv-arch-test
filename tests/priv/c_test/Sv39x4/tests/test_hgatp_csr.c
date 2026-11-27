/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 1: hgatp CSR field validation (GHCSR-01..09)
 *
 * Spec anchors:
 *   norm:hgatp_sz_acc_op   - hgatp is HSXLEN-bit RW with MODE/VMID/PPN
 *   norm:hgatp_mode_warl   - unsupported MODE is NOT silently dropped
 *                            (unlike satp); follows WARL semantics
 *   norm:hgatp_ppn_op      - PPN[1:0] reads as 0 in Sv*x4 modes
 *   norm:hgatp_vmid        - VMIDLEN is impl-defined, max 14
 *   norm:hgatp_mode_bare   - MODE=Bare requires other fields to be zero
 *   norm:hgatp_tvm_illegal - HS-mode access to hgatp with mstatus.TVM=1
 *                            triggers illegal-instruction exception
 * =================================================================== */

/* GHCSR-01: MODE=Bare write/read */
TEST_REGISTER(test_ghcsr_01_mode_bare);
bool test_ghcsr_01_mode_bare(void) {
    TEST_BEGIN("GHCSR-01: hgatp MODE=Bare write/read");

    hgatp_write(MAKE_HGATP(HGATP_MODE_BARE, 0, 0));
    uintptr_t r = hgatp_read();
    TEST_ASSERT_EQ("hgatp Bare reads back as 0", r, 0UL);

    HYP_TEST_END();
}

/* GHCSR-02: MODE=SUITE_HGATP_MODE write/read (baseline mode) */
TEST_REGISTER(test_ghcsr_02_mode_baseline);
bool test_ghcsr_02_mode_baseline(void) {
#if SUITE_HGATP_MODE == HGATP_MODE_SV39X4
    TEST_BEGIN("GHCSR-02: hgatp MODE=Sv39x4 write/read");
#elif SUITE_HGATP_MODE == HGATP_MODE_SV48X4
    TEST_BEGIN("GHCSR-02: hgatp MODE=Sv48x4 write/read");
#elif SUITE_HGATP_MODE == HGATP_MODE_SV57X4
    TEST_BEGIN("GHCSR-02: hgatp MODE=Sv57x4 write/read");
#endif

    /* PPN low 2 bits get forced to zero by HW; pre-mask to keep
     * the comparison clean. */
    uintptr_t ppn = (PLATFORM_MEM_BASE >> PAGE_SHIFT) & ~0x3UL;
    hgatp_write(MAKE_HGATP(SUITE_HGATP_MODE, /*vmid=*/0, ppn));
    uintptr_t r = hgatp_read();
    TEST_ASSERT_EQ("MODE field == SUITE_HGATP_MODE",
                   HGATP_GET_MODE(r), (uintptr_t)SUITE_HGATP_MODE);
    TEST_ASSERT_EQ("PPN field preserved",
                   HGATP_GET_PPN(r), ppn);

    hgatp_set_bare();
    HYP_TEST_END();
}

/* GHCSR-03: MODE=fallback-1 write/read (WARL fallback acceptable) */
TEST_REGISTER(test_ghcsr_03_mode_fallback1);
bool test_ghcsr_03_mode_fallback1(void) {
#if SUITE_HGATP_MODE == HGATP_MODE_SV39X4
    /* Sv39x4 baseline: test Sv48x4 fallback */
    TEST_BEGIN("GHCSR-03: hgatp MODE=Sv48x4 write/read");
    uintptr_t ppn = (PLATFORM_MEM_BASE >> PAGE_SHIFT) & ~0x3UL;
    hgatp_write(MAKE_HGATP(HGATP_MODE_SV48X4, 0, ppn));
    uintptr_t mode = HGATP_GET_MODE(hgatp_read());
    TEST_ASSERT("MODE is Sv48x4 or Bare (WARL)",
                mode == HGATP_MODE_SV48X4 || mode == HGATP_MODE_BARE);
#elif SUITE_HGATP_MODE == HGATP_MODE_SV48X4
    /* Sv48x4 baseline: test Sv39x4 fallback */
    TEST_BEGIN("GHCSR-03: hgatp MODE=Sv39x4 write/read");
    uintptr_t ppn = (PLATFORM_MEM_BASE >> PAGE_SHIFT) & ~0x3UL;
    hgatp_write(MAKE_HGATP(HGATP_MODE_SV39X4, 0, ppn));
    uintptr_t mode = HGATP_GET_MODE(hgatp_read());
    TEST_ASSERT("MODE is Sv39x4 or Bare (WARL)",
                mode == HGATP_MODE_SV39X4 || mode == HGATP_MODE_BARE);
#elif SUITE_HGATP_MODE == HGATP_MODE_SV57X4
    /* Sv57x4 baseline: test Sv39x4 fallback */
    TEST_BEGIN("GHCSR-03: hgatp MODE=Sv39x4 write/read");
    uintptr_t ppn = (PLATFORM_MEM_BASE >> PAGE_SHIFT) & ~0x3UL;
    hgatp_write(MAKE_HGATP(HGATP_MODE_SV39X4, 0, ppn));
    uintptr_t mode = HGATP_GET_MODE(hgatp_read());
    TEST_ASSERT("MODE is Sv39x4 or Bare (WARL)",
                mode == HGATP_MODE_SV39X4 || mode == HGATP_MODE_BARE);
#endif

    hgatp_set_bare();
    HYP_TEST_END();
}

/* GHCSR-04: MODE=fallback-2 write/read (WARL fallback acceptable) */
TEST_REGISTER(test_ghcsr_04_mode_fallback2);
bool test_ghcsr_04_mode_fallback2(void) {
#if SUITE_HGATP_MODE == HGATP_MODE_SV39X4
    /* Sv39x4 baseline: test Sv57x4 fallback */
    TEST_BEGIN("GHCSR-04: hgatp MODE=Sv57x4 write/read");
    uintptr_t ppn = (PLATFORM_MEM_BASE >> PAGE_SHIFT) & ~0x3UL;
    hgatp_write(MAKE_HGATP(HGATP_MODE_SV57X4, 0, ppn));
    uintptr_t mode = HGATP_GET_MODE(hgatp_read());
    TEST_ASSERT("MODE is Sv57x4 or Bare (WARL)",
                mode == HGATP_MODE_SV57X4 || mode == HGATP_MODE_BARE);
#elif SUITE_HGATP_MODE == HGATP_MODE_SV48X4
    /* Sv48x4 baseline: test Sv57x4 fallback */
    TEST_BEGIN("GHCSR-04: hgatp MODE=Sv57x4 write/read");
    uintptr_t ppn = (PLATFORM_MEM_BASE >> PAGE_SHIFT) & ~0x3UL;
    hgatp_write(MAKE_HGATP(HGATP_MODE_SV57X4, 0, ppn));
    uintptr_t mode = HGATP_GET_MODE(hgatp_read());
    TEST_ASSERT("MODE is Sv57x4 or Bare (WARL)",
                mode == HGATP_MODE_SV57X4 || mode == HGATP_MODE_BARE);
#elif SUITE_HGATP_MODE == HGATP_MODE_SV57X4
    /* Sv57x4 baseline: test Sv48x4 fallback */
    TEST_BEGIN("GHCSR-04: hgatp MODE=Sv48x4 write/read");
    uintptr_t ppn = (PLATFORM_MEM_BASE >> PAGE_SHIFT) & ~0x3UL;
    hgatp_write(MAKE_HGATP(HGATP_MODE_SV48X4, 0, ppn));
    uintptr_t mode = HGATP_GET_MODE(hgatp_read());
    TEST_ASSERT("MODE is Sv48x4 or Bare (WARL)",
                mode == HGATP_MODE_SV48X4 || mode == HGATP_MODE_BARE);
#endif

    hgatp_set_bare();
    HYP_TEST_END();
}

/* GHCSR-05: unsupported MODE follows WARL — write does NOT silently
 * succeed as the reserved value (this is the key difference vs satp). */
TEST_REGISTER(test_ghcsr_05_mode_warl);
bool test_ghcsr_05_mode_warl(void) {
    TEST_BEGIN("GHCSR-05: hgatp unsupported MODE follows WARL");

    /* Establish a known-good baseline. */
    uintptr_t ppn = (PLATFORM_MEM_BASE >> PAGE_SHIFT) & ~0x3UL;
    hgatp_write(MAKE_HGATP(SUITE_HGATP_MODE, 0, ppn));
    uintptr_t baseline_mode = HGATP_GET_MODE(hgatp_read());

    /* Attempt to write reserved MODE=2. Use the raw writer so that
     * the framework's spec-WARL shim does not pre-mask the value. */
    hgatp_write_raw(MAKE_HGATP(/*reserved*/2, 0, ppn));
    uintptr_t mode = HGATP_GET_MODE(hgatp_read());
    TEST_ASSERT("MODE not silently accepted as reserved 2", mode != 2);
    TEST_ASSERT("MODE remains a legal value",
                mode == baseline_mode    ||
                mode == HGATP_MODE_BARE  ||
                mode == HGATP_MODE_SV39X4 ||
                mode == HGATP_MODE_SV48X4 ||
                mode == HGATP_MODE_SV57X4);

    hgatp_set_bare();
    HYP_TEST_END();
}

/* GHCSR-06: PPN[1:0] forced to zero in Sv*x4 modes */
TEST_REGISTER(test_ghcsr_06_ppn_low2_zero);
bool test_ghcsr_06_ppn_low2_zero(void) {
#if SUITE_HGATP_MODE == HGATP_MODE_SV39X4
    TEST_BEGIN("GHCSR-06: hgatp PPN[1:0] reads as zero in Sv39x4");
#elif SUITE_HGATP_MODE == HGATP_MODE_SV48X4
    TEST_BEGIN("GHCSR-06: hgatp PPN[1:0] reads as zero in Sv48x4");
#elif SUITE_HGATP_MODE == HGATP_MODE_SV57X4
    TEST_BEGIN("GHCSR-06: hgatp PPN[1:0] reads as zero in Sv57x4");
#endif

    uintptr_t test_ppn = ((PLATFORM_MEM_BASE >> PAGE_SHIFT) | 0x3UL)
                         & HGATP_PPN_MASK;
    hgatp_write(MAKE_HGATP(SUITE_HGATP_MODE, 0, test_ppn));
    uintptr_t ppn = HGATP_GET_PPN(hgatp_read());
    TEST_ASSERT_EQ("PPN[1:0] reads zero", ppn & 0x3UL, 0UL);

    hgatp_set_bare();
    HYP_TEST_END();
}

/* GHCSR-07: VMIDLEN probing and round-trip */
TEST_REGISTER(test_ghcsr_07_vmidlen);
bool test_ghcsr_07_vmidlen(void) {
    TEST_BEGIN("GHCSR-07: hgatp VMID probing");

    /* Write all-ones to VMID and read back; bits that read as 0 are
     * unimplemented (VMIDLEN < 14). */
    hgatp_write(MAKE_HGATP(SUITE_HGATP_MODE, /*vmid=*/0x3FFFU, /*ppn=*/0));
    uintptr_t vmid_field = (hgatp_read() >> HGATP64_VMID_SHIFT) & HGATP64_VMID_MASK;

    int vmidlen = 0;
    for (int i = 0; i < 14; i++) {
        if (vmid_field & (1UL << i))
            vmidlen = i + 1;
    }
    TEST_ASSERT("VMIDLEN <= 14", vmidlen <= 14);

    /* norm:hgatp_vmid_lsbs: the least-significant VMID bits are
     * implemented first, so the readback must be a contiguous mask
     * of vmidlen low bits. */
    uintptr_t expect_mask = (vmidlen == 0) ? 0UL
                          : ((1UL << vmidlen) - 1UL);
    TEST_ASSERT_EQ("VMID implemented bits are contiguous LSBs",
                   vmid_field, expect_mask);

    if (vmidlen > 0) {
        unsigned vmid = 0x5U & ((1U << vmidlen) - 1U);
        hgatp_write(MAKE_HGATP(SUITE_HGATP_MODE, vmid, 0));
        uintptr_t got = (hgatp_read() >> HGATP64_VMID_SHIFT) & HGATP64_VMID_MASK;
        TEST_ASSERT_EQ("VMID round-trip", got, (uintptr_t)vmid);
    }

    hgatp_set_bare();
    HYP_TEST_END();
}

/* GHCSR-08: mstatus.TVM=1 + HS-mode hgatp access -> illegal-instruction */
static uintptr_t _hs_csrr_hgatp(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    v = CSRR(CSR_HGATP);
    return v;
}

TEST_REGISTER(test_ghcsr_08_tvm);
bool test_ghcsr_08_tvm(void) {
    TEST_BEGIN("GHCSR-08: TVM=1 traps HS-mode hgatp access");

    /* Set mstatus.TVM = 1. TVM is a configuration bit (not an xret
     * return-path bit), so the adaptive accessor proxies it safely from
     * S(HS)-mode via T-SBI. */
    tsbi_csr_set(CSR_MSTATUS, MSTATUS_TVM);

    /* From HS-mode, csrr hgatp -> illegal-instruction. */
    trap_expect_begin();
    (void)run_in_priv(PRIV_S, _hs_csrr_hgatp, 0);
    TEST_ASSERT("trap triggered in HS-mode", trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause=illegal-instruction (2)",
                       trap_get_cause(),
                       (uintptr_t)CAUSE_ILLEGAL_INST);
    }
    trap_expect_end();

    /* Clear TVM. */
    tsbi_csr_clear(CSR_MSTATUS, MSTATUS_TVM);

    /* M-mode access still works. */
    EXPECT_NO_TRAP((void)hgatp_read());

    HYP_TEST_END();
}

/* GHCSR-09: MODE=Bare passthrough — GPA = SPA, no translation or
 * protection.  VS-mode memory access should succeed without any
 * G-stage page table being set up.
 *
 * Spec anchor:
 *   norm:hgatp_mode_bare - "When MODE=Bare, guest physical addresses
 *       are equal to supervisor physical addresses, and there is no
 *       further memory protection for a guest virtual machine beyond
 *       the physical memory protection scheme."
 *   norm:hgatp_mode_bare_trans - "When the address translation scheme
 *       selected by the MODE field of hgatp is Bare, guest physical
 *       addresses are equal to supervisor physical addresses without
 *       modification, and no memory protection applies in the trivial
 *       translation." (pass-through side; the no-protection side is
 *       covered by Group 14 GBARE-01..05) */
TEST_REGISTER(test_ghcsr_09_bare_passthrough);
bool test_ghcsr_09_bare_passthrough(void) {
    TEST_BEGIN("GHCSR-09: hgatp MODE=Bare passthrough (GPA=SPA)");

    gpt_pool_reset();
    two_stage_ctx_t ctx;
    /* vsatp=Bare, hgatp=Bare: no translation at either stage. */
    two_stage_init(&ctx, SATP_MODE_BARE, HGATP_MODE_BARE);

    /* Access a known-valid physical address from VS-mode.
     * With both stages Bare, GPA == SPA so the access should
     * succeed without any page table being walked. */
    uintptr_t target = (uintptr_t)test_data_area;
    *(volatile uint64_t *)target = 0;

    uintptr_t r = two_stage_run_in_vs(&ctx, test_vs_read_write, target);
    TEST_ASSERT_EQ("VS-mode r/w succeeds with hgatp=Bare (passthrough)",
                   r, 0UL);

    two_stage_cleanup(&ctx);
    hyp_reset_state();
    HYP_TEST_END();
}
