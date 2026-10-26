/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_mode.c - Group 1: vstvec.MODE writability
 *
 * Per SPEC/shvstvecd.adoc:4-6 (norm:shvstvecd_vstvec_mode_direct):
 *   vstvec.MODE must be capable of holding the value 0 (Direct).
 *
 * Shvstvecd does NOT require Vectored mode (MODE=1) to be implemented.
 * SPEC does NOT declare vstvec as WARL, so writing reserved MODE values
 * (2, 3) has undefined behavior -- we do not test those.
 *
 * All Group 1 tests run in M-mode and directly access vstvec (CSR 0x205).
 *
 * Test coverage:
 *   VSTVEC-MODE-01: MODE writable to 0 (Direct)
 *   VSTVEC-MODE-02: MODE 0 -> 1 -> 0 round-trip
 */

TEST_REGISTER(test_shvstvecd_mode_01_direct_writable);
bool test_shvstvecd_mode_01_direct_writable(void) {
    TEST_BEGIN("VSTVEC-MODE-01: vstvec.MODE writable to 0 (Direct)");

    VSTVEC_SAVE();

    /* Write BASE=0, MODE=0 */
    vstvec_write((uintptr_t)0);

    uintptr_t rb = vstvec_read();
    TEST_ASSERT("vstvec.MODE reads back as 0 (Direct)",
                (rb & VSTVEC_MODE_MASK) == VSTVEC_MODE_DIRECT);

    VSTVEC_RESTORE();
    TEST_END();
}

TEST_REGISTER(test_shvstvecd_mode_02_round_trip);
bool test_shvstvecd_mode_02_round_trip(void) {
    TEST_BEGIN("VSTVEC-MODE-02: vstvec.MODE 0 -> 1 -> 0 round-trip");

    VSTVEC_SAVE();

    /* Step 1: write MODE=0, expect readback == 0 */
    vstvec_write((uintptr_t)VSTVEC_MODE_DIRECT);
    uintptr_t rb1 = vstvec_read() & VSTVEC_MODE_MASK;
    TEST_ASSERT("after write MODE=0, readback == 0",
                rb1 == VSTVEC_MODE_DIRECT);

    /* Step 2: write MODE=1 (Vectored). Shvstvecd does NOT require
     * Vectored to be implemented. Either readback (0 or 1) is legal. */
    vstvec_write((uintptr_t)VSTVEC_MODE_VECTORED);
    uintptr_t rb2 = vstvec_read() & VSTVEC_MODE_MASK;
    TEST_ASSERT("after write MODE=1, readback in {0, 1}",
                rb2 == VSTVEC_MODE_DIRECT || rb2 == VSTVEC_MODE_VECTORED);
    if (rb2 == VSTVEC_MODE_VECTORED) {
        LOG_I("platform implements vstvec Vectored mode\n");
    } else {
        LOG_I("platform does NOT implement vstvec Vectored "
              "(MODE=1 -> 0)\n");
    }

    /* Step 3: write MODE=0 again, expect readback == 0 */
    vstvec_write((uintptr_t)VSTVEC_MODE_DIRECT);
    uintptr_t rb3 = vstvec_read() & VSTVEC_MODE_MASK;
    TEST_ASSERT("after write MODE=0 again, readback == 0",
                rb3 == VSTVEC_MODE_DIRECT);

    VSTVEC_RESTORE();
    TEST_END();
}
