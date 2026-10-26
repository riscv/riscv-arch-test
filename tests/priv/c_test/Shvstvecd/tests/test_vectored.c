/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_vectored.c - Group 5: Vectored mode probe (non-normative)
 *
 * Shvstvecd does NOT require Vectored mode (MODE=1) to be implemented.
 * This group merely probes whether it is supported and, if so, verifies
 * the expected interrupt offset behavior (BASE + 4*cause).
 *
 * Test coverage:
 *   VSTVEC-VEC-01: Vectored mode writability probe (always PASS)
 *   VSTVEC-VEC-02: Vectored interrupt jumps to BASE+4*cause (conditional)
 */

TEST_REGISTER(test_shvstvecd_vec_01_probe);
bool test_shvstvecd_vec_01_probe(void) {
    TEST_BEGIN("VSTVEC-VEC-01: probe vstvec Vectored mode support");

    VSTVEC_SAVE();

    /* Write MODE=1 (Vectored) + a reasonable BASE */
    uintptr_t base = 0x80001000UL;
    uintptr_t write_val = base | VSTVEC_MODE_VECTORED;
    vstvec_write(write_val);

    uintptr_t readback = vstvec_read();
    unsigned mode = readback & VSTVEC_MODE_MASK;

    if (mode == VSTVEC_MODE_VECTORED) {
        LOG_I("vstvec Vectored mode (MODE=1) is SUPPORTED\n");
    } else {
        LOG_I("vstvec Vectored mode (MODE=1) is NOT supported "
              "(readback MODE=%u)\n", mode);
    }

    /* This test always PASS — it's purely informational. */
    VSTVEC_RESTORE();
    TEST_END();
}

/* VSTVEC-VEC-02: Verify Vectored mode interrupt offset (BASE + 4*cause).
 *
 * Uses shvstvecd_vectored_table as the trap base:
 *   [0] BASE+0: nop (Direct landing, fall through)
 *   [1] BASE+4: j shvstvecd_vectored_handler (Vectored cause=1)
 *   [2] BASE+8: j shvstvecd_trap_entry
 *   ...
 *
 * In Direct mode: CPU lands at slot 0, falls through to slot 1,
 *   jumps to shvstvecd_trap_entry. g_shvstvecd_vec_marker stays 0.
 * In Vectored mode (cause=1 SSI): CPU lands at slot 1, jumps to
 *   shvstvecd_vectored_handler which sets g_shvstvecd_vec_marker=1,
 *   then jumps to shvstvecd_trap_entry.
 *
 * The test asserts g_shvstvecd_vec_marker == 1 for Vectored mode. */

/* VS-mode payload for Vectored VSSIP test. Sets stvec with MODE=1. */
static uintptr_t vsmode_enable_vssi_vectored(uintptr_t entry_with_mode) {
    /* entry_with_mode = BASE | 1 (Vectored) */
    asm volatile ("csrw stvec, %0" :: "r"(entry_with_mode));
    asm volatile ("csrw sscratch, %0"
                  :: "r"(shvstvecd_trap_scratch) : "memory");
    /* Enable SSIE + SIE to let VSSIP fire */
    asm volatile ("csrs sie, %0" :: "r"(BIT_SSI));
    asm volatile ("csrs sstatus, %0" :: "r"(SSTATUS_SIE_BIT));
    asm volatile ("nop");
    asm volatile ("csrc sstatus, %0" :: "r"(SSTATUS_SIE_BIT));
    asm volatile ("csrc sie, %0" :: "r"(BIT_SSI));
    return 0;
}

TEST_REGISTER(test_shvstvecd_vec_02_vectored_offset);
bool test_shvstvecd_vec_02_vectored_offset(void) {
    TEST_BEGIN("VSTVEC-VEC-02: Vectored VSSIP lands at BASE+4*cause");

    /* First check if Vectored is supported */
    if (!vstvec_supports_vectored()) {
        TEST_SKIP("vstvec Vectored mode not supported on this platform");
    }

    VSTVEC_SAVE();

    uintptr_t entry = (uintptr_t)&shvstvecd_vectored_table;

    /* Delegate VSSIP to VS-mode */
    hyp_delegate_to_vs(0, 1UL << 2);
    shvstvecd_reset_trap_record();

    /* Reset the Vectored marker */
    g_shvstvecd_vec_marker = 0;

    /* Inject VSSIP */
    hvip_set_vssi(true);

    /* Enter VS-mode with Vectored mode: BASE | 1 */
    uintptr_t entry_vectored = entry | VSTVEC_MODE_VECTORED;
    run_in_vs_mode(vsmode_enable_vssi_vectored, entry_vectored);

    /* In Vectored mode with VSSIP (cause=1), CPU jumps to BASE+4*1.
     * shvstvecd_vectored_handler runs and sets g_shvstvecd_vec_marker=1.
     *
     * In Direct mode (if MODE=1 was not accepted), CPU would land at
     * slot 0 (nop), fall through to slot 1 -> shvstvecd_trap_entry.
     * g_shvstvecd_vec_marker would stay 0. */
    TEST_ASSERT("Vectored mode: marker == 1 (vectored handler executed)",
                g_shvstvecd_vec_marker == 1);
    TEST_ASSERT("trap handler was invoked (cause != 0)",
                g_shvstvecd_trap_cause != 0);

    LOG_D("Vectored: marker=%lu, trap_cause=0x%lx\n",
          (unsigned long)g_shvstvecd_vec_marker,
          (unsigned long)g_shvstvecd_trap_cause);

    hvip_set_vssi(false);
    hyp_undelegate();
    VSTVEC_RESTORE();
    HYP_TEST_END();
}
