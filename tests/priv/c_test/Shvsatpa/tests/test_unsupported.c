/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 5: Unsupported MODE write handling
 *
 * Spec anchors:
 *   norm:vsatp_mode_unsupported_v0 (hypervisor.adoc:1415-1416):
 *     V=0 write vsatp with unsupported MODE: either entire write
 *     ignored (same as satp), or fields handled per WARL.
 *   norm:vsatp_mode_unsupported_v1 (hypervisor.adoc:1417-1418):
 *     V=1 write satp (actually vsatp) with unsupported MODE: the
 *     write is FULLY IGNORED, vsatp is not modified.
 *   norm:satp_mode_op_unsupported  (supervisor.adoc:1052-1055):
 *     Writing unsupported MODE to satp: entire write has no effect.
 *
 * Test list (matches DOCS/testplan/shvsatpa_test_plan.md VSATP-UNSUP):
 *   VSATP-UNSUP-01  V=0 write vsatp reserved MODE=7
 *   VSATP-UNSUP-02  V=0 write vsatp reserved MODE=15
 *   VSATP-UNSUP-03  V=1 write satp unsupported MODE (fully ignored)
 * =================================================================== */

#define MODE_RESERVED_7   7UL
#define MODE_RESERVED_15  15UL

static uintptr_t vsmode_write_unsup_mode(uintptr_t arg) {
    asm volatile ("csrw satp, %0" :: "r"(arg) : "memory");
    return 0;
}

/* ---- VSATP-UNSUP-01 ---- */
TEST_REGISTER(test_shvsatpa_unsup_v0_mode7);
bool test_shvsatpa_unsup_v0_mode7(void) {
    TEST_BEGIN("VSATP-UNSUP-01: V=0 write vsatp reserved MODE=7");

    uintptr_t saved = vsatp_read();

    /* Set vsatp to Bare baseline */
    vsatp_write(MAKE_SATP(SATP_MODE_BARE, 0, 0));

    /* Write reserved MODE=7 */
    uintptr_t bad_val = (MODE_RESERVED_7 << SATP64_MODE_SHIFT) | 0x12345UL;
    vsatp_write(bad_val);

    uintptr_t mode = SATP_GET_MODE(vsatp_read());
    TEST_ASSERT_NEQ("vsatp.MODE != 7 (reserved value rejected)",
                    mode, MODE_RESERVED_7);

    vsatp_write(saved);
    HYP_TEST_END();
}

/* ---- VSATP-UNSUP-02 ---- */
TEST_REGISTER(test_shvsatpa_unsup_v0_mode15);
bool test_shvsatpa_unsup_v0_mode15(void) {
    TEST_BEGIN("VSATP-UNSUP-02: V=0 write vsatp reserved MODE=15");

    uintptr_t saved = vsatp_read();

    vsatp_write(MAKE_SATP(SATP_MODE_BARE, 0, 0));

    uintptr_t bad_val = (MODE_RESERVED_15 << SATP64_MODE_SHIFT) | 0x67890UL;
    vsatp_write(bad_val);

    uintptr_t mode = SATP_GET_MODE(vsatp_read());
    TEST_ASSERT_NEQ("vsatp.MODE != 15 (reserved value rejected)",
                    mode, MODE_RESERVED_15);

    vsatp_write(saved);
    HYP_TEST_END();
}

/* ---- VSATP-UNSUP-03 ---- */
TEST_REGISTER(test_shvsatpa_unsup_v1_ignored);
bool test_shvsatpa_unsup_v1_ignored(void) {
    TEST_BEGIN("VSATP-UNSUP-03: V=1 write unsupported MODE is fully ignored");

    uintptr_t saved = vsatp_read();

    /* Set vsatp to a known value (Bare + characteristic PPN) */
    uintptr_t known_val = MAKE_SATP(SATP_MODE_BARE, 0, 0x54321UL);
    vsatp_write(known_val);

    uintptr_t verify = vsatp_read();
    TEST_ASSERT_EQ("vsatp preset successful", verify, known_val);

    /* VS-mode writes unsupported MODE (7) with different PPN */
    uintptr_t bad_write = (MODE_RESERVED_7 << SATP64_MODE_SHIFT) | 0xABCDEUL;
    run_in_vs_mode(vsmode_write_unsup_mode, bad_write);

    /* M-mode reads vsatp: should be unchanged (V=1 write fully ignored) */
    uintptr_t readback = vsatp_read();
    TEST_ASSERT_EQ("vsatp unchanged after V=1 write with unsupported MODE",
                   readback, known_val);

    vsatp_write(saved);
    HYP_TEST_END();
}
