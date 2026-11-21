/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 1: Sub-extension existence verification (smoke tests)
 *
 * Spec anchor: SPEC/sha.adoc:4-14
 *
 * Sha = H + Ssstateen + Shcounterenw + Shvstvala + Shtvala +
 *        Shvstvecd + Shvsatpa + Shgatpa
 *
 * Each test does a minimal "capability exists" assertion for one
 * sub-extension. Shvstvala/Shtvala existence is deferred to Group 5
 * (requires trap environment).
 *
 * 8 tests: SHA-EXIST-01 ~ SHA-EXIST-08
 * =================================================================== */

/* ---- SHA-EXIST-01: H extension present ---- */

TEST_REGISTER(test_sha_exist_h);
bool test_sha_exist_h(void) {
    TEST_BEGIN("SHA-EXIST-01: H extension present (hstatus accessible)");

    uintptr_t val = hstatus_read();
    /* If we reach here without trap, hstatus is accessible */
    TEST_ASSERT("hstatus readable (H extension present)", 1);
    (void)val;

    HYP_TEST_END();
}

/* ---- SHA-EXIST-02: Ssstateen present (hstateen0) ---- */

TEST_REGISTER(test_sha_exist_ssstateen_hstateen0);
bool test_sha_exist_ssstateen_hstateen0(void) {
    TEST_BEGIN("SHA-EXIST-02: Ssstateen hstateen0 CSR accessible");

    /* Ensure mstateen0 bit63=1 so HS can access hstateen0 */
    mstateen_set_bit63(0, true);

    uintptr_t saved = hstateen_read(0);

    /* Write bit 63 (always writable per spec) */
    hstateen_set_bits(0, STATEEN_BIT63);
    uintptr_t readback = hstateen_read(0);
    TEST_ASSERT("hstateen0 bit 63 writable (norm:hstateen_bit_63_writable)",
                (readback & STATEEN_BIT63) != 0);

    hstateen_write(0, saved);
    HYP_TEST_END();
}

/* ---- SHA-EXIST-03: Ssstateen present (sstateen0) ---- */

TEST_REGISTER(test_sha_exist_ssstateen_sstateen0);
bool test_sha_exist_ssstateen_sstateen0(void) {
    TEST_BEGIN("SHA-EXIST-03: Ssstateen sstateen0 CSR accessible");

    /* Ensure hierarchy allows access: mstateen0.63=1, hstateen0.63=1 */
    mstateen_set_bit63(0, true);
    hstateen_set_bit63(0, true);

    uintptr_t val = sstateen_read(0);
    /* If we reach here, sstateen0 is accessible */
    TEST_ASSERT("sstateen0 readable (Ssstateen present)", 1);
    (void)val;

    HYP_TEST_END();
}

/* ---- SHA-EXIST-04: Shcounterenw present ---- */

TEST_REGISTER(test_sha_exist_shcounterenw);
bool test_sha_exist_shcounterenw(void) {
    TEST_BEGIN("SHA-EXIST-04: Shcounterenw (hcounteren.CY writable)");

    uintptr_t saved = hcounteren_read();

    /* Write CY bit (bit 0) = 1 */
    hcounteren_set(0x1);
    uintptr_t rb = hcounteren_read();
    TEST_ASSERT("hcounteren.CY writable", (rb & 0x1) != 0);

    hcounteren_write(saved);
    HYP_TEST_END();
}

/* ---- SHA-EXIST-05: Shvstvecd present ---- */

TEST_REGISTER(test_sha_exist_shvstvecd);
bool test_sha_exist_shvstvecd(void) {
    TEST_BEGIN("SHA-EXIST-05: Shvstvecd (vstvec.MODE can hold Direct)");

    uintptr_t saved = vstvec_read();

    /* Write MODE=0 (Direct) with a test base address */
    uintptr_t test_base = 0x80001000UL;
    vstvec_write(test_base & ~0x3UL);  /* MODE=0 */
    int mode = vstvec_get_mode();
    TEST_ASSERT("vstvec.MODE == Direct (0)", mode == 0);

    vstvec_write(saved);
    HYP_TEST_END();
}

/* ---- SHA-EXIST-06: Shvsatpa present ---- */

TEST_REGISTER(test_sha_exist_shvsatpa);
bool test_sha_exist_shvsatpa(void) {
    TEST_BEGIN("SHA-EXIST-06: Shvsatpa (vsatp supports satp modes)");

    /* Probe satp for Sv39 */
    bool satp_sv39 = satp_supports_mode(PLATFORM_SATP_MODE);
    if (!satp_sv39) {
        TEST_SKIP("satp does not support Sv39, cannot verify Shvsatpa");
    }

    /* Shvsatpa: vsatp must also support Sv39 */
    bool vsatp_sv39 = vsatp_supports_mode(PLATFORM_SATP_MODE);
    TEST_ASSERT("vsatp supports Sv39 (same as satp)", vsatp_sv39);

    HYP_TEST_END();
}

/* ---- SHA-EXIST-07: Shgatpa present (Bare) ---- */

TEST_REGISTER(test_sha_exist_shgatpa_bare);
bool test_sha_exist_shgatpa_bare(void) {
    TEST_BEGIN("SHA-EXIST-07: Shgatpa (hgatp Bare mode)");

    uintptr_t saved = hgatp_read();
    hgatp_set_bare();
    uintptr_t rb = hgatp_read();
    TEST_ASSERT("hgatp Bare: MODE==0 and value==0",
                rb == 0);

    hgatp_write(saved);
    HYP_TEST_END();
}

/* ---- SHA-EXIST-08: Shgatpa present (SvNNx4) ---- */

TEST_REGISTER(test_sha_exist_shgatpa_svnnx4);
bool test_sha_exist_shgatpa_svnnx4(void) {
    TEST_BEGIN("SHA-EXIST-08: Shgatpa (hgatp SvNNx4 per satp SvNN)");

    bool satp_sv39 = satp_supports_mode(PLATFORM_SATP_MODE);
    if (!satp_sv39) {
        TEST_SKIP("satp does not support Sv39");
    }

    bool hgatp_sv39x4 = hgatp_supports_mode(PLATFORM_HGATP_MODE);
    TEST_ASSERT("hgatp supports Sv39x4 (Shgatpa: satp Sv39 -> hgatp Sv39x4)",
                hgatp_sv39x4);

    HYP_TEST_END();
}
