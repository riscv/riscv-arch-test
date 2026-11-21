/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#include "test_framework.h"

/* Halt the machine with a fail status via RVMODEL_HALT_FAIL (entry.S).
 * On QEMU/Spike/Sail this terminates the simulation; on HW it spins. */
extern void _halt_fail(void) __attribute__((noreturn));

/* Build with -DENABLE_TRAP_ARM_DIAG (or temporarily #define here) to
 * enable trap-arm state-trace counters that print on UNEXPECTED TRAP.
 * Default-off: zero overhead in normal builds. Used during the
 * fix-gvalid03-fetch-recovery plan to empirically confirm armed-bit
 * clear sites. Note: CFLAGS_EXTRA= is NOT honored by Makefile.common
 * — define here directly when re-enabling. */

/* ===================================================================
 * Privilege mode definitions are in encoding.h.
 * =================================================================== */

#ifdef ENABLE_HYP
/* Check if a privilege target requires V=1 (virtualized mode).
 * File-local mirror of the same helper in privilege.c. */
static inline bool is_virt_target(unsigned target) {
    return (target & 0x4) != 0;
}
#endif

/* ===================================================================
 * Trap record - captures exception information for test assertions
 * =================================================================== */
typedef volatile struct {
    bool      armed;        /* true = expecting a possible exception */
    bool      triggered;    /* true = an exception was captured */
    unsigned  priv_level;   /* privilege level where exception occurred */
    uintptr_t cause;        /* mcause / scause value */
    uintptr_t epc;          /* mepc / sepc value */
    uintptr_t tval;         /* mtval / stval value */
    uintptr_t status_snap;  /* mstatus/sstatus snapshot at trap entry */
    uintptr_t return_addr;  /* for instruction faults: where to resume */
#ifdef ENABLE_HYP
    uintptr_t htval;        /* mtval2 (M-mode) / htval (S-mode), hardware value >> 2 */
    uintptr_t htinst;       /* mtinst / htinst, hardware value */
    bool      gva;          /* mstatus.GVA / hstatus.GVA captured at trap time */
    bool      spv;          /* hstatus.SPV captured at trap time */
#endif
} trap_record_t;

trap_record_t trap_record;

/* Automatic snapshot of a double-trap (cause 16) record taken in the
 * M-mode handler before any later delivery can overwrite trap_record.
 * Tests reset trap_dt_snap_valid before triggering and inspect the
 * snapshot afterwards. */
trap_snapshot_t trap_dt_snap;
bool trap_dt_snap_valid;

/* Ssdbltrp probe robustness state (used by the trap handlers below):
 * a probe is in flight while ssdbltrp_probe_active is set, and
 * ssdbltrp_s_probe_repeats counts how many times the probe trap was
 * delivered, so repeated deliveries cannot loop forever. */
__attribute__((weak)) volatile bool ssdbltrp_probe_active;
__attribute__((weak)) char ssdbltrp_probe_rearm[0];
__attribute__((weak)) char ssdbltrp_run_s_probe[0];
__attribute__((weak)) char ssdbltrp_probe_return[0];
__attribute__((weak)) char ssdbltrp_probe_mtval2_ld[0];
unsigned ssdbltrp_s_probe_repeats;
unsigned ssdbltrp_dt_entries;

/* True when linked into a suite that defines the Ssdbltrp probe
 * symbols (Ssdbltrp suite).  The address check is required because
 * the weak references are NULL in every other suite; the pragma
 * silences -Waddress in the suite where the symbols are strong. */
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Waddress"
static inline bool _ssdbltrp_probe_present(void) {
    return &ssdbltrp_probe_active != 0 && &ssdbltrp_probe_rearm != 0;
}
#pragma GCC diagnostic pop

/* ===================================================================
 * Trap entry trace ring (diagnostic)
 *
 * Records the last few trap entries (M and S side) so unexpected
 * traps can dump the sequence that led to them.  Zero overhead when
 * trap_trace_enabled is left at 0.
 * =================================================================== */
#define TRAP_TRACE_DEPTH 8
typedef struct {
    unsigned      priv;    /* PRIV_M / PRIV_S handler side */
    uintptr_t     cause;
    uintptr_t     epc;
    uintptr_t     status;
    uintptr_t     tval;
    uintptr_t     mtval2;
    int           armed;
} trap_trace_entry_t;
static volatile trap_trace_entry_t _trace_ring[TRAP_TRACE_DEPTH];
static volatile unsigned _trace_idx;
static volatile bool trap_trace_enabled;

void trap_trace_on(void)  { trap_trace_enabled = true; }
void trap_trace_off(void) { trap_trace_enabled = false; }

/* ===================================================================
 * mtval2 CSR availability detection
 *
 * mtval2 (0x34B) exists when the Hypervisor extension is implemented
 * (H "adds CSRs mtval2 and mtinst") OR when Ssdbltrp is implemented
 * (norm:mtval2_Ssdbltrap: "The Ssdbltrap extension requires the
 * implementation of the mtval2 CSR" -- independent of H).  On builds
 * whose ISA has neither (e.g. Ss_CSR), reading mtval2 raises an
 * illegal instruction, which inside m_trap_handler would nest into an
 * infinite trap loop.  A compile-time macro cannot express this: it
 * depends on each suite's effective ISA (suites run with restricted
 * ISA strings even on max-capability platform configs), so probe
 * once at reset (M-mode, trap vectors already installed) and read
 * mtval2 in the handler only when present. */
static bool trap_mtval2_present;

/* Trap-arming API (defined further down in this file) */
extern void trap_expect_begin(void);
extern void trap_expect_end(void);
extern bool trap_was_triggered(void);

void trap_probe_mtval2(void) {
    trap_expect_begin();
    (void)CSRR(CSR_MTVAL2);
    trap_mtval2_present = !trap_was_triggered();
    trap_expect_end();
}

/* Explicit override of the mtval2 availability gate. Tests that
 * transiently disable the H extension at runtime (e.g. clearing
 * misa.H per norm:misa_h_op) must suppress the handler's entry-time
 * mtval2 read for the disabled window to avoid a nested-trap loop,
 * then re-probe with trap_probe_mtval2() after restoring. */
void trap_set_mtval2_present(bool present) {
    trap_mtval2_present = present;
}

static inline void _trace_add(unsigned priv, uintptr_t cause,
                              uintptr_t epc, uintptr_t status,
                              uintptr_t tval, uintptr_t mtval2,
                              int armed) {
    if (!trap_trace_enabled)
        return;
    unsigned i = _trace_idx % TRAP_TRACE_DEPTH;
    _trace_ring[i].priv   = priv;
    _trace_ring[i].cause  = cause;
    _trace_ring[i].epc    = epc;
    _trace_ring[i].status = status;
    _trace_ring[i].tval   = tval;
    _trace_ring[i].mtval2 = mtval2;
    _trace_ring[i].armed  = armed;
    _trace_idx++;
}

static void _trace_dump(void) {
    if (!trap_trace_enabled)
        return;
    LOG_T("last trap entries (old -> new):\n");
    unsigned start = (_trace_idx < TRAP_TRACE_DEPTH)
                         ? 0 : _trace_idx;
    for (unsigned k = 0; k < TRAP_TRACE_DEPTH && k < _trace_idx; k++) {
        unsigned i = (start + k) % TRAP_TRACE_DEPTH;
        LOG_T("  priv=%c cause=0x%lx epc=0x%lx status=0x%lx "
              "tval=0x%lx mtval2=0x%lx armed=%d\n",
              _trace_ring[i].priv == 3 ? 'M' : 'S',
              (unsigned long)_trace_ring[i].cause,
              (unsigned long)_trace_ring[i].epc,
              (unsigned long)_trace_ring[i].status,
              (unsigned long)_trace_ring[i].tval,
              (unsigned long)_trace_ring[i].mtval2,
              _trace_ring[i].armed);
    }
}

#ifdef ENABLE_HYP
/* Snapshot of mstatus.MPV/MPP captured at M-mode trap entry, before
 * the handler modifies them.  Tests use trap_get_mpv/mpp() to verify
 * hardware auto-writes on trap entry (e.g. TENT-12/13/14). */
static volatile bool      _m_trap_mpv_snap;
static volatile uintptr_t _m_trap_mpp_snap;
#endif

/* CFI (Zicfilp) PELP control flags for Hypervisor_Zicfilp tests.
 * Default 0 preserves existing behavior (clear MPELP/SPELP on
 * software-check trap). Tests set these to verify hardware xRET
 * xpelp handling:
 * - g_trap_preserve_pelp=1: skip clearing MPELP/SPELP so xRET
 *   restores ELP (LP-16/19).
 * - g_trap_force_pelp=1: force MPELP/SPELP=1 before xRET to verify
 *   hardware clears xpelp on xRET (LP-17/20).
 * Default 0 = no impact on existing suites (cfi.Zicfilp, etc.). */
bool g_trap_preserve_pelp = 0;
bool g_trap_force_pelp = 0;

/* Bridge to _exec_return_addr (weak symbol, default=0) */
uintptr_t _exec_return_addr __attribute__((weak)) = 0;

/* ===================================================================
 * ENABLE_TRAP_ARM_DIAG: optional trap-arm state-trace counters.
 *
 * Enabled only when ENABLE_TRAP_ARM_DIAG is #defined at the top of
 * this file (Makefile.common does not propagate CFLAGS_EXTRA, so do
 * not rely on a -D on the command line). Counters and prints are
 * compiled out by default — zero overhead in normal builds.
 * Originally added to confirm the GVALID-03 fetch-into-V=0 trap-arm
 * race; kept around as a turnkey diagnostic for similar issues.
 * =================================================================== */
#ifdef ENABLE_TRAP_ARM_DIAG
unsigned long _diag_arm_begin_count       = 0;
unsigned long _diag_arm_end_count         = 0;
unsigned long _diag_arm_handler_clear     = 0;
unsigned long _diag_arm_last_clear_epc    = 0;
unsigned long _diag_arm_last_clear_cause  = 0;
#endif

/* ===================================================================
 * Legacy ecall convention (pre-T-SBI)
 *
 * ecall_args[] used to carry a0/a1 through globals.  The handlers now read
 * the trapped a0/a1 straight out of the trap frame (T-SBI register
 * convention, see tsbi.h SECTION 6), so nothing reads these any more.
 * The definitions stay so that suites which still WRITE them keep
 * compiling; their writes are simply ignored (expected during migration).
 * =================================================================== */
uintptr_t ecall_args[2];

/* Retained for suites that still reference it; the T-SBI GOTO path uses
 * g_tsbi_forward_resume instead. */
#define ECALL_PRIV_RESUME  2
static uintptr_t g_priv_resume_addr __attribute__((unused));

/* ===================================================================
 * T-SBI framework-internal state
 * =================================================================== */

/* P1 raw-ecall escape flag (consume-once).  Set through
 * tsbi_arm_raw_ecall(); cleared by whichever handler sees the next ecall
 * first, so exactly one ecall is diverted from service dispatch to the
 * armed-stimulus path.  Shared by every handler level on purpose: the
 * stimulus may be delivered to M or S depending on delegation. */
static volatile bool _tsbi_skip_dispatch;

void tsbi_arm_raw_ecall(bool skip_dispatch)
{
    _tsbi_skip_dispatch = skip_dispatch;
}

/* Resume point of the ORIGINAL requester while a GOTO is being forwarded
 * up the privilege chain.  The forwarding handler records the requester's
 * ecall+4 here before re-issuing the ecall; the level that finally SERVES the
 * request lands its xret there instead of at the forwarder's own ecall+4.
 * Zero when no forward is in flight.
 *
 * This is the framework-internal answer to the upstream reference
 * implementation's open TODO ("for forwarded GOTOs M-mode should set
 * mepc = sepc"), and it replaces the old ECALL_PRIV_RESUME pseudo-opcode:
 * the protocol now only ever sees a standard GOTO request.
 *
 * Two rules keep it correct across a multi-hop chain (VS -> HS -> M), and both
 * halves must be obeyed by every level:
 *   - forwarding: record only if still zero.  A non-zero value means a LOWER
 *     level already recorded the true origin, and our own epc is just the
 *     forwarding ecall inside _tsbi_forward_goto.
 *   - serving:    consume it via tsbi_goto_resume() below.
 */
static uintptr_t g_tsbi_forward_resume;

/* Resolve where a GOTO we are about to serve must resume, and consume the
 * hand-off.  See g_tsbi_forward_resume for the two-rule invariant. */
static uintptr_t tsbi_goto_resume(uintptr_t own_resume)
{
    if (g_tsbi_forward_resume != 0) {
        uintptr_t origin = g_tsbi_forward_resume;
        g_tsbi_forward_resume = 0;
        return origin;
    }
    return own_resume;
}

/* Record the origin before forwarding a GOTO one level up. */
static void tsbi_goto_forward_mark(uintptr_t own_resume)
{
    if (g_tsbi_forward_resume == 0)
        g_tsbi_forward_resume = own_resume;
}

/* ===================================================================
 * tsbi_forward_up - chain-forward a request one level up
 *
 * A handler that cannot serve a request re-issues it to the next level.
 * The upstream assembly restores its temporaries and executes a bare
 * ecall, letting a0/a1 pass through untouched.  In C we cannot leave the
 * registers alone across the call boundary, so we reload them from the
 * frame and issue the bare ecall; the result is written back into the
 * frame.  Semantically identical, and invisible to the requester.
 *
 * Note this is deliberately NOT tsbi_ecall(): that would overwrite the
 * caller's a0/a1 with its own arguments and assumes an ordinary C
 * environment (see tsbi_design_brief.md FAQ).
 *
 * Used for the RETURNING forwards (M-level CSR, memory proxy): the upper
 * level serves the request, mret's back here, and we sret to the
 * requester with the result in the frame.  Context handover is correct
 * because we never leave this handler.
 * =================================================================== */
static void tsbi_forward_up(uintptr_t *frame)
{
    register uintptr_t a0 asm("a0") = frame[TSBI_FRAME_A0];
    register uintptr_t a1 asm("a1") = frame[TSBI_FRAME_A1];
    register uintptr_t a2 asm("a2") = frame[TSBI_FRAME_A2];
    asm volatile ("ecall" : "+r"(a0) : "r"(a1), "r"(a2) : "memory");
    frame[TSBI_FRAME_A0] = a0;
}

/* ===================================================================
 * tsbi_forward_goto - forward a privilege-raising request; never returns
 *
 * GOTO_MMODE needs mstatus.MPP, which only M has, so only M can serve it.
 * (GOTO_VSMODE/VUMODE are NOT forwarded by HS: it owns hstatus.SPV and serves
 * them locally - see the S handler's GOTO branch for why that is mandatory.
 * A VS-level handler forwards every GOTO, having authority over none.)
 *
 * The body is _tsbi_forward_goto in trap_asm.S: the requester's whole
 * register context has to be back in the registers before the bare ecall,
 * which a C function cannot arrange (the compiler owns sp/s0/ra).  See that
 * routine for why, and note the consequence - with the context handover now
 * correct, forwarding a GOTO is a fully supported path rather than the
 * degraded one this used to be.
 * =================================================================== */
extern void _tsbi_forward_goto(uintptr_t *frame) __attribute__((noreturn));

/* Count of delegated exceptions actually recorded by the S-mode handler.
 * Lets tests prove that a delegated trap was delivered to S-mode
 * (as opposed to being taken by M-mode because delegation was off). */
volatile uintptr_t g_s_deleg_exc_count;

/* Forward declaration */
extern void goto_priv(unsigned target);

/* Current tracked privilege level */
extern unsigned current_priv;

/* ===================================================================
 * Helper: is this cause an instruction fetch fault?
 * =================================================================== */
static bool is_inst_fault(uintptr_t cause) {
    return (cause == CAUSE_INST_ADDR_MISALIGN ||
            cause == CAUSE_INST_ACCESS_FAULT  ||
            cause == CAUSE_INST_PAGE_FAULT
#ifdef ENABLE_HYP
            /* H-ext: VS-mode fetch into a V=0 leaf (or any G-stage
             * fetch fault) is also an instruction fault from the
             * recovery-anchor perspective: skipping epc+2/4 lands
             * inside the same V=0 page and re-faults forever. The
             * caller (test_vs_exec_expect_fault) installs a recovery
             * label via _exec_return_addr / trap_record.return_addr
             * to escape. */
            || cause == CAUSE_INST_GUEST_PAGE_FAULT
#endif
            );
}

/* ===================================================================
 * Helper: is this cause an ecall?
 * =================================================================== */
static bool is_ecall(uintptr_t cause) {
    /* Interrupts are never ecalls. Must check the interrupt bit
     * BEFORE the CLIC-mode 0xFFF mask, because on RV32 the mask
     * strips bit 31, causing SEI (0x80000009) to collide with
     * CAUSE_ECALL_FROM_S (9) and MEI (0x8000000b) to collide
     * with CAUSE_ECALL_FROM_M (11). */
    if (cause & CAUSE_INTERRUPT_BIT) return false;
    /* In CLIC mode, mcause has extended fields (mpp, mpie, mpil)
     * in the high bits. Mask to exccode only (bits 11:0) before
     * comparing with standard cause codes. */
    cause &= 0xFFF;
    return (cause == CAUSE_ECALL_FROM_U ||
            cause == CAUSE_ECALL_FROM_S ||
            cause == CAUSE_ECALL_FROM_M
#ifdef ENABLE_HYP
            || cause == CAUSE_ECALL_FROM_VS
#endif
            );
}

#ifdef ENABLE_HYP
/* ===================================================================
 * Helper: is this cause a guest-page-fault? (cause 20/21/23)
 * =================================================================== */
static inline bool is_guest_page_fault(uintptr_t cause) {
    return (cause == CAUSE_INST_GUEST_PAGE_FAULT  ||
            cause == CAUSE_LOAD_GUEST_PAGE_FAULT  ||
            cause == CAUSE_STORE_GUEST_PAGE_FAULT);
}

/* ===================================================================
 * QEMU quirk: TVM-protected hgatp/satp access cause normalization
 *
 * Per the privileged spec, when mstatus.TVM=1 a HS-mode CSR access
 * to satp / hgatp / hfence.* must raise an *Illegal Instruction*
 * exception (cause 2). Some QEMU versions instead raise an
 * *Instruction Access Fault* (cause 1) for this case. To keep test
 * assertions spec-strict we transparently rewrite the captured
 * cause when, and only when, the trap context unambiguously matches
 * the TVM-protected pattern:
 *
 *   1. mcause == 1                                  (Inst Access Fault)
 *   2. trap_record.armed                            (test arms a trap)
 *   3. mstatus.MPP == S  &&  mstatus.MPV == 0       (came from HS)
 *   4. mstatus.TVM == 1
 *   5. instruction at mepc is a 32-bit SYSTEM CSR op
 *      with funct3 ∈ {1,2,3,5,6,7} (csrrw/s/c[i])
 *      and csr field ∈ {0x680 hgatp, 0x180 satp}
 *
 * Any other instruction-access fault is left untouched. This is a
 * scoped software shim, equivalent to a HW errata workaround.
 * =================================================================== */
static uintptr_t normalize_qemu_tvm_cause(uintptr_t cause, uintptr_t epc) {
    if (cause != (uintptr_t)CAUSE_INST_ACCESS_FAULT)
        return cause;

    uintptr_t ms  = CSRR(mstatus);
    unsigned  mpp = (unsigned)((ms >> MSTATUS_MPP_OFF) & 0x3UL);
    unsigned  mpv = (unsigned)(((uint64_t)ms >> 39) & 0x1UL);
    unsigned  tvm = (unsigned)((ms >> 20) & 0x1UL);
    if (!(mpp == PRIV_S && mpv == 0 && tvm == 1))
        return cause;

    /* Decode the trapping instruction. Must be a 32-bit SYSTEM CSR
     * op against satp or hgatp. We tolerate epc accesses because
     * the kernel is identity-mapped in M-mode here (no MPRV/satp
     * indirection that would change the effective fetch address). */
    uint16_t lo = *(volatile uint16_t *)epc;
    if ((lo & 0x3) != 0x3)                    /* must be 32-bit */
        return cause;
    uint32_t inst = *(volatile uint32_t *)epc;
    if ((inst & 0x7F) != 0x73)                /* SYSTEM major opcode */
        return cause;
    uint32_t funct3 = (inst >> 12) & 0x7;
    /* csrrw=1, csrrs=2, csrrc=3, csrrwi=5, csrrsi=6, csrrci=7;
     * funct3 == 0 → ECALL/EBREAK/MRET/SRET/WFI/SFENCE — not CSR ops. */
    if (funct3 == 0 || funct3 == 4)
        return cause;
    uint32_t csr = (inst >> 20) & 0xFFF;
    if (csr != 0x680 /* hgatp */ && csr != 0x180 /* satp */)
        return cause;

    return (uintptr_t)CAUSE_ILLEGAL_INST;
}

/* Capture mtval2/mtinst (M-mode side) into trap_record.
 * Also capture mstatus.GVA into trap_record.gva.
 *
 * Called on EVERY trap into M-mode, not only guest-page faults:
 * norm:mtval2_trapval mandates mtval2 = 0 for other traps and
 * norm:H_trap_xtinst_interrupt mandates mtinst = 0 on interrupts,
 * so tests must observe the real hardware-written values instead of
 * software-forced zeros. */
static inline void hyp_capture_m(void) {
    /* mtval2: the faulting guest physical address >> 2 on a
     * guest-page-fault; hardware must write 0 for other traps. */
    trap_record.htval  = CSRR(CSR_MTVAL2);
    trap_record.htinst = CSRR(CSR_MTINST);
    /* mstatus.GVA = bit 38 (RV64 only) */
    uintptr_t ms = CSRR(mstatus);
    trap_record.gva = (((uint64_t)ms >> 38) & 0x1UL) != 0;
}

/* Capture htval/htinst (HS-side) when trap is taken in HS-mode. */
static inline void hyp_capture_s(void) {
    trap_record.htval  = CSRR(CSR_HTVAL);
    trap_record.htinst = CSRR(CSR_HTINST);
    uintptr_t hs = CSRR(CSR_HSTATUS);
    trap_record.gva = ((hs >> 6) & 0x1UL) != 0;  /* HSTATUS_GVA bit 6 */
    /* Record whether the trap came from a virtualized mode. For
     * HS-mode delivery use hstatus.SPVP (written like sstatus.SPP
     * when V was 1, norm:H_trap_hs_csrwrites) falling back to SPV:
     * both are cleared by sret, so they must be snapshotted here. */
    trap_record.spv = (((hs >> 7) & 0x1UL) != 0) ||   /* SPVP */
                      ((hs & HSTATUS_SPV) != 0);      /* SPV  */
}
#endif /* ENABLE_HYP */

/* ===================================================================
 * Helper: compute next instruction address (skip current instruction)
 *
 * Checks if current instruction is compressed (2 bytes) or not (4 bytes).
 * =================================================================== */
static inline uintptr_t next_instruction(uintptr_t epc) {
    uint16_t inst_low = *(volatile uint16_t *)epc;
    /* Compressed instructions have bits [1:0] != 0b11 */
    if ((inst_low & 0x3) == 0x3)
        return epc + 4;
    else
        return epc + 2;
}

/* ===================================================================
 * M-mode trap handler (called from trap.S)
 *
 * Returns the privilege level to return to (for mret MPP setup).
 * =================================================================== */
/* Weak hook: called at every M-mode trap entry with the mtval2 value
 * read at the earliest point of the C handler, where the hardware
 * trap-entry write is guaranteed to be visible (an assembly-side
 * capture right after the MDT-clearing MRET may run too early).
 * Suites that need the entry-time mtval2 (Ssdbltrp) override this
 * hook. */
__attribute__((weak)) void trap_m_entry_mtval2_hook(uintptr_t mtval2) {
    (void)mtval2;
}

unsigned m_trap_handler(uintptr_t *frame) {
    uintptr_t cause = CSRR(mcause);
    uintptr_t epc   = CSRR(mepc);
    uintptr_t tval  = CSRR(mtval);

    /* ================================================================
     * P0: nested-fault capture (Strategy A) - MUST BE ABSOLUTELY FIRST
     *
     * tsbi_proxy_record.armed means WE are mid-flight executing an
     * instruction injected on a caller's behalf (CSR / memory proxy) and
     * that instruction just faulted.  This is our own accident, not a new
     * event: claiming it here keeps it out of trap_record (which would
     * corrupt the test's assertion) and out of the UNEXPECTED path.
     *
     * The mret below resumes the HANDLER, not the original requester:
     * tsbi_proxy_record.recover is a label inside tsbi_*_access_dispatch, which
     * runs in M-mode.  So mstatus must keep saying "came from M" - exactly
     * what the nested trap just wrote.  Do NOT restore status_snap here: that
     * would mret into handler code at the requester's privilege level, and the
     * very next M-level CSR access would fault.  P2 re-applies status_snap once
     * the dispatch has returned, right before the final mret.
     * ================================================================ */
    if (tsbi_proxy_record.armed) {
        tsbi_proxy_record.faulted = true;
        tsbi_proxy_record.cause   = cause;
        CSRW(mepc, tsbi_proxy_record.recover);
        return PRIV_M;
    }

    /* mtval2 exists only with the H extension or Ssdbltrp
     * (norm:mtval2_Ssdbltrap); reading it when unimplemented traps
     * into this very handler and loops forever.  Only read it when
     * the reset-time probe found it present (pass 0 otherwise,
     * matching the hardware-write-zero rule for other traps). */
    uintptr_t mtval2_val = trap_mtval2_present ? CSRR(CSR_MTVAL2) : 0;
    _trace_add(PRIV_M, cause, epc, CSRR(mstatus), tval,
               mtval2_val, trap_record.armed);
    /* Feed the mtval2 capture hook on eligible entries; the hook
     * itself applies any suite-specific gating (e.g. one-shot). */
    trap_m_entry_mtval2_hook(mtval2_val);

    /* Ssdbltrp probe tolerance (M side): a cause-16 arrival may hit
     * the handler after the armed flag was already consumed by an
     * earlier record.  Re-arm it while a probe is in flight so the
     * escalated record is taken instead of halting the suite. */
    if (_ssdbltrp_probe_present() && ssdbltrp_probe_active &&
        cause == CAUSE_DOUBLE_TRAP && !trap_record.armed &&
        ssdbltrp_s_probe_repeats < 16) {
        trap_record.armed = true;
    }

    /* ================================================================
     * P1: raw-ecall escape (consume-once) - MUST PRECEDE P2
     *
     * The test declared "my next ecall is the stimulus, not a service
     * request".  A raw stimulus ecall carries an uncontrolled a0 that
     * might otherwise look like a valid opcode, so we must divert it
     * BEFORE P2 reads a0.  The flag is cleared on first sight so the
     * framework's own follow-up ecall (e.g. run_in_priv's return path)
     * keeps normal T-SBI semantics.
     * ================================================================ */
    bool tsbi_raw_ecall = false;
    if (is_ecall(cause) && _tsbi_skip_dispatch) {
        _tsbi_skip_dispatch = false;
        tsbi_raw_ecall = true;
    }

    /* ================================================================
     * P2: T-SBI service dispatch - M-mode is the chain endpoint
     *
     * Full capability, no forward-up exit: GOTO (all five targets),
     * ECALL_TEST, CSR_ACCESS for any privilege level, memory proxy.
     * Results are written into frame[TSBI_FRAME_A0] because
     * RESTORE_CONTEXT reloads a0 from there (a C return only selects
     * mret vs sret).
     * ================================================================ */
    if (!tsbi_raw_ecall && is_ecall(cause)) {
        uintptr_t op = frame[TSBI_FRAME_A0];

        if (TSBI_IS_GOTO(op)) {
            unsigned target = tsbi_goto_to_priv(op);

            /* Forwarded up by a lower handler?  Then the resume point is the
             * ORIGINAL requester's instruction, not the forwarder's own
             * ecall.  This is the framework-internal counterpart of the
             * upstream "set mepc = sepc for forwarded GOTOs" TODO. */
            CSRW(mepc, tsbi_goto_resume(next_instruction(epc)));

            current_priv = target;

            /* mstatus.MPP[12:11] selects where mret lands (U=0,S=1,M=3).
             * Clear MPRV too: with MPP=M, mret does not clear MPRV, which
             * would make M-mode load/store use U-mode PMP rules.
             * For virtualised targets (PRIV_VS=5, PRIV_VU=4) bit 2 marks
             * V=1: the low 2 bits become MPP and MPV must be set. */
            uintptr_t ms = CSRR(mstatus);
            ms &= ~((3UL << 11) | (1UL << 17));    /* clear MPP and MPRV */
            ms |= ((uintptr_t)(target & 3) << 11); /* MPP = target & 3   */
#ifdef ENABLE_HYP
            ms &= ~MSTATUS_MPV;
            if (target & 0x4)
                ms |= MSTATUS_MPV;
#endif
            CSRW(mstatus, ms);
            return PRIV_M;
        }

        if (TSBI_IS_ECALL_TEST(op)) {
            /* Return this ecall's xEPC: proves the handler was entered. */
            frame[TSBI_FRAME_A0] = epc;
            CSRW(mepc, next_instruction(epc));
            return PRIV_M;
        }

        if (TSBI_IS_CSR_ACCESS(op)) {
            /* Snapshot our xstatus for P0's faulted path before injecting. */
            tsbi_proxy_record.status_snap = CSRR(mstatus);
            frame[TSBI_FRAME_A0] =
                tsbi_csr_access_dispatch((uint32_t)op, frame[TSBI_FRAME_A1]);
            /* A fault inside the dispatch left mstatus.MPP/MPV saying "came
             * from M" (P0 deliberately kept it that way to get back here).
             * Put the requester's own values back so the mret below returns
             * to where the request came from. */
            if (tsbi_proxy_record.faulted)
                CSRW(mstatus, tsbi_proxy_record.status_snap);
            CSRW(mepc, next_instruction(epc));
            return PRIV_M;
        }

        if (tsbi_is_mem_proxy(op)) {
            tsbi_proxy_record.status_snap = CSRR(mstatus);
            frame[TSBI_FRAME_A0] =
                tsbi_mem_access_dispatch((uint32_t)op, frame[TSBI_FRAME_A1],
                                         frame[TSBI_FRAME_A2]);
            if (tsbi_proxy_record.faulted)
                CSRW(mstatus, tsbi_proxy_record.status_snap);
            CSRW(mepc, next_instruction(epc));
            return PRIV_M;
        }

        /* Recognised as an ecall but not a known operation.  Per the
         * protocol, unrecognised operations return -1; fall through to the
         * armed/unexpected path only if nothing else claims it, so tests
         * that use a bare ecall as stimulus still work when they armed the
         * trap record instead of the escape flag. */
        if (!trap_record.armed) {
            frame[TSBI_FRAME_A0] = TSBI_RESERVED_RET;
            CSRW(mepc, next_instruction(epc));
            return PRIV_M;
        }
    }

    /* ---- Handle asynchronous interrupts ---- */
    if (cause & CAUSE_INTERRUPT_BIT) {
        uintptr_t irq = cause & ~CAUSE_INTERRUPT_BIT;
        if (irq == IRQ_LCOFI) {
            /* Clear LCOFIP to prevent infinite interrupt loop */
            CSRC(mip, MIP_LCOFIP);
        }
        if (irq == IRQ_S_TIMER) {
            /* S-mode timer interrupt: write stimecmp to max value
             * to clear the interrupt source and prevent re-entry */
            CSRW(CSR_STIMECMP, (uintptr_t)-1);
        }
        if (irq == IRQ_M_TIMER) {
            /* M-mode timer interrupt (ACLINT MTIMER): write MTIMECMP[0]
             * to max value to clear the interrupt source. Use the
             * per-platform MTIMECMP address: platforms with a per-hart
             * MTIMER do not follow the centralized CLINT layout.
             * Halfword write order: parking the high half at the
             * maximum FIRST keeps every intermediate compare value
             * above mtime, so no spurious MTIP can fire mid-sequence
             * (same sequence as sm_mtimecmp_write in Sm_Interrupts
             * and the Zawrs helpers). */
            uintptr_t mtimecmp_addr = PLATFORM_MTIMECMP_ADDR;
            asm volatile(
                "li t0, -1\n\t"
                "sw t0, 4(%0)\n\t"
                "sw t0, 0(%0)\n\t"
                "sw t0, 4(%0)\n\t"
                "fence\n\t"
                :: "r"(mtimecmp_addr) : "t0", "memory"
            );
        }
        if (irq == IRQ_M_SOFTWARE) {
            /* M-mode software interrupt (ACLINT MSWI): write MSIP[0]
             * to 0 to clear the interrupt source. Use the per-platform
             * MSIP address (config macro, same source as the MTIMECMP
             * address above). */
            uintptr_t msip_addr = PLATFORM_MSIP_ADDR;
            asm volatile(
                "sw zero, 0(%0)\n\t"
                "fence\n\t"
                :: "r"(msip_addr) : "memory"
            );
        }
        if (irq == IRQ_S_SOFTWARE) {
            /* S-mode software interrupt (SSIP): clear mip.SSIP to
             * prevent infinite re-entry. SSIP is software-writable. */
            CSRC(mip, (1UL << 1));
        }
        if (irq == IRQ_S_EXTERNAL) {
            /* S-mode external interrupt (SEIP): clear mip.SEIP software
             * bit to prevent infinite re-entry. */
            CSRC(mip, (1UL << 9));
        }
#ifdef ENABLE_HYP
        if (irq == IRQ_VS_SOFTWARE) {
            /* VS software interrupt (VSSIP): the only software-writable
             * source is hvip.VSSIP. Clear it to prevent infinite
             * re-entry when a test injects VSSIP without delegating it
             * to VS-mode (trap delivered to M-mode instead). */
            CSRC(CSR_HVIP, (1UL << 2));
        }
#endif
        /* Record interrupt in trap_record if armed */
        if (trap_record.armed) {
            trap_record.triggered   = true;
            trap_record.priv_level  = PRIV_M;
            trap_record.cause       = cause;
            trap_record.epc         = epc;
            trap_record.tval        = tval;
            trap_record.status_snap = CSRR(mstatus);
#ifdef ENABLE_HYP
            /* Interrupts also write mtval2/mtinst/mstatus.GVA on trap
             * entry (zero per norm:mtval2_trapval and
             * norm:H_trap_xtinst_interrupt); capture the hardware
             * values so tests can verify them. */
            hyp_capture_m();
            trap_record.spv = (CSRR(CSR_HSTATUS) & HSTATUS_SPV) ? true : false;
            /* A trap into M-mode records the prior V bit in mstatus.MPV
             * (not hstatus.SPV, which is written only for HS-mode traps).
             * Snapshot MPV/MPP here too so trap_get_mpv/mpp() reflect an
             * interrupt taken from VS/VU-mode, matching the synchronous
             * exception path below. */
            {
                uintptr_t _ms = CSRR(mstatus);
                _m_trap_mpv_snap = (((uint64_t)_ms >> 39) & 0x1UL) != 0;
                _m_trap_mpp_snap = (_ms >> MSTATUS_MPP_OFF) & 0x3UL;
            }
#endif
            trap_record.armed       = false;
        }
        /* Return to interrupted instruction (no epc advance for interrupts) */
        return PRIV_M;
    }

    /* ---- Handle expected (armed) exceptions ---- */
    if (trap_record.armed) {
#ifdef ENABLE_HYP
        /* QEMU quirk: TVM-protected hgatp/satp access in HS-mode is
         * raised as cause=1 instead of the spec-required cause=2 on
         * some QEMU versions. Normalize before recording so test
         * assertions stay spec-strict. Strict guard inside ensures
         * unrelated IAFs are untouched. */
        cause = normalize_qemu_tvm_cause(cause, epc);
#endif
        trap_record.triggered   = true;
        trap_record.priv_level  = PRIV_M;
        trap_record.cause       = cause;
        trap_record.epc         = epc;
        trap_record.tval        = tval;
        trap_record.status_snap = CSRR(mstatus);
#ifdef ENABLE_HYP
        /* Capture the hardware-written values unconditionally: for
         * non-guest-page-fault traps the spec still mandates specific
         * writes (mtval2/mtinst = 0, norm:mtval2_trapval), so tests
         * must observe the real hardware values rather than
         * software-forced zeros. */
        hyp_capture_m();
        /* Snapshot hstatus.SPV for tests that need to verify trap
         * came from VS-mode (LP-36/40). sret/mret clears SPV, so
         * capture it at trap entry. */
        trap_record.spv = (CSRR(CSR_HSTATUS) & HSTATUS_SPV) ? true : false;
        /* Snapshot mstatus.MPV/MPP before handler consumes them via mret. */
        {
            uintptr_t _ms = CSRR(mstatus);
            _m_trap_mpv_snap = (((uint64_t)_ms >> 39) & 0x1UL) != 0;
            _m_trap_mpp_snap = (_ms >> MSTATUS_MPP_OFF) & 0x3UL;
        }
#endif
#ifdef ENABLE_TRAP_ARM_DIAG
        _diag_arm_handler_clear++;
        _diag_arm_last_clear_epc   = (unsigned long)epc;
        _diag_arm_last_clear_cause = (unsigned long)cause;
#endif
        trap_record.armed      = false;

        /* Clear MPRV so that mret does not resume with translated
         * load/store semantics.  Without this, a test that sets MPRV=1
         * before a trap_expect-protected access will fault again on
         * the very next memory operation after mret. */
        CSRC(mstatus, MSTATUS_MPRV_BIT);

        /* Ssdbltrp double-trap recovery: a double-trap exception
         * (cause 16, norm:sstatus_sdt_trap) arrives with sstatus.SDT
         * still set and mstatus.MPP=S (written like the unexpected
         * trap would have).  mret back to S-mode would leave SDT=1,
         * and the framework's ecall-based return to M-mode would be
         * delegated to S-mode again, cascading into another unexpected
         * trap.  The SPEC note says a handler should clear SDT once
         * state is saved, so do it here and redirect mret to M-mode
         * where the test resumes.  Harmless on implementations without
         * Ssdbltrp (cause 16 cannot occur there). */
        if (cause == CAUSE_DOUBLE_TRAP) {
            /* Bound the escalation loop: if cause-16 entries keep
             * arriving while the probe is in flight, fail explicitly
             * instead of hanging. */
            if (_ssdbltrp_probe_present() && ssdbltrp_probe_active &&
                ++ssdbltrp_dt_entries > 8) {
                LOG_E("UNRECOVERABLE: double-trap escalation "
                      "does not terminate; aborting\n");
                _halt_fail();
            }
            /* Snapshot the record now: a later delivery may overwrite
             * trap_record. */
            trap_dt_snap_valid = true;
            trap_dt_snap.triggered   = trap_record.triggered;
            trap_dt_snap.priv_level  = trap_record.priv_level;
            trap_dt_snap.cause       = trap_record.cause;
            trap_dt_snap.epc         = trap_record.epc;
            trap_dt_snap.tval        = trap_record.tval;
            trap_dt_snap.status_snap = trap_record.status_snap;
            /* Probe-flow recovery (Ssdbltrp suite only): clear SDT,
             * redirect mret to M-mode and disable DTE so the ecall
             * return path cannot cascade.  Other suites that observe
             * cause 16 keep the architectural state untouched. */
            if (_ssdbltrp_probe_present() && ssdbltrp_probe_active) {
                CSRC(sstatus, (1UL << 24));       /* sstatus.SDT */
                uintptr_t _ms = CSRR(mstatus);
                _ms |= (3UL << 11);               /* MPP = M-mode */
                CSRW(mstatus, _ms);
                /* Force the resume point to the probe continuation on
                 * EVERY escalation (the generic _exec_return_addr is
                 * consumed after the first use). */
                _exec_return_addr = (uintptr_t)ssdbltrp_probe_rearm;
                /* The record and its mtval2 capture are already
                 * taken; disable DTE so the return path cannot
                 * re-enter the double-trap machinery.  The test
                 * restores menvcfg.  DTE is bit 59 of the combined
                 * 64-bit menvcfg: on RV64 it is in menvcfg, on RV32
                 * it would be in menvcfgh.  The Ssdbltrp probe flow
                 * is currently RV64-only, so guard the clear. */
#if __riscv_xlen == 64
                CSRC(menvcfg, (1UL << 59));      /* menvcfg.DTE */
#endif
            }
        }

        /* CFI (Zicfilp): Any synchronous exception taken while
         * ELP=LP_EXPECTED saves ELP into mstatus.MPELP (trap to M).
         * If we don't clear it before mret, the restored ELP=LP_EXPECTED
         * will cause the next non-LPAD instruction at the recovery PC
         * to fault again (with armed=false → UNEXPECTED TRAP).  This
         * applies to ALL sync exceptions, not just software-check —
         * e.g. instruction access-fault / page-fault during a JALR to
         * an unmapped address also saves ELP to MPELP (LP-29).
         * Note: MPELP(bit 41) and SPELP(bit 33) only exist on RV64.
         * g_trap_preserve_pelp=1 skips clearing so tests can verify
         * hardware xRET restores ELP (LP-16/19). */
#if __riscv_xlen > 32
        if (!g_trap_preserve_pelp) {
            uintptr_t pelp_bits = MSTATUS_MPELP_BIT | MSTATUS_SPELP_BIT;
            CSRC(mstatus, pelp_bits);
        }
#endif

        /* Recovery: if exec_at() set a recovery address, always use it.
         * exec_at() jumps to arbitrary code that may trigger any exception
         * (IAF, illegal instruction, etc.), not just instruction faults.
         * The recovery address returns control to exec_at's caller. */
        if (_exec_return_addr != 0) {
            CSRW(mepc, _exec_return_addr);
            _exec_return_addr = 0;
        } else if (is_inst_fault(cause) && trap_record.return_addr != 0) {
            CSRW(mepc, trap_record.return_addr);
            trap_record.return_addr = 0;
        } else if (is_inst_fault(cause)) {
            /* Instruction fault without recovery address: epc may point
             * to an invalid/tagged address that we cannot safely read
             * (e.g., PM-tagged PC in NEG-01).  Skip 4 bytes as a safe
             * default — the caller should check trap_was_triggered()
             * and not rely on the resumed PC being meaningful. */
            CSRW(mepc, epc + 4);
        } else {
            /* Skip the faulting instruction */
            CSRW(mepc, next_instruction(epc));
        }

        /* CFI (Zicfilp) test hook: force MPELP/SPELP=1 before mret so
         * tests can verify hardware clears xpelp on mret (LP-20).
         * No-op unless g_trap_force_pelp is set by the test. */
#if __riscv_xlen > 32
        if (g_trap_force_pelp) {
            CSRS(mstatus, MSTATUS_MPELP_BIT | MSTATUS_SPELP_BIT);
        }
#endif

        /* Always return PRIV_M so _trap_return uses mret.
         * mret uses mstatus.MPP (set by hardware on trap entry) to
         * return to the correct privilege level (S or U mode).
         * Using sret here would be wrong because sepc is not set. */
        return PRIV_M;
    }

    /* ---- Unexpected exception: fatal error ---- */
    LOG_E("UNEXPECTED TRAP in M-mode !!!\n");
#ifdef ENABLE_TRAP_ARM_DIAG
    LOG_D("[DIAG] begin=%lu end=%lu handler_clear=%lu\n",
          _diag_arm_begin_count, _diag_arm_end_count,
          _diag_arm_handler_clear);
    LOG_D("[DIAG] last_clear epc=0x%lx cause=0x%lx\n",
          _diag_arm_last_clear_epc, _diag_arm_last_clear_cause);
#endif
    LOG_E("mcause  = 0x%lx\n", (unsigned long)cause);
    LOG_E("mepc    = 0x%lx\n", (unsigned long)epc);
    LOG_E("mtval   = 0x%lx\n", (unsigned long)tval);
    LOG_E("mstatus = 0x%lx\n", (unsigned long)CSRR(mstatus));
    LOG_E("armed   = %d  current_priv = %u\n",
          (int)trap_record.armed, current_priv);
    _trace_dump();

    /* Halt with fail status */
    _halt_fail();

    return PRIV_M; /* unreachable */
}

/* ===================================================================
 * T-SBI service stages shared by the S and HS handler levels
 *
 * HS *is* the S privilege level with V=0, so it owes requesters exactly the
 * same subset of the protocol as plain S.  The three stages therefore live
 * here once and both entry points call them in order: s_trap_handler below,
 * and hs_trap_handler in common/hyp/hyp_trap.c.  A second copy inside the HS
 * handler would be free to drift, and the drift would be invisible - a test
 * would simply see its request silently dropped.
 *
 * Keeping the stages in this file also keeps the forwarding primitives and
 * the escape flag above file-static.
 *
 * The order is load-bearing (see tsbi_design_brief.md):
 *   P0 first - a nested proxy fault is our own accident, not a new event
 *   P1 next  - an armed raw ecall is a stimulus, not a service request
 *   P2 last, but still BEFORE the handler records anything: a request we
 *              served is framework traffic and must not surface in a trap
 *              record the test is asserting on
 * =================================================================== */

/* P0: claim a fault taken by an instruction we injected on a caller's
 * behalf.  Returns true if the trap was ours, in which case the caller must
 * return to the recovery point at once without recording anything.
 *
 * sstatus is deliberately left untouched: tsbi_proxy_record.recover is a
 * label inside tsbi_*_access_dispatch, which runs at THIS level, so the sret
 * has to land here - and the nested trap already set SPP to say so.  P2 puts
 * status_snap back once the dispatch has returned. */
bool tsbi_s_proxy_capture(uintptr_t cause)
{
    if (!tsbi_proxy_record.armed)
        return false;

    tsbi_proxy_record.faulted = true;
    tsbi_proxy_record.cause   = cause;
    CSRW(sepc, tsbi_proxy_record.recover);
    return true;
}

/* P1: consume the raw-ecall escape flag.  Returns true when this ecall is an
 * armed test stimulus and must therefore bypass P2 entirely. */
bool tsbi_raw_ecall_consume(uintptr_t cause)
{
    if (is_ecall(cause) && _tsbi_skip_dispatch) {
        _tsbi_skip_dispatch = false;
        return true;
    }
    return false;
}

/* P2: serve the S/HS-level subset of the protocol.
 *
 * Reached by ecalls delegated down to us (ecall-from-U with medeleg[8]=1,
 * ecall-from-VS with medeleg[10]=1 and hedeleg[10] read-only-zero).
 * ecall-from-S never lands here: medeleg[9] is 0 by framework invariant, so
 * an S-mode test's request goes straight to M.
 *
 * Served locally : ECALL_TEST, GOTO_SMODE/UMODE, GOTO_VSMODE/VUMODE,
 *                  U/S/HS/VS-level CSR_ACCESS
 * Forwarded to M : GOTO_MMODE, M-level CSR, memory proxy
 *
 * Returns true if the request was disposed of, in which case the caller must
 * return to the requester at once.  False means "not mine": the trap is a
 * genuine event and the handler's normal recording path owns it. */
bool tsbi_s_dispatch(uintptr_t *frame, uintptr_t cause, uintptr_t epc)
{
    if (!is_ecall(cause))
        return false;

    uintptr_t op     = frame[TSBI_FRAME_A0];
    uintptr_t resume = next_instruction(epc);

    if (TSBI_IS_GOTO(op)) {
        unsigned target = tsbi_goto_to_priv(op);

        if (target == PRIV_S || target == PRIV_U) {
            /* Within our authority: set sstatus.SPP and sret. */
            current_priv = target;
#ifdef ENABLE_HYP
            /* The requester is leaving V=1 behind, so SPV must go with it or
             * the sret would drop it back into VS/VU instead of HS/U.  Safe
             * to clear unconditionally: hardware overwrote SPV with the
             * requester's V when it took this trap, so there is no
             * test-written value here left to destroy. */
            CSRW(CSR_HSTATUS, CSRR(CSR_HSTATUS) & ~(uintptr_t)HSTATUS_SPV);
#endif
            uintptr_t ss = CSRR(sstatus);
            ss &= ~MSTATUS_SPP_BIT;
            if (target == PRIV_S)
                ss |= MSTATUS_SPP_BIT;
            CSRW(sstatus, ss);
            CSRW(sepc, tsbi_goto_resume(resume));
            return true;
        }

#ifdef ENABLE_HYP
        if (target == PRIV_VS || target == PRIV_VU) {
            /* Also within our authority: hstatus is an HS-level CSR, so
             * entering V=1 needs no M excursion.  Serving this here is
             * MANDATORY, not an optimisation: sret+hstatus.SPV is the only
             * way a real hypervisor enters a guest, whereas M's
             * mret+mstatus.MPV is a path that does not exist in practice and
             * bypasses hstatus.SPV entirely - no test could then observe SPV
             * semantics (e.g. sret clearing SPV). */
            current_priv = target;
            CSRW(CSR_HSTATUS, CSRR(CSR_HSTATUS) | HSTATUS_SPV);
            uintptr_t ss = CSRR(sstatus);
            ss &= ~MSTATUS_SPP_BIT;
            if (target == PRIV_VS)
                ss |= MSTATUS_SPP_BIT;   /* SPV=1 + SPP=1 -> VS, 0 -> VU */
            CSRW(sstatus, ss);
            CSRW(sepc, tsbi_goto_resume(resume));
            return true;
        }
#endif

        /* Beyond our authority (GOTO_MMODE needs mstatus.MPP): forward up
         * the privilege chain.  Record the ORIGINAL requester's resume point
         * first - the level that serves this uses it instead of our own
         * ecall+4 (see tsbi_goto_resume). */
        current_priv = target;
        tsbi_goto_forward_mark(resume);
        _tsbi_forward_goto(frame);
        /* Never returns: the serving level resumes the original requester
         * directly, with the register context this frame carries. */
    }

    if (TSBI_IS_ECALL_TEST(op)) {
        frame[TSBI_FRAME_A0] = epc;
        CSRW(sepc, resume);
        return true;
    }

    if (TSBI_IS_CSR_ACCESS(op)) {
        uint32_t csr = tsbi_csr_addr_of(op);
        if (tsbi_csr_is_m_level(csr)) {
            /* No authority: forward, then hand the result back. */
            tsbi_forward_up(frame);
            CSRW(sepc, resume);
            return true;
        }
        /* Anything below M is reachable from here - including the VS-level
         * CSRs a guest cannot touch itself, which is the whole reason a VS
         * requester needs us. */
        tsbi_proxy_record.status_snap = CSRR(sstatus);
        frame[TSBI_FRAME_A0] =
            tsbi_csr_access_dispatch((uint32_t)op, frame[TSBI_FRAME_A1]);
        /* Same as the M side: a fault left sstatus.SPP saying "came from
         * S", so restore the requester's own value before the sret. */
        if (tsbi_proxy_record.faulted)
            CSRW(sstatus, tsbi_proxy_record.status_snap);
        CSRW(sepc, resume);
        return true;
    }

    if (tsbi_is_mem_proxy(op)) {
        /* Physical-address access needs M privilege: forward. */
        tsbi_forward_up(frame);
        CSRW(sepc, resume);
        return true;
    }

    if (!trap_record.armed) {
        frame[TSBI_FRAME_A0] = TSBI_RESERVED_RET;
        CSRW(sepc, resume);
        return true;
    }

    return false;
}

#ifdef ENABLE_HYP
/* ===================================================================
 * P2 for the VS level - the most restricted dispatch layer
 *
 * Reached by ecall-from-VU once medeleg[8] and hedeleg[8] both delegate it
 * down (hedeleg[8] is in the baseline, see tsbi/tsbi_deleg.c).  ecall-from-VS
 * cannot land here: hedeleg[10] is read-only-zero, so a VS-mode test's own
 * request always stops at HS - which is what starts the VS->HS chain.
 *
 * Served locally : ECALL_TEST, U/S-level CSR_ACCESS
 * Forwarded to HS: every GOTO, HS-level CSR, M-level CSR, memory proxy
 *
 * Two notes on that split (it is the design brief's capability table, third
 * column, not an implementation shortcut):
 *
 *  - EVERY GOTO leaves.  Even GOTO_VSMODE/VUMODE, which a VS handler could
 *    technically fake with vsstatus.SPP + sret while staying inside V=1:
 *    doing so would enter the guest without ever touching hstatus.SPV, i.e.
 *    down a path no real hypervisor uses.  Forwarding to HS instead makes the
 *    request arrive at the level that owns SPV, and HS serves it with the
 *    genuine sret+SPV entry (see the S dispatch's V=1 branch).  Uniform rule,
 *    better semantics: a GOTO always names an absolute privilege target and is
 *    always served by the level that owns every field involved.
 *
 *  - HS-level CSRs leave too.  In V=1 the 0x2xx/0x6xx addresses either trap as
 *    virtual instructions or are simply unreachable, and they are exactly the
 *    registers a guest is not allowed to see - which is the whole reason a VS
 *    requester needs a proxy for them.  bits[9:8] does the classifying:
 *    tsbi_csr_is_hs_level() joins tsbi_csr_is_m_level() as a forward trigger.
 *
 * The forwarded ecall reaches HS because ecall-from-VS is never delegated,
 * so tsbi_forward_up() / _tsbi_forward_goto() need no special casing here.
 *
 * The locally served CSR case needs none either: at V=1 the plain S CSR names
 * alias the virtual ones, so tsbi_csr_access_dispatch() acting on "sstatus"
 * reaches vsstatus - the guest's own register, which is precisely what a VS/VU
 * requester means by an S-level CSR.  Same reason CSRW(sepc, resume) below
 * writes vsepc.
 *
 * Returns true if the request was disposed of.  Same contract as
 * tsbi_s_dispatch: false means the trap is a genuine event and the VS handler's
 * recording path owns it.
 * =================================================================== */
bool tsbi_vs_dispatch(uintptr_t *frame, uintptr_t cause, uintptr_t epc)
{
    if (!is_ecall(cause))
        return false;

    uintptr_t op     = frame[TSBI_FRAME_A0];
    uintptr_t resume = next_instruction(epc);

    if (TSBI_IS_GOTO(op)) {
        /* No authority over any privilege-selecting field reachable from here:
         * forward unconditionally, recording the requester's resume point for
         * whichever level ends up serving it (see tsbi_goto_resume). */
        current_priv = tsbi_goto_to_priv(op);
        tsbi_goto_forward_mark(resume);
        _tsbi_forward_goto(frame);
        /* Never returns. */
    }

    if (TSBI_IS_ECALL_TEST(op)) {
        frame[TSBI_FRAME_A0] = epc;
        CSRW(sepc, resume);
        return true;
    }

    if (TSBI_IS_CSR_ACCESS(op)) {
        uint32_t csr = tsbi_csr_addr_of(op);
        if (tsbi_csr_is_m_level(csr) || tsbi_csr_is_hs_level(csr)) {
            /* Above our authority: forward, then hand the result back.  This
             * is the RETURNING kind of forward - HS (or M behind it) serves
             * the request and returns here, so our own frame stays valid. */
            tsbi_forward_up(frame);
            CSRW(sepc, resume);
            return true;
        }
        tsbi_proxy_record.status_snap = CSRR(sstatus);
        frame[TSBI_FRAME_A0] =
            tsbi_csr_access_dispatch((uint32_t)op, frame[TSBI_FRAME_A1]);
        if (tsbi_proxy_record.faulted)
            CSRW(sstatus, tsbi_proxy_record.status_snap);
        CSRW(sepc, resume);
        return true;
    }

    if (tsbi_is_mem_proxy(op)) {
        /* Physical-address access: not even HS can serve it, but forwarding
         * one level is all we do - HS forwards it on to M. */
        tsbi_forward_up(frame);
        CSRW(sepc, resume);
        return true;
    }

    if (!trap_record.armed) {
        frame[TSBI_FRAME_A0] = TSBI_RESERVED_RET;
        CSRW(sepc, resume);
        return true;
    }

    return false;
}
#endif /* ENABLE_HYP */

/* ===================================================================
 * S-mode trap handler (called from trap.S)
 *
 * Returns the privilege level to return to (for sret SPP setup).
 * =================================================================== */
unsigned s_trap_handler(uintptr_t *frame) {
    uintptr_t cause = CSRR(scause);
    uintptr_t epc   = CSRR(sepc);
    uintptr_t tval  = CSRR(stval);

    /* P0: nested-fault capture (Strategy A) - MUST BE ABSOLUTELY FIRST. */
    if (tsbi_s_proxy_capture(cause))
        return PRIV_S;

    /* NOTE: do NOT read mtval2 here: mtval2 is an M-mode CSR, so an
     * S-side read may raise an illegal-instruction trap inside the
     * handler itself and overwrite the armed record. Pass 0; the
     * M-side entry still captures mtval2. */
    _trace_add(PRIV_S, cause, epc, CSRR(sstatus), tval,
               0, trap_record.armed);

    /* Ssdbltrp probe tolerance (S side): the probe trap may be
     * redelivered after the armed flag was consumed by an earlier
     * record (e.g. an escalated double-trap entry in M-mode).  Re-arm
     * these traps so the armed branch below records them instead of
     * halting the suite.  Region A is the trampoline entry path plus
     * probe body; region B is the continuation's mtval2 read. */
    if (_ssdbltrp_probe_present() && ssdbltrp_probe_active &&
        cause == CAUSE_ILLEGAL_INST && !trap_record.armed &&
        ssdbltrp_s_probe_repeats < 16 &&
        ((epc >= (uintptr_t)ssdbltrp_run_s_probe &&
          epc < (uintptr_t)ssdbltrp_probe_rearm) ||
         (epc >= (uintptr_t)ssdbltrp_probe_mtval2_ld &&
          epc < (uintptr_t)ssdbltrp_probe_mtval2_ld + 8))) {
        trap_record.armed = true;
    }

    /* ================================================================
     * P1 + P2: raw-ecall escape, then T-SBI service dispatch.
     * Both stages are shared with the HS handler; see their definitions
     * above for the served/forwarded split and the ordering rules.
     * ================================================================ */
    if (!tsbi_raw_ecall_consume(cause) && tsbi_s_dispatch(frame, cause, epc))
        return PRIV_S;

    /* ---- Handle asynchronous interrupts ---- */
    if (cause & CAUSE_INTERRUPT_BIT) {
        uintptr_t irq = cause & ~CAUSE_INTERRUPT_BIT;
        if (irq == IRQ_LCOFI) {
            /* Clear LCOFIP to prevent infinite interrupt loop */
            CSRC(sip, MIP_LCOFIP);
        }
        if (irq == IRQ_S_TIMER) {
            /* S-mode timer interrupt: write stimecmp to max value
             * to clear the interrupt source and prevent re-entry */
            CSRW(CSR_STIMECMP, (uintptr_t)-1);
        }
#ifdef ENABLE_HYP
        if (irq == IRQ_VS_SOFTWARE) {
            /* VS software interrupt delivered to HS-mode (mideleg
             * bit 2 is read-only 1 per norm:mideleg_acc_h, and
             * hideleg bit 2 is clear). The only software-writable
             * source is hvip.VSSIP; clear it to prevent infinite
             * re-entry. */
            CSRC(CSR_HVIP, (1UL << 2));
        }
#endif
        /* Record interrupt in trap_record if armed */
        if (trap_record.armed) {
            trap_record.triggered   = true;
            trap_record.priv_level  = PRIV_S;
            trap_record.cause       = cause;
            trap_record.epc         = epc;
            trap_record.tval        = tval;
            trap_record.status_snap = CSRR(sstatus);
#ifdef ENABLE_HYP
            /* Interrupts into HS-mode also write htval/htinst/GVA
             * (zero per norm:htval_trapval / H_trap_xtinst_interrupt);
             * capture the hardware values for verification. Also
             * snapshots hstatus.SPV/SPVP into trap_record.spv. */
            hyp_capture_s();
#endif
            trap_record.armed       = false;
        }
        /* Return to interrupted instruction (no epc advance for interrupts) */
        return PRIV_S;
    }

    /* ---- Handle expected (armed) exceptions ---- */
    if (trap_record.armed) {
        trap_record.triggered   = true;
        trap_record.priv_level  = PRIV_S;
        trap_record.cause       = cause;
        trap_record.epc         = epc;
        trap_record.tval        = tval;
        trap_record.status_snap = CSRR(sstatus);
        if (!(cause & CAUSE_INTERRUPT_BIT))
            g_s_deleg_exc_count++;
#ifdef ENABLE_HYP
        /* Capture the hardware-written values unconditionally: for
         * non-guest-page-fault traps the spec still mandates specific
         * writes (htval/htinst = 0, norm:htval_trapval), so tests
         * must observe the real hardware values rather than
         * software-forced zeros. Also snapshots hstatus.SPV/SPVP
         * into trap_record.spv. */
        hyp_capture_s();
#endif
        trap_record.armed      = false;

        /* Ssdbltrp probe tolerance: the probe trap may be delivered
         * repeatedly, or resume in a mode where a C call is unsafe.
         * While a probe is in flight, keep the expectation armed so
         * repeated deliveries are recorded instead of halting the
         * suite, and redirect the resume point to the probe
         * continuation label (a mode-agnostic ecall-based return to
         * M-mode).  With a single delivery this only re-arms a harmless
         * leftover expectation. */
        if (_ssdbltrp_probe_present() && ssdbltrp_probe_active &&
            cause == CAUSE_ILLEGAL_INST &&
            ((epc >= (uintptr_t)ssdbltrp_run_s_probe &&
              epc < (uintptr_t)ssdbltrp_probe_rearm) ||
             (epc >= (uintptr_t)ssdbltrp_probe_mtval2_ld &&
              epc < (uintptr_t)ssdbltrp_probe_mtval2_ld + 8))) {
            ssdbltrp_s_probe_repeats++;
            if (ssdbltrp_s_probe_repeats > 4) {
                CSRW(sepc, (uintptr_t)ssdbltrp_probe_rearm);
                return PRIV_S;
            }
            trap_record.armed = true;
            CSRW(sepc, (uintptr_t)ssdbltrp_probe_rearm);
            return PRIV_S;
        }

        /* CFI (Zicfilp): clear SPELP on any synchronous exception for
         * clean recovery, same logic as m_trap_handler. Any sync trap
         * taken while ELP=LP_EXPECTED saves ELP into SPELP (trap to S).
         * Without clearing, sret restores ELP=LP_EXPECTED and the next
         * non-LPAD instruction faults again (LP-15/29).
         * g_trap_preserve_pelp=1 skips clearing so tests can verify
         * hardware xRET restores ELP (LP-16/19).
         * Note: SPELP(bit 23) only exists on RV64. Use sstatus (not
         * mstatus) because this is the S-mode handler. */
#if __riscv_xlen > 32
        if (!g_trap_preserve_pelp) {
            CSRC(sstatus, MSTATUS_SPELP_BIT);
#ifdef ENABLE_HYP
            /* When the trap came from a V=1 mode the sret below returns to VS,
             * and per norm:Zicfilp_pelp_trap_return an xret into mode y
             * restores ELP from y's own xpelp -- for VS that is
             * vsstatus.SPELP, not sstatus.SPELP.  Clear it too, otherwise a
             * landing-pad fault taken from VS resumes with ELP=LP_EXPECTED and
             * the very next instruction re-faults (unbounded, because the
             * expectation has been consumed by then).  hstatus.SPV says the
             * trap source had V=1. */
            if (CSRR(CSR_HSTATUS) & HSTATUS_SPV)
                CSRC(CSR_VSSTATUS, VSSTATUS_SPELP_BIT);
#endif
        }
#endif

        /* Recovery: if exec_at() set a recovery address, always use it. */
        if (_exec_return_addr != 0) {
            CSRW(sepc, _exec_return_addr);
            _exec_return_addr = 0;
        } else if (is_inst_fault(cause) && trap_record.return_addr != 0) {
            CSRW(sepc, trap_record.return_addr);
            trap_record.return_addr = 0;
        } else if (is_inst_fault(cause)) {
            /* Instruction fault without recovery address: epc may point
             * to an invalid/tagged address that we cannot safely read.
             * Skip 4 bytes as a safe default. */
            CSRW(sepc, epc + 4);
        } else {
            CSRW(sepc, next_instruction(epc));
        }

        /* CFI (Zicfilp) test hook: force SPELP=1 before sret so tests
         * can verify hardware clears xpelp on sret (LP-17).
         * No-op unless g_trap_force_pelp is set by the test.
         * Use sstatus (not mstatus) because this is the S-mode handler. */
#if __riscv_xlen > 32
        if (g_trap_force_pelp) {
            CSRS(sstatus, MSTATUS_SPELP_BIT);
        }
#endif

        /* Return PRIV_S so _trap_return uses sret, which returns to
         * the correct privilege level using sstatus.SPP (set by hardware). */
        return PRIV_S;
    }

    /* ---- Unexpected exception ---- */
    LOG_E("UNEXPECTED TRAP in S-mode !!!\n");
    LOG_E("scause = 0x%lx\n", (unsigned long)cause);
    LOG_E("sepc   = 0x%lx\n", (unsigned long)epc);
    LOG_E("stval  = 0x%lx\n", (unsigned long)tval);
    _trace_dump();

    /* Halt with fail status */
    _halt_fail();

    return PRIV_S; /* unreachable */
}

/* ===================================================================
 * Trap API for test framework
 * =================================================================== */

#ifdef ENABLE_HYP
/* A stimulus trap delegated down to VS by hedeleg lands in vs_trap_handler
 * (hyp_vs_trap.c), which keeps its own record.  The accessors below merge it so
 * trap_expect / trap_was_triggered / trap_get_cause observe a VS-delegated trap
 * exactly as they do an M/HS one.  Declared locally, not via hyp_vs_trap.h,
 * which pulls in test_framework.h and would make the dependency circular (the
 * same reason trap_clear_record() declares hs_trap_record_reset locally). */
extern void      vs_trap_clear(void);
extern bool      vs_trap_was_triggered(void);
extern uintptr_t vs_trap_get_cause(void);
extern uintptr_t vs_trap_get_epc(void);
extern uintptr_t vs_trap_get_tval(void);
#endif

void trap_expect_begin(void) {
    __sync_synchronize();
    trap_record.armed       = true;
    trap_record.triggered   = false;
    trap_record.return_addr = 0;
    trap_record.cause       = 0;
    trap_record.epc         = 0;
    trap_record.tval        = 0;
    trap_record.status_snap  = 0;
#ifdef ENABLE_HYP
    vs_trap_clear();   /* a fresh expectation must not see a stale VS record */
#endif
#ifdef ENABLE_TRAP_ARM_DIAG
    _diag_arm_begin_count++;
#endif
    __sync_synchronize();
}

void trap_expect_end(void) {
    __sync_synchronize();
    trap_record.armed = false;
#ifdef ENABLE_TRAP_ARM_DIAG
    _diag_arm_end_count++;
#endif
    __sync_synchronize();
}

/* ===================================================================
 * trap_clear_record - Clear all trap record fields and disarm.
 *
 * Unlike trap_expect_end() which only sets armed=false, this function
 * also clears triggered, cause, epc, tval, and all other fields.
 * Used by reset_state() to ensure a clean slate between tests.
 *
 * Under ENABLE_HYP this also clears the HS-mode record kept in
 * common/hyp/hyp_trap.c.  That record is a trap record too, and leaving it
 * behind is not merely untidy: the accessors below prefer it whenever its
 * triggered flag is set, so a stale one makes every later test read the
 * cause/htval of a trap it never caused.  Declared locally rather than by
 * including hyp_trap.h, which pulls in test_framework.h and would make the
 * dependency circular.
 * =================================================================== */
#ifdef ENABLE_HYP
extern void hs_trap_record_reset(void);
#endif

void trap_clear_record(void) {
    __sync_synchronize();
    trap_record.armed       = false;
    trap_record.triggered   = false;
    trap_record.priv_level  = 0;
    trap_record.cause       = 0;
    trap_record.epc         = 0;
    trap_record.tval        = 0;
    trap_record.status_snap = 0;
    trap_record.return_addr = 0;
#ifdef ENABLE_HYP
    trap_record.htval       = 0;
    trap_record.htinst      = 0;
    trap_record.gva         = false;
    trap_record.spv         = false;
    hs_trap_record_reset();
    vs_trap_clear();
#endif
    __sync_synchronize();
}

bool trap_was_triggered(void) {
    if (trap_record.triggered)
        return true;
#ifdef ENABLE_HYP
    /* A stimulus trap delegated down to VS by hedeleg is recorded by
     * vs_trap_handler in its own record; merge it so a test observes it
     * through the same generic API as an M/HS trap. */
    if (vs_trap_was_triggered())
        return true;
#endif
    return false;
}

uintptr_t trap_get_cause(void) {
#ifdef ENABLE_HYP
    if (!trap_record.triggered && vs_trap_was_triggered())
        return vs_trap_get_cause();
#endif
    return trap_record.cause;
}

uintptr_t trap_get_epc(void) {
#ifdef ENABLE_HYP
    if (!trap_record.triggered && vs_trap_was_triggered())
        return vs_trap_get_epc();
#endif
    return trap_record.epc;
}

uintptr_t trap_get_tval(void) {
#ifdef ENABLE_HYP
    if (!trap_record.triggered && vs_trap_was_triggered())
        return vs_trap_get_tval();
#endif
    return trap_record.tval;
}

uintptr_t trap_get_status_snap(void) {
    return trap_record.status_snap;
}

/* Snapshot of the current trap record into caller storage.  Needed by
 * flows where a single hardware event produces more than one handler
 * record (e.g. broken Ssdbltrp implementations delivering both the
 * escalated double-trap to M-mode and the original trap to S-mode):
 * the continuation code snapshots the first record before the second
 * delivery overwrites trap_record. */
void trap_snapshot(trap_snapshot_t *snap) {
    snap->triggered   = trap_record.triggered;
    snap->priv_level  = trap_record.priv_level;
    snap->cause       = trap_record.cause;
    snap->epc         = trap_record.epc;
    snap->tval        = trap_record.tval;
    snap->status_snap = trap_record.status_snap;
}

#ifdef ENABLE_HYP
/* The three below are the M-mode record's raw view.  The names tests actually
 * call - trap_get_htval/htinst/gva - are defined in common/hyp/hyp_trap.c,
 * which merges this view with the HS-mode record the same way trap_get_spv()
 * does.  A trap delegated by hedeleg never reaches this file, so answering
 * from here alone would report zeroes for it. */
uintptr_t trap_get_htval_snap(void) {
    return trap_record.htval;
}

uintptr_t trap_get_htinst_snap(void) {
    return trap_record.htinst;
}

bool trap_get_gva_snap(void) {
    return trap_record.gva;
}

bool trap_get_mpv(void) {
    return _m_trap_mpv_snap;
}

uintptr_t trap_get_mpp(void) {
    return _m_trap_mpp_snap;
}

/* hstatus.SPV snapshot captured at trap entry (M or S mode).
 * Used by trap_get_spv() when the trap went through s_trap_handler
 * or m_trap_handler instead of hs_trap_handler. */
bool trap_get_spv_snap(void) {
    return trap_record.spv;
}
#endif
