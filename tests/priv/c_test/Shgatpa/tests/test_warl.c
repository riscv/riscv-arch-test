/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 4: hgatp MODE WARL behavior verification
 *
 * Spec anchors:
 *   norm:hgatp_mode_warl (hypervisor.adoc:1073-1076):
 *     Writing hgatp with an unsupported MODE value is NOT ignored
 *     (unlike satp). Fields are handled per WARL independently.
 *
 * Test list (matches DOCS/testplan/shgatpa_test_plan.md HGATP-WARL):
 *   HGATP-WARL-01  write reserved MODE=7
 *   HGATP-WARL-02  write reserved MODE=15
 *   HGATP-WARL-03  write reserved MODE=1
 *   HGATP-WARL-04  WARL behavior: PPN may be updated even with bad MODE
 *   HGATP-WARL-05  all MODE values 1-15 produce legal readback
 *
 * NOTE: hgatp_write_raw() is used to bypass the framework's software
 * WARL masking, so we can observe the actual hardware WARL behavior.
 * =================================================================== */

/* Legal MODE values for HSXLEN=64 */
static inline bool _is_legal_hgatp_mode(uintptr_t mode) {
    return mode == HGATP_MODE_BARE   ||
           mode == HGATP_MODE_SV39X4 ||
           mode == HGATP_MODE_SV48X4 ||
           mode == HGATP_MODE_SV57X4;
}

/* ---- HGATP-WARL-01 ---- */
TEST_REGISTER(test_shgatpa_warl_mode7);
bool test_shgatpa_warl_mode7(void) {
    TEST_BEGIN("HGATP-WARL-01: write reserved MODE=7, WARL forces legal value");

    uintptr_t saved = hgatp_read();

    hgatp_write_raw(0UL);   /* Bare baseline */
    hgatp_write_raw(MAKE_HGATP(7, 0, 0x2000));

    uintptr_t mode = HGATP_GET_MODE(hgatp_read());
    TEST_ASSERT_NEQ("hgatp.MODE != 7 (reserved value not held)",
                    mode, 7UL);
    TEST_ASSERT("hgatp.MODE is a legal value",
                _is_legal_hgatp_mode(mode));

    hgatp_write_raw(saved);
    HYP_TEST_END();
}

/* ---- HGATP-WARL-02 ---- */
TEST_REGISTER(test_shgatpa_warl_mode15);
bool test_shgatpa_warl_mode15(void) {
    TEST_BEGIN("HGATP-WARL-02: write reserved MODE=15, WARL forces legal value");

    uintptr_t saved = hgatp_read();

    hgatp_write_raw(0UL);
    hgatp_write_raw(MAKE_HGATP(15, 0, 0x3000));

    uintptr_t mode = HGATP_GET_MODE(hgatp_read());
    TEST_ASSERT_NEQ("hgatp.MODE != 15 (reserved value not held)",
                    mode, 15UL);
    TEST_ASSERT("hgatp.MODE is a legal value",
                _is_legal_hgatp_mode(mode));

    hgatp_write_raw(saved);
    HYP_TEST_END();
}

/* ---- HGATP-WARL-03 ---- */
TEST_REGISTER(test_shgatpa_warl_mode1);
bool test_shgatpa_warl_mode1(void) {
    TEST_BEGIN("HGATP-WARL-03: write reserved MODE=1, WARL forces legal value");

    uintptr_t saved = hgatp_read();

    hgatp_write_raw(0UL);
    hgatp_write_raw(MAKE_HGATP(1, 0, 0x4000));

    uintptr_t mode = HGATP_GET_MODE(hgatp_read());
    TEST_ASSERT_NEQ("hgatp.MODE != 1 (reserved value not held)",
                    mode, 1UL);
    TEST_ASSERT("hgatp.MODE is a legal value",
                _is_legal_hgatp_mode(mode));

    hgatp_write_raw(saved);
    HYP_TEST_END();
}

/* ---- HGATP-WARL-04 ---- */
TEST_REGISTER(test_shgatpa_warl_ppn_behavior);
bool test_shgatpa_warl_ppn_behavior(void) {
    TEST_BEGIN("HGATP-WARL-04: WARL behavior - PPN with unsupported MODE");

    uintptr_t saved = hgatp_read();

    /* Baseline: Bare with PPN=0 */
    hgatp_write_raw(0UL);
    TEST_ASSERT_EQ("baseline hgatp == 0", hgatp_read(), 0UL);

    /* Write unsupported MODE=7 + PPN=0x5000.
     * Per norm:hgatp_mode_warl, this is NOT fully ignored (unlike satp).
     * The MODE is WARL-forced to a legal value, but PPN may or may not
     * be updated -- implementation-defined. We observe and log. */
    hgatp_write_raw(MAKE_HGATP(7, 0, 0x5000));
    uintptr_t readback = hgatp_read();
    uintptr_t mode = HGATP_GET_MODE(readback);
    uintptr_t ppn  = HGATP_GET_PPN(readback);

    TEST_ASSERT("MODE forced to legal value", _is_legal_hgatp_mode(mode));

    /* Log PPN behavior for diagnostic purposes.
     * WARL allows either outcome: PPN updated or PPN stays 0. */
    if (ppn == 0x5000) {
        LOG_I("hgatp PPN was updated to 0x5000 despite unsupported MODE (WARL independent)\n");
    } else if (ppn == 0) {
        LOG_I("hgatp PPN stayed 0 after unsupported MODE write (WARL combined)\n");
    } else {
        LOG_I("hgatp PPN = 0x%lx after unsupported MODE write\n",
              (unsigned long)ppn);
    }

    hgatp_write_raw(saved);
    HYP_TEST_END();
}

/* ---- HGATP-WARL-05 ---- */
TEST_REGISTER(test_shgatpa_warl_all_modes_legal);
bool test_shgatpa_warl_all_modes_legal(void) {
    TEST_BEGIN("HGATP-WARL-05: all MODE values produce legal readback");

    uintptr_t saved = hgatp_read();
    bool all_legal = true;

    for (unsigned m = 0; m <= 15; m++) {
        hgatp_write_raw(0UL);  /* reset to Bare */
        hgatp_write_raw(MAKE_HGATP(m, 0, 0));
        uintptr_t readback_mode = HGATP_GET_MODE(hgatp_read());

        if (!_is_legal_hgatp_mode(readback_mode)) {
            LOG_I("MODE=%u: readback MODE=%lu (ILLEGAL)\n",
                  m, (unsigned long)readback_mode);
            all_legal = false;
        }
    }

    TEST_ASSERT("all hgatp MODE readbacks are legal (0, 8, 9, or 10)",
                all_legal);

    hgatp_write_raw(saved);
    HYP_TEST_END();
}
