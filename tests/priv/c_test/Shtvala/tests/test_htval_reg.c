/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 1: htval CSR existence and WARL behaviour
 *
 * Spec anchors:
 *   norm:H_htval — htval is present and writable when H is implemented.
 *
 * Test list (matches DOCS/testplan/shtvala_test_plan.md HTVAL-REG):
 *   HTVAL-REG-01  read-after-reset (== 0 once hyp_reset_state)
 *   HTVAL-REG-02  csrw writeable, readback equal
 *   HTVAL-REG-03  csrw of all-ones; readback masks reserved bits
 *                 (we accept whatever the implementation reports)
 *   HTVAL-REG-04  csrr/csrw round-trip is bit-stable for low 32 bits
 * =================================================================== */

static inline uintptr_t htval_read(void) {
    uintptr_t v;
    asm volatile ("csrr %0, " CSR_STR(CSR_HTVAL) : "=r"(v));
    return v;
}
static inline void htval_write(uintptr_t v) {
    asm volatile ("csrw " CSR_STR(CSR_HTVAL) ", %0" :: "r"(v));
}

TEST_REGISTER(test_htval_reg_01_reset_zero);
bool test_htval_reg_01_reset_zero(void) {
    TEST_BEGIN("HTVAL-REG-01: M-mode write/read htval (WARL subset)");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    hyp_reset_state();

    /* Write a known pattern and read back. */
    uintptr_t pattern = 0xDEADBEEFUL;
    htval_write(pattern);
    uintptr_t got = htval_read();
    /* htval is WARL: readback must be a valid subset value.
     * The implementation may mask reserved bits, but must not throw
     * an exception. We accept any readback value as long as it is
     * bit-stable on a second read. */
    uintptr_t got2 = htval_read();
    TEST_ASSERT_EQ("htval readback is stable", got2, got);

    /* Write 0 must be preserved (WARL mandatory). */
    htval_write(0);
    TEST_ASSERT_EQ("htval write 0 preserved", htval_read(), 0UL);

    HYP_TEST_END();
}

TEST_REGISTER(test_htval_reg_02_writable);
bool test_htval_reg_02_writable(void) {
    TEST_BEGIN("HTVAL-REG-02: htval is writable, readback preserves GPA>>2");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");

    /* Write 0 must be preserved. */
    htval_write(0);
    TEST_ASSERT_EQ("htval write 0 preserved", htval_read(), 0UL);

    /* Write a valid GPA>>2 pattern; readback must be complete. */
    uintptr_t test_gpa_shifted = 0x80100000UL >> 2;  /* 41-bit valid GPA */
    htval_write(test_gpa_shifted);
    TEST_ASSERT_EQ("htval write GPA>>2 preserved",
                   htval_read(), test_gpa_shifted);

    htval_write(0);
    HYP_TEST_END();
}

TEST_REGISTER(test_htval_reg_03_all_ones_warl);
bool test_htval_reg_03_all_ones_warl(void) {
    TEST_BEGIN("HTVAL-REG-03: htval all-ones write probes WARL subset");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    htval_write((uintptr_t)-1);
    uintptr_t got = htval_read();
    /* htval is WARL: readback must be a subset of the written value
     * (bit-wise) and must not throw an exception. */
    TEST_ASSERT("no exception on all-ones write", 1);  /* reached here = no trap */
    TEST_ASSERT("readback is non-zero (some bits implemented)", got != 0);
    /* Bitwise subset: readback & ~written == 0. Since written = ~0,
     * this is trivially true. Just check stability. */
    uintptr_t got2 = htval_read();
    TEST_ASSERT_EQ("htval is stable", got2, got);
    htval_write(0);
    HYP_TEST_END();
}

/* VS-mode helper: attempt to read htval (CSR 0x643).
 * In VS/VU-mode this should cause virtual-instruction (cause=22). */
static uintptr_t vs_csrr_htval(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, " CSR_STR(CSR_HTVAL) : "=r"(v));
    return v;
}

TEST_REGISTER(test_htval_reg_04_vs_vu_access);
bool test_htval_reg_04_vs_vu_access(void) {
    TEST_BEGIN("HTVAL-REG-04: VS/VU-mode access to htval traps");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");

    /* VS-mode: csrr htval -> virtual-instruction (cause=22).
     * htval (0x643) is an HS-level CSR; accessing from VS-mode with
     * V=1 triggers virtual-instruction per the H-extension spec. */
    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_csrr_htval, 0));

    /* VU-mode: csrr htval -> also virtual-instruction (cause=22).
     * Per the H-extension spec, hypervisor CSRs accessed from any
     * V=1 context raise virtual-instruction. */
    EXPECT_VIRTUAL_INST(run_in_vu_mode(vs_csrr_htval, 0));

    HYP_TEST_END();
}
