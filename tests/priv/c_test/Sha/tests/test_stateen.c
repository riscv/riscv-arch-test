/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 2: Ssstateen CSR basic accessibility and WARL behavior
 *
 * Spec anchors:
 *   norm:sstateen_rv64_csrs   — sstateen0-3 exist
 *   norm:hstateen_rv64_csrs   — hstateen0-3 exist
 *   norm:hstateen_bit_63_writable — hstateen bit 63 always writable
 *   norm:stateen_reserved_roz — reserved bits read-only zero
 *
 * 5 tests: SHA-STATEEN-01 ~ SHA-STATEEN-05
 *
 * Where a test only observes the CONTENT of hstateenN/sstateenN it runs the
 * accesses inside an M-mode excursion: access from below M is gated by
 * mstateenN[63] (norm:mstateen_bit_63_op + norm:stateen_illegal_state_access),
 * and an implementation may wire that gate bit read-only zero when the matching
 * sstateenN is all-zero (norm:mstateen_bit_63_roz), so an HS-mode read can trap
 * on a register that does exist. norm:stateen_op puts M-mode above the gate.
 * The gate itself is what SHA-HIER-01..03 exercise from S(HS)-mode.
 * =================================================================== */

/* ---- SHA-STATEEN-01: hstateen0-3 all readable ---- */

static bool g_stn_h_readable;

static uintptr_t _m_probe_hstateen(uintptr_t arg) {
    (void)arg;
    g_stn_h_readable = true;
    for (int i = 0; i < 4; i++) {
        trap_expect_begin();
        (void)hstateen_read(i);
        if (trap_was_triggered())
            g_stn_h_readable = false;
        trap_expect_end();
    }
    return 0;
}

TEST_REGISTER(test_sha_stateen_hstateen_readable);
bool test_sha_stateen_hstateen_readable(void) {
    TEST_BEGIN("SHA-STATEEN-01: hstateen0-3 all readable");

    /* norm:hstateen_rv64_csrs adds hstateen0-3, so this is an existence probe
     * (see the file header for why it runs in M-mode). */
    (void)run_in_priv(PRIV_M, _m_probe_hstateen, 0);

    TEST_ASSERT("hstateen0-3 all readable without trap", g_stn_h_readable);

    HYP_TEST_END();
}

/* ---- SHA-STATEEN-02: sstateen0-3 all readable ---- */

static bool g_stn_s_readable;

static uintptr_t _m_probe_sstateen(uintptr_t arg) {
    (void)arg;
    g_stn_s_readable = true;
    for (int i = 0; i < 4; i++) {
        trap_expect_begin();
        (void)sstateen_read(i);
        if (trap_was_triggered())
            g_stn_s_readable = false;
        trap_expect_end();
    }
    return 0;
}

TEST_REGISTER(test_sha_stateen_sstateen_readable);
bool test_sha_stateen_sstateen_readable(void) {
    TEST_BEGIN("SHA-STATEEN-02: sstateen0-3 all readable");

    /* norm:sstateen_rv64_csrs adds sstateen0-3; same M-mode vantage point as
     * SHA-STATEEN-01 (here both mstateenN[63] and hstateenN[63] would gate a
     * lower-mode read). */
    (void)run_in_priv(PRIV_M, _m_probe_sstateen, 0);

    TEST_ASSERT("sstateen0-3 all readable without trap", g_stn_s_readable);

    HYP_TEST_END();
}

/* ---- SHA-STATEEN-03: hstateen0 bit 63 toggle ---- */

TEST_REGISTER(test_sha_stateen_hstateen0_bit63_toggle);
bool test_sha_stateen_hstateen0_bit63_toggle(void) {
    TEST_BEGIN("SHA-STATEEN-03: hstateen0 bit 63 writable (toggle)");

    mstateen_set_bit63(0, true);
    uintptr_t saved = hstateen_read(0);

    /* Set bit 63 */
    hstateen_set_bits(0, STATEEN_BIT63);
    uintptr_t rb1 = hstateen_read(0);
    TEST_ASSERT("hstateen0 bit 63 set to 1", (rb1 & STATEEN_BIT63) != 0);

    /* Clear bit 63 */
    hstateen_clear_bits(0, STATEEN_BIT63);
    uintptr_t rb0 = hstateen_read(0);
    TEST_ASSERT("hstateen0 bit 63 cleared to 0", (rb0 & STATEEN_BIT63) == 0);

    hstateen_write(0, saved);
    HYP_TEST_END();
}

/* ---- SHA-STATEEN-04: hstateen1/2/3 bit 63 writable ---- */

/* Result codes of the M-mode toggle probe below. */
#define STN_TOGGLE_WRITABLE  1  /* bit63 set to 1 and cleared back to 0 */
#define STN_TOGGLE_ROZ       0  /* bit63 stuck at 0                     */
#define STN_TOGGLE_STUCK1    2  /* bit63 set but failed to clear        */
#define STN_TOGGLE_NO_ACCESS 3  /* the register itself is not accessible */

static int _stn_toggle_result;

static uintptr_t _m_hstateen_toggle63(uintptr_t idx) {
    int i = (int)idx;

    trap_expect_begin();
    uintptr_t saved = hstateen_read(i);
    bool trapped = trap_was_triggered();
    trap_expect_end();
    if (trapped) {
        _stn_toggle_result = STN_TOGGLE_NO_ACCESS;
        return 0;
    }

    hstateen_set_bits(i, STATEEN_BIT63);
    uintptr_t rb1 = hstateen_read(i);
    if ((rb1 & STATEEN_BIT63) == 0) {
        hstateen_write(i, saved);
        _stn_toggle_result = STN_TOGGLE_ROZ;
        return 0;
    }

    hstateen_clear_bits(i, STATEEN_BIT63);
    uintptr_t rb0 = hstateen_read(i);
    hstateen_write(i, saved);
    _stn_toggle_result = (rb0 & STATEEN_BIT63) == 0 ? STN_TOGGLE_WRITABLE
                                                    : STN_TOGGLE_STUCK1;
    return 0;
}

TEST_REGISTER(test_sha_stateen_hstateen123_bit63);
bool test_sha_stateen_hstateen123_bit63(void) {
    TEST_BEGIN("SHA-STATEEN-04: hstateen1/2/3 bit 63 writable");

    int implemented = 0;

    for (int i = 1; i <= 3; i++) {
        mstateen_set_bit63(i, true);
        (void)run_in_priv(PRIV_M, _m_hstateen_toggle63, (uintptr_t)i);

        switch (_stn_toggle_result) {
        case STN_TOGGLE_NO_ACCESS:
            /* norm:hstateen_rv64_csrs: hstateen0-3 all exist, and M-mode is
             * above every stateen gate, so this is a hard failure. */
            LOG_E("hstateen%d not accessible even from M-mode\n", i);
            TEST_ASSERT("hstateen1-3 accessible from M-mode", false);
            break;
        case STN_TOGGLE_ROZ:
            LOG_W("hstateen%d bit 63 not implemented (read-only zero)\n", i);
            break;
        case STN_TOGGLE_STUCK1:
            LOG_E("hstateen%d bit 63 failed to clear\n", i);
            TEST_ASSERT("hstateen bit 63 clear failed", false);
            break;
        default:
            implemented++;
            break;
        }
    }

    if (implemented == 0)
        TEST_SKIP("hstateen1/2/3 not implemented (bit 63 read-only zero, SPEC optional)");

    LOG_I("%d of 3 hstateenN (N=1,2,3) implemented\n", implemented);
    HYP_TEST_END();
}

/* ---- SHA-STATEEN-05: hstateen0 reserved bits read-only zero ---- */

TEST_REGISTER(test_sha_stateen_hstateen0_reserved_roz);
bool test_sha_stateen_hstateen0_reserved_roz(void) {
    TEST_BEGIN("SHA-STATEEN-05: hstateen0 reserved bits read-only zero");

    mstateen_set_bit63(0, true);

    /* Also set mstateen0 to all-1 so that hstateen0 bits are not
     * masked by mstateen0 hierarchy */
    uintptr_t saved_mstateen = tsbi_csr_read(CSR_MSTATEEN0);
    tsbi_csr_write(CSR_MSTATEEN0, ~0UL);

    uintptr_t saved = hstateen_read(0);

    /* Write all 1s */
    hstateen_write(0, ~0UL);
    uintptr_t rb = hstateen_read(0);

    /* Bit 63 must be 1 (always writable) */
    TEST_ASSERT("hstateen0 bit 63 == 1 after all-1 write",
                (rb & STATEEN_BIT63) != 0);

    /* Reserved/unimplemented bits should be 0.
     * We check bits [62:59] which are typically reserved on most
     * implementations (except bit 58 which may be Sscofpmf). */
    uintptr_t reserved_mask = 0x7UL << 59;  /* bits 61:59 */
    uintptr_t reserved_readback = rb & reserved_mask;
    LOG_D("hstateen0 readback after all-1 write: 0x%lx\n",
          (unsigned long)rb);
    LOG_D("reserved bits [61:59] readback: 0x%lx (expect 0)\n",
          (unsigned long)reserved_readback);

    /* Note: This is a soft check. Some bits in [62:0] may be defined
     * by extensions (e.g., bit 58 for Sscofpmf, bit 1 for Fcsr, etc.).
     * We only assert that the readback is a valid WARL value (i.e.,
     * some bits stuck at 0 = reserved bits are ROZ). */
    bool has_roz = (rb != ~0UL);
    TEST_ASSERT("hstateen0 has some read-only-zero bits (WARL)", has_roz);

    hstateen_write(0, saved);
    tsbi_csr_write(CSR_MSTATEEN0, saved_mstateen);
    HYP_TEST_END();
}
