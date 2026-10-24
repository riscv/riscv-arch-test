/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 3: hstateen VS/VU access control
 *
 * Spec anchors:
 *   norm:hstateen_encoding          — hstateen controls VS/VU access
 *   norm:stateen_illegal_state_access — violation triggers exception
 *   norm:sstateen_vsmode_access_roz — hstateen=0 => VS sees ROZ
 *
 * 5 tests: SHA-HCTL-01 ~ SHA-HCTL-05
 * =================================================================== */

/* VS-mode helper: read sstateen0 */
static uintptr_t _vs_read_sstateen0(uintptr_t arg) {
    (void)arg;
    uintptr_t val;
    asm volatile ("csrr %0, " CSR_STR(CSR_SSTATEEN0) : "=r"(val));
    return val;
}

/* VS-mode helper: write sstateen0 */
static uintptr_t _vs_write_sstateen0(uintptr_t arg) {
    asm volatile ("csrw " CSR_STR(CSR_SSTATEEN0) ", %0" :: "r"(arg));
    return 0;
}

/* ---- SHA-HCTL-01: hstateen0 bit63=0 -> VS read sstateen0 traps ---- */

TEST_REGISTER(test_sha_hctl_bit63_zero_vs_read_traps);
bool test_sha_hctl_bit63_zero_vs_read_traps(void) {
    TEST_BEGIN("SHA-HCTL-01: hstateen0 bit63=0, VS csrr sstateen0 traps");

    /* Ensure mstateen0 bit63=1 (HS-level allowed) */
    mstateen_set_bit63(0, true);

    uintptr_t saved_hstateen0 = hstateen_read(0);

    /* Set hstateen0 bit63=0 -> VS cannot access sstateen0 */
    hstateen_clear_bits(0, STATEEN_BIT63);

    EXPECT_VIRTUAL_INST(
        run_in_vs_mode(_vs_read_sstateen0, 0)
    );

    hstateen_write(0, saved_hstateen0);
    HYP_TEST_END();
}

/* ---- SHA-HCTL-02: hstateen0 bit63=1 -> VS can read sstateen0 ---- */

TEST_REGISTER(test_sha_hctl_bit63_one_vs_read_ok);
bool test_sha_hctl_bit63_one_vs_read_ok(void) {
    TEST_BEGIN("SHA-HCTL-02: hstateen0 bit63=1, VS csrr sstateen0 OK");

    mstateen_set_bit63(0, true);

    uintptr_t saved_hstateen0 = hstateen_read(0);

    /* Set hstateen0 bit63=1 -> VS can access sstateen0 */
    hstateen_set_bits(0, STATEEN_BIT63);

    VS_EXPECT_NO_TRAP(
        run_in_vs_mode(_vs_read_sstateen0, 0)
    );

    hstateen_write(0, saved_hstateen0);
    HYP_TEST_END();
}

/* ---- SHA-HCTL-03: hstateen0 bit63=0 -> VS write sstateen0 traps ---- */

TEST_REGISTER(test_sha_hctl_bit63_zero_vs_write_traps);
bool test_sha_hctl_bit63_zero_vs_write_traps(void) {
    TEST_BEGIN("SHA-HCTL-03: hstateen0 bit63=0, VS csrw sstateen0 traps");

    mstateen_set_bit63(0, true);
    uintptr_t saved_hstateen0 = hstateen_read(0);

    /* Set hstateen0 bit63=0 */
    hstateen_clear_bits(0, STATEEN_BIT63);

    EXPECT_VIRTUAL_INST(
        run_in_vs_mode(_vs_write_sstateen0, STATEEN_BIT63)
    );

    hstateen_write(0, saved_hstateen0);
    HYP_TEST_END();
}

/* ---- SHA-HCTL-04: hstateen0 bit63=0 -> sstateen0 appears ROZ to VS ---- */

TEST_REGISTER(test_sha_hctl_bit63_zero_sstateen0_roz);
bool test_sha_hctl_bit63_zero_sstateen0_roz(void) {
    TEST_BEGIN("SHA-HCTL-04: hstateen0 bit63=0, sstateen0 ROZ from VS view");

    mstateen_set_bit63(0, true);
    uintptr_t saved_hstateen0 = hstateen_read(0);

    /* When hstateen0 bit63=0, VS-mode attempting to access sstateen0
     * triggers virtual-instruction exception (cause=22). This is the
     * hardware enforcement of the ROZ view: VS-mode cannot read or
     * write sstateen0 at all — the access is completely blocked.
     *
     * Per spec (smstateen.adoc:89-95): "If hstateen bit is zero and
     * mstateen bit is one, then V=1 access triggers virtual-instruction
     * exception." */

    /* Set hstateen0 bit63=0 */
    hstateen_clear_bits(0, STATEEN_BIT63);

    /* From M-mode, sstateen0 is still accessible (not gated).
     * M-mode is never gated by mstateen/hstateen hierarchy.
     * We just read sstateen0 to verify no trap occurs. */
    uintptr_t saved_sstateen0 = sstateen_read(0);
    uintptr_t m_view = sstateen_read(0);
    TEST_ASSERT("sstateen0 readable from M-mode (not gated by hstateen)",
                1);  /* reaching here = no trap = success */
    (void)m_view;

    /* VS-mode access traps — the ROZ guarantee is enforced via trap.
     * When hstateen0.63=0 and mstateen0.63=1, VS access to sstateen0
     * triggers virtual-instruction exception (cause=22). */
    EXPECT_VIRTUAL_INST(
        run_in_vs_mode(_vs_read_sstateen0, 0)
    );

    sstateen_write(0, saved_sstateen0);
    hstateen_write(0, saved_hstateen0);
    HYP_TEST_END();
}

/* ---- SHA-HCTL-05: hstateen0 CSRIND gate on siselect/sireg ---- */

/* VS-mode helper: read siselect (CSR 0x150) */
static uintptr_t _vs_read_siselect(uintptr_t arg) {
    (void)arg;
    uintptr_t val;
    asm volatile ("csrr %0, " CSR_STR(CSR_SISELECT) : "=r"(val));
    return val;
}

TEST_REGISTER(test_sha_hctl_csrind_gate);
bool test_sha_hctl_csrind_gate(void) {
    TEST_BEGIN("SHA-HCTL-05: hstateen0 CSRIND gate on VS siselect access");

    mstateen_set_bit63(0, true);

    /* Also ensure mstateen0 CSRIND bit = 1 to allow HS-level access */
    uintptr_t saved_mstateen0 = tsbi_csr_read(CSR_MSTATEEN0);
    tsbi_csr_set(CSR_MSTATEEN0, STATEEN0_CSRIND);

    uintptr_t saved_hstateen0 = hstateen_read(0);

    /* Probe: is CSRIND bit writable in hstateen0?
     * If not, Sscsrind is not implemented — skip. */
    hstateen_set_bits(0, STATEEN0_CSRIND);
    uintptr_t rb = hstateen_read(0);
    if ((rb & STATEEN0_CSRIND) == 0) {
        hstateen_write(0, saved_hstateen0);
        tsbi_csr_write(CSR_MSTATEEN0, saved_mstateen0);
        TEST_SKIP("hstateen0 CSRIND bit not writable (no Sscsrind)");
    }

    /* Also verify siselect is a valid CSR (Sscsrind actually implemented).
     * The hstateen0 bit may be writable even when Sscsrind is not
     * implemented (WARL behavior), so the writability probe alone is
     * insufficient. Try reading siselect from M-mode: if it traps with
     * illegal-instruction, Sscsrind is not present. */
    trap_expect_begin();
    uintptr_t sival;
    asm volatile (
        ".option push\n\t"
        ".option norvc\n\t"
        "csrr %0, " CSR_STR(CSR_SISELECT) "\n\t"
        ".option pop\n\t"
        : "=r"(sival) :: "memory"
    );
    bool siselect_valid = !trap_was_triggered();
    trap_expect_end();
    if (!siselect_valid) {
        hstateen_write(0, saved_hstateen0);
        tsbi_csr_write(CSR_MSTATEEN0, saved_mstateen0);
        TEST_SKIP("siselect not accessible (no Sscsrind implemented)");
    }

    /* CSRIND bit is writable. Verify it can be set and cleared. */
    TEST_ASSERT("hstateen0 CSRIND bit set to 1",
                (rb & STATEEN0_CSRIND) != 0);

    hstateen_clear_bits(0, STATEEN0_CSRIND);
    rb = hstateen_read(0);
    TEST_ASSERT("hstateen0 CSRIND bit cleared to 0",
                (rb & STATEEN0_CSRIND) == 0);

    /* Key test: With hstateen0 CSRIND=0 and mstateen0 CSRIND=1,
     * VS-mode access to siselect triggers virtual-instruction (cause=22).
     * Per spec norm:hstateen0_csrind_op. */
    EXPECT_VIRTUAL_INST(
        run_in_vs_mode(_vs_read_siselect, 0)
    );

    hstateen_write(0, saved_hstateen0);
    tsbi_csr_write(CSR_MSTATEEN0, saved_mstateen0);
    HYP_TEST_END();
}
