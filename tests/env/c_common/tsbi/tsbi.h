/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 *
 * tsbi.h - T-SBI (Test Supervisor Binary Interface) protocol layer
 *
 * T-SBI is a PROTOCOL, not a feature of any particular privilege mode.
 * It defines only three things:
 *   1. calling convention : ecall, a0 = opcode, a1 = argument, a0 = return
 *   2. opcode encodings   : GOTO_xMODE / ECALL_TEST / CSR_ACCESS / memory proxy
 *   3. layered semantics  : serve locally if possible, else forward up the chain
 *
 * Every privilege level's trap handler (M / HS / VS) implements the same call
 * set with decreasing capability; the protocol itself spans all of them.
 *
 * AUTHORITATIVE SOURCE (constants below MUST match):
 *   common/act4/rvtest_trap_handler.h   (vendored verbatim, lines 186-199)
 *   SPEC/abstraction.adoc               (T-SBI Calls table)
 * See common/act4/VERSION for provenance and the constant cross-check table.
 */

#ifndef COMMON_TSBI_H
#define COMMON_TSBI_H

#include "types.h"
#include "encoding.h"   /* PRIV_* */

/* ===================================================================
 * SECTION 1: Operation codes
 *
 * Upstream rvtest_trap_handler.h:186-191, 199.
 * =================================================================== */

/* ACT extension: privilege-mode switch (small integers 1..5) */
#define TSBI_GOTO_MMODE     0x00000001u
#define TSBI_GOTO_SMODE     0x00000002u
#define TSBI_GOTO_UMODE     0x00000003u
#define TSBI_GOTO_VSMODE    0x00000004u
#define TSBI_GOTO_VUMODE    0x00000005u

/* Core T-SBI: probe the ecall->handler path; returns xEPC in a0.
 * 0x73 is the ecall instruction encoding itself (funct3 == 0, which is how
 * the handler tells it apart from CSR_ACCESS). */
#define TSBI_ECALL_TEST     0x00000073u

/* Returned in a0 for unrecognised operations (and for a faulted proxy). */
#define TSBI_RESERVED_RET   ((uintptr_t)-1)

/* ===================================================================
 * SECTION 2: CSR_ACCESS encodings
 *
 * a0 IS a complete RISC-V CSR instruction word:
 *   csr[31:20] | rs1[19:15] | funct3[14:12] | rd[11:7] | 0x73[6:0]
 *
 * The handler writes this word into an executable buffer, fence.i's, and
 * executes it.  rd/rs1 are already encoded by the caller:
 *   WRITE : csrrw x0, csr, a1   (rd=x0  -> no old value returned)
 *   SET   : csrrs x0, csr, a1
 *   CLEAR : csrrc x0, csr, a1
 *   READ  : csrrs a0, csr, x0   (rd=a0  -> result lands directly in a0)
 * =================================================================== */
#define TSBI_CSR_WRITE_ENCODE(csr)  (((uint32_t)(csr) << 20) | 0x59073u)
#define TSBI_CSR_SET_ENCODE(csr)    (((uint32_t)(csr) << 20) | 0x5A073u)
#define TSBI_CSR_CLEAR_ENCODE(csr)  (((uint32_t)(csr) << 20) | 0x5B073u)
#define TSBI_CSR_READ_ENCODE(csr)   (((uint32_t)(csr) << 20) | 0x02573u)

/* ===================================================================
 * SECTION 3: Memory proxy encodings (fixed instruction words)
 *
 * Access the physical address in a1 with the serving level's privilege;
 * used for mtime / MMIO that only a higher level may touch.
 *
 *   LW  : lw a0, 0(a1)     LW4 : lw a0, 4(a1)     LD : ld a0, 0(a1)
 *   SW  : sw a2, 0(a1)     SW4 : sw a2, 4(a1)     SD : sd a2, 0(a1)
 *
 * REGISTER ROLES: a0 = opcode (in) / loaded value (out), a1 = address,
 * a2 = value to store.
 *
 * UPSTREAM DISCREPANCY (resolved in favour of the reference implementation):
 * abstraction.adoc's T-SBI Calls table prints the stores as "SW a0, 0(a1)"
 * (word 0x00a5a023), but rvtest_trap_handler.h's instruction table (line
 * 1754) emits `sw a2, 0(a1)`.  The a0 form cannot work: a0 already carries
 * the opcode, so it cannot also carry the value.  We therefore follow the
 * reference implementation and encode rs2 = a2.
 * =================================================================== */
#define TSBI_LW     0x0005a503u   /* lw a0, 0(a1) */
#define TSBI_LW4    0x0045a503u   /* lw a0, 4(a1) */
#define TSBI_LD     0x0005b503u   /* ld a0, 0(a1)  (RV64) */
#define TSBI_SW     0x00c5a023u   /* sw a2, 0(a1) */
#define TSBI_SW4    0x00c5a223u   /* sw a2, 4(a1) */
#define TSBI_SD     0x00c5b023u   /* sd a2, 0(a1)  (RV64) */

/* ===================================================================
 * SECTION 4: Dispatch classification
 *
 * Upstream dispatch order (rvtest_trap_handler.h:178-182):
 *   1. (a0-1) < 5                      -> GOTO_xMODE
 *   2. a0 == 0x73                      -> ECALL_TEST
 *   3. a0[6:0]==0x73 && a0[14:12]!=0   -> CSR_ACCESS
 *   4. otherwise                       -> RESERVED (-1)
 * The memory-proxy words are exact matches checked alongside CSR_ACCESS.
 * =================================================================== */

/* (a0 - 1) < 5, i.e. a0 in [1..5]; unsigned wrap makes a0==0 fail the test */
#define TSBI_IS_GOTO(a0)        (((uintptr_t)(a0) - 1u) < 5u)
#define TSBI_IS_ECALL_TEST(a0)  ((uintptr_t)(a0) == TSBI_ECALL_TEST)
#define TSBI_IS_SYSTEM(a0)      (((uintptr_t)(a0) & 0x7Fu) == 0x73u)
#define TSBI_IS_CSR_ACCESS(a0)  (TSBI_IS_SYSTEM(a0) && ((((uintptr_t)(a0) >> 12) & 7u) != 0u))

static inline bool tsbi_is_mem_proxy(uintptr_t a0)
{
    return a0 == TSBI_LW  || a0 == TSBI_LW4 || a0 == TSBI_LD ||
           a0 == TSBI_SW  || a0 == TSBI_SW4 || a0 == TSBI_SD;
}

/* Any recognised T-SBI operation (used by the handlers' P2 gate). */
static inline bool tsbi_is_valid_op(uintptr_t a0)
{
    return TSBI_IS_GOTO(a0) || TSBI_IS_ECALL_TEST(a0) ||
           TSBI_IS_CSR_ACCESS(a0) || tsbi_is_mem_proxy(a0);
}

/* Extract the 12-bit CSR address from a CSR_ACCESS encoding. */
static inline uint32_t tsbi_csr_addr_of(uintptr_t a0)
{
    return (uint32_t)(((uintptr_t)(a0) >> 20) & 0xFFFu);
}

/* ===================================================================
 * SECTION 5: CSR privilege classification
 *
 * RISC-V CSR address bits [9:8] encode the lowest privilege that may
 * access the register:
 *   00 = U, 01 = S, 10 = hypervisor/VS, 11 = M
 * A serving handler must forward any request above its own authority.
 * =================================================================== */

/* 0x3xx / 0x7xx / 0xBxx / 0xFxx -> M-level; an HS/VS handler must forward. */
static inline bool tsbi_csr_is_m_level(uint32_t csr)
{
    return ((csr >> 8) & 3u) == 3u;
}

/* bits[9:8] == 10 -> hypervisor-level (0x2xx vs-CSRs, 0x6xx h-CSRs such as
 * hgatp, plus 0xAxx / 0xExx).
 * A VS handler must forward these to HS; an HS handler can serve them. */
static inline bool tsbi_csr_is_hs_level(uint32_t csr)
{
    return ((csr >> 8) & 3u) == 2u;
}

/* -------------------------------------------------------------------
 * Fully trap-state CSRs: hardware overwrites the ENTIRE register on a trap
 * taken to its level (xepc/xcause/xtval for x in {m,s,vs}, plus the H-ext
 * mtval2/mtinst/htval/htinst).
 *
 * These can NOT be read through the T-SBI CSR proxy: the proxy IS an ecall,
 * and the trap entry it causes clobbers the very register being read, so the
 * value returned is the proxy trap's own state, not the caller's.  Even an
 * M-excursion cannot recover the ambient value (its own entry trap clobbers
 * it first).  tsbi_csr_* therefore refuses to proxy them; use trap_get_cause()/
 * epc()/tval() for what a trap RECORDED, or mcsr_write()/mcsr_write_readback()
 * to SET one inside a single M excursion.
 *
 * mstatus/sstatus/hstatus are only PARTIALLY trap-state (MPP/MPIE/MIE, SPP/
 * SPIE/SIE, SPV/GVA); they are handled by a bit-mask guard in tsbi_csr_set/clear,
 * not listed here, so their config fields (TW/SUM/MXR/FS...) still proxy fine.
 * ------------------------------------------------------------------- */
static inline bool tsbi_csr_is_trap_state(uint16_t csr)
{
    switch (csr) {
    case CSR_MEPC:   case CSR_MCAUSE: case CSR_MTVAL:
    case CSR_SEPC:   case CSR_SCAUSE: case CSR_STVAL:
    case CSR_MTVAL2: case CSR_MTINST:
    case CSR_HTVAL:  case CSR_HTINST:
    case CSR_VSEPC:  case CSR_VSCAUSE: case CSR_VSTVAL:
        return true;
    default:
        return false;
    }
}

/* -------------------------------------------------------------------
 * Proxy-safety guard for the caller-side CSR primitives (SECTION 8).
 *
 * A test that calls tsbi_csr_* has ALREADY decided the access must be
 * proxied (the current privilege cannot reach the CSR directly, otherwise
 * it would use csr_read()/csr_write()).  Two kinds of CSR must never be
 * proxied, because the proxy IS an ecall trap:
 *
 *   - fully trap-state CSRs (xepc/xcause/xtval/...): the trap entry
 *     overwrites the register before the handler can read it, so the value
 *     returned is the proxy's own state, not the caller's;
 *   - mstatus/sstatus return-path bits (MPP/MPIE/MIE/MPRV/MPV, SPP/SPIE/
 *     SIE): the serving handler's xret consumes them, so a proxied write
 *     corrupts the return path and lands the caller in the wrong privilege.
 *
 * `mask` is the bit mask for set/clear, ~0 for a full write, 0 for a read
 * (a read cannot corrupt the return path, so for reads only the fully
 * trap-state check applies).  The test is purely STATIC -- no privilege
 * query -- because choosing tsbi_csr_* over csr_read()/csr_write() already
 * encodes "this must be proxied".  To observe what a trap recorded use
 * trap_get_cause()/epc()/tval(); to SET a trap-state CSR use
 * mcsr_write()/mcsr_write_readback() inside a single M excursion.
 * ------------------------------------------------------------------- */
#define TSBI_MSTATUS_RETCTL  ((uintptr_t)(MSTATUS_MPP_MASK | MSTATUS_MPIE_BIT | \
                              MSTATUS_MIE_BIT  | MSTATUS_MPRV_BIT | MSTATUS_MPV))
#define TSBI_SSTATUS_RETCTL  ((uintptr_t)(MSTATUS_SPP_BIT | MSTATUS_SPIE_BIT | \
                              MSTATUS_SIE_BIT))

static inline bool tsbi_csr_proxy_unsafe(uint16_t csr, uintptr_t mask)
{
    if (tsbi_csr_is_trap_state(csr))
        return true;
    if (csr == CSR_MSTATUS && (mask & TSBI_MSTATUS_RETCTL))
        return true;
    if (csr == CSR_SSTATUS && (mask & TSBI_SSTATUS_RETCTL))
        return true;
    return false;
}

/* Reports a refused trap-state / return-path proxy and returns the reserved
 * sentinel so the caller's assertion fails loudly.  Defined out-of-line in
 * csr_accessors.c (LOG_E lives in a higher layer); tsbi.h only DECLARES it,
 * so there is no include inversion -- just a link-time symbol. */
extern uintptr_t tsbi_trap_state_guard(uint16_t csr, const char *op);

/* ===================================================================
 * SECTION 6: Trap-frame layout
 *
 * MUST stay in lockstep with SAVE_CONTEXT in common/trap_asm.S, which
 * stores x1..x31 at sp[0..30] such that sp[i] == x(i+1); the x2 (sp) slot
 * at index 1 is left unused.  Therefore:
 *     x10 (a0) -> frame[9]     x11 (a1) -> frame[10]
 *
 * The handler receives this array as its first argument and MUST write any
 * T-SBI return value into frame[TSBI_FRAME_A0]: RESTORE_CONTEXT reloads a0
 * from that slot, so a C `return` value only selects mret vs sret and never
 * reaches the caller.
 * =================================================================== */
#define TSBI_FRAME_RA   0   /* x1  */
#define TSBI_FRAME_A0   9   /* x10 - opcode in, result out */
#define TSBI_FRAME_A1   10  /* x11 - argument (CSR rs1 value / address) */
#define TSBI_FRAME_A2   11  /* x12 - value to store (memory proxy) */

/* ===================================================================
 * SECTION 7: PRIV_* <-> GOTO opcode mapping
 *
 * Both mappers below are written as comparison chains and MUST NOT be
 * turned back into `switch` statements.
 *
 * A dense `switch` is lowered by clang -O0 into a jump table dispatched
 * with `jr <reg>`.  Per the Zicfilp landing-pad-expectation rule
 * (SPEC/riscv-isa-manual/src/unpriv/cfi.adoc, IND_CALL_JMP):
 *
 *   is_lp_expected = ((JALR || C.JR || C.JALR) &&
 *                     (rs1 != x1) && (rs1 != x5) && (rs1 != x7)) ? 1 : 0
 *
 * a jump table whose index register is an ordinary data register arms
 * ELP, so the target's first instruction has to be an `lpad`.  This
 * framework is not compiled with landing pads, so such a jump raises a
 * software-check exception (cause=18, tval=2 "landing pad fault") as
 * soon as a test enables forward-edge CFI for HS-mode (menvcfg.LPE=1),
 * which the henvcfg tests legitimately do to make henvcfg.LPE writable.
 *
 * tsbi_priv_to_goto() sits on the HS->M excursion path, i.e. exactly the
 * path HYP_TEST_END() takes to reach hyp_reset_state()/reset_state(),
 * which is what clears menvcfg.LPE again.  An indirect jump here would
 * therefore fault before the cleanup ever runs.  gcc happens to emit a
 * comparison chain for the same source, which is why only clang builds
 * are affected.  Comparison chains contain no indirect branch and are
 * unaffected by menvcfg.LPE.
 *
 * Every PRIV_* / TSBI_GOTO_* value is listed explicitly (same order and
 * same one-to-one mapping as the operation-code table in SECTION 1); the
 * trailing return is the old `default:` arm, which falls back to M-mode
 * exactly as the switch did.
 * =================================================================== */
static inline uintptr_t tsbi_priv_to_goto(unsigned priv)
{
    if (priv == PRIV_M)  return TSBI_GOTO_MMODE;
    if (priv == PRIV_S)  return TSBI_GOTO_SMODE;
    if (priv == PRIV_U)  return TSBI_GOTO_UMODE;
    if (priv == PRIV_VS) return TSBI_GOTO_VSMODE;
    if (priv == PRIV_VU) return TSBI_GOTO_VUMODE;
    return TSBI_GOTO_MMODE;   /* default: out-of-range falls back to M-mode */
}

static inline unsigned tsbi_goto_to_priv(uintptr_t op)
{
    if (op == TSBI_GOTO_MMODE)  return PRIV_M;
    if (op == TSBI_GOTO_SMODE)  return PRIV_S;
    if (op == TSBI_GOTO_UMODE)  return PRIV_U;
    if (op == TSBI_GOTO_VSMODE) return PRIV_VS;
    if (op == TSBI_GOTO_VUMODE) return PRIV_VU;
    return PRIV_M;            /* default: out-of-range falls back to M-mode */
}

/* ===================================================================
 * SECTION 8: Caller-side primitives
 *
 * These are for TEST CODE only.  A trap handler that needs to forward a
 * request up the chain does NOT call these: it re-issues a bare ecall with
 * a0/a1 untouched (see tsbi_design_brief.md, FAQ).  Reasons: tsbi_ecall()
 * would overwrite the caller's a0/a1, and a C function's runtime
 * assumptions (valid C stack frame, free register allocation) do not hold
 * in trap context.
 * =================================================================== */
static inline uintptr_t tsbi_ecall(uintptr_t op, uintptr_t arg)
{
    register uintptr_t a0 asm("a0") = op;
    register uintptr_t a1 asm("a1") = arg;
    asm volatile ("ecall" : "+r"(a0) : "r"(a1) : "memory");
    return a0;
}

/* ECALL_TEST: returns the xEPC of the ecall itself (proves handler entry). */
static inline uintptr_t tsbi_ecall_test(void)
{
    return tsbi_ecall(TSBI_ECALL_TEST, 0);
}

/* CSR proxy.  Only READ returns a value; WRITE/SET/CLEAR encode rd=x0 and
 * therefore do NOT return the old value (issue a read first if needed).
 *
 * Each form is guarded by tsbi_csr_proxy_unsafe(): proxying a trap-state CSR
 * or an mstatus/sstatus return-path bit is REFUSED -- the read hands back
 * TSBI_RESERVED_RET and the writes are dropped -- so a misuse fails loudly
 * instead of silently returning clobbered state or corrupting the xret path.
 * Reaching for a direct csr_read()/csr_write() (or mcsr_write*() for
 * trap-state) is the caller's responsibility; these primitives never auto-
 * route, they always proxy. */
static inline uintptr_t tsbi_csr_read(uint16_t csr)
{
    if (tsbi_csr_proxy_unsafe(csr, 0))
        return tsbi_trap_state_guard(csr, "read");
    return tsbi_ecall(TSBI_CSR_READ_ENCODE(csr), 0);
}
static inline void tsbi_csr_write(uint16_t csr, uintptr_t val)
{
    if (tsbi_csr_proxy_unsafe(csr, ~(uintptr_t)0)) {
        (void)tsbi_trap_state_guard(csr, "write");
        return;
    }
    (void)tsbi_ecall(TSBI_CSR_WRITE_ENCODE(csr), val);
}
static inline void tsbi_csr_set(uint16_t csr, uintptr_t mask)
{
    if (tsbi_csr_proxy_unsafe(csr, mask)) {
        (void)tsbi_trap_state_guard(csr, "set");
        return;
    }
    (void)tsbi_ecall(TSBI_CSR_SET_ENCODE(csr), mask);
}
static inline void tsbi_csr_clear(uint16_t csr, uintptr_t mask)
{
    if (tsbi_csr_proxy_unsafe(csr, mask)) {
        (void)tsbi_trap_state_guard(csr, "clear");
        return;
    }
    (void)tsbi_ecall(TSBI_CSR_CLEAR_ENCODE(csr), mask);
}

/* Memory proxy: access physical address `pa` with the serving level's
 * privilege (mtime / MMIO).  Loads return the value in a0; stores hand the
 * value over in a2 (see SECTION 3 on the upstream register roles). */
static inline uintptr_t tsbi_lw(uintptr_t pa)  { return tsbi_ecall(TSBI_LW,  pa); }
static inline uintptr_t tsbi_lw4(uintptr_t pa) { return tsbi_ecall(TSBI_LW4, pa); }

static inline uintptr_t tsbi_ecall3(uintptr_t op, uintptr_t arg1, uintptr_t arg2)
{
    register uintptr_t a0 asm("a0") = op;
    register uintptr_t a1 asm("a1") = arg1;
    register uintptr_t a2 asm("a2") = arg2;
    asm volatile ("ecall" : "+r"(a0) : "r"(a1), "r"(a2) : "memory");
    return a0;
}

static inline void tsbi_sw(uintptr_t pa, uint32_t val)
{
    (void)tsbi_ecall3(TSBI_SW, pa, (uintptr_t)val);
}
static inline void tsbi_sw4(uintptr_t pa, uint32_t val)
{
    (void)tsbi_ecall3(TSBI_SW4, pa, (uintptr_t)val);
}

#if __riscv_xlen > 32
static inline uintptr_t tsbi_ld(uintptr_t pa)  { return tsbi_ecall(TSBI_LD,  pa); }
static inline void tsbi_sd(uintptr_t pa, uintptr_t val)
{
    (void)tsbi_ecall3(TSBI_SD, pa, val);
}
#endif

/* ===================================================================
 * SECTION 9: Control plane (escape hatch)
 *
 * Arm the next ecall to be treated as a plain test stimulus (recorded in
 * trap_record) instead of a T-SBI service request.  Consume-once: the
 * handler clears the flag the first time it sees it, so a framework ecall
 * issued right after (e.g. run_in_priv's return path) keeps normal T-SBI
 * semantics.  Needed because a raw stimulus ecall carries an uncontrolled
 * a0 that might otherwise be mistaken for an opcode.
 * =================================================================== */
void tsbi_arm_raw_ecall(bool skip_dispatch);

/* ===================================================================
 * SECTION 9b: Handler-side service stages (implemented in trap.c)
 *
 * FRAMEWORK-INTERNAL - test code must never call these.  They exist so the
 * HS-mode handler in common/hyp/hyp_trap.c can serve the protocol with the
 * very same code the S handler uses: HS is the S privilege level with V=0,
 * and while a test has _hs_trap_entry installed in stvec it is the only
 * S-level service point in existence.
 *
 * Call order in an S/HS-level handler is fixed:
 *     if (tsbi_s_proxy_capture(cause))                    return PRIV_S;
 *     if (!tsbi_raw_ecall_consume(cause) &&
 *         tsbi_s_dispatch(frame, cause, epc))             return PRIV_S;
 *     ... only now record the trap and handle it as an event ...
 * =================================================================== */

/* P0: claim a nested fault taken by an instruction the proxy injected.
 * True => return to the requester immediately, record nothing. */
bool tsbi_s_proxy_capture(uintptr_t cause);

/* P1: consume the raw-ecall escape flag.  True => this ecall is an armed
 * test stimulus and P2 must be skipped. */
bool tsbi_raw_ecall_consume(uintptr_t cause);

/* P2: serve the S/HS-level subset, forwarding the rest to M.
 * True => the request was disposed of; return to the requester at once. */
bool tsbi_s_dispatch(uintptr_t *frame, uintptr_t cause, uintptr_t epc);

#ifdef ENABLE_HYP
/* P2 for the VS level, used by vs_trap_handler in common/hyp/hyp_vs_trap.c.
 * P0 and P1 above are reused verbatim (they are privilege-agnostic: at V=1 the
 * plain S CSR names alias the virtual ones, so tsbi_s_proxy_capture's
 * CSRW(sepc, ...) redirects vsepc), which is why only this stage has a second
 * flavour - it is the only one whose served/forwarded split differs.
 *
 * Serves ECALL_TEST and U/S-level CSR access; forwards every GOTO, HS/M-level
 * CSR access and the memory proxy to HS, forming the VS->HS->M chain. */
bool tsbi_vs_dispatch(uintptr_t *frame, uintptr_t cause, uintptr_t epc);
#endif

/* ===================================================================
 * SECTION 10: Proxy engine interface (implemented in tsbi_proxy.c)
 *
 * Strategy A: the record is armed while an injected instruction runs.  If
 * that instruction faults, the nested trap is claimed by the handler's P0
 * stage, which records the cause and redirects xEPC to `recover`, so the
 * dispatch returns TSBI_RESERVED_RET instead of letting the fault escape
 * as an UNEXPECTED TRAP.
 * =================================================================== */
typedef volatile struct {
    bool      armed;      /* an injected instruction is executing */
    bool      faulted;    /* it took a nested trap */
    uintptr_t cause;      /* cause of that nested trap */
    uintptr_t recover;    /* resume PC: just after the injection call */
    uintptr_t status_snap;/* xstatus snapshot (MPP/MPV/MPRV) to restore */
} tsbi_proxy_record_t;

extern tsbi_proxy_record_t tsbi_proxy_record;

/* Execute a CSR instruction encoding on the caller's behalf.
 * @encoding: the CSR instruction word (see TSBI_CSR_*_ENCODE)
 * @rs1_val : value placed in a1 for WRITE/SET/CLEAR (ignored by READ)
 * Returns the CSR value for READ, or TSBI_RESERVED_RET if it faulted. */
uintptr_t tsbi_csr_access_dispatch(uint32_t encoding, uintptr_t rs1_val);

/* Execute a memory-proxy instruction word (TSBI_LW/LW4/LD/SW/SW4/SD).
 * @addr: physical address (goes to a1)
 * @val : value to store (goes to a2; ignored by loads)
 * Returns the loaded value, or TSBI_RESERVED_RET if it faulted. */
uintptr_t tsbi_mem_access_dispatch(uint32_t encoding, uintptr_t addr,
                                   uintptr_t val);

/* True if the last dispatch faulted (queried by tests doing negative checks). */
bool tsbi_proxy_faulted(void);

/* ===================================================================
 * SECTION 11: Compile-time protocol lock
 *
 * These guard the two things that silently break the protocol if they
 * drift: the opcode values (vs upstream) and the frame layout (vs
 * trap_asm.S SAVE_CONTEXT).
 * =================================================================== */
_Static_assert(TSBI_GOTO_MMODE  == 0x1u,  "GOTO_MMODE must match upstream");
_Static_assert(TSBI_GOTO_SMODE  == 0x2u,  "GOTO_SMODE must match upstream");
_Static_assert(TSBI_GOTO_UMODE  == 0x3u,  "GOTO_UMODE must match upstream");
_Static_assert(TSBI_GOTO_VSMODE == 0x4u,  "GOTO_VSMODE must match upstream");
_Static_assert(TSBI_GOTO_VUMODE == 0x5u,  "GOTO_VUMODE must match upstream");
_Static_assert(TSBI_ECALL_TEST  == 0x73u, "ECALL_TEST must match upstream");

/* Encoding templates must reproduce the documented example words:
 *   csrrs a0, mstatus, x0  == 0x30002573   (READ  mstatus 0x300)
 *   csrrs x0, mstatus, a1  == 0x3005a073   (SET   mstatus)
 *   csrrs a0, mip, x0      == 0x34402573   (READ  mip     0x344) */
_Static_assert(TSBI_CSR_READ_ENCODE(0x300) == 0x30002573u, "CSR READ template");
_Static_assert(TSBI_CSR_SET_ENCODE(0x300)  == 0x3005A073u, "CSR SET template");
_Static_assert(TSBI_CSR_READ_ENCODE(0x344) == 0x34402573u, "CSR READ (mip)");

/* Frame layout: a0/a1/a2 slots follow sp[i] == x(i+1) from SAVE_CONTEXT. */
_Static_assert(TSBI_FRAME_A0 == 9,  "a0 slot must match SAVE_CONTEXT layout");
_Static_assert(TSBI_FRAME_A1 == 10, "a1 slot must match SAVE_CONTEXT layout");
_Static_assert(TSBI_FRAME_A2 == 11, "a2 slot must match SAVE_CONTEXT layout");

/* Privilege encodings used by the GOTO mapping. */
_Static_assert(PRIV_U == 0 && PRIV_S == 1 && PRIV_M == 3,
               "PRIV_* encodings changed; revisit tsbi_priv_to_goto()");
_Static_assert(PRIV_VU == 4 && PRIV_VS == 5,
               "virtualised PRIV_* encodings changed; revisit GOTO mapping");

#endif /* COMMON_TSBI_H */
