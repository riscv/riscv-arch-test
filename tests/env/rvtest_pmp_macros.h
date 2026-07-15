// rvtest_pmp_macros.h
// PMP R/W/X verification macros for the PMP test suite (tests/priv/pmp/...).
// SPDX-License-Identifier: Apache-2.0
//
// Shared, centralized versions of the per-test PMP_VERIFICATION_* macros. Each macro
// probes how a PMP-protected region responds to execute / store / load accesses and
// records the outcome with RVTEST_SIGUPD. Defined here (instead of redefined in every
// test) so cross-cutting fixes — e.g. inserting RVTEST_FENCEI to sync the I-cache
// after writing executable code — are made in one place. RVTEST_FENCEI is
// self-disabling: fence.i only when Zifencei is supported, otherwise nop.
//
// Included from riscv_arch_test.h after rvtest_config.h / utils.h / signature.h, so
// UDB_PMP_GRANULARITY, NOP/DOUBLE_NOP, LA/LI and RVTEST_SIGUPD are all available.
//
// Contract for callers (must hold in each test that uses these):
//   - Signature pointer / temp registers x2, x5, x4 follow suite convention.
//   - The string labels test_<n>_str referenced below are defined in the test's
//     RVTEST_DATA section, with SIGUPD_COUNT sized accordingly.
//
// These are GAS (.macro) definitions; a test that uses one must NOT also define a
// local .macro of the same name (GAS errors on macro redefinition).
//==============================================================================

// PMP_NAPOT_REGION_PAD_WORDS: number of 4-byte filler words to emit before a NAPOT
// region-under-test so the region lands on the next g_napot-aligned boundary
// (0x80005008 at coverage grain 2). This makes the region's pmpaddr encode a *clean*
// NAPOT region that matches the coverage model's STANDARD_REGION / PMP_NAPOT_REGION_START
// and does NOT swallow the return-instruction pad (which would give a 16-byte region and
// hang execute probes). g_napot = (GRAN>3) ? 2^GRAN : 2^(GRAN+1); words = g_napot/4.
// (GAS .rept cannot evaluate a C ternary, so the branch is done with the preprocessor.)
#if UDB_PMP_GRANULARITY > 3
  #define PMP_NAPOT_REGION_PAD_WORDS (1 << (UDB_PMP_GRANULARITY - 2))
#else
  #define PMP_NAPOT_REGION_PAD_WORDS (1 << (UDB_PMP_GRANULARITY - 1))
#endif

// PMP_VERIFICATION_X_C: compressed execute-only check.
// Jumps (c.jalr) to ADDRESS and records whether execution was permitted.
// No store occurs, so no RVTEST_FENCEI is required.
//   ADDRESS   - region label to execute from
//   TEST_CASE - prefix for the local result label (TEST_CASE_1)
.macro PMP_VERIFICATION_X_C ADDRESS, TEST_CASE
    \TEST_CASE\()_1:
    LA(x15, \ADDRESS)               // Address to be verified
    c.jalr x15
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)
.endm

// PMP_VERIFICATION_CBO: cache-block-operation permission check (the Zicbo cbo_wr family).
// Runs cbo.zero/clean/flush/inval on ADDRESS and records each outcome. No jump and no
// ordinary store, so no RVTEST_FENCEI is required.
//   ADDRESS   - cache-block-aligned region label
//   TEST_CASE - prefix for the local result labels (TEST_CASE_1 .. _4)
.macro PMP_VERIFICATION_CBO ADDRESS, TEST_CASE
    // Address must be aligned to the cache block
    LA(a4, \ADDRESS)

    \TEST_CASE\()_1:
    cbo.zero  (a4)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)

    \TEST_CASE\()_2:
    cbo.clean (a4)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)

    \TEST_CASE\()_3:
    cbo.flush (a4)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)

    \TEST_CASE\()_4:
    cbo.inval (a4)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_4, test_4_str)
.endm

// PMP_VERIFICATION_RWX: basic word-width R/W/X check (cfg_A_off / mprv family).
// Execute-first: jalr to the region, one word store, one word load. RVTEST_FENCEI syncs
// the I-cache before the jump. The only XLEN difference is the written sentinel value
// (RV32: NOP, RV64: DOUBLE_NOP), selected with .if below. Needs test_1_str..test_3_str.
//   ADDRESS   - region label to probe
//   TEST_CASE - prefix for the local result labels (TEST_CASE_1 .. _3)
.macro PMP_VERIFICATION_RWX ADDRESS, TEST_CASE
    // Execution Access Check
    LA (a4, \ADDRESS)
    LA(ra, 1f)                           // ra: where the trap handler resumes on a fetch fault (and the region's ret target)
    RVTEST_FENCEI                              // sync I-cache: a prior store may have updated this executable region
    \TEST_CASE\()_1:
    jalr x0, 0(a4)
    nop
1:
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)

    // Store Access Check
    LA(a5, \ADDRESS)                                         // Address to be verified
  .if (UDB_MXLEN == 64)
    LI(a4, DOUBLE_NOP)                                       // Value to write (DOUBLE_NOP)
  .else
    LI(a4, NOP)                                              // Value to write (NOP)
  .endif
    \TEST_CASE\()_2:
    sw a4, 0(a5)                                             // Word store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)

    // Load Access Check
    \TEST_CASE\()_3:
    lw a4, 0(a5)                                             // Word load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)
.endm

// PMP_VERIFICATION_RWX_LEGAL: full boundary R/W/X check (the *_legal_lxwr/lwxr family).
// Probes execute, then store, then load at five offsets relative to the region:
// start, start-4, start+4, start+g-4, start+g, where g = (1<<UDB_PMP_GRANULARITY) is the
// PMP granule size in bytes. Cases are numbered in execution order: the five execute
// probes are recorded as TEST_CASE_1..5, then the five stores (_6.._10) and five loads
// (_11.._15). RVTEST_FENCEI at the top syncs the I-cache so a prior invocation's store
// can't leave a stale instruction. Needs test_1_str..test_15_str.
//   ADDRESS   - region label to probe
//   TEST_CASE - prefix for the local result labels
.macro PMP_VERIFICATION_RWX_LEGAL ADDRESS, TEST_CASE

    RVTEST_FENCEI

    // Execution Access Check
    LA (a4, \ADDRESS)
    LA(ra, 1f)         // ra: resume target on a fetch fault (and the region's ret target)
    \TEST_CASE\()_1:
    jalr x0, 0(a4)
    nop
    nop
1:
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)

    addi a4, a4, -4                     // REGIONSTART - 4
    LA(ra, 2f)         // ra: resume target on a fetch fault (and the region's ret target)
    \TEST_CASE\()_2:
    jalr x0, 0(a4)
    nop
    nop
2:
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)

    addi a4, a4, 8                      // REGIONSTART + 4
    LA(ra, 3f)         // ra: resume target on a fetch fault (and the region's ret target)
    \TEST_CASE\()_3:
    jalr x0, 0(a4)
    nop
    nop
3:
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)

    // t0 <- g_napot - 8, where g_napot = 2^GRAN at grain>3, else 2^(GRAN+1) (matches the
    // coverage model's PMP_NAPOT_REGION_START granularity, NOT the plain PMP granule
    // 1<<UDB_PMP_GRANULARITY used elsewhere in this macro's addressing).
    .if (UDB_PMP_GRANULARITY > 3)
    LI(t0, ((1<<(UDB_PMP_GRANULARITY))-8))
    .else
    LI(t0, ((1<<(UDB_PMP_GRANULARITY+1))-8))
    .endif   // g - 8, where g = (1<<UDB_PMP_GRANULARITY) is the granule size in bytes
    add a4, a4, t0                  // REGIONSTART + g - 4
    LA(ra, 4f)         // ra: resume target on a fetch fault (and the region's ret target)
    \TEST_CASE\()_4:
    jalr x0, 0(a4)
    nop
    nop
4:
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_4, test_4_str)

    addi a4, a4, 4                      // REGIONSTART + g
    \TEST_CASE\()_5:
    LA(ra, 5f)         // ra: resume target on a fetch fault (and the region's ret target)
    jalr x0, 0(a4)
    nop
    nop
5:
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_5, test_5_str)

    LI(a4, NOP)                                             // Value to write (NOP)
    // Store Access Check
    LA(a5, \ADDRESS)                                        // Address to be verified

    \TEST_CASE\()_6:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_6, test_6_str)

    addi a5, a5, -4                                         // REGIONSTART - 4

    \TEST_CASE\()_7:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_7, test_7_str)

    addi a5, a5, 8                                          // REGIONSTART + 4

    \TEST_CASE\()_8:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_8, test_8_str)

    // t0 <- g_napot - 8, where g_napot = 2^GRAN at grain>3, else 2^(GRAN+1) (matches the
    // coverage model's PMP_NAPOT_REGION_START granularity, NOT the plain PMP granule
    // 1<<UDB_PMP_GRANULARITY used elsewhere in this macro's addressing).
    .if (UDB_PMP_GRANULARITY > 3)
    LI(t0, ((1<<(UDB_PMP_GRANULARITY))-8))
    .else
    LI(t0, ((1<<(UDB_PMP_GRANULARITY+1))-8))
    .endif   // g - 8, where g = (1<<UDB_PMP_GRANULARITY) is the granule size in bytes
    add a5, a5, t0                                      // REGIONSTART + g - 4

    \TEST_CASE\()_9:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_9, test_9_str)

    addi a5, a5, 4                                          // REGIONSTART + g

    \TEST_CASE\()_10:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_10, test_10_str)

    LA(a5, \ADDRESS)                                        // Address to be verified

    \TEST_CASE\()_11:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_11, test_11_str)                                   // Signature update

    addi a5, a5, -4                                         // REGIONSTART - 4

    \TEST_CASE\()_12:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_12, test_12_str)                                   // Signature update

    addi a5, a5, 8                                          // REGIONSTART + 4

    \TEST_CASE\()_13:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_13, test_13_str)                                   // Signature update

    // t0 <- g_napot - 8, where g_napot = 2^GRAN at grain>3, else 2^(GRAN+1) (matches the
    // coverage model's PMP_NAPOT_REGION_START granularity, NOT the plain PMP granule
    // 1<<UDB_PMP_GRANULARITY used elsewhere in this macro's addressing).
    .if (UDB_PMP_GRANULARITY > 3)
    LI(t0, ((1<<(UDB_PMP_GRANULARITY))-8))
    .else
    LI(t0, ((1<<(UDB_PMP_GRANULARITY+1))-8))
    .endif   // g - 8, where g = (1<<UDB_PMP_GRANULARITY) is the granule size in bytes
    add a5, a5, t0                                      // REGIONSTART + g - 4

    \TEST_CASE\()_14:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_14, test_14_str)                                   // Signature update

    addi a5, a5, 4                                          // REGIONSTART + g

    \TEST_CASE\()_15:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_15, test_15_str)                                   // Signature update
.endm

// PMP_VERIFICATION_RWX_ALL: all-access-width R/W/X check (the cfg_XWR_all family).
// Execute-first: probe execution, then every store width, then every load width,
// recording each outcome. RVTEST_FENCEI syncs the I-cache before the jump in case a
// prior invocation's store updated this executable region. RV64 additionally exercises
// doubleword accesses (sd/lwu/ld) and uses DOUBLE_NOP; RV32 uses NOP — selected with .if.
// Each referenced test_<n>_str must be defined, and SIGUPD_COUNT sized accordingly
// (RV32: 9 cases, RV64: 12).
//   ADDRESS   - region label to probe
//   TEST_CASE - prefix for the local result labels
.macro PMP_VERIFICATION_RWX_ALL ADDRESS, TEST_CASE
    // Execution Access Check
    LA (a4, \ADDRESS)
    LA(ra, 1f)                           // ra: where the trap handler resumes on a fetch fault (and the region's ret target)
    RVTEST_FENCEI                              // sync I-cache: a prior store may have updated this executable region
  .if (UDB_MXLEN == 64)
    \TEST_CASE\()_12:
  .else
    \TEST_CASE\()_9:
  .endif
    jalr x0, 0(a4)
    nop
1:
    nop
  .if (UDB_MXLEN == 64)
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_12, test_12_str)
  .else
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_9, test_9_str)
  .endif

    // Store Access Check
    LA(a5, \ADDRESS)                                         // Address to be verified
  .if (UDB_MXLEN == 64)
    LI(a4, DOUBLE_NOP)                                              // Value to write (DOUBLE_NOP)
  .else
    LI(a4, NOP)                                              // Value to write (NOP)
  .endif
    \TEST_CASE\()_1:
    sb a4, 0(a5)                                             // Byte-level store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)
    \TEST_CASE\()_2:
    sh a4, 0(a5)                                             // Half-word store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)
    \TEST_CASE\()_3:
    sw a4, 0(a5)                                             // Word store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)
  .if (UDB_MXLEN == 64)
    \TEST_CASE\()_4:
    sd a4, 0(a5)                                             // Doubleword store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_4, test_4_str)
  .endif

    // Load Access Check
  .if (UDB_MXLEN == 64)
    \TEST_CASE\()_5:
    lb a4, 0(a5)                                             // Byte-level load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_5, test_5_str)                                   // Signature update
    \TEST_CASE\()_6:
    lbu a4, 0(a5)                                             // Byte-level load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_6, test_6_str)                                  // Signature update
    \TEST_CASE\()_7:
    lh a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_7, test_7_str)                                   // Signature update
    \TEST_CASE\()_8:
    lhu a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_8, test_8_str)                                  // Signature update
    \TEST_CASE\()_9:
    lw a4, 0(a5)                                             // Word load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_9, test_9_str)                                   // Signature update
    \TEST_CASE\()_10:
    lwu a4, 0(a5)                                             // Word load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_10, test_10_str)                                   // Signature update
    \TEST_CASE\()_11:
    ld a4, 0(a5)                                             // Doubleword load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_11, test_11_str)                                   // Signature update
  .else
    \TEST_CASE\()_4:
    lb a4, 0(a5)                                             // Byte-level load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_4, test_4_str)                                   // Signature update
    \TEST_CASE\()_5:
    lbu a4, 0(a5)                                             // Byte-level load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_5, test_5_str)                                  // Signature update
    \TEST_CASE\()_6:
    lh a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_6, test_6_str)                                   // Signature update
    \TEST_CASE\()_7:
    lhu a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_7, test_7_str)                                  // Signature update
    \TEST_CASE\()_8:
    lw a4, 0(a5)                                             // Word load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_8, test_8_str)                                   // Signature update
  .endif
.endm

// PMP_VERIFICATION_X_ZCD: compressed double-precision FP access check (Zcd).
// Loads 1.0 into f8, then stores/loads it at ADDRESS with c.fsd/c.fld (recorded as
// TEST_CASE_1/_2) and again through sp with c.fsdsp/c.fldsp, recording whether the PMP
// region permits the access. No jump, so no RVTEST_FENCEI is required.
//   ADDRESS   - region label to probe
//   TEST_CASE - prefix for the local result labels (TEST_CASE_1 .. _2)
.macro PMP_VERIFICATION_X_ZCD ADDRESS, TEST_CASE

    li    x15, 0x3f800000               // bit pattern for 1.0f (IEEE-754 single)
    fmv.w.x f8, x15                     // move 32-bit integer bits into float reg f8
    // Store Access Check
    LA(x8, \ADDRESS)                                         // Address to be verified
    \TEST_CASE\()_1:
    c.fsd f8, 0(x8)
    c.nop
    c.nop
    c.nop
    c.nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)

    \TEST_CASE\()_2:
    c.fld f8, 0(x8)
    c.nop
    c.nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)

    mv t0, sp
    addi sp, x8, 0


    c.fsdsp f8, 0(sp)
    c.nop
    c.nop
    c.nop
    c.nop


    c.fldsp f8, 0(sp)
    c.nop
    c.nop
    mv sp, t0


.endm

// PMP_VERIFICATION_X_ZCB: compressed byte/half access check (Zcb).
// Runs the compressed loads/stores c.sb/c.lbu/c.sh/c.lhu/c.lh at ADDRESS and records each
// outcome (TEST_CASE_1 .. _6), verifying how the PMP region responds. No jump, so no
// RVTEST_FENCEI is required.
//   ADDRESS   - region label to probe
//   TEST_CASE - prefix for the local result labels (TEST_CASE_1 .. _6)
.macro PMP_VERIFICATION_X_ZCB ADDRESS, TEST_CASE

    LI(x15, NOP)                                              // Value to write (NOP)
    // Store Access Check
    LA(x8, \ADDRESS)                                         // Address to be verified
    \TEST_CASE\()_1:
    c.sb   x15, 0(x8)
    c.nop
    c.nop
    c.nop
    c.nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)

    \TEST_CASE\()_2:
    c.lbu  x15, 0(x8)
    c.nop
    c.nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)

    \TEST_CASE\()_3:
    c.sh   x15, 0(x8)
    c.nop
    c.nop
    c.nop
    c.nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)

    \TEST_CASE\()_4:
    c.lhu  x15, 0(x8)
    c.nop
    c.nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_4, test_4_str)

    \TEST_CASE\()_5:
    c.sh   x15, 0(x8)
    c.nop
    c.nop
    c.nop
    c.nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_5, test_5_str)

    \TEST_CASE\()_6:
    c.lh   x15, 0(x8)
    c.nop
    c.nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_6, test_6_str)

.endm

// PMP_VERIFICATION_RWX_NA4_RV32: boundary R/W/X check for a 4-byte NA4 region (RV32).
// Probes execute at start, start-4, start+4 (recorded _1.._3), then stores and loads a
// word at start, start-4, start+4 (recorded _4.._9). RVTEST_FENCEI at the top syncs the
// I-cache so a prior invocation's store can't leave a stale instruction.
// Needs test_1_str..test_9_str.
//   ADDRESS   - region label to probe
//   TEST_CASE - prefix for the local result labels
.macro PMP_VERIFICATION_RWX_NA4_RV32 ADDRESS, TEST_CASE

    RVTEST_FENCEI

    // Execution Access Check
    LA (a4, \ADDRESS)
    LA(ra, 1f)                           // ra: where the trap handler resumes on a fetch fault (and the region's ret target)
    \TEST_CASE\()_1:
    jalr x0, 0(a4)
    nop
1:
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)

    addi a4, a4, -4                     // REGIONSTART - 4
    LA(ra, 2f)           // ra: resume target on a fetch fault (and the region's ret target)
    \TEST_CASE\()_2:
    jalr x0, 0(a4)
    nop
2:
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)

    addi a4, a4, 8                      // REGIONSTART + 4
    LA(ra, 3f)           // ra: resume target on a fetch fault (and the region's ret target)
    \TEST_CASE\()_3:
    jalr x0, 0(a4)
    nop
3:
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)

    LI(a4, NOP)                                              // Value to write (NOP)
    // Load & Store Access Check
    LA(a5, \ADDRESS)                                         // Address to be verified

    \TEST_CASE\()_4:
    sw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_4, test_4_str)

    \TEST_CASE\()_5:
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_5, test_5_str)                                  // Signature update

    addi a5, a5, -4                                         // REGIONSTART - 4
    \TEST_CASE\()_6:
    sw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_6, test_6_str)

    \TEST_CASE\()_7:
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_7, test_7_str)

    addi a5, a5, 8                                          // REGIONSTART + 4                                            // Address to be verified
    \TEST_CASE\()_8:
    sw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_8, test_8_str)

    \TEST_CASE\()_9:
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_9, test_9_str)

.endm

// PMP_VERIFICATION_RWX_NAPOT: full boundary R/W/X check for NAPOT regions (napot_legal
// family). Execute-first over the region's sub-blocks, then stores, then loads at NAPOT
// boundaries; offsets use the PMP granule (1<<UDB_PMP_GRANULARITY). RV64 additionally
// exercises sd/ld/lwu (cases _22.._24) and uses DOUBLE_NOP; RV32 uses NOP — selected with
// .if. Needs the test_<n>_str labels (RV32: through _21, RV64: through _24).
//   ADDRESS   - region label to probe
//   TEST_CASE - prefix for the local result labels
.macro PMP_VERIFICATION_RWX_NAPOT ADDRESS, TEST_CASE

    RVTEST_FENCEI

    // Execution Access Check
    LA (a4, \ADDRESS)
    LA(ra, 1f)         // ra: resume target on a fetch fault (and the region's ret target)
    \TEST_CASE\()_17:
    jalr x0, 0(a4)
    nop
    nop
1:
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_17, test_17_str)

    addi a4, a4, -4                     // REGIONSTART - 4
    LA(ra, 2f)         // ra: resume target on a fetch fault (and the region's ret target)
    \TEST_CASE\()_18:
    jalr x0, 0(a4)
    nop
    nop
2:
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_18, test_18_str)

    addi a4, a4, 8                      // REGIONSTART + 4
    LA(ra, 3f)         // ra: resume target on a fetch fault (and the region's ret target)
    \TEST_CASE\()_19:
    jalr x0, 0(a4)
    nop
    nop
3:
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_19, test_19_str)

    // t0 <- g_napot - 8, where g_napot = 2^GRAN at grain>3, else 2^(GRAN+1) (matches the
    // coverage model's PMP_NAPOT_REGION_START granularity, NOT the plain PMP granule
    // 1<<UDB_PMP_GRANULARITY used elsewhere in this macro's addressing).
    .if (UDB_PMP_GRANULARITY > 3)
    LI(t0, ((1<<(UDB_PMP_GRANULARITY))-8))
    .else
    LI(t0, ((1<<(UDB_PMP_GRANULARITY+1))-8))
    .endif
    add a4, a4, t0                  // REGIONSTART + (1<<(UDB_PMP_GRANULARITY)) - 4
    LA(ra, 4f)         // ra: resume target on a fetch fault (and the region's ret target)
    \TEST_CASE\()_20:
    jalr x0, 0(a4)
    nop
    nop
4:
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_20, test_20_str)

    addi a4, a4, 4                      // REGIONSTART + (1<<(UDB_PMP_GRANULARITY))
    LA(ra, 5f)         // ra: resume target on a fetch fault (and the region's ret target)
    \TEST_CASE\()_21:
    jalr x0, 0(a4)
    nop
    nop
5:
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_21, test_21_str)

  .if (UDB_MXLEN == 64)
    LI(a4, DOUBLE_NOP)                                             // Value to write (DOUBLE_NOP)
  .else
    LI(a4, NOP)                                             // Value to write (NOP)
  .endif
    // Store Access Check
    LA(a5, \ADDRESS)                                        // Address to be verified

    \TEST_CASE\()_1:
    sb a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)

    \TEST_CASE\()_2:
    sh a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)

    \TEST_CASE\()_3:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)

    addi a5, a5, -4                                         // REGIONSTART - 4

    \TEST_CASE\()_4:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_4, test_4_str)

    addi a5, a5, 8                                          // REGIONSTART + 4

    \TEST_CASE\()_5:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_5, test_5_str)

    // t0 <- g_napot - 8, where g_napot = 2^GRAN at grain>3, else 2^(GRAN+1) (matches the
    // coverage model's PMP_NAPOT_REGION_START granularity, NOT the plain PMP granule
    // 1<<UDB_PMP_GRANULARITY used elsewhere in this macro's addressing).
    .if (UDB_PMP_GRANULARITY > 3)
    LI(t0, ((1<<(UDB_PMP_GRANULARITY))-8))
    .else
    LI(t0, ((1<<(UDB_PMP_GRANULARITY+1))-8))
    .endif
    add a5, a5, t0                                      // REGIONSTART + (1<<(UDB_PMP_GRANULARITY)) - 4

    \TEST_CASE\()_6:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_6, test_6_str)

    addi a5, a5, 4                                          // REGIONSTART + (1<<(UDB_PMP_GRANULARITY))

    \TEST_CASE\()_7:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_7, test_7_str)

    LA(a5, \ADDRESS)                                        // Address to be verified

    \TEST_CASE\()_8:
    lb a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_8, test_8_str)                                   // Signature update

    \TEST_CASE\()_9:
    lbu a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_9, test_9_str)                                   // Signature update

    \TEST_CASE\()_10:
    lh a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_10, test_10_str)                                   // Signature update

    \TEST_CASE\()_11:
    lhu a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_11, test_11_str)                                   // Signature update

    \TEST_CASE\()_12:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_12, test_12_str)                                   // Signature update

    addi a5, a5, -4                                         // REGIONSTART - 4

    \TEST_CASE\()_13:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_13, test_13_str)                                   // Signature update

    addi a5, a5, 8                                          // REGIONSTART + 4

    \TEST_CASE\()_14:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_14, test_14_str)                                   // Signature update

    // t0 <- g_napot - 8, where g_napot = 2^GRAN at grain>3, else 2^(GRAN+1) (matches the
    // coverage model's PMP_NAPOT_REGION_START granularity, NOT the plain PMP granule
    // 1<<UDB_PMP_GRANULARITY used elsewhere in this macro's addressing).
    .if (UDB_PMP_GRANULARITY > 3)
    LI(t0, ((1<<(UDB_PMP_GRANULARITY))-8))
    .else
    LI(t0, ((1<<(UDB_PMP_GRANULARITY+1))-8))
    .endif
    add a5, a5, t0                                      // REGIONSTART + (1<<(UDB_PMP_GRANULARITY)) - 4

    \TEST_CASE\()_15:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_15, test_15_str)                                   // Signature update

    addi a5, a5, 4                                          // REGIONSTART + (1<<(UDB_PMP_GRANULARITY))

    \TEST_CASE\()_16:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_16, test_16_str)
  .if (UDB_MXLEN == 64)

    LA(a5, \ADDRESS)

    \TEST_CASE\()_22:
    sd a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_22, test_22_str)

    \TEST_CASE\()_23:
    ld a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_23, test_23_str)                                    // Signature update

    \TEST_CASE\()_24:
    lwu a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_24, test_24_str)                                   // Signature update

  .endif
.endm

// PMP_VERIFICATION_RWX_NAPOT_SM_RV64: boundary R/W/X check for a NAPOT region (RV64,
// Smepmp napot_legal family). Executes from start, start-4, start+4, start+g_napot-4,
// start+g_napot (the minimum NAPOT region size g_napot = 2^(UDB_PMP_GRANULARITY+1) at
// grain <=3, matching the coverage model's PMP_NAPOT_REGION_START granularity, NOT the
// same as the plain PMP granule (1<<UDB_PMP_GRANULARITY)) to exercise the fetch path,
// then records every store width (sb/sh/sw/sd, _1.._4) plus boundary word stores
// (_5.._8) and every load width (lb/lbu/lh/lhu/lw/lwu/ld, _9.._15) plus boundary word
// loads (_16.._19). The five execute probes are recorded as _20.._24. RVTEST_FENCEI
// before the first jump syncs the I-cache after a prior store. Needs test_1_str..test_24_str.
//   ADDRESS   - region label to probe
//   TEST_CASE - prefix for the local result labels
.macro PMP_VERIFICATION_RWX_NAPOT_SM_RV64 ADDRESS, TEST_CASE

    // t1 <- g_napot - 8, reused at each "highest_word"/"just_beyond" boundary probe below.
    .if (UDB_PMP_GRANULARITY > 3)
    LI(t1, (1<<(UDB_PMP_GRANULARITY))-8)
    .else
    LI(t1, (1<<(UDB_PMP_GRANULARITY+1))-8)
    .endif

    // Execution Access Check — probe start, start-4, start+4, start+g_napot-4,
    // start+g_napot and record each outcome (_20.._24). Each probe sets ra to its
    // resume label so the trap handler returns there after an execute (fetch) fault
    // instead of looping.
    LA (a4, \ADDRESS)
    LA(ra, 1f)                            // ra: resume target on a fetch fault (and the region's ret target)
    RVTEST_FENCEI                         // sync I-cache: a prior store may have updated this executable region
    \TEST_CASE\()_20:
    jalr x0, 0(a4)
    nop
1:
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_20, test_20_str)

    addi a4, a4, -4                       // REGIONSTART - 4
    LA(ra, 2f)                            // ra: resume target on a fetch fault (and the region's ret target)
    \TEST_CASE\()_21:
    jalr x0, 0(a4)
    nop
2:
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_21, test_21_str)

    addi a4, a4, 8                        // REGIONSTART + 4
    LA(ra, 3f)                            // ra: resume target on a fetch fault (and the region's ret target)
    \TEST_CASE\()_22:
    jalr x0, 0(a4)
    nop
3:
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_22, test_22_str)

    add a4, a4, t1                        // REGIONSTART + g_napot - 4
    LA(ra, 4f)                            // ra: resume target on a fetch fault (and the region's ret target)
    \TEST_CASE\()_23:
    jalr x0, 0(a4)
    nop
4:
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_23, test_23_str)

    addi a4, a4, 4                        // REGIONSTART + g_napot
    LA(ra, 5f)                            // ra: resume target on a fetch fault (and the region's ret target)
    \TEST_CASE\()_24:
    jalr x0, 0(a4)
    nop
5:
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_24, test_24_str)

    LI(a4, DOUBLE_NOP)                                       // Value to write (DOUBLE_NOP)

    // Store Access Check
    LA(a5, \ADDRESS)                                         // Address to be verified

    \TEST_CASE\()_1:
    sb a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)

    \TEST_CASE\()_2:
    sh a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)

    \TEST_CASE\()_3:
    sw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)

    \TEST_CASE\()_4:
    sd a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_4, test_4_str)


    addi a5, a5, -4                                          // REGIONSTART - 4

    \TEST_CASE\()_5:
    sw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_5, test_5_str)


    addi a5, a5, 8                                           // REGIONSTART + 4

    \TEST_CASE\()_6:
    sw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_6, test_6_str)


    add a5, a5, t1                                           // REGIONSTART + g_napot - 4

    \TEST_CASE\()_7:
    sw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_7, test_7_str)


    addi a5, a5, 4                                           // REGIONSTART + g_napot

    \TEST_CASE\()_8:
    sw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_8, test_8_str)

    LA(a5, \ADDRESS)

    \TEST_CASE\()_9:
    lb a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_9, test_9_str)

    \TEST_CASE\()_10:
    lbu a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_10, test_10_str)

    \TEST_CASE\()_11:
    lh a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_11, test_11_str)

    \TEST_CASE\()_12:
    lhu a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_12, test_12_str)

    \TEST_CASE\()_13:
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_13, test_13_str)

    \TEST_CASE\()_14:
    lwu a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_14, test_14_str)

    \TEST_CASE\()_15:
    ld a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_15, test_15_str)


    addi a5, a5, -4

    \TEST_CASE\()_16:
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_16, test_16_str)


    addi a5, a5, 8

    \TEST_CASE\()_17:
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_17, test_17_str)


    add a5, a5, t1                                           // REGIONSTART + g_napot - 4

    \TEST_CASE\()_18:
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_18, test_18_str)


    addi a5, a5, 4

    \TEST_CASE\()_19:
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_19, test_19_str)

.endm
