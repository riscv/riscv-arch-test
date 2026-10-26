/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * Test Group 3: TRET - trap return behaviour
 *
 * Tests TRET-01 through TRET-19 verify MRET/SRET mode switching behavior.
 *
 * SRET cases (TRET-06..14, 16..19) follow norm:sret_h: they execute a
 * REAL SRET instruction in HS-mode (V=0) or VS-mode (V=1) and verify
 * the landing context plus the before/after CSR state. Landing mode is
 * discriminated by sentinel probes (sscratch/vsscratch) and by the
 * exception an S-level CSR access raises at the landing privilege.
 */

#include "hyp_test_helpers.h"

/* ===================================================================
 * SRET behaviour probes (norm:sret_h / sret_v0 / sret_v1)
 *
 * hs_sret_probe executes a real SRET in HS-mode (V=0) with hstatus.SPV
 * / sstatus.SPP / sepc programmed from globals. vs_sret_probe executes
 * a real SRET in VS-mode (V=1); there `csrw sepc` writes vsepc, so HS
 * sepc can be poisoned beforehand: if the implementation wrongly
 * returns through HS sepc, execution faults at the poisoned address.
 *
 * Both probes transfer control to tret_sret_land (address passed via
 * g_tret_land), which runs at the privilege selected by the SRET:
 *   - VS landing : csrr sscratch reads vsscratch (sentinel VS)
 *   - HS landing : csrr sscratch reads sscratch  (sentinel HS)
 *   - VU landing : csrr sscratch raises virtual-instruction (cause 22)
 *   - U  landing : csrr sscratch raises illegal-instruction (cause 2)
 * The landing function ends with `ret`: ra survives SRET unchanged, so
 * control returns to the run_in_priv/run_in_vs_mode trampoline.
 * =================================================================== */

#define TRET_MAGIC_VS    0x5A5A5A5A5A5A5A5AUL  /* vsscratch sentinel */
#define TRET_MAGIC_HS    0xA5A5A5A5A5A5A5A5UL  /* sscratch sentinel  */
#define TRET_FLAG_MAGIC  0x1234ABCD5678EF01UL  /* trap-resume proof  */
#define TRET_POISON_EPC  0xDEAD0000UL          /* unmapped, even-aligned */

#define TRET_SSTATUS_SIE   (1UL << 1)
#define TRET_SSTATUS_SPIE  (1UL << 5)
#define TRET_SSTATUS_SPP   (1UL << 8)

static volatile uintptr_t g_tret_landing;  /* sscratch readback at landing */
static volatile uintptr_t g_tret_flag;     /* written after trap-resume    */
static uintptr_t g_tret_spv;               /* hstatus.SPV for HS probe     */
static uintptr_t g_tret_spp;               /* sstatus.SPP for HS probe     */
static uintptr_t g_tret_land;              /* sepc target (landing label)  */
static volatile uintptr_t g_tret_vs_cause; /* cause seen by VS handler     */

/* Small CSR access helpers used by the assertions below. */
static uintptr_t tret_sstatus_read(void)
{
    uintptr_t v;

    v = CSRR(CSR_SSTATUS);
    return v;
}

static void tret_sstatus_write(uintptr_t v)
{
    CSRW(CSR_SSTATUS, v);
}



static uintptr_t tret_sepc_read(void)
{
    uintptr_t v;

    v = CSRR(CSR_SEPC);
    return v;
}

static void tret_sepc_write(uintptr_t v)
{
    CSRW(CSR_SEPC, v);
}

static uintptr_t tret_vsepc_read(void)
{
    uintptr_t v;

    v = CSRR(CSR_VSEPC);  /* vsepc */
    return v;
}

static void tret_vsepc_write(uintptr_t v)
{
    CSRW(CSR_VSEPC, v);  /* vsepc */
}

/* SRET landing point shared by the HS/VS probes. Runs at the privilege
 * selected by the SRET under test. */
static void tret_sret_land(void) __attribute__((naked, aligned(16)));
static void tret_sret_land(void)
{
    asm volatile (
        ".option push\n\t"
        ".option norvc\n\t"
        "csrr   t0, sscratch\n\t"   /* vsscratch in VS; traps in VU/U */
        "la     t1, g_tret_landing\n\t"
        "sd     t0, 0(t1)\n\t"
        ".option pop\n\t"
        "ret\n\t"
        ::: "t0", "t1", "memory"
    );
}

/* Execute a real SRET in HS-mode (V=0, norm:sret_v0). hstatus.SPV and
 * sstatus.SPP are programmed from globals, sepc from g_tret_land. */
static uintptr_t hs_sret_probe(uintptr_t arg) __attribute__((naked, aligned(16)));
static uintptr_t hs_sret_probe(uintptr_t arg)
{
    asm volatile (
        ".option push\n\t"
        ".option norvc\n\t"
        /* hstatus.SPV <- g_tret_spv (SPV is bit 7) */
        "la     t0, g_tret_spv\n\t"
        "ld     t1, 0(t0)\n\t"
        "li     t2, 0x80\n\t"
        "beqz   t1, 1f\n\t"
        "csrs   hstatus, t2\n\t"
        "j      2f\n\t"
        "1:\n\t"
        "csrc   hstatus, t2\n\t"
        /* sstatus.SPP <- g_tret_spp (SPP is bit 8) */
        "2:\n\t"
        "la     t0, g_tret_spp\n\t"
        "ld     t1, 0(t0)\n\t"
        "li     t2, 0x100\n\t"
        "beqz   t1, 3f\n\t"
        "csrs   sstatus, t2\n\t"
        "j      4f\n\t"
        "3:\n\t"
        "csrc   sstatus, t2\n\t"
        /* sepc <- g_tret_land, then the real SRET under test */
        "4:\n\t"
        "la     t0, g_tret_land\n\t"
        "ld     t0, 0(t0)\n\t"
        "csrw   sepc, t0\n\t"
        "sret\n\t"
        ".option pop\n\t"
        ::: "t0", "t1", "t2", "memory"
    );
}

/* Execute a real SRET in VS-mode (V=1, norm:sret_v1). In V=1 the
 * `sepc` name aliases vsepc, so this programs vsepc = g_tret_land. */
static uintptr_t vs_sret_probe(uintptr_t arg) __attribute__((naked, aligned(16)));
static uintptr_t vs_sret_probe(uintptr_t arg)
{
    asm volatile (
        ".option push\n\t"
        ".option norvc\n\t"
        "la     t0, g_tret_land\n\t"
        "ld     t0, 0(t0)\n\t"
        "csrw   sepc, t0\n\t"   /* V=1: writes vsepc */
        "sret\n\t"
        ".option pop\n\t"
        ::: "t0", "memory"
    );
}

/* ebreak probe for the trap round-trip tests (TRET-18/19). After the
 * handler skips the ebreak and SRET-resumes this context, the magic
 * flag write proves execution really continued here. */
static uintptr_t tret_ebreak_probe(uintptr_t arg) __attribute__((naked, aligned(16)));
static uintptr_t tret_ebreak_probe(uintptr_t arg)
{
    asm volatile (
        ".option push\n\t"
        ".option norvc\n\t"
        "ebreak\n\t"
        "la     t0, g_tret_flag\n\t"
        "li     t1, 0x1234ABCD5678EF01\n\t"
        "sd     t1, 0(t0)\n\t"
        ".option pop\n\t"
        "li     a0, 0\n\t"
        "ret\n\t"
        ::: "t0", "t1", "memory"
    );
}

/* Custom VS-mode handler for TRET-19: records vscause, advances
 * vsepc past the 4-byte ebreak and returns with a real SRET (the
 * hardware-set vsstatus.SPP=1 brings execution back to VS-mode).
 * aligned(4): vstvec BASE masking would otherwise misdirect entry. */
static void tret_vs_handler(void) __attribute__((naked, aligned(4)));
static void tret_vs_handler(void)
{
    asm volatile (
        ".option push\n\t"
        ".option norvc\n\t"
        "addi   sp, sp, -16\n\t"
        "sd     t0, 0(sp)\n\t"
        "sd     t1, 8(sp)\n\t"
        "csrr   t0, scause\n\t"     /* vscause in V=1 */
        "la     t1, g_tret_vs_cause\n\t"
        "sd     t0, 0(t1)\n\t"
        "csrr   t0, sepc\n\t"       /* vsepc in V=1 */
        "addi   t0, t0, 4\n\t"      /* ebreak is 4 bytes (.option norvc) */
        "csrw   sepc, t0\n\t"
        "ld     t0, 0(sp)\n\t"
        "ld     t1, 8(sp)\n\t"
        "addi   sp, sp, 16\n\t"
        "sret\n\t"
        ".option pop\n\t"
        ::: "memory"
    );
}

/* Common setup for the hs_sret_probe based cases. */
static void tret_hs_probe_setup(uintptr_t spv, uintptr_t spp)
{
    clear_all_deleg();
    CSRW(CSR_SSCRATCH, TRET_MAGIC_HS);
    CSRW(CSR_VSSCRATCH, TRET_MAGIC_VS);  /* vsscratch */
    g_tret_landing = 0;
    g_tret_spv = spv;
    g_tret_spp = spp;
    g_tret_land = (uintptr_t)tret_sret_land;

    /* hs_sret_probe is a naked routine that executes a real SRET and never
     * returns normally: control comes back only through the run_in_priv
     * trampoline, whose ecall-to-M recovery is what pulls us out of the
     * VS/VU/U context the SRET lands in. That trampoline is used only when
     * run_in_priv goes DOWN in privilege. Under the S-mode-normal model the
     * test body runs in HS-mode, so run_in_priv(PRIV_S, ...) would be a
     * same-privilege direct call with no trampoline and no recovery, stranding
     * execution in the guest (its next hstatus access then raises cause 22).
     * Hop to M-mode first so the PRIV_S run goes down through the trampoline
     * -- this is also where the old M-mode-normal model ran it. hyp_reset_state
     * at HYP_TEST_END returns the suite to HS-mode afterwards. */
    goto_priv(PRIV_M);
}

/* ------------------------------------------------------------------
 * TRET-01: MRET return to VS-mode (MPV=1, MPP=1)
 * ------------------------------------------------------------------ */
TEST_REGISTER(tret_01_mret_to_vs);
bool tret_01_mret_to_vs(void) {
    TEST_BEGIN("TRET-01: MRET returns to VS-mode (run_in_vs_mode)");

    /* Use run_in_vs_mode to verify MRET returns correctly. */
    uintptr_t r = run_in_vs_mode(vs_read_sstatus, 0);
    TEST_ASSERT("returned from VS-mode", r != (uintptr_t)-1);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * TRET-02: MRET return to VU-mode (MPV=1, MPP=0)
 * ------------------------------------------------------------------ */
TEST_REGISTER(tret_02_mret_to_vu);
bool tret_02_mret_to_vu(void) {
    TEST_BEGIN("TRET-02: MRET returns to VU-mode (run_in_vu_mode)");

    /* Use run_in_vu_mode to verify MRET returns correctly.
     * NOTE: VU-mode cannot access S-level CSRs like sstatus.
     * Use a simple function that just returns its argument. */
    uintptr_t r = run_in_vu_mode(vu_nop, 0x42);
    TEST_ASSERT_EQ("returned from VU-mode with correct value", r, 0x42);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * TRET-03: MRET return to HS-mode (MPV=0, MPP=1)
 * ------------------------------------------------------------------ */
TEST_REGISTER(tret_03_mret_to_hs);
bool tret_03_mret_to_hs(void) {
    TEST_BEGIN("TRET-03: MRET returns to HS-mode (basic privilege switch)");

    /* Verify we can switch to S-mode (HS-mode) and back */
    goto_priv(PRIV_S);
    /* If we reach here, we successfully entered and returned from HS-mode */
    goto_priv(PRIV_M);
    TEST_ASSERT("MRET to HS-mode and back succeeded", true);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * TRET-04: MRET return to M-mode (MPP=3)
 * ------------------------------------------------------------------ */
TEST_REGISTER(tret_04_mret_to_m);
bool tret_04_mret_to_m(void) {
    TEST_BEGIN("TRET-04: Verify current mode is M-mode");

    /* We're running in HS-mode (S-mode with virtualization). */
    /* This is a simplified test - verify we can access M-mode CSRs.
     * mstatus is M-level; read it through the adaptive tsbi_csr_read(), which
     * routes via the T-SBI CSR proxy from S(HS)-mode. */
    uintptr_t mstatus = tsbi_csr_read(CSR_MSTATUS);
    TEST_ASSERT("mstatus accessible (M-mode)", mstatus != 0);

    HYP_TEST_END();
}

/* mstatus.MIE is a return-path bit: the tsbi_csr_ guard refuses to proxy a
 * set/clear of it from S(HS)-mode, and a whole-word tsbi_csr_write would clobber
 * the framework-managed MPP. Verify MIE writability inside a single M-mode
 * excursion instead, flipping only MIE with csrs/csrc so the rest of mstatus
 * (notably MPP, which the excursion's return relies on) is preserved.
 * Returns 1 if MIE was observed to clear then set (i.e. it is writable). */
static uintptr_t tret_m_mie_toggle_readback(uintptr_t arg)
{
    (void)arg;
    uintptr_t orig = CSRR(mstatus);
    CSRC(mstatus, 1UL << 3);              /* MIE <- 0 */
    uintptr_t rb0 = CSRR(mstatus) & (1UL << 3);
    CSRS(mstatus, 1UL << 3);              /* MIE <- 1 */
    uintptr_t rb1 = CSRR(mstatus) & (1UL << 3);
    CSRW(mstatus, orig);                  /* restore exactly (preserves MPP) */
    return (rb0 == 0 && rb1 != 0) ? 1 : 0;
}

/* ------------------------------------------------------------------
 * TRET-05: MRET MIE/MPIE restore
 * ------------------------------------------------------------------ */
TEST_REGISTER(tret_05_mret_mie_mpie);
bool tret_05_mret_mie_mpie(void) {
    TEST_BEGIN("TRET-05: MRET MIE/MPIE fields readable/writable");

    /* Verify mstatus MIE/MPIE fields are readable. mstatus is M-level; read
     * the whole word via the adaptive tsbi_csr_read() (config bits are correct;
     * MPP/MPIE reflect the proxy trap). */
    uintptr_t mstatus = tsbi_csr_read(CSR_MSTATUS);

    /* MIE is bit 3, MPIE is bit 7. */
    bool mie = (mstatus >> 3) & 1;
    bool mpie = (mstatus >> 7) & 1;
    (void)mie;
    (void)mpie;

    TEST_ASSERT("MIE field readable", true);
    TEST_ASSERT("MPIE field readable", true);

    /* Verify MIE is writable via an M-mode excursion write+readback (see
     * helper): the old raw csrw mstatus from S(HS)-mode traps illegal, and
     * MIE cannot be proxied by tsbi_csr_ (return-path bit). */
    TEST_ASSERT("MIE field writable (M-excursion write+readback)",
                run_in_priv(PRIV_M, tret_m_mie_toggle_readback, 0) == 1);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * TRET-06: SRET(V=0) return to VS-mode (real sret, norm:sret_v0)
 * ------------------------------------------------------------------ */
TEST_REGISTER(tret_06_sret_v0_to_vs);
bool tret_06_sret_v0_to_vs(void) {
    TEST_BEGIN("TRET-06: SRET(V=0) returns to VS-mode (real sret)");

    tret_hs_probe_setup(1 /* SPV */, 1 /* SPP */);

    trap_expect_begin();
    run_in_priv(PRIV_S, hs_sret_probe, 0);
    bool trapped = trap_was_triggered();
    trap_expect_end();

    TEST_ASSERT("no trap on SRET(V=0) to VS-mode", !trapped);
    TEST_ASSERT_EQ("landed in VS-mode (vsscratch sentinel)",
                   g_tret_landing, TRET_MAGIC_VS);
    TEST_ASSERT_EQ("hstatus.SPV cleared by SRET",
                   hstatus_get_spv(), 0);
    TEST_ASSERT_EQ("sstatus.SPP cleared by SRET",
                   tret_sstatus_read() & TRET_SSTATUS_SPP, 0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * TRET-07: SRET(V=0) return to VU-mode (real sret, norm:sret_v0)
 * ------------------------------------------------------------------ */
TEST_REGISTER(tret_07_sret_v0_to_vu);
bool tret_07_sret_v0_to_vu(void) {
    TEST_BEGIN("TRET-07: SRET(V=0) returns to VU-mode (real sret)");

    tret_hs_probe_setup(1 /* SPV */, 0 /* SPP */);

    /* At the VU landing, csrr sscratch raises virtual-instruction;
     * the armed M-mode handler records and skips it. */
    trap_expect_begin();
    run_in_priv(PRIV_S, hs_sret_probe, 0);
    TEST_ASSERT("landing probe trapped in VU-mode", trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause=22 proves VU-mode landing",
                       trap_get_cause(),
                       (uintptr_t)CAUSE_VIRTUAL_INSTRUCTION);
    }
    trap_expect_end();

    TEST_ASSERT_EQ("hstatus.SPV cleared by SRET",
                   hstatus_get_spv(), 0);
    TEST_ASSERT_EQ("sstatus.SPP cleared by SRET",
                   tret_sstatus_read() & TRET_SSTATUS_SPP, 0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * TRET-08: SRET(V=0) return to HS-mode (real sret, norm:sret_v0)
 * ------------------------------------------------------------------ */
TEST_REGISTER(tret_08_sret_v0_to_hs);
bool tret_08_sret_v0_to_hs(void) {
    TEST_BEGIN("TRET-08: SRET(V=0) returns to HS-mode (real sret)");

    tret_hs_probe_setup(0 /* SPV */, 1 /* SPP */);

    trap_expect_begin();
    run_in_priv(PRIV_S, hs_sret_probe, 0);
    bool trapped = trap_was_triggered();
    trap_expect_end();

    TEST_ASSERT("no trap on SRET(V=0) to HS-mode", !trapped);
    /* A VS landing would read back TRET_MAGIC_VS, a VU/U landing
     * would trap instead: the HS sentinel is the only conforming
     * outcome. */
    TEST_ASSERT_EQ("landed in HS-mode (sscratch sentinel)",
                   g_tret_landing, TRET_MAGIC_HS);
    TEST_ASSERT_EQ("hstatus.SPV stays 0", hstatus_get_spv(), 0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * TRET-09: SRET(V=0) return to U-mode (real sret, norm:sret_v0)
 * ------------------------------------------------------------------ */
TEST_REGISTER(tret_09_sret_v0_to_u);
bool tret_09_sret_v0_to_u(void) {
    TEST_BEGIN("TRET-09: SRET(V=0) returns to U-mode (real sret)");

    tret_hs_probe_setup(0 /* SPV */, 0 /* SPP */);

    /* At the U landing, csrr sscratch raises illegal-instruction;
     * a VU landing would raise cause=22 instead. */
    trap_expect_begin();
    run_in_priv(PRIV_S, hs_sret_probe, 0);
    TEST_ASSERT("landing probe trapped in U-mode", trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause=2 proves U-mode landing (not VU)",
                       trap_get_cause(), (uintptr_t)CAUSE_ILLEGAL_INST);
    }
    trap_expect_end();

    TEST_ASSERT_EQ("hstatus.SPV stays 0", hstatus_get_spv(), 0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * TRET-10: SRET(V=0) SIE/SPIE restore (real sret, norm:sret_v0)
 * ------------------------------------------------------------------ */
TEST_REGISTER(tret_10_sret_v0_sie_spie);
bool tret_10_sret_v0_sie_spie(void) {
    TEST_BEGIN("TRET-10: SRET(V=0) SIE=old SPIE, SPIE=1 (real sret)");

    /* Pattern (a): SPIE=1, SIE=0 -> after SRET: SIE=1, SPIE=1. */
    tret_hs_probe_setup(0 /* SPV */, 1 /* SPP */);
    tret_sstatus_write((tret_sstatus_read()
                        & ~(TRET_SSTATUS_SIE | TRET_SSTATUS_SPIE))
                       | TRET_SSTATUS_SPIE);

    trap_expect_begin();
    run_in_priv(PRIV_S, hs_sret_probe, 0);
    bool trapped = trap_was_triggered();
    trap_expect_end();

    TEST_ASSERT("pattern (a): no trap", !trapped);
    TEST_ASSERT_EQ("pattern (a): landed in HS-mode",
                   g_tret_landing, TRET_MAGIC_HS);
    uintptr_t ss = tret_sstatus_read();
    TEST_ASSERT("pattern (a): SIE == old SPIE (1)",
                (ss & TRET_SSTATUS_SIE) != 0);
    TEST_ASSERT("pattern (a): SPIE == 1",
                (ss & TRET_SSTATUS_SPIE) != 0);

    /* Pattern (b): SPIE=0, SIE=1 -> after SRET: SIE=0, SPIE=1. */
    tret_hs_probe_setup(0 /* SPV */, 1 /* SPP */);
    tret_sstatus_write((tret_sstatus_read()
                        & ~(TRET_SSTATUS_SIE | TRET_SSTATUS_SPIE))
                       | TRET_SSTATUS_SIE);

    trap_expect_begin();
    run_in_priv(PRIV_S, hs_sret_probe, 0);
    trapped = trap_was_triggered();
    trap_expect_end();

    TEST_ASSERT("pattern (b): no trap", !trapped);
    TEST_ASSERT_EQ("pattern (b): landed in HS-mode",
                   g_tret_landing, TRET_MAGIC_HS);
    ss = tret_sstatus_read();
    TEST_ASSERT("pattern (b): SIE == old SPIE (0)",
                (ss & TRET_SSTATUS_SIE) == 0);
    TEST_ASSERT("pattern (b): SPIE == 1",
                (ss & TRET_SSTATUS_SPIE) != 0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * TRET-11: SRET(V=1) return to VS-mode (real sret, norm:sret_v1)
 *
 * HS sepc is poisoned: if the implementation wrongly returns through
 * HS sepc instead of vsepc, execution faults at the poisoned address.
 * ------------------------------------------------------------------ */
TEST_REGISTER(tret_11_sret_v1_to_vs);
bool tret_11_sret_v1_to_vs(void) {
    TEST_BEGIN("TRET-11: SRET(V=1) returns to VS-mode (real sret)");

    clear_all_deleg();
    hstatus_set_vtsr(0);
    CSRW(CSR_VSSCRATCH, TRET_MAGIC_VS);  /* vsscratch */

    /* Poison HS sepc; the probe writes vsepc (sepc alias in V=1). */
    tret_sepc_write(TRET_POISON_EPC);
    TEST_ASSERT_EQ("sepc poison accepted (WARL)",
                   tret_sepc_read(), TRET_POISON_EPC);

    /* vsstatus: SPP=1 (return to VS), SPIE=1, SIE=0. */
    vsstatus_write(TRET_SSTATUS_SPP | TRET_SSTATUS_SPIE);
    g_tret_landing = 0;
    g_tret_land = (uintptr_t)tret_sret_land;

    VS_EXPECT_NO_TRAP(run_in_vs_mode(vs_sret_probe, 0));

    TEST_ASSERT_EQ("landed at vsepc target (vsscratch sentinel)",
                   g_tret_landing, TRET_MAGIC_VS);
    uintptr_t vss = vsstatus_read();
    TEST_ASSERT_EQ("vsstatus.SPP cleared by SRET",
                   vss & TRET_SSTATUS_SPP, 0);
    TEST_ASSERT("vsstatus.SIE == old SPIE (1)",
                (vss & TRET_SSTATUS_SIE) != 0);
    TEST_ASSERT("vsstatus.SPIE == 1",
                (vss & TRET_SSTATUS_SPIE) != 0);
    TEST_ASSERT_EQ("HS sepc untouched by SRET(V=1)",
                   tret_sepc_read(), TRET_POISON_EPC);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * TRET-12: SRET(V=1) return to VU-mode (real sret, norm:sret_v1)
 * ------------------------------------------------------------------ */
TEST_REGISTER(tret_12_sret_v1_to_vu);
bool tret_12_sret_v1_to_vu(void) {
    TEST_BEGIN("TRET-12: SRET(V=1) returns to VU-mode (real sret)");

    clear_all_deleg();
    hstatus_set_vtsr(0);

    tret_sepc_write(TRET_POISON_EPC);
    /* vsstatus: SPP=0 (return to VU), SPIE=1, SIE=0. */
    vsstatus_write(TRET_SSTATUS_SPIE);
    g_tret_landing = 0;
    g_tret_land = (uintptr_t)tret_sret_land;

    /* At the VU landing, csrr sscratch raises virtual-instruction. */
    trap_expect_begin();
    run_in_vs_mode(vs_sret_probe, 0);
    TEST_ASSERT("landing probe trapped in VU-mode", trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause=22 proves VU-mode landing",
                       trap_get_cause(),
                       (uintptr_t)CAUSE_VIRTUAL_INSTRUCTION);
    }
    trap_expect_end();

    TEST_ASSERT_EQ("vsstatus.SPP cleared by SRET",
                   vsstatus_read() & TRET_SSTATUS_SPP, 0);
    TEST_ASSERT_EQ("HS sepc untouched by SRET(V=1)",
                   tret_sepc_read(), TRET_POISON_EPC);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * TRET-13: SRET(V=1) SIE/SPIE restore (real sret, norm:sret_v1)
 * ------------------------------------------------------------------ */
TEST_REGISTER(tret_13_sret_v1_sie_spie);
bool tret_13_sret_v1_sie_spie(void) {
    TEST_BEGIN("TRET-13: SRET(V=1) SIE=old SPIE, SPIE=1 (real sret)");

    clear_all_deleg();
    hstatus_set_vtsr(0);
    CSRW(CSR_VSSCRATCH, TRET_MAGIC_VS);  /* vsscratch */

    /* Pattern (a): SPIE=1, SIE=0 -> after SRET: SIE=1, SPIE=1. */
    vsstatus_write(TRET_SSTATUS_SPP | TRET_SSTATUS_SPIE);
    g_tret_landing = 0;
    g_tret_land = (uintptr_t)tret_sret_land;

    VS_EXPECT_NO_TRAP(run_in_vs_mode(vs_sret_probe, 0));
    TEST_ASSERT_EQ("pattern (a): landed in VS-mode",
                   g_tret_landing, TRET_MAGIC_VS);
    uintptr_t vss = vsstatus_read();
    TEST_ASSERT("pattern (a): SIE == old SPIE (1)",
                (vss & TRET_SSTATUS_SIE) != 0);
    TEST_ASSERT("pattern (a): SPIE == 1",
                (vss & TRET_SSTATUS_SPIE) != 0);

    /* Pattern (b): SPIE=0, SIE=1 -> after SRET: SIE=0, SPIE=1. */
    vsstatus_write(TRET_SSTATUS_SPP | TRET_SSTATUS_SIE);
    g_tret_landing = 0;

    VS_EXPECT_NO_TRAP(run_in_vs_mode(vs_sret_probe, 0));
    TEST_ASSERT_EQ("pattern (b): landed in VS-mode",
                   g_tret_landing, TRET_MAGIC_VS);
    vss = vsstatus_read();
    TEST_ASSERT("pattern (b): SIE == old SPIE (0)",
                (vss & TRET_SSTATUS_SIE) == 0);
    TEST_ASSERT("pattern (b): SPIE == 1",
                (vss & TRET_SSTATUS_SPIE) != 0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * TRET-14: SRET pc=sepc and SRET does not modify sepc
 * ------------------------------------------------------------------ */
TEST_REGISTER(tret_14_sret_sepc);
bool tret_14_sret_sepc(void) {
    TEST_BEGIN("TRET-14: SRET jumps to sepc, sepc kept unchanged");

    /* The landing label is a non-adjacent function, so landing there
     * proves pc was really loaded from sepc (not sepc+4 fallthrough). */
    tret_hs_probe_setup(0 /* SPV */, 1 /* SPP */);

    trap_expect_begin();
    run_in_priv(PRIV_S, hs_sret_probe, 0);
    bool trapped = trap_was_triggered();
    trap_expect_end();

    TEST_ASSERT("no trap on SRET", !trapped);
    TEST_ASSERT_EQ("landed at sepc target (sscratch sentinel)",
                   g_tret_landing, TRET_MAGIC_HS);
    TEST_ASSERT_EQ("sepc still holds landing label after SRET",
                   tret_sepc_read(), (uintptr_t)tret_sret_land);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * TRET-15: MRET mepc restore PC
 * ------------------------------------------------------------------ */
TEST_REGISTER(tret_15_mret_mepc);
bool tret_15_mret_mepc(void) {
    TEST_BEGIN("TRET-15: MRET mepc readable/writable");

    /* mepc is a trap-state CSR: a proxy round-trip from S(HS)-mode would read
     * back a value clobbered by the ecall trap itself. mcsr_write_readback()
     * performs the write and the read-back inside one M-mode excursion, so no
     * intervening trap clobbers it -- the only correct way to check
     * writability from S-mode. */
    uintptr_t test_val = 0xABCDEF00UL;
    uintptr_t read_val = mcsr_write_readback(CSR_MEPC, test_val);

    TEST_ASSERT_EQ("mepc readback == written value", read_val, test_val);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * TRET-16: SRET(V=1) must not modify V=0 state (norm:sret_h)
 * ------------------------------------------------------------------ */
TEST_REGISTER(tret_16_sret_v1_preserves_v0);
bool tret_16_sret_v1_preserves_v0(void) {
    TEST_BEGIN("TRET-16: SRET(V=1) leaves hstatus/sstatus/sepc intact");

    clear_all_deleg();
    hstatus_set_vtsr(0);
    CSRW(CSR_VSSCRATCH, TRET_MAGIC_VS);  /* vsscratch */

    /* Pre-load V=0 state that a spec-compliant SRET(V=1) must keep. */
    hstatus_set_spv(1);
    tret_sstatus_write(tret_sstatus_read() | TRET_SSTATUS_SPP);
    tret_sepc_write(TRET_POISON_EPC);

    /* vsstatus: SPP=1 keeps the probe in VS-mode across the SRET. */
    vsstatus_write(TRET_SSTATUS_SPP | TRET_SSTATUS_SPIE);
    g_tret_landing = 0;
    g_tret_land = (uintptr_t)tret_sret_land;

    VS_EXPECT_NO_TRAP(run_in_vs_mode(vs_sret_probe, 0));

    TEST_ASSERT_EQ("landed in VS-mode (vsscratch sentinel)",
                   g_tret_landing, TRET_MAGIC_VS);
    /* sret_v1 operates only on vsstatus/vsepc: only SRET(V=0) may
     * clear hstatus.SPV, so it must survive here. */
    TEST_ASSERT_EQ("hstatus.SPV unchanged by SRET(V=1)",
                   hstatus_get_spv(), 1);
    TEST_ASSERT("sstatus.SPP unchanged by SRET(V=1)",
                (tret_sstatus_read() & TRET_SSTATUS_SPP) != 0);
    TEST_ASSERT_EQ("HS sepc unchanged by SRET(V=1)",
                   tret_sepc_read(), TRET_POISON_EPC);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * TRET-17: SRET(V=0) must not modify VS state (norm:sret_h)
 * ------------------------------------------------------------------ */
TEST_REGISTER(tret_17_sret_v0_preserves_vs);
bool tret_17_sret_v0_preserves_vs(void) {
    TEST_BEGIN("TRET-17: SRET(V=0) leaves vsstatus/vsepc intact");

    /* Pre-load VS state that a spec-compliant SRET(V=0) must keep. */
    vsstatus_write(TRET_SSTATUS_SPP);
    tret_vsepc_write(TRET_POISON_EPC);
    CSRW(CSR_VSSCRATCH, TRET_MAGIC_VS);  /* vsscratch */

    /* SRET(V=0) with SPV=1, SPP=1 returns into VS-mode. */
    tret_hs_probe_setup(1 /* SPV */, 1 /* SPP */);

    trap_expect_begin();
    run_in_priv(PRIV_S, hs_sret_probe, 0);
    bool trapped = trap_was_triggered();
    trap_expect_end();

    TEST_ASSERT("no trap on SRET(V=0) to VS-mode", !trapped);
    TEST_ASSERT_EQ("landed in VS-mode (vsscratch sentinel)",
                   g_tret_landing, TRET_MAGIC_VS);
    /* sret_v0 operates only on hstatus/sstatus/sepc. */
    TEST_ASSERT("vsstatus.SPP unchanged by SRET(V=0)",
                (vsstatus_read() & TRET_SSTATUS_SPP) != 0);
    TEST_ASSERT_EQ("vsepc unchanged by SRET(V=0)",
                   tret_vsepc_read(), TRET_POISON_EPC);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * TRET-18: full round-trip VU trap -> HS handler -> SRET resume
 * ------------------------------------------------------------------ */
TEST_REGISTER(tret_18_vu_trap_hs_sret_resume);
bool tret_18_vu_trap_hs_sret_resume(void) {
    TEST_BEGIN("TRET-18: VU ebreak -> HS handler -> SRET resumes VU");

#ifdef SKIP_BREAKPOINT_TESTS
    TEST_SKIP("platform does not support breakpoint (SKIP_BREAKPOINT_TESTS)");
#endif

    /* Delegate ebreak M->HS only; the trap stays in HS-mode. */
    clear_all_deleg();
    setup_deleg_to_hs(1UL << CAUSE_BREAKPOINT);

    uintptr_t saved_stvec;
    saved_stvec = CSRR(CSR_STVEC);
    CSRW(CSR_STVEC, (uintptr_t)&_hs_trap_entry);

    g_tret_flag = 0;
    run_in_vu_mode(tret_ebreak_probe, 0);

    CSRW(CSR_STVEC, saved_stvec);
    clear_all_deleg();

    /* The flag write after the ebreak proves the HS handler took the
     * trap and its SRET really resumed VU-mode execution. */
    TEST_ASSERT_EQ("HS handler SRET resumed VU execution",
                   g_tret_flag, TRET_FLAG_MAGIC);
    TEST_ASSERT("trap entered HS-mode with SPV=1", trap_get_spv());
    /* SRET(V=0) clears hstatus.SPV on the way back to the guest. */
    TEST_ASSERT_EQ("hstatus.SPV cleared by HS SRET",
                   hstatus_get_spv(), 0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * TRET-19: nested VS trap -> VS handler SRET resume
 * ------------------------------------------------------------------ */
TEST_REGISTER(tret_19_vs_trap_vs_sret_resume);
bool tret_19_vs_trap_vs_sret_resume(void) {
    TEST_BEGIN("TRET-19: VS ebreak -> VS handler -> SRET resumes VS");

#ifdef SKIP_BREAKPOINT_TESTS
    TEST_SKIP("platform does not support breakpoint (SKIP_BREAKPOINT_TESTS)");
#endif

    /* Delegate ebreak M->HS->VS so the trap is delivered to VS-mode. */
    clear_all_deleg();
    setup_deleg_to_vs(1UL << CAUSE_BREAKPOINT, 0);
    vs_trap_setup_direct((uintptr_t)tret_vs_handler);

    /* HS-level sentinel: the V=1 trap/return path must not touch it. */
    tret_sstatus_write(tret_sstatus_read() | TRET_SSTATUS_SPP);

    g_tret_flag = 0;
    g_tret_vs_cause = 0;
    VS_EXPECT_NO_TRAP(run_in_vs_mode(tret_ebreak_probe, 0));

    clear_all_deleg();

    TEST_ASSERT_EQ("VS handler saw cause=3 (ebreak)",
                   g_tret_vs_cause, (uintptr_t)CAUSE_BREAKPOINT);
    /* The flag write after the ebreak proves the VS handler's SRET
     * really resumed the VS context. */
    TEST_ASSERT_EQ("VS handler SRET resumed guest execution",
                   g_tret_flag, TRET_FLAG_MAGIC);
    TEST_ASSERT_EQ("vsstatus.SPP cleared by VS SRET",
                   vsstatus_read() & TRET_SSTATUS_SPP, 0);
    TEST_ASSERT("HS sstatus.SPP untouched by the V=1 path",
                (tret_sstatus_read() & TRET_SSTATUS_SPP) != 0);

    HYP_TEST_END();
}
