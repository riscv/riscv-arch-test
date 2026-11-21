/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * Test Group 3: henvcfg configuration
 *
 * Tests HENV-01 through HENV-29 verify henvcfg register fields
 * and their control over the VS-mode execution environment.
 *
 * Each henvcfg bit is constrained by the corresponding menvcfg bit:
 * if menvcfg.X=0 then henvcfg.X is read-only zero. Tests enable the
 * menvcfg bit first, then manipulate henvcfg independently.
 */

#include "hyp_test_helpers.h"

/* ===================================================================
 * Local bit definitions for henvcfg / menvcfg fields (RV64).
 *
 * These complement the MENVCFG_PBMTE, MENVCFG_ADUE, and HENVCFG_STCE
 * constants already present in encoding.h.
 * =================================================================== */

#define ENVCFG_FIOM       (1ULL << 0)   /* Fence of I/O implies Memory */
#define ENVCFG_LPE        (1ULL << 2)   /* Landing Pad Enable (Zicfilp) */
#define ENVCFG_SSE        (1ULL << 3)   /* Shadow Stack Enable (Zicfiss) */
#define ENVCFG_PMM_OFF    32            /* PMM field offset [33:32] */
#define ENVCFG_PMM_MASK   (3ULL << 32)  /* PMM field mask */
#define ENVCFG_DTE        (1ULL << 59)  /* Double Trap Enable (Ssdbltrp) */
#define ENVCFG_PBMTE      (1ULL << 62)  /* Page-Based Memory Types Enable */
#define ENVCFG_STCE       (1ULL << 63)  /* STimecmp Enable */

/* vsstatus.SDT bit (Ssdbltrp double-trap indicator, bit 24) */
#define VSSTATUS_SDT      (1ULL << 24)

/* ===================================================================
 * Extension probing and henvcfg field manipulation helpers
 * =================================================================== */

/**
 * probe_menvcfg_bit - Check if a menvcfg feature bit is writable.
 *
 * Returns true if the extension is implemented (bit sticks after write).
 * Restores original menvcfg value afterwards.
 */
static bool probe_menvcfg_bit(uintptr_t bit) {
    uintptr_t orig = tsbi_csr_read(CSR_MENVCFG);
    tsbi_csr_write(CSR_MENVCFG, orig | bit);
    uintptr_t readback = tsbi_csr_read(CSR_MENVCFG);
    tsbi_csr_write(CSR_MENVCFG, orig);
    return (readback & bit) != 0;
}

/**
 * enable_envcfg_bit - Enable a feature in both menvcfg and henvcfg.
 *
 * menvcfg constrains henvcfg: the menvcfg bit must be set first.
 */
static void enable_envcfg_bit(uintptr_t bit) {
    tsbi_csr_write(CSR_MENVCFG, tsbi_csr_read(CSR_MENVCFG) | bit);
    henvcfg_write(henvcfg_read() | bit);
}

/**
 * disable_henvcfg_bit - Clear a feature bit in henvcfg only.
 *
 * menvcfg stays enabled so the bit is writable for subsequent tests.
 */
static void disable_henvcfg_bit(uintptr_t bit) {
    henvcfg_write(henvcfg_read() & ~bit);
}

/**
 * set_henvcfg_cbie - Write the 2-bit CBIE field in henvcfg.
 */
static void set_henvcfg_cbie(uintptr_t value) {
    uintptr_t cfg = henvcfg_read();
    cfg &= ~ENVCFG_CBIE_MASK;
    cfg |= (value << ENVCFG_CBIE_SHIFT) & ENVCFG_CBIE_MASK;
    henvcfg_write(cfg);
}

/* ===================================================================
 * VS-mode trampoline functions (passed to run_in_vs_mode)
 * =================================================================== */

/*
 * CBO.ZERO (Zicboz): funct12=0x004, funct3=010, opcode=MISC-MEM.
 * Encoding with rs1=a0(x10): 0x0045200F.
 */
static uintptr_t vs_exec_cbo_zero(uintptr_t addr) {
    register uintptr_t base asm("a0") = addr;
    asm volatile (".4byte 0x0045200F" :: "r"(base) : "memory");
    return 0;
}

/* CBO.CLEAN (Zicbom): funct12=0x001, encoding: 0x0015200F. */
static uintptr_t vs_exec_cbo_clean(uintptr_t addr) {
    register uintptr_t base asm("a0") = addr;
    asm volatile (".4byte 0x0015200F" :: "r"(base) : "memory");
    return 0;
}

/* CBO.INVAL (Zicbom): funct12=0x000, encoding: 0x0005200F. */
static uintptr_t vs_exec_cbo_inval(uintptr_t addr) {
    register uintptr_t base asm("a0") = addr;
    asm volatile (".4byte 0x0005200F" :: "r"(base) : "memory");
    return 0;
}

/* CBO.FLUSH (Zicbom): funct12=0x002, encoding: 0x0025200F. */
static uintptr_t vs_exec_cbo_flush(uintptr_t addr) {
    register uintptr_t base asm("a0") = addr;
    asm volatile (".4byte 0x0025200F" :: "r"(base) : "memory");
    return 0;
}

/* Read stimecmp CSR 0x14D (maps to vstimecmp when V=1 + STCE=1). */
static uintptr_t vs_read_stimecmp(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    v = CSRR(CSR_STIMECMP);
    return v;
}

/*
 * FENCE with I/O-only ordering (pred=IO, succ=IO).
 * With FIOM=1 this implies full IORW ordering; with FIOM=0 only IO.
 * Encoding: fm=0000, pred=1100, succ=1100 → 0x0CC0000F.
 */
static uintptr_t vs_exec_fence_io(uintptr_t arg) {
    (void)arg;
    asm volatile (".4byte 0x0CC0000F" ::: "memory");
    return 0;
}

/* ===================================================================
 * Two-stage translation setup for PBMTE / ADUE tests.
 *
 * Creates identity mapping (VA=GPA=SPA) on both VS-stage and G-stage.
 * Uses PTE_U on both stages + sets vsstatus.SUM=1 so VS-mode can
 * access user-flagged pages.
 * =================================================================== */

static void setup_vs_two_stage(two_stage_ctx_t *ctx) {
    gpt_pool_reset();
    pt_pool_reset();
    two_stage_init(ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    uintptr_t flags = PTE_V | PTE_R | PTE_W | PTE_X | PTE_U | PTE_A | PTE_D;

    /*
     * VS-stage kernel code pages must NOT have PTE_U: the RISC-V spec
     * forbids S-mode (and VS-mode) instruction fetch from U-flagged
     * pages regardless of SUM.  SUM only relaxes load/store access.
     */
    uintptr_t vs_kern_flags = PTE_V | PTE_R | PTE_W | PTE_X | PTE_A | PTE_D;

    /* Map low memory (kernel + UART) at 2MB granularity on both stages. */
    uintptr_t lo_base = PLATFORM_MEM_BASE & ~(PAGE_SIZE_2M - 1);
    uintptr_t lo_end  = TEST_REGION_BASE  & ~(PAGE_SIZE_2M - 1);
    if (lo_end > lo_base) {
        two_stage_setup_identity(ctx, lo_base, lo_end - lo_base,
                                 flags, PT_LEVEL_2M);
        two_stage_vs_identity(ctx, lo_base, lo_end - lo_base,
                              vs_kern_flags, PT_LEVEL_2M);
    }

    /* Map test region at 4KB granularity on both stages. */
    uintptr_t r_start = TEST_REGION_BASE;
    uintptr_t r_end   = (uintptr_t)__vm_test_region_end;
    two_stage_setup_identity(ctx, r_start, r_end - r_start,
                             flags, PT_LEVEL_4K);
    two_stage_vs_identity(ctx, r_start, r_end - r_start,
                          flags, PT_LEVEL_4K);

    /* Allow VS-mode to access U-flagged pages (load/store only). */
    uintptr_t vsstatus;
    vsstatus = CSRR(CSR_VSSTATUS);
    vsstatus |= SSTATUS_SUM_BIT;
    CSRW(CSR_VSSTATUS, vsstatus);
}

/* ===================================================================
 * HENV-01: henvcfg basic read/write
 * norm:henvcfg_sz_acc_op
 * =================================================================== */
TEST_REGISTER(henvcfg_01_basic_rw);
bool henvcfg_01_basic_rw(void) {
    TEST_BEGIN("HENV-01: henvcfg basic read/write");

    /* Enable all menvcfg bits so henvcfg is unconstrained. */
    tsbi_csr_write(CSR_MENVCFG, ~0ULL);

    /* Write all-ones and read back to discover implemented fields. */
    henvcfg_write(~0ULL);
    uintptr_t all_ones = henvcfg_read();

    /* Write all-zeros and read back. */
    henvcfg_write(0ULL);
    uintptr_t all_zeros = henvcfg_read();

    /* Verify at least some fields are writable. */
    TEST_ASSERT("henvcfg has writable fields", all_ones != all_zeros);

    /*
     * Write a pattern using only spec-legal field values and verify
     * read-after-write consistency.  Avoid arbitrary bit patterns:
     * CBIE is a 2-bit WARL field where encoding 0b10 is reserved,
     * and WPRI bits may have implementation-defined behaviour.
     */
    uintptr_t pattern = ENVCFG_FIOM
                      | (CBIE_FLUSH << ENVCFG_CBIE_SHIFT)
                      | ENVCFG_CBCFE
                      | ENVCFG_STCE;
    henvcfg_write(pattern);
    uintptr_t readback = henvcfg_read();

    /* Restrict comparison to known spec-defined fields only. */
    uintptr_t writable_mask = all_ones ^ all_zeros;
    uintptr_t known_fields = ENVCFG_FIOM | ENVCFG_CBIE_MASK | ENVCFG_CBCFE
                           | ENVCFG_CBZE | ENVCFG_DTE | ENVCFG_PBMTE
                           | ENVCFG_STCE;
    uintptr_t field_mask = writable_mask & known_fields;
    TEST_ASSERT_EQ("pattern read-after-write consistent",
                   readback & field_mask,
                   pattern & field_mask);

    HYP_TEST_END();
}

/* ===================================================================
 * HENV-02: FIOM=1 modifies FENCE behavior in V=1
 * norm:henvcfg_fiom_op / norm:henvcfg_fiom_order
 *
 * With FIOM=1, FENCE IO,IO implies FENCE IORW,IORW in VS-mode.
 * Memory ordering cannot be functionally verified on a single core;
 * we verify the field is writable and VS-mode FENCE executes cleanly.
 * =================================================================== */
TEST_REGISTER(henvcfg_02_fiom_enabled);
bool henvcfg_02_fiom_enabled(void) {
    TEST_BEGIN("HENV-02: FIOM=1 modifies FENCE behavior");

    if (!probe_menvcfg_bit(ENVCFG_FIOM))
        TEST_SKIP("FIOM not implemented in menvcfg");

    /* Enable FIOM in both menvcfg and henvcfg. */
    enable_envcfg_bit(ENVCFG_FIOM);
    TEST_ASSERT_EQ("henvcfg.FIOM=1",
                   henvcfg_read() & ENVCFG_FIOM, ENVCFG_FIOM);

    /* VS-mode: FENCE IO,IO should execute without exception. */
    VS_EXPECT_NO_TRAP(run_in_vs_mode(vs_exec_fence_io, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * HENV-03: FIOM=0 does not modify FENCE in V=1
 * norm:henvcfg_fiom_op
 *
 * With FIOM=0 the FENCE behaves unchanged (no I/O→Memory implication).
 * =================================================================== */
TEST_REGISTER(henvcfg_03_fiom_disabled);
bool henvcfg_03_fiom_disabled(void) {
    TEST_BEGIN("HENV-03: FIOM=0 does not modify FENCE");

    if (!probe_menvcfg_bit(ENVCFG_FIOM))
        TEST_SKIP("FIOM not implemented in menvcfg");

    /* Enable FIOM in menvcfg (so henvcfg.FIOM is writable), then clear. */
    tsbi_csr_write(CSR_MENVCFG, tsbi_csr_read(CSR_MENVCFG) | ENVCFG_FIOM);
    disable_henvcfg_bit(ENVCFG_FIOM);
    TEST_ASSERT_EQ("henvcfg.FIOM=0",
                   henvcfg_read() & ENVCFG_FIOM, 0UL);

    /* VS-mode: FENCE IO,IO should still execute without exception. */
    VS_EXPECT_NO_TRAP(run_in_vs_mode(vs_exec_fence_io, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * HENV-04: PBMTE=1 enables VS-stage Svpbmt
 * norm:henvcfg_pbmte_op
 *
 * When PBMTE=1, the PBMT field in VS-stage PTEs is honoured.
 * We set PBMT to NC (Non-Cacheable) on a test page and verify the
 * access completes without fault (the memory type change itself is
 * not functionally observable in a simple test, but the PTE remains
 * valid and the access succeeds).
 * =================================================================== */
TEST_REGISTER(henvcfg_04_pbmte_enabled);
bool henvcfg_04_pbmte_enabled(void) {
    TEST_BEGIN("HENV-04: PBMTE=1 enables VS-stage Svpbmt");

    if (!probe_menvcfg_bit(ENVCFG_PBMTE))
        TEST_SKIP("Svpbmt not implemented (menvcfg.PBMTE not writable)");

    /* Enable PBMTE on both levels. */
    enable_envcfg_bit(ENVCFG_PBMTE);

    /* Build two-stage identity mapping. */
    two_stage_ctx_t ctx;
    setup_vs_two_stage(&ctx);

    /*
     * Modify the VS-stage PTE for test_data_area: add PBMT=NC.
     * Re-map that single 4K page with the PBMT field set.
     */
    uintptr_t target = (uintptr_t)test_data_area;
    uintptr_t page   = target & ~(PAGE_SIZE_4K - 1);
    uintptr_t vs_flags = PTE_V | PTE_R | PTE_W | PTE_U | PTE_A | PTE_D
                         | PBMT_NC;
    two_stage_vs_map(&ctx, page, page, vs_flags, PT_LEVEL_4K);

    /* VS-mode load should succeed — PBMT=NC is valid when PBMTE=1. */
    VS_EXPECT_NO_TRAP(two_stage_run_in_vs(&ctx, test_vs_load, target));

    two_stage_cleanup(&ctx);
    HYP_TEST_END();
}

/* ===================================================================
 * HENV-05: PBMTE=0 disables VS-stage Svpbmt
 * norm:henvcfg_pbmte_op
 *
 * When PBMTE=0, any non-zero PBMT in a VS-stage PTE is reserved and
 * causes a page fault.
 * =================================================================== */
TEST_REGISTER(henvcfg_05_pbmte_disabled);
bool henvcfg_05_pbmte_disabled(void) {
    TEST_BEGIN("HENV-05: PBMTE=0 disables VS-stage Svpbmt");

    if (!probe_menvcfg_bit(ENVCFG_PBMTE))
        TEST_SKIP("Svpbmt not implemented (menvcfg.PBMTE not writable)");

    /* Enable menvcfg.PBMTE so henvcfg.PBMTE is writable, then clear it. */
    tsbi_csr_write(CSR_MENVCFG, tsbi_csr_read(CSR_MENVCFG) | ENVCFG_PBMTE);
    disable_henvcfg_bit(ENVCFG_PBMTE);
    TEST_ASSERT_EQ("henvcfg.PBMTE=0",
                   henvcfg_read() & ENVCFG_PBMTE, 0UL);

    /* Build two-stage identity mapping. */
    two_stage_ctx_t ctx;
    setup_vs_two_stage(&ctx);

    /* Set PBMT=NC on the VS-stage PTE for test_data_area. */
    uintptr_t target = (uintptr_t)test_data_area;
    uintptr_t page   = target & ~(PAGE_SIZE_4K - 1);
    uintptr_t vs_flags = PTE_V | PTE_R | PTE_W | PTE_U | PTE_A | PTE_D
                         | PBMT_NC;
    two_stage_vs_map(&ctx, page, page, vs_flags, PT_LEVEL_4K);

    /* VS-mode load should fault: PBMT≠0 is reserved when PBMTE=0. */
    trap_expect_begin();
    two_stage_run_in_vs(&ctx, test_vs_load_expect_fault, target);
    TEST_ASSERT("page fault triggered", trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause == load page fault",
                       trap_get_cause(),
                       (uintptr_t)CAUSE_LOAD_PAGE_FAULT);
    }
    trap_expect_end();

    two_stage_cleanup(&ctx);
    HYP_TEST_END();
}

/* ===================================================================
 * HENV-06: ADUE=1 enables VS-stage A/D hardware update
 * norm:henvcfg_adue_op
 *
 * When ADUE=1, hardware auto-sets the A and D bits in VS-stage PTEs.
 * We map a page with A=0, D=0 and verify the access succeeds (hardware
 * updates A/D).
 * =================================================================== */
TEST_REGISTER(henvcfg_06_adue_enabled);
bool henvcfg_06_adue_enabled(void) {
    TEST_BEGIN("HENV-06: ADUE=1 enables VS-stage A/D hw update");

    if (!probe_menvcfg_bit(MENVCFG_ADUE))
        TEST_SKIP("Svadu not implemented (menvcfg.ADUE not writable)");

    /* Enable ADUE on both menvcfg and henvcfg. */
    enable_envcfg_bit(MENVCFG_ADUE);

    /* Build two-stage identity mapping. */
    two_stage_ctx_t ctx;
    setup_vs_two_stage(&ctx);

    /* Re-map test_data_area with A=0, D=0 on VS-stage. */
    uintptr_t target = (uintptr_t)test_data_area;
    uintptr_t page   = target & ~(PAGE_SIZE_4K - 1);
    uintptr_t vs_flags = PTE_V | PTE_R | PTE_W | PTE_U; /* A=0, D=0 */
    two_stage_vs_map(&ctx, page, page, vs_flags, PT_LEVEL_4K);

    /* VS-mode load: with ADUE=1, HW sets A bit — no fault. */
    VS_EXPECT_NO_TRAP(two_stage_run_in_vs(&ctx, test_vs_load, target));

    /* Verify hardware actually set the A bit in VS-stage PTE. */
    uintptr_t *pte = pt_get_pte(&ctx.vs_ctx, page, PT_LEVEL_4K);
    TEST_ASSERT("hardware set A bit in VS-stage PTE",
                pte != NULL && (*pte & PTE_A) != 0);

    two_stage_cleanup(&ctx);
    HYP_TEST_END();
}

/* ===================================================================
 * HENV-07: ADUE=0 disables VS-stage A/D hardware update (Svade)
 * norm:henvcfg_adue_op
 *
 * When ADUE=0, accessing a PTE with A=0 causes a page fault instead
 * of a hardware A/D update.
 * =================================================================== */
TEST_REGISTER(henvcfg_07_adue_disabled);
bool henvcfg_07_adue_disabled(void) {
    TEST_BEGIN("HENV-07: ADUE=0 disables VS-stage A/D hw update");

    if (!probe_menvcfg_bit(MENVCFG_ADUE))
        TEST_SKIP("Svadu not implemented (menvcfg.ADUE not writable)");

    /* Enable menvcfg.ADUE so henvcfg.ADUE is writable, then clear it. */
    tsbi_csr_write(CSR_MENVCFG, tsbi_csr_read(CSR_MENVCFG) | MENVCFG_ADUE);
    disable_henvcfg_bit(MENVCFG_ADUE);
    TEST_ASSERT_EQ("henvcfg.ADUE=0",
                   henvcfg_read() & MENVCFG_ADUE, 0UL);

    /* Build two-stage identity mapping. */
    two_stage_ctx_t ctx;
    setup_vs_two_stage(&ctx);

    /* Re-map test_data_area with A=0 on VS-stage. */
    uintptr_t target = (uintptr_t)test_data_area;
    uintptr_t page   = target & ~(PAGE_SIZE_4K - 1);
    uintptr_t vs_flags = PTE_V | PTE_R | PTE_W | PTE_U; /* A=0 */
    two_stage_vs_map(&ctx, page, page, vs_flags, PT_LEVEL_4K);

    /* VS-mode load should page-fault (A=0 + ADUE=0 → Svade fault). */
    trap_expect_begin();
    two_stage_run_in_vs(&ctx, test_vs_load_expect_fault, target);
    TEST_ASSERT("page fault triggered", trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause == load page fault",
                       trap_get_cause(),
                       (uintptr_t)CAUSE_LOAD_PAGE_FAULT);
    }
    trap_expect_end();

    two_stage_cleanup(&ctx);
    HYP_TEST_END();
}

/* ===================================================================
 * HENV-08: STCE=1 enables vstimecmp access
 * norm:henvcfg_stce
 *
 * When STCE=1 and hcounteren.TM=1, VS-mode can access stimecmp
 * (which maps to vstimecmp). The access should complete normally.
 * =================================================================== */
TEST_REGISTER(henvcfg_08_stce_enabled);
bool henvcfg_08_stce_enabled(void) {
    TEST_BEGIN("HENV-08: STCE=1 enables vstimecmp access");

    if (!probe_menvcfg_bit(ENVCFG_STCE))
        TEST_SKIP("Sstc not implemented (menvcfg.STCE not writable)");

    /* Enable STCE in both menvcfg and henvcfg. */
    enable_envcfg_bit(ENVCFG_STCE);

    /* Ensure mcounteren.TM=1 and hcounteren.TM=1 so VS-mode can access
     * stimecmp/vstimecmp. Both are required by the spec. */
    tsbi_csr_set(CSR_MCOUNTEREN, 1U << 1);
    hcounteren_set(1U << 1);

    /* VS-mode read of stimecmp (=vstimecmp) should succeed. */
    VS_EXPECT_NO_TRAP(run_in_vs_mode(vs_read_stimecmp, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * HENV-09: STCE=0 disables vstimecmp (virtual-instruction exception)
 * norm:henvcfg_stce
 *
 * When STCE=0, VS-mode access to stimecmp triggers a
 * virtual-instruction exception (cause=22).
 * =================================================================== */
TEST_REGISTER(henvcfg_09_stce_disabled);
bool henvcfg_09_stce_disabled(void) {
    TEST_BEGIN("HENV-09: STCE=0 disables vstimecmp access");

    if (!probe_menvcfg_bit(ENVCFG_STCE))
        TEST_SKIP("Sstc not implemented (menvcfg.STCE not writable)");

    /* Enable menvcfg.STCE so henvcfg.STCE is writable, then clear it. */
    tsbi_csr_write(CSR_MENVCFG, tsbi_csr_read(CSR_MENVCFG) | ENVCFG_STCE);
    disable_henvcfg_bit(ENVCFG_STCE);
    TEST_ASSERT_EQ("henvcfg.STCE=0",
                   henvcfg_read() & ENVCFG_STCE, 0UL);

    /* Ensure mcounteren.TM=1 and hcounteren.TM=1 so the trap is due to STCE,
     * not counteren. Both are required by the spec. */
    tsbi_csr_set(CSR_MCOUNTEREN, 1U << 1);
    hcounteren_set(1U << 1);

    /* VS-mode read of stimecmp should trap with cause=22. */
    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_read_stimecmp, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * HENV-10: CBZE=1 enables CBO.ZERO in VS-mode
 * norm:henvcfg_cbze
 *
 * When henvcfg.CBZE=1 (and menvcfg.CBZE=1), VS-mode can execute
 * CBO.ZERO without exception.
 * =================================================================== */
TEST_REGISTER(henvcfg_10_cbze_enabled);
bool henvcfg_10_cbze_enabled(void) {
    TEST_BEGIN("HENV-10: CBZE=1 enables CBO.ZERO");

    if (!probe_menvcfg_bit(ENVCFG_CBZE))
        TEST_SKIP("Zicboz not implemented (menvcfg.CBZE not writable)");

    enable_envcfg_bit(ENVCFG_CBZE);

    /* CBO.ZERO operates on the cache-block containing test_data_area. */
    uintptr_t target = (uintptr_t)test_data_area;

    VS_EXPECT_NO_TRAP(run_in_vs_mode(vs_exec_cbo_zero, target));

    HYP_TEST_END();
}

/* ===================================================================
 * HENV-11: CBZE=0 disables CBO.ZERO in VS-mode
 * norm:henvcfg_cbze
 *
 * When henvcfg.CBZE=0, VS-mode CBO.ZERO triggers a
 * virtual-instruction exception (cause=22).
 * =================================================================== */
TEST_REGISTER(henvcfg_11_cbze_disabled);
bool henvcfg_11_cbze_disabled(void) {
    TEST_BEGIN("HENV-11: CBZE=0 disables CBO.ZERO");

    if (!probe_menvcfg_bit(ENVCFG_CBZE))
        TEST_SKIP("Zicboz not implemented (menvcfg.CBZE not writable)");

    /* Enable menvcfg.CBZE so henvcfg bit is writable, then clear it. */
    tsbi_csr_write(CSR_MENVCFG, tsbi_csr_read(CSR_MENVCFG) | ENVCFG_CBZE);
    disable_henvcfg_bit(ENVCFG_CBZE);
    TEST_ASSERT_EQ("henvcfg.CBZE=0",
                   henvcfg_read() & ENVCFG_CBZE, 0UL);

    uintptr_t target = (uintptr_t)test_data_area;

    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_exec_cbo_zero, target));

    HYP_TEST_END();
}

/* ===================================================================
 * HENV-12: CBCFE=1 enables CBO.CLEAN/FLUSH in VS-mode
 * norm:henvcfg_cbcfe
 *
 * When henvcfg.CBCFE=1, VS-mode can execute CBO.CLEAN normally.
 * =================================================================== */
TEST_REGISTER(henvcfg_12_cbcfe_enabled);
bool henvcfg_12_cbcfe_enabled(void) {
    TEST_BEGIN("HENV-12: CBCFE=1 enables CBO.CLEAN");

    if (!probe_menvcfg_bit(ENVCFG_CBCFE))
        TEST_SKIP("Zicbom not implemented (menvcfg.CBCFE not writable)");

    enable_envcfg_bit(ENVCFG_CBCFE);

    uintptr_t target = (uintptr_t)test_data_area;

    VS_EXPECT_NO_TRAP(run_in_vs_mode(vs_exec_cbo_clean, target));

    /* Also verify CBO.FLUSH is enabled when CBCFE=1. */
    VS_EXPECT_NO_TRAP(run_in_vs_mode(vs_exec_cbo_flush, target));

    HYP_TEST_END();
}

/* ===================================================================
 * HENV-13: CBCFE=0 disables CBO.CLEAN/FLUSH in VS-mode
 * norm:henvcfg_cbcfe
 *
 * When henvcfg.CBCFE=0, VS-mode CBO.CLEAN triggers a
 * virtual-instruction exception (cause=22).
 * =================================================================== */
TEST_REGISTER(henvcfg_13_cbcfe_disabled);
bool henvcfg_13_cbcfe_disabled(void) {
    TEST_BEGIN("HENV-13: CBCFE=0 disables CBO.CLEAN");

    if (!probe_menvcfg_bit(ENVCFG_CBCFE))
        TEST_SKIP("Zicbom not implemented (menvcfg.CBCFE not writable)");

    tsbi_csr_write(CSR_MENVCFG, tsbi_csr_read(CSR_MENVCFG) | ENVCFG_CBCFE);
    disable_henvcfg_bit(ENVCFG_CBCFE);
    TEST_ASSERT_EQ("henvcfg.CBCFE=0",
                   henvcfg_read() & ENVCFG_CBCFE, 0UL);

    uintptr_t target = (uintptr_t)test_data_area;

    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_exec_cbo_clean, target));

    /* Also verify CBO.FLUSH triggers virtual-instruction when CBCFE=0. */
    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_exec_cbo_flush, target));

    HYP_TEST_END();
}

/* ===================================================================
 * HENV-14: CBIE=01 makes CBO.INVAL perform flush in VS-mode
 * norm:henvcfg_cbie
 *
 * When henvcfg.CBIE=01, CBO.INVAL in VS-mode performs a cache-block
 * flush instead of invalidate. The instruction should execute without
 * exception.
 * =================================================================== */
TEST_REGISTER(henvcfg_14_cbie_flush);
bool henvcfg_14_cbie_flush(void) {
    TEST_BEGIN("HENV-14: CBIE=01 CBO.INVAL performs flush");

    /* CBIE requires Zicbom (same menvcfg bit group as CBCFE). */
    if (!probe_menvcfg_bit(ENVCFG_CBCFE))
        TEST_SKIP("Zicbom not implemented (menvcfg.CBCFE not writable)");

    /* Enable menvcfg CBIE field writable. */
    uintptr_t mcfg = tsbi_csr_read(CSR_MENVCFG);
    mcfg |= ENVCFG_CBIE_MASK | ENVCFG_CBCFE;
    tsbi_csr_write(CSR_MENVCFG, mcfg);

    /* Set henvcfg.CBIE=01 (flush). */
    set_henvcfg_cbie(CBIE_FLUSH);
    uintptr_t cbie_val = (henvcfg_read() & ENVCFG_CBIE_MASK) >> ENVCFG_CBIE_SHIFT;
    TEST_ASSERT_EQ("henvcfg.CBIE=01", cbie_val, CBIE_FLUSH);

    uintptr_t target = (uintptr_t)test_data_area;

    /* CBO.INVAL should execute as flush — no exception. */
    VS_EXPECT_NO_TRAP(run_in_vs_mode(vs_exec_cbo_inval, target));

    HYP_TEST_END();
}

/* ===================================================================
 * HENV-15: CBIE=00 disables CBO.INVAL in VS-mode
 * norm:henvcfg_cbie
 *
 * When henvcfg.CBIE=00, CBO.INVAL triggers a virtual-instruction
 * exception (cause=22).
 * =================================================================== */
TEST_REGISTER(henvcfg_15_cbie_illegal);
bool henvcfg_15_cbie_illegal(void) {
    TEST_BEGIN("HENV-15: CBIE=00 disables CBO.INVAL");

    if (!probe_menvcfg_bit(ENVCFG_CBCFE))
        TEST_SKIP("Zicbom not implemented (menvcfg.CBCFE not writable)");

    /* Enable menvcfg CBIE field. */
    uintptr_t mcfg = tsbi_csr_read(CSR_MENVCFG);
    mcfg |= ENVCFG_CBIE_MASK | ENVCFG_CBCFE;
    tsbi_csr_write(CSR_MENVCFG, mcfg);

    /* Set henvcfg.CBIE=00 (illegal). */
    set_henvcfg_cbie(CBIE_DISABLE);
    uintptr_t cbie_val = (henvcfg_read() & ENVCFG_CBIE_MASK) >> ENVCFG_CBIE_SHIFT;
    TEST_ASSERT_EQ("henvcfg.CBIE=00", cbie_val, CBIE_DISABLE);

    uintptr_t target = (uintptr_t)test_data_area;

    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_exec_cbo_inval, target));

    HYP_TEST_END();
}

/* ===================================================================
 * HENV-16: DTE=0 disables VS-mode Ssdbltrp (vsstatus.SDT read-zero)
 * norm:henvcfg_dte_op
 *
 * When henvcfg.DTE=0, the vsstatus.SDT field is read-only zero.
 * =================================================================== */
TEST_REGISTER(henvcfg_16_dte_disabled);
bool henvcfg_16_dte_disabled(void) {
    TEST_BEGIN("HENV-16: DTE=0 disables vsstatus.SDT");

    if (!probe_menvcfg_bit(ENVCFG_DTE))
        TEST_SKIP("Ssdbltrp not implemented (menvcfg.DTE not writable)");

    /* Enable menvcfg.DTE so henvcfg.DTE is writable, then clear it. */
    tsbi_csr_write(CSR_MENVCFG, tsbi_csr_read(CSR_MENVCFG) | ENVCFG_DTE);
    disable_henvcfg_bit(ENVCFG_DTE);
    TEST_ASSERT_EQ("henvcfg.DTE=0",
                   henvcfg_read() & ENVCFG_DTE, 0UL);

    /* Try to set vsstatus.SDT=1 via direct CSR write (CSR 0x200). */
    uintptr_t vsstatus;
    vsstatus = CSRR(CSR_VSSTATUS);
    CSRW(CSR_VSSTATUS, vsstatus | VSSTATUS_SDT);

    /* Read back — SDT should be zero. */
    uintptr_t readback;
    readback = CSRR(CSR_VSSTATUS);
    TEST_ASSERT_EQ("vsstatus.SDT reads zero when DTE=0",
                   readback & VSSTATUS_SDT, 0UL);

    HYP_TEST_END();
}

/* ===================================================================
 * HENV-17: DTE=1 enables VS-mode Ssdbltrp (vsstatus.SDT writable)
 * norm:henvcfg_dte_op
 *
 * When henvcfg.DTE=1, vsstatus.SDT is read-write.
 * =================================================================== */
TEST_REGISTER(henvcfg_17_dte_enabled);
bool henvcfg_17_dte_enabled(void) {
    TEST_BEGIN("HENV-17: DTE=1 enables vsstatus.SDT");

    if (!probe_menvcfg_bit(ENVCFG_DTE))
        TEST_SKIP("Ssdbltrp not implemented (menvcfg.DTE not writable)");

    /* Enable DTE in both menvcfg and henvcfg. */
    enable_envcfg_bit(ENVCFG_DTE);
    TEST_ASSERT_EQ("henvcfg.DTE=1",
                   henvcfg_read() & ENVCFG_DTE, ENVCFG_DTE);

    /* Write vsstatus.SDT=1 and read back. */
    uintptr_t vsstatus;
    vsstatus = CSRR(CSR_VSSTATUS);
    CSRW(CSR_VSSTATUS, vsstatus | VSSTATUS_SDT);

    uintptr_t readback;
    readback = CSRR(CSR_VSSTATUS);
    TEST_ASSERT_EQ("vsstatus.SDT=1 when DTE=1",
                   readback & VSSTATUS_SDT, VSSTATUS_SDT);

    /* Clear SDT to avoid side effects. */
    CSRW(CSR_VSSTATUS, readback & ~VSSTATUS_SDT);

    HYP_TEST_END();
}

/* ===================================================================
 * HENV-18: PBMTE reads zero when Svpbmt not implemented
 * norm:henvcfg_pbmte_op
 *
 * If the platform does not implement Svpbmt, menvcfg.PBMTE is
 * read-only zero, and consequently henvcfg.PBMTE must also be zero.
 * =================================================================== */
TEST_REGISTER(henvcfg_18_pbmte_unimplemented);
bool henvcfg_18_pbmte_unimplemented(void) {
    TEST_BEGIN("HENV-18: PBMTE reads zero when Svpbmt not implemented");

    if (probe_menvcfg_bit(ENVCFG_PBMTE))
        TEST_SKIP("Svpbmt IS implemented — test only for non-impl case");

    /* menvcfg.PBMTE=0 (not writable), so henvcfg.PBMTE must read zero. */
    henvcfg_write(henvcfg_read() | ENVCFG_PBMTE);
    TEST_ASSERT_EQ("henvcfg.PBMTE reads zero",
                   henvcfg_read() & ENVCFG_PBMTE, 0UL);

    HYP_TEST_END();
}

/* ===================================================================
 * HENV-19: STCE reads zero when Sstc not implemented
 * norm:henvcfg_stce
 *
 * If the platform does not implement Sstc, menvcfg.STCE is read-only
 * zero, and consequently henvcfg.STCE must also be zero.
 * =================================================================== */
TEST_REGISTER(henvcfg_19_stce_unimplemented);
bool henvcfg_19_stce_unimplemented(void) {
    TEST_BEGIN("HENV-19: STCE reads zero when Sstc not implemented");

    if (probe_menvcfg_bit(ENVCFG_STCE))
        TEST_SKIP("Sstc IS implemented — test only for non-impl case");

    /* menvcfg.STCE=0 (not writable), so henvcfg.STCE must read zero. */
    henvcfg_write(henvcfg_read() | ENVCFG_STCE);
    TEST_ASSERT_EQ("henvcfg.STCE reads zero",
                   henvcfg_read() & ENVCFG_STCE, 0UL);

    HYP_TEST_END();
}

/* ===================================================================
 * HENV-20: CBIE=11 makes CBO.INVAL perform invalidate in VS-mode
 * norm:henvcfg_cbie
 *
 * When henvcfg.CBIE=11, CBO.INVAL in VS-mode performs a true
 * invalidate operation. The instruction should execute without
 * exception.
 * =================================================================== */
TEST_REGISTER(henvcfg_20_cbie_inval);
bool henvcfg_20_cbie_inval(void) {
    TEST_BEGIN("HENV-20: CBIE=11 CBO.INVAL performs invalidate");

    if (!probe_menvcfg_bit(ENVCFG_CBCFE))
        TEST_SKIP("Zicbom not implemented (menvcfg.CBCFE not writable)");

    /* Enable menvcfg CBIE field. */
    uintptr_t mcfg = tsbi_csr_read(CSR_MENVCFG);
    mcfg |= ENVCFG_CBIE_MASK | ENVCFG_CBCFE;
    tsbi_csr_write(CSR_MENVCFG, mcfg);

    /* Set henvcfg.CBIE=11 (invalidate). */
    set_henvcfg_cbie(CBIE_INVAL);
    uintptr_t cbie_val = (henvcfg_read() & ENVCFG_CBIE_MASK) >> ENVCFG_CBIE_SHIFT;
    TEST_ASSERT_EQ("henvcfg.CBIE=11", cbie_val, CBIE_INVAL);

    uintptr_t target = (uintptr_t)test_data_area;

    /* CBO.INVAL should execute as invalidate -- no exception. */
    VS_EXPECT_NO_TRAP(run_in_vs_mode(vs_exec_cbo_inval, target));

    HYP_TEST_END();
}

/* ===================================================================
 * HENV-21: CBIE=10 is reserved, WARL behavior
 * norm:henvcfg_cbie
 *
 * The encoding 10b is reserved for CBIE. Writing it should result
 * in a legal value (WARL). Verify the field does not retain the
 * reserved encoding.
 * =================================================================== */
TEST_REGISTER(henvcfg_21_cbie_reserved);
bool henvcfg_21_cbie_reserved(void) {
    TEST_BEGIN("HENV-21: CBIE=10 reserved WARL behavior");

    if (!probe_menvcfg_bit(ENVCFG_CBCFE))
        TEST_SKIP("Zicbom not implemented (menvcfg.CBCFE not writable)");

    /* Enable menvcfg CBIE field. */
    uintptr_t mcfg = tsbi_csr_read(CSR_MENVCFG);
    mcfg |= ENVCFG_CBIE_MASK | ENVCFG_CBCFE;
    tsbi_csr_write(CSR_MENVCFG, mcfg);

    /* Also enable menvcfg.CBIE=11 so henvcfg.CBIE is not constrained. */
    mcfg = tsbi_csr_read(CSR_MENVCFG);
    mcfg &= ~ENVCFG_CBIE_MASK;
    mcfg |= (CBIE_INVAL << ENVCFG_CBIE_SHIFT) & ENVCFG_CBIE_MASK;
    tsbi_csr_write(CSR_MENVCFG, mcfg);

    /* Write reserved encoding 10b to henvcfg.CBIE. */
    set_henvcfg_cbie(2ULL);
    uintptr_t cbie_val = (henvcfg_read() & ENVCFG_CBIE_MASK) >> ENVCFG_CBIE_SHIFT;

    /* WARL: the reserved encoding 10b must NOT be retained. */
    TEST_ASSERT("CBIE does not retain reserved encoding 10b",
                cbie_val != 2ULL);

    HYP_TEST_END();
}

/* ===================================================================
 * HENV-22: PMM field read/write (Ssnpm)
 * norm:henvcfg_pmm_op
 *
 * When Ssnpm is implemented, the PMM WARL field in henvcfg controls
 * pointer masking for VS-mode. Legal values are 00, 10, 11.
 * Value 01 is reserved.
 * =================================================================== */
TEST_REGISTER(henvcfg_22_pmm_rw);
bool henvcfg_22_pmm_rw(void) {
    TEST_BEGIN("HENV-22: PMM field read/write (Ssnpm)");

    /* Probe: enable menvcfg.PMM and check if writable. */
    uintptr_t orig_m = tsbi_csr_read(CSR_MENVCFG);
    uintptr_t pmm_en = 3ULL << ENVCFG_PMM_OFF;  /* PMM=11 */
    tsbi_csr_write(CSR_MENVCFG, orig_m | pmm_en);
    uintptr_t m_rb = tsbi_csr_read(CSR_MENVCFG);
    tsbi_csr_write(CSR_MENVCFG, orig_m);
    if ((m_rb & ENVCFG_PMM_MASK) == 0)
        TEST_SKIP("Ssnpm not implemented (menvcfg.PMM not writable)");

    /* Enable PMM=11 in menvcfg so henvcfg.PMM is unconstrained. */
    tsbi_csr_write(CSR_MENVCFG, tsbi_csr_read(CSR_MENVCFG) | pmm_en);

    /* Test PMM=00 (disable). */
    uintptr_t cfg = henvcfg_read() & ~ENVCFG_PMM_MASK;
    henvcfg_write(cfg);
    TEST_ASSERT_EQ("PMM=00 writable",
                   (henvcfg_read() & ENVCFG_PMM_MASK) >> ENVCFG_PMM_OFF, 0UL);

    /* Test PMM=10 (PMLEN=7). */
    henvcfg_write(cfg | (2ULL << ENVCFG_PMM_OFF));
    uintptr_t rb = (henvcfg_read() & ENVCFG_PMM_MASK) >> ENVCFG_PMM_OFF;
    TEST_ASSERT_EQ("PMM=10 writable", rb, 2UL);

    /* Test PMM=11 (PMLEN=16). */
    henvcfg_write(cfg | (3ULL << ENVCFG_PMM_OFF));
    rb = (henvcfg_read() & ENVCFG_PMM_MASK) >> ENVCFG_PMM_OFF;
    TEST_ASSERT_EQ("PMM=11 writable", rb, 3UL);

    /* Test PMM=01 (reserved) -- WARL: must not retain 01. */
    henvcfg_write(cfg | (1ULL << ENVCFG_PMM_OFF));
    rb = (henvcfg_read() & ENVCFG_PMM_MASK) >> ENVCFG_PMM_OFF;
    TEST_ASSERT("PMM=01 reserved not retained (WARL)", rb != 1UL);

    /* Restore PMM=00. */
    henvcfg_write(cfg);
    tsbi_csr_write(CSR_MENVCFG, orig_m);

    HYP_TEST_END();
}

/* ===================================================================
 * HENV-23: LPE/SSE field read/write (Zicfilp / Zicfiss)
 * norm:henvcfg_lpe_op / norm:henvcfg_sse_op
 *
 * When implemented, LPE (bit 2) and SSE (bit 3) should be writable
 * in henvcfg (constrained by menvcfg).
 * =================================================================== */
TEST_REGISTER(henvcfg_23_lpe_sse_rw);
bool henvcfg_23_lpe_sse_rw(void) {
    TEST_BEGIN("HENV-23: LPE/SSE field read/write");

    /* --- LPE (Zicfilp) --- */
    if (!probe_menvcfg_bit(ENVCFG_LPE)) {
        /* LPE not implemented -- verify henvcfg.LPE reads zero. */
        henvcfg_write(henvcfg_read() | ENVCFG_LPE);
        TEST_ASSERT_EQ("henvcfg.LPE read-only zero (Zicfilp not impl)",
                       henvcfg_read() & ENVCFG_LPE, 0UL);
    } else {
        enable_envcfg_bit(ENVCFG_LPE);
        TEST_ASSERT_EQ("henvcfg.LPE=1",
                       henvcfg_read() & ENVCFG_LPE, ENVCFG_LPE);

        disable_henvcfg_bit(ENVCFG_LPE);
        TEST_ASSERT_EQ("henvcfg.LPE=0",
                       henvcfg_read() & ENVCFG_LPE, 0UL);
    }

    /* --- SSE (Zicfiss) --- */
    if (!probe_menvcfg_bit(ENVCFG_SSE)) {
        /* SSE not implemented -- verify henvcfg.SSE reads zero. */
        henvcfg_write(henvcfg_read() | ENVCFG_SSE);
        TEST_ASSERT_EQ("henvcfg.SSE read-only zero (Zicfiss not impl)",
                       henvcfg_read() & ENVCFG_SSE, 0UL);
    } else {
        enable_envcfg_bit(ENVCFG_SSE);
        TEST_ASSERT_EQ("henvcfg.SSE=1",
                       henvcfg_read() & ENVCFG_SSE, ENVCFG_SSE);

        disable_henvcfg_bit(ENVCFG_SSE);
        TEST_ASSERT_EQ("henvcfg.SSE=0",
                       henvcfg_read() & ENVCFG_SSE, 0UL);
    }

    HYP_TEST_END();
}

/* ===================================================================
 * HENV-24: PMM reads zero when Ssnpm not implemented
 * norm:henvcfg_pmm_op
 *
 * If the platform does not implement Ssnpm, menvcfg.PMM is read-only
 * zero, and consequently henvcfg.PMM must also be zero.
 * =================================================================== */
TEST_REGISTER(henvcfg_24_pmm_unimplemented);
bool henvcfg_24_pmm_unimplemented(void) {
    TEST_BEGIN("HENV-24: PMM reads zero when Ssnpm not implemented");

    /* Probe menvcfg.PMM. */
    uintptr_t orig_m = tsbi_csr_read(CSR_MENVCFG);
    uintptr_t pmm_en = 3ULL << ENVCFG_PMM_OFF;
    tsbi_csr_write(CSR_MENVCFG, orig_m | pmm_en);
    uintptr_t m_rb = tsbi_csr_read(CSR_MENVCFG);
    tsbi_csr_write(CSR_MENVCFG, orig_m);
    if ((m_rb & ENVCFG_PMM_MASK) != 0)
        TEST_SKIP("Ssnpm IS implemented -- test only for non-impl case");

    /* menvcfg.PMM=0 (not writable), so henvcfg.PMM must read zero. */
    henvcfg_write(henvcfg_read() | ENVCFG_PMM_MASK);
    TEST_ASSERT_EQ("henvcfg.PMM reads zero",
                   henvcfg_read() & ENVCFG_PMM_MASK, 0UL);

    HYP_TEST_END();
}

/* ===================================================================
 * HENV-25: CBIE reads zero when Zicbom not implemented
 * norm:henvcfg_cbie
 *
 * If the platform does not implement Zicbom, the CBIE field in
 * henvcfg is read-only zero.
 * =================================================================== */
TEST_REGISTER(henvcfg_25_cbie_unimplemented);
bool henvcfg_25_cbie_unimplemented(void) {
    TEST_BEGIN("HENV-25: CBIE reads zero when Zicbom not implemented");

    if (probe_menvcfg_bit(ENVCFG_CBCFE))
        TEST_SKIP("Zicbom IS implemented -- test only for non-impl case");

    henvcfg_write(henvcfg_read() | ENVCFG_CBIE_MASK);
    TEST_ASSERT_EQ("henvcfg.CBIE reads zero",
                   henvcfg_read() & ENVCFG_CBIE_MASK, 0UL);

    HYP_TEST_END();
}

/* ===================================================================
 * HENV-26: CBCFE reads zero when Zicbom not implemented
 * norm:henvcfg_cbcfe
 * =================================================================== */
TEST_REGISTER(henvcfg_26_cbcfe_unimplemented);
bool henvcfg_26_cbcfe_unimplemented(void) {
    TEST_BEGIN("HENV-26: CBCFE reads zero when Zicbom not implemented");

    if (probe_menvcfg_bit(ENVCFG_CBCFE))
        TEST_SKIP("Zicbom IS implemented -- test only for non-impl case");

    henvcfg_write(henvcfg_read() | ENVCFG_CBCFE);
    TEST_ASSERT_EQ("henvcfg.CBCFE reads zero",
                   henvcfg_read() & ENVCFG_CBCFE, 0UL);

    HYP_TEST_END();
}

/* ===================================================================
 * HENV-27: CBZE reads zero when Zicboz not implemented
 * norm:henvcfg_cbze
 * =================================================================== */
TEST_REGISTER(henvcfg_27_cbze_unimplemented);
bool henvcfg_27_cbze_unimplemented(void) {
    TEST_BEGIN("HENV-27: CBZE reads zero when Zicboz not implemented");

    if (probe_menvcfg_bit(ENVCFG_CBZE))
        TEST_SKIP("Zicboz IS implemented -- test only for non-impl case");

    henvcfg_write(henvcfg_read() | ENVCFG_CBZE);
    TEST_ASSERT_EQ("henvcfg.CBZE reads zero",
                   henvcfg_read() & ENVCFG_CBZE, 0UL);

    HYP_TEST_END();
}

/* ===================================================================
 * HENV-28: DTE reads zero when Ssdbltrp not implemented
 * norm:henvcfg_dte_op
 * =================================================================== */
TEST_REGISTER(henvcfg_28_dte_unimplemented);
bool henvcfg_28_dte_unimplemented(void) {
    TEST_BEGIN("HENV-28: DTE reads zero when Ssdbltrp not implemented");

    if (probe_menvcfg_bit(ENVCFG_DTE))
        TEST_SKIP("Ssdbltrp IS implemented -- test only for non-impl case");

    henvcfg_write(henvcfg_read() | ENVCFG_DTE);
    TEST_ASSERT_EQ("henvcfg.DTE reads zero",
                   henvcfg_read() & ENVCFG_DTE, 0UL);

    HYP_TEST_END();
}

/* ===================================================================
 * HENV-29: ADUE reads zero when Svadu not implemented
 * norm:henvcfg_adue_op
 * =================================================================== */
TEST_REGISTER(henvcfg_29_adue_unimplemented);
bool henvcfg_29_adue_unimplemented(void) {
    TEST_BEGIN("HENV-29: ADUE reads zero when Svadu not implemented");

    if (probe_menvcfg_bit(MENVCFG_ADUE))
        TEST_SKIP("Svadu IS implemented -- test only for non-impl case");

    henvcfg_write(henvcfg_read() | MENVCFG_ADUE);
    TEST_ASSERT_EQ("henvcfg.ADUE reads zero",
                   henvcfg_read() & MENVCFG_ADUE, 0UL);

    HYP_TEST_END();
}
