/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef COMMON_TEST_FRAMEWORK_H
#define COMMON_TEST_FRAMEWORK_H

#include "types.h"
#include "encoding.h"
#include "uart.h"
#include "mem_ops.h"
#include "tsbi/tsbi.h"
#include "csr_accessors.h"   /* by-number CSR access: csr_read/write + tsbi_csr_* */

/* ===================================================================
 * Compiler Identification
 *
 * Detects the compiler (GCC or Clang) at compile time and exposes a
 * concise version string for use in test banners.
 * =================================================================== */
#define _TF_STRINGIFY(x) #x
#define _TF_STR(x) _TF_STRINGIFY(x)

#ifdef __clang__
    #define COMPILER_INFO "Clang " _TF_STR(__clang_major__) "." _TF_STR(__clang_minor__) "." _TF_STR(__clang_patchlevel__)
#elif defined(__GNUC__)
    #define COMPILER_INFO "GCC " _TF_STR(__GNUC__) "." _TF_STR(__GNUC_MINOR__) "." _TF_STR(__GNUC_PATCHLEVEL__)
#else
    #define COMPILER_INFO "Unknown"
#endif

/* ===================================================================
 * Test Function Type and Registration
 * =================================================================== */

typedef bool (*test_func_t)(void);

/**
 * TEST_REGISTER - Register a test function for automatic execution
 *
 * Usage:
 *   TEST_REGISTER(test_pmp_napot_rwx);
 *   bool test_pmp_napot_rwx(void) {
 *       TEST_BEGIN("PMP NAPOT RWX");
 *       // ... test logic ...
 *       TEST_END();
 *   }
 *
 * The test function pointer is placed in the .test_table section,
 * which is collected by the linker script.
 */
#define TEST_REGISTER(test_fn) \
    bool test_fn(void); \
    static test_func_t test_fn##_ptr \
        __attribute__((section(".test_table"), used)) = test_fn

/* ===================================================================
 * Test Result Tracking
 * =================================================================== */

#define MAX_FAILED_TESTS  16
#define MAX_SKIPPED_TESTS 16

typedef struct {
    unsigned int total;
    unsigned int passed;
    unsigned int failed;
    unsigned int skipped;
    unsigned int tests_passed;
    unsigned int tests_failed;
    const char  *current_test_name;
    bool         current_test_failed;
    const char  *failed_names[MAX_FAILED_TESTS];
    unsigned int failed_count;
    const char  *skipped_names[MAX_SKIPPED_TESTS];
    const char  *skipped_reasons[MAX_SKIPPED_TESTS];
    unsigned int skipped_count;
} test_result_t;

extern test_result_t test_results;

/* ===================================================================
 * Test Lifecycle Macros
 * =================================================================== */

/* Simple substring search for bare-metal filter (no libc) */
static inline const char *_tf_strstr(const char *h, const char *n) {
    if (!*n) return h;
    for (; *h; h++) {
        const char *hp = h, *np = n;
        while (*hp && *np && *hp == *np) { hp++; np++; }
        if (!*np) return h;
    }
    return (const char *)0;
}

/**
 * TEST_BEGIN - Start a test case
 *
 * Initializes per-test state and prints the test name.
 * When TEST_FILTER is defined, tests whose name does not contain
 * the filter string are silently skipped (return true).
 */
#define TEST_BEGIN(name) do { \
    test_results.current_test_name = (name); \
    test_results.current_test_failed = false; \
    TEST_FILTER_CHECK(name); \
    printf("[TEST] %s\n", (name)); \
} while (0)

#ifdef TEST_FILTER
#define TEST_FILTER_CHECK(name) do { \
    if (!_tf_strstr((name), TEST_FILTER)) { \
        return true; \
    } \
} while (0)
#else
#define TEST_FILTER_CHECK(name) ((void)0)
#endif

/**
 * Fail-fast support (build with FAIL_FAST=1, see Makefile.common)
 *
 * When TEST_FAIL_FAST is defined, the suite halts immediately after a
 * test case fails instead of running the remaining cases. A partial
 * summary is printed before halting so the stop point is visible.
 * _halt_fail() terminates the simulation with fail status via
 * RVMODEL_HALT_FAIL (on HW it spins).
 */
#ifdef TEST_FAIL_FAST
int test_print_summary(void);
extern void _halt_fail(void) __attribute__((noreturn));

static inline void _test_fail_fast(void) {
    printf("[FAIL-FAST] halting at first failed test\n");
    test_print_summary();
    _halt_fail();
}

/* TEST_FATAL variant: count the aborted test as failed before halting,
 * so the partial summary reflects it. */
static inline void _test_fatal_fail_fast(void) {
    test_results.tests_failed++;
    _test_fail_fast();
}
#define IF_FAIL_FATAL() _test_fatal_fail_fast()
#else
#define IF_FAIL_FATAL() ((void)0)
#endif

/**
 * _test_end_record - Common test-end bookkeeping (statistics + print)
 *
 * Shared by TEST_END() and HYP_TEST_END() to avoid duplicating the
 * pass/fail tracking logic. Each caller is responsible for invoking
 * its own reset function before calling this.
 *
 * Returns the pass/fail result (true = passed).
 */
static inline bool _test_end_record(void) {
    if (test_results.current_test_failed) {
        test_results.tests_failed++;
        if (test_results.failed_count < MAX_FAILED_TESTS) {
            test_results.failed_names[test_results.failed_count++] =
                test_results.current_test_name;
        }
        printf("[FAIL] %s\n\n", test_results.current_test_name);
#ifdef TEST_FAIL_FAST
        _test_fail_fast(); /* noreturn */
#endif
    } else {
        test_results.tests_passed++;
        printf("[PASS] %s\n\n", test_results.current_test_name);
    }
    return !test_results.current_test_failed;
}

/**
 * TEST_EXIT_RESET - the reset every test-exit macro performs
 *
 * A single seam so the three exit macros below cannot drift apart.  The base
 * definition is reset_state(); hyp_test.h overrides it so H-aware suites also
 * clear hypervisor state on the way out.  It has to be a macro rather than a
 * function pointer because the override must apply per translation unit: a
 * suite that never includes hyp_test.h is not linked against the H reset at
 * all (hyp_reset.o is built only under ENABLE_HYP).
 *
 * Overriding this instead of the exit macros themselves keeps the bookkeeping
 * in one place - the counters and the printf stay here, and an override cannot
 * fall behind by copying an older version of them.
 */
#define TEST_EXIT_RESET() reset_state()

/**
 * TEST_END - End a test case
 *
 * Raises to M-mode for the reset work, then TEST_EXIT_RESET() hands control
 * back to the S-mode normal state (see tsbi_design_brief.md section 1), so
 * the next test starts in S-mode.  Prints PASS/FAIL.
 * Returns true if all assertions passed.
 *
 * With -DTSBI_BOOT_MODE_M the framework stays in M-mode throughout.
 */
#define TEST_END() do { \
    goto_priv(PRIV_M); \
    TEST_EXIT_RESET(); \
    return _test_end_record(); \
} while (0)

/**
 * TEST_SKIP - Skip a test case with a reason
 *
 * Increments the skipped counter, prints [SKIP], restores state,
 * and returns true (skip is not a failure).
 */
#define TEST_SKIP(reason) do { \
    test_results.skipped++; \
    if (test_results.skipped_count < MAX_SKIPPED_TESTS) { \
        test_results.skipped_names[test_results.skipped_count] = \
            test_results.current_test_name; \
        test_results.skipped_reasons[test_results.skipped_count] = (reason); \
        test_results.skipped_count++; \
    } \
    printf("[SKIP] %s: %s\n\n", test_results.current_test_name, (reason)); \
    goto_priv(PRIV_M); \
    TEST_EXIT_RESET(); \
    return true; \
} while (0)

/**
 * TEST_FATAL - Unconditionally fail the current test with a reason
 *
 * Use when a code path that should be unreachable is reached,
 * or to explicitly mark a test as failed with a descriptive message.
 */
#define TEST_FATAL(reason) do { \
    test_results.total++; \
    test_results.failed++; \
    test_results.current_test_failed = true; \
    printf("[FATAL] %s: %s\n\n", test_results.current_test_name, (reason)); \
    goto_priv(PRIV_M); \
    TEST_EXIT_RESET(); \
    IF_FAIL_FATAL(); \
    return false; \
} while (0)

/* ===================================================================
 * Assertion Macros
 * =================================================================== */

/**
 * TEST_ASSERT - Check a boolean condition
 */
#define TEST_ASSERT(msg, cond) do { \
    test_results.total++; \
    if (cond) { \
        test_results.passed++; \
    } else { \
        test_results.failed++; \
        test_results.current_test_failed = true; \
        printf("  ASSERT FAIL: %s (%s:%d)\n", (msg), __FILE__, __LINE__); \
    } \
} while (0)

/**
 * TEST_ASSERT_EQ - Check equality of two values
 */
#define TEST_ASSERT_EQ(msg, actual, expected) do { \
    test_results.total++; \
    if ((uintptr_t)(actual) == (uintptr_t)(expected)) { \
        test_results.passed++; \
    } else { \
        test_results.failed++; \
        test_results.current_test_failed = true; \
        printf("  ASSERT FAIL: %s: got 0x%lx, expected 0x%lx (%s:%d)\n", \
               (msg), (unsigned long)(actual), (unsigned long)(expected), \
               __FILE__, __LINE__); \
    } \
} while (0)

/**
 * TEST_ASSERT_NEQ - Check inequality of two values
 *
 * Asserts that actual != not_expected. On failure, prints the value
 * that should NOT have been equal.
 */
#define TEST_ASSERT_NEQ(msg, actual, not_expected) do { \
    test_results.total++; \
    if ((uintptr_t)(actual) != (uintptr_t)(not_expected)) { \
        test_results.passed++; \
    } else { \
        test_results.failed++; \
        test_results.current_test_failed = true; \
        printf("  ASSERT FAIL: %s: got 0x%lx, should NOT equal 0x%lx (%s:%d)\n", \
               (msg), (unsigned long)(actual), (unsigned long)(not_expected), \
               __FILE__, __LINE__); \
    } \
} while (0)

/**
 * TEST_ASSERT_BITS - Check specific bit field of a value
 *
 * Extracts (value & mask) and compares with (expected & mask).
 * On failure, prints the full value, mask, and extracted field values.
 *
 * Useful for verifying CSR bit fields (e.g., mseccfg.MML, hstatus.SPV).
 */
#define TEST_ASSERT_BITS(msg, value, mask, expected) do { \
    test_results.total++; \
    uintptr_t _val = (uintptr_t)(value); \
    uintptr_t _mask = (uintptr_t)(mask); \
    uintptr_t _exp = (uintptr_t)(expected); \
    if ((_val & _mask) == (_exp & _mask)) { \
        test_results.passed++; \
    } else { \
        test_results.failed++; \
        test_results.current_test_failed = true; \
        printf("  ASSERT FAIL: %s: value=0x%lx, mask=0x%lx, " \
               "got field 0x%lx, expected field 0x%lx (%s:%d)\n", \
               (msg), (unsigned long)_val, (unsigned long)_mask, \
               (unsigned long)(_val & _mask), (unsigned long)(_exp & _mask), \
               __FILE__, __LINE__); \
    } \
} while (0)


/* ===================================================================
 * Exception Test Macros
 *
 * These macros wrap a statement with trap arming/disarming and
 * automatically check whether the expected exception occurred.
 * =================================================================== */

/* Forward declarations from trap.c */
extern void trap_expect_begin(void);
extern void trap_expect_end(void);
extern void trap_clear_record(void);
extern bool trap_was_triggered(void);
extern uintptr_t trap_get_cause(void);
extern uintptr_t trap_get_epc(void);
extern uintptr_t trap_get_tval(void);
extern uintptr_t trap_get_status_snap(void);

/* Snapshot of the trap record; trap_snapshot_t is defined in types.h */
extern void trap_snapshot(trap_snapshot_t *snap);

/* Automatic snapshot of a double-trap (cause 16) record, taken by the
 * M-mode handler before a possible second delivery overwrites the
 * record.  Reset trap_dt_snap_valid before triggering. */
extern trap_snapshot_t trap_dt_snap;
extern bool trap_dt_snap_valid;

/* Trap entry trace (diagnostic): record the last few trap entries and
 * dump them on UNEXPECTED TRAP.  Off by default, zero overhead. */
extern void trap_trace_on(void);
extern void trap_trace_off(void);

/* CFI (Zicfilp) PELP control flags (defined in trap.c).
 * Default 0 = no impact on existing suites. Tests set these to
 * verify hardware xRET xpelp handling. See trap.c for details. */
extern bool g_trap_preserve_pelp;
extern bool g_trap_force_pelp;

/* ===================================================================
 * Double Trap (Smdbltrp) Support
 *
 * On CPUs with Smdbltrp, mstatus.MDT (bit 42) is set to 1 on reset
 * and on every M-mode trap entry. While MDT=1, any synchronous
 * exception in M-mode triggers a fatal double trap instead of
 * entering the trap handler normally.
 *
 * mret clears MDT automatically, but if M-mode code *expects* to
 * trigger a trap (e.g., probing whether a CSR exists), MDT must be
 * cleared explicitly before the trapping instruction.
 *
 * Use M_TRAP_EXPECT_BEGIN / M_EXPECT_TRAP / M_EXPECT_NO_TRAP
 * instead of their plain counterparts when the protected operation
 * runs in M-mode and may raise a synchronous exception.
 *
 * T-SBI S-mode-normal note: mstatus(.h).MDT is M-mode-only state, so
 * a bare CSRC/CSRS/CSRR of it from S/U-mode is an illegal instruction
 * (scause=2). Under the S-mode-normal model main() and most stimuli run
 * in S-mode, where there is no M-double-trap exposure at all -- the MDT
 * helpers therefore guard the raw access on get_current_priv()==PRIV_M
 * and degrade to a no-op / false elsewhere. This keeps the exact
 * behaviour for M-mode callers (reset_state(), genuine M-mode stimuli)
 * while making M_TRAP_EXPECT_* safe to arm from S-mode.
 * =================================================================== */

#ifdef SMDBLTRP_SUPPORTED
#if __riscv_xlen == 64
#define MSTATUS_MDT_BIT  (1UL << 42)
static inline void clear_mdt(void) {
    if (get_current_priv() == PRIV_M)
        CSRC(mstatus, MSTATUS_MDT_BIT);
}
static inline void set_mdt(void) {
    if (get_current_priv() == PRIV_M)
        CSRS(mstatus, MSTATUS_MDT_BIT);
}
static inline bool get_mdt(void) {
    if (get_current_priv() != PRIV_M)
        return false;
    return (CSRR(mstatus) & MSTATUS_MDT_BIT) != 0;
}
#else
/* On RV32, mstatus.MDT is bit 42 of the full 64-bit mstatus register.
 * The low 32 bits are accessed via mstatus, the high 32 bits via mstatush.
 * bit 42 = mstatush bit (42-32) = bit 10. */
#define MSTATUSH_MDT_BIT  (1UL << 10)
static inline void clear_mdt(void) {
    if (get_current_priv() == PRIV_M)
        CSRC(CSR_MSTATUSH, MSTATUSH_MDT_BIT);
}
static inline void set_mdt(void) {
    if (get_current_priv() == PRIV_M)
        CSRS(CSR_MSTATUSH, MSTATUSH_MDT_BIT);
}
static inline bool get_mdt(void) {
    if (get_current_priv() != PRIV_M)
        return false;
    return (CSRR(CSR_MSTATUSH) & MSTATUSH_MDT_BIT) != 0;
}
#endif
#else
static inline void clear_mdt(void) { /* no-op */ }
static inline void set_mdt(void) { /* no-op */ }
static inline bool get_mdt(void) { return false; }
#endif

/**
 * M_TRAP_EXPECT_BEGIN - Like trap_expect_begin, but first clears
 * mstatus.MDT on platforms with Smdbltrp so the expected trap
 * does not cause a double trap.
 */
#define M_TRAP_EXPECT_BEGIN() do { \
    clear_mdt(); \
    trap_expect_begin(); \
} while (0)

/**
 * M_EXPECT_TRAP - Like EXPECT_TRAP, but clears MDT first.
 */
#define M_EXPECT_TRAP(expected_cause, stmt) do { \
    clear_mdt(); \
    EXPECT_TRAP(expected_cause, stmt); \
} while (0)

/**
 * M_EXPECT_NO_TRAP - Like EXPECT_NO_TRAP, but clears MDT first.
 */
#define M_EXPECT_NO_TRAP(stmt) do { \
    clear_mdt(); \
    EXPECT_NO_TRAP(stmt); \
} while (0)

/**
 * EXPECT_NO_TRAP - Execute stmt and assert no exception occurs
 *
 * Must only be used in M-mode. In S/U-mode, use PRIV_DO + CHECK_NO_TRAP instead.
 */
#define EXPECT_NO_TRAP(stmt) do { \
    trap_expect_begin(); \
    stmt; \
    TEST_ASSERT("no trap", !trap_was_triggered()); \
    trap_expect_end(); \
} while (0)

/**
 * EXPECT_TRAP - Execute stmt and assert a specific exception occurs
 *
 * Must only be used in M-mode. In S/U-mode, use PRIV_DO + CHECK_TRAP instead.
 */
#define EXPECT_TRAP(expected_cause, stmt) do { \
    trap_expect_begin(); \
    stmt; \
    TEST_ASSERT("trap triggered", trap_was_triggered()); \
    if (trap_was_triggered()) { \
        TEST_ASSERT_EQ("cause matches", trap_get_cause(), (expected_cause)); \
    } \
    trap_expect_end(); \
} while (0)

/**
 * EXPECT_EXEC_TRAP - Jump to addr and assert instruction access fault
 *
 * Uses exec_at() which saves return_addr for trap recovery.
 */
#define EXPECT_EXEC_TRAP(expected_cause, addr) do { \
    trap_expect_begin(); \
    exec_at(addr); \
    TEST_ASSERT("exec trap triggered", trap_was_triggered()); \
    if (trap_was_triggered()) { \
        TEST_ASSERT_EQ("exec cause matches", trap_get_cause(), (expected_cause)); \
    } \
    trap_expect_end(); \
} while (0)

/**
 * EXPECT_EXEC_NO_TRAP - Jump to addr and assert no exception
 */
#define EXPECT_EXEC_NO_TRAP(addr) do { \
    trap_expect_begin(); \
    exec_at(addr); \
    TEST_ASSERT("exec no trap", !trap_was_triggered()); \
    trap_expect_end(); \
} while (0)

/* ===================================================================
 * CSR existence probe (M-mode, trap-armed)
 *
 * PROBE_CSR(csr_num, out_val) - Attempts to read a CSR with trap
 * arming. Evaluates to true if the CSR is accessible (no trap),
 * storing the read value into *(out_val). Must run in M-mode.
 * =================================================================== */
#define PROBE_CSR(csr_num, out_val) ({ \
    uintptr_t _probe_v = 0; \
    bool _probe_ok; \
    M_TRAP_EXPECT_BEGIN(); \
    asm volatile ("csrr %0, " CSR_STR(csr_num) : "=r"(_probe_v)); \
    _probe_ok = !trap_was_triggered(); \
    trap_expect_end(); \
    if (_probe_ok) \
        *(out_val) = _probe_v; \
    _probe_ok; \
})

/* ===================================================================
 * S/U-mode safe trap macros
 *
 * When running in S-mode or U-mode, printf (UART access) is not
 * available. Use PRIV_DO_* to arm/execute/disarm in privileged mode,
 * then return to M-mode and use CHECK_* to assert results.
 *
 * Pattern:
 *   goto_priv(PRIV_S);
 *   PRIV_DO_NO_TRAP(mem_load8(addr));   // arm + execute + disarm, no printf
 *   goto_priv(PRIV_M);
 *   CHECK_NO_TRAP("read succeeded");    // assert in M-mode (printf OK)
 * =================================================================== */

/**
 * PRIV_DO - Arm trap, execute stmt, disarm. No printf.
 *
 * Use in S/U-mode where UART is inaccessible. After returning to
 * M-mode, use CHECK_NO_TRAP or CHECK_TRAP to assert the result.
 *
 * The trap arming/disarming is identical regardless of whether a
 * trap is expected; the expectation is expressed by the CHECK_*
 * macro used afterwards.
 */
#define PRIV_DO(stmt) do { \
    trap_expect_begin(); \
    (void)(stmt); \
    trap_expect_end(); \
} while (0)

/**
 * PRIV_DO_EXEC - Arm trap, exec_at(addr), disarm. No printf.
 *
 * Use in S/U-mode for testing instruction execution permissions.
 * After returning to M-mode, use CHECK_NO_TRAP or CHECK_TRAP.
 */
#define PRIV_DO_EXEC(addr) do { \
    trap_expect_begin(); \
    exec_at(addr); \
    trap_expect_end(); \
} while (0)

/* Backward-compatible aliases (deprecated — prefer PRIV_DO / PRIV_DO_EXEC) */
#define PRIV_DO_NO_TRAP(stmt)       PRIV_DO(stmt)
#define PRIV_DO_TRAP(stmt)          PRIV_DO(stmt)
#define PRIV_DO_EXEC_NO_TRAP(addr)  PRIV_DO_EXEC(addr)
#define PRIV_DO_EXEC_TRAP(addr)     PRIV_DO_EXEC(addr)

/**
 * CHECK_NO_TRAP - Assert that the last PRIV_DO_NO_TRAP did not trigger a trap.
 * Must be called in M-mode after goto_priv(PRIV_M).
 */
#define CHECK_NO_TRAP(msg) do { \
    TEST_ASSERT(msg, !trap_was_triggered()); \
} while (0)

/**
 * CHECK_TRAP - Assert that the last PRIV_DO_TRAP triggered the expected trap.
 * Must be called in M-mode after goto_priv(PRIV_M).
 */
#define CHECK_TRAP(msg, expected_cause) do { \
    TEST_ASSERT(msg ": trap triggered", trap_was_triggered()); \
    if (trap_was_triggered()) { \
        TEST_ASSERT_EQ(msg ": cause", trap_get_cause(), (uintptr_t)(expected_cause)); \
    } \
} while (0)

/* ===================================================================
 * Privilege Level Definitions and API
 *
 * PRIV_U/S/M/VU/VS are defined in encoding.h.
 * =================================================================== */

extern void goto_priv(unsigned target);
extern unsigned get_current_priv(void);
extern uintptr_t run_in_priv(unsigned priv, uintptr_t (*fn)(uintptr_t), uintptr_t arg);

/* Canonical T-SBI-prefixed names (see DOCS/framework/tsbi_design_brief.md).
 * New code should use these; goto_priv/run_in_priv stay valid as the historical
 * spelling so the ~2500 existing call sites need no churn. */
#define tsbi_goto_priv    goto_priv
#define tsbi_run_in_priv  run_in_priv

/* The by-number CSR access layer -- direct csr_read()/csr_write(), the T-SBI
 * tsbi_csr_read/write/set/clear() proxy primitives with their guard, and
 * the mcsr_write()/mcsr_write_readback() M-excursion accessors -- lives in
 * csr_accessors.h (included at the top of this header); csr_ops.h (the named
 * accessors) builds on it too. Keeping the CSR-access mechanism in that one
 * lower-level header avoids a dependency inversion (csr_ops.h -> here). */

/* ===================================================================
 * Delegation control (implemented in tsbi/tsbi_deleg.c)
 *
 * The baseline is delegation-first, so the DELEGATED leg comes for free and
 * a test that wants to observe "this trap must land in M" has to switch the
 * cause out explicitly.  reset_state() restores the baseline afterwards.
 *
 * Both must run with M-mode authority (inside an M excursion, or from a
 * test already in M).  trap_delegate_exc() refuses ecall-from-S: delegating
 * it would break the T-SBI service channel and dead-loop run_in_priv().
 * =================================================================== */
extern bool tsbi_delegate_exc(unsigned cause);
extern bool tsbi_undelegate_exc(unsigned cause);
extern void tsbi_deleg_apply_baseline(void);
extern void tsbi_deleg_restore_baseline(void);
extern uintptr_t tsbi_deleg_effective_medeleg(void);
extern uintptr_t tsbi_deleg_effective_mideleg(void);

/* M-safe bulk delegation setters: OR / clear bits in medeleg (exc_mask) and
 * mideleg (int_mask), raising to M internally so they are callable from
 * S(HS)-mode.  Single source of truth shared by the H-extension delegation
 * helpers; tsbi_deleg_or() keeps the medeleg[9] invariant.  See tsbi/tsbi_deleg.c. */
extern void tsbi_deleg_or(uintptr_t exc_mask, uintptr_t int_mask);
extern void tsbi_deleg_clear(uintptr_t exc_mask, uintptr_t int_mask);

/* Framework-facing aliases (naming kept close to the trap_* family). */
#define trap_delegate_exc(cause)    tsbi_delegate_exc(cause)
#define trap_undelegate_exc(cause)  tsbi_undelegate_exc(cause)

#ifdef ENABLE_HYP
/* Hypervisor trap-record extensions.  Available after a guest-page-fault /
 * virtual-instruction trap, wherever it was taken: these are defined in
 * common/hyp/hyp_trap.c and answer from the HS-mode record when the trap was
 * delegated there by hedeleg, falling back to the M-mode snapshots below
 * otherwise.  Same arrangement as trap_get_spv()/trap_get_spv_snap().
 *
 * Note that trap_get_cause()/epc()/tval() are NOT merged this way.  They are
 * the generic accessors, paired with the armed/triggered handshake behind
 * EXPECT_TRAP, and the HS handler records unconditionally - it has no armed
 * check.  Folding it in would make an HS trap satisfy an M-mode EXPECT_TRAP.
 * A test watching an hedeleg-delegated trap reads hs_trap_get_cause() instead
 * (common/hyp/hyp_trap.h). */
extern uintptr_t trap_get_htval(void);
extern uintptr_t trap_get_htinst(void);
extern bool      trap_get_gva(void);

/* The M-mode record's own view of the three above, for the fallback path. */
extern uintptr_t trap_get_htval_snap(void);
extern uintptr_t trap_get_htinst_snap(void);
extern bool      trap_get_gva_snap(void);

/* mstatus.MPV/MPP snapshots captured at M-mode trap entry, before
 * the handler modifies them. Used to verify hardware auto-writes on
 * trap entry (e.g. HCFI-LP-41 trap from VS-mode). */
extern bool      trap_get_mpv(void);
extern uintptr_t trap_get_mpp(void);

/* hstatus.SPV snapshot captured at trap entry (M or S mode handler).
 * Used by trap_get_spv() as a fallback when the trap did not go
 * through hs_trap_handler (e.g. LP-36/40 via s_trap_handler). */
extern bool      trap_get_spv_snap(void);
#endif

/* ===================================================================
 * State Management
 * =================================================================== */

/**
 * trap_probe_mtval2 - Detect mtval2 CSR availability
 *
 * Probes mtval2 (0x34B) with a trap-protected read and records the
 * result for the trap handlers. mtval2 exists when the Hypervisor
 * extension or Ssdbltrp is implemented (norm:mtval2_Ssdbltrap); the
 * m_trap_handler reads it only when this probe found it, avoiding
 * an infinite nested-trap loop on platforms without it.
 * Called automatically by reset_state() after trap vectors are set up.
 */
void trap_probe_mtval2(void);

/**
 * trap_set_mtval2_present - Override the mtval2 availability gate
 *
 * Sets the handler-side gate directly without trapping. Needed by
 * tests that transiently disable the H extension at runtime (e.g.
 * clearing misa.H): suppress the entry-time mtval2 read while H is
 * disabled, then call trap_probe_mtval2() after restoring.
 */
void trap_set_mtval2_present(bool present);

/**
 * reset_state - Reset all PMP and test state
 *
 * Clears all PMP entries, resets mseccfg, returns to M-mode.
 */
void reset_state(void);

/**
 * test_print_banner - Print test suite banner
 *
 * Prints a standardized banner with platform info (Platform, XLEN,
 * Compiler, MEM_BASE, MEM_SIZE). Call at the start of main() before
 * running tests. Extension-specific info can be printed after this.
 */
void test_print_banner(const char *title);

/**
 * test_print_summary - Print final test results
 */
int test_print_summary(void);

/* ===================================================================
 * Log Level Macros
 * =================================================================== */

#ifndef LOG_LEVEL
#define LOG_LEVEL 3
#endif

#define LOG_NONE    0
#define LOG_ERROR   1
#define LOG_WARN    2
#define LOG_INFO    3
#define LOG_DEBUG   4
#define LOG_TRACE   5
#define LOG_VERBOSE 6

#define LOG_E(fmt, ...) do { if (LOG_LEVEL >= LOG_ERROR)   printf("  [ERROR] " fmt, ##__VA_ARGS__); } while(0)
#define LOG_W(fmt, ...) do { if (LOG_LEVEL >= LOG_WARN)    printf("  [WARN] " fmt, ##__VA_ARGS__); } while(0)
#define LOG_I(fmt, ...) do { if (LOG_LEVEL >= LOG_INFO)    printf("  [INFO] " fmt, ##__VA_ARGS__); } while(0)
#define LOG_D(fmt, ...) do { if (LOG_LEVEL >= LOG_DEBUG)   printf("  [DEBUG] " fmt, ##__VA_ARGS__); } while(0)
#define LOG_T(fmt, ...) do { if (LOG_LEVEL >= LOG_TRACE)   printf("  [TRACE] " fmt, ##__VA_ARGS__); } while(0)
#define LOG_V(fmt, ...) do { if (LOG_LEVEL >= LOG_VERBOSE) printf("  [VERBOSE] " fmt, ##__VA_ARGS__); } while(0)

/* ===================================================================
 * Instruction-retirement workload helper
 *
 * Executes `count` NOPs to create a measurable number of retired
 * instructions (used by counter / HPM tests). This is the single
 * authoritative implementation; suites must not keep a local copy.
 * =================================================================== */
static inline void execute_nops(unsigned count)
{
    for (volatile unsigned i = 0; i < count; i++) {
        asm volatile("nop");
    }
}

#endif /* COMMON_TEST_FRAMEWORK_H */
