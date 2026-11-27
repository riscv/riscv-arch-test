/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 4: mstateen -> hstateen -> sstateen hierarchy gating
 *
 * Spec anchors:
 *   norm:mstateen_bit_63_op         — mstateen0.63 controls hstateen0
 *   norm:hstateen_bit_63_op         — hstateen0.63 controls VS sstateen0
 *   norm:mstateen_lower_priv_roz    — mstateen=0 -> hstateen/sstateen ROZ
 *
 * 3 tests: SHA-HIER-01 ~ SHA-HIER-03
 * =================================================================== */

static inline uintptr_t _read_hstateen0(void) {
    uintptr_t v;
    asm volatile ("csrr %0, " CSR_STR(CSR_HSTATEEN0) : "=r"(v));
    return v;
}

/* M-mode excursion payload: read hstateen0. norm:stateen_op puts M-mode above
 * the access gate that mstateen0[63]=0 imposes on HS-mode, so this read never
 * traps and still shows the read-only-zero appearance mandated by
 * norm:mstateen_lower_priv_roz. */
static uintptr_t _m_read_hstateen0(uintptr_t arg) {
    (void)arg;
    return hstateen_read(0);
}

/* ---- SHA-HIER-01: mstateen0 bit63=1 -> hstateen0 bit63 writable ---- */

TEST_REGISTER(test_sha_hier_mstateen_enables_hstateen);
bool test_sha_hier_mstateen_enables_hstateen(void) {
    TEST_BEGIN("SHA-HIER-01: mstateen0 bit63=1 enables hstateen0 bit63 write");

    uintptr_t saved_mstateen0 = tsbi_csr_read(CSR_MSTATEEN0);
    uintptr_t saved_hstateen0 = hstateen_read(0);

    /* Set mstateen0 bit63=1 (allow HS access to hstateen0) */
    mstateen_set_bit63(0, true);

    /* Write hstateen0 bit63=1 */
    hstateen_set_bits(0, STATEEN_BIT63);
    uintptr_t rb = hstateen_read(0);
    TEST_ASSERT("hstateen0 bit63 == 1 when mstateen0 bit63 == 1",
                (rb & STATEEN_BIT63) != 0);

    /* Write hstateen0 bit63=0 */
    hstateen_clear_bits(0, STATEEN_BIT63);
    rb = hstateen_read(0);
    TEST_ASSERT("hstateen0 bit63 == 0 after clear",
                (rb & STATEEN_BIT63) == 0);

    hstateen_write(0, saved_hstateen0);
    tsbi_csr_write(CSR_MSTATEEN0, saved_mstateen0);
    HYP_TEST_END();
}

/* ---- SHA-HIER-02: mstateen0 bit63=0 -> hstateen0 bit63 reads zero ---- */

TEST_REGISTER(test_sha_hier_mstateen_zero_hstateen_roz);
bool test_sha_hier_mstateen_zero_hstateen_roz(void) {
    TEST_BEGIN("SHA-HIER-02: mstateen0 bit63=0 -> hstateen0 bit63 ROZ");

    uintptr_t saved_mstateen0 = tsbi_csr_read(CSR_MSTATEEN0);
    uintptr_t saved_hstateen0 = hstateen_read(0);

    /* First: set mstateen0 bit63=1 and write hstateen0 bit63=1 */
    mstateen_set_bit63(0, true);
    hstateen_set_bits(0, STATEEN_BIT63);

    uintptr_t rb = hstateen_read(0);
    TEST_ASSERT("hstateen0 bit63 set to 1 (baseline)", (rb & STATEEN_BIT63) != 0);

    /* Now clear mstateen0 bit63. Two spec rules then apply at once:
     *   norm:mstateen_lower_priv_roz - a zero mstateen bit makes the same bit
     *     appear read-only zero in the matching hstateen/sstateen CSR, which
     *     is a property of the value read, visible from M-mode too;
     *   norm:mstateen_bit_63_op + norm:stateen_illegal_state_access - bit 63
     *     also gates HS-mode's access to hstateen0 outright (illegal
     *     instruction, asserted by SHA-HIER-03).
     * So the read-only-zero appearance has to be observed from M-mode: under
     * the T-SBI S-mode-normal boot the suite body runs in S(HS)-mode, where
     * the same read traps instead of returning a value. */
    mstateen_set_bit63(0, false);

    rb = run_in_priv(PRIV_M, _m_read_hstateen0, 0);
    LOG_D("hstateen0 readback from M-mode with mstateen0.63=0: 0x%lx\n",
          (unsigned long)rb);
    TEST_ASSERT("hstateen0 bit63 appears read-only zero with mstateen0.63=0",
                (rb & STATEEN_BIT63) == 0);

    tsbi_csr_write(CSR_MSTATEEN0, saved_mstateen0);
    hstateen_write(0, saved_hstateen0);
    HYP_TEST_END();
}

/* ---- SHA-HIER-03: mstateen0 bit63=0 -> HS access hstateen0 traps ---- */

TEST_REGISTER(test_sha_hier_mstateen_zero_hs_traps);
bool test_sha_hier_mstateen_zero_hs_traps(void) {
    TEST_BEGIN("SHA-HIER-03: mstateen0 bit63=0 -> HS access hstateen0 traps");

    uintptr_t saved_mstateen0 = tsbi_csr_read(CSR_MSTATEEN0);

    /* Clear mstateen0 bit63 -> HS cannot access hstateen0 */
    mstateen_set_bit63(0, false);

    /* Attempt to read hstateen0 from the mode the gate applies to. The suite
     * body already runs in S(HS)-mode under the T-SBI S-mode-normal boot, so
     * no privilege scaffolding is needed here (goto_priv(PRIV_S) would be a
     * no-op and goto_priv(PRIV_M) would leave the rest of the test in M). */
    PRIV_DO_TRAP(_read_hstateen0());
    CHECK_TRAP("HS access hstateen0 with mstateen0.63=0", CAUSE_ILLEGAL_INST);

    tsbi_csr_write(CSR_MSTATEEN0, saved_mstateen0);
    HYP_TEST_END();
}
