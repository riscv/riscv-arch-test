/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_transparent.c - Group 4: V=1 transparency verification
 *
 * Per SPEC/hypervisor.adoc:1302-1308 (norm:vstvec_sz_acc_op):
 *   When V=1, vstvec substitutes for stvec. Instructions that normally
 *   read or modify stvec actually access vstvec instead.
 *
 * Test coverage:
 *   VSTVEC-TRANS-01: VS-mode writes stvec -> M-mode reads vstvec
 *   VSTVEC-TRANS-02: M-mode writes vstvec -> VS-mode reads stvec
 *   VSTVEC-TRANS-03: VS-mode writes stvec does NOT affect HS-mode stvec
 */

/* ===================================================================
 * VS-mode payload functions
 * =================================================================== */

/* VSTVEC-TRANS-01: VS-mode writes stvec (V=1: actually writes vstvec). */
static uintptr_t vsmode_write_stvec(uintptr_t arg) {
    /* V=1: csrw stvec actually writes vstvec */
    asm volatile ("csrw stvec, %0" :: "r"(arg));
    return 0;
}

/* VSTVEC-TRANS-02: VS-mode reads stvec (V=1: actually reads vstvec). */
static uintptr_t vsmode_read_stvec(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    /* V=1: csrr stvec actually reads vstvec */
    asm volatile ("csrr %0, stvec" : "=r"(v));
    return v;
}

/* VSTVEC-TRANS-03: VS-mode writes stvec, then returns the HS-stvec
 * value (which should remain unchanged). We write a known value to
 * vstvec (via stvec in V=1), then return. The test reads HS-mode
 * stvec afterward to confirm it wasn't affected. */
static uintptr_t vsmode_write_stvec_for_isolation(uintptr_t arg) {
    asm volatile ("csrw stvec, %0" :: "r"(arg));
    return 0;
}

/* ===================================================================
 * Test cases
 * =================================================================== */

TEST_REGISTER(test_shvstvecd_trans_01_vs_write_m_read);
bool test_shvstvecd_trans_01_vs_write_m_read(void) {
    TEST_BEGIN("VSTVEC-TRANS-01: VS writes stvec, M reads vstvec");

    VSTVEC_SAVE();

    uintptr_t test_val = 0xDEAD0000UL;  /* 4-byte aligned, MODE=0 */

    /* VS-mode writes stvec (V=1: actually vstvec) */
    run_in_vs_mode(vsmode_write_stvec, test_val);

    /* M-mode reads vstvec (CSR 0x205) */
    uintptr_t readback = vstvec_read();
    TEST_ASSERT("vstvec == value written by VS-mode via stvec",
                readback == test_val);

    VSTVEC_RESTORE();
    HYP_TEST_END();
}

TEST_REGISTER(test_shvstvecd_trans_02_m_write_vs_read);
bool test_shvstvecd_trans_02_m_write_vs_read(void) {
    TEST_BEGIN("VSTVEC-TRANS-02: M writes vstvec, VS reads stvec");

    VSTVEC_SAVE();

    uintptr_t test_val = 0xBEEF0004UL;  /* 4-byte aligned, MODE=0 */

    /* M-mode writes vstvec (CSR 0x205) */
    vstvec_write(test_val);

    /* VS-mode reads stvec (V=1: actually vstvec) */
    uintptr_t readback = run_in_vs_mode(vsmode_read_stvec, 0);
    TEST_ASSERT("VS-mode reads stvec == value written by M to vstvec",
                readback == test_val);

    VSTVEC_RESTORE();
    HYP_TEST_END();
}

TEST_REGISTER(test_shvstvecd_trans_03_vs_write_no_affect_hs);
bool test_shvstvecd_trans_03_vs_write_no_affect_hs(void) {
    TEST_BEGIN("VSTVEC-TRANS-03: VS writes stvec does NOT affect HS stvec");

    VSTVEC_SAVE();

    /* Read HS-mode stvec (CSR 0x105) before the test. */
    uintptr_t hs_stvec_before;
    asm volatile ("csrr %0, stvec" : "=r"(hs_stvec_before));

    /* VS-mode writes a distinct value to stvec (V=1: writes vstvec) */
    uintptr_t vs_write_val = 0x12340000UL;
    run_in_vs_mode(vsmode_write_stvec_for_isolation, vs_write_val);

    /* Read HS-mode stvec after VS-mode operation. It must be unchanged. */
    uintptr_t hs_stvec_after;
    asm volatile ("csrr %0, stvec" : "=r"(hs_stvec_after));
    TEST_ASSERT("HS-mode stvec unchanged after VS-mode write",
                hs_stvec_after == hs_stvec_before);

    /* Also confirm vstvec holds the VS-mode written value. */
    uintptr_t vstvec_val = vstvec_read();
    TEST_ASSERT("vstvec holds the VS-mode written value",
                vstvec_val == vs_write_val);

    VSTVEC_RESTORE();
    HYP_TEST_END();
}
