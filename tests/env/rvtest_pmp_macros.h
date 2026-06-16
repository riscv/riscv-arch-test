// rvtest_pmp_macros.h
// PMP R/W/X verification macros for the PMP test suite (tests/priv/pmp/...).
// SPDX-License-Identifier: Apache-2.0
//
// Shared, centralized versions of the per-test PMP_VERIFICATION_* macros. Each macro
// probes how a PMP-protected region responds to execute / store / load accesses and
// records the outcome with RVTEST_SIGUPD. Defined here (instead of redefined in every
// test) so cross-cutting fixes — e.g. inserting RVMODEL_FENCEI to sync the I-cache
// after writing executable code — are made in one place. RVMODEL_FENCEI is
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

// rvtest_pmp_macros.h is included before rvtest_trap_handler.h (where RVMODEL_FENCEI is
// normally defined), so define it here too. The #ifndef guard makes the later
// definition in rvtest_trap_handler.h a no-op; ZIFENCEI_SUPPORTED comes from the
// already-included derived_config.h. Keep this in sync with rvtest_trap_handler.h.
#ifndef   RVMODEL_FENCEI
  #ifndef ZIFENCEI_SUPPORTED
       #define RVMODEL_FENCEI nop                // no Zifencei: assume coherent I-cache
  #else
       #define RVMODEL_FENCEI fence.i            // Zifencei available: use fence.i
  #endif
#endif
// PMP_VERIFICATION_X_C: compressed execute-only check.
// Jumps (c.jalr) to ADDRESS and records whether execution was permitted.
// No store occurs, so no RVMODEL_FENCEI is required.
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
// ordinary store, so no RVMODEL_FENCEI is required.
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
// Execute-first: jalr to the region, one word store, one word load. RVMODEL_FENCEI syncs
// the I-cache before the jump. The only XLEN difference is the written sentinel value
// (RV32: NOP, RV64: DOUBLE_NOP), selected with .if below. Needs test_1_str..test_3_str.
//   ADDRESS   - region label to probe
//   TEST_CASE - prefix for the local result labels (TEST_CASE_1 .. _3)
.macro PMP_VERIFICATION_RWX ADDRESS, TEST_CASE
    // Execution Access Check
    LA (a4, \ADDRESS)
    LI(x4, 0xACCE)                        // Store a value which is to be checked in trap handler
    LA(x1, 1f)                            // Store the return Address in x1
    RVMODEL_FENCEI                              // sync I-cache: a prior store may have updated this executable region
    \TEST_CASE\()_1:
    jalr ra, 0(a4)
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
// start, start-4, start+4, start+g-4, start+g (g = PMP granule). Execute is done first
// for all five offsets (results recorded as TEST_CASE_11..15), then the five stores
// (_1.._5) and five loads (_6.._10). RVMODEL_FENCEI at the top syncs the I-cache so a
// prior invocation's store can't leave a stale instruction. Needs `g` defined and test_1_str..test_15_str.
//   ADDRESS   - region label to probe
//   TEST_CASE - prefix for the local result labels
.macro PMP_VERIFICATION_RWX_LEGAL ADDRESS, TEST_CASE

    RVMODEL_FENCEI

    LI(x4, 0xACCE)                      // Store a value which is to be checked in trap handler
    // Execution Access Check
    LA (a4, \ADDRESS)
    LA(x1, 1f)                          // Store the return Address in x1
    \TEST_CASE\()_11:
    jalr ra, 0(a4)
    nop
    nop
1:
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_11, test_11_str)

    LI(x4, 0xACCE)                      // Store a value which is to be checked in trap handler
    addi a4, a4, -4                     // REGIONSTART - 4
    LA(x1, 2f)                          // Store the return Address in x1
    \TEST_CASE\()_12:
    jalr ra, 0(a4)
    nop
    nop
2:
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_12, test_12_str)

    LI(x4, 0xACCE)                      // Store a value which is to be checked in trap handler
    addi a4, a4, 8                      // REGIONSTART + 4
    LA(x1, 3f)                          // Store the return Address in x1
    \TEST_CASE\()_13:
    jalr ra, 0(a4)
    nop
    nop
3:
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_13, test_13_str)

    li t0, ((1<<(UDB_PMP_GRANULARITY))-8)   // g-8, where g = PMP granule
    add a4, a4, t0                  // REGIONSTART + g - 4
    LA(x1, 4f)                          // Store the return Address in x1
    \TEST_CASE\()_14:
    jalr ra, 0(a4)
    nop
    nop
4:
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_14, test_14_str)

    addi a4, a4, 4                      // REGIONSTART + g
    \TEST_CASE\()_15:
    LA(x1, 5f)                          // Store the return Address in x1
    jalr ra, 0(a4)
    nop
    nop
5:
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_15, test_15_str)

    LI(a4, NOP)                                             // Value to write (NOP)
    // Store Access Check
    LA(a5, \ADDRESS)                                        // Address to be verified

    \TEST_CASE\()_1:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)

    addi a5, a5, -4                                         // REGIONSTART - 4

    \TEST_CASE\()_2:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)

    addi a5, a5, 8                                          // REGIONSTART + 4

    \TEST_CASE\()_3:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)

    li t0, ((1<<(UDB_PMP_GRANULARITY))-8)   // g-8, where g = PMP granule
    add a5, a5, t0                                      // REGIONSTART + g - 4

    \TEST_CASE\()_4:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_4, test_4_str)

    addi a5, a5, 4                                          // REGIONSTART + g

    \TEST_CASE\()_5:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_5, test_5_str)

    LA(a5, \ADDRESS)                                        // Address to be verified

    \TEST_CASE\()_6:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_6, test_6_str)                                   // Signature update

    addi a5, a5, -4                                         // REGIONSTART - 4

    \TEST_CASE\()_7:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_7, test_7_str)                                   // Signature update

    addi a5, a5, 8                                          // REGIONSTART + 4

    \TEST_CASE\()_8:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_8, test_8_str)                                   // Signature update

    li t0, ((1<<(UDB_PMP_GRANULARITY))-8)   // g-8, where g = PMP granule
    add a5, a5, t0                                      // REGIONSTART + g - 4

    \TEST_CASE\()_9:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_9, test_9_str)                                   // Signature update

    addi a5, a5, 4                                          // REGIONSTART + g

    \TEST_CASE\()_10:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_10, test_10_str)                                   // Signature update
.endm

// PMP_VERIFICATION_RWX_ALL: all-access-width R/W/X check (the cfg_XWR_all family).
// Execute-first: probe execution, then every store width, then every load width,
// recording each outcome. RVMODEL_FENCEI syncs the I-cache before the jump in case a
// prior invocation's store updated this executable region. RV64 additionally exercises
// doubleword accesses (sd/lwu/ld) and uses DOUBLE_NOP; RV32 uses NOP — selected with .if.
// Each referenced test_<n>_str must be defined, and SIGUPD_COUNT sized accordingly
// (RV32: 9 cases, RV64: 12).
//   ADDRESS   - region label to probe
//   TEST_CASE - prefix for the local result labels
.macro PMP_VERIFICATION_RWX_ALL ADDRESS, TEST_CASE
    // Execution Access Check
    LA (a4, \ADDRESS)
    LI(x4, 0xACCE)                        // Store a value which is to be checked in trap handler
    LA(x1, 1f)                            // Store the return Address in x1
    RVMODEL_FENCEI                              // sync I-cache: a prior store may have updated this executable region
  .if (UDB_MXLEN == 64)
    \TEST_CASE\()_12:
  .else
    \TEST_CASE\()_9:
  .endif
    jalr ra, 0(a4)
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

// PMP_VERIFICATION_X_ZCD: centralized body for the zcd_legal_lxwr.S
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

// PMP_VERIFICATION_X_ZCB: centralized body for the zcb_legal_lxwr.S family
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

// PMP_VERIFICATION_RWX_NA4_RV32: centralized body for the na4_legal_lxwr.S family
.macro PMP_VERIFICATION_RWX_NA4_RV32 ADDRESS, TEST_CASE

    RVMODEL_FENCEI

    LI(x4, 0xACCE)                        // Store a value which is to be checked in trap handler
    // Execution Access Check
    LA (a4, \ADDRESS)
    LA(x1, 1f)                            // Store the return Address in x1
    \TEST_CASE\()_1:
    jalr ra, 0(a4)
    nop
1:
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)

    addi a4, a4, -4                     // REGIONSTART - 4
    LA(x1, 2f)                            // Store the return Address in x1
    \TEST_CASE\()_2:
    jalr ra, 0(a4)
    nop
2:
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)

    addi a4, a4, 8                      // REGIONSTART + 4
    LA(x1, 3f)                            // Store the return Address in x1
    \TEST_CASE\()_3:
    jalr ra, 0(a4)
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

    RVMODEL_FENCEI

    LI(x4, 0xACCE)                      // Store a value which is to be checked in trap handler
    // Execution Access Check
    LA (a4, \ADDRESS)
    LA(x1, 1f)                          // Store the return Address in x1
    \TEST_CASE\()_17:
    jalr ra, 0(a4)
    nop
    nop
1:
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_17, test_17_str)

    LI(x4, 0xACCE)                        // Store a value which is to be checked in trap handler
    addi a4, a4, -4                     // REGIONSTART - 4
    LA(x1, 2f)                          // Store the return Address in x1
    \TEST_CASE\()_18:
    jalr ra, 0(a4)
    nop
    nop
2:
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_18, test_18_str)

    LI(x4, 0xACCE)                        // Store a value which is to be checked in trap handler
    addi a4, a4, 8                      // REGIONSTART + 4
    LA(x1, 3f)                          // Store the return Address in x1
    \TEST_CASE\()_19:
    jalr ra, 0(a4)
    nop
    nop
3:
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_19, test_19_str)

    li t0, ((1<<(UDB_PMP_GRANULARITY))-8)
    add a4, a4, t0                  // REGIONSTART + (1<<(UDB_PMP_GRANULARITY)) - 4
    LA(x1, 4f)                          // Store the return Address in x1
    \TEST_CASE\()_20:
    jalr ra, 0(a4)
    nop
    nop
4:
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_20, test_20_str)

    addi a4, a4, 4                      // REGIONSTART + (1<<(UDB_PMP_GRANULARITY))
    LA(x1, 5f)                          // Store the return Address in x1
    \TEST_CASE\()_21:
    jalr ra, 0(a4)
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

    li t0, ((1<<(UDB_PMP_GRANULARITY))-8)
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

    li t0, ((1<<(UDB_PMP_GRANULARITY))-8)
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

// PMP_VERIFICATION_RWX_NAPOT_SM_RV64: centralized body for the napot_legal_lxwr-01.S family
.macro PMP_VERIFICATION_RWX_NAPOT_SM_RV64 ADDRESS, TEST_CASE

    LI(x4, 0xACCE)                        // Store a value which is to be checked in trap handler
    // Execution Access Check
    LA (a4, \ADDRESS)
    LA(x1, 1f)                            // Store the return Address in x1
    RVMODEL_FENCEI                              // sync I-cache: a prior store may have updated this executable region
    jalr ra, 0(a4)
    nop
1:
    nop

    addi a4, a4, -4                       // REGIONSTART - 4
    LA(x1, 2f)                            // Store the return Address in x1
    jalr ra, 0(a4)
    nop
2:
    nop

    addi a4, a4, 8                        // REGIONSTART + 4
    LA(x1, 3f)                            // Store the return Address in x1
    jalr ra, 0(a4)
    nop
3:
    nop

    LI(t0, (1<<(UDB_PMP_GRANULARITY))-8)
    add a4, a4, t0                        // REGIONSTART + (1<<(UDB_PMP_GRANULARITY)) - 4
    LA(x1, 4f)                            // Store the return Address in x1
    jalr ra, 0(a4)
    nop
4:
    nop

    addi a4, a4, 4                        // REGIONSTART + (1<<(UDB_PMP_GRANULARITY))
    LA(x1, 5f)                            // Store the return Address in x1
    jalr ra, 0(a4)
    nop
5:
    nop

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


    LI(t0, (1<<(UDB_PMP_GRANULARITY))-8)
    add a5, a5, t0                                           // REGIONSTART + (1<<(UDB_PMP_GRANULARITY)) - 4

    \TEST_CASE\()_7:
    sw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_7, test_7_str)


    addi a5, a5, 4                                           // REGIONSTART + (1<<(UDB_PMP_GRANULARITY))

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


    LI(t0, (1<<(UDB_PMP_GRANULARITY))-8)
    add a5, a5, t0

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
