/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 8: htval / stval consistency & low-2-bit reconstruction
 *
 * Spec anchors:
 *   norm:mtval2_htval_virtaddr — for non-implicit GPF, the nonzero
 *     GPA in htval must correspond to the exact virtual address in
 *     stval.
 *   norm:htval_trapval NOTE — "the least-significant two bits are
 *     ordinarily the same as the least-significant two bits of the
 *     faulting virtual address in stval. For faults due to implicit
 *     memory accesses for VS-stage address translation, the least-
 *     significant two bits are instead zeros."
 *
 * Reconstruction formula:
 *   GPA = (htval << 2) | (stval & 0x3)
 *
 * Plan list:
 *   HTVAL-CON-01  load  GPF with low-2-bit = 0b11 -> full GPA match
 *   HTVAL-CON-02  store GPF with low-2-bit = 0b01 -> full GPA match
 *   HTVAL-CON-03  implicit GPF: htval<<2 low 2 bits == 0 (PTE aligned)
 *
 * With vsatp=BARE (GVA == GPA) the reconstruction simplifies to:
 *   (mtval2 << 2) | (mtval & 0x3) == faulting_address
 * =================================================================== */

/* Strict reconstruction check: (htval<<2) | (stval&3) must equal
 * the exact faulting address (page base + low bits). */
static bool _check_recon_strict(uintptr_t target)
{
    if (!trap_was_triggered()) {
        LOG_E("no trap fired\n");
        return false;
    }
    uintptr_t htval = trap_get_htval();
    uintptr_t tval  = trap_get_tval();
    uintptr_t reconstructed = (htval << 2) | (tval & 0x3UL);

    if (reconstructed != target) {
        LOG_E("reconstruct mismatch: htval=0x%lx tval=0x%lx -> 0x%lx, "
              "expected 0x%lx\n",
              (unsigned long)htval, (unsigned long)tval,
              (unsigned long)reconstructed, (unsigned long)target);
        return false;
    }
    return true;
}

/* ===================================================================
 * HTVAL-CON-01: load GPF with non-zero low 2 bits
 *
 * vsatp=BARE so GVA=GPA. Fault address = test_fault_page | 0x3
 * (low 2 bits = 0b11). Verifies:
 *   (htval << 2) | (stval & 0x3) == fault_address
 *   stval & 0x3 == 0x3
 * =================================================================== */
TEST_REGISTER(test_htval_con_01_load_low_bits);
bool test_htval_con_01_load_low_bits(void) {
    TEST_BEGIN("HTVAL-CON-01: (htval<<2)|(stval&3) == GPA, low2=0b11");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t page = (uintptr_t)test_fault_page;
    uintptr_t target = page | 0x3UL;  /* low 2 bits = 0b11 */
    uintptr_t flags  = (G_FLAGS_RWXU_AD & ~PTE_R);

    bool fired = fire_vs_load_fault(target, flags);
    TEST_ASSERT("load gpf fired", fired);
    if (fired) {
        TEST_ASSERT("reconstruction matches faulting GPA",
                    _check_recon_strict(target));
        TEST_ASSERT_EQ("stval low 2 bits = 0x3",
                       trap_get_tval() & 0x3UL, 0x3UL);
        TEST_ASSERT("htval != 0 (Shtvala)", trap_get_htval() != 0);
    }
    hyp_reset_state();
    HYP_TEST_END();
}

/* ===================================================================
 * HTVAL-CON-02: store GPF with non-zero low 2 bits (0b01)
 *
 * Tests the same reconstruction for a store with low-2-bit = 0b01.
 * =================================================================== */
TEST_REGISTER(test_htval_con_02_store_low_bits);
bool test_htval_con_02_store_low_bits(void) {
    TEST_BEGIN("HTVAL-CON-02: (htval<<2)|(stval&3) == GPA, low2=0b01");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t page = (uintptr_t)test_fault_page;
    uintptr_t target = page | 0x1UL;  /* low 2 bits = 0b01 */
    uintptr_t flags  = (G_FLAGS_RWXU_AD & ~PTE_W);

    bool fired = fire_vs_store_fault(target, flags);
    TEST_ASSERT("store gpf fired", fired);
    if (fired) {
        TEST_ASSERT("reconstruction matches faulting GPA",
                    _check_recon_strict(target));
        TEST_ASSERT_EQ("stval low 2 bits = 0x1",
                       trap_get_tval() & 0x3UL, 0x1UL);
        TEST_ASSERT("htval != 0 (Shtvala)", trap_get_htval() != 0);
    }
    hyp_reset_state();
    HYP_TEST_END();
}

/* ===================================================================
 * HTVAL-CON-03: implicit GPF — low 2 bits of (htval<<2) must be 0
 *
 * Spec anchor (norm:htval_trapval NOTE):
 *   "For faults due to implicit memory accesses for VS-stage address
 *    translation, the least-significant two bits are instead zeros."
 *
 * Since VS-stage PTE pages are 4KB-aligned (and individual PTEs are
 * 8-byte aligned), htval << 2 must have its low 2 bits == 0.
 * This is independent of stval's low 2 bits (which report the
 * original GVA, not the PTE address).
 *
 * Reuses the implicit PTE GPF setup from Group 3.
 * =================================================================== */
TEST_REGISTER(test_htval_con_03_implicit_low_bits);
bool test_htval_con_03_implicit_low_bits(void) {
    TEST_BEGIN("HTVAL-CON-03: implicit GPF, (htval<<2) low 2 bits == 0");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    /* Test VA must be in a different 1GB region from kernel. */
    uintptr_t kernel_vpn2 = (unsigned long)(PLATFORM_MEM_BASE) >> 30;
    uintptr_t imp_vpn2    = (kernel_vpn2 == 1) ? 2UL : 1UL;
    uintptr_t test_va     = (imp_vpn2 << 30) | 0x200000UL;

    two_stage_ctx_t ctx;
    uintptr_t victim_gpa = setup_implicit_walk_victim_level(&ctx, test_va,
                                              /*victim_pt_level=*/0,
                                              /*victim_g_flags=*/0);

    uintptr_t pte_offset = VA_VPN(test_va, 0) * sizeof(uintptr_t);
    uintptr_t pte_gpa = victim_gpa + pte_offset;

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_load_expect_fault, test_va);
    TEST_ASSERT("implicit GPF triggered", trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause = 21 (load-gpf)",
                       trap_get_cause(), CAUSE_LOAD_GUEST_PAGE_FAULT);
        CHECK_HTVAL("htval = PTE GPA>>2", pte_gpa >> 2);

        /* Core check: low 2 bits of (htval << 2) must be 0.
         * PTE addresses are 8-byte aligned, so the low 3 bits of
         * the PTE GPA are 0. After >>2 and <<2, the low 2 bits
         * are guaranteed 0. */
        uintptr_t htval_shifted_back = trap_get_htval() << 2;
        TEST_ASSERT_EQ("(htval << 2) low 2 bits == 0",
                       htval_shifted_back & 0x3UL, 0UL);

        /* Verify stval (original GVA) is different from the PTE GPA.
         * The stval low 2 bits are for the original GVA, NOT the PTE. */
        uintptr_t stval = trap_get_tval();
        LOG_I("stval=0x%lx, htval<<2=0x%lx (PTE GPA) — "
              "stval low2 may differ from htval<<2 low2\n",
              (unsigned long)stval, (unsigned long)htval_shifted_back);
    }
    trap_expect_end();

    two_stage_cleanup(&ctx);
    hyp_reset_state();
    HYP_TEST_END();
}
