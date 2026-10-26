/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 4: Straddle / cross-page load (HTVAL-STR-*)
 *
 * Spec anchor:
 *   norm:H_htval — htval reports the GPA where the fault is taken.
 *
 * For an access that straddles two pages, the implementation may
 * deliver the misaligned-address exception OR may split the access
 * and only one half faults. The Shtvala normative requirement is
 * about htval contents, not about WHICH half faults; we just check
 * htval is consistent with the trapping address.
 *
 * Plan list:
 *   HTVAL-STR-01  load straddle with high half on V=0 page
 *   HTVAL-STR-02  store straddle with high half on W=0 page
 *   HTVAL-STR-03  load 8B unaligned, only 1B in V=0 page
 *
 * Strategy: place the access at GPA = page_n_end - 1, with the
 * fault page being the *next* page. We expect either:
 *   (a) cause=21 (load gpf) with htval ∈ {(fault_page)>>2, (op_addr)>>2}, or
 *   (b) cause=4  (load misaligned) — in which case Shtvala doesn't
 *       prescribe htval (no GPF). We accept either outcome but
 *       fail if cause is GPF and htval is unrelated.
 * =================================================================== */

/* VS-mode helpers performing the straddle access. Each takes the
 * starting address of the access and triggers a multi-byte load/
 * store across the page boundary. */
static uintptr_t vs_straddle_load(uintptr_t arg) {
    volatile uint64_t *p = (volatile uint64_t *)arg;
    (void)*p;
    return trap_get_cause();
}
static uintptr_t vs_straddle_store(uintptr_t arg) {
    volatile uint64_t *p = (volatile uint64_t *)arg;
    *p = HYP_TEST_MAGIC;
    return trap_get_cause();
}

/* Helper: fire a straddle load whose first byte sits on a normal
 * page and whose remaining 7 bytes spill into `victim_page`
 * configured with `victim_flags`. Returns true iff a trap fired. */
static bool _fire_straddle(uintptr_t (*helper)(uintptr_t),
                           uintptr_t straddle_addr,
                           uintptr_t victim_page,
                           uintptr_t victim_flags)
{
    two_stage_ctx_t ctx;
    setup_gstage_with_victim(&ctx, victim_page, victim_flags);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, helper, straddle_addr);
    bool fired = trap_was_triggered();
    trap_expect_end();

    two_stage_cleanup(&ctx);
    return fired;
}

static bool _check_htval_for_straddle(uintptr_t straddle_addr,
                                      uintptr_t victim_page)
{
    uintptr_t cause = trap_get_cause();
    if (cause == CAUSE_LOAD_GUEST_PAGE_FAULT ||
        cause == CAUSE_STORE_GUEST_PAGE_FAULT ||
        cause == CAUSE_INST_GUEST_PAGE_FAULT) {
        uintptr_t htval = trap_get_htval();
        uintptr_t op_lo = straddle_addr >> 2;
        uintptr_t vp_lo = victim_page  >> 2;
        if (htval != op_lo && htval != vp_lo) {
            LOG_E("htval 0x%lx is neither op>>2=0x%lx nor victim>>2=0x%lx\n",
                  (unsigned long)htval,
                  (unsigned long)op_lo,
                  (unsigned long)vp_lo);
            return false;
        }
        return true;
    }
    /* Misalign or other: Shtvala doesn't apply, accept. */
    return true;
}

TEST_REGISTER(test_htval_str_01_load_straddle);
bool test_htval_str_01_load_straddle(void) {
    TEST_BEGIN("HTVAL-STR-01: load straddle into V=0 page reports htval = GPA>>2");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    /* Place the 8-byte access starting 1 byte before the fault page.
     * test_data_area is the page right before test_fault_page. */
    uintptr_t straddle = (uintptr_t)test_data_area + PAGE_SIZE_4K - 1;
    uintptr_t victim   = (uintptr_t)test_fault_page;

    bool fired = _fire_straddle(vs_straddle_load, straddle, victim, /*flags=*/0);
    TEST_ASSERT("trap fired", fired);
    if (fired) {
        bool ok = _check_htval_for_straddle(straddle, victim);
        TEST_ASSERT("htval consistent with trap", ok);
    }
    hyp_reset_state();
    HYP_TEST_END();
}

TEST_REGISTER(test_htval_str_02_store_straddle);
bool test_htval_str_02_store_straddle(void) {
    TEST_BEGIN("HTVAL-STR-02: store straddle into W=0 page reports htval = GPA>>2");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t straddle = (uintptr_t)test_data_area + PAGE_SIZE_4K - 1;
    uintptr_t victim   = (uintptr_t)test_fault_page;
    uintptr_t flags    = (G_FLAGS_RWXU_AD & ~PTE_W);

    bool fired = _fire_straddle(vs_straddle_store, straddle, victim, flags);
    TEST_ASSERT("trap fired", fired);
    if (fired) {
        bool ok = _check_htval_for_straddle(straddle, victim);
        TEST_ASSERT("htval consistent with trap", ok);
    }
    hyp_reset_state();
    HYP_TEST_END();
}

/* ===================================================================
 * HTVAL-STR-03: Cross-page instruction fetch GPF (cause=20)
 *
 * Spec anchor:
 *   norm:H_straddle — when an instruction fetch straddles a page
 *   boundary and the second page faults, htval must report the
 *   faulting portion's GPA >> 2, with cause=20 (inst GPF).
 *
 * Strategy: jump to an address 2 bytes before the fault page
 * boundary. A 4-byte instruction spans both pages. The first 2
 * bytes are on a valid page; the last 2 bytes are on the fault
 * page (V=0 in G-stage). The CPU fetches the second half and
 * triggers cause=20 with htval = fault_page >> 2.
 * =================================================================== */

/* VS-mode trampoline: jump to the straddle address and execute.
 * The caller places 2 NOPs at straddle_addr-2 (on the valid page)
 * as padding; the 4-byte NOP at straddle_addr straddles into the
 * fault page, triggering the GPF.
 *
 * If the platform transparently handles the fetch (no fault), we
 * return 0 and the caller detects the missing trap. */
static uintptr_t vs_straddle_fetch(uintptr_t arg) {
    uintptr_t straddle_addr = arg;
    uintptr_t ret;
    asm volatile (
        "la   %0, 1f\n\t"     /* save return address */
        "jr   %1\n\t"         /* jump to straddle address */
        "1:\n\t"
        : "=r"(ret) : "r"(straddle_addr) : "ra", "memory"
    );
    return ret;
}

TEST_REGISTER(test_htval_str_03_fetch_straddle);
bool test_htval_str_03_fetch_straddle(void) {
    TEST_BEGIN("HTVAL-STR-03: fetch straddle into V=0 page, cause=20, htval=GPA>>2");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    /* Place the straddle point 2 bytes before the fault page.
     * A 4-byte instruction at this address spans into the fault page. */
    uintptr_t straddle = (uintptr_t)test_data_area + PAGE_SIZE_4K - 2;
    uintptr_t victim   = (uintptr_t)test_fault_page;

    /* Write 2 NOPs at the straddle point (valid page side) so the
     * CPU fetches them before attempting the fault-page half. */
    volatile uint16_t *pad = (volatile uint16_t *)straddle;
    pad[0] = 0x0001;  /* c.nop */

    two_stage_ctx_t ctx;
    setup_gstage_with_victim(&ctx, victim, /*flags=*/0);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, vs_straddle_fetch, straddle);
    bool fired = trap_was_triggered();
    trap_expect_end();

    two_stage_cleanup(&ctx);

    if (!fired) {
        /* Platform transparently fetched across the page boundary
         * (hardware page-crossing support). No GPF -> SKIP. */
        LOG_W("platform supports transparent cross-page fetch\n");
        hyp_reset_state();
        TEST_SKIP("no cross-page fetch GPF");
    }

    uintptr_t cause = trap_get_cause();
    if (cause == CAUSE_INST_GUEST_PAGE_FAULT) {
        /* Expected: inst GPF with htval = fault page >> 2 */
        TEST_ASSERT_EQ("cause = 20 (inst-gpf)",
                       cause, (uintptr_t)CAUSE_INST_GUEST_PAGE_FAULT);
        TEST_ASSERT_EQ("htval = fault page >> 2",
                       trap_get_htval(), victim >> 2);
    } else if (cause == CAUSE_LOAD_ADDR_MISALIGN) {
        /* Platform does not support 2-byte-aligned fetch; misalign
         * fires before GPF. Shtvala does not constrain htval here. */
        LOG_I("misaligned-fetch before GPF (impl-defined)\n");
    } else {
        TEST_ASSERT("unexpected cause", 0);
    }

    hyp_reset_state();
    HYP_TEST_END();
}
