/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_base.c - Group 2: vstvec.BASE holding capacity under MODE=Direct
 *
 * Per SPEC/shvstvecd.adoc:8-10 (norm:shvstvecd_vstvec_base_aligned_address):
 *   When vstvec.MODE=Direct, vstvec.BASE must be capable of holding any
 *   valid four-byte-aligned address.
 *
 * All Group 2 tests run in M-mode; we never take a trap with these BASE
 * values, so writing arbitrary addresses is safe.
 *
 * Test coverage:
 *   VSTVEC-BASE-01: BASE = 0x0
 *   VSTVEC-BASE-02: BASE = PLATFORM_MEM_BASE
 *   VSTVEC-BASE-03: BASE = 0x40000004 (cross 1 GiB boundary)
 *   VSTVEC-BASE-04: BASE = 0x8000000000 (bit 39, high-bit probe)
 *   VSTVEC-BASE-06: MODE=0 fixed, sweep BASE values
 *   VSTVEC-BASE-07: high-bit scan k in {12..38}
 *   VSTVEC-BASE-08: BASE = max legal address (0x7FFFFFFFFFFFFFFC)
 */

TEST_REGISTER(test_shvstvecd_base_01_zero);
bool test_shvstvecd_base_01_zero(void) {
    TEST_BEGIN("VSTVEC-BASE-01: BASE = 0x0");

    VSTVEC_SAVE();

    vstvec_write((uintptr_t)0x0);
    uintptr_t rb = vstvec_read();
    TEST_ASSERT("readback == 0x0", rb == 0x0UL);

    VSTVEC_RESTORE();
    TEST_END();
}

TEST_REGISTER(test_shvstvecd_base_02_platform_mem_base);
bool test_shvstvecd_base_02_platform_mem_base(void) {
    TEST_BEGIN("VSTVEC-BASE-02: BASE = PLATFORM_MEM_BASE");

    VSTVEC_SAVE();

    uintptr_t target = (uintptr_t)PLATFORM_MEM_BASE;
    TEST_ASSERT("PLATFORM_MEM_BASE is 4-byte aligned",
                (target & VSTVEC_MODE_MASK) == 0);

    vstvec_write(target);
    uintptr_t rb = vstvec_read();
    TEST_ASSERT("BASE field == PLATFORM_MEM_BASE",
                (rb & VSTVEC_BASE_MASK) == target);
    TEST_ASSERT("MODE field == 0 (Direct)",
                (rb & VSTVEC_MODE_MASK) == VSTVEC_MODE_DIRECT);

    VSTVEC_RESTORE();
    TEST_END();
}

TEST_REGISTER(test_shvstvecd_base_03_cross_1g);
bool test_shvstvecd_base_03_cross_1g(void) {
    TEST_BEGIN("VSTVEC-BASE-03: BASE = 0x40000004 (cross 1 GiB boundary)");

    VSTVEC_SAVE();

    uintptr_t target = 0x40000004UL;        /* 1 GiB + 4, 4-byte aligned */
    vstvec_write(target);
    uintptr_t rb = vstvec_read();
    TEST_ASSERT("readback == 0x40000004 (BASE preserved, MODE=0)",
                rb == target);

    VSTVEC_RESTORE();
    TEST_END();
}

TEST_REGISTER(test_shvstvecd_base_04_high_bit_39);
bool test_shvstvecd_base_04_high_bit_39(void) {
    TEST_BEGIN("VSTVEC-BASE-04: BASE = 0x8000000000 (bit 39, Shvstvecd probe)");

    VSTVEC_SAVE();

    /* Hard probe: a Shvstvecd-compliant impl must hold any valid
     * 4-byte aligned address. If BASE WARL-truncates high bits,
     * this assertion fails -- indicating Shvstvecd not truly enabled. */
    uintptr_t target = 1UL << 39;           /* 0x8000000000 */
    vstvec_write(target);
    uintptr_t rb = vstvec_read();
    TEST_ASSERT("readback == 0x8000000000 "
                "(high bit preserved -> Shvstvecd active)",
                rb == target);

    VSTVEC_RESTORE();
    TEST_END();
}

TEST_REGISTER(test_shvstvecd_base_06_independent_of_mode);
bool test_shvstvecd_base_06_independent_of_mode(void) {
    TEST_BEGIN("VSTVEC-BASE-06: BASE rewrites do not disturb MODE=Direct");

    VSTVEC_SAVE();

    /* Pin MODE=Direct and rewrite BASE several times. */
    static const uintptr_t bases[] = {
        0x1000UL, 0x2000UL, 0x4000UL, 0x8000UL,
    };
    const unsigned n = sizeof(bases) / sizeof(bases[0]);

    for (unsigned i = 0; i < n; i++) {
        uintptr_t target = bases[i] | VSTVEC_MODE_DIRECT;
        vstvec_write(target);
        uintptr_t rb = vstvec_read();
        TEST_ASSERT("BASE preserved across rewrite",
                    (rb & VSTVEC_BASE_MASK) == bases[i]);
        TEST_ASSERT("MODE remains Direct (=0)",
                    (rb & VSTVEC_MODE_MASK) == VSTVEC_MODE_DIRECT);
    }

    VSTVEC_RESTORE();
    TEST_END();
}

TEST_REGISTER(test_shvstvecd_base_07_high_bit_scan);
bool test_shvstvecd_base_07_high_bit_scan(void) {
    TEST_BEGIN("VSTVEC-BASE-07: high-bit scan k in {12..38}");

    VSTVEC_SAVE();

    /* Scan k from 12 (4 KiB) up to 38 (near Sv39 VA limit).
     * Each 1<<k is already 4-byte aligned for k>=2. */
    static const int ks[] = { 12, 16, 20, 24, 28, 32, 36, 38 };
    const unsigned n = sizeof(ks) / sizeof(ks[0]);

    for (unsigned i = 0; i < n; i++) {
        int k = ks[i];
        uintptr_t target = 1UL << k;
        vstvec_write(target);
        uintptr_t rb = vstvec_read();
        if (rb != target) {
            LOG_D("k=%d wrote 0x%lx readback 0x%lx\n",
                  k, (unsigned long)target, (unsigned long)rb);
        }
        TEST_ASSERT("readback == 1<<k (Shvstvecd holds any 4-aligned BASE)",
                    rb == target);
    }

    VSTVEC_RESTORE();
    TEST_END();
}

TEST_REGISTER(test_shvstvecd_base_08_max_address);
bool test_shvstvecd_base_08_max_address(void) {
    TEST_BEGIN("VSTVEC-BASE-08: BASE = max legal (0x7FFFFFFFFFFFFFFC)");

    VSTVEC_SAVE();

    /* VSXLEN=64: maximum valid 4-byte-aligned address with bit 63=0.
     * Shvstvecd requires "any valid 4-byte-aligned address". */
    uintptr_t target = 0x7FFFFFFFFFFFFFFCUL;
    vstvec_write(target);
    uintptr_t rb = vstvec_read();
    TEST_ASSERT("readback == 0x7FFFFFFFFFFFFFFC (address space upper bound)",
                rb == target);

    VSTVEC_RESTORE();
    TEST_END();
}
